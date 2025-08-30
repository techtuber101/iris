/**
 * Canonical Tool Views for normalized messages
 * 
 * These components render tool calls and results using the existing tool view components
 * but with the new canonical message format.
 */

import React from 'react';
import { NormalizedMessage } from '@/lib/normalizeMessage';
import { WebSearchToolView } from './tool-views/WebSearchToolView';
import { FileOperationToolView } from './tool-views/FileOperationToolView';
import { CommandToolView } from './tool-views/CommandToolView';
import { WebCrawlToolView } from './tool-views/WebCrawlToolView';
import { GenericToolView } from './tool-views/GenericToolView';
import { CircleDashed, CheckCircle, AlertTriangle, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ToolCallViewProps {
  message: NormalizedMessage;
  state?: 'running' | 'done' | 'error';
}

interface ToolResultViewProps {
  message: NormalizedMessage;
  state?: 'done' | 'error';
}

interface StatusChipProps {
  message: NormalizedMessage;
}

/**
 * Renders a tool call in progress
 */
export function ToolCallView({ message, state = 'running' }: ToolCallViewProps) {
  const { tool, arguments: args } = message;

  // Convert arguments to assistant content format for existing tool views
  const assistantContent = formatArgumentsForDisplay(tool, args);

  const commonProps = {
    name: tool,
    assistantContent,
    toolContent: '',
    isSuccess: state !== 'error',
    isStreaming: state === 'running',
    assistantTimestamp: message.timestamp,
  };

  // Route to appropriate tool view based on tool name
  switch (tool) {
    case 'web_search':
      return <WebSearchToolView {...commonProps} />;
    
    case 'file_write':
    case 'create_file':
    case 'str_replace':
      return <FileOperationToolView {...commonProps} />;
    
    case 'execute_bash':
    case 'execute_command':
      return <CommandToolView {...commonProps} />;
    
    case 'crawl_webpage':
      return <WebCrawlToolView {...commonProps} />;
    
    default:
      return <GenericToolView {...commonProps} />;
  }
}

/**
 * Renders a completed tool result
 */
export function ToolResultView({ message, state = 'done' }: ToolResultViewProps) {
  const { tool, output, success, error } = message;

  // Format output for display
  const toolContent = formatOutputForDisplay(output);
  
  const commonProps = {
    name: tool,
    assistantContent: '', // No assistant content for results
    toolContent,
    isSuccess: success !== false && !error,
    isStreaming: false,
    toolTimestamp: message.timestamp,
  };

  // Route to appropriate tool view based on tool name
  switch (tool) {
    case 'web_search':
      return <WebSearchToolView {...commonProps} />;
    
    case 'file_write':
    case 'create_file':
    case 'str_replace':
      return <FileOperationToolView {...commonProps} />;
    
    case 'execute_bash':
    case 'execute_command':
      return <CommandToolView {...commonProps} />;
    
    case 'crawl_webpage':
      return <WebCrawlToolView {...commonProps} />;
    
    default:
      return <GenericToolView {...commonProps} />;
  }
}

/**
 * Renders a status chip for lifecycle events
 */
export function StatusChip({ message }: StatusChipProps) {
  const { status_type, message: statusMessage } = message;

  const getStatusIcon = () => {
    switch (status_type) {
      case 'assistant_response_start':
      case 'tool_started':
      case 'agent_working':
        return <CircleDashed className="h-3 w-3 animate-spin" />;
      case 'tool_completed':
      case 'execution_completed':
        return <CheckCircle className="h-3 w-3" />;
      case 'tool_error':
        return <AlertTriangle className="h-3 w-3" />;
      default:
        return <Clock className="h-3 w-3" />;
    }
  };

  const getStatusColor = () => {
    switch (status_type) {
      case 'tool_completed':
      case 'execution_completed':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'tool_error':
        return 'text-red-600 bg-red-50 border-red-200';
      default:
        return 'text-blue-600 bg-blue-50 border-blue-200';
    }
  };

  // Don't render certain internal status types
  if (['thread_run_start', 'thread_run_end', 'routing_decision'].includes(status_type || '')) {
    return null;
  }

  return (
    <div className={cn(
      'inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium border',
      getStatusColor()
    )}>
      {getStatusIcon()}
      <span>{statusMessage || status_type}</span>
    </div>
  );
}

/**
 * Generic tool call/result card for unknown tools
 */
export function ToolCallCard({ message }: { message: NormalizedMessage }) {
  const { tool, arguments: args, type } = message;

  return (
    <div className="border border-zinc-200 dark:border-zinc-800 rounded-md overflow-hidden">
      <div className="flex items-center p-2 bg-zinc-100 dark:bg-zinc-900 justify-between border-b border-zinc-200 dark:border-zinc-800">
        <div className="flex items-center">
          <CircleDashed className="h-4 w-4 mr-2 text-zinc-600 dark:text-zinc-400" />
          <span className="text-xs font-medium text-zinc-700 dark:text-zinc-300">
            {tool?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) || 'Unknown Tool'}
          </span>
        </div>
        <span className="text-xs text-zinc-500">
          {type === 'tool_call' ? 'Running...' : 'Completed'}
        </span>
      </div>
      
      <div className="p-3 bg-white dark:bg-zinc-950">
        <pre className="text-xs font-mono text-zinc-700 dark:text-zinc-300 whitespace-pre-wrap">
          {JSON.stringify(args || message.output || {}, null, 2)}
        </pre>
      </div>
    </div>
  );
}

