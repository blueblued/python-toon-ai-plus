# python-toon encoder/decoder

**Token-Oriented Object Notation for Python**

A compact data format optimized for transmitting structured information to Large Language Models (LLMs) with 30-60% fewer tokens than JSON.

[![Tests](https://github.com/xaviviro/python-toon/actions/workflows/test.yml/badge.svg)](https://github.com/xaviviro/python-toon/actions)
[![PyPI](https://img.shields.io/pypi/v/python-toon.svg)](https://pypi.org/project/python-toon/)
[![Python Versions](https://img.shields.io/pypi/pyversions/python-toon.svg)](https://pypi.org/project/python-toon/)

## Installation

```bash
pip install python-toon
```

## What is TOON?

TOON (Token-Oriented Object Notation) combines YAML's indentation-based structure for nested objects and CSV's tabular format for uniform data rows, optimized specifically for token efficiency in LLM contexts.

This is a faithful Python port of the original [TOON TypeScript library](https://github.com/johannschopplich/toon) by Johann Schopplich, maintaining 100% output compatibility with the [official TOON specification](https://github.com/johannschopplich/toon/blob/main/SPEC.md).

### Key Features

- **30-60% token reduction** compared to standard JSON
- **Minimal syntax**: Eliminates redundant punctuation (braces, brackets, most quotes)
- **Tabular arrays**: CSV-like row format for uniform object collections
- **Explicit metadata**: Array length indicators `[N]` for validation
- **LLM-friendly**: Maintains semantic clarity while reducing token count
- **100% compatible** with original TypeScript implementation


## Quick Start

```python
from toon import encode

# Simple object
data = {"name": "Alice", "age": 30}
print(encode(data))
# Output:
# name: Alice
# age: 30

# Tabular array (uniform objects)
users = [
    {"id": 1, "name": "Alice", "age": 30},
    {"id": 2, "name": "Bob", "age": 25},
    {"id": 3, "name": "Charlie", "age": 35},
]
print(encode(users))
# Output:
# [3,]{id,name,age}:
#   1,Alice,30
#   2,Bob,25
#   3,Charlie,35

# Complex nested structure
data = {
    "metadata": {"version": 1, "author": "test"},
    "items": [
        {"id": 1, "name": "Item1"},
        {"id": 2, "name": "Item2"},
    ],
    "tags": ["alpha", "beta", "gamma"],
}
print(encode(data))
# Output:
# metadata:
#   version: 1
#   author: test
# items[2,]{id,name}:
#   1,Item1
#   2,Item2
# tags[3]: alpha,beta,gamma
```

## CLI Usage

Command-line tool for converting between JSON and TOON formats.

```bash
# Encode JSON to TOON (auto-detected by .json extension)
toon input.json -o output.toon

# Decode TOON to JSON (auto-detected by .toon extension)
toon data.toon -o output.json

# Use stdin/stdout
echo '{"name": "Ada"}' | toon -
# Output: name: Ada

# Force encode mode
toon data.json --encode

# Force decode mode
toon data.toon --decode

# Custom delimiter
toon data.json --delimiter "\t" -o output.toon

# With length markers
toon data.json --length-marker -o output.toon

# Lenient decoding (disable strict validation)
toon data.toon --no-strict -o output.json
```

### CLI Options

| Option | Description |
|--------|-------------|
| `-o, --output <file>` | Output file path (prints to stdout if omitted) |
| `-e, --encode` | Force encode mode (overrides auto-detection) |
| `-d, --decode` | Force decode mode (overrides auto-detection) |
| `--delimiter <char>` | Array delimiter: `,` (comma), `\t` (tab), `\|` (pipe) |
| `--indent <number>` | Indentation size (default: 2) |
| `--length-marker` | Add `#` prefix to array lengths (e.g., `items[#3]`) |
| `--no-strict` | Disable strict validation when decoding |

## API Reference

### `encode(value, options=None)`

Converts a Python value to TOON format.

**Parameters:**
- `value` (Any): JSON-serializable value to encode
- `options` (dict, optional): Encoding options

**Returns:** `str` - TOON-formatted string

**Example:**

```python
from toon import encode

data = {"id": 123, "name": "Ada"}
toon_str = encode(data)
print(toon_str)
# Output:
# id: 123
# name: Ada
```

### `decode(input_str, options=None)`

Converts a TOON-formatted string back to Python values.

**Parameters:**
- `input_str` (str): TOON-formatted string to parse
- `options` (DecodeOptions, optional): Decoding options

**Returns:** Python value (dict, list, or primitive)

**Example:**

```python
from toon import decode

toon_str = """items[2]{sku,qty,price}:
  A1,2,9.99
  B2,1,14.5"""

data = decode(toon_str)
print(data)
# Output: {'items': [{'sku': 'A1', 'qty': 2, 'price': 9.99}, {'sku': 'B2', 'qty': 1, 'price': 14.5}]}
```

### Encoding Options

```python
from toon import encode

encode(data, {
    "indent": 2,           # Spaces per indentation level (default: 2)
    "delimiter": ",",      # Delimiter for arrays: "," | "\t" | "|" (default: ",")
    "lengthMarker": "#"    # Optional marker prefix: "#" | False (default: False)
})
```

### Decoding Options

```python
from toon import decode, DecodeOptions

options = DecodeOptions(
    indent=2,    # Expected number of spaces per indentation level (default: 2)
    strict=True  # Enable strict validation (default: True)
)

data = decode(toon_str, options)
```

**Strict Mode:**

By default, the decoder validates input strictly:
- **Invalid escape sequences**: Throws on `"\x"`, unterminated strings
- **Syntax errors**: Throws on missing colons, malformed headers
- **Array length mismatches**: Throws when declared length doesn't match actual count
- **Delimiter mismatches**: Throws when row delimiters don't match header

Set `strict=False` to allow lenient parsing.

### Delimiter Options

You can use string literals directly:

```python
data = [1, 2, 3, 4, 5]

# Comma (default)
print(encode(data))
# [5]: 1,2,3,4,5

# Tab
print(encode(data, {"delimiter": "\t"}))
# [5	]: 1	2	3	4	5

# Pipe
print(encode(data, {"delimiter": "|"}))
# [5|]: 1|2|3|4|5
```

Or use the string keys:

```python
encode(data, {"delimiter": "comma"})   # Default
encode(data, {"delimiter": "tab"})     # Tab-separated
encode(data, {"delimiter": "pipe"})    # Pipe-separated
```

### Length Markers

Add the `#` prefix to array length indicators:

```python
users = [
    {"id": 1, "name": "Alice"},
    {"id": 2, "name": "Bob"},
]

# Without marker (default)
print(encode(users))
# [2,]{id,name}:
# 1,Alice
# 2,Bob

# With marker
print(encode(users, {"lengthMarker": "#"}))
# [#2,]{id,name}:
#   1,Alice
#   2,Bob
```

## Format Rules

### Objects
Key-value pairs with primitives or nested structures:
```python
{"name": "Alice", "age": 30}
# =>
# name: Alice
# age: 30
```

### Primitive Arrays
Arrays always include length `[N]`:
```python
[1, 2, 3, 4, 5]
# => [5]: 1,2,3,4,5

["alpha", "beta", "gamma"]
# => [3]: alpha,beta,gamma
```

### Tabular Arrays
Uniform objects with identical primitive-only fields use CSV-like format:
```python
[
    {"id": 1, "name": "Alice"},
    {"id": 2, "name": "Bob"},
]
# =>
# [2,]{id,name}:
#   1,Alice
#   2,Bob
```

**Note**: The delimiter appears in the length bracket `[2,]` for tabular arrays.

### Mixed Arrays
Non-uniform data using list format with `-` markers:
```python
[{"name": "Alice"}, 42, "hello"]
# =>
# [3]:
#   - name: Alice
#   - 42
#   - hello
```

### Array Length Format

The length bracket format depends on the array type:

**Tabular arrays (with fields):**
- Delimiter always shown: `[2,]{fields}:` or `[2|]{fields}:` or `[2\t]{fields}:`

**Primitive arrays (no fields):**
- Comma: `[3]:` (delimiter hidden)
- Other: `[3|]:` or `[3\t]:` (delimiter shown)

### Quoting Rules

Strings are quoted only when necessary (following the [TOON specification](https://github.com/johannschopplich/toon/blob/main/SPEC.md)):

- Empty strings
- Keywords: `null`, `true`, `false`
- Numeric strings: `42`, `-3.14`
- Leading or trailing whitespace
- Contains structural characters: `:`, `[`, `]`, `{`, `}`, `-`, `"`
- Contains current delimiter (`,`, `|`, or tab)
- Contains control characters (newline, carriage return, tab, backslash)

```python
"hello"          # => hello (no quotes)
"hello world"    # => hello world (internal spaces OK)
" hello"         # => " hello" (leading space requires quotes)
"null"           # => "null" (keyword)
"42"             # => "42" (looks like number)
""               # => "" (empty)
```

## Type Conversions

Non-JSON types are normalized automatically:
- **Numbers**: Decimal form (no scientific notation)
- **Dates/DateTime**: ISO 8601 strings (quoted)
- **Decimal**: Converted to float
- **Infinity/NaN**: Converted to `null`
- **Functions/Callables**: Converted to `null`
- **-0**: Normalized to `0`

## LLM Integration Best Practices

When using TOON with LLMs:

1. **Wrap in code blocks** for clarity:
   ````markdown
   ```toon
   name: Alice
   age: 30
   ```
   ````

2. **Instruct the model** about the format:
   > "Respond using TOON format (Token-Oriented Object Notation). Use `key: value` syntax, indentation for nesting, and tabular format `[N,]{fields}:` for uniform arrays."

3. **Leverage length markers** for validation:
   ```python
   encode(data, {"lengthMarker": "#"})
   ```
   Tell the model: "Array lengths are marked with `[#N]`. Ensure your response matches these counts."

4. **Acknowledge tokenizer variance**: Token savings depend on the specific tokenizer and model being used.

## Token Efficiency Example

```python
import json
from toon import encode

data = {
    "users": [
        {"id": 1, "name": "Alice", "age": 30, "active": True},
        {"id": 2, "name": "Bob", "age": 25, "active": True},
        {"id": 3, "name": "Charlie", "age": 35, "active": False},
    ]
}

json_str = json.dumps(data)
toon_str = encode(data)

print(f"JSON: {len(json_str)} characters")
print(f"TOON: {len(toon_str)} characters")
print(f"Reduction: {100 * (1 - len(toon_str) / len(json_str)):.1f}%")

# Output:
# JSON: 177 characters
# TOON: 85 characters
# Reduction: 52.0%
```

**JSON output:**
```json
{"users": [{"id": 1, "name": "Alice", "age": 30, "active": true}, {"id": 2, "name": "Bob", "age": 25, "active": true}, {"id": 3, "name": "Charlie", "age": 35, "active": false}]}
```

**TOON output:**
```
users[3,]{id,name,age,active}:
  1,Alice,30,true
  2,Bob,25,true
  3,Charlie,35,false
```

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/xaviviro/python-toon.git
cd python-toon

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Install development dependencies
pip install -r requirements-dev.txt
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=pytoon --cov-report=term

# Run original compatibility tests
python test_original_cases.py
```

### Type Checking

```bash
mypy src/pytoon
```

### Linting

```bash
ruff check src/pytoon tests
```

## Credits

This project is a Python implementation of the original [TOON](https://github.com/johannschopplich/toon) format created by [Johann Schopplich](https://github.com/johannschopplich).

**Original TOON (TypeScript)**: MIT License © 2025-PRESENT Johann Schopplich

**python-toon (Python port)**: Developed by Xavi Vinaixa

## License

MIT License - see [LICENSE](LICENSE) file for details

## Related

- [Original TOON (TypeScript)](https://github.com/johannschopplich/toon) - The original implementation
- [TOON Format Specification (SPEC.md)](https://github.com/johannschopplich/toon/blob/main/SPEC.md) - Official v1 specification with normative encoding rules
- [TOON README](https://github.com/johannschopplich/toon#readme) - Format overview and examples

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

When contributing, please:
- Run `python test_original_cases.py` to ensure 100% compatibility with the original
- Add tests for new features
- Update documentation as needed

## Support

For bugs and feature requests, please [open an issue](https://github.com/xaviviro/python-toon/issues).
