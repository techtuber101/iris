/**
 * File Write Tool View
 *
 * Renders the file-write tool with path and status
 */

import React from 'react'
import { ToolViewProps } from '../../tool-views/types'
import { CircleDashed, CheckCircle, AlertTriangle, FileText } from 'lucide-react'
import { cn } from '@/lib/utils'

export function FileWriteView({
  name,
  assistantContent,
  toolContent,
  isSuccess,
  isStreaming,
  toolTimestamp
}: ToolViewProps) {
  // Parse assistant content to extract file path
  let filePath = 'unknown file'
  let error = ''

  try {
    if (assistantContent) {
      const parsed = typeof assistantContent === 'string' ? JSON.parse(assistantContent) : assistantContent
      if (parsed && typeof parsed === 'object') {
        filePath = parsed.path || filePath
      }
    }
    if (toolContent) {
      const parsed = typeof toolContent === 'string' ? JSON.parse(toolContent) : toolContent
      if (parsed && typeof parsed === 'object') {
        error = parsed.error || ''
        filePath = parsed.path || filePath
      }
    }
  } catch {
    // If parsing fails, use raw values
    if (typeof assistantContent === 'string') {
      filePath = assistantContent
    }
  }

  const getStatusIcon = () => {
    if (!isSuccess && error) return <AlertTriangle className="w-4 h-4 text-red-500" />
    if (isSuccess) return <CheckCircle className="w-4 h-4 text-green-500" />
    return <CircleDashed className="w-4 h-4 text-blue-500 animate-spin" />
  }

  const getStatusText = () => {
    if (!isSuccess && error) return 'Failed'
    if (isSuccess) return 'Created'
    return 'Writing…'
  }

  return (
    <div className="rounded-2xl border p-4 bg-background">
      {/* Header */}
      <div className="flex items-center gap-3 mb-3">
        {getStatusIcon()}
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-muted-foreground" />
          <span className="font-medium">File Write</span>
        </div>
      </div>

      {/* Status */}
      <div className="text-sm text-muted-foreground mb-2">
        {getStatusText()}
      </div>

      {/* File Path */}
      <div className="text-sm">
        <span className="text-muted-foreground">Path:</span>{' '}
        {isSuccess ? (
          <a
            href={`/files?path=${encodeURIComponent(filePath)}`}
            className="underline hover:text-primary"
          >
            {filePath}
          </a>
        ) : (
          <code className="bg-muted px-1 py-0.5 rounded text-xs">
            {filePath}
          </code>
        )}
      </div>

      {/* Error */}
      {error && (
        <pre className="mt-2 p-2 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded text-sm text-red-800 dark:text-red-200 whitespace-pre-wrap">
          {error}
        </pre>
      )}

      {/* Starting state */}
      {isStreaming && (
        <div className="text-sm text-muted-foreground mt-2">
          Creating file at {filePath}…
        </div>
      )}
    </div>
  )
}
