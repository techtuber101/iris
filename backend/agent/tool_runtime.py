"""
Tool Runtime System for Iris Agent

This module provides the XML-based tool execution system that:
1. Parses XML tool calls from model output
2. Maps XML tags to tool methods using the xml_schema decorators
3. Executes tools and returns structured results
4. Handles legacy tag aliases for backward compatibility
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple, Callable, Awaitable
from dataclasses import dataclass
from xml.etree import ElementTree as ET
from xml.parsers.expat import ExpatError

from agentpress.tool import Tool, ToolResult, XMLTagSchema, XMLNodeMapping
from agentpress.thread_manager import ThreadManager
from sandbox.sandbox import Sandbox

logger = logging.getLogger(__name__)

@dataclass
class XmlCall:
    """Represents a parsed XML tool call."""
    tag_name: str
    attributes: Dict[str, str]
    content: str
    full_xml: str
    line_number: Optional[int] = None

@dataclass
class ToolExecutionResult:
    """Structured result from tool execution."""
    tag: str
    success: bool
    data: Any
    error: Optional[str] = None
    message_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tag": self.tag,
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "message_id": self.message_id
        }

class ToolRegistry:
    """
    Registry for XML-based tools with automatic discovery and instantiation.

    This class:
    - Imports and instantiates all tools from tools.__all__
    - Introspects @xml_schema decorated methods
    - Builds a mapping from XML tag names to tool methods
    - Handles legacy tag aliases
    """

    def __init__(self):
        self._tools: Dict[str, Tuple[Tool, Callable, XMLTagSchema]] = {}
        self._aliases: Dict[str, str] = {}
        self._legacy_warnings: set = set()
        self._initialize_tools()

    def _initialize_tools(self):
        """Initialize and register all available tools."""
        try:
            from .tools import __all__ as tool_classes
            from .tools import (
                MessageTool, SandboxFilesTool, WebSearchTool, SandboxShellTool,
                SandboxBrowserTool, DataProvidersTool, SandboxDeployTool, SandboxExposeTool
            )

            # Tool class to instance mapping with required dependencies
            tool_instances = {}

            # For tools that need sandbox, we'll create placeholder instances
            # Real instances will be created when dependencies are available
            tool_instances[MessageTool] = MessageTool()

            logger.info(f"Initialized tool registry with {len(self._tools)} tools")

        except ImportError as e:
            logger.error(f"Failed to import tools: {e}")
            return

    def register_tool(self, tool_instance: Tool):
        """Register a tool instance and its XML schema methods."""
        tool_name = tool_instance.__class__.__name__

        # Get all methods with XML schemas
        schemas = tool_instance.get_schemas()

        for method_name, method_schemas in schemas.items():
            method = getattr(tool_instance, method_name)

            for schema in method_schemas:
                if schema.xml_schema:
                    tag_name = schema.xml_schema.tag_name
                    self._tools[tag_name] = (tool_instance, method, schema.xml_schema)
                    logger.debug(f"Registered XML tool: {tag_name} -> {tool_name}.{method_name}")

        logger.info(f"Registered tool: {tool_name} with {len([s for s in schemas.values() if any(sch.xml_schema for sch in s)])} XML methods")

    def register_alias(self, alias: str, target: str):
        """Register a legacy tag alias."""
        self._aliases[alias] = target
        logger.debug(f"Registered alias: {alias} -> {target}")

    def resolve_tag(self, tag_name: str) -> str:
        """Resolve tag name, handling aliases and legacy warnings."""
        if tag_name in self._tools:
            return tag_name

        if tag_name in self._aliases:
            target = self._aliases[tag_name]
            if tag_name not in self._legacy_warnings:
                logger.warning(f"Legacy tag '{tag_name}' used, consider switching to '{target}'")
                self._legacy_warnings.add(tag_name)
            return target

        return tag_name  # Return as-is if not found

    def get_tool(self, tag_name: str) -> Optional[Tuple[Tool, Callable, XMLTagSchema]]:
        """Get tool information for a tag name."""
        resolved_tag = self.resolve_tag(tag_name)
        return self._tools.get(resolved_tag)

    def list_available_tags(self) -> List[str]:
        """List all available XML tag names."""
        return list(self._tools.keys()) + list(self._aliases.keys())

class XmlToolRunner:
    """
    XML tool call parser and executor.

    This class:
    - Parses XML tool calls from model output using robust parsing
    - Extracts parameters according to XML schema mappings
    - Executes tool methods and handles results
    - Returns structured tool results for the model
    """

    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self._xml_parser = self._create_robust_parser()

    def _create_robust_parser(self):
        """Create a robust XML parser with recovery mode."""
        try:
            # Try to use lxml for better error recovery if available
            from lxml import etree as lxml_etree
            return lxml_etree.XMLParser(recover=True, strip_cdata=False)
        except ImportError:
            # Fall back to standard library parser
            return ET.XMLParser()

    def find_tags(self, text: str) -> List[XmlCall]:
        """
        Find and parse XML tool calls in text using robust parsing.

        Args:
            text: The text to search for XML tool calls

        Returns:
            List of parsed XmlCall objects
        """
        calls = []

        # Use regex to find potential XML tags first, then parse with ET
        tag_pattern = r'<([a-zA-Z0-9\-_]+)(?:\s+[^>]*)?>(.*?)</\1>'
        for match in re.finditer(tag_pattern, text, re.DOTALL | re.MULTILINE):
            tag_name = match.group(1)
            full_xml = match.group(0)

            try:
                # Check if we have lxml parser (with recover capability)
                if hasattr(self._xml_parser, 'recover'):
                    # lxml parser
                    root = ET.fromstring(full_xml, parser=self._xml_parser)
                else:
                    # Standard library parser - may fail on malformed XML
                    try:
                        root = ET.fromstring(full_xml, parser=self._xml_parser)
                    except ET.ParseError:
                        # Try fallback parsing for malformed XML
                        fallback_call = self._parse_malformed_xml(full_xml, tag_name)
                        if fallback_call:
                            calls.append(fallback_call)
                        continue

                # Extract attributes
                attributes = root.attrib.copy()

                # Extract content (text between tags)
                content = (root.text or "").strip()

                # Also check for nested elements based on schema
                tool_info = self.registry.get_tool(tag_name)
                if tool_info:
                    _, _, schema = tool_info
                    # Extract nested elements if defined in schema
                    for mapping in schema.mappings:
                        if mapping.node_type == "element" and mapping.path != ".":
                            element_name = mapping.path
                            element = root.find(element_name)
                            if element is not None:
                                if element.text:
                                    attributes[mapping.param_name] = element.text.strip()
                                else:
                                    attributes[mapping.param_name] = ""

                calls.append(XmlCall(
                    tag_name=tag_name,
                    attributes=attributes,
                    content=content,
                    full_xml=full_xml
                ))

            except Exception as e:
                logger.warning(f"Failed to parse XML tag '{tag_name}': {e}")
                # Try fallback parsing for malformed XML
                fallback_call = self._parse_malformed_xml(full_xml, tag_name)
                if fallback_call:
                    calls.append(fallback_call)

        return calls

    def _parse_malformed_xml(self, xml_text: str, tag_name: str) -> Optional[XmlCall]:
        """Fallback parser for malformed XML."""
        try:
            # Extract attributes using regex
            attr_pattern = r'([a-zA-Z_][a-zA-Z0-9_\-]*)\s*=\s*"([^"]*)"'
            attributes = dict(re.findall(attr_pattern, xml_text))

            # Extract content (everything between opening and closing tag)
            content_pattern = rf'<{tag_name}[^>]*>(.*?)</{tag_name}>'
            content_match = re.search(content_pattern, xml_text, re.DOTALL)
            content = content_match.group(1).strip() if content_match else ""

            return XmlCall(
                tag_name=tag_name,
                attributes=attributes,
                content=content,
                full_xml=xml_text
            )
        except Exception as e:
            logger.error(f"Failed to parse malformed XML: {e}")
            return None

    def extract_parameters(self, call: XmlCall, schema: XMLTagSchema) -> Dict[str, Any]:
        """
        Extract parameters from XML call according to schema mappings.

        Args:
            call: The parsed XML call
            schema: The XML schema defining parameter mappings

        Returns:
            Dictionary of extracted parameters
        """
        params = {}

        for mapping in schema.mappings:
            param_name = mapping.param_name
            value = None

            try:
                if mapping.node_type == "attribute":
                    # If path is '.', interpret as attribute with the same name as the parameter
                    attr_key = mapping.path if mapping.path and mapping.path != "." else param_name
                    value = call.attributes.get(attr_key, "")
                elif mapping.node_type == "content":
                    value = call.content
                elif mapping.node_type == "element":
                    # For nested elements, we already extracted them in find_tags
                    value = call.attributes.get(param_name, "")

                # Type conversion and validation
                if value is not None:
                    params[param_name] = self._convert_parameter_value(value, param_name, schema)

            except Exception as e:
                logger.warning(f"Failed to extract parameter '{param_name}': {e}")

        return params

    def _convert_parameter_value(self, value: str, param_name: str, schema: XMLTagSchema) -> Any:
        """Convert string parameter values to appropriate types."""
        if not value:
            return value

        # Try to detect and convert common types
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        elif value.isdigit():
            return int(value)
        elif value.replace('.', '', 1).isdigit():
            try:
                return float(value)
            except ValueError:
                pass
        elif value.startswith('[') or value.startswith('{'):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass

        return value

    async def execute(self, call: XmlCall) -> ToolExecutionResult:
        """
        Execute a single XML tool call.

        Args:
            call: The parsed XML call to execute

        Returns:
            Structured tool execution result
        """
        try:
            tool_info = self.registry.get_tool(call.tag_name)

            if not tool_info:
                return ToolExecutionResult(
                    tag=call.tag_name,
                    success=False,
                    data=None,
                    error=f"Unknown tool tag: {call.tag_name}. Available tags: {', '.join(self.registry.list_available_tags())}"
                )

            tool_instance, method, schema = tool_info

            # Extract parameters according to schema
            params = self.extract_parameters(call, schema)

            logger.debug(f"Executing tool {call.tag_name} with params: {list(params.keys())}")

            # Execute the tool method
            result = await method(**params)

            # Convert ToolResult to our format
            if isinstance(result, ToolResult):
                return ToolExecutionResult(
                    tag=call.tag_name,
                    success=result.success,
                    data=result.output if result.success else None,
                    error=result.output if not result.success else None
                )
            else:
                # Handle direct return values
                return ToolExecutionResult(
                    tag=call.tag_name,
                    success=True,
                    data=result
                )

        except Exception as e:
            logger.exception(f"Tool execution failed for {call.tag_name}")
            return ToolExecutionResult(
                tag=call.tag_name,
                success=False,
                data=None,
                error=f"Tool execution error: {str(e)}"
            )

    async def execute_all(self, text: str) -> List[ToolExecutionResult]:
        """
        Find and execute all XML tool calls in the given text.

        Args:
            text: Text containing potential XML tool calls

        Returns:
            List of tool execution results
        """
        calls = self.find_tags(text)
        results = []

        logger.debug(f"Found {len(calls)} tool calls in text")

        for call in calls:
            logger.debug(f"Processing tool call: {call.tag_name}")
            result = await self.execute(call)
            results.append(result)

        return results

# Global registry instance
_registry = ToolRegistry()

def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance."""
    return _registry

def get_xml_runner() -> XmlToolRunner:
    """Get an XML tool runner instance."""
    return XmlToolRunner(_registry)

# Initialize legacy aliases
_registry.register_alias("file-write", "create-file")
_registry.register_alias("str_replace", "str-replace")
_registry.register_alias("file_rewrite", "full-file-rewrite")
_registry.register_alias("command", "execute-command")
_registry.register_alias("shell", "execute-command")
_registry.register_alias("run", "execute-command")
_registry.register_alias("expose", "expose-port")
_registry.register_alias("websearch", "web-search")
_registry.register_alias("crawl", "crawl-webpage")
_registry.register_alias("navigate", "browser-navigate-to")

logger.info("Tool runtime system initialized with XML parsing and execution capabilities")
