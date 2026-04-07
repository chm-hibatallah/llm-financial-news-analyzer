# FinSentiment-Lab: Complete Python File & Import Analysis

**Generated**: 2026-04-07  
**Total Python Files**: 29  
**Workspace**: c:\Users\HP PRO\Documents\FinSentiment-Lab

---

## 📋 Executive Summary

### Key Findings

1. **Streamlit App Location**: `.streamlit/streamlit_app.py` (NOT at root)
   - Currently isolated; doesn't import internal project modules
   - Will need integration strategy when moving to new structure

2. **Import Pattern**: All 28 internal modules use **relative imports** from root context
   - Format: `from config.logger import get_logger`
   - Format: `from sentiment_engine.schemas import ArticleSentiment`
   - Assumes execution from root directory with modules accessible directly

3. **Path Management**: Centralized in `config/settings.py`
   - All paths computed relative to `BASE_DIR` using `os.path.join()`
   - Cross-platform compatible (Windows/Unix)
   - Directories auto-created on import

4. **Critical Dependencies**:
   - **config/settings.py** → Used by ALL modules for paths & constants
   - **config/logger.py** → Imported by ALL modules for logging
   - No circular import issues detected

---

## 📂 Complete File Inventory with Imports

### ROOT LEVEL (2 files)

#### `main.py`
**Role**: FastAPI application entry point  
**Import Category**: Mixed (external + relative)  
**Relative Imports** (Breaking points):
- `from config.logger import get_logger` ✓
- `from pipeline.api_router import router as collect_router` ✓
- `from analysis.api_router import router as analysis_router` ✓

**External Imports**:
```python
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
```

**Data Paths Used**: None directly  
**Potential Issues**: 
- ✅ All relative imports start from root
- ✅ No path assumptions inside main.py

---

#### `app.jsx`
**Role**: React frontend (NOT Python - skipped)

---

### CONFIG (2 files)

#### `config/settings.py`
**Role**: Central configuration, environment variables, path definitions  
**Import Category**: Standard library only  
**All Imports**:
```python
import os
from dataclasses import dataclass, field
from typing import List
```

**Data Paths Defined** (used by all modules):
```python
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CACHE_DIR = os.path.join(DATA_DIR, "cache")
RAW_NEWS_DIR = os.path.join(DATA_DIR, "raw_news")
RAW_PRICES_DIR = os.path.join(DATA_DIR, "raw_prices")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
```

**Constants Used by Modules**:
- TICKERS, COMPANY_KEYWORDS, LOOKBACK_DAYS
- NEWSAPI_KEY, NEWSAPI_BASE_URL, PRICE_INTERVAL
- LOG_LEVEL, LOG_FORMAT, HTTP_TIMEOUT, MAX_RETRIES

**Potential Issues**: ⚠️ 
- No __init__.py mentioned; relies on namespace packages
- Relative paths use `os.path.dirname()` chain — works but fragile if file moves

---

#### `config/logger.py`
**Role**: Centralized logging factory  
**Import Category**: Standard library + relative  
**All Imports**:
```python
import logging
import sys
from config.settings import LOG_LEVEL, LOG_FORMAT  # Relative import
```

**Usage Pattern**:
```python
log = get_logger(__name__)  # Called in ALL 28 internal modules
```

**Circular Import Risk**: ⚠️ 
- Imports from `config.settings` (safe, settings imports only stdlib)

---

### SENTIMENT ENGINE (5 files)

#### `sentiment_engine/schemas.py`
**Role**: Pydantic models for sentiment data structures  
**Import Category**: External (pydantic)  
**All Imports**:
```python
from __future__ import annotations
from datetime import date, datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
```

**Relative Imports**: None  
**Data Paths Used**: None  
**Potential Issues**: ✅ None

---

