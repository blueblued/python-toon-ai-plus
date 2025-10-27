"""Test cases matching the original TOON TypeScript implementation."""

from toon import encode


def test_case(name: str, input_data: any, expected: str, options: dict = None) -> bool:
    """Test a single case."""
    result = encode(input_data, options)
    passed = result == expected
    status = "✓" if passed else "✗"
    print(f"{status} {name}")
    if not passed:
        print(f"  Expected: {repr(expected)}")
        print(f"  Got:      {repr(result)}")
    return passed


# Track results
passed = 0
total = 0


# Primitives
print("=== Primitives ===")
total += 1
passed += test_case("Safe string", "hello", "hello")
total += 1
passed += test_case("Safe string with underscore", "Ada_99", "Ada_99")
total += 1
passed += test_case("Empty string", "", '""')
total += 1
passed += test_case("String 'true' (quoted)", "true", '"true"')
total += 1
passed += test_case("String '42' (quoted)", "42", '"42"')
total += 1
passed += test_case("String '-3.14' (quoted)", "-3.14", '"-3.14"')
total += 1
passed += test_case("Newline escape", "line1\nline2", '"line1\\nline2"')
total += 1
passed += test_case("Backslash escape", "C:\\Users\\path", '"C:\\\\Users\\\\path"')
total += 1
passed += test_case("Unicode (café)", "café", "café")
total += 1
passed += test_case("Emoji", "🚀", "🚀")
total += 1
passed += test_case("Number 42", 42, "42")
total += 1
passed += test_case("Number 3.14", 3.14, "3.14")
total += 1
passed += test_case("Number -0", -0, "0")
total += 1
passed += test_case("Boolean true", True, "true")
total += 1
passed += test_case("Boolean false", False, "false")
total += 1
passed += test_case("null", None, "null")

# Simple Objects
print("\n=== Simple Objects ===")
total += 1
passed += test_case(
    "Basic object",
    {"id": 123, "name": "Ada", "active": True},
    "id: 123\nname: Ada\nactive: true",
)
total += 1
passed += test_case("Empty object", {}, "")
total += 1
passed += test_case("Object with colon in value", {"note": "a:b"}, 'note: "a:b"')

# Object Keys
print("\n=== Object Keys ===")
total += 1
passed += test_case("Key with colon", {"order:id": 7}, '"order:id": 7')
total += 1
passed += test_case("Key with brackets", {"[index]": 5}, '"[index]": 5')
total += 1
passed += test_case("Numeric key", {123: "x"}, '"123": x')

# Nested Objects
print("\n=== Nested Objects ===")
total += 1
passed += test_case(
    "Deep nesting", {"a": {"b": {"c": "deep"}}}, "a:\n  b:\n    c: deep"
)
total += 1
passed += test_case("Empty nested object", {"user": {}}, "user:")

# Primitive Arrays
print("\n=== Primitive Arrays ===")
total += 1
passed += test_case(
    "String array", {"tags": ["reading", "gaming"]}, "tags[2]: reading,gaming"
)
total += 1
passed += test_case("Number array", {"nums": [1, 2, 3]}, "nums[3]: 1,2,3")
total += 1
passed += test_case("Empty array", {"items": []}, "items[0]:")
total += 1
passed += test_case("Array with empty string", {"items": [""]}, 'items[1]: ""')
total += 1
passed += test_case(
    "Array with special chars",
    {"items": ["a", "b,c", "d:e"]},
    'items[3]: a,"b,c","d:e"',
)

# Tabular Arrays
print("\n=== Tabular Arrays ===")
total += 1
passed += test_case(
    "Uniform objects tabular",
    {"items": [{"sku": "A1", "qty": 2, "price": 9.99}, {"sku": "B2", "qty": 1, "price": 14.5}]},
    "items[2,]{sku,qty,price}:\n  A1,2,9.99\n  B2,1,14.5",
)
total += 1
passed += test_case(
    "Different fields (list format)",
    {"items": [{"id": 1, "name": "First"}, {"id": 2, "name": "Second", "extra": True}]},
    "items[2]:\n  - id: 1\n    name: First\n  - id: 2\n    name: Second\n    extra: true",
)

# Nested Arrays
print("\n=== Nested Arrays ===")
total += 1
passed += test_case(
    "Array of arrays",
    {"pairs": [["a", "b"], ["c", "d"]]},
    "pairs[2]:\n  - [2,]: a,b\n  - [2,]: c,d",
)

# Root Arrays
print("\n=== Root Arrays ===")
total += 1
passed += test_case(
    "Primitives at root", ["x", "y", "true", True, 10], '[5]: x,y,"true",true,10'
)
total += 1
passed += test_case(
    "Objects at root (tabular)", [{"id": 1}, {"id": 2}], "[2,]{id}:\n  1\n  2"
)
total += 1
passed += test_case(
    "Objects at root (list)",
    [{"id": 1}, {"id": 2, "name": "Ada"}],
    "[2]:\n  - id: 1\n  - id: 2\n    name: Ada",
)

# Delimiter Options
print("\n=== Delimiter Options ===")
total += 1
passed += test_case(
    "Pipe delimiter",
    {"tags": ["reading", "gaming", "coding"]},
    "tags[3|]: reading|gaming|coding",
    {"delimiter": "|"},
)
total += 1
passed += test_case(
    "Tab delimiter tabular",
    {"items": [{"sku": "A1", "qty": 2}]},
    "items[1\t]{sku\tqty}:\n  A1\t2",
    {"delimiter": "\t"},
)
total += 1
passed += test_case(
    "Quoted delimiter in value",
    {"items": ["a", "b|c"]},
    'items[2|]: a|"b|c"',
    {"delimiter": "|"},
)

# Length Marker Option
print("\n=== Length Marker ===")
total += 1
passed += test_case(
    "With # marker",
    {"tags": ["reading", "gaming"]},
    "tags[#2]: reading,gaming",
    {"lengthMarker": "#"},
)
total += 1
passed += test_case(
    "# marker with pipe delimiter",
    {"tags": ["reading", "gaming"]},
    "tags[#2|]: reading|gaming",
    {"lengthMarker": "#", "delimiter": "|"},
)

# Summary
print(f"\n{'='*50}")
print(f"Results: {passed}/{total} tests passed")
if passed == total:
    print("✓ All tests passed!")
else:
    print(f"✗ {total - passed} tests failed")
