# -*- coding: utf-8 -*-
"""
DISCOM P&L and Date-Range Profit Estimation Engine
Calculates operational load metrics and financial savings under CERC 2024 DSM regulations.
"""

from pathlib import Path
import pandas as pd
import numpy as np

# Load dataset once
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PARQUET_PATH = DATA_DIR / "full_predictions_with_bands.parquet"
CSV_PATH = Path(__file__).resolve().parent.parent / "outputs" / "predictions_with_bands.csv"

DISCOM_SHARES = {
    "ALL": {"name": "Delhi NCT (Combined Grid)", "share": 1.00, "consumers": "62 Lakhs"},
    "BRPL": {"name": "BSES Rajdhani Power Limited (South & West)", "share": 0.44, "consumers": "28 Lakhs"},
    "TPDDL": {"name": "Tata Power Delhi Distribution Limited (North & NW)", "share": 0.29, "consumers": "19 Lakhs"},
    "BYPL": {"name": "BSES Yamuna Power Limited (East & Central)", "share": 0.23, "consumers": "15 Lakhs"}
}

def load_predictions_data():
    if PARQUET_PATH.exists():
        df = pd.read_parquet(PARQUET_PATH)
    elif CSV_PATH.exists():
        df = pd.read_csv(CSV_PATH, index_col=0)
    else:
        raise FileNotFoundError("Prediction datasets not found. Run pipeline first.")
    df.index = pd.to_datetime(df.index)
    return df

_cached_df = None

def get_data():
    global _cached_df
    if _cached_df is None:
        _cached_df = load_predictions_data()
    return _cached_df