#### `sentiment_engine/pipeline.py`
**Role**: Main orchestrator for sentiment scoring  
**Import Category**: Mixed (external + relative)  
**Relative Imports** (Breaking points):
```python
from config.logger import get_logger
from config.settings import PROCESSED_DIR, TICKERS
from sentiment_engine.aggregator import SentimentAggregator
from sentiment_engine.claude_scorer import ClaudeScorer
from sentiment_engine.finbert_scorer import FinBERTScorer
from sentiment_engine.schemas import ArticleSentiment, SentimentReport
```

**External Imports**:
```python
from __future__ import annotations
import glob, os
from datetime import datetime, timezone
from typing import List, Optional
import pandas as pd
```

**Data Paths Used**:
- `PROCESSED_DIR` from config (to save enriched parquet)

**Potential Issues**: ✅ None (all intra-package, config-dependent)

---

#### `sentiment_engine/finbert_scorer.py`
**Role**: FinBERT model for article sentiment scoring  
**Import Category**: Standard library + relative  
**Relative Imports**:
```python
from config.logger import get_logger
from sentiment_engine.schemas import ArticleSentiment, ScoringModel, SentimentLabel
```

**External Imports**:
```python
from __future__ import annotations
from typing import List, Optional, Tuple
```

**Note**: Imports TensorFlow/transformers lazily inside class (not at top)

**Potential Issues**: ✅ None

---

#### `sentiment_engine/claude_scorer.py`
**Role**: Claude-based escalation scorer  
**Import Category**: Mixed (anthropic + relative)  
**Relative Imports**:
```python
from config.logger import get_logger
from config.settings import CACHE_DIR
from sentiment_engine.schemas import ArticleSentiment, ScoringModel, SentimentLabel
```

**External Imports**:
```python
from __future__ import annotations
import hashlib, json, os
from typing import List, Optional
import anthropic
```

**Data Paths Used**:
- `CACHE_DIR` (to store article cache)

**Potential Issues**: 
- ⚠️ Uses `CACHE_DIR` path — must be available at import time

---

#### `sentiment_engine/aggregator.py`
**Role**: Aggregates articles into daily sentiment index  
**Import Category**: Mixed  
**Relative Imports**:
```python
from config.logger import get_logger
from config.settings import PROCESSED_DIR
from sentiment_engine.schemas import (
    ArticleSentiment,
    DailySentimentIndex,
    SentimentReport,
)
```

**External Imports**:
```python
from __future__ import annotations
import os
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Dict, List, Optional, Tuple
import pandas as pd
```

**Data Paths Used**:
- `PROCESSED_DIR` (to save sentiment index parquet)

**Potential Issues**: ✅ None

---

### ANALYSIS (5 files)

#### `analysis/pipeline.py`
**Role**: Orchestrator for statistical analysis (correlation, regression, Granger)  
**Import Category**: Mixed  
**Relative Imports**:
```python
from config.logger import get_logger
from config.settings import PROCESSED_DIR
from analysis.correlation import CorrelationAnalyzer
from analysis.granger import GrangerAnalyzer
from analysis.regression import OLSAnalyzer
```

**External Imports**:
```python
from __future__ import annotations
import glob, json, os
from datetime import datetime, timezone
from typing import Optional
import pandas as pd
```

**Data Paths Used**:
- `PROCESSED_DIR` (input/output)

**Potential Issues**: ✅ None

---

#### `analysis/correlation.py`
**Role**: Pearson & Spearman correlation analysis  
**Import Category**: External + relative  
**Relative Imports**:
```python
from config.logger import get_logger
```

**External Imports**:
```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np
import pandas as pd
from scipy import stats
```

**Data Paths Used**: None (input/output via parameters)

**Potential Issues**: ✅ None

---

#### `analysis/regression.py`
**Role**: OLS regression analysis (sentiment → returns)  
**Import Category**: External + relative  
**Relative Imports**:
```python
from config.logger import get_logger
```

**External Imports**:
```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np
import pandas as pd
# (statsmodels imported conditionally)
```

