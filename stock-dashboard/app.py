import logging
from html import escape

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
from dashboard_utils import (
    debt_to_equity_ratio,
    dividend_yield_percent,
    equal_weight_index,
    format_price,
    statement_value,
)


logger = logging.getLogger(__name__)
 
# =============================================================
# PAGE SETUP
# =============================================================
st.set_page_config(
    page_title="Equity Intelligence | Research Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="auto",
)
 
# ---- Color tokens (used in Python logic / Plotly / SVG) ----
BG_DEEP   = "#07111f"
CARD      = "#0f1b2d"
BORDER    = "rgba(255,255,255,0.08)"
BLUE      = "#3b82f6"
BLUE_LT   = "#60a5fa"
BLUE_DARK = "#1d4ed8"
TEXT      = "#e5eefc"
MUTED     = "#94a3b8"
GREEN     = "#22c55e"
RED       = "#ef4444"
ORANGE    = "#f59e0b"
PURPLE    = "#a78bfa"
 
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

    .product-head {
        display:flex; align-items:center; justify-content:space-between; gap:16px;
        padding:0 0 16px; margin-bottom:18px; border-bottom:1px solid var(--ei-border);
    }
    .product-head .identity { display:flex; align-items:center; gap:12px; }
    .product-mark {
        width:34px; height:34px; border-radius:9px; display:grid; place-items:center;
        color:#dbeafe; background:#152744; border:1px solid rgba(96,165,250,.34);
        font-size:17px; font-weight:800;
    }
    .product-name { color:var(--ei-text); font-size:22px; font-weight:800; letter-spacing:-.35px; }
    .product-sub { color:var(--ei-muted); font-size:12px; margin-top:1px; letter-spacing:.25px; }
    .product-byline { color:var(--ei-muted); font-size:12px; white-space:nowrap; }

    .security-header {
        display:grid; grid-template-columns:minmax(0,1.55fr) minmax(210px,.8fr); gap:20px;
        align-items:center; background:var(--ei-surface); border:1px solid var(--ei-border);
        border-radius:var(--ei-radius-md); padding:18px 20px; margin:0 0 22px;
    }
    .security-id { display:flex; align-items:center; gap:14px; min-width:0; }
    .security-symbol {
        min-width:58px; height:48px; padding:0 10px; border-radius:9px; display:grid;
        place-items:center; background:#142744; border:1px solid rgba(96,165,250,.28);
        color:#bfdbfe; font-size:15px; font-weight:800;
    }
    .security-name { color:var(--ei-text); font-size:20px; font-weight:800; line-height:1.2; }
    .security-meta { color:var(--ei-muted); font-size:12px; margin-top:5px; line-height:1.45; }
    .security-quote { text-align:right; }
    .security-price { color:var(--ei-text); font-size:27px; font-weight:800; line-height:1; }
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
        padding:15px 16px; margin-bottom:18px;
    }
    [data-testid="stSidebar"] .sb-brand .t { font-size:16px; letter-spacing:-.1px; }
    [data-testid="stSidebar"] .sb-brand .s { font-size:11px; margin-top:4px; }
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
        .product-name { font-size:19px; }
        .product-byline { display:none; }
        .security-header { padding:15px; }
        .security-id { align-items:flex-start; }
        .security-symbol { min-width:52px; height:43px; }
        .security-name { font-size:18px; }
        .security-quote { padding-left:66px; }
        .security-price { font-size:24px; }
        .stat-grid, .dcf-result-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
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
 
