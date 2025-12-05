"""
Connection pooling for Remotable.

Provides efficient connection reuse and management.
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, List, Set
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
from collections import deque
import weakref
import websockets
from websockets.client import WebSocketClientProtocol

logger = logging.getLogger(__name__)


@dataclass
class PoolConfig:
    """Connection pool configuration."""

    min_size: int = 2  # Minimum connections to maintain
    max_size: int = 10  # Maximum connections allowed
    max_idle_time: float = 300.0  # Max idle time before closing (5 min)
    acquire_timeout: float = 10.0  # Timeout for acquiring connection
    connection_timeout: float = 10.0  # Timeout for creating connection
    health_check_interval: float = 30.0  # Health check interval
    max_retries: int = 3  # Max retries for failed connections
    retry_delay: float = 1.0  # Delay between retries


@dataclass
class PooledConnection:
    """Wrapper for pooled connection."""

    connection: WebSocketClientProtocol
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    use_count: int = 0
    pool: Optional["ConnectionPool"] = None
    in_use: bool = False

    def is_expired(self, max_idle_time: float) -> bool:
        """Check if connection has expired."""
        return time.time() - self.last_used > max_idle_time

    def is_healthy(self) -> bool:
        """Check if connection is healthy."""
        return self.connection is not None and not self.connection.closed and self.connection.open

    async def close(self) -> None:
        """Close the connection."""
        if self.connection and not self.connection.closed:
            await self.connection.close()


class ConnectionPool:
    """
    Connection pool for WebSocket connections.

    Example:
        pool = ConnectionPool(uri="ws://localhost:8080")
        async with pool.acquire() as conn:
            await conn.send(message)
            response = await conn.recv()
    """

    def __init__(self, uri: str, config: Optional[PoolConfig] = None, **connect_kwargs):
        """
        Initialize connection pool.

        Args:
            uri: WebSocket URI to connect to
            config: Pool configuration
            **connect_kwargs: Additional arguments for websockets.connect()
        """
        self.uri = uri
        self.config = config or PoolConfig()
        self.connect_kwargs = connect_kwargs

        # Pool state
        self._available: deque[PooledConnection] = deque()
        self._in_use: Set[PooledConnection] = set()
        self._all_connections: weakref.WeakSet[PooledConnection] = weakref.WeakSet()

        # Synchronization
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(self.config.max_size)
        self._waiters: deque[asyncio.Future] = deque()

        # Background tasks
        self._health_check_task: Optional[asyncio.Task] = None
        self._closing = False

        # Statistics
        self._stats = PoolStats()

    async def start(self) -> None:
        """Start the connection pool."""
        if self._health_check_task:
            return

        # Create minimum connections
        for _ in range(self.config.min_size):
            try:
                conn = await self._create_connection()
                self._available.append(conn)
            except Exception as e:
                logger.warning(f"Failed to create initial connection: {e}")

        # Start health check task
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info(f"Connection pool started with {len(self._available)} connections")

    async def stop(self) -> None:
        """Stop the connection pool."""
        self._closing = True

        # Cancel health check
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        # Close all connections
        async with self._lock:
            all_conns = list(self._available) + list(self._in_use)
            for conn in all_conns:
                await conn.close()

            self._available.clear()
            self._in_use.clear()

        # Cancel waiters
        for waiter in self._waiters:
            if not waiter.done():
                waiter.cancel()

        logger.info("Connection pool stopped")

    async def _create_connection(self) -> PooledConnection:
        """Create a new connection."""
        for attempt in range(self.config.max_retries):
            try:
                conn = await asyncio.wait_for(
                    websockets.connect(self.uri, **self.connect_kwargs),
                    timeout=self.config.connection_timeout,
                )
                pooled = PooledConnection(connection=conn, pool=self)
                self._all_connections.add(pooled)
                self._stats.connections_created += 1
                return pooled

            except asyncio.TimeoutError:
                logger.error(f"Connection timeout on attempt {attempt + 1}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay)
                else:
                    raise
            except Exception as e:
                logger.error(f"Connection failed on attempt {attempt + 1}: {e}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay)
                else:
                    raise

        raise ConnectionError("Failed to create connection after retries")

    @asynccontextmanager
    async def acquire(self):
        """
        Acquire a connection from the pool.

        Returns:
            Context manager yielding a WebSocket connection
        """
        if self._closing:
            raise RuntimeError("Pool is closing")

        conn = await self._acquire_connection()
        try:
            yield conn.connection
        finally:
            await self._release_connection(conn)

    async def _acquire_connection(self) -> PooledConnection:
        """Acquire a connection from the pool."""
        start_time = time.time()

        while True:
            # Check timeout
            if time.time() - start_time > self.config.acquire_timeout:
                self._stats.acquire_timeouts += 1
                raise TimeoutError("Failed to acquire connection from pool")

            async with self._lock:
                # Try to get available connection
                while self._available:
                    conn = self._available.popleft()

                    # Check if connection is healthy
                    if conn.is_healthy() and not conn.is_expired(self.config.max_idle_time):
                        conn.in_use = True
                        conn.last_used = time.time()
                        conn.use_count += 1
                        self._in_use.add(conn)
                        self._stats.acquires += 1
                        return conn
                    else:
                        # Close unhealthy connection
                        await conn.close()
                        self._stats.connections_closed += 1

                # Check if we can create new connection
                if len(self._in_use) < self.config.max_size:
                    try:
                        conn = await self._create_connection()
                        conn.in_use = True
                        self._in_use.add(conn)
                        self._stats.acquires += 1
                        return conn
                    except Exception as e:
                        logger.error(f"Failed to create new connection: {e}")
                        self._stats.connection_failures += 1

            # Wait for available connection
            waiter = asyncio.Future()
            self._waiters.append(waiter)
            try:
                await asyncio.wait_for(waiter, timeout=1.0)
            except asyncio.TimeoutError:
                # Continue loop to check timeout
                pass
            finally:
                self._waiters.remove(waiter)

    async def _release_connection(self, conn: PooledConnection) -> None:
        """Release a connection back to the pool."""
        async with self._lock:
            if conn in self._in_use:
                self._in_use.remove(conn)

            if conn.is_healthy() and not self._closing:
                conn.in_use = False
                conn.last_used = time.time()
                self._available.append(conn)
                self._stats.releases += 1

                # Notify waiters
                if self._waiters:
                    waiter = self._waiters.popleft()
                    if not waiter.done():
                        waiter.set_result(None)
            else:
                # Close unhealthy connection
                await conn.close()
                self._stats.connections_closed += 1

    async def _health_check_loop(self) -> None:
        """Background task to check connection health."""
        while not self._closing:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self._health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")

    async def _health_check(self) -> None:
        """Check health of pooled connections."""
        async with self._lock:
            # Check available connections
            healthy_conns = deque()
            for conn in self._available:
                if conn.is_healthy() and not conn.is_expired(self.config.max_idle_time):
                    # Send ping to check connection
                    try:
                        pong_waiter = await conn.connection.ping()
                        await asyncio.wait_for(pong_waiter, timeout=5.0)
                        healthy_conns.append(conn)
                    except Exception:
                        await conn.close()
                        self._stats.connections_closed += 1
                else:
                    await conn.close()
                    self._stats.connections_closed += 1

            self._available = healthy_conns

            # Maintain minimum connections
            current_size = len(self._available) + len(self._in_use)
            if current_size < self.config.min_size:
                for _ in range(self.config.min_size - current_size):
                    try:
                        conn = await self._create_connection()
                        self._available.append(conn)
                    except Exception as e:
                        logger.warning(f"Failed to create connection during health check: {e}")

    def get_stats(self) -> "PoolStats":
        """Get pool statistics."""
        self._stats.available_connections = len(self._available)
        self._stats.in_use_connections = len(self._in_use)
        self._stats.total_connections = len(self._available) + len(self._in_use)
        return self._stats


@dataclass
class PoolStats:
    """Connection pool statistics."""

    connections_created: int = 0
    connections_closed: int = 0
    connection_failures: int = 0
    acquires: int = 0
    releases: int = 0
    acquire_timeouts: int = 0
    available_connections: int = 0
    in_use_connections: int = 0
    total_connections: int = 0

    def __str__(self) -> str:
        """String representation of stats."""
        return (
            f"PoolStats(available={self.available_connections}, "
            f"in_use={self.in_use_connections}, "
            f"total={self.total_connections}, "
            f"created={self.connections_created}, "
            f"closed={self.connections_closed})"
        )


class ConnectionPoolManager:
    """
    Manager for multiple connection pools.

    Manages pools for different URIs/endpoints.
    """

    def __init__(self, default_config: Optional[PoolConfig] = None):
        """
        Initialize pool manager.

        Args:
            default_config: Default configuration for pools
        """
        self.default_config = default_config or PoolConfig()
        self._pools: Dict[str, ConnectionPool] = {}
        self._lock = asyncio.Lock()

    async def get_pool(
        self, uri: str, config: Optional[PoolConfig] = None, **connect_kwargs
    ) -> ConnectionPool:
        """
        Get or create a connection pool for URI.

        Args:
            uri: WebSocket URI
            config: Pool configuration (uses default if not provided)
            **connect_kwargs: Additional connection arguments

        Returns:
            Connection pool for the URI
        """
        async with self._lock:
            if uri not in self._pools:
                pool_config = config or self.default_config
                pool = ConnectionPool(uri, pool_config, **connect_kwargs)
                await pool.start()
                self._pools[uri] = pool

            return self._pools[uri]

    async def close_pool(self, uri: str) -> None:
        """Close a specific pool."""
        async with self._lock:
            if uri in self._pools:
                await self._pools[uri].stop()
                del self._pools[uri]

    async def close_all(self) -> None:
        """Close all pools."""
        async with self._lock:
            for pool in self._pools.values():
                await pool.stop()
            self._pools.clear()

    def get_stats(self) -> Dict[str, PoolStats]:
        """Get statistics for all pools."""
        return {uri: pool.get_stats() for uri, pool in self._pools.items()}
