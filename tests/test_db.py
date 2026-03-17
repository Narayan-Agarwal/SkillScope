"""
Tests for src/db.py — schema creation, write operations, and property tests P10/P11.
"""
import sys
import os
import sqlite3
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from db import (
    create_schema,
    get_connection,
    insert_job_role,
    insert_role_skill,
    query,
    upsert_company,
    upsert_skill_frequency,
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
# Task 4.4 — Unit tests
# ---------------------------------------------------------------------------

def test_create_schema_creates_all_tables():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    table_names = {r["name"] for r in rows}
    assert "companies" in table_names
    assert "job_roles" in table_names
    assert "role_skills" in table_names
    assert "skill_frequency" in table_names


def test_upsert_company_returns_id():
    conn = make_conn()
    cid = upsert_company(conn, "Acme Corp", "Product", "Tech")
    assert cid > 0


def test_upsert_company_idempotent():
    conn = make_conn()
    cid1 = upsert_company(conn, "Acme Corp", "Product", "Tech")
    cid2 = upsert_company(conn, "Acme Corp", "Product", "Tech")
    assert cid1 == cid2


def test_insert_job_role():
    conn = make_conn()
    cid = upsert_company(conn, "Acme Corp", "Product", None)
    rid = insert_job_role(conn, cid, "SDE", "Mid")
    assert rid > 0


def test_insert_role_skill():
    conn = make_conn()
    cid = upsert_company(conn, "Acme Corp", "Product", None)
    rid = insert_job_role(conn, cid, "SDE", None)
    # Should not raise
    insert_role_skill(conn, rid, "Python", "Programming", "kaggle")


def test_query_returns_list_of_dicts():
    conn = make_conn()
    upsert_company(conn, "Acme Corp", "Product", "Tech")
    results = query(conn, "SELECT * FROM companies WHERE company_name = ?", ("Acme Corp",))
    assert isinstance(results, list)
    assert len(results) == 1
    assert isinstance(results[0], dict)
    assert results[0]["company_name"] == "Acme Corp"


# ---------------------------------------------------------------------------
# Task 4.5 — Property test P10: Frequency count increment invariant
# ---------------------------------------------------------------------------

# Feature: skillscope, Property 10: Frequency count increment invariant
@given(st.integers(min_value=1, max_value=50))
@settings(max_examples=50)
def test_frequency_count_increment_invariant(n):
    """Validates: Requirements 5.6"""
    conn = make_conn()
    skill = "Python"
    for _ in range(n):
        upsert_skill_frequency(conn, skill, "Programming")
    rows = query(conn, "SELECT frequency_count FROM skill_frequency WHERE skill_name = ?", (skill,))
    assert len(rows) == 1
    assert rows[0]["frequency_count"] == n


# ---------------------------------------------------------------------------
# Task 4.6 — Property test P11: ISO 8601 timestamp format
# ---------------------------------------------------------------------------

# Feature: skillscope, Property 11: ISO 8601 timestamp format
@given(st.integers(min_value=1, max_value=10))
@settings(max_examples=50)
def test_iso8601_timestamp_format(n):
    """Validates: Requirements 5.7"""
    conn = make_conn()
    skill = "JavaScript"
    for _ in range(n):
        upsert_skill_frequency(conn, skill, "Web")
    rows = query(conn, "SELECT last_updated FROM skill_frequency WHERE skill_name = ?", (skill,))
    assert len(rows) == 1
    # Must parse without raising
    datetime.fromisoformat(rows[0]["last_updated"])
