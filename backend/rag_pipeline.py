# rag_pipeline.py
import asyncio
import re
from typing import AsyncGenerator

from langchain_classic.schema import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama

from config import (
    FEATURES,
    HISTORY_SUMMARIZE_AT,
    LLM_MODEL,
    MAX_TOKENS,
    OLLAMA_BASE_URL,
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_NO_CONTEXT,
    TEMPERATURE,
    TOKEN_BUDGET,
)
from filter import redact_query, redact_chunks
from logger import logger, Timer
from models import RetrievedChunk
from redis_history import get_history, append_exchange, update_summary
from retriever import retrieve
import indexer


class MarkdownOutputParser(StrOutputParser):
    """StrOutputParser that signals the chain expects markdown-formatted output."""
    pass


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


# ── helpers ────────────────────────────────────────────

def _strip_think_tags(text: str) -> str:
    stripped = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # only strip surrounding whitespace if think tags were actually removed
    return stripped.strip() if stripped != text else text


def _estimate_tokens(text: str) -> int:
    return max(1, int(len(text.split()) / 0.75))


def _build_context(chunks: list[RetrievedChunk]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, 1):
        page = f" p.{chunk.page}" if chunk.page else ""
        parts.append(f"[{i}] Source: {chunk.source}{page}\n{chunk.text}")
    return "\n\n---\n\n".join(parts)


def _detect_citations(token: str, chunk_map: dict[int, str]) -> list[dict]:
    citations = []
    for match in re.finditer(r"\[(\d+)\]", token):
        idx = int(match.group(1))
        if idx in chunk_map:
            citations.append({
                "type":           "citation",
                "citation_index": idx,
                "citation_id":    chunk_map[idx],
            })
    return citations


def _format_history(summary: str, recent: list[dict]) -> str:
    """Build a compact history string to inject into the user prompt."""
    parts = []
    if summary:
        parts.append(f"Conversation summary: {summary}")
    if recent:
        parts.append("Recent exchanges:")
        for m in recent[-4:]:   # last 2 user/assistant pairs
            role    = m["role"].capitalize()
            content = m["content"][:300]
            parts.append(f"  {role}: {content}")
    return "\n".join(parts)


# ── query rewriting ────────────────────────────────────

async def _rewrite_query(
    query:  str,
    summary: str,
    recent:  list[dict],
    llm:    ChatOllama,
) -> str:
    """
    Make the query self-contained using conversation history.
    Only called when history is non-empty; falls back to original on any error.
    """
    history_text = _format_history(summary, recent)

    prompt = (
        f"{history_text}\n\n"
        f"New question: {query}\n\n"
        f"If this question refers to anything from the conversation above "
        f"(uses pronouns such as 'it', 'they', 'this', 'that', or implicitly "
        f"continues a prior topic), rewrite it as a fully self-contained question. "
        f"If it is already self-contained, return it unchanged. "
        f"Output only the question text, no explanation."
    )

    try:
        response  = await llm.ainvoke([HumanMessage(content=prompt)])
        rewritten = _strip_think_tags(response.content).strip()

        # sanity checks — reject if empty, too long, or clearly broken
        if not rewritten or len(rewritten) > len(query) * 4:
            return query

        logger.info(
            f"query rewritten: '{query[:50]}' → '{rewritten[:50]}'",
            stage="rewrite",
        )
        return rewritten

    except Exception as e:
        logger.warning(f"query rewrite failed: {e}", stage="rewrite")
        return query


# ── background history save + summarisation ────────────

async def _save_and_maybe_summarise(
    session_id:     str,
    user_msg:       str,
    assistant_msg:  str,
    summary:        str,
    llm:            ChatOllama,
) -> None:
    """
    Append the exchange to Redis, then summarise older messages if the
    history has grown beyond HISTORY_SUMMARIZE_AT.
    Runs as a fire-and-forget asyncio task — does not block the response.
    """
    msg_count = await append_exchange(session_id, user_msg, assistant_msg)

    if msg_count < HISTORY_SUMMARIZE_AT:
        return

    # re-fetch after append to get the current state
    _, messages = await get_history(session_id)
    if len(messages) < 4:
        return

    # summarise the first half, keep the second half raw
    split        = len(messages) // 2
    to_summarise = messages[:split]
    keep         = messages[split:]

    convo_text = "\n".join(
        f"{m['role'].capitalize()}: {m['content'][:300]}"
        for m in to_summarise
    )

    existing = f"Previous summary: {summary}\n\n" if summary else ""
    prompt = (
        f"{existing}"
        f"Summarise this conversation excerpt in 2-3 concise sentences, "
        f"capturing key topics, questions, and conclusions only:\n\n"
        f"{convo_text}"
    )

    try:
        response    = await llm.ainvoke([HumanMessage(content=prompt)])
        new_summary = _strip_think_tags(response.content).strip()
        await update_summary(session_id, new_summary, keep)
        logger.info(
            f"history summarised: {session_id[:8]}… "
            f"({len(to_summarise)} msgs → summary)",
            stage="history",
        )
    except Exception as e:
        logger.warning(f"history summarisation failed: {e}", stage="history")


# ── core streaming loop ────────────────────────────────

