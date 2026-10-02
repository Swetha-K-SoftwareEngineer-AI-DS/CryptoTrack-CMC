"""
CoinMarketCap Selenium Scraper Service
Extracts real-time top cryptocurrency data directly from CoinMarketCap,
with support for CSV export, historical append logging, and dataset filtering.
"""

from datetime import datetime, timezone
import json
import os
import re
import urllib.request
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


class CMCScraperError(Exception):
    """Custom exception raised when CoinMarketCap scraping fails."""
    pass


def _get_doh_ip(domain: str = "coinmarketcap.com") -> str:
    """Resolve IP address using DNS-over-HTTPS (Google DoH)."""
    try:
        url = f"https://dns.google/resolve?name={domain}&type=A"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            for answer in data.get("Answer", []):
                if answer.get("type") == 1:
                    return str(answer.get("data"))
    except Exception:
        pass
    # Reliable fallback IP for coinmarketcap.com edge
    return "18.161.246.119"


def _clean_numeric(value_str: str) -> float | None:
    """Helper to convert formatted currency/percentage strings to float."""
    if not value_str or not isinstance(value_str, str):
        return None
    cleaned = value_str.replace("$", "").replace(",", "").replace("%", "").strip()
    multiplier = 1.0
    if cleaned.endswith("T"):
        multiplier = 1e12
        cleaned = cleaned[:-1]
    elif cleaned.endswith("B"):
        multiplier = 1e9
        cleaned = cleaned[:-1]
    elif cleaned.endswith("M"):
        multiplier = 1e6
        cleaned = cleaned[:-1]
    elif cleaned.endswith("K"):
        multiplier = 1e3
        cleaned = cleaned[:-1]
    try:
        return float(cleaned) * multiplier
    except (ValueError, TypeError):
        return None


