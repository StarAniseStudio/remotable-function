# Remotable Demo

展示 Remotable 核心功能的基础示例：服务器通过 RPC 调用客户端工具。

## 架构

```
┌─────────────────┐     WebSocket + JSON-RPC 2.0     ┌─────────────────┐
│  Server (云端)   │ ◄─────────────────────────────► │  Client (本地)   │
│                 │                                  │                 │
│  Gateway        │  1. Client 注册工具               │  Client         │
│  (调用工具)      │ ◄── tools: [read, write, ...]   │  (提供工具)      │
│                 │                                  │                 │
│  call_tool()    │  2. Server 调用工具               │  Tool.execute() │
│                 │ ──► execute: read_file           │                 │
│                 │ ◄── result: {content: "..."}    │                 │
└─────────────────┘                                  └─────────────────┘
```

## 快速开始

### 终端 1：启动服务器

```bash
cd demo/server
python main.py
```

输出：
```
[INFO] Gateway running on ws://0.0.0.0:8000
[INFO] Waiting for clients...
```

### 终端 2：启动客户端

```bash
cd demo/client
python main.py
```

输出：
```
[INFO] Registered 5 tools
[INFO] Connected to server as 'demo-client'
[INFO] Tools: filesystem.read_file, filesystem.write_file, ...
```

### 自动演示

客户端连接后，服务器会自动演示所有功能：

```
============================================================
DEMO: Remote Tool Calls
============================================================

[1] Reading /tmp/test.txt...
✓ File read successfully (87 bytes)

[2] Writing to /tmp/remotable_test.txt...
✓ File written successfully (62 bytes)

[3] Listing /tmp directory...
✓ Found 45 items (42 files, 3 directories)

[4] Executing 'echo Hello'...
✓ Command executed (return code: 0)

[5] Executing 'uname -a'...
✓ Darwin MacBook-Pro.local 25.1.0...

============================================================
DEMO COMPLETED
============================================================
```

## Unity Netcode 风格 API

一套代码，通过 `configure()` 区分身份：

### 服务器端

```python
import remotable

# 配置为服务器
remotable.configure(role="server")

# 创建 Gateway
gateway = remotable.Gateway(host="0.0.0.0", port=8000)

# 客户端连接时调用工具
@gateway.on_client_connected
async def on_connected(client_id, client_info):
    result = await gateway.call_tool(
        client_id=client_id,
        tool="filesystem.read_file",
        args={"path": "/tmp/test.txt"}
    )
    print(result)

# 启动
await gateway.start()
```

### 客户端

```python
import remotable

# 配置为客户端
remotable.configure(role="client")

# 创建 Client
client = remotable.Client(
    server_url="ws://localhost:8000",
    client_id="my-client"
)

# 注册工具
from remotable.client.tools import ReadFileTool, WriteFileTool
client.register_tools(ReadFileTool(), WriteFileTool())

# 连接
await client.connect()
```

## 内置工具

客户端提供 5 个开箱即用的工具：

### 文件系统

1. **filesystem.read_file** - 读取文件
   - 参数: `path`, `encoding` (可选)
   - 返回: `content`, `size`, `path`

2. **filesystem.write_file** - 写入文件
   - 参数: `path`, `content`, `encoding` (可选), `append` (可选)
   - 返回: `path`, `size`, `appended`

3. **filesystem.list_directory** - 列出目录
   - 参数: `path`, `recursive` (可选)
   - 返回: `files`, `directories`, `count`

4. **filesystem.delete** - 删除文件/目录
   - 参数: `path`, `recursive` (可选)
   - 返回: `deleted`, `type`

### Shell

5. **shell.execute** - 执行命令
   - 参数: `command`, `cwd` (可选), `timeout` (可选)
   - 返回: `stdout`, `stderr`, `returncode`

## 自定义工具

创建自定义工具很简单：

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

# 注册
client.register_tool(MyTool())
```

## 核心特性

**Server (Gateway)**
- WebSocket 服务器
- 客户端管理
- 远程工具调用
- 心跳监控

**Client**
- WebSocket 客户端
- 自动重连
- 工具注册和执行
- 心跳响应

**Protocol**
- JSON-RPC 2.0
- 请求-响应匹配
- 超时控制
- 错误处理

## 文件结构

```
demo/
├── README.md       # 本文件
├── server/
│   └── main.py     # 服务器示例
└── client/
    └── main.py     # 客户端示例
```

## 下一步

1. 运行 demo 查看效果
2. 阅读源代码了解实现
3. 创建自定义工具
4. 查看 `agent_demo/` 了解 AI Agent 集成

---

**Unity Netcode 风格 - 一套代码，身份区分！** 🎮
