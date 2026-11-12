"""
Module 3 & 4: Model Training Pipeline
======================================
Trains all 7 models for the Delhi DISCOM forecasting system:

  Module 3: Multi-Horizon Quantile Regression Engine
    - LightGBM Quantile (P10/P50/P90) for 24h horizon  → 3 models
    - LightGBM Quantile (P10/P50/P90) for 168h horizon → 3 models
    - Seasonal-Naive baseline (reference)
    - Ridge Linear Regression baseline (reference)

  Module 4: Dedicated Binary Peak-Event Classifier
    - LightGBM Binary Classifier (top-decile peak, optimised for Recall)
"""

import warnings
warnings.filterwarnings("ignore")

import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import pandas as pd
import joblib
import lightgbm as lgb
from sklearn.linear_model import Ridge
from sklearn.metrics import (
    mean_absolute_percentage_error, mean_squared_error,
    precision_score, recall_score, f1_score, classification_report
)

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────
FEATURE_COLS = [
    "CDH", "heat_index",
    "rolling_temp_24h", "rolling_temp_48h", "rolling_temp_72h",
    "temp_delta_24h",
    "hour_sin", "hour_cos", "dow_sin", "dow_cos",
    "month_sin", "month_cos", "doy_sin", "doy_cos",
    "hour", "day_of_week", "month", "is_weekend",
    "is_diwali", "is_eid", "is_holi",
    "is_republic_day", "is_independence", "is_christmas",
    "is_major_festival", "odd_even_flag", "lockdown_flag",
    "load_lag_24h", "load_lag_48h", "load_lag_168h",
    "load_rolling_mean_24h", "load_rolling_mean_48h",
    "load_delta_1h", "load_delta_24h",
    "trend_years",
    "temp_c", "humidity",
]

QUANTILES     = [0.10, 0.50, 0.90]
HORIZONS      = [24, 168]           # hours ahead
MODELS_DIR    = Path("models")
OUTPUTS_DIR   = Path("outputs")

# ─────────────────────────────────────────────────────────────────────────────
# LightGBM base params (quantile regression)
# ─────────────────────────────────────────────────────────────────────────────
LGBM_BASE_PARAMS = {
    "num_leaves":       127,
    "learning_rate":    0.05,
    "n_estimators":     800,
    "min_child_samples": 20,
    "subsample":        0.85,
    "colsample_bytree": 0.80,
    "reg_alpha":        0.1,
    "reg_lambda":       0.1,
    "random_state":     42,
    "n_jobs":           -1,
    "verbose":          -1,
}

LGBM_CLF_PARAMS = {
    "num_leaves":        63,
    "learning_rate":     0.05,
    "n_estimators":      600,
    "min_child_samples": 10,
    "subsample":         0.80,
    "colsample_bytree":  0.75,
    "scale_pos_weight":  8,          # Handles class imbalance (90:10 ratio)
    "random_state":      42,
    "n_jobs":            -1,
    "verbose":           -1,
}

# ─────────────────────────────────────────────────────────────────────────────
# Train / Validation split (chronological — NO shuffle)
# ─────────────────────────────────────────────────────────────────────────────
def chronological_split(df: pd.DataFrame, val_fraction: float = 0.15):
    """
    Strict chronological split. val_fraction = last 15% of data as validation.
    """
    n = len(df)
    split_idx = int(n * (1 - val_fraction))
    train_df = df.iloc[:split_idx]
    val_df   = df.iloc[split_idx:]
    print(f"  Train: {train_df.index.min().date()} -> {train_df.index.max().date()} ({len(train_df):,} rows)")
    print(f"  Val  : {val_df.index.min().date()} -> {val_df.index.max().date()} ({len(val_df):,} rows)")
    return train_df, val_df


def build_horizon_target(df: pd.DataFrame, horizon: int) -> pd.Series:
    """
    Build target = load_mw shifted back by `horizon` hours.
    i.e., at time t, target is what load will be at t+horizon.
    We shift FEATURES forward (predict future from current features).
    Equivalent: target = load.shift(-horizon), train on rows where target is known.
    """
    return df["load_mw"].shift(-horizon)


