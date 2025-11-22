#!/usr/bin/env python3
"""
Remotable Function AI Agent Server

服务器端主程序：
- 启动 Remotable Function Gateway（管理客户端连接）
- 启动 AI Agent（处理用户请求）
- 提供交互界面
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Load .env file if exists
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import remotable_function

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich import box
from rich.markdown import Markdown

# Import Agent
from agent import RemotableAgent

console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# Suppress verbose logs from httpx and agno
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("agno").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("remotable").setLevel(logging.INFO)
logging.getLogger("websockets").setLevel(logging.WARNING)


async def main():
    """Main server function."""

    # Print banner
    console.print()
    console.print(Panel.fit(
        "[bold magenta]Remotable Function AI Agent Server[/bold magenta]\n"
        "[dim]Agent + Gateway 一体化服务[/dim]",
        border_style="magenta",
        box=box.DOUBLE
    ))
    console.print()

    # Check API key (optional for simple mode)
    has_api_key = bool(os.getenv("OPENAI_API_KEY"))
    if not has_api_key:
        console.print("[yellow]⚠️  未设置 OPENAI_API_KEY[/yellow]")
        console.print("[dim]将使用简化模式（基于关键词匹配）[/dim]\n")

    # Create Gateway
    console.print("[bold yellow]🚀 创建 Remotable Function Gateway[/bold yellow]")
    gateway = remotable_function.Gateway(
        host="0.0.0.0",
        port=8000,
        heartbeat_interval=30,
        heartbeat_timeout=60
    )
    console.print("[green]✓[/green] Gateway 创建成功\n")

    # Register Gateway event handlers
    @gateway.on_client_connected
    async def on_client_connected(client_id: str, client_info):
        """Handle client connection."""
        console.print()
        console.print(Panel(
            f"[bold cyan]客户端ID:[/bold cyan] {client_id}\n"
            f"[cyan]平台:[/cyan] {client_info.platform}\n"
            f"[cyan]工具数量:[/cyan] {len(gateway.list_tools(client_id=client_id))}",
            title="[bold green]✓ 客户端已连接[/bold green]",
            border_style="green"
        ))

    @gateway.on_client_disconnected
    async def on_client_disconnected(client_id: str):
        """Handle client disconnection."""
        console.print(f"\n[bold red]✗ 客户端断开连接:[/bold red] {client_id}\n")

    # Start Gateway
    console.print("[bold yellow]🌐 启动 Gateway 服务器[/bold yellow]")
    await gateway.start()
    console.print(f"[green]✓[/green] Gateway 运行在 [cyan]ws://0.0.0.0:8000[/cyan]\n")

    # Wait for client to connect
    console.print("[yellow]⏳ 等待客户端连接...[/yellow]")
    console.print("[dim]请在另一个终端运行: cd client && python main.py[/dim]\n")

    # Wait for at least one client
    for i in range(30):  # Wait up to 30 seconds
        await asyncio.sleep(1)
        clients = gateway.manager.list_clients()
        if clients:
            client_id = list(clients.keys())[0]
            console.print(f"[green]✓[/green] 客户端已连接: [cyan]{client_id}[/cyan]\n")
            break
    else:
        console.print("[yellow]⚠️  没有客户端连接[/yellow]")
        console.print("[dim]Agent 将继续运行，等待客户端连接[/dim]\n")
        client_id = None

    # Create AI Agent
    console.print("[bold yellow]🤖 创建 AI Agent[/bold yellow]")
    agent = RemotableAgent(
        gateway=gateway,
        client_id=client_id or "unknown",  # Will use first connected client
        use_llm=has_api_key
    )
    console.print("[green]✓[/green] Agent 创建成功\n")

    # Display capabilities
    console.print(Panel(
        "[bold cyan]Agent 能力:[/bold cyan]\n\n"
        "📖 文件操作:\n"
        "  • read_file - 读取文件\n"
        "  • write_file - 写入文件\n"
        "  • list_directory - 列出目录\n"
        "  • delete_file - 删除文件\n\n"
        "🖥️  Shell 操作:\n"
        "  • execute_shell - 执行命令\n\n"
        "💻 系统信息:\n"
        "  • get_system_info - 获取系统信息",
        title="[bold]🎯 可用工具[/bold]",
        border_style="cyan"
    ))
    console.print()

    # Interactive loop
    console.print("[bold green]💬 开始对话[/bold green]")
    console.print("[dim]输入 'quit' 或 'exit' 退出，输入 'help' 查看帮助[/dim]\n")

    while True:
        try:
            # Check if we have a connected client
            clients = gateway.manager.list_clients()
            if clients and not client_id:
                client_id = list(clients.keys())[0]
                agent.client_id = client_id
                console.print(f"[green]✓[/green] 使用客户端: [cyan]{client_id}[/cyan]\n")

            # Get user input (run in thread to avoid blocking event loop)
            user_message = await asyncio.to_thread(
                Prompt.ask, "\n[bold cyan]You[/bold cyan]"
            )

            # Check for exit
            if user_message.lower() in ["quit", "exit", "q", "退出"]:
                console.print("\n[yellow]再见！[/yellow]\n")
                break

            # Process command
            console.print("\n[bold magenta]Agent[/bold magenta]:")
            try:
                # Check client connection before processing
                if not clients:
                    console.print("[yellow]⚠️  没有客户端连接，无法执行工具调用[/yellow]")
                    continue

                response = await agent.process(user_message)

                if agent.use_llm:
                    # LLM response is markdown
                    console.print(Markdown(response))
                else:
                    # Simple response is plain text
                    console.print(response)

            except Exception as e:
                console.print(f"[bold red]错误:[/bold red] {e}")
                # Re-check clients after error
                clients = gateway.manager.list_clients()
                if not clients:
                    console.print("[yellow]提示:[/yellow] 客户端已断开，请重新连接 client")

        except KeyboardInterrupt:
            console.print("\n\n[yellow]正在退出...[/yellow]\n")
            break
        except EOFError:
            console.print("\n\n[yellow]再见！[/yellow]\n")
            break

    # Cleanup
    console.print("[yellow]正在关闭服务器...[/yellow]")
    await gateway.stop()
    console.print("[green]✓ 服务器已停止[/green]\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]退出中...[/yellow]")
        sys.exit(0)
