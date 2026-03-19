# config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# load .env if present — silently ignored in Docker
load_dotenv()

# ── Base ───────────────────────────────────────────────
BASE_DIR = Path(os.getcwd())

# ── Ollama ─────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2:3b")
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
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2048"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.1"))
TOKEN_BUDGET = int(os.getenv("TOKEN_BUDGET", "8192"))

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
You are a helpful assistant that answers questions based on \
the provided context documents. Be concise and accurate.
Always cite sources using [1], [2] notation matching the chunks.
Never fabricate information not present in the context.\
"""
