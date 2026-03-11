"""
Orchestrates the full model training and evaluation step.

Flow
----
1. Load feature matrix from data/processed/features_*.parquet
2. Prepare classification splits  (LogReg + XGBoost classifier + LSTM)
3. Prepare regression splits      (XGBoost regressor)
4. Train all four models per ticker + pooled
5. Evaluate each model with all metrics
6. Save comparison table + feature importances to parquet/json
7. Print leaderboard to console

Output files
------------
data/processed/model_results_<date>.parquet   ← comparison table
data/processed/feature_importance_<date>.json ← top features per model
data/processed/model_results_<date>.json      ← findings + interpretations
"""

from __future__ import annotations

import glob
import json
import os
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd

from config.logger import get_logger
from config.settings import PROCESSED_DIR
from models.preparation import DataPreparator, CLASSIFICATION_TARGET, REGRESSION_TARGET
from models.predictors  import (
    LogisticRegressionModel,
    XGBoostClassifier,
    XGBoostRegressorModel,
    LSTMModel,
)
from models.evaluation import ModelEvaluator, ModelEvaluation

log = get_logger(__name__)


class ModelPipeline:
    """
    Trains and evaluates all four predictive models.

    Parameters
    ----------
    run_lstm        : set False to skip LSTM (requires TensorFlow, slow)
    lstm_timesteps  : sequence length for LSTM
    test_size       : fraction of data for test set
    """

    def __init__(
        self,
        run_lstm:       bool  = True,
        lstm_timesteps: int   = 10,
        test_size:      float = 0.20,
    ):
        self.run_lstm   = run_lstm
        self.preparator = DataPreparator(
            test_size      = test_size,
            lstm_timesteps = lstm_timesteps,
        )
        self.evaluator  = ModelEvaluator()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run(self, input_parquet: Optional[str] = None) -> dict:
        """
        Execute full model training + evaluation pipeline.

        Returns
        -------
        dict with keys:
          results       : List[ModelEvaluation]
          comparison    : pd.DataFrame  (leaderboard)
          importances   : dict          (feature importance per model/ticker)
        """
        log.info("=" * 60)
        log.info("Starting ModelPipeline")
        log.info("=" * 60)

        df = self._load(input_parquet)
        if df.empty:
            log.error("No feature data. Run feature_engineering.pipeline first.")
            return {}

        log.info("Feature matrix: %s", df.shape)

        all_results:  list[ModelEvaluation] = []
        importances:  dict                  = {}

        # ── Classification splits ─────────────────────────────────────
        clf_splits    = self.preparator.prepare_classification(df)
        pooled_clf    = self.preparator.prepare_pooled(df, target=CLASSIFICATION_TARGET)
        if pooled_clf:
            clf_splits["POOLED"] = pooled_clf

        # ── Regression splits ─────────────────────────────────────────
        reg_splits    = self.preparator.prepare_regression(df)
        pooled_reg    = self.preparator.prepare_pooled(df, target=REGRESSION_TARGET)
        if pooled_reg:
            reg_splits["POOLED"] = pooled_reg

        # ── LSTM splits ───────────────────────────────────────────────
        lstm_splits = {}
        if self.run_lstm:
            lstm_splits = self.preparator.prepare_lstm(df, target=CLASSIFICATION_TARGET)

        # ── Train + evaluate per ticker ───────────────────────────────
        for ticker in list(clf_splits.keys()):
            log.info("── Training models for %s ──", ticker)

            clf_split = clf_splits.get(ticker)
            reg_split = reg_splits.get(ticker)
            lstm_split = lstm_splits.get(ticker)

            # 1. Logistic Regression
            if clf_split:
                res, imp = self._run_logreg(clf_split)
                all_results.extend(res)
                if imp is not None:
                    importances[f"LogReg_{ticker}"] = imp.head(10).to_dict()

            # 2. XGBoost Classifier
            if clf_split:
                res, imp = self._run_xgb_clf(clf_split)
                all_results.extend(res)
                if imp is not None:
                    importances[f"XGBClf_{ticker}"] = imp.head(10).to_dict()

            # 3. XGBoost Regressor
            if reg_split:
                res, imp = self._run_xgb_reg(reg_split)
                all_results.extend(res)
                if imp is not None:
                    importances[f"XGBReg_{ticker}"] = imp.head(10).to_dict()

            # 4. LSTM
            if lstm_split and self.run_lstm:
                res = self._run_lstm(lstm_split)
                all_results.extend(res)

        # ── Comparison table ──────────────────────────────────────────
        comparison = self.evaluator.comparison_table(all_results)

        # ── Save ──────────────────────────────────────────────────────
        self._save(comparison, importances, all_results)

        # ── Print leaderboard ─────────────────────────────────────────
        self._print_leaderboard(comparison, importances)

        return {
            "results":    all_results,
            "comparison": comparison,
            "importances": importances,
        }

    # ------------------------------------------------------------------
    # Per-model trainers
    # ------------------------------------------------------------------

    def _run_logreg(self, split):
        model = LogisticRegressionModel()
        try:
            model.fit(split.X_train, split.y_train)
        except Exception as e:
            log.error("LogReg failed for %s: %s", split.ticker, e)
            return [], None

        y_pred  = model.predict(split.X_test)
        y_proba = model.predict_proba(split.X_test)
        rets    = self._get_actual_returns(split)

        result = self.evaluator.evaluate_classifier(
            model_name     = "LogisticRegression",
            ticker         = split.ticker,
            y_true         = split.y_test,
            y_pred         = y_pred,
            y_proba        = y_proba,
            actual_returns = rets,
        )
        imp = model.feature_importance(split.feature_names)
        return [result], imp

    def _run_xgb_clf(self, split):
        model = XGBoostClassifier()
        try:
            model.fit(split.X_train, split.y_train)
        except Exception as e:
            log.error("XGBClf failed for %s: %s", split.ticker, e)
            return [], None

        y_pred  = model.predict(split.X_test)
        y_proba = model.predict_proba(split.X_test)
        rets    = self._get_actual_returns(split)

        result = self.evaluator.evaluate_classifier(
            model_name     = "XGBoostClassifier",
            ticker         = split.ticker,
            y_true         = split.y_test,
            y_pred         = y_pred,
            y_proba        = y_proba,
            actual_returns = rets,
        )
        imp = model.feature_importance(split.feature_names)
        return [result], imp

    def _run_xgb_reg(self, split):
        model = XGBoostRegressorModel()
        try:
            model.fit(split.X_train, split.y_train)
        except Exception as e:
            log.error("XGBReg failed for %s: %s", split.ticker, e)
            return [], None

        y_pred = model.predict(split.X_test)
        rets   = split.y_test   # for regression, y_test IS the returns

        result = self.evaluator.evaluate_regressor(
            model_name     = "XGBoostRegressor",
            ticker         = split.ticker,
            y_true         = split.y_test,
            y_pred         = y_pred,
            actual_returns = rets,
        )
        imp = model.feature_importance(split.feature_names)
        return [result], imp

    def _run_lstm(self, seq_split):
        model = LSTMModel(
            timesteps  = seq_split.timesteps,
            n_features = seq_split.X_train.shape[2],
        )
        try:
            model.fit(seq_split.X_train, seq_split.y_train)
        except Exception as e:
            log.error("LSTM failed for %s: %s", seq_split.ticker, e)
            return []

        y_pred  = model.predict(seq_split.X_test)
        y_proba = model.predict_proba(seq_split.X_test)

        result = self.evaluator.evaluate_classifier(
            model_name = "LSTM",
            ticker     = seq_split.ticker,
            y_true     = seq_split.y_test,
            y_pred     = y_pred,
            y_proba    = y_proba,
        )
        return [result]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_actual_returns(self, split) -> Optional[np.ndarray]:
        """Try to get forward_return_1d aligned with the test split."""
        return None  # Will be enriched if return data is available in split

    def _load(self, path: Optional[str]) -> pd.DataFrame:
        if path and os.path.exists(path):
            return pd.read_parquet(path)
        files = sorted(glob.glob(os.path.join(PROCESSED_DIR, "features_*.parquet")))
        if not files:
            return pd.DataFrame()
        log.info("Auto-loading: %s", os.path.basename(files[-1]))
        return pd.read_parquet(files[-1])

    def _save(self, comparison: pd.DataFrame, importances: dict, results: list):
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")

        comparison.to_parquet(
            os.path.join(PROCESSED_DIR, f"model_results_{date_str}.parquet"),
            index=False,
        )
        with open(os.path.join(PROCESSED_DIR, f"feature_importance_{date_str}.json"), "w") as f:
            json.dump(importances, f, indent=2)

        findings = [r.interpretation for r in results if r.interpretation]
        with open(os.path.join(PROCESSED_DIR, f"model_findings_{date_str}.json"), "w") as f:
            json.dump(findings, f, indent=2)

        log.info("Model results saved to data/processed/")

    def _print_leaderboard(self, comparison: pd.DataFrame, importances: dict):
        sep = "═" * 65
        print(f"\n{sep}")
        print("  FINSENTIMENT LAB · MODEL LEADERBOARD")
        print(sep)

        display_cols = ["ticker", "model", "task", "n_test",
                        "accuracy", "auc_roc", "hit_rate", "sharpe", "r_squared"]
        cols = [c for c in display_cols if c in comparison.columns]
        print(comparison[cols].to_string(index=False))

        print(f"\n{sep}")
        print("  TOP FEATURES (XGBoost Classifier — POOLED)")
        print(sep)
        pooled_imp = importances.get("XGBClf_POOLED", {})
        if pooled_imp:
            for feat, score in sorted(pooled_imp.items(), key=lambda x: -x[1])[:10]:
                bar = "█" * int(score * 200)
                print(f"  {feat:<35} {score:.4f}  {bar}")
        else:
            print("  (run pipeline to populate)")
        print(sep)


