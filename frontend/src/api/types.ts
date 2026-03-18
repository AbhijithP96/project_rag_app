// ── Chunks returned by retrieval ──────────────────────
export interface RetrievedChunk {
  id: string
  text: string
  source: string       // filename
  page?: number
  score: number        // final rerank score
  bm25Score: number
  vectorScore: number
  startChar: number
  endChar: number
}

// ── SSE event types emitted by /query ─────────────────
export type SSEEventType =
  | 'retrieval_start'
  | 'retrieval_complete'
  | 'rerank_complete'
  | 'generation_start'
  | 'token'
  | 'citation'
  | 'token_usage'
  | 'done'
  | 'error'

// ── Shape of each SSE event payload ───────────────────
export interface SSEEvent {
  type: SSEEventType
  token?:        string
  chunks?:       RetrievedChunk[]
  citationIndex?: number
  citationId?:   string
  usage?: {
    promptTokens:     number
    contextTokens:    number
    completionTokens: number
    totalTokens:      number
    budgetLimit:      number
  }
  errorType?: 'retrieval_error' | 'model_error' | 'rerank_error'
  message?:   string
}

// ── /index endpoint types ─────────────────────────────
export interface IndexRequest {
  directory: string
}

export interface IndexProgressEvent {
  status:         'indexing' | 'complete' | 'error'
  filesProcessed: string[]
  chunksIndexed:  number
  currentFile?:   string
  message?:       string
}

// ── Conversation types ─────────────────────────────────
export type MessageRole = 'user' | 'assistant'

export interface Message {
  id:         string
  role:       MessageRole
  content:    string        // final joined text for assistant, raw input for user
  tokens:     string[]      // raw token array — used for typewriter in active msg
  chunks:     RetrievedChunk[]
  citations:  Record<number, string>  // citationIndex → chunkId
  error:      { errorType: SSEEvent['errorType']; message: string } | null
  usage:      SSEEvent['usage'] | null
  timestamp:  number
  isStreaming: boolean
}

export interface ConversationState {
  messages:    Message[]
  isStreaming: boolean
}