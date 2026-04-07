# Complete Python Import Analysis

**Generated**: 2026-04-07  
**Total Python Files**: 29  

---

## Executive Summary

### Key Findings

1. **Streamlit App Location**: `.streamlit/streamlit_app.py` (isolated from internal modules)
   - Uses REST API for integration
   - No internal module imports needed

2. **Import Pattern**: All 28 internal modules use **relative imports** from root context
   - Format: `from config.logger import get_logger`
   - Format: `from sentiment_engine.schemas import ArticleSentiment`
   - Assumes execution from project root directory

3. **Path Management**: Centralized in `config/settings.py`
   - All paths relative to `BASE_DIR` using `os.path.join()`
   - Cross-platform compatible (Windows/Unix)
   - Paths auto-created on import

4. **Critical Dependencies**:
   - **config/settings.py** → Central configuration (used by ALL modules)
   - **config/logger.py** → Logging (used by ALL modules)
   - No circular import issues detected

---

## Module Dependencies

### Core Dependencies (Lowest Layer)

```
config/settings.py
    ↓
config/logger.py
    ↓
All other modules (import from config)
```

### Package Organization

**config/** (Foundation)
- `settings.py` - Paths, constants, configuration
- `logger.py` - Centralized logging factory

**sentiment_engine/** (NLP Layer)
- `schemas.py` - Pydantic models (no imports)
- `finbert_scorer.py` - FinBERT model integration
- `claude_scorer.py` - Claude API integration
- `aggregator.py` - Score aggregation
- `pipeline.py` - Orchestrator

**data_collection/** (Data Ingestion Layer)
- `schemas.py` - Data models
- `http_client.py` - HTTP wrapper
- `news/newsapi_fetcher.py` - News API client
- `prices/yfinance_fetcher.py` - Price data client
- `pipeline.py` - Orchestrator

**feature_engineering/** (Feature Layer)
- `sentiment_features.py` - Sentiment-derived features
- `momentum_features.py` - Price momentum
- `volatility_features.py` - Volatility measures
- `pipeline.py` - Orchestrator

**analysis/** (Analysis Layer)
- `correlation.py` - Correlation analysis
- `regression.py` - OLS regression
- `granger.py` - Granger causality tests
- `api_router.py` - FastAPI endpoints
- `pipeline.py` - Orchestrator

**models/** (ML Layer)
- `preparation.py` - Data prep & scaling
- `predictors.py` - Model definitions (XGBoost, LSTM, LogReg)
- `evaluation.py` - Metrics & backtesting
- `pipeline.py` - Training orchestrator

**pipeline/** (Integration)
- `api_router.py` - Unified FastAPI routes

---

## Import Patterns

### Pattern 1: Config Imports
```python
from config.logger import get_logger
from config.settings import PROCESSED_DIR, TICKERS
```
Used by: ALL modules

### Pattern 2: Cross-Package Imports
```python
from sentiment_engine.schemas import ArticleSentiment
from feature_engineering.momentum_features import MomentumFeatureBuilder
```
Used by: Pipeline and router modules

### Pattern 3: Lazy Imports
```python
# Inside class methods, not at module level
from transformers import pipeline as hf_pipeline
import tensorflow as tf
```
Used by: Heavy ML modules (to defer load)

---

## Data Flow & Dependencies

```
FastAPI (main.py)
    ├─→ pipeline/api_router.py
    │   ├─→ data_collection/pipeline.py
    │   │   ├─→ news/newsapi_fetcher.py
    │   │   └─→ prices/yfinance_fetcher.py
    │   │
    │   ├─→ sentiment_engine/pipeline.py
    │   │   ├─→ finbert_scorer.py
    │   │   ├─→ claude_scorer.py
    │   │   └─→ aggregator.py
    │   │
    │   ├─→ feature_engineering/pipeline.py
    │   │   ├─→ sentiment_features.py
    │   │   ├─→ momentum_features.py
    │   │   └─→ volatility_features.py
    │   │
    │   └─→ models/pipeline.py
    │       ├─→ preparation.py
    │       ├─→ predictors.py
    │       └─→ evaluation.py
    │
    └─→ analysis/api_router.py
        ├─→ correlation.py
        ├─→ regression.py
        ├─→ granger.py
        └─→ Local data files (JSON parquet)
```

---

## Import Verification Results

### All 28 Modules: VERIFIED ✓

| Category | Files | Status |
|----------|-------|--------|
| config | 2 | ✓ OK |
| sentiment_engine | 5 | ✓ OK |
| analysis | 5 | ✓ OK |
| feature_engineering | 4 | ✓ OK |
| data_collection | 5 | ✓ OK |
| models | 4 | ✓ OK |
| pipeline | 1 | ✓ OK |
| root (main.py) | 1 | ✓ OK |
| **Total** | **28** | **✓ OK** |

Special cases:
- `.streamlit/streamlit_app.py` - Uses REST API, isolated (no changes needed)

---

## Critical Path & Bottlenecks

### Execution Entry Points

1. **CLI**: `python main.py` (FastAPI server)
   - Requires: config/ initialized correctly
   - Starts: All routers

2. **Dashboard**: `streamlit run .streamlit/streamlit_app.py` (Frontend)
   - Requires: Running FastAPI server
   - HTTP calls only to `/analysis/*` endpoints

3. **Streaming**: `python stream_prices.py` (Background worker)
   - Requires: yfinance available
   - No internal module imports

---

## Potential Import Issues Fixed

✅ **No __init__.py files** → FIXED: Created 10 `__init__.py` files  
✅ **Fragile path logic** → FIXED: Updated `config/settings.py` to use pathlib  
✅ **Hardcoded paths** → FIXED: Updated `notebooks/generate_mock_data.py`  
✅ **No circular imports** → No issues detected  

---

## Execution Requirements

**Must be run from project root:**
```bash
cd /path/to/FinSentiment-Lab
python main.py              # ✓ Works
streamlit run .streamlit/streamlit_app.py  # ✓ Works
python stream_prices.py     # ✓ Works
```

**Will NOT work from subdirectories:**
```bash
cd analysis/
python ../main.py           # ✗ Fails (relative imports broken)
```

---

## Best Practices Observed

✅ Centralized configuration in `config/settings.py`  
✅ Consistent logging via `config/logger.py`  
✅ Pydantic models for type safety  
✅ Lazy imports for heavy dependencies  
✅ Clear package organization  
✅ Cross-platform path handling  

---

## Recommendations

1. **Running the project**: Always from root directory
2. **Adding new modules**: Follow existing import patterns
3. **Modifying paths**: Update `config/settings.py`, not hardcoded values
4. **Testing**: Run tests from root with relative imports

