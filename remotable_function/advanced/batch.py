"""
Batch processing for Remotable.

Provides request batching to improve throughput.
"""

import asyncio
import logging
import time
import json
from typing import List, Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from collections import deque
from enum import Enum
import uuid

from .protocol import RPCRequest, RPCResponse, RPCError, RPCErrorCode

logger = logging.getLogger(__name__)


class BatchStrategy(Enum):
    """Batching strategies."""

    TIME_BASED = "time_based"  # Batch by time window
    SIZE_BASED = "size_based"  # Batch by request count
    HYBRID = "hybrid"  # Combine time and size


@dataclass
class BatchConfig:
    """Batch processing configuration."""

    strategy: BatchStrategy = BatchStrategy.HYBRID
    max_batch_size: int = 50  # Maximum requests per batch
    batch_timeout: float = 0.1  # Maximum wait time (100ms)
    max_queue_size: int = 1000  # Maximum pending requests
    enable_compression: bool = True  # Compress batch requests
    enable_deduplication: bool = True  # Deduplicate identical requests
    parallel_execution: bool = True  # Execute batch items in parallel


@dataclass
class BatchRequest:
    """Individual request in a batch."""

    request: RPCRequest
    future: asyncio.Future
    timestamp: float = field(default_factory=time.time)
    priority: int = 0
    retry_count: int = 0

    def __hash__(self) -> int:
        """Hash for deduplication."""
        return hash((self.request.method, json.dumps(self.request.params, sort_keys=True)))


class BatchProcessor:
    """
    Batch processor for aggregating and processing requests.

    Example:
        processor = BatchProcessor(send_func=gateway.send_batch)

        # Queue requests
        result1 = await processor.add_request(request1)
        result2 = await processor.add_request(request2)

        # Requests are automatically batched and sent
    """

    def __init__(
        self,
        send_func: Callable,
        config: Optional[BatchConfig] = None,
    ):
        """
        Initialize batch processor.

        Args:
            send_func: Function to send batch (async)
            config: Batch configuration
        """
        self.send_func = send_func
        self.config = config or BatchConfig()

        # Request queue
        self._queue: deque[BatchRequest] = deque()
        self._pending: Dict[str, List[BatchRequest]] = {}  # For deduplication

        # Processing
        self._processing = False
        self._process_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

        # Statistics
        self._stats = BatchStats()

    async def start(self) -> None:
        """Start batch processing."""
        if self._process_task:
            return

        self._processing = True
        self._process_task = asyncio.create_task(self._process_loop())
        logger.info("Batch processor started")

    async def stop(self) -> None:
        """Stop batch processing."""
        self._processing = False

        if self._process_task:
            # Process remaining requests
            await self._flush()

            # Cancel task
            self._process_task.cancel()
            try:
                await self._process_task
            except asyncio.CancelledError:
                pass

        logger.info("Batch processor stopped")

    async def add_request(
        self,
        request: RPCRequest,
        priority: int = 0,
    ) -> Any:
        """
        Add request to batch queue.

        Args:
            request: RPC request
            priority: Request priority (higher = more important)

        Returns:
            Request result (when batch is processed)
        """
        if len(self._queue) >= self.config.max_queue_size:
            raise RuntimeError("Batch queue is full")

        # Create batch request
        batch_req = BatchRequest(
            request=request,
            future=asyncio.Future(),
            priority=priority,
        )

        # Check for deduplication
        if self.config.enable_deduplication:
            req_hash = hash(batch_req)
            async with self._lock:
                if req_hash in self._pending:
                    # Duplicate request - share the future
                    existing = self._pending[req_hash][0]
                    self._stats.duplicates_merged += 1
                    return await existing.future
                else:
                    self._pending.setdefault(req_hash, []).append(batch_req)

        # Add to queue
        async with self._lock:
            self._queue.append(batch_req)
            self._stats.requests_queued += 1

        # Wait for result
        return await batch_req.future

    async def _process_loop(self) -> None:
        """Main processing loop."""
        while self._processing:
            try:
                # Collect batch
                batch = await self._collect_batch()

                if batch:
                    # Process batch
                    await self._process_batch(batch)

                else:
                    # No requests - wait briefly
                    await asyncio.sleep(0.01)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Batch processing error: {e}")
                await asyncio.sleep(0.1)

    async def _collect_batch(self) -> List[BatchRequest]:
        """Collect requests for a batch."""
        batch: List[BatchRequest] = []
        start_time = time.time()

        async with self._lock:
            # Collect based on strategy
            if self.config.strategy == BatchStrategy.SIZE_BASED:
                # Collect up to max_batch_size
                while self._queue and len(batch) < self.config.max_batch_size:
                    batch.append(self._queue.popleft())

            elif self.config.strategy == BatchStrategy.TIME_BASED:
                # Collect all within timeout window
                deadline = start_time + self.config.batch_timeout
                while self._queue and time.time() < deadline:
                    batch.append(self._queue.popleft())
                    if len(batch) >= self.config.max_batch_size:
                        break

            else:  # HYBRID
                # Collect until size or timeout reached
                deadline = start_time + self.config.batch_timeout
                while self._queue:
                    if len(batch) >= self.config.max_batch_size:
                        break
                    if time.time() >= deadline and batch:
                        break
                    batch.append(self._queue.popleft())

            # Sort by priority if needed
            if batch and any(req.priority != 0 for req in batch):
                batch.sort(key=lambda x: x.priority, reverse=True)

        return batch

    async def _process_batch(self, batch: List[BatchRequest]) -> None:
        """Process a batch of requests."""
        if not batch:
            return

        start_time = time.time()
        self._stats.batches_processed += 1
        self._stats.requests_processed += len(batch)

        try:
            # Prepare batch request
            batch_data = {
                "jsonrpc": "2.0",
                "method": "batch",
                "params": {
                    "requests": [req.request.to_dict() for req in batch],
                    "parallel": self.config.parallel_execution,
                },
                "id": str(uuid.uuid4()),
            }

            # Send batch
            responses = await self.send_func(batch_data)

            # Process responses
            if isinstance(responses, dict) and "results" in responses:
                results = responses["results"]
                for i, batch_req in enumerate(batch):
                    if i < len(results):
                        result = results[i]
                        if "error" in result:
                            error = RPCError.from_dict(result["error"])
                            batch_req.future.set_exception(Exception(error.message))
                        else:
                            batch_req.future.set_result(result.get("result"))
                    else:
                        batch_req.future.set_exception(Exception("Missing response"))

            else:
                # Single response or error
                for batch_req in batch:
                    batch_req.future.set_exception(Exception("Invalid batch response"))

            # Update stats
            duration = time.time() - start_time
            self._stats.total_latency += duration
            self._stats.avg_batch_size = (
                self._stats.avg_batch_size * (self._stats.batches_processed - 1) + len(batch)
            ) / self._stats.batches_processed

        except Exception as e:
            logger.error(f"Batch send error: {e}")
            self._stats.batch_errors += 1

            # Set error for all requests
            for batch_req in batch:
                if not batch_req.future.done():
                    batch_req.future.set_exception(e)

        finally:
            # Clear pending tracking
            if self.config.enable_deduplication:
                async with self._lock:
                    for batch_req in batch:
                        req_hash = hash(batch_req)
                        if req_hash in self._pending:
                            del self._pending[req_hash]

    async def _flush(self) -> None:
        """Flush all pending requests."""
        while self._queue:
            batch = await self._collect_batch()
            if batch:
                await self._process_batch(batch)

    def get_stats(self) -> "BatchStats":
        """Get batch processing statistics."""
        self._stats.queue_size = len(self._queue)
        if self._stats.batches_processed > 0:
            self._stats.avg_latency = self._stats.total_latency / self._stats.batches_processed
        return self._stats


