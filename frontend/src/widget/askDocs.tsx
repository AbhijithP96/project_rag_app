// src/widget/AskDocsWidget.tsx
import { useReducer, useRef, useEffect } from 'react'
import { useConversation } from '../hooks/useConv'
import { MessageBubble }    from '../components/MessageBubble'
import { TokenBudget }      from '../components/TokenBudget'
import { ContextInspector } from '../components/ContextInspector'
import { LogPanel }         from '../components/LogPanel'
import { logger }           from '../utils/logger'
import type { WidgetOptions, IndexStatus } from './types'
import { IndexManager } from '../components/IndexManager'

interface Props {
  options:    WidgetOptions
  shadowHost: HTMLElement
}

interface UIState {
  theme:       'light' | 'dark'
  indexStatus: IndexStatus
  indexId:     string | undefined
  logOpen:     boolean
}

type UIAction =
  | { type: 'TOGGLE_THEME' }
  | { type: 'TOGGLE_LOG' }
  | { type: 'SET_INDEX_STATUS'; payload: IndexStatus; indexId?: string }

function reducer(state: UIState, action: UIAction): UIState {
  switch (action.type) {
    case 'TOGGLE_THEME':
      return { ...state, theme: state.theme === 'dark' ? 'light' : 'dark' }
    case 'TOGGLE_LOG':
      return { ...state, logOpen: !state.logOpen }
    case 'SET_INDEX_STATUS':
      return { ...state, indexStatus: action.payload, indexId: action.indexId }
  }
}

