"""Tests for Vision reading-order reconstruction."""

from echo.adapters.ocr.reading_order import text_from_bounding_boxes


def _word(text: str, xmin: int) -> dict:
    return {
        "boundingBox": {
            "vertices": [
                {"x": xmin, "y": 0},
                {"x": xmin + 50, "y": 0},
                {"x": xmin + 50, "y": 20},
                {"x": xmin, "y": 20},
            ]
        },
        "symbols": [{"text": char} for char in text],
    }


class TestReadingOrder:
    def test_sorts_words_in_paragraph_left_to_right(self) -> None:
        annotation = {
            "pages": [
                {
                    "blocks": [
                        {
                            "paragraphs": [
                                {
                                    "words": [
                                        _word("world", xmin=80),
                                        _word("hello", xmin=10),
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        assert text_from_bounding_boxes(annotation) == "hello world"

    def test_preserves_paragraph_order_from_api(self) -> None:
        annotation = {
            "pages": [
                {
                    "blocks": [
                        {
                            "paragraphs": [
                                {"words": [_word("first", xmin=10)]},
                                {"words": [_word("second", xmin=10)]},
                            ]
                        }
                    ]
                }
            ]
        }

        assert text_from_bounding_boxes(annotation) == "first\nsecond"

    def test_falls_back_to_annotation_text_when_empty(self) -> None:
        assert text_from_bounding_boxes({"text": "fallback"}) == "fallback"
