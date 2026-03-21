import { useState, useCallback, useRef } from 'react'
import { useSSEStream } from './handleSSE'
import { logger } from '../utils/logger'
import type { Message } from '../api/types'

function generateId(): string {
  return `msg-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
}

export function useConversation(budgetLimit: number = 8192) {
  const [messages, setMessages] = useState<Message[]>([])
  // stable per-tab session ID — never persisted, so each tab is isolated
  const sessionId = useRef<string>(crypto.randomUUID())
  const { state: stream, sendQuery, cancel, reset: resetStream } = useSSEStream(budgetLimit)

  // ── add a user message and fire the query ─────────────
  const submitQuery = useCallback(async (query: string, indexId?: string) => {
    if (!query.trim() || stream.isStreaming) return

    // 1. push user message immediately
    const userMsg: Message = {
      id:          generateId(),
      role:        'user',
      content:     query,
      tokens:      [],
      chunks:      [],
      citations:   {},
      error:       null,
      usage:       null,
      timestamp:   Date.now(),
      isStreaming: false,
    }

    setMessages(prev => [...prev, userMsg])
    logger.info('stream', `query sent: "${query}"`)

    // 2. push empty assistant message as placeholder
    const assistantId = generateId()
    const assistantMsg: Message = {
      id:          assistantId,
      role:        'assistant',
      content:     '',
      tokens:      [],
      chunks:      [],
      citations:   {},
      error:       null,
      usage:       null,
      timestamp:   Date.now(),
      isStreaming: true,
    }

    setMessages(prev => [...prev, assistantMsg])

    // 3. fire the stream — updates come via stream state
    await sendQuery(query, indexId, sessionId.current)

  }, [stream.isStreaming, sendQuery])

  // ── sync stream state into the active assistant message ──
  // This effect runs whenever stream state changes and updates
  // the last assistant message in the history
  useState(() => {
    // intentional: we derive assistant message content from stream state
    // the last message in the array is always the active assistant message
  })

  // ── finalise the active assistant message when done ───
  const finaliseMessage = useCallback(() => {
  setMessages(prev => {
    const last = prev[prev.length - 1]
    if (!last || last.role !== 'assistant') return prev

    const updated: Message = {
      ...last,
      content:     stream.tokens.join(''),
      tokens:      stream.tokens,
      chunks:      stream.chunks,      // ← persist chunks on message
      citations:   stream.citations,
      error:       stream.error,
      usage:       stream.usage,
      isStreaming: false,
    }

    logger.info('stream', 'done', {
      tokens: stream.tokens.length,
      chunks: stream.chunks.length,
    })

    if (stream.usage) {
      logger.info('usage',
        `prompt: ${stream.usage.promptTokens} · ` +
        `context: ${stream.usage.contextTokens} · ` +
        `completion: ${stream.usage.completionTokens}`
      )
    }

    return [...prev.slice(0, -1), updated]
  })
}, [stream])

  // ── clear everything ──────────────────────────────────
  const reset = useCallback(() => {
    resetStream()
    setMessages([])
    logger.info('system', 'conversation cleared')
  }, [resetStream])

  // ── cancel active stream ──────────────────────────────
  const handleCancel = useCallback(() => {
    cancel()
    logger.warn('stream', 'cancelled by user')
    // finalise whatever tokens arrived before cancel
    setMessages(prev => {
      const last = prev[prev.length - 1]
      if (!last || last.role !== 'assistant') return prev
      return [...prev.slice(0, -1), {
        ...last,
        content:     stream.tokens.join(''),
        tokens:      stream.tokens,
        isStreaming: false,
      }]
    })
  }, [cancel, stream.tokens])

  return {
    messages,
    stream,          // expose raw stream state for token budget + phase indicator
    submitQuery,
    finaliseMessage,
    cancel:           handleCancel,
    reset,
  }
}