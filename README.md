# Remotable Function

**轻量级 RPC 通信组件 - 让服务器调用客户端工具像本地函数一样简单**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 这是什么？

Remotable Function 是一个**纯粹的 RPC 通信组件**，解决一个核心问题：

> 如何让服务器端代码方便地调用客户端工具？

### 架构

```
┌─────────────────┐     WebSocket + JSON-RPC 2.0     ┌─────────────────┐
│   Server 端      │ ◄─────────────────────────────► │   Client 端      │
│                 │                                  │                 │
│  你的代码        │  1. Client 注册工具               │  Remotable       │
│  (Agent/API/    │ ◄── tools: [read, write, ...]   │  Client          │
│   脚本/...)     │                                  │  + 工具          │
│                 │  2. Server 调用工具               │                 │
│  call_tool()    │ ──► execute: read_file           │  Tool.execute() │
│                 │ ◄── result: {content: "..."}    │                 │
└─────────────────┘                                  └─────────────────┘
```

### 定位

**Remotable Function 是：**
- ✅ RPC 通信组件（WebSocket + JSON-RPC 2.0）
- ✅ 工具调用框架（服务器调用客户端工具）
- ✅ 轻量级设计（单包，简单配置）

**Remotable Function 不是：**
- ❌ AI Agent 框架（不包含 LLM、任务规划）
- ❌ Web 应用（不包含前端 UI）
- ❌ 完整的开发平台

**Remotable Function 是通信层，需要在此基础上构建你的应用。**

---

## 核心特性

### 1. 简单直观的工具调用

```python
# 服务器端调用客户端工具
result = await gateway.call_tool(
    client_id="client-1",
    tool="filesystem.read_file",
    args={"path": "/tmp/test.txt"}
)
print(result['content'])
```

### 2. 内置工具

客户端提供 5 个开箱即用的工具：

- **filesystem.read_file** - 读取文件
- **filesystem.write_file** - 写入文件
- **filesystem.list_directory** - 列出目录
- **filesystem.delete** - 删除文件/目录
- **shell.execute** - 执行命令

### 3. 易于扩展

```python
from remotable.client.tool import Tool

class MyTool(Tool):
    name = "my_tool"
    description = "My custom tool"
    namespace = "custom"

    async def execute(self, context, **kwargs):
        return {"result": "success"}
```

### 4. 事件系统

```python
@gateway.on_client_connected
async def on_connected(client_id, client_info):
    print(f"Client {client_id} connected")

@client.on_tool_executed
async def on_executed(tool_name, result):
    print(f"Tool {tool_name} executed")
```

### 5. 性能优化 (v1.3.0+)

- **响应缓存**: LRU + TTL 缓存，减少重复调用 ~80%
- **消息压缩**: 自动 zlib 压缩，大型负载节省 ~98% 带宽
- **异步 I/O**: aiofiles 集成，并发吞吐量 ~130 MB/s

```python
from remotable import Gateway
from remotable.core.cache import ResponseCache
from remotable.core.compression import MessageCompressor

# 启用响应缓存
cache = ResponseCache(max_size=1000, default_ttl=60.0)
gateway = Gateway(host="0.0.0.0", port=8000, response_cache=cache)

# 启用消息压缩
compressor = MessageCompressor(threshold=1024, level=6)
```

---

## 快速开始

### 安装

```bash
# 基础安装
pip install websockets

# 完整安装（包含性能优化）
pip install websockets aiofiles
```

### 运行 Demo

**终端 1 - 服务器:**
```bash
cd demo/server
python main.py
```

**终端 2 - 客户端:**
```bash
cd demo/client
python main.py
```

服务器会自动调用客户端的 5 个工具并展示结果！

### 服务器端示例

```python
from remotable import Gateway
import asyncio

async def main():
    # 创建 Gateway
    gateway = Gateway(host="0.0.0.0", port=8000)

    @gateway.on_client_connected
    async def on_connected(client_id, client_info):
        # 调用客户端工具
        result = await gateway.call_tool(
            client_id=client_id,
            tool="filesystem.read_file",
            args={"path": "/tmp/test.txt"}
        )
        print(f"Content: {result['content']}")

    await gateway.start()
    print("Gateway started on ws://0.0.0.0:8000")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
```

### 客户端示例

```python
from remotable import Client
from remotable.client.tools.filesystem import ReadFileTool, WriteFileTool
import asyncio

async def main():
    # 创建 Client
    client = Client(
        server_url="ws://localhost:8000",
        client_id="my-client"
    )

    # 注册工具
    client.register_tools(ReadFileTool(), WriteFileTool())

    await client.connect()
    print("Client connected")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 项目结构

```
remotable/                   # 核心包
├── __init__.py             # 包入口
├── core/                   # 共享组件
│   ├── protocol.py         # JSON-RPC 2.0
│   ├── types.py            # 类型定义
│   ├── registry.py         # 工具注册表
│   ├── cache.py            # 响应缓存 (v1.3.0+)
│   ├── compression.py      # 消息压缩 (v1.3.0+)
│   ├── events.py           # 事件系统 (v1.3.0+)
│   ├── ratelimit.py        # 速率限制 (v1.3.0+)
│   └── validation.py       # 参数验证 (v1.3.0+)
├── server/                 # 服务器端
│   ├── gateway.py          # RPC Gateway
│   └── manager.py          # 连接管理
└── client/                 # 客户端
    ├── client.py           # RPC Client
    ├── tool.py             # Tool 基类
    └── tools/              # 内置工具
        ├── filesystem.py   # 文件系统工具
        └── shell.py        # Shell 工具