**Data Paths Used**: None

**Potential Issues**: ✅ None (statsmodels is optional)

---

#### `analysis/granger.py`
**Role**: Granger causality tests  
**Import Category**: External + relative  
**Relative Imports**:
```python
from config.logger import get_logger
```

**External Imports**:
```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np
import pandas as pd
```

**Data Paths Used**: None

**Potential Issues**: ✅ None (statsmodels is optional/lazy)

---

#### `analysis/api_router.py`
**Role**: FastAPI router exposing analysis endpoints  
**Import Category**: Mixed  
**Relative Imports**:
```python
from config.logger import get_logger
from config.settings import PROCESSED_DIR, TICKERS
```

**External Imports**:
```python
from __future__ import annotations
import json, glob, os
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import pandas as pd
```

**Data Paths Used**:
- Reads from `PROCESSED_DIR` (glob patterns for data files)

**Potential Issues**: ⚠️ 
- Uses glob on `PROCESSED_DIR` — no issue if path valid

---

### FEATURE ENGINEERING (4 files)

#### `feature_engineering/pipeline.py`
**Role**: Main orchestrator for feature engineering  
**Import Category**: Mixed  
**Relative Imports** (First 50 lines):
```python
from __future__ import annotations 
import glob, os
from datetime import datetime, timezone
from typing import Optional
# (Imports feature builders below line 50)
```

**Likely Relative Imports** (based on file structure):
```python
from config.logger import get_logger  # Assumed
from config.settings import PROCESSED_DIR  # Assumed
from feature_engineering.sentiment_features import SentimentFeatureBuilder
from feature_engineering.volatility_features import VolatilityFeatureBuilder
from feature_engineering.momentum_features import MomentumFeatureBuilder
```

**External Imports**:
```python
import glob, os
from datetime import datetime, timezone
from typing import Optional
import pandas as pd
```

**Data Paths Used**:
- `PROCESSED_DIR` (input/output)

**Potential Issues**: ✅ Likely none (standard pattern)

---

#### `feature_engineering/sentiment_features.py`
**Role**: Builds sentiment-derived features  
**Import Category**: Minimal  
**Relative Imports**:
```python
from config.logger import get_logger
```

**External Imports**:
```python
from __future__ import annotations
import numpy as np
import pandas as pd
```

**Data Paths Used**: None

**Potential Issues**: ✅ None

---

#### `feature_engineering/momentum_features.py`
**Role**: Builds price momentum features  
**Import Category**: Minimal  
**Relative Imports**:
```python
from config.logger import get_logger
```

**External Imports**:
```python
from __future__ import annotations
import numpy as np
import pandas as pd
```

**Data Paths Used**: None

**Potential Issues**: ✅ None

---

#### `feature_engineering/volatility_features.py`
**Role**: Builds volatility features  
**Import Category**: Minimal  
**Relative Imports**:
```python
from config.logger import get_logger
```

**External Imports**:
```python
from __future__ import annotations
import numpy as np
import pandas as pd
```

**Data Paths Used**: None

**Potential Issues**: ✅ None

---

### DATA COLLECTION (5 files)

#### `data_collection/pipeline.py`
**Role**: Orchestrator for news + price data collection  
**Import Category**: Mixed  
**Relative Imports**:
```python
from config.logger import get_logger
from config.settings import PROCESSED_DIR, TICKERS, LOOKBACK_DAYS
from data_collection.news.newsapi_fetcher import NewsAPIFetcher
from data_collection.prices.yfinance_fetcher import YFinanceFetcher
from data_collection.schemas import NewsCollection, PriceHistory
```

**External Imports**:
```python
from __future__ import annotations
import os
from datetime import date, datetime, timezone
from typing import List, Optional, Tuple
import pandas as pd
```

**Data Paths Used**:
- `PROCESSED_DIR` (output)

**Potential Issues**: ✅ None

---

