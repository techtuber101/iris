/**
 * Message Normalizer for Frontend
 * 
 * This module normalizes various message formats into canonical types
 * for consistent rendering in the frontend.
 */

export interface NormalizedMessage {
  id: string;
  type: 'user' | 'assistant' | 'tool_call' | 'tool_result' | 'tool_start' | 'tool_error' | 'status' | 'unknown';
  content?: string;
  _content?: any; // Parsed content object
  tool?: string;
  arguments?: Record<string, any>;
  output?: any;
  success?: boolean;
  error?: string;
  status_type?: string;
  message?: string;
  timestamp?: string;
  metadata?: Record<string, any>;
  raw?: any; // Original message for debugging
}

/**
 * Normalize a message from various formats into canonical format
 */
export function normalizeMessage(message: any): NormalizedMessage {
  try {
    // Handle null/undefined
    if (!message) {
      return {
        id: generateId(),
        type: 'unknown',
        raw: message
      };
    }

    // If already normalized, return as-is
    if (message.type && ['user', 'assistant', 'tool_call', 'tool_result', 'tool_start', 'tool_error', 'status'].includes(message.type)) {
      return {
        id: message.id || message.message_id || generateId(),
        ...message
      };
    }

    // Handle legacy/synthetic message formats
    const normalized: NormalizedMessage = {
      id: message.id || message.message_id || generateId(),
      type: 'unknown',
      raw: message
    };

    // Parse content if it's a JSON string
    let content = message.content;
    let parsedContent: any = undefined;
    if (typeof content === 'string') {
      try {
        const parsed = JSON.parse(content);
        if (typeof parsed === 'object') {
          parsedContent = parsed;
          content = parsed;
        }
      } catch {
        // Keep as string if not valid JSON
      }
    }

    // Set _content for easier access to parsed content
    normalized._content = parsedContent;

    // Determine message type and normalize
    if (message.type === 'status') {
      normalized.type = 'status';
      normalized.status_type = message.status_type || message.status;
      normalized.message = message.message || message.content;
      
      // Handle tool-related status messages
      if (message.status_type === 'tool_started') {
        normalized.type = 'status';
        normalized.message = 'Computer is starting...';
      } else if (message.status_type === 'tool_completed') {
        normalized.type = 'status';
        normalized.message = 'Done';
      }
    }
    else if (message.type === 'tool' || message.role === 'tool') {
      // Handle legacy tool messages - try to parse into tool_call or tool_result
      const toolMessage = parseToolMessage(message, content);
      if (toolMessage) {
        return toolMessage;
      }
      
      normalized.type = 'tool_result';
      normalized.tool = extractToolName(message, content);
      normalized.output = content || message.output;
      normalized.success = message.success !== false; // Default to true unless explicitly false
    }
    else if (message.type === 'user' || message.role === 'user') {
      normalized.type = 'user';
      normalized.content = typeof content === 'string' ? content : content?.content || JSON.stringify(content);
    }
    else if (message.type === 'assistant' || message.role === 'assistant') {
      normalized.type = 'assistant';
      normalized.content = typeof content === 'string' ? content : content?.content || JSON.stringify(content);
    }
    else if (message.type === 'tool_start') {
      normalized.type = 'tool_start';
      if (content && typeof content === 'object') {
        normalized.tool = content.tag;
        normalized.arguments = content.attrs;
      }
      normalized.content = message.content || JSON.stringify(content);
    }
    else if (message.type === 'tool_result') {
      normalized.type = 'tool_result';
      if (content && typeof content === 'object') {
        normalized.tool = content.tag;
        normalized.output = content.result;
        normalized.success = content.result?.ok !== false;
        normalized.error = content.result?.error;
      }
      normalized.content = message.content || JSON.stringify(content);
    }
    else if (message.type === 'tool_error') {
      normalized.type = 'tool_error';
      if (content && typeof content === 'object') {
        normalized.tool = content.tag;
        normalized.error = content.error;
        normalized.success = false;
      }
      normalized.content = message.content || JSON.stringify(content);
    }
    else {
      // Try to detect tool calls/results from content
      const detectedType = detectMessageType(content || message);
      if (detectedType) {
        return detectedType;
      }
      
      // Default to unknown
      normalized.type = 'unknown';
      normalized.content = JSON.stringify(message);
    }

    // Add metadata
    normalized.timestamp = message.timestamp || message.created_at;
    normalized.metadata = message.metadata ? (typeof message.metadata === 'string' ? JSON.parse(message.metadata) : message.metadata) : {};

    return normalized;

  } catch (error) {
    console.error('Error normalizing message:', error);
    return {
      id: generateId(),
      type: 'unknown',
      content: `Error normalizing message: ${error}`,
      raw: message
    };
  }
}

/**
 * Parse legacy tool messages that might contain escaped JSON or XML wrappers
 */
