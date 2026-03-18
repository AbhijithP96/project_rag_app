// src/components/TokenBudget.tsx
import { useEffect, useRef } from 'react'
import type { SSEEvent } from '../api/types'

interface Props {
  usage:       SSEEvent['usage'] | null
  isStreaming: boolean
}

export function TokenBudget({ usage, isStreaming }: Props) {
  const barRef = useRef<HTMLDivElement>(null)

  const total   = usage?.totalTokens   ?? 0
  const limit   = usage?.budgetLimit   ?? 8192
  const percent = Math.min(100, Math.round((total / limit) * 100))

  const color =
    percent >= 90 ? 'var(--error)'   :
    percent >= 70 ? 'var(--warning)' :
                    'var(--accent)'

  // animate the bar width via CSS custom property
  useEffect(() => {
    if (barRef.current) {
      barRef.current.style.setProperty('--bar-width', `${percent}%`)
      barRef.current.style.setProperty('--bar-color', color)
    }
  }, [percent, color])

  // don't render if no usage data yet and not streaming
  if (!usage && !isStreaming) return null

  return (
    <div className="token-budget">

      {/* label row */}
      <div className="budget-header">
        <span className="budget-title">token budget</span>
        <span
          className="budget-percent"
          style={{ color }}
        >
          {percent}%
        </span>
      </div>

      {/* animated progress bar */}
      <div className="budget-track">
        <div
          ref={barRef}
          className={`budget-bar ${isStreaming ? 'streaming' : ''}`}
          style={{
            '--bar-width': `${percent}%`,
            '--bar-color': color,
          } as React.CSSProperties}
        />
      </div>

      {/* breakdown row */}
      {usage && (
        <div className="budget-breakdown">
          <span className="budget-item">
            <span className="budget-item-label">prompt</span>
            <span className="budget-item-value">{usage.promptTokens}</span>
          </span>
          <span className="budget-divider">·</span>
          <span className="budget-item">
            <span className="budget-item-label">context</span>
            <span className="budget-item-value">{usage.contextTokens}</span>
          </span>
          <span className="budget-divider">·</span>
          <span className="budget-item">
            <span className="budget-item-label">completion</span>
            <span className="budget-item-value">{usage.completionTokens}</span>
          </span>
          <span className="budget-divider">·</span>
          <span className="budget-item">
            <span className="budget-item-label">total</span>
            <span
              className="budget-item-value total"
              style={{ color }}
            >
              {usage.totalTokens} / {usage.budgetLimit}
            </span>
          </span>
        </div>
      )}

      {/* over budget warning */}
      {percent >= 100 && (
        <div className="budget-warning">
          ⚠ token budget exceeded — responses may be truncated
        </div>
      )}

    </div>
  )
}