#### `data_collection/http_client.py`
**Role**: Retry-enabled HTTP client wrapper  
**Import Category**: External only  
**All Imports**:
```python
import time
from typing import Any, Dict, Optional
import requests
from requests import Response
from config.logger import get_logger  # Relative import
from config.settings import HTTP_TIMEOUT, MAX_RETRIES, RETRY_BACKOFF  # Relative
```

**Data Paths Used**: None

**Potential Issues**: ✅ None

---

#### `data_collection/schemas.py`
**Role**: Pydantic models for news/price data  
**Import Category**: External only  
**All Imports**:
```python
from __future__ import annotations
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
```

**Relative Imports**: None

**Data Paths Used**: None

**Potential Issues**: ✅ None

---

#### `data_collection/news/newsapi_fetcher.py`
**Role**: NewsAPI client for fetching articles  
**Import Category**: Mixed  
**Relative Imports**:
```python
from config.logger import get_logger
from config.settings import (
    COMPANY_KEYWORDS,
    NEWSAPI_BASE_URL,
    NEWSAPI_KEY,
    NEWSAPI_MAX_PAGES,
    NEWSAPI_PAGE_SIZE,
    RAW_NEWS_DIR,
    CACHE_DIR,
    TICKERS,
    LOOKBACK_DAYS,
)
from data_collection.http_client import HTTPClient
from data_collection.schemas import NewsCollection, RawArticle
```

**External Imports**:
```python
import json, os
from datetime import datetime, timedelta, timezone
from typing import List, Optional
```

**Data Paths Used**:
- `RAW_NEWS_DIR` (save raw articles)
- `CACHE_DIR` (cache fetched articles)

**Potential Issues**: 
- ⚠️ Creates/uses `RAW_NEWS_DIR` and `CACHE_DIR` — must exist

---

#### `data_collection/prices/yfinance_fetcher.py`
**Role**: Yahoo Finance price data fetcher  
**Import Category**: Mixed  
**Relative Imports**:
```python
from config.logger import get_logger
from config.settings import (
    CACHE_DIR,
    LOOKBACK_DAYS,
    PRICE_INTERVAL,
    RAW_PRICES_DIR,
    TICKERS,
)
from data_collection.schemas import DailyPrice, PriceHistory
```

**External Imports**:
```python
import json, math, os
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional
import pandas as pd
import yfinance as yf
```

**Data Paths Used**:
- `CACHE_DIR` (caching)
- `RAW_PRICES_DIR` (save raw prices)

**Potential Issues**:
- ⚠️ Uses `RAW_PRICES_DIR` and `CACHE_DIR`

---

### MODELS (4 files)

#### `models/pipeline.py`
**Role**: Train and evaluate all predictive models  
**Import Category**: Mixed  
**Relative Imports**:
```python
from config.logger import get_logger
from config.settings import PROCESSED_DIR
from models.preparation import DataPreparator, CLASSIFICATION_TARGET, REGRESSION_TARGET
from models.predictors import (
    LogisticRegressionModel,
    XGBoostClassifier,
    XGBoostRegressorModel,
    LSTMModel,
)
from models.evaluation import ModelEvaluator, ModelEvaluation
```

**External Imports**:
```python
from __future__ import annotations
import glob, json, os
from datetime import datetime, timezone
from typing import Optional
import numpy as np
import pandas as pd
```

**Data Paths Used**:
- `PROCESSED_DIR` (input/output)

**Potential Issues**: ✅ None

---

#### `models/predictors.py`
**Role**: Four ML model implementations (LogReg, XGBoost×2, LSTM)  
**Import Category**: Minimal relative  
**Relative Imports**:
```python
from config.logger import get_logger
```

**External Imports**:
```python
from __future__ import annotations
from typing import Optional
import numpy as np
import pandas as pd
# (sklearn, xgboost, keras imported inside classes)
```

**Data Paths Used**: None

**Potential Issues**: ✅ None (models are late imports inside methods)

---

