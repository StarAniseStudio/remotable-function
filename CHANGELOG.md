# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-16

### Added
- 🎉 Initial release of Remotable Function
- Unity Netcode style API with `configure(role="server"|"client")`
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
- 🎮 Unity Netcode-inspired design
- 🛠️ Extensible tool system
- 📡 Event-driven architecture

### Documentation
- Complete README with quick start guide
- API documentation
- Demo examples
- Agent integration example


[1.0.0]: https://github.com/StarAniseStudio/remotable-function/releases/tag/v1.0.0
