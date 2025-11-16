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
]
