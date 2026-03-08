"""
Pydantic models for every data structure produced by the sentiment engine.

Hierarchy
---------
  ArticleSentiment          ← one article scored by FinBERT (and optionally Claude)
      └─ used to build ─►
  DailySentimentIndex       ← one (ticker, date) aggregate
      └─ collected into ─►
  SentimentReport           ← full run output across all tickers / dates
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SentimentLabel(str, Enum):
    BEARISH  = "bearish"
    NEUTRAL  = "neutral"
    BULLISH  = "bullish"


class ScoringModel(str, Enum):
    FINBERT = "finbert"
    CLAUDE  = "claude"


# ---------------------------------------------------------------------------
# Article-level
# ---------------------------------------------------------------------------

class ArticleSentiment(BaseModel):
    """
    Sentiment scores for a single news article.

    score       : float in [-1, +1]
                  -1 = maximally bearish, 0 = neutral, +1 = maximally bullish
    confidence  : float in [0, 1]
                  FinBERT softmax probability of the winning class.
                  Claude calls return 1.0 when used as escalation scorer.
    label       : bearish / neutral / bullish derived from score thresholds
    model_used  : which model produced this score
    escalated   : True when FinBERT confidence was low and Claude was called
    """

    ticker:       str
    url:          str
    title:        str
    published_at: datetime
    score:        float = Field(..., ge=-1.0, le=1.0)
    confidence:   float = Field(..., ge=0.0,  le=1.0)
    label:        SentimentLabel
    model_used:   ScoringModel
    escalated:    bool = False

    # Raw model outputs kept for debugging / auditing
    finbert_scores: Optional[dict] = None   # {"positive": .8, "negative": .1, "neutral": .1}
    claude_reason:  Optional[str]  = None   # short explanation when Claude was used

    @field_validator("score")
    @classmethod
    def round_score(cls, v: float) -> float:
        return round(v, 4)

    @field_validator("confidence")
    @classmethod
    def round_confidence(cls, v: float) -> float:
        return round(v, 4)

    @classmethod
    def label_from_score(cls, score: float) -> SentimentLabel:
        """Derive label from numeric score using standard thresholds."""
        if score >= 0.15:
            return SentimentLabel.BULLISH
        if score <= -0.15:
            return SentimentLabel.BEARISH
        return SentimentLabel.NEUTRAL


# ---------------------------------------------------------------------------
# Daily aggregate
# ---------------------------------------------------------------------------

class DailySentimentIndex(BaseModel):
    """
    Aggregated sentiment for one ticker on one trading day.

    mean_score          : volume-weighted average of article scores
    article_count       : total articles scored that day
    bullish_count       : articles labelled bullish
    bearish_count       : articles labelled bearish
    neutral_count       : articles labelled neutral
    bullish_ratio       : bullish_count / article_count
    bearish_ratio       : bearish_count / article_count
    sentiment_momentum  : mean_score(day_t) - mean_score(day_t-1)  [filled downstream]
    escalation_rate     : fraction of articles that needed Claude escalation
    dominant_label      : label with the most articles that day
    """

    ticker:              str
    date:                date
    mean_score:          float
    std_score:           float                        # dispersion of opinions
    article_count:       int
    bullish_count:       int
    bearish_count:       int
    neutral_count:       int
    bullish_ratio:       float
    bearish_ratio:       float
    escalation_rate:     float
    dominant_label:      SentimentLabel
    sentiment_momentum:  Optional[float] = None       # filled by feature engineering
    articles:            List[ArticleSentiment] = Field(default_factory=list)

    @classmethod
    def from_articles(
        cls,
        ticker:   str,
        day:      date,
        articles: List[ArticleSentiment],
    ) -> "DailySentimentIndex":
        """
        Aggregate a list of ArticleSentiment objects into a daily index.
        Called by the Aggregator after all articles for a day are scored.
        """
        if not articles:
            return cls(
                ticker           = ticker,
                date             = day,
                mean_score       = 0.0,
                std_score        = 0.0,
                article_count    = 0,
                bullish_count    = 0,
                bearish_count    = 0,
                neutral_count    = 0,
                bullish_ratio    = 0.0,
                bearish_ratio    = 0.0,
                escalation_rate  = 0.0,
                dominant_label   = SentimentLabel.NEUTRAL,
                articles         = [],
            )

        scores     = [a.score for a in articles]
        mean_score = sum(scores) / len(scores)
        variance   = sum((s - mean_score) ** 2 for s in scores) / len(scores)
        std_score  = variance ** 0.5

        bullish = [a for a in articles if a.label == SentimentLabel.BULLISH]
        bearish = [a for a in articles if a.label == SentimentLabel.BEARISH]
        neutral = [a for a in articles if a.label == SentimentLabel.NEUTRAL]

        n = len(articles)
        counts = {
            SentimentLabel.BULLISH: len(bullish),
            SentimentLabel.BEARISH: len(bearish),
            SentimentLabel.NEUTRAL: len(neutral),
        }
        dominant_label = max(counts, key=lambda k: counts[k])
        escalation_rate = sum(1 for a in articles if a.escalated) / n

        return cls(
            ticker          = ticker,
            date            = day,
            mean_score      = round(mean_score, 4),
            std_score       = round(std_score, 4),
            article_count   = n,
            bullish_count   = len(bullish),
            bearish_count   = len(bearish),
            neutral_count   = len(neutral),
            bullish_ratio   = round(len(bullish) / n, 4),
            bearish_ratio   = round(len(bearish) / n, 4),
            escalation_rate = round(escalation_rate, 4),
            dominant_label  = dominant_label,
            articles        = articles,
        )


# ---------------------------------------------------------------------------
# Full report
# ---------------------------------------------------------------------------

class SentimentReport(BaseModel):
    """Output of one full sentiment engine run."""

    run_at:        datetime
    tickers:       List[str]
    total_articles: int
    total_days:    int
    indices:       List[DailySentimentIndex] = Field(default_factory=list)

    def for_ticker(self, ticker: str) -> List[DailySentimentIndex]:
        return [idx for idx in self.indices if idx.ticker == ticker]