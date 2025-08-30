/**
 * Agent Run View Component
 *
 * Renders agent run messages using the new tool system
 */

import React from 'react'
import { AgentMessage } from '@/lib/agentRunStream'
import { normalizeMessage, NormalizedMessage } from '@/lib/normalizeMessage'
import { getToolModel } from './tools/types'
import { getToolView } from './tools/registry'
import { Markdown } from '@/components/ui/markdown'
import { cn } from '@/lib/utils'
import Image from 'next/image'

interface AgentRunViewProps {
  messages: AgentMessage[]
  className?: string
}

interface AssistantMessageProps {
  content: string
  className?: string
}

interface UserMessageProps {
  content: string
  className?: string
}

interface StatusPillProps {
  status: string
  className?: string
}

/**
 * Main Agent Run View component
 */
export function AgentRunView({ messages, className }: AgentRunViewProps) {
  return (
    <div className={cn('flex flex-col space-y-3', className)}>
      {messages.map((raw) => {
        const msg = normalizeMessage(raw)
        return <MessageRenderer key={msg.id} message={msg} />
      })}
    </div>
  )
}

/**
 * Render individual normalized messages
 */
function MessageRenderer({ message }: { message: NormalizedMessage }) {
  switch (message.type) {
    case 'tool_start':
    case 'tool_result':
    case 'tool_error':
      return <ToolMessageRenderer message={message} />

    case 'assistant':
      return <AssistantMessage content={message.content || ''} />

    case 'user':
      return <UserMessage content={message.content || ''} />

    case 'status':
      return <StatusPill status={message.status_type || message.message || 'status'} />

    default:
      return <GenericMessage message={message} />
  }
}

/**
 * Render tool messages using the new tool system
 */
function ToolMessageRenderer({ message }: { message: NormalizedMessage }) {
  const toolModel = getToolModel(message)
  const ToolView = getToolView(toolModel.tag)

  // Convert ToolModel to ToolViewProps format for existing tool views
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
  }

  return <ToolView {...toolViewProps} />
}

/**
 * Assistant message component
 */
function AssistantMessage({ content, className }: AssistantMessageProps) {
  if (!content) return null

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
  )
}

/**
 * User message component
 */
function UserMessage({ content, className }: UserMessageProps) {
  if (!content) return null

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
  )
}

/**
 * Status pill component
 */
function StatusPill({ status, className }: StatusPillProps) {
  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'running':
      case 'thread_run_start':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
      case 'completed':
      case 'done':
      case 'thread_run_end':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
      case 'error':
      case 'failed':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
    }
  }

  return (
    <div className={cn('flex justify-center', className)}>
      <span className={cn('px-3 py-1 rounded-full text-xs font-medium', getStatusColor(status))}>
        {status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
      </span>
    </div>
  )
}

/**
 * Generic message component for unknown message types
 */
function GenericMessage({ message }: { message: NormalizedMessage }) {
  return (
    <div className="rounded-lg border p-3 bg-muted/10">
      <div className="text-xs text-muted-foreground mb-1">
        {message.type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
      </div>
      <div className="text-sm">
        {typeof message._content === 'string'
          ? message._content
          : JSON.stringify(message._content || message, null, 2)
        }
      </div>
    </div>
  )
}
