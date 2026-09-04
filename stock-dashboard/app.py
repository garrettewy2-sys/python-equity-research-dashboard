import logging
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

from dcf_model import (
    equity_scenario_assumptions,
    estimate_defaults,
    estimate_equity_dcf_defaults,
    run_dcf,
    run_equity_dcf,
    scenario_assumptions,
    solve_implied_year_one_growth,
)
from dcf_v2 import (
    build_v2_defaults,
    framework_for,
    run_v2_case,
    scenario_inputs,
    solve_v2_assumption,
)
from dashboard_utils import (
    align_price_series,
    debt_to_equity_ratio,
    dividend_yield_percent,
    equal_weight_index,
    format_price,
    risk_statistics,
    statement_value,
    valuation_share_count,
    valuation_share_count_details,
)


logger = logging.getLogger(__name__)
 
# =============================================================
# PAGE SETUP
# =============================================================
st.set_page_config(
    page_title="Equity Research Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="auto",
)
 
# ---- Color tokens (used in Python logic / Plotly / SVG) ----
BG_DEEP   = "#f7f9fc"
CARD      = "#ffffff"
BORDER    = "#dfe5ed"
BLUE      = "#1769e0"
BLUE_LT   = "#2f7df4"
BLUE_DARK = "#0b5bd3"
TEXT      = "#13213d"
MUTED     = "#687892"
GREEN     = "#0f9f6e"
RED       = "#dc2626"
ORANGE    = "#64748b"
PURPLE    = "#2563eb"
 
