/**
 * Types for agentic tool system
 */

import { NormalizedMessage } from '@/lib/normalizeMessage'
import { parseMaybeJSON } from '@/lib/agentRunStream'

export type ToolPayload = {
  tag: 'execute-python' | 'file-write' | 'web-search' | 'daytona-run' | string
  attrs?: Record<string, string>
  result?: any
  error?: string
  logs?: string
  path?: string
  workspace?: string
  mode?: 'local' | 'daytona'
}

export type ToolModel = {
  id: string
  type: 'tool_start' | 'tool_result' | 'tool_error'
  tag?: string
  attrs?: Record<string, string>
  result?: any
  error?: string
  logs?: string
  path?: string
  workspace?: string
  mode?: 'local' | 'daytona'
  created_at: string
}

/**
 * Extract tool model from normalized message
 */
export function getToolModel(msg: NormalizedMessage): ToolModel {
  // Parse content if it's a JSON string
  const contentObj = parseMaybeJSON<any>(msg.content)
  const c = typeof msg._content === 'string' ? { text: msg._content } : (msg._content || contentObj || {})

  return {
    id: msg.id,
    type: msg.type as 'tool_start' | 'tool_result' | 'tool_error',
    tag: c.tag || msg.tool,
    attrs: c.attrs || msg.arguments,
    result: c.result || msg.output,
    error: c.error || msg.error,
    logs: c.logs || c.result?.logs,
    path: c.path || c.result?.path,
    workspace: c.workspace || c.result?.workspace,
    mode: c.mode || c.result?.mode,
    created_at: msg.timestamp || new Date().toISOString(),
  }
}

/**
 * Get display name for a tool
 */
export function getToolDisplayName(tag?: string): string {
  if (!tag) return 'Unknown Tool'

  const displayNames: Record<string, string> = {
    'execute-python': 'Execute Python',
    'file-write': 'File Write',
    'web-search': 'Web Search',
    'daytona-run': 'Daytona Command',
    'execute-bash': 'Execute Command',
    'crawl-webpage': 'Web Crawler',
    'ask': 'Ask User',
    'browser-navigate': 'Browser Navigation',
    'browser-click': 'Browser Click',
    'browser-input': 'Browser Input',
  }

  return displayNames[tag] || tag.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}
