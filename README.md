# Remotable Function

**Simple and efficient RPC framework for AI agents**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-2.0.0-green.svg)](https://github.com/StarAniseStudio/remotable-function)

---

## What is Remotable Function?

Remotable Function is a **lightweight RPC framework** that makes it easy for servers to call tools on remote clients, perfect for AI agents that need to execute code, access files, or run commands on user machines.

### Architecture

```
┌─────────────────┐     WebSocket + JSON-RPC 2.0     ┌─────────────────┐
│   Gateway       │ ◄─────────────────────────────► │   Client        │
│   (Server)      │                                  │                 │
│                 │  1. Client registers tools       │  Tools:         │
│  await call_tool│ ◄── register: [read, write, ...] │  - FileSystem   │
│                 │                                  │  - Shell        │
│                 │  2. Gateway calls tool           │  - Custom       │
│  "read_file"    │ ──► execute: read_file          │                 │
│                 │ ◄── result: "file content"       │  execute()      │
└─────────────────┘                                  └─────────────────┘
```

---

## ✨ Key Features

### 🚀 Dead Simple - 2 Lines to Start

```python
# Server
import remotable_function
server = await remotable_function.start_server(port=8000)

# Client
import remotable_function
client = await remotable_function.connect_client("ws://localhost:8000")
```

### 🔧 Built-in Tools

Ready-to-use tools for common operations:

- **FileSystemTool** - Read, write, list files safely
- **ShellTool** - Execute commands with control

### 🎯 Easy to Extend

```python
class MyTool(remotable_function.Tool):
    name = "my_tool"

    async def execute(self, **kwargs):
        return {"result": "success"}
```

### ⚡ Production Ready

- **Authentication** - Token-based auth
- **Compression** - Automatic message compression
- **Caching** - Response caching with TTL
- **Rate Limiting** - Protect against abuse
- **Auto-reconnect** - Handle network issues
- **TLS/SSL** - Secure connections

---

## Installation

```bash
pip install remotable-function
```

Or install from source:

```bash
git clone https://github.com/StarAniseStudio/remotable-function.git
cd remotable-function
pip install -e .
```

---

## Quick Start

### Basic Example

**Server (Gateway):**

```python
import remotable_function
import asyncio

async def main():
    # Start server
    gateway = await remotable_function.start_server(port=8000)
    print("Server running on ws://localhost:8000")

    # List connected clients
    clients = gateway.list_clients()
    print(f"Connected clients: {clients}")

    # Call a tool on client
    if clients:
        client_id = list(clients.keys())[0]
        result = await gateway.call_tool(
            client_id=client_id,
            tool="read_file",
            args={"path": "/tmp/test.txt"}
        )
        print(f"File content: {result}")

    await asyncio.Event().wait()

asyncio.run(main())
```

**Client:**

```python
import remotable_function
import asyncio

async def main():
    # Connect with built-in tools
    client = await remotable_function.connect_client(
        "ws://localhost:8000",
        tools=[
            remotable_function.FileSystemTool(),
            remotable_function.ShellTool()
        ]
    )
    print("Client connected with tools")

    # Keep running
    await client.wait_closed()

asyncio.run(main())
```

---

## Advanced Usage

### Configuration

Use configuration objects for production settings:

```python
from remotable_function import Gateway, GatewayConfig

# Production configuration
config = GatewayConfig.production()
gateway = Gateway(config)
await gateway.start()

# This automatically enables:
# ✅ Authentication required
# ✅ Rate limiting (100 req/min)
# ✅ Response caching
# ✅ Message compression
# ✅ Size limits (10MB)
```

### Custom Tools

Create your own tools:

```python
from remotable_function import Tool

class DatabaseTool(Tool):
    """Query database tool."""
    name = "database"

    def __init__(self, connection_string):
        self.db = connect(connection_string)

    async def execute(self, query: str, **kwargs):
        return await self.db.execute(query)

# Register on client
client.register_tool(DatabaseTool("postgres://..."))
```

### Event System

React to events:

```python
# Server events
@gateway.on("client_connected")
def on_connect(client_id, tools):
    print(f"Client {client_id} connected with {len(tools)} tools")

@gateway.on("tool_called")
def on_tool_call(client_id, tool, args, result):
    print(f"Called {tool} on {client_id}: {result}")

# Client events
@client.on("connected")
async def on_connected():
    print("Connected to server!")

@client.on("tool_executed")
async def on_execute(tool, args, result):
    print(f"Executed {tool}: {result}")
```

### Authentication

Secure your connections:

```python
# Server with auth
server = await remotable_function.start_server(
    port=8000,
    auth_token="secret-key"
)

# Client with auth
client = await remotable_function.connect_client(
    "ws://localhost:8000",
    auth_token="secret-key"
)
```

### TLS/SSL Support

For production environments:

```python
# Server with SSL
gateway = remotable_function.Gateway(
    host="0.0.0.0",
    port=8000,
    ssl_certfile="/path/to/cert.pem",
    ssl_keyfile="/path/to/key.pem"
)

# Client connecting to wss://
client = remotable_function.Client(
    server_url="wss://example.com:8000",
    verify_ssl=True  # Default
)
```

---

## Real-World Example: AI Agent Integration

```python
# Server: AI Agent with tool execution
import remotable_function
import openai

class AIAgent:
    def __init__(self, gateway):
        self.gateway = gateway
        self.llm = openai.Client()

    async def process_request(self, user_request: str, client_id: str):
        # AI decides what tool to use
        response = self.llm.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": user_request}],
            tools=[...] # Tool descriptions
        )

        # Execute tool on client
        if response.tool_calls:
            tool_call = response.tool_calls[0]
            result = await self.gateway.call_tool(
                client_id=client_id,
                tool=tool_call.function.name,
                args=json.loads(tool_call.function.arguments)
            )

            # Process result
            return f"Executed {tool_call.function.name}: {result}"

# Start agent server
async def main():
    gateway = await remotable_function.start_server(port=8000)
    agent = AIAgent(gateway)

    # Handle user requests
    @gateway.on("client_connected")
    async def on_client(client_id, tools):
        result = await agent.process_request(
            "Read the config.json file",
            client_id
        )
        print(result)
```

---

## Performance

### v2.0 Improvements

- **62.5% less code** - From ~4000 to ~1500 lines
- **Unified implementation** - Single code path, less overhead
- **Smart caching** - ~80% reduction in repeated calls
- **Message compression** - ~98% bandwidth savings for large payloads
- **Async I/O** - ~130 MB/s concurrent throughput

### Benchmarks

| Operation | Latency | Throughput |
|-----------|---------|------------|
| Tool call (local) | <10ms | 100/s |
| Tool call (remote) | <50ms | 20/s |
| File read (1MB) | <100ms | 10 MB/s |
| File read (async) | <100ms | 130 MB/s |

---

## API Reference

### Gateway (Server)

```python
# Create and start
gateway = Gateway(config)
await gateway.start()

# Call tools
result = await gateway.call_tool(client_id, tool, args, timeout=30)

# List resources
clients = gateway.list_clients()
tools = gateway.list_tools(client_id)

# Events
gateway.on(event, callback)
```

### Client

```python
# Create and connect
client = Client(config)
client.register_tool(tool)
await client.connect()

# Properties
client.is_connected
client.list_tools()

# Events
client.on(event, callback)
```

### Tool

```python
class MyTool(Tool):
    name = "tool_name"

    async def execute(self, **kwargs):
        return result
```

---

## Examples

Check out the `/samples/` directory:

- `simple/` - Basic examples showing all patterns
- `demo/` - Full-featured demo application
- `agent_demo/` - AI agent integration example

---

## Testing

```bash
# Run all tests
./run_tests.sh

# Run specific tests
pytest tests/unit/
pytest tests/integration/
pytest tests/security/

# With coverage
pytest --cov=remotable
```

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## FAQ

**Q: How is this different from other RPC frameworks?**

A: Remotable Function is specifically designed for AI agents to call tools on remote clients. It's simpler than gRPC, more focused than JSON-RPC libraries, and includes built-in tools for common operations.

**Q: Is it production-ready?**

A: Yes! v2.0 is stable and includes authentication, rate limiting, caching, compression, and comprehensive error handling. Many teams use it in production.

**Q: Can I use it without AI/LLMs?**

A: Absolutely! While designed with AI agents in mind, Remotable Function is a general-purpose RPC framework suitable for any server-client tool execution scenario.

**Q: What about security?**

A: Remotable Function includes authentication, TLS support, rate limiting, path traversal prevention, command filtering, and message size limits. Always review security practices for your use case.

---

## Support

- 📖 [Documentation](https://github.com/StarAniseStudio/remotable-function/wiki)
- 🐛 [Issue Tracker](https://github.com/StarAniseStudio/remotable-function/issues)
- 💬 [Discussions](https://github.com/StarAniseStudio/remotable-function/discussions)

---

**Built with ❤️ for the AI agent community**