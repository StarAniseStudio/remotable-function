"""
JSON-RPC 2.0 Protocol Implementation
"""

from typing import Any, Optional, Dict
from enum import IntEnum
from dataclasses import dataclass, asdict
import json


class RPCErrorCode(IntEnum):
    """JSON-RPC 2.0 Error Codes"""
    # Standard JSON-RPC errors
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # Remotable custom errors
    PERMISSION_DENIED = -32001
    TOOL_NOT_FOUND = -32002
    CLIENT_NOT_CONNECTED = -32003
    TIMEOUT = -32004
    RESOURCE_LIMIT_EXCEEDED = -32005
    TOOL_EXECUTION_FAILED = -32006
    INVALID_TOOL_ARGS = -32007
    CLIENT_DISCONNECTED = -32008


@dataclass
class RPCError:
    """RPC Error"""
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "code": self.code,
            "message": self.message
        }
        if self.data:
            result["data"] = self.data
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RPCError":
        return cls(
            code=data["code"],
            message=data["message"],
            data=data.get("data")
        )


@dataclass
class RPCRequest:
    """RPC Request"""
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    method: str = ""
    params: Dict[str, Any] = None

    def __post_init__(self):
        if self.params is None:
            self.params = {}

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "jsonrpc": self.jsonrpc,
            "method": self.method,
            "params": self.params
        }
        if self.id is not None:
            result["id"] = self.id
        return result

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RPCRequest":
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            id=data.get("id"),
            method=data["method"],
            params=data.get("params", {})
        )

    @classmethod
    def from_json(cls, json_str: str) -> "RPCRequest":
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class RPCResponse:
    """RPC Response"""
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[RPCError] = None

    def to_dict(self) -> Dict[str, Any]:
        response = {
            "jsonrpc": self.jsonrpc,
            "id": self.id
        }

        if self.error:
            response["error"] = self.error.to_dict()
        else:
            response["result"] = self.result

        return response

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RPCResponse":
        error = None
        if "error" in data:
            error = RPCError.from_dict(data["error"])

        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            id=data.get("id"),
            result=data.get("result"),
            error=error
        )

    @classmethod
    def from_json(cls, json_str: str) -> "RPCResponse":
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def success(cls, request_id: str, result: Any) -> "RPCResponse":
        """Create success response"""
        return cls(id=request_id, result=result)

    @classmethod
    def error(cls, request_id: Optional[str], code: int, message: str, data: Optional[Dict] = None) -> "RPCResponse":
        """Create error response"""
        return cls(
            id=request_id,
            error=RPCError(code=code, message=message, data=data)
        )


def validate_rpc_request(data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate JSON-RPC 2.0 request format

    Returns:
        (is_valid, error_message)
    """
    if not isinstance(data, dict):
        return False, "Request must be an object"

    if data.get("jsonrpc") != "2.0":
        return False, "Invalid jsonrpc version, must be '2.0'"

    if "method" not in data:
        return False, "Missing 'method' field"

    if not isinstance(data["method"], str):
        return False, "'method' must be a string"

    if "params" in data and not isinstance(data["params"], (dict, list)):
        return False, "'params' must be an object or array"

    return True, None


def validate_rpc_response(data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate JSON-RPC 2.0 response format

    Returns:
        (is_valid, error_message)
    """
    if not isinstance(data, dict):
        return False, "Response must be an object"

    if data.get("jsonrpc") != "2.0":
        return False, "Invalid jsonrpc version, must be '2.0'"

    if "id" not in data:
        return False, "Missing 'id' field"

    has_result = "result" in data
    has_error = "error" in data

    if has_result and has_error:
        return False, "Response must not contain both 'result' and 'error'"

    if not has_result and not has_error:
        return False, "Response must contain either 'result' or 'error'"

    return True, None
