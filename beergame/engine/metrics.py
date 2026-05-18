"""Aggregate metrics over a completed (or in-progress) game.

This module is intentionally a stub here — Phase 3 will flesh it out with the
debrief-chart helpers. The two functions below are what Plan 03 (engine gates)
needs to compute the bullwhip-ratio gate.
"""
from beergame.engine.state import GameState, Role


def peak_orders(state: GameState, role: Role) -> int:
    """Max order placed by ``role`` over the game so far."""
    h = state.stations[role.value].orders_placed_history
    return max(h) if h else 0


def bullwhip_ratio(state: GameState) -> float:
    """max(factory orders) / max(retailer orders) — the canonical bullwhip metric."""
    retailer_peak = peak_orders(state, Role.RETAILER)
    factory_peak = peak_orders(state, Role.FACTORY)
    if retailer_peak == 0:
        raise ValueError("retailer never ordered — cannot compute ratio")
    return factory_peak / retailer_peak
