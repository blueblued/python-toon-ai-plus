"""TOON decoder implementation following v1.2 spec."""

import re
from typing import Any, Dict, List, Optional, Tuple

from .constants import (
    BACKSLASH,
    CARRIAGE_RETURN,
    CLOSE_BRACE,
    CLOSE_BRACKET,
    COLON,
    COMMA,
    DOUBLE_QUOTE,
    FALSE_LITERAL,
    LIST_ITEM_MARKER,
    NEWLINE,
    NULL_LITERAL,
    OPEN_BRACE,
    OPEN_BRACKET,
    PIPE,
    TAB,
    TRUE_LITERAL,
)
from .types import DecodeOptions, JsonValue


class ToonDecodeError(Exception):
    """TOON decoding error."""
    pass


class Line:
    """Represents a line in the TOON document."""

    def __init__(self, content: str, depth: int, line_number: int):
        self.content = content
        self.depth = depth
        self.line_number = line_number
        self.is_blank = not content.strip()


def compute_depth(line: str, indent_size: int, strict: bool) -> int:
    """Compute indentation depth for a line.

    Args:
        line: Line content
        indent_size: Number of spaces per indentation level
        strict: Whether to enforce strict indentation rules

    Returns:
        Indentation depth

    Raises:
        ToonDecodeError: If indentation is invalid in strict mode
    """
    if not line:
        return 0

    # Count leading spaces
    leading_spaces = len(line) - len(line.lstrip(' '))

    # Check for tabs in indentation (always error in strict mode)
    if strict and '\t' in line[:leading_spaces]:
        raise ToonDecodeError("Tabs are not allowed in indentation")

    # In strict mode, leading spaces must be exact multiple of indent_size
    if strict:
        if leading_spaces % indent_size != 0:
            raise ToonDecodeError(
                f"Indentation must be an exact multiple of {indent_size} spaces"
            )
        return leading_spaces // indent_size
    else:
        # Non-strict mode: use floor division
        return leading_spaces // indent_size


def unescape_string(value: str) -> str:
    """Unescape a quoted string.

    Args:
        value: Escaped string (without surrounding quotes)

    Returns:
        Unescaped string

    Raises:
        ToonDecodeError: If escape sequence is invalid
    """
    result = []
    i = 0
    while i < len(value):
        if value[i] == BACKSLASH:
            if i + 1 >= len(value):
                raise ToonDecodeError("Unterminated string: missing closing quote")
            next_char = value[i + 1]
            if next_char == BACKSLASH:
                result.append(BACKSLASH)
            elif next_char == DOUBLE_QUOTE:
                result.append(DOUBLE_QUOTE)
            elif next_char == 'n':
                result.append(NEWLINE)
            elif next_char == 'r':
                result.append(CARRIAGE_RETURN)
            elif next_char == 't':
                result.append(TAB)
            else:
                raise ToonDecodeError(f"Invalid escape sequence: \\{next_char}")
            i += 2
        else:
            result.append(value[i])
            i += 1
    return ''.join(result)


def parse_primitive(token: str) -> JsonValue:
    """Parse a primitive token.

    Args:
        token: Token string

    Returns:
        Parsed value

    Raises:
        ToonDecodeError: If quoted string is malformed
    """
    token = token.strip()

    # Quoted string
    if token.startswith(DOUBLE_QUOTE):
        if not token.endswith(DOUBLE_QUOTE) or len(token) < 2:
            raise ToonDecodeError("Unterminated string: missing closing quote")
        return unescape_string(token[1:-1])

    # Boolean literals
    if token == TRUE_LITERAL:
        return True
    if token == FALSE_LITERAL:
        return False
    if token == NULL_LITERAL:
        return None

    # Try to parse as number
    # Must handle: 42, -3.14, 1e-6, -1E+9
    # Must reject leading zeros like "05", "0001"
    if token:
        # Check for forbidden leading zeros
        if re.match(r'^0\d+$', token):
            # Leading zero like "05" -> string
            return token

        try:
            # Try int first
            if '.' not in token and 'e' not in token.lower():
                return int(token)
            # Then float
            return float(token)
        except ValueError:
            pass

    # Otherwise it's an unquoted string
    return token


