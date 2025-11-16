#!/usr/bin/env python3
"""
Remotable Server Demo - Enhanced UI Version

这是一个增强版的服务器demo，使用 rich 库提供更美观的命令行输出。
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# Configure Remotable as server
import remotable
remotable.configure(role="server")

# Rich console for beautiful output
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich import box
from rich.tree import Tree

console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# 只显示 INFO 及以上级别
logging.getLogger("remotable").setLevel(logging.INFO)
logging.getLogger("websockets").setLevel(logging.WARNING)


async def main():
    """Main server function with enhanced UI."""

    # Print banner
    console.clear()
    console.print(Panel.fit(
        "[bold magenta]Remotable Server Demo[/bold magenta]\n"
        "[dim]Unity Netcode Style RPC Gateway[/dim]",
        border_style="magenta",
        box=box.DOUBLE
    ))
    console.print()

    # Create Gateway
    console.print("[bold yellow]🚀 创建 RPC Gateway[/bold yellow]")
    gateway = remotable.Gateway(
        host="0.0.0.0",
        port=8000,
        heartbeat_interval=30,
        heartbeat_timeout=60
    )
    console.print("[green]✓[/green] Gateway 创建成功\n")

    # Track connected clients
    _client_tools = {}

    # Register event handlers
    @gateway.on_client_connected
    async def on_client_connected(client_id: str, client_info):
        """Handle client connection."""
        console.print()
        console.print(Panel(
            f"[bold cyan]客户端ID:[/bold cyan] {client_id}\n"
            f"[cyan]平台:[/cyan] {client_info.platform}\n"
            f"[cyan]版本:[/cyan] {client_info.version}\n"
            f"[cyan]能力:[/cyan] {', '.join(client_info.capabilities)}",
            title="[bold green]✓ 客户端已连接[/bold green]",
            border_style="green"
        ))
        _client_tools[client_id] = []

    @gateway.on_client_disconnected
    async def on_client_disconnected(client_id: str):
        """Handle client disconnection."""
        console.print(f"\n[bold red]✗ 客户端断开连接:[/bold red] {client_id}\n")

    @gateway.on_tool_registered
    async def on_tool_registered(client_id: str, tool_name: str):
        """Handle tool registration."""
        if client_id not in _client_tools:
            _client_tools[client_id] = []
        _client_tools[client_id].append(tool_name)

        # When all tools are registered (assuming 6 tools)
        if len(_client_tools[client_id]) == 6:
            # Show tools table
            table = Table(title=f"客户端工具列表 ({client_id})", box=box.ROUNDED)
            table.add_column("工具名称", style="cyan", no_wrap=True)
            table.add_column("命名空间", style="yellow")

            tools = gateway.list_tools(client_id=client_id)
            for tool in tools:
                namespace, name = tool.full_name.split('.')
                table.add_row(tool.full_name, namespace)

            console.print(table)
            console.print()

            # Start demo asynchronously (don't block the registration callback)
            asyncio.create_task(demo_tool_calls_enhanced(gateway, client_id))

    # Start Gateway
    console.print("[bold yellow]🌐 启动 Gateway 服务器[/bold yellow]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("正在启动服务器...", total=None)
        await gateway.start()
        progress.update(task, completed=True)

    console.print(f"[green]✓[/green] Gateway 运行在 [cyan]ws://0.0.0.0:8000[/cyan]\n")
    console.print("[dim]等待客户端连接...[/dim]\n")

    # Keep running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        console.print("\n[yellow]正在关闭服务器...[/yellow]")
        await gateway.stop()
        console.print("[green]✓ Gateway 已停止[/green]\n")


async def demo_tool_calls_enhanced(gateway, client_id: str):
    """
    Enhanced demo with beautiful progress tracking and output.
    """
    from pathlib import Path

    # Get demo directory path
    # Use resolve() to get absolute path first
    demo_dir = Path(__file__).resolve().parent.parent
    test_dir = demo_dir / "test_files"
    client_file = test_dir / "client_data.txt"
    server_file = test_dir / "server_message.txt"

    console.print()
    console.print(Panel.fit(
        "[bold]远程工具调用演示[/bold]\n\n"
        f"[cyan]测试目录:[/cyan] {test_dir}\n"
        "[dim]打开该目录中的文件，实时查看远程操作效果！[/dim]",
        border_style="magenta",
        title="🎯 DEMO"
    ))
    console.print()

    # Demo steps
    steps = [
        ("读取文件", "📖"),
        ("创建文件", "✍️"),
        ("修改文件", "📝"),
        ("列出目录", "📂"),
        ("执行命令", "🖥️"),
        ("系统信息", "💻"),
    ]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:

        main_task = progress.add_task("[cyan]执行演示步骤...", total=len(steps))

        # Step 1: Read file
        step_task = progress.add_task(f"{steps[0][1]} {steps[0][0]}", total=1)
        try:
            result = await gateway.call_tool(
                client_id=client_id,
                tool="filesystem.read_file",
                args={"path": str(client_file)},
                timeout=10
            )
            progress.update(step_task, completed=1)
            progress.update(main_task, advance=1)

            console.print(Panel(
                f"[green]✓ 文件读取成功[/green]\n\n"
                f"[cyan]大小:[/cyan] {result['size']} bytes\n"
                f"[cyan]路径:[/cyan] {client_file}\n\n"
                "[dim]内容预览:[/dim]\n" +
                "\n".join(f"  {line}" for line in result['content'].split('\n')[:3]) + "\n  ...",
                title=f"{steps[0][1]} {steps[0][0]}",
                border_style="green"
            ))

        except Exception as e:
            progress.update(step_task, completed=1)
            progress.update(main_task, advance=1)
            # Don't show error - file might not exist yet
            console.print(f"[yellow]⚠️  {steps[0][0]}跳过 (文件不存在)[/yellow]")

        # Step 2: Write file
        step_task = progress.add_task(f"{steps[1][1]} {steps[1][0]}", total=1)
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            server_content = f"""{'=' * 60}
Remotable Demo - 服务器远程创建的文件
{'=' * 60}

