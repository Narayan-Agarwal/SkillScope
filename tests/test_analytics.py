"""
Tests for src/analytics.py — property tests P12–P14 and unit tests.
"""
import sys
import os
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from db import create_schema, upsert_company, insert_job_role, insert_role_skill, upsert_skill_frequency
from analytics import (
    get_companies,
    get_top_skills,
    get_ai_skills,
    get_aggregated_role_skills,
    get_gap_skill_frequencies,
    compute_gap_analysis,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_conn() -> sqlite3.Connection:
    """Return an in-memory connection with schema created."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    return conn


# ---------------------------------------------------------------------------
# Task 7.8 — Property test P12: Analytics filter correctness
# ---------------------------------------------------------------------------

# Feature: skillscope, Property 12: Analytics filter correctness
@given(st.sampled_from(["Product", "Indian IT", "Startup", "EdTech", "Esports", "Consulting"]))
@settings(max_examples=30)
def test_analytics_filter_correctness(tier):
    """Validates: Requirements 6.3, 7.3, 10.2

    For any tier filter value, every row returned by get_companies(conn, tier=T) must have tier==T.
    For any category filter, every row from get_top_skills(conn, category=C) must have skill_category==C.
    """
    conn = make_conn()

    # Insert companies of multiple tiers
    all_tiers = ["Product", "Indian IT", "Startup", "EdTech", "Esports", "Consulting"]
    for i, t in enumerate(all_tiers):
        upsert_company(conn, f"Company_{t}_{i}", t, "Tech")

    # Filter by the given tier — all returned rows must match
    df = get_companies(conn, tier=tier)
    assert len(df) > 0, f"Expected at least one company for tier={tier}"
    for _, row in df.iterrows():
        assert row["tier"] == tier, f"Expected tier={tier}, got {row['tier']}"

    # Insert skills of multiple categories and filter by one
    categories = ["Programming", "Web", "Data & ML", "AI & GenAI", "Cloud & DevOps"]
    for i, cat in enumerate(categories):
        upsert_skill_frequency(conn, f"Skill_{cat}_{i}", cat)

    target_cat = "Programming"
    df_skills = get_top_skills(conn, category=target_cat)
    assert len(df_skills) > 0
    for _, row in df_skills.iterrows():
        assert row["skill_category"] == target_cat


# ---------------------------------------------------------------------------
# Task 7.9 — Property test P13: AI skills category exclusivity
# ---------------------------------------------------------------------------

# Feature: skillscope, Property 13: AI skills category exclusivity
@given(st.integers(min_value=1, max_value=10))
@settings(max_examples=30)
def test_ai_skills_category_exclusivity(n):
    """Validates: Requirements 9.1

    get_ai_skills() must only return rows with skill_category == 'AI & GenAI'.
    """
    conn = make_conn()

    # Insert n AI skills
    for i in range(n):
        upsert_skill_frequency(conn, f"AI_Skill_{i}", "AI & GenAI")

    # Insert n non-AI skills
    for i in range(n):
        upsert_skill_frequency(conn, f"NonAI_Skill_{i}", "Programming")

    df = get_ai_skills(conn)
    assert len(df) == n, f"Expected {n} AI skills, got {len(df)}"
    for _, row in df.iterrows():
        assert row["skill_category"] == "AI & GenAI", (
            f"Expected 'AI & GenAI', got '{row['skill_category']}'"
        )


# ---------------------------------------------------------------------------
# Task 7.10 — Property test P14: Sorted analytics results
# ---------------------------------------------------------------------------

# Feature: skillscope, Property 14: Sorted analytics results
@given(st.integers(min_value=2, max_value=20))
@settings(max_examples=30)
def test_sorted_analytics_results(n):
    """Validates: Requirements 11.2, 14.2

    get_aggregated_role_skills and get_gap_skill_frequencies must return results
    sorted DESC by frequency.
    """
    conn = make_conn()

    # Set up a company and role
    cid = upsert_company(conn, "TestCo", "Product", None)
    rid = insert_job_role(conn, cid, "SDE", None)

    # Insert n skills with varying frequencies (skill_i appears i+1 times)
    skill_names = [f"Skill_{i}" for i in range(n)]
    for i, skill in enumerate(skill_names):
        for _ in range(i + 1):
            insert_role_skill(conn, rid, skill, "Programming", "kaggle")

    # Test get_aggregated_role_skills is sorted DESC
    df_agg = get_aggregated_role_skills(conn, "SDE", limit=n)
    assert len(df_agg) > 0
    freqs = df_agg["frequency"].tolist()
    assert freqs == sorted(freqs, reverse=True), f"Not sorted DESC: {freqs}"

    # Test get_gap_skill_frequencies is sorted DESC
    # Insert skills into skill_frequency with known counts
    conn2 = make_conn()
    for i, skill in enumerate(skill_names):
        for _ in range(i + 1):
            upsert_skill_frequency(conn2, skill, "Programming")

    df_gap = get_gap_skill_frequencies(conn2, skill_names)
    assert len(df_gap) == n
    counts = df_gap["frequency_count"].tolist()
    assert counts == sorted(counts, reverse=True), f"Not sorted DESC: {counts}"


# ---------------------------------------------------------------------------
# Task 7.11 — Unit test: gap skill frequencies returns correct counts
# ---------------------------------------------------------------------------

def test_gap_skill_frequencies_returns_correct_counts():
    """Insert known skills with known frequencies, verify returned counts match."""
    conn = make_conn()

    # Insert skills with specific frequencies
    skill_data = [
        ("Python", "Programming", 5),
        ("Docker", "Cloud & DevOps", 3),
        ("React", "Web", 7),
    ]
    for skill_name, category, count in skill_data:
        for _ in range(count):
            upsert_skill_frequency(conn, skill_name, category)

    skill_names = [s[0] for s in skill_data]
    df = get_gap_skill_frequencies(conn, skill_names)

    assert len(df) == 3
    # Build a lookup from result
    result_map = dict(zip(df["skill_name"], df["frequency_count"]))
    assert result_map["Python"] == 5
    assert result_map["Docker"] == 3
    assert result_map["React"] == 7


def test_gap_skill_frequencies_missing_skills_get_zero():
    """Skills not in DB should get frequency_count=0."""
    conn = make_conn()
    upsert_skill_frequency(conn, "Python", "Programming")

    df = get_gap_skill_frequencies(conn, ["Python", "UnknownSkill"])
    result_map = dict(zip(df["skill_name"], df["frequency_count"]))
    assert result_map["Python"] == 1
    assert result_map["UnknownSkill"] == 0


# ---------------------------------------------------------------------------
# Unit tests for compute_gap_analysis
# ---------------------------------------------------------------------------

def test_compute_gap_analysis_basic():
    """resume=[Python, SQL], jd=[Python, SQL, Docker] → gap=[Docker], score=66.7"""
    result = compute_gap_analysis(["Python", "SQL"], ["Python", "SQL", "Docker"])
    assert set(result["matched_skills"]) == {"Python", "SQL"}
    assert result["gap_skills"] == ["Docker"]
    assert result["match_score"] == 66.7


def test_compute_gap_analysis_perfect_match():
    """resume=jd → gap=[], score=100.0"""
    skills = ["Python", "SQL", "Docker"]
    result = compute_gap_analysis(skills, skills)
    assert result["gap_skills"] == []
    assert result["match_score"] == 100.0


def test_compute_gap_analysis_empty_jd():
    """jd=[] → score=0.0"""
    result = compute_gap_analysis(["Python", "SQL"], [])
    assert result["match_score"] == 0.0
    assert result["gap_skills"] == []
    assert result["matched_skills"] == []
