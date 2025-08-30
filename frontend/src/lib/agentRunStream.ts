/**
 * Agent Run Stream utilities
 *
 * Handles connecting to agent run streams and managing real-time updates
 */

export type AgentMessage = {
  message_id: string
  thread_id: string
  type: 'assistant' | 'user' | 'status' | 'tool_start' | 'tool_result' | 'tool_error' | 'cost'
  is_llm_message: boolean
  content: string            // JSON string for tool_* and status; plain text for user/assistant
  metadata?: string          // JSON string (optional)
  created_at: string
  updated_at: string
}

/**
 * Connect to an agent run stream using EventSource
 */
export function connectRunStream(runId: string, onEvent: (msg: AgentMessage) => void): () => void {
  const url = `/api/agent-run/${runId}/stream`

  // Create EventSource connection
  const es = new EventSource(url)

  es.onmessage = (e) => {
    try {
      const msg: AgentMessage = JSON.parse(e.data)
      onEvent(msg)
    } catch (error) {
      console.error('Failed to parse agent message:', error, e.data)
    }
  }

  es.onerror = (error) => {
    console.error('Agent run stream error:', error)
    // You might want to implement retry logic here
  }

  // Return cleanup function
  return () => {
    es.close()
  }
}

/**
 * Parse maybe JSON content safely
 */
export function parseMaybeJSON<T>(raw?: string | null): T | undefined {
  if (!raw) return undefined
  try {
    return JSON.parse(raw) as T
  } catch {
    return undefined
  }
}
