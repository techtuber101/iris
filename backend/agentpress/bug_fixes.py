"""
Bug Fixes for Iris AgentPress

This module contains fixes for specific bugs identified in the system,
including bytes/string conversion issues, sentinel brittleness, and
parameter handling problems.
"""

import json
import re
from typing import Any, Dict, List, Optional, Union
from utils.logger import logger
from utils.debug_utils import debug_log, DEBUG_MODE


class StringBytesConverter:
    """
    Handles conversion between strings and bytes safely.
    Fixes issues where streaming chunks might be bytes or strings.
    """
    
    @staticmethod
    def ensure_string(data: Union[str, bytes]) -> str:
        """
        Ensure data is a string, converting from bytes if necessary.
        
        Args:
            data: String or bytes data
            
        Returns:
            String representation of the data
        """
        if isinstance(data, bytes):
            try:
                return data.decode('utf-8')
            except UnicodeDecodeError:
                # Fallback to latin-1 if utf-8 fails
                return data.decode('latin-1', errors='replace')
        elif isinstance(data, str):
            return data
        else:
            return str(data)
    
    @staticmethod
    def ensure_bytes(data: Union[str, bytes]) -> bytes:
        """
        Ensure data is bytes, converting from string if necessary.
        
        Args:
            data: String or bytes data
            
        Returns:
            Bytes representation of the data
        """
        if isinstance(data, str):
            return data.encode('utf-8')
        elif isinstance(data, bytes):
            return data
        else:
            return str(data).encode('utf-8')
    
    @staticmethod
    def safe_json_loads(data: Union[str, bytes]) -> Any:
        """
        Safely load JSON from string or bytes.
        
        Args:
            data: JSON data as string or bytes
            
        Returns:
            Parsed JSON object or None if parsing fails
        """
        try:
            string_data = StringBytesConverter.ensure_string(data)
            return json.loads(string_data)
        except (json.JSONDecodeError, TypeError) as e:
            debug_log(f"JSON parsing failed: {e}", data, level='warning')
            return None


class SentinelCleaner:
    """
    Removes brittle sentinel patterns like <d> tags and other artifacts.
    """
    
    # Patterns to remove
    SENTINEL_PATTERNS = [
        r'<d>.*?</d>',  # Remove <d> tags
        r'</?d>',       # Remove orphaned d tags
        r'```\s*$',     # Remove trailing code block markers
        r'^\s*```',     # Remove leading code block markers
        r'\x00+',       # Remove null bytes
        r'\r\n|\r|\n\n\n+',  # Normalize line endings
    ]
    
    @staticmethod
    def clean_content(content: str) -> str:
        """
        Clean content by removing sentinel patterns and artifacts.
        
        Args:
            content: Content to clean
            
        Returns:
            Cleaned content
        """
        if not isinstance(content, str):
            content = StringBytesConverter.ensure_string(content)
        
        cleaned = content
        
        # Apply all sentinel patterns
        for pattern in SentinelCleaner.SENTINEL_PATTERNS:
            cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE | re.DOTALL)
        
        # Normalize whitespace
        cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)  # Max 2 consecutive newlines
        cleaned = cleaned.strip()
        
        if DEBUG_MODE and cleaned != content:
            debug_log("Content cleaned", {
                'original_length': len(content),
                'cleaned_length': len(cleaned),
                'removed_chars': len(content) - len(cleaned)
            })
        
        return cleaned


