// src/components/ContextInspector.tsx
import { useState } from 'react'
import type { RetrievedChunk } from '../api/types'

interface Props {
  chunks: RetrievedChunk[]
  phase:  string
}

export function ContextInspector({ chunks, phase }: Props) {
  const [open,        setOpen]        = useState(true)
  const [expandedId,  setExpandedId]  = useState<string | null>(null)

  if (chunks.length === 0 && phase === 'idle') return null

  return (
    <div className="inspector">

      {/* header — click to collapse */}
      <div
        className="inspector-header"
        onClick={() => setOpen(prev => !prev)}
        role="button"
        aria-expanded={open}
      >
        <div className="inspector-title-row">
          <span className="inspector-title">context</span>
          {chunks.length > 0 && (
            <span className="inspector-count">{chunks.length} chunks</span>
          )}
          {phase === 'retrieving' || phase === 'reranking' ? (
            <span className="inspector-spinner" />
          ) : null}
        </div>
        <span className="inspector-chevron">{open ? '▾' : '▸'}</span>
      </div>

      {/* chunk list */}
      {open && (
        <div className="inspector-body">

          {chunks.length === 0 && (
            <p className="inspector-empty">
              {phase === 'retrieving' ? 'searching...' :
               phase === 'reranking' ? 'reranking...' :
               'no chunks retrieved'}
            </p>
          )}

          {chunks.map((chunk, i) => {
            const isExpanded = expandedId === chunk.id

            return (
              <div key={chunk.id} className="chunk-card">

                {/* chunk header */}
                <div
                  className="chunk-header"
                  onClick={() => setExpandedId(isExpanded ? null : chunk.id)}
                  role="button"
                >
                  <div className="chunk-meta">
                    <span className="chunk-index">#{i + 1}</span>
                    <span className="chunk-source">{chunk.source}</span>
                    {chunk.page && (
                      <span className="chunk-page">p.{chunk.page}</span>
                    )}
                  </div>
                  <span className="chunk-chevron">
                    {isExpanded ? '▾' : '▸'}
                  </span>
                </div>

                {/* score bars — always visible */}
                <div className="chunk-scores">
                  <ScoreBar
                    label="relevance"
                    value={chunk.score}
                    className="relevance"
                  />
                  <ScoreBar
                    label="bm25"
                    value={chunk.bm25Score}
                    className="bm25"
                  />
                  <ScoreBar
                    label="vector"
                    value={chunk.vectorScore}
                    className="vector"
                  />
                </div>

                {/* chunk text — expandable */}
                {isExpanded && (
                  <div className="chunk-text">
                    {chunk.text}
                  </div>
                )}

              </div>
            )
          })}

        </div>
      )}

    </div>
  )
}

// ── score bar sub-component ───────────────────────────
interface ScoreBarProps {
  label:     string
  value:     number
  className: string
}

function ScoreBar({ label, value, className }: ScoreBarProps) {
  return (
    <div className="score-row">
      <span className="score-label">{label}</span>
      <div className="score-track">
        <div
          className={`score-fill ${className}`}
          style={{ width: `${value * 100}%` }}
        />
      </div>
      <span className="score-value">{value.toFixed(2)}</span>
    </div>
  )
}