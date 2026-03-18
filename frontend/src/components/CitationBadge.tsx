// src/components/CitationBadge.tsx
import { useState, useRef, useEffect } from 'react'
import type { RetrievedChunk } from '../api/types'

interface Props {
  index:      number                        // the [n] number
  chunkId:    string                        // maps to chunk in the list
  chunks:     RetrievedChunk[]              // full chunk list for lookup
  shadowRoot: ShadowRoot | null            // needed for popover positioning
}

export function CitationBadge({ index, chunkId, chunks, shadowRoot }: Props) {
  const [open, setOpen]   = useState(false)
  const badgeRef          = useRef<HTMLSpanElement>(null)
  const popoverRef        = useRef<HTMLDivElement>(null)

  const chunk = chunks.find(c => c.id === chunkId)

  // close popover when clicking outside — scoped to shadow root
  useEffect(() => {
    if (!open) return

    const handleClick = (e: Event) => {
      const target = e.target as Node
      if (
        badgeRef.current  && !badgeRef.current.contains(target) &&
        popoverRef.current && !popoverRef.current.contains(target)
      ) {
        setOpen(false)
      }
    }

    // listen on shadow root, not document — stays inside boundary
    const root = shadowRoot ?? document
    root.addEventListener('click', handleClick)
    return () => root.removeEventListener('click', handleClick)
  }, [open, shadowRoot])

  if (!chunk) return <sup className="citation-badge missing">[{index}]</sup>

  return (
    <span className="citation-wrapper" ref={badgeRef}>
      <sup
        className={`citation-badge ${open ? 'active' : ''}`}
        onClick={() => setOpen(prev => !prev)}
        role="button"
        aria-label={`Citation ${index}: ${chunk.source}`}
      >
        [{index}]
      </sup>

      {open && (
        <div className="citation-popover" ref={popoverRef}>

          {/* header */}
          <div className="popover-header">
            <span className="popover-source">{chunk.source}</span>
            {chunk.page && (
              <span className="popover-page">p.{chunk.page}</span>
            )}
            <button
              className="popover-close"
              onClick={() => setOpen(false)}
              aria-label="Close"
            >
              ✕
            </button>
          </div>

          {/* score bars */}
          <div className="popover-scores">
            <div className="score-row">
              <span className="score-label">relevance</span>
              <div className="score-bar-track">
                <div
                  className="score-bar-fill"
                  style={{ width: `${chunk.score * 100}%` }}
                />
              </div>
              <span className="score-value">{chunk.score.toFixed(2)}</span>
            </div>
            <div className="score-row">
              <span className="score-label">bm25</span>
              <div className="score-bar-track">
                <div
                  className="score-bar-fill bm25"
                  style={{ width: `${chunk.bm25Score * 100}%` }}
                />
              </div>
              <span className="score-value">{chunk.bm25Score.toFixed(2)}</span>
            </div>
            <div className="score-row">
              <span className="score-label">vector</span>
              <div className="score-bar-track">
                <div
                  className="score-bar-fill vector"
                  style={{ width: `${chunk.vectorScore * 100}%` }}
                />
              </div>
              <span className="score-value">{chunk.vectorScore.toFixed(2)}</span>
            </div>
          </div>

          {/* chunk text preview */}
          <div className="popover-text">
            {chunk.text}
          </div>

        </div>
      )}
    </span>
  )
}