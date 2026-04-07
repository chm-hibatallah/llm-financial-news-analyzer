# System Architecture

Complete system design and data flow documentation for FinSentiment Lab.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────┐
│          USER INTERFACE (Browser)                   │
│  http://localhost:8502 (Streamlit Dashboard)       │
└────────────────────┬────────────────────────────────┘
                     │ HTTP REST Calls
                     ↓
┌─────────────────────────────────────────────────────┐
│        BACKEND API (FastAPI Server)                 │
│  http://localhost:8000                             │
│  ├─ /analysis/sentiment/{ticker}                   │
│  ├─ /analysis/leaderboard                          │
│  ├─ /analysis/features                             │
│  ├─ /analysis/granger                              │
│  ├─ /analysis/correlation                          │
│  └─ /collection/... (data collection routes)       │
└────────────────────┬────────────────────────────────┘
                     │
          ┌──────────┴──────────┐
          ↓                     ↓
    ┌──────────────────┐  ┌──────────────────┐
    │   Data Pipeline  │  │  Stream Cache    │
    │  (Background)    │  │  (1-min prices)  │
    └────────┬─────────┘  └────────┬─────────┘
             │                     │
          ┌──┴─────────────────────┴──┐
          ↓                           ↓
    ┌──────────────────┐      ┌──────────────────┐
    │  Analysis Cache  │      │  Price Stream    │
    │  (Processed)     │      │  (Stream prices) │
    └────────┬─────────┘      └────────┬─────────┘
             │                         │
             └─────────────────────────┘
                     ↓
            ┌────────────────────┐
            │  Data Files (JSON) │
            │  on Disk           │
            └────────────────────┘
```

---

## Component Layers

### Layer 1: Data Ingestion
**files**: `data_collection/`

```
NewsAPI                    Yahoo Finance
    │ articles                  │ prices (OHLCV)
    └─────→ NewsAPIFetcher      └─→ YFinanceFetcher
               │                        │
               └────────→ data/raw_news │
                          ..           │
                                      data/raw_prices
```

### Layer 2: Sentiment Analysis
**files**: `sentiment_engine/`

```
Raw Articles (JSON)
    │
    ├─→ FinBERTScorer (HuggingFace transformer)
    │   └─→ score: -1.0 to +1.0
    │
    ├─→ ClaudeScorer (Anthropic API)
    │   └─→ detailed analysis
    │
    └─→ SentimentAggregator
        └─→ ensemble score
            └─→ label: bullish|neutral|bearish
                └─→ data/processed/sentiment_*.parquet
```

### Layer 3: Feature Engineering
**files**: `feature_engineering/`

```
Sentiment Scores + Price Data
    │
    ├─→ SentimentFeatureBuilder
    │   ├─ sentiment_zscore
    │   ├─ sentiment_roll_7d
    │   └─ bullish_ratio
    │
    ├─→ MomentumFeatureBuilder
    │   ├─ daily_return
    │   ├─ log_return
    │   └─ SMA/EMA
    │
    └─→ VolatilityFeatureBuilder
        ├─ realized_vol_5d
        ├─ ATR
        └─ RSI
            └─→ data/processed/features_*.parquet
```

### Layer 4: Modeling
**files**: `models/`

```
Engineered Features
    │
    ├─→ DataPreparation (scaling, train/test split)
    │
    ├─→ Predictors
    │   ├─ XGBoostClassifier (63.8% AUC)
    │   ├─ LSTMModel
    │   └─ LogisticRegression
    │
    └─→ Evaluator (AUC, F1, Sharpe, returns)
        └─→ data/processed/model_findings_*.json
```

### Layer 5: Statistical Analysis
**files**: `analysis/`

```
Processed Features
    │
    ├─→ CorrelationAnalyzer (Pearson)
    │   └─→ correlation matrix
    │
    ├─→ RegressionAnalyzer (OLS)
    │   └─→ sentiment→return coefficients
    │
    ├─→ GrangerAnalyzer (causality tests)
    │   └─→ proves sentiment CAUSES price moves
    │
    └─→ APIRouter (REST endpoints)
        └─→ FastAPI serves results