tests/                      # 测试套件 (v1.3.0+)
├── unit/                   # 单元测试
├── integration/            # 集成测试
├── security/               # 安全测试
└── conftest.py            # pytest 配置

demo/                       # 基础示例
├── server/main.py          # 服务器示例
└── client/main.py          # 客户端示例

agent_demo/                 # AI Agent 集成示例
├── server/                 # AI Agent + Gateway
└── client/                 # 工具提供者
```

---

## 核心组件

### Gateway (Server)

**职责:** 接受客户端连接，调用远程工具

```python
gateway = remotable.Gateway(host, port)
await gateway.start()
await gateway.call_tool(client_id, tool, args)
gateway.list_clients()
gateway.list_tools(client_id)
```

**事件:**
- `@gateway.on_client_connected`
- `@gateway.on_client_disconnected`
- `@gateway.on_tool_registered`

### Client (Client)

**职责:** 连接服务器，注册和执行工具

```python
client = remotable.Client(server_url, client_id)
client.register_tool(tool)
client.register_tools(*tools)
await client.connect()
await client.disconnect()
```

**事件:**
- `@client.on_connected`
- `@client.on_disconnected`
- `@client.on_tool_executed`
- `@client.on_error`

### Tool (Client)

**职责:** 定义可被远程调用的工具

```python
from remotable.client.tool import Tool
from remotable.core.types import ToolContext, ParameterSchema, ParameterType

class MyTool(Tool):
    name = "my_tool"
    description = "My custom tool"
    namespace = "custom"

    parameters = [
        ParameterSchema(
            name="arg1",
            type=ParameterType.STRING,
            description="First argument",
            required=True
        )
    ]

    async def execute(self, context: ToolContext, **kwargs):
        arg1 = kwargs["arg1"]
        return {"result": f"Processed: {arg1}"}
```

---

## 技术细节

### 协议
- **JSON-RPC 2.0** - 标准 RPC 协议
- **WebSocket** - 全双工实时通信
- **心跳机制** - 30s 间隔，60s 超时
- **TLS/SSL 加密** - 支持 wss:// 加密连接

### 性能
- **O(1) 查找** - 工具注册表多索引
- **异步 I/O** - 基于 asyncio
- **自动重连** - 指数退避

### 可靠性
- **超时控制** - 工具调用超时
- **错误处理** - 完整异常处理
- **状态追踪** - 连接状态管理

### 测试覆盖 (v1.3.0+)
- **40 个测试**: 36 通过 (90% 通过率)
- **单元测试**: Cache, Compression, Events (24/24)
- **集成测试**: Gateway + Client 通信 (5/7)
- **安全测试**: 文件系统和 Shell 安全 (7/9)

```bash
# 运行所有测试
./run_tests.sh

# 运行特定测试
./run_tests.sh unit          # 单元测试
./run_tests.sh integration   # 集成测试
./run_tests.sh security      # 安全测试
./run_tests.sh coverage      # 带覆盖率报告
```

### TLS/SSL 加密

Remotable Function 支持 TLS/SSL 加密通信，保护数据传输安全。

#### 客户端使用 wss://

客户端会自动检测 `wss://` URL 并启用 TLS 加密：

```python
# 自动启用 TLS（验证服务器证书）
client = remotable.Client(server_url="wss://example.com:8000")
await client.connect()

# 禁用证书验证（开发/测试环境）
client = remotable.Client(
    server_url="wss://localhost:8000",
    verify_ssl=False  # 仅用于开发！
)
await client.connect()

# 使用自定义 SSL context
import ssl
ssl_context = ssl.create_default_context()
ssl_context.load_verify_locations(cafile="/path/to/ca.pem")

client = remotable.Client(
    server_url="wss://example.com:8000",
    ssl_context=ssl_context
)
await client.connect()
```

#### 服务器端配置 SSL

服务器端需要提供 SSL 证书和私钥：

```python
# 使用证书文件
gateway = remotable.Gateway(
    host="0.0.0.0",
    port=8000,
    ssl_certfile="/path/to/cert.pem",
    ssl_keyfile="/path/to/key.pem"
)
await gateway.start()  # 启动为 wss://0.0.0.0:8000

# 使用自定义 SSL context
import ssl
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain(
    certfile="/path/to/cert.pem",
    keyfile="/path/to/key.pem"
)

gateway = remotable.Gateway(
    host="0.0.0.0",
    port=8000,
    ssl_context=ssl_context
)
await gateway.start()
```

