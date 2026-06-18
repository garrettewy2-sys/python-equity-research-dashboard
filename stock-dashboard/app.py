import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# -----------------------------
# Page setup
# -----------------------------
st.set_page_config(
    page_title="Python Equity Research Dashboard",
    page_icon="📈",
    layout="wide"
)
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    h1 {
        font-size: 42px !important;
        font-weight: 800 !important;
    }

    h2, h3 {
        font-weight: 700 !important;
    }

    div[data-testid="stMetric"] {
    background-color: #f8f9fa;
    color: #111827 !important;
    border: 1px solid #e5e7eb;
    padding: 15px;
    border-radius: 12px;
}

div[data-testid="stMetric"] * {
    color: #111827 !important;
}

div[data-testid="stMetricLabel"] p {
    color: #4b5563 !important;
}

    .dashboard-card {
    background-color: #f8f9fa;
    color: #111827;
    padding: 18px;
    border-radius: 14px;
    border: 1px solid #e5e7eb;
    margin-bottom: 15px;
}

.dashboard-card h4 {
    color: #111827;
}

.small-muted {
    color: #4b5563;
    font-size: 15px;
}

.thesis-box {
    background-color: #f8f9fa;
    color: #111827;
    padding: 16px;
    border-radius: 14px;
    border-left: 5px solid #2563eb;
    font-size: 16px;
    line-height: 1.5;
    margin-bottom: 8px;
}
    </style>
    """,
    unsafe_allow_html=True
)
st.markdown(
    """
    <h1>📈 Python Equity Research Dashboard</h1>
    <p style='font-size: 18px; margin-top: -10px;'>
        Created by <b>Garrett Ewy</b>
    </p>
    <p class='small-muted'>
        An interactive equity research dashboard built with Python, Streamlit, yfinance, Pandas, and Plotly.
        This dashboard tracks 20 companies, compares key market metrics, visualizes price action, and includes investment thesis notes.
    </p>
    """,
    unsafe_allow_html=True
)
tab1, tab2, tab3, tab4 = st.tabs([
    "Overview",
    "High-Upside Watchlist",
    "Market Data",
    "Equity Research"
])

with tab1:
    st.markdown(
        """
        <div class='dashboard-card'>
            <h4>20 Companies</h4>
            <p class='small-muted'>
            This dashboard tracks 20 companies across technology, finance, defense, fintech, and space.
            Use the comparison table below to compare price, daily movement, one-year return, risk level, and category.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