@dataclass
class BatchStats:
    """Batch processing statistics."""

    requests_queued: int = 0
    requests_processed: int = 0
    batches_processed: int = 0
    batch_errors: int = 0
    duplicates_merged: int = 0
    queue_size: int = 0
    avg_batch_size: float = 0.0
    avg_latency: float = 0.0
    total_latency: float = 0.0


class RequestAggregator:
    """
    Aggregates similar requests for efficient processing.

    Useful for read-heavy workloads with repeated queries.
    """

    def __init__(self, window_ms: int = 100):
        """
        Initialize request aggregator.

        Args:
            window_ms: Aggregation window in milliseconds
        """
        self.window_ms = window_ms
        self._pending: Dict[str, List[asyncio.Future]] = {}
        self._lock = asyncio.Lock()

    async def aggregate(self, key: str, func: Callable, *args, **kwargs) -> Any:
        """
        Aggregate request with others.

        Args:
            key: Request key for aggregation
            func: Function to call
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result
        """
        future = asyncio.Future()

        async with self._lock:
            if key in self._pending:
                # Add to existing aggregation
                self._pending[key].append(future)
            else:
                # Start new aggregation
                self._pending[key] = [future]

                # Schedule execution
                asyncio.create_task(self._execute_aggregated(key, func, *args, **kwargs))

        return await future

    async def _execute_aggregated(self, key: str, func: Callable, *args, **kwargs) -> None:
        """Execute aggregated request."""
        # Wait for aggregation window
        await asyncio.sleep(self.window_ms / 1000.0)

        # Get all futures
        async with self._lock:
            futures = self._pending.pop(key, [])

        if not futures:
            return

        try:
            # Execute function once
            result = await func(*args, **kwargs)

            # Set result for all futures
            for future in futures:
                if not future.done():
                    future.set_result(result)

        except Exception as e:
            # Set exception for all futures
            for future in futures:
                if not future.done():
                    future.set_exception(e)


class BatchRequestOptimizer:
    """
    Optimizes batch requests by reordering and combining.
    """

    @staticmethod
    def optimize(requests: List[RPCRequest]) -> List[RPCRequest]:
        """
        Optimize batch of requests.

        Args:
            requests: List of requests

        Returns:
            Optimized list of requests
        """
        # Group by method
        by_method: Dict[str, List[RPCRequest]] = {}
        for req in requests:
            by_method.setdefault(req.method, []).append(req)

        # Optimize each group
        optimized = []

        # Process reads first (usually faster)
        for method in sorted(by_method.keys()):
            if "read" in method.lower() or "get" in method.lower():
                optimized.extend(by_method.pop(method))

        # Then writes
        for method in sorted(by_method.keys()):
            optimized.extend(by_method[method])

        return optimized

    @staticmethod
    def combine_similar(requests: List[RPCRequest]) -> List[RPCRequest]:
        """
        Combine similar requests where possible.

        Args:
            requests: List of requests

        Returns:
            Combined requests
        """
        # Example: Combine multiple reads of same resource
        combined = []
        seen = set()

        for req in requests:
            req_key = (req.method, json.dumps(req.params, sort_keys=True))
            if req_key not in seen:
                combined.append(req)
                seen.add(req_key)

        return combined