#### 生成自签名证书（开发环境）

```bash
# 生成私钥
openssl genrsa -out key.pem 2048

# 生成自签名证书（有效期 365 天）
openssl req -new -x509 -key key.pem -out cert.pem -days 365 \
    -subj "/C=CN/ST=State/L=City/O=Org/CN=localhost"
```

#### 使用场景

**开发环境：**
- 使用自签名证书
- 客户端禁用证书验证 (`verify_ssl=False`)

**生产环境：**
- 使用受信任的 CA 签发证书（如 Let's Encrypt）
- 客户端启用证书验证（默认）
- 使用域名而非 IP 地址

---

## 使用场景

### 1. AI Agent 远程工具

```python
# 服务器端 - AI Agent
async def agent_task():
    # 读取客户端文件
    content = await gateway.call_tool(
        client_id="laptop",
        tool="filesystem.read_file",
        args={"path": "/project/main.py"}
    )

    # AI 分析...
    analysis = await llm.analyze(content)

    # 写入结果
    await gateway.call_tool(
        client_id="laptop",
        tool="filesystem.write_file",
        args={"path": "/project/analysis.txt", "content": analysis}
    )
```

### 2. 自动化运维

```python
# 服务器端 - 运维脚本
async def deploy(client_id):
    # 停止服务
    await gateway.call_tool(
        client_id, "shell.execute",
        {"command": "systemctl stop myapp"}
    )

    # 更新代码
    await gateway.call_tool(
        client_id, "filesystem.write_file",
        {"path": "/app/main.py", "content": new_code}
    )

    # 启动服务
    await gateway.call_tool(
        client_id, "shell.execute",
        {"command": "systemctl start myapp"}
    )
```

### 3. 远程管理

```python
# 服务器端 - 管理平台
async def get_info(client_id):
    system = await gateway.call_tool(
        client_id, "shell.execute",
        {"command": "uname -a"}
    )

    disk = await gateway.call_tool(
        client_id, "shell.execute",
        {"command": "df -h"}
    )

    return {"system": system, "disk": disk}
```

---

## 文档

- [README.md](README.md) - 本文档（快速开始）
- [CHANGELOG.md](CHANGELOG.md) - 版本变更历史
- [demo/README.md](demo/README.md) - 基础示例
- [agent_demo/README.md](agent_demo/README.md) - AI Agent 集成示例
- [TEST_SUITE.md](TEST_SUITE.md) - 测试套件文档
- [docs/api/SINGLE_PACKAGE_GUIDE.md](docs/api/SINGLE_PACKAGE_GUIDE.md) - 完整 API 文档

---

## 设计理念

### 1. 保持简单

Remotable Function 只做一件事：**让服务器调用客户端工具**

不包含：
- ❌ AI/LLM 功能
- ❌ 任务调度
- ❌ Web UI
- ❌ 数据库
- ❌ 认证授权（可由用户实现）

### 2. 易于扩展

- 工具系统 - 继承 `Tool` 类
- 事件系统 - 装饰器注册
- 协议扩展 - 基于 JSON-RPC 2.0

---

## 常见问题

**Q: Remotable Function 包含 AI Agent 吗？**

A: 不包含。Remotable Function 只是 RPC 通信组件。需要自己集成 LLM（参考 `agent_demo/`）。

**Q: 需要 Web 前端吗？**

A: 不需要。Remotable Function 是纯后端组件，不涉及 UI。

**Q: 如何添加认证？**

A: 在 Gateway 中添加认证逻辑：

```python
@gateway.on_client_connected
async def on_connected(client_id, client_info):
    if not verify_token(client_info.metadata.get("token")):
        await gateway.disconnect_client(client_id)
```

**Q: 性能如何？**

A: (v1.3.0+ 性能显著提升)
- 工具查找：O(1)
- 单次调用延迟：< 10ms (本地网络)
- 响应缓存：减少重复调用 ~80%
- 消息压缩：大型负载节省 ~98% 带宽
- 异步 I/O：并发吞吐量 ~130 MB/s
- 并发连接：受限于系统资源

**Q: 可以用于生产环境吗？**

A: 核心功能稳定，但建议添加：
- 认证授权
- 日志监控
- 错误恢复
- 负载均衡

---

## 技术栈

**核心依赖:**
- **Python 3.8+**
- **asyncio** - 异步 I/O
- **websockets** - WebSocket 通信
- **dataclasses** - 数据结构
- **typing** - 类型提示

**可选依赖 (v1.3.0+):**
- **aiofiles** - 异步文件 I/O (性能优化)
- **pytest** - 测试框架
- **pytest-asyncio** - 异步测试支持
- **pytest-cov** - 测试覆盖率

---

## 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

**Remotable Function - 让远程工具调用像本地函数一样简单** 🚀
