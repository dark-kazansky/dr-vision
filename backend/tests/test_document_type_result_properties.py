"""Property-based tests for DocumentTypeResult schema.

Feature: dual-split-modes
Property 6: DocumentTypeResult serialization round-trip

Validates: Requirements 8.1, 8.4
"""

import json

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from core.schemas import DocumentTypeResult


# --- Strategies ---

valid_type_name = st.text(min_size=1, max_size=100).filter(lambda s: len(s.strip()) > 0)

valid_page_numbers = st.lists(
    st.integers(min_value=1, max_value=10000),
    min_size=1,
    max_size=50,
)

valid_confidence = st.one_of(
    st.none(),
    st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
)

valid_document_type_result = st.builds(
    DocumentTypeResult,
    type_name=valid_type_name,
    page_numbers=valid_page_numbers,
    confidence=valid_confidence,
)

valid_document_type_result_list = st.lists(
    valid_document_type_result,
    min_size=0,
    max_size=20,
)


class TestDocumentTypeResultSerializationRoundTrip:
    """Feature: dual-split-modes, Property 6: DocumentTypeResult serialization round-trip

    Validates: Requirements 8.1, 8.4
    """

    @given(results=valid_document_type_result_list)
    @settings(max_examples=100)
    def test_round_trip_serialization(self, results):
        """Serializing to JSON and deserializing back produces equivalent objects."""
        # Serialize to JSON
        serialized = [r.model_dump() for r in results]
        json_str = json.dumps(serialized)

        # Deserialize back
        parsed = json.loads(json_str)
        deserialized = [DocumentTypeResult(**item) for item in parsed]

        # Verify equivalence
        assert len(deserialized) == len(results)
        for original, restored in zip(results, deserialized):
            assert restored.type_name == original.type_name
            assert restored.page_numbers == original.page_numbers
            assert restored.confidence == original.confidence

    @given(result=valid_document_type_result)
    @settings(max_examples=100)
    def test_single_round_trip(self, result):
        """A single DocumentTypeResult round-trips through JSON correctly."""
        json_str = result.model_dump_json()
        restored = DocumentTypeResult.model_validate_json(json_str)

        assert restored.type_name == result.type_name
        assert restored.page_numbers == result.page_numbers
        assert restored.confidence == result.confidence


class TestDocumentTypeResultValidation:
    """Feature: dual-split-modes, Property 6 supplement: DocumentTypeResult validation

    Validates: Requirements 8.1
    """

    @given(page_num=st.integers(max_value=0))
    @settings(max_examples=100)
    def test_rejects_negative_or_zero_page_numbers(self, page_num):
        """Pydantic rejects page numbers that are <= 0."""
        with pytest.raises(ValidationError):
            DocumentTypeResult(
                type_name="Valid",
                page_numbers=[page_num],
            )

    @given(confidence=st.floats(min_value=1.001, max_value=1e10, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_rejects_confidence_above_one(self, confidence):
        """Pydantic rejects confidence values > 1.0."""
        with pytest.raises(ValidationError):
            DocumentTypeResult(
                type_name="Valid",
                page_numbers=[1],
                confidence=confidence,
            )

    @given(confidence=st.floats(max_value=-0.001, allow_nan=False, allow_infinity=False))
    @settings(max_examples=100)
    def test_rejects_negative_confidence(self, confidence):
        """Pydantic rejects confidence values < 0.0."""
        with pytest.raises(ValidationError):
            DocumentTypeResult(
                type_name="Valid",
                page_numbers=[1],
                confidence=confidence,
            )

    @settings(max_examples=100)
    @given(data=st.data())
    def test_rejects_empty_type_name(self, data):
        """Pydantic rejects empty type_name."""
        with pytest.raises(ValidationError):
            DocumentTypeResult(
                type_name="",
                page_numbers=[1],
            )

    def test_rejects_empty_page_numbers_list(self):
        """Pydantic rejects empty page_numbers list."""
        with pytest.raises(ValidationError):
            DocumentTypeResult(
                type_name="Valid",
                page_numbers=[],
            )
