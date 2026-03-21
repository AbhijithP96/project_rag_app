# worker.py
import asyncio
import time
from enum import Enum
from typing import AsyncGenerator, Optional
from pathlib import Path

import psutil

from config import MAX_CONCURRENT_REQUESTS, BASE_DIR
from logger import logger, new_request_id, set_request_id, get_all_p95
from rag_pipeline import run_pipeline
import indexer


# job state
class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    done = "done"
    cancelled = "cancelled"
    failed = "failed"


class Job:
    def __init__(self, request_id: str, query: str):
        self.request_id = request_id
        self.query = query
        self.status = JobStatus.queued
        self.created_at = time.time()
        self.started_at: Optional[float] = None
        self.ended_at: Optional[float] = None
        self.cancelled = False

    def start(self):
        self.status = JobStatus.running
        self.started_at = time.time()

    def finish(self):
        self.status = JobStatus.done
        self.ended_at = time.time()

    def fail(self):
        self.status = JobStatus.failed
        self.ended_at = time.time()

    def cancel(self):
        self.cancelled = True
        self.status = JobStatus.cancelled
        self.ended_at = time.time()

    @property
    def duration_ms(self) -> Optional[float]:
        if self.started_at and self.ended_at:
            return round((self.ended_at - self.started_at) * 1000, 2)
        return None