PERIOD_MAP = {"1M": "1mo", "6M": "6mo", "1Y": "1y", "5Y": "5y", "All": "max"}
 
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
        <div class="t">Equity Intelligence</div>
        <div class="s">Equity Research Platform</div>
    </div>
    """,
    unsafe_allow_html=True,
)

PAGES = [
    "Overview", "Company Analysis", "Financials", "Valuation",
    "Watchlist", "Research Notes", "About",
]

LEGACY_PAGE_NAMES = {
    "🏠  Overview": "Overview",
    "📊  Company Analysis": "Company Analysis",
    "📈  Financials": "Financials",
    "💲  Valuation": "Valuation",
    "⭐  Watchlist": "Watchlist",
    "📓  Notebook": "Research Notes",
    "⚙️  Settings": "About",
}
for state_key in ("active_page", "mobile_navigation"):
    if st.session_state.get(state_key) in LEGACY_PAGE_NAMES:
        st.session_state[state_key] = LEGACY_PAGE_NAMES[st.session_state[state_key]]

NAV_GROUPS = {
    "RESEARCH": ["Overview", "Company Analysis", "Financials", "Watchlist", "Research Notes"],
    "VALUATION": ["Valuation"],
    "INFORMATION": ["About"],
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

st.sidebar.divider()
st.sidebar.caption("Market and fundamentals data via Yahoo Finance. Research use only; not investment advice.")
 
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

    price_text = format_price(price)
    if change is not None and change_pct is not None:
        direction = "pos" if change >= 0 else "neg"
        change_text = f"{change:+,.2f} ({change_pct:+.2f}%)"
    else:
        direction = "neutral"
        change_text = "Change unavailable"

    st.markdown(
        f"""<div class="security-header">
        <div class="security-id">
            <div class="security-symbol">{escape(ticker)}</div>
            <div><div class="security-name">{name}</div>
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
 
 
def price_chart(height=430, key="period_main"):
    pcols = st.columns([3, 2])
    with pcols[1]:
        sel = st.radio("period", list(PERIOD_MAP.keys()), index=2, horizontal=True,
                       key=key, label_visibility="collapsed")
    period = PERIOD_MAP[sel]
    data = get_stock_data(ticker, period, interval)
    if data.empty:
        st.error("Could not load price data for this ticker (may be unavailable or rate-limited).")
        return None
 
    data = data.reset_index()
    data["MA50"] = data["Close"].rolling(50).mean()
    data["MA200"] = data["Close"].rolling(200).mean()
 
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=data["Date"], open=data["Open"], high=data["High"], low=data["Low"], close=data["Close"],
        name="Price",
        increasing=dict(line=dict(color=GREEN), fillcolor=GREEN),
        decreasing=dict(line=dict(color=RED), fillcolor=RED),
    ))
    fig.add_trace(go.Scatter(x=data["Date"], y=data["MA50"], mode="lines",
                             name="MA50", line=dict(color=ORANGE, width=1.7)))
    fig.add_trace(go.Scatter(x=data["Date"], y=data["MA200"], mode="lines",
                             name="MA200", line=dict(color=BLUE_LT, width=1.7)))
    fig.update_layout(
        template="plotly_dark", height=height, xaxis_rangeslider_visible=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, family="Inter"), margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                    bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.05)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.05)", zeroline=False)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
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
    tiles = "".join(f"<div class='stat'><div class='k'>{k}</div><div class='v'>{v}</div></div>" for k, v in pairs)
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
        template="plotly_dark", barmode="group", height=360,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, family="Inter"), margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.05)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.05)")
    st.markdown("<div style='font-size:17px;font-weight:800;color:#f8fafc;margin-bottom:6px;'>Financials Overview</div>",
                unsafe_allow_html=True)
    with st.container(border=True):
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def render_bank_equity_dcf(info, statement_data):
    """Render a bank-appropriate FCFE valuation instead of misusing net debt."""
    history = [
        row for row in statement_data["history"]
        if row.get("net_income") is not None and row.get("book_equity") is not None
    ]
    current_price = g(info, "currentPrice") or g(info, "regularMarketPrice")
    shares = g(info, "sharesOutstanding") or g(info, "impliedSharesOutstanding")
    market_cap = g(info, "marketCap")
    if shares is None and market_cap and current_price:
        shares = market_cap / current_price
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
    default_values = []
    for name in ["Bear", "Base", "Bull"]:
        assumptions = equity_scenario_assumptions(defaults, name)
        try:
            default_values.append(run_equity_dcf(
                base_net_income=float(history[-1]["net_income"]),
                starting_roe=defaults["starting_roe"],
                year_one_growth=assumptions["year_one_growth"],
                final_year_growth=assumptions["final_year_growth"],
                target_roe=assumptions["target_roe"],
                cost_of_equity=assumptions["cost_of_equity"],
                terminal_growth=assumptions["terminal_growth"],
                forecast_years=assumptions["forecast_years"],
                shares_outstanding=float(shares),
            )["value_per_share"])
        except ValueError:
            pass
    range_text = f"{format_price(min(default_values))}–{format_price(max(default_values))}" if default_values else "—"
    result_tiles = [
        ("Current Price", format_price(current_price), ""),
        (f"{scenario_name} Equity DCF", format_price(fair_value), ""),
        ("Upside / Downside", f"{upside:+.1f}%", "pos" if upside >= 0 else "neg"),
        ("Default Scenario Range", range_text, ""),
    ]
    result_html = "".join(
        f"<div class='dcf-result'><div class='k'>{label}</div><div class='v {css}'>{value}</div></div>"
        for label, value, css in result_tiles
    )
    st.markdown(f"<div class='dcf-result-grid'>{result_html}</div>", unsafe_allow_html=True)
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
            template="plotly_dark", height=310, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT, family="Inter"), margin=dict(l=10, r=10, t=28, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0), yaxis_title="$ billions",
        )
        chart.update_xaxes(gridcolor="rgba(255,255,255,0.05)")
        chart.update_yaxes(gridcolor="rgba(255,255,255,0.05)")
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
            template="plotly_dark", height=330, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
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
    shares = g(info, "sharesOutstanding") or g(info, "impliedSharesOutstanding")
    market_cap = g(info, "marketCap")
    if shares is None and market_cap and current_price:
        shares = market_cap / current_price
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
    default_values = []
    for name in ["Bear", "Base", "Bull"]:
        assumptions = scenario_assumptions(defaults, name)
        try:
            default_values.append(run_dcf(
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
            )["value_per_share"])
        except ValueError:
            pass
    range_text = "—"
    if default_values:
        range_text = f"{format_price(min(default_values))}–{format_price(max(default_values))}"

    result_tiles = [
        ("Current Price", format_price(current_price), ""),
        (f"{scenario_name} DCF Value", format_price(fair_value), ""),
        ("Upside / Downside", f"{upside:+.1f}%", upside_class),
        ("Default Scenario Range", range_text, ""),
    ]
    result_html = "".join(
        f"<div class='dcf-result'><div class='k'>{label}</div><div class='v {css}'>{value}</div></div>"
        for label, value, css in result_tiles
    )
    st.markdown(f"<div class='dcf-result-grid'>{result_html}</div>", unsafe_allow_html=True)

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
            template="plotly_dark", height=310,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=TEXT, family="Inter"), margin=dict(l=10, r=10, t=28, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            yaxis_title="$ billions",
        )
        chart.update_xaxes(gridcolor="rgba(255,255,255,0.05)")
        chart.update_yaxes(gridcolor="rgba(255,255,255,0.05)")
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
                template="plotly_dark", height=320,
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
        format_func=lambda item: f"Current section: {item}",
        key="mobile_navigation",
        on_change=sync_mobile_navigation,
        label_visibility="collapsed",
    )

