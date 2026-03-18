# pii_filter.py
import re
from dataclasses import dataclass
from typing import Optional

from config import FEATURES, PII_ENTITIES
from logger import logger, Timer


# PII pattern definitions
PII_PATTERNS: dict[str, re.Pattern] = {
    "EMAIL_ADDRESS": re.compile(
        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
        re.IGNORECASE,
    ),
    "PHONE_NUMBER": re.compile(
        r"""
        (?:
            \+?1?[\s.\-]?          # optional country code
            (?:\(\d{3}\)|\d{3})    # area code
            [\s.\-]?
            \d{3}
            [\s.\-]?
            \d{4}
        )
        """,
        re.VERBOSE,
    ),
    "CREDIT_CARD": re.compile(
        r"""
        (?:
            4[0-9]{12}(?:[0-9]{3})?          |  # Visa
            5[1-5][0-9]{14}                   |  # Mastercard
            3[47][0-9]{13}                    |  # Amex
            3(?:0[0-5]|[68][0-9])[0-9]{11}   |  # Diners
            6(?:011|5[0-9]{2})[0-9]{12}       |  # Discover
            (?:2131|1800|35\d{3})\d{11}           # JCB
        )
        """,
        re.VERBOSE,
    ),
    "IBAN_CODE": re.compile(
        r"\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}(?:[A-Z0-9]?){0,16}\b",
    ),
    "IP_ADDRESS": re.compile(
        r"""
        (?:
            # IPv4
            (?:25[0-5]|2[0-4]\d|[01]?\d\d?)
            (?:\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)){3}
            |
            # IPv6 simplified
            (?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}
        )
        """,
        re.VERBOSE,
    ),
    "SSN": re.compile(
        r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b",
    ),
    "PASSPORT": re.compile(
        r"\b[A-Z]{1,2}\d{6,9}\b",
    ),
    "DATE_OF_BIRTH": re.compile(
        r"""
        \b
        (?:
            (?:0?[1-9]|1[0-2])[-/.](?:0?[1-9]|[12]\d|3[01])[-/.](?:19|20)\d{2}  |
            (?:19|20)\d{2}[-/.](?:0?[1-9]|1[0-2])[-/.](?:0?[1-9]|[12]\d|3[01])
        )
        \b
        """,
        re.VERBOSE,
    ),
    "LOCATION": re.compile(
        r"""
        \b
        (?:
            \d{1,5}\s+                          # street number
            (?:[A-Z][a-z]+\s+){1,3}             # street name
            (?:Street|St|Avenue|Ave|Road|Rd|
               Boulevard|Blvd|Lane|Ln|Drive|Dr|
               Court|Ct|Place|Pl|Way)\b
        )
        """,
        re.VERBOSE,
    ),
    "NRP": re.compile(  # National Registration / ID
        r"\b[A-Z]{1,2}\d{6,8}[A-Z]?\b",
    ),
    "PERSON": re.compile(
        r"""
        \b
        (?:
            Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.          # title
        )
        \s+
        [A-Z][a-z]+                              # first name
        (?:\s+[A-Z][a-z]+)?                      # optional last name
        \b
        """,
        re.VERBOSE,
    ),
}


# detection result
@dataclass
class PIIMatch:
    entity_type: str
    text: str
    start: int
    end: int


@dataclass
class PIIResult:
    original: str
    redacted: str
    matches: list[PIIMatch]
    has_pii: bool


# core redaction
def _redact_text(text: str, entities: list[str]) -> PIIResult:
    matches: list[PIIMatch] = []
    redacted: str = text

    # collect all matches first — process in reverse
    # order to preserve string positions
    all_matches: list[tuple[int, int, str, str]] = []

    for entity_type in entities:
        pattern = PII_PATTERNS.get(entity_type)
        if pattern is None:
            continue

        for match in pattern.finditer(text):
            all_matches.append(
                (
                    match.start(),
                    match.end(),
                    entity_type,
                    match.group(),
                )
            )

    # sort by start position descending so replacements
    # don't shift subsequent positions
    all_matches.sort(key=lambda x: x[0], reverse=True)

    for start, end, entity_type, matched_text in all_matches:
        # skip very short matches — likely false positives
        if len(matched_text.strip()) < 3:
            continue

        placeholder = f"[{entity_type}]"
        redacted = redacted[:start] + placeholder + redacted[end:]

        matches.append(
            PIIMatch(
                entity_type=entity_type,
                text=matched_text,
                start=start,
                end=end,
            )
        )

    return PIIResult(
        original=text,
        redacted=redacted,
        matches=matches,
        has_pii=len(matches) > 0,
    )


# public API
def scan_and_redact(
    text: str,
    entities: Optional[list[str]] = None,
) -> PIIResult:
    """
    Scan text for PII and return redacted version.
    Uses entities from config by default.
    """
    if not FEATURES.get("pii_redaction", True):
        return PIIResult(
            original=text,
            redacted=text,
            matches=[],
            has_pii=False,
        )

    active_entities = entities or PII_ENTITIES

    with Timer("retrieval", {"stage": "pii_scan"}):
        result = _redact_text(text, active_entities)

    if result.has_pii:
        logger.warning(
            f"PII detected: {len(result.matches)} matches — "
            f"{[m.entity_type for m in result.matches]}",
            stage="pii",
            details={
                "entity_types": [m.entity_type for m in result.matches],
                "count": len(result.matches),
            },
        )
    else:
        logger.info("PII scan: clean", stage="pii")

    return result


def redact_query(query: str) -> str:
    """Redact PII from user query before sending to LLM."""
    result = scan_and_redact(query)
    if result.has_pii:
        logger.warning(
            f"query contains PII — redacted {len(result.matches)} items",
            stage="pii",
        )
    return result.redacted


def redact_chunks(chunks: list[str]) -> list[str]:
    """Redact PII from retrieved chunks before sending to LLM."""
    redacted = []
    for chunk in chunks:
        result = scan_and_redact(chunk)
        redacted.append(result.redacted)
    return redacted
