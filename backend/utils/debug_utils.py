"""
Debug Utilities for Iris Backend

This module provides debugging and diagnostic utilities for troubleshooting
issues in the Iris system, especially around XML parsing, tool execution,
and streaming responses.
"""

import os
import json
import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from functools import wraps

from utils.logger import logger

# Check if debug mode is enabled
DEBUG_MODE = os.getenv('IRIS_DEBUG', '').lower() in ('true', '1', 'yes', 'on')


def debug_log(message: str, data: Any = None, level: str = 'info'):
    """
    Log debug information if debug mode is enabled.
    
    Args:
        message: Debug message
        data: Optional data to include
        level: Log level (info, warning, error)
    """
    if not DEBUG_MODE:
        return
    
    timestamp = datetime.now(timezone.utc).isoformat()
    debug_msg = f"[DEBUG {timestamp}] {message}"
    
    if data is not None:
        if isinstance(data, (dict, list)):
            debug_msg += f"\nData: {json.dumps(data, indent=2, default=str)}"
        else:
            debug_msg += f"\nData: {data}"
    
    if level == 'error':
        logger.error(debug_msg)
    elif level == 'warning':
        logger.warning(debug_msg)
    else:
        logger.info(debug_msg)


def debug_xml_parsing(content: str, chunks: List[str], tool_calls: List[Any]):
    """
    Debug XML parsing process.
    
    Args:
        content: Original XML content
        chunks: Extracted XML chunks
        tool_calls: Parsed tool calls
    """
    if not DEBUG_MODE:
        return
    
    debug_log("XML Parsing Debug", {
        'content_length': len(content),
        'content_preview': content[:200] + '...' if len(content) > 200 else content,
        'chunks_found': len(chunks),
        'chunks': chunks,
        'tool_calls_parsed': len(tool_calls),
        'tool_calls': [
            {
                'tag_name': tc.tag_name,
                'function_name': tc.function_name,
                'arguments': tc.arguments
            } for tc in tool_calls
        ]
    })


def debug_tool_execution(tool_name: str, arguments: Dict[str, Any], result: Any, execution_time: float):
    """
    Debug tool execution.
    
    Args:
        tool_name: Name of the tool
        arguments: Tool arguments
        result: Execution result
        execution_time: Time taken to execute
    """
    if not DEBUG_MODE:
        return
    
    debug_log(f"Tool Execution: {tool_name}", {
        'tool_name': tool_name,
        'arguments': arguments,
        'result_type': type(result).__name__,
        'result_success': getattr(result, 'success', None),
        'execution_time_ms': round(execution_time * 1000, 2),
        'result_preview': str(result)[:500] + '...' if len(str(result)) > 500 else str(result)
    })


def debug_streaming_chunk(chunk_type: str, chunk_data: Any, chunk_size: int = None):
    """
    Debug streaming chunks.
    
    Args:
        chunk_type: Type of chunk (content, tool_call, tool_result, etc.)
        chunk_data: Chunk data
        chunk_size: Size of chunk if applicable
    """
    if not DEBUG_MODE:
        return
    
    debug_log(f"Streaming Chunk: {chunk_type}", {
        'type': chunk_type,
        'size': chunk_size or len(str(chunk_data)),
        'data_preview': str(chunk_data)[:200] + '...' if len(str(chunk_data)) > 200 else str(chunk_data)
    })


def debug_response_processing(phase: str, data: Any):
    """
    Debug response processing phases.
    
    Args:
        phase: Processing phase name
        data: Phase-specific data
    """
    if not DEBUG_MODE:
        return
    
    debug_log(f"Response Processing: {phase}", data)


def debug_adaptive_routing(query: str, decision: str, confidence: float, reasoning: str):
    """
    Debug adaptive routing decisions.
    
    Args:
        query: User query
        decision: Routing decision (direct/agentic)
        confidence: Confidence score
        reasoning: Reasoning for decision
    """
    if not DEBUG_MODE:
        return
    
    debug_log("Adaptive Routing Decision", {
        'query': query,
        'decision': decision,
        'confidence': confidence,
        'reasoning': reasoning
    })


