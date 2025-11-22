#!/usr/bin/env python3
"""
Remotable v2.0 - Client Example

Shows the unified API of Remotable v2.0.
"""

import asyncio

# Add remotable_function to path
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import remotable_function
from datetime import datetime


# Example custom tools
class TimeTool(remotable_function.Tool):
    """Get current time in various formats."""
    name = "time"
    description = "Get current time in various formats"
    namespace = "utility"

    async def execute(self, context, format: str = "iso") -> str:
        now = datetime.now()
        formats = {
            "iso": now.isoformat(),
            "human": now.strftime("%Y-%m-%d %H:%M:%S"),
            "unix": str(int(now.timestamp())),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S")
        }
        return formats.get(format, now.isoformat())


class MathTool(remotable_function.Tool):
    """Perform mathematical operations."""
    name = "math"
    description = "Perform mathematical operations"
    namespace = "utility"

    async def execute(self, context, expression: str) -> float:
        # Safe evaluation of math expressions
        import ast
        import operator as op

        # Supported operators
        operators = {
            ast.Add: op.add,
            ast.Sub: op.sub,
            ast.Mult: op.mul,
            ast.Div: op.truediv,
            ast.Pow: op.pow,
            ast.USub: op.neg
        }

        def eval_expr(node):
            if isinstance(node, ast.Num):
                return node.n
            elif isinstance(node, ast.BinOp):
                return operators[type(node.op)](
                    eval_expr(node.left),
                    eval_expr(node.right)
                )
            elif isinstance(node, ast.UnaryOp):
                return operators[type(node.op)](eval_expr(node.operand))
            else:
                raise TypeError(f"Unsupported type {node}")

        node = ast.parse(expression, mode='eval')
        return eval_expr(node.body)


async def quick_start():
    """Quickest way to connect - 3 lines!"""
    print("Connecting client (quickest way)...")

    client = await remotable_function.connect_client(
        "ws://localhost:8000",
        tools=[TimeTool(), MathTool()]
    )

    print("✅ Client connected with tools!")
    await client.wait_closed()


async def with_config():
    """Client with full configuration."""
    from remotable_function import Client, ClientConfig

    config = ClientConfig(
        server_url="ws://localhost:8000",
        client_id="my-client-v2",
        auto_reconnect=True
    )

    client = remotable_function.Client(config)
    client.register_tool(TimeTool())
    client.register_tool(MathTool())
    client.register_tool(remotable_function.FileSystemTool())
    client.register_tool(remotable_function.ShellTool())

    await client.connect()

    print("✅ Client connected with configuration:")
    print(f"  - Client ID: {config.client_id}")
    print(f"  - Auto-reconnect: {config.auto_reconnect}")
    print(f"  - Tools: {client.list_tools()}")

    await client.wait_closed()


async def backward_compatible():
    """Backward compatible with v1.x API."""
    # Old-style parameters still work
    client = remotable_function.Client(
        server_url="ws://localhost:8000",
        client_id="compat-client",
        auth_token="secret",
        auto_reconnect=True
    )

    client.register_tool(TimeTool())
    await client.connect()

    print("✅ Client connected (v1.x style API)")

    await client.wait_closed()


async def with_events():
    """Client with event callbacks."""
    client = remotable_function.create_client("ws://localhost:8000")

    # Register event callbacks
    @client.on("connected")
    async def on_connected():
        print("🔌 Connected to server!")

    @client.on("tool_executed")
    async def on_tool(tool, args, result):
        print(f"🔧 Executed {tool}: {result}")

    @client.on("disconnected")
    async def on_disconnected():
        print("🔌 Disconnected from server!")

    client.register_tool(TimeTool())
    client.register_tool(MathTool())

    await client.connect()
    print("✅ Client with events connected")

    await client.wait_closed()


async def minimal():
    """Absolute minimum client."""
    # Just built-in tools
    client = await remotable_function.connect_client("ws://localhost:8000")
    print("✅ Minimal client connected")
    await client.wait_closed()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == "config":
            asyncio.run(with_config())
        elif mode == "compat":
            asyncio.run(backward_compatible())
        elif mode == "events":
            asyncio.run(with_events())
        elif mode == "minimal":
            asyncio.run(minimal())
        else:
            print(f"Unknown mode: {mode}")
    else:
        # Default: quick start
        asyncio.run(quick_start())