
def calculate_procurement(
    demand,
    scheduled,
    under_penalty=3.5,
    over_cost=1.0
):
    shortfall = max(0, demand - scheduled)

    surplus = max(0, scheduled - demand)

    total_cost = (
        shortfall * under_penalty
        + surplus * over_cost
    )

    return {
        "predicted_demand": demand,
        "scheduled_procurement": scheduled,
        "shortfall": shortfall,
        "surplus": surplus,
        "estimated_cost_index": total_cost
    }
