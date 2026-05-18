"""Per-tick and cumulative cost helpers.

Cost asymmetry (HOLDING_COST=0.50, BACKORDER_COST=1.00) is the canonical lesson:
backlogs cost 2x what surplus inventory costs, so naive players who hedge by
over-ordering still "feel" cheap relative to letting a stockout linger.
"""
from beergame.config.costs import BACKORDER_COST, HOLDING_COST
from beergame.engine.state import GameState, StationState


def weekly_cost(station: StationState) -> float:
    """Per-week cost charged on POST-FILL inventory and backlog."""
    return HOLDING_COST * max(0, station.inventory) + BACKORDER_COST * station.backlog


def total_cost(state: GameState) -> dict:
    """Returns ``{role: cumulative_cost}`` for all stations."""
    return {
        s.role: (s.cost_history[-1] if s.cost_history else 0.0)
        for s in state.stations
    }
