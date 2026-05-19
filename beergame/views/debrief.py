"""Debrief screen — Phase 3 full implementation.

A thin Streamlit assembler. ALL math lives in ``beergame.engine.metrics``;
chart construction lives in ``beergame.charts``; narrative copy lives in
``beergame.narrative``. This file is the only place ``streamlit`` and the
debrief-specific imports meet.

Layout (top to bottom):
  1. Title.
  2. Headline ``st.metric`` — overall variance amplification ratio (2dp).
  3. 4-panel chart (orders + inventory across all stations, week-5 vline).
  4. Four per-echelon ``st.metric`` tiles (one per station, 2dp).
  5. Cost breakdown table (4 rows × 4 columns) via ``st.table``.
  6. Narrative paragraph for the player's role via ``st.markdown``.
  7. "Play again" button bound to ``on_reset``.

Critical Streamlit 1.57.0 conventions enforced here:
  - ``st.plotly_chart(fig, key="debrief_four_panel", width="stretch")`` —
    ``width="stretch"`` is REQUIRED in 1.57.0 (the older container-width
    kwarg is deprecated; do NOT reintroduce it).
  - ``st.table([dict, dict, ...])`` — list of dicts. NO pandas. NO
    ``st.dataframe``.
  - The "Play again" button label is load-bearing — ``tests/test_app_smoke.py``
    asserts that label appears in ``at.button`` after the 36th submission.
"""
import streamlit as st

from beergame.charts import build_four_panel
from beergame.config.costs import REVENUE_PER_UNIT_SHIPPED
from beergame.engine.metrics import (
    cost_breakdown,
    per_echelon_amplification,
    variance_bullwhip_ratio,
)
from beergame.engine.state import GameState, Role
from beergame.engine.tick import is_game_over
from beergame.narrative import narrative_for


def _signed_dollars(value: float) -> str:
    """Format with explicit sign so winning vs losing is unambiguous."""
    if value > 0.01:
        return f"+${value:,.2f}"
    if value < -0.01:
        return f"-${abs(value):,.2f}"
    return "$0.00"


def _pnl_for(state: GameState, role: Role) -> dict:
    """Compute revenue / cost / net for one station. Render-only scoring;
    revenue model lives in beergame/config/costs.py.
    """
    s = state.stations[role.value]
    revenue = sum(s.shipments_sent_history) * REVENUE_PER_UNIT_SHIPPED
    cost = s.cost_history[-1] if s.cost_history else 0.0
    return {"revenue": revenue, "cost": cost, "net": revenue - cost}


def render(state: GameState, on_reset) -> None:
    """Render the full debrief.

    Args:
        state: the final ``GameState``. MUST satisfy ``is_game_over(state)``
            — the engine guarantees ``phase == "done"`` and every history
            tuple is length ``state.total_weeks``.
        on_reset: callback invoked when the user clicks "Play again" —
            ``app.py`` binds this to ``reset_game`` which pops the
            game-related session_state keys while preserving ``seen_rules``.
    """
    assert is_game_over(state), (
        f"Debrief called with phase={state.phase!r} (week={state.week})"
    )

    # ---- Title + headline (DEB-03 primary readout) ----
    st.title("🍺 Game complete")

    # Two headlines side-by-side: the bullwhip (the lesson) and the player's
    # final P&L (the score). Color-code the P&L number so winning vs losing
    # is unmistakable.
    overall = variance_bullwhip_ratio(state)
    player_pnl = _pnl_for(state, state.player_role)
    pnl_color = ("#4ade80" if player_pnl["net"] > 0.01
                 else "#ff5d6a" if player_pnl["net"] < -0.01
                 else "#cfd2d6")
    verdict = ("YOU WON" if player_pnl["net"] > 0.01
               else "YOU LOST" if player_pnl["net"] < -0.01
               else "BREAK-EVEN")

    h_left, h_right = st.columns(2)
    with h_left:
        st.metric(
            "Bullwhip amplification",
            f"{overall:.2f}×",
            help=(
                "Variance of Factory production starts ÷ variance of actual "
                "customer demand. Customer demand changed exactly once: "
                "4 → 8 at week 5."
            ),
        )
    with h_right:
        st.markdown(
            f"<div style='text-align:left;'>"
            f"<div style='text-transform:uppercase;letter-spacing:0.06em;"
            f"font-size:1.7rem;color:#9aa0a6;font-weight:600;'>"
            f"Your final P&amp;L · {verdict}</div>"
            f"<div style='font-size:4.8rem;font-weight:700;color:{pnl_color};"
            f"line-height:1.2;margin-top:0.2rem;'>"
            f"{_signed_dollars(player_pnl['net'])}</div>"
            f"<div style='font-size:1.7rem;color:#9aa0a6;'>"
            f"${player_pnl['revenue']:,.2f} earned shipping cases "
            f"&minus; ${player_pnl['cost']:,.2f} in holding + backorder fees"
            f"</div></div>",
            unsafe_allow_html=True,
        )

    # ---- 4-panel chart (DEB-01, DEB-02). Stable key per RESEARCH.md Pitfall 5. ----
    fig = build_four_panel(state)
    st.plotly_chart(fig, key="debrief_four_panel", width="stretch")

    # ---- Per-echelon ratios (DEB-03 secondary readouts) ----
    st.subheader("Amplification by station")
    ratios = per_echelon_amplification(state)
    cols = st.columns(4)
    for i, role in enumerate(Role):
        with cols[i]:
            st.metric(
                role.name.title(),
                f"{ratios[role]:.2f}×",
                help="variance(this station's orders) / variance(customer demand)",
            )

    # ---- Cost + P&L breakdown table (DEB-04, extended with revenue/net) ----
    st.subheader("Scoreboard")
    rows = cost_breakdown(state)
    st.table([
        {
            "Station": r.role.name.title(),
            "Holding ($)": f"{r.holding:,.2f}",
            "Backorder ($)": f"{r.backorder:,.2f}",
            "Total cost ($)": f"{r.total:,.2f}",
            "Revenue ($)": f"{_pnl_for(state, r.role)['revenue']:,.2f}",
            "Net P&L ($)": _signed_dollars(_pnl_for(state, r.role)["net"]),
        }
        for r in rows
    ])

    # ---- Narrative (DEB-05) ----
    st.subheader("What just happened")
    st.markdown(narrative_for(state))

    # ---- Play again (DEB-06) ----
    st.button(
        "Play again",
        on_click=on_reset,
        type="primary",
        key="debrief_reset_btn",
    )