class ParameterDefaulter:
    """
    Handles missing parameter defaults and type coercion for tool calls.
    """
    
    # Default values for common parameters
    PARAMETER_DEFAULTS = {
        'query': '',
        'content': '',
        'text': '',
        'message': '',
        'path': '',
        'filename': '',
        'url': '',
        'command': '',
        'code': '',
        'language': 'python',
        'timeout': 30,
        'max_results': 10,
        'recursive': False,
        'overwrite': False,
        'create_dirs': True,
        'encoding': 'utf-8'
    }
    
    # Type coercion rules
    TYPE_COERCIONS = {
        'timeout': int,
        'max_results': int,
        'recursive': bool,
        'overwrite': bool,
        'create_dirs': bool,
        'port': int,
        'limit': int,
        'offset': int
    }
    
    @staticmethod
    def apply_defaults(tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply default values and type coercion to tool parameters.
        
        Args:
            tool_name: Name of the tool
            parameters: Tool parameters
            
        Returns:
            Parameters with defaults applied
        """
        if not isinstance(parameters, dict):
            debug_log(f"Invalid parameters for {tool_name}", parameters, level='warning')
            return {}
        
        result = parameters.copy()
        
        # Apply defaults for missing parameters
        for param_name, default_value in ParameterDefaulter.PARAMETER_DEFAULTS.items():
            if param_name not in result or result[param_name] is None:
                result[param_name] = default_value
        
        # Apply type coercion
        for param_name, target_type in ParameterDefaulter.TYPE_COERCIONS.items():
            if param_name in result and result[param_name] is not None:
                try:
                    if target_type == bool:
                        # Handle boolean conversion
                        value = result[param_name]
                        if isinstance(value, str):
                            result[param_name] = value.lower() in ('true', '1', 'yes', 'on')
                        else:
                            result[param_name] = bool(value)
                    else:
                        result[param_name] = target_type(result[param_name])
                except (ValueError, TypeError) as e:
                    debug_log(f"Type coercion failed for {param_name}: {e}", 
                             result[param_name], level='warning')
        
        # Tool-specific parameter handling
        result = ParameterDefaulter._apply_tool_specific_defaults(tool_name, result)
        
        if DEBUG_MODE and result != parameters:
            debug_log(f"Applied defaults for {tool_name}", {
                'original': parameters,
                'with_defaults': result
            })
        
        return result
    
    @staticmethod
    def _apply_tool_specific_defaults(tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply tool-specific parameter defaults.
        
        Args:
            tool_name: Name of the tool
            parameters: Parameters with general defaults applied
            
        Returns:
            Parameters with tool-specific defaults
        """
        result = parameters.copy()
        
        if tool_name == 'web_search':
            if 'query' not in result or not result['query']:
                result['query'] = result.get('content', result.get('text', ''))
        
        elif tool_name == 'file_write':
            if 'content' not in result:
                result['content'] = result.get('text', '')
            if 'path' not in result:
                result['path'] = result.get('filename', 'output.txt')
        
        elif tool_name == 'execute_bash':
            if 'command' not in result:
                result['command'] = result.get('code', result.get('content', ''))
        
        elif tool_name == 'crawl_webpage':
            if 'url' not in result:
                result['url'] = result.get('content', '')
        
        return result


class ToolNameMapper:
    """
    Maps various tool name formats to canonical names.
    """
    
    # Mapping from XML tag names to function names
    TAG_TO_FUNCTION = {
        'web-search': 'web_search',
        'web_search': 'web_search',
        'websearch': 'web_search',
        'search': 'web_search',
        
        'file-write': 'file_write',
        'file_write': 'file_write',
        'filewrite': 'file_write',
        'write-file': 'file_write',
        'write_file': 'file_write',
        'create-file': 'file_write',
        'create_file': 'file_write',
        
        'execute-bash': 'execute_bash',
        'execute_bash': 'execute_bash',
        'bash': 'execute_bash',
        'shell': 'execute_bash',
        'command': 'execute_bash',
        'run-command': 'execute_bash',
        'run_command': 'execute_bash',
        
        'crawl-webpage': 'crawl_webpage',
        'crawl_webpage': 'crawl_webpage',
        'crawl': 'crawl_webpage',
        'fetch-page': 'crawl_webpage',
        'fetch_page': 'crawl_webpage',
        
        'ask-user': 'ask',
        'ask_user': 'ask',
        'ask': 'ask',
        'question': 'ask',
        
        'str-replace': 'str_replace',
        'str_replace': 'str_replace',
        'replace': 'str_replace',
        'edit-file': 'str_replace',
        'edit_file': 'str_replace'
    }
    
    @staticmethod
    def normalize_tool_name(tag_name: str) -> str:
        """
        Normalize a tool name from XML tag to canonical function name.
        
        Args:
            tag_name: XML tag name or function name
            
        Returns:
            Canonical function name
        """
        if not tag_name:
            return 'unknown'
        
        # Convert to lowercase and handle common variations
        normalized = tag_name.lower().strip()
        
        # Direct mapping
        if normalized in ToolNameMapper.TAG_TO_FUNCTION:
            return ToolNameMapper.TAG_TO_FUNCTION[normalized]
        
        # Try with underscores replaced by hyphens
        hyphenated = normalized.replace('_', '-')
        if hyphenated in ToolNameMapper.TAG_TO_FUNCTION:
            return ToolNameMapper.TAG_TO_FUNCTION[hyphenated]
        
        # Try with hyphens replaced by underscores
        underscored = normalized.replace('-', '_')
        if underscored in ToolNameMapper.TAG_TO_FUNCTION:
            return ToolNameMapper.TAG_TO_FUNCTION[underscored]
        
        # Return as-is if no mapping found
        debug_log(f"No mapping found for tool name: {tag_name}", level='warning')
        return normalized


class AsyncGeneratorFixer:
    """
    Fixes async generator shutdown issues and resource cleanup.
    """
    
    @staticmethod
    async def safe_generator_close(generator):
        """
        Safely close an async generator.
        
        Args:
            generator: Async generator to close
        """
        try:
            if hasattr(generator, 'aclose'):
                await generator.aclose()
        except Exception as e:
            debug_log(f"Error closing async generator: {e}", level='warning')
    
    @staticmethod
    async def safe_generator_iteration(generator, max_items: int = 1000):
        """
        Safely iterate over an async generator with limits.
        
        Args:
            generator: Async generator to iterate
            max_items: Maximum items to process
            
        Yields:
            Items from the generator
        """
        count = 0
        try:
            async for item in generator:
                if count >= max_items:
                    debug_log(f"Generator iteration limit reached: {max_items}", level='warning')
                    break
                yield item
                count += 1
        except Exception as e:
            debug_log(f"Error in generator iteration: {e}", level='error')
        finally:
            await AsyncGeneratorFixer.safe_generator_close(generator)


def apply_all_fixes(content: str, tool_name: str = None, parameters: Dict[str, Any] = None) -> tuple:
    """
    Apply all bug fixes to content and parameters.
    
    Args:
        content: Content to fix
        tool_name: Tool name to normalize
        parameters: Parameters to fix
        
    Returns:
        Tuple of (fixed_content, normalized_tool_name, fixed_parameters)
    """
    # Fix content
    fixed_content = StringBytesConverter.ensure_string(content)
    fixed_content = SentinelCleaner.clean_content(fixed_content)
    
    # Fix tool name
    normalized_tool_name = ToolNameMapper.normalize_tool_name(tool_name) if tool_name else None
    
    # Fix parameters
    fixed_parameters = ParameterDefaulter.apply_defaults(
        normalized_tool_name or 'unknown', 
        parameters or {}
    )
    
    return fixed_content, normalized_tool_name, fixed_parameters

