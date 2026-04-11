"""Tests for strip_code_blocks utility (Task 5.7).

Validates Requirement 9.3:
- strip_code_blocks removes leading ```json or ``` fences and trailing ```
- Returns inner content stripped of whitespace
- Passes through content without fences unchanged
"""

from core.utils import strip_code_blocks


class TestStripCodeBlocks:
    """Requirement 9.3: strip_code_blocks handles various fence formats."""

    def test_strips_json_fence(self):
        """Content wrapped in ```json ... ``` should be unwrapped."""
        raw = '```json\n{"key": "value"}\n```'
        assert strip_code_blocks(raw) == '{"key": "value"}'

    def test_strips_plain_fence(self):
        """Content wrapped in ``` ... ``` (no language tag) should be unwrapped."""
        raw = '```\n{"key": "value"}\n```'
        assert strip_code_blocks(raw) == '{"key": "value"}'

    def test_no_fences_unchanged(self):
        """Content without fences should be returned as-is."""
        raw = '{"key": "value"}'
        assert strip_code_blocks(raw) == '{"key": "value"}'

    def test_multiline_json_content(self):
        """Multi-line JSON inside fences should be preserved."""
        raw = '```json\n{\n  "a": 1,\n  "b": 2\n}\n```'
        result = strip_code_blocks(raw)
        assert '"a": 1' in result
        assert '"b": 2' in result

    def test_strips_whitespace_around_content(self):
        """Leading/trailing whitespace inside fences should be stripped."""
        raw = '```json\n  {"a": 1}  \n```'
        assert strip_code_blocks(raw) == '{"a": 1}'

    def test_other_language_fence(self):
        """Fences with other language tags (e.g. ```python) should also be stripped."""
        raw = '```python\nprint("hello")\n```'
        assert strip_code_blocks(raw) == 'print("hello")'

    def test_empty_fenced_block(self):
        """An empty fenced block should return an empty string."""
        raw = '```json\n\n```'
        assert strip_code_blocks(raw) == ''

    def test_plain_text_not_starting_with_backticks(self):
        """Plain text that doesn't start with ``` should pass through."""
        raw = 'just some text'
        assert strip_code_blocks(raw) == 'just some text'