这个文件由服务器远程创建！

服务器信息：
  - 操作时间: {timestamp}
  - 客户端ID: {client_id}
  - 操作类型: 远程文件写入

这证明了 Remotable 的核心功能：
服务器端代码可以在客户端机器上创建和修改文件！

{'=' * 60}
"""

            result = await gateway.call_tool(
                client_id=client_id,
                tool="filesystem.write_file",
                args={
                    "path": str(server_file),
                    "content": server_content
                },
                timeout=10
            )
            progress.update(step_task, completed=1)
            progress.update(main_task, advance=1)

            console.print(Panel(
                f"[green]✓ 文件创建成功[/green]\n\n"
                f"[cyan]路径:[/cyan] {server_file}\n"
                f"[cyan]大小:[/cyan] {result['size']} bytes",
                title=f"{steps[1][1]} {steps[1][0]}",
                border_style="green"
            ))

        except Exception as e:
            progress.update(step_task, completed=1)
            progress.update(main_task, advance=1)
            console.print(f"[red]✗ {steps[1][0]}失败: {e}[/red]")

        # Step 3: Append to file
        step_task = progress.add_task(f"{steps[2][1]} {steps[2][0]}", total=1)
        try:
            result = await gateway.call_tool(
                client_id=client_id,
                tool="filesystem.read_file",
                args={"path": str(client_file)},
                timeout=10
            )
            original_content = result['content']

            updated_content = original_content + f"""
[服务器操作记录 - {timestamp}]
✓ 服务器已读取此文件
✓ 服务器已创建新文件: server_message.txt
✓ 服务器正在追加此操作记录

