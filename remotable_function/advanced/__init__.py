"""
Advanced features for Remotable.

These are optional features for advanced use cases. Most users won't need these.
"""

# Connection pooling
from .pool import (
    ConnectionPool,
    ConnectionPoolManager,
    PoolConfig,
    PoolStats,
)

# Batch processing
from .batch import (
    BatchProcessor,
    BatchConfig,
    BatchStrategy,
    RequestAggregator,
)

# Advanced serialization
from .serialization import (
    FastSerializer,
    SerializationFormat,
    SerializationConfig,
    BinaryProtocol,
)

# Pooled client
from .pooled_client import (
    PooledClient,
    MultiGatewayClient,
)

__all__ = [
    # Pool
    "ConnectionPool",
    "ConnectionPoolManager",
    "PoolConfig",
    "PoolStats",
    # Batch
    "BatchProcessor",
    "BatchConfig",
    "BatchStrategy",
    "RequestAggregator",
    # Serialization
    "FastSerializer",
    "SerializationFormat",
    "SerializationConfig",
    "BinaryProtocol",
    # Clients
    "PooledClient",
    "MultiGatewayClient",
]
