"""
Remotable Client - Unified implementation for v2.0

A clean, unified RPC client that combines the best of both implementations.
"""

import asyncio
import json
import logging
import uuid
from typing import Optional, Dict, Any, List, Union

import websockets
from websockets.client import WebSocketClientProtocol

from .config import ClientConfig
from .client.tool import Tool
from .core.protocol import RPCRequest, RPCResponse

logger = logging.getLogger(__name__)


class Client:
    """
    Unified RPC Client for Remotable v2.0.

    Supports both configuration object and direct parameters for backward compatibility.

    Examples:
        # Method 1: Using configuration object (recommended)
        config = ClientConfig(server_url="ws://localhost:8000")
        client = Client(config)

        # Method 2: Direct parameters (backward compatible)
        client = Client(server_url="ws://localhost:8000", auth_token="secret")

        # Method 3: Quick start with defaults
        client = Client()
    """

    def __init__(
        self,
        config: Optional[Union[ClientConfig, Dict, str]] = None,
        # Backward compatibility parameters
        server_url: Optional[str] = None,
        client_id: Optional[str] = None,
        auth_token: Optional[str] = None,
        auto_reconnect: Optional[bool] = None,
        **kwargs
    ):
        """
        Initialize Client with flexible configuration.

        Args:
            config: ClientConfig object, dict, or server URL string
            server_url: Server URL (backward compat)
            client_id: Client ID (backward compat)
            auth_token: Authentication token (backward compat)
            auto_reconnect: Enable auto-reconnect (backward compat)
            **kwargs: Additional backward compatibility parameters
        """
        # Handle configuration
        if config is None:
            # Create default config
            config = ClientConfig()

            # Apply individual parameters
            if server_url is not None:
                config.server_url = server_url
            if client_id is not None:
                config.client_id = client_id
            if auth_token is not None:
                config.security.auth_token = auth_token
            if auto_reconnect is not None:
                config.auto_reconnect = auto_reconnect

        elif isinstance(config, str):
            # Treat string as server URL
            config = ClientConfig(server_url=config)

        elif isinstance(config, dict):
            # Create config from dict
            config = ClientConfig(**config)

        self.config = config

        # Generate client ID if needed
        if not self.config.client_id:
            self.config.client_id = f"client-{uuid.uuid4().hex[:8]}"

        self.client_id = self.config.client_id

        # Tool registry
        self._tools: Dict[str, Tool] = {}

        # Connection state
        self._websocket: Optional[WebSocketClientProtocol] = None
        self._connected = False
        self._receive_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._reconnect_attempts = 0

        # Event callbacks
        self._callbacks: Dict[str, list] = {
            "connected": [],
            "disconnected": [],
            "tool_executed": [],
            "error": []
        }

        # Setup logging
        logging.basicConfig(level=self.config.log_level.value)

    def register_tool(self, tool: Tool) -> None:
        """
        Register a tool with the client.

        Args:
            tool: Tool instance to register
        """
        # Use full_name (namespace.name) as key for v2.0
        self._tools[tool.full_name] = tool
        logger.debug(f"Registered tool: {tool.full_name}")

    def register_tools(self, *tools: Tool) -> None:
        """
        Register multiple tools at once.

        Args:
            *tools: Tool instances to register
        """
        for tool in tools:
            self.register_tool(tool)

    def unregister_tool(self, name: str) -> bool:
        """
        Unregister a tool.

        Args:
            name: Tool name to unregister

        Returns:
            True if tool was unregistered, False if not found
        """
        if name in self._tools:
            del self._tools[name]
            logger.debug(f"Unregistered tool: {name}")
            return True
        return False

    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    async def connect(self) -> None:
        """Connect to the Gateway server."""
        if self._connected:
            logger.warning("Already connected")
            return

        try:
            logger.info(f"Connecting to {self.config.server_url}...")

            # Connect WebSocket
            self._websocket = await websockets.connect(
                self.config.server_url,
                max_size=self.config.security.max_message_size,
                ping_interval=None,  # We handle our own heartbeat
                ping_timeout=None
            )

            # Send registration
            await self._register()

            self._connected = True
            self._reconnect_attempts = 0

            # Start background tasks
            self._receive_task = asyncio.create_task(self._receive_loop())
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            logger.info(f"✅ Connected as {self.client_id}")
            await self._emit("connected")

        except Exception as e:
            logger.error(f"Connection failed: {e}")
            await self._emit("error", e)

            # Auto-reconnect if enabled
            if self.config.auto_reconnect:
                await self._reconnect()
            else:
                raise

    async def disconnect(self) -> None:
        """Disconnect from the server."""
        if not self._connected:
            return

        logger.info("Disconnecting...")
        self._connected = False

        # Cancel background tasks
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
            try:
                await self._websocket.close()
            except Exception:
                pass
            self._websocket = None

        logger.info("Disconnected")
        await self._emit("disconnected")

    async def _register(self) -> None:
        """Send registration message to server."""
        # Prepare tools list with full metadata
        tools = []
        for full_name, tool in self._tools.items():
            # Send complete tool definition
            tool_def = {
                "name": full_name,  # Send full_name (e.g., "filesystem.read_file")
                "description": tool.description,
            }

            # Add parameters
            if hasattr(tool, 'parameters') and tool.parameters:
                tool_def["parameters"] = [p.to_dict() for p in tool.parameters]

            # Add optional metadata
            if hasattr(tool, 'permissions') and tool.permissions:
                tool_def["permissions"] = tool.permissions
            if hasattr(tool, 'tags') and tool.tags:
                tool_def["tags"] = tool.tags
            if hasattr(tool, 'timeout'):
                tool_def["timeout"] = tool.timeout

            tools.append(tool_def)

        # Create registration message
        registration = {
            "jsonrpc": "2.0",
            "method": "register",
            "params": {
                "client_id": self.client_id,
                "tools": tools,
                "version": "2.0.0"
            },
            "id": str(uuid.uuid4())
        }

        # Add authentication if configured
        if self.config.security.auth_token:
            registration["params"]["auth"] = {
                "token": self.config.security.auth_token
            }

        # Send registration
        await self._websocket.send(json.dumps(registration))

        # Wait for response
        response = await asyncio.wait_for(self._websocket.recv(), timeout=5.0)
        data = json.loads(response)

        if "error" in data:
            error = data["error"]
            raise Exception(f"Registration failed: {error.get('message', 'Unknown error')}")

        logger.debug(f"Registration successful: {data.get('result')}")

    async def _receive_loop(self) -> None:
        """Receive and process messages from server."""
        try:
            async for message in self._websocket:
                await self._handle_message(json.loads(message))
        except websockets.exceptions.ConnectionClosed:
            logger.info("Connection closed by server")
            self._connected = False
            await self._emit("disconnected")

            # Auto-reconnect if enabled
            if self.config.auto_reconnect:
                await self._reconnect()
        except Exception as e:
            logger.error(f"Receive error: {e}")
            self._connected = False
            await self._emit("error", e)

    async def _handle_message(self, data: Dict[str, Any]) -> None:
        """Handle message from server."""
        try:
            method = data.get("method")

            # Tool invocation
            if method in self._tools:
                await self._execute_tool(data)

            # Ping/heartbeat
            elif method == "ping":
                await self._websocket.send(json.dumps({
                    "jsonrpc": "2.0",
                    "result": "pong",
                    "id": data.get("id")
                }))

            # Unknown method
            else:
                logger.debug(f"Unknown method: {method}")

        except Exception as e:
            logger.error(f"Message handling error: {e}")

            # Send error response if request had ID
            if "id" in data:
                await self._websocket.send(json.dumps({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    },
                    "id": data["id"]
                }))

    async def _execute_tool(self, request: Dict[str, Any]) -> None:
        """Execute tool and send response."""
        method = request["method"]
        params = request.get("params", {})
        request_id = request.get("id")

        try:
            tool = self._tools[method]

            # Execute tool
            if asyncio.iscoroutinefunction(tool.execute):
                result = await tool.execute(**params)
            else:
                # Run sync tool in executor
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, tool.execute, **params)

            # Send success response
            response = {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }

            # Emit event
            await self._emit("tool_executed", method, params, result)

        except Exception as e:
            logger.error(f"Tool execution error: {e}")

            # Send error response
            response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": str(e)
                },
                "id": request_id
            }

        await self._websocket.send(json.dumps(response))

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeat to server."""
        interval = self.config.network.ping_interval

        while self._connected:
            try:
                await asyncio.sleep(interval)

                # Send heartbeat
                heartbeat = {
                    "jsonrpc": "2.0",
                    "method": "heartbeat",
                    "params": {"client_id": self.client_id},
                    "id": str(uuid.uuid4())
                }
                await self._websocket.send(json.dumps(heartbeat))

                logger.debug("Heartbeat sent")

            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                break

    async def _reconnect(self) -> None:
        """Attempt to reconnect to server."""
        if self._reconnect_attempts >= self.config.network.reconnect_max_attempts:
            logger.error("Max reconnection attempts reached")
            return

        self._reconnect_attempts += 1
        wait_time = self.config.network.reconnect_interval * self._reconnect_attempts

        logger.info(f"Reconnecting in {wait_time}s (attempt {self._reconnect_attempts})...")
        await asyncio.sleep(wait_time)

        try:
            await self.connect()
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            await self._reconnect()

    # Event system

    def on(self, event: str, callback: callable = None):
        """
        Register event callback.

        Can be used as a method or decorator:
            client.on("connected", callback)

            @client.on("connected")
            async def callback():
                pass

        Supported events: connected, disconnected, tool_executed, error
        """
        def decorator(func):
            if event in self._callbacks:
                self._callbacks[event].append(func)
            return func

        if callback is None:
            # Used as decorator
            return decorator
        else:
            # Used as method
            if event in self._callbacks:
                self._callbacks[event].append(callback)
            return callback

    async def _emit(self, event: str, *args, **kwargs) -> None:
        """Emit event to registered callbacks."""
        if event in self._callbacks:
            for callback in self._callbacks[event]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(*args, **kwargs)
                    else:
                        callback(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in {event} callback: {e}")

    # Properties

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected

    async def wait_closed(self) -> None:
        """Wait until connection is closed."""
        if self._receive_task:
            await self._receive_task


# Convenience functions

def create_client(
    server_url: str = "ws://localhost:8000",
    client_id: Optional[str] = None,
    auth_token: Optional[str] = None,
    **kwargs
) -> Client:
    """
    Create a client with common settings.

    Examples:
        client = create_client("ws://localhost:9000")
        client = create_client(auth_token="secret")
    """
    config = ClientConfig(server_url=server_url)

    if client_id:
        config.client_id = client_id
    if auth_token:
        config.security.auth_token = auth_token

    return Client(config, **kwargs)


async def connect_client(
    server_url: str = "ws://localhost:8000",
    tools: Optional[List[Tool]] = None,
    auth_token: Optional[str] = None,
    **kwargs
) -> Client:
    """
    Quick connect a client with tools.

    Examples:
        client = await connect_client("ws://localhost:8000")
        client = await connect_client(tools=[FileSystemTool()])
    """
    client = create_client(server_url, auth_token=auth_token, **kwargs)

    if tools:
        for tool in tools:
            client.register_tool(tool)

    await client.connect()
    return client