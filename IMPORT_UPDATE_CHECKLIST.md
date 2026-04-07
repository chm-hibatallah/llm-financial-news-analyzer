# FinSentiment-Lab: Import Update Checklist

**Analysis Date**: 2026-04-07  
**Status**: Ready for migration  
**Total Files to Update**: 28 Python files (+ streamlit special case)

---

## 🎯 QUICK SUMMARY

### Key Structural Issues Found

| Issue | Severity | Files Affected | Impact |
|-------|----------|----------------|--------|
| No `__init__.py` files | Medium | All packages | Namespace packages only; explicit is better |
| Relative imports assume root execution | High | 28 files | BREAKS if module path changes |
| `.streamlit/streamlit_app.py` isolated | Medium | 1 file | Uses REST API; won't auto-update with refactoring |
| Hardcoded paths in generate_mock_data.py | Low | 1 file | Works, but fragile; should use config |
| `config/settings.py` path logic fragile | Medium | 1 file (affects all 28) | Uses dirname chain; breaks if moved |

---

## ✅ IMPORT UPDATE CHECKLIST

### Phase 1: Package Structure (Before Running Code)

- [ ] Create `__init__.py` in each package:
  - [ ] `config/__init__.py`
  - [ ] `sentiment_engine/__init__.py`
  - [ ] `analysis/__init__.py`
  - [ ] `feature_engineering/__init__.py`
  - [ ] `data_collection/__init__.py`
  - [ ] `data_collection/news/__init__.py`
  - [ ] `data_collection/prices/__init__.py`
  - [ ] `models/__init__.py`
  - [ ] `pipeline/__init__.py`
  - [ ] `notebooks/__init__.py` (optional, for testing)

### Phase 2: Update Path Logic in config/settings.py

- [ ] Replace fragile `os.path.dirname()` chain with pathlib:
  ```python
  # Change from:
  BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  
  # Change to:
  from pathlib import Path
  BASE_DIR = Path(__file__).parent.parent.resolve()
  ```

### Phase 3: Verify 28 Core Files (Loop through each)

For each of these 28 files, verify imports work in new structure:

