# logger.py
import sys
import time
import uuid
import psutil
import traceback
from typing import Optional
from contextvars import ContextVar
from datetime import timezone

from loguru import logger
from config import LOG_FILE, LOG_LEVEL

# context var : carries request_id across async calls
request_id_var: ContextVar[str] = ContextVar("request_id", default="system")

# latency tracking store
_latency_store: dict[str, list[float]] = {
    "retrieval": [],
    "reranking": [],
    "generation": [],
    "index": [],
}


# JSON serialiser for loguru
def _json_sink(message) -> str:
    record = message.record
    log = {
        "timestamp": record["time"].astimezone(timezone.utc).isoformat(),
        "level": record["level"].name,
        "request_id": request_id_var.get("system"),
        "logger": record["name"],
        "message": record["message"],
        "memory_mb": _get_memory_mb(),
    }

    # attach extra fields from record["extra"]
    for key in (
        "stage",
        "duration_ms",
        "file_count",
        "chunk_count",
        "error",
        "details",
    ):
        if key in record["extra"]:
            log[key] = record["extra"][key]

    # attach exception if present
    if record["exception"]:
        log["exception"] = "".join(
            traceback.format_exception(
                record["exception"].type,
                record["exception"].value,
                record["exception"].traceback,
            )
        )

    import json

    return json.dumps(log) + "\n"


# setup loguru
def setup_logging() -> None:
    # remove default loguru handler
    logger.remove()

    # console — human readable during dev
    logger.add(
        sys.stdout,
        level=LOG_LEVEL.upper(),
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{extra[request_id]}</cyan> | "
            "{message}"
        ),
        colorize=True,
        filter=lambda r: _inject_defaults(r),
    )

    # file — JSON lines for production
    logger.add(
        str(LOG_FILE),
        level=LOG_LEVEL.upper(),
        format="{message}",
        serialize=False,
        rotation="100 MB",
        retention="7 days",
        compression="zip",
        filter=lambda r: _inject_defaults(r),
    )


def _inject_defaults(record) -> bool:
    record["extra"].setdefault("request_id", request_id_var.get("system"))
    return True


# initialise on import
setup_logging()


# request context
def new_request_id() -> str:
    rid = str(uuid.uuid4())[:8]
    request_id_var.set(rid)
    return rid


def set_request_id(rid: str) -> None:
    request_id_var.set(rid)


# timer context manager
class Timer:
    """Measures duration and logs it with stage + extra context."""

    def __init__(self, stage: str, extra: Optional[dict] = None):
        self.stage = stage
        self.extra = extra or {}
        self.start = 0.0
        self.elapsed = 0.0

    def __enter__(self) -> "Timer":
        self.start = time.perf_counter()
        return self

    def __exit__(self, *_) -> None:
        self.elapsed = (time.perf_counter() - self.start) * 1000
        _record_latency(self.stage, self.elapsed)

        # merge stage into extra dict — don't pass as separate kwarg
        extra = {
            "stage": self.stage,
            "duration_ms": round(self.elapsed, 2),
            **self.extra,
        }
        logger.bind(**extra).info(
            f"{self.stage} completed in {round(self.elapsed, 2)}ms"
        )


# latency tracking
def _record_latency(stage: str, duration_ms: float) -> None:
    if stage in _latency_store:
        store = _latency_store[stage]
        store.append(duration_ms)
        if len(store) > 100:
            _latency_store[stage] = store[-100:]


def get_p95_latency(stage: str) -> Optional[float]:
    store = _latency_store.get(stage, [])
    if not store:
        return None
    sorted_store = sorted(store)
    idx = int(len(sorted_store) * 0.95)
    return round(sorted_store[min(idx, len(sorted_store) - 1)], 2)


def get_all_p95() -> dict[str, Optional[float]]:
    return {stage: get_p95_latency(stage) for stage in _latency_store}


# memory utility
def _get_memory_mb() -> float:
    try:
        return round(psutil.Process().memory_info().rss / 1024 / 1024, 1)
    except Exception:
        return 0.0


def log_memory(label: str = "") -> None:
    mb = _get_memory_mb()
    logger.bind(stage="memory", memory_mb=mb).info(f"memory: {mb}MB {label}".strip())
