"""
Robust XML Parser for AgentPress Tool Calls.

This module provides robust XML parsing for tool calls with proper error handling,
bytes/string conversion, and tool name normalization.
"""

import re
import hashlib
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass
from utils.logger import logger


@dataclass
class ParsedToolCall:
    """Represents a parsed tool call from XML."""
    tag_name: str  # Original XML tag name (e.g., "file-write")
    function_name: str  # Normalized function name (e.g., "file_write")
    arguments: Dict[str, Any]
    attributes: Dict[str, str]
    text_content: str
    xml_content: str  # Original XML content


class XMLToolParser:
    """
    Robust XML parser for tool calls with proper error handling and normalization.
    """
    
    def __init__(self):
        # Tool name mapping from XML tags to function names
        self.tool_name_mapping = {
            'file-write': 'file_write',
            'execute-bash': 'execute_bash', 
            'web-search': 'web_search',
            'crawl-webpage': 'crawl_webpage',
            'ask': 'ask',
            'create-file': 'file_write',
            'str-replace': 'str_replace',
            'browser-navigate-to': 'browser_navigate',
            'browser-click-element': 'browser_click',
            'browser-input-text': 'browser_input',
            'browser-scroll-down': 'browser_scroll_down',
            'browser-scroll-up': 'browser_scroll_up',
            'execute-command': 'execute_bash',
        }
        
        # Cache for de-duplication
        self.recent_hashes: Set[str] = set()
        self.max_cache_size = 100
        
    def extract_xml_chunks(self, content: str) -> List[str]:
        """
        Extract complete XML chunks using robust pattern matching.
        
        Args:
            content: The content to parse (string)
            
        Returns:
            List of XML chunk strings
        """
        chunks = []
        
        try:
            # Ensure we're working with string, not bytes
            if isinstance(content, bytes):
                content = content.decode('utf-8', errors='replace')
            
            # Remove any sentinel markers like <d> if they exist
            content = self._clean_content(content)
            
            # Find all potential tool tags
            tool_tags = list(self.tool_name_mapping.keys())
            
            pos = 0
            while pos < len(content):
                # Find the next tool tag
                next_tag_start = -1
                current_tag = None
                
                # Find the earliest occurrence of any registered tag
                for tag_name in tool_tags:
                    start_pattern = f'<{tag_name}'
                    tag_pos = content.find(start_pattern, pos)
                    
                    if tag_pos != -1 and (next_tag_start == -1 or tag_pos < next_tag_start):
                        next_tag_start = tag_pos
                        current_tag = tag_name
                
                if next_tag_start == -1 or not current_tag:
                    break
                
                # Extract the complete XML chunk
                chunk = self._extract_complete_tag(content, next_tag_start, current_tag)
                if chunk:
                    chunks.append(chunk)
                    pos = next_tag_start + len(chunk)
                else:
                    pos = next_tag_start + 1
                    
        except Exception as e:
            logger.error(f"Error extracting XML chunks: {e}")
            logger.error(f"Content preview: {content[:200]}...")
        
        return chunks
    
    def _clean_content(self, content: str) -> str:
        """
        Clean content by removing sentinel markers and normalizing.
        """
        # Remove <d> sentinel markers if they exist
        content = re.sub(r'<d[^>]*>', '', content)
        content = re.sub(r'</d>', '', content)
        
        # Normalize whitespace but preserve structure
        return content.strip()
    
    def _extract_complete_tag(self, content: str, start_pos: int, tag_name: str) -> Optional[str]:
        """
        Extract a complete XML tag including nested tags.
        """
        try:
            end_pattern = f'</{tag_name}>'
            tag_stack = []
            current_pos = start_pos
            
            # Find the opening tag end
            opening_end = content.find('>', start_pos)
            if opening_end == -1:
                return None
            
            # Check if it's a self-closing tag
            if content[opening_end - 1] == '/':
                return content[start_pos:opening_end + 1]
            
            current_pos = opening_end + 1
            
            while current_pos < len(content):
                # Look for next start or end tag of the same type
                next_start = content.find(f'<{tag_name}', current_pos)
                next_end = content.find(end_pattern, current_pos)
                
                if next_end == -1:  # No closing tag found
                    break
                
                if next_start != -1 and next_start < next_end:
                    # Found nested start tag
                    tag_stack.append(next_start)
                    current_pos = next_start + 1
                else:
                    # Found end tag
                    if not tag_stack:  # This is our matching end tag
                        chunk_end = next_end + len(end_pattern)
                        return content[start_pos:chunk_end]
                    else:
                        # Pop nested tag
                        tag_stack.pop()
                        current_pos = next_end + 1
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting complete tag {tag_name}: {e}")
            return None
    
    def parse_xml_tools(self, xml_content: str) -> List[ParsedToolCall]:
        """
        Parse XML content and return list of tool calls.
        
        Args:
            xml_content: XML content to parse
            
        Returns:
            List of ParsedToolCall objects
        """
        tool_calls = []
        
        try:
            # Extract XML chunks
            chunks = self.extract_xml_chunks(xml_content)
            
            for chunk in chunks:
                parsed_call = self._parse_single_tool_call(chunk)
                if parsed_call and not self._is_duplicate(parsed_call):
                    tool_calls.append(parsed_call)
                    
        except Exception as e:
            logger.error(f"Error parsing XML tools: {e}")
        
        return tool_calls
    
    def _parse_single_tool_call(self, xml_chunk: str) -> Optional[ParsedToolCall]:
        """
        Parse a single XML chunk into a tool call.
        """
        try:
            # Extract tag name
            tag_match = re.match(r'<([^\s/>]+)', xml_chunk)
            if not tag_match:
                logger.warning(f"No tag found in XML chunk: {xml_chunk[:100]}...")
                return None
            
            xml_tag_name = tag_match.group(1)
            
            # Normalize function name
            function_name = self.tool_name_mapping.get(xml_tag_name, xml_tag_name.replace('-', '_'))
            
            # Parse XML to extract elements and attributes
            try:
                # Wrap in a root element if needed for parsing
                if not xml_chunk.startswith('<?xml'):
                    wrapped_xml = f"<root>{xml_chunk}</root>"
                    root = ET.fromstring(wrapped_xml)
                    element = root[0]  # Get the actual tool element
                else:
                    element = ET.fromstring(xml_chunk)
                
                # Extract attributes
                attributes = dict(element.attrib)
                
                # Extract child elements as arguments
                arguments = {}
                text_content = ""
                
                # Get direct text content
                if element.text and element.text.strip():
                    text_content = element.text.strip()
                    arguments['content'] = text_content
                
                # Extract child elements
                for child in element:
                    child_name = child.tag
                    child_text = ""
                    
                    # Get all text content including nested elements
                    if child.text:
                        child_text = child.text.strip()
                    
                    # Join text from nested elements
                    for nested in child:
                        if nested.text:
                            child_text += " " + nested.text.strip()
                        if nested.tail:
                            child_text += " " + nested.tail.strip()
                    
                    if child.tail:
                        child_text += " " + child.tail.strip()
                    
                    # Clean up whitespace
                    child_text = re.sub(r'\s+', ' ', child_text).strip()
                    
                    if child_text:
                        arguments[child_name] = child_text
                
                # Apply parameter defaults and coercions
                arguments = self._apply_parameter_defaults(function_name, arguments)
                
                return ParsedToolCall(
                    tag_name=xml_tag_name,
                    function_name=function_name,
                    arguments=arguments,
                    attributes=attributes,
                    text_content=text_content,
                    xml_content=xml_chunk
                )
                
            except ET.ParseError as e:
                logger.warning(f"XML parse error for chunk: {e}")
                # Try to extract arguments using regex as fallback
                return self._parse_with_regex_fallback(xml_chunk, xml_tag_name, function_name)
                
        except Exception as e:
            logger.error(f"Error parsing single tool call: {e}")
            return None
    
    def _parse_with_regex_fallback(self, xml_chunk: str, xml_tag_name: str, function_name: str) -> Optional[ParsedToolCall]:
        """
        Fallback parsing using regex when XML parsing fails.
        """
        try:
            arguments = {}
            
            # Extract content between tags using regex
            content_pattern = rf'<{xml_tag_name}[^>]*>(.*?)</{xml_tag_name}>'
            content_match = re.search(content_pattern, xml_chunk, re.DOTALL)
            
            if content_match:
                inner_content = content_match.group(1).strip()
                
                # Extract child elements
                child_pattern = r'<(\w+)>(.*?)</\1>'
                child_matches = re.findall(child_pattern, inner_content, re.DOTALL)
                
                for child_name, child_content in child_matches:
                    child_content = re.sub(r'\s+', ' ', child_content).strip()
                    arguments[child_name] = child_content
                
                # If no child elements, use the content directly
                if not arguments and inner_content:
                    # Remove any remaining XML tags
                    clean_content = re.sub(r'<[^>]+>', '', inner_content).strip()
                    if clean_content:
                        arguments['content'] = clean_content
            
            # Apply parameter defaults
            arguments = self._apply_parameter_defaults(function_name, arguments)
            
            return ParsedToolCall(
                tag_name=xml_tag_name,
                function_name=function_name,
                arguments=arguments,
                attributes={},
                text_content=arguments.get('content', ''),
                xml_content=xml_chunk
            )
            
        except Exception as e:
            logger.error(f"Error in regex fallback parsing: {e}")
            return None
    
    def _apply_parameter_defaults(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply parameter defaults and coercions based on function name.
        """
        try:
            if function_name == 'web_search':
                # Ensure required parameters
                if 'query' not in arguments and 'content' in arguments:
                    arguments['query'] = arguments['content']
                
                # Set defaults
                if 'summary' not in arguments and 'query' in arguments:
                    arguments['summary'] = arguments['query']
                
                if 'num_results' not in arguments:
                    arguments['num_results'] = 5
                else:
                    # Coerce to int
                    try:
                        arguments['num_results'] = int(arguments['num_results'])
                    except (ValueError, TypeError):
                        arguments['num_results'] = 5
            
            elif function_name == 'crawl_webpage':
                # Ensure URL is present
                if 'url' not in arguments and 'content' in arguments:
                    arguments['url'] = arguments['content'].strip()
            
            elif function_name == 'file_write':
                # Ensure path is present
                if 'path' not in arguments:
                    logger.warning("file_write missing path parameter")
                
                # Content can be in 'content' or as direct text
                if 'content' not in arguments and 'text' in arguments:
                    arguments['content'] = arguments['text']
            
            elif function_name == 'execute_bash':
                # Ensure command is present
                if 'command' not in arguments and 'content' in arguments:
                    arguments['command'] = arguments['content']
            
            elif function_name == 'ask':
                # Handle attachments
                if 'attachments' in arguments:
                    attachments_str = arguments['attachments']
                    if isinstance(attachments_str, str):
                        # Split by newlines or commas
                        attachments = [a.strip() for a in re.split(r'[,\n]', attachments_str) if a.strip()]
                        arguments['attachments'] = attachments
        
        except Exception as e:
            logger.warning(f"Error applying parameter defaults for {function_name}: {e}")
        
        return arguments
    
    def _is_duplicate(self, tool_call: ParsedToolCall) -> bool:
        """
        Check if this tool call is a duplicate using hash-based deduplication.
        """
        try:
            # Create hash from function name and arguments
            hash_content = f"{tool_call.function_name}:{str(sorted(tool_call.arguments.items()))}"
            call_hash = hashlib.sha256(hash_content.encode()).hexdigest()[:16]
            
            if call_hash in self.recent_hashes:
                logger.debug(f"Duplicate tool call detected: {tool_call.function_name}")
                return True
            
            # Add to cache and manage size
            self.recent_hashes.add(call_hash)
            if len(self.recent_hashes) > self.max_cache_size:
                # Remove oldest entries (simple approach - clear half)
                self.recent_hashes = set(list(self.recent_hashes)[self.max_cache_size // 2:])
            
            return False
            
        except Exception as e:
            logger.warning(f"Error checking for duplicates: {e}")
            return False

