#!/usr/bin/env python3
"""
Remotable Function AI Agent

支持两种模式：
1. LLM 模式 - 使用 Agno + OpenAI（需要 API Key）
2. Simple 模式 - 基于关键词匹配（无需 API Key）
"""

import asyncio
import os
from typing import Optional

from remotable_tools import RemotableTools


class RemotableAgent:
    """
    Remotable Function AI Agent

    可以使用 LLM 或简单规则处理用户请求
    """

    def __init__(
        self,
        gateway,
        client_id: str
    ):
        """
        初始化 Agent

        Args:
            gateway: Remotable Function Gateway 实例
            client_id: 目标客户端 ID
        """
        self.gateway = gateway
        self.client_id = client_id

        # Check for API keys - OpenRouter or OpenAI
        self.has_openrouter = bool(os.getenv("OPENROUTER_API_KEY"))
        self.has_openai = bool(os.getenv("OPENAI_API_KEY"))
        self.use_llm = self.has_openrouter or self.has_openai

        # Initialize tools
        self.tools = RemotableTools(gateway=gateway, client_id=client_id)

        # Initialize LLM agent if available
        if self.use_llm:
            self._init_llm_agent()
        else:
            self.llm_agent = None

    def _init_llm_agent(self):
        """初始化 LLM Agent（Agno）- 支持 OpenRouter 和 OpenAI"""
        try:
            from agno.agent import Agent

            from agno.models.openrouter import OpenRouter

            model = OpenRouter(id="google/gemini-2.5-flash")
            model_name = "OpenRouter (Gemini 2.5 Flash)"

            print(f"使用模型: {model_name}")

            self.llm_agent = Agent(
                name="RemotableAssistant",
                model=model,
                tools=self.tools.get_tool_functions(),
                instructions=[
                    "你是一个 AI 助手，拥有远程执行工具的能力。",
                    "",
                    "核心原则：",
                    "1. **优先执行，而不是解释** - 当用户请求操作时，直接调用工具执行，不要只是告诉用户如何操作",
                    "2. **主动使用工具** - 不要问用户是否需要执行，直接执行并展示结果",
                    "3. **实际操作优先** - 用户问「文件权限是什么」时，调用 execute_shell('ls -l 文件名')，而不是解释如何查看",
                    "",
                    "可用工具：",
                    "- read_file - 读取文件内容",
                    "- write_file - 写入文件",
                    "- list_directory - 列出目录内容",
                    "- delete_file - 删除文件/目录",
                    "- execute_shell - 执行 Shell 命令（用于获取系统信息、查看权限等）",
                    "- get_system_info - 获取系统信息",
                    "",
                    "示例：",
                    "- 用户：「查看 /tmp/test.txt 的权限」→ 调用 execute_shell('ls -l /tmp/test.txt')",
                    "- 用户：「列出 /tmp 目录」→ 调用 list_directory('/tmp')",
                    "- 用户：「系统信息」→ 调用 get_system_info()",
                    "",
                    "只有在以下情况才不执行：",
                    "- 危险操作（删除、覆盖重要文件）需要确认",
                    "- 用户明确只是询问如何操作，而不是要求执行",
                ],
                markdown=True,
                show_tool_calls=True,
                add_history_to_messages=True,
                num_history_responses=3,
            )
        except ImportError:
            print("Agno not installed. Falling back to simple mode.")
            self.llm_agent = None
            self.use_llm = False

    async def process(self, user_input: str) -> str:
        """
        处理用户输入

        Args:
            user_input: 用户输入的文本

        Returns:
            Agent 的回复
        """
        if self.use_llm and self.llm_agent:
            return await self._process_with_llm(user_input)
        else:
            return await self._process_simple(user_input)

    async def _process_with_llm(self, user_input: str) -> str:
        """使用 LLM 处理"""
        try:
            # Run agent asynchronously (for async tools)
            response = await self.llm_agent.arun(user_input)

            if response and response.content:
                return response.content
            else:
                return "抱歉，我没有理解你的请求。"

        except Exception as e:
            return f"处理请求时出错: {e}"

    async def _process_simple(self, user_input: str) -> str:
        """简单模式处理（关键词匹配）"""
        user_input = user_input.lower()

        # 读取文件
        if "读取" in user_input or "read" in user_input or "查看文件" in user_input:
            path = self._extract_path(user_input)
            if path:
                return await self.tools.read_file(path)
            return "请指定要读取的文件路径\n例如：读取 /etc/hosts"

        # 写入文件
        elif "写入" in user_input or "创建文件" in user_input or "write" in user_input:
            return "写入文件示例：写入 /tmp/test.txt 内容 Hello World"

        # 列出目录
        elif any(kw in user_input for kw in ["列出", "list", "查看目录", "ls", "dir"]):
            path = self._extract_path(user_input)
            if path:
                return await self.tools.list_directory(path)
            return "请指定要列出的目录路径\n例如：列出 /tmp"

        # 系统信息
        elif "系统" in user_input or "system" in user_input or "信息" in user_input:
            return await self.tools.get_system_info()

        # 执行命令
        elif "执行" in user_input or "运行" in user_input or "命令" in user_input:
            # 简单提取命令（仅作演示）
            return "执行命令示例：执行 ls -la /tmp"

        # 帮助
        elif "帮助" in user_input or "help" in user_input:
            return """
📖 可用命令：

文件操作：
  • 读取 <path>       - 读取文件（例：读取 /etc/hosts）
  • 列出 <path>       - 列出目录（例：列出 /tmp）

系统操作：
  • 系统信息          - 获取客户端系统信息

其他：
  • 帮助              - 显示此帮助信息
  • 退出              - 退出程序

💡 提示：如果设置了 OPENAI_API_KEY，可以使用自然语言！
"""

        else:
            return f"我不太理解你的意思。输入 '帮助' 查看可用命令。\n\n你说的是：{user_input}"

    def _extract_path(self, text: str) -> Optional[str]:
        """从文本中提取文件路径"""
        for word in text.split():
            if "/" in word:
                # 清理标点符号
                path = word.strip("，。！?、")
                return path
        return None