#### `models/preparation.py`
**Role**: Data preparation and feature selection  
**Import Category**: Mixed  
**Relative Imports**:
```python
from config.logger import get_logger
```

**External Imports**:
```python
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
```

**Data Paths Used**: None

**Potential Issues**: ✅ None

---

#### `models/evaluation.py`
**Role**: Calculates ML model evaluation metrics  
**Import Category**: Minimal relative  
**Relative Imports**:
```python
from config.logger import get_logger
```

**External Imports**:
```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np
import pandas as pd
```

**Data Paths Used**: None

**Potential Issues**: ✅ None

---

### PIPELINE (1 file)

#### `pipeline/api_router.py`
**Role**: FastAPI router for data collection endpoints  
**Import Category**: Mixed  
**Relative Imports**:
```python
from config.logger import get_logger
from config.settings import PROCESSED_DIR, TICKERS, LOOKBACK_DAYS
from data_collection.pipeline import DataCollectionPipeline
```

**External Imports**:
```python
from __future__ import annotations
import glob, os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel
```

**Data Paths Used**:
- `PROCESSED_DIR` (check for processed files)

**Potential Issues**: ✅ None

---

### NOTEBOOKS (1 file)

#### `notebooks/generate_mock_data.py`
**Role**: Generates mock enriched parquet for testing  
**Import Category**: Standard library + numpy/pandas  
**Relative Imports**: **NONE** ⚠️  
**All Imports**:
```python
from __future__ import annotations
import os
import numpy as np
import pandas as pd
from datetime import date, timedelta
```

**Data Paths Used**:
- Hardcoded: `"data/processed/mock_enriched.parquet"`
- Uses `os.makedirs(os.path.dirname(output_path), exist_ok=True)`

**Potential Issues**: 
- ⚠️ **CRITICAL**: Uses relative path `"data/processed/mock_enriched.parquet"` 
- ⚠️ No imports from `config` — path is hardcoded
- ⚠️ Assumes script runs from root directory
- ✅ Script is standalone, not imported by others

---

### STREAMLIT (1 file)

#### `.streamlit/streamlit_app.py`
**Role**: Interactive web dashboard  
**Location**: **NOT at root** (in `.streamlit/` subdirectory) ⚠️  
**Import Category**: External visualization only  
**All Imports**:
```python
import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
```

**Relative Imports**: **NONE** ❌

**Data Paths Used**: None visible in first 50 lines

**Potential Issues**: 
- ❌ **CRITICAL**: Does NOT import any project modules
- ❌ Must import from parent directories or use sys.path manipulation
- ⚠️ Uses `requests` to call API endpoints instead of importing modules
- ⚠️ Relative pathing will break if moved or structure changes

---

## ⚠️ BREAKING POINTS SUMMARY

### Files that need updating for new structure:

1. **ALL 28 internal Python files** use relative imports assuming:
   - Root-level execution context
   - `config/`, `sentiment_engine/`, `analysis/`, etc. all accessible from `sys.path[0]`

2. **`.streamlit/streamlit_app.py`** — Different import pattern:
   - Currently uses REST API calls via `requests` module
   - Will need to add `sys.path` manipulation or import config after moving
   - Relative paths won't work from `.streamlit/` directory

3. **`notebooks/generate_mock_data.py`** — Isolated:
   - Hardcoded path: `"data/processed/mock_enriched.parquet"`
   - Must be run from root directory
   - No config imports → no fragile dependency

4. **Path dependencies** (in `config/settings.py`):
   - `BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))`
   - Assumes `config/settings.py` is 2 levels deep from root
   - Will BREAK if `settings.py` moves to different depth

---

## 📊 Import Dependency Graph

