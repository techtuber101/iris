/**
 * Tool Registry for Agentic Tools
 *
 * Maps tool tags to their respective view components
 */

import React from 'react'
import { ToolViewProps } from '../tool-views/types'
import { ToolModel } from './types'

// Import existing tool views
import { CommandToolView } from '../tool-views/CommandToolView'
import { FileOperationToolView } from '../tool-views/FileOperationToolView'
import { WebSearchToolView } from '../tool-views/WebSearchToolView'
import { GenericToolView } from '../tool-views/GenericToolView'

// Import new agentic tool views
import { ExecutePythonView } from './views/ExecutePythonView'
import { FileWriteView } from './views/FileWriteView'
import { DaytonaRunView } from './views/DaytonaRunView'
import { DefaultToolView } from './views/DefaultToolView'

export type ToolViewComponent = React.FC<ToolViewProps>

export const TOOL_VIEWS: Record<string, ToolViewComponent> = {
  'execute-python': ExecutePythonView,
  'file-write': FileWriteView,
  'web-search': WebSearchToolView,
  'daytona-run': DaytonaRunView,
  // Legacy mappings for existing tools
  'execute-bash': CommandToolView,
  'execute_command': CommandToolView,
  'create_file': FileOperationToolView,
  'str_replace': FileOperationToolView,
  'crawl_webpage': WebSearchToolView,
}

/**
 * Get the appropriate tool view component for a tool tag
 */
export function getToolView(tag?: string): ToolViewComponent {
  if (!tag) return DefaultToolView

  // Use specific views for agentic tools, fallback to existing views
  const specificViews = ['execute-python', 'file-write', 'daytona-run']
  if (specificViews.includes(tag)) {
    return TOOL_VIEWS[tag] ?? DefaultToolView
  }

  // For other tools, use existing views
  return TOOL_VIEWS[tag] ?? GenericToolView
}

/**
 * Check if a tool tag has a specific view
 */
export function hasSpecificView(tag?: string): boolean {
  if (!tag) return false
  const specificViews = ['execute-python', 'file-write', 'daytona-run']
  return specificViews.includes(tag) && TOOL_VIEWS[tag] !== DefaultToolView
}
