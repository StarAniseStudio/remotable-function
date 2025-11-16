"""
Client - Client-side RPC client for Remotable.

The Client connects to the Gateway server and provides tools for remote invocation.
"""

import asyncio
import json
import logging
import platform
import uuid
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
import websockets
from websockets.client import WebSocketClientProtocol

from ..core.types import ClientInfo, ToolContext, ConnectionState, ToolExecutionState
from ..core.protocol import RPCRequest, RPCResponse, RPCError, RPCErrorCode
from ..core.registry import ToolRegistry
from .tool import Tool

logger = logging.getLogger(__name__)


class Client:
    """
    RPC Client for connecting to Gateway server.

    The Client:
    1. Connects to Gateway via WebSocket
    2. Registers tools with the server
    3. Executes tools when requested by server
    4. Handles heartbeat and reconnection

    Usage:
        import remotable
        remotable.configure(role="client")

        client = remotable.Client(
            server_url="ws://localhost:8000",
            client_id="my-client"
        )

        # Register tools
        from remotable.client.tools import FileSystemTools
        client.register_tools(FileSystemTools())

        # Connect
        await client.connect()

        # Keep alive
        await asyncio.Event().wait()
    """

    def __init__(
        self,
        server_url: str,
        client_id: Optional[str] = None,
        version: str = "1.0.0",
        auto_reconnect: bool = True,
        reconnect_interval: int = 5,
        reconnect_max_attempts: int = 10
    ):
        """
        Initialize Client.

        Args:
            server_url: Gateway server URL (e.g., ws://localhost:8000)
            client_id: Client ID (auto-generated if not provided)
            version: Client version
            auto_reconnect: Enable auto-reconnect
            reconnect_interval: Reconnect interval in seconds
            reconnect_max_attempts: Max reconnect attempts
        """
        self.server_url = server_url
        self.client_id = client_id or f"client-{uuid.uuid4().hex[:8]}"
        self.version = version
        self.auto_reconnect = auto_reconnect
        self.reconnect_interval = reconnect_interval
        self.reconnect_max_attempts = reconnect_max_attempts

        # Client info
        self.client_info = ClientInfo(
            client_id=self.client_id,
            name=self.client_id,  # Use client_id as default name
            version=version,
            platform=platform.system(),
            capabilities=["filesystem", "shell"],
            metadata={}
        )

        # Tool registry
        self.registry = ToolRegistry()
        self._tools: Dict[str, Tool] = {}  # full_name -> Tool instance

        # Connection
        self._websocket: Optional[WebSocketClientProtocol] = None
        self._state = ConnectionState.DISCONNECTED
        self._receive_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._reconnect_attempts = 0

        # Event callbacks
        self._callbacks: Dict[str, List[Callable]] = {
            "connected": [],
            "disconnected": [],
            "tool_executed": [],
            "error": [],
        }

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._state == ConnectionState.CONNECTED

    def on_connected(self, callback: Callable) -> Callable:
        """
        Decorator: Register callback for connection.

        Example:
            @client.on_connected
            async def on_connected():
                print("Connected to server")
        """
        self._callbacks["connected"].append(callback)
        return callback

    def on_disconnected(self, callback: Callable) -> Callable:
        """Decorator: Register callback for disconnection."""
        self._callbacks["disconnected"].append(callback)
        return callback

    def on_tool_executed(self, callback: Callable) -> Callable:
        """Decorator: Register callback for tool execution."""
        self._callbacks["tool_executed"].append(callback)
        return callback

    def on_error(self, callback: Callable) -> Callable:
        """Decorator: Register callback for errors."""
        self._callbacks["error"].append(callback)
        return callback

    async def _emit(self, event: str, *args, **kwargs) -> None:
        """Emit event to all registered callbacks."""
        if event in self._callbacks:
            for callback in self._callbacks[event]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(*args, **kwargs)
                    else:
                        callback(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in {event} callback: {e}")

    def register_tool(self, tool: Tool) -> None:
        """
        Register a single tool.

        Args:
            tool: Tool instance

        Raises:
            ValueError: If tool with same name already registered
        """
        tool_def = tool.to_definition()
        self.registry.register(tool_def)
        self._tools[tool_def.full_name] = tool

    def register_tools(self, *tools: Tool) -> None:
        """
        Register multiple tools.

        Args:
            *tools: Tool instances
        """
        for tool in tools:
            self.register_tool(tool)

    def unregister_tool(self, full_name: str) -> bool:
        """
        Unregister a tool.

        Args:
            full_name: Tool full name (namespace.name)

        Returns:
            True if tool was unregistered, False if not found
        """
        tool_def = self.registry.unregister(full_name)
        if tool_def:
            self._tools.pop(full_name, None)
            logger.info(f"Tool unregistered: {full_name}")
            return True
        return False

    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return [tool.full_name for tool in self.registry.list_all()]

    async def connect(self) -> None:
        """
        Connect to Gateway server.

        This will:
        1. Establish WebSocket connection
        2. Send registration message
        3. Start receive and heartbeat tasks
        """
        if self.is_connected:
            logger.warning("Already connected")
            return

        try:
            self._state = ConnectionState.CONNECTING
            # Only log on first attempt
            if self._reconnect_attempts == 0:
                logger.info(f"Connecting to {self.server_url}...")

            # Connect WebSocket with increased ping timeout
            # Disable websockets' built-in ping/pong to avoid conflicts with our heartbeat
            self._websocket = await websockets.connect(
                self.server_url,
                ping_interval=None,  # Disable built-in ping (we use our own heartbeat)
                ping_timeout=None    # Disable ping timeout
            )

            # Send registration
            await self._register()

            # Update state
            self._state = ConnectionState.CONNECTED
            self._reconnect_attempts = 0

            # Start tasks
            self._receive_task = asyncio.create_task(self._receive_loop())
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            logger.info(f"Connected to server as {self.client_id}")
            await self._emit("connected")

        except Exception as e:
            self._state = ConnectionState.DISCONNECTED
            # Only log detailed error on first attempt
            if self._reconnect_attempts == 0:
                logger.error(f"Connection failed: {e}")
                await self._emit("error", e)

            # Auto-reconnect
            if self.auto_reconnect:
                await self._reconnect()
            else:
                raise

    async def disconnect(self) -> None:
        """Disconnect from server."""
        if not self.is_connected:
            return

        logger.info("Disconnecting...")

        # Cancel tasks
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        # Close WebSocket
        if self._websocket:
            await self._websocket.close()
            self._websocket = None

        self._state = ConnectionState.DISCONNECTED
        logger.info("Disconnected")
        await self._emit("disconnected")

    async def _register(self) -> None:
        """Send registration message to server."""
        if not self._websocket:
            raise RuntimeError("WebSocket not connected")

        # Prepare tools list
        tools = [tool.to_dict() for tool in self.registry.list_all()]

        # Send registration
        message = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "register",
            "params": {
                "client_id": self.client_id,
                "version": self.version,
                "platform": self.client_info.platform,
                "capabilities": self.client_info.capabilities,
                "metadata": self.client_info.metadata,
                "tools": tools
            }
        }

        await self._websocket.send(json.dumps(message))

        # Wait for registration response
        response = await asyncio.wait_for(self._websocket.recv(), timeout=10)
        data = json.loads(response)

        if "error" in data:
            raise Exception(f"Registration failed: {data['error']}")

    async def _receive_loop(self) -> None:
        """Receive messages from server."""
        while self.is_connected and self._websocket:
            try:
                message = await self._websocket.recv()
                await self._handle_message(message)
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Connection closed by server")
                self._state = ConnectionState.DISCONNECTED
                await self._emit("disconnected")

                if self.auto_reconnect:
                    await self._reconnect()
                break
            except Exception as e:
                logger.error(f"Error in receive loop: {e}")
                await self._emit("error", e)

    async def _heartbeat_loop(self) -> None:
        """Send heartbeat to server."""
        while self.is_connected and self._websocket:
            try:
                await asyncio.sleep(30)

                if self.is_connected and self._websocket:
                    await self._websocket.send(json.dumps({
                        "jsonrpc": "2.0",
                        "method": "heartbeat",
                        "params": {}
                    }))

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")

    async def _handle_message(self, message: str) -> None:
        """Handle incoming message from server."""
        try:
            data = json.loads(message)
            method = data.get("method")

            if method == "tool.execute":
                # Execute tool request
                await self._handle_tool_execute(data)

            elif method == "heartbeat":
                # Heartbeat from server (silent)
                pass

            else:
                logger.warning(f"Unknown method: {method}")

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)

    async def _handle_tool_execute(self, request: dict) -> None:
        """Handle tool execution request."""
        request_id = request.get("id")
        params = request.get("params", {})
        tool_name = params.get("tool")
        args = params.get("args", {})

        try:
            # Get tool
            tool = self._tools.get(tool_name)
            if not tool:
                raise ValueError(f"Tool not found: {tool_name}")

            # Create context
            context = ToolContext(
                client_id=self.client_id,
                request_id=request_id,
                timestamp=datetime.now().timestamp(),
                metadata={}
            )

            # Execute tool
            result = await tool(context, **args)

            # Send success response
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }

            if self._websocket:
                await self._websocket.send(json.dumps(response))

            await self._emit("tool_executed", tool_name, result)

        except Exception as e:
            logger.error(f"Tool execution failed ({tool_name}): {e}")

            # Send error response
            error_response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": RPCErrorCode.INTERNAL_ERROR,
                    "message": str(e)
                }
            }

            if self._websocket:
                await self._websocket.send(json.dumps(error_response))

            await self._emit("error", e)

    async def _reconnect(self) -> None:
        """Reconnect to server with exponential backoff."""
        while self._reconnect_attempts < self.reconnect_max_attempts:
            self._reconnect_attempts += 1
            wait_time = min(self.reconnect_interval * (2 ** (self._reconnect_attempts - 1)), 60)

            # Only log on first few attempts to avoid spam
            if self._reconnect_attempts <= 3:
                logger.info(f"Reconnecting in {wait_time}s (attempt {self._reconnect_attempts}/{self.reconnect_max_attempts})...")
            await asyncio.sleep(wait_time)

            try:
                await self.connect()
                return  # Success
            except Exception:
                # Don't log every reconnect failure - too spammy
                pass

        logger.error(f"Max reconnect attempts ({self.reconnect_max_attempts}) reached")
        self._state = ConnectionState.DISCONNECTED

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"Client(id={self.client_id}, state={self._state}, "
            f"tools={len(self._tools)})"
        )
