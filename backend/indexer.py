# indexer.py
import asyncio
import hashlib
import json
import pickle
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from rank_bm25 import BM25Okapi

from config import (
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    SEPARATORS,
    EMBEDDING_MODEL,
    OLLAMA_BASE_URL,
    INDEX_DIR,
)
from document_loader import LoadedDocument
from logger import logger, Timer, log_memory


# ── per-directory index store ──────────────────────────
@dataclass
class IndexStore:
    faiss_store:  FAISS
    bm25_index:   BM25Okapi
    chunk_metas:  list   # list[ChunkMeta]
    is_ready:     bool = True


# ── global registry + per-key locks ───────────────────
_registry:    dict[str, IndexStore] = {}
_index_locks: dict[str, asyncio.Lock] = {}
_lock_mutex:  asyncio.Lock = asyncio.Lock()


# ── public index-key helpers ───────────────────────────
def get_index_key(directory: str) -> str:
    """Stable 12-char hex key for a directory path."""
    abs_path = str(Path(directory).resolve())
    return hashlib.md5(abs_path.encode()).hexdigest()[:12]


async def get_or_create_lock(key: str) -> asyncio.Lock:
    """Return (or lazily create) the asyncio Lock for a given key."""
    async with _lock_mutex:
        if key not in _index_locks:
            _index_locks[key] = asyncio.Lock()
        return _index_locks[key]


# ── readiness / lookup ─────────────────────────────────
def is_ready(index_key: str | None = None) -> bool:
    if index_key:
        store = _registry.get(index_key)
        return store is not None and store.is_ready
    return any(s.is_ready for s in _registry.values())


def get_index(index_key: str) -> IndexStore:
    store = _registry.get(index_key)
    if store is None or not store.is_ready:
        raise RuntimeError(f"Index '{index_key}' not ready — run /index first")
    return store


def get_any_index() -> IndexStore:
    """Return any ready index (fallback when no index_key is provided)."""
    for store in _registry.values():
        if store.is_ready:
            return store
    raise RuntimeError("No index ready — run /index first")


# ── path helpers ───────────────────────────────────────
def _key_dir(key: str) -> Path:
    return INDEX_DIR / key

def _faiss_path(key: str) -> Path:
    return _key_dir(key) / "faiss_store"

def _bm25_path(key: str) -> Path:
    return _key_dir(key) / "bm25_store.pkl"

def _meta_path(key: str) -> Path:
    return _key_dir(key) / "chunk_meta.json"

def _stats_path(key: str) -> Path:
    return _key_dir(key) / "index_stats.json"


# ── chunk metadata ─────────────────────────────────────
class ChunkMeta:
    def __init__(
        self,
        chunk_id: str,
        text: str,
        source: str,
        file_type: str,
        page: Optional[int],
        start_char: int,
        end_char: int,
    ):
        self.chunk_id = chunk_id
        self.text = text
        self.source = source
        self.file_type = file_type
        self.page = page
        self.start_char = start_char
        self.end_char = end_char

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "source": self.source,
            "file_type": self.file_type,
            "page": self.page,
            "start_char": self.start_char,
            "end_char": self.end_char,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ChunkMeta":
        return cls(**d)


def get_chunk_by_id(chunk_id: str, index_key: str | None = None) -> Optional[ChunkMeta]:
    stores = (
        [_registry[index_key]]
        if index_key and index_key in _registry
        else list(_registry.values())
    )
    for store in stores:
        for c in store.chunk_metas:
            if c.chunk_id == chunk_id:
                return c
    return None


# ── splitter / embeddings ─────────────────────────────
def _get_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=SEPARATORS,
        length_function=len,
        is_separator_regex=False,
    )


def _get_embeddings() -> OllamaEmbeddings:
    return OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_BASE_URL)


# ── chunk a document ──────────────────────────────────
def _chunk_document(doc: LoadedDocument) -> list[ChunkMeta]:
    splitter = _get_splitter()
    chunks = splitter.split_text(doc.content)
    metas = []
    cursor = 0

    for chunk_text in chunks:
        start = doc.content.find(chunk_text, cursor)
        if start == -1:
            start = cursor
        end = start + len(chunk_text)
        cursor = max(cursor, start)

        page = None
        if doc.file_type == "pdf" and doc.page_count > 1:
            ratio = start / max(len(doc.content), 1)
            page = int(ratio * doc.page_count) + 1

        metas.append(
            ChunkMeta(
                chunk_id=str(uuid.uuid4()),
                text=chunk_text.strip(),
                source=doc.source,
                file_type=doc.file_type,
                page=page,
                start_char=start,
                end_char=end,
            )
        )

    return metas


def _build_bm25(metas: list[ChunkMeta]) -> BM25Okapi:
    tokenized = [m.text.lower().split() for m in metas]
    return BM25Okapi(tokenized)


# ── persist one key's index to disk ───────────────────
def _save_index(
    key: str,
    faiss_store: FAISS,
    bm25_index: BM25Okapi,
    metas: list[ChunkMeta],
    stats: dict,
) -> None:
    key_dir = _key_dir(key)
    key_dir.mkdir(parents=True, exist_ok=True)

    faiss_store.save_local(str(_faiss_path(key)))

    with open(_bm25_path(key), "wb") as f:
        pickle.dump(bm25_index, f)

    _meta_path(key).write_text(json.dumps([m.to_dict() for m in metas], indent=2))
    _stats_path(key).write_text(json.dumps(stats, indent=2))

    logger.info(f"index saved: {key_dir}", stage="index")


