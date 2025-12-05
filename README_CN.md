# Remotable Function

**为 AI 智能体打造的简单高效 RPC 框架**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-2.0.0-green.svg)](https://github.com/StarAniseStudio/remotable-function)

---

## 什么是 Remotable Function？

Remotable Function 是一个**轻量级 RPC 框架**，让服务器能够轻松调用远程客户端上的工具，特别适合需要在用户机器上执行代码、访问文件或运行命令的 AI 智能体。

### 架构设计

```
┌─────────────────┐     WebSocket + JSON-RPC 2.0     ┌─────────────────┐
│   Gateway       │ ◄─────────────────────────────► │   Client        │
│   (服务器)      │                                  │   (客户端)      │
│                 │  1. 客户端注册工具                │                 │
│  await call_tool│ ◄── 注册: [read, write, ...]     │  工具:          │
│                 │                                  │  - 文件系统     │
│                 │  2. Gateway 调用工具             │  - Shell        │
│  "read_file"    │ ──► 执行: read_file              │  - 自定义       │
│                 │ ◄── 结果: "文件内容"              │                 │
└─────────────────┘                                  └─────────────────┘
```

---

## ✨ 核心特性

### 🚀 极简启动 - 仅需 2 行代码

```python
# 服务器端
import remotable_function
server = await remotable_function.start_server(port=8000)

# 客户端
import remotable_function
client = await remotable_function.connect_client("ws://localhost:8000")
```

### 🔧 内置工具

开箱即用的常用操作工具：

- **FileSystemTool（文件系统工具）** - 安全地读取、写入、列出文件
- **ShellTool（Shell 工具）** - 受控的命令执行

### 🎯 易于扩展

```python
class MyTool(remotable_function.Tool):
    name = "my_tool"

    async def execute(self, **kwargs):
        return {"result": "success"}
```

### ⚡ 生产就绪

- **身份验证** - 基于令牌的认证
- **消息压缩** - 自动压缩消息
- **响应缓存** - 带 TTL 的响应缓存
- **速率限制** - 防止滥用
- **自动重连** - 处理网络问题
- **TLS/SSL** - 安全连接

---

## 安装

```bash
pip install remotable-function
```

或从源码安装：

```bash
git clone https://github.com/StarAniseStudio/remotable-function.git
cd remotable-function
pip install -e .
```

---

## 快速入门

### 基础示例

**服务器端 (Gateway)：**

```python
import remotable_function
import asyncio

async def main():
    # 启动服务器
    gateway = await remotable_function.start_server(port=8000)
    print("服务器运行在 ws://localhost:8000")

    # 列出已连接的客户端
    clients = gateway.list_clients()
    print(f"已连接客户端: {clients}")

    # 调用客户端上的工具
    if clients:
        client_id = list(clients.keys())[0]
        result = await gateway.call_tool(
            client_id=client_id,
            tool="read_file",
            args={"path": "/tmp/test.txt"}
        )
        print(f"文件内容: {result}")

    await asyncio.Event().wait()

asyncio.run(main())
```

**客户端：**

```python
import remotable_function
import asyncio

async def main():
    # 使用内置工具连接
    client = await remotable_function.connect_client(
        "ws://localhost:8000",
        tools=[
            remotable_function.FileSystemTool(),
            remotable_function.ShellTool()
        ]
    )
    print("客户端已连接，工具已注册")

    # 保持运行
    await client.wait_closed()

asyncio.run(main())
```

---

## 高级用法

### 配置选项

使用配置对象进行生产环境设置：

```python
from remotable_function import Gateway, GatewayConfig

# 生产环境配置
config = GatewayConfig.production()
gateway = Gateway(config)
await gateway.start()

# 这会自动启用：
# ✅ 必须身份验证
# ✅ 速率限制（100 请求/分钟）
# ✅ 响应缓存
# ✅ 消息压缩
# ✅ 消息大小限制（10MB）
```

### 自定义工具

创建自己的工具：

```python
from remotable_function import Tool

class DatabaseTool(Tool):
    """数据库查询工具。"""
    name = "database"

    def __init__(self, connection_string):
        self.db = connect(connection_string)

    async def execute(self, query: str, **kwargs):
        return await self.db.execute(query)

# 在客户端注册
client.register_tool(DatabaseTool("postgres://..."))
```

### 事件系统

响应事件：

```python
# 服务器端事件
@gateway.on("client_connected")
def on_connect(client_id, tools):
    print(f"客户端 {client_id} 已连接，工具数量: {len(tools)}")

@gateway.on("tool_called")
def on_tool_call(client_id, tool, args, result):
    print(f"在 {client_id} 上调用 {tool}: {result}")

# 客户端事件
@client.on("connected")
async def on_connected():
    print("已连接到服务器！")

@client.on("tool_executed")
async def on_execute(tool, args, result):
    print(f"执行了 {tool}: {result}")
```

### 身份验证

保护您的连接：

```python
# 带身份验证的服务器
server = await remotable_function.start_server(
    port=8000,
    auth_token="secret-key"
)

# 带身份验证的客户端
client = await remotable_function.connect_client(
    "ws://localhost:8000",
    auth_token="secret-key"
)
```

### TLS/SSL 支持

生产环境配置：

```python
# 带 SSL 的服务器
gateway = remotable_function.Gateway(
    host="0.0.0.0",
    port=8000,
    ssl_certfile="/path/to/cert.pem",
    ssl_keyfile="/path/to/key.pem"
)

# 连接到 wss:// 的客户端
client = remotable_function.Client(
    server_url="wss://example.com:8000",
    verify_ssl=True  # 默认值
)
```

---

## 实际应用示例：AI 智能体集成

```python
# 服务器端：带工具执行的 AI 智能体
import remotable_function
import openai

class AIAgent:
    def __init__(self, gateway):
        self.gateway = gateway
        self.llm = openai.Client()

    async def process_request(self, user_request: str, client_id: str):
        # AI 决定使用哪个工具
        response = self.llm.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": user_request}],
            tools=[...]  # 工具描述
        )

        # 在客户端上执行工具
        if response.tool_calls:
            tool_call = response.tool_calls[0]
            result = await self.gateway.call_tool(
                client_id=client_id,
                tool=tool_call.function.name,
                args=json.loads(tool_call.function.arguments)
            )

            # 处理结果
            return f"执行了 {tool_call.function.name}: {result}"

# 启动智能体服务器
async def main():
    gateway = await remotable_function.start_server(port=8000)
    agent = AIAgent(gateway)

    # 处理用户请求
    @gateway.on("client_connected")
    async def on_client(client_id, tools):
        result = await agent.process_request(
            "读取 config.json 文件",
            client_id
        )
        print(result)
```

---

## 性能表现

### v2.0 改进

- **代码减少 62.5%** - 从约 4000 行减少到约 1500 行
- **统一实现** - 单一代码路径，更少的开销
- **智能缓存** - 重复调用减少约 80%
- **消息压缩** - 大型有效载荷带宽节省约 98%
- **异步 I/O** - 约 130 MB/s 的并发吞吐量

### 基准测试

| 操作 | 延迟 | 吞吐量 |
|------|------|--------|
| 工具调用（本地） | <10ms | 100/秒 |
| 工具调用（远程） | <50ms | 20/秒 |
| 文件读取（1MB） | <100ms | 10 MB/秒 |
| 文件读取（异步） | <100ms | 130 MB/秒 |

---

## API 参考

### Gateway（服务器）

```python
# 创建和启动
gateway = Gateway(config)
await gateway.start()

# 调用工具
result = await gateway.call_tool(client_id, tool, args, timeout=30)

# 列出资源
clients = gateway.list_clients()
tools = gateway.list_tools(client_id)

# 事件
gateway.on(event, callback)
```

### Client（客户端）

```python
# 创建和连接
client = Client(config)
client.register_tool(tool)
await client.connect()

# 属性
client.is_connected
client.list_tools()

# 事件
client.on(event, callback)
```

### Tool（工具）

```python
class MyTool(Tool):
    name = "tool_name"

    async def execute(self, **kwargs):
        return result
```

---

## 示例代码

查看 `/samples/` 目录：

- `simple/` - 展示所有基本模式的简单示例
- `demo/` - 功能完整的演示应用
- `agent_demo/` - AI 智能体集成示例
- `web_client/` - **JavaScript 前端 + Python 后端** 双向通信演示

---

## 测试

```bash
# 运行所有测试
./run_tests.sh

# 运行特定测试
pytest tests/unit/
pytest tests/integration/
pytest tests/security/

# 带覆盖率测试
pytest --cov=remotable
```

---

## 贡献指南

我们欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解指南。

---

## 开源许可

MIT License - 详见 [LICENSE](LICENSE)。

---

## 常见问题

**Q: 这与其他 RPC 框架有什么不同？**

A: Remotable Function 专门为 AI 智能体在远程客户端上调用工具而设计。它比 gRPC 更简单，比 JSON-RPC 库更专注，并且包含常用操作的内置工具。

**Q: 可以用于生产环境吗？**

A: 可以！v2.0 是稳定版本，包含身份验证、速率限制、缓存、压缩和全面的错误处理。许多团队在生产环境中使用它。

**Q: 可以在没有 AI/LLM 的情况下使用吗？**

A: 当然可以！虽然是为 AI 智能体设计的，但 Remotable Function 是一个通用的 RPC 框架，适用于任何服务器-客户端工具执行场景。

**Q: 安全性如何？**

A: Remotable Function 包含身份验证、TLS 支持、速率限制、路径遍历防护、命令过滤和消息大小限制。但请始终根据您的使用场景审查安全实践。

**Q: 支持哪些编程语言？**

A: 服务器端和 Python 客户端是原生支持的。由于使用标准的 WebSocket 和 JSON-RPC 2.0 协议，您可以用任何语言（JavaScript、Go、Rust、Java 等）编写客户端。我们在 `samples/web_client/` 中提供了一个完整的 JavaScript 客户端示例。

---

## 核心特色功能

### 🌐 跨语言客户端支持

Remotable Function 使用标准的 **WebSocket** 和 **JSON-RPC 2.0** 协议，这意味着您可以用任何编程语言编写客户端：

```javascript
// JavaScript 客户端示例
const client = new RemotableClient('ws://localhost:8000');
await client.connect();

// 调用 Python 服务器的工具
const result = await client.callTool('demo.get_time', {
    format: 'iso'
});
```

查看 `samples/web_client/` 获取完整的浏览器端 JavaScript 客户端实现！

### 🔄 双向 RPC 通信

不仅服务器可以调用客户端工具，客户端也可以调用服务器端工具：

```python
# Python 服务器提供工具
class ServerTool(Tool):
    name = "process_data"
    async def execute(self, data):
        return process(data)

# JavaScript 客户端调用
const result = await client.callTool('process_data', {
    data: [1, 2, 3]
});
```

### 🛡️ 企业级安全

```python
# 完整的安全配置
config = GatewayConfig(
    # 身份验证
    auth_token="strong-secret-key",
    require_auth=True,

    # TLS/SSL
    ssl_certfile="/path/to/cert.pem",
    ssl_keyfile="/path/to/key.pem",

    # 速率限制
    rate_limit_enabled=True,
    rate_limit_requests=100,
    rate_limit_window=60,

    # 消息大小限制
    max_message_size=10_000_000,  # 10 MB
)
```

### 📊 监控和日志

```python
# 详细的事件系统
@gateway.on("client_connected")
def on_connect(client_id, tools):
    logger.info(f"新客户端连接: {client_id}, 工具: {tools}")

@gateway.on("tool_called")
def on_tool_call(client_id, tool, args, result):
    metrics.record_tool_call(tool, success=True)

@gateway.on("error")
def on_error(error):
    logger.error(f"错误: {error}")
    alert_team(error)
```

---

## 使用场景

### 1. AI 智能体工具执行

让 AI 模型在用户本地机器上执行操作：

```python
# AI 智能体决定执行文件操作
result = await gateway.call_tool(
    client_id="user-laptop",
    tool="filesystem.read_file",
    args={"path": "~/documents/report.pdf"}
)
```

### 2. 远程运维自动化

集中管理多台服务器：

```python
# 在所有客户端上执行更新
for client_id in gateway.list_clients():
    await gateway.call_tool(
        client_id=client_id,
        tool="shell.execute",
        args={"command": "apt-get update && apt-get upgrade -y"}
    )
```

### 3. IoT 设备控制

从中央服务器控制物联网设备：

```python
# 控制智能家居设备
await gateway.call_tool(
    client_id="bedroom-light",
    tool="set_brightness",
    args={"level": 80}
)
```

### 4. 浏览器端应用

Web 界面与 Python 后端实时交互：

```javascript
// 浏览器调用 Python 数据处理
const result = await client.callTool('analyze_data', {
    dataset: userData
});
updateChart(result);
```

### 5. 分布式任务执行

在多个工作节点上分发任务：

```python
# 分布式数据处理
tasks = split_data(large_dataset)
results = await asyncio.gather(*[
    gateway.call_tool(client_id, "process_chunk", {"data": chunk})
    for client_id, chunk in zip(clients, tasks)
])
```

---

## 架构优势

### 🎯 为什么选择 Remotable Function？

| 特性 | Remotable Function | gRPC | 传统 REST |
|------|-------------------|------|-----------|
| **学习曲线** | 极简（2行代码启动） | 陡峭 | 中等 |
| **双向通信** | ✅ 原生支持 | ❌ 需要额外配置 | ❌ 需要轮询 |
| **实时性** | ✅ WebSocket | ⚠️ 需要流式 | ❌ 请求-响应 |
| **跨语言** | ✅ 任何支持 WebSocket 的语言 | ⚠️ 需要 Protobuf | ✅ 通用 |
| **AI 工具集成** | ✅ 专门设计 | ❌ 需要适配 | ❌ 需要适配 |
| **内置工具** | ✅ 文件系统、Shell | ❌ 无 | ❌ 无 |
| **自动重连** | ✅ 内置 | ❌ 需要实现 | ❌ 需要实现 |

### 📈 性能对比

```python
# Remotable Function - 简单直接
result = await gateway.call_tool("read_file", {"path": "/tmp/data.txt"})

# gRPC - 需要定义 .proto、生成代码、编译
# 1. 编写 file_service.proto
# 2. protoc --python_out=. file_service.proto
# 3. 实现 FileServiceServicer
# 4. 启动 gRPC 服务器
# 5. 创建 stub 并调用

# REST API - 需要 HTTP 服务器、路由等
# 1. 创建 Flask/FastAPI 应用
# 2. 定义路由 @app.post("/read_file")
# 3. 启动 HTTP 服务器
# 4. 使用 requests/httpx 调用
```

---

## 迁移指南

### 从 v1.x 升级到 v2.0

v2.0 带来了重大改进，同时保持了向后兼容：

```python
# v1.x (旧版)
import remotable
remotable.configure(role="server")
server = remotable.Gateway(host="0.0.0.0", port=8000)

# v2.0 (新版) - 推荐
import remotable_function
server = await remotable_function.start_server(port=8000)
```

**主要变化：**
- ✅ 移除了 `configure()` - 不再需要
- ✅ 统一的 API - Gateway 和 Client 类
- ✅ 改进的自动重连 - 指数退避 + 抖动
- ✅ 更好的事件系统 - 更多生命周期事件
- ✅ 完整的类型提示 - 更好的 IDE 支持

---

## 社区和支持

### 获取帮助

- 📖 **文档**: [GitHub Wiki](https://github.com/StarAniseStudio/remotable-function/wiki)
- 🐛 **问题追踪**: [Issues](https://github.com/StarAniseStudio/remotable-function/issues)
- 💬 **讨论**: [Discussions](https://github.com/StarAniseStudio/remotable-function/discussions)
- 📧 **邮件**: support@staranise.studio

### 示例项目

查看真实世界的示例：

1. **Web 客户端演示** (`samples/web_client/`)
   - JavaScript 客户端 + Python 服务器
   - 双向 RPC 通信
   - 实时 Web 界面

2. **AI 智能体演示** (`samples/agent_demo/`)
   - OpenAI GPT 集成
   - 工具选择和执行
   - 完整的对话流程

3. **简单示例** (`samples/simple/`)
   - 最小化代码示例
   - 快速入门模板

### 贡献

我们欢迎各种形式的贡献：

- 🐛 报告 Bug
- 💡 提出新功能
- 📝 改进文档
- 🔧 提交代码
- 🌍 翻译文档

查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详细信息。

---

## 路线图

### v2.1（计划中）

- [ ] 🔐 更多身份验证方法（OAuth2、JWT）
- [ ] 📊 内置监控面板
- [ ] 🔌 插件系统
- [ ] 🌐 官方 JavaScript/TypeScript 客户端库

### v2.2（未来）

- [ ] 🗄️ 数据库工具（PostgreSQL、MongoDB）
- [ ] 📦 Docker 工具
- [ ] ☁️ 云服务集成（AWS、Azure、GCP）
- [ ] 🎯 负载均衡支持

---

## 致谢

特别感谢所有为 Remotable Function 做出贡献的开发者和用户！

---

**用 ❤️ 为 AI 智能体社区打造**

**Star ⭐ 这个项目**，如果它对您有帮助的话！
