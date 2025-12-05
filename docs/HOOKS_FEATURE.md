# 客户端工具调用 Hook 功能

## 概述

Remotable v2.0 新增了强大的客户端 Hook 机制，允许在工具调用的不同阶段插入自定义逻辑。

## 新增功能

### Hook 事件类型

1. **`before_tool_execute`** - 工具执行前
   - 记录日志、安全检查、参数修改、取消执行

2. **`after_tool_execute`** - 工具执行后（成功）
   - 记录结果、统计、后续处理

3. **`tool_error`** - 工具执行失败
   - 错误日志、告警、错误统计

4. **`tool_executed`** - 向后兼容（`after_tool_execute` 的别名）

## 快速开始

```python
import remotable_function

client = remotable_function.Client(server_url="ws://localhost:8000")

# 注册 hook
async def log_before(tool_name, args, context):
    print(f"执行工具: {tool_name}, 参数: {args}")

client.on("before_tool_execute", log_before)
```

## 使用场景

### 1. 日志记录

```python
async def audit_log(tool_name, args, context):
    logger.info(f"[{context.client_id}] 调用 {tool_name}: {args}")

client.on("before_tool_execute", audit_log)
```

### 2. 安全控制

```python
async def security_check(tool_name, args, context):
    if tool_name == "filesystem.write_file":
        if args["path"].startswith("/etc/"):
            raise PermissionError("禁止写入系统目录")

client.on("before_tool_execute", security_check)
```

### 3. 参数修改

```python
async def add_timestamp(tool_name, args, context):
    if tool_name == "filesystem.write_file":
        args["content"] = f"[{datetime.now()}] {args['content']}"

client.on("before_tool_execute", add_timestamp)
```

### 4. 调用统计

```python
stats = {}

async def count_calls(tool_name, args, result, context):
    stats[tool_name] = stats.get(tool_name, 0) + 1

client.on("after_tool_execute", count_calls)
```

### 5. 错误处理

```python
async def handle_errors(tool_name, args, error, context):
    send_alert(f"工具 {tool_name} 失败: {error}")

client.on("tool_error", handle_errors)
```

## Hook 签名

### before_tool_execute
```python
async def hook(tool_name: str, args: dict, context: ToolContext) -> None:
    """
    tool_name: 工具全名（如 "filesystem.read_file"）
    args: 参数字典（可修改）
    context: 包含 client_id, request_id 等
    """
```

### after_tool_execute
```python
async def hook(tool_name: str, args: dict, result: Any, context: ToolContext) -> None:
    """
    tool_name: 工具全名
    args: 参数字典
    result: 工具返回结果
    context: 执行上下文
    """
```

### tool_error
```python
async def hook(tool_name: str, args: dict, error: Exception, context: ToolContext | None) -> None:
    """
    tool_name: 工具全名
    args: 参数字典
    error: 异常对象
    context: 执行上下文（可能为 None）
    """
```

## 执行顺序

对于每个工具调用：

```
1. 所有 before_tool_execute hooks（按注册顺序）
   ├─ 如果抛出异常 → 跳到 tool_error
   └─ 否则继续

2. 工具执行
   ├─ 成功 → 触发 after_tool_execute 和 tool_executed
   └─ 失败 → 触发 tool_error
```

## 示例代码

### 完整示例
参见 [samples/hook_example.py](samples/hook_example.py) - 包含 6 个实用 hook 示例

### 测试代码
参见 [test_hooks.py](test_hooks.py) - 验证 hook 功能

## 文档

详细文档：[docs/client_hooks.md](docs/client_hooks.md)

## 修改的文件

### 核心代码
- `remotable_function/client_unified.py`
  - 添加了 `before_tool_execute`, `after_tool_execute`, `tool_error` 事件
  - 在 `_execute_tool_v2()` 和 `_execute_tool()` 中调用 hooks
  - 支持参数修改和执行取消

### 示例和文档
- `samples/hook_example.py` - 完整可运行示例
- `docs/client_hooks.md` - 详细使用文档
- `test_hooks.py` - 功能测试
- `HOOKS_FEATURE.md` - 本文件

## 向后兼容

✅ 完全向后兼容
- 保留原有的 `tool_executed` 事件
- 不影响现有代码
- Hook 是可选功能

## 测试验证

运行测试：
```bash
python3 test_hooks.py
```

预期输出：
```
✅ PASS: before_tool_execute 被调用
✅ PASS: after_tool_execute 被调用
✅ PASS: tool_executed 被调用 (向后兼容)
✅ PASS: 参数修改功能
🎉 所有测试通过！
```

## 最佳实践

1. **轻量化**: Hook 在每次调用时执行，保持轻量
2. **异常处理**: 使用 try-except 处理预期错误
3. **文档化**: 记录 Hook 的作用，特别是修改参数的 Hook
4. **条件性**: 使用 `if` 判断只针对特定工具
5. **顺序**: 注意多个 Hook 的注册顺序

## 相关 PR/Issues

- 功能需求：添加统一的工具调用监听 hook
- 实现日期：2025-01-22
- 版本：v2.0

## 作者

Claude Code Assistant
