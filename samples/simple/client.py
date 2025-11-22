#!/usr/bin/env python3
"""
Remotable - Simple Client Example

Shows how to connect a client with tools using the new simplified API.
"""

import asyncio

# Add remotable_function to path
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import remotable_function
from datetime import datetime


# Define custom tools
class GreetingTool(remotable_function.Tool):
    """A simple greeting tool."""
    name = "greet"

    async def execute(self, name: str = "World") -> str:
        """Greet someone by name."""
        return f"Hello, {name}! The time is {datetime.now().strftime('%H:%M:%S')}"


class CalculatorTool(remotable_function.Tool):
    """A simple calculator tool."""
    name = "calculate"

    async def execute(self, operation: str, a: float, b: float) -> float:
        """Perform basic math operations."""
        operations = {
            "add": a + b,
            "subtract": a - b,
            "multiply": a * b,
            "divide": a / b if b != 0 else float('inf')
        }
        return operations.get(operation, 0)


async def main():
    """Connect a simple client with tools."""

    # Method 1: Quick connect with tools
    print("Connecting to server...")
    client = remotable_function.create_client("ws://localhost:8000")

    # Register custom tools
    client.register_tool(GreetingTool())
    client.register_tool(CalculatorTool())

    # Register built-in tools
    client.register_tool(remotable_function.FileSystemTool())
    client.register_tool(remotable_function.ShellTool())

    # Connect
    await client.connect()
    print("✅ Connected with 4 tools registered!")
    print("  - greet: Send greetings")
    print("  - calculate: Basic math")
    print("  - filesystem: File operations")
    print("  - shell: Execute commands")

    # Keep client running
    await client.wait_closed()


async def main_simple():
    """Simplest possible client - just built-in tools."""

    # Even simpler - one-liner setup
    client = await remotable_function.connect_client(
        "ws://localhost:8000",
        tools=[
            remotable_function.FileSystemTool(),
            remotable_function.ShellTool()
        ]
    )
    print("✅ Client connected with built-in tools!")

    # Keep running
    await asyncio.Event().wait()


async def main_with_auth():
    """Connect with authentication."""

    client = remotable_function.create_client(
        "ws://localhost:8000",
        auth_token="my-secret-key"
    )

    client.register_tool(GreetingTool())
    await client.connect()

    print("✅ Securely connected with auth!")

    await client.wait_closed()


if __name__ == "__main__":
    # Run the standard version
    asyncio.run(main())

    # Or run the simplest version:
    # asyncio.run(main_simple())

    # Or run with auth:
    # asyncio.run(main_with_auth())