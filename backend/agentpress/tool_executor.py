"""
Tool Executor for AgentPress.

This module handles tool execution and emits canonical tool_call and tool_result events
as specified in the requirements. It provides a clean interface between parsed tool calls
and actual tool execution.
"""

import asyncio
import json
from typing import Dict, Any, Optional, AsyncGenerator
from datetime import datetime, timezone
from dataclasses import dataclass

from agentpress.xml_parser import ParsedToolCall
from agentpress.tool_registry import ToolRegistry
from utils.logger import logger


@dataclass
class ToolResult:
    """Standardized tool result envelope."""
    success: bool
    output: Any
    error: Optional[str] = None
    execution_time: Optional[float] = None


class ToolExecutor:
    """
    Executes tools and emits canonical events for streaming.
    """
    
    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
    
    async def execute_tool_calls(
        self, 
        tool_calls: list[ParsedToolCall],
        **execution_context
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute a list of tool calls and emit canonical events.
        
        Args:
            tool_calls: List of parsed tool calls to execute
            **execution_context: Additional context for execution
            
        Yields:
            Canonical tool_call and tool_result events
        """
        for tool_call in tool_calls:
            # Emit tool_call event immediately
            yield {
                "type": "tool_call",
                "tool": tool_call.function_name,
                "arguments": tool_call.arguments,
                "xml_tag_name": tool_call.tag_name,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Execute the tool
            result = await self._execute_single_tool(tool_call, **execution_context)
            
            # Emit tool_result event
            yield {
                "type": "tool_result", 
                "tool": tool_call.function_name,
                "output": result.output,
                "success": result.success,
                "error": result.error,
                "execution_time": result.execution_time,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def _execute_single_tool(
        self, 
        tool_call: ParsedToolCall,
        **execution_context
    ) -> ToolResult:
        """
        Execute a single tool call and return standardized result.
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Get tool from registry
            tool_info = self.tool_registry.get_tool(tool_call.function_name)
            if not tool_info:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Tool not found: {tool_call.function_name}"
                )
            
            # Get the tool instance and method
            tool_instance = tool_info['instance']
            method_name = tool_info['method']
            
            if not hasattr(tool_instance, method_name):
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Method not found: {method_name} on {tool_instance.__class__.__name__}"
                )
            
            method = getattr(tool_instance, method_name)
            
            # Prepare arguments
            kwargs = tool_call.arguments.copy()
            kwargs.update(execution_context)
            
            # Execute the tool method
            if asyncio.iscoroutinefunction(method):
                output = await method(**kwargs)
            else:
                output = method(**kwargs)
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            return ToolResult(
                success=True,
                output=output,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"Error executing tool {tool_call.function_name}: {e}")
            
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
                execution_time=execution_time
            )
    
    def emit_status_event(self, status_type: str, **kwargs) -> Dict[str, Any]:
        """
        Emit a status event with consistent format.
        """
        return {
            "type": "status",
            "status_type": status_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **kwargs
        }
    
    def emit_lifecycle_events(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate lifecycle events for progressive response UX.
        """
        async def _generate():
            yield self.emit_status_event("assistant_response_start")
            
            # Small delay for perceived responsiveness
            await asyncio.sleep(0.1)
            
            yield self.emit_status_event("tool_started", message="Computer is starting...")
            
            await asyncio.sleep(0.3)
            
            yield self.emit_status_event("agent_working", message="Iris is working...")
        
        return _generate()
    
    async def handle_tool_execution_with_lifecycle(
        self,
        tool_calls: list[ParsedToolCall],
        **execution_context
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute tools with full lifecycle events for progressive UX.
        """
        # Emit lifecycle start events
        async for event in self.emit_lifecycle_events():
            yield event
        
        # Execute tools and emit canonical events
        async for event in self.execute_tool_calls(tool_calls, **execution_context):
            # Add specific status messages for different tools
            if event["type"] == "tool_call":
                tool_name = event["tool"]
                if tool_name == "web_search":
                    yield self.emit_status_event("tool_progress", message="Searching web...")
                elif tool_name == "file_write":
                    yield self.emit_status_event("tool_progress", message="Writing file...")
                elif tool_name == "execute_bash":
                    yield self.emit_status_event("tool_progress", message="Executing command...")
                elif tool_name == "crawl_webpage":
                    yield self.emit_status_event("tool_progress", message="Crawling webpage...")
                else:
                    yield self.emit_status_event("tool_progress", message=f"Running {tool_name}...")
            
            yield event
            
            # Emit completion status for each tool
            if event["type"] == "tool_result":
                if event["success"]:
                    yield self.emit_status_event("tool_completed", message="Done")
                else:
                    yield self.emit_status_event("tool_error", message=f"Error: {event.get('error', 'Unknown error')}")
        
        # Final completion
        yield self.emit_status_event("execution_completed", message="All tasks completed")