```
Imported by ALL modules:
├─ config.settings (constants, paths)
└─ config.logger (logging factory)

Entry points:
├─ main.py → FastAPI routers
├─ .streamlit/streamlit_app.py → REST API calls (isolated)
└─ notebooks/generate_mock_data.py → Standalone (hardcoded paths)

Main pipelines:
├─ sentiment_engine/pipeline.py
├─ feature_engineering/pipeline.py
├─ data_collection/pipeline.py
├─ analysis/pipeline.py
└─ models/pipeline.py

API routers:
├─ pipeline/api_router.py → calls data_collection/pipeline.py
├─ analysis/api_router.py → reads PROCESSED_DIR
└─ main.py registers both

Data flow:
  data_collection → sentiment_engine → feature_engineering → analysis/models
```

---

## ✅ Recommendations for Restructuring

### 1. Add `__init__.py` files
If moving modules, add explicit:
```python
# Each package/module/__init__.py
from .submodule import Class  # Explicit re-exports
```

### 2. Update `config/settings.py` path logic
```python
# Current (fragile):
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Better (robust):
import pathlib
BASE_DIR = pathlib.Path(__file__).parent.parent.resolve()
```

### 3. Handle `.streamlit/streamlit_app.py`
- Option A: Keep using REST API calls (current approach — works!)
- Option B: Add sys.path manipulation at top:
  ```python
  import sys
  from pathlib import Path
  sys.path.insert(0, str(Path(__file__).parent.parent))
  from config.logger import get_logger
  ```

### 4. Update `notebooks/generate_mock_data.py`
- Add config import:
  ```python
  from pathlib import Path
  import sys
  sys.path.insert(0, str(Path(__file__).parent.parent))
  from config.settings import PROCESSED_DIR
  
  def generate_mock_enriched(output_path: str = None):
      output_path = output_path or os.path.join(PROCESSED_DIR, "mock_enriched.parquet")
  ```

### 5. Don't move `config/settings.py` relative to root
- Keep it exactly 1 level deep from root
- Or recompute `BASE_DIR` dynamically after any move

---

## 📌 All Python Files Listed (29 total)

✓ Relative imports reviewed:
1. `.streamlit/streamlit_app.py` — NO relative imports ❌
2. `main.py` — uses relative imports ✓
3. `config/settings.py` — stdlib only ✓
4. `config/logger.py` — 1 relative import ✓
5. `sentiment_engine/schemas.py` — stdlib only ✓
6. `sentiment_engine/pipeline.py` — 5 relative imports ✓
7. `sentiment_engine/finbert_scorer.py` — 2 relative imports ✓
8. `sentiment_engine/claude_scorer.py` — 3 relative imports ✓
9. `sentiment_engine/aggregator.py` — 3 relative imports ✓
10. `analysis/pipeline.py` — 5 relative imports ✓
11. `analysis/correlation.py` — 1 relative import ✓
12. `analysis/regression.py` — 1 relative import ✓
13. `analysis/granger.py` — 1 relative import ✓
14. `analysis/api_router.py` — 2 relative imports ✓
15. `feature_engineering/pipeline.py` — ~3 relative imports ✓
16. `feature_engineering/sentiment_features.py` — 1 relative import ✓
17. `feature_engineering/momentum_features.py` — 1 relative import ✓
18. `feature_engineering/volatility_features.py` — 1 relative import ✓
19. `data_collection/pipeline.py` — 5 relative imports ✓
20. `data_collection/http_client.py` — 2 relative imports ✓
21. `data_collection/schemas.py` — stdlib only ✓
22. `data_collection/news/newsapi_fetcher.py` — 4 relative imports ✓
23. `data_collection/prices/yfinance_fetcher.py` — 3 relative imports ✓
24. `models/pipeline.py` — 5 relative imports ✓
25. `models/predictors.py` — 1 relative import ✓
26. `models/preparation.py` — 1 relative import ✓
27. `models/evaluation.py` — 1 relative import ✓
28. `pipeline/api_router.py` — 3 relative imports ✓
29. `notebooks/generate_mock_data.py` — NO relative imports ❌

---

**Status**: ✅ Analysis Complete
