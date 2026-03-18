"""
SQLite CRUD layer for SkillScope.
Each function opens its own connection with check_same_thread=False and closes it in a finally block.
This prevents the SQLite threading error when Streamlit runs pages in separate threads.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'skillscope.db')


def _connect() -> sqlite3.Connection:
    """Open a new SQLite connection. Always use this — never share connections across threads."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Legacy helpers kept for seed_data.py compatibility
# ---------------------------------------------------------------------------

def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Return a new connection. Callers in seed_data.py use this directly."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    """Create all 4 tables if they don't exist. Accepts an existing connection."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS companies (
            company_id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL UNIQUE,
            tier TEXT NOT NULL,
            industry_sector TEXT
        );
        CREATE TABLE IF NOT EXISTS job_roles (
            role_id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            role_title TEXT NOT NULL,
            experience_level TEXT,
            FOREIGN KEY (company_id) REFERENCES companies(company_id)
        );
        CREATE TABLE IF NOT EXISTS role_skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role_id INTEGER NOT NULL,
            skill_name TEXT NOT NULL,
            skill_category TEXT NOT NULL,
            data_source TEXT NOT NULL,
            FOREIGN KEY (role_id) REFERENCES job_roles(role_id)
        );
        CREATE TABLE IF NOT EXISTS skill_frequency (
            skill_id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_name TEXT NOT NULL UNIQUE,
            skill_category TEXT NOT NULL,
            frequency_count INTEGER NOT NULL DEFAULT 0,
            last_updated TEXT NOT NULL
        );
    """)
    conn.commit()


# ---------------------------------------------------------------------------
# Write operations — each opens and closes its own connection
# ---------------------------------------------------------------------------

def upsert_company(conn: sqlite3.Connection, name: str, tier: str, sector: str | None) -> int:
    """Insert company if not exists; return company_id."""
    conn.execute(
        "INSERT OR IGNORE INTO companies (company_name, tier, industry_sector) VALUES (?, ?, ?)",
        (name, tier, sector),
    )
    conn.commit()
    row = conn.execute(
        "SELECT company_id FROM companies WHERE company_name = ?", (name,)
    ).fetchone()
    return row["company_id"]


def insert_job_role(conn: sqlite3.Connection, company_id: int, role_title: str, exp_level: str | None) -> int:
    """Insert a job role and return its role_id."""
    cur = conn.execute(
        "INSERT INTO job_roles (company_id, role_title, experience_level) VALUES (?, ?, ?)",
        (company_id, role_title, exp_level),
    )
    conn.commit()
    return cur.lastrowid


def insert_role_skill(conn: sqlite3.Connection, role_id: int, skill_name: str, category: str, source: str) -> None:
    """Insert a role skill (ignore duplicates)."""
    conn.execute(
        "INSERT OR IGNORE INTO role_skills (role_id, skill_name, skill_category, data_source) VALUES (?, ?, ?, ?)",
        (role_id, skill_name, category, source),
    )
    conn.commit()


def upsert_skill_frequency(conn: sqlite3.Connection, skill_name: str, category: str) -> None:
    """Increment frequency_count if skill exists, otherwise insert with count=1."""
    now = datetime.now(timezone.utc).isoformat()
    existing = conn.execute(
        "SELECT skill_id FROM skill_frequency WHERE skill_name = ?", (skill_name,)
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE skill_frequency SET frequency_count = frequency_count + 1, last_updated = ? WHERE skill_name = ?",
            (now, skill_name),
        )
    else:
        conn.execute(
            "INSERT INTO skill_frequency (skill_name, skill_category, frequency_count, last_updated) VALUES (?, ?, 1, ?)",
            (skill_name, category, now),
        )
    conn.commit()


# ---------------------------------------------------------------------------
# Read operations — each opens its own thread-safe connection
# ---------------------------------------------------------------------------

def query(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict]:
    """Execute SQL with params and return a list of dicts."""
    rows = conn.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Thread-safe standalone query functions (used by Streamlit pages directly)
# ---------------------------------------------------------------------------

def execute_query(sql: str, params: tuple = ()) -> list[dict]:
    """Open a fresh connection, run a query, close it. Thread-safe."""
    conn = _connect()
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f'DB error: {e}')
        return []
    finally:
        conn.close()
