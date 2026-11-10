"""
Visual theme for the Streamlit dashboard.

Light canvas, white cards, navy typography, purple/blue gradient accents and soft
shadows. All custom components are plain HTML strings so they stay dependency free
and render identically in the browser and in screenshots.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Tuple

import streamlit as st

from .config import PALETTE

NAVY = PALETTE["navy"]
NAVY_SOFT = PALETTE["navy_soft"]
PURPLE = PALETTE["purple"]
BLUE = PALETTE["blue"]

_BASE_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {{
    --sga-bg: {PALETTE['background']};
    --sga-card: {PALETTE['card']};
    --sga-navy: {NAVY};
    --sga-navy-soft: {NAVY_SOFT};
    --sga-purple: {PURPLE};
    --sga-blue: {BLUE};
    --sga-border: #E6E9F2;
    --sga-radius: 18px;
    --sga-shadow: 0 6px 24px rgba(27, 37, 89, 0.07);
}}

html, body, [class*="st-"], .stApp, button, input, select, textarea {{
    font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
}}

.stApp {{ background: var(--sga-bg); }}
.block-container {{ padding-top: 2.0rem; padding-bottom: 3.0rem; max-width: 1480px; }}

h1, h2, h3, h4, h5 {{ color: var(--sga-navy); font-weight: 700; letter-spacing: -0.015em; }}
p, span, label, li {{ color: var(--sga-navy-soft); }}

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] {{
    background: #FFFFFF;
    border-right: 1px solid var(--sga-border);
}}
section[data-testid="stSidebar"] .block-container {{ padding-top: 1.4rem; }}
[data-testid="stSidebarNav"] a {{ border-radius: 10px; margin: 1px 6px; }}
[data-testid="stSidebarNav"] a span {{ color: var(--sga-navy) !important; font-weight: 600; font-size: 0.9rem; }}
[data-testid="stSidebarNav"] a:hover {{ background: #F7F5FC; }}
[data-testid="stSidebarNav"] a[aria-current="page"] {{ background: linear-gradient(90deg, rgba(105,84,217,0.14), rgba(59,130,246,0.10)); }}
[data-testid="stSidebarNav"] a[aria-current="page"] span {{ color: var(--sga-purple) !important; }}

/* ---------- Widgets ---------- */
.stButton > button, .stDownloadButton > button {{
    border-radius: 12px;
    border: 1px solid var(--sga-border);
    background: #FFFFFF;
    color: var(--sga-navy);
    font-weight: 600;
    box-shadow: 0 2px 6px rgba(27,37,89,0.04);
    transition: all .15s ease;
}}
.stButton > button:hover, .stDownloadButton > button:hover {{
    border-color: var(--sga-purple);
    color: var(--sga-purple);
    box-shadow: 0 4px 14px rgba(105,84,217,0.16);
}}
.stButton > button[kind="primary"],
.stButton > button[data-testid="stBaseButton-primary"] {{
    background: linear-gradient(135deg, {PURPLE}, {BLUE});
    color: #FFFFFF; border: none; box-shadow: 0 6px 18px rgba(105,84,217,0.26);
}}
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="stBaseButton-primary"]:hover {{
    color: #FFFFFF; opacity: 0.95; box-shadow: 0 8px 22px rgba(105,84,217,0.32);
}}
.stDownloadButton > button {{ background: linear-gradient(135deg, {PURPLE}, {BLUE}); color: #FFFFFF; border: none; }}
.stDownloadButton > button:hover {{ color: #FFFFFF; opacity: 0.94; box-shadow: 0 6px 18px rgba(59,130,246,0.28); }}

div[data-testid="stDataFrame"], div[data-testid="stTable"] {{
    border-radius: 14px;
    border: 1px solid var(--sga-border);
    box-shadow: var(--sga-shadow);
    overflow: hidden;
    background: #FFFFFF;
}}
[data-testid="stMetric"] {{
    background: #FFFFFF; border-radius: var(--sga-radius); padding: 18px 20px;
    border: 1px solid var(--sga-border); box-shadow: var(--sga-shadow);
}}
[data-testid="stMetricLabel"] {{ color: var(--sga-navy-soft); }}
[data-testid="stMetricValue"] {{ color: var(--sga-navy); font-weight: 700; }}

div[data-testid="stExpander"] {{
    background: #FFFFFF; border-radius: 14px; border: 1px solid var(--sga-border);
    box-shadow: var(--sga-shadow);
}}
div[data-testid="stExpander"] summary {{ color: var(--sga-navy); font-weight: 600; }}

.stTabs [data-baseweb="tab-list"] {{ gap: 6px; }}
.stTabs [data-baseweb="tab"] {{
    background: #FFFFFF; border-radius: 12px; padding: 8px 16px;
    border: 1px solid var(--sga-border); color: var(--sga-navy-soft); font-weight: 600;
}}
.stTabs [aria-selected="true"] {{
    background: linear-gradient(135deg, rgba(105,84,217,0.12), rgba(59,130,246,0.12));
    color: var(--sga-purple) !important; border-color: rgba(105,84,217,0.35);
}}

/* ---------- Custom components ---------- */
.sga-hero {{
    background: linear-gradient(120deg, #FFFFFF 0%, #FBFAFF 42%, #F3F6FF 100%);
    border: 1px solid var(--sga-border);
    border-radius: 22px;
    padding: 26px 30px;
    box-shadow: var(--sga-shadow);
    margin-bottom: 18px;
    position: relative;
    overflow: hidden;
}}
.sga-hero:before {{
    content: ""; position: absolute; top: 0; left: 0; height: 5px; width: 100%;
    background: linear-gradient(90deg, {PURPLE}, {BLUE});
}}
.sga-hero h1 {{ font-size: 1.72rem; margin: 0 0 6px 0; color: var(--sga-navy); }}
.sga-hero p {{ margin: 0; color: var(--sga-navy-soft); font-size: 0.94rem; line-height: 1.5; }}
.sga-eyebrow {{
    display: inline-block; font-size: 0.7rem; font-weight: 700; letter-spacing: 0.12em;
    text-transform: uppercase; color: var(--sga-purple); margin-bottom: 8px;
}}
.sga-kpi {{
    background: #FFFFFF; border: 1px solid var(--sga-border); border-radius: var(--sga-radius);
    padding: 16px 18px 14px 18px; box-shadow: var(--sga-shadow); height: 100%;
    position: relative; overflow: hidden;
}}
.sga-kpi:after {{
    content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
    background: linear-gradient(180deg, {PURPLE}, {BLUE});
}}
.sga-kpi .label {{
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.07em; text-transform: uppercase;
    color: #7A83A3; margin-bottom: 6px;
}}
.sga-kpi .value {{ font-size: 1.62rem; font-weight: 800; color: var(--sga-navy); line-height: 1.1; }}
.sga-kpi .sub {{ font-size: 0.76rem; color: var(--sga-navy-soft); margin-top: 4px; }}
.sga-card {{
    background: #FFFFFF; border: 1px solid var(--sga-border); border-radius: var(--sga-radius);
    padding: 18px 20px; box-shadow: var(--sga-shadow); margin-bottom: 14px;
}}
.sga-section-title {{ font-size: 1.12rem; font-weight: 700; color: var(--sga-navy); margin: 6px 0 2px 0; }}
.sga-section-sub {{ font-size: 0.85rem; color: var(--sga-navy-soft); margin-bottom: 12px; }}
.sga-notice {{
    border-radius: 14px; padding: 14px 18px; font-size: 0.88rem; line-height: 1.55;
    border: 1px solid rgba(245,158,11,0.35); background: rgba(245,158,11,0.08); color: #7A4A05;
}}
.sga-notice.info {{ border-color: rgba(59,130,246,0.3); background: rgba(59,130,246,0.07); color: #17418F; }}
.sga-notice.ok {{ border-color: rgba(20,184,166,0.3); background: rgba(20,184,166,0.08); color: #0B6B60; }}
.sga-notice.warn {{ border-color: rgba(244,63,94,0.3); background: rgba(244,63,94,0.07); color: #9F1239; }}
.sga-pill {{
    display: inline-block; padding: 3px 11px; border-radius: 999px; font-size: 0.72rem;
    font-weight: 700; letter-spacing: 0.03em;
}}
.sga-pill.purple {{ background: rgba(105,84,217,0.12); color: {PURPLE}; }}
.sga-pill.blue {{ background: rgba(59,130,246,0.12); color: {BLUE}; }}
.sga-pill.green {{ background: rgba(20,184,166,0.14); color: #0B6B60; }}
.sga-formula {{
    font-family: 'SFMono-Regular', ui-monospace, 'Courier New', monospace;
    background: #F7F8FD; border: 1px dashed #D9DEEF; border-radius: 10px;
    padding: 10px 14px; color: var(--sga-navy); font-size: 0.86rem;
}}
.sga-table-note {{ font-size: 0.78rem; color: #8A93AC; margin-top: 4px; }}
hr {{ border-color: var(--sga-border); }}
</style>
"""


