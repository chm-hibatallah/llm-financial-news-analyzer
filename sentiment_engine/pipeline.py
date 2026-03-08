"""
Orchestrates the full sentiment scoring pipeline:

  1. Load the aligned raw data produced by data_collection/pipeline.py
  2. Score every article with FinBERT
  3. Escalate low-confidence articles to Claude
  4. Aggregate scored articles into the daily sentiment index
  5. Merge the index back with price data
  6. Save the enriched dataset to parquet

This is the single entry-point called by:
  - FastAPI background task  (via sentiment_engine/api_router.py)
  - CLI runner               (python -m sentiment_engine.pipeline)
  - Downstream analysis modules that need scored data

Cascade model
-------------
  Article text
      │
      ▼
  FinBERT scorer  ──── confidence ≥ threshold ──► ArticleSentiment (FinBERT)
      │
      └── confidence < threshold ──► Claude scorer ──► ArticleSentiment (Claude)
                                                              │
                                          ┌───────────────────┘
                                          ▼
                               DailySentimentIndex
                                          │
                                          ▼
                               Merged with price data
                                          │
                                          ▼
                        data/processed/enriched_<date>.parquet
"""

from __future__ import annotations

import glob
import os
from datetime import datetime, timezone
from typing import List, Optional

import pandas as pd

from config.logger import get_logger
from config.settings import PROCESSED_DIR, TICKERS
from sentiment_engine.aggregator import SentimentAggregator
from sentiment_engine.claude_scorer import ClaudeScorer
from sentiment_engine.finbert_scorer import FinBERTScorer
from sentiment_engine.schemas import ArticleSentiment, SentimentReport

log = get_logger(__name__)


