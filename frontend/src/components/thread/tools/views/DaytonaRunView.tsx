/**
 * Daytona Run Tool View
 *
 * Renders the daytona-run tool with workspace, command, and logs
 */

import React from 'react'
import { ToolViewProps } from '../../tool-views/types'
import { CircleDashed, CheckCircle, AlertTriangle, Terminal } from 'lucide-react'
import { cn } from '@/lib/utils'

export function DaytonaRunView({
  name,
  assistantContent,
  toolContent,
  isSuccess,
  isStreaming,
  toolTimestamp
}: ToolViewProps) {
  // Parse content to extract workspace, command, and other metadata
  let workspace = 'default'
  let command = ''
  let logs = ''
  let error = ''

  try {
    if (assistantContent) {
      const parsed = typeof assistantContent === 'string' ? JSON.parse(assistantContent) : assistantContent
      if (parsed && typeof parsed === 'object') {
        workspace = parsed.workspace || workspace
        command = parsed.cmd || command
      }
    }
    if (toolContent) {
      const parsed = typeof toolContent === 'string' ? JSON.parse(toolContent) : toolContent
      if (parsed && typeof parsed === 'object') {
        workspace = parsed.workspace || workspace
        logs = parsed.logs || ''
        error = parsed.error || ''
      }
    }
  } catch {
    // If parsing fails, use raw values
    if (typeof assistantContent === 'string') {
      command = assistantContent
    }
    if (typeof toolContent === 'string') {
      logs = toolContent
    }
  }

  const getStatusIcon = () => {
    if (!isSuccess && error) return <AlertTriangle className="w-4 h-4 text-red-500" />
    if (isSuccess) return <CheckCircle className="w-4 h-4 text-green-500" />
    return <CircleDashed className="w-4 h-4 text-blue-500 animate-spin" />
  }

  const getStatusText = () => {
    if (!isSuccess && error) return 'Failed'
    if (isSuccess) return 'Completed'
    return 'Running…'
  }

  return (
    <div className="rounded-2xl border p-4 bg-background">
      {/* Header */}
      <div className="flex items-center gap-3 mb-3">
        {getStatusIcon()}
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-muted-foreground" />
          <span className="font-medium">Daytona Command</span>
          <span className="text-xs bg-muted px-2 py-1 rounded">
            {workspace}
          </span>
        </div>
      </div>

      {/* Status */}
      <div className="text-sm text-muted-foreground mb-2">
        {getStatusText()}
      </div>

      {/* Command */}
      {command && (
        <div className="mb-3">
          <div className="text-xs text-muted-foreground mb-1">Command:</div>
          <code className="bg-muted px-2 py-1 rounded text-xs block whitespace-pre-wrap">
            {command}
          </code>
        </div>
      )}

      {/* Error */}
      {error && (
        <pre className="mt-2 p-2 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded text-sm text-red-800 dark:text-red-200 whitespace-pre-wrap">
          {error}
        </pre>
      )}

      {/* Logs */}
      {logs && (
        <div className="mt-3">
          <div className="text-xs text-muted-foreground mb-1">Output:</div>
          <pre className="p-3 bg-muted/30 rounded text-xs whitespace-pre-wrap max-h-64 overflow-auto">
            {logs}
          </pre>
        </div>
      )}

      {/* Starting state */}
      {isStreaming && (
        <div className="text-sm text-muted-foreground">
          Running command in Daytona workspace {workspace}…
        </div>
      )}
    </div>
  )
}
