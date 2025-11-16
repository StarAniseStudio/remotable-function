#!/usr/bin/env python3
"""
Remotable Tools Adapter for Agno

这个模块将 Remotable 的远程工具适配为 Agno Agent 可以使用的工具。
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import remotable
remotable.configure(role="server")

logger = logging.getLogger(__name__)


class RemotableTools:
    """
    Remotable 工具适配器

    将 Remotable Gateway 的远程工具暴露给 Agno Agent。
    """

    def __init__(
        self,
        gateway: Optional[remotable.Gateway] = None,
        client_id: str = "ai-agent-tools",
        timeout: int = 30
    ):
        """
        初始化 Remotable 工具适配器

        Args:
            gateway: Gateway 实例（直接传入）
            client_id: 目标客户端 ID
            timeout: 工具调用超时时间（秒）
        """
        self.client_id = client_id
        self.timeout = timeout
        self.gateway = gateway
        self._initialized = gateway is not None

    async def _ensure_gateway(self):
        """确保 Gateway 已初始化（Agent 内部模式）"""
        if not self._initialized:
            # 这里我们假设 Gateway 已经在外部启动
            # Agent 通过 HTTP/WebSocket 与 Gateway 通信
            # 所以我们创建一个轻量级的 Gateway 客户端
            self._initialized = True
            logger.info(f"Remotable Tools initialized for client: {self.client_id}")

    def _get_gateway(self) -> remotable.Gateway:
        """获取 Gateway 实例（需要外部传入或创建）"""
        if self.gateway is None:
            raise RuntimeError(
                "Gateway not set. Please call set_gateway() first or ensure Gateway is running."
            )
        return self.gateway

    def set_gateway(self, gateway: remotable.Gateway):
        """设置 Gateway 实例"""
        self.gateway = gateway
        self._initialized = True

    # ==================== 文件系统工具 ====================

    async def read_file(self, path: str, encoding: str = "utf-8") -> str:
        """
        读取文件内容

        Args:
            path: 文件路径
            encoding: 文件编码（默认 utf-8）

        Returns:
            文件内容字符串
        """
        await self._ensure_gateway()
        gateway = self._get_gateway()

        try:
            result = await gateway.call_tool(
                client_id=self.client_id,
                tool="filesystem.read_file",
                args={"path": path, "encoding": encoding},
                timeout=self.timeout
            )
            return f"文件读取成功！\n路径: {result['path']}\n大小: {result['size']} bytes\n\n内容:\n{result['content']}"
        except Exception as e:
            return f"读取文件失败: {e}"

    async def write_file(
        self,
        path: str,
        content: str,
        encoding: str = "utf-8",
        append: bool = False
    ) -> str:
        """
        写入文件

        Args:
            path: 文件路径
            content: 文件内容
            encoding: 文件编码（默认 utf-8）
            append: 是否追加模式（默认 False）

        Returns:
            操作结果描述
        """
        await self._ensure_gateway()
        gateway = self._get_gateway()

        try:
            result = await gateway.call_tool(
                client_id=self.client_id,
                tool="filesystem.write_file",
                args={
                    "path": path,
                    "content": content,
                    "encoding": encoding,
                    "append": append
                },
                timeout=self.timeout
            )
            action = "追加" if result.get('appended') else "写入"
            return f"文件{action}成功！\n路径: {result['path']}\n大小: {result['size']} bytes"
        except Exception as e:
            return f"写入文件失败: {e}"

    async def list_directory(self, path: str, recursive: bool = False) -> str:
        """
        列出目录内容

        Args:
            path: 目录路径
            recursive: 是否递归列出（默认 False）

        Returns:
            目录内容描述
        """
        await self._ensure_gateway()
        gateway = self._get_gateway()

        try:
            result = await gateway.call_tool(
                client_id=self.client_id,
                tool="filesystem.list_directory",
                args={"path": path, "recursive": recursive},
                timeout=self.timeout
            )

            files = result.get('files', [])
            directories = result.get('directories', [])

            output = [f"目录: {result['path']}"]
            output.append(f"总计: {result['count']} 个项目\n")

            if directories:
                output.append(f"📁 目录 ({len(directories)} 个):")
                for d in directories[:10]:  # 只显示前 10 个
                    output.append(f"  - {d['name']}")
                if len(directories) > 10:
                    output.append(f"  ... 还有 {len(directories) - 10} 个")
                output.append("")

            if files:
                output.append(f"📄 文件 ({len(files)} 个):")
                for f in files[:10]:  # 只显示前 10 个
                    output.append(f"  - {f['name']} ({f['size']} bytes)")
                if len(files) > 10:
                    output.append(f"  ... 还有 {len(files) - 10} 个")

            return "\n".join(output)
        except Exception as e:
            return f"列出目录失败: {e}"

    async def delete_file(self, path: str, recursive: bool = False) -> str:
        """
        删除文件或目录

        Args:
            path: 文件/目录路径
            recursive: 是否递归删除目录（默认 False）

        Returns:
            操作结果描述
        """
        await self._ensure_gateway()
        gateway = self._get_gateway()

        try:
            result = await gateway.call_tool(
                client_id=self.client_id,
                tool="filesystem.delete",
                args={"path": path, "recursive": recursive},
                timeout=self.timeout
            )
            item_type = result['type']
            return f"删除成功！\n类型: {item_type}\n路径: {result['path']}"
        except Exception as e:
            return f"删除失败: {e}"

    # ==================== Shell 工具 ====================

    async def execute_shell(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout: int = 30
    ) -> str:
        """
        执行 Shell 命令

        Args:
            command: Shell 命令
            cwd: 工作目录（可选）
            timeout: 超时时间（秒）

        Returns:
            命令执行结果
        """
        await self._ensure_gateway()
        gateway = self._get_gateway()

        try:
            result = await gateway.call_tool(
                client_id=self.client_id,
                tool="shell.execute",
                args={"command": command, "cwd": cwd, "timeout": timeout},
                timeout=self.timeout
            )

            output = [f"命令: {command}"]
            output.append(f"返回码: {result['returncode']}\n")

            if result.get('stdout'):
                output.append("标准输出:")
                output.append(result['stdout'])

            if result.get('stderr'):
                output.append("\n标准错误:")
                output.append(result['stderr'])

            return "\n".join(output)
        except Exception as e:
            return f"执行命令失败: {e}"

    # ==================== 系统信息工具 ====================

    async def get_system_info(self) -> str:
        """
        获取系统信息

        Returns:
            系统信息描述
        """
        await self._ensure_gateway()
        gateway = self._get_gateway()

        try:
            result = await gateway.call_tool(
                client_id=self.client_id,
                tool="system.get_system_info",
                args={},
                timeout=self.timeout
            )

            sys_info = result.get('system', {})
            user_info = result.get('user', {})
            net_info = result.get('network', {})
            env_info = result.get('environment', {})

            output = ["=== 系统信息 ===\n"]
            output.append("📱 系统:")
            output.append(f"  操作系统: {sys_info.get('system', 'N/A')}")
            output.append(f"  主机名: {sys_info.get('node', 'N/A')}")
            output.append(f"  版本: {sys_info.get('release', 'N/A')}")
            output.append(f"  架构: {sys_info.get('machine', 'N/A')}")
            output.append(f"  Python: {sys_info.get('python_version', 'N/A')}\n")

            output.append("👤 用户:")
            output.append(f"  用户名: {user_info.get('username', 'N/A')}")
            output.append(f"  主目录: {user_info.get('home_dir', 'N/A')}")
            output.append(f"  当前目录: {user_info.get('current_dir', 'N/A')}\n")

            output.append("🌐 网络:")
            output.append(f"  主机: {net_info.get('hostname', 'N/A')}")
            output.append(f"  IP地址: {net_info.get('ip_address', 'N/A')}")

            return "\n".join(output)
        except Exception as e:
            return f"获取系统信息失败: {e}"

    # ==================== 工具注册辅助方法 ====================

    def get_tool_functions(self):
        """
        获取所有工具函数，用于注册到 Agno Agent

        Returns:
            工具函数列表
        """
        return [
            self.read_file,
            self.write_file,
            self.list_directory,
            self.delete_file,
            self.execute_shell,
            self.get_system_info,
        ]
