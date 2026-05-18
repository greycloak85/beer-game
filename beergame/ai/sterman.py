"""Sterman anchor-and-adjust ordering heuristic.

Implements the median empirical parameter fit from:
    Sterman, J.D. (1989). "Modeling Managerial Behavior: Misperceptions of
    Feedback in a Dynamic Decision-Making Experiment." Management Science
    35(3): 321-339, Table 2.

CRITICAL: These are the EMPIRICAL parameters (fit to real human subjects),
NOT the "optimal" parameters (alpha=beta=1, theta=0) from later theoretical
work (e.g., Edali & Yasarcan, JASSS 17(4):2, 2014). The empirical parameters
REPRODUCE the bullwhip; the optimal parameters MINIMIZE it. We want
reproduction, not minimization -- the bullwhip is the teaching point.

Order formula (per Sterman 1989):
    L_t = theta * D_t + (1 - theta) * L_{t-1}     # smoothed expected demand
    O_t = max(0, round(L_t + alpha * (S' - NS_t) - beta * SL_t))
where NS_t = inventory - backlog (net stock), SL_t = supply line.
"""
from dataclasses import dataclass, field

from beergame.engine.state import StationView


@dataclass
class ShipmentAnchorAndAdjustAgent:
    """Sterman 1989 empirical anchor-and-adjust ordering policy."""

    # === Empirical parameters (Sterman 1989, Table 2 median fit) ===
    alpha: float = 0.26          # stock-adjustment fraction
    beta: float = 0.34           # supply-line weight (rational = 1.0)
    theta: float = 0.36          # demand-smoothing weight (rational = 0.0)
    desired_inventory: float = 17.0   # S' -- desired inventory + supply line target

    # === Per-instance forecast state (carries across weeks) ===
    # Initialized to equilibrium throughput so week 1's order matches the
    # initial in-transit shipments (system stays in equilibrium until demand step).
    smoothed_demand: float = field(default=4.0)

    def decide_order(self, view: StationView) -> int:
        # Update the smoothed-demand forecast with this week's observed order.
        self.smoothed_demand = (
            self.theta * view.last_order_received
            + (1.0 - self.theta) * self.smoothed_demand
        )
        net_stock = view.inventory - view.backlog
        raw_order = (
            self.smoothed_demand
            + self.alpha * (self.desired_inventory - net_stock)
            - self.beta * view.supply_line
        )
        return max(0, round(raw_order))
