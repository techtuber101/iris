/**
 * Default Tool View
 *
 * Fallback component for unknown or unmapped tools
 */

import React from 'react'
import { ToolViewProps } from '../../tool-views/types'
import { CircleDashed, CheckCircle, AlertTriangle, Wrench } from 'lucide-react'
import { cn } from '@/lib/utils'

export function DefaultToolView({
  name,
  assistantContent,
  toolContent,
  isSuccess,
  isStreaming,
  toolTimestamp
}: ToolViewProps) {
  // Parse content to extract parameters and results
  let error = ''
  let result = ''
  let logs = ''

  try {
    if (assistantContent) {
      const parsed = typeof assistantContent === 'string' ? JSON.parse(assistantContent) : assistantContent
      if (parsed && typeof parsed === 'object') {
        // Extract parameters from assistant content
      }
    }
    if (toolContent) {
      const parsed = typeof toolContent === 'string' ? JSON.parse(toolContent) : toolContent
      if (parsed && typeof parsed === 'object') {
        error = parsed.error || ''
        result = parsed.result || ''
        logs = parsed.logs || ''
      }
    }
  } catch {
    // If parsing fails, use raw values
    if (typeof toolContent === 'string') {
      result = toolContent
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

  const getToolName = () => {
    return name || 'Unknown Tool'
  }

  return (
    <div className="rounded-2xl border p-4 bg-background">
      {/* Header */}
      <div className="flex items-center gap-3 mb-3">
        {getStatusIcon()}
        <div className="flex items-center gap-2">
          <Wrench className="w-4 h-4 text-muted-foreground" />
          <span className="font-medium">Tool: {getToolName()}</span>
        </div>
      </div>

      {/* Status */}
      <div className="text-sm text-muted-foreground mb-2">
        {getStatusText()}
      </div>

      {/* Assistant Content (Parameters) */}
      {assistantContent && (
        <div className="mb-3">
          <div className="text-xs text-muted-foreground mb-1">Parameters:</div>
          <div className="text-xs bg-muted/30 p-2 rounded">
            {typeof assistantContent === 'string'
              ? assistantContent
              : JSON.stringify(assistantContent, null, 2)
            }
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <pre className="mt-2 p-2 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded text-sm text-red-800 dark:text-red-200 whitespace-pre-wrap">
          {error}
        </pre>
      )}

      {/* Result */}
      {result && (
        <div className="mt-3">
          <div className="text-xs text-muted-foreground mb-1">Result:</div>
          <pre className="p-2 bg-muted/30 rounded text-xs whitespace-pre-wrap max-h-64 overflow-auto">
            {result}
          </pre>
        </div>
      )}

      {/* Logs */}
      {logs && (
        <div className="mt-3">
          <div className="text-xs text-muted-foreground mb-1">Logs:</div>
          <pre className="p-2 bg-muted/30 rounded text-xs whitespace-pre-wrap max-h-64 overflow-auto">
            {logs}
          </pre>
        </div>
      )}

      {/* Starting state */}
      {isStreaming && (
        <div className="text-sm text-muted-foreground">
          Executing {getToolName()}…
        </div>
      )}
    </div>
  )
}
