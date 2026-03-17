"""
Dashboard page for SkillScope — Job Market Intelligence Platform.
Renders skill demand analytics, heatmap, tier comparison, and AI skills spotlight.
"""
from __future__ import annotations

import subprocess
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import streamlit as st
import plotly.express as px
import pandas as pd

from analytics import (
    get_top_skills,
    get_heatmap_data,
    get_tier_comparison,
    get_ai_skills,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ROLE_OPTIONS = [
    'All',
    'SDE', 'Data Scientist', 'ML Engineer', 'Data Engineer',
    'Frontend Engineer', 'Backend Engineer', 'Full Stack Engineer',
    'DevOps Engineer', 'Cloud Engineer', 'Product Manager',
    'Data Analyst', 'Security Engineer', 'QA Engineer',
    'Mobile Engineer', 'Other',
]

CATEGORY_OPTIONS = [
    'All',
    'Programming', 'Web', 'Data_and_ML', 'AI & GenAI',
    'Cloud_and_DevOps', 'Database', 'Tools_and_Practices',
    'Cybersecurity', 'Domain_Specific', 'Soft_Skills',
]

TIER_OPTIONS = ['All', 'Product', 'Indian IT', 'Startup', 'EdTech', 'Esports', 'Consulting']


# ---------------------------------------------------------------------------
# Theme helpers
# ---------------------------------------------------------------------------

def _get_theme_colors() -> dict:
    dark = st.session_state.get('dark_mode', True)
    if dark:
        return {
            'paper_bgcolor': '#0f1117',
            'plot_bgcolor': '#0f1117',
            'font_color': '#FAFAFA',
        }
    return {
        'paper_bgcolor': '#FFFFFF',
        'plot_bgcolor': '#FFFFFF',
        'font_color': '#1F3864',
    }


def _apply_theme(fig, theme: dict) -> None:
    """Apply consistent theme and font sizes to a Plotly figure."""
    fig.update_layout(
        paper_bgcolor=theme['paper_bgcolor'],
        plot_bgcolor=theme['plot_bgcolor'],
        font=dict(color=theme['font_color'], size=12),
        title_font=dict(size=14),
        margin=dict(l=60, r=30, t=50, b=60),
    )
    fig.update_xaxes(tickfont=dict(size=11), title_font=dict(size=12))
    fig.update_yaxes(tickfont=dict(size=11), title_font=dict(size=12))


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------

def render(conn) -> None:
    # ---- Header ----
    header_col, btn_col = st.columns([8, 1])
    with header_col:
        st.title('📊 Job Market Dashboard')
        st.markdown('Real-time skill demand intelligence across 91 companies and 15 job roles.')
    with btn_col:
        if st.button('🔄 Refresh Data'):
            with st.spinner('Refreshing data…'):
                subprocess.run(['python', 'src/seed_data.py'])
            st.success('Data refreshed successfully!')

    st.divider()

    # ---- Global Filter Bar ----
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1:
        selected_tier_label = st.selectbox('Filter by Company Tier', options=TIER_OPTIONS)
    with f_col2:
        selected_role_label = st.selectbox('Filter by Job Role', options=ROLE_OPTIONS)
    with f_col3:
        selected_category_label = st.selectbox('Filter by Skill Category', options=CATEGORY_OPTIONS)

    selected_tier = None if selected_tier_label == 'All' else selected_tier_label
    selected_role = None if selected_role_label == 'All' else selected_role_label
    selected_category = None if selected_category_label == 'All' else selected_category_label

    theme = _get_theme_colors()

    st.divider()

    # ---- Row 1: Summary Stat Cards ----
    m1, m2, m3, m4 = st.columns(4)

    try:
        total_companies = conn.execute('SELECT COUNT(*) FROM companies').fetchone()[0]
    except Exception:
        total_companies = 'N/A'

    try:
        total_skills = conn.execute('SELECT COUNT(*) FROM skill_frequency').fetchone()[0]
    except Exception:
        total_skills = 'N/A'

    try:
        row = conn.execute(
            'SELECT skill_name FROM skill_frequency ORDER BY frequency_count DESC LIMIT 1'
        ).fetchone()
        top_skill = row[0] if row else 'N/A'
    except Exception:
        top_skill = 'N/A'

    with m1:
        st.metric('Total Companies Tracked', total_companies)
    with m2:
        st.metric('Total Unique Skills', total_skills)
    with m3:
        st.metric('Total Job Roles Covered', 15)
    with m4:
        st.metric('Most Demanded Skill', top_skill)

    st.divider()

    # ---- Row 2: Top Skills Bar + Category Donut ----
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader('Top 20 Most In-Demand Skills')
        try:
            df_skills = get_top_skills(conn, limit=20, category=selected_category)
            if df_skills.empty:
                st.info('No skill data available. Please run the data pipeline.')
            else:
                fig_bar = px.bar(
                    df_skills,
                    x='frequency_count',
                    y='skill_name',
                    orientation='h',
                    height=450,
                    color_discrete_sequence=['#4F8EF7'],
                    title='Top 20 Most In-Demand Skills',
                    labels={
                        'frequency_count': 'Number of Company-Role Combinations',
                        'skill_name': 'Skill Name',
                    },
                )
                _apply_theme(fig_bar, theme)
                st.plotly_chart(fig_bar, use_container_width=True)
                st.caption(
                    'Counts how many unique company-role combinations require each skill, '
                    'based on job postings from 91 companies across 15 roles.'
                )
                top_row = df_skills.iloc[0]
                total_freq = df_skills['frequency_count'].sum()
                pct = round(top_row['frequency_count'] / total_freq * 100, 1) if total_freq else 0
                st.markdown(
                    f"**{top_row['skill_name']}** is the most demanded skill, "
                    f"appearing in **{pct}%** of all tracked skill occurrences."
                )
        except Exception:
            st.error('Data unavailable. Please try again.')

    with chart_col2:
        st.subheader('Skill Category Distribution')
        try:
            rows = conn.execute(
                'SELECT skill_category, SUM(frequency_count) as total '
                'FROM skill_frequency GROUP BY skill_category'
            ).fetchall()
            if not rows:
                st.info('No results found for the selected filters. Try adjusting your selection.')
            else:
                df_cat = pd.DataFrame([dict(r) for r in rows])
                fig_donut = px.pie(
                    df_cat,
                    values='total',
                    names='skill_category',
                    hole=0.5,
                    height=450,
                    title='Skill Demand by Category',
                )
                _apply_theme(fig_donut, theme)
                st.plotly_chart(fig_donut, use_container_width=True)
                st.caption(
                    'Distribution of total skill demand across all 10 skill categories, '
                    'weighted by frequency across all company-role combinations.'
                )
                top_cat = df_cat.loc[df_cat['total'].idxmax()]
                total_all = df_cat['total'].sum()
                cat_pct = round(top_cat['total'] / total_all * 100, 1) if total_all else 0
                st.markdown(
                    f"**{top_cat['skill_category']}** is the largest category, "
                    f"accounting for **{cat_pct}%** of total skill demand."
                )
        except Exception:
            st.error('Data unavailable. Please try again.')

    st.divider()

    # ---- Row 3: Role vs Skill Heatmap ----
    st.subheader('Role vs Skill Demand Heatmap')
    try:
        pivot_df = get_heatmap_data(conn, tier=selected_tier)
        if pivot_df.empty:
            st.info('No data available for the selected filters.')
        else:
            fig_heat = px.imshow(
                pivot_df,
                color_continuous_scale='RdYlGn',
                height=500,
                title='Role vs Skill Demand Heatmap',
                labels={'x': 'Skill Category', 'y': 'Job Role', 'color': 'Count'},
            )
            _apply_theme(fig_heat, theme)
            fig_heat.update_xaxes(title_text='Skill Category')
            fig_heat.update_yaxes(title_text='Job Role')
            st.plotly_chart(fig_heat, use_container_width=True)
            st.caption(
                'Heatmap showing how frequently each skill category appears across job roles. '
                'Darker green indicates higher demand.'
            )
            max_val = pivot_df.values.max()
            max_pos = pivot_df.stack().idxmax()
            st.markdown(
                f"**{max_pos[0]}** × **{max_pos[1]}** has the highest demand "
                f"with a count of **{int(max_val)}**."
            )
    except Exception:
        st.error('Data unavailable. Please try again.')

    st.divider()

    # ---- Row 4: Tier Comparison + AI Skills ----
    row4_col1, row4_col2 = st.columns(2)

    with row4_col1:
        st.subheader('Company Tier Skill Comparison')
        try:
            df_tier = get_tier_comparison(conn, highlight_tier=selected_tier)
            if df_tier.empty:
                st.info('No results found for the selected filters. Try adjusting your selection.')
            else:
                fig_tier = px.bar(
                    df_tier,
                    x='skill_name',
                    y='frequency',
                    color='tier',
                    barmode='group',
                    height=430,
                    title='Skill Demand by Company Tier',
                )
                _apply_theme(fig_tier, theme)
                fig_tier.update_xaxes(tickangle=-30)
                st.plotly_chart(fig_tier, use_container_width=True)
                st.caption(
                    'Compares the top skills demanded by each company tier, '
                    'revealing how skill priorities differ across industry segments.'
                )
                top_tier_row = df_tier.loc[df_tier['frequency'].idxmax()]
                st.markdown(
                    f"**{top_tier_row['tier']}** companies most frequently require "
                    f"**{top_tier_row['skill_name']}** (frequency: {int(top_tier_row['frequency'])})."
                )
        except Exception:
            st.error('Data unavailable. Please try again.')

    with row4_col2:
        st.subheader('AI & Emerging Skills Spotlight')
        try:
            df_ai = get_ai_skills(conn)
            if df_ai.empty:
                st.info('No results found for the selected filters. Try adjusting your selection.')
            else:
                fig_ai = px.bar(
                    df_ai,
                    x='skill_name',
                    y='frequency_count',
                    color_discrete_sequence=['#27AE60'],
                    height=430,
                    title='AI & Emerging Skills Demand',
                )
                _apply_theme(fig_ai, theme)
                fig_ai.update_xaxes(tickangle=-30)
                st.plotly_chart(fig_ai, use_container_width=True)
                st.caption(
                    'Demand for AI and generative AI skills across all tracked companies and roles, '
                    'highlighting the fastest-growing technology segment.'
                )
                top_ai = df_ai.iloc[0]
                st.markdown(
                    f"**{top_ai['skill_name']}** leads AI skill demand with "
                    f"**{int(top_ai['frequency_count'])}** occurrences."
                )
        except Exception:
            st.error('Data unavailable. Please try again.')
