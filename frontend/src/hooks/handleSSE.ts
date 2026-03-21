// src/hooks/useSSEStream.ts
import { useState, useCallback, useRef } from 'react'
import { mockQuery } from '../api/mockapi'
import type { SSEEvent, RetrievedChunk } from '../api/types'
import { logger } from '../utils/logger'

export interface StreamState {
  isStreaming:   boolean
  tokens:        string[]        // all tokens received so far
  chunks:        RetrievedChunk[] // retrieved + reranked chunks
  citations:     Record<number, string> // citationIndex → chunkId
  usage:         SSEEvent['usage'] | null
  error:         { errorType: SSEEvent['errorType']; message: string } | null
  phase:         'idle' | 'retrieving' | 'reranking' | 'generating' | 'done' | 'error'
}

const initialState: StreamState = {
  isStreaming: false,
  tokens:      [],
  chunks:      [],
  citations:   {},
  usage:       null,
  error:       null,
  phase:       'idle',
}

export function useSSEStream(budgetLimit: number = 8192) {
  const [state, setState] = useState<StreamState>(initialState)
  const abortRef = useRef(false)

  const sendQuery = useCallback(async (query: string, indexId?: string, sessionId?: string) => {
    abortRef.current = false

    setState({
      ...initialState,
      isStreaming: true,
      phase: 'retrieving',
    })

    const generator = mockQuery(query, budgetLimit, indexId, sessionId)

    for await (const event of generator) {
      if (abortRef.current) break

      setState(prev => {
        switch (event.type) {

          case 'retrieval_start':
            logger.info('retrieval', 'searching documents...')
            return { ...prev, phase: 'retrieving' }

          case 'retrieval_complete':
            logger.info('retrieval',
              `${event.chunks?.length ?? 0} chunks retrieved`,
              { chunks: event.chunks?.map(c => c.source) }
            )
            return { ...prev, chunks: event.chunks ?? [] }

          case 'rerank_complete':
            logger.info('reranking',
              `rerank complete · top score: ${event.chunks?.[0]?.score.toFixed(2) ?? 'n/a'}`,
              { scores: event.chunks?.map(c => c.score) }
            )
            return { ...prev, chunks: event.chunks ?? prev.chunks, phase: 'reranking' }

          case 'generation_start':
            logger.info('generation', 'streaming started')
            return { ...prev, phase: 'generating' }

          case 'citation':
            return {
              ...prev,
              citations: {
                ...prev.citations,
                [event.citationIndex ?? 0]: event.citationId ?? '',
              },
            }

          case 'token':
            // don't log every token — too noisy
            return { ...prev, tokens: [...prev.tokens, event.token ?? ''] }

          case 'token_usage':
            logger.info('tokens',
              `${event.usage?.completionTokens ?? 0} tokens generated`
            )
            return { ...prev, usage: event.usage ?? null }

          case 'done':
            logger.info('stream', 'done')
            return { ...prev, isStreaming: false, phase: 'done' }

          case 'error':
            if (event.errorType === 'rerank_error') {
              logger.warn('reranking', event.message ?? 'reranker unavailable — degraded mode')
              return {
                ...prev,
                error: { errorType: event.errorType, message: event.message ?? '' },
              }
            }
            logger.error('error', event.message ?? 'unknown error', { errorType: event.errorType })
            return {
              ...prev,
              isStreaming: false,
              phase: 'error',
              error: { errorType: event.errorType, message: event.message ?? '' },
            }

          default:
            return prev
        }
      })
    }
  }, [budgetLimit])

  const cancel = useCallback(() => {
    abortRef.current = true
    setState(prev => ({ ...prev, isStreaming: false, phase: 'idle' }))
  }, [])

  const reset = useCallback(() => {
    abortRef.current = true
    setState(initialState)
  }, [])

  return { state, sendQuery, cancel, reset }
}