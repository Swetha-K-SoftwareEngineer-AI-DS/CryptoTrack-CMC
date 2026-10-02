"""
CryptoTrack – Cryptocurrency Market Tracker
Streamlit Web Application
"""

from datetime import datetime, timezone
import os
import pandas as pd
import streamlit as st

from services.cmc_scraper import (
    CMCScraperError,
    get_cmc_top_cryptos,
    log_to_historical_csv,
    filter_by_price,
    filter_by_24h_change,
)

# 1. Page Configuration
st.set_page_config(
    page_title="CryptoTrack – Cryptocurrency Market Tracker",
    page_icon="🪙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for a clean, professional aesthetic
st.markdown(
    """
    <style>
        .main-header {
            font-size: 2.2rem;
            font-weight: 700;
            color: #1E293B;
            margin-bottom: 0.1rem;
        }
        .sub-header {
            font-size: 1.2rem;
            font-weight: 600;
            color: #3B82F6;
            margin-bottom: 0.4rem;
        }
        .caption-text {
            font-size: 0.95rem;
            color: #64748B;
            margin-bottom: 1.5rem;
        }
        .metric-card {
            background-color: #F8FAFC;
            border-radius: 8px;
            padding: 16px;
            border: 1px solid #E2E8F0;
        }
        .positive-change {
            color: #16A34A;
            font-weight: 600;
        }
        .negative-change {
            color: #DC2626;
            font-weight: 600;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def format_large_currency(num: float | None) -> str:
    """Format large numbers into human-readable currency strings (T, B, M)."""
    if num is None or pd.isna(num):
        return "N/A"
    if num >= 1e12:
        return f"${num / 1e12:,.2f} T"
    if num >= 1e9:
        return f"${num / 1e9:,.2f} B"
    if num >= 1e6:
        return f"${num / 1e6:,.2f} M"
    return f"${num:,.2f}"


def format_price(price: float | None) -> str:
    """Format price with appropriate precision based on magnitude."""
    if price is None or pd.isna(price):
        return "N/A"
    if price >= 1.0:
        return f"${price:,.2f}"
    return f"${price:,.4f}"


def format_percentage(val: float | None) -> str:
    """Format percentage with +/- prefix."""
    if val is None or pd.isna(val):
        return "N/A"
    prefix = "+" if val > 0 else ""
    return f"{prefix}{val:.2f}%"


# Initialize Session State
if "market_data" not in st.session_state:
    st.session_state["market_data"] = None

if "last_scraped_time" not in st.session_state:
    st.session_state["last_scraped_time"] = None

if "scrape_error" not in st.session_state:
    st.session_state["scrape_error"] = None


# 2. Header
col_header_left, col_header_right = st.columns([3, 1])
with col_header_left:
    st.markdown('<div class="main-header">CryptoTrack</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Cryptocurrency Market Tracker</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="caption-text">Real-Time Cryptocurrency Market Data powered by CoinMarketCap</div>',
        unsafe_allow_html=True,
    )

with col_header_right:
    st.write("")
    # 3. Scrape Control Button
    if st.button("🔄 Fetch Live Market Data", type="primary", width="stretch"):
        st.session_state["scrape_error"] = None
        with st.spinner("Starting Selenium Chrome WebDriver to scrape live data from CoinMarketCap..."):
            try:
                scraped_df = get_cmc_top_cryptos(limit=10, headless=True)
                st.session_state["market_data"] = scraped_df
                st.session_state["last_scraped_time"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                # Append to historical CSV log
                log_to_historical_csv(scraped_df, filepath="data/historical_scrapes.csv")
                st.toast("Live market data scraped successfully!", icon="✅")
            except CMCScraperError as err:
                st.session_state["scrape_error"] = f"CoinMarketCap Scraping Error: {str(err)}"
            except Exception as err:
                st.session_state["scrape_error"] = f"Unexpected Scraping Failure: {str(err)}"

# Error Alert Banner
if st.session_state["scrape_error"]:
    st.error(
        f"⚠️ **Unable to retrieve live market data from CoinMarketCap.**\n\n"
        f"Details: {st.session_state['scrape_error']}"
    )

# Sidebar: 6. Filters
st.sidebar.header("Market Filters")

df_raw = st.session_state["market_data"]

if df_raw is not None and not df_raw.empty:
    min_available_price = float(df_raw["Price"].min())
    max_available_price = float(df_raw["Price"].max())
    min_available_change = float(df_raw["24h Change"].min())
    max_available_change = float(df_raw["24h Change"].max())

    st.sidebar.markdown("### Price Range ($)")
    filter_min_p = st.sidebar.number_input(
        "Min Price ($)",
        min_value=0.0,
        max_value=max_available_price,
        value=0.0,
        step=10.0,
    )
    filter_max_p = st.sidebar.number_input(
        "Max Price ($)",
        min_value=0.0,
        max_value=max_available_price * 1.5,
        value=float(max_available_price * 1.05),
        step=100.0,
    )

    st.sidebar.markdown("### 24h Change Range (%)")
    filter_min_c = st.sidebar.number_input(
        "Min 24h Change (%)",
        min_value=-100.0,
        max_value=100.0,
        value=float(min_available_change - 1.0),
        step=0.5,
    )
    filter_max_c = st.sidebar.number_input(
        "Max 24h Change (%)",
        min_value=-100.0,
        max_value=500.0,
        value=float(max_available_change + 1.0),
        step=0.5,
    )

    # Apply backend filter functions
    filtered_df = filter_by_price(df_raw, min_price=filter_min_p, max_price=filter_max_p)
    filtered_df = filter_by_24h_change(filtered_df, min_change=filter_min_c, max_change=filter_max_c)

    if st.sidebar.button("Reset Filters", width="stretch"):
        st.rerun()

else:
    st.sidebar.info("Fetch live market data to enable interactive filters.")
    filtered_df = None


# Display Main Content
if df_raw is not None and not df_raw.empty:
    if st.session_state["last_scraped_time"]:
        st.caption(f"🕒 **Last Scraped**: {st.session_state['last_scraped_time']}")

    # 5. Summary Metrics
    st.subheader("Market Overview Summary")
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

    with metric_col1:
        st.metric(
            label="Coins Displayed",
            value=f"{len(filtered_df)} / {len(df_raw)}",
        )

    with metric_col2:
        if not filtered_df.empty:
            highest_price_row = filtered_df.loc[filtered_df["Price"].idxmax()]
            st.metric(
                label="Highest Priced Coin",
                value=format_price(highest_price_row["Price"]),
                delta=f"{highest_price_row['Name']} ({highest_price_row['Symbol']})",
                delta_color="off",
            )
        else:
            st.metric(label="Highest Priced Coin", value="N/A")

    with metric_col3:
        if not filtered_df.empty:
            highest_gain_row = filtered_df.loc[filtered_df["24h Change"].idxmax()]
            st.metric(
                label="Top 24h Gainer",
                value=f"{highest_gain_row['24h Change']:+.2f}%",
                delta=f"{highest_gain_row['Name']} ({highest_gain_row['Symbol']})",
                delta_color="normal",
            )
        else:
            st.metric(label="Top 24h Gainer", value="N/A")

    with metric_col4:
        if not filtered_df.empty:
            total_mcap = filtered_df["Market Cap"].sum()
            st.metric(
                label="Total Market Cap (Displayed)",
                value=format_large_currency(total_mcap),
            )
        else:
            st.metric(label="Total Market Cap (Displayed)", value="N/A")

    st.markdown("---")

    # 4. Top 10 Market Table
    st.subheader("Top 10 Live Cryptocurrency Market Data")

    if filtered_df.empty:
        st.warning("No cryptocurrencies match your active filter criteria. Try adjusting the sidebar filters.")
    else:
        # Build formatted presentation table
        display_df = filtered_df.copy()
        display_df["Formatted Price"] = display_df["Price"].apply(format_price)
        display_df["Formatted 24h Change"] = display_df["24h Change"].apply(format_percentage)
        display_df["Formatted Market Cap"] = display_df["Market Cap"].apply(format_large_currency)

        table_to_render = display_df[[
            "Rank",
            "Name",
            "Symbol",
            "Formatted Price",
            "Formatted 24h Change",
            "Formatted Market Cap",
        ]].rename(
            columns={
                "Formatted Price": "Price",
                "Formatted 24h Change": "24h Change",
                "Formatted Market Cap": "Market Cap",
            }
        )

        st.dataframe(
            table_to_render,
            width="stretch",
            hide_index=True,
        )

    # 7. CSV Export Button
    st.markdown("### Data Export")
    if not filtered_df.empty:
        csv_export_bytes = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Current Data CSV",
            data=csv_export_bytes,
            file_name="crypto_data.csv",
            mime="text/csv",
            width="content",
        )
    else:
        st.button("📥 Download Current Data CSV", disabled=True)

else:
    if not st.session_state["scrape_error"]:
        st.info("💡 Click **'🔄 Fetch Live Market Data'** above to launch the Selenium scraper and retrieve real-time CoinMarketCap rankings.")

st.markdown("---")

# 8. Historical Data Section
st.subheader("Historical Scrape Records")

historical_file = "data/historical_scrapes.csv"

if os.path.exists(historical_file) and os.path.getsize(historical_file) > 0:
    try:
        hist_df = pd.read_csv(historical_file)
        hist_count = len(hist_df)
        latest_timestamp = hist_df["Timestamp"].iloc[-1] if "Timestamp" in hist_df.columns and not hist_df.empty else "N/A"

        hist_col1, hist_col2 = st.columns(2)
        with hist_col1:
            st.metric("Total Historical Records Logged", value=f"{hist_count:,}")
        with hist_col2:
            st.metric("Latest Session Timestamp", value=str(latest_timestamp))

        with st.expander("📂 View Full Historical Log Table", expanded=False):
            st.dataframe(
                hist_df,
                width="stretch",
                hide_index=True,
            )
    except Exception as hist_err:
        st.warning(f"Could not load historical log: {hist_err}")
else:
    st.info("No historical scrapes logged yet. Running a live market scrape will create and populate the historical log.")