def parse_delimited_values(line: str, delimiter: str) -> List[str]:
    """Parse delimiter-separated values, respecting quotes.

    Args:
        line: Line content
        delimiter: Active delimiter

    Returns:
        List of token strings
    """
    tokens = []
    current = []
    in_quotes = False
    i = 0

    while i < len(line):
        char = line[i]

        if char == DOUBLE_QUOTE:
            in_quotes = not in_quotes
            current.append(char)
        elif char == BACKSLASH and i + 1 < len(line) and in_quotes:
            # In quotes, consume escape sequence
            current.append(char)
            current.append(line[i + 1])
            i += 1
        elif char == delimiter and not in_quotes:
            # Split on unquoted delimiter
            tokens.append(''.join(current))
            current = []
            i += 1
            continue
        else:
            current.append(char)

        i += 1

    # Add final token
    if current or tokens:  # Include empty final token if there was a delimiter
        tokens.append(''.join(current))

    return tokens


def parse_header(line: str) -> Optional[Tuple[Optional[str], int, str, Optional[List[str]]]]:
    """Parse an array header.

    Args:
        line: Line content

    Returns:
        Tuple of (key, length, delimiter, fields) or None if not a header

    Raises:
        ToonDecodeError: If header is malformed
    """
    line = line.strip()

    # Find the bracket segment
    bracket_start = line.find(OPEN_BRACKET)
    if bracket_start == -1:
        return None

    # Extract key (if any)
    key = None
    if bracket_start > 0:
        key_part = line[:bracket_start].strip()
        key = parse_key(key_part) if key_part else None

    # Find closing bracket
    bracket_end = line.find(CLOSE_BRACKET, bracket_start)
    if bracket_end == -1:
        return None

    # Parse bracket content: [#?N<delim?>]
    bracket_content = line[bracket_start + 1:bracket_end]

    # Remove optional # marker
    if bracket_content.startswith('#'):
        bracket_content = bracket_content[1:]

    # Determine delimiter from bracket content
    delimiter = COMMA  # default
    length_str = bracket_content

    if bracket_content.endswith(TAB):
        delimiter = TAB
        length_str = bracket_content[:-1]
    elif bracket_content.endswith(PIPE):
        delimiter = PIPE
        length_str = bracket_content[:-1]
    elif bracket_content.endswith(COMMA):
        # Explicit comma delimiter (for tabular arrays)
        delimiter = COMMA
        length_str = bracket_content[:-1]

    # Parse length
    try:
        length = int(length_str)
    except ValueError:
        return None

    # Check for fields segment
    fields = None
    after_bracket = line[bracket_end + 1:].strip()

    if after_bracket.startswith(OPEN_BRACE):
        brace_end = after_bracket.find(CLOSE_BRACE)
        if brace_end == -1:
            raise ToonDecodeError("Unterminated fields segment")

        fields_content = after_bracket[1:brace_end]
        # Parse fields using the delimiter
        field_tokens = parse_delimited_values(fields_content, delimiter)
        fields = [parse_key(f.strip()) for f in field_tokens]

        after_bracket = after_bracket[brace_end + 1:].strip()

    # Must end with colon
    if not after_bracket.startswith(COLON):
        return None

    return (key, length, delimiter, fields)


def parse_key(key_str: str) -> str:
    """Parse a key (quoted or unquoted).

    Args:
        key_str: Key string

    Returns:
        Parsed key

    Raises:
        ToonDecodeError: If quoted key is malformed
    """
    key_str = key_str.strip()

    if key_str.startswith(DOUBLE_QUOTE):
        if not key_str.endswith(DOUBLE_QUOTE) or len(key_str) < 2:
            raise ToonDecodeError("Unterminated quoted key")
        return unescape_string(key_str[1:-1])

    return key_str


def split_key_value(line: str) -> Tuple[str, str]:
    """Split a line into key and value at first unquoted colon.

    Args:
        line: Line content

    Returns:
        Tuple of (key, value)

    Raises:
        ToonDecodeError: If no colon found
    """
    in_quotes = False
    i = 0

    while i < len(line):
        char = line[i]

        if char == DOUBLE_QUOTE:
            in_quotes = not in_quotes
        elif char == BACKSLASH and i + 1 < len(line) and in_quotes:
            i += 1  # Skip next char
        elif char == COLON and not in_quotes:
            key = line[:i].strip()
            value = line[i + 1:].strip()
            return (key, value)

        i += 1

    raise ToonDecodeError("Missing colon after key")


