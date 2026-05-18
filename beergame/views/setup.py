"""Setup screen (SETUP-02, SETUP-03, SETUP-04).

A single form with: station radio, seed input, "Start game" submit button.
The widget keys (player_role, seed) match the session_state keys initialized
by app.py::_init_session_state — Streamlit binds them automatically, and on
form submit the just-entered values land in session_state before the
on_click callback runs.
"""
import streamlit as st

from beergame.config.scenarios import DEFAULT_SEED  # noqa: F401 — referenced in docstring
from beergame.engine.state import Role


def render(on_start) -> None:
    """Render the station + seed form.

    Args:
        on_start: callback invoked on form submit — app.py binds this to
            ``start_game``, which constructs the GameState + the Sterman
            agents dict and routes to the play phase.
    """
    st.title(":beer_mug: Beer Game — Setup")
    st.write(
        "Pick a station to play. You'll see only that station's view "
        "during the game."
    )

    with st.form("setup_form"):
        st.radio(
            "Your station",
            options=list(Role),
            format_func=lambda r: r.name.title(),
            key="player_role",
            horizontal=True,
        )
        st.number_input(
            "Random seed (advanced — leave default for the canonical run)",
            min_value=0,
            step=1,
            key="seed",
        )
        st.form_submit_button(
            "Start game",
            on_click=on_start,
            type="primary",
        )
