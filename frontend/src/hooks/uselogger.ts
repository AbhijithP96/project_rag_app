// src/hooks/useLogger.ts
import { useState, useEffect, useCallback } from 'react'
import { logger } from '../utils/logger'
import type { LogEntry, LogLevel } from '../utils/logger'

export function useLogger(minLevel: LogLevel = 'INFO') {
  const [entries, setEntries] = useState<LogEntry[]>([])

  useEffect(() => {
    // subscribe returns an unsubscribe function — perfect for useEffect cleanup
    const unsubscribe = logger.subscribe(all => {
      setEntries(filterByLevel(all, minLevel))
    })
    return unsubscribe
  }, [minLevel])

  const clear = useCallback(() => {
    logger.clear()
  }, [])

  return { entries, clear }
}

// ── only show entries at or above the requested level ──
const LEVEL_ORDER: LogLevel[] = ['DEBUG', 'INFO', 'WARN', 'ERROR']

function filterByLevel(entries: LogEntry[], min: LogLevel): LogEntry[] {
  const minIndex = LEVEL_ORDER.indexOf(min)
  return entries.filter(e => LEVEL_ORDER.indexOf(e.level) >= minIndex)
}