with tab2:
    st.markdown(
        """
        <div class='dashboard-card'>
            <h4> High-Upside Watchlist</h4>
            <p class='small-muted'>
            The High-Upside watchlist includes Rocket Lab, SoFi, and AST SpaceMobile.
            These are higher-risk names with potential mid-to-long-term upside if they execute well.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

with tab3:
    st.markdown(
        """
        <div class='dashboard-card'>
            <h4>Live Market Data</h4>
            <p class='small-muted'>
            Stock price data is pulled using yfinance and shown through price metrics, candlestick charts,
            moving averages, and historical tables.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

with tab4:
    st.markdown(
        """
        <div class='dashboard-card'>
            <h4>Equity Research</h4>
            <p class='small-muted'>
            Each company includes an investment thesis explaining what the company does,
            why it may be interesting, and the main risk to watch.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )


st.divider()



# -----------------------------
# Company list
# -----------------------------
COMPANIES = {
    "Apple": "AAPL",
    "Palantir": "PLTR",
    "Nvidia": "NVDA",
    "SpaceX": "SPCX",
    "Tesla": "TSLA",
    "Microsoft": "MSFT",
    "Amazon": "AMZN",
    "Alphabet / Google": "GOOGL",
    "Meta": "META",
    "AMD": "AMD",
    "Broadcom": "AVGO",
    "JPMorgan Chase": "JPM",
    "Goldman Sachs": "GS",
    "Visa": "V",
    "Berkshire Hathaway": "BRK-B",
    "Lockheed Martin": "LMT",
    "Rocket Lab": "RKLB",
    "SoFi": "SOFI",
    "Uber": "UBER",
    "AST SpaceMobile": "ASTS"
}

SLEEPER_STOCKS = ["Rocket Lab", "SoFi", "AST SpaceMobile"]
CATEGORIES = {
    "Apple": "Big Tech",
    "Palantir": "AI / Data",
    "Nvidia": "AI / Semiconductors",
    "SpaceX": "Space",
    "Tesla": "EV / Energy",
    "Microsoft": "Cloud / AI",
    "Amazon": "E-commerce / Cloud",
    "Alphabet / Google": "Search / AI",
    "Meta": "Social / AI",
    "AMD": "Semiconductors",
    "Broadcom": "Semiconductors",
    "JPMorgan Chase": "Banking",
    "Goldman Sachs": "Investment Banking",
    "Visa": "Payments",
    "Berkshire Hathaway": "Conglomerate",
    "Lockheed Martin": "Defense",
    "Rocket Lab": "Space",
    "SoFi": "Fintech",
    "Uber": "Mobility / Delivery",
    "AST SpaceMobile": "Space / Telecom"
}

RISK_LEVELS = {
    "Apple": "Lower",
    "Palantir": "High",
    "Nvidia": "Medium",
    "SpaceX": "High",
    "Tesla": "High",
    "Microsoft": "Lower",
    "Amazon": "Medium",
    "Alphabet / Google": "Lower",
    "Meta": "Medium",
    "AMD": "High",
    "Broadcom": "Medium",
    "JPMorgan Chase": "Lower",
    "Goldman Sachs": "Medium",
    "Visa": "Lower",
    "Berkshire Hathaway": "Lower",
    "Lockheed Martin": "Lower",
    "Rocket Lab": "High",
    "SoFi": "High",
    "Uber": "Medium",
    "AST SpaceMobile": "Very High"
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

    "Berkshire Hathaway": "Berkshire Hathaway is a diversified holding company with businesses in insurance, railroads, energy, cash investments, and a large stock portfolio. I like Berkshire because it is financially strong, conservative, and diversified across many parts of the economy. The main risk is that future returns may be lower as the company gets larger and moves further beyond Warren Buffett’s leadership era.",

    "Lockheed Martin": "Lockheed Martin is a major defense company that builds aircraft, missiles, space systems, and military technology. I like Lockheed Martin because defense spending is usually more stable than many other industries and geopolitical tensions can support demand. The main risk is that the company depends heavily on government contracts and political budget decisions.",

    "Rocket Lab": "Rocket Lab is a smaller space company focused on rocket launches, satellites, and space systems. I like Rocket Lab as a sleeper stock because it has exposure to the growing space economy but is still much smaller than the largest players. The main risk is that the company is still high-risk and needs strong execution to prove it can scale profitably.",

    "SoFi": "SoFi is a fintech and banking company that offers lending, banking, investing, and personal finance products. I like SoFi as a sleeper stock because it could grow if it keeps adding members, deposits, and financial products over time. The main risk is that loan losses, credit quality, and competition from banks could hurt the business.",

    "Uber": "Uber is a platform company focused on ridesharing, food delivery, freight, and mobility services. I like Uber because it has a large global network and has become more focused on profitability. The main risk is that regulation, driver costs, and competition could pressure margins.",

    "AST SpaceMobile": "AST SpaceMobile is a space and telecom company trying to connect regular smartphones directly to satellites. I like AST SpaceMobile as a high-risk sleeper stock because the potential market could be huge if the technology works and scales. The main risk is that the business is expensive, unproven, and may need a lot of capital before becoming profitable."
}

# -----------------------------
# Sidebar controls
# -----------------------------
st.sidebar.header("Dashboard Controls")
st.sidebar.caption("Select a company, time period, and chart interval.")

selected_company = st.sidebar.selectbox(
    "Choose a company",
    list(COMPANIES.keys())
)

ticker = COMPANIES[selected_company]

period = st.sidebar.selectbox(
    "Choose time period",
    ["1mo", "3mo", "6mo", "1y", "2y", "5y"],
    index=3
)

interval = st.sidebar.selectbox(
    "Choose candle interval",
    ["1d", "1wk", "1mo"],
    index=0
)

st.sidebar.write(f"Ticker: **{ticker}**")

if selected_company in SLEEPER_STOCKS:
    st.sidebar.warning("Sleeper watchlist stock: higher risk / higher potential upside.")

# -----------------------------
# Function to get stock data
# -----------------------------
@st.cache_data(ttl=300)
def get_stock_data(symbol, selected_period, selected_interval):
    stock = yf.Ticker(symbol)
    data = stock.history(period=selected_period, interval=selected_interval)
    return data
@st.cache_data(ttl=600)
def get_comparison_data(companies):
    rows = []

    for company, symbol in companies.items():
        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period="1y", interval="1d")

            if hist.empty:
                rows.append({
                    "Company": company,
                    "Ticker": symbol,
                    "Current Price": None,
                    "Daily Change %": None,
                    "1Y Return %": None,
                    "52W High": None,
                    "52W Low": None,
                    "Category": CATEGORIES.get(company, "N/A"),
                    "Risk Level": RISK_LEVELS.get(company, "N/A")
                })
                continue

            last_close = hist["Close"].iloc[-1]
            previous_close = hist["Close"].iloc[-2] if len(hist) > 1 else last_close
            first_close = hist["Close"].iloc[0]

            daily_change_percent = ((last_close - previous_close) / previous_close) * 100
            one_year_return = ((last_close - first_close) / first_close) * 100
            high_52w = hist["High"].max()
            low_52w = hist["Low"].min()

            rows.append({
                "Company": company,
                "Ticker": symbol,
                "Current Price": last_close,
                "Daily Change %": daily_change_percent,
                "1Y Return %": one_year_return,
                "52W High": high_52w,
                "52W Low": low_52w,
                "Category": CATEGORIES.get(company, "N/A"),
                "Risk Level": RISK_LEVELS.get(company, "N/A")
            })

        except Exception:
            rows.append({
                "Company": company,
                "Ticker": symbol,
                "Current Price": None,
                "Daily Change %": None,
                "1Y Return %": None,
                "52W High": None,
                "52W Low": None,
                "Category": CATEGORIES.get(company, "N/A"),
                "Risk Level": RISK_LEVELS.get(company, "N/A")
            })

    return pd.DataFrame(rows)
# -----------------------------
# 20-company comparison table
# -----------------------------
st.subheader("Market Comparison Overview")
st.write("Compare all 20 companies across price, daily movement, one-year return, 52-week range, category, and risk level.")

comparison_df = get_comparison_data(COMPANIES)
comparison_df.index = comparison_df.index + 1
st.dataframe(
    comparison_df,
    use_container_width=True,
    column_config={
        "Current Price": st.column_config.NumberColumn(format="$%.2f"),
        "Daily Change %": st.column_config.NumberColumn(format="%.2f%%"),
        "1Y Return %": st.column_config.NumberColumn(format="%.2f%%"),
        "52W High": st.column_config.NumberColumn(format="$%.2f"),
        "52W Low": st.column_config.NumberColumn(format="$%.2f"),
    }
)

comparison_csv = comparison_df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download comparison table as CSV",
    data=comparison_csv,
    file_name="stock_comparison_table.csv",
    mime="text/csv"
)
# -----------------------------
# Load data
# -----------------------------
data = get_stock_data(ticker, period, interval)

if data.empty:
    st.error(
        "Could not load data for this ticker. It may be unavailable, too new, or temporarily blocked by Yahoo Finance."
    )
else:
    # Clean up data
    data = data.reset_index()

    st.divider()
    st.subheader(f"Company Deep Dive: {selected_company} ({ticker})")

    # -----------------------------
    # Metrics
    # -----------------------------
    last_close = data["Close"].iloc[-1]

    if len(data) > 1:
        previous_close = data["Close"].iloc[-2]
    else:
        previous_close = last_close

    price_change = last_close - previous_close

    if previous_close != 0:
        percent_change = (price_change / previous_close) * 100
    else:
        percent_change = 0

    period_high = data["High"].max()
    period_low = data["Low"].min()
    average_volume = data["Volume"].mean()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Current Price", f"${last_close:.2f}")
    col2.metric("Price Change", f"${price_change:.2f}")
    col3.metric("Percent Change", f"{percent_change:.2f}%")
    col4.metric("Average Volume", f"{average_volume:,.0f}")

    col5, col6 = st.columns(2)
    col5.metric("Period High", f"${period_high:.2f}")
    col6.metric("Period Low", f"${period_low:.2f}")

    if price_change >= 0:
        st.success(
            f"{selected_company} is trading at ${last_close:.2f}, up ${price_change:.2f} or {percent_change:.2f}% from the previous close."
        )
    else:
        st.error(
            f"{selected_company} is trading at ${last_close:.2f}, down ${abs(price_change):.2f} or {abs(percent_change):.2f}% from the previous close."
        )

    # -----------------------------
    # Moving averages
    # -----------------------------
    data["20 Day MA"] = data["Close"].rolling(window=20).mean()
    data["50 Day MA"] = data["Close"].rolling(window=50).mean()

    # -----------------------------
    # Candlestick chart
    # -----------------------------
    st.subheader("Candlestick Chart")

    fig = go.Figure()

    fig.add_trace(
        go.Candlestick(
            x=data["Date"],
            open=data["Open"],
            high=data["High"],
            low=data["Low"],
            close=data["Close"],
            name="Price"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=data["Date"],
            y=data["20 Day MA"],
            mode="lines",
            name="20 Day Moving Average"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=data["Date"],
            y=data["50 Day MA"],
            mode="lines",
            name="50 Day Moving Average"
        )
    )

    fig.update_layout(
    title=f"{selected_company} Price Chart",
    xaxis_title="Date",
    yaxis_title="Price",
    height=450,
    xaxis_rangeslider_visible=False,
    template="plotly_white",
    margin=dict(l=20, r=20, t=60, b=20),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    )
)

    st.plotly_chart(fig, use_container_width=True)

       # -----------------------------
    # Notes section
    # -----------------------------
    st.subheader("Investment Thesis")

    st.markdown(
        f"""
        <div class='thesis-box'>
            {NOTES[selected_company]}
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    st.info(
        "This dashboard is for learning and research only. It is not financial advice."
    )

    # -----------------------------
    # Historical data table
    # -----------------------------
    st.subheader("Historical Data")

    table = data[["Date", "Open", "High", "Low", "Close", "Volume"]].copy()
    table = table.sort_values("Date", ascending=False)

    st.dataframe(table, use_container_width=True)

    csv = table.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download this data as CSV",
        data=csv,
        file_name=f"{ticker}_stock_data.csv",
        mime="text/csv"
    )
    st.divider()

st.caption(
    "Created by Garrett Ewy. Built for educational equity research purposes using Python, Streamlit, yfinance, Pandas, and Plotly. This is not financial advice."
)
