"""Debrief screen — Phase-3 placeholder.

The full debrief (charts + narrative) ships in Phase 3. This file gives us
a working end-of-game screen so the play -> done transition is observable in
Plan 02. Asserts ``is_game_over(state)`` defensively (Pitfall 10).
"""
import streamlit as st

from beergame.engine.state import GameState
from beergame.engine.tick import is_game_over


def render(state: GameState, on_reset) -> None:
    """Render the placeholder debrief.

    Args:
        state: the final GameState. MUST satisfy ``is_game_over(state)``.
        on_reset: callback invoked when the user clicks "Play again" —
            app.py binds this to ``reset_game``.
    """
    assert is_game_over(state), (
        f"Debrief called with phase={state.phase!r} (week={state.week})"
    )

    st.title(":beer_mug: Game complete!")
    st.write(
        f"You played the **{state.player_role.name.title()}** through "
        f"{state.total_weeks} weeks."
    )
    st.info("Charts and narrative debrief are coming in Phase 3.")

    me = state.stations[state.player_role.value]
    final_cost = me.cost_history[-1] if me.cost_history else 0.0

    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("Your total orders placed", sum(me.orders_placed_history))
        st.metric("Final inventory", me.inventory)
    with col_b:
        st.metric("Final backlog", me.backlog)
        st.metric("Final cumulative cost", f"${final_cost:.2f}")

    st.button(
        "Play again",
        on_click=on_reset,
        type="primary",
        key="debrief_reset_btn",
    )
