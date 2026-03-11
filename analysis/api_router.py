"""
analysis/api_router.py
----------------------------------------------------------------------
FastAPI router that exposes sentiment, model, and analysis data over HTTP.

Endpoints
---------
GET  /analysis/sentiment/{ticker}    → sentiment timeline for a ticker
GET  /analysis/leaderboard           → model performance rankings
GET  /analysis/features              → feature importance for all models
GET  /analysis/granger               → Granger causality results
GET  /analysis/correlation           → correlation matrix
"""

from __future__ import annotations

import json
import glob
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import pandas as pd

from config.logger import get_logger
from config.settings import PROCESSED_DIR, TICKERS

log = get_logger(__name__)
router = APIRouter(prefix="/analysis", tags=["Analysis"])


# ─── Response Models ──────────────────────────────────────────────────────────

class SentimentPoint(BaseModel):
    date: str
    score: float
    label: str


class LeaderboardRow(BaseModel):
    ticker: str
    model: str
    auc: float
    accuracy: Optional[float] = None
    f1: Optional[float] = None
    hit_rate: Optional[float] = None
    sharpe: float
    cum_return: Optional[float] = None


class FeatureImportanceItem(BaseModel):
    feature: str
    score: float
    model: str
    ticker: str


class GrangerResult(BaseModel):
    ticker: str
    cause: str
    effect: str
    lag: int
    p_value: float
    significant: bool


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _load_latest_json(pattern: str) -> Any:
    """Load the most recent JSON file matching a glob pattern."""
    files = sorted(glob.glob(pattern))
    if not files:
        return None
    try:
        with open(files[-1], 'r') as f:
            return json.load(f)
    except Exception as e:
        log.error(f"Failed to load {files[-1]}: {e}")
        return None


def _parse_model_findings() -> List[Dict]:
    """Parse model findings from JSON into structured data."""
    findings = _load_latest_json(os.path.join(PROCESSED_DIR, "model_findings_*.json"))
    if not findings or not isinstance(findings, list):
        return []
    
    results = []
    for line in findings:
        if isinstance(line, str):
            # Parse: "AAPL XGBoostClassifier: AUC=0.762 — ... | hit_rate=80.0% — ..."
            parts = line.split(':')
            if len(parts) < 2:
                continue
            
            ticker_model = parts[0].strip().split()
            if len(ticker_model) < 2:
                continue
            
            ticker = ticker_model[0]
            model = ' '.join(ticker_model[1:])
            metrics_str = ':'.join(parts[1:])
            
            # Extract metrics
            auc_match = metrics_str.find('AUC=')
            hit_match = metrics_str.find('hit_rate=')
            sharpe_match = metrics_str.find('Sharpe=')
            r2_match = metrics_str.find('R²=')
            
            auc = None
            hit_rate = None
            sharpe = None
            accuracy = None
            f1 = None
            cum_return = None
            
            if auc_match != -1:
                auc_end = metrics_str.find(' ', auc_match)
                auc_str = metrics_str[auc_match+4:auc_end if auc_end != -1 else auc_match+10]
                try:
                    auc = float(auc_str.strip('—').strip())
                except:
                    pass
            
            if hit_match != -1:
                hit_end = metrics_str.find('%', hit_match)
                hit_str = metrics_str[hit_match+9:hit_end if hit_end != -1 else hit_match+15]
                try:
                    hit_rate = float(hit_str.strip()) / 100
                except:
                    pass
            
            if sharpe_match != -1:
                sharpe_end = metrics_str.find(' ', sharpe_match)
                sharpe_str = metrics_str[sharpe_match+7:sharpe_end if sharpe_end != -1 else sharpe_match+12]
                try:
                    sharpe = float(sharpe_str.strip())
                except:
                    pass
            
            if r2_match != -1:
                r2_end = metrics_str.find(' ', r2_match)
                r2_str = metrics_str[r2_match+3:r2_end if r2_end != -1 else r2_match+10]
                try:
                    accuracy = float(r2_str.strip())
                except:
                    pass
            
            # Set defaults
            if auc is None:
                auc = 0.5
            if hit_rate is None:
                hit_rate = 0.5
            if sharpe is None:
                sharpe = 0.0
            
            results.append({
                "ticker": ticker,
                "model": model,
                "auc": auc,
                "accuracy": accuracy,
                "f1": f1,
                "hit_rate": hit_rate,
                "sharpe": sharpe,
                "cum_return": cum_return,
            })
    
    return results


def _parse_granger_results() -> List[Dict]:
    """Parse Granger causality results from analysis findings."""
    findings = _load_latest_json(os.path.join(PROCESSED_DIR, "analysis_*_findings.json"))
    if not findings or not isinstance(findings, list):
        return []
    
    results = []
    for line in findings:
        if isinstance(line, str) and '—>' in line:
            # Format: "  AAPL: mean_score → daily_return | best_lag=0d | p=1.0000  ✗ NO"
            try:
                parts = line.strip().split('|')
                if len(parts) < 3:
                    continue
                
                ticker_cause = parts[0].strip().split(':')
                if len(ticker_cause) < 2:
                    continue
                
                ticker = ticker_cause[0].strip()
                cause_effect = ticker_cause[1].strip().split('→')
                if len(cause_effect) < 2:
                    continue
                
                cause = cause_effect[0].strip()
                effect = cause_effect[1].strip()
                
                lag_str = parts[1].strip()
                p_str = parts[2].strip()
                
                # Extract lag
                lag = 0
                if 'best_lag=' in lag_str:
                    lag_val = lag_str.split('best_lag=')[1].strip().replace('d', '')
                    try:
                        lag = int(lag_val)
                    except:
                        pass
                
                # Extract p-value
                p_value = 1.0
                if 'p=' in p_str:
                    p_val_str = p_str.split('p=')[1].strip().split()[0]
                    try:
                        p_value = float(p_val_str)
                    except:
                        pass
                
                significant = p_value < 0.05
                
                results.append({
                    "ticker": ticker,
                    "cause": cause,
                    "effect": effect,
                    "lag": lag,
                    "p_value": p_value,
                    "significant": significant,
                })
            except Exception as e:
                log.debug(f"Failed to parse Granger line: {e}")
    
    return results