# ─────────────────────────────────────────────────────────────────────────────
# Module 3A: Baseline Models
# ─────────────────────────────────────────────────────────────────────────────
def train_seasonal_naive(df: pd.DataFrame) -> dict:
    """Seasonal-Naive: predict load = same hour 7 days ago (168h lag)."""
    return {
        "24h":  df["load_lag_168h"],   # For day-ahead: use last week same hour
        "168h": df["load_mw"].shift(2 * 168),  # For week-ahead: use 2 weeks ago
    }


def train_ridge_baseline(X_train, y_train, X_val, y_val, label=""):
    """Ridge regression baseline (linear model)."""
    ridge = Ridge(alpha=1.0)
    ridge.fit(X_train, y_train)
    preds = ridge.predict(X_val)
    mape  = mean_absolute_percentage_error(y_val, preds) * 100
    rmse  = np.sqrt(mean_squared_error(y_val, preds))
    print(f"  Ridge {label}: MAPE={mape:.2f}%  RMSE={rmse:.1f} MW")
    return ridge, preds


# ─────────────────────────────────────────────────────────────────────────────
# Module 3B: LightGBM Quantile Regression
# ─────────────────────────────────────────────────────────────────────────────
def train_quantile_model(
    X_train, y_train, X_val, y_val,
    quantile: float, horizon: int, label: str = ""
) -> lgb.LGBMRegressor:
    """Train a single LightGBM quantile regression model."""
    params = dict(LGBM_BASE_PARAMS)
    params["objective"] = "quantile"
    params["alpha"]     = quantile

    model = lgb.LGBMRegressor(**params)
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(-1)]
    )

    preds = model.predict(X_val)
    # For P50 (median), compute MAPE
    if abs(quantile - 0.50) < 0.01:
        mape = mean_absolute_percentage_error(y_val, preds) * 100
        rmse = np.sqrt(mean_squared_error(y_val, preds))
        print(f"  LightGBM P50 h={horizon}h {label}: MAPE={mape:.2f}%  RMSE={rmse:.1f} MW  (iters={model.best_iteration_})")

    return model


# ─────────────────────────────────────────────────────────────────────────────
# Pinball loss & PICP helpers
# ─────────────────────────────────────────────────────────────────────────────
def pinball_loss(y_true, y_pred, q: float) -> float:
    err = y_true - y_pred
    return float(np.mean(np.where(err >= 0, q * err, (q - 1) * err)))


def picp(y_true, y_p10, y_p90) -> float:
    """Prediction Interval Coverage Probability."""
    return float(np.mean((y_true >= y_p10) & (y_true <= y_p90)))


# ─────────────────────────────────────────────────────────────────────────────
# Module 4: Peak-Event Binary Classifier
# ─────────────────────────────────────────────────────────────────────────────
def train_peak_classifier(
    X_train, y_peak_train, X_val, y_peak_val
) -> lgb.LGBMClassifier:
    """
    Binary LightGBM classifier: predict whether hour will be in top-decile peak.
    Optimised for Recall (we do NOT want to miss a peak event).
    """
    clf = lgb.LGBMClassifier(**LGBM_CLF_PARAMS)
    clf.fit(
        X_train, y_peak_train,
        eval_set=[(X_val, y_peak_val)],
        callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(-1)]
    )

    proba = clf.predict_proba(X_val)[:, 1]
    # Find threshold maximising Recall >= 0.85
    best_thresh = 0.5
    best_recall = 0.0
    for t in np.arange(0.2, 0.8, 0.02):
        preds_t = (proba >= t).astype(int)
        if y_peak_val.sum() == 0:
            continue
        r = recall_score(y_peak_val, preds_t, zero_division=0)
        if r >= 0.85 and r > best_recall:
            best_recall = r
            best_thresh = t

    final_preds = (proba >= best_thresh).astype(int)
    prec = precision_score(y_peak_val, final_preds, zero_division=0)
    rec  = recall_score(y_peak_val, final_preds, zero_division=0)
    f1   = f1_score(y_peak_val, final_preds, zero_division=0)

    print(f"  Peak Classifier (thresh={best_thresh:.2f}): "
          f"Precision={prec:.3f}  Recall={rec:.3f}  F1={f1:.3f}")
    if rec < 0.85:
        print(f"  [WARNING] Recall {rec:.3f} < 0.85 target — lower threshold or add features")

    return clf, best_thresh, {"precision": prec, "recall": rec, "f1": f1}


