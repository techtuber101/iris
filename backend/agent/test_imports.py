#!/usr/bin/env python3

import sys
import os

# Add the parent directory to the path so we can import modules
sys.path.insert(0, '/Users/ishaantheman/Downloads/iris-clean7 3/backend')

try:
    from agent.tool_registry import extract_tool_calls, registry
    from agent.executors import register_all_tools
    print('✅ Imports successful!')
    print(f'Registry: {registry}')

    # Test XML parsing
    test_text = """
    I need to write a file.

    <file-write path="test.py">
    print("Hello!")
    </file-write>
    """

    calls = extract_tool_calls(test_text)
    print(f"Found {len(calls)} tool calls:")
    for call in calls:
        print(f"  Tag: {call['tag']}, Attrs: {call['attrs']}")

    # Test tool registration
    register_all_tools()
    print(f"Registry now has {len(registry.tools)} tools:")
    for name in registry.tools:
        print(f"  - {name}")

except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
