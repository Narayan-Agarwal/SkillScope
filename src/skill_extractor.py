"""
Skill extractor for SkillScope — keyword matching against the taxonomy.
"""
from __future__ import annotations

import re
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from skill_taxonomy import get_taxonomy


def _term_pattern(term: str) -> str:
    """Return a regex pattern string for a single term with appropriate boundaries.

    For terms that start/end with word characters (alphanumeric/_), use word boundary.
    For terms that start/end with non-word characters (e.g. C++, C#, F#),
    use a lookahead/lookbehind that asserts a non-alphanumeric boundary.
    """
    escaped = re.escape(term)

    # Determine left boundary
    if re.match(r"\w", term[0]):
        left = r"\b"
    else:
        left = r"(?<![A-Za-z0-9])"

    # Determine right boundary
    if re.match(r"\w", term[-1]):
        right = r"\b"
    else:
        right = r"(?![A-Za-z0-9])"

    return left + escaped + right


def _build_patterns(taxonomy: list[dict]) -> list[tuple[re.Pattern, str, str]]:
    """Build compiled regex patterns for each taxonomy entry.

    Returns a list of (pattern, skill_name, skill_category) tuples.
    Each pattern matches the canonical skill_name OR any of its aliases
    as whole words/phrases (word-boundary anchored, case-insensitive).
    """
    patterns = []
    for entry in taxonomy:
        skill_name = entry["skill_name"]
        skill_category = entry["skill_category"]
        aliases = entry.get("aliases", [])

        # Collect all terms: canonical name + aliases
        terms = [skill_name] + aliases

        # Build boundary-aware pattern for each term
        term_patterns = [_term_pattern(term) for term in terms]
        combined = "|".join(term_patterns)
        pattern = re.compile(combined, re.IGNORECASE)
        patterns.append((pattern, skill_name, skill_category))

    return patterns


# Build patterns once at module load time
_PATTERNS: list[tuple[re.Pattern, str, str]] = _build_patterns(get_taxonomy())


def extract_skills(text: str) -> list[tuple[str, str]]:
    """Extract skills from text using word-boundary regex matching.

    Args:
        text: Arbitrary text (job description, resume, etc.)

    Returns:
        Deduplicated list of (skill_name, skill_category) tuples.
        Each canonical skill_name appears at most once regardless of
        how many times it or its aliases appear in the text.
    """
    seen: set[str] = set()
    results: list[tuple[str, str]] = []

    for pattern, skill_name, skill_category in _PATTERNS:
        if skill_name in seen:
            continue
        if pattern.search(text):
            seen.add(skill_name)
            results.append((skill_name, skill_category))

    return results
