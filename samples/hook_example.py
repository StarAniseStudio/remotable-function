#!/usr/bin/env python3
"""
示例：使用客户端的工具调用 Hook

演示如何使用 before_tool_execute, after_tool_execute, 和 tool_error hooks
来监听和拦截工具调用。
"""

import asyncio
import sys
import os

# Add remotable to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import remotable_function
from remotable_function.client.tools import ReadFileTool, WriteFileTool


async def main():
    """演示 Hook 功能"""

    print("=" * 60)
    print("Remotable 工具调用 Hook 示例")
    print("=" * 60)
    print()

    # 创建客户端
    client = remotable_function.Client(
        server_url="ws://localhost:8000",
        client_id="hook-demo-client"
    )

    # 注册工具
    client.register_tool(ReadFileTool())
    client.register_tool(WriteFileTool())

    print("✅ 已注册工具:")
    for tool_name in client.list_tools():
        print(f"  - {tool_name}")
    print()

    # ========================================
    # Hook 1: 执行前记录日志
    # ========================================
    async def log_before_execute(tool_name, args, context):
        """在工具执行前记录日志"""
        print(f"📝 [BEFORE] 工具: {tool_name}")
        print(f"   参数: {args}")
        print(f"   请求ID: {context.request_id}")
        print()

    client.on("before_tool_execute", log_before_execute)

    # ========================================
    # Hook 2: 执行后记录结果
    # ========================================
    async def log_after_execute(tool_name, args, result, context):
        """在工具执行后记录结果"""
        print(f"✅ [AFTER] 工具: {tool_name}")
        print(f"   结果: {result}")
        print()

    client.on("after_tool_execute", log_after_execute)

    # ========================================
    # Hook 3: 捕获错误
    # ========================================
    async def log_tool_error(tool_name, args, error, context):
        """捕获工具执行错误"""
        print(f"❌ [ERROR] 工具: {tool_name}")
        print(f"   错误: {error}")
        print(f"   参数: {args}")
        print()

    client.on("tool_error", log_tool_error)

    # ========================================
    # Hook 4: 安全拦截 - 阻止删除操作
    # ========================================
    async def security_check(tool_name, args, context):
        """安全检查：阻止某些敏感操作"""
        # 示例：阻止写入系统目录
        if tool_name == "filesystem.write_file":
            path = args.get("path", "")
            if path.startswith("/etc/") or path.startswith("/sys/"):
                raise PermissionError(f"🛡️ 安全策略：禁止写入系统目录 {path}")

    client.on("before_tool_execute", security_check)

    # ========================================
    # Hook 5: 统计工具调用次数
    # ========================================
    call_stats = {}

    async def count_calls(tool_name, args, result, context):
        """统计每个工具的调用次数"""
        call_stats[tool_name] = call_stats.get(tool_name, 0) + 1

    client.on("after_tool_execute", count_calls)

    # ========================================
    # Hook 6: 参数修改示例（高级用法）
    # ========================================
    async def add_timestamp_to_write(tool_name, args, context):
        """在写入文件时自动添加时间戳"""
        if tool_name == "filesystem.write_file":
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 修改参数（注意：args 是可变的 dict）
            original_content = args.get("content", "")
            args["content"] = f"[{timestamp}] {original_content}"

            print(f"🕐 自动添加时间戳到文件写入")

    client.on("before_tool_execute", add_timestamp_to_write)

    # ========================================
    # 连接并运行
    # ========================================
    print("🔌 连接到服务器...")
    await client.connect()

    print("🟢 客户端运行中...")
    print("   服务器将调用工具，观察 Hook 输出")
    print()
    print("按 Ctrl+C 退出")
    print("=" * 60)
    print()

    try:
        # 保持运行
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("📊 工具调用统计:")
        for tool_name, count in call_stats.items():
            print(f"  {tool_name}: {count} 次")
        print("=" * 60)
        print()

        print("🔌 断开连接...")
        await client.disconnect()
        print("✅ 已退出")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n退出中...")
        sys.exit(0)
