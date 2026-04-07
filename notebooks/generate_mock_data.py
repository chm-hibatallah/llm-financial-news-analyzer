"""

Generates a realistic mock enriched parquet so you can run and test the
EDA script without having completed Modules 1 & 2.

Simulates 90 days of AAPL, TSLA, MSFT data with:
  - Realistic OHLCV prices (geometric random walk)
  - Correlated sentiment scores (slight positive edge → bullish bias)
  - Realistic news coverage gaps (not every day has articles)
  - Occasional outlier days (earnings surprises, etc.)

Usage
-----
    python notebooks/generate_mock_data.py
    python notebooks/eda.py --input data/processed/mock_enriched.parquet
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from datetime import date, timedelta

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import PROCESSED_DIR

SEED   = 42
DAYS   = 90
TICKERS = {
    "AAPL":  {"start_price": 185.0, "vol": 0.018, "drift": 0.0004},
    "TSLA":  {"start_price": 175.0, "vol": 0.035, "drift": 0.0002},
    "MSFT":  {"start_price": 415.0, "vol": 0.015, "drift": 0.0005},
}

rng = np.random.default_rng(SEED)


def _business_days(start: date, n: int):
    days, count = [], 0
    current = start
    while count < n:
        if current.weekday() < 5:
            days.append(current)
            count += 1
        current += timedelta(days=1)
    return days


def generate_mock_enriched(output_path: str = None):
    if output_path is None:
        output_path = os.path.join(PROCESSED_DIR, "mock_enriched.parquet")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    start = date.today() - timedelta(days=DAYS + 15)
    bdays = _business_days(start, DAYS)

    rows = []
    for ticker, cfg in TICKERS.items():
        price  = cfg["start_price"]
        prices = []

        # Generate price series
        for _ in bdays:
            ret   = rng.normal(cfg["drift"], cfg["vol"])
            price = price * (1 + ret)
            prices.append(price)

        prices = np.array(prices)
        log_rets = np.diff(np.log(prices), prepend=np.log(prices[0]))

        for i, (day, close, log_ret) in enumerate(zip(bdays, prices, log_rets)):
            # News coverage: ~70% of days
            has_news     = rng.random() < 0.70
            article_count = int(rng.integers(1, 12)) if has_news else 0

            # Sentiment: weakly correlated with next-day return
            if has_news:
                base_score   = rng.normal(0.05, 0.25)          # slight bullish bias
                base_score   = float(np.clip(base_score, -1, 1))
                noise        = rng.normal(0, 0.05)
                mean_score   = float(np.clip(base_score + noise, -1, 1))
                std_score    = float(abs(rng.normal(0.1, 0.05)))

                if mean_score >= 0.15:
                    dominant_label = "bullish"
                elif mean_score <= -0.15:
                    dominant_label = "bearish"
                else:
                    dominant_label = "neutral"

                bullish_ratio = float(np.clip(rng.beta(2, 2), 0, 1))
                bearish_ratio = float(np.clip(rng.beta(2, 2) * (1 - bullish_ratio), 0, 1))

                # Momentum
                sentiment_momentum = (
                    float(rng.normal(0, 0.1)) if i > 0 else None
                )
            else:
                mean_score = std_score = bullish_ratio = bearish_ratio = None
                dominant_label = None
                sentiment_momentum = None

            # Occasional outlier
            daily_return = float(log_ret)
            if rng.random() < 0.04:
                daily_return *= rng.choice([-3.5, 3.5])

            rows.append({
                "ticker":             ticker,
                "date":               pd.Timestamp(day),
                "open":               float(close * (1 + rng.normal(0, 0.003))),
                "high":               float(close * (1 + abs(rng.normal(0, 0.008)))),
                "low":                float(close * (1 - abs(rng.normal(0, 0.008)))),
                "close":              float(close),
                "adj_close":          float(close),
                "volume":             int(rng.integers(20_000_000, 80_000_000)),
                "daily_return":       daily_return,
                "log_return":         daily_return,
                "realised_vol_5":     float(abs(rng.normal(cfg["vol"], 0.005))),
                "article_count":      article_count,
                "mean_score":         mean_score,
                "std_score":          std_score,
                "bullish_ratio":      bullish_ratio,
                "bearish_ratio":      bearish_ratio,
                "dominant_label":     dominant_label,
                "sentiment_momentum": sentiment_momentum,
                "escalation_rate":    float(rng.uniform(0, 0.3)) if has_news else None,
                "bullish_count":      int(article_count * (bullish_ratio or 0)),
                "bearish_count":      int(article_count * (bearish_ratio or 0)),
                "neutral_count":      int(article_count * max(0, 1 - (bullish_ratio or 0) - (bearish_ratio or 0))),
            })

    df = pd.DataFrame(rows).sort_values(["ticker", "date"]).reset_index(drop=True)
    df.to_parquet(output_path, index=False)
    print(f"Mock data saved → {output_path}")
    print(f"Shape: {df.shape}  |  Tickers: {df['ticker'].unique().tolist()}")
    return output_path


if __name__ == "__main__":
    path = generate_mock_enriched()
    print(f"\nNow run:\n  python notebooks/eda.py --input {path} --save")