page = st.session_state["active_page"]

if page in {"Overview", "Company Analysis", "Watchlist"}:
    comparison_df, basket = get_market_data(COMPANIES)
if page == "Overview":
    sp_last, sp_chg, sp_series = get_index_series("^GSPC")

st.markdown(
    """
    <div class="product-head">
        <div class="identity">
            <div class="product-mark">EI</div>
            <div><div class="product-name">Equity Intelligence</div>
            <div class="product-sub">Equity Research Platform</div></div>
        </div>
        <div class="product-byline">Built by Garrett Ewy</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# =============================================================
# MAIN PAGE CONTROLS
# =============================================================
with st.container(border=True):
    st.markdown(
        "<div style='font-size:14px;font-weight:750;color:#e7eef8;margin-bottom:8px;'>Research context</div>",
        unsafe_allow_html=True,
    )

    control_1, control_2 = st.columns([2.2, 1.2])

    with control_1:
        selected_company = st.selectbox(
            "Company / Ticker",
            list(COMPANIES.keys()),
            format_func=lambda company: f"{company} ({COMPANIES[company]})",
            key="main_company_select",
        )

    ticker = COMPANIES[selected_company]

    with control_2:
        interval = st.selectbox(
            "Chart interval",
            ["1d", "1wk", "1mo"],
            index=0,
            key="main_interval_select",
        )

if selected_company in SLEEPER_STOCKS:
    st.warning("Higher-risk coverage company. Review the underlying thesis and model assumptions carefully.")

st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

security_info = get_fundamentals(ticker) if page not in {"Watchlist", "About"} else {}
if page not in {"Watchlist", "About"}:
    security_header(security_info)

if page == "Overview":
    page_head("Overview", f"Latest available market snapshot across your {len(COMPANIES)}-stock research universe")
    summary_cards()
    st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)
    research_note_block(compact=True)
 
    left, right = st.columns([2.1, 1])
    with left:
        st.markdown(f"<div style='font-size:17px;font-weight:800;color:#f8fafc;margin-bottom:6px;'>"
                    f"{selected_company} — Price &amp; Moving Averages</div>", unsafe_allow_html=True)
        with st.container(border=True):
            chart_data = price_chart(height=420, key="period_overview")
    with right:
        watchlist_table(comparison_df)
 
    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
    info = security_info
    cc1, cc2 = st.columns([1, 1.1])
    with cc1:
        stat_grid(f"Company Analysis — {ticker}", fundamentals_pairs(info))
    with cc2:
        financials_chart()
 
    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:17px;font-weight:800;color:#f8fafc;margin-bottom:6px;'>Data Log</div>",
                unsafe_allow_html=True)
    data_log_block(chart_data)
 
elif page == "Company Analysis":
    page_head(f"Company Analysis — {selected_company}", CATEGORIES.get(selected_company, ""))
    info = security_info

    # Authored research is deliberately separated from sourced company facts.
    research_note_block()
    st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)
 
    # ---- Snapshot + key metrics ----
    a, b = st.columns([1.15, 1])
    with a:
        company_card(info)
    with b:
        stat_grid("Key Metrics", fundamentals_pairs(info))
 
    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        price_chart(height=420, key="period_company")
 
elif page == "Financials":
    page_head(f"Financials — {selected_company}", "Revenue, net income, and operating cash flow")
    financials_chart()
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
    data = get_stock_data(ticker, "1y", interval)
    if not data.empty:
        data = data.reset_index()
        st.markdown("<div style='font-size:17px;font-weight:800;color:#f8fafc;margin:6px 0;'>"
                    "Recent Price History</div>", unsafe_allow_html=True)
        history_table(data, limit=150)
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        full = data[["Date", "Open", "High", "Low", "Close", "Volume"]].sort_values("Date", ascending=False)
        st.download_button("⬇ Download price history (CSV)",
                           full.to_csv(index=False).encode("utf-8"),
                           file_name=f"{ticker}_history.csv", mime="text/csv")
 
elif page == "Valuation":
    page_head(f"Valuation — {selected_company}", "Market multiples, editable DCF, and price history")
    info = security_info
    pairs = [
        ("Market Cap", fmt_big(g(info, "marketCap"))),
        ("Trailing P/E", fmt_x(g(info, "trailingPE"))),
        ("Forward P/E", fmt_x(g(info, "forwardPE"))),
        ("PEG Ratio", fmt_x(g(info, "pegRatio"))),
        ("Price / Sales", fmt_x(g(info, "priceToSalesTrailing12Months"))),
        ("Price / Book", fmt_x(g(info, "priceToBook"))),
        ("EV / EBITDA", fmt_x(g(info, "enterpriseToEbitda"))),
        ("52W High", format_price(g(info, "fiftyTwoWeekHigh"))),
        ("52W Low", format_price(g(info, "fiftyTwoWeekLow"))),
    ]
    stat_grid(f"Valuation Multiples — {ticker}", pairs)
    render_dcf_model(info)
    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        price_chart(height=420, key="period_val")
 
elif page == "Watchlist":
    page_head("High-Upside Watchlist", "Higher-risk names with mid-to-long-term upside")
    wl = comparison_df[comparison_df["Company"].isin(SLEEPER_STOCKS)]
    cols = st.columns(len(SLEEPER_STOCKS))
    for col, comp in zip(cols, SLEEPER_STOCKS):
        r = comparison_df[comparison_df["Company"] == comp]
        with col:
            if not r.empty:
                r = r.iloc[0]
                price = f"${r['Current Price']:,.2f}" if pd.notna(r["Current Price"]) else "—"
                y = r["1Y Return %"]
                ycls = "pos" if (pd.notna(y) and y >= 0) else "neg"
                ytxt = f"{y:+.1f}% · up to 1Y" if pd.notna(y) else "—"
                st.markdown(
                    f"""<div class="sum-card"><div class="label">{comp} · {r['Ticker']}</div>
                    <div class="row"><div class="value">{price}</div></div>
                    <div class="sub {ycls}">{ytxt} · {r['Risk Level']} risk</div></div>""",
                    unsafe_allow_html=True,
                )
    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='thesis-box'>{NOTES[selected_company]}</div>"
                if selected_company in SLEEPER_STOCKS else
                "<div class='small-muted'>Select Rocket Lab, SoFi, or AST SpaceMobile in the sidebar to read its thesis.</div>",
                unsafe_allow_html=True)
    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
    page_head("Full Universe", "")
    styled_comparison(comparison_df)
    st.download_button("⬇ Download universe (CSV)", comparison_df.to_csv(index=False).encode("utf-8"),
                       file_name="equity_universe.csv", mime="text/csv")
 
elif page == "Research Notes":
    page_head("Research Notes", "Authored investment theses across the coverage universe")
    research_note_block()
    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
    with st.expander(f"View all {len(COMPANIES)} research notes"):
        for comp in COMPANIES:
            st.markdown(f"**{comp}** — {CATEGORIES[comp]} · {RISK_LEVELS[comp]} risk")
            st.markdown(f"<div class='small-muted' style='margin-bottom:12px;'>{NOTES[comp]}</div>",
                        unsafe_allow_html=True)

elif page == "About":
    page_head("About", "Project purpose and implementation")
    st.markdown(
        """<div class="panel">
        <h4>Equity Intelligence</h4>
        <p class="small-muted">Equity Intelligence is an interactive equity-research platform designed
        to combine market data, fundamental analysis, valuation and quantitative research tools in one
        workflow. The current coverage universe contains 19 public companies.</p>
        <p class="small-muted" style="margin-top:10px;">Built by <b>Garrett Ewy</b> using Python,
        Streamlit, yfinance, Pandas and Plotly. Market and fundamental information is cached to improve
        responsiveness and reduce unnecessary source requests.</p>
        <p class="small-muted" style="margin-top:10px;color:#d6a85f;">Models and commentary are for
        educational and research purposes. They are estimates, not investment recommendations.</p>
        </div>""",
        unsafe_allow_html=True,
    )
 
st.divider()
st.caption(
    "Equity Intelligence · Built by Garrett Ewy · Market and fundamental data via Yahoo Finance. "
    "Educational research only; not investment advice."
)
 
