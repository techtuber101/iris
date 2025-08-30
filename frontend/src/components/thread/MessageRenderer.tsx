/**
 * Message Renderer Component
 * 
 * This component renders messages using the normalized message format
 * and canonical tool views, eliminating raw JSON dumps in the chat.
 */

import React from 'react';
import { normalizeMessage, NormalizedMessage, isToolMessage, isStatusMessage } from '@/lib/normalizeMessage';
import {
  ToolCallView,
  ToolResultView,
  StatusChip,
  ToolCallCard,
  ToolResultCard,
  UnknownMessage
} from './CanonicalToolViews';
import { getToolModel } from './tools/types';
import { getToolView, hasSpecificView } from './tools/registry';
import { Markdown } from '@/components/ui/markdown';
import { cn } from '@/lib/utils';
import Image from 'next/image';

interface MessageRendererProps {
  message: any; // Raw message from API
  className?: string;
}

interface AssistantMessageProps {
  content: string;
  className?: string;
}

interface UserMessageProps {
  content: string;
  className?: string;
}

/**
 * Main message renderer that handles all message types
 */
export function MessageRenderer({ message, className }: MessageRendererProps) {
  const normalized = normalizeMessage(message);

  return (
    <div className={cn('message-renderer', className)}>
      {renderNormalizedMessage(normalized)}
    </div>
  );
}

/**
 * Render a normalized message based on its type
 */
function renderNormalizedMessage(message: NormalizedMessage): React.ReactNode {
  switch (message.type) {
    case 'tool_call':
      return <ToolCallView message={message} state="running" />;

    case 'tool_start':
    case 'tool_result':
    case 'tool_error':
      // Check if we have a specific view for this tool
      const toolModel = getToolModel(message);
      if (hasSpecificView(toolModel.tag)) {
        const ToolView = getToolView(toolModel.tag);
        // Convert ToolModel to ToolViewProps format
        const toolViewProps = {
          name: toolModel.tag,
          assistantContent: JSON.stringify({
            tag: toolModel.tag,
            attrs: toolModel.attrs,
            workspace: toolModel.workspace,
            cmd: toolModel.attrs?.cmd,
            path: toolModel.path
          }),
          toolContent: JSON.stringify({
            result: toolModel.result,
            error: toolModel.error,
            logs: toolModel.logs,
            mode: toolModel.mode
          }),
          isSuccess: !toolModel.error,
          isStreaming: toolModel.type === 'tool_start',
          toolTimestamp: toolModel.created_at
        };
        return <ToolView {...toolViewProps} />;
      }
      // Fall back to legacy views
      if (message.type === 'tool_start') {
        return <ToolCallView message={message} state="running" />;
      }
      return <ToolResultView message={message} state={message.success ? 'done' : 'error'} />;

    case 'assistant':
      return <AssistantMessage content={message.content || ''} />;

    case 'user':
      return <UserMessage content={message.content || ''} />;

    case 'status':
      return <StatusChip message={message} />;

    case 'unknown':
    default:
      // For debugging - show unknown messages in development
      if (process.env.NODE_ENV === 'development') {
        return <UnknownMessage message={message} />;
      }
      // In production, try to render as tool card if it looks like a tool message
      if (message.tool || (message.raw && (message.raw.tool || message.raw.function_name))) {
        if (message.raw?.type === 'tool_call' || message.raw?.function_name) {
          return <ToolCallCard message={message} />;
        } else {
          return <ToolResultCard message={message} />;
        }
      }
      return null; // Don't render unknown messages in production
  }
}

/**
 * Assistant message component
 */
function AssistantMessage({ content, className }: AssistantMessageProps) {
  if (!content) return null;

  return (
    <div className={cn('flex items-start gap-3', className)}>
      <div className="flex-shrink-0 w-5 h-5 mt-2 rounded-md flex items-center justify-center overflow-hidden ml-auto mr-2">
        <Image 
          src="/iris-symbol.png" 
          alt="Iris" 
          width={14} 
          height={14} 
          className="object-contain invert dark:invert-0 opacity-70" 
        />
      </div>
      <div className="flex-1">
        <div className="inline-flex max-w-[90%] rounded-lg bg-muted/5 px-4 py-3 text-sm">
          <Markdown>{content}</Markdown>
        </div>
      </div>
    </div>
  );
}

