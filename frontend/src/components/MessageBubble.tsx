// src/components/MessageBubble.tsx
import React from 'react'
import ReactMarkdown from 'react-markdown'
import { CitationBadge } from './CitationBadge'
import type { Message, RetrievedChunk } from '../api/types'

interface Props {
  message:    Message
  chunks:     RetrievedChunk[]
  shadowRoot: ShadowRoot | null
}

export function MessageBubble({ message, chunks, shadowRoot }: Props) {
  if (message.role === 'user') {
    return (
      <div className="message-row user">
        <div className="bubble user-bubble">
          <span className="bubble-role">you</span>
          <p className="bubble-text">{message.content}</p>
          <span className="bubble-time">{formatTime(message.timestamp)}</span>
        </div>
      </div>
    )
  }

  const rawText  = message.isStreaming
    ? message.tokens.join('')
    : message.content
  const citations = message.citations
  const hasChunks = chunks.length > 0

  return (
    <div className="message-row assistant">
      <div className="bubble assistant-bubble">

        <span className="bubble-role">assistant</span>

        <div className="bubble-text">
          <ReactMarkdown components={makeMdComponents(citations, chunks, hasChunks, shadowRoot)}>
            {rawText}
          </ReactMarkdown>

          {/* blinking cursor while streaming */}
          {message.isStreaming && <span className="cursor" />}
        </div>

        {/* error card inline */}
        {message.error && (
          <div className={`error-card ${message.error.errorType ?? ''}`}>
            <span className="error-icon">✕</span>
            <div className="error-body">
              <span className="error-type">{errorLabel(message.error.errorType)}</span>
              <span className="error-msg">{message.error.message}</span>
            </div>
            {message.error.errorType === 'rerank_error' && (
              <span className="error-badge">degraded</span>
            )}
          </div>
        )}

        {/* token usage — only show when done */}
        {!message.isStreaming && message.usage && (
          <div className="bubble-usage">
            <span>prompt: {message.usage.promptTokens}</span>
            <span>·</span>
            <span>context: {message.usage.contextTokens}</span>
            <span>·</span>
            <span>completion: {message.usage.completionTokens}</span>
          </div>
        )}

        <span className="bubble-time">{formatTime(message.timestamp)}</span>
      </div>
    </div>
  )
}

// ── inline citation rendering ──────────────────────────
// Processes string children inside markdown block elements and replaces
// [n] markers with CitationBadge components (or pending sups).
function renderWithCitations(
  children:   React.ReactNode,
  citations:  Record<number, string>,
  chunks:     RetrievedChunk[],
  hasChunks:  boolean,
  shadowRoot: ShadowRoot | null,
): React.ReactNode {
  if (!hasChunks) return children

  return React.Children.map(children, (child) => {
    if (typeof child !== 'string') return child

    const parts = splitOnCitations(child)
    if (parts.length === 1 && parts[0].type === 'text') return child

    return parts.map((part, i) => {
      if (part.type === 'text') {
        return <React.Fragment key={i}>{part.content}</React.Fragment>
      }
      const chunkId = citations[part.index]
      if (!chunkId) {
        return (
          <sup key={i} className="citation-badge pending">
            [{part.index}]
          </sup>
        )
      }
      return (
        <CitationBadge
          key={i}
          index={part.index}
          chunkId={chunkId}
          chunks={chunks}
          shadowRoot={shadowRoot}
        />
      )
    })
  })
}

// ── ReactMarkdown component map ────────────────────────
function makeMdComponents(
  citations:  Record<number, string>,
  chunks:     RetrievedChunk[],
  hasChunks:  boolean,
  shadowRoot: ShadowRoot | null,
) {
  const cite = (children: React.ReactNode) =>
    renderWithCitations(children, citations, chunks, hasChunks, shadowRoot)

  return {
    h1: ({ children }: any) => <h1 className="md-h1">{children}</h1>,
    h2: ({ children }: any) => <h2 className="md-h2">{children}</h2>,
    h3: ({ children }: any) => <h3 className="md-h3">{children}</h3>,
    p:  ({ children }: any) => <p  className="md-p">{cite(children)}</p>,
    strong: ({ children }: any) => <strong className="md-bold">{children}</strong>,
    em:     ({ children }: any) => <em className="md-italic">{children}</em>,
    blockquote: ({ children }: any) => (
      <blockquote className="md-blockquote">{children}</blockquote>
    ),
    ul:   ({ children }: any) => <ul  className="md-ul">{children}</ul>,
    ol:   ({ children }: any) => <ol  className="md-ol">{children}</ol>,
    li:   ({ children }: any) => <li  className="md-li">{cite(children)}</li>,
    // react-markdown v10: pre wraps block code, code handles inline
    pre:  ({ children }: any) => <pre className="md-codeblock">{children}</pre>,
    code: ({ children, className }: any) => (
      <code className={className ? `md-code ${className}` : 'md-code'}>{children}</code>
    ),
    // block external links — no navigation out of air-gap
    a:   ({ href, children }: any) => (
      <span className="md-link-blocked" title={href}>{children}</span>
    ),
    img: () => null,
  }
}

// ── split text on [n] citation markers ────────────────
type TextPart     = { type: 'text';     content: string }
type CitationPart = { type: 'citation'; index: number }
type Part = TextPart | CitationPart

function splitOnCitations(text: string): Part[] {
  const parts: Part[] = []
  const pattern       = /\[(\d+)\]/g
  let last            = 0
  let match: RegExpExecArray | null

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > last) {
      parts.push({ type: 'text', content: text.slice(last, match.index) })
    }
    parts.push({ type: 'citation', index: parseInt(match[1], 10) })
    last = match.index + match[0].length
  }

  if (last < text.length) {
    parts.push({ type: 'text', content: text.slice(last) })
  }

  return parts.length > 0 ? parts : [{ type: 'text', content: text }]
}

// ── helpers ───────────────────────────────────────────
function formatTime(ts: number): string {
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function errorLabel(type: string | undefined): string {
  switch (type) {
    case 'retrieval_error': return 'Retrieval failed'
    case 'model_error':     return 'Model error'
    case 'rerank_error':    return 'Reranking unavailable'
    default:                return 'Error'
  }
}
