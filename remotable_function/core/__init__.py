"""
Core components shared between server and client.
"""

from .protocol import RPCRequest, RPCResponse, RPCError, RPCErrorCode
from .types import (
    ToolDefinition,
    ParameterSchema,
    ParameterType,
    ToolExample,
    ClientInfo,
    ToolContext,
    ConnectionState,
    ToolExecutionState,
)
from .registry import ToolRegistry
from .ratelimit import (
    RateLimiter,
    SlidingWindowRateLimiter,
    TokenBucketRateLimiter,
    CompositeRateLimiter,
    RateLimitConfig,
    create_rate_limiter,
)
from .events import EventEmitter, EventPriority, EventHandler
from .cache import LRUCache, ResponseCache, CacheStats
from .compression import (
    MessageCompressor,
    CompressionStats,
    create_compressed_message,
    extract_compressed_message,
)
from .exceptions import (
    RemotableError,
    ConnectionError,
    AuthenticationError,
    ValidationError,
    ToolError,
    TimeoutError,
    RateLimitError,
    ConfigurationError,
    SecurityError,
)

__all__ = [
    # Protocol
    "RPCRequest",
    "RPCResponse",
    "RPCError",
    "RPCErrorCode",
    # Types
    "ToolDefinition",
    "ParameterSchema",
    "ParameterType",
    "ToolExample",
    "ClientInfo",
    "ToolContext",
    "ConnectionState",
    "ToolExecutionState",
    # Registry
    "ToolRegistry",
    # Rate Limiting
    "RateLimiter",
    "SlidingWindowRateLimiter",
    "TokenBucketRateLimiter",
    "CompositeRateLimiter",
    "RateLimitConfig",
    "create_rate_limiter",
    # Events
    "EventEmitter",
    "EventPriority",
    "EventHandler",
    # Cache
    "LRUCache",
    "ResponseCache",
    "CacheStats",
    # Compression
    "MessageCompressor",
    "CompressionStats",
    "create_compressed_message",
    "extract_compressed_message",
    # Exceptions
    "RemotableError",
    "ConnectionError",
    "AuthenticationError",
    "ValidationError",
    "ToolError",
    "TimeoutError",
    "RateLimitError",
    "ConfigurationError",
    "SecurityError",
]