def calculate_discom_pnl_for_range(
    start_date: str = "2023-05-01",
    end_date: str = "2023-06-30",
    discom: str = "ALL",
    base_tariff: float = 4500.0,  # INR per MWh (~Rs 4.50/kWh)
    under_penalty: float = 3.5,   # DSM penalty multiplier (CERC 2024)
    over_cost: float = 1.0        # Fixed capacity charge surplus loss
):
    df = get_data()
    discom_key = discom.upper() if discom.upper() in DISCOM_SHARES else "ALL"
    discom_meta = DISCOM_SHARES[discom_key]
    share = discom_meta["share"]

    # Parse dates with timezone safety
    try:
        dt_start = pd.to_datetime(start_date)
        dt_end = pd.to_datetime(end_date)
        if dt_start.tzinfo is None and df.index.tzinfo is not None:
            dt_start = dt_start.tz_localize(df.index.tzinfo)
        if dt_end.tzinfo is None and df.index.tzinfo is not None:
            dt_end = dt_end.tz_localize(df.index.tzinfo)
        # Include entire end day
        dt_end = dt_end + pd.Timedelta(hours=23, minutes=59, seconds=59)
    except Exception:
        # Fallback to summer 2023
        dt_start = df.index[-1464]
        dt_end = df.index[-1]

    mask = (df.index >= dt_start) & (df.index <= dt_end)
    sub = df[mask].copy()

    if len(sub) == 0:
        # Fallback to last 720 hours (30 days)
        sub = df.tail(720).copy()
        dt_start = sub.index[0]
        dt_end = sub.index[-1]

    # Apply DISCOM share scaling
    actual = sub["actual_mw"].values * share
    p10 = sub["pred_q10_h24"].values * share
    p50 = sub["pred_q50_h24"].values * share
    p90 = sub["pred_q90_h24"].values * share
    copilot = sub["procured_mw"].values * share
    peak_flag = sub["pred_peak_flag"].values
    peak_proba = sub["pred_peak_proba"].values

    # Financial Cost Calculation Helper
    def evaluate_strategy(procured_arr):
        shortfall = np.maximum(0, actual - procured_arr)
        surplus = np.maximum(0, procured_arr - actual)
        shortfall_mwh = float(np.sum(shortfall))
        surplus_mwh = float(np.sum(surplus))
        dsm_penalty = shortfall_mwh * base_tariff * under_penalty
        surplus_waste = surplus_mwh * base_tariff * over_cost
        total_cost = dsm_penalty + surplus_waste
        return {
            "shortfall_mwh": round(shortfall_mwh, 1),
            "surplus_mwh": round(surplus_mwh, 1),
            "dsm_penalty_inr": round(dsm_penalty, 2),
            "dsm_penalty_lakhs": round(dsm_penalty / 1e5, 2),
            "dsm_penalty_crores": round(dsm_penalty / 1e7, 3),
            "surplus_waste_inr": round(surplus_waste, 2),
            "surplus_waste_lakhs": round(surplus_waste / 1e5, 2),
            "surplus_waste_crores": round(surplus_waste / 1e7, 3),
            "total_financial_loss_inr": round(total_cost, 2),
            "total_financial_loss_lakhs": round(total_cost / 1e5, 2),
            "total_financial_loss_crores": round(total_cost / 1e7, 3)
        }

    p50_eval = evaluate_strategy(p50)
    p90_eval = evaluate_strategy(p90)
    copilot_eval = evaluate_strategy(copilot)

    # Net Profit Saved
    net_savings_inr = p50_eval["total_financial_loss_inr"] - copilot_eval["total_financial_loss_inr"]
    net_savings_lakhs = round(net_savings_inr / 1e5, 2)
    net_savings_crores = round(net_savings_inr / 1e7, 3)

    avoided_dsm_inr = p50_eval["dsm_penalty_inr"] - copilot_eval["dsm_penalty_inr"]
    avoided_dsm_crores = round(avoided_dsm_inr / 1e7, 3)

    deficit_mwh_avoided = round(p50_eval["shortfall_mwh"] - copilot_eval["shortfall_mwh"], 1)
    deficit_reduction_pct = round(
        (deficit_mwh_avoided / max(1e-5, p50_eval["shortfall_mwh"])) * 100, 1
    )

    # DISCOM operational overview
    total_mwh = float(np.sum(actual))
    max_peak_mw = float(np.max(actual))
    avg_mw = float(np.mean(actual))
    peak_hours_count = int(np.sum(peak_flag))

    # Time-series sampling for frontend charting (max 60 data points)
    resample_freq = "D" if len(sub) > 168 else "6h" if len(sub) > 48 else "h"
    sub_resampled = pd.DataFrame({
        "actual_mw": actual,
        "p10_mw": p10,
        "p50_mw": p50,
        "p90_mw": p90,
        "procured_mw": copilot,
        "peak_proba": peak_proba
    }, index=sub.index)

    if resample_freq == "D":
        chart_df = sub_resampled.resample("D").agg({
            "actual_mw": "max",
            "p10_mw": "min",
            "p50_mw": "mean",
            "p90_mw": "max",
            "procured_mw": "max",
            "peak_proba": "max"
        }).dropna()
    elif resample_freq == "6h":
        chart_df = sub_resampled.resample("6h").mean().dropna()
    else:
        chart_df = sub_resampled

    chart_points = []
    for idx, r in chart_df.iterrows():
        chart_points.append({
            "time": idx.strftime("%d %b" if resample_freq == "D" else "%d %b %H:%M"),
            "actual": round(float(r["actual_mw"]), 1),
            "p10": round(float(r["p10_mw"]), 1),
            "p50": round(float(r["p50_mw"]), 1),
            "p90": round(float(r["p90_mw"]), 1),
            "procured": round(float(r["procured_mw"]), 1),
            "peak_probability": round(float(r["peak_proba"]), 3)
        })

    # Top 3 Critical Peak Stress Events in this range
    peak_indices = np.argsort(actual)[-3:][::-1]
    top_events = []
    for p_idx in peak_indices:
        ts = sub.index[p_idx]
        top_events.append({
            "timestamp": ts.strftime("%Y-%m-%d %H:%M IST"),
            "actual_demand_mw": round(float(actual[p_idx]), 1),
            "p50_baseline_mw": round(float(p50[p_idx]), 1),
            "copilot_procured_mw": round(float(copilot[p_idx]), 1),
            "peak_probability": round(float(peak_proba[p_idx]), 3),
            "penalty_averted_lakhs": round(
                max(0.0, float(actual[p_idx] - p50[p_idx])) * (base_tariff * under_penalty / 1e5), 2
            )
        })

    return {
        "status": "success",
        "discom": {
            "key": discom_key,
            "name": discom_meta["name"],
            "share_percentage": round(share * 100, 1),
            "consumer_base": discom_meta["consumers"]
        },
        "period": {
            "start": dt_start.strftime("%Y-%m-%d %H:%M"),
            "end": dt_end.strftime("%Y-%m-%d %H:%M"),
            "total_hours": len(sub)
        },
        "operational_metrics": {
            "total_energy_mwh": round(total_mwh, 1),
            "peak_demand_mw": round(max_peak_mw, 1),
            "avg_demand_mw": round(avg_mw, 1),
            "predicted_peak_hours": peak_hours_count
        },
        "estimated_pnl": {
            "net_profit_saved_crores": net_savings_crores,
            "net_profit_saved_lakhs": net_savings_lakhs,
            "avoided_dsm_penalties_crores": avoided_dsm_crores,
            "deficit_mwh_avoided": deficit_mwh_avoided,
            "deficit_reduction_pct": deficit_reduction_pct,
            "traditional_p50": p50_eval,
            "continuous_p90": p90_eval,
            "copilot_policy": copilot_eval
        },
        "top_peak_events": top_events,
        "chart_data": chart_points
    }
