"""
Analytics query layer for SkillScope.
Returns DataFrames consumed by Streamlit pages.
"""
from __future__ import annotations

import sqlite3

import pandas as pd

from skill_taxonomy import get_taxonomy


# ---------------------------------------------------------------------------
# Taxonomy lookup for gaps_by_category
# ---------------------------------------------------------------------------

def _build_skill_category_map() -> dict[str, str]:
    """Return {skill_name_lower: skill_category} from taxonomy."""
    return {entry["skill_name"].lower(): entry["skill_category"] for entry in get_taxonomy()}


_SKILL_CATEGORY_MAP: dict[str, str] = _build_skill_category_map()


# ---------------------------------------------------------------------------
# Dashboard analytics
# ---------------------------------------------------------------------------

def get_top_skills(conn: sqlite3.Connection, limit: int = 20, category: str | None = None) -> pd.DataFrame:
    """Query skill_frequency, optional category filter, sorted by frequency_count DESC.

    Returns DataFrame with columns: skill_name, skill_category, frequency_count
    """
    if category is not None:
        sql = (
            "SELECT skill_name, skill_category, frequency_count "
            "FROM skill_frequency "
            "WHERE skill_category = ? "
            "ORDER BY frequency_count DESC "
            "LIMIT ?"
        )
        rows = conn.execute(sql, (category, limit)).fetchall()
    else:
        sql = (
            "SELECT skill_name, skill_category, frequency_count "
            "FROM skill_frequency "
            "ORDER BY frequency_count DESC "
            "LIMIT ?"
        )
        rows = conn.execute(sql, (limit,)).fetchall()

    if not rows:
        return pd.DataFrame(columns=["skill_name", "skill_category", "frequency_count"])
    return pd.DataFrame([dict(r) for r in rows])


def get_heatmap_data(conn: sqlite3.Connection, tier: str | None = None) -> pd.DataFrame:
    """Join role_skills, job_roles, companies; pivot rows=role_title, columns=skill_category.

    Optional tier filter on companies.tier.
    Returns pivoted DataFrame (may be empty).
    """
    if tier is not None:
        sql = (
            "SELECT jr.role_title, rs.skill_category "
            "FROM role_skills rs "
            "JOIN job_roles jr ON rs.role_id = jr.role_id "
            "JOIN companies c ON jr.company_id = c.company_id "
            "WHERE c.tier = ?"
        )
        rows = conn.execute(sql, (tier,)).fetchall()
    else:
        sql = (
            "SELECT jr.role_title, rs.skill_category "
            "FROM role_skills rs "
            "JOIN job_roles jr ON rs.role_id = jr.role_id "
            "JOIN companies c ON jr.company_id = c.company_id"
        )
        rows = conn.execute(sql).fetchall()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame([dict(r) for r in rows])
    pivot = df.groupby(["role_title", "skill_category"]).size().reset_index(name="count")
    return pivot.pivot(index="role_title", columns="skill_category", values="count").fillna(0)


def get_tier_comparison(conn: sqlite3.Connection, highlight_tier: str | None = None) -> pd.DataFrame:
    """Return top 10 skills per tier by frequency in role_skills joined to companies.

    highlight_tier is stored but used by the UI layer for opacity.
    Returns DataFrame with columns: tier, skill_name, frequency
    """
    sql = (
        "SELECT c.tier, rs.skill_name, COUNT(*) as frequency "
        "FROM role_skills rs "
        "JOIN job_roles jr ON rs.role_id = jr.role_id "
        "JOIN companies c ON jr.company_id = c.company_id "
        "GROUP BY c.tier, rs.skill_name "
        "ORDER BY c.tier, frequency DESC"
    )
    rows = conn.execute(sql).fetchall()

    if not rows:
        return pd.DataFrame(columns=["tier", "skill_name", "frequency"])

    df = pd.DataFrame([dict(r) for r in rows])
    # Keep top 10 per tier
    df = df.groupby("tier", group_keys=False).apply(lambda g: g.head(10)).reset_index(drop=True)
    return df


def get_ai_skills(conn: sqlite3.Connection) -> pd.DataFrame:
    """Filter skill_frequency WHERE skill_category = 'AI & GenAI'.

    Returns DataFrame sorted by frequency_count DESC.
    """
    sql = (
        "SELECT skill_name, skill_category, frequency_count "
        "FROM skill_frequency "
        "WHERE skill_category = 'AI & GenAI' "
        "ORDER BY frequency_count DESC"
    )
    rows = conn.execute(sql).fetchall()

    if not rows:
        return pd.DataFrame(columns=["skill_name", "skill_category", "frequency_count"])
    return pd.DataFrame([dict(r) for r in rows])


# ---------------------------------------------------------------------------
# Job Explorer analytics
# ---------------------------------------------------------------------------

