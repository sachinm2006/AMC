"""
Module 1: Data Preprocessing & Quality Pipeline
================================================
Cleans raw Delhi SLDC hourly load + weather data:
  1. Loads raw CSV / parquet
  2. Ensures continuous hourly DatetimeIndex (Asia/Kolkata)
  3. Detects & imputes missing meter readings (linear spline)
  4. Clips severe grid outage outliers (Z-score threshold)
  5. Saves clean parquet checkpoint
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from pathlib import Path
from scipy.interpolate import CubicSpline

# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────
RAW_CSV    = Path("data/raw/delhi_load_raw.csv")
CLEAN_OUT  = Path("data/clean_delhi_load.parquet")

# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Load & parse timestamps
# ─────────────────────────────────────────────────────────────────────────────
def load_raw(path: Path = RAW_CSV) -> pd.DataFrame:
    """Load raw CSV, parse timestamps, set as DatetimeIndex."""
    df = pd.read_csv(path, parse_dates=["timestamp"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=False)

    # Localize if naive (assume IST)
    if df["timestamp"].dt.tz is None:
        df["timestamp"] = df["timestamp"].dt.tz_localize("Asia/Kolkata", ambiguous="infer", nonexistent="shift_forward")
    else:
        df["timestamp"] = df["timestamp"].dt.tz_convert("Asia/Kolkata")

    df = df.sort_values("timestamp").set_index("timestamp")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Enforce continuous hourly index (no gaps, no duplicate hours)
# ─────────────────────────────────────────────────────────────────────────────
def enforce_continuous_index(df: pd.DataFrame) -> pd.DataFrame:
    """
    Reindex to a complete hourly DatetimeIndex.
    Missing rows introduced here will have NaN load → imputed next.
    Duplicate timestamps (DST issues) → keep last.
    """
    df = df[~df.index.duplicated(keep="last")]

    full_idx = pd.date_range(
        start=df.index.min(),
        end=df.index.max(),
        freq="h",
        tz="Asia/Kolkata"
    )
    df = df.reindex(full_idx)
    missing_pct = df["load_mw"].isna().mean() * 100
    print(f"  → Reindexed to {len(df)} hourly rows | {missing_pct:.2f}% missing load")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Clip grid outage outliers BEFORE imputation
# ─────────────────────────────────────────────────────────────────────────────
def clip_outage_outliers(df: pd.DataFrame, z_thresh: float = 4.0) -> pd.DataFrame:
    """
    Identify hours where load deviates > z_thresh standard deviations
    from a 7-day rolling median — flag as outage → set to NaN for imputation.
    """
    rolling_med = df["load_mw"].rolling(window=168, center=True, min_periods=24).median()
    rolling_std = df["load_mw"].rolling(window=168, center=True, min_periods=24).std()

    z_score = (df["load_mw"] - rolling_med).abs() / (rolling_std + 1e-6)
    outage_mask = z_score > z_thresh

    n_clipped = outage_mask.sum()
    df.loc[outage_mask, "load_mw"] = np.nan
    print(f"  → Clipped {n_clipped} outage outliers (Z > {z_thresh}) → set to NaN")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Impute missing load with cubic spline (gaps up to 6h) + linear fill
# ─────────────────────────────────────────────────────────────────────────────
def impute_missing_load(df: pd.DataFrame, max_gap_hours: int = 6) -> pd.DataFrame:
    """
    For short gaps (≤ max_gap_hours): cubic spline interpolation.
    For longer gaps: linear interpolation (safe fallback).
    Temperature / humidity: simple linear fill.
    """
    # Identify run-lengths of NaN blocks in load
    is_nan = df["load_mw"].isna()
    nan_groups = (is_nan != is_nan.shift()).cumsum()

    for group_id, grp in df[is_nan].groupby(nan_groups[is_nan]):
        gap_len = len(grp)
        start_i = df.index.get_loc(grp.index[0])
        end_i   = df.index.get_loc(grp.index[-1])

        # Grab surrounding known points (5 either side for spline)
        ctx_start = max(0, start_i - 5)
        ctx_end   = min(len(df) - 1, end_i + 5)
        ctx = df.iloc[ctx_start:ctx_end + 1]
        known = ctx[~ctx["load_mw"].isna()]

        if len(known) >= 2 and gap_len <= max_gap_hours:
            x_known = known.index.astype(np.int64)
            y_known = known["load_mw"].values
            cs = CubicSpline(x_known, y_known, extrapolate=False)
            x_fill = grp.index.astype(np.int64)
            filled = cs(x_fill)
            df.loc[grp.index, "load_mw"] = np.clip(filled, 1000, 9500)
        else:
            # Long gap: linear interpolation
            df["load_mw"] = df["load_mw"].interpolate(method="linear")

    # Remaining NaN (edges): forward/backward fill
    df["load_mw"] = df["load_mw"].ffill().bfill()

    # Temperature / humidity: simple linear
    for col in ["temp_c", "humidity"]:
        if col in df.columns:
            df[col] = df[col].interpolate(method="linear").ffill().bfill()

    nan_remaining = df["load_mw"].isna().sum()
    print(f"  → Imputation complete | Remaining NaN in load_mw: {nan_remaining}")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Step 5 — Validate & save
# ─────────────────────────────────────────────────────────────────────────────
def validate(df: pd.DataFrame) -> None:
    assert df["load_mw"].isna().sum() == 0, "NaN values remain in load_mw!"
    assert df.index.is_monotonic_increasing,  "Index is not monotonically increasing!"
    assert df.index.is_unique,                "Duplicate timestamps found!"
    freq = pd.infer_freq(df.index[:200])
    assert freq in ("h", "H"),                f"Non-hourly frequency detected: {freq}"
    print(f"  ✅ Validation passed | Shape: {df.shape} | Date range: {df.index.min()} → {df.index.max()}")


def save_clean(df: pd.DataFrame, path: Path = CLEAN_OUT) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)
    print(f"  ✅ Saved clean data → {path}")


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────
def run_preprocessing(raw_path: Path = RAW_CSV, out_path: Path = CLEAN_OUT) -> pd.DataFrame:
    print("\n📦 [Module 1] Data Preprocessing & Quality Pipeline")
    print("─" * 55)

    print("1️⃣  Loading raw data...")
    df = load_raw(raw_path)
    print(f"     Raw shape: {df.shape}")

    print("2️⃣  Enforcing continuous hourly index...")
    df = enforce_continuous_index(df)

    print("3️⃣  Clipping grid outage outliers...")
    df = clip_outage_outliers(df)

    print("4️⃣  Imputing missing meter readings...")
    df = impute_missing_load(df)

    print("5️⃣  Validating...")
    validate(df)

    save_clean(df, out_path)
    return df


if __name__ == "__main__":
    df = run_preprocessing()
    print("\nSample output:")
    print(df[["load_mw", "temp_c", "humidity"]].describe().round(2))
