"""Property-based tests for document type splitting in the Splitter class.

Feature: dual-split-modes
Properties: 1, 2, 5
"""

import json

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from components.splitter import (
    ChunkCategory,
    DocumentTypeItem,
    Splitter,
)


# ---------------------------------------------------------------------------
# Shared strategies
# ---------------------------------------------------------------------------

# Category names: printable, non-empty, stripped
_category_name = (
    st.text(
        alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
        min_size=1,
        max_size=60,
    )
    .map(str.strip)
    .filter(lambda s: len(s) > 0)
    .filter(lambda s: s != "Unrecognized")
)

_chunk_category = st.builds(
    ChunkCategory,
    name=_category_name,
    description=st.text(min_size=0, max_size=100),
    order=st.integers(min_value=0, max_value=100),
)

_category_list = st.lists(_chunk_category, min_size=1, max_size=10).filter(
    lambda cats: len({c.name for c in cats}) == len(cats)  # unique names
)

_page_numbers = st.lists(
    st.integers(min_value=1, max_value=500), min_size=1, max_size=20
)

_confidence = st.one_of(
    st.none(),
    st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
)

# Unknown type names that are guaranteed NOT to be in any category list
_unknown_name = (
    st.text(
        alphabet=st.characters(whitelist_categories=("L", "N")),
        min_size=1,
        max_size=40,
    )
    .map(lambda s: f"__UNKNOWN__{s}")
)


# ===================================================================
# Property 1 – VLM response parsing with unrecognized handling
# ===================================================================


class TestVLMResponseParsingUnrecognizedHandling:
    """Feature: dual-split-modes, Property 1: VLM response parsing with unrecognized handling

    For any valid VLM JSON response containing document type objects and for any
    set of user-defined categories, parsing the response SHALL produce
    DocumentTypeItem objects where type names matching a user-defined category
    retain their original name, and type names not matching any category are
    grouped under "Unrecognized".

    **Validates: Requirements 4.3, 4.4**
    """

    @given(
        categories=_category_list,
        unknown_names=st.lists(_unknown_name, min_size=1, max_size=5),
        data=st.data(),
    )
    @settings(max_examples=100)
    def test_known_names_preserved_unknown_become_unrecognized(
        self, categories, unknown_names, data
    ):
        """Known category names are preserved; unknown names become 'Unrecognized'."""
        cat_names = [c.name for c in categories]

        # Build a VLM-style JSON response mixing known and unknown names
        items = []
        for name in cat_names:
            pages = data.draw(_page_numbers)
            conf = data.draw(_confidence)
            items.append(
                {"type_name": name, "page_numbers": pages, "confidence": conf}
            )
        for uname in unknown_names:
            # Ensure the unknown name is truly not in categories
            assume(uname not in cat_names)
            pages = data.draw(_page_numbers)
            conf = data.draw(_confidence)
            items.append(
                {"type_name": uname, "page_numbers": pages, "confidence": conf}
            )

        vlm_json = json.dumps(items)

        # We need a Splitter instance but _parse_doc_type_response doesn't use
        # self.agent, so we can pass a dummy.
        splitter = Splitter.__new__(Splitter)
        result = splitter._parse_doc_type_response(vlm_json, categories)

        assert result.success is True
        assert result.document_types is not None

        known_set = set(cat_names)
        for dt in result.document_types:
            if dt.type_name != "Unrecognized":
                assert dt.type_name in known_set, (
                    f"Non-Unrecognized name '{dt.type_name}' not in categories"
                )

        # All unknown entries should have been mapped to "Unrecognized"
        parsed_names = [dt.type_name for dt in result.document_types]
        # The first len(cat_names) items correspond to known names
        for i, name in enumerate(cat_names):
            assert parsed_names[i] == name
        for i in range(len(cat_names), len(parsed_names)):
            assert parsed_names[i] == "Unrecognized"


# ===================================================================
# Property 2 – Page assignment completeness validation
# ===================================================================


class TestPageAssignmentCompleteness:
    """Feature: dual-split-modes, Property 2: Page assignment completeness

    For any set of DocumentTypeItem objects and a known total page count,
    validation SHALL confirm that every page number from 1 to total_pages
    appears in exactly one DocumentTypeItem's page_numbers list — no gaps
    and no overlaps.

    **Validates: Requirements 4.5**
    """

    @given(total_pages=st.integers(min_value=1, max_value=200), data=st.data())
    @settings(max_examples=100)
    def test_complete_coverage_returns_true(self, total_pages, data):
        """A perfect partition of 1..total_pages validates as True."""
        pages = list(range(1, total_pages + 1))
        # Randomly partition pages into 1-5 groups
        num_groups = data.draw(st.integers(min_value=1, max_value=min(5, total_pages)))
        # Shuffle and split
        shuffled = data.draw(st.permutations(pages))
        groups: list[list[int]] = [[] for _ in range(num_groups)]
        for i, p in enumerate(shuffled):
            groups[i % num_groups].append(p)

        doc_types = [
            DocumentTypeItem(type_name=f"Type{i}", page_numbers=g)
            for i, g in enumerate(groups)
            if g  # skip empty groups
        ]

        assert Splitter.validate_page_coverage(doc_types, total_pages) is True

    @given(total_pages=st.integers(min_value=2, max_value=200), data=st.data())
    @settings(max_examples=100)
    def test_missing_page_returns_false(self, total_pages, data):
        """Removing a page from coverage causes validation to fail."""
        pages = list(range(1, total_pages + 1))
        # Remove one random page
        remove_idx = data.draw(st.integers(min_value=0, max_value=len(pages) - 1))
        pages.pop(remove_idx)

        doc_types = [DocumentTypeItem(type_name="All", page_numbers=pages)]
        assert Splitter.validate_page_coverage(doc_types, total_pages) is False

    @given(total_pages=st.integers(min_value=1, max_value=200), data=st.data())
    @settings(max_examples=100)
    def test_overlapping_pages_returns_false(self, total_pages, data):
        """Duplicating a page across groups causes validation to fail."""
        pages = list(range(1, total_pages + 1))
        # Pick a page to duplicate
        dup_page = data.draw(st.sampled_from(pages))

        doc_types = [
            DocumentTypeItem(type_name="Group1", page_numbers=pages),
            DocumentTypeItem(type_name="Group2", page_numbers=[dup_page]),
        ]
        assert Splitter.validate_page_coverage(doc_types, total_pages) is False


# ===================================================================
# Property 5 – Document type prompt contains all categories
# ===================================================================


class TestDocTypePromptContainsAllCategories:
    """Feature: dual-split-modes, Property 5: Document type prompt contains all categories

    For any non-empty list of ChunkCategory objects, the constructed doc-type
    VLM prompt SHALL contain every category name from the input list, and SHALL
    contain the word "Unrecognized" as the fallback type instruction.

    **Validates: Requirements 7.1, 7.4**
    """

    @given(categories=_category_list)
    @settings(max_examples=100)
    def test_prompt_contains_every_category_and_unrecognized(self, categories):
        """The prompt string includes every category name and 'Unrecognized'."""
        splitter = Splitter.__new__(Splitter)
        prompt = splitter._build_doc_type_prompt(categories)

        for cat in categories:
            assert cat.name in prompt, (
                f"Category '{cat.name}' not found in prompt"
            )

        assert "Unrecognized" in prompt, "'Unrecognized' not found in prompt"
