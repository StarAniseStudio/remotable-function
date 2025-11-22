#!/usr/bin/env python3
"""
Remotable - Test Tool Calls

Shows how to call tools from the server side.
Run this after starting server.py and client.py.
"""

import asyncio

# Add remotable_function to path
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import remotable_function


async def test_tools():
    """Test calling tools on connected clients."""

    # Connect to the gateway (assuming it's already running)
    from remotable_function import Gateway

    # Note: In a real scenario, you'd get the gateway instance
    # from your server. This is just for testing.
    print("Testing tool calls...")
    print("\nNote: Make sure server.py and client.py are already running!")

    # For testing, we need to connect as another client to get the gateway reference
    # In production, you'd have direct access to the gateway instance

    # Create a simple test setup
    gateway = remotable_function.create_gateway(port=8000)

    # List connected clients
    clients = gateway.list_clients()
    print(f"\nConnected clients: {list(clients.keys())}")

    if not clients:
        print("❌ No clients connected. Please run client.py first.")
        return

    # Get first client ID
    client_id = list(clients.keys())[0]
    print(f"\nTesting with client: {client_id}")

    # Test greeting tool
    try:
        result = await gateway.call_tool(
            client_id=client_id,
            tool="greet",
            args={"name": "Remotable"}
        )
        print(f"✅ Greeting result: {result}")
    except Exception as e:
        print(f"❌ Greeting failed: {e}")

    # Test calculator tool
    try:
        result = await gateway.call_tool(
            client_id=client_id,
            tool="calculate",
            args={"operation": "multiply", "a": 7, "b": 6}
        )
        print(f"✅ Calculator result: 7 * 6 = {result}")
    except Exception as e:
        print(f"❌ Calculator failed: {e}")

    # Test filesystem tool (safe operation)
    try:
        result = await gateway.call_tool(
            client_id=client_id,
            tool="list_directory",
            args={"path": "/tmp"}
        )
        print(f"✅ Directory listing: {len(result)} items in /tmp")
    except Exception as e:
        print(f"❌ Filesystem operation failed: {e}")


async def interactive_test():
    """Interactive tool testing."""

    print("Remotable Interactive Tool Tester")
    print("=" * 40)

    gateway = remotable_function.create_gateway(port=8000)

    while True:
        # List clients
        clients = gateway.list_clients()
        if not clients:
            print("\n❌ No clients connected. Waiting...")
            await asyncio.sleep(2)
            continue

        print("\nConnected clients:")
        for i, (cid, info) in enumerate(clients.items(), 1):
            tools = info.get('tools', [])
            print(f"  {i}. {cid}: {len(tools)} tools")

        # Get user input
        try:
            client_num = input("\nSelect client number (or 'q' to quit): ")
            if client_num.lower() == 'q':
                break

            client_id = list(clients.keys())[int(client_num) - 1]

            # List tools
            tools = gateway.list_tools().get(client_id, [])
            print(f"\nAvailable tools for {client_id}:")
            for tool in tools:
                print(f"  - {tool['name']}: {tool.get('description', 'No description')}")

            tool_name = input("\nEnter tool name: ")

            # Simple argument input (in production, use proper JSON)
            args_str = input("Enter arguments as key=value pairs (comma-separated): ")
            args = {}
            if args_str:
                for pair in args_str.split(','):
                    if '=' in pair:
                        k, v = pair.split('=', 1)
                        # Try to parse as number
                        try:
                            v = float(v)
                            if v.is_integer():
                                v = int(v)
                        except:
                            pass
                        args[k.strip()] = v

            # Call tool
            print(f"\nCalling {tool_name} with args: {args}")
            result = await gateway.call_tool(
                client_id=client_id,
                tool=tool_name,
                args=args,
                timeout=30
            )

            print(f"✅ Result: {result}")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ Error: {e}")

    print("\nGoodbye!")


if __name__ == "__main__":
    # Run simple test
    # asyncio.run(test_tools())

    # Or run interactive test
    asyncio.run(interactive_test())