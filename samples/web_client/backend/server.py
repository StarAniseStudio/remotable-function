#!/usr/bin/env python3
"""
Remotable Function - Web Client Demo Backend

Python Gateway that provides demo tools for JavaScript frontend to call.
"""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path

# Add remotable_function to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import remotable_function


# Custom demo tool: Get current server time
class GetTimeTool(remotable_function.Tool):
    """Get current server time in various formats"""

    name = "get_time"
    description = "Get current server time"
    namespace = "demo"

    async def execute(self, context, format: str = "iso"):
        """
        Get current time from server.

        Args:
            format: Time format (iso, unix, human)

        Returns:
            Current time in requested format
        """
        now = datetime.now()

        formats = {
            "iso": now.isoformat(),
            "unix": int(now.timestamp()),
            "human": now.strftime("%Y-%m-%d %H:%M:%S"),
            "detailed": {
                "year": now.year,
                "month": now.month,
                "day": now.day,
                "hour": now.hour,
                "minute": now.minute,
                "second": now.second
            }
        }

        return {
            "time": formats.get(format, now.isoformat()),
            "timezone": "UTC",
            "timestamp": int(now.timestamp())
        }


# Custom demo tool: Calculate math expressions
class CalculateTool(remotable_function.Tool):
    """Safe calculator for basic math operations"""

    name = "calculate"
    description = "Calculate math expressions safely"
    namespace = "demo"

    async def execute(self, context, expression: str):
        """
        Calculate a math expression.

        Args:
            expression: Math expression to evaluate (e.g., "2 + 2", "10 * 5")

        Returns:
            Calculation result
        """
        try:
            # Safe evaluation of math expressions
            # Only allow numbers and basic operators
            allowed_chars = set('0123456789+-*/.() ')
            if not all(c in allowed_chars for c in expression):
                raise ValueError("Expression contains invalid characters")

            result = eval(expression, {"__builtins__": {}}, {})

            return {
                "expression": expression,
                "result": result,
                "type": type(result).__name__
            }
        except Exception as e:
            return {
                "error": str(e),
                "expression": expression
            }


# Custom demo tool: Echo message back
class EchoTool(remotable_function.Tool):
    """Echo back the message"""

    name = "echo"
    description = "Echo back any message"
    namespace = "demo"

    async def execute(self, context, message: str, uppercase: bool = False):
        """
        Echo a message back.

        Args:
            message: Message to echo
            uppercase: Convert to uppercase

        Returns:
            Echoed message
        """
        result = message.upper() if uppercase else message

        return {
            "original": message,
            "echoed": result,
            "length": len(message),
            "uppercase_applied": uppercase
        }


async def main():
    """Main server function."""

    print("=" * 60)
    print("Remotable Function - Web Client Demo")
    print("=" * 60)
    print()
    print("Python Gateway providing tools for JavaScript frontend")
    print()

    # Create Gateway with custom tools
    print("🚀 Creating Gateway...")
    gateway = remotable_function.Gateway(
        host="0.0.0.0",
        port=8765,
        enable_compression=False  # Disable for easier debugging
    )

    # Create server-side tools
    server_tools = {
        "demo.get_time": GetTimeTool(),
        "demo.calculate": CalculateTool(),
        "demo.echo": EchoTool()
    }

    # Store tools on gateway for execution
    gateway._server_tools = server_tools

    print("✓ Gateway created")
    print("✓ Registered 3 server-side tools")
    print()

    # Event handlers
    def on_client_connected(client_id: str, tools: list):
        """Handle client connection."""
        tool_names = [tool.get("name", "unknown") if isinstance(tool, dict) else str(tool) for tool in tools]
        print(f"✓ JavaScript client connected: {client_id}")
        print(f"  Tools from client: {len(tools)}")
        for tool_name in tool_names:
            print(f"    - {tool_name}")
        print()

        # Start demo after client connects
        asyncio.create_task(demo_interaction(gateway, client_id))

    def on_client_disconnected(client_id: str):
        """Handle client disconnection."""
        print(f"✗ Client disconnected: {client_id}")
        print()

    def on_tool_called(client_id: str, tool: str, args: dict, result):
        """Handle tool calls."""
        print(f"📞 Tool called: {tool}")
        print(f"   Args: {args}")
        print(f"   Result: {result}")
        print()

    # Register event handlers
    gateway.on("client_connected", on_client_connected)
    gateway.on("client_disconnected", on_client_disconnected)
    gateway.on("tool_called", on_tool_called)

    # Start Gateway
    print("🌐 Starting Gateway server...")
    await gateway.start()

    print("✓ Gateway running at ws://localhost:8765")
    print()
    print("📱 Open frontend/index.html in your browser to connect")
    print()
    print("Available Python tools for JavaScript to call:")
    print("  - demo.get_time: Get current server time")
    print("  - demo.calculate: Calculate math expressions")
    print("  - demo.echo: Echo messages back")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 60)
    print()

    # Keep running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down server...")
        await gateway.stop()
        print("✓ Gateway stopped")


async def demo_interaction(gateway, client_id: str):
    """
    Demo interaction: Gateway calls JavaScript client tools.
    """
    await asyncio.sleep(2)  # Wait for client to be ready

    print()
    print("=" * 60)
    print("🎯 Demo: Gateway calling JavaScript tools")
    print("=" * 60)
    print()

    # Call JavaScript tool: show_notification
    try:
        print("Calling browser.show_notification...")
        result = await gateway.call_tool(
            client_id=client_id,
            tool="browser.show_notification",
            args={
                "title": "Hello from Python!",
                "message": "This notification was triggered by the Python backend!",
                "type": "success"
            },
            timeout=5
        )
        print(f"✓ Notification result: {result}")
        print()
    except Exception as e:
        print(f"✗ Failed to call show_notification: {e}")
        print()

    await asyncio.sleep(2)

    # Call JavaScript tool: update_dom
    try:
        print("Calling browser.update_dom...")
        result = await gateway.call_tool(
            client_id=client_id,
            tool="browser.update_dom",
            args={
                "selector": "#server-message",
                "content": f"Server says: Connection successful! Time: {datetime.now().strftime('%H:%M:%S')}"
            },
            timeout=5
        )
        print(f"✓ DOM update result: {result}")
        print()
    except Exception as e:
        print(f"✗ Failed to update DOM: {e}")
        print()

    await asyncio.sleep(2)

    # Call JavaScript tool: get_browser_info
    try:
        print("Calling browser.get_info...")
        result = await gateway.call_tool(
            client_id=client_id,
            tool="browser.get_info",
            args={},
            timeout=5
        )
        print(f"✓ Browser info received:")
        print(f"   User Agent: {result.get('userAgent', 'N/A')}")
        print(f"   Language: {result.get('language', 'N/A')}")
        print(f"   Platform: {result.get('platform', 'N/A')}")
        print(f"   Screen: {result.get('screen', 'N/A')}")
        print()
    except Exception as e:
        print(f"✗ Failed to get browser info: {e}")
        print()

    print("=" * 60)
    print("🎉 Demo interaction completed!")
    print("=" * 60)
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
