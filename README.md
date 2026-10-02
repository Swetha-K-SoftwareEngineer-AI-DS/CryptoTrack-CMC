# CryptoTrack – Cryptocurrency Market Tracker

A professional, real-time cryptocurrency market tracking dashboard built with **Python**, **Selenium WebDriver**, **pandas**, and **Streamlit**.

---

## 📸 Dashboard Preview

> **Note**: Add a screenshot of the running Streamlit dashboard here (e.g., `docs/dashboard_preview.png`).
> 
> ```markdown
> ![CryptoTrack Dashboard](docs/dashboard_preview.png)
> ```

---

## 📌 Project Overview

**CryptoTrack** is an automated cryptocurrency tracker designed to fetch live market rankings, prices, and statistics directly from [CoinMarketCap](https://coinmarketcap.com/). By leveraging Selenium WebDriver with dynamic JavaScript rendering and explicit wait conditions, CryptoTrack retrieves real-time top cryptocurrency data, formats and analyzes it through pandas, and presents it in a modern, interactive Streamlit dashboard.

---

## 🔄 How It Works (System Workflow)

The data pipeline operates in an end-to-end automated sequence:

```text
CoinMarketCap
    ↓
Selenium + Chrome
    ↓
Top 10 Cryptocurrency Data
    ↓
Pandas DataFrame
    ↓
Filtering
    ↓
Streamlit Dashboard / CSV Export
    ↓
Historical CSV Logging
```

1. **CoinMarketCap**: The authoritative live cryptocurrency rankings page serving dynamic JavaScript content.
2. **Selenium + Chrome**: Automated WebDriver (managed via `webdriver_manager`) executes headless Chrome and navigates to the target URL.
3. **Top 10 Cryptocurrency Data**: Extracts live rows while filtering out index funds, promotional banners, and non-crypto rows.
4. **Pandas DataFrame**: Cleans currency/percentage formats into numerical values and constructs a structured DataFrame.
5. **Filtering**: Non-destructive price and 24h change filter algorithms applied dynamically on user demand.
6. **Streamlit Dashboard / CSV Export**: Renders summary metrics, data tables, and provides an instant one-click CSV export download.
7. **Historical CSV Logging**: Every scrape run is timestamped (UTC ISO 8601) and appended to `data/historical_scrapes.csv` to preserve history.

---

## 🎯 Project Objective

- Eliminate dependence on mock or delayed data by scraping live market data directly from CoinMarketCap.
- Handle JavaScript-heavy single-page applications reliably using Selenium `WebDriverWait` and `expected_conditions`.
- Provide automated historical session logging with ISO timestamps to track market movement across runs.
- Deliver an interactive web dashboard with interactive filtering and one-click CSV exporting.

---

## ✨ Key Features

- **Live Market Data Scraping**: Scrapes real-time rankings and financial metrics directly from CoinMarketCap.
- **Top 10 Cryptocurrency Extraction**: Accurately extracts the top 10 ranked cryptocurrencies (excluding non-crypto index products and promoted banners).
- **Dynamic JavaScript Page Handling**: Uses explicit Selenium waits to guarantee table rendering before data extraction.
- **Headless & Headed Browser Execution**: Supports both headless (`headless=True`) and visible (`headless=False`) Google Chrome modes.
- **Interactive Streamlit Dashboard**: Clean, responsive web UI with metric cards, summary statistics, and interactive controls.
- **Market Filters**: Filter live datasets dynamically by Price range and 24h Percentage Change without altering the original dataset.
- **CSV Data Export**: One-click download button in Streamlit to export the currently filtered table to CSV.
- **Historical Session Logging**: Appends every scraping session with an ISO timestamp to `data/historical_scrapes.csv` without overwriting prior records.
- **Robust Error Handling**: Custom `CMCScraperError` exception prevents application crashes and provides clear diagnostics if network or layout issues arise.

---

## 🛠️ Technologies Used

- **Programming Language**: Python 3.10+ (Tested on Python 3.14)
- **Web Automation**: Selenium 4.x
- **Browser Driver Manager**: `webdriver_manager`
- **Target Browser**: Google Chrome & ChromeDriver
- **Data Manipulation**: `pandas`
- **User Interface**: `streamlit`
- **Storage / Formats**: CSV, UTF-8

---

## 📂 Project Structure

```text
CryptoTrack/
│
├── app.py                     # Main Streamlit web application & UI
├── requirements.txt           # Python dependencies
├── README.md                  # Project documentation
├── LICENSE                    # MIT License
├── .gitignore                 # Git ignore rules
│
├── services/
│   ├── __init__.py            # Services package initialization
│   └── cmc_scraper.py         # Selenium scraper, filters, CSV exporter & logger
│
├── data/
│   ├── .gitkeep               # Preserves data directory structure in Git
│   └── historical_scrapes.csv # Persistent historical append log
│
└── exports/
    ├── .gitkeep               # Preserves exports directory structure in Git
    └── crypto_data.csv        # Exported CSV snapshot
```

---

## 📊 Top 10 Cryptocurrency Data Fields

Each extracted record contains the following 6 fields:

| Field | Type | Description | Example |
|---|---|---|---|
| **Rank** | `int` | Current market cap rank | `1` |
| **Name** | `str` | Full cryptocurrency name | `Bitcoin` |
| **Symbol** | `str` | Asset ticker symbol | `BTC` |
| **Price** | `float` | Current price in USD | `86757.23` |
| **24h Change** | `float` | 24-hour percentage price change | `+3.73` |
| **Market Cap** | `float` | Total market capitalization in USD | `1740000000000.0` |

---

## 🔍 Filtering Functionality

CryptoTrack includes dedicated, non-destructive filtering functions:

- **`filter_by_price(df, min_price=None, max_price=None)`**: Filters assets by minimum and/or maximum USD price.
- **`filter_by_24h_change(df, min_change=None, max_change=None)`**: Filters assets by minimum and/or maximum 24h percentage change.

Both functions return a fresh DataFrame copy, leaving the original dataset in `st.session_state` intact.

---

## 💾 CSV Export & Historical Logging

### 1. Snapshot Export (`exports/crypto_data.csv` or Web Download)
- The `export_to_csv(df, filepath)` function saves the current table to CSV.
- In the dashboard, the **"📥 Download Current Data CSV"** button exports the currently displayed (filtered) data directly through the browser.

### 2. Historical Append Logging (`data/historical_scrapes.csv`)
- The `log_to_historical_csv(df, filepath)` function appends new scrape records with a `Timestamp` column (`ISO 8601`).
- Preserves all historical records across sessions without overwriting.
- Automatically creates parent directories and writes headers only when the file is initially created.

---

## 🌐 Headless Browser Execution

The scraper supports both execution modes:

```python
# Headless mode (default for web apps and automated jobs)
df = get_cmc_top_cryptos(limit=10, headless=True)

# Headed mode (opens a visible Chrome window for visual debugging)
df = get_cmc_top_cryptos(limit=10, headless=False)
```

Chrome options include `--no-sandbox`, `--disable-dev-shm-usage`, `--window-size=1920,1080`, custom user-agents, and automated ChromeDriver management via `webdriver_manager`.

---

## 🚀 Installation & Setup

### Prerequisites
- Python 3.10 or higher
- Google Chrome browser installed on the system

### 1. Clone or Navigate to the Repository
```bash
git clone <repository-url>
cd "CryptoTrack – Cryptocurrency Market Tracker"
```

### 2. Install Dependencies
```bash
python -m pip install -r requirements.txt
```

---

## 🖥️ How to Run the Application

### Option 1: Run the Streamlit Web Dashboard
```bash
python -m streamlit run app.py
```
Open your browser and navigate to `http://localhost:8501`.

### Option 2: Run the Standalone Scraper Test
```bash
python services/cmc_scraper.py
```
This runs the full backend test suite:
- Scrapes the live CoinMarketCap top 10
- Exports a CSV snapshot to `exports/crypto_data.csv`
- Appends historical logs to `data/historical_scrapes.csv`
- Tests price and 24h percentage change filters
- Verifies dataset immutability and column integrity

---

## ⚠️ Current Limitations

- Scraping relies on CoinMarketCap's live HTML DOM structure; significant layout redesigns may require selector updates.
- Scraper scope is currently configured for top 10 assets.
- Requires network connectivity and access to CoinMarketCap and ChromeDriver endpoints.

---

## 🔮 Future Scope

- Configurable scrape limits (e.g., Top 50, Top 100).
- Interactive historical trend charts and price volatility graphs.
- Scheduled automatic background scraping jobs.
- Multi-currency support (EUR, GBP, JPY, INR).
- Customizable asset watchlists and price alerts.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
