"""Value normalization for TOON encoding."""

import math
from datetime import date, datetime
from decimal import Decimal
from typing import Any, List

from .types import JsonValue


def normalize_value(value: Any) -> JsonValue:
    """Normalize a value to JSON-compatible type.

    Args:
        value: Input value

    Returns:
        JSON-compatible value
    """
    # Handle None and booleans
    if value is None or isinstance(value, bool):
        return value

    # Handle numbers
    if isinstance(value, (int, float)):
        # Convert -0 to 0
        if value == 0:
            return 0
        # Convert NaN and Infinity to null
        if math.isnan(value) or math.isinf(value):
            return None
        return value

    # Handle Decimal
    if isinstance(value, Decimal):
        if not value.is_finite():
            return None
        return float(value)

    # Handle strings
    if isinstance(value, str):
        return value

    # Handle dates
    if isinstance(value, (date, datetime)):
        return value.isoformat()

    # Handle lists/tuples
    if isinstance(value, (list, tuple)):
        return [normalize_value(item) for item in value]

    # Handle sets
    if isinstance(value, set):
        return [normalize_value(item) for item in value]

    # Handle dicts
    if isinstance(value, dict):
        return {str(key): normalize_value(val) for key, val in value.items()}

    # Handle Pydantic BaseModel (v2 and v1)
    try:
        # Pydantic v2: has model_dump
        if hasattr(value, "model_dump") and callable(getattr(value, "model_dump")):
            dumped = value.model_dump()
            return {str(k): normalize_value(v) for k, v in dumped.items()}
        # Pydantic v1: has dict()
        if hasattr(value, "dict") and callable(getattr(value, "dict")):
            dumped = value.dict()
            return {str(k): normalize_value(v) for k, v in dumped.items()}
    except Exception:
        pass

    # Handle callables, undefined, symbols -> null
    if callable(value):
        return None

    # Try to convert to string, otherwise null
    try:
        if hasattr(value, "__dict__"):
            return None
        return str(value)
    except Exception:
        return None


def is_json_primitive(value: Any) -> bool:
    """Check if value is a JSON primitive."""
    return value is None or isinstance(value, (bool, int, float, str))


def is_json_array(value: Any) -> bool:
    """Check if value is an array."""
    return isinstance(value, list)


def is_json_object(value: Any) -> bool:
    """Check if value is an object (dict but not a list)."""
    return isinstance(value, dict) and not isinstance(value, list)


def is_array_of_primitives(arr: List[Any]) -> bool:
    """Check if all array elements are primitives."""
    return all(is_json_primitive(item) for item in arr)


def is_array_of_arrays(arr: List[Any]) -> bool:
    """Check if all array elements are arrays."""
    return all(is_json_array(item) for item in arr)


def is_array_of_objects(arr: List[Any]) -> bool:
    """Check if all array elements are objects."""
    return all(is_json_object(item) for item in arr)
