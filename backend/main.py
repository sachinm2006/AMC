import sys
from pathlib import Path
from typing import Optional
import pandas as pd
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Robust path resolution: Works from repo root or backend/ directory
BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Backend local helper modules
try:
    from backend.copilot import generate_insights
    from backend.metrics import calculate_metrics
    from backend.procurement import calculate_procurement
    from backend.peak_analytics import analyze_peaks
    from backend.discom_service import calculate_discom_pnl_for_range, DISCOM_SHARES
except ImportError:
    from copilot import generate_insights
    from metrics import calculate_metrics
    from procurement import calculate_procurement
    from peak_analytics import analyze_peaks
    from discom_service import calculate_discom_pnl_for_range, DISCOM_SHARES

# ML pipeline modules
from src.procurement import (
    calculate_procurement_loss,
    simulate_procurement_comparison
)

# Load prediction dataset
DATA_PATH = REPO_ROOT / "outputs" / "predictions_with_bands.csv"
if not DATA_PATH.exists():
    raise FileNotFoundError(f"Predictions dataset not found at {DATA_PATH}. Run Phase 2 pipeline first.")
df = pd.read_csv(DATA_PATH, index_col=0)

app = FastAPI(
    title="Delhi DISCOM Load Forecasting & P&L Copilot API",
    description="Electricity Load Forecasting, Date-Range Profit Estimation, and Procurement Copilot for BRPL, BYPL, and TPDDL",
    version="1.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "message": "Delhi DISCOM Procurement Copilot Backend is running!",
        "status": "online",
        "version": "1.1.0",
        "records_loaded": len(df),
        "supported_discoms": list(DISCOM_SHARES.keys()),
        "endpoints": [
            "/api/forecast",
            "/api/peaks",
            "/api/copilot",
            "/api/discom/shares",
            "/api/discom/analysis"
        ]
    }


@app.get("/api/forecast")
def get_forecast():
    row = df.iloc[-1]
    return {
        "timestamp": str(row.name),
        "actual_mw": float(row["actual_mw"]),
        "P10": float(row["pred_q10_h24"]),
        "P50": float(row["pred_q50_h24"]),
        "P90": float(row["pred_q90_h24"])
    }


@app.get("/api/peaks")
def get_peaks():
    row = df.iloc[-1]
    return {
        "timestamp": str(row.name),
        "peak_detected": bool(row["pred_peak_flag"]),
        "peak_probability": float(row["pred_peak_proba"]),
        "predicted_peak_demand": float(row["pred_q90_h24"])
    }


@app.get("/api/peaks/analytics")
def peaks_analytics():
    return analyze_peaks(df)


@app.get("/api/copilot")
def copilot():
    return generate_insights(df)


# =========================================================================
# DISCOM P&L AND DATE-RANGE PROFIT SIMULATOR ENDPOINTS
# =========================================================================

@app.get("/api/discom/shares")
def get_discom_shares():
    return DISCOM_SHARES


class DiscomAnalysisInput(BaseModel):
    start_date: str = "2023-05-01"
    end_date: str = "2023-06-30"
    discom: str = "ALL"
    base_tariff: float = 4500.0
    under_penalty: float = 3.5
    over_cost: float = 1.0


@app.get("/api/discom/analysis")
def get_discom_analysis(
    start_date: str = Query("2023-05-01", description="Start date (YYYY-MM-DD)"),
    end_date: str = Query("2023-06-30", description="End date (YYYY-MM-DD)"),
    discom: str = Query("ALL", description="DISCOM: ALL, BRPL, TPDDL, BYPL"),
    base_tariff: float = Query(4500.0, description="Base tariff in INR/MWh"),
    under_penalty: float = Query(3.5, description="DSM penalty multiplier (CERC 2024)"),
    over_cost: float = Query(1.0, description="Surplus capacity cost multiplier")
):
    """
    Evaluates DISCOM load metrics and computes estimated financial profit/savings
    under the CERC 2024 Deviation Settlement Mechanism for any custom date range.
    """
    return calculate_discom_pnl_for_range(
        start_date=start_date,
        end_date=end_date,
        discom=discom,
        base_tariff=base_tariff,
        under_penalty=under_penalty,
        over_cost=over_cost
    )


@app.post("/api/discom/analysis")
def post_discom_analysis(data: DiscomAnalysisInput):
    """POST variant for JSON body input."""
    return calculate_discom_pnl_for_range(
        start_date=data.start_date,
        end_date=data.end_date,
        discom=data.discom,
        base_tariff=data.base_tariff,
        under_penalty=data.under_penalty,
        over_cost=data.over_cost
    )


# =========================================================================
# STANDARD PROCUREMENT & METRICS
# =========================================================================

class ProcurementInput(BaseModel):
    demand: float
    scheduled: float
    under_penalty: float = 3.5
    over_cost: float = 1.0


@app.post("/api/simulate-procurement")
def simulate_procurement(data: ProcurementInput):
    return calculate_procurement(
        data.demand,
        data.scheduled,
        data.under_penalty,
        data.over_cost
    )


class MetricsInput(BaseModel):
    actual: list[float]
    predicted: list[float]


@app.post("/api/metrics")
def get_metrics(data: MetricsInput):
    return calculate_metrics(data.actual, data.predicted)


@app.get("/api/procurement/comparison")
def procurement_comparison():
    summary, savings = simulate_procurement_comparison(df)
    return {
        "strategies": summary.to_dict(orient="records"),
        "estimated_savings_inr": float(savings),
        "recommended_strategy": "P90" if savings > 0 else "P50"
    }


@app.get("/api/procurement/risk")
def procurement_risk():
    actual = df["actual_mw"].values
    p10 = df["pred_q10_h24"].values
    p50 = df["pred_q50_h24"].values
    p90 = df["pred_q90_h24"].values

    return {
        "P10": calculate_procurement_loss(actual, p10),
        "P50": calculate_procurement_loss(actual, p50),
        "P90": calculate_procurement_loss(actual, p90)
    }
