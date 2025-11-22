#!/usr/bin/env python3
"""
Remotable Function Client Demo - Enhanced UI Version

这是一个增强版的客户端demo，使用 rich 库提供更美观的命令行输出。
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# Add remotable_function to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import remotable_function

# Import built-in tools
from remotable_function.client.tools import (
    ReadFileTool,
    WriteFileTool,
    ListDirectoryTool,
    DeleteFileTool,
    ShellExecuteTool,
)

# Import custom tool base
from remotable_function.client.tool import Tool
from remotable_function.core.types import ToolContext, ParameterSchema, ParameterType

# Rich console for beautiful output
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich import box

console = Console()


# Custom Tool: System Info
class SystemInfoTool(Tool):
    """获取系统和用户信息的自定义工具"""

    name = "get_system_info"
    description = "获取本机的系统信息和用户信息"
    namespace = "system"
    permissions = ["system.read"]
    tags = ["system", "info"]

    parameters = []  # 不需要参数

    async def execute(self, context: ToolContext, **kwargs) -> dict:
        """
        获取系统和用户信息

        Returns:
            包含系统和用户信息的字典
        """
        import platform
        import os
        import getpass
        import socket
        from datetime import datetime

        try:
            # 系统信息
            system_info = {
                "system": platform.system(),
                "node": platform.node(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
            }

            # 用户信息
            user_info = {
                "username": getpass.getuser(),
                "home_dir": os.path.expanduser("~"),
                "current_dir": os.getcwd(),
            }

            # 网络信息
            try:
                hostname = socket.gethostname()
                ip_address = socket.gethostbyname(hostname)
                network_info = {
                    "hostname": hostname,
                    "ip_address": ip_address,
                }
            except Exception:
                network_info = {
                    "hostname": "unknown",
                    "ip_address": "unknown",
                }

            # 环境信息
            env_info = {
                "shell": os.environ.get("SHELL", "unknown"),
                "terminal": os.environ.get("TERM", "unknown"),
                "lang": os.environ.get("LANG", "unknown"),
            }

            return {
                "timestamp": datetime.now().isoformat(),
                "system": system_info,
                "user": user_info,
                "network": network_info,
                "environment": env_info,
            }

        except Exception as e:
            raise Exception(f"Failed to get system info: {e}")


# Configure logging
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
#     datefmt="%H:%M:%S"
# )
# logger = logging.getLogger(__name__)

# 只显示 INFO 及以上级别
# logging.getLogger("remotable").setLevel(logging.INFO)
# logging.getLogger("websockets").setLevel(logging.WARNING)


async def main():
    """Main client function with enhanced UI."""

    # Print banner
    console.clear()
    console.print(Panel.fit(
        "[bold cyan]Remotable Function Client Demo[/bold cyan]\n"
        "[dim]轻量级 RPC 框架[/dim]",
        border_style="cyan",
        box=box.DOUBLE
    ))
    console.print()

    # Initialize test environment
    console.print("[bold yellow]🔧 初始化测试环境[/bold yellow]")
    test_dir = await prepare_test_file()
    console.print(f"[green]✓[/green] 测试目录: [cyan]{test_dir}[/cyan]\n")

    # Create Client
    console.print("[bold yellow]🚀 创建客户端实例[/bold yellow]")
    client = remotable_function.Client(
        server_url="ws://localhost:8000",
        client_id="demo-client",
        version="1.0.0",
        auto_reconnect=True,
        reconnect_interval=5,
        reconnect_max_attempts=10
    )
    console.print("[green]✓[/green] 客户端创建成功\n")

    # Register event handlers using v2.0 API
    async def on_connected():
        """Handle connection."""
        # Re-ensure test files exist after connection (handles any startup order)
        await prepare_test_file()

        console.print()
        console.print(Panel(
            "[bold green]✓ 已连接到服务器[/bold green]\n\n"
            f"[cyan]客户端ID:[/cyan] {client.client_id}\n"
            f"[cyan]已注册工具:[/cyan] {len(client.list_tools())}",
            title="[bold]连接成功[/bold]",
            border_style="green"
        ))

        # Show tools table
        table = Table(title="注册的工具", box=box.ROUNDED)
        table.add_column("工具名称", style="cyan")
        table.add_column("命名空间", style="yellow")

        for tool_name in client.list_tools():
            if '.' in tool_name:
                namespace, name = tool_name.split('.')
                table.add_row(tool_name, namespace)
            else:
                table.add_row(tool_name, "-")

        console.print(table)
        console.print()
        console.print("[dim]等待服务器调用工具...[/dim]\n")

    async def on_disconnected():
        """Handle disconnection."""
        console.print("\n[bold red]✗ 已断开连接[/bold red]\n")

    async def on_tool_executed(tool_name: str, result):
        """Handle tool execution."""
        # 使用简洁的输出
        console.print(f"[green]→[/green] 执行工具: [cyan]{tool_name}[/cyan]")

    # Register the event handlers if the client supports them
    if hasattr(client, 'on'):
        client.on("connected", on_connected)
        client.on("disconnected", on_disconnected)
        client.on("tool_executed", on_tool_executed)

    # Register tools with progress
    console.print("[bold yellow]📦 注册工具[/bold yellow]")

    tools = [
        ReadFileTool(),
        WriteFileTool(),
        ListDirectoryTool(),
        DeleteFileTool(),
        ShellExecuteTool(),
        SystemInfoTool(),  # 自定义工具
    ]

    for tool in tools:
        client.register_tool(tool)
        console.print(f"  [green]✓[/green] {tool.full_name}")

    console.print()

    # Connect to server with animation
    console.print("[bold yellow]🔌 连接到服务器[/bold yellow]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("正在连接 ws://localhost:8000...", total=None)
        await client.connect()
        progress.update(task, completed=True)

    # Keep running with status
    try:
        console.print("\n[bold green]🟢 客户端运行中[/bold green]")
        console.print("[dim]按 Ctrl+C 退出[/dim]\n")

        await asyncio.Event().wait()
    except KeyboardInterrupt:
        console.print("\n[yellow]正在关闭客户端...[/yellow]")
        await client.disconnect()
        console.print("[green]✓ 客户端已停止[/green]\n")


async def prepare_test_file():
    """Prepare test files for demo."""
    from pathlib import Path

    # Create test_files directory in demo folder
    # Use resolve() to get absolute path first
    demo_dir = Path(__file__).resolve().parent.parent
    test_dir = demo_dir / "test_files"

    try:
        # Create directory
        test_dir.mkdir(parents=True, exist_ok=True)

        # Create initial test file (always recreate to ensure it exists)
        test_file = test_dir / "client_data.txt"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Always write the file to ensure it exists
        test_file.write_text(f"""{'=' * 60}