def get_companies(conn: sqlite3.Connection, tier: str | None = None) -> pd.DataFrame:
    """Query companies table, optional tier filter.

    Returns DataFrame with columns: company_id, company_name, tier, industry_sector
    """
    if tier is not None:
        sql = (
            "SELECT company_id, company_name, tier, industry_sector "
            "FROM companies WHERE tier = ?"
        )
        rows = conn.execute(sql, (tier,)).fetchall()
    else:
        sql = "SELECT company_id, company_name, tier, industry_sector FROM companies"
        rows = conn.execute(sql).fetchall()

    if not rows:
        return pd.DataFrame(columns=["company_id", "company_name", "tier", "industry_sector"])
    return pd.DataFrame([dict(r) for r in rows])


def get_roles_for_company(conn: sqlite3.Connection, company_id: int) -> pd.DataFrame:
    """Query job_roles WHERE company_id = ?.

    Returns DataFrame with columns: role_id, role_title, experience_level
    """
    sql = (
        "SELECT role_id, role_title, experience_level "
        "FROM job_roles WHERE company_id = ?"
    )
    rows = conn.execute(sql, (company_id,)).fetchall()

    if not rows:
        return pd.DataFrame(columns=["role_id", "role_title", "experience_level"])
    return pd.DataFrame([dict(r) for r in rows])


def get_skills_for_role(conn: sqlite3.Connection, role_id: int) -> pd.DataFrame:
    """Query role_skills WHERE role_id = ?.

    Returns DataFrame with columns: skill_name, skill_category, data_source
    """
    sql = (
        "SELECT skill_name, skill_category, data_source "
        "FROM role_skills WHERE role_id = ?"
    )
    rows = conn.execute(sql, (role_id,)).fetchall()

    if not rows:
        return pd.DataFrame(columns=["skill_name", "skill_category", "data_source"])
    return pd.DataFrame([dict(r) for r in rows])


def get_aggregated_role_skills(conn: sqlite3.Connection, role_title: str, limit: int = 15) -> pd.DataFrame:
    """Join role_skills + job_roles WHERE role_title = ?, group by skill_name, sort DESC, limit.

    Returns DataFrame with columns: skill_name, skill_category, frequency
    """
    sql = (
        "SELECT rs.skill_name, rs.skill_category, COUNT(*) as frequency "
        "FROM role_skills rs "
        "JOIN job_roles jr ON rs.role_id = jr.role_id "
        "WHERE jr.role_title = ? "
        "GROUP BY rs.skill_name, rs.skill_category "
        "ORDER BY frequency DESC "
        "LIMIT ?"
    )
    rows = conn.execute(sql, (role_title, limit)).fetchall()

    if not rows:
        return pd.DataFrame(columns=["skill_name", "skill_category", "frequency"])
    return pd.DataFrame([dict(r) for r in rows])


# ---------------------------------------------------------------------------
# Resume Analyzer analytics
# ---------------------------------------------------------------------------

def get_gap_skill_frequencies(conn: sqlite3.Connection, skill_names: list[str]) -> pd.DataFrame:
    """Query skill_frequency for each skill in skill_names.

    Skills not found in DB get frequency_count=0.
    Returns DataFrame sorted by frequency_count DESC with columns: skill_name, skill_category, frequency_count
    """
    if not skill_names:
        return pd.DataFrame(columns=["skill_name", "skill_category", "frequency_count"])

    placeholders = ",".join("?" * len(skill_names))
    sql = (
        f"SELECT skill_name, skill_category, frequency_count "
        f"FROM skill_frequency "
        f"WHERE skill_name IN ({placeholders})"
    )
    rows = conn.execute(sql, skill_names).fetchall()
    found = {dict(r)["skill_name"]: dict(r) for r in rows}

    records = []
    for name in skill_names:
        if name in found:
            records.append(found[name])
        else:
            records.append({"skill_name": name, "skill_category": "", "frequency_count": 0})

    df = pd.DataFrame(records, columns=["skill_name", "skill_category", "frequency_count"])
    return df.sort_values("frequency_count", ascending=False).reset_index(drop=True)


def compute_gap_analysis(resume_skills: list[str], jd_skills: list[str]) -> dict:
    """Compute gap analysis between resume skills and JD skills.

    Args:
        resume_skills: list of skill_name strings from resume
        jd_skills: list of skill_name strings from job description

    Returns dict with:
        matched_skills: list[str] — skills in both
        gap_skills: list[str] — skills in jd but not in resume
        match_score: float — round((len(matched)/len(jd))*100, 1) if jd non-empty else 0.0
        gaps_by_category: dict[str, list[str]] — gap skills grouped by category
    """
    resume_set = set(resume_skills)
    jd_set = set(jd_skills)

    matched = sorted(resume_set & jd_set)
    gaps = sorted(jd_set - resume_set)

    if jd_skills:
        match_score = round((len(matched) / len(jd_set)) * 100, 1)
    else:
        match_score = 0.0

    gaps_by_category: dict[str, list[str]] = {}
    for skill in gaps:
        category = _SKILL_CATEGORY_MAP.get(skill.lower(), "Other")
        gaps_by_category.setdefault(category, []).append(skill)

    return {
        "matched_skills": matched,
        "gap_skills": gaps,
        "match_score": match_score,
        "gaps_by_category": gaps_by_category,
    }
