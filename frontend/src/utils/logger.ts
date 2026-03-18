// src/utils/logger.ts

export type LogLevel    = 'DEBUG' | 'INFO' | 'WARN' | 'ERROR'
export type LogCategory =
  | 'stream'
  | 'retrieval'
  | 'reranking'
  | 'generation'
  | 'tokens'
  | 'usage'
  | 'index'
  | 'system'
  | 'error'

export interface LogEntry {
  id:        string
  level:     LogLevel
  category:  LogCategory
  message:   string
  timestamp: Date
  data?:     Record<string, unknown>
}

type LogListener = (entries: LogEntry[]) => void

// ── Singleton store ────────────────────────────────────
class LogStore {
  private entries:   LogEntry[]   = []
  private listeners: LogListener[] = []
  private counter:   number       = 0

  log(
    level:    LogLevel,
    category: LogCategory,
    message:  string,
    data?:    Record<string, unknown>
  ) {
    const entry: LogEntry = {
      id:        `log-${++this.counter}`,
      level,
      category,
      message,
      timestamp: new Date(),
      data,
    }
    this.entries = [...this.entries, entry]
    this.listeners.forEach(fn => fn(this.entries))
  }

  // convenience methods
  info  = (cat: LogCategory, msg: string, data?: Record<string, unknown>) =>
    this.log('INFO',  cat, msg, data)
  warn  = (cat: LogCategory, msg: string, data?: Record<string, unknown>) =>
    this.log('WARN',  cat, msg, data)
  error = (cat: LogCategory, msg: string, data?: Record<string, unknown>) =>
    this.log('ERROR', cat, msg, data)
  debug = (cat: LogCategory, msg: string, data?: Record<string, unknown>) =>
    this.log('DEBUG', cat, msg, data)

  subscribe(fn: LogListener): () => void {
    this.listeners.push(fn)
    // immediately call with current entries so new subscribers
    // get existing logs on mount
    fn(this.entries)
    return () => {
      this.listeners = this.listeners.filter(l => l !== fn)
    }
  }

  clear() {
    this.entries = []
    this.listeners.forEach(fn => fn(this.entries))
  }

  getEntries() { return this.entries }
}

// export single instance — import this everywhere
export const logger = new LogStore()