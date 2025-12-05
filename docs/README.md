# Remotable Function - 技术文档

本目录包含 Remotable Function 框架的详细技术文档。

## 📚 文档索引

### 核心功能文档

#### [RECONNECTION_FIX_SUMMARY.md](RECONNECTION_FIX_SUMMARY.md)
**客户端重连问题修复总结**

修复了服务器重启后客户端无法重连的问题。包含：
- 3 个根本原因分析
- 完整的修复方案
- 测试验证结果

**关键修复**:
1. ✅ 断开检测 - 添加 `finally` 块确保总能检测到服务器断开
2. ✅ 参数处理 - 正确处理 `reconnect_max_attempts` 等参数
3. ✅ 连接清理 - 重连前清理旧连接和后台任务

---

#### [RECONNECT_IMPROVEMENTS.md](RECONNECT_IMPROVEMENTS.md)
**自动重连功能改进详解**

详细说明了从线性退避到指数退避的升级过程。包含：
- Before/After 对比
- 指数退避算法实现
- 配置参数说明
- 完整代码示例

**核心改进**:
- 指数退避 + 随机抖动（jitter）
- 循环替代递归（避免栈溢出）
- 心跳超时检测
- 增强的事件系统

---

#### [AUTO_RECONNECT_ANALYSIS.md](AUTO_RECONNECT_ANALYSIS.md)
**自动重连功能分析报告**

对重连功能的全面分析和业界对比。包含：
- 现有实现分析
- 与 AWS SDK、gRPC、Socket.IO 对比
- 问题识别（6 个主要问题）
- 改进建议（优先级排序）

**参考实现**:
- AWS SDK 重试策略
- gRPC 连接管理
- Socket.IO 重连机制

---

### 特性文档

#### [HOOKS_FEATURE.md](HOOKS_FEATURE.md)
**Hooks 功能特性文档**

Client 端的事件钩子系统，支持生命周期事件监听。包含：
- 可用的钩子列表
- 使用示例
- 优先级系统
- 错误处理

**支持的钩子**:
- `connected` - 连接成功
- `disconnected` - 断开连接
- `reconnecting` - 正在重连
- `tool_executed` - 工具执行完成
- `error` - 错误事件

---

#### [client_hooks.md](client_hooks.md)
**客户端钩子详细文档**

Client hooks 的完整 API 文档和使用指南。

---

## 🔍 快速导航

### 按主题查找

**重连相关**:
- [RECONNECTION_FIX_SUMMARY.md](RECONNECTION_FIX_SUMMARY.md) - 问题修复
- [RECONNECT_IMPROVEMENTS.md](RECONNECT_IMPROVEMENTS.md) - 功能改进
- [AUTO_RECONNECT_ANALYSIS.md](AUTO_RECONNECT_ANALYSIS.md) - 深度分析

**事件系统**:
- [HOOKS_FEATURE.md](HOOKS_FEATURE.md) - Hooks 特性
- [client_hooks.md](client_hooks.md) - 客户端钩子

### 按角色查找

**开发者**:
1. 快速开始 → 查看主 [README.md](../README.md)
2. 了解重连 → [RECONNECTION_FIX_SUMMARY.md](RECONNECTION_FIX_SUMMARY.md)
3. 使用钩子 → [HOOKS_FEATURE.md](HOOKS_FEATURE.md)

**架构师/技术负责人**:
1. 技术分析 → [AUTO_RECONNECT_ANALYSIS.md](AUTO_RECONNECT_ANALYSIS.md)
2. 改进详情 → [RECONNECT_IMPROVEMENTS.md](RECONNECT_IMPROVEMENTS.md)
3. 业界对比 → [AUTO_RECONNECT_ANALYSIS.md](AUTO_RECONNECT_ANALYSIS.md#业界最佳实践)

**运维人员**:
1. 故障排查 → [RECONNECTION_FIX_SUMMARY.md](RECONNECTION_FIX_SUMMARY.md#测试推荐)
2. 配置参考 → [RECONNECTION_FIX_SUMMARY.md](RECONNECTION_FIX_SUMMARY.md#配置)

## 📊 技术要点总结

### 自动重连

**算法**: 指数退避 + 随机抖动
```python
delay = min(max_delay, base_delay * (2 ^ attempts)) * (1 ± 30% jitter)
```

**默认配置**:
- 基础延迟: 1.0 秒
- 最大延迟: 60.0 秒
- 乘数: 2.0
- 抖动: ±30%
- 最大尝试: 10 次

**重连序列示例**:
```
尝试 1: ~2秒
尝试 2: ~4秒
尝试 3: ~8秒
尝试 4: ~16秒
尝试 5: ~32秒
尝试 6-10: ~60秒
```

### 事件系统

**生命周期事件**:
1. `connected` - 成功连接到服务器
2. `disconnected` - 与服务器断开连接
3. `reconnecting` - 正在尝试重连（包含尝试次数和等待时间）
4. `reconnect_failed` - 单次重连尝试失败
5. `reconnect_stopped` - 重连已停止（达到最大次数或其他原因）

**工具执行事件**:
- `before_tool_execute` - 工具执行前
- `tool_executed` - 工具执行成功
- `after_tool_execute` - 工具执行后
- `tool_error` - 工具执行出错

## 🔧 配置示例

### 自定义重连配置
```python
from remotable_function import Client, ClientConfig, NetworkConfig

config = ClientConfig(
    server_url="ws://localhost:8000",
    auto_reconnect=True,
    network=NetworkConfig(
        reconnect_max_attempts=15,      # 最多重试 15 次
        reconnect_base_delay=2.0,       # 基础延迟 2 秒
        reconnect_max_delay=120.0,      # 最大延迟 120 秒
        reconnect_multiplier=2.0,       # 指数乘数
        reconnect_jitter=0.3,           # ±30% 抖动
    )
)

client = Client(config)
```

### 监听重连事件
```python
async def on_reconnecting(event_data):
    attempt = event_data["attempt"]
    wait_time = event_data["wait_time"]
    max_attempts = event_data["max_attempts"]
    print(f"正在重连... ({attempt}/{max_attempts}，等待 {wait_time:.1f}s)")

client.on("reconnecting", on_reconnecting)
client.on("connected", lambda: print("✅ 已连接"))
client.on("disconnected", lambda: print("❌ 已断开"))
```

## 📝 版本历史

### v2.0 (当前)
- ✅ 指数退避 + 抖动算法
- ✅ 改进的断开检测（`finally` 块）
- ✅ 完整的事件系统
- ✅ 向后兼容参数处理

### v1.x
- ⚠️ 线性退避（已废弃）
- ⚠️ 递归重连（有栈溢出风险）
- ⚠️ 有限的事件支持

## 🤝 贡献

如需更新文档，请确保：
1. 使用清晰的 Markdown 格式
2. 包含代码示例
3. 添加适当的链接
4. 更新此 README 的索引

## 📮 反馈

有问题或建议？请：
- 提交 Issue
- 参与讨论
- 贡献代码

---

**最后更新**: 2025-11-23
**维护者**: Remotable 团队
