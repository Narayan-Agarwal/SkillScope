"""Unit tests for skill_taxonomy.py — taxonomy completeness (Task 2.3)."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from skill_taxonomy import get_taxonomy, get_keyword_set


REQUIRED_CATEGORIES = {
    "Programming",
    "Web",
    "Data & ML",
    "AI & GenAI",
    "Cloud & DevOps",
    "Database",
    "Tools & Practices",
    "Cybersecurity",
    "Domain Specific",
    "Soft Skills",
}


def test_taxonomy_has_at_least_250_skills():
    """Req 3.5, 16.1 — taxonomy must contain at least 250 unique skill entries."""
    assert len(get_taxonomy()) >= 250


def test_all_10_categories_represented():
    """Req 3.5, 16.1 — all 10 skill categories must be present."""
    categories = {entry["skill_category"] for entry in get_taxonomy()}
    assert REQUIRED_CATEGORIES == categories


def test_no_duplicate_skill_names():
    """Req 16.1 — every skill_name must be unique."""
    names = [entry["skill_name"] for entry in get_taxonomy()]
    assert len(names) == len(set(names))


def test_each_entry_has_required_keys():
    """Every taxonomy entry must have skill_name, skill_category, and aliases."""
    for entry in get_taxonomy():
        assert "skill_name" in entry
        assert "skill_category" in entry
        assert "aliases" in entry
        assert isinstance(entry["skill_name"], str) and entry["skill_name"]
        assert entry["skill_category"] in REQUIRED_CATEGORIES
        assert isinstance(entry["aliases"], list)


def test_keyword_set_contains_all_skill_names():
    """get_keyword_set() must include the lowercased canonical skill_name for every entry."""
    kw = get_keyword_set()
    for entry in get_taxonomy():
        assert entry["skill_name"].lower() in kw, (
            f"skill_name '{entry['skill_name']}' not found in keyword_set"
        )


def test_keyword_set_contains_all_aliases():
    """get_keyword_set() must include every alias (lowercased)."""
    kw = get_keyword_set()
    for entry in get_taxonomy():
        for alias in entry["aliases"]:
            assert alias.lower() in kw, (
                f"alias '{alias}' for skill '{entry['skill_name']}' not in keyword_set"
            )


def test_keyword_set_is_all_lowercase():
    """All keywords in get_keyword_set() must be lowercase strings."""
    for kw in get_keyword_set():
        assert kw == kw.lower(), f"keyword '{kw}' is not fully lowercase"


def test_keyword_set_non_empty():
    """get_keyword_set() must return a non-empty set."""
    assert len(get_keyword_set()) > 0
