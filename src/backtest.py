"""
Module 5: Walk-Forward Backtesting Framework (Upgraded & Reconciled)
===================================================================
Implements strict rolling-origin walk-forward cross-validation:
  - 52 sequential test windows (1 per week of data)
  - Zero temporal data leakage (strictly historical data only)
  - Compares against BOTH Seasonal-Naive (168h) AND Yesterday-Naive (24h)
  - Cost-Derived Peak Threshold: p* = 1 / (1 + 3.5) ≈ 0.222
  - Conformalized Quantile Regression (CQR) for exact ~80% PICP coverage
  - Monotonicity enforcement (P10 <= P50 <= P90)
  - Pooled Metrics across all 52 folds (avoids sparse-event division noise)
"""

import warnings
warnings.filterwarnings("ignore")

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import pandas as pd
import joblib
import lightgbm as lgb
from sklearn.metrics import (
    mean_absolute_percentage_error, mean_squared_error,
    recall_score, precision_score, f1_score
)

from feature_engineering import FEATURE_COLS

N_SPLITS      = 52
MIN_TRAIN_PCT = 0.50
MODELS_DIR    = Path("models")
OUTPUTS_DIR   = Path("outputs")

# Decision threshold derived from asymmetric loss ratio: C_FP / (C_FP + C_FN) = 1 / (1 + 3.5)
COST_DERIVED_THRESHOLD = 1.0 / (1.0 + 3.5)  # ~0.2222

LGBM_PARAMS = {
    "objective":        "quantile",
    "num_leaves":       63,
    "learning_rate":    0.08,
    "n_estimators":     150,
    "min_child_samples": 20,
    "subsample":        0.85,
    "colsample_bytree": 0.80,
    "reg_alpha":        0.1,
    "reg_lambda":       0.1,
    "random_state":     42,
    "n_jobs":           -1,
    "verbose":          -1,
}

CLF_PARAMS = {
    "num_leaves":        31,
    "learning_rate":     0.08,
    "n_estimators":      120,
    "min_child_samples": 10,
    "scale_pos_weight":  8,
    "random_state":      42,
    "n_jobs":            -1,
    "verbose":           -1,
}

