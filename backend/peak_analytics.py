import pandas as pd


def analyze_peaks(df):

    peak_days = df[df["pred_peak_flag"] == 1]

    return {
        "total_records": int(len(df)),
        "predicted_peak_records": int(len(peak_days)),
        "peak_percentage": round(
            len(peak_days) / len(df) * 100, 2
        ),
        "maximum_predicted_probability": float(
            df["pred_peak_proba"].max()
        ),
        "maximum_demand_mw": float(
            df["pred_q90_h24"].max()
        ),
        "peak_records": peak_days.tail(20).reset_index().to_dict(
            orient="records"
        )
    }