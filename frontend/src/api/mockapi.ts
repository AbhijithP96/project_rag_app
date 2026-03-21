// src/api/mockApi.ts
import type {
  SSEEvent,
  IndexProgressEvent,
  IndexRequest,
} from './types'

const API_BASE = 'http://localhost:5000'

// ── /index endpoint ───────────────────────────────────
export async function* mockIndexDirectory(
  req: IndexRequest,
): AsyncGenerator<IndexProgressEvent> {
  const response = await fetch(`${API_BASE}/index`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ directory: req.directory }),
  })

  if (!response.ok) {
    yield {
      status:          'error',
      filesProcessed:  [],
      chunksIndexed:   0,
      message:         `Server error: ${response.status}`,
    }
    return
  }

  const reader  = response.body!.getReader()
  const decoder = new TextDecoder()
  let   buffer  = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      try {
        const raw = JSON.parse(line.slice(6))
        yield {
          status:          raw.status,
          filesProcessed:  raw.files_processed  ?? raw.filesProcessed  ?? [],
          chunksIndexed:   raw.chunks_indexed   ?? raw.chunksIndexed   ?? 0,
          currentFile:     raw.current_file     ?? raw.currentFile,
          message:         raw.message,
          indexId:         raw.index_id         ?? raw.indexId,
        } as IndexProgressEvent
      } catch {
        // skip malformed lines
      }
    }
  }
}

// ── /query endpoint ───────────────────────────────────
export async function* mockQuery(
  query:       string,
  budgetLimit: number = 8192,
  indexId?:    string,
  sessionId?:  string,
): AsyncGenerator<SSEEvent> {
  const response = await fetch(`${API_BASE}/query`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({
      query,
      top_k:      10,
      rerank_top: 3,
      index_id:   indexId  ?? null,
      session_id: sessionId ?? null,
    }),
  })

  if (!response.ok) {
    yield {
      type:      'error',
      errorType: 'model_error',
      message:   `Server error: ${response.status}`,
    }
    return
  }

  const reader  = response.body!.getReader()
  const decoder = new TextDecoder()
  let   buffer  = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      try {
        const raw = JSON.parse(line.slice(6))

        // normalise snake_case from backend to camelCase for frontend
        const event: SSEEvent = {
          type:           raw.type,
          token:          raw.token,
          chunks:         raw.chunks?.map((c: any) => ({
            id:           c.id,
            text:         c.text,
            source:       c.source,
            page:         c.page,
            score:        c.score        ?? 0,
            bm25Score:    c.bm25_score   ?? 0,
            vectorScore:  c.vector_score ?? 0,
            startChar:    c.start_char   ?? 0,
            endChar:      c.end_char     ?? 0,
          })),
          citationIndex:  raw.citation_index,
          citationId:     raw.citation_id,
          usage:          raw.usage ? {
            promptTokens:     raw.usage.prompt_tokens,
            contextTokens:    raw.usage.context_tokens,
            completionTokens: raw.usage.completion_tokens,
            totalTokens:      raw.usage.total_tokens,
            budgetLimit:      raw.usage.budget_limit ?? budgetLimit,
          } : undefined,
          errorType:      raw.error_type,
          message:        raw.message,
        }

        yield event
      } catch {
        // skip malformed lines
      }
    }
  }
}