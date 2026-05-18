"""Per-turn play view — Plan 03 replaces this stub.

Plan 02 ships this file as a placeholder so the views package imports cleanly
and app.py can boot. Plan 03 fills in the real per-turn rendering: metrics,
order-history mini-chart, st.form with st.number_input, st.form_submit_button.
"""
import streamlit as st

from beergame.engine.state import GameState


def render(state: GameState, on_submit) -> None:
    """Plan 03 will replace this. Stub renders a 'work in progress' banner."""
    st.title(":beer_mug: Beer Game — Play (work in progress)")
    st.warning(
        "The per-turn play view is implemented in Plan 03. "
        "If you're seeing this in production, Plan 03 has not been merged yet."
    )
    st.write(
        f"Debug: phase={state.phase!r}, week={state.week}, "
        f"player_role={state.player_role.name}"
    )