# ─── Route Handlers ───────────────────────────────────────────────────────────

@router.get("/sentiment/{ticker}", response_model=List[SentimentPoint], 
            summary="Get sentiment timeline for a ticker")
async def get_sentiment_timeline(
    ticker: str,
    days: int = Query(60, description="Number of days to return"),
):
    """
    Returns sentiment scores over time for the specified ticker.
    Data is loaded from cached sentiment files.
    """
    ticker = ticker.upper()
    if ticker not in TICKERS and ticker != "POOLED":
        raise HTTPException(status_code=400, detail=f"Invalid ticker: {ticker}")
    
    # Look for cached sentiment data
    cache_pattern = os.path.join(PROCESSED_DIR, f"sentiment_{ticker}_*.json")
    cache_files = sorted(glob.glob(cache_pattern))
    
    if not cache_files:
        # Fallback: generate mock data if no cache exists
        log.warning(f"No sentiment cache found for {ticker}, returning empty list")
        return []
    
    try:
        with open(cache_files[-1], 'r') as f:
            data = json.load(f)
        
        # Ensure it's a list and format properly
        if isinstance(data, dict):
            data = data.get('data', [])
        
        if isinstance(data, list):
            results = []
            for item in data[-days:]:  # Return last N days
                results.append(SentimentPoint(
                    date=item.get('date', ''),
                    score=float(item.get('score', 0.0)),
                    label=item.get('label', 'neutral'),
                ))
            return results
    except Exception as e:
        log.error(f"Error loading sentiment for {ticker}: {e}")
    
    return []


@router.get("/leaderboard", response_model=List[LeaderboardRow],
            summary="Get model performance leaderboard")
async def get_leaderboard():
    """
    Returns ranked models by AUC score.
    Data is parsed from the latest model_findings JSON.
    """
    results = _parse_model_findings()
    # Sort by AUC descending
    results.sort(key=lambda x: x.get('auc', 0), reverse=True)
    return [LeaderboardRow(**r) for r in results]


@router.get("/features", response_model=List[FeatureImportanceItem],
            summary="Get feature importance across all models")
async def get_feature_importance(
    model: Optional[str] = Query(None, description="Filter by model name"),
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
):
    """
    Returns feature importance scores from all trained models.
    """
    importance_data = _load_latest_json(
        os.path.join(PROCESSED_DIR, "feature_importance_*.json")
    )
    
    if not importance_data or not isinstance(importance_data, dict):
        return []
    
    results = []
    for model_key, features in importance_data.items():
        # Parse model_key: "LogReg_AAPL", "XGBClf_MSFT", etc.
        parts = model_key.rsplit('_', 1)
        if len(parts) == 2:
            model_name, ticker_name = parts
            
            # Skip if filtering doesn't match
            if model and model not in model_name:
                continue
            if ticker and ticker != ticker_name:
                continue
            
            for feature, score in features.items():
                results.append(FeatureImportanceItem(
                    feature=feature,
                    score=float(score),
                    model=model_name,
                    ticker=ticker_name,
                ))
    
    return results


@router.get("/granger", response_model=List[GrangerResult],
            summary="Get Granger causality test results")
async def get_granger(
    significant_only: bool = Query(False, description="Filter to significant only"),
):
    """
    Returns Granger causality test results showing lagged sentiment effects on price/volatility.
    """
    results = _parse_granger_results()
    
    if significant_only:
        results = [r for r in results if r.get('significant', False)]
    
    return [GrangerResult(**r) for r in results]


@router.get("/correlation", summary="Get correlation matrix")
async def get_correlation(
    ticker: str = Query("POOLED", description="Ticker for correlation"),
):
    """
    Returns feature correlation matrix.
    Currently returns a mock correlation matrix.
    """
    import numpy as np
    
    features = ["mean_score", "sent_roll_7d", "sent_zscore", "rsi_14d",
                "vol_ratio", "return_5d", "atr_pct", "news_day"]
    
    # Generate mock correlation (in production, load from saved matrix)
    np.random.seed(hash(ticker) % 2**32)
    corr_matrix = np.random.uniform(-0.7, 1, (len(features), len(features)))
    corr_matrix = (corr_matrix + corr_matrix.T) / 2
    np.fill_diagonal(corr_matrix, 1.0)
    
    return {
        "ticker": ticker,
        "features": features,
        "correlation_matrix": corr_matrix.tolist(),
    }


@router.get("/health", summary="Health check for analysis subsystem")
async def health_check():
    """Simple health check."""
    return {"status": "ok", "service": "analysis"}
