# rag_pipeline.py
import re
from typing import AsyncGenerator

from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_classic.schema import HumanMessage, SystemMessage

from config import (
    LLM_MODEL,
    OLLAMA_BASE_URL,
    MAX_TOKENS,
    TEMPERATURE,
    TOKEN_BUDGET,
    SYSTEM_PROMPT,
    FEATURES,
)
from models import RetrievedChunk
from retriever import retrieve
from filter import redact_query, redact_chunks
from logger import logger, Timer
import indexer


# LLM singleton
_llm: ChatOllama | None = None


def _get_llm() -> ChatOllama:
    global _llm
    if _llm is None:
        _llm = ChatOllama(
            model=LLM_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=TEMPERATURE,
            num_predict=MAX_TOKENS,
        )
        logger.info(f"LLM loaded: {LLM_MODEL}", stage="generation")
    return _llm


# helpers
def _strip_think_tags(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _estimate_tokens(text: str) -> int:
    return max(1, int(len(text.split()) / 0.75))


def _build_context(chunks: list[RetrievedChunk]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, 1):
        page = f" p.{chunk.page}" if chunk.page else ""
        parts.append(f"[{i}] Source: {chunk.source}{page}\n{chunk.text}")
    return "\n\n---\n\n".join(parts)


def _detect_citations(token: str, chunk_map: dict[int, str]) -> list[dict]:
    """Detect [n] citation markers in a token and return citation events."""
    citations = []
    for match in re.finditer(r"\[(\d+)\]", token):
        idx = int(match.group(1))
        if idx in chunk_map:
            citations.append(
                {
                    "type": "citation",
                    "citation_index": idx,
                    "citation_id": chunk_map[idx],
                }
            )
    return citations


# core streaming loop
async def _stream_llm(
    llm: ChatOllama,
    messages: list,
    ref_text: str,
    chunk_map: dict[int, str] | None = None,
) -> AsyncGenerator[dict, None]:
    prompt_tokens = _estimate_tokens(ref_text)
    completion_tokens = 0
    last_token = ""

    try:
        with Timer("generation"):
            async for chunk in llm.astream(messages):
                token = _strip_think_tags(chunk.content)
                if not token:
                    continue

                # spacing fix
                if (
                    last_token
                    and not token.startswith(" ")
                    and not token.startswith("\n")
                    and not token[0] in ".,!?;:)'\"]-"
                    and not last_token.endswith(" ")
                    and not last_token.endswith("\n")
                    and not last_token[-1] in "(['\"-"
                ):
                    token = " " + token

                last_token = token
                completion_tokens += 1

                # emit citation events before the token
                if chunk_map:
                    for citation in _detect_citations(token, chunk_map):
                        yield citation

                yield {"type": "token", "token": token}

        yield {
            "type": "token_usage",
            "usage": {
                "prompt_tokens": prompt_tokens,
                "context_tokens": _estimate_tokens(ref_text),
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "budget_limit": TOKEN_BUDGET,
            },
        }
        yield {"type": "done"}

    except Exception as e:
        logger.error(f"LLM stream error: {e}", stage="generation", error=str(e))
        yield {
            "type": "error",
            "error_type": "model_error",
            "message": f"LLM generation failed: {str(e)}",
        }


# main pipeline
async def run_pipeline(
    query: str,
    index_key: str | None = None,
    history: str = "",
    top_k: int = 10,
    top_n: int = 3,
) -> AsyncGenerator[dict, None]:
    """
    Simple RAG pipeline:
      1. PII redact query
      2. Hybrid retrieval + BGE reranking
      3. Stream LLM response with citations
    """
    llm = _get_llm()

    # step 1: PII redaction
    if FEATURES["pii_redaction"]:
        query = redact_query(query)
        logger.info("query PII redacted", stage="pii")

    # step 2: check if index is ready — require explicit index_key for RAG
    if not index_key or not indexer.is_ready(index_key):
        logger.info("no index — pure LLM mode", stage="generation")
        yield {"type": "generation_start"}
        async for event in _stream_llm(
            llm,
            [
                SystemMessage(content="You are a helpful assistant. Answer concisely."),
                HumanMessage(content=query),
            ],
            query,
        ):
            yield event
        return

    # step 3: hybrid retrieval
    yield {"type": "retrieval_start"}
    logger.info(f"retrieving for: '{query[:60]}'", stage="retrieval")

    try:
        with Timer("retrieval"):
            raw_chunks, reranked_chunks = await retrieve(
                query, index_key=index_key, top_k=top_k, top_n=top_n
            )
    except Exception as e:
        logger.error(f"retrieval failed: {e}", stage="retrieval", error=str(e))
        yield {
            "type": "error",
            "error_type": "retrieval_error",
            "message": f"Retrieval failed: {str(e)}",
        }
        return

    yield {
        "type": "retrieval_complete",
        "chunks": [c.model_dump() for c in raw_chunks],
    }

    logger.info(
        f"retrieved {len(raw_chunks)} chunks, reranked to {len(reranked_chunks)}",
        stage="retrieval",
    )

    # step 4: reranking
    yield {
        "type": "rerank_complete",
        "chunks": [c.model_dump() for c in reranked_chunks],
    }

    # fallback to raw if reranking filtered everything
    final_chunks = reranked_chunks if reranked_chunks else raw_chunks[:top_n]

    if not final_chunks:
        logger.warning("no chunks available — pure LLM fallback", stage="retrieval")
        yield {"type": "generation_start"}
        async for event in _stream_llm(
            llm,
            [
                SystemMessage(content="You are a helpful assistant. Answer concisely."),
                HumanMessage(content=query),
            ],
            query,
        ):
            yield event
        return

    # step 5: PII redact chunks
    if FEATURES["pii_redaction"]:
        texts = redact_chunks([c.text for c in final_chunks])
        for i, chunk in enumerate(final_chunks):
            chunk.text = texts[i]

    # step 6: build context + citation map
    context = _build_context(final_chunks)
    chunk_map = {i + 1: c.id for i, c in enumerate(final_chunks)}

    logger.info(
        f"context built: {len(final_chunks)} chunks, "
        f"{_estimate_tokens(context)} tokens",
        stage="generation",
    )

    # step 7: stream generation
    yield {"type": "generation_start"}

    # build prompt with history if provided
    history_section = ""
    if history.strip():
        history_section = f"\nConversation history:\n{history}\n"

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"{history_section}"
                f"Context documents:\n\n{context}"
                f"\n\n---\n\n"
                f"Question: {query}\n\n"
                f"Answer based on the context above. "
                f"Cite sources as [1], [2] etc."
            )
        ),
    ]

    async for event in _stream_llm(llm, messages, context, chunk_map):
        yield event

    logger.info("pipeline complete", stage="generation")