# ---------------------------------------------------------------------------
# FastAPI router
# ---------------------------------------------------------------------------

from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import Any, Dict as FDict

router = APIRouter(prefix="/models", tags=["Models"])
_state = type("S", (), {"running": False, "last_run_at": None, "error": None})()
_cache: FDict[str, Any] = {}


def _run_bg(input_parquet, run_lstm):
    _state.running = True
    _state.error   = None
    try:
        pipeline = ModelPipeline(run_lstm=run_lstm)
        results  = pipeline.run(input_parquet=input_parquet)
        _cache["comparison"]   = results["comparison"].to_dict(orient="records") if results else []
        _cache["importances"]  = results.get("importances", {})
        _cache["findings"]     = [r.interpretation for r in results.get("results", [])]
        _state.last_run_at     = datetime.now(timezone.utc).isoformat()
    except Exception as exc:
        _state.error = str(exc)
        log.error("Model pipeline failed: %s", exc)
    finally:
        _state.running = False


@router.post("/run")
async def run_models(
    background_tasks: BackgroundTasks,
    input_parquet: Optional[str] = None,
    run_lstm: bool = True,
):
    if _state.running:
        raise HTTPException(409, "Model pipeline already running.")
    background_tasks.add_task(_run_bg, input_parquet, run_lstm)
    return {"status": "started"}


@router.get("/status")
async def get_status():
    return {"running": _state.running, "last_run_at": _state.last_run_at, "error": _state.error}


@router.get("/leaderboard")
async def get_leaderboard(ticker: Optional[str] = None):
    if "comparison" not in _cache:
        raise HTTPException(404, "Run the model pipeline first.")
    data = _cache["comparison"]
    if ticker:
        data = [r for r in data if r.get("ticker") == ticker.upper()]
    return data


@router.get("/importances")
async def get_importances(model: Optional[str] = None):
    if "importances" not in _cache:
        raise HTTPException(404, "Run the model pipeline first.")
    if model:
        return {k: v for k, v in _cache["importances"].items() if model in k}
    return _cache["importances"]


@router.get("/findings")
async def get_findings():
    if "findings" not in _cache:
        raise HTTPException(404, "Run the model pipeline first.")
    return {"findings": _cache["findings"]}


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="FinSentiment Lab — Model Pipeline")
    parser.add_argument("--input",     default=None,        help="Path to features parquet")
    parser.add_argument("--no-lstm",   action="store_true", help="Skip LSTM (faster)")
    args = parser.parse_args()

    pipeline = ModelPipeline(run_lstm=not args.no_lstm)
    pipeline.run(input_parquet=args.input)