class SentimentPipeline:
    """
    End-to-end sentiment scoring pipeline.

    Parameters
    ----------
    confidence_threshold : FinBERT scores below this escalate to Claude
    use_claude           : set False to disable escalation (useful for testing)
    """

    def __init__(
        self,
        confidence_threshold: float = 0.72,
        use_claude:           bool  = True,
    ):
        self.confidence_threshold = confidence_threshold
        self.use_claude           = use_claude

        self.finbert     = FinBERTScorer(confidence_threshold=confidence_threshold)
        self.claude      = ClaudeScorer() if use_claude else None
        self.aggregator  = SentimentAggregator()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run(self, input_parquet: Optional[str] = None) -> pd.DataFrame:
        """
        Execute the full sentiment pipeline.

        Parameters
        ----------
        input_parquet : path to the raw_aligned parquet from data_collection.
                        If None, the most recent file in PROCESSED_DIR is used.

        Returns
        -------
        pd.DataFrame
            Enriched DataFrame with columns from both price data and the
            daily sentiment index, keyed on (ticker, date).
            Saved to data/processed/enriched_<date>.parquet.
        """
        log.info("=" * 60)
        log.info("Starting SentimentPipeline")
        log.info("=" * 60)

        # Step 1: Load raw aligned data
        raw_df = self._load_raw_data(input_parquet)
        if raw_df.empty:
            log.error("No input data found. Run data_collection.pipeline first.")
            return pd.DataFrame()

        log.info("Loaded %d rows from input parquet.", len(raw_df))

        # Step 2: Score all articles
        all_articles = self._score_all_articles(raw_df)
        log.info("Scoring complete: %d articles scored.", len(all_articles))

        if not all_articles:
            log.warning("No articles were scored — enriched data will have no sentiment columns.")
            return raw_df

        # Step 3: Aggregate into daily sentiment index
        report: SentimentReport = self.aggregator.aggregate(all_articles)
        sentiment_df = self.aggregator.to_dataframe(report)
        self.aggregator.save(report)

        # Step 4: Merge sentiment index with price data
        enriched_df = self._merge_with_prices(raw_df, sentiment_df)

        # Step 5: Save enriched dataset
        output_path = self._save_enriched(enriched_df)
        log.info("Pipeline complete → %s (%d rows)", output_path, len(enriched_df))

        return enriched_df

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def _score_all_articles(self, raw_df: pd.DataFrame) -> List[ArticleSentiment]:
        """
        Iterate over each row in the raw DataFrame, extract individual
        articles from the pipe-separated article_texts column, score them
        with FinBERT, and escalate low-confidence ones to Claude.
        """
        all_articles: List[ArticleSentiment] = []

        # Filter rows that actually have articles
        has_articles = raw_df[raw_df["article_count"] > 0].copy()
        log.info("Rows with articles to score: %d / %d", len(has_articles), len(raw_df))

        for _, row in has_articles.iterrows():
            ticker       = row["ticker"]
            date_val     = row["date"]
            titles_raw   = str(row.get("article_titles", ""))
            texts_raw    = str(row.get("article_texts",  ""))

            # Split pipe-separated article bundles back into individual articles
            titles = [t.strip() for t in titles_raw.split(" | ") if t.strip()]
            texts  = [t.strip() for t in texts_raw.split(" | ")  if t.strip()]

            # Pad texts if lengths don't match (shouldn't happen, but defensive)
            while len(texts) < len(titles):
                texts.append("")

            if not titles:
                continue

            # Published_at: use midday of the price bar date as a proxy
            # (exact time is in the raw news JSON but not the aggregated parquet)
            published_at = datetime.combine(date_val, datetime.min.time()).replace(
                hour=12, tzinfo=timezone.utc
            )

            published_ats = [published_at] * len(titles)

            # FinBERT batch scoring
            scored = self.finbert.score_batch(
                ticker        = ticker,
                urls          = [f"{ticker}_{date_val}_{i}" for i in range(len(titles))],
                titles        = titles,
                texts         = texts,
                published_ats = published_ats,
            )

            # Claude escalation for low-confidence articles
            if self.claude:
                to_escalate = [a for a in scored if self.finbert.needs_escalation(a)]
                if to_escalate:
                    log.info(
                        "Escalating %d / %d articles for %s %s to Claude…",
                        len(to_escalate), len(scored), ticker, date_val,
                    )
                    rescored_map = {
                        a.url: self.claude.rescore(a)
                        for a in to_escalate
                    }
                    # Replace the FinBERT entries with Claude entries
                    scored = [
                        rescored_map.get(a.url, a) for a in scored
                    ]

            all_articles.extend(scored)

        return all_articles

    # ------------------------------------------------------------------
    # Merge + persist
    # ------------------------------------------------------------------

    def _merge_with_prices(
        self, raw_df: pd.DataFrame, sentiment_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Left-join prices with sentiment index on (ticker, date)."""
        if sentiment_df.empty:
            return raw_df

        # Normalise date types
        raw_df["date"]       = pd.to_datetime(raw_df["date"]).dt.date
        sentiment_df["date"] = pd.to_datetime(sentiment_df["date"]).dt.date

        # Drop article_texts (large, not needed downstream)
        drop_cols = [c for c in ["article_texts", "article_titles"] if c in raw_df.columns]
        price_df  = raw_df.drop(columns=drop_cols)

        enriched = price_df.merge(sentiment_df, on=["ticker", "date"], how="left")

        # Fill sentiment columns with 0 for days without news
        sentiment_cols = [
            "mean_score", "std_score", "bullish_ratio", "bearish_ratio",
            "escalation_rate", "sentiment_momentum",
        ]
        for col in sentiment_cols:
            if col in enriched.columns:
                enriched[col] = enriched[col].fillna(0)

        return enriched.sort_values(["ticker", "date"]).reset_index(drop=True)

    def _load_raw_data(self, path: Optional[str]) -> pd.DataFrame:
        """Load the most recent raw_aligned parquet if no path is given."""
        if path and os.path.exists(path):
            return pd.read_parquet(path)

        pattern = os.path.join(PROCESSED_DIR, "raw_aligned_*.parquet")
        files   = sorted(glob.glob(pattern))
        if not files:
            return pd.DataFrame()

        latest = files[-1]
        log.info("Auto-loading latest raw data: %s", os.path.basename(latest))
        return pd.read_parquet(latest)

    def _save_enriched(self, df: pd.DataFrame) -> str:
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        path     = os.path.join(PROCESSED_DIR, f"enriched_{date_str}.parquet")
        df.to_parquet(path, index=False)
        return path


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run FinSentiment sentiment pipeline")
    parser.add_argument("--input",      default=None,  help="Path to raw_aligned parquet")
    parser.add_argument("--no-claude",  action="store_true", help="Disable Claude escalation")
    parser.add_argument("--threshold",  type=float, default=0.72, help="FinBERT confidence threshold")
    args = parser.parse_args()

    pipeline = SentimentPipeline(
        confidence_threshold = args.threshold,
        use_claude           = not args.no_claude,
    )
    df = pipeline.run(input_parquet=args.input)

    if not df.empty:
        print("\nSample enriched output:")
        cols = ["ticker", "date", "close", "daily_return", "mean_score", "dominant_label", "article_count"]
        print(df[[c for c in cols if c in df.columns]].tail(12).to_string(index=False))