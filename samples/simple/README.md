# Remotable - Simple Examples

**最简化的 Remotable v2.0 示例** - 展示如何用最少的代码启动服务器和客户端。

## 快速开始（2 个终端窗口）

### 终端 1: 启动服务器
```bash
cd samples/simple
python3 server.py
```

### 终端 2: 连接客户端
```bash
cd samples/simple
python3 client.py
```

## 文件说明

### 📄 server.py
展示 3 种启动服务器的方式：

1. **快速启动** (2 行代码!)
   ```python
   import remotable_function
   server = await remotable_function.start_server(port=8000)
   ```

2. **带认证的服务器**
   ```python
   server = await remotable_function.start_server(
       port=8000,
       auth_token="my-secret-key"
   )
   ```

3. **生产环境配置**
   ```python
   from remotable_function import Gateway, GatewayConfig
   config = GatewayConfig.production()
   gateway = Gateway(config)
   await gateway.start()
   ```

### 📄 client.py
展示 3 种连接客户端的方式：

1. **标准客户端** (带自定义工具)
   ```python
   import remotable_function

   class MyTool(remotable_function.Tool):
       name = "my_tool"
       async def execute(self, context, **kwargs):
           return "result"

   client = await remotable_function.connect_client(
       "ws://localhost:8000",
       tools=[MyTool()]
   )
   ```

2. **最简客户端** (仅内置工具)
   ```python
   client = await remotable_function.connect_client(
       "ws://localhost:8000",
       tools=[
           remotable_function.FileSystemTool(),
           remotable_function.ShellTool()
       ]
   )
   ```

3. **带认证的客户端**
   ```python
   client = await remotable_function.connect_client(
       "ws://localhost:8000",
       auth_token="my-secret-key",
       tools=[MyTool()]
   )
   ```

## 核心特性

### ✨ 自动重连
客户端支持自动重连，包含：
- 指数退避算法（exponential backoff）
- 随机抖动（jitter）防止雷鸣群效应
- 可配置的重试次数和延迟

```python
client = remotable_function.Client(
    server_url="ws://localhost:8000",
    auto_reconnect=True,              # 启用自动重连
    reconnect_max_attempts=10,        # 最多重试 10 次
    reconnect_interval=2,             # 基础延迟 2 秒
)
```

### 🔒 内置安全特性
- 身份验证（Authentication）
- 速率限制（Rate limiting）
- 消息大小限制
- 压缩传输

### 📦 内置工具
- **FileSystemTool** - 安全的文件系统操作
- **ShellTool** - 受控的命令执行

## 自定义工具示例

创建自定义工具非常简单：

```python
import remotable_function
from datetime import datetime

class TimeTool(remotable_function.Tool):
    """获取当前时间的工具"""

    name = "time"
    description = "Get current time in various formats"
    namespace = "utility"

    async def execute(self, context, format: str = "iso") -> str:
        now = datetime.now()
        formats = {
            "iso": now.isoformat(),
            "human": now.strftime("%Y-%m-%d %H:%M:%S"),
            "unix": str(int(now.timestamp()))
        }
        return formats.get(format, now.isoformat())
```

## 运行示例

### 方式 1: 快速启动（默认）
```bash
# 终端 1
python3 server.py

# 终端 2
python3 client.py
```

### 方式 2: 带认证
修改 `server.py` 和 `client.py` 中的 `if __name__ == "__main__"` 部分：
```python
# server.py
asyncio.run(with_auth())

# client.py
asyncio.run(with_auth())
```

### 方式 3: 生产环境配置
```python
# server.py
asyncio.run(with_config())
```

## 测试连接

客户端连接后，服务器端会显示：
```
✅ Server is running at ws://localhost:8000
Client connected: client-xxxxx with 2 tools
  - utility.time
  - utility.math
```

客户端会显示：
```
✅ Connected to server
Registered tools: 2
  - utility.time
  - utility.math
Client is ready!
```

## 高级示例

需要更完整的示例？查看：
- `samples/demo/` - 带 UI 的完整演示
- `samples/agent_demo/` - AI Agent 集成示例

## API 变更

### v2.0 新特性
- ✅ 无需 `remotable.configure()` - 直接使用
- ✅ 统一的 API - Gateway 和 Client 类
- ✅ 改进的自动重连 - 指数退避 + 抖动
- ✅ 更好的事件系统 - 更多生命周期事件
- ✅ 类型提示 - 完整的类型支持

### 从 v1.x 升级

**v1.x (旧版):**
```python
import remotable
remotable.configure(role="server")  # ❌ 已废弃
server = remotable.Gateway(host="0.0.0.0", port=8000)
```

**v2.0 (新版):**
```python
import remotable_function  # 或 import remotable
server = await remotable_function.start_server(port=8000)  # ✅ 推荐
```

## 故障排除

### 端口已被占用
```bash
# 查找占用端口的进程
lsof -i :8000

# 或使用不同端口
python3 server.py --port 8001  # (如果支持命令行参数)
```

### 连接失败
1. 确保服务器已启动
2. 检查防火墙设置
3. 验证服务器地址和端口正确

### 客户端无法重连
检查以下设置：
```python
client = Client(
    auto_reconnect=True,          # 确保启用
    reconnect_max_attempts=10,    # 足够的重试次数
)
```

## 更多信息

- 📖 [完整文档](../../README.md)
- 🐛 [问题反馈](https://github.com/your-repo/issues)
- 💡 [示例集合](../)
