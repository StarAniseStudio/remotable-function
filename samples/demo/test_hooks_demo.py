#!/usr/bin/env python3
"""
快速验证 Hook 功能的独立测试
"""

import asyncio
import sys
import os

# Add remotable to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from remotable_function.client_unified import Client
from remotable_function.client.tools import WriteFileTool


async def main():
    """测试 Hook 功能"""

    print("=" * 70)
    print("🪝 客户端 Hook 功能验证")
    print("=" * 70)
    print()

    # 创建客户端
    client = Client(
        server_url="ws://localhost:8000",
        client_id="hook-test-client"
    )

    # 注册工具
    client.register_tool(WriteFileTool())

    # 统计
    stats = {"before": 0, "after": 0, "errors": 0}

    print("📝 注册 Hooks...")
    print()

    # Hook 1: before_tool_execute
    async def before_hook(tool_name, args, _context):
        stats["before"] += 1
        print(f"  [cyan]🪝 BEFORE[/cyan] | 工具: {tool_name}")
        print(f"             | 参数: {args}")

    client.on("before_tool_execute", before_hook)

    # Hook 2: after_tool_execute
    async def after_hook(tool_name, _args, result, _context):
        stats["after"] += 1
        print(f"  [green]🪝 AFTER [/green] | 工具: {tool_name} - ✅ 成功")
        print(f"             | 结果: {result}")
        print()

    client.on("after_tool_execute", after_hook)

    # Hook 3: tool_error
    async def error_hook(tool_name, _args, error, _context):
        stats["errors"] += 1
        print(f"  [red]🪝 ERROR [/red] | 工具: {tool_name} - ❌ 失败")
        print(f"             | 错误: {error}")
        print()

    client.on("tool_error", error_hook)

    print("✅ Hooks 注册完成:")
    print("   - before_tool_execute")
    print("   - after_tool_execute")
    print("   - tool_error")
    print()
    print("-" * 70)
    print()

    # 模拟工具调用
    print("🔧 模拟工具调用...")
    print()

    # 模拟 WebSocket
    class MockWebSocket:
        async def send(self, data):
            pass  # 静默

    client._websocket = MockWebSocket()
    client._connected = True

    # 测试 1: 成功的调用
    request1 = {
        "jsonrpc": "2.0",
        "method": "tool.execute",
        "params": {
            "tool": "filesystem.write_file",
            "args": {
                "path": "/tmp/hook_test.txt",
                "content": "Test content from hook demo"
            }
        },
        "id": "test-1"
    }

    print("测试 1: 正常调用")
    await client._execute_tool_v2(request1)

    # 测试 2: 会失败的调用（无效路径）
    request2 = {
        "jsonrpc": "2.0",
        "method": "tool.execute",
        "params": {
            "tool": "filesystem.write_file",
            "args": {
                "path": "/invalid/\x00/path.txt",  # 无效路径
                "content": "This will fail"
            }
        },
        "id": "test-2"
    }

    print("测试 2: 失败调用（无效路径）")
    await client._execute_tool_v2(request2)

    print("-" * 70)
    print()
    print("📊 统计结果:")
    print(f"   before_tool_execute 调用: {stats['before']} 次")
    print(f"   after_tool_execute 调用:  {stats['after']} 次")
    print(f"   tool_error 调用:          {stats['errors']} 次")
    print()
    print("=" * 70)
    print()

    # 验证结果
    if stats["before"] == 2 and stats["after"] == 1 and stats["errors"] == 1:
        print("✅ 所有 Hook 正常工作！")
        print()
        print("验证:")
        print("  ✓ before_tool_execute 在每次调用前都触发（2次）")
        print("  ✓ after_tool_execute 只在成功时触发（1次）")
        print("  ✓ tool_error 只在失败时触发（1次）")
        return True
    else:
        print("❌ Hook 调用次数不符合预期")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
