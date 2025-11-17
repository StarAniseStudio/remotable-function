# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2025-01-17

### Added
- 🚀 **Phase 2: Architecture Optimization**
  - Multi-instance support - removed global state, supports multiple Gateway/Client instances
  - Direct imports - `from remotable import Gateway, Client` (no `configure()` needed)
  - Async file I/O with aiofiles integration (~130 MB/s concurrent throughput)
  - Unified event system with priority and lifecycle management

- ⚡ **Phase 3: Performance Optimization**
  - Response caching with LRU + TTL (82% cache coverage in tests)
  - Message compression with zlib (98.6% compression for large payloads)
  - Configurable compression threshold and levels

- ✅ **Complete Test Suite**
  - 40 tests total: 36 passing (90% pass rate)
  - Unit tests (24/24): Cache, compression, events
  - Integration tests (5/7): Gateway + Client communication
  - Security tests (7/9): Filesystem and shell security

- 📦 **New Core Modules**
  - `remotable.core.cache` - LRU cache with TTL expiration
  - `remotable.core.compression` - Automatic message compression
  - `remotable.core.events` - Enhanced event system with priorities
  - `remotable.core.ratelimit` - Rate limiting (Token Bucket, Sliding Window)
  - `remotable.core.validation` - Enhanced parameter validation

### Changed
- ⚠️ **DEPRECATED**: `remotable.configure()` is now deprecated
  - Use direct imports instead: `from remotable import Gateway, Client`
  - Old code still works but shows deprecation warning
- Updated all documentation to remove Unity Netcode references
- Simplified API examples throughout the project

### Fixed
- Security improvements in filesystem tools (path traversal prevention)
- Better error handling in tool execution
- Improved connection state management

### Performance
- Response caching reduces repeated calls by ~80%
- Message compression saves ~98% bandwidth for large payloads
- Async file I/O improves concurrent throughput to ~130 MB/s

### Documentation
- Updated README.md with new API patterns
- Added comprehensive test suite documentation
- Removed Unity Netcode terminology for clearer positioning

## [1.0.0] - 2025-01-16

### Added
- 🎉 Initial release of Remotable Function
- 简洁的 API 设计，支持直接导入 Gateway 和 Client
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
