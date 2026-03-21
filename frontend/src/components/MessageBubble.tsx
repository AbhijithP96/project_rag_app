// src/components/MessageBubble.tsx
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
          <span className="bubble-time">
            {formatTime(message.timestamp)}
          </span>
        </div>
      </div>
    )
  }

  // ── assistant message ──────────────────────────────────
  // split content on citation markers [n] and interleave badges
  const parts = splitOnCitations(
    message.isStreaming
      ? message.tokens.join('')   // live tokens during stream
      : message.content            // finalised content after done
  )

  return (
    <div className="message-row assistant">
      <div className="bubble assistant-bubble">

        <span className="bubble-role">assistant</span>

        <div className="bubble-text">
          {parts.map((part, i) => {
            if (part.type === 'text') {
              return (
                <ReactMarkdown key={i} components={mdComponents}>
                  {part.content}
                </ReactMarkdown>
              )
            }

            if (part.type === 'citation') {
              const chunkId = message.citations[part.index]
              if (!chunkId) {
                // citation not yet received — show plain text
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
            }

            return null
          })}

          {/* blinking cursor while streaming */}
          {message.isStreaming && <span className="cursor" />}
        </div>

        {/* error card inline */}
        {message.error && (
          <div className={`error-card ${message.error.errorType ?? ''}`}>
            <span className="error-icon">✕</span>
            <div className="error-body">
              <span className="error-type">
                {errorLabel(message.error.errorType)}
              </span>
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

        <span className="bubble-time">
          {formatTime(message.timestamp)}
        </span>

      </div>
    </div>
  )
}

// ── ReactMarkdown component overrides ─────────────────
// maps markdown elements to shadow-DOM safe class names
// a and img are blocked — no external resource fetches in air-gapped environments
const mdComponents = {
  p:    ({ children }: any) => <p className="md-p">{children}</p>,
  strong:({ children }: any) => <strong className="md-bold">{children}</strong>,
  em:   ({ children }: any) => <em className="md-italic">{children}</em>,
  code: ({ children, className }: any) => {
    const isBlock = className?.includes('language-')
    return isBlock
      ? <pre className="md-codeblock"><code>{children}</code></pre>
      : <code className="md-code">{children}</code>
  },
  ul:   ({ children }: any) => <ul className="md-ul">{children}</ul>,
  ol:   ({ children }: any) => <ol className="md-ol">{children}</ol>,
  li:   ({ children }: any) => <li className="md-li">{children}</li>,
  // block external links — render as plain text to prevent navigation out of air-gap
  a:    ({ href, children }: any) => (
    <span className="md-link-blocked" title={href}>{children}</span>
  ),
  // block images — prevent browser from fetching external URLs
  img:  () => null,
}

// ── split text on [n] citation markers ────────────────
type TextPart     = { type: 'text';     content: string }
type CitationPart = { type: 'citation'; index: number }
type Part = TextPart | CitationPart

function splitOnCitations(text: string): Part[] {
  const parts: Part[]  = []
  const pattern        = /\[(\d+)\]/g
  let last             = 0
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

  // if no citations found, return whole text as one part
  if (parts.length === 0) {
    parts.push({ type: 'text', content: text })
  }

  return parts
}

// ── helpers ───────────────────────────────────────────
function formatTime(ts: number): string {
  return new Date(ts).toLocaleTimeString([], {
    hour:   '2-digit',
    minute: '2-digit',
  })
}

function errorLabel(type: string | undefined): string {
  switch (type) {
    case 'retrieval_error': return 'Retrieval failed'
    case 'model_error':     return 'Model error'
    case 'rerank_error':    return 'Reranking unavailable'
    default:                return 'Error'
  }
}