export function AskDocsWidget({ options, shadowHost }: Props) {
  const [ui, dispatch] = useReducer(reducer, {
    theme:       options.theme ?? 'dark',
    indexStatus: 'idle',
    indexId:     undefined,
    logOpen:     false,
  })

  const {
    messages,
    stream,
    submitQuery,
    finaliseMessage,
    cancel,
    reset,
  } = useConversation(options.tokenCount ?? 8192)

  const messagesRef = useRef<HTMLDivElement>(null)
  const inputRef    = useRef<HTMLInputElement>(null)
  const inputVal    = useRef<string>('')

  // get shadow root for citation popovers
  const shadowRoot  = shadowHost.shadowRoot

  // finalise active message when stream completes
  useEffect(() => {
    if (stream.phase === 'done' || stream.phase === 'error') {
      finaliseMessage()
    }
  }, [stream.phase])

  // auto-scroll as tokens arrive
  useEffect(() => {
    if (messagesRef.current) {
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight
    }
  }, [stream.tokens, messages.length])

  // log widget mount
  useEffect(() => {
    logger.info('system', `widget mounted · api: ${options.apiBase}`)
    logger.info('system', `budget: ${options.tokenCount ?? 8192} tokens`)
  }, [])

  const toggleTheme = () => {
    const next = ui.theme === 'dark' ? 'light' : 'dark'
    shadowHost.setAttribute('data-theme', next)
    dispatch({ type: 'TOGGLE_THEME' })
    logger.info('system', `theme → ${next}`)
  }

  const handleSubmit = () => {
    const query = inputVal.current.trim()
    if (!query || stream.isStreaming) return
    if (inputRef.current) inputRef.current.value = ''
    inputVal.current = ''
    submitQuery(query, ui.indexId)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleReset = () => {
    reset()
    if (inputRef.current) inputRef.current.value = ''
    inputVal.current = ''
  }

  // latest usage — from last assistant message or live stream
  const latestUsage = stream.usage ??
    [...messages].reverse().find(m => m.usage)?.usage ?? null

  return (
    <div className="widget-shell">

      {/* ── TOP BAR ── */}
      <div className="top-bar">
        <div className="left">
          <span className={`status-dot status-${ui.indexStatus}`} />
          <span className="title">AskDocs</span>
          {stream.isStreaming && (
            <span className="phase-label">{stream.phase}</span>
          )}
        </div>
        <div className="top-bar-actions">
          <button
            className="theme-toggle"
            onClick={handleReset}
            title="New chat"
            aria-label="New chat"
            disabled={stream.isStreaming}
          >
            ↺
          </button>
          <button
            className="theme-toggle"
            onClick={toggleTheme}
            title="Toggle theme"
            aria-label="Toggle theme"
          >
            {ui.theme === 'dark' ? '◑' : '◐'}
          </button>
        </div>
      </div>

      {/* ── INDEX MANAGER — sits below top bar ── */}
      <IndexManager
        onStatusChange={(status, indexId) =>
          dispatch({ type: 'SET_INDEX_STATUS', payload: status, indexId })
        }
      />

      {/* ── MAIN AREA — messages + inspector side by side ── */}
      <div className="main-area">

        {/* ── MESSAGE COLUMN ── */}
        <div className="message-column">

          {/* message list */}
          <div className="message-area" ref={messagesRef}>

            {/* empty state */}
            {messages.length === 0 && (
              <div className="empty-state">
                <p className="empty-title">AskDocs</p>
                <p className="empty-sub">
                  Ask anything about your indexed documents
                </p>
              </div>
            )}

            {/* phase indicator — retrieval / reranking */}
            {stream.isStreaming &&
              stream.phase !== 'generating' &&
              stream.phase !== 'idle' && (
              <div className="phase-indicator">
                <span className="phase-spinner" />
                <span className="phase-text">{phaseLabel(stream.phase)}</span>
              </div>
            )}

            {/* conversation history */}
            {messages.map(message => (
              <MessageBubble
                key={message.id}
                message={
                  message.isStreaming
                    ? {
                        ...message,
                        tokens:    stream.tokens,
                        citations: stream.citations,
                        chunks:    stream.chunks,
                        error:     stream.error,
                      }
                    : message
                }
                chunks={
                  message.isStreaming
                    ? stream.chunks      // live chunks during streaming
                    : message.chunks     // persisted chunks after done
                }
                shadowRoot={shadowRoot}
              />
            ))}

          </div>

          {/* token budget bar — above input */}
          <TokenBudget
            usage={latestUsage}
            isStreaming={stream.isStreaming}
          />

          {/* input bar */}
          <div className="input-bar">
            <input
              ref={inputRef}
              className="query-input"
              type="text"
              placeholder="Ask a question..."
              defaultValue=""
              onChange={e => { inputVal.current = e.target.value }}
              onKeyDown={handleKeyDown}
              disabled={stream.isStreaming}
            />
            <button
              className={`send-btn ${stream.isStreaming ? 'streaming' : ''}`}
              onClick={stream.isStreaming ? cancel : handleSubmit}
              aria-label={stream.isStreaming ? 'Cancel' : 'Send'}
            >
              {stream.isStreaming ? '◼' : '↑'}
            </button>
          </div>

        </div>

        {/* ── CONTEXT INSPECTOR — right column ── */}
        {(stream.chunks.length > 0 || stream.phase !== 'idle') && (
          <div className="inspector-column">
            <ContextInspector
              chunks={stream.chunks}
              phase={stream.phase}
            />
          </div>
        )}

      </div>

      {/* ── LOG DRAWER — bottom ── */}
      <LogPanel
        open={ui.logOpen}
        onToggle={() => dispatch({ type: 'TOGGLE_LOG' })}
      />

      {/* ── STATUS BAR ── */}
      <div className="status-bar">
        <span>
          {ui.indexStatus === 'idle'
            ? 'No index loaded · 0 chunks'
            : `${ui.indexStatus} · ${stream.chunks.length} chunks`}
        </span>
        <button
          className="log-toggle-btn"
          onClick={() => dispatch({ type: 'TOGGLE_LOG' })}
          title="Toggle pipeline log"
        >
          {ui.logOpen ? '▾ log' : '▴ log'}
        </button>
        <span className="api-base">{options.apiBase}</span>
      </div>

    </div>
  )
}

function phaseLabel(phase: string): string {
  switch (phase) {
    case 'retrieving': return 'Searching documents...'
    case 'reranking':  return 'Reranking results...'
    case 'generating': return 'Generating response...'
    default:           return ''
  }
}