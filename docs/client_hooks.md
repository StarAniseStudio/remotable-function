# 客户端工具调用 Hook

## 概述

Remotable v2.0 客户端提供了强大的 Hook 机制，允许你在工具执行的不同阶段插入自定义逻辑。这对于日志记录、安全检查、参数修改、统计等场景非常有用。

## Hook 类型

### 1. `before_tool_execute` - 执行前 Hook

在工具执行**之前**触发，可以用于：
- 记录日志
- 安全检查和权限验证
- 修改参数
- 取消执行（通过抛出异常）

**签名：**
```python
async def before_hook(tool_name: str, args: dict, context: ToolContext) -> None:
    pass
```

**参数：**
- `tool_name`: 工具全名（例如 "filesystem.read_file"）
- `args`: 工具参数字典（可修改）
- `context`: 工具执行上下文（包含 client_id, request_id 等）

**示例：**
```python
async def security_check(tool_name, args, context):
    """安全检查"""
    if tool_name == "filesystem.write_file":
        path = args.get("path", "")
        if path.startswith("/etc/"):
            raise PermissionError(f"禁止写入系统目录: {path}")

client.on("before_tool_execute", security_check)
```

### 2. `after_tool_execute` - 执行后 Hook

在工具**成功执行后**触发，可以用于：
- 记录执行结果
- 统计调用次数
- 后续处理
- 结果验证

**签名：**
```python
async def after_hook(tool_name: str, args: dict, result: Any, context: ToolContext) -> None:
    pass
```

**参数：**
- `tool_name`: 工具全名
- `args`: 工具参数字典
- `result`: 工具返回结果
- `context`: 工具执行上下文

**示例：**
```python
call_stats = {}

async def count_calls(tool_name, args, result, context):
    """统计调用次数"""
    call_stats[tool_name] = call_stats.get(tool_name, 0) + 1

client.on("after_tool_execute", count_calls)
```

### 3. `tool_error` - 错误 Hook

在工具**执行失败**时触发，可以用于：
- 错误日志记录
- 错误通知
- 错误统计
- 自定义错误处理

**签名：**
```python
async def error_hook(tool_name: str, args: dict, error: Exception, context: ToolContext | None) -> None:
    pass
```

**参数：**
- `tool_name`: 工具全名
- `args`: 工具参数字典
- `error`: 异常对象
- `context`: 工具执行上下文（可能为 None）

**示例：**
```python
async def log_errors(tool_name, args, error, context):
    """记录错误"""
    logger.error(f"工具 {tool_name} 执行失败: {error}")
    # 可以发送告警、记录到数据库等

client.on("tool_error", log_errors)
```

### 4. `tool_executed` - 向后兼容 Hook

这是 `after_tool_execute` 的别名，为保持向后兼容而保留。

**签名（简化版）：**
```python
async def executed_hook(tool_name: str, args: dict, result: Any) -> None:
    pass
```

**注意：** 这个 hook 不包含 `context` 参数，建议新代码使用 `after_tool_execute`。

## 使用方法

### 注册 Hook

使用 `client.on(event_name, callback)` 注册 hook：

```python
client = remotable_function.Client(server_url="ws://localhost:8000")

# 注册单个 hook
client.on("before_tool_execute", my_before_hook)

# 注册多个 hook（按注册顺序执行）
client.on("after_tool_execute", log_result)
client.on("after_tool_execute", count_calls)
client.on("after_tool_execute", notify_admin)
```

### Hook 执行顺序

对于每个工具调用：

1. **所有 `before_tool_execute` hooks**（按注册顺序）
   - 如果任何 hook 抛出异常，工具不会执行，直接跳到 `tool_error`

2. **工具执行**

3. 如果成功：
   - **所有 `tool_executed` hooks**（向后兼容）
   - **所有 `after_tool_execute` hooks**

4. 如果失败：
   - **所有 `tool_error` hooks**

## 高级用法

### 1. 参数修改

`before_tool_execute` 可以修改参数：

```python
async def add_timestamp(tool_name, args, context):
    """自动添加时间戳"""
    if tool_name == "filesystem.write_file":
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 修改 args（是可变字典）
        original = args.get("content", "")
        args["content"] = f"[{timestamp}] {original}"

client.on("before_tool_execute", add_timestamp)
```

### 2. 取消执行

通过抛出异常来阻止工具执行：

```python
async def block_dangerous_commands(tool_name, args, context):
    """阻止危险命令"""
    if tool_name == "shell.execute":
        cmd = args.get("command", "")
        if "rm -rf" in cmd:
            raise PermissionError("危险命令已被阻止")

client.on("before_tool_execute", block_dangerous_commands)
```

### 3. 条件性 Hook

使用条件判断来针对特定工具：

```python
async def log_file_operations(tool_name, args, result, context):
    """只记录文件系统操作"""
    if tool_name.startswith("filesystem."):
        logger.info(f"文件操作: {tool_name} - {args}")

client.on("after_tool_execute", log_file_operations)
```

### 4. 组合多个 Hook

创建 Hook 链来实现复杂逻辑：

```python
# Hook 1: 验证权限
async def check_permission(tool_name, args, context):
    if not has_permission(context.client_id, tool_name):
        raise PermissionError("无权限")

# Hook 2: 记录审计日志
async def audit_log(tool_name, args, context):
    save_audit_log(context.client_id, tool_name, args)

# Hook 3: 限流
async def rate_limit(tool_name, args, context):
    if not check_rate_limit(context.client_id):
        raise Exception("请求过于频繁")

# 按顺序注册
client.on("before_tool_execute", check_permission)
client.on("before_tool_execute", audit_log)
client.on("before_tool_execute", rate_limit)
```

## 完整示例

参见 [samples/hook_example.py](../samples/hook_example.py) 获取完整的可运行示例。

## 最佳实践

1. **保持 Hook 轻量**: Hook 会在每次工具调用时执行，避免耗时操作
2. **异常处理**: Hook 中的异常会传播，使用 try-except 处理预期的错误
3. **避免修改 result**: 在 `after_tool_execute` 中不要修改 result（已经发送给服务器）
4. **使用 context**: 利用 context 获取 request_id、client_id 等元数据
5. **文档化**: 清楚记录你的 Hook 做了什么，特别是修改参数的 Hook

## 与工具自身验证的区别

- **工具验证**: 在工具类的 `execute()` 方法内部，是工具自身的逻辑
- **Hook**: 在客户端层面，跨所有工具统一应用，更适合横切关注点（日志、权限、统计等）

建议：
- 工具特定的业务逻辑 → 放在工具内部
- 跨工具的通用逻辑 → 使用 Hook

## ToolContext 对象

所有 hook 都会接收 `ToolContext` 对象：

```python
@dataclass
class ToolContext:
    client_id: str       # 客户端 ID
    request_id: str      # 请求 ID
    timestamp: int       # 时间戳
    metadata: dict       # 额外的元数据
```

## 注意事项

1. **向后兼容**: `tool_executed` hook 保留但建议使用 `after_tool_execute`
2. **异步要求**: 所有 hook 必须是 async 函数
3. **执行顺序**: 同一事件的多个 hook 按注册顺序执行
4. **参数可变性**: `args` 在 `before_tool_execute` 中是可修改的，但要小心副作用
5. **错误传播**: Hook 中的异常会中断执行流程

## 相关文档

- [客户端 API 文档](./client_api.md)
- [工具开发指南](./tool_development.md)
- [安全最佳实践](./security.md)
