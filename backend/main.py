# main.py
import asyncio
import json
import signal
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from pathlib import Path

from config import TOKEN_BUDGET
from logger import logger, new_request_id, get_all_p95
from models import (
    IndexRequest,
    QueryRequest,
    HealthResponse,
    IndexStats,
)
from worker import worker
import indexer


# lifespan :startup + shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()

    def _handle_sigterm(*_):
        logger.info("SIGTERM received — shutting down", stage="system")
        worker.shutdown()
        # actually stop the process
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _handle_sigterm)

    loop.run_in_executor(None, worker.startup)

    yield

    worker.shutdown()
    logger.info("server stopped", stage="system")


# app
app = FastAPI(
    title="RAG Backend",
    description="Self-RAG pipeline with hybrid search",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# SSE helper
async def _sse_generator(async_gen):
    """Convert async generator of dicts to SSE data lines."""
    try:
        async for event in async_gen:
            yield {
                "data": json.dumps(event),
            }
    except asyncio.CancelledError:
        logger.info("SSE client disconnected", stage="stream")


# /health
@app.get("/health")
async def health() -> dict:
    return worker.health()


# /stats
@app.get("/stats")
async def stats() -> dict:
    """Index statistics — used by frontend status bar."""
    if not indexer.is_ready():
        return {
            "total_files": 0,
            "total_chunks": 0,
            "indexed_at": None,
            "file_types": {},
        }

    from config import STATS_PATH

    try:
        import json as _json

        s = _json.loads(STATS_PATH.read_text())
        return s
    except Exception:
        return {
            "total_files": 0,
            "total_chunks": len(indexer._chunk_metas),
            "indexed_at": None,
            "file_types": {},
        }


# /index
@app.post("/index")
async def index_documents(req: IndexRequest, request: Request):
    """
    Index documents from a local directory.
    Streams SSE progress events.

    SSE event types emitted:
        indexing  — progress update per file
        complete  — indexing finished
        error     — something went wrong
    """
    if not worker.is_ready():
        raise HTTPException(
            status_code=503,
            detail="Server not ready — try again in a moment",
        )

    rid = new_request_id()
    logger.info(
        f"POST /index — dir: {req.directory}",
        stage="index",
    )

    async def _gen():
        async for event in worker.handle_index(
            directory=req.directory,
            request_id=rid,
        ):
            yield {"data": json.dumps(event)}

    return EventSourceResponse(_gen())


# /query
@app.post("/query")
async def query_documents(req: QueryRequest, request: Request):
    """
    Run the RAG pipeline and stream the response.

    SSE event types emitted:
        retrieval_start    — hybrid search started
        retrieval_complete — chunks retrieved (with chunk list)
        rerank_complete    — BGE reranker finished (with chunk list)
        generation_start   — LLM streaming started
        token              — one token from LLM
        citation           — citation reference detected inline
        token_usage        — final token counts
        done               — stream complete
        error              — pipeline error
    """
    if not worker.is_ready():
        raise HTTPException(
            status_code=503,
            detail="Server not ready — try again in a moment",
        )

    rid = new_request_id()
    logger.info(f"POST /query — '{req.query[:60]}'", stage="stream")

    async def _gen():
        # track reranked chunks so citations can reference them
        reranked_chunks: list[dict] = []

        async for event in worker.handle_query(
            query=req.query,
            history="",
            top_k=req.top_k,
            top_n=req.rerank_top,
            request_id=rid,
        ):
            event_type = event.get("type")

            # capture reranked chunks for citation enrichment
            if event_type == "rerank_complete":
                reranked_chunks = event.get("chunks", [])

            # enrich citation events with verified chunk data
            if event_type == "citation":
                citation_index = event.get("citation_index", 0)
                chunk_idx = citation_index - 1
                if 0 <= chunk_idx < len(reranked_chunks):
                    # override citation_id with confirmed chunk id
                    event["citation_id"] = reranked_chunks[chunk_idx]["id"]
                else:
                    # citation index out of range — skip it
                    continue

            yield {"data": json.dumps(event)}

    return EventSourceResponse(_gen())


# directory endpoint
@app.get("/directories")
async def list_directories(path: str = "."):
    """List subdirectories at a given path for the frontend picker."""
    try:
        base = Path(path).resolve()
        if not base.exists():
            base = Path.cwd()

        dirs = sorted(
            [
                {
                    "name": d.name,
                    "path": str(d),
                }
                for d in base.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            ],
            key=lambda x: x["name"],
        )

        return {
            "current": str(base),
            "parent": str(base.parent),
            "dirs": dirs,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# /cancel/{request_id}
@app.post("/cancel/{request_id}")
async def cancel_job(request_id: str):
    """Cancel an active streaming job."""
    cancelled = worker.cancel_job(request_id)
    return {
        "cancelled": cancelled,
        "request_id": request_id,
    }


# run
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="warning",  # loguru handles logging
        access_log=False,
    )
