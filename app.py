"""
SkillScope — Job Market Intelligence Platform
Streamlit entry point: page config, sidebar nav, DB connection.
"""
from __future__ import annotations

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Page config — must be first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title='SkillScope',
    page_icon='🎯',
    layout='wide',
    initial_sidebar_state='expanded',
)

# ---------------------------------------------------------------------------
# Local imports (after sys.path setup)
# ---------------------------------------------------------------------------
from db import get_connection, create_schema  # noqa: E402
import pages.dashboard as dashboard  # noqa: E402
import pages.job_explorer as job_explorer  # noqa: E402
import pages.resume_analyzer as resume_analyzer  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_secret(key: str) -> str | None:
    """Read from st.secrets first, fall back to os.environ."""
    try:
        return st.secrets[key]
    except (KeyError, AttributeError, FileNotFoundError):
        return os.environ.get(key)


@st.cache_resource
def _get_conn():
    """Open DB connection once and cache for the session."""
    conn = get_connection()
    create_schema(conn)
    return conn


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------

PAGES = {
    '📊 Dashboard': 'dashboard',
    '🔍 Job Explorer': 'job_explorer',
    '📄 Resume Analyzer': 'resume_analyzer',
}

with st.sidebar:
    st.image('https://img.icons8.com/fluency/96/target.png', width=60)
    st.title('SkillScope')
    st.caption('Job Market Intelligence Platform')
    st.divider()

    selected_page = st.radio('Navigate', list(PAGES.keys()), label_visibility='collapsed')

    st.divider()

    # Dark / light theme toggle
    dark_mode = st.toggle('🌙 Dark Mode', value=st.session_state.get('dark_mode', True))
    st.session_state['dark_mode'] = dark_mode

    st.divider()
    st.caption('Data sourced from Kaggle & Adzuna')

# ---------------------------------------------------------------------------
# Render selected page
# ---------------------------------------------------------------------------

try:
    conn = _get_conn()
except Exception as exc:
    logging.exception('Failed to open DB connection')
    st.error(f'Database connection failed: {exc}')
    st.stop()

page_key = PAGES[selected_page]

try:
    if page_key == 'dashboard':
        dashboard.render(conn)
    elif page_key == 'job_explorer':
        job_explorer.render(conn)
    elif page_key == 'resume_analyzer':
        resume_analyzer.render(conn)
except Exception as exc:
    logging.exception('Page render error')
    st.error(f'An error occurred while loading the page: {exc}')
