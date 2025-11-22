#!/usr/bin/env python3
"""
Remotable v2.0 - Server Example

Shows the unified API of Remotable v2.0.
"""

import asyncio

# Add remotable_function to path
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import remotable_function


async def quick_start():
    """Quickest way to start a server - 2 lines!"""
    print("Starting server (quickest way)...")
    server = await remotable_function.start_server(port=8000)
    print("✅ Server is running at ws://localhost:8000")

    await asyncio.Event().wait()


async def with_auth():
    """Server with authentication."""
    server = await remotable_function.start_server(
        port=8000,
        auth_token="my-secret-key"
    )
    print("✅ Secure server running (auth required)")

    await asyncio.Event().wait()


async def with_config():
    """Server with full configuration."""
    from remotable_function import Gateway, GatewayConfig

    # Use production configuration preset
    config = GatewayConfig.production()
    config.network.port = 8000
    config.security.auth_token = "production-key"

    gateway = remotable_function.Gateway(config)
    await gateway.start()

    print("✅ Production server running with:")
    print("  - Authentication: enabled")
    print("  - Rate limiting: enabled")
    print("  - Caching: enabled")
    print("  - Compression: enabled")

    await gateway.wait_closed()


async def backward_compatible():
    """Backward compatible with v1.x API."""
    # Old-style parameters still work
    gateway = remotable_function.Gateway(
        host="localhost",
        port=8000,
        auth_token="secret",
        enable_cache=True,
        enable_compression=True
    )
    await gateway.start()

    print("✅ Server running (v1.x style API)")

    await gateway.wait_closed()


async def with_events():
    """Server with event callbacks."""
    gateway = remotable_function.create_gateway(port=8000)

    # Register event callbacks
    @gateway.on("client_connected")
    def on_client(client_id, tools):
        print(f"📌 Client connected: {client_id} with {len(tools)} tools")

    @gateway.on("tool_called")
    def on_tool(client_id, tool, args, result):
        print(f"🔧 Tool called: {tool} on {client_id}")

    await gateway.start()
    print("✅ Server with events running")

    await gateway.wait_closed()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == "auth":
            asyncio.run(with_auth())
        elif mode == "config":
            asyncio.run(with_config())
        elif mode == "compat":
            asyncio.run(backward_compatible())
        elif mode == "events":
            asyncio.run(with_events())
        else:
            print(f"Unknown mode: {mode}")
    else:
        # Default: quick start
        asyncio.run(quick_start())