def get_cmc_top_cryptos(limit: int = 10, headless: bool = True) -> pd.DataFrame:
    """
    Scrapes the top N cryptocurrencies from CoinMarketCap.

    Parameters:
        limit (int): Number of top cryptocurrencies to extract (default: 10).
        headless (bool): Whether to run Chrome in headless mode (default: True).

    Returns:
        pd.DataFrame: DataFrame containing Rank, Name, Symbol, Price, 24h Change, Market Cap.

    Raises:
        CMCScraperError: If scraping or data parsing fails.
    """
    driver = None
    try:
        # Configure Chrome Options
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        # Ensure DNS resolution works across various network environments
        cmc_ip = _get_doh_ip("coinmarketcap.com")
        if cmc_ip:
            chrome_options.add_argument(
                f"--host-resolver-rules=MAP coinmarketcap.com {cmc_ip}, "
                f"MAP *.coinmarketcap.com {cmc_ip}, "
                f"MAP *.cmc.io {cmc_ip}"
            )

        # Initialize WebDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        target_url = "https://coinmarketcap.com/"
        driver.get(target_url)

        # Wait for the table to appear and rows to populate
        wait = WebDriverWait(driver, 25)
        wait.until(
            EC.presence_of_element_located((By.XPATH, "//table//tbody/tr"))
        )
        wait.until(
            lambda d: len(d.find_elements(By.XPATH, "//table//tbody/tr")) >= limit
        )

        rows = driver.find_elements(By.XPATH, "//table//tbody/tr")
        if not rows:
            raise CMCScraperError("No cryptocurrency rows found in CoinMarketCap table.")

        records = []
        expected_rank = 1

        for row in rows:
            if len(records) >= limit:
                break

            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) < 6:
                continue

            try:
                # Rank Extraction
                rank_raw = cells[1].text.strip()
                rank_digits = re.findall(r"^\d+", rank_raw)
                
                # Filter out promotional banner rows (e.g. DTF / Index products)
                row_text = row.text
                if "Index" in row_text and "DTF" in row_text:
                    continue

                if rank_digits:
                    rank_num = int(rank_digits[0])
                else:
                    rank_num = expected_rank

                # Name and Symbol
                name_cell = cells[2]
                name_paras = [p.text.strip() for p in name_cell.find_elements(By.TAG_NAME, "p") if p.text.strip()]
                
                if len(name_paras) >= 2:
                    name = name_paras[0]
                    symbol = name_paras[1]
                else:
                    parts = [p.strip() for p in name_cell.text.split("\n") if p.strip()]
                    if len(parts) >= 2:
                        name = parts[0]
                        symbol = parts[1]
                    else:
                        name = name_cell.text.strip()
                        symbol = ""

                # Filter non-crypto index header rows
                if "Index" in name and "CMC" in symbol:
                    continue

                # Price
                price_cell = cells[3]
                price = _clean_numeric(price_cell.text.strip())

                # 24h Change
                change_24h = None
                change_cell = None
                
                if len(cells) >= 6:
                    for candidate_cell in [cells[5], cells[4]]:
                        cell_txt = candidate_cell.text.strip()
                        if "%" in cell_txt or re.search(r"\d+(\.\d+)?%", cell_txt):
                            change_cell = candidate_cell
                            break

                if change_cell is not None:
                    raw_change = change_cell.text.strip()
                    val = _clean_numeric(raw_change)
                    if val is not None:
                        html = change_cell.get_attribute("innerHTML")
                        is_negative = (
                            "-" in raw_change
                            or "icon-Caret-down" in html
                            or "color-down" in html
                            or "caret-down" in html
                            or "decrease" in html
                            or "icon-caret-down" in html.lower()
                        )
                        change_24h = -abs(val) if is_negative else abs(val)

                # Market Cap
                market_cap = None
                for idx in [7, 6, 8, 5]:
                    if idx < len(cells):
                        cap_text = cells[idx].text.strip()
                        if "$" in cap_text:
                            parsed_cap = _clean_numeric(cap_text)
                            if parsed_cap is not None and (price is None or parsed_cap > price):
                                market_cap = parsed_cap
                                break

                records.append({
                    "Rank": rank_num,
                    "Name": name,
                    "Symbol": symbol,
                    "Price": price,
                    "24h Change": change_24h,
                    "Market Cap": market_cap,
                })
                expected_rank += 1

            except Exception:
                continue

        if len(records) < limit:
            raise CMCScraperError(
                f"Extracted only {len(records)} records, expected {limit}. CoinMarketCap structure might have changed."
            )

        df = pd.DataFrame(records[:limit])

        # Column type casting
        df["Rank"] = df["Rank"].astype(int)
        df["Name"] = df["Name"].astype(str)
        df["Symbol"] = df["Symbol"].astype(str)
        df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
        df["24h Change"] = pd.to_numeric(df["24h Change"], errors="coerce")
        df["Market Cap"] = pd.to_numeric(df["Market Cap"], errors="coerce")

        return df

    except Exception as exc:
        if isinstance(exc, CMCScraperError):
            raise
        raise CMCScraperError(f"Selenium scraping failed: {str(exc)}") from exc

    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass


def export_to_csv(df: pd.DataFrame, filepath: str = "exports/crypto_data.csv") -> str:
    """
    Saves the current scraped DataFrame to a CSV file.

    Parameters:
        df (pd.DataFrame): The cryptocurrency DataFrame.
        filepath (str): Target CSV path (default: 'exports/crypto_data.csv').

    Returns:
        str: Absolute or normalized file path of the saved CSV.
    """
    if df is None or df.empty:
        raise ValueError("Cannot export empty or None DataFrame.")

    target_dir = os.path.dirname(filepath)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)

    df.to_csv(filepath, index=False)
    return filepath


def log_to_historical_csv(df: pd.DataFrame, filepath: str = "data/historical_scrapes.csv") -> str:
    """
    Appends the scraped DataFrame to a historical CSV log with an ISO timestamp.

    Parameters:
        df (pd.DataFrame): The cryptocurrency DataFrame.
        filepath (str): Target historical CSV path (default: 'data/historical_scrapes.csv').

    Returns:
        str: Absolute or normalized file path of the historical CSV.
    """
    if df is None or df.empty:
        raise ValueError("Cannot log empty or None DataFrame.")

    target_dir = os.path.dirname(filepath)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)

    # Create copy and prepend Timestamp column
    log_df = df.copy()
    current_iso_time = datetime.now(timezone.utc).isoformat()
    log_df.insert(0, "Timestamp", current_iso_time)

    # Check if file exists and has content to decide header writing
    file_exists = os.path.exists(filepath) and os.path.getsize(filepath) > 0

    log_df.to_csv(filepath, mode="a", index=False, header=not file_exists)
    return filepath


