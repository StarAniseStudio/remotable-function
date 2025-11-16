# Server 端 - AI Agent + Gateway

服务器端程序，运行 AI Agent 和 Remotable Gateway。

## 职责

1. **AI Agent** - 处理用户请求，理解意图，调用远程工具
2. **Remotable Gateway** - 管理客户端连接，路由工具调用
3. **交互界面** - 提供命令行界面与用户交互

## 文件说明

```
server/
├── main.py              # 主程序（启动 Gateway 和 Agent）
├── agent.py             # AI Agent（支持 LLM 和简单模式）
├── remotable_tools.py   # Remotable 工具适配器
├── requirements.txt     # 依赖
├── start.sh             # 启动脚本
└── .env.example         # 环境变量模板
```

## 快速开始

### 使用启动脚本（推荐）

```bash
./start.sh
```

启动脚本会自动：
- 检查并安装依赖
- 加载 .env 文件
- 检测运行模式（AI 或简单模式）
- 启动服务器

### 手动启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动
python main.py
```

## 运行模式

### 简单模式（默认）
- **无需配置**，直接启动
- 基于关键词匹配
- 适合快速测试

**示例：**
```
User: 列出 /tmp
User: 读取 /etc/hosts
User: 系统信息
```

### AI 模式（推荐）
- 需要 OpenAI API Key
- 自然语言理解
- 智能工具选择

**配置方法：**

```bash
# 方法 1: .env 文件（推荐）
cp .env.example .env
# 编辑 .env，填入: OPENAI_API_KEY=sk-your-api-key-here

# 方法 2: 环境变量
export OPENAI_API_KEY="sk-your-api-key-here"
```

**获取 API Key:** https://platform.openai.com/

**示例：**
```
User: 帮我查看客户端 /tmp 目录下有哪些文件
User: 创建一个文件 /tmp/hello.txt，内容是 Hello World
User: 查看 demo.txt 的文件权限
```

## 配置

### Gateway 配置（main.py）

```python
gateway = remotable.Gateway(
    host="0.0.0.0",        # 监听地址
    port=8000,             # 端口
    heartbeat_interval=30, # 心跳间隔（秒）
    heartbeat_timeout=60   # 心跳超时（秒）
)
```

### Agent 配置（agent.py）

```python
# LLM 模型
model=OpenAIChat(id="gpt-4o-mini")  # 或 gpt-4

# Agent 指令
instructions=[
    "你是一个 AI 助手...",
    # 自定义指令
]
```

## 网络配置

### 本地测试
```
服务器: localhost:8000
客户端: 同一台机器
```

### 局域网
```
服务器: 192.168.1.100:8000
客户端: 局域网内其他机器
```

### 云端
```
服务器: your-server.com:8000
客户端: 任何地方（需配置防火墙）
```

## 可用工具

服务器可以调用客户端提供的工具：

- `read_file(path, encoding)` - 读取文件
- `write_file(path, content, append)` - 写入文件
- `list_directory(path, recursive)` - 列出目录
- `delete_file(path, recursive)` - 删除文件/目录
- `execute_shell(command, cwd, timeout)` - 执行命令
- `get_system_info()` - 获取系统信息

## 安全建议

⚠️ 生产环境需要：
- 添加身份认证（JWT/API Key）
- 使用 TLS 加密（wss:// 而不是 ws://）
- 实现权限控制
- 限制工具访问
- 记录审计日志

## 相关文档

- [../README.md](../README.md) - 项目总览
- [../client/README.md](../client/README.md) - 客户端文档
- [../../README.md](../../README.md) - Remotable 文档