async def _stream_llm(
    llm:       ChatOllama,
    messages:  list,
    ref_text:  str,
    chunk_map: dict[int, str] | None = None,
) -> AsyncGenerator[dict, None]:
    prompt_tokens     = _estimate_tokens(ref_text)
    completion_tokens = 0

    try:
        chain = llm | MarkdownOutputParser()
        with Timer("generation"):
            async for token in chain.astream(messages):
                token = _strip_think_tags(token)
                if not token:
                    continue

                completion_tokens += 1

                if chunk_map:
                    for citation in _detect_citations(token, chunk_map):
                        yield citation

                yield {"type": "token", "token": token}

        yield {
            "type": "token_usage",
            "usage": {
                "prompt_tokens":    prompt_tokens,
                "context_tokens":   _estimate_tokens(ref_text),
                "completion_tokens": completion_tokens,
                "total_tokens":     prompt_tokens + completion_tokens,
                "budget_limit":     TOKEN_BUDGET,
            },
        }
        yield {"type": "done"}

    except Exception as e:
        logger.error(f"LLM stream error: {e}", stage="generation", error=str(e))
        yield {
            "type":       "error",
            "error_type": "model_error",
            "message":    f"LLM generation failed: {str(e)}",
        }


# ── main pipeline ──────────────────────────────────────

async def run_pipeline(
    query:      str,
    session_id: str | None = None,
    index_key:  str | None = None,
    top_k:      int = 10,
    top_n:      int = 3,
) -> AsyncGenerator[dict, None]:
    """
    RAG pipeline:
      1. Fetch conversation history from Redis
      2. Rewrite query to be self-contained (if history exists)
      3. PII redact
      4. Hybrid retrieval + BGE reranking
      5. Stream LLM response with citations
      6. Save exchange to Redis (background) + summarise if needed
    """
    llm = _get_llm()

    # step 1: fetch history
    summary, recent = ("", [])
    if session_id:
        summary, recent = await get_history(session_id)

    # step 2: rewrite query if history exists
    original_query = query
    if session_id and (summary or recent):
        query = await _rewrite_query(query, summary, recent, llm)

    # step 3: PII redaction
    if FEATURES["pii_redaction"]:
        query = redact_query(query)
        logger.info("query PII redacted", stage="pii")

    # ── helpers for streaming + collecting response ────
    response_tokens: list[str] = []

    async def _stream_and_collect(llm, messages, ref_text, chunk_map=None):
        async for event in _stream_llm(llm, messages, ref_text, chunk_map):
            if event.get("type") == "token":
                response_tokens.append(event["token"])
            yield event

    # step 4: check index — no index_key → pure LLM mode
    if not index_key or not indexer.is_ready(index_key):
        logger.info("no index — pure LLM mode", stage="generation")

        history_section = (
            f"\n{_format_history(summary, recent)}\n\n"
            if (summary or recent) else ""
        )

        yield {"type": "generation_start"}
        async for event in _stream_and_collect(
            llm,
            [
                SystemMessage(content=SYSTEM_PROMPT_NO_CONTEXT),
                HumanMessage(content=f"{history_section}Question: {query}"),
            ],
            query,
        ):
            yield event

        # save to Redis in background
        if session_id:
            asyncio.create_task(_save_and_maybe_summarise(
                session_id, original_query, "".join(response_tokens),
                summary, llm,
            ))
        return

    # step 5: hybrid retrieval
    yield {"type": "retrieval_start"}
    logger.info(f"retrieving for: '{query[:60]}'", stage="retrieval")

    try:
        with Timer("retrieval"):
            raw_chunks, reranked_chunks = await retrieve(
                query, index_key=index_key, top_k=top_k, top_n=top_n,
            )
    except Exception as e:
        logger.error(f"retrieval failed: {e}", stage="retrieval", error=str(e))
        yield {
            "type":       "error",
            "error_type": "retrieval_error",
            "message":    f"Retrieval failed: {str(e)}",
        }
        return

    yield {"type": "retrieval_complete", "chunks": [c.model_dump() for c in raw_chunks]}
    logger.info(
        f"retrieved {len(raw_chunks)} chunks, reranked to {len(reranked_chunks)}",
        stage="retrieval",
    )

    # step 6: reranking
    yield {"type": "rerank_complete", "chunks": [c.model_dump() for c in reranked_chunks]}

    final_chunks = reranked_chunks if reranked_chunks else raw_chunks[:top_n]

    if not final_chunks:
        logger.warning("no chunks — pure LLM fallback", stage="retrieval")
        yield {"type": "generation_start"}
        async for event in _stream_and_collect(
            llm,
            [
                SystemMessage(content=SYSTEM_PROMPT_NO_CONTEXT),
                HumanMessage(content=query),
            ],
            query,
        ):
            yield event

        if session_id:
            asyncio.create_task(_save_and_maybe_summarise(
                session_id, original_query, "".join(response_tokens),
                summary, llm,
            ))
        return

    # step 7: PII redact chunks
    if FEATURES["pii_redaction"]:
        texts = redact_chunks([c.text for c in final_chunks])
        for i, chunk in enumerate(final_chunks):
            chunk.text = texts[i]

    # step 8: build context + citation map
    context   = _build_context(final_chunks)
    chunk_map = {i + 1: c.id for i, c in enumerate(final_chunks)}

    logger.info(
        f"context built: {len(final_chunks)} chunks, "
        f"{_estimate_tokens(context)} tokens",
        stage="generation",
    )

    # step 9: stream generation
    yield {"type": "generation_start"}

    history_section = (
        f"\n## Conversation history\n\n{_format_history(summary, recent)}\n\n"
        if (summary or recent) else ""
    )

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"{history_section}"
                f"## Context documents\n\n{context}"
                f"\n\n---\n\n"
                f"## Question\n\n{query}\n\n"
                f"Provide a detailed, well-structured answer using the context above. "
                f"Cover all relevant aspects the context supports. "
                f"Cite every claim with [1], [2], … inline."
            )
        ),
    ]

    async for event in _stream_and_collect(llm, messages, context, chunk_map):
        yield event

    # step 10: save exchange to Redis (background)
    if session_id:
        asyncio.create_task(_save_and_maybe_summarise(
            session_id, original_query, "".join(response_tokens),
            summary, llm,
        ))

    logger.info("pipeline complete", stage="generation")
