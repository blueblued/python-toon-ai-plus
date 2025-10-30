"""Core TOON encoding functionality."""

from typing import Any, Optional, Dict, List

from .constants import DEFAULT_DELIMITER, DELIMITERS
from .encoders import encode_value
from .normalize import normalize_value
from .types import EncodeOptions, ResolvedEncodeOptions
from .writer import LineWriter


def _extract_model_field_description_map(value: Any, base_path: List[str] | None = None) -> Dict[str, str]:
    """Extract dotted-path comments from Pydantic BaseModel descriptions.

    Supports Pydantic v2 (model_fields, field.description) and v1 (__fields__, FieldInfo.description).
    """
    result: Dict[str, str] = {}
    if base_path is None:
        base_path = []

    def join(parts: List[str]) -> str:
        return ".".join(parts)

    # v2 BaseModel detection
    if hasattr(value, "model_fields") and isinstance(getattr(value, "model_fields"), dict):
        fields = getattr(value, "model_fields")
        for name, field in fields.items():
            desc = None
            try:
                desc = getattr(field, "description", None)
                if desc is None and hasattr(field, "json_schema_extra"):
                    extra = getattr(field, "json_schema_extra")
                    if isinstance(extra, dict):
                        desc = extra.get("description")
            except Exception:
                desc = None
            if desc:
                result[join([*base_path, name])] = str(desc)
            try:
                sub_value = getattr(value, name)
                # Recurse
                nested = _extract_model_field_description_map(sub_value, [*base_path, name])
                result.update(nested)
            except Exception:
                pass
        return result

    # v1 BaseModel detection
    if hasattr(value, "__fields__") and isinstance(getattr(value, "__fields__"), dict):
        fields = getattr(value, "__fields__")
        for name, field in fields.items():
            desc = None
            try:
                # pydantic v1 Field has .field_info.description
                fi = getattr(field, "field_info", None)
                if fi is not None:
                    desc = getattr(fi, "description", None)
            except Exception:
                desc = None
            if desc:
                result[join([*base_path, name])] = str(desc)
            try:
                sub_value = getattr(value, name)
                nested = _extract_model_field_description_map(sub_value, [*base_path, name])
                result.update(nested)
            except Exception:
                pass
        return result

    # Containers
    if isinstance(value, dict):
        for k, v in value.items():
            nested = _extract_model_field_description_map(v, [*base_path, str(k)])
            result.update(nested)
        return result

    if isinstance(value, (list, tuple)):
        for item in value:
            nested = _extract_model_field_description_map(item, base_path)
            result.update(nested)
        return result

    return result


def encode(value: Any, options: Optional[EncodeOptions] = None) -> str:
    """Encode a value into TOON format.

    Args:
        value: The value to encode (must be JSON-serializable)
        options: Optional encoding options

    Returns:
        TOON-formatted string
    """
    # Merge model-derived comments before normalization so we don't lose metadata
    incoming_options = options or {}
    model_comments_enabled = incoming_options.get("modelComments", True)
    auto_comments: Dict[str, str] = {}
    if model_comments_enabled:
        try:
            auto_comments = _extract_model_field_description_map(value)
        except Exception:
            auto_comments = {}

    # Merge with user-provided comments (user wins)
    provided_comments = incoming_options.get("comments", {}) or {}
    merged_comments = {**auto_comments, **provided_comments}

    normalized = normalize_value(value)
    # Inject merged comments into options before resolving
    merged_options: EncodeOptions = {**incoming_options, "comments": merged_comments}
    resolved_options = resolve_options(merged_options)
    writer = LineWriter(resolved_options.indent)
    encode_value(normalized, resolved_options, writer, 0)
    return writer.to_string()


def resolve_options(options: Optional[EncodeOptions]) -> ResolvedEncodeOptions:
    """Resolve encoding options with defaults.

    Args:
        options: Optional user-provided options

    Returns:
        Resolved options with defaults applied
    """
    if options is None:
        return ResolvedEncodeOptions()

    indent = options.get("indent", 2)
    delimiter = options.get("delimiter", DEFAULT_DELIMITER)
    length_marker = options.get("lengthMarker", False)
    comments = options.get("comments", {})
    comment_prefix = options.get("commentPrefix", "#")

    # Resolve delimiter if it's a key
    if delimiter in DELIMITERS:
        delimiter = DELIMITERS[delimiter]

    return ResolvedEncodeOptions(
        indent=indent,
        delimiter=delimiter,
        length_marker=length_marker,
        comments=comments,
        comment_prefix=comment_prefix,
    )
