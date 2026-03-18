# document_loader.py
import hashlib
import json
import re
from pathlib import Path
from typing import Optional

import frontmatter
import markdownify
import openpyxl
from bs4 import BeautifulSoup
from pypdf import PdfReader

from config import (
    HASH_STORE_PATH,
    FEATURES,
)
from logger import logger, Timer

# supported extensions
SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf", ".xlsx", ".html", ".htm"}


# data class for a loaded document
class LoadedDocument:
    def __init__(
        self,
        content: str,
        source: str,
        file_type: str,
        page_count: int = 1,
        metadata: Optional[dict] = None,
    ):
        self.content = content
        self.source = source
        self.file_type = file_type
        self.page_count = page_count
        self.metadata = metadata or {}


# hash store
def _load_hash_store() -> dict[str, str]:
    if HASH_STORE_PATH.exists():
        try:
            return json.loads(HASH_STORE_PATH.read_text())
        except Exception:
            return {}
    return {}


def _save_hash_store(store: dict[str, str]) -> None:
    HASH_STORE_PATH.write_text(json.dumps(store, indent=2))


def _hash_file(path: Path) -> str:
    """SHA256 hash of file contents."""
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)
    return sha.hexdigest()


# individual file loaders
def _load_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _load_markdown(path: Path) -> str:
    post = frontmatter.load(str(path))
    content = str(post.content)
    # prepend frontmatter metadata as context
    if post.metadata:
        meta_lines = "\n".join(f"**{k}**: {v}" for k, v in post.metadata.items())
        content = f"{meta_lines}\n\n{content}"
    return content


def _load_pdf(path: Path) -> tuple[str, int]:
    reader = PdfReader(str(path))
    pages = []
    page_count = len(reader.pages)

    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(f"<!-- page {i + 1} -->\n{text}")

    return "\n\n".join(pages), page_count


def _load_html(path: Path) -> str:
    html = path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")

    # remove noise elements
    for tag in soup(
        ["script", "style", "nav", "footer", "header", "aside", "meta", "link"]
    ):
        tag.decompose()

    # convert to markdown
    md = markdownify.markdownify(
        str(soup),
        heading_style="ATX",
        bullets="-",
        strip=["a"],
    )

    # clean up excessive whitespace
    md = re.sub(r"\n{3,}", "\n\n", md).strip()
    return md


def _load_xlsx(path: Path) -> str:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheets = []

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = []
        headers = []

        for i, row in enumerate(ws.iter_rows(values_only=True)):
            # skip completely empty rows
            values = [str(v).strip() if v is not None else "" for v in row]
            if not any(values):
                continue

            if i == 0:
                # first non-empty row is the header
                headers = values
                rows.append("| " + " | ".join(headers) + " |")
                rows.append("| " + " | ".join(["---"] * len(headers)) + " |")
            else:
                # pad row to header length
                while len(values) < len(headers):
                    values.append("")
                rows.append("| " + " | ".join(values[: len(headers)]) + " |")

        if rows:
            sheets.append(f"## Sheet: {sheet_name}\n\n" + "\n".join(rows))

    wb.close()
    return "\n\n".join(sheets)


# main loader
def load_file(path: Path) -> Optional[LoadedDocument]:
    """Load a single file and return a LoadedDocument or None if unsupported."""
    ext = path.suffix.lower()

    if ext not in SUPPORTED_EXTENSIONS:
        logger.warning(f"unsupported file type: {path.name}", stage="loader")
        return None

    try:
        if ext == ".txt":
            content = _load_txt(path)
            page_count = 1

        elif ext == ".md":
            content = _load_markdown(path)
            page_count = 1

        elif ext == ".pdf":
            content, page_count = _load_pdf(path)

        elif ext in (".html", ".htm"):
            content = _load_html(path)
            page_count = 1

        elif ext == ".xlsx":
            content = _load_xlsx(path)
            page_count = 1

        else:
            return None

        if not content.strip():
            logger.warning(f"empty content: {path.name}", stage="loader")
            return None

        return LoadedDocument(
            content=content,
            source=path.name,
            file_type=ext.lstrip("."),
            page_count=page_count,
            metadata={"path": str(path), "size_bytes": path.stat().st_size},
        )

    except Exception as e:
        logger.error(
            f"failed to load {path.name}: {e}",
            stage="loader",
            error=str(e),
        )
        return None


# directory scanner
def scan_directory(
    directory: str,
) -> tuple[list[LoadedDocument], list[str], list[str]]:
    """
    Scan directory for supported files.
    Returns:
        docs_to_process  — new or modified files
        skipped_files    — unchanged files (hash match)
        failed_files     — files that failed to load
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")

    # collect all supported files recursively
    all_files = [
        p
        for p in dir_path.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    if not all_files:
        raise ValueError(f"No supported files found in: {directory}")

    hash_store = _load_hash_store() if FEATURES["content_hashing"] else {}
    docs_to_process: list[LoadedDocument] = []
    skipped_files: list[str] = []
    failed_files: list[str] = []

    for file_path in sorted(all_files):
        file_key = str(file_path)
        file_hash = _hash_file(file_path)

        # skip unchanged files
        if FEATURES["content_hashing"] and hash_store.get(file_key) == file_hash:
            logger.info(
                f"skipping unchanged: {file_path.name}",
                stage="loader",
            )
            skipped_files.append(file_path.name)
            continue

        with Timer("index", {"file": file_path.name}):
            doc = load_file(file_path)

        if doc is None:
            failed_files.append(file_path.name)
            continue

        # update hash store on successful load
        hash_store[file_key] = file_hash
        docs_to_process.append(doc)
        logger.info(
            f"loaded: {file_path.name} ({doc.file_type}, " f"{len(doc.content)} chars)",
            stage="loader",
        )

    # persist updated hashes
    if FEATURES["content_hashing"]:
        _save_hash_store(hash_store)

    logger.info(
        f"scan complete: {len(docs_to_process)} new, "
        f"{len(skipped_files)} skipped, "
        f"{len(failed_files)} failed",
        stage="loader",
        file_count=len(docs_to_process),
    )

    return docs_to_process, skipped_files, failed_files
