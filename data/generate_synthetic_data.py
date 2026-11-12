"""
Synthetic Delhi SLDC Load Data Generator
Generates realistic hourly load + weather data for Delhi DISCOM
(2000 MW winter baseline → 8300 MW summer peak)
Used when real SLDC data is not yet available.
"""

import numpy as np
import pandas as pd
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────
np.random.seed(42)
START = "2021-01-01"
END   = "2023-12-31 23:00:00"
FREQ  = "h"

# ─────────────────────────────────────────────────────────────────────────────
# Indian festival dates (binary flag)
# ─────────────────────────────────────────────────────────────────────────────
DIWALI_DATES = [
    "2021-11-04", "2022-10-24", "2023-11-12"
]
EID_DATES = [
    "2021-05-13", "2021-07-20", "2022-05-02", "2022-07-09",
    "2023-04-21", "2023-06-28"
]
HOLI_DATES = [
    "2021-03-29", "2022-03-18", "2023-03-08"
]

# Delhi odd-even scheme approximate periods (placeholder)
ODD_EVEN_PERIODS = [
    ("2021-11-01", "2021-11-15"),
    ("2022-11-01", "2022-11-15"),
]

def _in_odd_even(ts):
    for start, end in ODD_EVEN_PERIODS:
        s = pd.Timestamp(start, tz=ts.tz) if ts.tz else pd.Timestamp(start)
        e = pd.Timestamp(end,   tz=ts.tz) if ts.tz else pd.Timestamp(end)
        if s <= ts <= e:
            return 1
    return 0

# ─────────────────────────────────────────────────────────────────────────────
# Generate temperature (synthetic IMD-like, Delhi climate)
# ─────────────────────────────────────────────────────────────────────────────
def synthetic_temperature(idx):
    """Delhi seasonal temperature: 5°C winter → 45°C summer, diurnal ±5°C."""
    day_of_year = idx.day_of_year
    hour        = idx.hour
    # Annual cycle: coldest ~Jan (day 15), hottest ~June (day 165)
    seasonal = 25 + 20 * np.sin(2 * np.pi * (day_of_year - 15) / 365)
    # Diurnal cycle: peak ~14:00
    diurnal  = 5 * np.sin(2 * np.pi * (hour - 6) / 24)
    noise    = np.random.normal(0, 1.5, len(idx))
    return np.clip(seasonal + diurnal + noise, 2, 47)

# ─────────────────────────────────────────────────────────────────────────────
# Generate load (synthetic Delhi SLDC hourly, MW)
# ─────────────────────────────────────────────────────────────────────────────
def synthetic_load(idx, temp):
    """
    Base: 3500 MW.  Seasonal cooling + diurnal morning/evening peaks.
    Annual growth trend ~4%.
    """
    hour        = idx.hour
    day_of_year = idx.day_of_year
    day_num     = (idx - idx[0]).days

    # Seasonal base (winter trough ~2000 MW, summer peak ~8300 MW)
    seasonal = 3500 + 2200 * np.sin(2 * np.pi * (day_of_year - 15) / 365)

    # Diurnal: morning ramp 6-10 AM, evening peak 7-11 PM
    morning_peak = 800 * np.exp(-0.5 * ((hour - 8) / 2) ** 2)
    evening_peak = 1000 * np.exp(-0.5 * ((hour - 20) / 2) ** 2)
    diurnal = morning_peak + evening_peak

    # Temperature response (AC load above 28°C)
    temp_response = np.where(temp > 28, (temp - 28) * 80, 0)

    # Annual growth trend (~4% per year)
    trend = 0.04 * seasonal * (day_num / 365)

    # Weekend / holiday dip
    dow = idx.day_of_week
    weekend_dip = np.where(dow >= 5, -300, 0)

    noise = np.random.normal(0, 120, len(idx))

    load = seasonal + diurnal + temp_response + trend + weekend_dip + noise
    return np.clip(load, 1500, 9000)

# ─────────────────────────────────────────────────────────────────────────────
# Inject synthetic anomalies (outages, missing readings)
# ─────────────────────────────────────────────────────────────────────────────
def inject_anomalies(df, missing_rate=0.015, outage_rate=0.005):
    """Randomly null some readings (meter gaps) and spike-down (outages)."""
    n = len(df)
    missing_mask = np.random.rand(n) < missing_rate
    outage_mask  = np.random.rand(n) < outage_rate
    df.loc[missing_mask, 'load_mw'] = np.nan
    df.loc[outage_mask,  'load_mw'] = df.loc[outage_mask, 'load_mw'] * 0.1
    return df

# ─────────────────────────────────────────────────────────────────────────────
# Main builder
# ─────────────────────────────────────────────────────────────────────────────
def build_raw_dataset() -> pd.DataFrame:
    idx = pd.date_range(start=START, end=END, freq=FREQ, tz="Asia/Kolkata")

    temp = synthetic_temperature(idx)
    load = synthetic_load(idx, temp)

    df = pd.DataFrame({
        "timestamp": idx,
        "load_mw":   load,
        "temp_c":    temp,
        "humidity":  np.clip(60 - 0.8 * temp + np.random.normal(0, 5, len(idx)), 10, 95),
    })
    df = inject_anomalies(df)

    # Festival flags (raw, before cleaning)
    df["is_diwali"]   = df["timestamp"].dt.date.astype(str).isin(DIWALI_DATES).astype(int)
    df["is_eid"]      = df["timestamp"].dt.date.astype(str).isin(EID_DATES).astype(int)
    df["is_holi"]     = df["timestamp"].dt.date.astype(str).isin(HOLI_DATES).astype(int)
    df["odd_even"]    = df["timestamp"].apply(_in_odd_even)

    df.set_index("timestamp", inplace=True)
    return df


if __name__ == "__main__":
    out = Path("data/raw")
    out.mkdir(parents=True, exist_ok=True)
    df = build_raw_dataset()
    df.to_csv(out / "delhi_load_raw.csv")
    print(f"✅ Saved synthetic raw dataset: {df.shape}  →  data/raw/delhi_load_raw.csv")
    print(df.describe())
