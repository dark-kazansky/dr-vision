"""
Unit tests for Document Comparison (feat-065).

Tests: DocumentComparator (line/word/paragraph diff, similarity scoring,
normalization, statistics), API router.
"""

from components.document_comparator import (
    CompareResult,
    DiffChunk,
    DocumentComparator,
)


class TestIdenticalDocuments:
    def test_identical_texts(self):
        comparator = DocumentComparator()
        result = comparator.compare("Hello World", "Hello World")
        assert result.success is True
        assert result.is_identical is True
        assert result.similarity_score == 1.0

    def test_empty_texts(self):
        comparator = DocumentComparator()
        result = comparator.compare("", "")
        assert result.success is True
        assert result.is_identical is True
        assert result.similarity_score == 1.0

    def test_none_texts(self):
        comparator = DocumentComparator()
        result = comparator.compare(None, None)
        assert result.success is True
        assert result.is_identical is True


class TestLineDiff:
    def test_simple_addition(self):
        text_a = "line 1\nline 2"
        text_b = "line 1\nline 2\nline 3"
        comparator = DocumentComparator(mode="line")
        result = comparator.compare(text_a, text_b)
        assert result.success is True
        assert not result.is_identical
        assert len(result.additions) >= 1
        assert "line 3" in result.additions[0]

    def test_simple_deletion(self):
        text_a = "line 1\nline 2\nline 3"
        text_b = "line 1\nline 3"
        comparator = DocumentComparator(mode="line")
        result = comparator.compare(text_a, text_b)
        assert result.success is True
        assert len(result.deletions) >= 1
        assert "line 2" in result.deletions[0]

    def test_modification(self):
        text_a = "Hello World\nFoo Bar"
        text_b = "Hello World\nFoo Baz"
        comparator = DocumentComparator(mode="line")
        result = comparator.compare(text_a, text_b)
        assert result.success is True
        assert len(result.modifications) >= 1
        assert result.modifications[0]["original"] == "Foo Bar"
        assert result.modifications[0]["modified"] == "Foo Baz"

    def test_completely_different(self):
        text_a = "aaa\nbbb\nccc"
        text_b = "xxx\nyyy\nzzz"
        comparator = DocumentComparator(mode="line")
        result = comparator.compare(text_a, text_b)
        assert result.success is True
        assert result.similarity_score < 0.3


class TestWordDiff:
    def test_word_addition(self):
        text_a = "The quick fox"
        text_b = "The quick brown fox"
        comparator = DocumentComparator(mode="word")
        result = comparator.compare(text_a, text_b)
        assert result.success is True
        assert len(result.additions) >= 1
        assert "brown" in result.additions[0]

    def test_word_deletion(self):
        text_a = "Hello beautiful World"
        text_b = "Hello World"
        comparator = DocumentComparator(mode="word")
        result = comparator.compare(text_a, text_b)
        assert result.success is True
        assert len(result.deletions) >= 1
        assert "beautiful" in result.deletions[0]


class TestParagraphDiff:
    def test_paragraph_addition(self):
        text_a = "Paragraph one.\n\nParagraph two."
        text_b = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        comparator = DocumentComparator(mode="paragraph")
        result = comparator.compare(text_a, text_b)
        assert result.success is True
        assert len(result.additions) >= 1
        assert "three" in result.additions[0]


class TestSimilarityScore:
    def test_identical_score_one(self):
        comparator = DocumentComparator()
        result = comparator.compare("same text", "same text")
        assert result.similarity_score == 1.0

    def test_completely_different_low_score(self):
        comparator = DocumentComparator()
        result = comparator.compare("aaaa bbbb cccc", "xxxx yyyy zzzz")
        assert result.similarity_score < 0.3

    def test_partially_similar(self):
        comparator = DocumentComparator()
        result = comparator.compare(
            "The quick brown fox jumps over the lazy dog",
            "The quick brown cat jumps over the lazy dog",
        )
        assert 0.7 < result.similarity_score < 1.0

    def test_one_empty(self):
        comparator = DocumentComparator()
        result = comparator.compare("some text", "")
        assert result.similarity_score == 0.0


class TestNormalization:
    def test_ignore_whitespace(self):
        comparator = DocumentComparator(ignore_whitespace=True)
        result = comparator.compare("hello    world", "hello world")
        assert result.is_identical is True

    def test_ignore_case(self):
        comparator = DocumentComparator(ignore_case=True)
        result = comparator.compare("Hello World", "hello world")
        assert result.is_identical is True

    def test_both_options(self):
        comparator = DocumentComparator(ignore_whitespace=True, ignore_case=True)
        result = comparator.compare("  HELLO   World  ", "hello world")
        assert result.is_identical is True


class TestStatistics:
    def test_stats_populated(self):
        comparator = DocumentComparator()
        result = comparator.compare("Hello World", "Hello Earth")
        assert "document_a" in result.stats
        assert "document_b" in result.stats
        assert result.stats["document_a"]["words"] == 2
        assert result.stats["document_b"]["words"] == 2
        assert "total_changes" in result.stats

    def test_word_count_diff(self):
        comparator = DocumentComparator()
        result = comparator.compare("one two", "one two three four")
        assert result.stats["word_count_diff"] == 2


class TestUnifiedDiff:
    def test_unified_diff_generated(self):
        comparator = DocumentComparator()
        result = comparator.compare("line1\nline2\nline3", "line1\nmodified\nline3")
        assert result.unified_diff != ""
        assert "---" in result.unified_diff
        assert "+++" in result.unified_diff


class TestDiffChunk:
    def test_to_dict(self):
        chunk = DiffChunk(type="addition", content="new text", line_start=5, line_end=5)
        d = chunk.to_dict()
        assert d["type"] == "addition"
        assert d["content"] == "new text"
        assert d["line_start"] == 5

    def test_modification_has_original(self):
        chunk = DiffChunk(type="modification", content="new", original="old")
        d = chunk.to_dict()
        assert d["original"] == "old"


class TestCompareResult:
    def test_to_dict(self):
        result = CompareResult(
            success=True,
            similarity_score=0.85,
            is_identical=False,
            additions=["new line"],
            deletions=["old line"],
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["similarity_score"] == 0.85
        assert d["is_identical"] is False
        assert len(d["additions"]) == 1


class TestAPIRouter:
    def test_compare_router_exists(self):
        from api.v1.compare import router
        assert router is not None
        assert len(router.routes) >= 2  # /text and /files
