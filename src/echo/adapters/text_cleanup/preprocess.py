"""Deterministic preprocessing of fragmented OCR text."""

import re

_DATE_LINE = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}\s*$")


def split_by_date(text: str) -> list[str]:
    """
    Split OCR text into sections at date headers (e.g. 9/16/25).

    Each section is pre-joined: lines are concatenated in OCR order with spaces,
    preserving word sequence before any LLM pass.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []

    sections: list[str] = []
    current_date: str | None = None
    current_words: list[str] = []

    def flush() -> None:
        if current_date is None and not current_words:
            return
        parts: list[str] = []
        if current_date:
            parts.append(current_date)
        if current_words:
            parts.append(" ".join(current_words))
        sections.append("\n\n".join(parts))

    for line in lines:
        if _DATE_LINE.match(line):
            flush()
            current_date = line
            current_words = []
        else:
            current_words.append(line)

    flush()
    return sections


def join_lines(text: str) -> str:
    """Join all non-empty lines in order with spaces (no LLM)."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return " ".join(lines)