def debug_message_normalization(original_message: Any, normalized_message: Any):
    """
    Debug message normalization.
    
    Args:
        original_message: Original message from API
        normalized_message: Normalized message
    """
    if not DEBUG_MODE:
        return
    
    debug_log("Message Normalization", {
        'original_type': type(original_message).__name__,
        'original_preview': str(original_message)[:200] + '...' if len(str(original_message)) > 200 else str(original_message),
        'normalized_type': normalized_message.get('type'),
        'normalized_tool': normalized_message.get('tool'),
        'normalized_success': normalized_message.get('success')
    })


def debug_performance(func):
    """
    Decorator to debug function performance.
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function with performance logging
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        if not DEBUG_MODE:
            return await func(*args, **kwargs)
        
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            debug_log(f"Performance: {func.__name__}", {
                'function': func.__name__,
                'execution_time_ms': round(execution_time * 1000, 2),
                'args_count': len(args),
                'kwargs_count': len(kwargs),
                'success': True
            })
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            debug_log(f"Performance: {func.__name__} (ERROR)", {
                'function': func.__name__,
                'execution_time_ms': round(execution_time * 1000, 2),
                'error': str(e),
                'success': False
            }, level='error')
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        if not DEBUG_MODE:
            return func(*args, **kwargs)
        
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            debug_log(f"Performance: {func.__name__}", {
                'function': func.__name__,
                'execution_time_ms': round(execution_time * 1000, 2),
                'args_count': len(args),
                'kwargs_count': len(kwargs),
                'success': True
            })
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            debug_log(f"Performance: {func.__name__} (ERROR)", {
                'function': func.__name__,
                'execution_time_ms': round(execution_time * 1000, 2),
                'error': str(e),
                'success': False
            }, level='error')
            raise
    
    # Return appropriate wrapper based on function type
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def debug_system_state():
    """
    Log current system state for debugging.
    """
    if not DEBUG_MODE:
        return
    
    import psutil
    import sys
    
    debug_log("System State", {
        'python_version': sys.version,
        'memory_usage_mb': round(psutil.Process().memory_info().rss / 1024 / 1024, 2),
        'cpu_percent': psutil.cpu_percent(),
        'debug_mode': DEBUG_MODE,
        'environment_vars': {
            'IRIS_DEBUG': os.getenv('IRIS_DEBUG'),
            'OPENAI_API_KEY': 'SET' if os.getenv('OPENAI_API_KEY') else 'NOT_SET',
            'SUPABASE_URL': 'SET' if os.getenv('SUPABASE_URL') else 'NOT_SET'
        }
    })


def debug_error_context(error: Exception, context: Dict[str, Any]):
    """
    Log error with additional context for debugging.
    
    Args:
        error: Exception that occurred
        context: Additional context information
    """
    debug_log(f"Error Context: {type(error).__name__}", {
        'error_type': type(error).__name__,
        'error_message': str(error),
        'context': context
    }, level='error')


class DebugTimer:
    """Context manager for timing operations in debug mode."""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
    
    def __enter__(self):
        if DEBUG_MODE:
            self.start_time = time.time()
            debug_log(f"Starting: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if DEBUG_MODE and self.start_time:
            execution_time = time.time() - self.start_time
            if exc_type:
                debug_log(f"Failed: {self.operation_name}", {
                    'execution_time_ms': round(execution_time * 1000, 2),
                    'error': str(exc_val)
                }, level='error')
            else:
                debug_log(f"Completed: {self.operation_name}", {
                    'execution_time_ms': round(execution_time * 1000, 2)
                })


def get_debug_info() -> Dict[str, Any]:
    """
    Get current debug information.
    
    Returns:
        Dictionary with debug information
    """
    return {
        'debug_mode': DEBUG_MODE,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'environment': {
            'IRIS_DEBUG': os.getenv('IRIS_DEBUG'),
            'NODE_ENV': os.getenv('NODE_ENV'),
            'ENVIRONMENT': os.getenv('ENVIRONMENT')
        }
    }