# ── load a single key from disk ────────────────────────
def load_index(key: str) -> bool:
    if not all([
        _faiss_path(key).exists(),
        _bm25_path(key).exists(),
        _meta_path(key).exists(),
    ]):
        return False

    try:
        embeddings = _get_embeddings()
        faiss_store = FAISS.load_local(
            str(_faiss_path(key)),
            embeddings,
            allow_dangerous_deserialization=True,
        )

        with open(_bm25_path(key), "rb") as f:
            bm25_index = pickle.load(f)

        raw_metas = json.loads(_meta_path(key).read_text())
        chunk_metas = [ChunkMeta.from_dict(m) for m in raw_metas]

        _registry[key] = IndexStore(
            faiss_store=faiss_store,
            bm25_index=bm25_index,
            chunk_metas=chunk_metas,
        )

        logger.info(
            f"index loaded: {key} ({len(chunk_metas)} chunks)",
            stage="index",
            chunk_count=len(chunk_metas),
        )
        return True

    except Exception as e:
        logger.error(f"failed to load index {key}: {e}", stage="index", error=str(e))
        return False


# ── load all persisted indexes at startup ─────────────
def load_indexes() -> bool:
    """Scan INDEX_DIR for per-key subdirs and load them all."""
    loaded = 0
    if not INDEX_DIR.exists():
        return False
    for subdir in INDEX_DIR.iterdir():
        if subdir.is_dir() and len(subdir.name) == 12:
            if load_index(subdir.name):
                loaded += 1
    logger.info(f"startup: {loaded} indexes loaded", stage="index")
    return loaded > 0


# ── build index for a specific key ────────────────────
async def build_index(docs: list[LoadedDocument], index_key: str):
    """
    Build FAISS + BM25 index for index_key.
    Yields SSE progress dicts. Caller holds the per-key lock.
    """
    all_metas: list[ChunkMeta] = []
    file_type_counts: dict[str, int] = {}

    # retain chunks from files not being re-indexed
    meta_p = _meta_path(index_key)
    if meta_p.exists():
        try:
            existing = json.loads(meta_p.read_text())
            new_sources = {d.source for d in docs}
            kept = [
                ChunkMeta.from_dict(m)
                for m in existing
                if m["source"] not in new_sources
            ]
            all_metas.extend(kept)
            logger.info(
                f"retained {len(kept)} chunks from unchanged files",
                stage="index",
            )
        except Exception:
            pass

    # chunk new docs
    for doc in docs:
        yield {
            "status": "indexing",
            "current_file": doc.source,
            "files_processed": [d.source for d in docs[: docs.index(doc)]],
            "chunks_indexed": len(all_metas),
        }

        with Timer("index", {"file": doc.source}):
            chunks = _chunk_document(doc)

        all_metas.extend(chunks)
        file_type_counts[doc.file_type] = file_type_counts.get(doc.file_type, 0) + 1

        logger.info(
            f"chunked {doc.source}: {len(chunks)} chunks",
            stage="index",
            chunk_count=len(chunks),
        )

        yield {
            "status": "indexing",
            "current_file": doc.source,
            "files_processed": [d.source for d in docs[: docs.index(doc) + 1]],
            "chunks_indexed": len(all_metas),
        }

    if not all_metas:
        raise ValueError("no chunks produced from documents")

    # build FAISS
    yield {
        "status": "indexing",
        "current_file": "building vector index...",
        "files_processed": [d.source for d in docs],
        "chunks_indexed": len(all_metas),
    }

    log_memory("before FAISS build")

    with Timer("index"):
        embeddings = _get_embeddings()
        texts = [m.text for m in all_metas]
        metadatas = [{"chunk_id": m.chunk_id, "source": m.source} for m in all_metas]
        faiss_store = FAISS.from_texts(texts, embeddings, metadatas=metadatas)

    log_memory("after FAISS build")
    logger.info(
        f"FAISS index built: {len(all_metas)} vectors",
        stage="index",
        chunk_count=len(all_metas),
    )

    # build BM25
    yield {
        "status": "indexing",
        "current_file": "building BM25 index...",
        "files_processed": [d.source for d in docs],
        "chunks_indexed": len(all_metas),
    }

    with Timer("index"):
        bm25_index = _build_bm25(all_metas)

    logger.info(
        f"BM25 index built: {len(all_metas)} documents",
        stage="index",
    )

    # persist
    from datetime import datetime

    stats = {
        "total_files": len(docs),
        "total_chunks": len(all_metas),
        "indexed_at": datetime.utcnow().isoformat(),
        "file_types": file_type_counts,
    }

    _save_index(index_key, faiss_store, bm25_index, all_metas, stats)

    _registry[index_key] = IndexStore(
        faiss_store=faiss_store,
        bm25_index=bm25_index,
        chunk_metas=all_metas,
    )

    logger.info(
        f"index complete: {len(all_metas)} chunks from {len(docs)} files (key: {index_key})",
        stage="index",
        chunk_count=len(all_metas),
        file_count=len(docs),
    )

    yield {
        "status": "complete",
        "current_file": "",
        "files_processed": [d.source for d in docs],
        "chunks_indexed": len(all_metas),
        "index_id": index_key,
        "message": f"{len(all_metas)} chunks indexed from {len(docs)} files",
    }
