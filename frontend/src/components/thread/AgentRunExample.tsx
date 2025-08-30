/**
 * Agent Run Example Component
 *
 * Demonstrates how to use the new agentic tool system
 */

import React, { useState } from 'react'
import { AgentRunView } from './AgentRunView'
import { useAgentRun } from '@/hooks/useAgentRun'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { AlertCircle, Play, Square } from 'lucide-react'

interface AgentRunExampleProps {
  threadId?: string
}

export function AgentRunExample({ threadId }: AgentRunExampleProps) {
  const [runId, setRunId] = useState<string>('')
  const [inputRunId, setInputRunId] = useState<string>('')

  const {
    messages,
    isStreaming,
    error,
    startStreaming,
    stopStreaming,
    clear
  } = useAgentRun(runId || undefined)

  const handleStartStreaming = () => {
    if (inputRunId.trim()) {
      setRunId(inputRunId.trim())
      startStreaming(inputRunId.trim())
    }
  }

  const handleStopStreaming = () => {
    stopStreaming()
  }

  const handleClear = () => {
    clear()
    setRunId('')
    setInputRunId('')
  }

  return (
    <div className="space-y-4">
      {/* Control Panel */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Play className="w-5 h-5" />
            Agent Run Viewer
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Input
              placeholder="Enter agent run ID"
              value={inputRunId}
              onChange={(e) => setInputRunId(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleStartStreaming()}
            />
            <Button
              onClick={handleStartStreaming}
              disabled={isStreaming || !inputRunId.trim()}
            >
              {isStreaming ? 'Streaming...' : 'Start'}
            </Button>
          </div>

          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={handleStopStreaming}
              disabled={!isStreaming}
            >
              <Square className="w-4 h-4 mr-1" />
              Stop
            </Button>
            <Button
              variant="outline"
              onClick={handleClear}
              disabled={messages.length === 0}
            >
              Clear
            </Button>
          </div>

          {isStreaming && (
            <div className="flex items-center gap-2 text-sm text-green-600">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              Streaming active
            </div>
          )}

          {error && (
            <div className="flex items-center gap-2 text-sm text-red-600">
              <AlertCircle className="w-4 h-4" />
              {error}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Messages */}
      {messages.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Run Messages ({messages.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <AgentRunView messages={messages} />
          </CardContent>
        </Card>
      )}

      {/* Example Tool Messages for Testing */}
      {!runId && (
        <Card>
          <CardHeader>
            <CardTitle>Example Tool Messages</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="text-sm text-muted-foreground">
              These are example tool messages to demonstrate the UI components:
            </div>

            <AgentRunView messages={[
              {
                message_id: 'example-1',
                thread_id: 'example-thread',
                type: 'tool_start',
                is_llm_message: false,
                content: JSON.stringify({
                  tag: 'execute-python',
                  attrs: { workspace: 'test' },
                }),
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
              },
              {
                message_id: 'example-2',
                thread_id: 'example-thread',
                type: 'tool_result',
                is_llm_message: false,
                content: JSON.stringify({
                  tag: 'execute-python',
                  result: {
                    ok: true,
                    mode: 'daytona',
                    logs: 'Python 3.11.0\nHello from agentic tools!\n'
                  }
                }),
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
              },
              {
                message_id: 'example-3',
                thread_id: 'example-thread',
                type: 'tool_start',
                is_llm_message: false,
                content: JSON.stringify({
                  tag: 'file-write',
                  attrs: { path: 'output.txt' },
                }),
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
              },
              {
                message_id: 'example-4',
                thread_id: 'example-thread',
                type: 'tool_result',
                is_llm_message: false,
                content: JSON.stringify({
                  tag: 'file-write',
                  result: { ok: true, path: 'output.txt' }
                }),
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
              },
              {
                message_id: 'example-5',
                thread_id: 'example-thread',
                type: 'tool_start',
                is_llm_message: false,
                content: JSON.stringify({
                  tag: 'daytona-run',
                  attrs: { cmd: 'ls -la', workspace: 'my-workspace' },
                }),
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
              },
              {
                message_id: 'example-6',
                thread_id: 'example-thread',
                type: 'tool_result',
                is_llm_message: false,
                content: JSON.stringify({
                  tag: 'daytona-run',
                  result: { ok: true, workspace: 'my-workspace' },
                  logs: 'total 48\ndrwxr-xr-x  8 user  group   256 Jan 15 10:30 .\ndrwxr-xr-x  3 user  group    96 Jan 15 10:25 ..\n'
                }),
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
              }
            ]} />
          </CardContent>
        </Card>
      )}
    </div>
  )
}
