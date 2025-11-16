"""
Remotable - Unified RPC Framework for Server and Client

类似 Unity Netcode 的设计，一套代码，通过 role 配置区分 server/client。

Example:
    Server side:
        import remotable
        remotable.configure(role="server")
        gateway = remotable.Gateway(host="0.0.0.0", port=8000)
        await gateway.start()

    Client side:
        import remotable
        remotable.configure(role="client")
        client = remotable.Client(server_url="ws://localhost:8000")
        await client.connect()
"""

__version__ = "0.2.0"

from typing import Optional, Dict, Any, Literal

# 全局配置
_role: Optional[Literal["server", "client"]] = None
_config: Dict[str, Any] = {}


def configure(role: Literal["server", "client"], **kwargs) -> None:
    """
    配置 Remotable 的运行角色。

    必须在使用任何其他 API 之前调用此函数。

    Args:
        role: "server" 或 "client"
        **kwargs: 其他配置参数
            - 对于 server: host, port, heartbeat_interval 等
            - 对于 client: server_url, client_id 等

    Example:
        # 服务器端
        remotable.configure(role="server", host="0.0.0.0", port=8000)

        # 客户端
        remotable.configure(role="client", server_url="ws://localhost:8000")

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

    print(f"✓ Remotable configured as {role.upper()}")


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


# 动态导入：根据 role 加载对应的类
def __getattr__(name: str):
    """
    动态导入基于角色的类。

    当访问 remotable.Gateway 或 remotable.Client 时，
    根据 configure() 设置的 role 自动导入对应的类。
    """
    if _role is None:
        raise RuntimeError(
            f"Cannot import '{name}': Remotable not configured.\n"
            f"Call remotable.configure(role='server' or 'client') first."
        )

    # 服务器端类
    if _role == "server":
        if name == "Gateway":
            from .server.gateway import Gateway

            return Gateway

        if name == "ConnectionManager":
            from .server.manager import ConnectionManager

            return ConnectionManager

    # 客户端类
    elif _role == "client":
        if name == "Client":
            from .client.client import Client

            return Client

        if name == "Tool":
            from .client.tools.base import Tool

            return Tool

        if name == "FileSystemTools":
            from .client.tools.filesystem import FileSystemTools

            return FileSystemTools

        if name == "ShellTools":
            from .client.tools.shell import ShellTools

            return ShellTools

    # 共享类（两端都可用）
    if name in ["RPCRequest", "RPCResponse", "RPCError", "RPCErrorCode"]:
        from .core.protocol import RPCRequest, RPCResponse, RPCError, RPCErrorCode

        return locals()[name]

    if name == "ToolDefinition":
        from .core.types import ToolDefinition

        return ToolDefinition

    # 未找到
    raise AttributeError(
        f"'{name}' is not available in {_role} mode.\n"
        f"Available in server mode: Gateway, ConnectionManager\n"
        f"Available in client mode: Client, Tool, FileSystemTools, ShellTools\n"
        f"Available in both modes: RPCRequest, RPCResponse, RPCError, ToolDefinition"
    )


# 导出的公共 API
__all__ = [
    # 配置函数
    "configure",
    "get_role",
    "get_config",
    "is_server",
    "is_client",
    # 动态导入的类（通过 __getattr__）
    "Gateway",  # server
    "ConnectionManager",  # server
    "Client",  # client
    "Tool",  # client
    "FileSystemTools",  # client
    "ShellTools",  # client
    # 共享类
    "RPCRequest",
    "RPCResponse",
    "RPCError",
    "RPCErrorCode",
    "ToolDefinition",
]