def decode(input_str: str, options: Optional[DecodeOptions] = None) -> JsonValue:
    """Decode a TOON-formatted string to a Python value.

    Args:
        input_str: TOON-formatted string
        options: Optional decoding options

    Returns:
        Decoded Python value

    Raises:
        ToonDecodeError: If input is malformed
    """
    if options is None:
        options = DecodeOptions()

    indent_size = options.indent
    strict = options.strict

    # Split into lines
    raw_lines = input_str.split('\n')

    # Process lines: compute depth and filter blanks outside arrays
    lines: List[Line] = []
    for i, raw in enumerate(raw_lines):
        # Skip trailing newline
        if i == len(raw_lines) - 1 and not raw.strip():
            continue

        depth = compute_depth(raw, indent_size, strict)
        line = Line(raw.strip(), depth, i + 1)

        # Keep all lines for now (we'll handle blank line rules during parsing)
        if line.content or not strict:
            lines.append(line)

    # Remove blank lines outside arrays (Section 12)
    # For simplicity, we'll handle this during parsing

    # Check for empty input
    non_blank_lines = [ln for ln in lines if not ln.is_blank]
    if not non_blank_lines:
        if strict:
            raise ToonDecodeError("Empty input")
        return None

    # Determine root form (Section 5)
    first_line = non_blank_lines[0]

    # Check if it's a root array header
    header_info = parse_header(first_line.content)
    if header_info is not None and header_info[0] is None:  # No key = root array
        # Root array
        return decode_array(lines, 0, 0, header_info, strict)

    # Check if it's a single primitive
    if len(non_blank_lines) == 1:
        line_content = first_line.content
        # Check if it's not a key-value line
        try:
            split_key_value(line_content)
            # It's a key-value, so root object
        except ToonDecodeError:
            # Not a key-value, check if it's a header
            if header_info is None:
                # Single primitive
                return parse_primitive(line_content)

    # Otherwise, root object
    return decode_object(lines, 0, 0, strict)


def decode_object(
    lines: List[Line],
    start_idx: int,
    parent_depth: int,
    strict: bool
) -> Dict[str, Any]:
    """Decode an object starting at given line index.

    Args:
        lines: List of lines
        start_idx: Starting line index
        parent_depth: Parent indentation depth
        strict: Strict mode flag

    Returns:
        Decoded object
    """
    result = {}
    i = start_idx
    expected_depth = parent_depth if start_idx == 0 else parent_depth + 1

    while i < len(lines):
        line = lines[i]

        # Skip blank lines outside arrays (allowed)
        if line.is_blank:
            i += 1
            continue

        # Stop if we've dedented below expected depth
        if line.depth < expected_depth:
            break

        # Skip lines that are too deeply indented (they belong to nested structures)
        if line.depth > expected_depth:
            i += 1
            continue

        content = line.content

        # Check for array header
        header_info = parse_header(content)
        if header_info is not None:
            key, length, delimiter, fields = header_info
            if key is not None:
                # Array field
                array_val, next_i = decode_array_from_header(
                    lines, i, line.depth, header_info, strict
                )
                result[key] = array_val
                i = next_i
                continue

        # Must be a key-value line
        try:
            key_str, value_str = split_key_value(content)
        except ToonDecodeError:
            # Invalid line, skip in non-strict mode
            if strict:
                raise
            i += 1
            continue

        key = parse_key(key_str)

        # Check if value is empty (nested object)
        if not value_str:
            # Nested object
            result[key] = decode_object(lines, i + 1, line.depth, strict)
            # Skip past nested object
            i += 1
            while i < len(lines) and lines[i].depth > line.depth:
                i += 1
        else:
            # Primitive value
            result[key] = parse_primitive(value_str)
            i += 1

    return result


def decode_array_from_header(
    lines: List[Line],
    header_idx: int,
    header_depth: int,
    header_info: Tuple[Optional[str], int, str, Optional[List[str]]],
    strict: bool
) -> Tuple[List[Any], int]:
    """Decode array starting from a header line.

    Args:
        lines: List of lines
        header_idx: Index of header line
        header_depth: Depth of header line
        header_info: Parsed header info
        strict: Strict mode flag

    Returns:
        Tuple of (decoded array, next line index)
    """
    key, length, delimiter, fields = header_info
    header_line = lines[header_idx].content

    # Check if there's inline content after the colon
    colon_idx = header_line.rfind(COLON)
    inline_content = header_line[colon_idx + 1:].strip()

    if inline_content:
        # Inline primitive array
        return decode_inline_array(inline_content, delimiter, length, strict), header_idx + 1

    # Non-inline array
    if fields is not None:
        # Tabular array
        return decode_tabular_array(lines, header_idx + 1, header_depth, fields, delimiter, length, strict)
    else:
        # List format (mixed/non-uniform)
        return decode_list_array(lines, header_idx + 1, header_depth, delimiter, length, strict)