# =============================================================
# GLOBAL CSS
# =============================================================
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
 
    html, body, [class*="css"], .stApp, [data-testid="stSidebar"] {
        font-family: 'Inter', -apple-system, sans-serif;
    }
 
    .stApp {
        background: linear-gradient(180deg, #07111f 0%, #0a1628 100%);
        background-attachment: fixed;
        color: #e5eefc;
    }
    [data-testid="stHeader"] { background: transparent; }
    .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1500px; }
 
    h1, h2, h3, h4 { color: #f8fafc !important; font-weight: 800 !important; letter-spacing: -0.4px; }
    p, span, label, li { color: #e5eefc; }
    .small-muted { color: #94a3b8; font-size: 14.5px; line-height: 1.55; }
 
    /* ---------- Page header bar ---------- */
    .page-head { display:flex; align-items:baseline; justify-content:space-between;
                 gap:6px 18px; flex-wrap:wrap; margin: 2px 0 18px 0; }
    .page-head .title { font-size: 28px; font-weight: 900; color:#f8fafc; line-height:1.25; }
    .page-head .sub { color:#94a3b8; font-size: 14px; }
 
    /* ---------- Summary cards ---------- */
    .sum-card {
        background:#0f1b2d; border:1px solid rgba(255,255,255,0.08);
        border-radius:16px; padding:18px 20px;
        box-shadow:0 10px 30px rgba(0,0,0,0.25); height:100%;
        transition: transform .15s ease, border-color .15s ease;
    }
    .sum-card:hover { transform: translateY(-3px); border-color: rgba(96,165,250,0.4); }
    .sum-card .label { color:#94a3b8; font-size:12px; font-weight:600; text-transform:uppercase; letter-spacing:0.6px; }
    .sum-card .row { display:flex; align-items:flex-end; justify-content:space-between; margin-top:10px; gap:10px; }
    .sum-card .value { color:#f8fafc; font-size:26px; font-weight:800; line-height:1.05; }
    .sum-card .value.sm { font-size:19px; }
    .sum-card .spark { flex:0 0 auto; opacity:0.95; }
    .sum-card .sub { font-size:13px; font-weight:600; margin-top:8px; }
    .pos { color:#22c55e; } .neg { color:#ef4444; } .neutral { color:#94a3b8; }
 
    /* ---------- Generic panel / card ---------- */
    .panel {
        background:#0f1b2d; border:1px solid rgba(255,255,255,0.08);
        border-radius:18px; padding:20px 22px;
        box-shadow:0 10px 30px rgba(0,0,0,0.25); margin-bottom:6px;
    }
    .panel h4 { margin:0 0 10px 0; font-size:17px; }
    .panel .small-muted { margin:0; }
 
    /* st.container(border=True) -> make it a dark panel too */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background:#0f1b2d; border:1px solid rgba(255,255,255,0.08) !important;
        border-radius:18px; box-shadow:0 10px 30px rgba(0,0,0,0.25);
    }
 
    .thesis-box {
        background: linear-gradient(135deg, rgba(59,130,246,0.10) 0%, #0f1b2d 60%);
        color:#e5eefc; padding:18px 20px; border-radius:16px;
        border:1px solid rgba(255,255,255,0.08); border-left:5px solid #3b82f6;
        font-size:15px; line-height:1.65; box-shadow:0 10px 30px rgba(0,0,0,0.25);
    }
 
    /* ---------- Stat grid (fundamentals / valuation) ---------- */
    .stat-grid { display:grid; grid-template-columns: repeat(3, 1fr); gap:12px; }
    .stat {
        background:#0c1626; border:1px solid rgba(255,255,255,0.07);
        border-radius:12px; padding:12px 14px;
    }
    .stat .k { color:#94a3b8; font-size:11.5px; font-weight:600; text-transform:uppercase; letter-spacing:0.4px; }
    .stat .v { color:#f8fafc; font-size:18px; font-weight:800; margin-top:3px; }

    /* ---------- DCF model ---------- */
    .dcf-preview-head {
        display:flex; align-items:baseline; justify-content:space-between; gap:10px;
        margin:20px 0 10px 0; flex-wrap:wrap;
    }
    .dcf-preview-head .t { color:#f8fafc; font-size:20px; font-weight:800; }
    .dcf-preview-head .b {
        color:#86efac; background:rgba(34,197,94,0.10); border:1px solid rgba(34,197,94,0.25);
        border-radius:999px; padding:4px 9px; font-size:11px; font-weight:700; letter-spacing:0.4px;
    }
    .dcf-result-grid { display:grid; grid-template-columns:repeat(4, 1fr); gap:12px; margin-bottom:12px; }
    .dcf-result {
        background:#0f1b2d; border:1px solid rgba(255,255,255,0.08);
        border-radius:14px; padding:16px 18px;
    }
    .dcf-result .k { color:#94a3b8; font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.45px; }
    .dcf-result .v { color:#f8fafc; font-size:23px; font-weight:800; margin-top:5px; }
    .dcf-result .v.pos { color:#22c55e; }
    .dcf-result .v.neg { color:#ef4444; }
    .dcf-assumption-grid { display:grid; grid-template-columns:1fr 1fr; gap:9px; }
    .dcf-assumption {
        background:#0c1626; border:1px solid rgba(255,255,255,0.07);
        border-radius:10px; padding:10px 12px;
    }
    .dcf-assumption .k { color:#94a3b8; font-size:11px; }
    .dcf-assumption .v { color:#e5eefc; font-size:15px; font-weight:700; margin-top:3px; }
    .dcf-mini-note { color:#94a3b8; font-size:12px; line-height:1.5; margin-top:10px; }
    .dcf-reverse {
        background:#0c1626; border-radius:12px; padding:14px 16px; margin-top:10px;
    }
    .dcf-reverse .k { color:#94a3b8; font-size:11px; text-transform:uppercase; letter-spacing:0.45px; }
    .dcf-reverse .v { color:#f8fafc; font-size:18px; font-weight:800; margin-top:4px; }
    .dcf-source {
        display:flex; justify-content:space-between; gap:10px; align-items:center;
        padding:8px 0; border-bottom:1px solid rgba(255,255,255,0.06); font-size:13px;
    }
    .dcf-source:last-child { border-bottom:0; }
    .dcf-source .k { color:#94a3b8; }
    .dcf-source .v { color:#e5eefc; font-weight:700; text-align:right; }
 
    /* ---------- Watchlist table ---------- */
    .wl { width:100%; border-collapse:collapse; }
    .wl th { color:#94a3b8; font-size:11.5px; font-weight:600; text-transform:uppercase;
             text-align:right; padding:8px 6px; border-bottom:1px solid rgba(255,255,255,0.08); }
    .wl th:first-child { text-align:left; }
    .wl td { font-size:13.5px; padding:9px 6px; text-align:right; border-bottom:1px solid rgba(255,255,255,0.05); }
    .wl td:first-child { text-align:left; font-weight:700; color:#e5eefc; }
    .wl-scroll { max-height: 360px; overflow-y:auto; }
 
    /* ---------- Data log ---------- */
    .terminal {
        background:#060d18; border:1px solid rgba(255,255,255,0.08); border-radius:14px;
        padding:16px 18px; font-family: 'SFMono-Regular', Consolas, monospace;
        font-size:13px; line-height:1.7; color:#cbd5e1; box-shadow:0 10px 30px rgba(0,0,0,0.25);
    }
    .terminal .p { color:#60a5fa; } .terminal .i { color:#22c55e; } .terminal .c { color:#e5eefc; }
 
    /* ---------- Sidebar ---------- */
    [data-testid="stSidebar"] { background:#0a1426; border-right:1px solid rgba(255,255,255,0.08); }
    [data-testid="stSidebar"] .sb-brand {
        background: linear-gradient(135deg, rgba(59,130,246,0.20), rgba(15,27,45,0.2));
        border:1px solid rgba(255,255,255,0.08); border-radius:14px; padding:14px 16px; margin-bottom:14px;
    }
    [data-testid="stSidebar"] .sb-brand .t { font-size:15px; font-weight:800; color:#fff; letter-spacing:0.3px; }
    [data-testid="stSidebar"] .sb-brand .s { font-size:12px; color:#94a3b8; margin-top:2px; }
    [data-testid="stSidebar"] label { color:#e5eefc !important; font-weight:600; }
 
    /* Sidebar radio -> nav menu (made to look like real clickable buttons) */
    [data-testid="stSidebar"] div[role="radiogroup"] { gap:6px; }
    [data-testid="stSidebar"] div[role="radiogroup"] label {
        display:flex !important; align-items:center; width:100%;
        background:#0c1626; border:1px solid rgba(255,255,255,0.09); border-radius:10px;
        padding:9px 12px; margin:0; cursor:pointer; transition: all .12s ease;
        font-weight:600; color:#cbd5e1;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background: rgba(59,130,246,0.10); border-color: rgba(96,165,250,0.45); transform: translateX(2px);
    }
    /* chevron on the right of every item -> signals "go to page" */
    [data-testid="stSidebar"] div[role="radiogroup"] label::after {
        content: "\\203A"; margin-left:auto; color:#ffffff; font-size:18px; font-weight:800; opacity:0.85;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
        background: rgba(59,130,246,0.18); border-color: rgba(59,130,246,0.6);
        border-left:3px solid #3b82f6; color:#ffffff; box-shadow:0 5px 16px rgba(59,130,246,0.25);
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked)::after { opacity:1; }
    [data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child { display:none; }  /* hide radio dot */
 
    /* Nav heading + caption */
    [data-testid="stSidebar"] .nav-title {
        font-size:12px; font-weight:800; letter-spacing:1.1px; color:#94a3b8;
        text-transform:uppercase; margin:2px 0 2px 2px; display:flex; align-items:center; gap:7px;
    }
    [data-testid="stSidebar"] .nav-title .dot { color:#60a5fa; font-size:14px; }
    [data-testid="stSidebar"] .nav-cap { font-size:11.5px; color:#64748b; margin:0 0 9px 2px; }
 
    /* Main-area hint that points to the menu */
    .nav-hint {
        font-size:13px; color:#94a3b8; background:rgba(59,130,246,0.08);
        border:1px solid rgba(59,130,246,0.22); border-left:3px solid #3b82f6;
        border-radius:10px; padding:9px 14px; margin:0 0 18px 0;
    }
    .nav-hint .ic { color:#60a5fa; font-weight:800; margin-right:7px; }
    .nav-hint b { color:#cbd5e1; }

    /* A second, phone-only section switcher prevents hidden navigation. */
    .st-key-mobile_section_nav { display:none; }
 
    /* ---------- Buttons ---------- */
    .stButton button, .stDownloadButton button {
        background:#1d4ed8; color:#fff; border:none; border-radius:10px;
        padding:9px 16px; font-weight:600; transition: all .15s ease;
    }
    .stButton button:hover, .stDownloadButton button:hover { background:#3b82f6; transform: translateY(-1px); color:#fff; }
 
    /* Horizontal period radio -> pill buttons (chart top-right) */
    div[role="radiogroup"][aria-label="period"] { gap:6px; }
 
    [data-testid="stDataFrame"] { border:1px solid rgba(255,255,255,0.08); border-radius:14px; overflow:hidden; }
    hr { border-color: rgba(255,255,255,0.08); }
 
    /* ---------- Top brand header (main panel) ---------- */
    .top-head {
        display:flex; align-items:baseline; gap:14px; flex-wrap:wrap;
        padding:0 0 14px 0; margin-bottom:16px;
        border-bottom:1px solid rgba(255,255,255,0.08);
    }
    .top-head .th-title { font-size:30px; font-weight:900; color:#f8fafc; letter-spacing:-0.6px; }
    .top-head .th-title .accent { color:#60a5fa; text-shadow:0 0 22px rgba(96,165,250,0.45); }
    .top-head .th-sub { font-size:15px; font-weight:600; color:#94a3b8; }
 
    /* ---------- Dark form inputs (fix white selectboxes) ---------- */
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    .stSelectbox div[data-baseweb="select"] > div,
    .stTextInput div[data-baseweb="input"] > div {
        background-color:#0c1626 !important;
        border:1px solid rgba(255,255,255,0.12) !important;
        color:#e5eefc !important;
        border-radius:10px !important;
    }
    div[data-baseweb="select"] *, div[data-baseweb="input"] input {
        color:#e5eefc !important;
    }
    div[data-baseweb="select"] svg { fill:#94a3b8 !important; color:#94a3b8 !important; }
    /* Dropdown menu popover */
    div[data-baseweb="popover"] ul,
    div[data-baseweb="menu"], ul[role="listbox"] {
        background-color:#0f1b2d !important; border:1px solid rgba(255,255,255,0.1) !important;
    }
    div[data-baseweb="popover"] li, ul[role="listbox"] li { color:#e5eefc !important; }
    div[data-baseweb="popover"] li:hover, ul[role="listbox"] li:hover {
        background-color: rgba(59,130,246,0.18) !important;
    }
 
    /* ---------- Dark HTML data tables ---------- */
    .dtab-wrap {
        overflow:auto; border:1px solid rgba(255,255,255,0.08);
        border-radius:14px; box-shadow:0 10px 30px rgba(0,0,0,0.25); background:#0f1b2d;
    }
    .dtab { width:100%; border-collapse:collapse; font-size:13px; }
    .dtab thead th {
        position:sticky; top:0; z-index:1; background:#0c1626; color:#94a3b8;
        font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.4px;
        padding:11px 13px; text-align:right; border-bottom:1px solid rgba(255,255,255,0.1);
    }
    .dtab thead th:first-child, .dtab tbody td:first-child { text-align:left; }
    .dtab tbody td {
        padding:9px 13px; text-align:right; color:#e5eefc;
        border-bottom:1px solid rgba(255,255,255,0.05); white-space:nowrap;
    }
    .dtab tbody td:first-child { font-weight:700; }
    .dtab tbody tr:hover td { background: rgba(59,130,246,0.07); }
 
    /* ---------- Company card extras ---------- */
    .logo-badge {
        width:54px; height:54px; border-radius:14px; background:rgba(59,130,246,0.15);
        border:1px solid rgba(96,165,250,0.4); display:flex; align-items:center;
        justify-content:center; font-weight:900; color:#60a5fa; font-size:16px;
    }
    .qstats { display:flex; gap:26px; padding-top:6px; border-top:1px solid rgba(255,255,255,0.07); }
    .qstats .k { color:#94a3b8; font-size:11.5px; font-weight:600; text-transform:uppercase; letter-spacing:0.4px; }
    .qstats .v { color:#f8fafc; font-size:19px; font-weight:800; margin-top:3px; }
 
    /* ---------- Prominent thesis ---------- */
    .thesis-head { font-size:20px; font-weight:900; color:#f8fafc; margin:2px 0 10px 0; }
    .thesis-head .star { color:#60a5fa; }
    .thesis-lg { font-size:16px; line-height:1.7; padding:22px 26px; border-left-width:6px; }
 
    /* ---------- Mobile layout ---------- */
    @media (max-width: 768px) {
        /* Use the sidebar as a real drawer instead of squeezing the page beside it. */
        section[data-testid="stSidebar"],
        section[data-testid="stSidebar"] > div:first-child,
        [data-testid="stSidebarContent"] {
            width: min(86vw, 20rem) !important; min-width: min(86vw, 20rem) !important;
        }
        /* Make Streamlit's easy-to-miss gray arrow look like a labeled control. */
        [data-testid="stSidebarCollapsedControl"] {
            top:0.65rem !important; left:0.65rem !important; z-index:1002 !important;
            width:88px !important; min-width:88px !important; height:42px !important;
            background:#2563eb !important; border:1px solid rgba(147,197,253,0.55) !important;
            border-radius:10px !important; box-shadow:0 8px 24px rgba(37,99,235,0.35) !important;
        }
        [data-testid="stSidebarCollapsedControl"]::after {
            content:"Menu"; color:#fff; font-size:13px; font-weight:800; margin-left:2px;
        }
        [data-testid="collapsedControl"] {
            background:#2563eb !important; border:1px solid rgba(147,197,253,0.55) !important;
            border-radius:10px !important; padding:8px 11px !important;
            box-shadow:0 8px 24px rgba(37,99,235,0.35) !important;
        }
        [data-testid="collapsedControl"]::after {
            content:"Menu"; color:#fff; font-size:13px; font-weight:800; margin-left:5px;
        }
        [data-testid="stSidebarCollapsedControl"] button {
            width:auto !important; min-width:82px !important; height:42px !important;
            padding:0 12px !important; border-radius:10px !important;
            background:#2563eb !important; border:1px solid rgba(147,197,253,0.55) !important;
            box-shadow:0 8px 24px rgba(37,99,235,0.35) !important;
        }
        [data-testid="stSidebarCollapsedControl"] button::after {
            content:"Menu"; color:#fff; font-size:13px; font-weight:800; margin-left:5px;
        }
        [data-testid="stSidebarCollapseButton"] button {
            background:rgba(59,130,246,0.18) !important; border-radius:10px !important;
        }
        /* Compact nav + brand inside the drawer. */
        [data-testid="stSidebar"] .sb-brand { padding: 10px 11px; }
        [data-testid="stSidebar"] .sb-brand .t { font-size: 13px; }
        [data-testid="stSidebar"] div[role="radiogroup"] label { padding: 10px 11px; font-size: 13px; }

        .block-container { padding: 0.9rem 0.8rem 5rem 1.5rem; }
        .st-key-mobile_section_nav {
            display:block; position:sticky; top:4rem; z-index:900;
            background:rgba(7,17,31,0.96); border:1px solid rgba(96,165,250,0.34);
            border-radius:14px; padding:10px 12px 12px; margin:0 0 14px 0;
            box-shadow:0 10px 28px rgba(0,0,0,0.35); backdrop-filter:blur(10px);
        }
        .st-key-mobile_section_nav [data-testid="stMarkdownContainer"] p {
            margin:0 0 4px 0; color:#93c5fd; font-size:11px; font-weight:800;
            letter-spacing:0.7px; text-transform:uppercase;
        }
        .desktop-nav-hint { display:none; }
        /* Stack headers so title and subtitle never touch */
        .page-head { flex-direction: column; align-items: flex-start; gap: 4px; margin-bottom: 14px; padding-left:8px; }
        .page-head .title { font-size: 20px; max-width:100%; overflow-wrap:anywhere; }
        .page-head .sub { font-size: 12.5px; }
        .top-head { flex-direction: column; align-items: flex-start; gap: 2px; }
        .top-head .th-title { font-size: 20px; max-width:100%; overflow-wrap:anywhere; line-height:1.2; }
        .top-head .th-sub { padding-left:8px; }
        /* Denser grids for the narrower screen */
        .stat-grid { grid-template-columns: repeat(2, 1fr); }
        .dcf-result-grid { grid-template-columns: repeat(2, 1fr); }
        .dcf-assumption-grid { grid-template-columns: 1fr; }
        .dcf-result .v { font-size:19px; }
        .qstats { gap: 16px; }
    }

    /* =========================================================
       Stage 3 design system overrides
       ========================================================= */
    :root {
        --ei-bg: #07111f;
        --ei-surface: #0d192a;
        --ei-surface-raised: #101e31;
        --ei-border: rgba(148, 163, 184, 0.18);
        --ei-border-strong: rgba(148, 163, 184, 0.28);
        --ei-text: #edf3fb;
        --ei-muted: #91a3ba;
        --ei-accent: #5b8def;
        --ei-radius-sm: 8px;
        --ei-radius-md: 12px;
        --ei-space-1: 8px;
        --ei-space-2: 16px;
        --ei-space-3: 24px;
        --ei-space-4: 32px;
    }

    .stApp {
        background: var(--ei-bg);
    }
    .block-container {
        max-width: 1440px;
        padding-top: 1.5rem;
    }
    .sum-card, .panel, .thesis-box, .dcf-result, .dcf-assumption,
    [data-testid="stVerticalBlockBorderWrapper"], .dtab-wrap, .terminal {
        border-color: var(--ei-border) !important;
        border-radius: var(--ei-radius-md) !important;
        box-shadow: none !important;
    }
    .sum-card:hover {
        transform: none;
        border-color: var(--ei-border-strong);
    }
    .page-head .title { font-size: 26px; letter-spacing: -0.35px; }
    .page-head .sub { color: var(--ei-muted); }

    .product-head { display:flex; align-items:center; gap:12px; padding:2px 0; }
    .product-head .identity { display:flex; align-items:center; gap:12px; }
    .product-mark {
        width:34px; height:34px; border-radius:9px; display:grid; place-items:center;
        color:#dbeafe; background:#152744; border:1px solid rgba(96,165,250,.34);
        font-size:17px; font-weight:800;
    }
    .product-name { color:var(--ei-text); font-size:22px; font-weight:800; letter-spacing:-.35px; }
    .product-sub { color:var(--ei-muted); font-size:12px; margin-top:1px; letter-spacing:.25px; }
    .product-byline { color:var(--ei-muted); font-size:10.5px; margin-top:4px; }
    .st-key-application_header {
        border-bottom:1px solid var(--ei-border); padding:0 0 12px; margin-bottom:12px;
    }
    .st-key-application_header [data-testid="stHorizontalBlock"] { align-items:center; }
    .st-key-application_header [data-testid="stSelectbox"] { margin-bottom:0; }
    .header-selector-label { color:var(--ei-muted); font-size:10px; font-weight:750; text-transform:uppercase; letter-spacing:.65px; margin-bottom:3px; }

    .security-header {
        display:grid; grid-template-columns:minmax(0,1.55fr) minmax(210px,.8fr); gap:20px;
        align-items:center; background:var(--ei-surface); border:1px solid var(--ei-border);
        border-radius:var(--ei-radius-md); padding:14px 17px; margin:0 0 16px;
    }
    .security-id { display:flex; align-items:center; gap:14px; min-width:0; }
    .security-symbol {
        min-width:54px; height:44px; padding:0 9px; border-radius:9px; display:grid;
        place-items:center; background:#142744; border:1px solid rgba(96,165,250,.28);
        color:#bfdbfe; font-size:15px; font-weight:800;
    }
    .security-name { color:var(--ei-text); font-size:18px; font-weight:800; line-height:1.2; }
    .security-meta { color:var(--ei-muted); font-size:12px; margin-top:5px; line-height:1.45; }
    .security-quote { text-align:right; }
    .security-price { color:var(--ei-text); font-size:24px; font-weight:800; line-height:1; }
    .security-change { font-size:13px; font-weight:700; margin-top:7px; }
    .security-stamp { color:var(--ei-muted); font-size:11px; margin-top:6px; line-height:1.4; }

    .research-note {
        background:#0c1828; border:1px solid var(--ei-border); border-left:3px solid var(--ei-accent);
        border-radius:var(--ei-radius-md); padding:16px 18px; margin:0 0 18px;
    }
    .research-note .eyebrow {
        color:#93b7f5; font-size:10.5px; font-weight:800; letter-spacing:.85px;
        text-transform:uppercase; margin-bottom:7px;
    }
    .research-note .title { color:var(--ei-text); font-size:15px; font-weight:750; margin-bottom:6px; }
    .research-note .body { color:#cbd7e7; font-size:13px; line-height:1.6; }
    .research-note .source { color:var(--ei-muted); font-size:10.5px; margin-top:8px; }
    .dcf-preview-head .b {
        color:#bfd5fb; background:rgba(91,141,239,.10); border-color:rgba(91,141,239,.28);
    }

    [data-testid="stSidebar"] { background:#081426; border-right:1px solid var(--ei-border); }
    [data-testid="stSidebar"] .sb-brand {
        background:#0d1b2f; border-color:var(--ei-border); border-radius:var(--ei-radius-md);
        padding:12px 13px; margin-bottom:18px; display:flex; align-items:center; gap:10px;
    }
    [data-testid="stSidebar"] .sb-brand .mark {
        width:32px; height:32px; border-radius:8px; display:grid; place-items:center;
        background:#152744; border:1px solid rgba(96,165,250,.3); color:#bfdbfe;
        font-size:12px; font-weight:850; flex:0 0 auto;
    }
    [data-testid="stSidebar"] .sb-brand .t { font-size:14px; letter-spacing:-.1px; }
    [data-testid="stSidebar"] .sb-brand .s { font-size:11px; margin-top:4px; }

    .company-description {
        background:#0f1b2d; border:1px solid var(--ei-border); border-radius:var(--ei-radius-md);
        padding:15px 17px; color:#cbd7e7; font-size:13px; line-height:1.58;
        display:-webkit-box; -webkit-line-clamp:6; -webkit-box-orient:vertical; overflow:hidden;
    }
    .financial-statement-scroll {
        width:100%; overflow-x:auto; border:1px solid var(--ei-border); border-radius:var(--ei-radius-sm);
    }
    .financial-statement { width:max-content; min-width:100%; border-collapse:separate; border-spacing:0; }
    .financial-statement th, .financial-statement td {
        padding:10px 13px; border-bottom:1px solid rgba(255,255,255,.06); white-space:nowrap;
        text-align:right; font-size:12.5px;
    }
    .financial-statement th { color:#91a3ba; background:#0c1828; font-size:10.5px; text-transform:uppercase; letter-spacing:.45px; }
    .financial-statement th:first-child, .financial-statement td:first-child {
        position:sticky; left:0; z-index:2; text-align:left; min-width:180px;
        background:#0d1a2c; box-shadow:1px 0 0 rgba(255,255,255,.09);
    }
    .financial-statement td:first-child { color:#e5eefc; font-weight:650; }
    .financial-statement tr:last-child td { border-bottom:0; }

    .formula-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }
    .formula-card { background:#0f1b2d; border:1px solid var(--ei-border); border-radius:var(--ei-radius-sm); padding:15px 17px; }
    .formula-card .name { color:#93b7f5; font-size:10.5px; text-transform:uppercase; letter-spacing:.7px; font-weight:800; }
    .formula-card .formula { color:#f8fafc; font-size:16px; font-weight:750; margin:8px 0; font-family:ui-monospace,SFMono-Regular,Consolas,monospace; }
    .formula-card .explain { color:#91a3ba; font-size:12px; line-height:1.55; }
    [data-testid="stSidebar"] .nav-title {
        margin:16px 0 7px 4px; color:#7890ad; font-size:10px; letter-spacing:1.25px;
    }
    [data-testid="stSidebar"] .nav-cap { display:none; }
    [data-testid="stSidebar"] div[role="radiogroup"] { gap:3px; }
    [data-testid="stSidebar"] div[role="radiogroup"] label {
        background:transparent; border-color:transparent; border-radius:8px; padding:8px 10px;
        color:#b9c7da; font-size:13px;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label::after { display:none; }
    [data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        transform:none; background:rgba(91,141,239,.08); border-color:transparent;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
        color:#f5f8fc; background:rgba(91,141,239,.14); border-color:rgba(91,141,239,.22);
        border-left:2px solid var(--ei-accent); box-shadow:none;
    }
    [data-testid="stSidebar"] input[type="radio"] {
        position:absolute !important; opacity:0 !important; pointer-events:none !important;
    }
    [data-testid="stSidebar"] label[data-testid="stRadioOption"] > div > div > div:first-child {
        display:none !important;
    }

    @media (min-width: 1024px) {
        section[data-testid="stSidebar"] {
            display:block !important; transform:none !important; visibility:visible !important;
            min-width:17rem !important; width:17rem !important;
        }
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="stExpandSidebarButton"] { display:none !important; }
        .st-key-mobile_section_nav { display:none !important; }
    }

    @media (min-width: 1024px) and (max-width: 1199px) {
        [data-testid="stHorizontalBlock"] { flex-wrap:wrap !important; }
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            min-width:calc(50% - 12px) !important; flex:1 1 calc(50% - 12px) !important;
        }
    }

    @media (max-width: 1023px) {
        [data-testid="stMain"], [data-testid="stAppViewContainer"] {
            margin-left:0 !important; width:100% !important;
        }
        section[data-testid="stSidebar"] {
            width:min(88vw, 20rem) !important; min-width:min(88vw, 20rem) !important;
        }
        section[data-testid="stSidebar"][aria-expanded="false"] {
            width:0 !important; min-width:0 !important; flex-basis:0 !important;
        }
        .st-key-mobile_section_nav {
            display:block; position:sticky; top:.6rem; z-index:900; background:rgba(7,17,31,.96);
            border:1px solid var(--ei-border-strong); border-radius:var(--ei-radius-md);
            padding:7px 9px; margin:0 0 14px 108px; width:calc(100% - 108px);
        }
        .st-key-mobile_section_nav [data-testid="stMarkdownContainer"] { display:none; }
        [data-testid="stSidebarCollapsedControl"] {
            position:fixed !important; top:.7rem !important; left:.65rem !important; z-index:1002 !important;
        }
        [data-testid="stSidebarCollapsedControl"] button {
            min-width:86px !important; height:40px !important; padding:0 11px !important;
            background:#1d4f91 !important; border:1px solid rgba(147,197,253,.4) !important;
            border-radius:9px !important; box-shadow:none !important;
        }
        [data-testid="stSidebarCollapsedControl"] button::after {
            content:"Menu"; color:white; font-size:12px; font-weight:750; margin-left:5px;
        }
        [data-testid="stExpandSidebarButton"] {
            position:fixed !important; top:.65rem !important; left:.65rem !important; z-index:1003 !important;
            width:98px !important; min-width:98px !important; height:40px !important;
            padding:0 11px !important; background:#1d4f91 !important;
            border:1px solid rgba(147,195,253,.42) !important; border-radius:9px !important;
            box-shadow:none !important;
        }
        [data-testid="stExpandSidebarButton"]::after {
            content:"Menu"; color:#fff; font-size:12px; font-weight:750; margin-left:5px;
        }
        [data-testid="stHorizontalBlock"] { flex-wrap:wrap !important; }
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            min-width:calc(50% - 10px) !important; flex:1 1 calc(50% - 10px) !important;
        }
        .security-header { grid-template-columns:1fr; gap:13px; }
        .security-quote { text-align:left; padding-left:72px; }
    }

    @media (max-width: 600px) {
        .block-container { padding:1rem .8rem 4rem 1.25rem; }
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            min-width:100% !important; flex:1 1 100% !important;
        }
        .product-head { align-items:flex-start; }
        .product-name { font-size:18px; }
        .product-byline { font-size:10px; }
        .product-sub { max-width:270px; line-height:1.35; }
        .st-key-application_header [data-testid="stHorizontalBlock"] { gap:6px; }
        .header-selector-label { display:none; }
        .formula-grid { grid-template-columns:1fr; }
        .financial-statement th:first-child, .financial-statement td:first-child { min-width:145px; }
        .security-header { padding:15px; }
        .security-id { align-items:flex-start; }
        .security-symbol { min-width:52px; height:43px; }
        .security-name { font-size:18px; }
        .security-quote { padding-left:66px; }
        .security-price { font-size:24px; }
        .stat-grid, .dcf-result-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
    }

    /* =========================================================
       White institutional dashboard reconstruction
       The attached light mockup is the visual source of truth.
       ========================================================= */
    :root {
        --ei-bg:#f7f9fc;
        --ei-surface:#ffffff;
        --ei-surface-raised:#ffffff;
        --ei-soft:#f8fafc;
        --ei-soft-blue:#eef5ff;
        --ei-border:#dfe5ed;
        --ei-border-strong:#cbd5e1;
        --ei-text:#13213d;
        --ei-muted:#687892;
        --ei-accent:#1769e0;
        --ei-positive:#0f9f6e;
        --ei-negative:#dc2626;
        --ei-radius-sm:6px;
        --ei-radius-md:8px;
        --ei-shadow:0 1px 3px rgba(15,31,61,.055), 0 1px 2px rgba(15,31,61,.03);
    }

    html, body, [class*="css"], .stApp, [data-testid="stSidebar"] {
        font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
    }
    html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background:var(--ei-bg) !important; color:var(--ei-text) !important;
    }
    [data-testid="stHeader"] { background:transparent !important; height:0 !important; }
    [data-testid="stToolbar"], [data-testid="stDecoration"] { display:none !important; }
    .block-container {
        width:100%; max-width:1600px; padding:0 16px 32px !important;
    }
    .block-container > [data-testid="stVerticalBlock"] { gap:12px !important; }
    .block-container > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:has(style) { display:none !important; }
    h1, h2, h3, h4, h5, h6,
    p, span, label, li, div { color:var(--ei-text); }
    h1, h2, h3, h4 { font-weight:700 !important; letter-spacing:-.25px; }
    h4 { font-size:14px !important; }
    .small-muted, .stCaption, [data-testid="stCaptionContainer"],
    [data-testid="stCaptionContainer"] p { color:var(--ei-muted) !important; font-size:10.5px !important; }
    hr { border-color:var(--ei-border) !important; }

    /* Main top bar */
    .st-key-application_header {
        position:sticky; top:0; z-index:990; min-height:44px; height:44px; box-sizing:border-box; overflow:visible;
        margin:0 -16px 0 !important; padding:5px 16px !important;
        background:rgba(255,255,255,.98); border-bottom:1px solid var(--ei-border) !important;
        box-shadow:none;
    }
    .st-key-application_header [data-testid="stHorizontalBlock"] {
        align-items:center !important; gap:8px !important; flex-wrap:nowrap !important;
    }
    .st-key-application_header [data-testid="stSelectbox"] { height:30px !important; min-height:30px !important; }
    .st-key-application_header [data-testid="stColumn"] { min-width:0 !important; }
    .header-ticker-chip {
        height:30px; display:flex; align-items:center; justify-content:center; gap:7px;
        padding:0 9px; border:1px solid var(--ei-border); border-radius:6px;
        background:#fff; color:var(--ei-text); font-size:11px; font-weight:650;
    }
    .header-ticker-chip .glyph { font-size:13px; color:#0f172a; }
    .header-market-time { color:var(--ei-muted); font-size:9.5px; text-align:right; white-space:nowrap; }
    .header-market-time .live-dot { color:var(--ei-positive); font-size:9px; margin-left:4px; }
    .header-actions { display:flex; align-items:center; justify-content:flex-end; gap:13px; }
    .header-action {
        width:24px; height:24px; display:grid; place-items:center; border:0;
        background:transparent; color:#263754; font-size:15px; line-height:1;
    }
    .header-avatar {
        width:28px; height:28px; display:grid; place-items:center; border-radius:50%;
        background:#f1f5f9; border:1px solid var(--ei-border); color:#475569;
        font-size:9px; font-weight:650;
    }
    .header-chevron { color:#64748b; font-size:12px; }
    .header-selector-label { display:none; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background:#fff !important; border-right:1px solid var(--ei-border) !important;
        box-shadow:none !important;
    }
    [data-testid="stSidebarContent"] { padding:0 !important; }
    [data-testid="stSidebarHeader"] { display:none !important; }
    [data-testid="stSidebarUserContent"] {
        box-sizing:border-box; width:100% !important; padding:5px 4px 110px !important;
    }
    [data-testid="stSidebar"] .sb-brand {
        display:flex; align-items:center; gap:8px; margin:0 0 8px !important;
        padding:4px 0 !important; background:transparent !important;
        border:0 !important; border-radius:0 !important;
    }
    [data-testid="stSidebar"] .sb-brand .mark {
        width:20px; height:20px; border:0; background:transparent;
        color:var(--ei-accent); font-size:17px; font-weight:800;
    }
    [data-testid="stSidebar"] .sb-brand .t {
        color:var(--ei-text) !important; font-size:12px !important; font-weight:700;
        letter-spacing:-.2px; white-space:nowrap;
    }
    [data-testid="stSidebar"] .sb-brand .t .accent { color:var(--ei-accent); }
    [data-testid="stSidebar"] .sb-brand .s { display:none; }
    [data-testid="stSidebar"] .nav-title {
        margin:15px 0 6px 4px !important; color:#7a879b !important;
        font-size:8px !important; font-weight:700; letter-spacing:.85px !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] { gap:1px !important; }
    [data-testid="stSidebar"] div[role="radiogroup"] label {
        position:relative; min-height:29px; padding:6px 8px !important; margin:0 !important;
        color:#263754 !important; background:transparent !important;
        border:1px solid transparent !important; border-left:2px solid transparent !important;
        border-radius:6px !important; font-size:9.5px !important; font-weight:500 !important;
        box-shadow:none !important; transform:none !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label::before {
        content:'◉'; width:15px; flex:0 0 15px; color:#40516d;
        font-size:10px; font-weight:500; text-align:center; margin-right:5px;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background:#f8fafc !important; border-color:#edf1f5 !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
        color:var(--ei-accent) !important; background:var(--ei-soft-blue) !important;
        border-color:#d7e7ff !important; border-left:2px solid var(--ei-accent) !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked)::before { color:var(--ei-accent); }
    [data-testid="stSidebar"] div[role="radiogroup"] label p {
        color:inherit !important; font-size:9.5px !important; white-space:nowrap !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label::after { display:none !important; }
    .sidebar-author {
        position:fixed; left:9px; bottom:38px; width:180px; padding:10px 12px;
        background:#fff; border:1px solid var(--ei-border); border-radius:7px;
        box-shadow:var(--ei-shadow); z-index:5;
    }
    .sidebar-author .row { display:flex; align-items:flex-start; gap:9px; }
    .sidebar-author .icon { color:var(--ei-accent); font-size:16px; line-height:1.2; }
    .sidebar-author .name { color:#4b5d78; font-size:9px; font-weight:500; }
    .sidebar-author .role { color:#5f7089; font-size:9px; margin-top:5px; }
    .sidebar-author .version { color:#77869b; font-size:8px; margin-top:10px; }

    /* Page and company headers */
    .page-head { margin:0 0 7px !important; padding:12px 0 6px; gap:6px 14px; }
    .page-head .title { color:var(--ei-text) !important; font-size:18px !important; font-weight:700 !important; }
    .page-head .sub { color:var(--ei-muted) !important; font-size:10px !important; }
    .security-header {
        grid-template-columns:minmax(0,1.6fr) minmax(220px,.7fr); gap:16px;
        height:78px; min-height:0; box-sizing:border-box; margin:0 0 2px; padding:10px 12px;
        background:#fff; border:1px solid var(--ei-border); border-radius:8px;
        box-shadow:var(--ei-shadow);
    }
    .security-id { gap:14px; }
    .security-symbol {
        min-width:56px; width:56px; height:56px; padding:0; border-radius:7px;
        background:#fff; border:1px solid var(--ei-border); color:#0f172a;
        font-size:12px; box-shadow:0 1px 2px rgba(15,31,61,.04);
    }
    .security-symbol.apple-mark { position:relative; }
    .apple-body {
        position:relative; display:block; width:24px; height:25px; background:#0f172a;
        border-radius:46% 48% 50% 50% / 42% 42% 58% 58%; transform:rotate(-4deg);
    }
    .apple-body::before {
        content:''; position:absolute; width:5px; height:9px; left:13px; top:-8px;
        background:#0f172a; border-radius:80% 10% 80% 10%; transform:rotate(35deg);
    }
    .apple-body::after {
        content:''; position:absolute; width:9px; height:9px; right:-5px; top:4px;
        background:#fff; border-radius:50%;
    }
    .security-name { color:var(--ei-text); font-size:20px; font-weight:700; }
    .security-name .ticker-badge {
        display:inline-flex; vertical-align:3px; margin-left:8px; padding:2px 7px;
        border-radius:4px; background:#f8fafc; border:1px solid var(--ei-border);
        color:#53627a; font-size:9px; font-weight:600;
    }
    .security-meta { color:var(--ei-muted); font-size:9.5px; margin-top:7px; }
    .security-price { color:var(--ei-text); font-size:24px; font-weight:700; }
    .security-change { margin-top:3px; font-size:11px; font-weight:650; }
    .security-stamp { color:var(--ei-muted); font-size:8.5px; margin-top:5px; line-height:1.35; }

    /* White card system */
    .sum-card, .panel, .thesis-box, .dcf-result, .dcf-assumption,
    [data-testid="stVerticalBlockBorderWrapper"], .dtab-wrap, .terminal,
    .research-note, .company-description, .formula-card {
        background:#fff !important; color:var(--ei-text) !important;
        border:1px solid var(--ei-border) !important; border-radius:7px !important;
        box-shadow:var(--ei-shadow) !important;
    }
    .panel { padding:11px 12px; margin-bottom:7px; }
    .panel h4 { color:var(--ei-text) !important; margin:0 0 9px; font-size:12px !important; font-weight:700 !important; }
    [data-testid="stVerticalBlockBorderWrapper"] { padding:0 !important; }
    [data-testid="stVerticalBlockBorderWrapper"] > div { gap:8px !important; }
    .sum-card { padding:11px 12px; }
    .sum-card:hover { transform:none !important; border-color:var(--ei-border-strong) !important; }
    .sum-card .label { color:var(--ei-muted); font-size:8.5px; letter-spacing:.35px; }
    .sum-card .value { color:var(--ei-text); font-size:18px; }
    .sum-card .sub { font-size:9px; }
    .stat-grid { gap:8px; }
    .stat {
        min-height:50px; padding:8px 10px; background:#fff;
        border:1px solid #e6ebf1; border-radius:6px;
    }
    .stat .k { color:var(--ei-muted); font-size:8px; font-weight:500; line-height:1.2; letter-spacing:0; text-transform:none; }
    .stat .v { color:var(--ei-text); font-size:14px; font-weight:700; line-height:1.1; margin-top:5px; }
    .pos { color:var(--ei-positive) !important; }
    .neg { color:var(--ei-negative) !important; }
    .neutral { color:var(--ei-muted) !important; }

    /* DCF cards */
    .dcf-preview-head { margin:10px 0 6px; }
    .dcf-preview-head .t { color:var(--ei-text); font-size:15px; font-weight:700; }
    .dcf-preview-head .b {
        color:var(--ei-accent); background:var(--ei-soft-blue); border-color:#d7e7ff;
        border-radius:999px; padding:3px 7px; font-size:8px;
    }
    .dcf-result-grid { gap:8px; margin-bottom:8px; }
    .dcf-result { min-height:62px; padding:10px 11px; text-align:center; }
    .dcf-result .k { color:var(--ei-muted); font-size:8px; font-weight:500; text-transform:none; letter-spacing:0; }
    .dcf-result .v { color:var(--ei-accent); font-size:17px; font-weight:700; margin-top:6px; }
    .dcf-result:nth-child(2) .v { color:var(--ei-negative); }
    .dcf-result:nth-child(4) .v { color:var(--ei-positive); }
    .dcf-assumption { padding:8px 10px; background:#fff !important; }
    .dcf-assumption .k, .dcf-mini-note, .dcf-reverse .k, .dcf-source .k { color:var(--ei-muted); }
    .dcf-assumption .v, .dcf-reverse .v, .dcf-source .v { color:var(--ei-text); }
    .dcf-reverse { background:#f8fafc; border:1px solid var(--ei-border); border-radius:6px; }
    .dcf-source { border-bottom-color:var(--ei-border); }

    /* Tables */
    .dtab-wrap { overflow:auto; }
    .dtab { background:#fff; color:var(--ei-text); font-size:9.5px; }
    .dtab thead th {
        background:#f8fafc; color:#66758d; font-size:8px; font-weight:600;
        text-transform:none; letter-spacing:0; padding:7px 9px;
        border-bottom:1px solid var(--ei-border);
    }
    .dtab tbody td {
        color:var(--ei-text); font-size:9px; padding:6px 9px;
        border-bottom:1px solid #edf1f5;
    }
    .dtab tbody tr:hover td { background:#f8fbff; }
    .wl th { color:var(--ei-muted); border-bottom-color:var(--ei-border); font-size:8px; padding:6px; }
    .wl td { color:var(--ei-text); border-bottom-color:#edf1f5; font-size:9.5px; padding:6px; }
    .wl td:first-child { color:var(--ei-text); }
    [data-testid="stDataFrame"] {
        background:#fff !important; border:1px solid var(--ei-border) !important;
        border-radius:6px !important; box-shadow:none !important; overflow:hidden;
    }
    [data-testid="stDataFrame"] button { color:#64748b !important; background:transparent !important; }
    .financial-statement-scroll { border-color:var(--ei-border); border-radius:6px; background:#fff; }
    .financial-statement th, .financial-statement td {
        color:var(--ei-text); border-bottom-color:#edf1f5; font-size:9.5px; padding:7px 9px;
    }
    .financial-statement th { color:var(--ei-muted); background:#f8fafc; font-size:8px; }
    .financial-statement th:first-child, .financial-statement td:first-child {
        background:#fff; box-shadow:1px 0 0 var(--ei-border);
    }
    .financial-statement td:first-child { color:var(--ei-text); }

    /* Controls, tabs and alerts */
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    .stSelectbox div[data-baseweb="select"] > div,
    .stTextInput div[data-baseweb="input"] > div,
    [data-testid="stNumberInput"] > div > div {
        min-height:30px !important; background:#fff !important; color:var(--ei-text) !important;
        border:1px solid var(--ei-border) !important; border-radius:6px !important;
        box-shadow:none !important;
    }
    div[data-baseweb="select"] *, div[data-baseweb="input"] input { color:var(--ei-text) !important; font-size:10px !important; }
    div[data-baseweb="select"] svg { fill:#708096 !important; color:#708096 !important; }
    div[data-baseweb="popover"] ul, div[data-baseweb="menu"], ul[role="listbox"] {
        background:#fff !important; border:1px solid var(--ei-border) !important; box-shadow:0 8px 20px rgba(15,31,61,.12) !important;
    }
    div[data-baseweb="popover"] li, ul[role="listbox"] li { color:var(--ei-text) !important; font-size:10px !important; }
    div[data-baseweb="popover"] li:hover, ul[role="listbox"] li:hover { background:var(--ei-soft-blue) !important; }
    [data-testid="stWidgetLabel"] p { color:#516078 !important; font-size:8.5px !important; font-weight:500 !important; }
    .stButton button, .stDownloadButton button {
        min-height:30px; padding:5px 11px; background:#fff; color:var(--ei-accent);
        border:1px solid #bcd4f7; border-radius:6px; box-shadow:none;
        font-size:9.5px; font-weight:600;
    }
    .stButton button:hover, .stDownloadButton button:hover {
        background:var(--ei-soft-blue); color:var(--ei-accent); border-color:#86b5f5; transform:none;
    }
    [data-baseweb="tab-list"] { gap:18px; border-bottom:1px solid var(--ei-border); }
    [data-baseweb="tab"] {
        min-height:34px; padding:6px 2px; background:transparent !important;
        color:#53627a !important; font-size:10px !important;
    }
    [aria-selected="true"][data-baseweb="tab"] { color:var(--ei-accent) !important; }
    [data-baseweb="tab-highlight"] { background-color:var(--ei-accent) !important; height:2px !important; }
    [data-testid="stExpander"] {
        background:#fff; border:1px solid var(--ei-border); border-radius:6px;
    }
    [data-testid="stExpander"] summary { color:var(--ei-text); font-size:10px; }
    [data-testid="stAlert"] { border-radius:6px !important; box-shadow:none !important; font-size:10px !important; }
    [data-testid="stAlert"] p { font-size:10px !important; }
    [data-testid="stMetric"] { padding:4px 0; }
    [data-testid="stMetricLabel"] p { color:var(--ei-muted) !important; font-size:8.5px !important; }
    [data-testid="stMetricValue"] { color:var(--ei-text) !important; font-size:16px !important; }
    div[role="radiogroup"] label { color:#46566f !important; font-size:10px !important; }
    div[role="radiogroup"] label:has(input:checked) p { color:var(--ei-accent) !important; }
    [data-testid="stSlider"] [role="slider"] { background:var(--ei-accent) !important; }

    /* Supporting components */
    .research-note { border-left:3px solid var(--ei-accent) !important; padding:11px 13px; }
    .research-note .eyebrow { color:var(--ei-accent); font-size:8px; }
    .research-note .title { color:var(--ei-text); font-size:12px; }
    .research-note .body { color:#46566f; font-size:10.5px; line-height:1.55; }
    .research-note .source { color:var(--ei-muted); font-size:8px; }
    .thesis-box { color:#34445f; border-left:3px solid var(--ei-accent) !important; font-size:10.5px; }
    .company-description { color:#34445f; font-size:10.5px; padding:11px 13px; }
    .formula-card { padding:11px 13px; }
    .formula-card .name { color:var(--ei-accent); font-size:8px; }
    .formula-card .formula { color:var(--ei-text); font-size:12px; }
    .formula-card .explain { color:var(--ei-muted); font-size:9.5px; }
    .terminal { background:#f8fafc !important; color:#334155 !important; font-size:10px; box-shadow:none !important; }
    .terminal .p { color:var(--ei-accent); }
    .terminal .i { color:var(--ei-positive); }
    .terminal .c { color:#334155; }
    .nav-hint { display:none; }

    /* Relative Valuation mockup composition */
    .st-key-relative_top { gap:0 !important; }
    .st-key-relative_top [data-testid="stHorizontalBlock"] {
        align-items:stretch !important; gap:12px !important; flex-wrap:nowrap !important;
    }
    .st-key-relative_top [data-testid="stColumn"] { min-width:0 !important; }
    .st-key-relative_top [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(1) {
        flex:0 0 calc(36% - 4px) !important; width:calc(36% - 4px) !important;
    }
    .st-key-relative_top [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) {
        flex:0 0 calc(64% - 8px) !important; width:calc(64% - 8px) !important;
    }
    .mock-card {
        background:#fff; border:1px solid var(--ei-border); border-radius:7px;
        box-shadow:var(--ei-shadow); padding:10px 11px;
    }
    .mock-card-title { color:var(--ei-text); font-size:11px; font-weight:700; margin-bottom:8px; }
    .mock-multiples, .mock-peers { height:216px; min-height:216px; box-sizing:border-box; overflow:hidden; }
    .mock-multiples .stat-grid { grid-template-columns:repeat(3,minmax(0,1fr)); gap:7px; }
    .mock-multiples .stat { min-height:49px; }
    .mock-table-wrap { width:100%; overflow:auto; border:1px solid #e7ebf0; border-radius:5px; }
    .mock-table { width:100%; border-collapse:collapse; background:#fff; table-layout:auto; }
    .mock-table th {
        padding:5px 7px; color:#687892; background:#f8fafc; border-bottom:1px solid var(--ei-border);
        border-right:1px solid #edf1f5; font-size:7.5px; font-weight:600; line-height:1.15; text-align:center; white-space:nowrap;
    }
    .mock-table td {
        padding:5px 7px; color:var(--ei-text); border-bottom:1px solid #edf1f5;
        border-right:1px solid #f1f4f7; font-size:8px; line-height:1.15; text-align:center; white-space:nowrap;
    }
    .mock-table th:first-child, .mock-table td:first-child { text-align:left; font-weight:600; }
    .mock-table th:last-child, .mock-table td:last-child { border-right:0; }
    .mock-table tr:last-child td { border-bottom:0; }
    .mock-note { color:var(--ei-muted); font-size:7.5px; line-height:1.3; margin-top:8px; }
    .mock-dcf-summary { height:105px; box-sizing:border-box; margin-top:17px; padding-bottom:10px; overflow:hidden; }
    .mock-summary-grid { display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:10px; }
    .mock-summary-cell {
        min-height:61px; display:flex; flex-direction:column; align-items:center; justify-content:center;
        padding:7px 8px; border:1px solid #e7ebf0; border-radius:5px; text-align:center;
    }
    .mock-summary-cell .k { color:var(--ei-muted); font-size:7.5px; font-weight:500; }
    .mock-summary-cell .v { color:var(--ei-accent); font-size:14px; font-weight:700; margin-top:6px; white-space:nowrap; }
    .mock-summary-cell .v.bear-value { color:var(--ei-negative); }
    .mock-summary-cell .v.bull-value { color:var(--ei-positive); }
    .mock-summary-cell .s { color:var(--ei-muted); font-size:7.5px; margin-top:4px; }
    .mock-summary-cell .range-value { font-size:12px; }
    .st-key-relative_preview {
        height:190px !important; min-height:190px !important; max-height:190px !important;
        box-sizing:border-box; overflow:hidden; margin-top:14px !important; padding:8px 11px 5px; background:#fff;
        border:1px solid var(--ei-border); border-radius:7px; box-shadow:var(--ei-shadow);
        gap:6px !important;
    }
    .preview-title { margin-bottom:0; }
    .st-key-relative_filters [data-testid="stHorizontalBlock"] {
        gap:9px !important; align-items:end !important; flex-wrap:nowrap !important;
    }
    .st-key-relative_filters [data-testid="stColumn"] { min-width:0 !important; }
    .st-key-relative_filters [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(1),
    .st-key-relative_filters [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2),
    .st-key-relative_filters [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3) {
        flex:1 1 0 !important; width:auto !important;
    }
    .st-key-relative_filters [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(4) {
        flex:2.35 1 0 !important; width:auto !important;
    }
    .st-key-relative_filters [data-testid="stSelectbox"],
    .st-key-relative_filters [data-testid="stSlider"] { margin-bottom:0 !important; }
    .st-key-relative_filters [data-testid="stSelectbox"] { height:50px !important; min-height:50px !important; overflow:visible; }
    .st-key-relative_filters [data-testid="stWidgetLabel"] { height:15px !important; min-height:15px !important; }
    .st-key-relative_filters [data-testid="stWidgetLabel"] p { line-height:1 !important; }
    .preview-table { border-left:0; border-right:0; border-radius:0; }
    .preview-table .mock-table th, .preview-table .mock-table td { padding-top:3px; padding-bottom:3px; }
    .st-key-relative_preview .stButton button { white-space:nowrap; font-size:8px; height:25px !important; min-height:25px !important; padding:2px 7px; }
    .st-key-relative_preview_button [data-testid="stHorizontalBlock"] { flex-wrap:nowrap !important; gap:8px !important; }
    .st-key-relative_preview_button [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(1),
    .st-key-relative_preview_button [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3) {
        flex:1 1 0 !important; width:auto !important; min-width:0 !important;
    }
    .st-key-relative_preview_button [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) {
        flex:0 0 170px !important; width:170px !important; min-width:170px !important;
    }
    .st-key-relative_preview_button { position:relative; top:10px; }

    /* Desktop/tablet/mobile behavior */
    @media (min-width:1024px) {
        section[data-testid="stSidebar"] {
            display:block !important; transform:none !important; visibility:visible !important;
            min-width:212px !important; width:212px !important;
        }
        [data-testid="stSidebarCollapsedControl"], [data-testid="stExpandSidebarButton"] { display:none !important; }
        .st-key-mobile_section_nav { display:none !important; }
        [data-testid="stLayoutWrapper"]:has(.st-key-mobile_section_nav) { display:none !important; }
    }
    @media (min-width:1024px) and (max-width:1199px) {
        .st-key-application_header [data-testid="stHorizontalBlock"] { flex-wrap:nowrap !important; }
        .st-key-application_header [data-testid="stColumn"] { min-width:0 !important; flex:auto !important; }
    }
    @media (max-width:1023px) {
        section[data-testid="stSidebar"] { background:#fff !important; }
        [data-testid="stToolbar"] { display:flex !important; }
        [data-testid="stSidebarHeader"] {
            display:flex !important; position:absolute !important; top:5px; right:5px;
            width:34px !important; height:34px !important; min-height:34px !important;
            padding:0 !important; z-index:1004;
        }
        [data-testid="stLogoSpacer"] { display:none !important; }
        [data-testid="stSidebarCollapseButton"],
        [data-testid="stSidebarCollapseButton"] button {
            width:34px !important; height:34px !important; min-width:34px !important;
            color:var(--ei-accent) !important; background:#fff !important;
            border:1px solid #bcd4f7 !important; border-radius:6px !important;
        }
        section[data-testid="stSidebar"][aria-expanded="false"] [data-testid="stSidebarHeader"] {
            display:none !important;
        }
        .st-key-mobile_section_nav {
            display:block; position:sticky; top:5px; z-index:1000; width:calc(100% - 94px);
            margin:5px 0 6px 94px; padding:4px 5px; background:#fff;
            border:1px solid var(--ei-border); border-radius:6px; box-shadow:var(--ei-shadow);
        }
        [data-testid="stSidebarCollapsedControl"] button,
        [data-testid="stExpandSidebarButton"] {
            min-width:78px !important; width:78px !important; height:34px !important;
            top:7px !important; left:8px !important; padding:0 9px !important;
            background:#fff !important; color:var(--ei-accent) !important;
            border:1px solid #bcd4f7 !important; border-radius:6px !important; box-shadow:var(--ei-shadow) !important;
        }
        [data-testid="stSidebarCollapsedControl"] button::after,
        [data-testid="stExpandSidebarButton"]::after { color:var(--ei-accent) !important; }
        .st-key-application_header { position:relative; margin-top:3px !important; }
        .header-market-time, .header-actions { display:none; }
        .st-key-application_header [data-testid="stColumn"]:nth-child(n+3) { display:none !important; }
        .security-header {
            grid-template-columns:minmax(0,1.6fr) minmax(220px,.7fr); gap:16px;
            height:78px; min-height:0;
        }
        .security-quote { text-align:right; padding-left:0; }
    }
    @media (max-width:600px) {
        .block-container { padding:0 10px 34px !important; }
        .st-key-application_header { margin:0 -10px 10px !important; padding:5px 10px !important; }
        .st-key-application_header [data-testid="stHorizontalBlock"] { display:grid !important; grid-template-columns:82px minmax(0,1fr); }
        .st-key-application_header [data-testid="stColumn"] { width:auto !important; min-width:0 !important; flex:auto !important; }
        .page-head { flex-direction:column; align-items:flex-start; gap:2px; padding-left:0; }
        .page-head .title { font-size:17px !important; }
        .security-header { padding:10px; }
        .security-header { grid-template-columns:1fr; gap:7px; height:auto; min-height:126px; }
        .security-symbol { min-width:48px; width:48px; height:48px; }
        .security-name { font-size:17px; }
        .security-quote { text-align:left; padding-left:62px; }
        .security-price { font-size:21px; }
        .stat-grid, .dcf-result-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
        .formula-grid { grid-template-columns:1fr; }
        [data-baseweb="tab-list"] { gap:12px; overflow-x:auto; }
        [data-baseweb="tab"] { white-space:nowrap; }
        .sidebar-author { position:relative; left:auto; bottom:auto; width:auto; margin-top:16px; }
        .st-key-relative_top [data-testid="stHorizontalBlock"],
        .st-key-relative_filters [data-testid="stHorizontalBlock"] { flex-wrap:wrap !important; }
        .st-key-relative_top [data-testid="stColumn"],
        .st-key-relative_filters [data-testid="stColumn"] { min-width:100% !important; flex:1 1 100% !important; }
        .mock-summary-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
        .mock-multiples, .mock-peers, .mock-dcf-summary {
            height:auto; min-height:0; overflow:visible;
        }
        .st-key-relative_preview {
            height:auto !important; min-height:0 !important; max-height:none !important; overflow:visible;
        }
        .st-key-relative_preview_button { top:0; padding-bottom:4px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)
 
# =============================================================
# DATA: companies, categories, risk, notes
# =============================================================
COMPANIES = {
    "Apple": "AAPL", "Palantir": "PLTR", "Nvidia": "NVDA",
    "Tesla": "TSLA", "Microsoft": "MSFT", "Amazon": "AMZN", "Alphabet / Google": "GOOGL",
    "Meta": "META", "AMD": "AMD", "Broadcom": "AVGO", "JPMorgan Chase": "JPM",
    "Goldman Sachs": "GS", "Visa": "V", "Berkshire Hathaway": "BRK-B",
    "Lockheed Martin": "LMT", "Rocket Lab": "RKLB", "SoFi": "SOFI",
    "Uber": "UBER", "AST SpaceMobile": "ASTS",
}
 
SLEEPER_STOCKS = ["Rocket Lab", "SoFi", "AST SpaceMobile"]
 
CATEGORIES = {
    "Apple": "Big Tech", "Palantir": "AI / Data", "Nvidia": "AI / Semiconductors",
    "Tesla": "EV / Energy", "Microsoft": "Cloud / AI",
    "Amazon": "E-commerce / Cloud", "Alphabet / Google": "Search / AI", "Meta": "Social / AI",
    "AMD": "Semiconductors", "Broadcom": "Semiconductors", "JPMorgan Chase": "Banking",
    "Goldman Sachs": "Investment Banking", "Visa": "Payments", "Berkshire Hathaway": "Conglomerate",
    "Lockheed Martin": "Defense", "Rocket Lab": "Space", "SoFi": "Fintech",
    "Uber": "Mobility / Delivery", "AST SpaceMobile": "Space / Telecom",
}
 
RISK_LEVELS = {
    "Apple": "Lower", "Palantir": "High", "Nvidia": "Medium",
    "Tesla": "High", "Microsoft": "Lower", "Amazon": "Medium", "Alphabet / Google": "Lower",
    "Meta": "Medium", "AMD": "High", "Broadcom": "Medium", "JPMorgan Chase": "Lower",
    "Goldman Sachs": "Medium", "Visa": "Lower", "Berkshire Hathaway": "Lower",
    "Lockheed Martin": "Lower", "Rocket Lab": "High", "SoFi": "High",
    "Uber": "Medium", "AST SpaceMobile": "Very High",
}
 
NOTES = {
    "Apple": "Apple is one of the biggest consumer technology companies in the world, best known for creating the iPhone, Mac, and iPad. I like Apple because it has a loyal customer base, recurring revenue from services, consistent cash flow, and strong brand power. The main risk is that growth could slow if iPhone demand weakens or if Apple struggles to stay competitive in AI features and new product categories.",
    "Palantir": "Palantir is a software company that helps governments and businesses organize data, use AI, and make better decisions. I like Palantir because it has strong exposure to artificial intelligence, defense, and commercial software growth. The main risk is that the stock can trade at a high valuation, so the company has to keep growing fast to meet investor expectations.",
    "Nvidia": "Nvidia is one of the world's largest semiconductor companies, best known for creating GPUs used in gaming, data centers, and, most importantly, artificial intelligence. I like Nvidia because it is one of the main companies benefiting from the growth of AI infrastructure and cloud computing. The main risk is that the stock already has high expectations built in, so any slowdown in AI demand could hurt the valuation.",
    "Tesla": "Tesla is an electric vehicle and energy company focused on EVs, batteries, charging, energy storage, and autonomous driving. I like Tesla because it has a strong brand and could benefit if electric vehicles, energy storage, and self-driving technology continue to grow. The main risk is that EV competition is increasing and the stock often trades based on aggressive future expectations.",
    "Microsoft": "Microsoft is one of the largest technology companies in the world, with businesses in software, cloud computing, gaming, cybersecurity, and artificial intelligence. I like Microsoft because it has recurring revenue, strong enterprise customers, and major exposure to AI through Azure and its software products. The main risk is that growth could slow if cloud demand weakens or if AI spending does not turn into strong profits.",
    "Amazon": "Amazon is a massive technology company best known for e-commerce, AWS cloud computing, advertising, logistics, and digital services. I like Amazon because AWS and advertising are high-margin businesses that could keep driving long-term earnings growth. The main risk is that the retail side of the business can have thin margins and Amazon faces strong competition in multiple industries.",
    "Alphabet / Google": "Alphabet is the parent company of Google, YouTube, Google Cloud, and several artificial intelligence businesses. I like Alphabet because search advertising is extremely profitable and the company has major resources to compete in AI. The main risk is that AI could disrupt traditional search and regulators could continue putting pressure on the company.",
    "Meta": "Meta is a technology company that owns Facebook, Instagram, WhatsApp, and other social media platforms. I like Meta because its advertising business is highly profitable and AI could improve content, ad targeting, and user engagement. The main risk is that social media trends can change quickly and the company spends a lot of money on long-term projects.",
    "AMD": "AMD is a semiconductor company that makes CPUs, GPUs, and data center chips. I like AMD because it has gained market share in important chip markets and could benefit from growth in AI and data centers. The main risk is that AMD competes against very strong companies like Nvidia and Intel.",
    "Broadcom": "Broadcom is a semiconductor and infrastructure software company with exposure to chips, networking, data centers, and enterprise software. I like Broadcom because it has strong cash flow and could benefit from AI-related demand for networking and data infrastructure. The main risk is that parts of the business are cyclical and depend on large technology spending cycles.",
    "JPMorgan Chase": "JPMorgan Chase is one of the largest banks in the world, with businesses in consumer banking, investment banking, asset management, and trading. I like JPMorgan because it is well diversified, financially strong, and has stronger leadership than many other banks. The main risk is that banks can be hurt by recessions, loan losses, and changes in interest rates.",
    "Goldman Sachs": "Goldman Sachs is a major investment bank focused on investment banking, trading, asset management, and wealth management. I like Goldman Sachs because it has strong exposure to dealmaking, capital markets, and high-net-worth clients. The main risk is that investment banking revenue can slow down when markets are weak or companies are doing fewer deals.",
    "Visa": "Visa is a global payments company that earns revenue when transactions move across its network. I like Visa because it has strong margins, global scale, and benefits from the long-term shift away from cash. The main risk is that regulation, fintech competition, or pressure on payment fees could hurt future growth.",
    "Berkshire Hathaway": "Berkshire Hathaway is a diversified holding company with businesses in insurance, railroads, energy, cash investments, and a large stock portfolio. I like Berkshire because it is financially strong, conservative, and diversified across many parts of the economy. The main risk is that future returns may be lower as the company gets larger and moves further beyond Warren Buffett's leadership era.",
    "Lockheed Martin": "Lockheed Martin is a major defense company that builds aircraft, missiles, space systems, and military technology. I like Lockheed Martin because defense spending is usually more stable than many other industries and geopolitical tensions can support demand. The main risk is that the company depends heavily on government contracts and political budget decisions.",
    "Rocket Lab": "Rocket Lab is a smaller space company focused on rocket launches, satellites, and space systems. I like Rocket Lab as a sleeper stock because it has exposure to the growing space economy but is still much smaller than the largest players. The main risk is that the company is still high-risk and needs strong execution to prove it can scale profitably.",
    "SoFi": "SoFi is a fintech and banking company that offers lending, banking, investing, and personal finance products. I like SoFi as a sleeper stock because it could grow if it keeps adding members, deposits, and financial products over time. The main risk is that loan losses, credit quality, and competition from banks could hurt the business.",
    "Uber": "Uber is a platform company focused on ridesharing, food delivery, freight, and mobility services. I like Uber because it has a large global network and has become more focused on profitability. The main risk is that regulation, driver costs, and competition could pressure margins.",
    "AST SpaceMobile": "AST SpaceMobile is a space and telecom company trying to connect regular smartphones directly to satellites. I like AST SpaceMobile as a high-risk sleeper stock because the potential market could be huge if the technology works and scales. The main risk is that the business is expensive, unproven, and may need a lot of capital before becoming profitable.",
}
 
PERIOD_MAP = {"1M": "1mo", "6M": "6mo", "1Y": "1y", "3Y": "3y", "5Y": "5y", "Max": "max"}

PEER_GROUPS = {
    "Apple": ["Microsoft", "Alphabet / Google", "Meta", "Amazon"],
    "Microsoft": ["Apple", "Alphabet / Google", "Amazon", "Meta"],
    "Alphabet / Google": ["Meta", "Microsoft", "Amazon", "Apple"],
    "Meta": ["Alphabet / Google", "Microsoft", "Amazon", "Apple"],
    "Amazon": ["Microsoft", "Alphabet / Google", "Meta", "Apple"],
    "Nvidia": ["AMD", "Broadcom", "Microsoft"],
    "AMD": ["Nvidia", "Broadcom", "Microsoft"],
    "Broadcom": ["Nvidia", "AMD", "Microsoft"],
    "Palantir": ["Microsoft", "Alphabet / Google", "Amazon"],
    "Tesla": ["Uber", "Apple", "Amazon"],
    "JPMorgan Chase": ["Goldman Sachs", "Visa", "Berkshire Hathaway", "SoFi"],
    "Goldman Sachs": ["JPMorgan Chase", "Visa", "Berkshire Hathaway", "SoFi"],
    "Visa": ["JPMorgan Chase", "Goldman Sachs", "SoFi"],
    "Berkshire Hathaway": ["JPMorgan Chase", "Goldman Sachs", "Lockheed Martin"],
    "Lockheed Martin": ["Rocket Lab", "AST SpaceMobile", "Berkshire Hathaway"],
    "Rocket Lab": ["AST SpaceMobile", "Lockheed Martin", "Palantir"],
    "AST SpaceMobile": ["Rocket Lab", "Lockheed Martin", "Palantir"],
    "SoFi": ["JPMorgan Chase", "Goldman Sachs", "Visa"],
    "Uber": ["Tesla", "Amazon", "Meta"],
}
MEGA_CAP_TECH = ["Apple", "Microsoft", "Alphabet / Google", "Meta", "Amazon"]
 
# =============================================================
# DATA FUNCTIONS
# =============================================================
@st.cache_data(ttl=300)
def get_stock_data(symbol, selected_period, selected_interval):
    try:
        data = yf.Ticker(symbol).history(
            period=selected_period,
            interval=selected_interval,
        )
        return data if isinstance(data, pd.DataFrame) else pd.DataFrame()
    except Exception:
        logger.exception("Could not load price history for %s", symbol)
        return pd.DataFrame()
 
 
@st.cache_data(ttl=600)
def get_market_data(companies):
    """Returns (comparison_df, equal-weight basket series as list)."""
    rows, closes = [], {}
    for company, symbol in companies.items():
        base = {
            "Company": company, "Ticker": symbol, "Current Price": None,
            "Daily Change %": None, "1Y Return %": None, "52W High": None, "52W Low": None,
            "Category": CATEGORIES.get(company, "N/A"), "Risk Level": RISK_LEVELS.get(company, "N/A"),
        }
        try:
            hist = yf.Ticker(symbol).history(period="1y", interval="1d")
            if hist.empty:
                rows.append(base); continue
            last_close = hist["Close"].iloc[-1]
            prev_close = hist["Close"].iloc[-2] if len(hist) > 1 else last_close
            first_close = hist["Close"].iloc[0]
            base.update({
                "Current Price": last_close,
                "Daily Change %": ((last_close - prev_close) / prev_close) * 100 if prev_close else 0,
                "1Y Return %": ((last_close - first_close) / first_close) * 100 if first_close else 0,
                "52W High": hist["High"].max(), "52W Low": hist["Low"].min(),
            })
            closes[company] = hist["Close"]
            rows.append(base)
        except Exception:
            logger.exception("Could not load market data for %s", symbol)
            rows.append(base)
 
    df = pd.DataFrame(rows)
 
    basket = equal_weight_index(closes)
    return df, basket
 
 
@st.cache_data(ttl=600)
def get_index_series(symbol):
    try:
        h = yf.Ticker(symbol).history(period="1y", interval="1d")
        if h.empty:
            return None, None, []
        close = h["Close"].dropna()
        last, first = close.iloc[-1], close.iloc[0]
        chg = (last - first) / first * 100 if first else 0
        return float(last), float(chg), close.tolist()
    except Exception:
        logger.exception("Could not load index data for %s", symbol)
        return None, None, []


@st.cache_data(ttl=3600)
def get_risk_free_rate():
    """Use the live 10-year Treasury yield proxy, with a documented fallback."""
    try:
        history = yf.Ticker("^TNX").history(period="5d", interval="1d")
        if not history.empty:
            rate = float(history["Close"].dropna().iloc[-1]) / 100.0
            if 0.0 < rate < 0.15:
                return rate
    except Exception:
        logger.exception("Could not load the 10-year Treasury yield")
    return 0.0425
 
 
@st.cache_data(ttl=900)
def get_fundamentals(symbol):
    try:
        return yf.Ticker(symbol).info or {}
    except Exception:
        logger.exception("Could not load fundamentals for %s", symbol)
        return {}
 
 
@st.cache_data(ttl=900)
def get_financials(symbol):
    out = {"years": [], "revenue": [], "net_income": [], "ocf": [], "error": None}
    try:
        t = yf.Ticker(symbol)
        inc = getattr(t, "income_stmt", None)
        if inc is None or inc.empty:
            inc = t.financials
        cf = getattr(t, "cashflow", None)
        if inc is None or inc.empty:
            return out
        cols = list(inc.columns)[:5][::-1]  # oldest -> newest
        for c in cols:
            yr = c.year if hasattr(c, "year") else str(c)
            rev = statement_value(inc, ["Total Revenue", "Operating Revenue"], c)
            ni = statement_value(inc, ["Net Income", "Net Income Common Stockholders"], c)
            ocf = statement_value(
                cf,
                ["Operating Cash Flow", "Total Cash From Operating Activities"],
                c,
            )
            if rev is None and ni is None and ocf is None:
                continue
            out["years"].append(str(yr))
            out["revenue"].append(rev)
            out["net_income"].append(ni)
            out["ocf"].append(ocf)
    except Exception:
        logger.exception("Could not load financial statements for %s", symbol)
        out["error"] = "Financial statement data could not be loaded."
    return out


@st.cache_data(ttl=900)
def get_financial_statements(symbol, quarterly=False):
    """Load the three reported statement tables without manufacturing gaps."""
    empty = {"income": pd.DataFrame(), "balance": pd.DataFrame(), "cashflow": pd.DataFrame(), "error": None}
    try:
        company = yf.Ticker(symbol)
        if quarterly:
            empty["income"] = getattr(company, "quarterly_income_stmt", pd.DataFrame())
            empty["balance"] = getattr(company, "quarterly_balance_sheet", pd.DataFrame())
            empty["cashflow"] = getattr(company, "quarterly_cashflow", pd.DataFrame())
        else:
            empty["income"] = getattr(company, "income_stmt", pd.DataFrame())
            empty["balance"] = getattr(company, "balance_sheet", pd.DataFrame())
            empty["cashflow"] = getattr(company, "cashflow", pd.DataFrame())
        return empty
    except Exception:
        logger.exception("Could not load financial statements for %s", symbol)
        empty["error"] = "Financial statement data could not be loaded."
        return empty


@st.cache_data(ttl=1800)
def get_company_metrics(company_names):
    """Load comparable company metrics only on pages that need them."""
    rows = []
    for company_name in company_names:
        symbol = COMPANIES[company_name]
        info = get_fundamentals(symbol)
        revenue = g(info, "totalRevenue")
        free_cash_flow = g(info, "freeCashflow")
        market_cap = g(info, "marketCap")
        rows.append({
            "Company": company_name,
            "Ticker": symbol,
            "Sector": g(info, "sector"),
            "Industry": g(info, "industry"),
            "Market Cap": market_cap,
            "P/E TTM": g(info, "trailingPE"),
            "EV / EBITDA": g(info, "enterpriseToEbitda"),
            "Revenue Growth": g(info, "revenueGrowth"),
            "Profit Margin": g(info, "profitMargins"),
            "Operating Margin": g(info, "operatingMargins"),
            "FCF Margin": (free_cash_flow / revenue) if free_cash_flow is not None and revenue else None,
            "Price / FCF": (market_cap / free_cash_flow) if market_cap is not None and free_cash_flow and free_cash_flow > 0 else None,
        })
    return pd.DataFrame(rows)


@st.cache_data(ttl=900)
def get_peer_price_history(company_names, period="3y"):
    series = {}
    for company_name in company_names:
        symbol = COMPANIES[company_name]
        data = get_stock_data(symbol, period, "1d")
        if not data.empty and "Close" in data:
            close = pd.to_numeric(data["Close"], errors="coerce").dropna()
            if len(close) >= 2:
                series[f"{company_name} ({symbol})"] = close / close.iloc[0] * 100.0
    return pd.DataFrame(series)


@st.cache_data(ttl=900)
def get_dcf_financials(symbol):
    """Load annual statement inputs needed for a company-specific FCFF DCF."""
    out = {"history": [], "cash": None, "debt": None, "error": None}
    try:
        company = yf.Ticker(symbol)
        income = getattr(company, "income_stmt", None)
        if income is None or income.empty:
            income = company.financials
        cash_flow = getattr(company, "cashflow", None)
        balance = getattr(company, "balance_sheet", None)
        if income is None or income.empty:
            out["error"] = "Annual income-statement data is unavailable."
            return out

        periods = list(income.columns)[:4][::-1]
        for period in periods:
            revenue = statement_value(
                income,
                ["Total Revenue", "Operating Revenue"],
                period,
            )
            net_income = statement_value(
                income,
                ["Net Income", "Net Income Common Stockholders"],
                period,
            )
            operating_income = statement_value(income, ["Operating Income", "EBIT"], period)
            diluted_average_shares = statement_value(
                income,
                ["Diluted Average Shares", "Basic Average Shares"],
                period,
            )
            book_equity = statement_value(
                balance,
                ["Stockholders Equity", "Common Stock Equity", "Total Equity Gross Minority Interest"],
                period,
            )
            pretax_income = statement_value(
                income,
                ["Pretax Income", "Income Before Tax"],
                period,
            )
            tax_provision = statement_value(income, ["Tax Provision"], period)
            interest = statement_value(
                income,
                ["Interest Expense", "Interest Expense Non Operating"],
                period,
            )
            operating_cash_flow = statement_value(
                cash_flow,
                ["Operating Cash Flow", "Total Cash From Operating Activities"],
                period,
            )
            capital_expenditure = statement_value(
                cash_flow,
                ["Capital Expenditure", "Capital Expenditures"],
                period,
            )
            reported_fcf = statement_value(cash_flow, ["Free Cash Flow"], period)

            if pretax_income and pretax_income > 0 and tax_provision is not None:
                tax_rate = max(0.0, min(0.35, tax_provision / pretax_income))
            else:
                tax_rate = 0.21

            levered_fcf = reported_fcf
            if levered_fcf is None and operating_cash_flow is not None:
                levered_fcf = operating_cash_flow - abs(capital_expenditure or 0.0)
            fcff = None
            if levered_fcf is not None:
                fcff = levered_fcf + abs(interest or 0.0) * (1.0 - tax_rate)

            if revenue is None and fcff is None and net_income is None:
                continue
            year = period.year if hasattr(period, "year") else str(period)
            out["history"].append(
                {
                    "year": str(year),
                    "revenue": revenue,
                    "fcff": fcff,
                    "net_income": net_income,
                    "operating_income": operating_income,
                    "operating_cash_flow": operating_cash_flow,
                    "capital_expenditure": capital_expenditure,
                    "diluted_average_shares": diluted_average_shares,
                    "book_equity": book_equity,
                    "interest": interest,
                    "tax_rate": tax_rate,
                }
            )

        if balance is not None and not balance.empty:
            latest_period = balance.columns[0]
            out["cash"] = statement_value(
                balance,
                [
                    "Cash Cash Equivalents And Short Term Investments",
                    "Cash And Cash Equivalents",
                    "Cash Financial",
                ],
                latest_period,
            )
            out["debt"] = statement_value(
                balance,
                ["Total Debt", "Total Non Current Liabilities Net Minority Interest"],
                latest_period,
            )
    except Exception:
        logger.exception("Could not load DCF financials for %s", symbol)
        out["error"] = "The reported financial inputs needed for a DCF could not be loaded."
    return out
 
 
# ---- small helpers ----
def top_mover(df, col):
    s = pd.to_numeric(df[col], errors="coerce")
    if s.dropna().empty:
        return None, None
    idx = s.idxmax()
    return df.loc[idx, "Company"], float(s.loc[idx])
 
 
def downsample(seq, n=34):
    seq = [v for v in seq if v is not None and not (isinstance(v, float) and pd.isna(v))]
    if len(seq) <= n:
        return seq
    step = len(seq) / n
    return [seq[min(len(seq) - 1, int(i * step))] for i in range(n)]
 
 
def sparkline_svg(values, color, width=110, height=34):
    vals = downsample(values, 34)
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1
    n = len(vals)
    pts = " ".join(
        f"{i/(n-1)*width:.1f},{height - (v-lo)/rng*(height-4) - 2:.1f}" for i, v in enumerate(vals)
    )
    return (
        f'<svg class="spark" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="none"><polyline points="{pts}" fill="none" stroke="{color}" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    )
 
 
def fmt_big(n):
    if n is None or (isinstance(n, float) and pd.isna(n)):
        return "—"
    a = abs(n)
    for div, suf in [(1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")]:
        if a >= div:
            return f"${n/div:,.2f}{suf}"
    return f"${n:,.0f}"
 
 
def g(info, key):
    v = info.get(key)
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    return v
 
 
def fmt_x(v, suffix=""):
    return f"{v:,.2f}{suffix}" if v is not None else "—"
 
 
def fmt_pct(v):
    return f"{v:,.2f}%" if v is not None else "—"
 
 
# =============================================================
# SIDEBAR  (brand + nav + controls)
# =============================================================
st.sidebar.markdown(
    """
    <div class="sb-brand">
        <div class="mark">↗</div>
        <div><div class="t">Equity Research <span class="accent">Dashboard</span></div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

PAGES = [
    "Overview", "Price & Chart", "Financial Statements", "Company Analysis",
    "Research Universe", "Research Notes", "DCF Model", "Relative Valuation",
    "Risk & Performance", "Peer Comparison", "Monte Carlo — Coming Soon",
    "Company Profile", "Sources & Methodology", "About",
]

LEGACY_PAGE_NAMES = {
    "🏠  Overview": "Overview",
    "📊  Company Analysis": "Company Analysis",
    "📈  Financials": "Financial Statements",
    "💲  Valuation": "DCF Model",
    "⭐  Watchlist": "Research Universe",
    "📓  Notebook": "Research Notes",
    "⚙️  Settings": "About",
}
LEGACY_PAGE_NAMES.update({
    "Financials": "Financial Statements",
    "Valuation": "DCF Model",
    "Watchlist": "Research Universe",
})
for state_key in ("active_page", "mobile_navigation"):
    if st.session_state.get(state_key) in LEGACY_PAGE_NAMES:
        st.session_state[state_key] = LEGACY_PAGE_NAMES[st.session_state[state_key]]

NAV_GROUPS = {
    "RESEARCH": ["Overview", "Price & Chart", "Financial Statements", "Company Analysis", "Research Universe", "Research Notes"],
    "VALUATION & RISK": ["DCF Model", "Relative Valuation", "Risk & Performance", "Peer Comparison", "Monte Carlo — Coming Soon"],
    "REFERENCE": ["Company Profile", "Sources & Methodology", "About"],
}


def nav_key(group_name):
    return f"nav_{group_name.lower()}"


def sync_sidebar_navigation(group_name):
    selected = st.session_state.get(nav_key(group_name))
    if not selected:
        return
    st.session_state["active_page"] = selected
    st.session_state["mobile_navigation"] = selected
    for other_group in NAV_GROUPS:
        if other_group != group_name:
            st.session_state[nav_key(other_group)] = None


def sync_mobile_navigation():
    st.session_state["active_page"] = st.session_state["mobile_navigation"]
    selected = st.session_state["mobile_navigation"]
    for group_name, group_pages in NAV_GROUPS.items():
        st.session_state[nav_key(group_name)] = selected if selected in group_pages else None


if st.session_state.get("active_page") not in PAGES:
    st.session_state["active_page"] = PAGES[0]
if st.session_state.get("mobile_navigation") not in PAGES:
    st.session_state["mobile_navigation"] = st.session_state["active_page"]
st.session_state.setdefault("active_page", PAGES[0])
st.session_state.setdefault("mobile_navigation", st.session_state["active_page"])

for group_name, group_pages in NAV_GROUPS.items():
    group_key = nav_key(group_name)
    if group_key not in st.session_state:
        st.session_state[group_key] = (
            st.session_state["active_page"] if st.session_state["active_page"] in group_pages else None
        )
    st.sidebar.markdown(f"<div class='nav-title'>{group_name}</div>", unsafe_allow_html=True)
    st.sidebar.radio(
        group_name,
        group_pages,
        index=None,
        label_visibility="collapsed",
        key=group_key,
        on_change=sync_sidebar_navigation,
        args=(group_name,),
    )

st.sidebar.markdown(
    """<div class="sidebar-author"><div class="row"><div class="icon">↗</div>
    <div><div class="name">Built by Garrett Ewy</div>
    <div class="role">Quantitative Equity Research</div></div></div>
    <div class="version">v2.0.0</div></div>""",
    unsafe_allow_html=True,
)
 
# Heavy universe data is loaded later, only on pages that use it.
comparison_df = pd.DataFrame()
basket = []
sp_last, sp_chg, sp_series = None, None, []
 
 
# =============================================================
# REUSABLE RENDER BLOCKS
# =============================================================
def page_head(title, sub=""):
    st.markdown(
        f"""<div class="page-head"><div class="title">{title}</div>
        <div class="sub">{sub}</div></div>""",
        unsafe_allow_html=True,
    )


def security_header(info):
    """Keep company and quote context visible across research pages."""
    name = escape(str(g(info, "longName") or selected_company))
    sector = escape(str(g(info, "sector") or CATEGORIES.get(selected_company, "Sector unavailable")))
    industry = escape(str(g(info, "industry") or "Industry unavailable"))
    exchange = escape(str(g(info, "fullExchangeName") or g(info, "exchange") or "Exchange unavailable"))

    price = g(info, "currentPrice") or g(info, "regularMarketPrice")
    change = g(info, "regularMarketChange")
    change_pct = g(info, "regularMarketChangePercent")
    if price is None or change is None or change_pct is None:
        quote_history = get_stock_data(ticker, "5d", "1d")
        closes = quote_history["Close"].dropna() if not quote_history.empty and "Close" in quote_history else pd.Series(dtype=float)
        if not closes.empty and price is None:
            price = float(closes.iloc[-1])
        if len(closes) >= 2:
            change = float(closes.iloc[-1] - closes.iloc[-2]) if change is None else change
            change_pct = float(change / closes.iloc[-2] * 100.0) if change_pct is None and closes.iloc[-2] else change_pct

    quote_time = g(info, "regularMarketTime")
    if quote_time:
        updated = pd.to_datetime(quote_time, unit="s", utc=True).tz_convert("America/Chicago")
        timestamp = updated.strftime("%b %d, %Y · %I:%M %p CT")
    else:
        timestamp = "Timestamp unavailable"

    price_text = format_price(price) if price is not None else "Data unavailable"
    if change is not None and change_pct is not None:
        direction = "pos" if change >= 0 else "neg"
        change_text = f"{change:+,.2f} ({change_pct:+.2f}%)"
    else:
        direction = "neutral"
        change_text = "Change unavailable"

    symbol_class = " apple-mark" if ticker == "AAPL" else ""
    symbol_content = "<span class='apple-body'></span>" if ticker == "AAPL" else escape(ticker)

    st.markdown(
        f"""<div class="security-header">
        <div class="security-id">
            <div class="security-symbol{symbol_class}">{symbol_content}</div>
            <div><div class="security-name">{name}<span class="ticker-badge">{escape(ticker)}</span></div>
            <div class="security-meta">{sector} · {industry} · {exchange}</div></div>
        </div>
        <div class="security-quote">
            <div class="security-price">{price_text}</div>
            <div class="security-change {direction}">{change_text}</div>
            <div class="security-stamp">Latest available quote · {timestamp}<br>Yahoo Finance via yfinance</div>
        </div></div>""",
        unsafe_allow_html=True,
    )


def research_note_block(compact=False):
    """Present authored commentary separately from sourced market facts."""
    note = NOTES[selected_company]
    if compact and len(note) > 330:
        note = note[:330].rsplit(" ", 1)[0] + "…"
    st.markdown(
        f"""<div class="research-note">
        <div class="eyebrow">Research Notes · Author viewpoint</div>
        <div class="title">{escape(selected_company)} — Investment thesis</div>
        <div class="body">{escape(note)}</div>
        <div class="source">Commentary by Garrett Ewy. This is personal research analysis, not sourced company data or an investment recommendation.</div>
        </div>""",
        unsafe_allow_html=True,
    )
 
 
def summary_cards():
    if basket:
        b_ret = basket[-1] - basket[0]
        b_cls = "pos" if b_ret >= 0 else "neg"
        b_arrow = "▲" if b_ret >= 0 else "▼"
        b_spark = sparkline_svg(basket, GREEN if b_ret >= 0 else RED)
        b_val = f"{b_ret:+.2f}%"
    else:
        b_cls, b_arrow, b_spark, b_val = "neutral", "", "", "—"
 
    if sp_last is not None:
        sp_cls = "pos" if sp_chg >= 0 else "neg"
        sp_arrow = "▲" if sp_chg >= 0 else "▼"
        sp_spark = sparkline_svg(sp_series, GREEN if sp_chg >= 0 else RED)
    else:
        sp_cls, sp_arrow, sp_spark = "neutral", "", ""
 
    gname, gval = top_mover(comparison_df, "Daily Change %")
    yname, yval = top_mover(comparison_df, "1Y Return %")
 
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f"""<div class="sum-card"><div class="label">{len(COMPANIES)}-Stock Basket · Up to 1Y</div>
            <div class="row"><div class="value">{b_val}</div>{b_spark}</div>
            <div class="sub {b_cls}">{b_arrow} Equal-weight daily returns</div></div>""",
            unsafe_allow_html=True,
        )
    with c2:
        sp_show = f"{sp_last:,.0f}" if sp_last is not None else "—"
        sp_sub = f"{sp_arrow} {sp_chg:+.2f}% 1Y" if sp_last is not None else "Data unavailable"
        st.markdown(
            f"""<div class="sum-card"><div class="label">S&amp;P 500 · ^GSPC</div>
            <div class="row"><div class="value">{sp_show}</div>{sp_spark}</div>
            <div class="sub {sp_cls}">{sp_sub}</div></div>""",
            unsafe_allow_html=True,
        )
    with c3:
        if gname is not None:
            st.markdown(
                f"""<div class="sum-card"><div class="label">Top Gainer · 1D</div>
                <div class="row"><div class="value sm">{gname}</div></div>
                <div class="sub pos">▲ {gval:+.2f}%</div></div>""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """<div class="sum-card"><div class="label">Top Gainer · 1D</div>
                <div class="row"><div class="value sm">—</div></div>
                <div class="sub neutral">Data unavailable</div></div>""",
                unsafe_allow_html=True,
            )
    with c4:
        if yname is not None:
            ycls = "pos" if yval >= 0 else "neg"
            yarrow = "▲" if yval >= 0 else "▼"
            st.markdown(
                f"""<div class="sum-card"><div class="label">Best Performer · Up to 1Y</div>
                <div class="row"><div class="value sm">{yname}</div></div>
                <div class="sub {ycls}">{yarrow} {yval:+.1f}%</div></div>""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """<div class="sum-card"><div class="label">Best Performer · Up to 1Y</div>
                <div class="row"><div class="value sm">—</div></div>
                <div class="sub neutral">Data unavailable</div></div>""",
                unsafe_allow_html=True,
            )
 
 
def price_chart(height=430, key="period_main", selected_interval="1d", chart_type="Candlestick", show_volume=False):
    pcols = st.columns([3, 2])
    with pcols[1]:
        sel = st.radio("period", list(PERIOD_MAP.keys()), index=2, horizontal=True,
                       key=key, label_visibility="collapsed")
    period = PERIOD_MAP[sel]
    data = get_stock_data(ticker, period, selected_interval)
    if data.empty:
        st.error("Could not load price data for this ticker (may be unavailable or rate-limited).")
        return None
 
    data = data.reset_index()
    data["MA50"] = data["Close"].rolling(50).mean()
    data["MA200"] = data["Close"].rolling(200).mean()
 
    fig = go.Figure()
    if chart_type == "Candlestick":
        fig.add_trace(go.Candlestick(
            x=data["Date"], open=data["Open"], high=data["High"], low=data["Low"], close=data["Close"],
            name="Price",
            increasing=dict(line=dict(color=GREEN), fillcolor=GREEN),
            decreasing=dict(line=dict(color=RED), fillcolor=RED),
        ))
    else:
        fig.add_trace(go.Scatter(
            x=data["Date"], y=data["Close"], mode="lines", name="Close",
            line=dict(color=BLUE_LT, width=2.2),
        ))
    fig.add_trace(go.Scatter(x=data["Date"], y=data["MA50"], mode="lines",
                             name="MA50", line=dict(color=ORANGE, width=1.7)))
    fig.add_trace(go.Scatter(x=data["Date"], y=data["MA200"], mode="lines",
                             name="MA200", line=dict(color=BLUE_LT, width=1.7)))
    fig.update_layout(
        template="plotly_white", height=height, xaxis_rangeslider_visible=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, family="Inter"), margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(gridcolor="rgba(15,31,61,0.08)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(15,31,61,0.08)", zeroline=False)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    if show_volume and "Volume" in data:
        volume = go.Figure(go.Bar(
            x=data["Date"], y=data["Volume"], name="Volume", marker_color="#315b86",
        ))
        volume.update_layout(
            template="plotly_white", height=180, paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT, family="Inter"),
            margin=dict(l=10, r=10, t=10, b=10), showlegend=False, yaxis_title="Volume",
        )
        volume.update_xaxes(gridcolor="rgba(15,31,61,0.08)")
        volume.update_yaxes(gridcolor="rgba(15,31,61,0.08)")
        st.plotly_chart(volume, width="stretch", config={"displayModeBar": False})
    return data
 
 
def watchlist_table(df, limit=None):
    rows = ""
    view = df if limit is None else df.head(limit)
    for _, r in view.iterrows():
        price = f"${r['Current Price']:,.2f}" if pd.notna(r["Current Price"]) else "—"
        d, y = r["Daily Change %"], r["1Y Return %"]
        dcls = "pos" if (pd.notna(d) and d >= 0) else "neg"
        ycls = "pos" if (pd.notna(y) and y >= 0) else "neg"
        dtxt = f"{d:+.2f}%" if pd.notna(d) else "—"
        ytxt = f"{y:+.1f}%" if pd.notna(y) else "—"
        rows += (
            f"<tr><td>{r['Ticker']}</td><td>{price}</td>"
            f"<td class='{dcls}'>{dtxt}</td><td class='{ycls}'>{ytxt}</td></tr>"
        )
    st.markdown(
        f"""<div class="panel"><h4>Watchlist</h4><div class="wl-scroll"><table class="wl">
        <thead><tr><th>Symbol</th><th>Price</th><th>1D %</th><th>Up to 1Y %</th></tr></thead>
        <tbody>{rows}</tbody></table></div></div>""",
        unsafe_allow_html=True,
    )
 
 
def stat_grid(title, pairs):
    tiles = "".join(
        f"<div class='stat'><div class='k'>{k}</div><div class='v'>{'Data unavailable' if v == '—' else v}</div></div>"
        for k, v in pairs
    )
    st.markdown(f"<div class='panel'><h4>{title}</h4><div class='stat-grid'>{tiles}</div></div>",
                unsafe_allow_html=True)
 
 
def fundamentals_pairs(info):
    de = debt_to_equity_ratio(info)
    dy = dividend_yield_percent(info)
    roe = g(info, "returnOnEquity")
    pm = g(info, "profitMargins")
    return [
        ("Market Cap", fmt_big(g(info, "marketCap"))),
        ("P/E (TTM)", fmt_x(g(info, "trailingPE"))),
        ("EPS (TTM)", fmt_x(g(info, "trailingEps"))),
        ("Revenue (TTM)", fmt_big(g(info, "totalRevenue"))),
        ("ROE", fmt_pct(roe * 100) if roe is not None else "—"),
        ("Profit Margin", fmt_pct(pm * 100) if pm is not None else "—"),
        ("Debt / Equity", fmt_x(de) if de is not None else "—"),
        ("Dividend Yield", fmt_pct(dy) if dy is not None else "—"),
        ("Beta (5Y)", fmt_x(g(info, "beta"))),
    ]
 
 
def company_card(info):
    name = g(info, "longName") or selected_company
    sector = g(info, "sector") or CATEGORIES.get(selected_company, "")
    industry = g(info, "industry") or ""
 
    row = comparison_df[comparison_df["Company"] == selected_company]
    price, dtxt, ytxt, dcls, ycls = "—", "—", "—", "neutral", "neutral"
    if not row.empty:
        rr = row.iloc[0]
        if pd.notna(rr["Current Price"]):
            price = f"${rr['Current Price']:,.2f}"
        d, y = rr["Daily Change %"], rr["1Y Return %"]
        if pd.notna(d):
            dtxt, dcls = f"{d:+.2f}%", ("pos" if d >= 0 else "neg")
        if pd.notna(y):
            ytxt, ycls = f"{y:+.1f}%", ("pos" if y >= 0 else "neg")
 
    st.markdown(
        f"""<div class="panel">
        <div style="display:flex;align-items:center;gap:14px;margin-bottom:16px;">
            <div class="logo-badge">{ticker[:4]}</div>
            <div><div style="font-size:20px;font-weight:800;color:#f8fafc;">{name}</div>
            <div class="small-muted">{sector}{' · ' + industry if industry else ''} · {RISK_LEVELS.get(selected_company, '')} risk</div></div>
        </div>
        <div class="qstats">
            <div><div class="k">Price</div><div class="v">{price}</div></div>
            <div><div class="k">1D</div><div class="v {dcls}">{dtxt}</div></div>
            <div><div class="k">Up to 1Y</div><div class="v {ycls}">{ytxt}</div></div>
        </div></div>""",
        unsafe_allow_html=True,
    )
 
 
def financials_chart():
    fin = get_financials(ticker)
    if not fin["years"]:
        message = fin.get("error") or "Financial statement data is unavailable for this ticker."
        st.markdown("<div class='panel'><h4>Financials Overview</h4>"
                    f"<p class='small-muted'>{message}</p></div>",
                    unsafe_allow_html=True)
        return
    yrs = fin["years"]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=yrs, y=fin["revenue"], name="Revenue", marker_color=BLUE))
    fig.add_trace(go.Bar(x=yrs, y=fin["net_income"], name="Net Income", marker_color=GREEN))
    fig.add_trace(go.Bar(x=yrs, y=fin["ocf"], name="Operating Cash Flow", marker_color=PURPLE))
    fig.update_layout(
        template="plotly_white", barmode="group", height=360,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, family="Inter"), margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(gridcolor="rgba(15,31,61,0.08)")
    fig.update_yaxes(gridcolor="rgba(15,31,61,0.08)")
    st.markdown("<div style='font-size:17px;font-weight:800;color:#f8fafc;margin-bottom:6px;'>Financials Overview</div>",
                unsafe_allow_html=True)
    with st.container(border=True):
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def value_or_unavailable(value, formatter):
    return formatter(value) if value is not None else "Data unavailable"


def percent_value(value, signed=False):
    if value is None:
        return "Data unavailable"
    return f"{value * 100:+.1f}%" if signed else f"{value * 100:.1f}%"


def default_dcf_v1_snapshot(info):
    """Calculate the frozen V1 scenario values for legacy comparisons."""
    statement_data = get_dcf_financials(ticker)
    history = statement_data.get("history", [])
    current_price = g(info, "currentPrice") or g(info, "regularMarketPrice")
    shares = valuation_share_count(info)
    if not current_price or not shares:
        return None
    model_info = {**info, "_risk_free_rate": get_risk_free_rate()}
    values = {}
    if ticker in {"JPM", "GS", "SOFI"}:
        usable = [row for row in history if row.get("net_income") is not None and row.get("book_equity") is not None]
        if not usable or usable[-1]["net_income"] <= 0:
            return None
        defaults = estimate_equity_dcf_defaults(usable, model_info)
        for name in ("Bear", "Base", "Bull"):
            assumptions = equity_scenario_assumptions(defaults, name)
            try:
                values[name] = run_equity_dcf(
                    base_net_income=float(usable[-1]["net_income"]),
                    starting_roe=defaults["starting_roe"],
                    year_one_growth=assumptions["year_one_growth"],
                    final_year_growth=assumptions["final_year_growth"],
                    target_roe=assumptions["target_roe"],
                    cost_of_equity=assumptions["cost_of_equity"],
                    terminal_growth=assumptions["terminal_growth"],
                    forecast_years=assumptions["forecast_years"],
                    shares_outstanding=float(shares),
                )["value_per_share"]
            except ValueError:
                return None
    else:
        usable = [row for row in history if row.get("revenue") is not None and row.get("fcff") is not None]
        if not usable:
            return None
        defaults = estimate_defaults(usable, model_info)
        cash = g(info, "totalCash")
        debt = g(info, "totalDebt")
        cash = float(cash if cash is not None else statement_data.get("cash") or 0.0)
        debt = float(debt if debt is not None else statement_data.get("debt") or 0.0)
        for name in ("Bear", "Base", "Bull"):
            assumptions = scenario_assumptions(defaults, name)
            try:
                values[name] = run_dcf(
                    base_revenue=float(usable[-1]["revenue"]),
                    starting_fcff_margin=defaults["starting_fcff_margin"],
                    year_one_growth=assumptions["year_one_growth"],
                    final_year_growth=assumptions["final_year_growth"],
                    target_fcff_margin=assumptions["target_fcff_margin"],
                    wacc=assumptions["wacc"],
                    terminal_growth=assumptions["terminal_growth"],
                    forecast_years=assumptions["forecast_years"],
                    net_debt=debt - cash,
                    shares_outstanding=float(shares),
                )["value_per_share"]
            except ValueError:
                return None
    values["Current"] = float(current_price)
    return values


def default_dcf_v2_snapshot(info):
    """Calculate unedited V2 scenarios for public dashboard summaries."""
    statement_data = get_dcf_financials(ticker)
    history = statement_data.get("history", [])
    current_price = g(info, "currentPrice") or g(info, "regularMarketPrice")
    shares = valuation_share_count(info)
    if not current_price or not shares:
        return None
    cash = g(info, "totalCash")
    debt = g(info, "totalDebt")
    cash = float(cash if cash is not None else statement_data.get("cash") or 0.0)
    debt = float(debt if debt is not None else statement_data.get("debt") or 0.0)
    model_info = {**info, "_risk_free_rate": get_risk_free_rate(), "_equity_risk_premium": 0.045}
    try:
        defaults = build_v2_defaults(ticker, history, model_info, float(shares), debt - cash)
        if not defaults.get("suitable"):
            return None
        values = {name: run_v2_case(defaults, name)[0]["value_per_share"] for name in ("Bear", "Base", "Bull")}
    except (TypeError, ValueError):
        return None
    values["Current"] = float(current_price)
    return values


def render_overview_metrics(info, history):
    close = history["Close"].dropna() if not history.empty and "Close" in history else pd.Series(dtype=float)
    one_year = (close.iloc[-1] / close.iloc[0] - 1.0) if len(close) > 1 and close.iloc[0] else None
    pairs = [
        ("Current Price", format_price(g(info, "currentPrice") or g(info, "regularMarketPrice"))),
        ("Market Cap", value_or_unavailable(g(info, "marketCap"), fmt_big)),
        ("P/E TTM", value_or_unavailable(g(info, "trailingPE"), lambda value: f"{value:.2f}x")),
        ("Revenue TTM", value_or_unavailable(g(info, "totalRevenue"), fmt_big)),
        ("Free Cash Flow TTM", value_or_unavailable(g(info, "freeCashflow"), fmt_big)),
        ("1Y Performance", percent_value(one_year, signed=True)),
    ]
    stat_grid("Executive Snapshot", pairs)


STATEMENT_LINES = {
    "Income Statement": [
        ("Revenue", ["Total Revenue", "Operating Revenue"]),
        ("Gross Profit", ["Gross Profit"]),
        ("Operating Income", ["Operating Income"]),
        ("EBIT", ["EBIT"]),
        ("Net Income", ["Net Income", "Net Income Common Stockholders"]),
        ("Diluted EPS", ["Diluted EPS", "Basic EPS"]),
    ],
    "Balance Sheet": [
        ("Cash", ["Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents"]),
        ("Total Assets", ["Total Assets"]),
        ("Total Debt", ["Total Debt"]),
        ("Total Liabilities", ["Total Liabilities Net Minority Interest", "Total Liabilities"]),
        ("Shareholders’ Equity", ["Stockholders Equity", "Common Stock Equity"]),
    ],
    "Cash Flow Statement": [
        ("Operating Cash Flow", ["Operating Cash Flow", "Total Cash From Operating Activities"]),
        ("Capital Expenditures", ["Capital Expenditure", "Capital Expenditures"]),
        ("Free Cash Flow", ["Free Cash Flow"]),
    ],
}


def statement_display_frame(statement, definitions, quarterly=False):
    if statement is None or statement.empty:
        return pd.DataFrame()
    periods = list(statement.columns)[:6]
    rows = []
    for label, candidates in definitions:
        row = {"Line Item": label}
        available = False
        for period in periods:
            value = statement_value(statement, candidates, period)
            heading = pd.to_datetime(period).strftime("%b %Y") if not isinstance(period, str) else period
            row[heading] = value
            available = available or value is not None
        if available:
            rows.append(row)
    if rows and rows[0].get("Line Item") == "Revenue":
        revenue_row = rows[0]
        period_headings = list(revenue_row.keys())[1:]
        lag = 4 if quarterly else 1
        growth_row = {"Line Item": "Revenue Growth (YoY)"}
        has_growth = False
        for index, heading in enumerate(period_headings):
            value = revenue_row.get(heading)
            previous = revenue_row.get(period_headings[index + lag]) if index + lag < len(period_headings) else None
            growth = (value / previous - 1.0) if value is not None and previous not in (None, 0) else None
            growth_row[heading] = growth
            has_growth = has_growth or growth is not None
        if has_growth:
            rows.insert(1, growth_row)
    return pd.DataFrame(rows)


def financial_table(frame):
    headers = "".join(f"<th>{escape(str(column))}</th>" for column in frame.columns)
    body = ""
    for _, row in frame.iterrows():
        label = str(row["Line Item"])
        cells = [f"<td>{escape(label)}</td>"]
        for column in frame.columns[1:]:
            value = row[column]
            if value is None or pd.isna(value):
                text = "Data unavailable"
            elif "Growth" in label:
                text = f"{float(value):+.1%}"
            elif "EPS" in label:
                text = format_price(value)
            else:
                text = fmt_big(value)
            cells.append(f"<td>{escape(text)}</td>")
        body += f"<tr>{''.join(cells)}</tr>"
    st.markdown(
        f"<div class='financial-statement-scroll'><table class='financial-statement'>"
        f"<thead><tr>{headers}</tr></thead><tbody>{body}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def render_financial_statements():
    frequency = st.radio("Reporting frequency", ["Annual", "Quarterly"], horizontal=True, key=f"statement_frequency_{ticker}")
    quarterly = frequency == "Quarterly"
    statements = get_financial_statements(ticker, quarterly=quarterly)
    tabs = st.tabs(list(STATEMENT_LINES))
    keys = {"Income Statement": "income", "Balance Sheet": "balance", "Cash Flow Statement": "cashflow"}
    for tab, name in zip(tabs, STATEMENT_LINES):
        with tab:
            frame = statement_display_frame(statements[keys[name]], STATEMENT_LINES[name], quarterly=quarterly)
            if frame.empty:
                st.info("Data unavailable for this statement and reporting frequency.")
            else:
                financial_table(frame)
    st.caption("Reported figures from Yahoo Finance via yfinance. Missing line items are omitted rather than estimated.")
    with st.expander("Financial Trends", expanded=False):
        financials_chart()


def derived_analysis(info, dcf_values):
    strengths, risks, drivers = [], [], []
    revenue_growth = g(info, "revenueGrowth")
    operating_margin = g(info, "operatingMargins")
    fcf = g(info, "freeCashflow")
    beta = g(info, "beta")
    trailing_pe = g(info, "trailingPE")
    if revenue_growth is not None and revenue_growth > 0:
        strengths.append(f"Reported TTM revenue growth is {revenue_growth:.1%}.")
        drivers.append("Continued revenue growth is a measurable driver to monitor.")
    if operating_margin is not None and operating_margin > 0.15:
        strengths.append(f"Operating margin is {operating_margin:.1%}, indicating solid operating profitability.")
    if fcf is not None and fcf > 0:
        strengths.append(f"Reported free cash flow is positive at {fmt_big(fcf)}.")
    if beta is not None and beta > 1.3:
        risks.append(f"Beta of {beta:.2f} indicates above-market historical sensitivity.")
    if trailing_pe is not None and trailing_pe > 40:
        risks.append(f"A {trailing_pe:.1f}x trailing P/E embeds demanding expectations.")
    if fcf is not None and fcf < 0:
        risks.append("Reported free cash flow is negative, increasing forecast uncertainty.")
    if not strengths:
        strengths.append("Available reported metrics do not support a clear quantitative strength signal.")
    if not risks:
        risks.append("No single threshold-based risk signal was triggered; company-specific risks still require qualitative review.")
    industry = g(info, "industry")
    if industry:
        drivers.append(f"Execution and demand trends in {industry} are the primary operating variables to follow.")
    if not drivers:
        drivers.append("Growth-driver data is unavailable from the current provider.")
    valuation = "DCF data unavailable."
    if dcf_values and dcf_values.get("Base") and dcf_values.get("Current"):
        gap = dcf_values["Base"] / dcf_values["Current"] - 1
        valuation = f"The default Base DCF estimate is {format_price(dcf_values['Base'])}, implying {gap:+.1%} versus the latest market price. This is an assumption-driven estimate, not a price target."
    return strengths, risks, drivers, valuation


def render_company_description(description, key):
    """Keep sourced descriptions readable without discarding the full provider text."""
    if not description:
        st.markdown("<div class='company-description'>Data unavailable</div>", unsafe_allow_html=True)
        return
    clean = str(description).strip()
    preview_limit = 620
    preview = clean
    needs_expander = len(clean) > 340
    if len(clean) > preview_limit:
        preview = clean[:preview_limit].rsplit(" ", 1)[0] + "…"
    st.markdown(f"<div class='company-description'>{escape(preview)}</div>", unsafe_allow_html=True)
    if needs_expander:
        with st.expander("Show full company description", expanded=False):
            st.write(clean)


def render_company_analysis(info):
    description = g(info, "longBusinessSummary")
    st.markdown("#### Sourced company information")
    render_company_description(description, "analysis")
    research_note_block()
    dcf_values = default_dcf_v2_snapshot(info)
    strengths, risks, drivers, valuation = derived_analysis(info, dcf_values)
    left, right = st.columns(2)
    with left:
        st.markdown("#### Key strengths · derived from reported metrics")
        st.markdown("\n".join(f"- {item}" for item in strengths))
        st.markdown("#### Growth drivers · research prompts")
        st.markdown("\n".join(f"- {item}" for item in drivers))
    with right:
        st.markdown("#### Key risks · derived from reported metrics")
        st.markdown("\n".join(f"- {item}" for item in risks))
        st.markdown("#### Financial quality")
        stat_grid("Reported quality indicators", [
            ("Revenue growth", percent_value(g(info, "revenueGrowth"))),
            ("Operating margin", percent_value(g(info, "operatingMargins"))),
            ("Profit margin", percent_value(g(info, "profitMargins"))),
            ("Return on equity", percent_value(g(info, "returnOnEquity"))),
        ])
    st.markdown("#### Valuation discussion · model-derived")
    st.info(valuation)


def render_relative_valuation(info):
    revenue = g(info, "totalRevenue")
    fcf = g(info, "freeCashflow")
    market_cap = g(info, "marketCap")
    price_fcf = market_cap / fcf if market_cap is not None and fcf and fcf > 0 else None
    multiple_pairs = [
        ("Trailing P/E", fmt_x(g(info, "trailingPE"), "x")),
        ("Forward P/E", fmt_x(g(info, "forwardPE"), "x")),
        ("PEG", fmt_x(g(info, "pegRatio"), "x")),
        ("EV / EBITDA", fmt_x(g(info, "enterpriseToEbitda"), "x")),
        ("Price / Sales", fmt_x(g(info, "priceToSalesTrailing12Months"), "x")),
        ("Price / Book", fmt_x(g(info, "priceToBook"), "x")),
        ("Price / FCF", fmt_x(price_fcf, "x")),
    ]
    peer_names = [selected_company, *PEER_GROUPS.get(selected_company, [])]
    peers = get_company_metrics(peer_names)
    display = peers.copy()
    display["Market Cap"] = display["Market Cap"].map(fmt_big)
    for column in ["P/E TTM", "EV / EBITDA", "Price / FCF"]:
        display[column] = display[column].map(lambda value: fmt_x(value, "x") if pd.notna(value) else "Data unavailable")
    for column in ["Revenue Growth", "Operating Margin", "FCF Margin"]:
        display[column] = display[column].map(lambda value: f"{value:.1%}" if pd.notna(value) else "Data unavailable")

    with st.container(key="relative_top"):
        multiple_column, peer_column = st.columns([0.36, 0.64])
        with multiple_column:
            tiles = "".join(
                f"<div class='stat'><div class='k'>{escape(label)}</div><div class='v'>{escape(value)}</div></div>"
                for label, value in multiple_pairs
            )
            st.markdown(
                f"<div class='mock-card mock-multiples'><div class='mock-card-title'>Trading Multiples — {escape(ticker)}</div>"
                f"<div class='stat-grid'>{tiles}</div></div>",
                unsafe_allow_html=True,
            )
        with peer_column:
            peer_columns = ["Company", "Ticker", "Market Cap", "P/E TTM", "EV / EBITDA", "Revenue Growth", "Operating Margin", "FCF Margin"]
            peer_head = "".join(f"<th>{escape(column)}</th>" for column in peer_columns)
            peer_rows = ""
            for _, row in display[peer_columns].iterrows():
                peer_rows += "<tr>" + "".join(f"<td>{escape(str(row[column]))}</td>" for column in peer_columns) + "</tr>"
            st.markdown(
                f"""<div class='mock-card mock-peers'><div class='mock-card-title'>Relevant Peer Snapshot</div>
                <div class='mock-table-wrap'><table class='mock-table'><thead><tr>{peer_head}</tr></thead><tbody>{peer_rows}</tbody></table></div>
                <div class='mock-note'>Peers are selected from the dashboard’s 19-company research universe.<br>
                Values are provider-reported or directly calculated; unavailable metrics are not estimated.</div></div>""",
                unsafe_allow_html=True,
            )

    dcf_values = default_dcf_v2_snapshot(info)
    current_price = dcf_values.get("Current") if dcf_values else (g(info, "currentPrice") or g(info, "regularMarketPrice"))
    bear_value = dcf_values.get("Bear") if dcf_values else None
    base_value = dcf_values.get("Base") if dcf_values else None
    bull_value = dcf_values.get("Bull") if dcf_values else None
    dcf_gap = base_value / current_price - 1.0 if base_value is not None and current_price else None
    valid_values = [value for value in (bear_value, base_value, bull_value) if value is not None]
    value_range = f"{format_price(min(valid_values))} – {format_price(max(valid_values))}" if valid_values else "Data unavailable"
    summary_cells = [
        ("Current Price", format_price(current_price), "neutral-value", ""),
        ("Bear DCF Value", format_price(bear_value), "bear-value", ""),
        ("Base DCF Value", format_price(base_value), "base-value", ""),
        ("Bull DCF Value", format_price(bull_value), "bull-value", ""),
        ("Valuation Range", value_range, "base-value range-value", f"Base: {format_price(base_value)}"),
        ("Implied Upside / Downside", f"{dcf_gap:+.1%}" if dcf_gap is not None else "Data unavailable", "bull-value" if dcf_gap is not None and dcf_gap >= 0 else "bear-value", "vs. Base DCF"),
    ]
    summary_html = "".join(
        f"<div class='mock-summary-cell'><div class='k'>{escape(label)}</div><div class='v {css}'>{escape(value)}</div>"
        f"{f'<div class=\"s\">{escape(subtext)}</div>' if subtext else ''}</div>"
        for label, value, css, subtext in summary_cells
    )
    framework_label = framework_for(ticker).get("framework", "Standard mature-company DCF")
    summary_method = {
        "Financial institution / FCFE": "Equity DCF / FCFE",
        "Pre-profit / emerging-company DCF": "Emerging-company DCF",
        "Special-case valuation": "Special-case valuation",
    }.get(framework_label, "Simplified Unlevered DCF")
    st.markdown(
        f"<div class='mock-card mock-dcf-summary'><div class='mock-card-title'>DCF Summary — {escape(selected_company)} ({escape(summary_method)})</div>"
        f"<div class='mock-summary-grid'>{summary_html}</div></div>",
        unsafe_allow_html=True,
    )

    preview_companies = {name: COMPANIES[name] for name in SLEEPER_STOCKS}
    preview, _ = get_market_data(preview_companies)
    preview_caps = get_company_metrics(SLEEPER_STOCKS)[["Company", "Market Cap"]]
    preview = preview.merge(preview_caps, on="Company", how="left")
    with st.container(key="relative_preview"):
        st.markdown("<div class='mock-card-title preview-title'>Research Universe Preview</div>", unsafe_allow_html=True)
        with st.container(key="relative_filters"):
            filter_category, filter_risk, filter_cap, filter_performance = st.columns([1.0, 0.95, 0.95, 2.35])
            with filter_category:
                category_choice = st.selectbox("Category", ["All Categories", *sorted(preview["Category"].dropna().unique())], key="relative_category")
            with filter_risk:
                risk_choice = st.selectbox("Risk Level", ["All Risk Levels", *sorted(preview["Risk Level"].dropna().unique())], key="relative_risk")
            with filter_cap:
                cap_choice = st.selectbox("Market Cap", ["All Market Caps", "≥ $10B", "< $10B"], key="relative_cap")
            returns = pd.to_numeric(preview["1Y Return %"], errors="coerce").dropna()
            with filter_performance:
                if returns.empty:
                    performance_range = None
                    st.caption("1Y performance unavailable")
                else:
                    low_return, high_return = float(returns.min()), float(returns.max())
                    performance_range = st.slider("1Y Performance (%)", low_return, high_return, (low_return, high_return), key="relative_performance")
        filtered = preview.copy()
        if category_choice != "All Categories":
            filtered = filtered[filtered["Category"] == category_choice]
        if risk_choice != "All Risk Levels":
            filtered = filtered[filtered["Risk Level"] == risk_choice]
        if cap_choice == "≥ $10B":
            filtered = filtered[filtered["Market Cap"] >= 10e9]
        elif cap_choice == "< $10B":
            filtered = filtered[filtered["Market Cap"] < 10e9]
        if performance_range is not None:
            filtered = filtered[pd.to_numeric(filtered["1Y Return %"], errors="coerce").between(*performance_range)]
        preview_rows = ""
        for _, row in filtered.iterrows():
            daily = row["Daily Change %"]
            annual = row["1Y Return %"]
            daily_class = "pos" if pd.notna(daily) and daily >= 0 else "neg" if pd.notna(daily) else "neutral"
            annual_class = "pos" if pd.notna(annual) and annual >= 0 else "neg" if pd.notna(annual) else "neutral"
            daily_text = f"{daily:+.2f}%" if pd.notna(daily) else "—"
            annual_text = f"{annual:+.2f}%" if pd.notna(annual) else "—"
            preview_rows += (
                f"<tr><td>{escape(str(row['Company']))}</td><td>{escape(str(row['Ticker']))}</td>"
                f"<td>{format_price(row['Current Price'])}</td><td class='{daily_class}'>{daily_text}</td>"
                f"<td class='{annual_class}'>{annual_text}</td><td>{format_price(row['52W High'])}</td>"
                f"<td>{format_price(row['52W Low'])}</td><td>{escape(str(row['Category']))}</td><td>{escape(str(row['Risk Level']))}</td></tr>"
            )
        st.markdown(
            f"""<div class='mock-table-wrap preview-table'><table class='mock-table'><thead><tr>
            <th>Company</th><th>Ticker</th><th>Price</th><th>1D %</th><th>1Y %</th><th>52W High</th><th>52W Low</th><th>Category</th><th>Risk</th>
            </tr></thead><tbody>{preview_rows}</tbody></table></div>""",
            unsafe_allow_html=True,
        )
        with st.container(key="relative_preview_button"):
            button_left, button_center, button_right = st.columns([1.0, 0.42, 1.0])
            with button_center:
                if st.button("View Full Research Universe  →", key="open_full_universe", width="stretch"):
                    st.session_state["active_page"] = "Research Universe"
                    st.session_state["mobile_navigation"] = "Research Universe"
                    for group_name, group_pages in NAV_GROUPS.items():
                        st.session_state[nav_key(group_name)] = "Research Universe" if "Research Universe" in group_pages else None
                    st.rerun()


def render_risk_performance(info):
    history = get_stock_data(ticker, "5y", "1d")
    benchmark_history = get_stock_data("^GSPC", "5y", "1d")
    if history.empty or benchmark_history.empty or "Close" not in history or "Close" not in benchmark_history:
        st.info("Company or S&P 500 data is unavailable for matched-period risk calculations.")
        return
    aligned = align_price_series(history["Close"], benchmark_history["Close"], ticker, "S&P 500")
    if len(aligned) < 20:
        st.info("Insufficient overlapping company and S&P 500 history for comparison.")
        return
    risk_free = get_risk_free_rate()
    company_stats = risk_statistics(aligned[ticker], risk_free)
    benchmark_stats = risk_statistics(aligned["S&P 500"], risk_free)
    stat_grid("Additional Company Risk", [
        ("Beta", fmt_x(g(info, "beta"))),
        ("Downside volatility", percent_value(company_stats["downside_volatility"])),
        ("Measurement period", f"{aligned.index.min():%b %Y}–{aligned.index.max():%b %Y}"),
    ])
    comparison_rows = []
    metric_map = [
        ("1Y Return", "return_1y", True),
        ("3Y Return", "return_3y", True),
        ("Annualized Volatility", "annualized_volatility", False),
        ("Maximum Drawdown", "maximum_drawdown", True),
    ]
    for label, key, signed in metric_map:
        comparison_rows.append({
            "Metric": label,
            selected_company: percent_value(company_stats[key], signed=signed),
            "S&P 500": percent_value(benchmark_stats[key], signed=signed),
        })
    comparison_rows.append({
        "Metric": "Sharpe Ratio",
        selected_company: fmt_x(company_stats["sharpe_ratio"]),
        "S&P 500": fmt_x(benchmark_stats["sharpe_ratio"]),
    })
    st.markdown("#### Matched-period benchmark comparison")
    st.dataframe(pd.DataFrame(comparison_rows), hide_index=True, width="stretch")
    st.caption("Both columns use the same overlapping trading dates, daily-return methodology and annual risk-free rate.")

    returns = aligned.pct_change(fill_method=None).dropna()
    cumulative = aligned.divide(aligned.iloc[0]).multiply(100)
    drawdown = aligned.divide(aligned.cummax()).subtract(1).multiply(100)
    rolling_vol = returns.rolling(63).std().multiply(252 ** 0.5).multiply(100)
    tab1, tab2, tab3 = st.tabs(["Cumulative Return", "Drawdown", "Rolling Volatility"])
    charts = [
        (tab1, cumulative, "Growth of $100", "Index"),
        (tab2, drawdown, "Drawdown", "%"),
        (tab3, rolling_vol, "63-day Rolling Annualized Volatility", "%"),
    ]
    for tab, frame, name, y_title in charts:
        with tab:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=frame.index, y=frame[ticker], mode="lines", name=selected_company, line=dict(color=BLUE_LT, width=2.2)))
            fig.add_trace(go.Scatter(x=frame.index, y=frame["S&P 500"], mode="lines", name="S&P 500", line=dict(color=ORANGE, width=1.8)))
            fig.update_layout(template="plotly_white", height=330, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT, family="Inter"), margin=dict(l=10, r=10, t=20, b=10), yaxis_title=y_title)
            fig.update_xaxes(gridcolor="rgba(15,31,61,0.08)")
            fig.update_yaxes(gridcolor="rgba(15,31,61,0.08)")
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    with st.expander("Metric definitions"):
        st.markdown(
            "- **Beta:** provider-reported sensitivity to market movements.\n"
            "- **Annualized volatility:** standard deviation of daily returns × √252.\n"
            "- **Maximum drawdown:** largest peak-to-trough decline during the matched measurement period.\n"
            "- **Sharpe ratio:** annualized excess daily return divided by annualized volatility, using the current 10-year Treasury proxy.\n"
            "- **Downside volatility:** annualized standard deviation of negative daily returns."
        )


def peer_group_selection():
    universe = get_company_metrics(list(COMPANIES))
    options = []
    if selected_company in MEGA_CAP_TECH:
        options.append("Mega-Cap Technology")
    options.extend(["Sector Peers", "Similar Market Cap", "Curated Coverage Peers"])
    group = st.selectbox("Peer group", options, key=f"peer_group_{ticker}")

    selected_row = universe[universe["Company"] == selected_company]
    if group == "Mega-Cap Technology":
        names = MEGA_CAP_TECH
        explanation = "Selected from the dashboard’s five mega-cap technology platforms for broad business-model and valuation context; these are not all direct operating competitors."
    elif group == "Sector Peers" and not selected_row.empty and pd.notna(selected_row.iloc[0]["Sector"]):
        sector = selected_row.iloc[0]["Sector"]
        candidates = universe[universe["Sector"] == sector].copy()
        target_cap = selected_row.iloc[0]["Market Cap"]
        if pd.notna(target_cap) and target_cap:
            candidates["Distance"] = (pd.to_numeric(candidates["Market Cap"], errors="coerce") - target_cap).abs() / target_cap
            candidates = candidates.sort_values("Distance")
        names = candidates["Company"].head(5).tolist()
        explanation = f"Selected from companies classified by Yahoo Finance in the {sector} sector, limited to this dashboard’s 19-security universe and ordered by market-cap proximity where available."
    elif group == "Similar Market Cap" and not selected_row.empty and pd.notna(selected_row.iloc[0]["Market Cap"]):
        target_cap = selected_row.iloc[0]["Market Cap"]
        candidates = universe[pd.to_numeric(universe["Market Cap"], errors="coerce").notna()].copy()
        candidates["Distance"] = (candidates["Market Cap"] - target_cap).abs() / target_cap
        names = candidates.sort_values("Distance")["Company"].head(5).tolist()
        explanation = "Selected from the dashboard’s 19-security universe by smallest percentage difference in reported market capitalization. Similar size does not imply similar operations."
    else:
        names = [selected_company, *PEER_GROUPS.get(selected_company, [])]
        explanation = "A manually curated comparison set from the existing coverage universe, chosen for overlapping markets, business economics or investor context."

    if selected_company not in names:
        names = [selected_company, *names]
    names = list(dict.fromkeys(names))[:5]
    if len(names) < 2:
        names = [selected_company, *PEER_GROUPS.get(selected_company, [])][:5]
        explanation += " Fewer than two sector matches were available, so the curated coverage set is used as a fallback."
    return group, names, explanation, universe


def render_peer_comparison():
    group, peer_names, explanation, universe = peer_group_selection()
    st.markdown(f"#### {group} Comparison")
    st.caption(explanation)
    metrics = universe[universe["Company"].isin(peer_names)].copy()
    order = {name: index for index, name in enumerate(peer_names)}
    metrics["_order"] = metrics["Company"].map(order)
    metrics = metrics.sort_values("_order").drop(columns="_order")
    history = get_peer_price_history(peer_names)
    if not history.empty:
        fig = go.Figure()
        for column in history.columns:
            fig.add_trace(go.Scatter(x=history.index, y=history[column], mode="lines", name=column))
        fig.update_layout(template="plotly_white", height=360, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT, family="Inter"), margin=dict(l=10, r=10, t=20, b=10), yaxis_title="Growth of $100", legend=dict(orientation="h"))
        fig.update_xaxes(gridcolor="rgba(15,31,61,0.08)")
        fig.update_yaxes(gridcolor="rgba(15,31,61,0.08)")
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    else:
        st.info("Price performance data unavailable for this peer group.")
    chart_metrics = metrics.set_index("Ticker")[["Revenue Growth", "Profit Margin", "Operating Margin"]] * 100
    if not chart_metrics.dropna(how="all").empty:
        bar = go.Figure()
        for column in chart_metrics.columns:
            bar.add_trace(go.Bar(x=chart_metrics.index, y=chart_metrics[column], name=column))
        bar.update_layout(template="plotly_white", barmode="group", height=320, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT, family="Inter"), margin=dict(l=10, r=10, t=20, b=10), yaxis_title="%")
        st.plotly_chart(bar, width="stretch", config={"displayModeBar": False})
    display = metrics.copy()
    display["Market Cap"] = display["Market Cap"].map(fmt_big)
    for column in ["Revenue Growth", "Profit Margin", "Operating Margin"]:
        display[column] = display[column].map(lambda value: f"{value:.1%}" if pd.notna(value) else "Data unavailable")
    for column in ["P/E TTM", "EV / EBITDA"]:
        display[column] = display[column].map(lambda value: f"{value:.2f}x" if pd.notna(value) else "Data unavailable")
    st.dataframe(display[["Company", "Ticker", "Market Cap", "Revenue Growth", "Profit Margin", "Operating Margin", "P/E TTM", "EV / EBITDA"]], hide_index=True, width="stretch")


def render_company_profile(info):
    city, state, country = g(info, "city"), g(info, "state"), g(info, "country")
    headquarters = ", ".join(str(value) for value in (city, state, country) if value) or "Data unavailable"
    employees = g(info, "fullTimeEmployees")
    fields = [
        ("Company name", g(info, "longName") or selected_company),
        ("Ticker", ticker),
        ("Exchange", g(info, "fullExchangeName") or g(info, "exchange") or "Data unavailable"),
        ("Sector", g(info, "sector") or "Data unavailable"),
        ("Industry", g(info, "industry") or "Data unavailable"),
        ("Market cap", value_or_unavailable(g(info, "marketCap"), fmt_big)),
        ("Headquarters", headquarters),
        ("Employees", f"{employees:,.0f}" if employees is not None else "Data unavailable"),
    ]
    stat_grid("Company Facts", fields)
    st.markdown("#### Business description")
    description = g(info, "longBusinessSummary")
    render_company_description(description, "profile")
    st.caption("Factual company fields and description are supplied by Yahoo Finance via yfinance.")


def render_formula_cards(cards):
    html = ""
    for name, formula, explanation in cards:
        html += (
            "<div class='formula-card'>"
            f"<div class='name'>{escape(name)}</div>"
            f"<div class='formula'>{escape(formula)}</div>"
            f"<div class='explain'>{escape(explanation)}</div></div>"
        )
    st.markdown(f"<div class='formula-grid'>{html}</div>", unsafe_allow_html=True)


def render_research_universe(comparison):
    fundamentals = get_company_metrics(list(COMPANIES))[["Company", "Market Cap"]]
    universe = comparison.merge(fundamentals, on="Company", how="left")
    f1, f2, f3, f4, f5 = st.columns([1.35, 1.0, 1.25, 0.75, 0.75])
    with f1:
        categories = st.multiselect("Category", sorted(universe["Category"].dropna().unique()), key="universe_category")
    with f2:
        risks = st.multiselect("Risk level", sorted(universe["Risk Level"].dropna().unique()), key="universe_risk")
    with f3:
        market_band = st.selectbox("Market cap", ["All", "Mega / Large (≥$200B)", "Mid ($10B–$200B)", "Small (<$10B)"], key="universe_market_cap")
    performance_values = pd.to_numeric(universe["1Y Return %"], errors="coerce").dropna()
    performance_min, performance_max = None, None
    if not performance_values.empty:
        low, high = float(performance_values.min()), float(performance_values.max())
        with f4:
            performance_min = st.number_input("Min 1Y return %", value=round(low, 1), step=5.0, key="universe_performance_min")
        with f5:
            performance_max = st.number_input("Max 1Y return %", value=round(high, 1), step=5.0, key="universe_performance_max")
    filtered = universe.copy()
    if categories:
        filtered = filtered[filtered["Category"].isin(categories)]
    if risks:
        filtered = filtered[filtered["Risk Level"].isin(risks)]
    if market_band.startswith("Mega"):
        filtered = filtered[filtered["Market Cap"] >= 200e9]
    elif market_band.startswith("Mid"):
        filtered = filtered[(filtered["Market Cap"] >= 10e9) & (filtered["Market Cap"] < 200e9)]
    elif market_band.startswith("Small"):
        filtered = filtered[filtered["Market Cap"] < 10e9]
    if performance_min is not None and performance_max is not None:
        lower, upper = sorted((performance_min, performance_max))
        filtered = filtered[pd.to_numeric(filtered["1Y Return %"], errors="coerce").between(lower, upper)]
    st.markdown("#### Speculative Coverage")
    st.caption("Higher-risk research names, not investment recommendations.")
    speculative = comparison[comparison["Company"].isin(SLEEPER_STOCKS)]
    styled_comparison(speculative)
    st.markdown("#### Full 19-company research universe")
    styled_comparison(filtered)
    st.download_button("Download filtered universe (CSV)", filtered.to_csv(index=False).encode("utf-8"), file_name="equity_research_universe.csv", mime="text/csv")


def render_bank_equity_dcf(info, statement_data):
    """Render a bank-appropriate FCFE valuation instead of misusing net debt."""
    history = [
        row for row in statement_data["history"]
        if row.get("net_income") is not None and row.get("book_equity") is not None
    ]
    current_price = g(info, "currentPrice") or g(info, "regularMarketPrice")
    shares = valuation_share_count(info)
    if not history or history[-1]["net_income"] <= 0 or not current_price or not shares:
        st.error("Positive earnings, common equity, price, and share-count data are required for this bank equity DCF.")
        return

    defaults = estimate_equity_dcf_defaults(history, info)
    scenario_name = st.radio(
        "Scenario",
        ["Bear", "Base", "Bull"],
        index=1,
        horizontal=True,
        key=f"bank_dcf_scenario_{ticker}",
    )
    scenario = equity_scenario_assumptions(defaults, scenario_name)

    with st.expander("Edit bank equity DCF assumptions", expanded=True):
        input_1, input_2, input_3 = st.columns(3)
        with input_1:
            year_one_growth = st.number_input(
                "Year 1 earnings growth (%)", -30.0, 60.0,
                round(scenario["year_one_growth"] * 100, 1), 0.5,
                key=f"bank_growth_1_{ticker}_{scenario_name}",
            ) / 100
            final_year_growth = st.number_input(
                "Final-year earnings growth (%)", -10.0, 25.0,
                round(scenario["final_year_growth"] * 100, 1), 0.5,
                key=f"bank_growth_final_{ticker}_{scenario_name}",
            ) / 100
        with input_2:
            target_roe = st.number_input(
                "Target ROE (%)", 3.0, 45.0,
                round(scenario["target_roe"] * 100, 1), 0.5,
                key=f"bank_roe_{ticker}_{scenario_name}",
            ) / 100
            cost_of_equity = st.number_input(
                "Cost of equity (%)", 5.0, 22.0,
                round(scenario["cost_of_equity"] * 100, 1), 0.25,
                key=f"bank_cost_equity_{ticker}_{scenario_name}",
            ) / 100
        with input_3:
            terminal_growth = st.number_input(
                "Terminal growth (%)", 0.0, 5.0,
                round(scenario["terminal_growth"] * 100, 1), 0.25,
                key=f"bank_terminal_{ticker}_{scenario_name}",
            ) / 100
            forecast_years = st.slider(
                "Forecast period (years)", 5, 10, int(scenario["forecast_years"]),
                key=f"bank_years_{ticker}_{scenario_name}",
            )

        source_tiles = [
            ("Reported net income", fmt_big(history[-1]["net_income"])),
            ("Common equity", fmt_big(history[-1]["book_equity"])),
            ("Starting ROE", f"{defaults['starting_roe']:.1%}"),
            ("Shares outstanding", f"{float(shares) / 1e9:,.2f}B"),
        ]
        source_html = "".join(
            f"<div class='dcf-assumption'><div class='k'>{label}</div><div class='v'>{value}</div></div>"
            for label, value in source_tiles
        )
        st.markdown(f"<div class='dcf-assumption-grid'>{source_html}</div>", unsafe_allow_html=True)

    model_inputs = {
        "base_net_income": float(history[-1]["net_income"]),
        "starting_roe": defaults["starting_roe"],
        "year_one_growth": year_one_growth,
        "final_year_growth": final_year_growth,
        "target_roe": target_roe,
        "cost_of_equity": cost_of_equity,
        "terminal_growth": terminal_growth,
        "forecast_years": forecast_years,
        "shares_outstanding": float(shares),
    }
    try:
        result = run_equity_dcf(**model_inputs)
    except ValueError as error:
        st.error(str(error))
        return

    fair_value = result["value_per_share"]
    upside = (fair_value / float(current_price) - 1.0) * 100.0
    default_values = {}
    for name in ["Bear", "Base", "Bull"]:
        assumptions = equity_scenario_assumptions(defaults, name)
        try:
            default_values[name] = run_equity_dcf(
                base_net_income=float(history[-1]["net_income"]),
                starting_roe=defaults["starting_roe"],
                year_one_growth=assumptions["year_one_growth"],
                final_year_growth=assumptions["final_year_growth"],
                target_roe=assumptions["target_roe"],
                cost_of_equity=assumptions["cost_of_equity"],
                terminal_growth=assumptions["terminal_growth"],
                forecast_years=assumptions["forecast_years"],
                shares_outstanding=float(shares),
            )["value_per_share"]
        except ValueError:
            pass
    default_values[scenario_name] = fair_value
    range_text = f"{format_price(min(default_values.values()))}–{format_price(max(default_values.values()))}" if default_values else "—"
    base_value = default_values.get("Base")
    base_gap = (base_value / float(current_price) - 1.0) * 100 if base_value is not None else None
    result_tiles = [
        ("Current Price", format_price(current_price), ""),
        ("Bear DCF Value", format_price(default_values.get("Bear")), ""),
        ("Base DCF Value", format_price(base_value), ""),
        ("Bull DCF Value", format_price(default_values.get("Bull")), ""),
        ("Base Upside / Downside", f"{base_gap:+.1f}%" if base_gap is not None else "—", "pos" if base_gap is not None and base_gap >= 0 else "neg"),
        ("Valuation Range", range_text, ""),
    ]
    result_html = "".join(
        f"<div class='dcf-result'><div class='k'>{label}</div><div class='v {css}'>{value}</div></div>"
        for label, value, css in result_tiles
    )
    st.markdown(f"<div class='dcf-result-grid'>{result_html}</div>", unsafe_allow_html=True)
    if base_gap is not None:
        relation = "below" if base_gap >= 0 else "above"
        st.caption(f"The current market price is {abs(base_gap):.1f}% {relation} the default Base equity DCF estimate.")
    stat_grid("Equity-value bridge", [
        ("Present value of forecast FCFE", fmt_big(result["present_value_fcfe"])),
        ("Present value of terminal value", fmt_big(result["present_value_terminal"])),
        ("Equity value", fmt_big(result["equity_value"])),
        ("Diluted shares", f"{float(shares) / 1e9:,.2f}B"),
        (f"{scenario_name} implied share price", format_price(fair_value)),
    ])
    if result["terminal_value_share"] > 0.80:
        st.info(f"{result['terminal_value_share']:.0%} of equity value comes from the terminal value. Treat the result as assumption-sensitive.")

    forecast_tab, sensitivity_tab, method_tab = st.tabs(["Forecast", "Sensitivity", "Sources & Method"])
    with forecast_tab:
        first_year = pd.Timestamp.now().year + 1
        rows = [{
            "Year": first_year + row["year"] - 1,
            "Growth": row["growth"], "ROE": row["roe"], "Payout": row["payout"],
            "Net Income": row["earnings"], "FCFE": row["fcfe"], "PV of FCFE": row["pv_fcfe"],
        } for row in result["schedule"]]
        forecast_df = pd.DataFrame(rows)
        chart = go.Figure()
        chart.add_trace(go.Bar(x=forecast_df["Year"], y=forecast_df["Net Income"] / 1e9, name="Net income", marker_color=BLUE))
        chart.add_trace(go.Scatter(x=forecast_df["Year"], y=forecast_df["FCFE"] / 1e9, name="FCFE", mode="lines+markers", line=dict(color=PURPLE, width=3)))
        chart.update_layout(
            template="plotly_white", height=310, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT, family="Inter"), margin=dict(l=10, r=10, t=28, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0), yaxis_title="$ billions",
        )
        chart.update_xaxes(gridcolor="rgba(15,31,61,0.08)")
        chart.update_yaxes(gridcolor="rgba(15,31,61,0.08)")
        st.plotly_chart(chart, width="stretch", config={"displayModeBar": False})
        display_df = forecast_df.copy()
        for column in ["Growth", "ROE", "Payout"]:
            display_df[column] = display_df[column].map(lambda value: f"{value:.1%}")
        for column in ["Net Income", "FCFE", "PV of FCFE"]:
            display_df[column] = display_df[column].map(lambda value: f"${value / 1e9:,.1f}B")
        st.dataframe(display_df, hide_index=True, width="stretch")

    with sensitivity_tab:
        cost_values = [cost_of_equity + offset for offset in [-0.01, -0.005, 0.0, 0.005, 0.01]]
        growth_values = [max(0.0, terminal_growth + offset) for offset in [-0.01, -0.005, 0.0, 0.005, 0.01]]
        matrix = []
        for test_cost in cost_values:
            row_values = []
            for test_growth in growth_values:
                row_values.append(None if test_cost <= test_growth else run_equity_dcf(**{
                    **model_inputs, "cost_of_equity": test_cost, "terminal_growth": test_growth,
                })["value_per_share"])
            matrix.append(row_values)
        heatmap = go.Figure(go.Heatmap(
            z=matrix, x=[f"g {value:.1%}" for value in growth_values],
            y=[f"Ke {value:.1%}" for value in cost_values],
            colorscale=[[0, "#7f1d1d"], [0.5, "#1d4ed8"], [1, "#166534"]],
            text=[[format_price(value) if value is not None else "—" for value in row] for row in matrix],
            texttemplate="%{text}", showscale=False,
        ))
        heatmap.update_layout(
            template="plotly_white", height=330, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT, family="Inter"), margin=dict(l=10, r=10, t=25, b=10),
        )
        st.plotly_chart(heatmap, width="stretch", config={"displayModeBar": False})

    with method_tab:
        st.markdown(
            "#### Why this model is different\n"
            "For a bank, deposits and borrowings are operating inputs, so subtracting net debt as if it were an industrial company is misleading. "
            "This model forecasts earnings, estimates the capital that must be retained from growth and ROE, and discounts the remaining cash flow to equity at the cost of equity."
        )
        history_df = pd.DataFrame(history)[["year", "net_income", "book_equity"]].rename(columns={
            "year": "Year", "net_income": "Net Income", "book_equity": "Common Equity",
        })
        for column in ["Net Income", "Common Equity"]:
            history_df[column] = history_df[column].map(fmt_big)
        st.dataframe(history_df, hide_index=True, width="stretch")


def render_dcf_model(info):
    """Render an editable, company-specific two-stage FCFF valuation."""
    statement_data = get_dcf_financials(ticker)
    model_info = {**info, "_risk_free_rate": get_risk_free_rate()}
    st.markdown(
        """<div class="dcf-preview-head">
        <div class="t">Intrinsic Value — Discounted Cash Flow</div>
        <div class="b">EDITABLE RESEARCH MODEL</div>
        </div>""",
        unsafe_allow_html=True,
    )

    financial_firms = {"JPM", "GS", "SOFI"}
    if ticker in financial_firms:
        st.caption("Bank equity DCF using free cash flow to equity. Assumptions are estimates, not facts.")
        st.warning(
            "Banks need an equity DCF: deposits and borrowings are operating inputs, so the industrial-company net-debt method would be misleading."
        )
        render_bank_equity_dcf(model_info, statement_data)
        return

    st.caption(
        "Simplified margin-based two-stage unlevered DCF using reported annual financials. "
        "It does not separately forecast EBIT, taxes, D&A, capital expenditure, or working capital. "
        "Assumptions are estimates, not facts."
    )
    history = [
        row for row in statement_data["history"]
        if row.get("revenue") is not None and row.get("fcff") is not None
    ]
    if not history:
        st.error(statement_data.get("error") or "Reported cash-flow data is unavailable, so a defensible DCF cannot be calculated.")
        return

    current_price = g(info, "currentPrice") or g(info, "regularMarketPrice")
    shares = valuation_share_count(info)
    if not current_price or not shares:
        st.error("Current price or share-count data is unavailable, so per-share DCF value cannot be calculated.")
        return

    cash = g(info, "totalCash")
    debt = g(info, "totalDebt")
    cash = float(cash if cash is not None else statement_data.get("cash") or 0.0)
    debt = float(debt if debt is not None else statement_data.get("debt") or 0.0)
    net_debt = debt - cash
    base_revenue = float(history[-1]["revenue"])
    defaults = estimate_defaults(history, model_info)

    if ticker == "BRK-B":
        st.warning("Berkshire is a conglomerate with large insurance operations; a sum-of-the-parts valuation is more reliable than one consolidated DCF.")
    elif defaults["starting_fcff_margin"] < 0:
        st.warning("This company currently has negative FCFF. Its value is highly sensitive to the assumed path to positive margins.")

    scenario_name = st.radio(
        "Scenario",
        ["Bear", "Base", "Bull"],
        index=1,
        horizontal=True,
        key=f"dcf_scenario_{ticker}",
    )
    scenario = scenario_assumptions(defaults, scenario_name)

    with st.expander("Edit DCF assumptions", expanded=True):
        input_1, input_2, input_3 = st.columns(3)
        with input_1:
            year_one_growth = st.number_input(
                "Year 1 revenue growth (%)",
                min_value=-30.0,
                max_value=80.0,
                value=round(scenario["year_one_growth"] * 100, 1),
                step=0.5,
                key=f"dcf_y1_growth_{ticker}_{scenario_name}",
            ) / 100
            final_year_growth = st.number_input(
                "Final-year revenue growth (%)",
                min_value=-10.0,
                max_value=30.0,
                value=round(scenario["final_year_growth"] * 100, 1),
                step=0.5,
                key=f"dcf_final_growth_{ticker}_{scenario_name}",
            ) / 100
        with input_2:
            target_margin = st.number_input(
                "Target FCFF margin (%)",
                min_value=-20.0,
                max_value=50.0,
                value=round(scenario["target_fcff_margin"] * 100, 1),
                step=0.5,
                key=f"dcf_margin_{ticker}_{scenario_name}",
            ) / 100
            wacc = st.number_input(
                "WACC (%)",
                min_value=4.0,
                max_value=20.0,
                value=round(scenario["wacc"] * 100, 1),
                step=0.25,
                key=f"dcf_wacc_{ticker}_{scenario_name}",
            ) / 100
        with input_3:
            terminal_growth = st.number_input(
                "Terminal growth (%)",
                min_value=0.0,
                max_value=5.0,
                value=round(scenario["terminal_growth"] * 100, 1),
                step=0.25,
                key=f"dcf_terminal_{ticker}_{scenario_name}",
            ) / 100
            forecast_years = st.slider(
                "Forecast period (years)",
                min_value=5,
                max_value=10,
                value=int(scenario["forecast_years"]),
                key=f"dcf_years_{ticker}_{scenario_name}",
            )

        source_tiles = [
            ("Reported revenue", fmt_big(base_revenue)),
            ("Starting FCFF margin", f"{defaults['starting_fcff_margin'] * 100:.1f}%"),
            ("Net cash" if net_debt < 0 else "Net debt", fmt_big(abs(net_debt))),
            ("Shares outstanding", f"{float(shares) / 1e9:,.2f}B"),
        ]
        tile_html = "".join(
            f"<div class='dcf-assumption'><div class='k'>{label}</div><div class='v'>{value}</div></div>"
            for label, value in source_tiles
        )
        st.markdown(f"<div class='dcf-assumption-grid'>{tile_html}</div>", unsafe_allow_html=True)

    model_inputs = {
        "base_revenue": base_revenue,
        "starting_fcff_margin": defaults["starting_fcff_margin"],
        "year_one_growth": year_one_growth,
        "final_year_growth": final_year_growth,
        "target_fcff_margin": target_margin,
        "wacc": wacc,
        "terminal_growth": terminal_growth,
        "forecast_years": forecast_years,
        "net_debt": net_debt,
        "shares_outstanding": float(shares),
    }

    try:
        result = run_dcf(**model_inputs)
    except ValueError as error:
        st.error(str(error))
        return

    fair_value = result["value_per_share"]
    upside = (fair_value / float(current_price) - 1.0) * 100.0
    upside_class = "pos" if upside >= 0 else "neg"
    default_values = {}
    for name in ["Bear", "Base", "Bull"]:
        assumptions = scenario_assumptions(defaults, name)
        try:
            default_values[name] = run_dcf(
                base_revenue=base_revenue,
                starting_fcff_margin=defaults["starting_fcff_margin"],
                year_one_growth=assumptions["year_one_growth"],
                final_year_growth=assumptions["final_year_growth"],
                target_fcff_margin=assumptions["target_fcff_margin"],
                wacc=assumptions["wacc"],
                terminal_growth=assumptions["terminal_growth"],
                forecast_years=assumptions["forecast_years"],
                net_debt=net_debt,
                shares_outstanding=float(shares),
            )["value_per_share"]
        except ValueError:
            pass
    default_values[scenario_name] = fair_value
    range_text = "—"
    if default_values:
        range_text = f"{format_price(min(default_values.values()))}–{format_price(max(default_values.values()))}"

    base_value = default_values.get("Base")
    base_gap = (base_value / float(current_price) - 1.0) * 100 if base_value is not None else None

    result_tiles = [
        ("Current Price", format_price(current_price), ""),
        ("Bear DCF Value", format_price(default_values.get("Bear")), ""),
        ("Base DCF Value", format_price(base_value), ""),
        ("Bull DCF Value", format_price(default_values.get("Bull")), ""),
        ("Base Upside / Downside", f"{base_gap:+.1f}%" if base_gap is not None else "—", "pos" if base_gap is not None and base_gap >= 0 else "neg"),
        ("Valuation Range", range_text, ""),
    ]
    result_html = "".join(
        f"<div class='dcf-result'><div class='k'>{label}</div><div class='v {css}'>{value}</div></div>"
        for label, value, css in result_tiles
    )
    st.markdown(f"<div class='dcf-result-grid'>{result_html}</div>", unsafe_allow_html=True)

    if base_gap is not None:
        relation = "below" if base_gap >= 0 else "above"
        st.caption(f"The current market price is {abs(base_gap):.1f}% {relation} the default Base DCF estimate.")
    stat_grid("Enterprise-to-equity bridge", [
        ("Enterprise Value", fmt_big(result["enterprise_value"])),
        ("Less: Net Debt", fmt_big(net_debt)),
        ("Equity Value", fmt_big(result["equity_value"])),
        ("Diluted Shares", f"{float(shares) / 1e9:,.2f}B"),
        (f"{scenario_name} Implied Share Price", format_price(fair_value)),
    ])

    if result["present_value_fcff"] < 0:
        st.warning("Forecast-period FCFF remains negative, so the valuation depends entirely on later profitability and terminal value.")
    elif result["terminal_value_share"] > 0.80:
        st.info(f"{result['terminal_value_share']:.0%} of enterprise value comes from the terminal value. Treat the result as assumption-sensitive.")

    forecast_tab, sensitivity_tab, method_tab = st.tabs(["Forecast", "Sensitivity", "Sources & Method"])
    with forecast_tab:
        forecast_rows = []
        first_year = pd.Timestamp.now().year + 1
        for row in result["schedule"]:
            forecast_rows.append({
                "Year": first_year + row["year"] - 1,
                "Growth": row["growth"],
                "FCFF Margin": row["fcff_margin"],
                "Revenue": row["revenue"],
                "FCFF": row["fcff"],
                "PV of FCFF": row["pv_fcff"],
            })
        forecast_df = pd.DataFrame(forecast_rows)
        chart = go.Figure()
        chart.add_trace(go.Bar(
            x=forecast_df["Year"], y=forecast_df["Revenue"] / 1e9,
            name="Revenue", marker_color=BLUE,
        ))
        chart.add_trace(go.Scatter(
            x=forecast_df["Year"], y=forecast_df["FCFF"] / 1e9,
            name="FCFF", mode="lines+markers", line=dict(color=PURPLE, width=3),
        ))
        chart.update_layout(
            template="plotly_white", height=310,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT, family="Inter"), margin=dict(l=10, r=10, t=28, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            yaxis_title="$ billions",
        )
        chart.update_xaxes(gridcolor="rgba(15,31,61,0.08)")
        chart.update_yaxes(gridcolor="rgba(15,31,61,0.08)")
        st.plotly_chart(chart, width="stretch", config={"displayModeBar": False})

        display_forecast = forecast_df.copy()
        display_forecast["Growth"] = display_forecast["Growth"].map(lambda value: f"{value:.1%}")
        display_forecast["FCFF Margin"] = display_forecast["FCFF Margin"].map(lambda value: f"{value:.1%}")
        for column in ["Revenue", "FCFF", "PV of FCFF"]:
            display_forecast[column] = display_forecast[column].map(lambda value: f"${value / 1e9:,.1f}B")
        st.dataframe(display_forecast, hide_index=True, width="stretch")
        st.download_button(
            "Download DCF forecast (CSV)",
            forecast_df.to_csv(index=False).encode("utf-8"),
            file_name=f"{ticker}_dcf_forecast.csv",
            mime="text/csv",
            key=f"dcf_download_{ticker}_{scenario_name}",
        )

    with sensitivity_tab:
        sensitivity_left, sensitivity_right = st.columns([1.35, 0.85])
        with sensitivity_left:
            wacc_values = [wacc + offset for offset in [-0.01, -0.005, 0.0, 0.005, 0.01]]
            growth_values = [max(0.0, terminal_growth + offset) for offset in [-0.01, -0.005, 0.0, 0.005, 0.01]]
            matrix = []
            for test_wacc in wacc_values:
                row_values = []
                for test_growth in growth_values:
                    if test_wacc <= test_growth:
                        row_values.append(None)
                    else:
                        row_values.append(run_dcf(**{
                            **model_inputs,
                            "wacc": test_wacc,
                            "terminal_growth": test_growth,
                        })["value_per_share"])
                matrix.append(row_values)
            sensitivity = go.Figure(go.Heatmap(
                z=matrix,
                x=[f"g {value:.1%}" for value in growth_values],
                y=[f"WACC {value:.1%}" for value in wacc_values],
                colorscale=[[0, "#7f1d1d"], [0.5, "#1d4ed8"], [1, "#166534"]],
                text=[[format_price(value) if value is not None else "—" for value in row] for row in matrix],
                texttemplate="%{text}",
                showscale=False,
            ))
            sensitivity.update_layout(
                template="plotly_white", height=320,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color=TEXT, family="Inter"), margin=dict(l=10, r=10, t=25, b=10),
            )
            st.plotly_chart(sensitivity, width="stretch", config={"displayModeBar": False})

        with sensitivity_right:
            implied_growth = solve_implied_year_one_growth(float(current_price), model_inputs)
            implied_text = f"{implied_growth:.1%}" if implied_growth is not None else "Outside model range"
            st.markdown(
                f"""<div class="dcf-reverse"><div class="k">Market-implied Year 1 growth</div>
                <div class="v">{implied_text}</div></div>
                <div class="dcf-mini-note">Solves for the first forecast year's revenue growth while holding your other assumptions constant.</div>""",
                unsafe_allow_html=True,
            )

    with method_tab:
        method_left, method_right = st.columns(2)
        with method_left:
            st.markdown("#### Reported inputs")
            source_rows = [
                ("Annual revenue", f"Yahoo Finance statements · {history[-1]['year']}"),
                ("FCFF", "Free cash flow + after-tax interest"),
                ("Cash and debt", "Latest balance sheet / company data"),
                ("Shares and price", "Current Yahoo Finance company data"),
                ("Risk-free rate", f"10Y Treasury proxy (^TNX) · {defaults['risk_free_rate']:.2%}"),
                ("Equity risk premium", f"Model assumption · {defaults['equity_risk_premium']:.2%}"),
                ("Beta", f"Yahoo Finance · {g(info, 'beta') or 1.0:.2f}"),
                ("Cost of equity", f"Risk-free rate + beta × equity risk premium · {defaults['cost_of_equity']:.2%}"),
                ("WACC", "Market-value equity/debt weights; after-tax cost of debt from reported interest and debt"),
            ]
            source_html = "".join(
                f"<div class='dcf-source'><span class='k'>{label}</span><span class='v'>{value}</span></div>"
                for label, value in source_rows
            )
            st.markdown(source_html, unsafe_allow_html=True)
        with method_right:
            st.markdown("#### How the model works")
            st.markdown(
                "1. Revenue growth fades from the Year 1 assumption to the final-year assumption.\n"
                "2. FCFF margin moves from the latest reported margin to your target margin.\n"
                "3. Annual FCFF is discounted at WACC.\n"
                "4. Terminal value uses the Gordon Growth formula.\n"
                "5. Net debt is subtracted and the result is divided by diluted shares."
            )
        history_df = pd.DataFrame(history)
        history_df = history_df.rename(columns={
            "year": "Year", "revenue": "Revenue", "fcff": "FCFF",
            "interest": "Interest Expense", "tax_rate": "Tax Rate",
        })
        for column in ["Revenue", "FCFF", "Interest Expense"]:
            history_df[column] = history_df[column].map(lambda value: fmt_big(value))
        history_df["Tax Rate"] = history_df["Tax Rate"].map(lambda value: f"{value:.1%}")
        st.dataframe(history_df, hide_index=True, width="stretch")


def render_dcf_v2(info):
    """Render the validated-comparison version without replacing the V1 baseline."""
    statement_data = get_dcf_financials(ticker)
    history = statement_data.get("history", [])
    current_price = g(info, "currentPrice") or g(info, "regularMarketPrice")
    share_details = valuation_share_count_details(info)
    shares = share_details["value"]
    if not current_price or not shares:
        st.error("Current price or aggregate share-count data is unavailable, so DCF V2 cannot calculate a per-share value.")
        return
    cash = g(info, "totalCash")
    debt = g(info, "totalDebt")
    cash = float(cash if cash is not None else statement_data.get("cash") or 0.0)
    debt = float(debt if debt is not None else statement_data.get("debt") or 0.0)
    model_info = {**info, "_risk_free_rate": get_risk_free_rate(), "_equity_risk_premium": 0.045}
    defaults = build_v2_defaults(ticker, history, model_info, float(shares), debt - cash)

    horizon_text = f"{defaults['horizon']} years" if defaults.get("horizon") else "Not applicable"
    stat_grid("DCF V2 Framework", [
        ("Primary valuation framework", defaults["framework"]),
        ("Modifiers", " · ".join(defaults["modifiers"])),
        ("Forecast horizon", horizon_text),
        ("Model status", "Public default · company-aware framework"),
    ])
    if not defaults.get("suitable"):
        for warning in defaults.get("warnings", []):
            st.warning(warning)
        st.info("DCF V2 intentionally withholds a consolidated per-share estimate when the selected framework is not financially appropriate.")
        return

    latest_diluted = next((row.get("diluted_average_shares") for row in reversed(history) if row.get("diluted_average_shares")), None)
    if latest_diluted and abs(float(shares) / float(latest_diluted) - 1.0) > 0.10:
        st.warning(
            f"Current aggregate shares differ from the latest reported diluted weighted-average shares by "
            f"{abs(float(shares) / float(latest_diluted) - 1.0):.1%}. The current aggregate measure is used; the historical diluted figure is a cross-check."
        )

    scenario_name = st.radio("DCF V2 scenario", ["Bear", "Base", "Bull"], index=1, horizontal=True, key=f"dcf_v2_scenario_{ticker}")
    scenario = scenario_inputs(defaults, scenario_name)
    with st.expander("Edit DCF V2 assumptions", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            year_one_growth = st.number_input("Year 1 growth (%)", -50.0, 100.0, round(scenario["year_one_growth"] * 100, 1), 0.5, key=f"v2_y1_{ticker}_{scenario_name}", help="Recent reported growth anchor; not inferred from market price.") / 100
            intermediate_growth = st.number_input("Intermediate-year growth (%)", -20.0, 60.0, round(scenario["intermediate_growth"] * 100, 1), 0.5, key=f"v2_mid_growth_{ticker}_{scenario_name}", help=f"Growth reached around forecast year {scenario['midpoint_year']}.") / 100
        with c2:
            mature_growth = st.number_input("Mature growth (%)", 0.0, 6.0, round(scenario["mature_growth"] * 100, 1), 0.25, key=f"v2_mature_growth_{ticker}_{scenario_name}", help="End-of-horizon growth and terminal-growth assumption.") / 100
            horizon = st.slider("Explicit forecast horizon", 5, 15, int(scenario["horizon"]), key=f"v2_horizon_{ticker}_{scenario_name}", help="Editable period required for the company to approach mature economics.")
        overrides = {
            "year_one_growth": year_one_growth,
            "intermediate_growth": intermediate_growth,
            "mature_growth": mature_growth,
            "horizon": horizon,
            "midpoint_year": max(2, (horizon + 1) // 2),
        }
        with c3:
            if defaults["framework"] == "Financial institution / FCFE":
                target_roe = st.number_input("Mature ROE (%)", 3.0, 45.0, round(scenario["target_roe"] * 100, 1), 0.5, key=f"v2_roe_{ticker}_{scenario_name}", help="ROE used to determine required retention and distributable FCFE.") / 100
                discount_rate = st.number_input("Cost of equity (%)", 5.0, 25.0, round(scenario["cost_of_equity"] * 100, 2), 0.25, key=f"v2_ke_{ticker}_{scenario_name}", help="Risk-free rate + beta × equity risk premium; WACC is not used to discount bank FCFE.") / 100
                overrides.update(target_roe=target_roe, cost_of_equity=discount_rate)
            elif defaults["framework"] == "Pre-profit / emerging-company DCF":
                target_operating_margin = st.number_input("Mature operating margin (%)", -10.0, 45.0, round(scenario["target_operating_margin"] * 100, 1), 0.5, key=f"v2_op_margin_{ticker}_{scenario_name}", help="Explicit profitability endpoint; terminal value is disabled if mature FCFF remains non-positive.") / 100
                sales_to_capital = st.number_input("Sales-to-capital ratio", 0.25, 5.0, float(scenario["sales_to_capital"]), 0.05, key=f"v2_sales_capital_{ticker}_{scenario_name}", help="Incremental revenue divided by reinvestment; lower values imply heavier capital needs.")
                wacc_input = st.number_input("WACC (%)", 4.0, 25.0, round(scenario["wacc"] * 100, 2), 0.25, key=f"v2_wacc_{ticker}_{scenario_name}", help="Calculated market-value WACC; editable for sensitivity analysis, not calibrated to market price.") / 100
                overrides.update(target_operating_margin=target_operating_margin, sales_to_capital=sales_to_capital, wacc=wacc_input)
            else:
                mature_margin = st.number_input("Mature FCFF margin (%)", -20.0, 65.0, round(scenario["mature_fcff_margin"] * 100, 1), 0.5, key=f"v2_fcff_margin_{ticker}_{scenario_name}", help=f"Issuer-specific economic guardrail: {defaults['margin_guardrail_low']:.0%} to {defaults['margin_guardrail_high']:.0%}.") / 100
                wacc_input = st.number_input("WACC (%)", 4.0, 25.0, round(scenario["wacc"] * 100, 2), 0.25, key=f"v2_wacc_{ticker}_{scenario_name}", help="Calculated market-value WACC; editable for sensitivity analysis, not calibrated to market price.") / 100
                overrides.update(mature_fcff_margin=mature_margin, wacc=wacc_input)

    if not (year_one_growth >= intermediate_growth >= mature_growth):
        st.warning("The selected growth path rises at one or more anchors. That can represent reacceleration, but the assumption should be justified.")
    if defaults["framework"] not in {"Financial institution / FCFE", "Pre-profit / emerging-company DCF"}:
        if mature_margin < defaults["margin_guardrail_low"] or mature_margin > defaults["margin_guardrail_high"]:
            st.warning("The mature FCFF margin is outside this company’s business-model guardrail. The input is not silently clamped.")

    try:
        result, applied_inputs = run_v2_case(defaults, scenario_name, overrides)
    except ValueError as error:
        st.error(str(error))
        st.info("No terminal value or per-share estimate is presented until the explicit forecast reaches a financially plausible state.")
        return

    scenario_values = {}
    for name in ("Bear", "Base", "Bull"):
        try:
            scenario_values[name] = run_v2_case(defaults, name, overrides if name == scenario_name else None)[0]["value_per_share"]
        except ValueError:
            scenario_values[name] = None
    base_value = scenario_values.get("Base")
    base_gap = (base_value / float(current_price) - 1.0) * 100 if base_value is not None else None
    valid_values = [value for value in scenario_values.values() if value is not None]
    range_text = f"{format_price(min(valid_values))}–{format_price(max(valid_values))}" if valid_values else "Data unavailable"
    result_tiles = [
        ("Current Price", format_price(current_price), ""),
        ("Bear DCF Value", format_price(scenario_values.get("Bear")), ""),
        ("Base DCF Value", format_price(base_value), ""),
        ("Bull DCF Value", format_price(scenario_values.get("Bull")), ""),
        ("Base Upside / Downside", f"{base_gap:+.1f}%" if base_gap is not None else "Data unavailable", "pos" if base_gap is not None and base_gap >= 0 else "neg"),
        ("Valuation Range", range_text, ""),
    ]
    result_html = "".join(f"<div class='dcf-result'><div class='k'>{label}</div><div class='v {css}'>{value}</div></div>" for label, value, css in result_tiles)
    st.markdown(f"<div class='dcf-result-grid'>{result_html}</div>", unsafe_allow_html=True)
    if base_gap is not None:
        relation = "below" if base_gap >= 0 else "above"
        st.caption(f"Current market price is {abs(base_gap):.1f}% {relation} the DCF V2 Base estimate.")

    v1 = default_dcf_v1_snapshot(info)
    comparison = pd.DataFrame([{
        "Model": "DCF V1 · legacy baseline",
        "Base Value": format_price(v1.get("Base") if v1 else None),
        "Market Difference": f"{(v1['Base'] / v1['Current'] - 1):+.1%}" if v1 and v1.get("Base") else "Data unavailable",
    }, {
        "Model": "DCF V2 · public default",
        "Base Value": format_price(base_value),
        "Market Difference": f"{base_gap / 100:+.1%}" if base_gap is not None else "Data unavailable",
    }])
    st.markdown("#### V1 / V2 comparison")
    st.dataframe(comparison, hide_index=True, width="stretch")

    breakdown = defaults["wacc_breakdown"]
    st.markdown("#### WACC transparency")
    wacc_columns = st.columns(3)
    applied_discount_rate = applied_inputs["cost_of_equity"] if defaults["framework"] == "Financial institution / FCFE" else applied_inputs["wacc"]
    metrics = [
        ("Risk-Free Rate", breakdown["risk_free_rate"], "Latest valid 10-year Treasury proxy (^TNX).", "percent"),
        ("Raw Beta", breakdown.get("raw_beta", g(info, "beta")), "Unadjusted beta supplied by Yahoo Finance.", "number"),
        ("Applied Beta", breakdown["beta"], "Raw beta with a disclosed 0.50–2.00 economic guardrail; 1.00 fallback if unavailable.", "number"),
        ("Equity Risk Premium", breakdown["equity_risk_premium"], "Explicit model assumption; currently 4.5%.", "percent"),
        ("Cost of Equity", breakdown["cost_of_equity"], "Risk-free rate + applied beta × equity risk premium.", "percent"),
        ("Pre-Tax Cost of Debt", breakdown["pre_tax_cost_of_debt"], "Reported interest expense ÷ total debt, with a disclosed 2%–12% guardrail.", "percent"),
        ("Tax Rate", breakdown["tax_rate"], "Latest usable reported effective rate, bounded at 0%–35%.", "percent"),
        ("Debt Weight", breakdown["debt_weight"], "Debt ÷ (market capitalization + debt).", "percent"),
        ("Equity Weight", breakdown["equity_weight"], "Market capitalization ÷ (market capitalization + debt).", "percent"),
        ("Calculated WACC", breakdown["wacc"], "Market-value weighted cost of equity and after-tax debt before scenario edits.", "percent"),
        ("Applied Discount Rate", applied_discount_rate, "The exact discount rate used in the selected scenario and forecast.", "percent"),
    ]
    for index, (label, value, help_text, display_type) in enumerate(metrics):
        with wacc_columns[index % 3]:
            display = "Data unavailable" if value is None else (f"{value:.2f}" if display_type == "number" else f"{value:.2%}")
            st.metric(label, display, help=help_text)
    if defaults["framework"] == "Financial institution / FCFE":
        st.caption(f"FCFE is discounted at cost of equity ({applied_inputs['cost_of_equity']:.2%}), not WACC.")

    share_crosscheck = f"{float(latest_diluted) / 1e9:,.2f}B" if latest_diluted else "Data unavailable"
    stat_grid("Share-count audit", [
        ("Per-share denominator", f"{float(shares) / 1e9:,.2f}B"),
        ("Exact measure used", share_details["source"]),
        ("Latest diluted weighted-average shares", share_crosscheck),
    ])

    if defaults["framework"] == "Financial institution / FCFE":
        bridge_pairs = [
            ("PV of explicit FCFE", fmt_big(result["present_value_fcfe"])),
            ("PV of terminal value", fmt_big(result["present_value_terminal"])),
            ("Equity value", fmt_big(result["equity_value"])),
            ("Aggregate shares", f"{float(shares) / 1e9:,.2f}B"),
            ("Implied share price", format_price(result["value_per_share"])),
        ]
    else:
        bridge_pairs = [
            ("Enterprise value", fmt_big(result["enterprise_value"])),
            ("Less: net debt", fmt_big(applied_inputs["net_debt"])),
            ("Equity value", fmt_big(result["equity_value"])),
            ("Aggregate shares", f"{float(shares) / 1e9:,.2f}B"),
            ("Implied share price", format_price(result["value_per_share"])),
        ]
    stat_grid(f"DCF V2 valuation bridge · {scenario_name}", bridge_pairs)
    if result["terminal_value_share"] > 0.80:
        st.warning(f"{result['terminal_value_share']:.0%} of modeled value comes from terminal value. The estimate is highly assumption-sensitive.")
    for warning in defaults.get("warnings", []):
        st.info(warning)

    forecast_df = pd.DataFrame(result["schedule"])
    forecast_df.insert(0, "Forecast Year", range(pd.Timestamp.now().year + 1, pd.Timestamp.now().year + 1 + len(forecast_df)))
    rename = {"growth": "Growth", "revenue": "Revenue", "fcff_margin": "FCFF Margin", "fcff": "FCFF", "operating_margin": "Operating Margin", "nopat": "NOPAT", "reinvestment": "Reinvestment", "earnings": "Net Income", "roe": "ROE", "payout": "Payout", "fcfe": "FCFE"}
    columns = ["Forecast Year"] + [column for column in rename if column in forecast_df.columns]
    display_forecast = forecast_df[columns].rename(columns=rename)
    for column in ["Growth", "FCFF Margin", "Operating Margin", "ROE", "Payout"]:
        if column in display_forecast:
            display_forecast[column] = display_forecast[column].map(lambda value: f"{value:.1%}")
    for column in ["Revenue", "FCFF", "NOPAT", "Reinvestment", "Net Income", "FCFE"]:
        if column in display_forecast:
            display_forecast[column] = display_forecast[column].map(fmt_big)
    st.markdown("#### Explicit forecast path")
    st.dataframe(display_forecast, hide_index=True, width="stretch")

    st.markdown("#### Reverse DCF · one-variable reconciliations")
    solver_defaults = {**defaults, **(overrides if scenario_name == "Base" else {})}
    if defaults["framework"] == "Financial institution / FCFE":
        solve_fields = [("Year 1 earnings growth", "year_one_growth", -0.30, 0.80), ("Mature ROE", "target_roe", 0.03, 0.45), ("Cost of equity", "cost_of_equity", max(mature_growth + 0.002, 0.04), 0.25), ("Terminal growth", "mature_growth", 0.0, min(solver_defaults["cost_of_equity"] - 0.002, 0.06))]
    elif defaults["framework"] == "Pre-profit / emerging-company DCF":
        solve_fields = [("Year 1 revenue growth", "year_one_growth", -0.30, 1.50), ("Mature operating margin", "target_operating_margin", 0.02, 0.45), ("WACC", "wacc", max(mature_growth + 0.002, 0.04), 0.25), ("Terminal growth", "mature_growth", 0.0, min(solver_defaults["wacc"] - 0.002, 0.06))]
    else:
        solve_fields = [("Year 1 revenue growth", "year_one_growth", -0.30, 1.50), ("Mature FCFF margin", "mature_fcff_margin", -0.10, 0.65), ("WACC", "wacc", max(mature_growth + 0.002, 0.04), 0.25), ("Terminal growth", "mature_growth", 0.0, min(solver_defaults["wacc"] - 0.002, 0.06))]
    solutions = []
    for label, field, lower, upper in solve_fields:
        solved = solve_v2_assumption(solver_defaults, float(current_price), field, lower, upper)
        solutions.append({"Assumption solved independently": label, "Market-consistent value": f"{solved:.2%}" if solved is not None else "No solution in tested range"})
    st.dataframe(pd.DataFrame(solutions), hide_index=True, width="stretch")
    st.caption("Each row changes only the named Base assumption and holds the others constant; combinations of assumptions could also reconcile the values.")
    st.info("Reverse DCF does not predict future performance. It shows the assumptions that would make the current market price consistent with this valuation framework.")


def data_log_block(data):
    rows = len(data) if data is not None else 0
    cols = data.shape[1] if data is not None else 0
    st.markdown(
        f"""<div class="terminal">
        <span class="p">$ python fetch_data.py --ticker {ticker} --interval {interval}</span><br>
        <span class="i">[INFO]</span> <span class="c">Downloading data for {ticker}</span><br>
        <span class="i">[INFO]</span> <span class="c">Price history loaded from yfinance</span><br>
        <span class="i">[INFO]</span> <span class="c">Rows: {rows} | Columns: {cols}</span><br>
        <span class="i">[INFO]</span> <span class="c">Data ready.</span><br>
        <span class="p">$</span></div>""",
        unsafe_allow_html=True,
    )
 
 
def dark_table(headers, rows_html, max_height=560):
    head = "".join(f"<th>{h}</th>" for h in headers)
    st.markdown(
        f'<div class="dtab-wrap" style="max-height:{max_height}px;">'
        f'<table class="dtab"><thead><tr>{head}</tr></thead>'
        f"<tbody>{rows_html}</tbody></table></div>",
        unsafe_allow_html=True,
    )
 
 
def styled_comparison(df):
    rows = ""
    for _, r in df.iterrows():
        price = f"${r['Current Price']:,.2f}" if pd.notna(r["Current Price"]) else "—"
        d, y = r["Daily Change %"], r["1Y Return %"]
        dcls = "pos" if (pd.notna(d) and d >= 0) else "neg"
        ycls = "pos" if (pd.notna(y) and y >= 0) else "neg"
        dtxt = f"{d:+.2f}%" if pd.notna(d) else "—"
        ytxt = f"{y:+.2f}%" if pd.notna(y) else "—"
        hi = f"${r['52W High']:,.2f}" if pd.notna(r["52W High"]) else "—"
        lo = f"${r['52W Low']:,.2f}" if pd.notna(r["52W Low"]) else "—"
        rows += (
            f"<tr><td>{r['Company']}</td><td>{r['Ticker']}</td><td>{price}</td>"
            f"<td class='{dcls}'>{dtxt}</td><td class='{ycls}'>{ytxt}</td>"
            f"<td>{hi}</td><td>{lo}</td><td>{r['Category']}</td><td>{r['Risk Level']}</td></tr>"
        )
    dark_table(
        ["Company", "Ticker", "Price", "1D %", "Up to 1Y %", "52W High", "52W Low", "Category", "Risk"],
        rows, max_height=560,
    )
 
 
def history_table(data, limit=150):
    tbl = data[["Date", "Open", "High", "Low", "Close", "Volume"]].sort_values("Date", ascending=False).head(limit)
    rows = ""
    for _, r in tbl.iterrows():
        dt = pd.to_datetime(r["Date"]).strftime("%Y-%m-%d")
        rows += (
            f"<tr><td>{dt}</td><td>${r['Open']:,.2f}</td><td>${r['High']:,.2f}</td>"
            f"<td>${r['Low']:,.2f}</td><td>${r['Close']:,.2f}</td><td>{r['Volume']:,.0f}</td></tr>"
        )
    dark_table(["Date", "Open", "High", "Low", "Close", "Volume"], rows, max_height=380)
 
 
# =============================================================
# ROUTING
# =============================================================
with st.container(key="mobile_section_nav"):
    st.markdown("Research navigation")
    st.selectbox(
        "Choose a research section",
        PAGES,
        format_func=lambda item: item,
        key="mobile_navigation",
        on_change=sync_mobile_navigation,
        label_visibility="collapsed",
    )

page = st.session_state["active_page"]

# =============================================================
# APPLICATION HEADER + GLOBAL SECURITY SELECTOR
# =============================================================
with st.container(key="application_header"):
    header_ticker, header_selector, header_spacer, header_market, header_icons = st.columns([0.72, 1.25, 2.8, 2.0, 1.15])
    with header_selector:
        selected_company = st.selectbox(
            "Company / Ticker",
            list(COMPANIES.keys()),
            format_func=lambda company: f"{company} Inc." if company == "Apple" else company,
            key="main_company_select",
            label_visibility="collapsed",
        )
ticker = COMPANIES[selected_company]
with header_ticker:
    st.markdown(
        f"<div class='header-ticker-chip'><span class='glyph'>{'●' if ticker == 'AAPL' else '◆'}</span>{escape(ticker)}<span style='color:#8390a2'>⌄</span></div>",
        unsafe_allow_html=True,
    )
with header_market:
    market_stamp = datetime.now(ZoneInfo("America/Chicago")).strftime("%b %d, %Y %I:%M %p CT")
    st.markdown(
        f"<div class='header-market-time'>Market data as of {market_stamp}<span class='live-dot'>●</span></div>",
        unsafe_allow_html=True,
    )
with header_icons:
    st.markdown(
        """<div class='header-actions' aria-label='Dashboard utilities'>
        <span class='header-action' title='Search'>⌕</span>
        <span class='header-action' title='Help'>?</span>
        <span class='header-action' title='Notifications'>♧</span>
        <span class='header-avatar' title='Garrett Ewy'>GE</span>
        <span class='header-chevron'>⌄</span></div>""",
        unsafe_allow_html=True,
    )

if selected_company in SLEEPER_STOCKS:
    st.warning("Higher-risk coverage company. Review the underlying thesis and model assumptions carefully.")

company_pages = {
    "Overview", "Price & Chart", "Financial Statements", "Company Analysis", "Research Notes",
    "DCF Model", "Relative Valuation", "Risk & Performance", "Peer Comparison", "Company Profile",
}
security_info = get_fundamentals(ticker) if page in company_pages else {}
if page in company_pages:
    security_header(security_info)

if page == "Overview":
    page_head(f"Overview — {selected_company}", "Executive stock summary")
    overview_history = get_stock_data(ticker, "1y", "1d")
    render_overview_metrics(security_info, overview_history)
    st.markdown("#### Price performance")
    with st.container(border=True):
        price_chart(height=390, key="period_overview", selected_interval="1d", chart_type="Price")

    dcf_values = default_dcf_v2_snapshot(security_info)
    dcf_base = dcf_values.get("Base") if dcf_values else None
    dcf_gap = (dcf_base / dcf_values["Current"] - 1) if dcf_base is not None and dcf_values.get("Current") else None
    valuation_col, financial_col = st.columns(2)
    with valuation_col:
        stat_grid("Valuation Snapshot", [
            ("P/E TTM", fmt_x(g(security_info, "trailingPE"), "x")),
            ("Forward P/E", fmt_x(g(security_info, "forwardPE"), "x")),
            ("EV / EBITDA", fmt_x(g(security_info, "enterpriseToEbitda"), "x")),
            ("Base DCF V2 Value", format_price(dcf_base)),
            ("DCF Upside / Downside", percent_value(dcf_gap, signed=True)),
        ])
    with financial_col:
        stat_grid("Financial Snapshot", [
            ("Revenue TTM", value_or_unavailable(g(security_info, "totalRevenue"), fmt_big)),
            ("Revenue Growth", percent_value(g(security_info, "revenueGrowth"))),
            ("Operating Margin", percent_value(g(security_info, "operatingMargins"))),
            ("Net Income TTM", value_or_unavailable(g(security_info, "netIncomeToCommon"), fmt_big)),
            ("Free Cash Flow TTM", value_or_unavailable(g(security_info, "freeCashflow"), fmt_big)),
        ])
    research_note_block(compact=True)

elif page == "Price & Chart":
    page_head(f"Price & Chart — {selected_company}", "Detailed market history and technical context")
    c1, c2 = st.columns(2)
    with c1:
        interval = st.selectbox("Chart interval", ["1d", "1wk", "1mo"], key="price_chart_interval")
    with c2:
        chart_type = st.radio("Chart type", ["Candlestick", "Price"], horizontal=True, key="price_chart_type")
    stat_grid("Trading Range", [
        ("52-Week High", format_price(g(security_info, "fiftyTwoWeekHigh"))),
        ("52-Week Low", format_price(g(security_info, "fiftyTwoWeekLow"))),
        ("50-Day Average", format_price(g(security_info, "fiftyDayAverage"))),
        ("200-Day Average", format_price(g(security_info, "twoHundredDayAverage"))),
    ])
    with st.container(border=True):
        price_data = price_chart(height=430, key="period_price", selected_interval=interval, chart_type=chart_type, show_volume=True)
    if price_data is not None and not price_data.empty:
        st.markdown("#### Daily price history")
        history_table(price_data, limit=200)
        export = price_data[["Date", "Open", "High", "Low", "Close", "Volume"]].sort_values("Date", ascending=False)
        st.download_button("Download price history (CSV)", export.to_csv(index=False).encode("utf-8"), file_name=f"{ticker}_price_history.csv", mime="text/csv")

elif page == "Financial Statements":
    page_head(f"Financial Statements — {selected_company}", "Reported income statement, balance sheet and cash flow history")
    render_financial_statements()

elif page == "Company Analysis":
    page_head(f"Company Analysis — {selected_company}", "Fundamentals and clearly labeled research interpretation")
    render_company_analysis(security_info)

elif page == "Research Universe":
    page_head("Research Universe", "Screen and review the full 19-company coverage list")
    comparison_df, _ = get_market_data(COMPANIES)
    render_research_universe(comparison_df)

elif page == "Research Notes":
    page_head("Research Notes", "Garrett Ewy’s personal investment theses, separated from sourced facts")
    research_note_block()
    with st.expander(f"View all {len(COMPANIES)} research notes"):
        for comp in COMPANIES:
            st.markdown(f"**{comp}** — {CATEGORIES[comp]} · {RISK_LEVELS[comp]} risk")
            st.markdown(f"<div class='small-muted' style='margin-bottom:12px;'>{NOTES[comp]}</div>",
                        unsafe_allow_html=True)

elif page == "DCF Model":
    page_head(f"DCF Model — {selected_company}", "Editable scenario valuation with forecast, sensitivity and reverse DCF")
    v2_tab, v1_tab = st.tabs(["DCF V2 · Public Default", "DCF V1 · Legacy Baseline"])
    with v2_tab:
        render_dcf_v2(security_info)
    with v1_tab:
        render_dcf_model(security_info)

elif page == "Relative Valuation":
    page_head(f"Relative Valuation — {selected_company}", "Trading multiples and relevant peer context")
    render_relative_valuation(security_info)

elif page == "Risk & Performance":
    page_head(f"Risk & Performance — {selected_company}", "Historical return, volatility and drawdown analysis")
    render_risk_performance(security_info)

elif page == "Peer Comparison":
    page_head(f"Peer Comparison — {selected_company}", "Focused comparison against a small relevant peer set")
    render_peer_comparison()

elif page == "Monte Carlo — Coming Soon":
    page_head("Monte Carlo", "Coming Soon")
    st.markdown(
        """<div class="panel" style="min-height:260px;display:flex;flex-direction:column;justify-content:center;align-items:flex-start;">
        <div class="eyebrow">FUTURE MODULE</div><h3 style="margin:.45rem 0;">Coming Soon</h3>
        <p class="small-muted">Future quantitative module for probabilistic price paths, ending-price distributions, downside percentiles and probability analysis.</p>
        <p class="small-muted" style="margin-top:8px;">Monte Carlo simulations depend on model assumptions and are not price predictions.</p>
        </div>""",
        unsafe_allow_html=True,
    )

elif page == "Company Profile":
    page_head(f"Company Profile — {selected_company}", "Provider-sourced company facts")
    render_company_profile(security_info)

elif page == "Sources & Methodology":
    page_head("Sources & Methodology", "Data provenance, calculation definitions and model limitations")
    data_tab, dcf_tab, quant_tab, limits_tab = st.tabs(["Data & Refresh", "DCF", "Multiples & Risk", "Limitations"])
    with data_tab:
        st.markdown(
            """#### Provider and refresh
- Market, company-profile and financial-statement data are fetched from **Yahoo Finance through the yfinance Python library**.
- Price history is cached for 5 minutes, universe data for 10 minutes, and company fundamentals/statements for 15 minutes.
- Quotes may be current, delayed or end-of-day depending on the exchange and Yahoo Finance feed. The security header shows the provider timestamp when available.
- Annual and quarterly tabs display the provider’s reported statement periods. Missing lines are shown as unavailable or omitted; no figures are fabricated.

#### TTM methodology
TTM fields such as revenue, free cash flow and net income use provider-reported trailing values when available. The dashboard does not add annual and quarterly figures together or silently construct an alternate TTM series."""
        )
    with dcf_tab:
        st.markdown(
            """#### DCF methodology
- **Versioning:** DCF V2 is the public default. The frozen DCF V1 remains available as a separately labeled legacy baseline for comparison.
- **V1 revenue forecast:** the first-year growth assumption fades linearly toward the final forecast-year rate.
- **V2 company-aware forecast:** each covered security is assigned a disclosed primary framework, business-model modifiers and a 5–15 year explicit horizon. Growth follows Year 1, intermediate and mature anchors. Mature margins use issuer-specific guardrails rather than one universal cap.
- **FCFF-margin approach:** unlevered free cash flow is estimated from reported free cash flow plus after-tax interest, then forecast as a margin of revenue. This simplified model does not separately forecast EBIT, taxes, D&A, capital expenditure and working capital.
- **Pre-profit V2:** revenue, operating margin, NOPAT and reinvestment are forecast explicitly. Terminal value is withheld if the explicit forecast does not support positive mature cash flow and equity value.
- **Financial-institution V2:** earnings and required retention are used to estimate FCFE, which is discounted at cost of equity rather than WACC.
- **WACC:** market-value equity and debt weights combine CAPM cost of equity with after-tax cost of debt. CAPM uses the live 10-year Treasury proxy, provider beta and a disclosed 4.5% equity-risk-premium assumption. V2 discloses raw and applied beta, debt-cost inputs, weights and the exact applied discount rate.
- **Terminal value:** Gordon Growth Model using final-year FCFF, WACC and terminal growth. WACC must exceed terminal growth.
- **Net debt:** total debt less cash is subtracted from enterprise value. For banks, an equity DCF is used because deposits and borrowings are operating inputs.
- **Share count:** aggregate implied shares are preferred, followed by market cap ÷ price, then reported shares outstanding. This avoids treating a single listed share class as the whole company.
- **Special cases:** V2 intentionally withholds a consolidated Berkshire Hathaway DCF because a sum-of-the-parts or adjusted-NAV framework is more appropriate.

Bear, Base and Bull cases are mechanical spreads around transparent defaults. They are estimates, not price targets or recommendations."""
        )
        render_formula_cards([
            (
                "FCFF used by this application",
                "Levered FCF = Yahoo FCF; fallback OCF − |CapEx|  ·  FCFF = Levered FCF + |Interest| × (1 − Tax Rate)",
                "The Yahoo Finance Free Cash Flow statement field is used when present. If absent, the code uses operating cash flow less the absolute value of capital expenditure. After-tax absolute interest expense is then added back. The reported effective tax rate is capped between 0% and 35%; 21% is used when a positive pretax-income rate cannot be calculated.",
            ),
            (
                "Terminal Value · Gordon Growth",
                "TV = FCFF(n+1) / (WACC − g)",
                "The final forecast-year FCFF grows once by the terminal rate, then is capitalized as a perpetuity and discounted to present value. WACC must be greater than terminal growth.",
            ),
        ])
    with quant_tab:
        st.markdown(
            """#### Multiples
Trailing and forward P/E, PEG, EV/EBITDA, Price/Sales and Price/Book are provider-reported. Price/FCF is calculated as market capitalization divided by positive provider-reported free cash flow; it is unavailable when FCF is non-positive or missing.

#### Risk calculations
- Volatility is the standard deviation of daily returns annualized by √252.
- Maximum drawdown is the worst peak-to-trough percentage decline in the available five-year price series.
- Sharpe ratio is annualized average daily return less the current 10-year Treasury proxy, divided by annualized volatility.
- Downside volatility annualizes the standard deviation of negative daily returns.
- Peer performance rebases each valid series to 100 at its first observation."""
        )
        render_formula_cards([
            (
                "Annualized Volatility",
                "σ annual = σ daily × √252",
                "The application takes the sample standard deviation of daily percentage returns and annualizes it using 252 trading days.",
            ),
            (
                "Sharpe Ratio",
                "Sharpe = (Annualized Asset Return − Annual Risk-Free Rate) / Annualized Volatility",
                "Annualized asset return is mean daily return × 252. The risk-free input is the current annual 10-year Treasury proxy, and volatility is annualized from the same daily returns.",
            ),
            (
                "Maximum Drawdown",
                "MDD = min[ Price(t) / Running Peak(t) − 1 ]",
                "This is the largest peak-to-trough percentage decline during the selected matched measurement period.",
            ),
        ])
    with limits_tab:
        st.markdown(
            """#### Limitations
Yahoo Finance fields can be delayed, revised, missing or defined differently across companies. Statement taxonomies vary by issuer. Historical returns do not predict future returns. DCF results are highly sensitive to growth, margins, discount rates and terminal assumptions; a single consolidated DCF is especially limited for conglomerates. Peer selections are a focused subset of this project’s coverage universe, not a complete industry set.

This dashboard is an educational research project and does not provide investment advice."""
        )

elif page == "About":
    page_head("About", "Project purpose and technology")
    st.markdown(
        """<div class="panel">
        <h4>Equity Research Dashboard</h4>
        <p class="small-muted">An interactive equity-research project combining market data, financial statement analysis, valuation and quantitative research tools.</p>
        <p class="small-muted" style="margin-top:10px;">Built by <b>Garrett Ewy</b>.</p>
        <p class="small-muted" style="margin-top:10px;">Technology: Python · Streamlit · Pandas · Plotly · yfinance</p>
        <p class="small-muted" style="margin-top:10px;color:#d6a85f;">Models and commentary are for
        educational and research purposes. They are estimates, not investment recommendations.</p>
        </div>""",
        unsafe_allow_html=True,
    )
 
st.divider()
st.caption(
    "Equity Research Dashboard · Built by Garrett Ewy · Market and fundamental data via Yahoo Finance. "
    "Educational research only; not investment advice."
)
 
