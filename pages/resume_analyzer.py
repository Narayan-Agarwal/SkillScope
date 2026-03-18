"""
Resume Analyzer page for SkillScope — upload a resume, paste a JD, get gap analysis.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import streamlit as st
import plotly.express as px
import pandas as pd

from resume_parser import extract_text
from skill_extractor import extract_skills
from analytics import compute_gap_analysis, get_gap_skill_frequencies


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


def _render_match_gauge(match_score: float) -> None:
    """Render a gauge chart for the match score."""
    theme = _get_theme_colors()
    fig = px.pie(
        values=[match_score, max(0, 100 - match_score)],
        names=['Match', 'Gap'],
        hole=0.7,
        color_discrete_sequence=['#27AE60', '#E74C3C'],
        title=f'Match Score: {match_score}%',
    )
    fig.update_traces(textinfo='none')
    fig.update_layout(
        showlegend=False,
        annotations=[dict(
            text=f'<b>{match_score}%</b>',
            x=0.5, y=0.5,
            font_size=28,
            showarrow=False,
            font_color=theme['font_color'],
        )],
        height=280,
        paper_bgcolor=theme['paper_bgcolor'],
        font=dict(color=theme['font_color']),
        margin=dict(l=20, r=20, t=50, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)



def _render_step1_upload() -> tuple[list[tuple[str, str]] | None, str | None]:
    """Step 1: PDF upload and skill extraction. Returns (skills, error_msg)."""
    st.subheader('Step 1 — Upload Your Resume')
    uploaded = st.file_uploader('Upload PDF resume (max 5 MB)', type=['pdf'], key='resume_upload')

    if uploaded is None:
        return None, None

    if uploaded.size > 5 * 1024 * 1024:
        return None, 'File size exceeds 5MB. Please upload a smaller file.'

    try:
        raw_bytes = uploaded.read()
        text = extract_text(raw_bytes)
    except ValueError as e:
        return None, f'Could not extract text from PDF: {e}'
    except Exception as e:
        return None, f'Unexpected error reading PDF: {e}'

    if not text or not text.strip():
        return None, 'The PDF appears to be empty or image-only. Please upload a text-based PDF.'

    skills = extract_skills(text)
    if not skills:
        return None, 'No recognized skills found in your resume. Try a different PDF.'

    return skills, None


def _render_skills_by_category(skills: list[tuple[str, str]]) -> None:
    """Display extracted skills grouped by category."""
    from collections import defaultdict
    by_cat: dict[str, list[str]] = defaultdict(list)
    for skill_name, category in skills:
        by_cat[category].append(skill_name)

    st.success(f'Found **{len(skills)}** skills in your resume.')
    cols = st.columns(2)
    for i, (cat, skill_list) in enumerate(sorted(by_cat.items())):
        with cols[i % 2]:
            st.markdown(f'**{cat}**')
            st.markdown(', '.join(sorted(skill_list)))


def _render_step2_jd() -> str | None:
    """Step 2: JD text area. Returns JD text or None if not submitted."""
    st.subheader('Step 2 — Paste Job Description')
    jd_text = st.text_area(
        'Paste the job description here',
        height=200,
        placeholder='Copy and paste the full job description…',
        key='jd_input',
    )
    if st.button('Analyze Gap', key='analyze_btn'):
        if not jd_text or not jd_text.strip():
            st.error('Job description cannot be empty.')
            return None
        return jd_text
    return None


def _render_step3_results(conn, resume_skills: list[tuple[str, str]], jd_text: str) -> None:
    """Step 3: Gap analysis results."""
    theme = _get_theme_colors()

    jd_skills_tuples = extract_skills(jd_text)
    resume_names = [s[0] for s in resume_skills]
    jd_names = [s[0] for s in jd_skills_tuples]

    result = compute_gap_analysis(resume_names, jd_names)

    st.subheader('Step 3 — Analysis Results')
    st.divider()

    # ---- Gauge + 4 panels ----
    gauge_col, panels_col = st.columns([1, 2])

    with gauge_col:
        _render_match_gauge(result['match_score'])

    with panels_col:
        p1, p2 = st.columns(2)
        with p1:
            st.metric('Skills Matched', len(result['matched_skills']))
            st.metric('Skills in JD', len(jd_names))
        with p2:
            st.metric('Skill Gaps', len(result['gap_skills']))
            st.metric('Skills in Resume', len(resume_names))

    st.divider()

    # ---- Matched skills ----
    if result['matched_skills']:
        with st.expander(f"✅ Matched Skills ({len(result['matched_skills'])})"):
            st.markdown(', '.join(sorted(result['matched_skills'])))

    # ---- Gap skills by category ----
    st.subheader('Missing Skills by Category')
    if not result['gap_skills']:
        st.success('No skill gaps detected — your resume covers all JD requirements.')
        return

    gaps_by_cat = result['gaps_by_category']
    for cat, skills in sorted(gaps_by_cat.items()):
        st.markdown(f'**{cat}** ({len(skills)} gaps)')
        st.markdown(', '.join(sorted(skills)))

    st.divider()

    # ---- Market frequency bar chart ----
    st.subheader('Gap Skills — Market Demand')
    df_freq = get_gap_skill_frequencies(conn, result['gap_skills'])

    if df_freq.empty:
        st.info('No market frequency data available for gap skills.')
    else:
        df_freq = df_freq.sort_values('frequency_count', ascending=True)
        fig_gap = px.bar(
            df_freq,
            x='frequency_count',
            y='skill_name',
            orientation='h',
            height=max(300, len(df_freq) * 28),
            color='skill_category',
            title='Gap Skills Ranked by Market Demand',
            labels={'frequency_count': 'Market Frequency', 'skill_name': 'Skill'},
            text='frequency_count',
        )
        _apply_theme(fig_gap, theme)
        fig_gap.update_traces(textposition='outside')
        st.plotly_chart(fig_gap, use_container_width=True)
        st.caption(
            'Market frequency shows how often each gap skill appears across all tracked '
            'company-role combinations. Prioritize high-frequency gaps.'
        )
        top_gap = df_freq.iloc[-1]  # highest after ascending sort
        st.markdown(
            f"**{top_gap['skill_name']}** is the most in-demand gap skill "
            f"with **{int(top_gap['frequency_count'])}** market occurrences."
        )



def render(conn) -> None:
    st.title('📄 Resume Analyzer')
    st.markdown('Upload your resume, paste a job description, and discover your skill gaps.')
    st.divider()

    # ---- Step 1: Upload ----
    skills, error = _render_step1_upload()

    if error:
        st.error(error)
        return

    if skills is None:
        st.info('Upload a PDF resume to get started.')
        return

    _render_skills_by_category(skills)
    st.divider()

    # ---- Step 2: JD input ----
    jd_text = _render_step2_jd()

    if jd_text is None:
        return

    # ---- Step 3: Results ----
    _render_step3_results(conn, resume_skills=skills, jd_text=jd_text)
