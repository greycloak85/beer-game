"""Sterman canonical cost parameters. Asymmetry is load-bearing —
over-ordering "feels safe" is the textbook lesson."""
HOLDING_COST: float = 0.50      # $ per case per week of on-hand inventory
BACKORDER_COST: float = 1.00    # $ per case per week of unfilled demand
