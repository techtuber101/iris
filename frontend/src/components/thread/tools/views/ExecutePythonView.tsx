/**
 * Execute Python Tool View
 *
 * Renders the execute-python tool with status, mode, and logs
 */

import React from 'react'
import { ToolViewProps } from '../../tool-views/types'
import { CircleDashed, CheckCircle, AlertTriangle, Code } from 'lucide-react'
import { cn } from '@/lib/utils'

export function ExecutePythonView({
  name,
  assistantContent,
  toolContent,
  isSuccess,
  isStreaming,
  toolTimestamp
}: ToolViewProps) {
  // Parse tool content to extract mode and other metadata
  let mode = 'sandbox'
  let logs = ''
  let error = ''

  try {
    if (toolContent) {
      const parsed = typeof toolContent === 'string' ? JSON.parse(toolContent) : toolContent
      if (parsed && typeof parsed === 'object') {
        mode = parsed.mode || 'sandbox'
        logs = parsed.logs || ''
        error = parsed.error || ''
      }
    }
  } catch {
    // If parsing fails, treat toolContent as logs
    logs = String(toolContent || '')
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
          <Code className="w-4 h-4 text-muted-foreground" />
          <span className="font-medium">Python Execution</span>
          <span className="text-xs bg-muted px-2 py-1 rounded">
            {mode}
          </span>
        </div>
      </div>

      {/* Status */}
      <div className="text-sm text-muted-foreground mb-2">
        {getStatusText()}
      </div>

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
          Executing Python code in {mode} environment…
        </div>
      )}
    </div>
  )
}
