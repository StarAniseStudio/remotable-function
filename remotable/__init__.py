"""
Remotable - Unified RPC Framework for Server and Client

轻量级 RPC 框架，支持服务器端调用客户端工具。

Example:
    Server side:
        from remotable import Gateway
        gateway = Gateway(host="0.0.0.0", port=8000)
        await gateway.start()

    Client side:
        from remotable import Client
        client = Client(server_url="ws://localhost:8000")
        await client.connect()
"""

__version__ = "1.3.0"

import warnings
from typing import Optional, Dict, Any, Literal

# 直接导出核心类，支持多实例，无需 configure()
from .server.gateway import Gateway
from .client.client import Client
from .core.protocol import RPCRequest, RPCResponse, RPCError, RPCErrorCode
from .core.types import ToolDefinition, ParameterSchema, ParameterType, ToolExample, ClientInfo
from .core.validation import validate_parameters, ValidationError
from .core.events import EventEmitter, EventPriority, EventHandler

# 客户端工具类（可选导入）
try:
    from .client.tools.base import Tool
    from .client.tools.filesystem import FileSystemTools
    from .client.tools.shell import ShellTools
except ImportError:
    # 如果客户端依赖不可用，优雅降级
    Tool = None
    FileSystemTools = None
    ShellTools = None

# 服务器管理类（可选导入）
try:
    from .server.manager import ConnectionManager
except ImportError:
    ConnectionManager = None

# 全局配置（已废弃，为了向后兼容保留）
_role: Optional[Literal["server", "client"]] = None
_config: Dict[str, Any] = {}


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
        stacklevel=2
    )

    print(f"✓ Remotable configured as {role.upper()} (configure() is deprecated, direct imports are now recommended)")


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
            stacklevel=2
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
