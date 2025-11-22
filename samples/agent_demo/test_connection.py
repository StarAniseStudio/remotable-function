#!/usr/bin/env python3
"""
快速测试 agent_demo 的连接和基本功能
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import remotable_function
from remotable_function.client.tools import ReadFileTool


async def test_connection():
    """测试客户端连接"""
    print("=" * 60)
    print("测试 Agent Demo 连接")
    print("=" * 60)
    print()

    # 创建客户端
    print("1. 创建客户端...")
    client = remotable_function.Client(
        server_url="ws://localhost:8000",
        client_id="test-connection-client"
    )

    # 注册一个工具
    print("2. 注册工具...")
    client.register_tool(ReadFileTool())

    # 连接
    print("3. 连接到 Gateway...")
    try:
        await client.connect()
        print("   ✅ 连接成功！")
    except Exception as e:
        print(f"   ❌ 连接失败: {e}")
        return False

    # 等待一秒
    await asyncio.sleep(1)

    # 检查连接状态
    print("4. 检查连接状态...")
    if client._connected:
        print("   ✅ 客户端已连接")
    else:
        print("   ❌ 客户端未连接")
        return False

    # 断开连接
    print("5. 断开连接...")
    await client.disconnect()
    print("   ✅ 断开成功")

    print()
    print("=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_connection())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
