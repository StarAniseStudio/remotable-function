# Remotable Agent Demo

将 **Remotable** 与 **Agno** AI Agent 框架结合使用的演示项目。

## 架构

```
┌─────────────────────────────────────┐
│  Server 端（云端/中心服务器）          │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  AI Agent (Agno + OpenAI)   │   │
│  │  - 处理用户请求              │   │
│  │  - 调用远程工具              │   │
│  └─────────────────────────────┘   │
│  ┌─────────────────────────────┐   │
│  │  Remotable Gateway          │   │
│  │  - 管理客户端连接            │   │
│  │  - 路由工具调用              │   │
│  └─────────────────────────────┘   │
└──────────────┬──────────────────────┘
               │
               │ WebSocket + JSON-RPC 2.0
               │
┌──────────────┴──────────────────────┐
│  Client 端（本地机器）                │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  Remotable Client           │   │
│  │  - 连接到 Gateway            │   │
│  │  - 提供本地工具              │   │
│  └─────────────────────────────┘   │
│  ┌─────────────────────────────┐   │
│  │  Tools                      │   │
│  │  - 文件系统                  │   │
│  │  - Shell 命令                │   │
│  │  - 系统信息                  │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
```

## 目录结构

```
agent_demo/
├── README.md           # 本文件
├── server/             # 服务器端
│   ├── main.py         # 启动脚本
│   ├── agent.py        # AI Agent (支持 LLM 和简单模式)
│   ├── remotable_tools.py  # 工具适配器
│   ├── requirements.txt
│   └── start.sh        # 启动脚本
└── client/             # 客户端
    ├── main.py         # 启动脚本
    ├── tools/          # 自定义工具
    │   └── system_info.py
    ├── requirements.txt
    └── start.sh        # 启动脚本
```

## 快速开始

### 方式 1: 使用启动脚本（推荐）

**终端 1 - 启动服务器:**
```bash
cd agent_demo/server
./start.sh
```

**终端 2 - 启动客户端:**
```bash
cd agent_demo/client
./start.sh
```

启动脚本会自动：
- ✅ 检查依赖并自动安装
- ✅ 加载 API Key（如果有 .env 文件）
- ✅ 显示配置信息

### 方式 2: 手动启动

**1. 安装依赖**
```bash
# 服务器端
cd agent_demo/server
pip install -r requirements.txt

# 客户端
cd agent_demo/client
pip install -r requirements.txt
```

**2. 启动服务**
```bash
# 终端 1 - 客户端
cd agent_demo/client
python main.py

# 终端 2 - 服务器
cd agent_demo/server
python main.py
```

## 运行模式

服务器支持两种模式：

### 简单模式（默认）
- 无需 API Key
- 基于关键词匹配
- 快速测试

示例命令：
```
User: 列出 /tmp
User: 读取 /etc/hosts
User: 系统信息
```

### AI 模式（推荐）
- 需要 OpenAI API Key
- 自然语言理解
- 智能工具选择

**配置 API Key:**
```bash
# 方法 1: .env 文件（推荐）
cd agent_demo/server
cp .env.example .env
# 编辑 .env，填入: OPENAI_API_KEY=sk-your-api-key-here

# 方法 2: 环境变量
export OPENAI_API_KEY="sk-your-api-key-here"
```

示例命令：
```
User: 帮我查看客户端 /tmp 目录下有哪些文件
User: 创建一个文件 /tmp/hello.txt，内容是 Hello World
User: 获取客户端的系统信息
```

## 可用工具

客户端提供以下工具：

- **文件系统**
  - `filesystem.read_file` - 读取文件
  - `filesystem.write_file` - 写入文件
  - `filesystem.list_directory` - 列出目录
  - `filesystem.delete` - 删除文件/目录

- **Shell**
  - `shell.execute` - 执行命令

- **系统**
  - `system.get_system_info` - 获取系统信息

## 使用场景

1. **远程运维** - Agent 在云端，控制本地机器
2. **多机管理** - 一个 Agent 管理多个客户端
3. **开发助手** - AI 助手控制本地开发环境

## 文档

- [server/README.md](server/README.md) - 服务器端详细文档
- [client/README.md](client/README.md) - 客户端详细文档
- [../README.md](../README.md) - Remotable 核心文档

## 安全提示

⚠️ 这是演示项目，生产环境需要：
- 添加身份认证
- 使用 TLS/SSL 加密
- 实现权限控制
- 限制工具访问
- 记录审计日志
