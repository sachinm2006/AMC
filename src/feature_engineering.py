"""
Module 2: Advanced Feature Engineering Pipeline
===============================================
Builds the full feature matrix for the Delhi DISCOM forecasting system:

  1. Thermal inertia features  — CDH, Heat-Index, 24h/48h/72h rolling means
  2. Cyclical time encodings   — sin/cos for hour, day-of-week, month
  3. Indian festival flags     — Diwali, Eid, Holi + pre/post windows
  4. Delhi event flags         — odd-even, lockdown
  5. Lag features              — 24h, 48h, 168h historical loads
  6. Annual linear trend term  — captures ~4% YoY load growth
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Indian festival dates (expand as needed)
# ─────────────────────────────────────────────────────────────────────────────
DIWALI_DATES = ["2021-11-04", "2022-10-24", "2023-11-12"]
EID_AL_FITR  = ["2021-05-13", "2022-05-02", "2023-04-21"]
EID_AL_ADHA  = ["2021-07-20", "2022-07-09", "2023-06-28"]
HOLI_DATES   = ["2021-03-29", "2022-03-18", "2023-03-08"]
REPUBLIC_DAY = ["2021-01-26", "2022-01-26", "2023-01-26"]
INDEPENDENCE  = ["2021-08-15", "2022-08-15", "2023-08-15"]
CHRISTMAS    = ["2021-12-25", "2022-12-25", "2023-12-25"]

# Delhi odd-even scheme approximate periods
ODD_EVEN_PERIODS = [
    ("2021-11-01", "2021-11-15"),
    ("2022-11-01", "2022-11-15"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Helper: windowed binary flag (day ± window_days)
# ─────────────────────────────────────────────────────────────────────────────
def _date_flag(idx: pd.DatetimeIndex, dates: list, window_days: int = 0) -> np.ndarray:
    """Return 1 if the timestamp falls within `window_days` of any date in `dates`."""
    flag = np.zeros(len(idx), dtype=int)
    for d in dates:
        center = pd.Timestamp(d).normalize()
        for offset in range(-window_days, window_days + 1):
            target = center + pd.Timedelta(days=offset)
            flag[idx.normalize() == target] = 1
    return flag


def _odd_even_flag(idx: pd.DatetimeIndex) -> np.ndarray:
    flag = np.zeros(len(idx), dtype=int)
    for start, end in ODD_EVEN_PERIODS:
        mask = (idx >= pd.Timestamp(start, tz=idx.tz)) & \
               (idx <= pd.Timestamp(end,   tz=idx.tz))
        flag[mask] = 1
    return flag


# ─────────────────────────────────────────────────────────────────────────────
# 1. Thermal Inertia Features
# ─────────────────────────────────────────────────────────────────────────────
def add_thermal_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    CDH = Cooling Degree Hours (above 24°C comfort baseline).
    Heat-Index using simplified Steadman formula.
    Rolling 24h / 48h / 72h mean temperatures (thermal inertia of buildings).
    """
    T = df["temp_c"]
    H = df.get("humidity", pd.Series(60, index=df.index))

    # Cooling Degree Hours
    df["CDH"] = (T - 24).clip(lower=0)

    # Simplified Heat Index (°C) — Steadman approximation
    df["heat_index"] = (
        -8.78469475556
        + 1.61139411   * T
        + 2.33854883889 * H
        - 0.14611605   * T * H
        - 0.012308094  * T ** 2
        - 0.016424828  * H ** 2
        + 0.002211732  * T ** 2 * H
        + 0.00072546   * T * H ** 2
        - 0.000003582  * T ** 2 * H ** 2
    ).clip(lower=T)   # Can't be cooler than actual temperature

    # Rolling thermal inertia (multi-day heat absorption)
    for window in [24, 48, 72]:
        df[f"rolling_temp_{window}h"] = T.rolling(window, min_periods=max(1, window // 4)).mean()

    # Temperature vs yesterday same hour (useful for ramp detection)
    df["temp_delta_24h"] = T - T.shift(24)

    return df


# ─────────────────────────────────────────────────────────────────────────────
# 2. Cyclical Time Encodings
# ─────────────────────────────────────────────────────────────────────────────
def add_cyclical_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sin/cos encodings prevent model from treating 23→0 as a large discontinuity.
    """
    idx = df.index

    # Hour of day (24-cycle)
    df["hour_sin"] = np.sin(2 * np.pi * idx.hour / 24)
    df["hour_cos"] = np.cos(2 * np.pi * idx.hour / 24)

    # Day of week (7-cycle)
    df["dow_sin"]  = np.sin(2 * np.pi * idx.day_of_week / 7)
    df["dow_cos"]  = np.cos(2 * np.pi * idx.day_of_week / 7)

    # Month (12-cycle)
    df["month_sin"] = np.sin(2 * np.pi * idx.month / 12)
    df["month_cos"] = np.cos(2 * np.pi * idx.month / 12)

    # Day of year (365-cycle — captures annual seasonality)
    df["doy_sin"] = np.sin(2 * np.pi * idx.day_of_year / 365)
    df["doy_cos"] = np.cos(2 * np.pi * idx.day_of_year / 365)

    # Raw calendar (non-cyclical, as extra signals)
    df["hour"]        = idx.hour
    df["day_of_week"] = idx.day_of_week
    df["month"]       = idx.month
    df["is_weekend"]  = (idx.day_of_week >= 5).astype(int)

    return df


# ─────────────────────────────────────────────────────────────────────────────
# 3. Indian Festival & Cultural Flags
# ─────────────────────────────────────────────────────────────────────────────
def add_festival_flags(df: pd.DataFrame) -> pd.DataFrame:
    """
    Binary flags for major Indian holidays + ±1 day window.
    Diwali has the highest load impact (heavy evening lighting load).
    """
    idx = df.index

    # Major festivals (with ±1 day window for pre/post effect)
    df["is_diwali"]      = _date_flag(idx, DIWALI_DATES,  window_days=1)
    df["is_eid"]         = _date_flag(idx, EID_AL_FITR + EID_AL_ADHA, window_days=1)
    df["is_holi"]        = _date_flag(idx, HOLI_DATES,    window_days=0)
    df["is_republic_day"]= _date_flag(idx, REPUBLIC_DAY,  window_days=0)
    df["is_independence"]= _date_flag(idx, INDEPENDENCE,  window_days=0)
    df["is_christmas"]   = _date_flag(idx, CHRISTMAS,     window_days=0)

    # Composite "major festival" flag (highest weight events)
    df["is_major_festival"] = ((df["is_diwali"] == 1) | (df["is_eid"] == 1)).astype(int)

    return df


# ─────────────────────────────────────────────────────────────────────────────
# 4. Delhi-Specific Event Flags
# ─────────────────────────────────────────────────────────────────────────────
def add_delhi_event_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Odd-even traffic scheme, lockdown flags (reduce commercial/industrial load)."""
    idx = df.index
    df["odd_even_flag"] = _odd_even_flag(idx)

    # COVID lockdown (approximate)
    lockdown_ranges = [
        ("2021-01-01", "2021-02-28"),  # 2nd wave prep
        ("2021-04-19", "2021-05-31"),  # Delhi lockdown
    ]
    df["lockdown_flag"] = 0
    for start, end in lockdown_ranges:
        mask = (idx >= pd.Timestamp(start, tz=idx.tz)) & \
               (idx <= pd.Timestamp(end,   tz=idx.tz))
        df.loc[mask, "lockdown_flag"] = 1

    return df


# ─────────────────────────────────────────────────────────────────────────────
# 5. Load Lag Features
# ─────────────────────────────────────────────────────────────────────────────
def add_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Lag historical load values:
      - 24h  : same hour yesterday
      - 48h  : same hour 2 days ago
      - 168h : same hour last week (Seasonal-Naïve reference)
    Also add rolling means over last 24h and 48h.
    """
    load = df["load_mw"]

    for lag in [24, 48, 168]:
        df[f"load_lag_{lag}h"] = load.shift(lag)

    # Rolling mean of last 24h and 48h actual load (trend context)
    df["load_rolling_mean_24h"] = load.shift(1).rolling(24, min_periods=12).mean()
    df["load_rolling_mean_48h"] = load.shift(1).rolling(48, min_periods=24).mean()

    # Load change from previous hour (ramp rate)
    df["load_delta_1h"]  = load.shift(1) - load.shift(2)
    df["load_delta_24h"] = load.shift(1) - load.shift(25)

    return df


# ─────────────────────────────────────────────────────────────────────────────
# 6. Annual Linear Trend
# ─────────────────────────────────────────────────────────────────────────────
def add_trend(df: pd.DataFrame) -> pd.DataFrame:
    """
    Linear trend term: captures Delhi's underlying ~4% per-year load growth.
    Units: fractional years from start of dataset.
    """
    t0 = df.index.min()
    df["trend_years"] = (df.index - t0).total_seconds() / (3600 * 24 * 365.25)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 7. Peak Classification Target
# ─────────────────────────────────────────────────────────────────────────────
def add_peak_target(df: pd.DataFrame, percentile: float = 0.90) -> pd.DataFrame:
    """
    Binary peak flag: 1 if load_mw >= 90th percentile of historical load.
    This is the target for the dedicated peak-event classifier.
    """
    threshold = df["load_mw"].quantile(percentile)
    df["y_peak"]          = (df["load_mw"] >= threshold).astype(int)
    df["peak_threshold_mw"] = threshold
    print(f"  → Peak threshold ({int(percentile*100)}th pct): {threshold:.1f} MW "
          f"| Peak hours: {df['y_peak'].sum()} / {len(df)} ({df['y_peak'].mean()*100:.1f}%)")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────
FEATURE_COLS = [
    # Thermal
    "CDH", "heat_index",
    "rolling_temp_24h", "rolling_temp_48h", "rolling_temp_72h",
    "temp_delta_24h",
    # Cyclical time
    "hour_sin", "hour_cos", "dow_sin", "dow_cos",
    "month_sin", "month_cos", "doy_sin", "doy_cos",
    "hour", "day_of_week", "month", "is_weekend",
    # Festivals & events
    "is_diwali", "is_eid", "is_holi",
    "is_republic_day", "is_independence", "is_christmas",
    "is_major_festival", "odd_even_flag", "lockdown_flag",
    # Lags
    "load_lag_24h", "load_lag_48h", "load_lag_168h",
    "load_rolling_mean_24h", "load_rolling_mean_48h",
    "load_delta_1h", "load_delta_24h",
    # Trend
    "trend_years",
    # Raw climate
    "temp_c", "humidity",
]


def build_feature_matrix(df: pd.DataFrame, dropna: bool = True) -> pd.DataFrame:
    """
    Full pipeline: raw cleaned DataFrame → feature matrix ready for ML.
    Returns DataFrame with feature columns + target columns.
    """
    print("\n🔧 [Module 2] Feature Engineering Pipeline")
    print("─" * 55)

    print("1️⃣  Thermal inertia features...")
    df = add_thermal_features(df)

    print("2️⃣  Cyclical time encodings...")
    df = add_cyclical_time_features(df)

    print("3️⃣  Indian festival flags...")
    df = add_festival_flags(df)

    print("4️⃣  Delhi event flags...")
    df = add_delhi_event_flags(df)

    print("5️⃣  Lag features...")
    df = add_lag_features(df)

    print("6️⃣  Annual linear trend...")
    df = add_trend(df)

    print("7️⃣  Peak classification target...")
    df = add_peak_target(df)

    # Drop rows where lag features created NaN (first 168h)
    if dropna:
        before = len(df)
        df = df.dropna(subset=["load_lag_168h"])
        print(f"  → Dropped {before - len(df)} warm-up rows (lag NaN period)")

    available_features = [c for c in FEATURE_COLS if c in df.columns]
    print(f"\n  ✅ Feature matrix ready | Shape: {df.shape}")
    print(f"     Features: {len(available_features)} columns")
    print(f"     Target  : load_mw (continuous) + y_peak (binary)")

    return df


if __name__ == "__main__":
    from preprocessing import run_preprocessing
    clean = run_preprocessing()
    feat  = build_feature_matrix(clean)
    # Save feature matrix
    out = Path("data/feature_matrix.parquet")
    feat.to_parquet(out)
    print(f"\n✅ Saved → {out}")
    print(feat[FEATURE_COLS].describe().round(2).T[["mean", "std", "min", "max"]])
