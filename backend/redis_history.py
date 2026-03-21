# redis_history.py
import json
from typing import Optional

import redis.asyncio as aioredis

from config import REDIS_URL, HISTORY_MAX_RECENT, HISTORY_TTL
from logger import logger


async def _client() -> Optional[aioredis.Redis]:
    """Return a connected Redis client, or None if unavailable."""
    try:
        r = aioredis.from_url(REDIS_URL, decode_responses=True)
        await r.ping()
        return r
    except Exception as e:
        logger.warning(f"Redis unavailable: {e}", stage="history")
        return None


async def get_history(session_id: str) -> tuple[str, list[dict]]:
    """
    Return (summary, recent_messages) for a session.
    Degrades gracefully to ("", []) if Redis is down or session is new.
    """
    r = await _client()
    if not r:
        return "", []
    try:
        key = f"session:{session_id}"
        data = await r.hgetall(key)
        if not data:
            return "", []
        summary  = data.get("summary", "")
        messages = json.loads(data.get("messages", "[]"))
        return summary, messages
    except Exception as e:
        logger.warning(f"history get failed: {e}", stage="history")
        return "", []
    finally:
        await r.aclose()


async def append_exchange(
    session_id: str,
    user_msg: str,
    assistant_msg: str,
) -> int:
    """
    Append one user/assistant exchange.
    Trims to the last HISTORY_MAX_RECENT messages.
    Returns the new message count (0 if Redis is down).
    """
    r = await _client()
    if not r:
        return 0
    try:
        key  = f"session:{session_id}"
        data = await r.hgetall(key)

        summary  = data.get("summary", "")
        messages = json.loads(data.get("messages", "[]"))

        messages.append({"role": "user",      "content": user_msg})
        # cap stored assistant response to avoid bloating Redis
        messages.append({"role": "assistant", "content": assistant_msg[:800]})

        if len(messages) > HISTORY_MAX_RECENT:
            messages = messages[-HISTORY_MAX_RECENT:]

        await r.hset(key, mapping={
            "summary":  summary,
            "messages": json.dumps(messages),
        })
        await r.expire(key, HISTORY_TTL)

        logger.info(
            f"history saved: {session_id[:8]}… ({len(messages)} messages)",
            stage="history",
        )
        return len(messages)

    except Exception as e:
        logger.warning(f"history append failed: {e}", stage="history")
        return 0
    finally:
        await r.aclose()


async def update_summary(
    session_id: str,
    new_summary: str,
    messages:    list[dict],
) -> None:
    """Persist a new rolling summary + trimmed message list after summarisation."""
    r = await _client()
    if not r:
        return
    try:
        key = f"session:{session_id}"
        await r.hset(key, mapping={
            "summary":  new_summary,
            "messages": json.dumps(messages),
        })
        await r.expire(key, HISTORY_TTL)
    except Exception as e:
        logger.warning(f"history update failed: {e}", stage="history")
    finally:
        await r.aclose()
