"""Rebuild OCR text from Vision's hierarchy, fixing word order within paragraphs."""

from __future__ import annotations

from typing import Any


def text_from_bounding_boxes(annotation: dict[str, Any]) -> str:
    """
    Reconstruct text using Vision's block/paragraph hierarchy.

    ``fullTextAnnotation.text`` inserts line breaks from ``DetectedBreak`` markers,
    which on handwriting often splits every word onto its own line.

    The accepted reconciliation is to walk the hierarchy in API order (Page → Block
    → Paragraph → Word) and only re-sort words within each paragraph by x-position.
    Block and paragraph order are left as Vision detected them.
    """
    lines: list[str] = []

    for page in annotation.get("pages", []):
        for block in page.get("blocks", []):
            for paragraph in block.get("paragraphs", []):
                words = sorted(
                    paragraph.get("words", []),
                    key=_word_x,
                )
                line = " ".join(_word_text(word) for word in words if _word_text(word))
                if line:
                    lines.append(line)

    if not lines:
        return annotation.get("text", "").strip()

    return "\n".join(lines).strip()


def _word_x(word: dict[str, Any]) -> float:
    vertices = word.get("boundingBox", {}).get("vertices", [])
    if not vertices:
        return 0.0
    return float(min(vertex.get("x", 0) for vertex in vertices))


def _word_text(word: dict[str, Any]) -> str:
    symbols = word.get("symbols", [])
    if symbols:
        return "".join(symbol.get("text", "") for symbol in symbols)
    return word.get("text", "")
