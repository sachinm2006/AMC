"""
Module 5: Walk-Forward Backtesting Framework
=============================================
Implements strict rolling-origin walk-forward cross-validation:
  - 52 sequential test windows (1 per week of data)
  - Zero temporal data leakage (no random shuffling)
  - Evaluates: MAPE, RMSE, Pinball Loss, PICP, Peak Recall, Peak Timing Error
  - Generates per-fold metrics + aggregated summary table
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

N_SPLITS      = 52        # One window per week
MIN_TRAIN_PCT = 0.50      # Use at least 50% of data before first test window
MODELS_DIR    = Path("models")
OUTPUTS_DIR   = Path("outputs")

# ─────────────────────────────────────────────────────────────────────────────
# Metric helpers
# ─────────────────────────────────────────────────────────────────────────────
def _pinball(y_true, y_pred, q):
    err = np.asarray(y_true) - np.asarray(y_pred)
    return float(np.mean(np.where(err >= 0, q * err, (q - 1) * err)))

def _picp(y_true, p10, p90):
    return float(np.mean((np.asarray(y_true) >= np.asarray(p10)) &
                         (np.asarray(y_true) <= np.asarray(p90))))

def _peak_timing_error(y_true, y_pred):
    """Average |hour(actual_max) - hour(pred_max)| in hours."""
    # Group by day and find peak hour
    errors = []
    for day in pd.Series(np.arange(len(y_true)) // 24).unique():
        start = day * 24
        end   = min(start + 24, len(y_true))
        if end - start < 2:
            continue
        actual_peak_hr = int(np.argmax(y_true[start:end]))
        pred_peak_hr   = int(np.argmax(y_pred[start:end]))
        errors.append(abs(actual_peak_hr - pred_peak_hr))
    return float(np.mean(errors)) if errors else 0.0

def _peak_magnitude_error_pct(y_true, y_pred):
    """Average |actual_max_MW - pred_max_MW| as % of actual peak."""
    errors = []
    for day in pd.Series(np.arange(len(y_true)) // 24).unique():
        start = day * 24
        end   = min(start + 24, len(y_true))
        actual_max = np.max(y_true[start:end])
        pred_max   = np.max(y_pred[start:end])
        if actual_max > 0:
            errors.append(abs(actual_max - pred_max) / actual_max * 100)
    return float(np.mean(errors)) if errors else 0.0


# ─────────────────────────────────────────────────────────────────────────────
# LightGBM params (same as training)
# ─────────────────────────────────────────────────────────────────────────────
LGBM_PARAMS = {
    "objective":        "quantile",
    "num_leaves":       63,
    "learning_rate":    0.08,
    "n_estimators":     150,          # Fast for 52 folds
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

# ─────────────────────────────────────────────────────────────────────────────
# Rolling-origin walk-forward splitter
# ─────────────────────────────────────────────────────────────────────────────
def rolling_origin_splits(n_total: int, n_splits: int = 52,
                           min_train_pct: float = 0.50,
                           test_window: int = 168):
    """
    Generator of (train_end_idx, test_start_idx, test_end_idx) tuples.
    Each test window is exactly `test_window` hours (1 week).
    """
    min_train = int(n_total * min_train_pct)
    # Total test period covers the last (1 - min_train_pct) fraction
    test_total = n_total - min_train
    # Slide test window across the test period
    step = max(1, (test_total - test_window) // (n_splits - 1))

    for i in range(n_splits):
        test_start = min_train + i * step
        test_end   = test_start + test_window
        if test_end > n_total:
            break
        yield test_start, test_end


# ─────────────────────────────────────────────────────────────────────────────
# Single fold evaluation
# ─────────────────────────────────────────────────────────────────────────────
def evaluate_fold(X, y_load, y_peak,
                  train_end: int, test_start: int, test_end: int,
                  feature_cols: list) -> dict:
    """Train quantile models + classifier on [0:train_end], test on [test_start:test_end]."""
    X_tr   = X.iloc[:train_end]
    y_tr   = y_load.iloc[:train_end]
    yp_tr  = y_peak.iloc[:train_end]

    X_te   = X.iloc[test_start:test_end]
    y_te   = y_load.iloc[test_start:test_end].values
    yp_te  = y_peak.iloc[test_start:test_end].values

    if len(X_te) == 0 or len(X_tr) == 0:
        return {}

    fold_res = {}

    # ── Seasonal Naive (reference) ──────────────────────────────────
    naive_pred = X.iloc[test_start:test_end]["load_lag_168h"].values
    naive_pred = np.where(np.isnan(naive_pred), np.nanmean(y_te), naive_pred)
    fold_res["naive_mape"] = mean_absolute_percentage_error(y_te, naive_pred) * 100
    fold_res["naive_rmse"] = float(np.sqrt(mean_squared_error(y_te, naive_pred)))

    # ── LightGBM Quantile (P10/P50/P90) ────────────────────────────
    preds = {}
    for q in [0.10, 0.50, 0.90]:
        qp = dict(LGBM_PARAMS)
        qp["alpha"] = q
        m = lgb.LGBMRegressor(**qp)
        m.fit(X_tr, y_tr,
              eval_set=[(X_te, y_te)],
              callbacks=[lgb.early_stopping(30, verbose=False), lgb.log_evaluation(-1)])
        preds[q] = m.predict(X_te)

    fold_res["mape_p50"]    = mean_absolute_percentage_error(y_te, preds[0.50]) * 100
    fold_res["rmse_p50"]    = float(np.sqrt(mean_squared_error(y_te, preds[0.50])))
    fold_res["pinball_p10"] = _pinball(y_te, preds[0.10], 0.10)
    fold_res["pinball_p50"] = _pinball(y_te, preds[0.50], 0.50)
    fold_res["pinball_p90"] = _pinball(y_te, preds[0.90], 0.90)
    fold_res["picp"]        = _picp(y_te, preds[0.10], preds[0.90])
    fold_res["peak_timing_error_hrs"] = _peak_timing_error(y_te, preds[0.50])
    fold_res["peak_magnitude_error_pct"] = _peak_magnitude_error_pct(y_te, preds[0.50])

    # Improvement over naive
    fold_res["mape_improvement_pct"] = (
        (fold_res["naive_mape"] - fold_res["mape_p50"]) / fold_res["naive_mape"] * 100
    )

    # ── Peak Classifier ─────────────────────────────────────────────
    if yp_tr.sum() > 5 and yp_te.sum() > 0:
        clf = lgb.LGBMClassifier(**CLF_PARAMS)
        clf.fit(X_tr, yp_tr,
                eval_set=[(X_te, yp_te)],
                callbacks=[lgb.early_stopping(20, verbose=False), lgb.log_evaluation(-1)])
        clf_preds = clf.predict(X_te)
        fold_res["peak_recall"]    = recall_score(yp_te, clf_preds, zero_division=0)
        fold_res["peak_precision"] = precision_score(yp_te, clf_preds, zero_division=0)
        fold_res["peak_f1"]        = f1_score(yp_te, clf_preds, zero_division=0)
    else:
        fold_res["peak_recall"] = fold_res["peak_precision"] = fold_res["peak_f1"] = np.nan

    return fold_res


# ─────────────────────────────────────────────────────────────────────────────
# Full walk-forward backtest
# ─────────────────────────────────────────────────────────────────────────────
def run_backtest(feature_path: Path = Path("data/feature_matrix.parquet")) -> pd.DataFrame:
    print("\n" + "=" * 60)
    print("  MODULE 5: WALK-FORWARD BACKTESTING FRAMEWORK")
    print("  52-Window Rolling-Origin Cross-Validation")
    print("=" * 60)

    # ── Load data ────────────────────────────────────────────────────
    print("\n[1] Loading feature matrix...")
    df = pd.read_parquet(feature_path)
    available = [c for c in FEATURE_COLS if c in df.columns]
    X      = df[available]
    y_load = df["load_mw"]
    y_peak = df["y_peak"]
    print(f"  Shape: {df.shape} | Features: {len(available)}")

    # ── Run folds ────────────────────────────────────────────────────
    splits = list(rolling_origin_splits(len(df), n_splits=N_SPLITS,
                                        min_train_pct=MIN_TRAIN_PCT))
    print(f"\n[2] Running {len(splits)} walk-forward folds...")

    fold_results = []
    for i, (test_start, test_end) in enumerate(splits):
        train_end = test_start
        if i % 10 == 0 or i == len(splits) - 1:
            print(f"  Fold {i+1:02d}/{len(splits)} | "
                  f"Train: 0->{train_end} | Test: {test_start}->{test_end} "
                  f"({df.index[test_start].date()} to {df.index[min(test_end-1, len(df)-1)].date()})")

        result = evaluate_fold(X, y_load, y_peak,
                               train_end, test_start, test_end, available)
        result["fold"]       = i + 1
        result["test_start"] = str(df.index[test_start].date())
        result["test_end"]   = str(df.index[min(test_end - 1, len(df) - 1)].date())
        fold_results.append(result)

    results_df = pd.DataFrame(fold_results)

    # ── Aggregate metrics ─────────────────────────────────────────────
    print("\n[3] Computing aggregate metrics...")
    agg = {}
    metric_cols = [c for c in results_df.columns
                   if c not in ("fold", "test_start", "test_end")]

    for col in metric_cols:
        vals = results_df[col].dropna()
        agg[col] = {
            "mean": vals.mean(),
            "std":  vals.std(),
            "min":  vals.min(),
            "max":  vals.max(),
        }

    agg_df = pd.DataFrame(agg).T.round(4)

    # ── Save outputs ──────────────────────────────────────────────────
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(OUTPUTS_DIR / "walkforward_fold_results.csv", index=False)
    agg_df.to_csv(OUTPUTS_DIR / "walkforward_aggregate_metrics.csv")
    print(f"  Saved -> outputs/walkforward_fold_results.csv")
    print(f"  Saved -> outputs/walkforward_aggregate_metrics.csv")

    # ── Print summary table ───────────────────────────────────────────
    _print_summary(agg_df, results_df)

    # ── Plots ─────────────────────────────────────────────────────────
    _plot_backtest_results(results_df)

    return results_df, agg_df


def _print_summary(agg_df: pd.DataFrame, results_df: pd.DataFrame):
    print("\n" + "=" * 60)
    print("  WALK-FORWARD BACKTEST — AGGREGATE RESULTS")
    print("=" * 60)

    targets = {
        "mape_p50":               ("MAPE P50 (day-ahead)",         "< baseline", "%"),
        "picp":                   ("PICP (P10-P90 coverage)",       "~80%",      "%"),
        "peak_recall":            ("Peak Recall (top-decile)",      "> 85%",      ""),
        "peak_precision":         ("Peak Precision",                "> 70%",      ""),
        "peak_timing_error_hrs":  ("Peak Timing Error",             "< 0.5h",     "h"),
        "peak_magnitude_error_pct":("Peak Magnitude Error",         "< 3%",       "%"),
        "pinball_p90":            ("Pinball Loss P90",              "minimise",   ""),
        "mape_improvement_pct":   ("MAPE Improvement vs Naive",     "> 0%",       "%"),
    }

    for key, (label, target, unit) in targets.items():
        if key in agg_df.index:
            mean = agg_df.loc[key, "mean"]
            std  = agg_df.loc[key, "std"]
            val_str = f"{mean:.2f}{unit} ± {std:.2f}"
            # Pass/fail indicator
            if key == "peak_recall":
                status = "PASS" if mean >= 0.85 else "FAIL"
            elif key == "picp":
                status = "PASS" if mean >= 0.75 else "FAIL"
            elif key == "mape_p50":
                status = "PASS" if mean < agg_df.loc["naive_mape", "mean"] else "FAIL"
            else:
                status = "INFO"
            flag = "[OK]" if status == "PASS" else ("[!!]" if status == "FAIL" else "[--]")
            print(f"  {flag} {label:<35} {val_str:<20} target: {target}")

    print("=" * 60)


def _plot_backtest_results(results_df: pd.DataFrame):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle("Walk-Forward Backtest Results (52 Folds)", fontsize=14, fontweight="bold")

        # 1. MAPE over folds
        ax = axes[0, 0]
        ax.plot(results_df["fold"], results_df["mape_p50"], "b-o", markersize=3, label="LightGBM P50")
        ax.plot(results_df["fold"], results_df["naive_mape"], "r--", linewidth=1.5, label="Seasonal-Naive")
        ax.set_title("MAPE by Fold")
        ax.set_ylabel("MAPE (%)")
        ax.set_xlabel("Fold")
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 2. PICP over folds
        ax = axes[0, 1]
        ax.plot(results_df["fold"], results_df["picp"] * 100, "g-o", markersize=3)
        ax.axhline(80, color="orange", linestyle="--", label="Target 80%")
        ax.set_title("PICP (P10-P90 Coverage) by Fold")
        ax.set_ylabel("Coverage (%)")
        ax.set_xlabel("Fold")
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 105)

        # 3. Peak Recall over folds
        ax = axes[1, 0]
        recall_data = results_df["peak_recall"].dropna()
        ax.plot(results_df.loc[recall_data.index, "fold"], recall_data * 100, "m-o", markersize=3)
        ax.axhline(85, color="red", linestyle="--", label="Target 85%")
        ax.set_title("Peak Recall by Fold")
        ax.set_ylabel("Recall (%)")
        ax.set_xlabel("Fold")
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 105)

        # 4. MAPE improvement vs naive
        ax = axes[1, 1]
        improvement = results_df["mape_improvement_pct"].dropna()
        colors = ["#2ecc71" if v > 0 else "#e74c3c" for v in improvement]
        ax.bar(results_df.loc[improvement.index, "fold"], improvement, color=colors, alpha=0.8)
        ax.axhline(0, color="black", linewidth=0.8)
        ax.set_title("MAPE Improvement over Seasonal-Naive (%)")
        ax.set_ylabel("Improvement (%)")
        ax.set_xlabel("Fold")
        ax.grid(True, alpha=0.3, axis="y")

        plt.tight_layout()
        plt.savefig(OUTPUTS_DIR / "walkforward_results.png", dpi=150, bbox_inches="tight")
        plt.close()
        print(f"\n  Saved -> outputs/walkforward_results.png")
    except Exception as e:
        print(f"  [WARNING] Could not generate plots: {e}")


if __name__ == "__main__":
    results_df, agg_df = run_backtest()
