"""
Module 2: Advanced Feature Engineering Pipeline (Upgraded with P0 Model Improvements)
=====================================================================================
Builds the full production feature matrix for the Delhi DISCOM forecasting system:

  1. Thermal inertia features  - CDH, Heat-Index, 24h/48h/72h rolling means
  2. Heatwave-Onset Detector   - Thermal slope, 2nd-derivative acceleration, onset flag (P0)
  3. Monsoon / Rain Regimes    - Rain probability, evening storm flag, cooling risk (P0)
  4. Cyclical time encodings   - sin/cos for hour, day-of-week, month, day-of-year
  5. Indian festival flags     - Diwali, Eid, Holi + post-festival recovery window
  6. Delhi event & policy      - odd-even, lockdown, exam calendar proxy
  7. Lag & volatility features - 24h, 48h, 168h lags, 12h rolling load volatility
  8. Annual linear trend term  - captures underlying ~4% YoY load growth
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Indian festival dates
# ─────────────────────────────────────────────────────────────────────────────
DIWALI_DATES = ["2021-11-04", "2022-10-24", "2023-11-12"]
EID_AL_FITR  = ["2021-05-13", "2022-05-02", "2023-04-21"]
EID_AL_ADHA  = ["2021-07-20", "2022-07-09", "2023-06-28"]
HOLI_DATES   = ["2021-03-29", "2022-03-18", "2023-03-08"]
REPUBLIC_DAY = ["2021-01-26", "2022-01-26", "2023-01-26"]
INDEPENDENCE = ["2021-08-15", "2022-08-15", "2023-08-15"]
CHRISTMAS    = ["2021-12-25", "2022-12-25", "2023-12-25"]

ODD_EVEN_PERIODS = [
    ("2021-11-01", "2021-11-15"),
    ("2022-11-01", "2022-11-15"),
]

def _date_flag(idx: pd.DatetimeIndex, dates: list, window_days: int = 0) -> np.ndarray:
    """Return 1 if timestamp falls within +/- window_days of any date."""
    flag = np.zeros(len(idx), dtype=int)
    for d in dates:
        center = pd.Timestamp(d).normalize()
        for offset in range(-window_days, window_days + 1):
            target = center + pd.Timedelta(days=offset)
            flag[idx.normalize() == target] = 1
    return flag

def _date_flag_forward(idx: pd.DatetimeIndex, dates: list, forward_days: int = 3) -> np.ndarray:
    """Return 1 if timestamp falls 1 to forward_days AFTER any date in dates."""
    flag = np.zeros(len(idx), dtype=int)
    for d in dates:
        center = pd.Timestamp(d).normalize()
        for offset in range(1, forward_days + 1):
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
# 1. Thermal Inertia & Heatwave Onset (P0 Quick Win)
# ─────────────────────────────────────────────────────────────────────────────
def add_thermal_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Day-Ahead Operational Weather Features:
      - Uses IMD forecast for target hour (actual + Gaussian error ~1.2°C).
      - Historical rolling thermal inertia is computed on PAST observed weather (lag >= 24h).
      - Adds Heatwave-Onset Detector: 6h temperature slope, 2nd-derivative acceleration,
        and onset flag (DT_24h > 3.5°C and CDH rising).
    """
    np.random.seed(42)
    forecast_noise = np.random.normal(0, 1.2, len(df))
    df["temp_forecast"] = np.clip(df["temp_c"] + forecast_noise, 2, 48)
    
    T_fc = df["temp_forecast"]
    H    = df.get("humidity", pd.Series(60, index=df.index))

    # Cooling Degree Hours
    df["CDH"] = (T_fc - 24).clip(lower=0)

    # Simplified Steadman Heat Index
    df["heat_index"] = (
        -8.78469475556
        + 1.61139411   * T_fc
        + 2.33854883889 * H
        - 0.14611605   * T_fc * H
        - 0.012308094  * T_fc ** 2
        - 0.016424828  * H ** 2
        + 0.002211732  * T_fc ** 2 * H
        + 0.00072546   * T_fc * H ** 2
        - 0.000003582  * T_fc ** 2 * H ** 2
    ).clip(lower=T_fc)

    # Strictly past observed thermal inertia (shifted by 24h)
    T_observed_past = df["temp_c"].shift(24)
    for window in [24, 48, 72]:
        df[f"rolling_temp_{window}h"] = T_observed_past.rolling(window, min_periods=max(1, window // 4)).mean()

    # Temperature delta: forecast today vs actual yesterday same hour
    df["temp_delta_24h"] = T_fc - df["temp_c"].shift(24)

    # ── P0 Improvement: Temperature Acceleration & Slope (Known at forecast time) ──
    # Slope over past 6h known at t-24
    t_past = df["temp_c"].shift(24)
    t_past_6 = df["temp_c"].shift(30)
    t_past_12 = df["temp_c"].shift(36)
    
    df["temp_slope_6h"] = (t_past - t_past_6) / 6.0
    # 2nd derivative (acceleration)
    df["temp_acceleration_6h"] = ((t_past - t_past_6) / 6.0) - ((t_past_6 - t_past_12) / 6.0)

    # ── P0 Improvement: Heatwave Onset Detector Flag ──
    # Condition: Delta T_24h > 3.5°C AND CDH rising / significant cooling load
    is_sudden_heat = (df["temp_delta_24h"] > 3.5) & (df["CDH"] > 8.0)
    is_extreme_ramp = (df["temp_slope_6h"] > 0.5) & (T_fc >= 38.0)
    df["heatwave_onset_flag"] = (is_sudden_heat | is_extreme_ramp).astype(int)

    # Humidity x CDH Interaction
    df["humidity_temp_interaction"] = df["CDH"] * (H / 100.0)

    return df


# ─────────────────────────────────────────────────────────────────────────────
# 2. Monsoon / Rain & Cooling Regime Features (P0 Quick Win)
# ─────────────────────────────────────────────────────────────────────────────
def add_monsoon_rain_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Monsoon evening drop-outs are the single largest source of error in Delhi (July-August).
    Sudden convective rainstorms drop temperatures and trigger mass AC shutoffs.
    """
    idx = df.index
    H   = df.get("humidity", pd.Series(60, index=df.index))
    
    # Day-ahead precipitation probability proxy:
    # High humidity (>70%) during Monsoon (July-September) gives high rain probability
    is_monsoon_season = idx.month.isin([6, 7, 8, 9])
    rain_base = np.clip((H - 60.0) / 35.0, 0.0, 1.0)
    df["rain_prob_forecast"] = np.where(is_monsoon_season, rain_base, rain_base * 0.15)

    # Flag for Monsoon evenings (July-August, 18:00 to 22:00)
    df["is_monsoon_evening"] = (idx.month.isin([7, 8]) & (idx.hour >= 18) & (idx.hour <= 22)).astype(int)

    # Sudden cooling risk: rain probability interacting with cooling degree hours
    df["monsoon_cooling_risk"] = df["rain_prob_forecast"] * df["CDH"]

    return df


# ─────────────────────────────────────────────────────────────────────────────
# 3. Cyclical Time Encodings & Calendar Signals
# ─────────────────────────────────────────────────────────────────────────────
def add_cyclical_time_features(df: pd.DataFrame) -> pd.DataFrame:
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

    # Day of year (365-cycle)
    df["doy_sin"] = np.sin(2 * np.pi * idx.day_of_year / 365)
    df["doy_cos"] = np.cos(2 * np.pi * idx.day_of_year / 365)

    # Raw calendar
    df["hour"]        = idx.hour
    df["day_of_week"] = idx.day_of_week
    df["month"]       = idx.month
    df["is_weekend"]  = (idx.day_of_week >= 5).astype(int)

    # Board exam calendar proxy (March-April alter commercial vs residential daytime load)
    df["is_exam_period"] = idx.month.isin([3, 4]).astype(int)

    return df


# ─────────────────────────────────────────────────────────────────────────────
# 4. Indian Festival & Cultural Flags (+ Post-Festival Recovery)
# ─────────────────────────────────────────────────────────────────────────────
def add_festival_flags(df: pd.DataFrame) -> pd.DataFrame:
    idx = df.index

    # Major festivals (with +/- 1 day window)
    df["is_diwali"]       = _date_flag(idx, DIWALI_DATES,  window_days=1)
    df["is_eid"]          = _date_flag(idx, EID_AL_FITR + EID_AL_ADHA, window_days=1)
    df["is_holi"]         = _date_flag(idx, HOLI_DATES,    window_days=0)
    df["is_republic_day"] = _date_flag(idx, REPUBLIC_DAY,  window_days=0)
    df["is_independence"] = _date_flag(idx, INDEPENDENCE,  window_days=0)
    df["is_christmas"]    = _date_flag(idx, CHRISTMAS,     window_days=0)

    # Composite major festival
    df["is_major_festival"] = ((df["is_diwali"] == 1) | (df["is_eid"] == 1)).astype(int)

    # Post-festival recovery window (day +1 to +3 after Diwali, Eid, Holi)
    df["post_festival_recovery"] = _date_flag_forward(
        idx, DIWALI_DATES + EID_AL_FITR + EID_AL_ADHA + HOLI_DATES, forward_days=3
    )

    return df


# ─────────────────────────────────────────────────────────────────────────────
# 5. Delhi-Specific Event & Policy Flags
# ─────────────────────────────────────────────────────────────────────────────
def add_delhi_event_flags(df: pd.DataFrame) -> pd.DataFrame:
    idx = df.index
    df["odd_even_flag"] = _odd_even_flag(idx)

    lockdown_ranges = [
        ("2021-01-01", "2021-02-28"),
        ("2021-04-19", "2021-05-31"),
    ]
    df["lockdown_flag"] = 0
    for start, end in lockdown_ranges:
        mask = (idx >= pd.Timestamp(start, tz=idx.tz)) & \
               (idx <= pd.Timestamp(end,   tz=idx.tz))
        df.loc[mask, "lockdown_flag"] = 1

    return df


# ─────────────────────────────────────────────────────────────────────────────
# 6. Load Lag Features & Volatility (Strict Lag >= 24h)
# ─────────────────────────────────────────────────────────────────────────────
def add_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    load = df["load_mw"]

    for lag in [24, 48, 168]:
        df[f"load_lag_{lag}h"] = load.shift(lag)

    # Rolling mean strictly prior to forecast issue time (>= 24h)
    df["load_rolling_mean_24h"] = load.shift(24).rolling(24, min_periods=12).mean()
    df["load_rolling_mean_48h"] = load.shift(24).rolling(48, min_periods=24).mean()

    # Ramp rates known at forecast time
    df["load_delta_1h"]  = load.shift(24) - load.shift(25)
    df["load_delta_24h"] = load.shift(24) - load.shift(48)

    # ── P0 Improvement: Rolling load volatility over past 12h (known at t-24) ──
    df["load_volatility_12h"] = load.shift(24).rolling(12, min_periods=6).std()

    # Peak timing recency
    threshold_90 = df["load_mw"].quantile(0.90)
    past_is_peak = (load.shift(24) >= threshold_90).astype(int)
    
    hours_since = np.zeros(len(df))
    last_p = -999
    for i in range(len(df)):
        if past_is_peak.iloc[i] == 1:
            last_p = i
        hours_since[i] = min(168, i - last_p if last_p != -999 else 168)
    df["hours_since_last_peak"] = hours_since

    return df


# ─────────────────────────────────────────────────────────────────────────────
# 7. Annual Linear Trend
# ─────────────────────────────────────────────────────────────────────────────
def add_trend(df: pd.DataFrame) -> pd.DataFrame:
    t0 = df.index.min()
    df["trend_years"] = (df.index - t0).total_seconds() / (3600 * 24 * 365.25)
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 8. Peak Classification Target
# ─────────────────────────────────────────────────────────────────────────────
def add_peak_target(df: pd.DataFrame, percentile: float = 0.90) -> pd.DataFrame:
    threshold = df["load_mw"].quantile(percentile)
    df["y_peak"]            = (df["load_mw"] >= threshold).astype(int)
    df["peak_threshold_mw"] = threshold
    print(f"  -> Peak threshold ({int(percentile*100)}th pct): {threshold:.1f} MW "
          f"| Peak hours: {df['y_peak'].sum()} / {len(df)} ({df['y_peak'].mean()*100:.1f}%)")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Public Feature List
# ─────────────────────────────────────────────────────────────────────────────
FEATURE_COLS = [
    # Thermal & Heatwave Dynamics
    "CDH", "heat_index",
    "rolling_temp_24h", "rolling_temp_48h", "rolling_temp_72h",
    "temp_delta_24h", "temp_forecast",
    "temp_slope_6h", "temp_acceleration_6h", "heatwave_onset_flag",
    "humidity_temp_interaction",
    # Monsoon & Rain Regimes
    "rain_prob_forecast", "is_monsoon_evening", "monsoon_cooling_risk",
    # Cyclical time & calendar
    "hour_sin", "hour_cos", "dow_sin", "dow_cos",
    "month_sin", "month_cos", "doy_sin", "doy_cos",
    "hour", "day_of_week", "month", "is_weekend",
    "is_exam_period",
    # Festivals & events
    "is_diwali", "is_eid", "is_holi",
    "is_republic_day", "is_independence", "is_christmas",
    "is_major_festival", "post_festival_recovery",
    "odd_even_flag", "lockdown_flag",
    # Lags & volatility (strictly lag >= 24h)
    "load_lag_24h", "load_lag_48h", "load_lag_168h",
    "load_rolling_mean_24h", "load_rolling_mean_48h",
    "load_delta_1h", "load_delta_24h",
    "load_volatility_12h",
    "hours_since_last_peak",
    # Trend
    "trend_years",
]


def build_feature_matrix(df: pd.DataFrame, dropna: bool = True) -> pd.DataFrame:
    """
    Full pipeline: raw cleaned DataFrame -> feature matrix ready for ML.
    """
    print("\n[Module 2] Feature Engineering Pipeline (With P0 Model Upgrades)")
    print("-" * 65)

    print("1. Thermal inertia & Heatwave Onset features...")
    df = add_thermal_features(df)

    print("2. Monsoon rain & cooling regime features...")
    df = add_monsoon_rain_features(df)

    print("3. Cyclical time & calendar encodings...")
    df = add_cyclical_time_features(df)

    print("4. Indian festival flags & post-festival recovery...")
    df = add_festival_flags(df)

    print("5. Delhi event & policy flags...")
    df = add_delhi_event_flags(df)

    print("6. Lag & volatility features...")
    df = add_lag_features(df)

    print("7. Annual linear trend...")
    df = add_trend(df)

    print("8. Peak classification target...")
    df = add_peak_target(df)

    # Drop warm-up rows (first 168h due to load_lag_168h)
    if dropna:
        before = len(df)
        df = df.dropna(subset=["load_lag_168h", "load_volatility_12h", "temp_acceleration_6h"])
        print(f"  -> Dropped {before - len(df)} warm-up rows")

    available_features = [c for c in FEATURE_COLS if c in df.columns]
    print(f"\n  Feature matrix ready | Shape: {df.shape}")
    print(f"     Features: {len(available_features)} columns (including P0 improvements)")
    print(f"     Target  : load_mw (continuous) + y_peak (binary)")

    return df


if __name__ == "__main__":
    from preprocessing import run_preprocessing
    clean = run_preprocessing()
    feat  = build_feature_matrix(clean)
    out = Path("data/feature_matrix.parquet")
    feat.to_parquet(out)
    print(f"\nSaved -> {out}")
    print(feat[FEATURE_COLS].describe().round(2).T[["mean", "std", "min", "max"]])
