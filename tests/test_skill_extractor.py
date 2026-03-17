"""
Tests for skill_extractor.py — Properties P5, P6, P7, P8, P17 + unit tests.
"""
import sys
import os

# Add workspace root and src/ to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hypothesis import given, settings, strategies as st
from hypothesis.strategies import sampled_from

from skill_taxonomy import get_taxonomy
from skill_extractor import extract_skills


# ── Helpers ──────────────────────────────────────────────────────────────────

def _taxonomy_lookup() -> dict[str, dict]:
    """Return a dict keyed by skill_name for fast lookup."""
    return {entry["skill_name"]: entry for entry in get_taxonomy()}


def _entries_with_aliases() -> list[dict]:
    """Return taxonomy entries that have at least one alias."""
    return [e for e in get_taxonomy() if e.get("aliases")]


# ── Property Tests ────────────────────────────────────────────────────────────

# Feature: skillscope, Property 5: Case-insensitive skill matching
@given(
    entry=sampled_from(get_taxonomy()),
    casing=sampled_from(["upper", "lower", "title"]),
)
@settings(max_examples=100)
def test_case_insensitive_matching(entry, casing):
    """P5 — Any casing variant of a skill keyword must return that skill.

    Validates: Requirements 3.1, 16.2
    """
    skill_name = entry["skill_name"]

    if casing == "upper":
        text = skill_name.upper()
    elif casing == "lower":
        text = skill_name.lower()
    else:
        text = skill_name.title()

    results = extract_skills(text)
    skill_names_found = [r[0] for r in results]
    assert skill_name in skill_names_found, (
        f"Expected '{skill_name}' in results for text '{text}', got {skill_names_found}"
    )


# Feature: skillscope, Property 6: Skill category correctness
@given(text=st.text())
@settings(max_examples=100)
def test_skill_category_correctness(text):
    """P6 — Every returned skill_category must match the taxonomy exactly.

    Validates: Requirements 3.2
    """
    lookup = _taxonomy_lookup()
    results = extract_skills(text)
    for skill_name, skill_category in results:
        assert skill_name in lookup, f"Returned unknown skill_name: '{skill_name}'"
        expected_category = lookup[skill_name]["skill_category"]
        assert skill_category == expected_category, (
            f"Category mismatch for '{skill_name}': "
            f"got '{skill_category}', expected '{expected_category}'"
        )


# Feature: skillscope, Property 7: Skill extraction return type
@given(text=st.text())
@settings(max_examples=100)
def test_skill_extraction_return_type(text):
    """P7 — extract_skills always returns a list of (str, str) tuples.

    Validates: Requirements 3.4
    """
    results = extract_skills(text)
    assert isinstance(results, list), f"Expected list, got {type(results)}"
    for item in results:
        assert isinstance(item, tuple), f"Expected tuple element, got {type(item)}: {item}"
        assert len(item) == 2, f"Expected 2-tuple, got length {len(item)}: {item}"
        skill_name, skill_category = item
        assert isinstance(skill_name, str), f"skill_name must be str, got {type(skill_name)}"
        assert isinstance(skill_category, str), (
            f"skill_category must be str, got {type(skill_category)}"
        )


# Feature: skillscope, Property 8: Skill deduplication per record
@given(text=st.text())
@settings(max_examples=100)
def test_skill_deduplication(text):
    """P8 — No skill_name appears more than once in the output.

    Validates: Requirements 3.3, 16.4
    """
    results = extract_skills(text)
    skill_names = [r[0] for r in results]
    assert len(skill_names) == len(set(skill_names)), (
        f"Duplicate skill_names found in results: {skill_names}"
    )


# Feature: skillscope, Property 17: Taxonomy alias round-trip
@given(entry=sampled_from(_entries_with_aliases()))
@settings(max_examples=100)
def test_taxonomy_alias_roundtrip(entry):
    """P17 — Text containing only an alias returns the canonical skill_name.

    Validates: Requirements 16.2, 16.3
    """
    skill_name = entry["skill_name"]
    skill_category = entry["skill_category"]

    for alias in entry["aliases"]:
        text = alias
        results = extract_skills(text)
        skill_names_found = [r[0] for r in results]
        assert skill_name in skill_names_found, (
            f"Alias '{alias}' did not return canonical skill '{skill_name}'. "
            f"Got: {skill_names_found}"
        )
        # Verify the canonical name is returned, not the alias itself
        # (unless alias == skill_name, which is allowed)
        for found_name, found_cat in results:
            if found_name == skill_name:
                assert found_cat == skill_category, (
                    f"Wrong category for '{skill_name}': got '{found_cat}', "
                    f"expected '{skill_category}'"
                )


# ── Unit Tests ────────────────────────────────────────────────────────────────

def test_extracts_python_from_text():
    """Concrete example: Python and SQL are extracted from a simple sentence."""
    text = "We need Python and SQL skills"
    results = extract_skills(text)
    skill_names = [r[0] for r in results]
    assert "Python" in skill_names, f"Expected 'Python' in {skill_names}"
    assert "SQL" in skill_names, f"Expected 'SQL' in {skill_names}"


def test_no_partial_match():
    """Word-boundary matching: 'JavaScript' must not cause 'Java' to match."""
    text = "JavaScript developer"
    results = extract_skills(text)
    skill_names = [r[0] for r in results]
    assert "JavaScript" in skill_names, f"Expected 'JavaScript' in {skill_names}"
    assert "Java" not in skill_names, (
        f"'Java' should NOT match inside 'JavaScript', but got {skill_names}"
    )


def test_empty_text():
    """Empty string input returns an empty list."""
    assert extract_skills("") == []


def test_alias_match():
    """Alias 'JS' should return canonical skill 'JavaScript', not 'JS'."""
    text = "We use JS for frontend development"
    results = extract_skills(text)
    skill_names = [r[0] for r in results]
    assert "JavaScript" in skill_names, (
        f"Expected canonical 'JavaScript' from alias 'JS', got {skill_names}"
    )
    assert "JS" not in skill_names, (
        f"Alias 'JS' should not appear in results, got {skill_names}"
    )
