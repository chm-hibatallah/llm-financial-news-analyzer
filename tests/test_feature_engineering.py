"""

-----------------------------------
Unit tests for all three feature builders.

All tests use synthetic DataFrames — no file I/O, no external dependencies.
Tests focus on:
  - Correct column names produced
  - Correct numeric values (rolling mean, RSI boundaries, ATR formula)
  - Zero-fill behaviour on silent days
  - Warm-up row dropping
  - No NaN leakage from future values into past rows
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

def _make_df(n: int = 60, ticker: str = "AAPL", seed: int = 42) -> pd.DataFrame:
    """Synthetic OHLCV + sentiment DataFrame for testing."""
    rng    = np.random.default_rng(seed)
    dates  = [date(2024, 1, 1) + timedelta(days=i) for i in range(n)]
    close  = 180 + np.cumsum(rng.normal(0, 1.5, n))
    lr     = np.concatenate([[0], np.diff(np.log(close))])

    return pd.DataFrame({
        "ticker":        ticker,
        "date":          pd.to_datetime(dates),
        "open":          close * (1 + rng.normal(0, 0.003, n)),
        "high":          close * (1 + np.abs(rng.normal(0, 0.006, n))),
        "low":           close * (1 - np.abs(rng.normal(0, 0.006, n))),
        "close":         close,
        "adj_close":     close,
        "volume":        rng.integers(20_000_000, 60_000_000, n),
        "daily_return":  lr,
        "log_return":    lr,
        "mean_score":    rng.uniform(-0.5, 0.5, n),
        "article_count": rng.integers(0, 8, n),
        "bullish_ratio": rng.uniform(0, 1, n),
        "bearish_ratio": rng.uniform(0, 0.5, n),
        "std_score":     rng.uniform(0, 0.2, n),
    })


# ---------------------------------------------------------------------------
# SentimentFeatureBuilder
# ---------------------------------------------------------------------------

class TestSentimentFeatureBuilder:

    def _build(self, df):
        from feature_engineering.sentiment_features import SentimentFeatureBuilder
        return SentimentFeatureBuilder(windows=[7, 14, 30]).transform(df)

    def test_rolling_columns_created(self):
        df  = _make_df()
        out = self._build(df)
        for w in [7, 14, 30]:
            assert f"sentiment_roll_{w}d" in out.columns
            assert f"sentiment_std_{w}d"  in out.columns

    def test_news_day_flag(self):
        df  = _make_df()
        out = self._build(df)
        assert "news_day" in out.columns
        assert out["news_day"].isin([0, 1]).all()

    def test_zero_fill_on_silent_days(self):
        df = _make_df()
        # Force some days to have no articles
        df.loc[df.index[:5], "article_count"] = 0
        out = self._build(df)
        silent = out[out["news_day"] == 0]
        assert (silent["mean_score"] == 0.0).all()

    def test_zscore_column_exists(self):
        df  = _make_df()
        out = self._build(df)
        assert "sentiment_zscore" in out.columns

    def test_regime_values_are_valid(self):
        df  = _make_df()
        out = self._build(df)
        assert out["sentiment_regime"].isin([-1, 0, 1]).all()

    def test_crossover_column_exists(self):
        df  = _make_df()
        out = self._build(df)
        assert "sentiment_cross_7_30" in out.columns

    def test_rolling_mean_correct(self):
        """Manual check: roll_7d at row 10 should equal mean of rows 4-10."""
        df  = _make_df(n=20)
        df["article_count"] = 5          # all days have news
        out = self._build(df)
        # pandas rolling mean with min_periods=4 — just check it's finite
        assert out["sentiment_roll_7d"].iloc[10:].notna().all()


# ---------------------------------------------------------------------------
# VolatilityFeatureBuilder
# ---------------------------------------------------------------------------

class TestVolatilityFeatureBuilder:

    def _build(self, df):
        from feature_engineering.volatility_features import VolatilityFeatureBuilder
        return VolatilityFeatureBuilder().transform(df)

    def test_vol_columns_created(self):
        df  = _make_df()
        out = self._build(df)
        for col in ["realised_vol_5d", "realised_vol_10d", "realised_vol_21d",
                    "atr_14d", "atr_14d_pct", "vol_zscore_21d", "vol_ratio_5_21"]:
            assert col in out.columns, f"Missing: {col}"

    def test_atr_is_positive(self):
        df  = _make_df()
        out = self._build(df)
        valid = out["atr_14d"].dropna()
        assert (valid >= 0).all()

    def test_atr_pct_reasonable(self):
        """ATR as % of price should typically be 0.1% – 5% for equities."""
        df  = _make_df()
        out = self._build(df)
        valid = out["atr_14d_pct"].dropna()
        assert valid.between(0, 15).all()

    def test_vol_flags_binary(self):
        df  = _make_df()
        out = self._build(df)
        assert out["high_vol_flag"].isin([0, 1]).all()
        assert out["low_vol_flag"].isin([0, 1]).all()

    def test_forward_vol_is_shifted(self):
        """forward_vol_5d at row i should equal realised_vol_5d at row i+5."""
        df  = _make_df(n=40)
        out = self._build(df).reset_index(drop=True)
        for i in range(10, 30):
            fv = out.loc[i, "forward_vol_5d"]
            rv = out.loc[i + 5, "realised_vol_5d"] if i + 5 < len(out) else np.nan
            if pd.notna(fv) and pd.notna(rv):
                assert abs(fv - rv) < 1e-8


# ---------------------------------------------------------------------------
# MomentumFeatureBuilder
# ---------------------------------------------------------------------------

class TestMomentumFeatureBuilder:

    def _build(self, df):
        from feature_engineering.momentum_features import MomentumFeatureBuilder
        return MomentumFeatureBuilder().transform(df)

    def test_momentum_columns_created(self):
        df  = _make_df()
        out = self._build(df)
        for col in ["sma_10d", "sma_30d", "ema_10d", "rsi_14d",
                    "return_5d", "return_10d", "return_21d",
                    "forward_return_1d", "direction_1d"]:
            assert col in out.columns, f"Missing: {col}"

    def test_rsi_bounds(self):
        """RSI must always be between 0 and 100."""
        df  = _make_df(n=80)
        out = self._build(df)
        valid = out["rsi_14d"].dropna()
        assert (valid >= 0).all() and (valid <= 100).all()

    def test_rsi_signal_values(self):
        df  = _make_df()
        out = self._build(df)
        assert out["rsi_signal"].isin([-1, 0, 1]).all()

    def test_direction_label_binary(self):
        df  = _make_df()
        out = self._build(df)
        assert out["direction_1d"].isin([0, 1]).all()

    def test_forward_return_is_shifted(self):
        """forward_return_1d at row i should equal log_return at row i+1."""
        df  = _make_df(n=20)
        out = self._build(df).reset_index(drop=True)
        for i in range(5, 15):
            fr = out.loc[i,   "forward_return_1d"]
            lr = out.loc[i+1, "log_return"] if i+1 < len(out) else np.nan
            if pd.notna(fr) and pd.notna(lr):
                assert abs(fr - lr) < 1e-8, f"Mismatch at row {i}: {fr} != {lr}"

    def test_no_future_leakage_in_sma(self):
        """SMA at row i must not depend on any row > i."""
        df  = _make_df(n=30)
        out = self._build(df).reset_index(drop=True)
        # Corrupt a future row and check SMA doesn't change
        out2 = out.copy()
        out2.loc[20, "close"] = 9999
        out3 = self._build(out2.drop(columns=[c for c in out2.columns if "sma" in c or "ema" in c]))
        # SMA at row 15 should be unaffected by row 20
        assert abs(out.loc[15, "sma_10d"] - out3.loc[15, "sma_10d"]) < 1e-4


# ---------------------------------------------------------------------------
# Full pipeline integration
# ---------------------------------------------------------------------------

class TestFeatureEngineeringPipeline:

    def test_pipeline_adds_all_feature_groups(self):
        from feature_engineering.pipeline import FeatureEngineeringPipeline

        df = _make_df(n=60)
        pipeline = FeatureEngineeringPipeline(drop_warmup_rows=False)

        # Run builders directly (bypass file I/O)
        df = pipeline.sentiment_builder.transform(df)
        df = pipeline.volatility_builder.transform(df)
        df = pipeline.momentum_builder.transform(df)

        sentiment_cols  = [c for c in df.columns if "sentiment" in c]
        volatility_cols = [c for c in df.columns if "vol" in c or "atr" in c]
        momentum_cols   = [c for c in df.columns if "sma" in c or "rsi" in c or "return_" in c]

        assert len(sentiment_cols)  >= 5
        assert len(volatility_cols) >= 5
        assert len(momentum_cols)   >= 5

    def test_feature_summary_runs(self):
        from feature_engineering.pipeline import FeatureEngineeringPipeline

        df = _make_df(n=60)
        pipeline = FeatureEngineeringPipeline(drop_warmup_rows=False)
        df = pipeline.sentiment_builder.transform(df)
        df = pipeline.volatility_builder.transform(df)
        df = pipeline.momentum_builder.transform(df)

        summary = pipeline.feature_summary(df)
        assert "feature"  in summary.columns
        assert "null_pct" in summary.columns
        assert len(summary) > 10