def decode_array(
    lines: List[Line],
    start_idx: int,
    parent_depth: int,
    header_info: Tuple[Optional[str], int, str, Optional[List[str]]],
    strict: bool
) -> List[Any]:
    """Decode array (convenience wrapper).

    Args:
        lines: List of lines
        start_idx: Starting line index
        parent_depth: Parent depth
        header_info: Header info
        strict: Strict mode

    Returns:
        Decoded array
    """
    arr, _ = decode_array_from_header(lines, start_idx, parent_depth, header_info, strict)
    return arr


def decode_inline_array(
    content: str,
    delimiter: str,
    expected_length: int,
    strict: bool
) -> List[Any]:
    """Decode an inline primitive array.

    Args:
        content: Inline content after colon
        delimiter: Active delimiter
        expected_length: Expected array length
        strict: Strict mode flag

    Returns:
        Decoded array

    Raises:
        ToonDecodeError: If length mismatch in strict mode
    """
    if not content and expected_length == 0:
        return []

    tokens = parse_delimited_values(content, delimiter)
    values = [parse_primitive(token) for token in tokens]

    if strict and len(values) != expected_length:
        raise ToonDecodeError(
            f"Expected {expected_length} values, but got {len(values)}"
        )

    return values


def decode_tabular_array(
    lines: List[Line],
    start_idx: int,
    header_depth: int,
    fields: List[str],
    delimiter: str,
    expected_length: int,
    strict: bool
) -> Tuple[List[Dict[str, Any]], int]:
    """Decode a tabular array.

    Args:
        lines: List of lines
        start_idx: Starting line index (after header)
        header_depth: Depth of header
        fields: Field names
        delimiter: Active delimiter
        expected_length: Expected number of rows
        strict: Strict mode flag

    Returns:
        Tuple of (decoded array, next line index)

    Raises:
        ToonDecodeError: If row width or count mismatch in strict mode
    """
    result = []
    i = start_idx
    row_depth = header_depth + 1

    while i < len(lines):
        line = lines[i]

        # Check for blank lines in array (error in strict mode)
        if line.is_blank:
            if strict:
                raise ToonDecodeError("Blank lines not allowed inside arrays")
            i += 1
            continue

        # Stop if dedented or different depth
        if line.depth < row_depth:
            break
        if line.depth > row_depth:
            # End of tabular rows (might be next key-value)
            break

        content = line.content

        # Disambiguation: check if this is a row or a key-value line
        # A row has no unquoted colon, or delimiter before colon
        if is_row_line(content, delimiter):
            # Parse as row
            tokens = parse_delimited_values(content, delimiter)
            values = [parse_primitive(token) for token in tokens]

            if strict and len(values) != len(fields):
                raise ToonDecodeError(
                    f"Expected {len(fields)} values in row, but got {len(values)}"
                )

            obj = {fields[j]: values[j] for j in range(min(len(fields), len(values)))}
            result.append(obj)
            i += 1
        else:
            # Not a row, end of tabular data
            break

    if strict and len(result) != expected_length:
        raise ToonDecodeError(
            f"Expected {expected_length} rows, but got {len(result)}"
        )

    return result, i


def is_row_line(line: str, delimiter: str) -> bool:
    """Check if a line is a tabular row (not a key-value line).

    Args:
        line: Line content
        delimiter: Active delimiter

    Returns:
        True if it's a row line
    """
    # Find first unquoted delimiter and first unquoted colon
    first_delim_pos = None
    first_colon_pos = None
    in_quotes = False
    i = 0

    while i < len(line):
        char = line[i]

        if char == DOUBLE_QUOTE:
            in_quotes = not in_quotes
        elif char == BACKSLASH and i + 1 < len(line) and in_quotes:
            i += 1
        elif not in_quotes:
            if char == delimiter and first_delim_pos is None:
                first_delim_pos = i
            if char == COLON and first_colon_pos is None:
                first_colon_pos = i

        i += 1

    # No unquoted colon -> row
    if first_colon_pos is None:
        return True

    # Both present: delimiter before colon -> row
    if first_delim_pos is not None and first_delim_pos < first_colon_pos:
        return True

    # Colon before delimiter or no delimiter -> key-value
    return False


