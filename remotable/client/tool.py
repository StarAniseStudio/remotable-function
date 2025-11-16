"""
Tool Base Class - Base class for client-side tools.
"""

import logging
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod

from ..core.types import ToolDefinition, ParameterSchema, ToolContext, ToolExample

logger = logging.getLogger(__name__)


class Tool(ABC):
    """
    Base class for client-side tools.

    Subclasses must implement:
    - name: Tool name
    - description: Tool description
    - execute(): Tool execution logic

    Optional attributes:
    - namespace: Tool namespace (default: "default")
    - parameters: Parameter schemas
    - permissions: Required permissions
    - tags: Tool tags
    - examples: Usage examples
    - timeout: Execution timeout

    Example:
        class ReadFileTool(Tool):
            name = "read_file"
            description = "Read file contents"
            namespace = "filesystem"

            parameters = [
                ParameterSchema(
                    name="path",
                    type=ParameterType.STRING,
                    description="File path",
                    required=True
                )
            ]

            async def execute(self, context: ToolContext, **kwargs) -> Dict[str, Any]:
                path = kwargs["path"]
                with open(path, "r") as f:
                    content = f.read()
                return {"content": content, "size": len(content)}
    """

    # Tool metadata (must be overridden by subclasses)
    name: str = ""
    description: str = ""
    namespace: str = "default"

    # Optional metadata
    parameters: List[ParameterSchema] = []
    permissions: List[str] = []
    tags: List[str] = []
    examples: List[ToolExample] = []
    timeout: int = 30

    def __init__(self):
        """Initialize tool."""
        if not self.name:
            raise ValueError(f"{self.__class__.__name__} must define 'name'")
        if not self.description:
            raise ValueError(f"{self.__class__.__name__} must define 'description'")

    @property
    def full_name(self) -> str:
        """Get full tool name (namespace.name)."""
        return f"{self.namespace}.{self.name}"

    @abstractmethod
    async def execute(self, context: ToolContext, **kwargs) -> Any:
        """
        Execute the tool.

        Args:
            context: Execution context
            **kwargs: Tool arguments

        Returns:
            Tool execution result

        Raises:
            ValueError: If arguments are invalid
            PermissionError: If permissions are insufficient
            Exception: If execution fails
        """
        pass

    def validate_args(self, kwargs: Dict[str, Any]) -> None:
        """
        Validate tool arguments against parameter schemas.

        Args:
            kwargs: Tool arguments

        Raises:
            ValueError: If validation fails
        """
        # Check required parameters
        for param in self.parameters:
            if param.required and param.name not in kwargs:
                raise ValueError(f"Missing required parameter: {param.name}")

        # Check parameter types (basic validation)
        for param in self.parameters:
            if param.name in kwargs:
                value = kwargs[param.name]

                # Type validation would go here
                # For now, just check None for required params
                if param.required and value is None:
                    raise ValueError(f"Parameter '{param.name}' cannot be None")

    def to_definition(self) -> ToolDefinition:
        """
        Convert tool to ToolDefinition for registration.

        Returns:
            ToolDefinition instance
        """
        return ToolDefinition(
            name=self.name,
            description=self.description,
            namespace=self.namespace,
            parameters=self.parameters,
            permissions=self.permissions,
            tags=self.tags,
            examples=self.examples,
            timeout=self.timeout
        )

    async def __call__(self, context: ToolContext, **kwargs) -> Any:
        """
        Call the tool (validates args then executes).

        Args:
            context: Execution context
            **kwargs: Tool arguments

        Returns:
            Tool execution result
        """
        # Validate arguments
        self.validate_args(kwargs)

        # Execute
        try:
            result = await self.execute(context, **kwargs)
            return result
        except Exception as e:
            # Don't log here - let the client handle logging
            raise

    def __repr__(self) -> str:
        """String representation."""
        return f"Tool(name={self.full_name}, params={len(self.parameters)})"
