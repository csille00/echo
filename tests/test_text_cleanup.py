"""Tests for OCR text cleanup preprocessing."""

from journal_search.adapters.text_cleanup.preprocess import join_lines, split_by_date


class TestSplitByDate:
    def test_splits_and_joins_lines_in_order(self) -> None:
        raw = "9/16/25\nToday\nwas\ngood\n9/17/25\nMore\ntext"
        sections = split_by_date(raw)
        assert len(sections) == 2
        assert sections[0] == "9/16/25\n\nToday was good"
        assert sections[1] == "9/17/25\n\nMore text"

    def test_single_section_without_date(self) -> None:
        raw = "Hello\nworld"
        assert split_by_date(raw) == ["Hello world"]


class TestJoinLines:
    def test_joins_in_order(self) -> None:
        assert join_lines("a\nb\nc") == "a b c"
