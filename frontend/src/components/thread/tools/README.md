# Agentic Tools Frontend System

This directory contains the frontend components for the agentic tools system, which provides rich UI components for displaying tool execution status and results.

## Overview

The agentic tools system processes backend messages with types `tool_start`, `tool_result`, and `tool_error` and renders them with appropriate UI components based on the tool type.

## Architecture

### Core Components

- **`types.ts`** - Type definitions and utility functions for tool models
- **`registry.tsx`** - Tool registry mapping tags to view components
- **`views/`** - Individual tool view components
- **`../AgentRunView.tsx`** - Main component for rendering agent runs
- **`../MessageRenderer.tsx`** - Updated to use the new tool system

### Tool Views

#### `ExecutePythonView`
- Displays Python code execution status
- Shows execution mode (local/daytona)
- Renders output logs with proper formatting
- Handles error states with red highlighting

#### `FileWriteView`
- Shows file creation/writing status
- Displays file path with clickable links
- Provides feedback on creation success/failure

#### `DaytonaRunView`
- Displays Daytona workspace commands
- Shows command execution status
- Renders command output and logs
- Workspace identification

#### `DefaultToolView`
- Fallback component for unknown tools
- Generic JSON display of tool data
- Expandable parameter and result views

## Usage

### Basic Usage

```tsx
import { AgentRunView } from './components/thread/AgentRunView'
import { useAgentRun } from './hooks/useAgentRun'

// In your component
const { messages, isStreaming } = useAgentRun(runId)

return (
  <AgentRunView messages={messages} />
)
```

### Tool Registry

Tools are automatically mapped using the registry:

```tsx
// Adding a new tool view
import { MyCustomToolView } from './views/MyCustomToolView'

TOOL_VIEWS['my-custom-tool'] = MyCustomToolView
```

### Message Flow

1. Backend emits `tool_start` → Shows loading state
2. Backend emits `tool_result` → Shows completion with results
3. Backend emits `tool_error` → Shows error state

## Integration

The system integrates with the existing message rendering pipeline:

1. **MessageRenderer** checks if a tool has a specific view
2. **Tool registry** maps tool tags to components
3. **Tool views** render with appropriate status and data
4. **Streaming updates** are handled via message ID merging

## Features

- **Streaming Support** - Real-time updates for long-running tools
- **Error Handling** - Proper error states and user feedback
- **Responsive Design** - Works on all screen sizes
- **Dark Mode** - Full dark mode support
- **Accessibility** - Proper ARIA labels and keyboard navigation
- **Performance** - Efficient re-renders using React.memo

## Development

### Adding New Tool Views

1. Create a new component in `views/`
2. Follow the `ToolModel` interface from `types.ts`
3. Handle all three states: `tool_start`, `tool_result`, `tool_error`
4. Add to the registry in `registry.tsx`

### Testing

Use the `AgentRunExample` component to test tool views with mock data.

## Backend Integration

The frontend expects these message formats from the backend:

```typescript
interface AgentMessage {
  message_id: string
  thread_id: string
  type: 'tool_start' | 'tool_result' | 'tool_error'
  content: string  // JSON with tool payload
  created_at: string
  updated_at: string
}
```

Tool payload structure:
```typescript
{
  tag: 'execute-python' | 'file-write' | 'daytona-run' | string
  attrs?: Record<string, string>
  result?: any
  error?: string
  logs?: string
  path?: string
  workspace?: string
  mode?: 'local' | 'daytona'
}
```
