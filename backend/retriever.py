from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
from langchain_classic.schema import Document
from sentence_transformers import CrossEncoder

from config import (
    TOP_K_RETRIEVAL,
    TOP_N_RERANK,
    RERANK_THRESHOLD,
    BM25_WEIGHT,
    VECTOR_WEIGHT,
    RERANKER_PATH,
    FEATURES,
)
from models import RetrievedChunk
from logger import logger, Timer
import indexer

# load reranker once at module level
# loads from local path — no internet required
_reranker: CrossEncoder | None = None


def _get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        logger.info(
            f"loading reranker from {RERANKER_PATH}",
            stage="reranking",
        )
        _reranker = CrossEncoder(
            str(RERANKER_PATH), max_length=512, local_files_only=True
        )
        logger.info("reranker loaded", stage="reranking")
    return _reranker


def _build_langchain_docs(store: indexer.IndexStore) -> list[Document]:
    return [
        Document(
            page_content=m.text,
            metadata={
                "chunk_id": m.chunk_id,
                "source": m.source,
                "page": m.page,
                "start_char": m.start_char,
                "end_char": m.end_char,
            },
        )
        for m in store.chunk_metas
    ]


async def retrieve(
    query: str,
    index_key: str | None = None,
    top_k: int = TOP_K_RETRIEVAL,
    top_n: int = TOP_N_RERANK,
) -> tuple[list[RetrievedChunk], list[RetrievedChunk]]:
    """
    Hybrid retrieval:
      1. BM25 + FAISS via EnsembleRetriever (RRF fusion)
      2. BGE-Reranker-Base cross-encoder reranking
    """
    if not indexer.is_ready(index_key):
        raise RuntimeError("index not ready — run /index first")

    store = indexer.get_index(index_key) if index_key else indexer.get_any_index()
    docs = _build_langchain_docs(store)

    # step 1: BM25 retriever
    with Timer("retrieval", {"stage": "bm25"}):
        bm25_retriever = BM25Retriever.from_documents(docs)
        bm25_retriever.k = top_k

    # step 2: FAISS retriever
    with Timer("retrieval", {"stage": "faiss"}):
        faiss_retriever = store.faiss_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": top_k},
        )

    # step 3: EnsembleRetriever (RRF built in)
    with Timer("retrieval", {"stage": "ensemble"}):
        ensemble = EnsembleRetriever(
            retrievers=[bm25_retriever, faiss_retriever],
            weights=[BM25_WEIGHT, VECTOR_WEIGHT],
        )
        results = await ensemble.ainvoke(query)

    logger.info(
        f"ensemble retrieval: {len(results)} chunks",
        stage="retrieval",
    )

    # step 4: build raw chunks
    raw_chunks: list[RetrievedChunk] = []
    for i, doc in enumerate(results[:top_k]):
        meta = doc.metadata
        raw_chunks.append(
            RetrievedChunk(
                id=meta["chunk_id"],
                text=doc.page_content,
                source=meta["source"],
                page=meta.get("page"),
                score=round(1.0 / (1.0 + i), 4),
                bm25_score=0.0,
                vector_score=0.0,
                start_char=meta.get("start_char", 0),
                end_char=meta.get("end_char", 0),
            )
        )

    # step 5: BGE cross-encoder reranking
    if FEATURES["reranking"] and raw_chunks:
        with Timer("reranking", {"stage": "bge_reranker"}):
            reranker = _get_reranker()

            pairs = [(query, c.text) for c in raw_chunks]
            scores = reranker.predict(pairs)

            for chunk, score in zip(raw_chunks, scores):
                chunk.score = round(float(score), 4)
                chunk.vector_score = chunk.score

            raw_chunks.sort(key=lambda c: c.score, reverse=True)

            reranked = [c for c in raw_chunks if c.score >= RERANK_THRESHOLD][:top_n]

        logger.info(
            f"BGE reranking: {len(reranked)} chunks selected "
            f"(threshold: {RERANK_THRESHOLD})",
            stage="reranking",
        )

    else:
        reranked = raw_chunks[:top_n]

    return raw_chunks, reranked
