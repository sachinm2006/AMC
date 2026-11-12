def generate_insights(df):
    latest = df.iloc[-1]

    demand = float(latest["pred_q50_h24"])
    lower = float(latest["pred_q10_h24"])
    upper = float(latest["pred_q90_h24"])
    peak_probability = float(latest["pred_peak_proba"])

    insights = []

    if peak_probability >= 0.7:
        insights.append("High peak-demand risk. Prepare additional procurement.")
    elif peak_probability >= 0.4:
        insights.append("Moderate peak-demand risk. Monitor demand closely.")
    else:
        insights.append("Low peak-demand risk under current forecast.")

    insights.append(
        f"Expected demand: {demand:.2f} MW. "
        f"Forecast range: {lower:.2f}–{upper:.2f} MW."
    )

    if upper - demand > 100:
        insights.append("Wide uncertainty band. Consider a conservative procurement buffer.")

    return {
        "copilot_insights": insights,
        "recommended_demand_mw": round(demand, 2),
        "peak_probability": round(peak_probability, 4)
    }