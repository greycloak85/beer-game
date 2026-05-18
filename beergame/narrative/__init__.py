"""Static-template narrative for the debrief (DEB-05).

Public API: ``narrative_for(state: GameState) -> str``.

Returns a Markdown string ≤200 words tailored to ``state.player_role``,
naming the bullwhip and citing this player's own peak/ratio/cost numbers.

Purity contract: this package is Streamlit-free and Plotly-free; it depends
only on ``beergame.engine.metrics`` (for ratios + cost decomposition) and
``beergame.engine.state`` (for ``GameState`` + ``Role``). The view layer is
the ONLY place where ``streamlit`` + ``beergame.narrative`` meet.
"""
from beergame.engine.metrics import (
    cost_breakdown,
    per_echelon_amplification,
    variance_bullwhip_ratio,
)
from beergame.engine.state import GameState, Role
from beergame.narrative.templates import _TEMPLATES


def narrative_for(state: GameState) -> str:
    """Return the role-specific debrief paragraph for ``state.player_role``.

    Args:
        state: a fully-played ``GameState``. The Retailer template references
            ``max(orders_placed_history)`` for Retailer and Factory; the
            Wholesaler/Distributor/Factory templates reference variance
            ratios. Empty histories degrade to 0 peaks (defensive — in the
            canonical 36-week run every history is length 36).

    Returns:
        A Markdown string ≤200 words. Mentions the literal token "bullwhip",
        names the role, and embeds at least one markdown ``**bold**`` span.
        Deterministic: same ``state`` → identical string.
    """
    role = state.player_role
    factory = state.stations[Role.FACTORY.value]
    retailer = state.stations[Role.RETAILER.value]

    ratios = per_echelon_amplification(state)
    overall = variance_bullwhip_ratio(state)
    rows = cost_breakdown(state)
    my_cost = next(r.total for r in rows if r.role == role)

    return _TEMPLATES[role].format(
        retailer_peak=(
            max(retailer.orders_placed_history)
            if retailer.orders_placed_history
            else 0
        ),
        factory_peak=(
            max(factory.orders_placed_history)
            if factory.orders_placed_history
            else 0
        ),
        ratio=overall,
        your_ratio=ratios[role],
        factory_ratio=ratios[Role.FACTORY],
        cost=my_cost,
    )


__all__ = ["narrative_for"]