**config/** (2 files)
- [ ] `settings.py` — No changes needed (stdlib only)
- [ ] `logger.py` — ✓ Uses `from config.settings import ...`

**sentiment_engine/** (5 files)
- [ ] `schemas.py` — No changes needed (pydantic only)
- [ ] `pipeline.py` — ✓ All relative imports
- [ ] `finbert_scorer.py` — ✓ All relative imports
- [ ] `claude_scorer.py` — ✓ All relative imports
- [ ] `aggregator.py` — ✓ All relative imports

**analysis/** (5 files)
- [ ] `pipeline.py` — ✓ All relative imports
- [ ] `correlation.py` — ✓ All relative imports
- [ ] `regression.py` — ✓ All relative imports
- [ ] `granger.py` — ✓ All relative imports
- [ ] `api_router.py` — ✓ All relative imports

**feature_engineering/** (4 files)
- [ ] `pipeline.py` — ✓ All relative imports
- [ ] `sentiment_features.py` — ✓ All relative imports
- [ ] `momentum_features.py` — ✓ All relative imports
- [ ] `volatility_features.py` — ✓ All relative imports

**data_collection/** (5 files)
- [ ] `pipeline.py` — ✓ All relative imports
- [ ] `http_client.py` — ✓ All relative imports
- [ ] `schemas.py` — No changes needed (pydantic only)
- [ ] `news/newsapi_fetcher.py` — ✓ All relative imports
- [ ] `prices/yfinance_fetcher.py` — ✓ All relative imports

**models/** (4 files)
- [ ] `pipeline.py` — ✓ All relative imports
- [ ] `predictors.py` — ✓ All relative imports
- [ ] `preparation.py` — ✓ All relative imports
- [ ] `evaluation.py` — ✓ All relative imports

**pipeline/** (1 file)
- [ ] `api_router.py` — ✓ All relative imports

**root/** (1 file)
- [ ] `main.py` — ✓ All relative imports

**notebooks/** (1 file - special case)
- [ ] `generate_mock_data.py` — ⚠️ Needs hardcoded path fix

**streamlit/** (1 file - special case)
- [ ] `.streamlit/streamlit_app.py` — ✓ No changes needed (uses REST API)

### Phase 4: Fix Fragile Imports

**File: `notebooks/generate_mock_data.py`** — UPDATE

Replace:
```python
def generate_mock_enriched(output_path: str = "data/processed/mock_enriched.parquet"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
```

With:
```python
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import PROCESSED_DIR

def generate_mock_enriched(output_path: str = None):
    if output_path is None:
        output_path = os.path.join(PROCESSED_DIR, "mock_enriched.parquet")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
```

**File: `.streamlit/streamlit_app.py`** — TEST (if importing modules)

If you later move from REST API to direct imports, add at top:
```python
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

# Then add your project imports:
# from config.logger import get_logger
# from config.settings import TICKERS
```

### Phase 5: Test Execution Modes

- [ ] **Mode 1 — CLI**: `python main.py` from root
  - Verify all relative imports resolve
  - Check that `config/settings.py` paths are found

- [ ] **Mode 2 — Module**: `python -m sentiment_engine.pipeline`
  - Verify all relative imports still work with `-m` flag

- [ ] **Mode 3 — Streamlit**: `streamlit run .streamlit/streamlit_app.py`
  - Verify API endpoint calls work
  - Verify REST responses match expected schema

- [ ] **Mode 4 — FastAPI**: `uvicorn main:app --reload`
  - Verify routers mount correctly
  - Verify data paths resolve from config

---

## 📋 File-by-File Import Audit

### ⚠️ Files with Potential Issues

#### 1. `config/settings.py` (Path computation)
**Current Issue**:
```python
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
```
**Why it's fragile**: Chain of dirname() calls; if moved, breaks silently  
**Recommendation**: Use pathlib

**Current**:
```python
BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR: str = os.path.join(BASE_DIR, "data")
CACHE_DIR: str = os.path.join(DATA_DIR, "cache")
```

**Recommended**:
```python
import pathlib
_BASE = pathlib.Path(__file__).parent.parent.resolve()
BASE_DIR: str = str(_BASE)
DATA_DIR: str = str(_BASE / "data")
CACHE_DIR: str = str(_BASE / "data" / "cache")
```

---

#### 2. `notebooks/generate_mock_data.py` (Hardcoded path)
**Current Issue**:
```python
def generate_mock_enriched(output_path: str = "data/processed/mock_enriched.parquet"):
```
**Why it's fragile**: Doesn't use config.settings; path breaks if run from different directory  
**Status**: LOW priority (notebook script, not imported)  
**Recommendation**: Use `config.settings.PROCESSED_DIR`

---

#### 3. `.streamlit/streamlit_app.py` (Import isolation)
**Current Issue**: Completely isolated; uses REST API calls only  
**Why it matters**: If you refactor, it won't auto-update  
**Status**: ACCEPTABLE (REST API is intentional boundary)  
**Options**:
- **Option A** (Current): Keep REST API calls — works as-is ✓
- **Option B** (Future): Add sys.path manipulation and import modules directly

---

### ✅ Files with Clean Imports

All 25 other files use consistent patterns:
```python
from config.logger import get_logger
from config.settings import CONSTANT_NAME
from sentiment_engine.pipeline import SomeClass
```

These will work **as-is** with just:
1. Addition of `__init__.py` files
2. Execution from root directory or with `python -m` module mode

---

## 🔍 Import Pattern Analysis

### Pattern A: Pure External (2 files)
```python
# sentiment_engine/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional
```
**Status**: ✅ No changes needed

---

### Pattern B: Config + Logger (18 files)
```python
# sentiment_engine/finbert_scorer.py
from config.logger import get_logger
from config.settings import CACHE_DIR
from sentiment_engine.schemas import ArticleSentiment
```
**Status**: ✅ All relative; works in current structure

---

### Pattern C: Root Entry Point (2 files)
```python
# main.py
from config.logger import get_logger
from pipeline.api_router import router as collect_router
from analysis.api_router import router as analysis_router
```
**Status**: ✅ Can import everything because it's at depth 1

---

### Pattern D: Isolated + Hardcoded (2 files)
```python
# .streamlit/streamlit_app.py
import streamlit as st
import requests
# (uses REST API calls, not imports)

# notebooks/generate_mock_data.py
output_path: str = "data/processed/mock_enriched.parquet"  # Hardcoded!
```
**Status**: ⚠️ Works but fragile if moved

---

## 🚀 Migration Steps

### Step 1: Create Package Structure
Before running any code, create these empty files:
```bash
touch config/__init__.py
touch sentiment_engine/__init__.py
touch analysis/__init__.py
touch feature_engineering/__init__.py
touch data_collection/__init__.py
touch data_collection/news/__init__.py
touch data_collection/prices/__init__.py
touch models/__init__.py
touch pipeline/__init__.py
```

### Step 2: Update `config/settings.py`
Replace path computation logic (see section above)

### Step 3: Test Each Entry Point
```bash
# Test 1: FastAPI server
uvicorn main:app --reload

# Test 2: CLI modules
python -m sentiment_engine.pipeline

# Test 3: Streamlit
streamlit run .streamlit/streamlit_app.py

# Test 4: Notebooks
cd notebooks
python generate_mock_data.py
cd ..
```

### Step 4: Update `PYTHONPATH` if Running from Different Directory
If scripts are run from outside the root, add to your shell:
```bash
export PYTHONPATH="${PYTHONPATH}:/path/to/FinSentiment-Lab"
```

---

## 📊 Summary Statistics

| Metric | Value |
|--------|-------|
| Total Python files | 29 |
| Files with relative imports | 27 |
| Files with NO relative imports | 2 (streamlit + notebooks) |
| Files needing path fixes | 1 (`generate_mock_data.py`) |
| Packages needing `__init__.py` | 9 |
| Entry points | 3 (main.py, streamlit, notebooks) |
| Centralized config imports | YES (config/settings.py) |
| Circular import risk | LOW (settings → logger is tree, not cycle) |

---

## 🎯 Next Actions

1. **TODAY**: 
   - [ ] Create all `__init__.py` files
   - [ ] Update `config/settings.py` with pathlib
   - [ ] Update `notebooks/generate_mock_data.py` path logic

2. **AFTER STRUCTURE CHANGE**:
   - [ ] Test each entry point
   - [ ] Verify all relative paths resolve
   - [ ] Check API endpoints respond correctly

3. **DOCUMENTATION**:
   - [ ] Add PYTHONPATH requirements to README
   - [ ] Document execution modes (CLI, FastAPI, Streamlit, Notebooks)
   - [ ] Add troubleshooting guide for import errors

---

**Analysis Complete** ✅  
**Ready for implementation** 🚀
