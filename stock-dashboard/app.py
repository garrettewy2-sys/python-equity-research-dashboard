import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
 
# =============================================================
# PAGE SETUP
# =============================================================
st.set_page_config(
    page_title="Python Equity Research Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
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
 
    /* ---------- Watchlist table ---------- */
    .wl { width:100%; border-collapse:collapse; }
    .wl th { color:#94a3b8; font-size:11.5px; font-weight:600; text-transform:uppercase;
             text-align:right; padding:8px 6px; border-bottom:1px solid rgba(255,255,255,0.08); }
    .wl th:first-child { text-align:left; }
    .wl td { font-size:13.5px; padding:9px 6px; text-align:right; border-bottom:1px solid rgba(255,255,255,0.05); }
    .wl td:first-child { text-align:left; font-weight:700; color:#e5eefc; }
    .wl-scroll { max-height: 360px; overflow-y:auto; }
 
    /* ---------- Terminal ---------- */
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
    @media (max-width: 640px) {
        /* Smaller sidebar so the right side fits; still starts open and is closeable */
        section[data-testid="stSidebar"],
        section[data-testid="stSidebar"] > div:first-child,
        [data-testid="stSidebarContent"] {
            width: 13.5rem !important; min-width: 13.5rem !important;
        }
        /* Compact nav + brand so labels fit the narrower sidebar */
        [data-testid="stSidebar"] .sb-brand { padding: 10px 11px; }
        [data-testid="stSidebar"] .sb-brand .t { font-size: 13px; }
        [data-testid="stSidebar"] div[role="radiogroup"] label { padding: 7px 9px; font-size: 13px; }
 
        .block-container { padding: 1.2rem 0.9rem 2rem 0.9rem; }
        /* Stack headers so title and subtitle never touch */
        .page-head { flex-direction: column; align-items: flex-start; gap: 4px; margin-bottom: 14px; }
        .page-head .title { font-size: 22px; }
        .page-head .sub { font-size: 12.5px; }
        .top-head { flex-direction: column; align-items: flex-start; gap: 2px; }
        .top-head .th-title { font-size: 22px; }
        /* Denser grids for the narrower screen */
        .stat-grid { grid-template-columns: repeat(2, 1fr); }
        .qstats { gap: 16px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)
 
# =============================================================
# DATA: companies, categories, risk, notes
# =============================================================
COMPANIES = {
    "Apple": "AAPL", "Palantir": "PLTR", "Nvidia": "NVDA", "SpaceX": "SPCX",
    "Tesla": "TSLA", "Microsoft": "MSFT", "Amazon": "AMZN", "Alphabet / Google": "GOOGL",
    "Meta": "META", "AMD": "AMD", "Broadcom": "AVGO", "JPMorgan Chase": "JPM",
    "Goldman Sachs": "GS", "Visa": "V", "Berkshire Hathaway": "BRK-B",
    "Lockheed Martin": "LMT", "Rocket Lab": "RKLB", "SoFi": "SOFI",
    "Uber": "UBER", "AST SpaceMobile": "ASTS",
}
 
SLEEPER_STOCKS = ["Rocket Lab", "SoFi", "AST SpaceMobile"]
 
CATEGORIES = {
    "Apple": "Big Tech", "Palantir": "AI / Data", "Nvidia": "AI / Semiconductors",
    "SpaceX": "Space", "Tesla": "EV / Energy", "Microsoft": "Cloud / AI",
    "Amazon": "E-commerce / Cloud", "Alphabet / Google": "Search / AI", "Meta": "Social / AI",
    "AMD": "Semiconductors", "Broadcom": "Semiconductors", "JPMorgan Chase": "Banking",
    "Goldman Sachs": "Investment Banking", "Visa": "Payments", "Berkshire Hathaway": "Conglomerate",
    "Lockheed Martin": "Defense", "Rocket Lab": "Space", "SoFi": "Fintech",
    "Uber": "Mobility / Delivery", "AST SpaceMobile": "Space / Telecom",
}
 
RISK_LEVELS = {
    "Apple": "Lower", "Palantir": "High", "Nvidia": "Medium", "SpaceX": "High",
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
    "SpaceX": "SpaceX is a space company focused on rocket launches, Starlink satellite internet, and long-term space infrastructure. I like SpaceX because it has strong exposure to the growing space economy, satellite internet, and government space contracts. The main risk is that space is extremely expensive and technical, so the company needs strong execution over a long period of time.",
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
    return yf.Ticker(symbol).history(period=selected_period, interval=selected_interval)
 
 
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
            rows.append(base)
 
    df = pd.DataFrame(rows)
 
    basket = []
    norm = []
    for s in closes.values():
        s = s.dropna()
        if len(s) > 5:
            norm.append((s / s.iloc[0]) * 100.0)
    if norm:
        try:
            mat = pd.concat(norm, axis=1)
            basket = mat.mean(axis=1).dropna().tolist()
        except Exception:
            basket = []
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
        return None, None, []
 
 
@st.cache_data(ttl=900)
def get_fundamentals(symbol):
    try:
        return yf.Ticker(symbol).info or {}
    except Exception:
        return {}
 
 
@st.cache_data(ttl=900)
def get_financials(symbol):
    out = {"years": [], "revenue": [], "net_income": [], "ocf": []}
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
            out["years"].append(str(yr))
            rev = inc.loc["Total Revenue", c] if "Total Revenue" in inc.index else None
            ni = inc.loc["Net Income", c] if "Net Income" in inc.index else None
            ocf = None
            if cf is not None and not cf.empty and c in cf.columns:
                for k in ["Operating Cash Flow", "Total Cash From Operating Activities"]:
                    if k in cf.index:
                        ocf = cf.loc[k, c]; break
            out["revenue"].append(float(rev) if pd.notna(rev) else None)
            out["net_income"].append(float(ni) if pd.notna(ni) else None)
            out["ocf"].append(float(ocf) if (ocf is not None and pd.notna(ocf)) else None)
    except Exception:
        pass
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
        <div class="t">📈 EQUITY RESEARCH</div>
        <div class="s">Independent Project · Garrett Ewy</div>
    </div>
    """,
    unsafe_allow_html=True,
)
 
PAGES = [
    "🏠  Overview", "📊  Company Analysis", "📈  Financials", "💲  Valuation",
    "⭐  Watchlist", "📓  Notebook", "⚙️  Settings",
]
st.sidebar.markdown(
    f"<div class='nav-title'><span class='dot'>●</span> Menu</div>"
    f"<div class='nav-cap'>{len(PAGES)} sections · tap one to explore ↓</div>",
    unsafe_allow_html=True,
)
nav = st.sidebar.radio("Navigation", PAGES, label_visibility="collapsed")
 
st.sidebar.divider()
st.sidebar.markdown("**Controls**")
selected_company = st.sidebar.selectbox("Company", list(COMPANIES.keys()))
ticker = COMPANIES[selected_company]
interval = st.sidebar.selectbox("Candle interval", ["1d", "1wk", "1mo"], index=0)
st.sidebar.markdown(f"<span class='small-muted'>Ticker:</span> **{ticker}**", unsafe_allow_html=True)
 
if selected_company in SLEEPER_STOCKS:
    st.sidebar.warning("Sleeper watchlist stock: higher risk / higher potential upside.")
 
st.sidebar.divider()
st.sidebar.caption("Data via yfinance · Educational use only · Not financial advice.")
 
# ---- Shared data ----
comparison_df, basket = get_market_data(COMPANIES)
sp_last, sp_chg, sp_series = get_index_series("^GSPC")
 
 
# =============================================================
# REUSABLE RENDER BLOCKS
# =============================================================
def page_head(title, sub=""):
    st.markdown(
        f"""<div class="page-head"><div class="title">{title}</div>
        <div class="sub">{sub}</div></div>""",
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
            f"""<div class="sum-card"><div class="label">20-Stock Basket · 1Y</div>
            <div class="row"><div class="value">{b_val}</div>{b_spark}</div>
            <div class="sub {b_cls}">{b_arrow} Equal-weight, indexed</div></div>""",
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
                f"""<div class="sum-card"><div class="label">Best Performer · 1Y</div>
                <div class="row"><div class="value sm">{yname}</div></div>
                <div class="sub {ycls}">{yarrow} {yval:+.1f}%</div></div>""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """<div class="sum-card"><div class="label">Best Performer · 1Y</div>
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
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
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
        <thead><tr><th>Symbol</th><th>Price</th><th>1D %</th><th>1Y %</th></tr></thead>
        <tbody>{rows}</tbody></table></div></div>""",
        unsafe_allow_html=True,
    )
 
 
def stat_grid(title, pairs):
    tiles = "".join(f"<div class='stat'><div class='k'>{k}</div><div class='v'>{v}</div></div>" for k, v in pairs)
    st.markdown(f"<div class='panel'><h4>{title}</h4><div class='stat-grid'>{tiles}</div></div>",
                unsafe_allow_html=True)
 
 
def fundamentals_pairs(info):
    de = g(info, "debtToEquity")
    if de is not None and de > 5:
        de = de / 100.0
    dy = g(info, "dividendYield")
    if dy is not None and dy < 1:
        dy = dy * 100
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
            <div><div class="k">1Y</div><div class="v {ycls}">{ytxt}</div></div>
        </div></div>""",
        unsafe_allow_html=True,
    )
 
 
def financials_chart():
    fin = get_financials(ticker)
    if not fin["years"]:
        st.markdown("<div class='panel'><h4>Financials Overview</h4>"
                    "<p class='small-muted'>Financial statement data is unavailable for this ticker.</p></div>",
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
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
 
 
def terminal_block(data):
    rows = len(data) if data is not None else 0
    cols = data.shape[1] if data is not None else 0
    st.markdown(
        f"""<div class="terminal">
        <span class="p">$ python fetch_data.py --ticker {ticker} --interval {interval}</span><br>
        <span class="i">[INFO]</span> <span class="c">Downloading data for {ticker}</span><br>
        <span class="i">[INFO]</span> <span class="c">Data saved to data/{ticker}_history.csv</span><br>
        <span class="i">[INFO]</span> <span class="c">Rows: {rows} | Columns: {cols}</span><br>
        <span class="i">[INFO]</span> <span class="c">Success.</span><br>
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
        ["Company", "Ticker", "Price", "1D %", "1Y %", "52W High", "52W Low", "Category", "Risk"],
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
page = nav.split("  ", 1)[-1]
 
st.markdown(
    """
    <div class="top-head">
        <div class="th-title">📈 <span class="accent">Equity Research</span> Dashboard</div>
        <div class="th-sub">by Garrett Ewy</div>
    </div>
    """,
    unsafe_allow_html=True,
)
 
st.markdown(
    f"<div class='nav-hint'><span class='ic'>◀</span> This is a <b>{len(PAGES)}-section dashboard</b> — "
    "use the <b>Menu</b> on the left to explore Company Analysis, Financials, Valuation, Watchlist and more.</div>",
    unsafe_allow_html=True,
)
 
if page == "Overview":
    page_head("Overview", "Live market snapshot across your 20-stock research universe")
    summary_cards()
    st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)
 
    left, right = st.columns([2.1, 1])
    with left:
        st.markdown(f"<div style='font-size:17px;font-weight:800;color:#f8fafc;margin-bottom:6px;'>"
                    f"{selected_company} — Price &amp; Moving Averages</div>", unsafe_allow_html=True)
        with st.container(border=True):
            chart_data = price_chart(height=420, key="period_overview")
    with right:
        watchlist_table(comparison_df)
 
    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
    info = get_fundamentals(ticker)
    cc1, cc2 = st.columns([1, 1.1])
    with cc1:
        stat_grid(f"Company Analysis — {ticker}", fundamentals_pairs(info))
    with cc2:
        financials_chart()
 
    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:17px;font-weight:800;color:#f8fafc;margin-bottom:6px;'>Terminal</div>",
                unsafe_allow_html=True)
    terminal_block(chart_data)
 
elif page == "Company Analysis":
    page_head(f"Company Analysis — {selected_company}", CATEGORIES.get(selected_company, ""))
    info = get_fundamentals(ticker)
 
    # ---- Investment thesis FIRST (lead with the original research) ----
    st.markdown(
        f"<div class='thesis-head'><span class='star'>★</span> Investment Thesis — {selected_company}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(f"<div class='thesis-box thesis-lg'>{NOTES[selected_company]}</div>", unsafe_allow_html=True)
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
    page_head(f"Valuation — {selected_company}", "Multiples and 52-week range")
    info = get_fundamentals(ticker)
    pairs = [
        ("Market Cap", fmt_big(g(info, "marketCap"))),
        ("Trailing P/E", fmt_x(g(info, "trailingPE"))),
        ("Forward P/E", fmt_x(g(info, "forwardPE"))),
        ("PEG Ratio", fmt_x(g(info, "pegRatio"))),
        ("Price / Sales", fmt_x(g(info, "priceToSalesTrailing12Months"))),
        ("Price / Book", fmt_x(g(info, "priceToBook"))),
        ("EV / EBITDA", fmt_x(g(info, "enterpriseToEbitda"))),
        ("52W High", fmt_big(g(info, "fiftyTwoWeekHigh")).replace("$", "$") if g(info, "fiftyTwoWeekHigh") else "—"),
        ("52W Low", f"${g(info,'fiftyTwoWeekLow'):,.2f}" if g(info, "fiftyTwoWeekLow") else "—"),
    ]
    stat_grid(f"Valuation Multiples — {ticker}", pairs)
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
                ytxt = f"{y:+.1f}% 1Y" if pd.notna(y) else "—"
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
 
elif page == "Notebook":
    page_head("Research Notebook", "Investment theses across the universe")
    st.markdown(f"<div style='font-size:16px;font-weight:800;color:#f8fafc;margin-bottom:6px;'>"
                f"{selected_company} — Thesis</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='thesis-box'>{NOTES[selected_company]}</div>", unsafe_allow_html=True)
    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
    with st.expander("View all 20 theses"):
        for comp in COMPANIES:
            st.markdown(f"**{comp}** — {CATEGORIES[comp]} · {RISK_LEVELS[comp]} risk")
            st.markdown(f"<div class='small-muted' style='margin-bottom:12px;'>{NOTES[comp]}</div>",
                        unsafe_allow_html=True)
 
elif page == "Settings":
    page_head("Settings", "About this dashboard")
    st.markdown(
        """<div class="panel">
        <h4>Python Equity Research Dashboard</h4>
        <p class="small-muted">An independent project by <b>Garrett Ewy</b>, built with Python, Streamlit,
        yfinance, Pandas, and Plotly. It tracks 20 companies across technology, finance, defense, fintech,
        and space — comparing market metrics, visualizing price action with moving averages, and pairing
        each name with an investment thesis.</p>
        <p class="small-muted" style="margin-top:10px;">Theme colors: deep navy <code>#07111f</code>,
        panel <code>#0f1b2d</code>, accent blue <code>#3b82f6</code>. Data is cached and refreshed
        periodically via yfinance.</p>
        <p class="small-muted" style="margin-top:10px;color:#f59e0b;">For learning and research only.
        This is not financial advice.</p>
        </div>""",
        unsafe_allow_html=True,
    )
 
st.divider()
st.caption(
    "Created by Garrett Ewy. Built for educational equity research purposes using Python, Streamlit, "
    "yfinance, Pandas, and Plotly. This is not financial advice."
)
 
