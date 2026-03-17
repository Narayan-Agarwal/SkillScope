"""
Job Explorer page for SkillScope — browse companies, roles, and skill requirements.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import streamlit as st
import plotly.express as px

from analytics import (
    get_companies,
    get_roles_for_company,
    get_skills_for_role,
    get_aggregated_role_skills,
)

TIER_OPTIONS = ['All', 'Product', 'Indian IT', 'Startup', 'EdTech', 'Esports', 'Consulting']

# Color coding for skill consensus bars
FREQUENCY_COLORS = {
    'high': '#27AE60',    # green  — appears in >50% of companies
    'medium': '#F39C12',  # yellow — 25–50%
    'low': '#E74C3C',     # orange/red — <25%
}


def _get_theme_colors() -> dict:
    dark = st.session_state.get('dark_mode', True)
    if dark:
        return {'paper_bgcolor': '#0f1117', 'plot_bgcolor': '#0f1117', 'font_color': '#FAFAFA'}
    return {'paper_bgcolor': '#FFFFFF', 'plot_bgcolor': '#FFFFFF', 'font_color': '#1F3864'}


def _apply_theme(fig, theme: dict) -> None:
    fig.update_layout(
        paper_bgcolor=theme['paper_bgcolor'],
        plot_bgcolor=theme['plot_bgcolor'],
        font=dict(color=theme['font_color'], size=12),
        title_font=dict(size=14),
        margin=dict(l=60, r=30, t=50, b=60),
    )
    fig.update_xaxes(tickfont=dict(size=11), title_font=dict(size=12))
    fig.update_yaxes(tickfont=dict(size=11), title_font=dict(size=12))



def _render_company_cards(companies_df, page: int, per_page: int = 12) -> None:
    """Render a 3-column grid of company cards for the current page."""
    start = page * per_page
    end = start + per_page
    page_df = companies_df.iloc[start:end]

    cols = st.columns(3)
    for idx, (_, row) in enumerate(page_df.iterrows()):
        with cols[idx % 3]:
            tier_badge = f"🏷️ {row['tier']}"
            sector = row.get('industry_sector') or 'N/A'
            if st.button(
                f"**{row['company_name']}**\n{tier_badge} · {sector}",
                key=f"company_{row['company_id']}",
                use_container_width=True,
            ):
                st.session_state['selected_company_id'] = int(row['company_id'])
                st.session_state['selected_company_name'] = row['company_name']
                st.session_state['selected_role_id'] = None
                st.session_state['selected_role_title'] = None
                st.rerun()


def _render_role_tabs(conn, company_id: int, company_name: str) -> None:
    """Show roles for a company and allow drilling into skill details."""
    st.markdown(f"### 🏢 {company_name}")
    roles_df = get_roles_for_company(conn, company_id)

    if roles_df.empty:
        st.info('No roles found for this company.')
        return

    role_options = roles_df['role_title'].tolist()
    selected_role_title = st.selectbox('Select a Role', options=role_options, key='role_selector')

    if selected_role_title:
        role_row = roles_df[roles_df['role_title'] == selected_role_title].iloc[0]
        role_id = int(role_row['role_id'])
        exp = role_row.get('experience_level') or 'N/A'
        st.caption(f"Experience level: {exp}")
        _render_skill_chart(conn, role_id=role_id, role_title=selected_role_title, company_specific=True)


def _render_skill_chart(conn, role_id: int | None, role_title: str, company_specific: bool) -> None:
    """Render horizontal bar chart of skills for a role."""
    theme = _get_theme_colors()

    if company_specific and role_id is not None:
        df = get_skills_for_role(conn, role_id)
        if df.empty:
            st.info('No skills found for this role.')
            return
        # Count occurrences per skill (should be 1 each for a single role)
        df = df.groupby(['skill_name', 'skill_category']).size().reset_index(name='frequency')
        title = f'Skills Required — {role_title}'
    else:
        df = get_aggregated_role_skills(conn, role_title, limit=15)
        if df.empty:
            st.info('No aggregated skill data found for this role.')
            return
        title = f'Top 15 Skills Across All Companies — {role_title}'

    # Determine total companies for this role to compute consensus %
    try:
        total_companies_for_role = conn.execute(
            "SELECT COUNT(DISTINCT jr.company_id) FROM job_roles jr WHERE jr.role_title = ?",
            (role_title,)
        ).fetchone()[0] or 1
    except Exception:
        total_companies_for_role = 1

    # Assign color based on consensus frequency
    def _color(freq: int) -> str:
        pct = freq / total_companies_for_role * 100
        if pct > 50:
            return FREQUENCY_COLORS['high']
        if pct >= 25:
            return FREQUENCY_COLORS['medium']
        return FREQUENCY_COLORS['low']

    df = df.sort_values('frequency', ascending=True)
    colors = [_color(f) for f in df['frequency']]

    fig = px.bar(
        df,
        x='frequency',
        y='skill_name',
        orientation='h',
        height=max(350, len(df) * 28),
        title=title,
        labels={'frequency': 'Frequency', 'skill_name': 'Skill'},
        color='skill_category',
    )
    _apply_theme(fig, theme)
    st.plotly_chart(fig, use_container_width=True)

    # Legend for color coding
    st.caption(
        '🟢 High demand (>50% of companies)  '
        '🟡 Medium demand (25–50%)  '
        '🔴 Lower demand (<25%)'
    )

    if not company_specific:
        try:
            company_count = conn.execute(
                "SELECT COUNT(DISTINCT jr.company_id) "
                "FROM role_skills rs JOIN job_roles jr ON rs.role_id = jr.role_id "
                "WHERE jr.role_title = ?",
                (role_title,)
            ).fetchone()[0]
            st.info(f"Aggregated from **{company_count}** companies hiring for **{role_title}**.")
        except Exception:
            pass



def render(conn) -> None:
    st.title('🔍 Job Explorer')
    st.markdown('Browse companies, explore roles, and discover the skills they demand.')
    st.divider()

    # ---- Tier filter ----
    selected_tier_label = st.selectbox('Filter by Company Tier', options=TIER_OPTIONS)
    selected_tier = None if selected_tier_label == 'All' else selected_tier_label

    # ---- Load companies ----
    companies_df = get_companies(conn, tier=selected_tier)

    if companies_df.empty:
        st.info('No companies found for the selected tier.')
        return

    # ---- Pagination state ----
    if 'explorer_page' not in st.session_state:
        st.session_state['explorer_page'] = 0
    if 'selected_company_id' not in st.session_state:
        st.session_state['selected_company_id'] = None
    if 'selected_company_name' not in st.session_state:
        st.session_state['selected_company_name'] = None

    # Reset page when tier changes
    if st.session_state.get('_last_tier') != selected_tier_label:
        st.session_state['explorer_page'] = 0
        st.session_state['selected_company_id'] = None
        st.session_state['_last_tier'] = selected_tier_label

    per_page = 12
    total_pages = max(1, (len(companies_df) + per_page - 1) // per_page)
    current_page = st.session_state['explorer_page']

    # ---- Company cards grid ----
    st.subheader(f'Companies ({len(companies_df)} total)')
    _render_company_cards(companies_df, page=current_page, per_page=per_page)

    # ---- Pagination controls ----
    if total_pages > 1:
        pg_col1, pg_col2, pg_col3 = st.columns([1, 2, 1])
        with pg_col1:
            if st.button('← Previous', disabled=(current_page == 0)):
                st.session_state['explorer_page'] = current_page - 1
                st.rerun()
        with pg_col2:
            st.markdown(
                f"<div style='text-align:center'>Page {current_page + 1} of {total_pages}</div>",
                unsafe_allow_html=True,
            )
        with pg_col3:
            if st.button('Next →', disabled=(current_page >= total_pages - 1)):
                st.session_state['explorer_page'] = current_page + 1
                st.rerun()

    st.divider()

    # ---- Company detail view ----
    selected_id = st.session_state.get('selected_company_id')
    selected_name = st.session_state.get('selected_company_name')

    if selected_id is not None:
        _render_role_tabs(conn, company_id=selected_id, company_name=selected_name)
    else:
        # Cross-company aggregated view — pick a role
        st.subheader('Cross-Company Role Skill Aggregation')
        st.markdown('Select a role to see the top 15 skills demanded across all companies.')

        ROLE_OPTIONS = [
            'SDE', 'Data Scientist', 'ML Engineer', 'Data Engineer',
            'Frontend Engineer', 'Backend Engineer', 'Full Stack Engineer',
            'DevOps Engineer', 'Cloud Engineer', 'Product Manager',
            'Data Analyst', 'Security Engineer', 'QA Engineer',
            'Mobile Engineer', 'Other',
        ]
        agg_role = st.selectbox('Select Role', options=ROLE_OPTIONS, key='agg_role_selector')
        if agg_role:
            _render_skill_chart(conn, role_id=None, role_title=agg_role, company_specific=False)