```

### Layer 6: Real-Time Streaming
**files**: `stream_prices.py`

```
Yahoo Finance (1-minute intervals)
    │
    └─→ YFinanceFetcher
        └─→ JSON cache (OHLCV)
            └─→ data/cache/intraday_prices.json
                └─→ Streamlit dashboard reads
                    every 5 seconds
```

### Layer 7: Frontend Dashboard
**files**: `.streamlit/streamlit_app.py`

```
Streamlit App
    │
    ├─→ View 1: Sentiment Timeline
    │   │ Data: API + sentiment cache
    │   └─→ Displays: sentiment bars + price line
    │
    ├─→ View 2: Price Overlay (Live)
    │   │ Data: API + streaming cache
    │   └─→ Displays: dual-axis price/sentiment
    │
    ├─→ View 3: Intraday Stream
    │   │ Data: streaming cache only
    │   └─→ Displays: 1-min candles + sentiment
    │
    ├─→ View 4: Features
    │   │ Data: API /analysis/features
    │   └─→ Displays: feature importance
    │
    ├─→ View 5: Correlation
    │   │ Data: API /analysis/correlation
    │   └─→ Displays: heatmap
    │
    ├─→ View 6: Granger Causality
    │   │ Data: API /analysis/granger
    │   └─→ Displays: significant relationships
    │
    └─→ View 7: Leaderboard
        │ Data: API /analysis/leaderboard
        └─→ Displays: model rankings
```

---

## Data Flow Example

### End-to-End Journey

```
1. DATA COLLECTION (Morning 9:30 AM)
   NewsAPI: "Tesla sales beat expectations"
   yfinance: TSLA = $215.50
   
2. SENTIMENT ANALYSIS
   FinBERT: 0.82 (bullish)
   Claude:  "Positive earnings news"
   Ensemble: 0.78 → BULLISH label
   
3. FEATURE ENGINEERING
   sentiment_zscore: +1.8
   sentiment_roll_7d: +0.58
   returns_5d: +0.023
   vol_ratio_5_21: 1.2
   
4. ML MODELING
   XGBoost prediction: 0.72
   -> 72% probability of UP move
   
5. STATISTICAL TESTS
   Granger: sentiment (t-2) → return (t)
   p-value: 0.031 (SIGNIFICANT)
   
6. RESULTS CACHED
   {
     "ticker": "TSLA",
     "date": "2026-04-07",
     "sentiment_score": 0.78,
     "model_prediction": 0.72,
     "granger_pvalue": 0.031
   }
   
7. DASHBOARD DISPLAY
   ✓ Chart: Green sentiment bar (0.78)
   ✓ Price overlay: $215.50 with trend
   ✓ Metrics: "18.3% return potential"
   ✓ Alert: "Strong sentiment correlation"