def rolling_origin_splits(n_total: int, n_splits: int = 52,
                           min_train_pct: float = 0.50,
                           test_window: int = 168):
    min_train = int(n_total * min_train_pct)
    test_total = n_total - min_train
    step = max(1, (test_total - test_window) // (n_splits - 1))

    for i in range(n_splits):
        test_start = min_train + i * step
        test_end   = test_start + test_window
        if test_end > n_total:
            break
        yield test_start, test_end

def evaluate_fold_cqr(X, y_load, y_peak,
                      train_end: int, test_start: int, test_end: int,
                      feature_cols: list) -> dict:
    X_tr   = X.iloc[:train_end]
    y_tr   = y_load.iloc[:train_end]
    yp_tr  = y_peak.iloc[:train_end]

    X_te   = X.iloc[test_start:test_end]
    y_te   = y_load.iloc[test_start:test_end].values
    yp_te  = y_peak.iloc[test_start:test_end].values

    if len(X_te) == 0 or len(X_tr) == 0:
        return {}

    fold_res = {}

    # 1. Dual Baselines
    # Seasonal-Naive (168h ago)
    naive_168 = X.iloc[test_start:test_end]["load_lag_168h"].values
    naive_168 = np.where(np.isnan(naive_168), np.nanmean(y_te), naive_168)
    fold_res["naive_168_mape"] = mean_absolute_percentage_error(y_te, naive_168) * 100

    # Yesterday-Naive (24h ago)
    naive_24 = X.iloc[test_start:test_end]["load_lag_24h"].values
    naive_24 = np.where(np.isnan(naive_24), np.nanmean(y_te), naive_24)
    fold_res["naive_24_mape"] = mean_absolute_percentage_error(y_te, naive_24) * 100

    # 2. LightGBM Quantile Models
    # Use last 10% of training data as rolling CQR calibration set
    calib_size = max(168, int(len(X_tr) * 0.10))
    X_train_fit = X_tr.iloc[:-calib_size]
    y_train_fit = y_tr.iloc[:-calib_size]
    X_calib     = X_tr.iloc[-calib_size:]
    y_calib     = y_tr.iloc[-calib_size:].values

    raw_preds_test  = {}
    raw_preds_calib = {}

    for q in [0.10, 0.50, 0.90]:
        qp = dict(LGBM_PARAMS)
        qp["alpha"] = q
        m = lgb.LGBMRegressor(**qp)
        m.fit(X_train_fit, y_train_fit,
              eval_set=[(X_calib, y_calib)],
              callbacks=[lgb.early_stopping(20, verbose=False), lgb.log_evaluation(-1)])
        raw_preds_calib[q] = m.predict(X_calib)
        raw_preds_test[q]  = m.predict(X_te)

    # 3. Conformalized Quantile Regression (CQR) Adjustment
    # Non-conformity score E on calibration set
    calib_err = np.maximum(raw_preds_calib[0.10] - y_calib, y_calib - raw_preds_calib[0.90])
    cqr_adjustment = np.quantile(calib_err, 0.80)  # 80th percentile correction
    cqr_adjustment = max(0.0, cqr_adjustment)     # Widen if under-covered

    # Apply CQR & Monotonicity
    p10_adj = raw_preds_test[0.10] - cqr_adjustment
    p50_adj = raw_preds_test[0.50]
    p90_adj = raw_preds_test[0.90] + cqr_adjustment

    # Enforce P10 <= P50 <= P90
    p10_final = np.minimum(p10_adj, p50_adj)
    p90_final = np.maximum(p90_adj, p50_adj)

    fold_res["mape_p50"]    = mean_absolute_percentage_error(y_te, p50_adj) * 100
    fold_res["rmse_p50"]    = float(np.sqrt(mean_squared_error(y_te, p50_adj)))
    fold_res["picp_raw"]    = float(np.mean((y_te >= raw_preds_test[0.10]) & (y_te <= raw_preds_test[0.90])))
    fold_res["picp_cqr"]    = float(np.mean((y_te >= p10_final) & (y_te <= p90_final)))

    # Improvement over strong baselines
    fold_res["mape_imprv_seasonal_pct"] = (
        (fold_res["naive_168_mape"] - fold_res["mape_p50"]) / fold_res["naive_168_mape"] * 100
    )
    fold_res["mape_imprv_yesterday_pct"] = (
        (fold_res["naive_24_mape"] - fold_res["mape_p50"]) / fold_res["naive_24_mape"] * 100
    )

    # 4. Peak Classifier with Cost-Derived Threshold (0.222)
    clf = lgb.LGBMClassifier(**CLF_PARAMS)
    clf.fit(X_train_fit, yp_tr.iloc[:-calib_size],
            eval_set=[(X_calib, yp_tr.iloc[-calib_size:])],
            callbacks=[lgb.early_stopping(20, verbose=False), lgb.log_evaluation(-1)])
    
    peak_proba_test = clf.predict_proba(X_te)[:, 1]
    peak_preds_cost = (peak_proba_test >= COST_DERIVED_THRESHOLD).astype(int)

    # Return raw vectors for pooled evaluation
    return fold_res, {
        "y_true": y_te,
        "y_pred_p50": p50_adj,
        "y_pred_p10": p10_final,
        "y_pred_p90": p90_final,
        "yp_true": yp_te,
        "yp_proba": peak_proba_test,
        "yp_pred": peak_preds_cost
    }

def run_backtest(feature_path: Path = Path("data/feature_matrix.parquet")):
    print("\n" + "=" * 60)
    print("  MODULE 5: 52-WINDOW WALK-FORWARD BACKTEST (CQR + COST-OPTIMAL)")
    print("=" * 60)

    df = pd.read_parquet(feature_path)
    available = [c for c in FEATURE_COLS if c in df.columns]
    X      = df[available]
    y_load = df["load_mw"]
    y_peak = df["y_peak"]

    splits = list(rolling_origin_splits(len(df), n_splits=N_SPLITS, min_train_pct=MIN_TRAIN_PCT))
    print(f"  Executing {len(splits)} rolling folds...")

    fold_results = []
    pooled_y_true = []
    pooled_y_p50  = []
    pooled_yp_true = []
    pooled_yp_pred = []
    pooled_yp_proba = []

    for i, (test_start, test_end) in enumerate(splits):
        train_end = test_start
        if i % 10 == 0 or i == len(splits) - 1:
            print(f"  Fold {i+1:02d}/{len(splits)} | Train: 0->{train_end} | Test: {test_start}->{test_end}")

        res, vectors = evaluate_fold_cqr(X, y_load, y_peak, train_end, test_start, test_end, available)
        res["fold"] = i + 1
        fold_results.append(res)

        pooled_y_true.extend(vectors["y_true"])
        pooled_y_p50.extend(vectors["y_pred_p50"])
        pooled_yp_true.extend(vectors["yp_true"])
        pooled_yp_pred.extend(vectors["yp_pred"])
        pooled_yp_proba.extend(vectors["yp_proba"])

    results_df = pd.DataFrame(fold_results)

    # Pooled Metrics across all 52 weeks (statistically robust)
    pooled_y_true = np.array(pooled_y_true)
    pooled_y_p50  = np.array(pooled_y_p50)
    pooled_yp_true = np.array(pooled_yp_true)
    pooled_yp_pred = np.array(pooled_yp_pred)

    pooled_mape = mean_absolute_percentage_error(pooled_y_true, pooled_y_p50) * 100
    pooled_peak_recall = recall_score(pooled_yp_true, pooled_yp_pred, zero_division=0)
    pooled_peak_prec   = precision_score(pooled_yp_true, pooled_yp_pred, zero_division=0)
    pooled_peak_f1     = f1_score(pooled_yp_true, pooled_yp_pred, zero_division=0)

    # Reconciled numbers
    seasonal_naive_pooled = mean_absolute_percentage_error(pooled_y_true, df.loc[df.index[-len(pooled_y_true):], "load_lag_168h"].values) * 100
    yesterday_naive_pooled = mean_absolute_percentage_error(pooled_y_true, df.loc[df.index[-len(pooled_y_true):], "load_lag_24h"].values) * 100
    pooled_reduction = (seasonal_naive_pooled - pooled_mape) / seasonal_naive_pooled * 100
    mean_fold_reduction = results_df["mape_imprv_seasonal_pct"].mean()

    # Aggregate DataFrame
    agg = {}
    for col in results_df.columns:
        if col != "fold":
            agg[col] = {
                "mean": results_df[col].mean(),
                "std": results_df[col].std(),
                "min": results_df[col].min(),
                "max": results_df[col].max(),
            }
    agg_df = pd.DataFrame(agg).T.round(4)

    # Save
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(OUTPUTS_DIR / "walkforward_fold_results.csv", index=False)
    agg_df.to_csv(OUTPUTS_DIR / "walkforward_aggregate_metrics.csv")

    # Print Reconciled Benchmark Summary
    print("\n" + "=" * 65)
    print("  WALK-FORWARD BACKTEST — RECONCILED BENCHMARK SUMMARY")
    print("=" * 65)
    print(f"  • LightGBM P50 Pooled MAPE         : {pooled_mape:.2f}%")
    print(f"  • Seasonal-Naive Baseline (168h)   : {seasonal_naive_pooled:.2f}%")
    print(f"  • Yesterday-Naive Baseline (24h)    : {yesterday_naive_pooled:.2f}%")
    print(f"  • Headline Error Reduction (Pooled) : {pooled_reduction:.1f}%")
    print(f"  • Mean Per-Fold Reduction Ratio     : {mean_fold_reduction:.1f}% ± {results_df['mape_imprv_seasonal_pct'].std():.1f}%")
    print(f"  • CQR Interval Coverage (PICP)      : {results_df['picp_cqr'].mean()*100:.1f}% (Raw was {results_df['picp_raw'].mean()*100:.1f}%)")
    print(f"  • Pooled Peak Recall (Cost Thresh)  : {pooled_peak_recall*100:.1f}% (Target: > 85%)")
    print(f"  • Pooled Peak Precision             : {pooled_peak_prec*100:.1f}%")
    print(f"  • Pooled Peak F1-Score              : {pooled_peak_f1:.3f}")
    print("=" * 65)

    return results_df, agg_df

if __name__ == "__main__":
    run_backtest()
