"""
Remotable Function v2.0 - Simple and efficient RPC framework for AI agents.

A lightweight framework for remote procedure calls between servers and clients,
optimized for AI agent tool execution.

Quick Start:
    # Server (2 lines)
    import remotable_function
    server = await remotable_function.start_server(port=8000)

    # Client (3 lines)
    import remotable_function
    client = await remotable_function.connect_client("ws://localhost:8000")
    client.register_tool(remotable_function.FileSystemTool())
"""

__version__ = "2.0.0"

# Core classes - Unified implementation
from .gateway_unified import Gateway, create_gateway, start_server
from .client_unified import Client, create_client, connect_client

# Import Tool base class
from .client.tool import Tool

# Configuration
try:
    from .config import GatewayConfig, ClientConfig, ConnectionState
except ImportError:
    # Provide stubs if config not available
    class GatewayConfig:
        def __init__(self):
            pass

        @classmethod
        def production(cls):
            return cls()

    class ClientConfig:
        def __init__(self):
            pass

        @classmethod
        def from_url(cls, url):
            return cls()

    class ConnectionState:
        DISCONNECTED = "disconnected"
        CONNECTING = "connecting"
        CONNECTED = "connected"
        RECONNECTING = "reconnecting"
        FAILED = "failed"


# Built-in tools
from .client.tools.filesystem import FileSystemTool
from .client.tools.shell import ShellTool

# Note: SystemInfoTool, NetworkTool, ProcessTool not yet implemented

# Essential types only
from .core.types import ToolDefinition, ParameterSchema, ParameterType

# Alias for backward compatibility
ToolParameter = ParameterSchema

__all__ = [
    # Main classes (3)
    "Gateway",
    "Client",
    "Tool",
    # Convenience functions (4)
    "create_gateway",
    "run_gateway",
    "create_client",
    "run_client",
    # Configuration (2)
    "GatewayConfig",
    "ClientConfig",
    # Built-in tools (2 available currently)
    "FileSystemTool",
    "ShellTool",
    # Types (3)
    "ToolDefinition",
    "ToolParameter",
    "ParameterType",
]


# Quick start functions
async def start_server(port: int = 8000, auth_token: str = None) -> Gateway:
    """
    Quick start a server.

    Example:
        server = await remotable.start_server(port=9000)
    """
    gateway = create_gateway(port=port, auth_token=auth_token)
    await gateway.start()
    return gateway


async def connect_client(
    server_url: str = "ws://localhost:8000", tools: list = None, auth_token: str = None
) -> Client:
    """
    Quick connect a client.

    Example:
        client = await remotable.connect_client(
            tools=[FileSystemTool()]
        )
    """
    client = create_client(server_url, auth_token=auth_token)
    if tools:
        for tool in tools:
            client.register_tool(tool)
    await client.connect()
    return client


# Import typing for backwards compatibility
from typing import Literal, Dict, Any
import warnings

# Global config for backward compatibility
_role = None
_config = {}


def configure(role: Literal["server", "client"], **kwargs) -> None:
    """
    配置 Remotable 的运行角色。

    ⚠️ DEPRECATED: 此函数已废弃，推荐直接导入类使用：
        from remotable import Gateway, Client

    为了向后兼容保留此函数，但不再是必需的。
    Remotable 现在支持多实例，无需全局配置。

    Args:
        role: "server" 或 "client"
        **kwargs: 其他配置参数（已忽略，请在实例化时传递）

    Example:
        # 旧用法（已废弃）
        remotable.configure(role="server")
        gateway = remotable.Gateway(host="0.0.0.0", port=8000)

        # 新用法（推荐）
        from remotable import Gateway
        gateway = Gateway(host="0.0.0.0", port=8000)

    Raises:
        ValueError: 如果 role 不是 "server" 或 "client"
    """
    global _role, _config

    if role not in ["server", "client"]:
        raise ValueError(
            f"Invalid role: '{role}'. Must be 'server' or 'client'.\n"
            f"Usage: remotable.configure(role='server') or remotable.configure(role='client')"
        )

    _role = role
    _config = kwargs

    # 显示废弃警告
    warnings.warn(
        "remotable.configure() is deprecated and no longer required. "
        "Simply import classes directly: from remotable import Gateway, Client",
        DeprecationWarning,
        stacklevel=2,
    )

    print(
        f"✓ Remotable configured as {role.upper()} (configure() is deprecated, direct imports are now recommended)"
    )


def get_role() -> str:
    """获取当前配置的角色"""
    if _role is None:
        raise RuntimeError(
            "Remotable not configured. Call remotable.configure(role='server' or 'client') first."
        )
    return _role


def get_config() -> Dict[str, Any]:
    """获取配置参数"""
    return _config.copy()


def is_server() -> bool:
    """检查是否配置为服务器"""
    return _role == "server"


def is_client() -> bool:
    """检查是否配置为客户端"""
    return _role == "client"


# 动态导入（已废弃，为了向后兼容保留）
def __getattr__(name: str):
    """
    动态导入基于角色的类（已废弃）。

    ⚠️ DEPRECATED: 此功能已废弃。所有类现在都已直接导入，
    无需 configure() 即可使用。

    保留此函数仅为向后兼容旧代码。
    """
    # 如果是已导入的类，直接返回
    module_globals = globals()
    if name in module_globals and module_globals[name] is not None:
        return module_globals[name]

    # 如果配置了 role，显示废弃警告
    if _role is not None:
        warnings.warn(
            f"Dynamic import of '{name}' via configure() is deprecated. "
            f"Use direct import instead: from remotable import {name}",
            DeprecationWarning,
            stacklevel=2,
        )

    # 未找到
    raise AttributeError(
        f"module 'remotable' has no attribute '{name}'.\n"
        f"Available classes: Gateway, Client, ConnectionManager, Tool, FileSystemTools, ShellTools\n"
        f"Available types: RPCRequest, RPCResponse, RPCError, RPCErrorCode, ToolDefinition, ParameterSchema\n"
        f"Usage: from remotable import Gateway, Client"
    )


# 导出的公共 API
__all__ = [
    # 核心类（直接导入，支持多实例）
    "Gateway",  # server
    "ConnectionManager",  # server
    "Client",  # client
    "Tool",  # client
    "FileSystemTools",  # client
    "ShellTools",  # client
    # 协议类型
    "RPCRequest",
    "RPCResponse",
    "RPCError",
    "RPCErrorCode",
    # 类型定义
    "ToolDefinition",
    "ParameterSchema",
    "ParameterType",
    "ToolExample",
    "ClientInfo",
    # 验证工具
    "validate_parameters",
    "ValidationError",
    # 事件系统
    "EventEmitter",
    "EventPriority",
    "EventHandler",
    # 配置函数（已废弃，向后兼容）
    "configure",
    "get_role",
    "get_config",
    "is_server",
    "is_client",
]
