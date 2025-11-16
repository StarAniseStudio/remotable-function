"""
Shell Tool - Execute shell commands.
"""

import asyncio
import logging
from typing import Dict, Any

from ...core.types import ToolContext, ParameterSchema, ParameterType
from ..tool import Tool

logger = logging.getLogger(__name__)


class ShellExecuteTool(Tool):
    """Execute shell commands."""

    name = "execute"
    description = "Execute a shell command"
    namespace = "shell"
    permissions = ["shell.execute"]
    tags = ["shell", "command"]
    timeout = 60  # Shell commands may take longer

    parameters = [
        ParameterSchema(
            name="command",
            type=ParameterType.STRING,
            description="Shell command to execute",
            required=True
        ),
        ParameterSchema(
            name="cwd",
            type=ParameterType.STRING,
            description="Working directory (default: current directory)",
            required=False
        ),
        ParameterSchema(
            name="timeout",
            type=ParameterType.INTEGER,
            description="Command timeout in seconds (default: 30)",
            required=False
        ),
    ]

    async def execute(self, context: ToolContext, **kwargs) -> Dict[str, Any]:
        """
        Execute shell command.

        Args:
            command: Shell command to execute
            cwd: Working directory (optional)
            timeout: Command timeout in seconds (default: 30)

        Returns:
            {
                "stdout": str,
                "stderr": str,
                "returncode": int,
                "command": str
            }
        """
        command = kwargs["command"]
        cwd = kwargs.get("cwd")
        timeout = kwargs.get("timeout", 30)

        try:
            # Create subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )

            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise TimeoutError(f"Command timeout after {timeout}s")

            # Decode output
            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            return {
                "stdout": stdout_str,
                "stderr": stderr_str,
                "returncode": process.returncode,
                "command": command
            }

        except FileNotFoundError:
            raise ValueError(f"Command not found: {command}")
        except PermissionError:
            raise PermissionError(f"Permission denied to execute: {command}")
        except Exception as e:
            raise Exception(f"Failed to execute command: {e}")
