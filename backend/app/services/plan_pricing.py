PLAN_PRICES = {
    "solo": {"monthly": 999, "biannual": 849, "annual": 749},
    "growth": {"monthly": 1499, "biannual": 1274, "annual": 1124},
    "professional": {"monthly": 3999, "biannual": 3399, "annual": 2999},
    "enterprise": {"monthly": 9999, "biannual": 8499, "annual": 7499},
}

CYCLE_MULTIPLIER = {"monthly": 1, "biannual": 6, "annual": 12}


def plan_amount_inr(plan: str, billing_cycle: str) -> int:
    if plan not in PLAN_PRICES:
        raise ValueError(f"Invalid plan: {plan}")
    if billing_cycle not in CYCLE_MULTIPLIER:
        raise ValueError(f"Invalid billing cycle: {billing_cycle}")
    monthly_rate = PLAN_PRICES[plan][billing_cycle]
    return monthly_rate * CYCLE_MULTIPLIER[billing_cycle]
