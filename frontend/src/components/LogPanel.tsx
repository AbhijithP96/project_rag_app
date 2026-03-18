// src/components/LogPanel.tsx
import { useRef, useEffect } from 'react'
import { useLogger } from '../hooks/uselogger'
//import type { LogEntry, LogLevel } from '../utils/logger'

interface Props {
  open:     boolean
  onToggle: () => void
}

export function LogPanel({ open, onToggle }: Props) {
  const { entries, clear } = useLogger('INFO')
  const bottomRef          = useRef<HTMLDivElement>(null)

  // auto-scroll to latest entry
  useEffect(() => {
    if (open && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [entries, open])

  return (
    <div className={`log-drawer ${open ? 'open' : ''}`}>

      {/* drawer handle — always visible, click to toggle */}
      <div className="log-handle" onClick={onToggle} role="button">
        <div className="log-handle-bar" />
        <div className="log-handle-meta">
          <span className="log-handle-title">pipeline log</span>
          <span className="log-entry-count">{entries.length} entries</span>
        </div>
        <div className="log-handle-actions">
          {entries.length > 0 && (
            <button
              className="log-clear-btn"
              onClick={e => { e.stopPropagation(); clear() }}
              aria-label="Clear logs"
            >
              clear
            </button>
          )}
          <span className="log-chevron">{open ? '▾' : '▴'}</span>
        </div>
      </div>

      {/* log entries — only rendered when open */}
      {open && (
        <div className="log-body">
          {entries.length === 0 && (
            <p className="log-empty">no log entries yet</p>
          )}

          {entries.map(entry => (
            <div
              key={entry.id}
              className={`log-entry level-${entry.level.toLowerCase()}`}
            >
              <span className="log-time">
                {formatLogTime(entry.timestamp)}
              </span>
              <span className={`log-level level-${entry.level.toLowerCase()}`}>
                {entry.level}
              </span>
              <span className="log-category">{entry.category}</span>
              <span className="log-msg">{entry.message}</span>
            </div>
          ))}

          <div ref={bottomRef} />
        </div>
      )}

    </div>
  )
}

function formatLogTime(date: Date): string {
  return date.toLocaleTimeString([], {
    hour:        '2-digit',
    minute:      '2-digit',
    second:      '2-digit',
    hour12:      false,
  })
}