👉 这些内容都是服务器远程添加的！
{'=' * 60}
"""

            result = await gateway.call_tool(
                client_id=client_id,
                tool="filesystem.write_file",
                args={
                    "path": str(client_file),
                    "content": updated_content
                },
                timeout=10
            )
            progress.update(step_task, completed=1)
            progress.update(main_task, advance=1)

            console.print(Panel(
                f"[green]✓ 文件修改成功[/green]\n\n"
                f"[cyan]路径:[/cyan] {client_file}\n"
                f"[dim]已追加服务器操作记录[/dim]",
                title=f"{steps[2][1]} {steps[2][0]}",
                border_style="green"
            ))

        except Exception as e:
            progress.update(step_task, completed=1)
            progress.update(main_task, advance=1)
            # Don't show error - file might not exist yet
            console.print(f"[yellow]⚠️  {steps[2][0]}跳过 (文件不存在)[/yellow]")

        # Step 4: List directory
        step_task = progress.add_task(f"{steps[3][1]} {steps[3][0]}", total=1)
        try:
            result = await gateway.call_tool(
                client_id=client_id,
                tool="filesystem.list_directory",
                args={"path": str(test_dir), "recursive": False},
                timeout=10
            )
            progress.update(step_task, completed=1)
            progress.update(main_task, advance=1)

            # Create file tree
            tree = Tree(f"📂 {test_dir}")
            for file_info in result['files']:
                tree.add(f"📄 {file_info['name']} [dim]({file_info['size']} bytes)[/dim]")

            console.print(Panel(
                tree,
                title=f"{steps[3][1]} {steps[3][0]}",
                border_style="green"
            ))

        except Exception as e:
            progress.update(step_task, completed=1)
            progress.update(main_task, advance=1)
            console.print(f"[red]✗ {steps[3][0]}失败: {e}[/red]")

        # Step 5: Execute command
        step_task = progress.add_task(f"{steps[4][1]} {steps[4][0]}", total=1)
        try:
            result = await gateway.call_tool(
                client_id=client_id,
                tool="shell.execute",
                args={"command": f"ls -lh {test_dir}"},
                timeout=10
            )
            progress.update(step_task, completed=1)
            progress.update(main_task, advance=1)

            console.print(Panel(
                f"[green]✓ 命令执行成功[/green]\n\n"
                f"[cyan]命令:[/cyan] ls -lh {test_dir}\n"
                f"[cyan]返回码:[/cyan] {result['returncode']}\n\n"
                "[dim]输出:[/dim]\n" +
                "\n".join(f"  {line}" for line in result['stdout'].strip().split('\n')),
                title=f"{steps[4][1]} {steps[4][0]}",
                border_style="green"
            ))

        except Exception as e:
            progress.update(step_task, completed=1)
            progress.update(main_task, advance=1)
            console.print(f"[red]✗ {steps[4][0]}失败: {e}[/red]")

        # Step 6: Get system info
        step_task = progress.add_task(f"{steps[5][1]} {steps[5][0]}", total=1)
        try:
            result = await gateway.call_tool(
                client_id=client_id,
                tool="system.get_system_info",
                args={},
                timeout=10
            )
            progress.update(step_task, completed=1)
            progress.update(main_task, advance=1)

            # Format system info
            sys_info = result.get('system', {})
            user_info = result.get('user', {})
            net_info = result.get('network', {})
            env_info = result.get('environment', {})

            info_text = f"[green]✓ 系统信息获取成功[/green]\n\n"
            info_text += "[bold cyan]系统信息:[/bold cyan]\n"
            info_text += f"  操作系统: {sys_info.get('system', 'N/A')}\n"
            info_text += f"  主机名: {sys_info.get('node', 'N/A')}\n"
            info_text += f"  版本: {sys_info.get('release', 'N/A')}\n"
            info_text += f"  架构: {sys_info.get('machine', 'N/A')}\n"
            info_text += f"  Python: {sys_info.get('python_version', 'N/A')}\n\n"

            info_text += "[bold cyan]用户信息:[/bold cyan]\n"
            info_text += f"  用户名: {user_info.get('username', 'N/A')}\n"
            info_text += f"  主目录: {user_info.get('home_dir', 'N/A')}\n"
            info_text += f"  当前目录: {user_info.get('current_dir', 'N/A')}\n\n"

            info_text += "[bold cyan]网络信息:[/bold cyan]\n"
            info_text += f"  主机: {net_info.get('hostname', 'N/A')}\n"
            info_text += f"  IP地址: {net_info.get('ip_address', 'N/A')}\n\n"

            info_text += "[bold cyan]环境信息:[/bold cyan]\n"
            info_text += f"  Shell: {env_info.get('shell', 'N/A')}\n"
            info_text += f"  终端: {env_info.get('terminal', 'N/A')}\n"
            info_text += f"  语言: {env_info.get('lang', 'N/A')}"

            console.print(Panel(
                info_text,
                title=f"{steps[5][1]} {steps[5][0]}",
                border_style="green"
            ))

        except Exception as e:
            progress.update(step_task, completed=1)
            progress.update(main_task, advance=1)
            console.print(f"[red]✗ {steps[5][0]}失败: {e}[/red]")

    # Final summary
    console.print()
    console.print(Panel.fit(
        "[bold green]✅ 演示完成！[/bold green]\n\n"
        f"[cyan]📁 查看结果:[/cyan] {test_dir}\n\n"
        "你会看到：\n"
        "  • [green]client_data.txt[/green] - 已被服务器修改\n"
        "  • [green]server_message.txt[/green] - 服务器创建的新文件\n"
        "  • [green]README.md[/green] - 说明文档",
        border_style="green",
        title="🎉 DEMO 完成"
    ))
    console.print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]退出中...[/yellow]")
        sys.exit(0)
