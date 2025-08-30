/**
 * Agent Run Hook
 *
 * Manages agent run state with streaming support
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { AgentMessage } from '@/lib/agentRunStream'

type AgentRunState = {
  byId: Record<string, AgentMessage>
  order: string[]
  isStreaming: boolean
  error: string | null
}

/**
 * Hook for managing agent run state
 */
export function useAgentRun(runId?: string) {
  const [state, setState] = useState<AgentRunState>({
    byId: {},
    order: [],
    isStreaming: false,
    error: null,
  })

  const streamCleanupRef = useRef<(() => void) | null>(null)

  /**
   * Add or update a message in the state
   */
  const updateMessage = useCallback((message: AgentMessage) => {
    setState(prevState => {
      const existingIndex = prevState.order.indexOf(message.message_id)

      if (existingIndex >= 0) {
        // Update existing message
        return {
          ...prevState,
          byId: {
            ...prevState.byId,
            [message.message_id]: { ...prevState.byId[message.message_id], ...message }
          }
        }
      } else {
        // Add new message
        return {
          ...prevState,
          byId: {
            ...prevState.byId,
            [message.message_id]: message
          },
          order: [...prevState.order, message.message_id]
        }
      }
    })
  }, [])

  /**
   * Start streaming for a run
   */
  const startStreaming = useCallback(async (targetRunId: string) => {
    if (streamCleanupRef.current) {
      streamCleanupRef.current()
    }

    setState(prev => ({ ...prev, isStreaming: true, error: null }))

    try {
      // Dynamic import to avoid SSR issues
      const { connectRunStream } = await import('@/lib/agentRunStream')

      const cleanup = connectRunStream(targetRunId, (message) => {
        updateMessage(message)
      })

      streamCleanupRef.current = cleanup
    } catch (error) {
      console.error('Failed to start streaming:', error)
      setState(prev => ({
        ...prev,
        isStreaming: false,
        error: error instanceof Error ? error.message : 'Failed to start streaming'
      }))
    }
  }, [updateMessage])

  /**
   * Stop streaming
   */
  const stopStreaming = useCallback(() => {
    if (streamCleanupRef.current) {
      streamCleanupRef.current()
      streamCleanupRef.current = null
    }
    setState(prev => ({ ...prev, isStreaming: false }))
  }, [])

  /**
   * Load initial messages for a run
   */
  const loadRun = useCallback(async (targetRunId: string) => {
    try {
      const response = await fetch(`/api/thread/agent-runs`)
      if (!response.ok) {
        throw new Error(`Failed to fetch run: ${response.status}`)
      }

      const runs = await response.json()
      const run = runs.find((r: any) => r.id === targetRunId)

      if (run && run.messages) {
        // Load existing messages
        run.messages.forEach((message: AgentMessage) => {
          updateMessage(message)
        })
      }
    } catch (error) {
      console.error('Failed to load run:', error)
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Failed to load run'
      }))
    }
  }, [updateMessage])

  /**
   * Clear all messages
   */
  const clear = useCallback(() => {
    stopStreaming()
    setState({
      byId: {},
      order: [],
      isStreaming: false,
      error: null,
    })
  }, [stopStreaming])

  // Auto-start streaming when runId changes
  useEffect(() => {
    if (runId) {
      loadRun(runId)
      startStreaming(runId)
    } else {
      stopStreaming()
    }

    return () => {
      stopStreaming()
    }
  }, [runId, loadRun, startStreaming, stopStreaming])

  return {
    messages: state.order.map(id => state.byId[id]).filter(Boolean),
    isStreaming: state.isStreaming,
    error: state.error,
    updateMessage,
    startStreaming,
    stopStreaming,
    clear,
  }
}
