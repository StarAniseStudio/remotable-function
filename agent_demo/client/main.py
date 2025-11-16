#!/usr/bin/env python3
"""
Remotable Client for AI Agent Demo

这个客户端提供工具给 AI Agent 使用。
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path to import remotable
sys.path.insert(0, str(Path(__file__).parent.parent))

import remotable
remotable.configure(role="client")

from remotable.client.tools import (
    ReadFileTool,
    WriteFileTool,
    ListDirectoryTool,
    DeleteFileTool,
    ShellExecuteTool,
)
from remotable.client.tool import Tool
from remotable.core.types import ToolContext, ParameterSchema, ParameterType

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)
logging.getLogger("remotable").setLevel(logging.INFO)


# Custom Tool: System Info
class SystemInfoTool(Tool):
    """获取系统和用户信息的工具"""

    name = "get_system_info"
    description = "获取本机的系统信息和用户信息"
    namespace = "system"
    permissions = ["system.read"]
    tags = ["system", "info"]

    parameters = []  # 不需要参数

    async def execute(self, context: ToolContext, **kwargs) -> dict:
        """获取系统和用户信息"""
        import platform
        import os
        import getpass
        import socket

        try:
            # System info
            system_info = {
                "system": platform.system(),
                "node": platform.node(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
            }

            # User info
            user_info = {
                "username": getpass.getuser(),
                "home_dir": os.path.expanduser("~"),
                "current_dir": os.getcwd(),
            }

            # Network info
            hostname = socket.gethostname()
            try:
                ip_address = socket.gethostbyname(hostname)
            except:
                ip_address = "N/A"

            network_info = {
                "hostname": hostname,
                "ip_address": ip_address,
            }

            # Environment info
            env_info = {
                "shell": os.environ.get("SHELL", "N/A"),
                "terminal": os.environ.get("TERM", "N/A"),
                "lang": os.environ.get("LANG", "N/A"),
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


async def main():
    """Main client function."""

    # Print banner
    console.clear()
    console.print(Panel.fit(
        "[bold green]Remotable Client - Tool Provider[/bold green]\n"
        "[dim]为 AI Agent 提供远程工具[/dim]",
        border_style="green",
        box=box.DOUBLE
    ))
    console.print()

    # Create Client
    console.print("[bold yellow]🚀 创建客户端实例[/bold yellow]")
    client = remotable.Client(
        server_url="ws://localhost:8000",
        client_id="ai-agent-tools",
        version="1.0.0",
        auto_reconnect=True,
        reconnect_interval=5,
        reconnect_max_attempts=10
    )
    console.print("[green]✓[/green] 客户端创建成功\n")

    # Register tools
    console.print("[bold yellow]🔧 注册工具[/bold yellow]")
    tools = [
        ReadFileTool(),
        WriteFileTool(),
        ListDirectoryTool(),
        DeleteFileTool(),
        ShellExecuteTool(),
        SystemInfoTool(),
    ]
    client.register_tools(*tools)
    console.print(f"[green]✓[/green] 已注册 {len(tools)} 个工具\n")

    # Register event handlers
    @client.on_connected
    async def on_connected():
        """Handle connection."""
        console.print()
        console.print(Panel(
            "[bold green]✓ 已连接到 Gateway[/bold green]\n\n"
            f"[cyan]客户端ID:[/cyan] {client.client_id}\n"
            f"[cyan]已注册工具:[/cyan] {len(client.list_tools())}",
            title="[bold]连接成功[/bold]",
            border_style="green"
        ))

        # Show tools table
        table = Table(title="可用工具", box=box.ROUNDED)
        table.add_column("工具名称", style="cyan")
        table.add_column("命名空间", style="yellow")

        for tool_name in client.list_tools():
            namespace, name = tool_name.split('.')
            table.add_row(tool_name, namespace)

        console.print(table)
        console.print()
        console.print("[dim]等待 AI Agent 调用工具...[/dim]\n")

    @client.on_disconnected
    async def on_disconnected():
        """Handle disconnection."""
        console.print("\n[bold red]✗ 已断开连接[/bold red]\n")

    @client.on_tool_executed
    async def on_tool_executed(tool_name: str, result):
        """Handle tool execution."""
        console.print(f"[green]✓[/green] 工具已执行: [cyan]{tool_name}[/cyan]")

    # Connect to Gateway
    console.print("[bold yellow]🔗 连接到 Gateway[/bold yellow]")
    try:
        await client.connect()
    except Exception as e:
        console.print(f"[bold red]✗ 连接失败:[/bold red] {e}")
        console.print("\n[yellow]提示:[/yellow] 请确保 Gateway 已启动 (运行 gateway.py)\n")
        return

    # Keep running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        console.print("\n[yellow]正在关闭客户端...[/yellow]")
        await client.disconnect()
        console.print("[green]✓ 客户端已停止[/green]\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]退出中...[/yellow]")
        sys.exit(0)
