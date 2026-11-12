# -*- coding: utf-8 -*-
"""
Module 6: Asymmetric Financial Procurement Advisor
==================================================
Converts probabilistic forecasts into cost-optimal MW purchasing schedules.
Implements the asymmetric tariff loss function:
  Under-procurement: 3.5x penalty (Deviation Settlement Mechanism - DSM fee)
  Over-procurement:  1.0x capacity waste

Quantifies financial risk across P10, P50, and P90 procurement policies.
"""

import numpy as np
import pandas as pd

def calculate_procurement_loss(
    actual_load: np.ndarray,
    procured_load: np.ndarray,
    base_tariff: float = 4500.0,  # INR per MWh (~₹4.5/kWh)
    under_multiplier: float = 3.5,
    over_multiplier: float = 1.0,
) -> dict:
    """
    Computes total procurement cost and penalty exposure.

    Args:
        actual_load: Actual grid demand in MW
        procured_load: Day-ahead scheduled / procured power in MW
        base_tariff: Tariff in ₹ per MWh
        under_multiplier: DSM penalty multiplier for deficit
        over_multiplier: Capacity charge multiplier for surplus
    """
    error = actual_load - procured_load
    under = np.maximum(0, error)
    over  = np.maximum(0, -error)

    under_cost = np.sum(under * under_multiplier * base_tariff)
    over_cost  = np.sum(over * over_multiplier * base_tariff)
    base_cost  = np.sum(procured_load * base_tariff)
    total_cost = base_cost + under_cost + over_cost

    return {
        "base_cost_inr": float(base_cost),
        "dsm_penalty_inr": float(under_cost),
        "surplus_waste_inr": float(over_cost),
        "total_financial_loss_inr": float(under_cost + over_cost),
        "total_procurement_cost_inr": float(total_cost),
        "under_procured_mwh": float(np.sum(under)),
        "over_procured_mwh": float(np.sum(over)),
    }

def simulate_procurement_comparison(
    predictions_df: pd.DataFrame,
    base_tariff: float = 4500.0,
    under_multiplier: float = 3.5,
    over_multiplier: float = 1.0,
) -> pd.DataFrame:
    """
    Compares P50 vs P90 procurement strategies on test data.
    Demonstrates why P90 minimizes net penalties under asymmetric DSM.
    """
    actual = predictions_df["actual_mw"].values
    p50 = predictions_df.get("pred_q50_h24", actual).values
    p90 = predictions_df.get("pred_q90_h24", actual * 1.1).values

    loss_p50 = calculate_procurement_loss(actual, p50, base_tariff, under_multiplier, over_multiplier)
    loss_p90 = calculate_procurement_loss(actual, p90, base_tariff, under_multiplier, over_multiplier)

    savings = loss_p50["total_financial_loss_inr"] - loss_p90["total_financial_loss_inr"]

    summary = pd.DataFrame([
        {
            "Strategy": "P50 (Point Forecast / Median)",
            "Under-procured (MWh)": round(loss_p50["under_procured_mwh"], 1),
            "Over-procured (MWh)": round(loss_p50["over_procured_mwh"], 1),
            "DSM Penalty (₹)": round(loss_p50["dsm_penalty_inr"], 2),
            "Wasted Capacity (₹)": round(loss_p50["surplus_waste_inr"], 2),
            "Total Penalty Loss (₹)": round(loss_p50["total_financial_loss_inr"], 2),
        },
        {
            "Strategy": "P90 (Probabilistic Tail-Risk Buffer)",
            "Under-procured (MWh)": round(loss_p90["under_procured_mwh"], 1),
            "Over-procured (MWh)": round(loss_p90["over_procured_mwh"], 1),
            "DSM Penalty (₹)": round(loss_p90["dsm_penalty_inr"], 2),
            "Wasted Capacity (₹)": round(loss_p90["surplus_waste_inr"], 2),
            "Total Penalty Loss (₹)": round(loss_p90["total_financial_loss_inr"], 2),
        }
    ])

    return summary, savings