# ─────────────────────────────────────────────────────────────────────────────
# Full training pipeline
# ─────────────────────────────────────────────────────────────────────────────
def run_training(feature_path: Path = Path("data/feature_matrix.parquet")) -> dict:
    print("\n" + "=" * 60)
    print("  MODULE 3 & 4: MODEL TRAINING PIPELINE")
    print("=" * 60)

    # ── Load feature matrix ──────────────────────────────────────────
    print("\n[1] Loading feature matrix...")
    df = pd.read_parquet(feature_path)
    available_features = [c for c in FEATURE_COLS if c in df.columns]
    print(f"  Shape: {df.shape} | Features used: {len(available_features)}")

    # ── Chronological split ──────────────────────────────────────────
    print("\n[2] Chronological train/val split (85%/15%)...")
    train_df, val_df = chronological_split(df, val_fraction=0.15)

    X_train = train_df[available_features]
    X_val   = val_df[available_features]

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    all_metrics = {}
    all_models  = {}

    # ── Baselines ────────────────────────────────────────────────────
    print("\n[3] Training baseline models...")
    for horizon in HORIZONS:
        label = f"h{horizon}"
        y_val_h = build_horizon_target(val_df, horizon=0)["load_mw"] if False else val_df["load_mw"]
        # Seasonal-Naïve
        naive_preds = val_df["load_lag_168h"].values
        naive_mape  = mean_absolute_percentage_error(val_df["load_mw"], naive_preds) * 100
        naive_rmse  = np.sqrt(mean_squared_error(val_df["load_mw"], naive_preds))
        print(f"  Seasonal-Naive ({label}): MAPE={naive_mape:.2f}%  RMSE={naive_rmse:.1f} MW")
        all_metrics[f"naive_{label}"] = {"mape": naive_mape, "rmse": naive_rmse}

        # Ridge
        ridge_model, ridge_preds = train_ridge_baseline(
            X_train, train_df["load_mw"],
            X_val,   val_df["load_mw"],
            label=label
        )
        ridge_mape = mean_absolute_percentage_error(val_df["load_mw"], ridge_preds) * 100
        ridge_rmse = np.sqrt(mean_squared_error(val_df["load_mw"], ridge_preds))
        all_metrics[f"ridge_{label}"] = {"mape": ridge_mape, "rmse": ridge_rmse}
        joblib.dump(ridge_model, MODELS_DIR / f"ridge_{label}.pkl")

    # ── LightGBM Quantile Models ──────────────────────────────────────
    print("\n[4] Training LightGBM Quantile Models (P10/P50/P90 x 24h/168h)...")
    quantile_preds = {}

    for horizon in HORIZONS:
        label = f"h{horizon}"
        # Build shifted target for this horizon
        y_train_h = train_df["load_mw"].shift(-horizon).dropna()
        X_train_h = X_train.iloc[:len(y_train_h)]

        y_val_h   = val_df["load_mw"]   # For current-step validation
        quantile_preds[label] = {}

        for q in QUANTILES:
            q_label = f"q{int(q*100)}"
            model_name = f"lgbm_{q_label}_{label}"
            print(f"\n  Training {model_name}...")

            model = train_quantile_model(
                X_train_h, y_train_h,
                X_val,     y_val_h,
                quantile=q, horizon=horizon, label=label
            )
            preds = model.predict(X_val)
            quantile_preds[label][q_label] = preds

            # Compute pinball loss
            pb = pinball_loss(y_val_h.values, preds, q)
            all_metrics[model_name] = {
                "pinball": pb,
                "mape":   mean_absolute_percentage_error(y_val_h, preds) * 100,
                "rmse":   np.sqrt(mean_squared_error(y_val_h, preds)),
            }

            # Save model
            joblib.dump(model, MODELS_DIR / f"{model_name}.pkl")
            all_models[model_name] = model

        # PICP for this horizon
        p10 = quantile_preds[label]["q10"]
        p90 = quantile_preds[label]["q90"]
        coverage = picp(y_val_h.values, p10, p90)
        all_metrics[f"picp_{label}"] = {"picp": coverage}
        print(f"\n  PICP ({label}): {coverage*100:.1f}% (target: ~80%)")

    # ── Module 4: Peak Classifier ─────────────────────────────────────
    print("\n[5] Training Peak-Event Binary Classifier (Module 4)...")
    y_peak_train = train_df["y_peak"]
    y_peak_val   = val_df["y_peak"]

    clf, best_thresh, clf_metrics = train_peak_classifier(
        X_train, y_peak_train, X_val, y_peak_val
    )
    joblib.dump({"model": clf, "threshold": best_thresh}, MODELS_DIR / "lgbm_peak_classifier.pkl")
    all_metrics["peak_classifier"] = clf_metrics
    all_models["peak_classifier"] = clf

    # ── Save predictions output CSV ───────────────────────────────────
    print("\n[6] Saving prediction outputs...")
    out_df = val_df[["load_mw", "y_peak", "temp_c"]].copy()
    out_df.columns = ["actual_mw", "actual_peak", "temp_c"]

    for horizon in HORIZONS:
        label = f"h{horizon}"
        for q_label in ["q10", "q50", "q90"]:
            if label in quantile_preds and q_label in quantile_preds[label]:
                out_df[f"pred_{q_label}_{label}"] = quantile_preds[label][q_label]

    # Peak classifier predictions
    peak_proba = clf.predict_proba(X_val)[:, 1]
    out_df["pred_peak_proba"]  = peak_proba
    out_df["pred_peak_flag"]   = (peak_proba >= best_thresh).astype(int)

    out_df.to_csv(OUTPUTS_DIR / "predictions_with_bands.csv")
    print(f"  Saved -> outputs/predictions_with_bands.csv ({len(out_df):,} rows)")

    # ── Metrics summary CSV ───────────────────────────────────────────
    metrics_df = pd.DataFrame(all_metrics).T
    metrics_df.to_csv(OUTPUTS_DIR / "metrics_summary.csv")
    print(f"  Saved -> outputs/metrics_summary.csv")

    # ── Feature importance ────────────────────────────────────────────
    _save_feature_importance(all_models, available_features)

    print("\n  Models saved:")
    for f in sorted(MODELS_DIR.glob("*.pkl")):
        print(f"    {f.name}  ({f.stat().st_size/1024:.1f} KB)")

    return all_metrics, all_models, out_df


