from dataclasses import dataclass
from typing import Callable, Awaitable, Any, Dict, List, Optional, Union
import re
import sys
import os

# Add the backend directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

ToolArgs = Dict[str, Any]
ToolResult = Dict[str, Any]
Executor = Callable[[ToolArgs], Awaitable[ToolResult]]

@dataclass
class ToolSpec:
    name: str
    executor: Executor
    parse_body_as: str = "text"  # "text" | "json" | "code"
    description: str = ""

class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec):
        self.tools[spec.name] = spec

    def get(self, name: str) -> Optional[ToolSpec]:
        return self.tools.get(name)

registry = ToolRegistry()

# --- XML extraction (simple) ---
TAG_RX = re.compile(
    r"<(?P<tag>[a-zA-Z0-9\-\_]+)(?P<attrs>[^>]*)>(?P<body>.*?)</\1>",
    re.DOTALL | re.MULTILINE
)

def parse_attrs(attr_str: str) -> Dict[str, str]:
    # Parses attributes like: path="foo" lang="py"
    rx = re.compile(r'([a-zA-Z_][a-zA-Z0-9_\-]*)="([^"]*)"')
    return {k:v for k,v in rx.findall(attr_str or "")}

def extract_tool_calls(text: str) -> List[Dict[str, Any]]:
    calls: List[Dict[str, Any]] = []
    for m in TAG_RX.finditer(text or ""):
        tag = m.group("tag")
        attrs = parse_attrs(m.group("attrs"))
        body = m.group("body")
        calls.append({"tag": tag, "attrs": attrs, "body": body, "full": m.group(0)})
    return calls

def strip_tools_from_text(text: str) -> str:
    return TAG_RX.sub("", text or "").strip()