def inject_css() -> None:
    """Inject the global stylesheet once per page render."""
    st.markdown(_BASE_CSS, unsafe_allow_html=True)


def hero(eyebrow: str, title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="sga-hero">
            <span class="sga-eyebrow">{eyebrow}</span>
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_row(items: Sequence[Tuple[str, str, str]]) -> None:
    """
    Render KPI cards in an even row.

    `items` is a sequence of (label, value, sub-caption).
    """
    columns = st.columns(len(items), gap="medium")
    for column, (label, value, sub) in zip(columns, items):
        with column:
            st.markdown(
                f"""
                <div class="sga-kpi">
                    <div class="label">{label}</div>
                    <div class="value">{value}</div>
                    <div class="sub">{sub}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def section_title(title: str, subtitle: str = "") -> None:
    st.markdown(
        f'<div class="sga-section-title">{title}</div>'
        + (f'<div class="sga-section-sub">{subtitle}</div>' if subtitle else ""),
        unsafe_allow_html=True,
    )


def notice(text: str, kind: str = "info") -> None:
    st.markdown(f'<div class="sga-notice {kind}">{text}</div>', unsafe_allow_html=True)


def pill(text: str, kind: str = "purple") -> str:
    return f'<span class="sga-pill {kind}">{text}</span>'


def formula(text: str) -> None:
    st.markdown(f'<div class="sga-formula">{text}</div>', unsafe_allow_html=True)


def card_open() -> None:
    st.markdown('<div class="sga-card">', unsafe_allow_html=True)


def card_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)