def _save_feature_importance(models: dict, feature_names: list):
    """Save feature importance plot for P50 24h model."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        model_key = "lgbm_q50_h24"
        if model_key not in models:
            return

        model = models[model_key]
        importances = model.feature_importances_
        indices = np.argsort(importances)[-20:]

        fig, ax = plt.subplots(figsize=(10, 7))
        ax.barh(range(len(indices)),
                importances[indices],
                color="#2ecc71", edgecolor="white", alpha=0.85)
        ax.set_yticks(range(len(indices)))
        ax.set_yticklabels([feature_names[i] for i in indices], fontsize=9)
        ax.set_xlabel("Feature Importance (Gain)")
        ax.set_title("Top 20 Features — LightGBM P50 (24h Day-Ahead)", fontweight="bold")
        ax.grid(True, axis="x", alpha=0.3)
        plt.tight_layout()
        plt.savefig(OUTPUTS_DIR / "feature_importance.png", dpi=150, bbox_inches="tight")
        plt.close()
        print(f"  Saved -> outputs/feature_importance.png")
    except Exception as e:
        print(f"  [WARNING] Could not save feature importance plot: {e}")


if __name__ == "__main__":
    metrics, models, preds = run_training()
    print("\n\nFinal Metrics Summary:")
    print(pd.DataFrame(metrics).T.round(3).to_string())
