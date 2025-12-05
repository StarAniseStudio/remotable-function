"""
Shell Tool - Execute shell commands.
"""

import asyncio
import logging
import re
import shlex
from typing import Dict, Any, Optional, List, Pattern, Union

from ...core.types import ToolContext, ParameterSchema, ParameterType
from ..tool import Tool

logger = logging.getLogger(__name__)


class ShellExecuteTool(Tool):
    """
    Execute shell commands with security restrictions.

    Security features:
    - Command whitelist support
    - Pattern-based command validation
    - Dangerous command blocking
    - Optional argument validation
    """

    name = "execute"
    description = "Execute a shell command (with security restrictions)"
    namespace = "shell"
    permissions = ["shell.execute"]
    tags = ["shell", "command"]
    timeout = 60  # Shell commands may take longer

    # Default dangerous command patterns
    DEFAULT_DENY_PATTERNS = [
        re.compile(r"rm\s+(-rf?|--recursive)"),  # Recursive delete
        re.compile(r"dd\s+if=/dev/(zero|random)"),  # Disk wipe
        re.compile(r":(){ :|:& };:"),  # Fork bomb
        re.compile(r"mkfs\."),  # Format filesystem
        re.compile(r"\||\|\||&&|;|`|\$\("),  # Command chaining (in some contexts)
        re.compile(r">>\s*/etc/|>\s*/etc/"),  # Write to /etc
    ]

    def __init__(
        self,
        allowed_commands: Optional[Union[List[str], bool]] = None,
        allowed_patterns: Optional[List[Pattern]] = None,
        deny_patterns: Optional[List[Pattern]] = None,
        allow_shell_operators: bool = False,
    ):
        """
        Initialize Shell Execute Tool with security restrictions.

        Args:
            allowed_commands: Whitelist of allowed command names (e.g., ["ls", "pwd", "echo"])
                            If None, all commands are allowed (unless denied by patterns)
                            If False, all commands are blocked (shell execution disabled)
                            If [], empty list also blocks all commands
                            If ["*"], wildcard allows all commands (explicit allow all)
            allowed_patterns: List of regex patterns for allowed commands
            deny_patterns: List of regex patterns for denied commands (default: dangerous commands)
            allow_shell_operators: Allow shell operators like |, &&, ; (default: False)
        """
        super().__init__()

        # Handle False or empty list to mean "block all commands"
        if allowed_commands is False:
            self.allowed_commands = []  # Empty list = block all
            logger.info("Shell execution disabled: allowed_commands=False")
        elif allowed_commands and "*" in allowed_commands:
            # Wildcard "*" means allow all commands
            self.allowed_commands = None  # None = allow all
            logger.info("Shell commands set to wildcard (*) - all commands allowed")
        else:
            self.allowed_commands = allowed_commands

        self.allowed_patterns = allowed_patterns or []
        self.deny_patterns = (
            deny_patterns if deny_patterns is not None else self.DEFAULT_DENY_PATTERNS
        )
        self.allow_shell_operators = allow_shell_operators

    parameters = [
        ParameterSchema(
            name="command",
            type=ParameterType.STRING,
            description="Shell command to execute",
            required=True,
        ),
        ParameterSchema(
            name="cwd",
            type=ParameterType.STRING,
            description="Working directory (default: current directory)",
            required=False,
        ),
        ParameterSchema(
            name="timeout",
            type=ParameterType.INTEGER,
            description="Command timeout in seconds (default: 30)",
            required=False,
        ),
    ]

    def _validate_command(self, command: str) -> None:
        """
        Validate command against security policies.

        Args:
            command: Command to validate

        Raises:
            PermissionError: If command is not allowed
        """
        # Check deny patterns first (highest priority)
        for pattern in self.deny_patterns:
            if pattern.search(command):
                raise PermissionError(
                    f"Command blocked by security policy: matches deny pattern '{pattern.pattern}'"
                )

        # Check shell operators if not allowed
        if not self.allow_shell_operators:
            dangerous_chars = ["|", "&", ";", "`", "$(", ")"]
            for char in dangerous_chars:
                if char in command:
                    raise PermissionError(
                        f"Shell operators not allowed. Found: '{char}'. "
                        f"Set allow_shell_operators=True to enable."
                    )

        # If whitelist specified, check command name
        if self.allowed_commands is not None:
            # Special case: empty list means block all commands
            if len(self.allowed_commands) == 0:
                raise PermissionError(
                    "Shell execution is disabled. Set allowed_commands to a list of commands to enable."
                )

            try:
                # Parse command to get the base command name
                parts = shlex.split(command)
                if not parts:
                    raise PermissionError("Empty command")

                cmd_name = parts[0].split("/")[-1]  # Get command name without path

                if cmd_name not in self.allowed_commands:
                    raise PermissionError(
                        f"Command '{cmd_name}' not in whitelist. "
                        f"Allowed: {', '.join(self.allowed_commands)}"
                    )
            except ValueError as e:
                raise PermissionError(f"Invalid command syntax: {e}")

        # Check allowed patterns (if specified)
        if self.allowed_patterns:
            if not any(pattern.search(command) for pattern in self.allowed_patterns):
                raise PermissionError(f"Command does not match any allowed patterns")

        logger.debug(f"Command validated: {command[:50]}...")

    async def execute(self, context: ToolContext, **kwargs) -> Dict[str, Any]:
        """
        Execute shell command with security validation.

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

        Raises:
            PermissionError: If command is not allowed by security policy
        """
        command = kwargs["command"]
        cwd = kwargs.get("cwd")
        timeout = kwargs.get("timeout", 30)

        # Validate command first
        self._validate_command(command)

        try:
            # Parse command for safer execution
            # If shell operators are not allowed, use exec form
            if not self.allow_shell_operators:
                try:
                    # Parse command into arguments
                    args = shlex.split(command)
                    if not args:
                        raise ValueError("Empty command")

                    # Create subprocess with exec form (safer, no shell)
                    process = await asyncio.create_subprocess_exec(
                        *args,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        cwd=cwd,
                    )
                except (ValueError, OSError) as e:
                    # Fall back to shell if parsing fails or command not found
                    logger.warning(f"Failed to use exec form, falling back to shell: {e}")
                    process = await asyncio.create_subprocess_shell(
                        command,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        cwd=cwd,
                    )
            else:
                # Use shell if operators are explicitly allowed
                process = await asyncio.create_subprocess_shell(
                    command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=cwd
                )

            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
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
                "command": command,
            }

        except FileNotFoundError:
            raise ValueError(f"Command not found: {command}")
        except PermissionError:
            raise PermissionError(f"Permission denied to execute: {command}")
        except Exception as e:
            raise Exception(f"Failed to execute command: {e}")


# Alias for backward compatibility
ShellTool = ShellExecuteTool
