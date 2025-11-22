# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-11-22

### 🎉 Major Release - Unified and Simplified

This is a major release that unifies the codebase and dramatically simplifies the API while maintaining full backward compatibility.

### Added
- ✨ **Unified Implementation**: Single `gateway.py` and `client.py` replacing dual implementations
- 🎯 **Event System**: Built-in event callbacks using `@gateway.on()` and `@client.on()` decorators
- 🔧 **Flexible Configuration**: Three ways to configure - config objects, parameters, or smart defaults
- 🚀 **Quick Start Functions**: `start_server()` and `connect_client()` for 2-line setup

### Changed
- 📉 **62.5% Code Reduction**: Core code reduced from ~4000 to ~1500 lines
- 🎯 **Simpler API**: Server starts in 2 lines (was 3), client in 3 lines (was 4)
- 📦 **Cleaner Structure**: Advanced features moved to `remotable.advanced` package
- 🔄 **Better Defaults**: Zero-config operation with smart defaults

### Removed
- 🗑️ Deleted `gateway_simple.py` and `client_simple.py` (redundant implementations)
- 🗑️ Removed 600+ lines of duplicate code
- 🗑️ Eliminated 6 over-engineered modules (moved to examples or removed)

### Migration Guide
```python
# v1.x code works without changes!
gateway = Gateway(host="0.0.0.0", port=8000, auth_token="secret")  # Still works

# But v2.0 way is cleaner:
config = GatewayConfig.production()
gateway = Gateway(config)

# Or even simpler:
server = await start_server(port=8000, auth_token="secret")
```

### Performance
- ⚡ Faster startup time (fewer imports)
- 💾 Lower memory usage (no duplicate code paths)
- 🚄 Unified code path reduces branching overhead


## [1.0.0] - 2025-01-16

### Added
- 🎉 Initial release of Remotable Function
- Server-side Gateway for managing client connections
- Client-side RPC client with auto-reconnection
- JSON-RPC 2.0 protocol implementation
- WebSocket-based bidirectional communication
- Built-in tools:
  - `filesystem.read_file` - Read files
  - `filesystem.write_file` - Write files
  - `filesystem.list_directory` - List directories
  - `filesystem.delete` - Delete files/directories
  - `shell.execute` - Execute shell commands
- Event system with decorator-based callbacks
- Heartbeat mechanism (30s interval, 60s timeout)
- Tool registry with O(1) lookup
- Automatic client reconnection with exponential backoff
- Type hints and py.typed support
- Comprehensive documentation
- Basic demo and Agent integration demo

### Features
- 🚀 Simple and intuitive API
- ⚡ Asynchronous I/O based on asyncio
- 🔄 Automatic reconnection
- 💪 Type-safe with full type hints
- 📦 Zero dependencies (except websockets)
- 🛠️ Extensible tool system
- 📡 Event-driven architecture

### Documentation
- Complete README with quick start guide
- API documentation
- Demo examples
- Agent integration example


[1.0.0]: https://github.com/StarAniseStudio/remotable-function/releases/tag/v1.0.0
