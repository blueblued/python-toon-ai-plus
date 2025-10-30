"""Type definitions for pytoon."""

from typing import Any, Dict, List, Literal, TypedDict, Union

# JSON-compatible types
JsonPrimitive = Union[str, int, float, bool, None]
JsonObject = Dict[str, Any]
JsonArray = List[Any]
JsonValue = Union[JsonPrimitive, JsonArray, JsonObject]

# Delimiter type
Delimiter = str
DelimiterKey = Literal["comma", "tab", "pipe"]


class EncodeOptions(TypedDict, total=False):
    """Options for TOON encoding.

    Attributes:
        indent: Number of spaces per indentation level (default: 2)
        delimiter: Delimiter character for arrays (default: comma)
        lengthMarker: Optional marker to prefix array lengths (default: False)
        comments: Optional mapping from dotted paths to comment text
        commentPrefix: Prefix for comment lines (default: '#')
        modelComments: Auto-extract comments from Pydantic BaseModel (default: True)
    """

    indent: int
    delimiter: Delimiter
    lengthMarker: Literal["#", False]
    comments: Dict[str, str]
    commentPrefix: str
    modelComments: bool


class ResolvedEncodeOptions:
    """Resolved encoding options with defaults applied."""

    def __init__(
        self,
        indent: int = 2,
        delimiter: str = ",",
        length_marker: Literal["#", False] = False,
        comments: Dict[str, str] | None = None,
        comment_prefix: str = "#",
    ) -> None:
        self.indent = indent
        self.delimiter = delimiter
        self.lengthMarker = length_marker
        self.comments: Dict[str, str] = comments or {}
        self.commentPrefix = comment_prefix


# Depth type for tracking indentation level
Depth = int