# worker singleton
class Worker:
    def __init__(self):
        # semaphore for query jobs (OOM protection)
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        # separate semaphore caps concurrent index builds across different dirs
        self._index_semaphore = asyncio.Semaphore(2)
        self._jobs: dict[str, Job] = {}
        self._ready: bool = False
        self._shutting_down: bool = False

    # lifecycle
    def startup(self):
        """Warm up models and load all persisted indexes at startup."""
        logger.info(
            "worker starting up...",
            stage="system",
        )

        loaded = indexer.load_indexes()
        logger.info(
            f"indexes loaded: {loaded}",
            stage="system",
        )

        # warm up BGE reranker
        try:
            from retriever import _get_reranker

            _get_reranker()
            logger.info("reranker warmed up", stage="system")
        except Exception as e:
            logger.warning(
                f"reranker warmup failed: {e}",
                stage="system",
            )

        # warm up LLM
        try:
            from rag_pipeline import _get_llm

            _get_llm()
            logger.info("LLM warmed up", stage="system")
        except Exception as e:
            logger.warning(
                f"LLM warmup failed: {e}",
                stage="system",
            )

        self._ready = True
        logger.info("worker ready", stage="system")

    def shutdown(self):
        """Graceful shutdown — stop accepting new jobs."""
        self._shutting_down = True
        logger.info(
            f"worker shutting down — " f"{self._active_count()} jobs still running",
            stage="system",
        )

    def is_ready(self) -> bool:
        return self._ready and not self._shutting_down

    def _active_count(self) -> int:
        return sum(1 for j in self._jobs.values() if j.status == JobStatus.running)

    # OOM check
    def _check_oom(self) -> bool:
        """Return True if memory is dangerously high."""
        try:
            vm = psutil.virtual_memory()
            if vm.percent > 90:
                logger.warning(
                    f"OOM risk: memory at {vm.percent:.1f}%",
                    stage="system",
                    memory_mb=round(vm.used / 1024 / 1024, 1),
                )
                return True
        except Exception:
            pass
        return False

    # health state
    def health(self) -> dict:
        try:
            vm = psutil.virtual_memory()
            cpu = psutil.cpu_percent(interval=0.1)
        except Exception:
            vm = None
            cpu = 0.0

        return {
            "status": "ready" if self.is_ready() else "unavailable",
            "index_ready": indexer.is_ready(),
            "active_jobs": self._active_count(),
            "total_jobs": len(self._jobs),
            "memory_percent": round(vm.percent, 1) if vm else 0.0,
            "memory_mb": round(vm.used / 1024 / 1024, 1) if vm else 0.0,
            "cpu_percent": cpu,
            "p95_latency_ms": get_all_p95(),
            "shutting_down": self._shutting_down,
        }

    # cancel job
    def cancel_job(self, request_id: str) -> bool:
        job = self._jobs.get(request_id)
        if job and job.status == JobStatus.running:
            job.cancel()
            logger.info(
                f"job cancelled: {request_id}",
                stage="system",
            )
            return True
        return False

    # main query handler
    async def handle_query(
        self,
        query:      str,
        session_id: str | None = None,
        index_key:  str | None = None,
        top_k:      int = 10,
        top_n:      int = 3,
        request_id: Optional[str] = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Run RAG pipeline with:
        - Concurrency semaphore (OOM protection)
        - Job tracking
        - Request ID context
        - Graceful cancellation
        """

        if self._shutting_down:
            yield {
                "type": "error",
                "error_type": "oom_error",
                "message": "Server is shutting down",
            }
            return

        if self._check_oom():
            yield {
                "type": "error",
                "error_type": "oom_error",
                "message": "Server memory too high — try again later",
            }
            return

        rid = request_id or new_request_id()
        set_request_id(rid)
        job = Job(rid, query)
        self._jobs[rid] = job

        logger.info(
            f"job queued: {rid} — '{query[:50]}'",
            stage="stream",
        )

        async with self._semaphore:
            job.start()
            logger.info(
                f"job started: {rid} " f"(active: {self._active_count()})",
                stage="stream",
            )

            try:
                async for event in run_pipeline(
                    query=query,
                    session_id=session_id,
                    index_key=index_key,
                    top_k=top_k,
                    top_n=top_n,
                ):
                    if job.cancelled:
                        logger.info(
                            f"job {rid} cancelled mid-stream",
                            stage="stream",
                        )
                        return

                    yield event

                job.finish()
                logger.info(
                    f"job done: {rid} " f"({job.duration_ms}ms)",
                    stage="stream",
                )

            except Exception as e:
                job.fail()
                logger.error(
                    f"job failed: {rid} — {e}",
                    stage="stream",
                    error=str(e),
                )
                yield {
                    "type": "error",
                    "error_type": "model_error",
                    "message": f"Pipeline failed: {str(e)}",
                }

    # index handler
    async def handle_index(
        self,
        directory: str,
        request_id: Optional[str] = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Run indexing for a directory with:
        - Per-directory key (content-addressed)
        - Per-key async lock — second tab for same dir waits then gets cached result
        - Separate index semaphore — different dirs can build concurrently (up to 2)
        - No overwriting: each directory has its own subdirectory under faiss_index/
        """
        path = Path(directory)

        if not path.is_absolute():
            path = BASE_DIR / path

        if not path.exists():
            yield {
                "status": "error",
                "message": (
                    f"Directory not found: {path}\n"
                    f"Current working directory: {Path.cwd()}\n"
                    f"Available directories: "
                    f"{[d.name for d in Path.cwd().iterdir() if d.is_dir()][:5]}"
                ),
            }
            return

        directory = str(path)

        if self._shutting_down:
            yield {"status": "error", "message": "Server is shutting down"}
            return

        if self._check_oom():
            yield {
                "status": "error",
                "message": "Server memory too high — try again later",
            }
            return

        rid = request_id or new_request_id()
        set_request_id(rid)

        index_key = indexer.get_index_key(directory)

        # acquire the per-key lock — serialises concurrent requests for the same dir
        lock = await indexer.get_or_create_lock(index_key)

        async with lock:
            # if a previous waiter already built it, return immediately
            if indexer.is_ready(index_key):
                store = indexer.get_index(index_key)
                logger.info(
                    f"index cache hit: {index_key} ({directory})",
                    stage="index",
                )
                yield {
                    "status": "complete",
                    "files_processed": [m.source for m in store.chunk_metas],
                    "chunks_indexed": len(store.chunk_metas),
                    "index_id": index_key,
                    "message": "Index already cached",
                }
                return

            logger.info(
                f"index job: {rid} — '{directory}' (key: {index_key})",
                stage="index",
            )

            try:
                from document_loader import scan_directory

                docs, skipped, failed = scan_directory(directory)

                logger.info(
                    f"scan complete: {len(docs)} new, "
                    f"{len(skipped)} skipped, "
                    f"{len(failed)} failed",
                    stage="index",
                )

                if not docs and not skipped:
                    yield {
                        "status": "error",
                        "message": f"No supported files found in: {directory}",
                    }
                    return

                if skipped:
                    yield {
                        "status": "indexing",
                        "current_file": f"skipping {len(skipped)} unchanged files...",
                        "files_processed": [],
                        "chunks_indexed": 0,
                        "message": f"{len(skipped)} files unchanged (cached)",
                    }

                if not docs:
                    # all files unchanged — load from disk
                    indexer.load_index(index_key)
                    store = indexer.get_index(index_key)
                    yield {
                        "status": "complete",
                        "files_processed": skipped,
                        "chunks_indexed": len(store.chunk_metas),
                        "index_id": index_key,
                        "message": "All files unchanged — using cached index",
                    }
                    return

                # build — cap concurrent builds across different directories
                async with self._index_semaphore:
                    async for progress in indexer.build_index(docs, index_key):
                        yield progress

            except FileNotFoundError as e:
                logger.error(
                    f"index failed: {e}",
                    stage="index",
                    error=str(e),
                )
                yield {"status": "error", "message": str(e)}

            except Exception as e:
                logger.error(
                    f"index failed: {e}",
                    stage="index",
                    error=str(e),
                )
                yield {"status": "error", "message": f"Indexing failed: {str(e)}"}


# global worker instance
worker = Worker()
