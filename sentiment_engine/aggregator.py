"""
Builds the daily sentiment index from a list of scored articles.

Responsibilities
----------------
1. Group ArticleSentiment objects by (ticker, date)
2. For each group, produce a DailySentimentIndex via the schema's
   from_articles() factory
3. Compute sentiment_momentum (day-over-day change in mean_score)
4. Save the resulting index to a dated parquet file

The aggregator is intentionally decoupled from the scorers — it only
cares about ArticleSentiment objects, not how they were produced.
"""

from __future__ import annotations

import os
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Dict, List, Optional, Tuple

import pandas as pd

from config.logger import get_logger
from config.settings import PROCESSED_DIR
from sentiment_engine.schemas import (
    ArticleSentiment,
    DailySentimentIndex,
    SentimentReport,
)

log = get_logger(__name__)


class SentimentAggregator:
    """
    Aggregates article-level scores into a daily sentiment index.

    Usage
    -----
        agg     = SentimentAggregator()
        report  = agg.aggregate(all_articles)
        df      = agg.to_dataframe(report)
        agg.save(report)
    """

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def aggregate(self, articles: List[ArticleSentiment]) -> SentimentReport:
        """
        Group articles by (ticker, date) and build a DailySentimentIndex
        for each group.  Also computes sentiment_momentum across days.

        Parameters
        ----------
        articles : flat list of ArticleSentiment from the scoring pipeline

        Returns
        -------
        SentimentReport containing all DailySentimentIndex objects
        """
        if not articles:
            log.warning("No articles to aggregate — returning empty report.")
            return SentimentReport(
                run_at         = datetime.now(timezone.utc),
                tickers        = [],
                total_articles = 0,
                total_days     = 0,
                indices        = [],
            )

        # Step 1: Group by (ticker, date)
        groups: Dict[Tuple[str, date], List[ArticleSentiment]] = defaultdict(list)
        for article in articles:
            day = article.published_at.date()
            groups[(article.ticker, day)].append(article)

        # Step 2: Build a DailySentimentIndex for each group
        indices: List[DailySentimentIndex] = []
        for (ticker, day), group_articles in sorted(groups.keys().__iter__() and groups.items()):
            index = DailySentimentIndex.from_articles(ticker, day, group_articles)
            indices.append(index)

        # Step 3: Compute sentiment_momentum per ticker (day-over-day delta)
        indices = self._compute_momentum(indices)

        tickers = sorted({idx.ticker for idx in indices})
        log.info(
            "Aggregation complete: %d articles → %d (ticker, day) indices across %s",
            len(articles), len(indices), tickers,
        )

        return SentimentReport(
            run_at         = datetime.now(timezone.utc),
            tickers        = tickers,
            total_articles = len(articles),
            total_days     = len(indices),
            indices        = indices,
        )

    def to_dataframe(self, report: SentimentReport) -> pd.DataFrame:
        """
        Flatten a SentimentReport into a tidy DataFrame with one row
        per (ticker, date).  Article-level detail is dropped here —
        use report.indices directly if you need it.

        Columns
        -------
        ticker | date | mean_score | std_score | article_count |
        bullish_count | bearish_count | neutral_count |
        bullish_ratio | bearish_ratio | escalation_rate |
        dominant_label | sentiment_momentum
        """
        rows = []
        for idx in report.indices:
            rows.append({
                "ticker":             idx.ticker,
                "date":               idx.date,
                "mean_score":         idx.mean_score,
                "std_score":          idx.std_score,
                "article_count":      idx.article_count,
                "bullish_count":      idx.bullish_count,
                "bearish_count":      idx.bearish_count,
                "neutral_count":      idx.neutral_count,
                "bullish_ratio":      idx.bullish_ratio,
                "bearish_ratio":      idx.bearish_ratio,
                "escalation_rate":    idx.escalation_rate,
                "dominant_label":     idx.dominant_label.value,
                "sentiment_momentum": idx.sentiment_momentum,
            })

        df = pd.DataFrame(rows)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values(["ticker", "date"]).reset_index(drop=True)

        return df

    def save(self, report: SentimentReport) -> str:
        """
        Persist the sentiment index as a parquet file.

        Returns
        -------
        str : path to the saved file
        """
        df   = self.to_dataframe(report)
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        path = os.path.join(PROCESSED_DIR, f"sentiment_index_{date_str}.parquet")
        df.to_parquet(path, index=False)
        log.info("Sentiment index saved to %s (%d rows)", path, len(df))
        return path

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _compute_momentum(
        self, indices: List[DailySentimentIndex]
    ) -> List[DailySentimentIndex]:
        """
        For each ticker, compute day-over-day change in mean_score.
        Modifies the DailySentimentIndex objects in place.
        """
        # Group by ticker, sort by date
        by_ticker: Dict[str, List[DailySentimentIndex]] = defaultdict(list)
        for idx in indices:
            by_ticker[idx.ticker].append(idx)

        for ticker, ticker_indices in by_ticker.items():
            ticker_indices.sort(key=lambda x: x.date)
            for i, idx in enumerate(ticker_indices):
                if i == 0:
                    idx.sentiment_momentum = None        # no prior day
                else:
                    prev = ticker_indices[i - 1]
                    idx.sentiment_momentum = round(idx.mean_score - prev.mean_score, 4)

        return indices