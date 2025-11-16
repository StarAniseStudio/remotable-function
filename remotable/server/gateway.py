"""
RPC Gateway - Server-side gateway for remote tool invocation.

The Gateway is the bridge between server-side AI agents and client-side tools.
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Optional, Callable, Any, List
from datetime import datetime
import websockets
from websockets.server import WebSocketServerProtocol, serve

from ..core.types import ClientInfo, ToolDefinition
from ..core.protocol import RPCRequest, RPCResponse, RPCError, RPCErrorCode
from ..core.registry import ToolRegistry
from .manager import ConnectionManager

logger = logging.getLogger(__name__)


class Gateway:
    """
    RPC Gateway for remote tool invocation.

    The Gateway manages:
    1. WebSocket server lifecycle
    2. Client connections (via ConnectionManager)
    3. Tool registry (tracks client tools)
    4. Remote tool invocation (call client tools from server)
    5. Event notifications

    Usage:
        import remotable
        remotable.configure(role="server")

        gateway = remotable.Gateway(host="0.0.0.0", port=8000)

        @gateway.on_client_connected
        async def on_connected(client_id, client_info):
            result = await gateway.call_tool(
                client_id=client_id,
                tool="filesystem.read_file",
                args={"path": "/tmp/test.txt"}
            )
            print(result)

        await gateway.start()
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8000,
        heartbeat_interval: int = 30,
        heartbeat_timeout: int = 60,
        default_timeout: int = 30
    ):
        """
        Initialize Gateway.

        Args:
            host: Server host
            port: Server port
            heartbeat_interval: Heartbeat interval in seconds
            heartbeat_timeout: Heartbeat timeout in seconds
            default_timeout: Default tool invocation timeout in seconds
        """
        self.host = host
        self.port = port
        self.default_timeout = default_timeout

        # Core components
        self.registry = ToolRegistry()
        self.manager = ConnectionManager(
            heartbeat_interval=heartbeat_interval,
            heartbeat_timeout=heartbeat_timeout
        )

        # WebSocket server
        self._server: Optional[websockets.WebSocketServer] = None
        self._running = False

        # Event callbacks
        self._callbacks: Dict[str, List[Callable]] = {
            "client_connected": [],
            "client_disconnected": [],
            "tool_registered": [],
            "tool_unregistered": [],
        }

        # Setup connection manager callbacks
        self.manager.on("connected", self._on_client_connected)
        self.manager.on("disconnected", self._on_client_disconnected)

    def on_client_connected(self, callback: Callable) -> Callable:
        """
        Decorator: Register callback for client connection.

        Example:
            @gateway.on_client_connected
            async def on_connected(client_id: str, client_info: ClientInfo):
                print(f"Client {client_id} connected")
        """
        self._callbacks["client_connected"].append(callback)
        return callback

    def on_client_disconnected(self, callback: Callable) -> Callable:
        """
        Decorator: Register callback for client disconnection.

        Example:
            @gateway.on_client_disconnected
            async def on_disconnected(client_id: str):
                print(f"Client {client_id} disconnected")
        """
        self._callbacks["client_disconnected"].append(callback)
        return callback

    def on_tool_registered(self, callback: Callable) -> Callable:
        """Decorator: Register callback for tool registration."""
        self._callbacks["tool_registered"].append(callback)
        return callback

    def on_tool_unregistered(self, callback: Callable) -> Callable:
        """Decorator: Register callback for tool unregistration."""
        self._callbacks["tool_unregistered"].append(callback)
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

    async def _on_client_connected(self, client_id: str, client_info: ClientInfo) -> None:
        """Internal handler for client connection."""
        await self._emit("client_connected", client_id, client_info)

    async def _on_client_disconnected(self, client_id: str) -> None:
        """Internal handler for client disconnection."""
        # Unregister all tools from this client
        unregistered = self.registry.unregister_client(client_id)
        for tool in unregistered:
            await self._emit("tool_unregistered", client_id, tool.full_name)

        await self._emit("client_disconnected", client_id)

    async def start(self) -> None:
        """
        Start the Gateway server.

        This starts:
        1. WebSocket server
        2. Heartbeat monitoring
        3. Event loop for handling messages
        """
        if self._running:
            logger.warning("Gateway already running")
            return

        # Start WebSocket server
        # Disable built-in ping/pong to avoid conflicts with our heartbeat mechanism
        self._server = await serve(
            self._handle_client,
            self.host,
            self.port,
            ping_interval=None,  # Disable built-in ping (we use our own heartbeat)
            ping_timeout=None    # Disable ping timeout
        )

        # Start heartbeat
        await self.manager.start_heartbeat()

        self._running = True
        logger.info(f"Gateway started on ws://{self.host}:{self.port}")

    async def stop(self) -> None:
        """Stop the Gateway server."""
        if not self._running:
            return

        self._running = False

        # Close all client connections
        await self.manager.close_all()

        # Stop WebSocket server
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        logger.info("Gateway stopped")

    async def _handle_client(self, websocket: WebSocketServerProtocol, path: str) -> None:
        """
        Handle a single client connection.

        This is the WebSocket connection handler that:
        1. Receives client registration
        2. Registers tools
        3. Handles tool invocation responses
        4. Processes heartbeat
        """
        client_id: Optional[str] = None

        try:
            # Wait for client registration
            message = await asyncio.wait_for(websocket.recv(), timeout=10)
            data = json.loads(message)

            if data.get("method") != "register":
                await websocket.send(RPCError(
                    code=RPCErrorCode.INVALID_REQUEST,
                    message="First message must be registration",
                    request_id=data.get("id")
                ).to_json())
                return

            # Parse client info
            params = data.get("params", {})
            client_id = params.get("client_id")
            client_info = ClientInfo(
                client_id=client_id,
                name=params.get("name", client_id),  # Use client_id as default name
                version=params.get("version", "unknown"),
                platform=params.get("platform", "unknown"),
                capabilities=params.get("capabilities", []),
                metadata=params.get("metadata", {})
            )

            # Register client
            connection = await self.manager.register(client_id, websocket, client_info)

            # Register tools
            tools = params.get("tools", [])
            for tool_data in tools:
                tool = ToolDefinition.from_dict(tool_data)
                self.registry.register(tool, client_id=client_id)
                await self._emit("tool_registered", client_id, tool.full_name)

            # Send registration success
            await connection.send({
                "jsonrpc": "2.0",
                "id": data.get("id"),
                "result": {
                    "status": "registered",
                    "client_id": client_id,
                    "server_time": datetime.now().isoformat()
                }
            })

            logger.info(f"Client {client_id} registered with {len(tools)} tools")

            # Message loop
            async for message in websocket:
                await self._handle_message(client_id, message)

        except asyncio.TimeoutError:
            logger.error("Client registration timeout")
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id} connection closed")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {e}")
        finally:
            if client_id:
                await self.manager.unregister(client_id)

    async def _handle_message(self, client_id: str, message: str) -> None:
        """Handle incoming message from client."""
        try:
            data = json.loads(message)
            method = data.get("method")

            if method == "heartbeat":
                # Update heartbeat
                connection = self.manager.get(client_id)
                if connection:
                    connection.update_heartbeat()

            elif method == "response" or "result" in data or "error" in data:
                # This is a response to our tool invocation
                request_id = data.get("id")
                connection = self.manager.get(client_id)

                if connection and request_id in connection.pending_requests:
                    future = connection.pending_requests.pop(request_id)
                    if not future.done():
                        future.set_result(data)

            else:
                logger.warning(f"Unknown method from {client_id}: {method}")

        except Exception as e:
            logger.error(f"Error handling message from {client_id}: {e}")

    async def call_tool(
        self,
        client_id: str,
        tool: str,
        args: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> Any:
        """
        Call a tool on a remote client.

        Args:
            client_id: Target client ID
            tool: Tool full name (namespace.name)
            args: Tool arguments
            timeout: Timeout in seconds (default: self.default_timeout)

        Returns:
            Tool execution result

        Raises:
            ValueError: If client not connected or tool not found
            TimeoutError: If tool invocation times out
            Exception: If tool execution fails

        Example:
            result = await gateway.call_tool(
                client_id="client-1",
                tool="filesystem.read_file",
                args={"path": "/tmp/test.txt"}
            )
        """
        # Check client connection
        connection = self.manager.get(client_id)
        if not connection:
            raise ValueError(f"Client not connected: {client_id}")

        # Check tool exists
        tool_def = self.registry.get(tool)
        if not tool_def:
            raise ValueError(f"Tool not found: {tool}")

        # Generate request
        request_id = str(uuid.uuid4())
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tool.execute",
            "params": {
                "tool": tool,
                "args": args or {}
            }
        }

        # Create future for response
        future: asyncio.Future = asyncio.Future()
        connection.pending_requests[request_id] = future

        # Send request
        try:
            await connection.send(request)

            # Wait for response
            timeout_value = timeout or tool_def.timeout or self.default_timeout
            response = await asyncio.wait_for(future, timeout=timeout_value)

            # Check for errors
            if "error" in response:
                error = response["error"]
                raise Exception(f"Tool execution error: {error.get('message', 'Unknown error')}")

            return response.get("result")

        except asyncio.TimeoutError:
            # Clean up pending request
            connection.pending_requests.pop(request_id, None)
            raise TimeoutError(f"Tool invocation timeout after {timeout_value}s")

        except Exception as e:
            # Clean up pending request
            connection.pending_requests.pop(request_id, None)
            raise

    def list_clients(self) -> Dict[str, ClientInfo]:
        """List all connected clients."""
        return self.manager.list_clients()

    def list_tools(self, client_id: Optional[str] = None) -> List[ToolDefinition]:
        """
        List available tools.

        Args:
            client_id: If specified, list tools from specific client only

        Returns:
            List of tool definitions
        """
        if client_id:
            return self.registry.list_by_client(client_id)
        return self.registry.list_all()

    def get_tool(self, tool_name: str) -> Optional[ToolDefinition]:
        """Get tool definition by full name."""
        return self.registry.get(tool_name)

    def is_running(self) -> bool:
        """Check if gateway is running."""
        return self._running

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"Gateway(host={self.host}, port={self.port}, "
            f"clients={len(self.manager)}, tools={self.registry.count()})"
        )