/**
 * User message component
 */
function UserMessage({ content, className }: UserMessageProps) {
  if (!content) return null;

  return (
    <div className={cn('flex items-start gap-3 justify-end', className)}>
      <div className="flex-1">
        <div className="inline-flex max-w-[90%] rounded-lg bg-primary px-4 py-3 text-sm text-primary-foreground ml-auto">
          <div className="whitespace-pre-wrap">{content}</div>
        </div>
      </div>
      <div className="flex-shrink-0 w-5 h-5 mt-2 rounded-md bg-primary flex items-center justify-center text-primary-foreground text-xs font-medium">
        U
      </div>
    </div>
  );
}

/**
 * Message group renderer for handling multiple related messages
 */
interface MessageGroupRendererProps {
  messages: any[];
  className?: string;
}

export function MessageGroupRenderer({ messages, className }: MessageGroupRendererProps) {
  if (!messages || messages.length === 0) return null;

  // Normalize all messages
  const normalizedMessages = messages.map(normalizeMessage);

  // Group related tool calls and results
  const groupedMessages = groupRelatedMessages(normalizedMessages);

  return (
    <div className={cn('message-group-renderer space-y-2', className)}>
      {groupedMessages.map((group, index) => (
        <div key={index} className="message-group">
          {group.map((message, msgIndex) => (
            <div key={`${message.id}-${msgIndex}`} className="mb-2">
              {renderNormalizedMessage(message)}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

/**
 * Group related messages (e.g., tool_call followed by tool_result)
 */
function groupRelatedMessages(messages: NormalizedMessage[]): NormalizedMessage[][] {
  const groups: NormalizedMessage[][] = [];
  let currentGroup: NormalizedMessage[] = [];

  for (const message of messages) {
    // Start a new group for user messages or assistant messages
    if (message.type === 'user' || message.type === 'assistant') {
      if (currentGroup.length > 0) {
        groups.push(currentGroup);
        currentGroup = [];
      }
      currentGroup.push(message);
    }
    // Add tool messages and status to current group
    else if (message.type === 'tool_call' || message.type === 'tool_result' || message.type === 'status') {
      currentGroup.push(message);
    }
    // Handle unknown messages
    else {
      currentGroup.push(message);
    }
  }

  // Add the last group if it has messages
  if (currentGroup.length > 0) {
    groups.push(currentGroup);
  }

  return groups;
}

/**
 * Utility function to check if a message should be rendered
 */
export function shouldRenderMessage(message: any): boolean {
  const normalized = normalizeMessage(message);
  
  // Always render user and assistant messages
  if (normalized.type === 'user' || normalized.type === 'assistant') {
    return true;
  }
  
  // Always render tool messages
  if (isToolMessage(normalized)) {
    return true;
  }
  
  // Render status messages except for internal ones
  if (isStatusMessage(normalized)) {
    const internalStatuses = ['thread_run_start', 'thread_run_end', 'routing_decision'];
    return !internalStatuses.includes(normalized.status_type || '');
  }
  
  // In development, render unknown messages for debugging
  if (process.env.NODE_ENV === 'development') {
    return true;
  }
  
  // In production, don't render unknown messages
  return false;
}

/**
 * Debug component to show raw message data (development only)
 */
export function MessageDebugView({ message }: { message: any }) {
  if (process.env.NODE_ENV !== 'development') {
    return null;
  }

  const normalized = normalizeMessage(message);

  return (
    <details className="mt-2 p-2 bg-gray-100 dark:bg-gray-800 rounded text-xs">
      <summary className="cursor-pointer font-mono">Debug: {normalized.type}</summary>
      <div className="mt-2 space-y-2">
        <div>
          <strong>Normalized:</strong>
          <pre className="mt-1 p-2 bg-gray-200 dark:bg-gray-700 rounded overflow-auto">
            {JSON.stringify(normalized, null, 2)}
          </pre>
        </div>
        <div>
          <strong>Raw:</strong>
          <pre className="mt-1 p-2 bg-gray-200 dark:bg-gray-700 rounded overflow-auto">
            {JSON.stringify(message, null, 2)}
          </pre>
        </div>
      </div>
    </details>
  );
}

