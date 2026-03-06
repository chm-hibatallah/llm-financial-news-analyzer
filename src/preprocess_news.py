"""
Preprocessing script for financial news data.
Extracts features, computes quality metrics, and flags articles ready for analysis.
Must match the EDA notebook's output format.
"""

import os
import re
import numpy as np
import pandas as pd
from datetime import datetime


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

INPUT_FILE  = r"C:\Users\dell\Documents\llm-financial-news-analyzer\data\raw\raw_news_data.csv"
OUTPUT_FILE = r"C:\Users\dell\Documents\llm-financial-news-analyzer\data\processed\processed_financial_news.csv"

REQUIRED_COLUMNS = ["title", "published", "source", "content", "description"]

FINANCIAL_TERMS = {
    # Instruments
    "stock", "stocks", "share", "shares", "equity", "equities",
    "bond", "bonds", "yield", "yields", "etf", "etfs", "fund", "funds",
    "dividend", "dividends", "commodity", "commodities",
    # Metrics
    "earnings", "revenue", "profit", "profits", "loss", "losses",
    "eps", "earnings per share", "book value", "market cap",
    "market capitalization", "p/e", "price-to-earnings", "pe ratio",
    "valuation", "valuations", "volume", "volumes", "beta", "alpha",
    # Market participants
    "investor", "investors", "investment", "investments",
    "trader", "traders", "trading",
    "private equity", "venture capital", "hedge fund", "hedge funds",
    "mutual fund", "mutual funds",
    # Market conditions
    "bull", "bulls", "bear", "bears", "bullish", "bearish",
    "volatility", "volatile", "rally", "rallies",
    "crash", "crashes", "correction", "corrections",
    # Indices & institutions
    "dow", "nasdaq", "s&p", "spx", "federal reserve", "fed",
    # Macro
    "inflation", "deflation", "gdp", "economy", "economic",
    "recession", "expansion", "interest rate", "interest rates",
    "rate hike", "rate cut", "monetary policy", "fiscal policy",
    "liquidity", "solvency",
    # Banking & credit
    "bank", "banks", "banking", "finance", "financial", "financing",
    "credit", "debt", "loan", "loans", "mortgage", "mortgages",
    # FX & crypto
    "forex", "currency", "currencies", "dollar", "euro", "pound", "yen",
    "crypto", "cryptocurrency", "bitcoin", "ethereum", "blockchain",
    # Metals & agriculture
    "oil", "gold", "silver", "copper", "wheat", "corn", "soy",
    # Corporate events
    "ipo", "merger", "mergers", "acquisition", "acquisitions",
    "takeover", "takeovers", "buyout", "buyouts",
    # Financial statements
    "portfolio", "portfolios", "asset", "assets",
    "liability", "liabilities", "balance sheet",
    "income statement", "cash flow",
}


# ---------------------------------------------------------------------------
# Feature-extraction helpers
# ---------------------------------------------------------------------------

def extract_money_amounts(text: str) -> int:
    """Count dollar-amount mentions (e.g. '$3.2 billion', '5 million dollars')."""
    if not isinstance(text, str):
        return 0
    pattern = (
        r"\$\s*\d+(?:\.\d+)?(?:\s*(?:million|billion|trillion|M|B|T|k|K))?"
        r"|\d+\s*(?:million|billion|trillion)\s*dollars"
    )
    return len(re.findall(pattern, text, re.IGNORECASE))


def extract_percentages(text: str) -> int:
    """Count percentage mentions (e.g. '3.5%', '12 percent')."""
    if not isinstance(text, str):
        return 0
    pattern = r"\d+(?:\.\d+)?\s*%|\d+(?:\.\d+)?\s*percent"
    return len(re.findall(pattern, text, re.IGNORECASE))


def count_financial_terms(text: str) -> int:
    """Count total occurrences of all financial-terms in the text."""
    if not isinstance(text, str):
        return 0
    text_lower = text.lower()
    return sum(text_lower.count(term) for term in FINANCIAL_TERMS)


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def calculate_length_score(word_count: int) -> float:
    """
    Score based on article length (optimal range: 50–500 words).
      < 10  words  → 0.0
      10–49 words  → linear ramp to 0.7
      50–500 words → 1.0
      > 500 words  → decays toward 0
    """
    if word_count < 10:
        return 0.0
    if word_count < 50:
        return word_count / 50 * 0.7
    if word_count <= 500:
        return 1.0
    return max(0.0, 1.0 - (word_count - 500) / 1500)


def calculate_financial_score(
    word_count: int,
    financial_term_count: int,
    money_mentions: int,
    percentage_mentions: int,
) -> float:
    """
    Score based on financial-content density (0–1).
    Combines term density, money mentions, and percentage mentions.
    """
    if word_count == 0:
        return 0.0

    term_density   = min(financial_term_count / max(word_count / 50, 1), 3) / 3
    money_score    = min(money_mentions, 3)      / 3
    percent_score  = min(percentage_mentions, 3) / 3

    raw = term_density * 0.50 + money_score * 0.25 + percent_score * 0.25
    return min(raw, 1.0)


