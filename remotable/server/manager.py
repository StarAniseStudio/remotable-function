"""
Connection Manager - Manages WebSocket connections and heartbeat.
"""

import asyncio
import json
import logging
from typing import Dict, Optional, Set, Callable, Any
from datetime import datetime
import websockets
from websockets.server import WebSocketServerProtocol

from ..core.types import ClientInfo, ConnectionState
from ..core.protocol import RPCRequest, RPCResponse, RPCError, RPCErrorCode

logger = logging.getLogger(__name__)


class ClientConnection:
    """Represents a single client connection."""

    def __init__(
        self,
        client_id: str,
        websocket: WebSocketServerProtocol,
        client_info: ClientInfo
    ):
        self.client_id = client_id
        self.websocket = websocket
        self.client_info = client_info
        self.state = ConnectionState.CONNECTED
        self.connected_at = datetime.now()
        self.last_heartbeat = datetime.now()
        self.pending_requests: Dict[str, asyncio.Future] = {}

    async def send(self, message: dict) -> None:
        """Send message to client."""
        try:
            await self.websocket.send(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send message to {self.client_id}: {e}")
            self.state = ConnectionState.DISCONNECTED
            raise

    async def close(self) -> None:
        """Close connection."""
        self.state = ConnectionState.DISCONNECTED
        await self.websocket.close()
        logger.info(f"Connection closed: {self.client_id}")

    def update_heartbeat(self) -> None:
        """Update last heartbeat time."""
        self.last_heartbeat = datetime.now()

    def is_alive(self, timeout: int = 60) -> bool:
        """Check if connection is alive (based on heartbeat)."""
        if self.state != ConnectionState.CONNECTED:
            return False
        elapsed = (datetime.now() - self.last_heartbeat).total_seconds()
        return elapsed < timeout


class ConnectionManager:
    """
    Manages all client connections.

    Features:
    - WebSocket connection lifecycle
    - Heartbeat monitoring
    - Client registration/unregistration
    - Message routing
    """

    def __init__(
        self,
        heartbeat_interval: int = 30,
        heartbeat_timeout: int = 60
    ):
        self.connections: Dict[str, ClientConnection] = {}
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._callbacks: Dict[str, Set[Callable]] = {
            "connected": set(),
            "disconnected": set(),
            "error": set(),
        }

    def on(self, event: str, callback: Callable) -> None:
        """Register event callback."""
        if event in self._callbacks:
            self._callbacks[event].add(callback)
        else:
            logger.warning(f"Unknown event: {event}")

    async def _emit(self, event: str, *args, **kwargs) -> None:
        """Emit event to all callbacks."""
        if event in self._callbacks:
            for callback in self._callbacks[event]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(*args, **kwargs)
                    else:
                        callback(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in {event} callback: {e}")

    async def register(
        self,
        client_id: str,
        websocket: WebSocketServerProtocol,
        client_info: ClientInfo
    ) -> ClientConnection:
        """Register a new client connection."""
        # Close existing connection if any
        if client_id in self.connections:
            logger.warning(f"Client {client_id} already connected, closing old connection")
            await self.unregister(client_id)

        # Create new connection
        connection = ClientConnection(client_id, websocket, client_info)
        self.connections[client_id] = connection

        await self._emit("connected", client_id, client_info)

        return connection

    async def unregister(self, client_id: str) -> bool:
        """Unregister a client connection."""
        connection = self.connections.pop(client_id, None)
        if not connection:
            return False

        # Cancel pending requests
        for future in connection.pending_requests.values():
            if not future.done():
                future.cancel()

        # Close connection
        try:
            await connection.close()
        except Exception as e:
            logger.error(f"Error closing connection {client_id}: {e}")

        logger.info(f"Client unregistered: {client_id}")
        await self._emit("disconnected", client_id)

        return True

    def get(self, client_id: str) -> Optional[ClientConnection]:
        """Get client connection by ID."""
        return self.connections.get(client_id)

    def list_clients(self) -> Dict[str, ClientInfo]:
        """List all connected clients."""
        return {
            client_id: conn.client_info
            for client_id, conn in self.connections.items()
            if conn.state == ConnectionState.CONNECTED
        }

    def is_connected(self, client_id: str) -> bool:
        """Check if client is connected."""
        connection = self.get(client_id)
        return connection is not None and connection.state == ConnectionState.CONNECTED

    async def send_to(self, client_id: str, message: dict) -> None:
        """Send message to specific client."""
        connection = self.get(client_id)
        if not connection:
            raise ValueError(f"Client not connected: {client_id}")
        await connection.send(message)

    async def broadcast(self, message: dict, exclude: Optional[Set[str]] = None) -> None:
        """Broadcast message to all clients."""
        exclude = exclude or set()
        tasks = []

        for client_id, connection in self.connections.items():
            if client_id not in exclude and connection.state == ConnectionState.CONNECTED:
                tasks.append(connection.send(message))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def start_heartbeat(self) -> None:
        """Start heartbeat monitoring."""
        if self._heartbeat_task is not None:
            logger.warning("Heartbeat already running")
            return

        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info(f"Heartbeat started (interval={self.heartbeat_interval}s, timeout={self.heartbeat_timeout}s)")

    async def stop_heartbeat(self) -> None:
        """Stop heartbeat monitoring."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
            logger.info("Heartbeat stopped")

    async def _heartbeat_loop(self) -> None:
        """Heartbeat monitoring loop."""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)

                # Check all connections
                dead_clients = []
                for client_id, connection in self.connections.items():
                    if not connection.is_alive(self.heartbeat_timeout):
                        dead_clients.append(client_id)
                        logger.warning(f"Client {client_id} heartbeat timeout")

                # Remove dead connections
                for client_id in dead_clients:
                    await self.unregister(client_id)
                    await self._emit("error", client_id, "Heartbeat timeout")

                # Send heartbeat to alive connections
                for connection in self.connections.values():
                    if connection.state == ConnectionState.CONNECTED:
                        try:
                            await connection.send({
                                "jsonrpc": "2.0",
                                "method": "heartbeat",
                                "params": {}
                            })
                        except Exception as e:
                            logger.error(f"Failed to send heartbeat to {connection.client_id}: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")

    async def close_all(self) -> None:
        """Close all connections."""
        client_ids = list(self.connections.keys())
        for client_id in client_ids:
            await self.unregister(client_id)

        await self.stop_heartbeat()
        logger.info("All connections closed")

    def __len__(self) -> int:
        """Get number of connected clients."""
        return len(self.connections)

    def __repr__(self) -> str:
        """String representation."""
        return f"ConnectionManager(clients={len(self.connections)})"
