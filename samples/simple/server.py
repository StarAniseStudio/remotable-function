#!/usr/bin/env python3
"""
Remotable - Simple Server Example

Shows how to start a server with the new simplified API.
"""

import asyncio
import sys
import os

# Add remotable_function to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import remotable_function


async def main():
    """Start a simple Remotable server."""

    # Method 1: Quickest way (2 lines)
    print("Starting server on port 8000...")
    server = await remotable_function.start_server(port=8000)
    print("✅ Server is running at ws://localhost:8000")
    print("Waiting for clients to connect...")

    # Keep server running
    await asyncio.Event().wait()


async def main_with_auth():
    """Start a server with authentication."""

    # Method 2: With authentication
    server = await remotable_function.start_server(
        port=8000,
        auth_token="my-secret-key"
    )
    print("✅ Secure server running (auth required)")

    # Keep server running
    await asyncio.Event().wait()


async def main_with_config():
    """Start a server with custom configuration."""

    # Method 3: Using configuration object
    from remotable_function import Gateway, GatewayConfig

    config = GatewayConfig.production()  # Production-ready settings
    gateway = Gateway(config)
    await gateway.start()

    print("✅ Production server running with:")
    print("  - Authentication: enabled")
    print("  - Rate limiting: enabled")
    print("  - Caching: enabled")
    print("  - Compression: enabled")

    # Keep server running
    await asyncio.Event().wait()


if __name__ == "__main__":
    # Run the simple version
    asyncio.run(main())

    # Or run with auth:
    # asyncio.run(main_with_auth())

    # Or run production config:
    # asyncio.run(main_with_config())