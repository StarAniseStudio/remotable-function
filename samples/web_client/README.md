# Remotable Function - Web Client Demo

**Python Backend + JavaScript Frontend** - 展示如何使用 JavaScript 客户端连接到 Remotable Python Gateway，实现浏览器与 Python 后端的双向 RPC 通信。

## 🎯 Demo 特性

这个 demo 展示了：

✅ **JavaScript 客户端连接 Python Gateway** - 使用标准 WebSocket 和 JSON-RPC 2.0 协议
✅ **JavaScript 调用 Python 工具** - 浏览器端调用服务器端的 Python 函数
✅ **Python 调用 JavaScript 工具** - 服务器端操作浏览器 DOM、弹窗等
✅ **实时双向通信** - 自动重连、事件驱动
✅ **美观的 Web 界面** - 实时日志、状态显示

## 📁 项目结构

```
web_client/
├── backend/
│   └── server.py          # Python Gateway（提供演示工具）
├── frontend/
│   ├── index.html         # Web 界面
│   ├── client.js          # JavaScript WebSocket 客户端
│   ├── app.js             # 应用逻辑
│   └── style.css          # 样式
└── README.md              # 本文档
```

## 🚀 快速开始

### 步骤 1: 启动 Python 后端

```bash
cd samples/web_client/backend
python3 server.py
```

你会看到：
```
============================================================
Remotable Function - Web Client Demo
============================================================

Python Gateway providing tools for JavaScript frontend

🚀 Creating Gateway...
✓ Gateway created

🌐 Starting Gateway server...
✓ Gateway running at ws://localhost:8765

📱 Open frontend/index.html in your browser to connect

Available Python tools for JavaScript to call:
  - demo.get_time: Get current server time
  - demo.calculate: Calculate math expressions
  - demo.echo: Echo messages back
```

### 步骤 2: 打开前端页面

在浏览器中打开：
```
file:///path/to/remotable/samples/web_client/frontend/index.html
```

或者使用简单的 HTTP 服务器（推荐）：
```bash
cd samples/web_client/frontend
python3 -m http.server 8080
```

然后访问：`http://localhost:8080`

### 步骤 3: 测试功能

**JavaScript 调用 Python 工具：**
1. 点击 "Get Time" - 获取服务器时间
2. 输入数学表达式，点击 "Calculate" - 计算结果
3. 输入消息，点击 "Echo" - 回显消息

**Python 调用 JavaScript 工具（自动演示）：**
- 连接成功后，Python 会自动调用浏览器的工具
- 显示通知
- 更新 DOM 元素
- 获取浏览器信息

## 🔧 技术细节

### Python 后端

**提供的工具：**

| 工具名 | 功能 | 参数 |
|--------|------|------|
| `demo.get_time` | 获取服务器时间 | `format`: iso/unix/human/detailed |
| `demo.calculate` | 计算数学表达式 | `expression`: 数学表达式字符串 |
| `demo.echo` | 回显消息 | `message`: 消息内容, `uppercase`: 是否大写 |

**代码示例：**
```python
class GetTimeTool(remotable_function.Tool):
    name = "get_time"
    namespace = "demo"

    async def execute(self, context, format: str = "iso"):
        now = datetime.now()
        return {
            "time": now.isoformat(),
            "timestamp": int(now.timestamp())
        }
```

### JavaScript 客户端

**提供的工具：**

| 工具名 | 功能 | 参数 |
|--------|------|------|
| `browser.show_notification` | 显示浏览器通知 | `title`, `message`, `type` |
| `browser.update_dom` | 更新 DOM 元素 | `selector`, `content` |
| `browser.get_info` | 获取浏览器信息 | 无 |

**核心 API：**
```javascript
// 创建客户端
const client = new RemotableClient('ws://localhost:8765');

// 注册工具
client.registerTool('browser', 'show_notification', async (args) => {
    // 实现逻辑
    return { success: true };
}, 'Show browser notification');

// 连接
await client.connect();

// 调用 Python 工具
const result = await client.callTool('demo.get_time', { format: 'iso' });
```

## 📋 协议说明

### JSON-RPC 2.0 协议

**请求格式（JavaScript 调用 Python）：**
```json
{
    "jsonrpc": "2.0",
    "method": "call_tool",
    "params": {
        "tool": "demo.get_time",
        "args": { "format": "iso" }
    },
    "id": "1234567890-abc123"
}
```

