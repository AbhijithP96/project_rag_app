# models.py
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# /index endpoint
class IndexRequest(BaseModel):
    directory: str = Field(..., description="Absolute or relative path to directory")


class IndexStatus(str, Enum):
    indexing = "indexing"
    complete = "complete"
    error = "error"


class IndexProgressEvent(BaseModel):
    status: IndexStatus
    files_processed: list[str] = Field(default_factory=list)
    chunks_indexed: int = 0
    current_file: Optional[str] = None
    message: Optional[str] = None


# /query endpoint
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2048)
    top_k: int = Field(default=10, ge=1, le=20)
    rerank_top: int = Field(default=3, ge=1, le=10)


# retrieved chunk
class RetrievedChunk(BaseModel):
    id: str
    text: str
    source: str
    page: Optional[int] = None
    score: float = 0.0  # final rerank score
    bm25_score: float = 0.0
    vector_score: float = 0.0
    start_char: int = 0
    end_char: int = 0


# SSE event types
class SSEEventType(str, Enum):
    retrieval_start = "retrieval_start"
    retrieval_complete = "retrieval_complete"
    rerank_complete = "rerank_complete"
    generation_start = "generation_start"
    token = "token"
    citation = "citation"
    token_usage = "token_usage"
    done = "done"
    error = "error"


class ErrorType(str, Enum):
    retrieval_error = "retrieval_error"
    model_error = "model_error"
    rerank_error = "rerank_error"
    pii_error = "pii_error"
    oom_error = "oom_error"


class TokenUsage(BaseModel):
    prompt_tokens: int
    context_tokens: int
    completion_tokens: int
    total_tokens: int
    budget_limit: int


class SSEEvent(BaseModel):
    type: SSEEventType
    token: Optional[str] = None
    chunks: Optional[list[RetrievedChunk]] = None
    citation_index: Optional[int] = None
    citation_id: Optional[str] = None
    usage: Optional[TokenUsage] = None
    error_type: Optional[ErrorType] = None
    message: Optional[str] = None

    def to_sse(self) -> str:
        """Format as SSE data line — consumed by frontend EventSource."""
        return f"data: {self.model_dump_json(exclude_none=True)}\n\n"


# health check
class HealthResponse(BaseModel):
    status: str
    ollama: bool
    index_ready: bool
    memory_mb: float
    p95_latency: dict[str, Optional[float]]


# stats
class IndexStats(BaseModel):
    total_files: int
    total_chunks: int
    indexed_at: Optional[str] = None
    file_types: dict[str, int] = Field(default_factory=dict)
