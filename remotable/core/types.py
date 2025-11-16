"""
Shared type definitions for Remotable.

These types are used by both server and client.
"""

from typing import Any, Dict, List, Optional, Literal
from dataclasses import dataclass, field, asdict
from enum import Enum


class ParameterType(str, Enum):
    """Parameter types for tool definitions"""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


@dataclass
class ParameterSchema:
    """Tool parameter schema definition"""
    name: str
    type: ParameterType
    description: str
    required: bool = False
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None
    items: Optional[Dict[str, Any]] = None  # For array type

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "name": self.name,
            "type": self.type.value if isinstance(self.type, ParameterType) else self.type,
            "description": self.description,
            "required": self.required,
        }

        if self.default is not None:
            result["default"] = self.default
        if self.enum is not None:
            result["enum"] = self.enum
        if self.min_value is not None:
            result["min_value"] = self.min_value
        if self.max_value is not None:
            result["max_value"] = self.max_value
        if self.pattern is not None:
            result["pattern"] = self.pattern
        if self.items is not None:
            result["items"] = self.items

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ParameterSchema":
        """Create from dictionary"""
        return cls(
            name=data["name"],
            type=ParameterType(data["type"]) if isinstance(data["type"], str) else data["type"],
            description=data["description"],
            required=data.get("required", False),
            default=data.get("default"),
            enum=data.get("enum"),
            min_value=data.get("min_value"),
            max_value=data.get("max_value"),
            pattern=data.get("pattern"),
            items=data.get("items"),
        )


@dataclass
class ToolExample:
    """Example usage of a tool"""
    description: str
    args: Dict[str, Any]
    expected_result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "description": self.description,
            "args": self.args,
        }
        if self.expected_result is not None:
            result["expected_result"] = self.expected_result
        return result


@dataclass
class ToolDefinition:
    """Tool definition (used for registration and discovery)"""
    name: str
    description: str
    namespace: str = "default"
    parameters: List[ParameterSchema] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    examples: List[ToolExample] = field(default_factory=list)
    timeout: int = 30  # Default timeout in seconds

    @property
    def full_name(self) -> str:
        """Get full tool name: namespace.name"""
        return f"{self.namespace}.{self.name}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for transmission"""
        return {
            "name": self.full_name,
            "description": self.description,
            "namespace": self.namespace,
            "parameters": [p.to_dict() for p in self.parameters],
            "permissions": self.permissions,
            "tags": self.tags,
            "examples": [e.to_dict() for e in self.examples],
            "timeout": self.timeout,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolDefinition":
        """Create from dictionary"""
        # Parse full name to extract namespace and name
        full_name = data.get("name", "")
        if "." in full_name:
            namespace, name = full_name.rsplit(".", 1)
        else:
            namespace = "default"
            name = full_name

        return cls(
            name=name,
            description=data["description"],
            namespace=namespace,
            parameters=[
                ParameterSchema.from_dict(p)
                for p in data.get("parameters", [])
            ],
            permissions=data.get("permissions", []),
            tags=data.get("tags", []),
            examples=[
                ToolExample(
                    description=e["description"],
                    args=e["args"],
                    expected_result=e.get("expected_result"),
                )
                for e in data.get("examples", [])
            ],
            timeout=data.get("timeout", 30),
        )


@dataclass
class ClientInfo:
    """Client information (sent during registration)"""
    client_id: str
    name: str
    version: str
    platform: str
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClientInfo":
        """Create from dictionary"""
        return cls(
            client_id=data["client_id"],
            name=data["name"],
            version=data["version"],
            platform=data["platform"],
            capabilities=data.get("capabilities", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ToolContext:
    """Context information passed to tool execution"""
    client_id: str
    request_id: str
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


# Connection states
class ConnectionState(str, Enum):
    """Connection state enumeration"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    DISCONNECTING = "disconnecting"


# Tool execution states
class ToolExecutionState(str, Enum):
    """Tool execution state"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