**响应格式：**
```json
{
    "jsonrpc": "2.0",
    "id": "1234567890-abc123",
    "result": {
        "time": "2025-11-23T12:00:00",
        "timestamp": 1700740800
    }
}
```

**工具调用（Python 调用 JavaScript）：**
```json
{
    "jsonrpc": "2.0",
    "method": "call_tool",
    "params": {
        "tool": "browser.show_notification",
        "args": {
            "title": "Hello",
            "message": "From Python!",
            "type": "success"
        }
    },
    "id": "server-request-123"
}
```

## 🎨 界面功能

### 状态面板
- **Connection**: 连接状态（Connected/Disconnected）
- **Client ID**: 当前客户端 ID
- **Server**: WebSocket 服务器地址

### Python 工具调用区
- **Get Server Time**: 获取服务器时间（支持多种格式）
- **Calculator**: 安全的数学表达式计算
- **Echo Message**: 消息回显（支持大写转换）

### 活动日志
- 实时显示所有 RPC 调用
- 彩色分类（INFO/SUCCESS/WARNING/ERROR）
- 时间戳和详细信息
- 自动滚动到最新日志

### JavaScript 工具列表
- 显示已注册的浏览器端工具
- Python 可以调用这些工具

## 🔍 调试

### 浏览器控制台
打开浏览器开发者工具（F12），可以看到：
- WebSocket 连接状态
- 发送和接收的消息
- 客户端日志

### Python 终端
Python 服务器会显示：
- 客户端连接/断开事件
- 工具调用记录
- 错误信息

## 🌟 扩展示例

### 添加新的 Python 工具

```python
class MyCustomTool(remotable_function.Tool):
    name = "my_tool"
    namespace = "custom"
    description = "My custom tool"

    async def execute(self, context, param1: str, param2: int = 0):
        # 实现你的逻辑
        return {
            "result": f"Received {param1} and {param2}"
        }

# 在 Gateway 中不需要手动注册
# 工具类会自动被客户端发现
```

### 添加新的 JavaScript 工具

```javascript
client.registerTool('custom', 'my_browser_tool', async (args) => {
    const { param1, param2 } = args;

    // 实现你的逻辑
    console.log(`Received: ${param1}, ${param2}`);

    return {
        success: true,
        result: "Operation completed"
    };
}, 'My custom browser tool');
```

### 在前端调用新工具

```javascript
async function callMyTool() {
    try {
        const result = await client.callTool('custom.my_tool', {
            param1: 'hello',
            param2: 42
        });
        console.log('Result:', result);
    } catch (error) {
        console.error('Error:', error);
    }
}
```

## 🔒 安全注意事项

1. **计算器工具** - 使用受限的 `eval()`，只允许数字和基本运算符
2. **DOM 操作** - 应该验证选择器和内容，防止 XSS
3. **生产环境** - 启用身份验证：
   ```python
   gateway = remotable_function.Gateway(
       port=8765,
       auth_token="your-secret-key"
   )
   ```

## 📊 性能特性

- **自动重连** - 网络断开后自动重连（最多 5 次）
- **指数退避** - 重连延迟逐渐增加
- **请求超时** - 默认 30 秒超时
- **日志限制** - 最多保留 100 条日志

## 🐛 故障排除

### 连接失败

**问题**: 浏览器无法连接到 `ws://localhost:8765`

**解决**:
1. 确保 Python 服务器正在运行
2. 检查端口是否被占用：`lsof -i :8765`
3. 查看浏览器控制台的错误信息
4. 确认防火墙设置

### CORS 问题

**问题**: 跨域请求被阻止

**解决**:
- 使用 `python3 -m http.server` 运行前端
- 或者使用 `file://` 协议（WebSocket 不受 CORS 限制）

### 工具调用超时

**问题**: 调用超时

**解决**:
```javascript
// 增加超时时间
const result = await client.callTool('demo.get_time', {}, 60000); // 60秒
```

## 📚 更多资源

- [Remotable 主文档](../../README.md)
- [Simple 示例](../simple/)
- [Agent Demo](../agent_demo/)
- [测试套件](../../tests/)

## 🎓 学习路径

1. **初学者**: 运行这个 demo，观察双向通信
2. **中级**: 添加自定义工具，修改界面
3. **高级**: 集成到实际项目，添加认证和安全功能

---

**提示**: 这个 demo 完全兼容标准 JSON-RPC 2.0 协议，你可以用任何支持 WebSocket 的语言（如 Go、Rust、Node.js）实现客户端！
