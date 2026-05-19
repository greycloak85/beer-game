"""Sterman canonical cost parameters. Asymmetry is load-bearing —
over-ordering "feels safe" is the textbook lesson.

REVENUE_PER_UNIT_SHIPPED is NOT canonical Sterman — the original 1989
exercise is purely cost-minimization. We add it as a UI scoring concept so
players can see winning vs losing on a green/red P&L gauge during play. It
does NOT feed back into the simulation engine; it's a render-only metric.

Chosen so that perfect equilibrium play (4 shipped/wk, 12 on hand, 0 backlog)
yields a small positive net: $2/wk × $8 revenue - $6 holding cost = +$2/wk.
This makes break-even-or-better feel like winning, anything significantly
worse (stockouts, pile-ups) clearly loses.
"""
HOLDING_COST: float = 0.50         # $ per case per week of on-hand inventory
BACKORDER_COST: float = 1.00       # $ per case per week of unfilled demand
REVENUE_PER_UNIT_SHIPPED: float = 2.00  # $ earned per case the station ships downstream
