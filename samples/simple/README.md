# Remotable - Simple Examples

These examples demonstrate the new simplified API of Remotable v1.0.

## Quick Start (3 Terminal Windows)

### Terminal 1: Start Server
```bash
python server.py
```

### Terminal 2: Connect Client
```bash
python client.py
```

### Terminal 3: Test Tools
```bash
python test_tools.py
```

## What's New in v1.0?

### Simplified Server (2 lines!)
```python
import remotable
server = await remotable.start_server(port=8000)
```

### Simplified Client (3 lines!)
```python
import remotable
client = await remotable.connect_client("ws://localhost:8000",
                                        tools=[remotable.FileSystemTool()])
```

### No More configure()
The old `remotable.configure(role="server")` is no longer needed!

## Examples Included

1. **server.py** - Three ways to start a server:
   - Quick start (2 lines)
   - With authentication
   - With production config

2. **client.py** - Three ways to connect clients:
   - Standard with custom tools
   - Simplest with built-in tools only
   - With authentication

3. **test_tools.py** - Interactive tool tester:
   - List connected clients
   - Browse available tools
   - Execute tools with custom arguments
   - See results in real-time

## Custom Tools

Creating custom tools is easy:

```python
class MyTool(remotable.Tool):
    name = "my_tool"

    async def execute(self, **kwargs):
        # Tool logic here
        return result
```

## Authentication

Add authentication with one parameter:

```python
# Server
server = await remotable.start_server(port=8000, auth_token="secret")

# Client
client = await remotable.connect_client("ws://localhost:8000", auth_token="secret")
```

## Production Configuration

Use pre-configured production settings:

```python
from remotable import Gateway, GatewayConfig

config = GatewayConfig.production()
gateway = Gateway(config)
await gateway.start()
```

This enables:
- ✅ Authentication required
- ✅ Rate limiting (100 req/min)
- ✅ Response caching
- ✅ Message compression
- ✅ Size limits (10MB)

## Built-in Tools

Remotable includes two production-ready tools:

- **FileSystemTool** - Safe file operations
- **ShellTool** - Controlled command execution

## Need the Old Examples?

The original examples using `remotable.configure()` are in:
- `samples/demo/` - Basic demo
- `samples/agent_demo/` - AI agent integration

These still work but use the deprecated API. We recommend using the new simplified API shown here.