function parseToolMessage(message: any, content: any): NormalizedMessage | null {
  try {
    // Check if content contains tool_result XML wrapper
    if (typeof content === 'string' && content.includes('<tool_result>')) {
      const match = content.match(/<tool_result[^>]*>(.*?)<\/tool_result>/gs);
      if (match) {
        try {
          const resultData = JSON.parse(match[1]);
          return {
            id: message.id || generateId(),
            type: 'tool_result',
            tool: resultData.tool || extractToolName(message, content),
            output: resultData.output || resultData,
            success: resultData.success !== false,
            error: resultData.error,
            timestamp: message.timestamp
          };
        } catch {
          // If JSON parse fails, use raw content
          return {
            id: message.id || generateId(),
            type: 'tool_result',
            tool: extractToolName(message, content),
            output: match[1],
            success: true,
            timestamp: message.timestamp
          };
        }
      }
    }

    // Check if content is escaped JSON
    if (typeof content === 'string' && (content.startsWith('{') || content.includes('role:'))) {
      try {
        const parsed = JSON.parse(content);
        if (parsed.type === 'tool_call') {
          return {
            id: message.id || generateId(),
            type: 'tool_call',
            tool: parsed.tool,
            arguments: parsed.arguments,
            timestamp: message.timestamp
          };
        } else if (parsed.type === 'tool_result') {
          return {
            id: message.id || generateId(),
            type: 'tool_result',
            tool: parsed.tool,
            output: parsed.output,
            success: parsed.success,
            error: parsed.error,
            timestamp: message.timestamp
          };
        }
      } catch {
        // Not valid JSON, continue
      }
    }

    return null;
  } catch {
    return null;
  }
}

/**
 * Extract tool name from various message formats
 */
function extractToolName(message: any, content: any): string {
  // Try metadata first
  if (message.metadata) {
    const metadata = typeof message.metadata === 'string' ? JSON.parse(message.metadata) : message.metadata;
    if (metadata.tool_name || metadata.function_name) {
      return metadata.tool_name || metadata.function_name;
    }
  }

  // Try to extract from content
  if (typeof content === 'string') {
    // Look for XML tags
    const xmlMatch = content.match(/<([a-zA-Z-]+)/);
    if (xmlMatch) {
      return xmlMatch[1].replace('-', '_');
    }
    
    // Look for function names in JSON
    const funcMatch = content.match(/"function_name":\s*"([^"]+)"/);
    if (funcMatch) {
      return funcMatch[1];
    }
  }

  return 'unknown';
}

/**
 * Detect message type from content patterns
 */
function detectMessageType(content: any): NormalizedMessage | null {
  if (!content) return null;

  const contentStr = typeof content === 'string' ? content : JSON.stringify(content);

  // Look for tool call patterns
  if (contentStr.includes('tool_call') || contentStr.includes('function_name')) {
    try {
      const parsed = typeof content === 'string' ? JSON.parse(content) : content;
      if (parsed.type === 'tool_call' || parsed.function_name) {
        return {
          id: generateId(),
          type: 'tool_call',
          tool: parsed.tool || parsed.function_name,
          arguments: parsed.arguments || {},
          timestamp: parsed.timestamp
        };
      }
    } catch {
      // Continue to other checks
    }
  }

  // Look for tool result patterns
  if (contentStr.includes('tool_result') || contentStr.includes('success') || contentStr.includes('output')) {
    try {
      const parsed = typeof content === 'string' ? JSON.parse(content) : content;
      if (parsed.type === 'tool_result' || (parsed.hasOwnProperty('success') && parsed.hasOwnProperty('output'))) {
        return {
          id: generateId(),
          type: 'tool_result',
          tool: parsed.tool || 'unknown',
          output: parsed.output,
          success: parsed.success,
          error: parsed.error,
          timestamp: parsed.timestamp
        };
      }
    } catch {
      // Continue to other checks
    }
  }

  return null;
}

/**
 * Generate a unique ID for messages
 */
function generateId(): string {
  return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Normalize an array of messages
 */
export function normalizeMessages(messages: any[]): NormalizedMessage[] {
  if (!Array.isArray(messages)) {
    return [];
  }

  return messages.map(normalizeMessage);
}

/**
 * Check if a message should be rendered as a tool view
 */
export function isToolMessage(message: NormalizedMessage): boolean {
  return message.type === 'tool_call' || message.type === 'tool_result' || message.type === 'tool_start' || message.type === 'tool_error';
}

/**
 * Check if a message should be rendered as a status chip
 */
export function isStatusMessage(message: NormalizedMessage): boolean {
  return message.type === 'status';
}

/**
 * Get display name for a tool
 */
export function getToolDisplayName(toolName: string): string {
  const displayNames: Record<string, string> = {
    'web_search': 'Web Search',
    'file_write': 'File Write',
    'execute-python': 'Execute Python',
    'daytona-run': 'Daytona Command',
    'execute_bash': 'Code Execution',
    'crawl_webpage': 'Web Crawler',
    'ask': 'Ask User',
    'browser_navigate': 'Browser Navigation',
    'browser_click': 'Browser Click',
    'browser_input': 'Browser Input'
  };

  return displayNames[toolName] || toolName.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

