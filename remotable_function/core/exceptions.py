"""
Custom exceptions for Remotable.

Provides consistent error handling across the framework.
"""

from typing import Optional, Any, Dict


class RemotableError(Exception):
    """Base exception for all Remotable errors."""

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize Remotable error.

        Args:
            message: Error message
            code: Error code for programmatic handling
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}


class ConnectionError(RemotableError):
    """Connection-related errors."""

    pass


class AuthenticationError(RemotableError):
    """Authentication/authorization errors."""

    pass


class ValidationError(RemotableError):
    """Parameter/data validation errors."""

    def __init__(self, message: str, parameter: Optional[str] = None, value: Any = None, **kwargs):
        """
        Initialize validation error.

        Args:
            message: Error message
            parameter: Parameter that failed validation
            value: Invalid value
        """
        super().__init__(message, **kwargs)
        self.parameter = parameter
        self.value = value
        if parameter:
            self.details["parameter"] = parameter
        if value is not None:
            self.details["value"] = str(value)


class ToolError(RemotableError):
    """Tool execution errors."""

    def __init__(self, message: str, tool_name: Optional[str] = None, **kwargs):
        """
        Initialize tool error.

        Args:
            message: Error message
            tool_name: Name of the tool that failed
        """
        super().__init__(message, **kwargs)
        self.tool_name = tool_name
        if tool_name:
            self.details["tool"] = tool_name


class TimeoutError(RemotableError):
    """Operation timeout errors."""

    def __init__(self, message: str, timeout: Optional[float] = None, **kwargs):
        """
        Initialize timeout error.

        Args:
            message: Error message
            timeout: Timeout value in seconds
        """
        super().__init__(message, **kwargs)
        self.timeout = timeout
        if timeout:
            self.details["timeout"] = timeout


class RateLimitError(RemotableError):
    """Rate limiting errors."""

    def __init__(
        self,
        message: str,
        limit: Optional[int] = None,
        retry_after: Optional[float] = None,
        **kwargs,
    ):
        """
        Initialize rate limit error.

        Args:
            message: Error message
            limit: Rate limit that was exceeded
            retry_after: Seconds to wait before retry
        """
        super().__init__(message, **kwargs)
        self.limit = limit
        self.retry_after = retry_after
        if limit:
            self.details["limit"] = limit
        if retry_after:
            self.details["retry_after"] = retry_after


class ConfigurationError(RemotableError):
    """Configuration errors."""

    pass


class SecurityError(RemotableError):
    """Security-related errors."""

    pass