```

---

## File Organization

```
FinSentiment-Lab/
│
├── main.py  ────────────────────────→ FastAPI entry point
│
├── stream_prices.py ─────────────────→ Real-time price updater
│
├── config/
│   ├── settings.py ─────────────────→ Central config + paths
│   └── logger.py ───────────────────→ Logging factory
│
├── data_collection/
│   ├── pipeline.py  ────────────────→ Orchestrator
│   ├── http_client.py ──────────────→ Base HTTP wrapper
│   ├── news/newsapi_fetcher.py ─────→ News source
│   └── prices/yfinance_fetcher.py ──→ Price source
│
├── sentiment_engine/
│   ├── pipeline.py  ────────────────→ Orchestrator
│   ├── finbert_scorer.py ───────────→ HF transformer
│   ├── claude_scorer.py ────────────→ Anthropic API
│   ├── aggregator.py ───────────────→ Ensemble
│   └── schemas.py  ─────────────────→ Data models
│
├── feature_engineering/
│   ├── pipeline.py  ────────────────→ Orchestrator
│   ├── sentiment_features.py ───────→ Sentiment features
│   ├── momentum_features.py ────────→ Price momentum
│   └── volatility_features.py ──────→ Volatility
│
├── models/
│   ├── pipeline.py  ────────────────→ Orchestrator
│   ├── predictors.py ───────────────→ ML models
│   ├── preparation.py ──────────────→ Data prep
│   └── evaluation.py ───────────────→ Metrics
│
├── analysis/
│   ├── pipeline.py  ────────────────→ Orchestrator
│   ├── correlation.py ──────────────→ Correlation
│   ├── regression.py ───────────────→ Regression
│   ├── granger.py  ─────────────────→ Granger tests
│   └── api_router.py ───────────────→ REST endpoints
│
├── pipeline/
│   └── api_router.py ───────────────→ Unified API routes
│
├── .streamlit/
│   └── streamlit_app.py ────────────→ Dashboard (7 views)
│
├── data/
│   ├── raw_news/ ────────────────────→ Raw articles (JSON)
│   ├── raw_prices/ ──────────────────→ Raw OHLCV (JSON)
│   ├── cache/ ───────────────────────→ Streaming prices
│   └── processed/ ───────────────────→ Analyzed data
│
└── README.md ────────────────────────→ Main documentation
```

---

## Data Models (Pydantic)

### News Domain
```python
Article
├── headline: str
├── summary: str
├── source: str
├── published_date: datetime
└── url: str

ArticleSentiment
├── article: Article
├── finbert_score: float (-1 to +1)
├── claude_score: float (-1 to +1)
├── ensemble_score: float (-1 to +1)
└── label: Literal["bullish", "neutral", "bearish"]

DailySentimentIndex
├── ticker: str
├── date: date
├── articles: List[ArticleSentiment]
├── mean_score: float
├── label: str
└── coverage: int (# articles)
```

### Price Domain
```python
DailyPrice
├── ticker: str
├── date: date
├── open: float
├── high: float
├── low: float
├── close: float
├── volume: int
├── daily_return: float
└── log_return: float

PriceHistory
├── ticker: str
├── bars: List[DailyPrice]
└── metadata: dict

IntradayCandle
├── timestamp: datetime
├── open: float
├── high: float
├── low: float
├── close: float
└── volume: int
```

### Analysis Domain
```python
CorrelationResult
├── features: List[str]
├── correlation_matrix: np.ndarray
└── p_values: np.ndarray

GrangerResult
├── cause: str
├── effect: str
├── lag: int
├── p_value: float
└── significant: bool

ModelPerformance
├── ticker: str
├── model: str
├── auc: float
├── accuracy: float
├── f1_score: float
├── sharpe_ratio: float
└── cumulative_return: float
```

---

## Execution Flow

### FastAPI Startup
```
1. main.py
2. ├─ config/settings.py (initialize paths)
3. ├─ config/logger.py (setup logging)
4. ├─ Include pipeline/api_router.py
5. ├─ Include analysis/api_router.py
6. └─ Start uvicorn server on :8000
```

### Streamlit Startup
```
1. .streamlit/streamlit_app.py
2. ├─ Load cache TTL strategy
3. ├─ Define views (7 functions)
4. ├─ Setup sidebar navigation
5. ├─ Start app on :8502
6. └─ Begin polling API every 5s
```

### Stream Process
```
1. stream_prices.py
2. ├─ Initialize YFinanceFetcher
3. ├─ Fetch 1-min candles
4. ├─ Format JSON
5. ├─ Write to data/cache/intraday_prices.json
6. ├─ Pause 60 seconds
7. └─ Repeat until Ctrl+C
```

---

## Performance Characteristics

| Component | Latency | Throughput | Cache |
|-----------|---------|-----------|-------|
| FastAPI endpoint | <500ms | Unlimited | 300s |
| Data collection | Variable (1-10s) | Batch | On demand |
| Feature engineering | <200ms | Unlimited | In-memory |
| Model prediction | <500ms | Unlimited | 300s |
| Streamlit dashboard | <2s | Single user | Session |
| Stream prices | 60s interval | 1 update/min | File-based |

---

Last Updated: April 7, 2026
