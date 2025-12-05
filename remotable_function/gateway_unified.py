"""
Remotable Gateway - Unified implementation for v2.0

A clean, unified RPC gateway server that combines the best of both implementations.
"""

import asyncio
import json
import logging
import uuid
from typing import Optional, Dict, Any, Union
from datetime import datetime

import websockets
from websockets.server import WebSocketServerProtocol

from .config import GatewayConfig
from .core.registry import ToolRegistry
from .core.protocol import RPCRequest, RPCResponse, RPCError, RPCErrorCode
from .core.cache import ResponseCache
from .core.compression import MessageCompressor
from .server.manager import ConnectionManager

logger = logging.getLogger(__name__)


class Gateway:
    """
    Unified RPC Gateway server for Remotable v2.0.

    Supports both configuration object and direct parameters for backward compatibility.

    Examples:
        # Method 1: Using configuration object (recommended)
        config = GatewayConfig.production()
        gateway = Gateway(config)

        # Method 2: Direct parameters (backward compatible)
        gateway = Gateway(port=8000, auth_token="secret")

        # Method 3: Quick start with defaults
        gateway = Gateway()
    """

    def __init__(
        self,
        config: Optional[Union[GatewayConfig, Dict]] = None,
        # Backward compatibility parameters
        host: Optional[str] = None,
        port: Optional[int] = None,
        auth_token: Optional[str] = None,
        require_auth: Optional[bool] = None,
        enable_cache: Optional[bool] = None,
        enable_compression: Optional[bool] = None,
        **kwargs,
    ):
        """
        Initialize Gateway with flexible configuration.

        Args:
            config: GatewayConfig object or dict (recommended)
            host: Host to bind to (backward compat)
            port: Port to bind to (backward compat)
            auth_token: Authentication token (backward compat)
            require_auth: Require authentication (backward compat)
            enable_cache: Enable response caching (backward compat)
            enable_compression: Enable message compression (backward compat)
            **kwargs: Additional backward compatibility parameters
        """
        # Handle configuration
        if config is None:
            # Create config from individual parameters
            config = GatewayConfig()

            # Apply individual parameters if provided
            if host is not None:
                config.network.host = host
            if port is not None:
                config.network.port = port
            if auth_token is not None:
                config.security.auth_token = auth_token
                config.security.require_auth = True
            if require_auth is not None:
                config.security.require_auth = require_auth
            if enable_cache is not None:
                config.performance.enable_cache = enable_cache
            if enable_compression is not None:
                config.performance.enable_compression = enable_compression

        elif isinstance(config, dict):
            # Create config from dict
            config = GatewayConfig(**config)

        self.config = config

        # Extract commonly used settings
        self.host = self.config.network.host
        self.port = self.config.network.port

        # Core components
        self.manager = ConnectionManager()
        self.registry = ToolRegistry()

        # Optional components based on config
        self.cache = None
        if self.config.performance.enable_cache:
            self.cache = ResponseCache(
                max_size=self.config.performance.cache_max_size,
                default_ttl=self.config.performance.cache_ttl,
            )

        self.compressor = None
        if self.config.performance.enable_compression:
            self.compressor = MessageCompressor(
                threshold=self.config.performance.compression_threshold
            )

        # Server state
        self._server = None
        self._running = False

        # Event callbacks (for backward compatibility)
        self._callbacks: Dict[str, list] = {
            "client_connected": [],
            "client_disconnected": [],
            "tool_called": [],
            "error": [],
        }

        # Setup logging
        logging.basicConfig(level=self.config.log_level.value)

    async def start(self) -> None:
        """Start the Gateway server."""
        if self._running:
            logger.warning("Gateway already running")
            return

        try:
            # Display startup info
            auth_status = "enabled" if self.config.security.require_auth else "disabled"
            logger.info(f"Starting Gateway v2.0 on {self.host}:{self.port}")
            logger.info(
                f"Configuration: auth={auth_status}, cache={self.config.performance.enable_cache}, compression={self.config.performance.enable_compression}"
            )

            # Security warning
            if not self.config.security.require_auth:
                logger.warning("⚠️  Authentication is disabled! Enable it for production use.")

            # Start WebSocket server
            self._server = await websockets.serve(
                self._handle_client,
                self.host,
                self.port,
                max_size=self.config.security.max_message_size,
                ping_interval=self.config.network.ping_interval,
                ping_timeout=self.config.network.ping_timeout,
            )

            self._running = True
            logger.info(f"✅ Gateway ready at ws://{self.host}:{self.port}")

            # Emit start event
            await self._emit("started")

        except Exception as e:
            logger.error(f"Failed to start Gateway: {e}")
            raise

    async def stop(self) -> None:
        """Stop the Gateway server gracefully."""
        if not self._running:
            return

        logger.info("Stopping Gateway...")
        self._running = False

        # Close all client connections
        await self.manager.close_all()

        # Stop server
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        # Clear cache if enabled
        if self.cache:
            await self.cache.clear()

        logger.info("Gateway stopped")
        await self._emit("stopped")

    async def _handle_client(self, websocket: WebSocketServerProtocol, path: str = None):
        """Handle incoming client connection."""
        # Handle both old and new websockets API
        if path is None:
            path = websocket.path if hasattr(websocket, "path") else "/"

        client_id = None

        try:
            # Wait for client registration
            message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            data = json.loads(message)

            # Validate registration message
            if data.get("method") != "register":
                await self._send_error(websocket, "Invalid registration", data.get("id"))
                return

            # Check authentication
            if self.config.security.require_auth:
                auth = data.get("params", {}).get("auth", {})
                token = auth.get("token")

                if token != self.config.security.auth_token:
                    await self._send_error(
                        websocket, "Authentication failed", data.get("id"), code=-32001
                    )
                    return

            # Extract client info
            params = data.get("params", {})
            client_id = params.get("client_id", f"client-{uuid.uuid4().hex[:8]}")
            tools = params.get("tools", [])

            # Create client info from params
            from .core.types import ClientInfo

            client_info = ClientInfo(
                client_id=client_id,
                name=params.get("name", "unknown"),
                version=params.get("version", "1.0.0"),
                platform=params.get("platform", "unknown"),
                capabilities=params.get("capabilities", []),
                metadata=params,
            )

            # Register connection
            connection = await self.manager.register(client_id, websocket, client_info)

            # Register tools
            from .core.types import ToolDefinition, ParameterSchema

            for tool_data in tools:
                # Convert tool data to ToolDefinition
                if isinstance(tool_data, dict):
                    # Parse tool name (might include namespace like "filesystem.read_file")
                    tool_name = tool_data.get("name", "")

                    # Create tool definition with client_id as namespace
                    tool_def = ToolDefinition(
                        name=tool_name,  # Keep full name for now
                        description=tool_data.get("description", ""),
                        namespace=client_id,
                        parameters=[
                            ParameterSchema.from_dict(p) for p in tool_data.get("parameters", [])
                        ],
                        permissions=tool_data.get("permissions", []),
                        tags=tool_data.get("tags", []),
                        timeout=tool_data.get("timeout", 30),
                    )
                else:
                    # If it's a string, create a basic tool definition
                    tool_def = ToolDefinition(
                        name=str(tool_data), description="", namespace=client_id
                    )

                # Register with client_id for tracking
                self.registry.register(tool_def, client_id=client_id)

            # Send success response
            await websocket.send(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "result": {
                            "status": "registered",
                            "client_id": client_id,
                            "timestamp": datetime.now().isoformat(),
                            "version": "2.0.0",
                        },
                        "id": data.get("id"),
                    }
                )
            )

            logger.info(f"Client {client_id} connected with {len(tools)} tools")
            await self._emit("client_connected", client_id, tools)

            # Handle messages
            async for message in websocket:
                await self._handle_message(client_id, json.loads(message))

        except asyncio.TimeoutError:
            logger.error("Client registration timeout")
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_id or 'unknown'} disconnected")
        except Exception as e:
            logger.error(f"Error handling client {client_id or 'unknown'}: {e}")
        finally:
            # Cleanup
            if client_id:
                self.registry.unregister_client(client_id)
                await self.manager.unregister(client_id)
                await self._emit("client_disconnected", client_id)

    async def _handle_message(self, client_id: str, data: Dict[str, Any]) -> None:
        """Handle incoming message from client."""
        method = data.get("method")

        if method == "heartbeat":
            # Update heartbeat
            connection = self.manager.get(client_id)
            if connection:
                connection.update_heartbeat()

        elif method == "call_tool":
            # Client calling server tool - Execute local tool
            await self._handle_client_tool_call(client_id, data)

        elif method == "response" or "result" in data or "error" in data:
            # Response to our tool invocation
            request_id = data.get("id")
            connection = self.manager.get(client_id)

            if connection and request_id in connection.pending_requests:
                future = connection.pending_requests.pop(request_id)
                if not future.done():
                    future.set_result(data)

    async def _handle_client_tool_call(self, client_id: str, data: Dict[str, Any]) -> None:
        """Handle tool call from client to server."""
        request_id = data.get("id")
        params = data.get("params", {})
        tool_name = params.get("tool", "")
        args = params.get("args", {})

        connection = self.manager.get(client_id)
        if not connection:
            return

        try:
            # Look for server-side tool
            server_tools = getattr(self, "_server_tools", {})
            tool_instance = server_tools.get(tool_name)

            if not tool_instance:
                # Send error response
                await connection.websocket.send(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {
                                "code": RPCErrorCode.TOOL_NOT_FOUND,
                                "message": f"Tool '{tool_name}' not found",
                            },
                        }
                    )
                )
                return

            # Execute the tool
            from .core.types import ToolContext

            context = ToolContext(
                client_id=client_id, request_id=request_id, timestamp=datetime.now(), metadata={}
            )

            result = await tool_instance.execute(context, **args)

            # Send success response
            await connection.websocket.send(
                json.dumps({"jsonrpc": "2.0", "id": request_id, "result": result})
            )

        except Exception as e:
            # Send error response
            logger.error(f"Tool execution error: {e}")
            await connection.websocket.send(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": RPCErrorCode.TOOL_EXECUTION_FAILED, "message": str(e)},
                    }
                )
            )

    async def call_tool(
        self,
        client_id: str,
        tool: str,
        args: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> Any:
        """
        Call a tool on a remote client.

        Args:
            client_id: Target client ID
            tool: Tool name
            args: Tool arguments
            timeout: Timeout in seconds (default: 30)

        Returns:
            Tool execution result

        Raises:
            ValueError: If client or tool not found
            TimeoutError: If execution times out
            Exception: If tool execution fails
        """
        # Default timeout
        if timeout is None:
            timeout = 30

        # Get connection
        connection = self.manager.get(client_id)
        if not connection:
            raise ValueError(f"Client {client_id} not connected")

        # Check tool exists
        tool_def = self.registry.get(f"{client_id}.{tool}")
        if not tool_def:
            raise ValueError(f"Tool {tool} not found on client {client_id}")

        # Check cache
        cache_key = None
        if self.cache and "cacheable" in tool_def.tags:
            import hashlib

            cache_key = hashlib.md5(
                f"{client_id}:{tool}:{json.dumps(args or {}, sort_keys=True)}".encode()
            ).hexdigest()

            cached = await self.cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for {tool}")
                return cached

        # Create request
        request = RPCRequest(
            method="tool.execute", params={"tool": tool, "args": args or {}}, id=str(uuid.uuid4())
        )

        # Send request
        future = asyncio.Future()
        connection.pending_requests[request.id] = future

        message = request.to_dict()

        # Compress if enabled
        if self.compressor:
            message = await self.compressor.compress_message(message)

        await connection.send(message)

        # Wait for response
        try:
            response = await asyncio.wait_for(future, timeout=timeout)

            if "error" in response:
                error = response["error"]
                raise Exception(f"Tool execution failed: {error.get('message', 'Unknown error')}")

            result = response.get("result")

            # Cache result
            if self.cache and cache_key:
                await self.cache.set(cache_key, result)

            # Emit event
            await self._emit("tool_called", client_id, tool, args, result)

            return result

        except asyncio.TimeoutError:
            connection.pending_requests.pop(request.id, None)
            raise TimeoutError(f"Tool {tool} execution timed out after {timeout}s")

    # Convenience methods

    def list_clients(self) -> Dict[str, Any]:
        """List all connected clients with their info."""
        return {
            client_id: {
                "tools": [t.name for t in self.registry.list_by_client(client_id)],
                "connected": True,
            }
            for client_id in self.manager.list_clients()
        }

    def list_tools(self, client_id: Optional[str] = None) -> Dict[str, list]:
        """List available tools, optionally filtered by client."""
        if client_id:
            return {
                client_id: [
                    {"name": t.name, "description": t.description}
                    for t in self.registry.list_by_client(client_id)
                ]
            }

        tools_by_client = {}
        for tool in self.registry.list_all():
            client = tool.namespace
            if client not in tools_by_client:
                tools_by_client[client] = []
            tools_by_client[client].append({"name": tool.name, "description": tool.description})
        return tools_by_client

    def is_running(self) -> bool:
        """Check if gateway is running."""
        return self._running

    # Event system (for backward compatibility)

    def on(self, event: str, callback: callable = None):
        """
        Register event callback.

        Can be used as a method or decorator:
            gateway.on("client_connected", callback)

            @gateway.on("client_connected")
            def callback(...):
                pass
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

    # Helper methods

    async def _send_error(
        self,
        websocket: WebSocketServerProtocol,
        message: str,
        request_id: Any = None,
        code: int = -32603,
    ) -> None:
        """Send error response to client."""
        await websocket.send(
            json.dumps(
                {"jsonrpc": "2.0", "error": {"code": code, "message": message}, "id": request_id}
            )
        )

    async def wait_closed(self) -> None:
        """Wait until gateway is closed."""
        if self._server:
            await self._server.wait_closed()


# Convenience functions for quick setup


def create_gateway(
    port: int = 8000, auth_token: Optional[str] = None, production: bool = False, **kwargs
) -> Gateway:
    """
    Create a gateway with common settings.

    Examples:
        gateway = create_gateway(port=9000)
        gateway = create_gateway(auth_token="secret", production=True)
    """
    if production:
        config = GatewayConfig.production()
    else:
        config = GatewayConfig()

    config.network.port = port
    if auth_token:
        config.security.auth_token = auth_token
        config.security.require_auth = True

    return Gateway(config, **kwargs)


async def start_server(
    port: int = 8000, auth_token: Optional[str] = None, production: bool = False, **kwargs
) -> Gateway:
    """
    Quick start a server.

    Examples:
        server = await start_server(port=8000)
        server = await start_server(port=9000, auth_token="secret")
    """
    gateway = create_gateway(port, auth_token, production, **kwargs)
    await gateway.start()
    return gateway