def decode_list_array(
    lines: List[Line],
    start_idx: int,
    header_depth: int,
    delimiter: str,
    expected_length: int,
    strict: bool
) -> Tuple[List[Any], int]:
    """Decode a list-format array (mixed/non-uniform).

    Args:
        lines: List of lines
        start_idx: Starting line index
        header_depth: Header depth
        delimiter: Active delimiter
        expected_length: Expected number of items
        strict: Strict mode flag

    Returns:
        Tuple of (decoded array, next line index)

    Raises:
        ToonDecodeError: If item count mismatch in strict mode
    """
    result = []
    i = start_idx
    item_depth = header_depth + 1

    while i < len(lines):
        line = lines[i]

        # Skip blank lines (error in strict mode)
        if line.is_blank:
            if strict:
                raise ToonDecodeError("Blank lines not allowed inside arrays")
            i += 1
            continue

        # Stop if dedented
        if line.depth < item_depth:
            break

        # Must start with "- "
        content = line.content
        if not content.startswith(LIST_ITEM_MARKER):
            # Not a list item, end of array
            break

        # Remove "- " prefix
        item_content = content[len(LIST_ITEM_MARKER):].strip()

        # Check what kind of item this is
        item_header = parse_header(item_content)
        if item_header is not None:
            # It's an array header: - [N]: ... or - key[N]: ...
            key, length, item_delim, fields = item_header

            if key is None:
                # - [N]: inline array
                colon_idx = item_content.find(COLON)
                if colon_idx != -1:
                    inline_part = item_content[colon_idx + 1:].strip()
                    if inline_part:
                        # Inline primitive array
                        item_val = decode_inline_array(inline_part, item_delim, length, strict)
                        result.append(item_val)
                        i += 1
                        continue
            else:
                # - key[N]: array field in object
                # This is an object with an array as its first field
                item_obj = {}
                array_val, next_i = decode_array_from_header(
                    lines, i, line.depth, item_header, strict
                )
                item_obj[key] = array_val

                # Continue reading remaining fields at depth +1
                i = next_i
                while i < len(lines) and lines[i].depth == line.depth + 1:
                    field_line = lines[i]
                    if field_line.is_blank:
                        i += 1
                        continue

                    field_content = field_line.content

                    # Check for array header
                    field_header = parse_header(field_content)
                    if field_header is not None and field_header[0] is not None:
                        field_key, field_length, field_delim, field_fields = field_header
                        field_val, next_i = decode_array_from_header(
                            lines, i, field_line.depth, field_header, strict
                        )
                        item_obj[field_key] = field_val
                        i = next_i
                        continue

                    try:
                        field_key_str, field_value_str = split_key_value(field_content)
                        field_key = parse_key(field_key_str)

                        if not field_value_str:
                            # Nested object
                            item_obj[field_key] = decode_object(lines, i + 1, field_line.depth, strict)
                            i += 1
                            while i < len(lines) and lines[i].depth > field_line.depth:
                                i += 1
                        else:
                            item_obj[field_key] = parse_primitive(field_value_str)
                            i += 1
                    except ToonDecodeError:
                        break

                result.append(item_obj)
                continue

        # Check if it's an object (has colon)
        try:
            key_str, value_str = split_key_value(item_content)
            # It's an object item
            item_obj = {}

            # First field
            key = parse_key(key_str)
            if not value_str:
                # First field is nested object: fields at depth +2
                nested = decode_object(lines, i + 1, line.depth + 1, strict)
                item_obj[key] = nested
                # Skip nested content
                i += 1
                while i < len(lines) and lines[i].depth > line.depth + 1:
                    i += 1
            else:
                # First field is primitive
                item_obj[key] = parse_primitive(value_str)
                i += 1

            # Remaining fields at depth +1
            while i < len(lines) and lines[i].depth == line.depth + 1:
                field_line = lines[i]
                if field_line.is_blank:
                    i += 1
                    continue

                field_content = field_line.content

                # Check for array header
                field_header = parse_header(field_content)
                if field_header is not None and field_header[0] is not None:
                    field_key, field_length, field_delim, field_fields = field_header
                    field_val, next_i = decode_array_from_header(
                        lines, i, field_line.depth, field_header, strict
                    )
                    item_obj[field_key] = field_val
                    i = next_i
                    continue

                try:
                    field_key_str, field_value_str = split_key_value(field_content)
                    field_key = parse_key(field_key_str)

                    if not field_value_str:
                        # Nested object
                        item_obj[field_key] = decode_object(lines, i + 1, field_line.depth, strict)
                        i += 1
                        while i < len(lines) and lines[i].depth > field_line.depth:
                            i += 1
                    else:
                        item_obj[field_key] = parse_primitive(field_value_str)
                        i += 1
                except ToonDecodeError:
                    break

            result.append(item_obj)
        except ToonDecodeError:
            # Not an object, must be a primitive
            result.append(parse_primitive(item_content))
            i += 1

    if strict and len(result) != expected_length:
        raise ToonDecodeError(
            f"Expected {expected_length} items, but got {len(result)}"
        )

    return result, i