def filter_by_price(
    df: pd.DataFrame,
    min_price: float | None = None,
    max_price: float | None = None,
) -> pd.DataFrame:
    """
    Filters cryptocurrency DataFrame by price range.

    Parameters:
        df (pd.DataFrame): The input DataFrame.
        min_price (float, optional): Minimum price threshold (inclusive).
        max_price (float, optional): Maximum price threshold (inclusive).

    Returns:
        pd.DataFrame: A new filtered DataFrame.
    """
    if df is None:
        raise ValueError("Input DataFrame cannot be None.")
    if "Price" not in df.columns:
        raise ValueError("Required column 'Price' not found in DataFrame.")

    filtered_df = df.copy()
    if min_price is not None:
        filtered_df = filtered_df[filtered_df["Price"] >= min_price]
    if max_price is not None:
        filtered_df = filtered_df[filtered_df["Price"] <= max_price]

    return filtered_df


def filter_by_24h_change(
    df: pd.DataFrame,
    min_change: float | None = None,
    max_change: float | None = None,
) -> pd.DataFrame:
    """
    Filters cryptocurrency DataFrame by 24h percentage change range.

    Parameters:
        df (pd.DataFrame): The input DataFrame.
        min_change (float, optional): Minimum 24h change percentage (inclusive).
        max_change (float, optional): Maximum 24h change percentage (inclusive).

    Returns:
        pd.DataFrame: A new filtered DataFrame.
    """
    if df is None:
        raise ValueError("Input DataFrame cannot be None.")
    if "24h Change" not in df.columns:
        raise ValueError("Required column '24h Change' not found in DataFrame.")

    filtered_df = df.copy()
    if min_change is not None:
        filtered_df = filtered_df[filtered_df["24h Change"] >= min_change]
    if max_change is not None:
        filtered_df = filtered_df[filtered_df["24h Change"] <= max_change]

    return filtered_df


if __name__ == "__main__":
    print("--- 1. Live Scraping Top 10 Cryptocurrencies ---")
    try:
        crypto_df = get_cmc_top_cryptos(limit=10, headless=True)
        original_count = len(crypto_df)
        print(f"Original number of records scraped: {original_count}\n")
        print("--- Original DataFrame ---")
        print(crypto_df.to_string(index=False))

        # 2. Test Price Filtering
        # Choose dynamic threshold based on scraped prices: e.g. min_price = $10.0
        price_min_thresh = 10.0
        price_filtered_df = filter_by_price(crypto_df, min_price=price_min_thresh)
        print(f"\n--- Price-Filtered Records (Price >= ${price_min_thresh}) ---")
        print(price_filtered_df.to_string(index=False))
        print(f"Number of records after price filter: {len(price_filtered_df)}")

        # 3. Test 24h Change Filtering
        # Choose dynamic threshold: e.g. coins with positive 24h change >= 1.0%
        change_min_thresh = 1.0
        change_filtered_df = filter_by_24h_change(crypto_df, min_change=change_min_thresh)
        print(f"\n--- 24h Change Filtered Records (24h Change >= {change_min_thresh}%) ---")
        print(change_filtered_df.to_string(index=False))
        print(f"Number of records after 24h change filter: {len(change_filtered_df)}")

        # 4. Verify Original DataFrame Immutability
        print("\n--- Immutability Verification ---")
        print(f"Original DataFrame length before filtering: {original_count}")
        print(f"Original DataFrame length after filtering: {len(crypto_df)}")
        is_unmodified = len(crypto_df) == original_count and list(crypto_df.columns) == [
            "Rank", "Name", "Symbol", "Price", "24h Change", "Market Cap"
        ]
        print(f"Original DataFrame remains completely unmodified: {is_unmodified}")

    except CMCScraperError as err:
        print(f"\nScraping failed with CMCScraperError: {err}")
    except Exception as err:
        print(f"\nUnexpected error: {err}")
