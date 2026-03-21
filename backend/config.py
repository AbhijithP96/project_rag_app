# config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# ── Air-gap: block ALL HuggingFace Hub network access ──
# Must be set before any transformers / sentence_transformers import.
# These prevent update checks, model downloads, and anonymous telemetry.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_DATASETS_OFFLINE", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")

# load .env if present — silently ignored in Docker
load_dotenv()

# ── Base ───────────────────────────────────────────────
BASE_DIR = Path(os.getcwd())

# ── Ollama ─────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:latest")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "mxbai-embed-large:latest")

# ── Model paths ────────────────────────────────────────
MODELS_DIR = Path(os.getenv("MODELS_DIR", "./models"))
RERANKER_PATH = Path(os.getenv("RERANKER_PATH", str(MODELS_DIR / "bge-reranker-base")))

# ── Chunking ───────────────────────────────────────────
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "512"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "64"))
SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

# ── Retrieval ──────────────────────────────────────────
TOP_K_RETRIEVAL = int(os.getenv("TOP_K_RETRIEVAL", "10"))
TOP_N_RERANK = int(os.getenv("TOP_N_RERANK", "3"))
RERANK_THRESHOLD = float(os.getenv("RERANK_THRESHOLD", "0.3"))

# ── Hybrid search weights ──────────────────────────────
BM25_WEIGHT = float(os.getenv("BM25_WEIGHT", "0.3"))
VECTOR_WEIGHT = float(os.getenv("VECTOR_WEIGHT", "0.7"))

# ── PII / Safety ───────────────────────────────────────
ENABLE_PII_REDACTION = os.getenv("PII_REDACTION", "true").lower() == "true"
PII_ENTITIES = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "CREDIT_CARD",
    "IBAN_CODE",
    "IP_ADDRESS",
    "LOCATION",
    "NRP",
]

# ── FAISS + hash store ─────────────────────────────────
INDEX_DIR = Path(os.getenv("INDEX_DIR", "./faiss_index"))
HASH_STORE_PATH = INDEX_DIR / "file_hashes.json"
STATS_PATH = INDEX_DIR / "index_stats.json"
INDEX_DIR.mkdir(exist_ok=True)

# ── LLM generation ─────────────────────────────────────
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "8192"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.1"))
TOKEN_BUDGET = int(os.getenv("TOKEN_BUDGET", "28000"))

# ── Redis (conversation history) ───────────────────────
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/")
HISTORY_MAX_RECENT = int(
    os.getenv("HISTORY_MAX_RECENT", "8")
)  # messages kept raw (= 4 exchanges)
HISTORY_SUMMARIZE_AT = int(
    os.getenv("HISTORY_SUMMARIZE_AT", "8")
)  # trigger summarisation at this count
HISTORY_TTL = int(os.getenv("HISTORY_TTL", "7200"))  # session expiry in seconds (2 h)

# ── OOM protection ─────────────────────────────────────
MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "3"))

# ── Logging ────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = Path(os.getenv("LOG_DIR", "./logs"))
LOG_FILE = LOG_DIR / "rag.log"
LOG_DIR.mkdir(exist_ok=True)

# ── Feature flags ──────────────────────────────────────
FEATURES = {
    "pii_redaction": ENABLE_PII_REDACTION,
    "self_correction": False,  # disabled — using simple RAG
    "content_hashing": os.getenv("CONTENT_HASHING", "true").lower() == "true",
    "hybrid_search": os.getenv("HYBRID_SEARCH", "true").lower() == "true",
    "reranking": os.getenv("RERANKING", "true").lower() == "true",
}

# ── System prompt ──────────────────────────────────────
SYSTEM_PROMPT = """\
You are an expert research assistant. Answer strictly from the provided \
context documents using well-structured **Markdown**.

## Formatting rules — follow exactly
- Start with a `##` heading that names the topic.
- Use `##` / `###` headings to separate major sections.
- Use `**bold**` for key terms on first use.
- Use numbered lists for sequential steps; bullet lists (`-`) for \
non-sequential items.
- Wrap all code, file names, and commands in backticks or fenced code blocks.
- Use `>` blockquotes for direct quotations from the source.
- Separate sections with a blank line. Do not use horizontal rules.

## Citations
- After every sentence that states a fact, append an inline marker: [1], [2], …
- The number matches the chunk number in "Context documents".
- If multiple chunks support the same fact, list all: [1][3].

## Accuracy
- Only state what the context explicitly supports.
- If the context is insufficient, say so and explain what is missing.
- Never fabricate facts, numbers, or citations.\
"""

# Pure LLM mode — no documents, no citations
SYSTEM_PROMPT_NO_CONTEXT = """\
You are a knowledgeable assistant. Answer the user's question thoroughly \
using well-structured **Markdown**.

## Formatting rules — follow exactly
- Start with a `##` heading that names the topic.
- Use `##` / `###` headings to separate major sections.
- Use `**bold**` for key terms on first use.
- Use numbered lists for steps; bullet lists (`-`) for non-sequential items.
- Wrap code, file names, and commands in backticks or fenced code blocks.
- Separate sections with a blank line.

Do NOT use citation markers like [1] or [2] — there are no source documents.\
"""
