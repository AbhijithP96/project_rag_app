# indexer.py
import json
import pickle
import uuid

# from pathlib import Path
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

# paths
FAISS_PATH = INDEX_DIR / "faiss_store"
BM25_PATH = INDEX_DIR / "bm25_store.pkl"
META_PATH = INDEX_DIR / "chunk_meta.json"
STATS_PATH = INDEX_DIR / "index_stats.json"


# chunk metadata
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


# global index checks
_faiss_store: Optional[FAISS] = None
_bm25_index: Optional[BM25Okapi] = None
_chunk_metas: list[ChunkMeta] = []
_is_ready: bool = False


def is_ready() -> bool:
    return _is_ready


def get_chunk_by_id(chunk_id: str) -> Optional[ChunkMeta]:
    for c in _chunk_metas:
        if c.chunk_id == chunk_id:
            return c
    return None


# text splitter
def _get_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=SEPARATORS,
        length_function=len,
        is_separator_regex=False,
    )


# chunk document
def _chunk_document(doc: LoadedDocument) -> list[ChunkMeta]:
    splitter = _get_splitter()
    chunks = splitter.split_text(doc.content)
    metas = []
    cursor = 0

    for chunk_text in chunks:
        # find postion
        start = doc.content.find(chunk_text, cursor)
        if start == -1:
            start = cursor
        end = start + len(chunk_text)
        cursor = max(cursor, start)

        # page number estimation
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


# embedding model


def _get_embeddings() -> OllamaEmbeddings:
    return OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_BASE_URL)


# build bm25 index


def _build_bm25(metas: list[ChunkMeta]) -> BM25Okapi:
    tokenized = [m.text.lower().split() for m in metas]
    return BM25Okapi(tokenized)


# persist index


def _save_indexes(
    faiss_store: FAISS,
    bm25_index: BM25Okapi,
    metas: list[ChunkMeta],
    stats: dict,
) -> None:
    # create FAISS
    faiss_store.save_local(str(FAISS_PATH))

    # BM25
    with open(BM25_PATH, "wb") as f:
        pickle.dump(bm25_index, f)

    # chunk metadata
    META_PATH.write_text(json.dumps([m.to_dict() for m in metas], indent=2))

    # index stats
    STATS_PATH.write_text(json.dumps(stats, indent=2))

    logger.info(
        f"indexes saved to {INDEX_DIR}",
        stage="index",
    )


# load saved indexes
def load_indexes() -> bool:
    global _faiss_store, _bm25_index, _chunk_metas, _is_ready

    if not all(
        [
            FAISS_PATH.exists(),
            BM25_PATH.exists(),
            META_PATH.exists(),
        ]
    ):
        logger.info("no persisted index found", stage="index")
        return False

    try:
        embeddings = _get_embeddings()
        _faiss_store = FAISS.load_local(
            str(FAISS_PATH),
            embeddings,
            allow_dangerous_deserialization=True,
        )

        with open(BM25_PATH, "rb") as f:
            _bm25_index = pickle.load(f)

        raw_metas = json.loads(META_PATH.read_text())
        _chunk_metas = [ChunkMeta.from_dict(m) for m in raw_metas]
        _is_ready = True

        logger.info(
            f"indexes loaded: {len(_chunk_metas)} chunks",
            stage="index",
            chunk_count=len(_chunk_metas),
        )
        return True

    except Exception as e:
        logger.error(f"failed to load indexes: {e}", stage="index", error=str(e))
        return False


# main function
async def build_index(docs: list[LoadedDocument]):
    """
    Build FAISS + BM25 index from loaded documents.
    Yields progress dicts for SSE streaming.
    """
    global _faiss_store, _bm25_index, _chunk_metas, _is_ready

    _is_ready = False
    all_metas: list[ChunkMeta] = []
    file_type_counts: dict[str, int] = {}

    # load existing chunks
    if META_PATH.exists():
        try:
            existing = json.loads(META_PATH.read_text())
            # keep chunks from files not being reindexed
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
        _faiss_store = FAISS.from_texts(
            texts,
            embeddings,
            metadatas=metadatas,
        )

    log_memory("after FAISS build")
    logger.info(
        f"FAISS index built: {len(all_metas)} vectors",
        stage="index",
        chunk_count=len(all_metas),
    )

    # build bm25
    yield {
        "status": "indexing",
        "current_file": "building BM25 index...",
        "files_processed": [d.source for d in docs],
        "chunks_indexed": len(all_metas),
    }

    with Timer("index"):
        _bm25_index = _build_bm25(all_metas)

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

    _save_indexes(_faiss_store, _bm25_index, all_metas, stats)
    _chunk_metas = all_metas
    _is_ready = True

    logger.info(
        f"index complete: {len(all_metas)} chunks from {len(docs)} files",
        stage="index",
        chunk_count=len(all_metas),
        file_count=len(docs),
    )

    yield {
        "status": "complete",
        "current_file": "",
        "files_processed": [d.source for d in docs],
        "chunks_indexed": len(all_metas),
        "message": f"{len(all_metas)} chunks indexed from {len(docs)} files",
    }
