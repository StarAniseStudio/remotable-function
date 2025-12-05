"""
Parameter validation for Remotable.

Provides validation utilities for tool parameters.
"""

import logging
import re
from typing import Any, Dict, List, Optional
from .types import ParameterSchema, ParameterType

logger = logging.getLogger(__name__)


class ValidationError(ValueError):
    """Parameter validation error."""

    def __init__(self, parameter: str, message: str):
        """
        Initialize validation error.

        Args:
            parameter: Parameter name
            message: Error message
        """
        self.parameter = parameter
        super().__init__(f"Parameter '{parameter}': {message}")


class ParameterValidator:
    """
    Parameter validator.

    Validates tool parameters against their schemas.
    """

    @staticmethod
    def validate(args: Dict[str, Any], schemas: List[ParameterSchema]) -> Dict[str, Any]:
        """
        Validate parameters against schemas.

        Args:
            args: Parameter values
            schemas: Parameter schemas

        Returns:
            Validated and coerced parameters

        Raises:
            ValidationError: If validation fails
        """
        validated = {}
        schema_dict = {s.name: s for s in schemas}

        # Check for required parameters
        for schema in schemas:
            if schema.required and schema.name not in args:
                raise ValidationError(schema.name, f"Required parameter missing")

        # Validate each provided parameter
        for name, value in args.items():
            if name not in schema_dict:
                logger.warning(f"Unknown parameter: {name}")
                validated[name] = value  # Pass through unknown parameters
                continue

            schema = schema_dict[name]

            # Validate type
            validated[name] = ParameterValidator._validate_type(name, value, schema)

            # Validate enum
            if schema.enum is not None:
                validated[name] = ParameterValidator._validate_enum(
                    name, validated[name], schema.enum
                )

            # Validate range (for numbers)
            if schema.type in (ParameterType.INTEGER, ParameterType.NUMBER):
                validated[name] = ParameterValidator._validate_range(
                    name, validated[name], schema.min_value, schema.max_value
                )

            # Validate pattern (for strings)
            if schema.type == ParameterType.STRING and schema.pattern:
                validated[name] = ParameterValidator._validate_pattern(
                    name, validated[name], schema.pattern
                )

        # Add default values for missing optional parameters
        for schema in schemas:
            if not schema.required and schema.name not in validated and schema.default is not None:
                validated[schema.name] = schema.default

        return validated

    @staticmethod
    def _validate_type(name: str, value: Any, schema: ParameterSchema) -> Any:
        """Validate and coerce parameter type."""
        param_type = schema.type

        if param_type == ParameterType.STRING:
            if not isinstance(value, str):
                raise ValidationError(name, f"Expected string, got {type(value).__name__}")
            return value

        elif param_type == ParameterType.INTEGER:
            if isinstance(value, bool):  # bool is subclass of int
                raise ValidationError(name, f"Expected integer, got boolean")
            if not isinstance(value, int):
                # Try to coerce
                try:
                    return int(value)
                except (ValueError, TypeError):
                    raise ValidationError(name, f"Expected integer, got {type(value).__name__}")
            return value

        elif param_type == ParameterType.NUMBER:
            if isinstance(value, bool):
                raise ValidationError(name, f"Expected number, got boolean")
            if not isinstance(value, (int, float)):
                # Try to coerce
                try:
                    return float(value)
                except (ValueError, TypeError):
                    raise ValidationError(name, f"Expected number, got {type(value).__name__}")
            return value

        elif param_type == ParameterType.BOOLEAN:
            if not isinstance(value, bool):
                # Try to coerce common string values
                if isinstance(value, str):
                    lower = value.lower()
                    if lower in ("true", "1", "yes", "on"):
                        return True
                    elif lower in ("false", "0", "no", "off"):
                        return False
                raise ValidationError(name, f"Expected boolean, got {type(value).__name__}")
            return value

        elif param_type == ParameterType.ARRAY:
            if not isinstance(value, list):
                raise ValidationError(name, f"Expected array, got {type(value).__name__}")
            return value

        elif param_type == ParameterType.OBJECT:
            if not isinstance(value, dict):
                raise ValidationError(name, f"Expected object, got {type(value).__name__}")
            return value

        else:
            # Unknown type, pass through
            return value

    @staticmethod
    def _validate_enum(name: str, value: Any, enum: List[Any]) -> Any:
        """Validate enum value."""
        if value not in enum:
            raise ValidationError(name, f"Value must be one of {enum}, got '{value}'")
        return value

    @staticmethod
    def _validate_range(
        name: str, value: float, min_value: Optional[float], max_value: Optional[float]
    ) -> float:
        """Validate numeric range."""
        if min_value is not None and value < min_value:
            raise ValidationError(name, f"Value {value} is less than minimum {min_value}")
        if max_value is not None and value > max_value:
            raise ValidationError(name, f"Value {value} is greater than maximum {max_value}")
        return value

    @staticmethod
    def _validate_pattern(name: str, value: str, pattern: str) -> str:
        """Validate string pattern."""
        try:
            if not re.match(pattern, value):
                raise ValidationError(name, f"Value '{value}' does not match pattern '{pattern}'")
        except re.error as e:
            logger.error(f"Invalid regex pattern '{pattern}': {e}")
            raise ValidationError(name, f"Invalid validation pattern")
        return value


# Convenience function
def validate_parameters(args: Dict[str, Any], schemas: List[ParameterSchema]) -> Dict[str, Any]:
    """
    Validate parameters against schemas.

    Args:
        args: Parameter values
        schemas: Parameter schemas

    Returns:
        Validated parameters

    Raises:
        ValidationError: If validation fails
    """
    return ParameterValidator.validate(args, schemas)
