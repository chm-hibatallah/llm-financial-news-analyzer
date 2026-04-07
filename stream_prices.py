"""
Real-time price streaming script that continuously fetches intraday prices
and writes them to a JSON cache file for the Streamlit dashboard.

Usage:
    python stream_prices.py

This will continuously fetch prices every 60 seconds and update the cache.
Press Ctrl+C to stop.
"""

import json
import time
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Dict, List

import yfinance as yf
import pandas as pd

from config.logger import get_logger
from config.settings import CACHE_DIR, TICKERS

log = get_logger(__name__)

# Cache file for streaming prices
STREAM_CACHE = Path(CACHE_DIR) / "intraday_prices.json"


def fetch_intraday_prices(
    tickers: List[str] = None,
    interval: str = "1m"  # 1-minute candles for real-time
) -> Dict[str, List[Dict]]:
    """
    Fetch intraday prices for given tickers using 1-minute interval.
    Returns dict of ticker -> list of {timestamp, open, high, low, close, volume}
    """
    tickers = tickers or TICKERS
    result = {}
    
    try:
        # Fetch 1-day of intraday data (gives us today's prices)
        data = yf.download(
            tickers=tickers,
            interval=interval,
            period="1d",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
        
        if data.empty:
            log.warning("No intraday data returned from yfinance")
            return result
        
        # Handle single vs multiple tickers
        for ticker in tickers:
            try:
                if len(tickers) == 1:
                    df = data.copy()
                else:
                    df = data[ticker].copy() if ticker in data.columns else data.xs(ticker, axis=1, level=1)
                
                if df.empty:
                    log.warning(f"No data for {ticker}")
                    continue
                
                # Convert to list of dicts
                ticker_data = []
                for idx, row in df.iterrows():
                    ts_str = idx.isoformat() if hasattr(idx, 'isoformat') else str(idx)
                    
                    ticker_data.append({
                        "timestamp": ts_str,
                        "open": float(row.get("Open", 0) or 0),
                        "high": float(row.get("High", 0) or 0),
                        "low": float(row.get("Low", 0) or 0),
                        "close": float(row.get("Close", 0) or 0),
                        "volume": int(row.get("Volume", 0) or 0),
                    })
                
                result[ticker] = ticker_data
                log.info(f"✓ {ticker}: {len(ticker_data)} intraday candles")
                
            except Exception as e:
                log.error(f"Error processing {ticker}: {e}")
        
        return result
    
    except Exception as e:
        log.error(f"Failed to fetch intraday prices: {e}")
        return result


def save_stream_cache(data: Dict[str, List[Dict]]) -> None:
    """Save intraday price data to JSON cache file."""
    try:
        cache_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "date": date.today().isoformat(),
            "tickers": data,
        }
        
        with open(STREAM_CACHE, "w") as f:
            json.dump(cache_data, f, indent=2)
        
        # Log summary
        for ticker, prices in data.items():
            if prices:
                latest = prices[-1]
                log.info(f"  {ticker}: latest ${latest['close']:.2f} at {latest['timestamp']}")
    
    except Exception as e:
        log.error(f"Failed to save cache: {e}")


def get_latest_prices() -> Dict[str, float]:
    """
    Get the latest close price for each ticker from cache.
    Returns {ticker: close_price}
    """
    try:
        if STREAM_CACHE.exists():
            with open(STREAM_CACHE, "r") as f:
                data = json.load(f)
            
            latest_prices = {}
            for ticker, prices in data.get("tickers", {}).items():
                if prices:
                    latest_prices[ticker] = prices[-1]["close"]
            
            return latest_prices
    except Exception as e:
        log.error(f"Failed to read cache: {e}")
    
    return {}


def stream_prices(interval_seconds: int = 60, max_duration_hours: int = 90) -> None:
    """
    Continuously fetch and update intraday prices.
    
    Args:
        interval_seconds: How often to update prices (default 60 seconds)
        max_duration_hours: Maximum duration to run (default 90 hours)
    """
    log.info(f"🚀 Starting price stream (updating every {interval_seconds}s)")
    log.info(f"📁 Cache: {STREAM_CACHE}")
    
    start_time = time.time()
    max_duration_seconds = max_duration_hours * 3600
    iteration = 0
    
    try:
        while True:
            # Check if we've exceeded max duration
            elapsed = time.time() - start_time
            if elapsed > max_duration_seconds:
                log.info(f"Reached max duration ({max_duration_hours}h). Exiting.")
                break
            
            iteration += 1
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log.info(f"\n[{iteration}] {current_time} — Fetching prices...")
            
            # Fetch latest prices
            prices = fetch_intraday_prices()
            
            if prices:
                # Save to cache
                save_stream_cache(prices)
                
                # Display latest
                latest = get_latest_prices()
                log.info("Current prices:")
                for ticker, price in sorted(latest.items()):
                    log.info(f"  ${ticker}: ${price:.2f}")
            else:
                log.warning("No new price data received")
            
            # Wait for next update
            log.info(f"Next update in {interval_seconds}s...")
            time.sleep(interval_seconds)
    
    except KeyboardInterrupt:
        log.info("\n⏹️ Stream stopped by user")
    except Exception as e:
        log.error(f"Stream error: {e}", exc_info=True)
    finally:
        elapsed = time.time() - start_time
        log.info(f"Streamed for {elapsed/60:.1f} minutes ({iteration} updates)")


if __name__ == "__main__":
    # Stream prices every 60 seconds
    stream_prices(interval_seconds=60)