Remotable Function Demo - 客户端初始数据
{'=' * 60}

这个文件由客户端创建，服务器将远程读取和修改它。

客户端信息：
  - 客户端ID: demo-client
  - 版本: 1.0.0
  - 创建时间: {timestamp}
  - 状态: 等待连接

等待服务器的远程操作...
{'=' * 60}
""", encoding="utf-8")

        # Create README
        readme_file = test_dir / "README.md"
        readme_file.write_text(f"""# Remotable Function Demo Test Files

这个目录包含 Remotable Function 演示的测试文件。

## 📁 文件说明

- `client_data.txt` - 客户端创建的初始数据文件
- `server_message.txt` - 服务器远程创建的文件（运行后出现）

## 👀 观察效果

1. **启动客户端**后，会创建 `client_data.txt`
2. **启动服务器**后，服务器会远程操作客户端：
   - 📖 读取 `client_data.txt`
   - ✍️  创建新的 `server_message.txt`
   - 📝 修改 `client_data.txt`，追加服务器的操作记录
   - 📂 列出目录内容
   - 🖥️  执行shell命令

👉 **打开这些文件，实时查看服务器的远程操作效果！**

---
*初始化时间: {timestamp}*
""", encoding="utf-8")

        # Clean up old server files
        server_file = test_dir / "server_message.txt"
        if server_file.exists():
            server_file.unlink()

        return str(test_dir)

    except Exception as e:
        console.print(f"[bold red]✗ 初始化失败:[/bold red] {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]退出中...[/yellow]")
        sys.exit(0)