def calculate_quality_score(row: pd.Series) -> float:
    """
    Overall quality score (0–1):
      40 % → length score
      60 % → financial-content score
    """
    length_score    = calculate_length_score(row.get("word_count", 0))
    financial_score = calculate_financial_score(
        word_count           = row.get("word_count", 0),
        financial_term_count = row.get("financial_term_count", 0),
        money_mentions       = row.get("money_mentions", 0),
        percentage_mentions  = row.get("percentage_mentions", 0),
    )
    return round(length_score * 0.4 + financial_score * 0.6, 6)


def is_ready_for_analysis(row: pd.Series) -> bool:
    """
    An article is ready for sentiment analysis when:
      - word count ≥ 20, AND
      - it contains financial content OR has a quality score > 0.3
    """
    return bool(
        row.get("word_count", 0) >= 20
        and (
            row.get("has_financial_content", False)
            or row.get("data_quality_score", 0) > 0.3
        )
    )


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def build_cleaned_text(row: pd.Series) -> str:
    """Concatenate title, description, and content into one clean string."""
    parts = [row.get("title", ""), row.get("description", ""), row.get("content", "")]
    return " ".join(str(p) for p in parts if pd.notna(p))


def preprocess_news_data(input_path: str, output_path: str) -> pd.DataFrame:
    """
    Full preprocessing pipeline:
      1. Load raw CSV
      2. Ensure required columns exist
      3. Build cleaned text
      4. Compute text metrics
      5. Extract financial features
      6. Parse temporal features
      7. Score quality & flag readiness
      8. Save processed CSV
    """

    # ── 1. Load ──────────────────────────────────────────────────────────────
    print(f"Loading data from: {input_path}")
    df = pd.read_csv(input_path)
    print(f"  {len(df):,} articles loaded.\n")

    # ── 2. Ensure required columns ───────────────────────────────────────────
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    # ── 3. Cleaned text ──────────────────────────────────────────────────────
    print("Step 1/5 — Building cleaned text …")
    df["cleaned_text"] = df.apply(build_cleaned_text, axis=1)

    # ── 4. Text metrics ──────────────────────────────────────────────────────
    print("Step 2/5 — Computing text metrics …")
    df["word_count"]     = df["cleaned_text"].str.split().str.len()
    df["sentence_count"] = df["cleaned_text"].apply(
        lambda x: len(re.findall(r"[.!?]+", x))
    )
    df["avg_word_length"] = df["cleaned_text"].apply(
        lambda x: round(np.mean([len(w) for w in x.split()]), 2) if x.split() else 0
    )

    # ── 5. Financial features ────────────────────────────────────────────────
    print("Step 3/5 — Extracting financial features …")
    df["financial_term_count"] = df["cleaned_text"].apply(count_financial_terms)
    df["money_mentions"]       = df["cleaned_text"].apply(extract_money_amounts)
    df["percentage_mentions"]  = df["cleaned_text"].apply(extract_percentages)
    df["has_financial_content"]= df["financial_term_count"] > 0

    # ── 6. Temporal features ─────────────────────────────────────────────────
    print("Step 4/5 — Parsing temporal features …")
    df["published"]     = pd.to_datetime(df["published"], errors="coerce")
    df["year"]          = df["published"].dt.year
    df["month"]         = df["published"].dt.month
    df["day"]           = df["published"].dt.day
    df["day_of_week"]   = df["published"].dt.day_name()
    df["hour"]          = df["published"].dt.hour
    df["processing_date"] = datetime.now().strftime("%Y-%m-%d")

    # ── 7. Quality scoring ───────────────────────────────────────────────────
    print("Step 5/5 — Scoring quality & flagging readiness …")
    df["data_quality_score"] = df.apply(calculate_quality_score, axis=1)
    df["ready_for_analysis"] = df.apply(is_ready_for_analysis, axis=1)

    # Metadata
    df["original_file"] = os.path.basename(input_path)

    # ── 8. Save ──────────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"\nSaved processed data to: {output_path}")

    # Summary
    ready_count = df["ready_for_analysis"].sum()
    print("\n── Summary ─────────────────────────────────────")
    print(f"  Total articles processed : {len(df):,}")
    print(f"  Ready for analysis       : {ready_count:,}  ({ready_count / len(df) * 100:.1f}%)")
    print(f"  Average quality score    : {df['data_quality_score'].mean():.3f}")
    print("────────────────────────────────────────────────\n")

    return df


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if os.path.exists(INPUT_FILE):
        preprocess_news_data(INPUT_FILE, OUTPUT_FILE)
    else:
        print(f"Input file not found: {INPUT_FILE}")
        print("Please ensure raw data exists at the specified path.")