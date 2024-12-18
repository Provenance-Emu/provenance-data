#!/usr/bin/env python3
import json
import sys
from typing import Any, Set

def analyze_schema(value: Any, seen_types: Set[str] = None, depth: int = 0) -> str:
    """Create a simplified schema representation"""
    if seen_types is None:
        seen_types = set()

    indent = "  " * depth

    if value is None:
        return "null"
    elif isinstance(value, (bool, int, float, str)):
        return type(value).__name__
    elif isinstance(value, list):
        if not value:
            return "[]"

        # Only analyze first item in array
        type_str = analyze_schema(value[0], seen_types, depth + 1)
        return f"Array<{type_str}>"

    elif isinstance(value, dict):
        type_key = f"dict{tuple(sorted(value.keys()))}"
        if type_key in seen_types:
            return "{...}" # Show recursion simply

        seen_types.add(type_key)

        # Show just a few key examples
        sample_keys = sorted(value.keys())[:20]
        parts = []
        for key in sample_keys:
            val_schema = analyze_schema(value[key], seen_types, depth + 1)
            parts.append(f"{indent}  {key}: {val_schema}")

        if len(value) > 20:
            parts.append(f"{indent}  ... ({len(value)-20} more fields)")

        return "{\n" + "\n".join(parts) + f"\n{indent}" + "}"

    return "unknown"

def print_schema(filename: str):
    """Load JSON file and print its simplified schema"""
    try:
        with open(filename, 'r') as f:
            print(f"\nSchema for {filename}:")
            print("=" * 40)
            data = json.load(f)
            schema = analyze_schema(data)
            print(schema)

    except FileNotFoundError:
        print(f"Error: File {filename} not found")
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python analyze_json.py <json_file>")
        sys.exit(1)

    print_schema(sys.argv[1])
