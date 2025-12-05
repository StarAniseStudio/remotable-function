"""
Pooled Client - Client with connection pooling support.

Provides efficient connection management for high-throughput scenarios.
"""

import asyncio
import json
import logging
import platform
import ssl
import uuid
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime

from ..core.types import ClientInfo, ToolContext, ConnectionState, ToolExecutionState
from ..core.protocol import RPCRequest, RPCResponse, RPCError, RPCErrorCode
from ..core.registry import ToolRegistry
from ..core.pool import ConnectionPool, PoolConfig, ConnectionPoolManager
from .tool import Tool
from .client import Client

logger = logging.getLogger(__name__)


class PooledClient(Client):
    """
    Enhanced client with connection pooling support.

    Uses connection pooling for better performance in high-throughput scenarios.
    Maintains multiple connections and reuses them efficiently.
    """

    def __init__(
        self,
        server_url: str,
        client_id: Optional[str] = None,
        version: str = "1.0.0",
        auto_reconnect: bool = True,
        reconnect_interval: int = 5,
        reconnect_max_attempts: int = 10,
        ssl_context: Optional[ssl.SSLContext] = None,
        verify_ssl: bool = True,
        auth_token: Optional[str] = None,
        auth_credentials: Optional[Dict[str, Any]] = None,
        pool_config: Optional[PoolConfig] = None,
    ):
        """
        Initialize pooled client.

        Args:
            server_url: Gateway server URL
            client_id: Client ID (auto-generated if not provided)
            version: Client version
            auto_reconnect: Enable auto-reconnect
            reconnect_interval: Reconnect interval in seconds
            reconnect_max_attempts: Max reconnect attempts
            ssl_context: Custom SSL context
            verify_ssl: Whether to verify SSL certificates
            auth_token: Authentication token
            auth_credentials: Authentication credentials
            pool_config: Connection pool configuration
        """
        super().__init__(
            server_url=server_url,
            client_id=client_id,
            version=version,
            auto_reconnect=auto_reconnect,
            reconnect_interval=reconnect_interval,
            reconnect_max_attempts=reconnect_max_attempts,
            ssl_context=ssl_context,
            verify_ssl=verify_ssl,
            auth_token=auth_token,
            auth_credentials=auth_credentials,
        )

        # Connection pool
        self.pool_config = pool_config or PoolConfig(
            min_size=2,
            max_size=10,
            max_idle_time=300.0,
            acquire_timeout=10.0,
        )
        self._pool: Optional[ConnectionPool] = None
        self._pool_manager = ConnectionPoolManager(self.pool_config)

    async def connect(self) -> None:
        """Connect to Gateway server with connection pool."""
        if self.is_connected:
            logger.warning("Already connected")
            return

        try:
            self._state = ConnectionState.CONNECTING

            # Create connection pool
            connect_kwargs = {
                "ssl": self._ssl_context,
                "ping_interval": None,
                "ping_timeout": None,
                "max_size": self.MAX_MESSAGE_SIZE,
            }

            self._pool = await self._pool_manager.get_pool(
                self.server_url, self.pool_config, **connect_kwargs
            )

            # Register with first connection
            async with self._pool.acquire() as conn:
                self._websocket = conn  # Temporarily set for registration
                await self._register()
                self._websocket = None  # Clear after registration

            self._state = ConnectionState.CONNECTED
            self._reconnect_attempts = 0

            # Start heartbeat task (receive task not needed with pool)
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            logger.info(f"Connected to server as {self.client_id} with connection pool")
            await self._emit("connected")

        except Exception as e:
            self._state = ConnectionState.DISCONNECTED
            if self._reconnect_attempts == 0:
                logger.error(f"Connection failed: {e}")
                await self._emit("error", e)

            if self.auto_reconnect:
                await self._reconnect()
            else:
                raise

    async def disconnect(self) -> None:
        """Disconnect from server and close pool."""
        if not self.is_connected:
            return

        logger.info("Disconnecting...")

        # Cancel heartbeat task
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        # Close connection pool
        if self._pool:
            await self._pool.stop()
            self._pool = None

        self._state = ConnectionState.DISCONNECTED
        logger.info("Disconnected")
        await self._emit("disconnected")

    async def _send_request(self, request: RPCRequest) -> RPCResponse:
        """
        Send RPC request using pooled connection.

        Args:
            request: RPC request to send

        Returns:
            RPC response from server

        Raises:
            Exception: If request fails
        """
        if not self._pool:
            raise RuntimeError("Not connected")

        # Acquire connection from pool
        async with self._pool.acquire() as conn:
            # Send request
            await conn.send(json.dumps(request.to_dict()))

            # Wait for response
            response_data = await conn.recv()
            response_dict = json.loads(response_data)

            # Parse response
            if "error" in response_dict:
                error = RPCError.from_dict(response_dict["error"])
                raise Exception(f"RPC Error: {error.message}")

            return RPCResponse.from_dict(response_dict)

    async def execute_tool(
        self,
        tool_name: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        """
        Execute a tool remotely.

        Args:
            tool_name: Tool name to execute
            params: Tool parameters
            timeout: Execution timeout

        Returns:
            Tool execution result
        """
        request = RPCRequest(
            method=f"tool.{tool_name}",
            params=params or {},
            id=str(uuid.uuid4()),
        )

        if timeout:
            response = await asyncio.wait_for(self._send_request(request), timeout=timeout)
        else:
            response = await self._send_request(request)

        return response.result

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeat using pooled connections."""
        interval = 30  # seconds

        while self.is_connected:
            try:
                await asyncio.sleep(interval)

                # Send heartbeat using pool
                async with self._pool.acquire() as conn:
                    request = RPCRequest(
                        method="heartbeat",
                        params={"timestamp": datetime.now().isoformat()},
                        id=str(uuid.uuid4()),
                    )
                    await conn.send(json.dumps(request.to_dict()))

                    # Wait for pong
                    response = await asyncio.wait_for(conn.recv(), timeout=5.0)
                    logger.debug("Heartbeat sent and acknowledged")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat failed: {e}")
                if self.auto_reconnect and not self._state == ConnectionState.RECONNECTING:
                    await self._reconnect()
                break

    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        if self._pool:
            stats = self._pool.get_stats()
            return {
                "available": stats.available_connections,
                "in_use": stats.in_use_connections,
                "total": stats.total_connections,
                "created": stats.connections_created,
                "closed": stats.connections_closed,
                "failures": stats.connection_failures,
                "acquires": stats.acquires,
                "releases": stats.releases,
            }
        return {}


class MultiGatewayClient:
    """
    Client that can connect to multiple gateways simultaneously.

    Uses connection pooling for efficient resource management across gateways.
    """

    def __init__(self, client_id: Optional[str] = None, pool_config: Optional[PoolConfig] = None):
        """
        Initialize multi-gateway client.

        Args:
            client_id: Client ID (shared across gateways)
            pool_config: Connection pool configuration
        """
        self.client_id = client_id or f"multi-client-{uuid.uuid4().hex[:8]}"
        self.pool_config = pool_config or PoolConfig()
        self._pool_manager = ConnectionPoolManager(self.pool_config)
        self._gateways: Dict[str, PooledClient] = {}

    async def add_gateway(
        self,
        gateway_id: str,
        server_url: str,
        auth_token: Optional[str] = None,
    ) -> PooledClient:
        """
        Add a gateway to connect to.

        Args:
            gateway_id: Unique gateway identifier
            server_url: Gateway URL
            auth_token: Authentication token

        Returns:
            Pooled client for the gateway
        """
        if gateway_id in self._gateways:
            raise ValueError(f"Gateway {gateway_id} already added")

        client = PooledClient(
            server_url=server_url,
            client_id=f"{self.client_id}-{gateway_id}",
            auth_token=auth_token,
            pool_config=self.pool_config,
        )

        await client.connect()
        self._gateways[gateway_id] = client

        logger.info(f"Added gateway: {gateway_id} at {server_url}")
        return client

    async def remove_gateway(self, gateway_id: str) -> None:
        """Remove a gateway."""
        if gateway_id in self._gateways:
            client = self._gateways.pop(gateway_id)
            await client.disconnect()
            logger.info(f"Removed gateway: {gateway_id}")

    def get_gateway(self, gateway_id: str) -> Optional[PooledClient]:
        """Get client for a specific gateway."""
        return self._gateways.get(gateway_id)

    def list_gateways(self) -> List[str]:
        """List all connected gateway IDs."""
        return list(self._gateways.keys())

    async def execute_on_gateway(
        self,
        gateway_id: str,
        tool_name: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Execute tool on a specific gateway.

        Args:
            gateway_id: Gateway to execute on
            tool_name: Tool name
            params: Tool parameters

        Returns:
            Execution result
        """
        client = self.get_gateway(gateway_id)
        if not client:
            raise ValueError(f"Gateway {gateway_id} not found")

        return await client.execute_tool(tool_name, params)

    async def execute_on_all(
        self,
        tool_name: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute tool on all gateways in parallel.

        Args:
            tool_name: Tool name
            params: Tool parameters

        Returns:
            Dictionary of gateway_id -> result
        """
        tasks = {
            gateway_id: client.execute_tool(tool_name, params)
            for gateway_id, client in self._gateways.items()
        }

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        return {gateway_id: result for gateway_id, result in zip(tasks.keys(), results)}

    async def disconnect_all(self) -> None:
        """Disconnect from all gateways."""
        await asyncio.gather(
            *[client.disconnect() for client in self._gateways.values()], return_exceptions=True
        )
        self._gateways.clear()

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all gateways."""
        return {
            gateway_id: client.get_pool_stats() for gateway_id, client in self._gateways.items()
        }