/**
 * Generic tool result card for unknown tools
 */
export function ToolResultCard({ message }: { message: NormalizedMessage }) {
  const { tool, output, success, error } = message;

  return (
    <div className="border border-zinc-200 dark:border-zinc-800 rounded-md overflow-hidden">
      <div className="flex items-center p-2 bg-zinc-100 dark:bg-zinc-900 justify-between border-b border-zinc-200 dark:border-zinc-800">
        <div className="flex items-center">
          {success ? (
            <CheckCircle className="h-4 w-4 mr-2 text-green-600" />
          ) : (
            <AlertTriangle className="h-4 w-4 mr-2 text-red-600" />
          )}
          <span className="text-xs font-medium text-zinc-700 dark:text-zinc-300">
            {tool?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) || 'Unknown Tool'}
          </span>
        </div>
        <span className={cn(
          'text-xs',
          success ? 'text-green-600' : 'text-red-600'
        )}>
          {success ? 'Success' : 'Failed'}
        </span>
      </div>
      
      <div className="p-3 bg-white dark:bg-zinc-950">
        {error ? (
          <div className="text-red-600 text-xs font-mono mb-2">
            Error: {error}
          </div>
        ) : null}
        <pre className="text-xs font-mono text-zinc-700 dark:text-zinc-300 whitespace-pre-wrap">
          {typeof output === 'string' ? output : JSON.stringify(output, null, 2)}
        </pre>
      </div>
    </div>
  );
}

/**
 * Unknown message component for debugging
 */
export function UnknownMessage({ message }: { message: NormalizedMessage }) {
  return (
    <div className="border border-amber-200 dark:border-amber-800 rounded-md overflow-hidden bg-amber-50 dark:bg-amber-950">
      <div className="flex items-center p-2 bg-amber-100 dark:bg-amber-900 border-b border-amber-200 dark:border-amber-800">
        <AlertTriangle className="h-4 w-4 mr-2 text-amber-600" />
        <span className="text-xs font-medium text-amber-700 dark:text-amber-300">
          Unknown Message Type
        </span>
      </div>
      
      <div className="p-3">
        <pre className="text-xs font-mono text-amber-700 dark:text-amber-300 whitespace-pre-wrap">
          {JSON.stringify(message.raw || message, null, 2)}
        </pre>
      </div>
    </div>
  );
}

/**
 * Helper function to format arguments for display in existing tool views
 */
function formatArgumentsForDisplay(tool?: string, args?: Record<string, any>): string {
  if (!args) return '';

  switch (tool) {
    case 'web_search':
      return args.query || args.content || '';
    
    case 'file_write':
    case 'create_file':
      return JSON.stringify({
        path: args.path,
        content: args.content
      });
    
    case 'execute_bash':
    case 'execute_command':
      return args.command || args.content || '';
    
    case 'crawl_webpage':
      return args.url || args.content || '';
    
    default:
      return JSON.stringify(args);
  }
}

/**
 * Helper function to format output for display in existing tool views
 */
function formatOutputForDisplay(output: any): string {
  if (typeof output === 'string') {
    return output;
  }
  
  if (output && typeof output === 'object') {
    return JSON.stringify(output, null, 2);
  }
  
  return String(output || '');
}

