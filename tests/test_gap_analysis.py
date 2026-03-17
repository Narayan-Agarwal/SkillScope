"""
Tests for compute_gap_analysis in src/analytics.py.
Property tests P15 and P16 + unit tests.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from hypothesis import given, settings
from hypothesis import strategies as st

from skill_taxonomy import get_taxonomy
from analytics import compute_gap_analysis


# ---------------------------------------------------------------------------
# Shared strategy: skill names from taxonomy
# ---------------------------------------------------------------------------

_SKILL_NAMES = [entry["skill_name"] for entry in get_taxonomy()]


# ---------------------------------------------------------------------------
# Task 10.2 — Property test P15: Gap analysis set difference
# ---------------------------------------------------------------------------

# Feature: skillscope, Property 15: Gap analysis set difference
@given(
    st.lists(st.sampled_from(_SKILL_NAMES), max_size=20),
    st.lists(st.sampled_from(_SKILL_NAMES), max_size=20),
)
@settings(max_examples=200)
def test_gap_analysis_set_difference(resume_skills, jd_skills):
    """Validates: Requirements 13.3

    For any resume_skills R and jd_skills J:
    - gap_skills == J - R (set difference)
    - No false positives: no skill in R appears in gap_skills
    - No false negatives: every skill in J-R appears in gap_skills
    """
    result = compute_gap_analysis(resume_skills, jd_skills)

    resume_set = set(resume_skills)
    jd_set = set(jd_skills)
    expected_gaps = jd_set - resume_set

    # gap_skills must equal the set difference J - R
    assert set(result["gap_skills"]) == expected_gaps, (
        f"Expected gaps={expected_gaps}, got {set(result['gap_skills'])}"
    )

    # No false positives: no gap skill should be in resume
    for skill in result["gap_skills"]:
        assert skill not in resume_set, (
            f"False positive: '{skill}' is in resume but listed as a gap"
        )

    # No false negatives: every skill in J-R must appear in gaps
    for skill in expected_gaps:
        assert skill in result["gap_skills"], (
            f"False negative: '{skill}' is in J-R but missing from gaps"
        )


# ---------------------------------------------------------------------------
# Task 10.3 — Property test P16: Match score formula
# ---------------------------------------------------------------------------

# Feature: skillscope, Property 16: Match score formula
@given(
    st.lists(st.sampled_from(_SKILL_NAMES), max_size=20),
    st.lists(st.sampled_from(_SKILL_NAMES), min_size=1, max_size=20),
)
@settings(max_examples=200)
def test_match_score_formula(resume_skills, jd_skills):
    """Validates: Requirements 13.5

    For any non-empty jd_skills J and resume_skills R:
    - match_score == round((len(R ∩ J) / len(J)) * 100, 1)
    - match_score is between 0.0 and 100.0 inclusive
    """
    result = compute_gap_analysis(resume_skills, jd_skills)

    resume_set = set(resume_skills)
    jd_set = set(jd_skills)
    matched = resume_set & jd_set

    expected_score = round((len(matched) / len(jd_set)) * 100, 1)

    assert result["match_score"] == expected_score, (
        f"Expected match_score={expected_score}, got {result['match_score']}"
    )
    assert 0.0 <= result["match_score"] <= 100.0, (
        f"match_score {result['match_score']} out of range [0.0, 100.0]"
    )


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def test_gap_analysis_basic():
    """resume=[Python, SQL], jd=[Python, SQL, Docker] → gap=[Docker], score=66.7"""
    result = compute_gap_analysis(["Python", "SQL"], ["Python", "SQL", "Docker"])
    assert set(result["matched_skills"]) == {"Python", "SQL"}
    assert result["gap_skills"] == ["Docker"]
    assert result["match_score"] == 66.7


def test_gap_analysis_perfect_match():
    """resume=jd → gap=[], score=100.0"""
    skills = ["Python", "SQL", "Docker"]
    result = compute_gap_analysis(skills, skills)
    assert result["gap_skills"] == []
    assert result["match_score"] == 100.0


def test_gap_analysis_empty_jd():
    """jd=[] → score=0.0, gap=[]"""
    result = compute_gap_analysis(["Python", "SQL"], [])
    assert result["match_score"] == 0.0
    assert result["gap_skills"] == []
    assert result["matched_skills"] == []


def test_gap_analysis_no_overlap():
    """resume=[Python], jd=[Docker] → gap=[Docker], score=0.0"""
    result = compute_gap_analysis(["Python"], ["Docker"])
    assert result["gap_skills"] == ["Docker"]
    assert result["match_score"] == 0.0
    assert result["matched_skills"] == []


def test_gaps_by_category_grouping():
    """Verify gaps_by_category groups gap skills by their taxonomy category."""
    # Docker → Cloud & DevOps, React → Web
    result = compute_gap_analysis(["Python"], ["Python", "Docker", "React"])
    gaps_by_cat = result["gaps_by_category"]

    assert "Cloud & DevOps" in gaps_by_cat
    assert "Docker" in gaps_by_cat["Cloud & DevOps"]

    assert "Web" in gaps_by_cat
    assert "React" in gaps_by_cat["Web"]

    # Python is matched, not a gap — should not appear in any category
    all_gap_skills = [s for skills in gaps_by_cat.values() for s in skills]
    assert "Python" not in all_gap_skills
