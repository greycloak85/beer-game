"""Streamlit entry point for the Beer Game.

Phase router pattern: a single st.session_state.phase string dispatches to
exactly one view's render() per rerun. All session_state mutation happens in
this file (via callbacks) — views are pure render functions.

See .planning/phases/02-ui-shell-per-turn-play/02-RESEARCH.md, Architecture
Pattern 1, for the canonical reference.
"""
import streamlit as st

from beergame.ai import ShipmentAnchorAndAdjustAgent
from beergame.config.scenarios import DEFAULT_SEED
from beergame.engine.state import Role, new_game
from beergame.engine.tick import advance_week, is_game_over
from beergame.views import debrief, play, rules, setup

st.set_page_config(
    page_title="Beer Game",
    page_icon=":beer_mug:",
    layout="centered",
)


def _init_session_state() -> None:
    """Guarded init — runs every rerun, sets values exactly once per session.

    Pitfall 1 in 02-RESEARCH.md: unguarded init wipes state on every click.
    Every assignment is gated on `"<key>" not in st.session_state`.
    """
    if "phase" not in st.session_state:
        st.session_state.phase = "rules"
    if "seen_rules" not in st.session_state:
        st.session_state.seen_rules = False
    if "player_role" not in st.session_state:
        st.session_state.player_role = Role.RETAILER
    if "seed" not in st.session_state:
        st.session_state.seed = DEFAULT_SEED
    if "game" not in st.session_state:
        st.session_state.game = None
    if "ai_agents" not in st.session_state:
        st.session_state.ai_agents = None


def go_to_setup() -> None:
    """Callback for the rules-screen 'Got it' button. Sets the seen-rules flag
    and flips the router to the setup phase."""
    st.session_state.seen_rules = True
    st.session_state.phase = "setup"


def start_game() -> None:
    """Callback for setup's 'Start game' form submit button.

    Reads st.session_state.player_role (bound by the radio's key) and
    st.session_state.seed (bound by the number_input's key). Constructs the
    GameState once and three Sterman agents once (Pitfall 8: agents MUST be
    instantiated once and reused across ticks so their smoothed_demand state
    accumulates).
    """
    role = st.session_state.player_role
    seed = int(st.session_state.seed)
    st.session_state.game = new_game(player_role=role, seed=seed)
    st.session_state.ai_agents = {
        r: ShipmentAnchorAndAdjustAgent()
        for r in Role
        if r != role
    }
    st.session_state.phase = "playing"


def submit_order() -> None:
    """Callback for play's 'Advance week' form submit button (Plan 03 attaches it).

    Reads the player's order via st.session_state["order_input"] (NOT via args=
    — Pitfall 2: args captures the value at form-render time, not submit time).
    Routes through engine.tick.advance_week with the persisted agents dict,
    replaces game state, and flips to 'done' when the engine reports game-over.
    """
    order_value = int(st.session_state.order_input)
    new_state = advance_week(
        state=st.session_state.game,
        player_order=order_value,
        ai_agents=st.session_state.ai_agents,
    )
    st.session_state.game = new_state
    if is_game_over(new_state):
        st.session_state.phase = "done"


def reset_game() -> None:
    """Callback for the debrief's 'Play again' button. Pops every game-related
    key so the next rerun's _init_session_state restores fresh defaults. Does
    NOT touch seen_rules — once a player has read the rules in this session,
    they don't have to re-read on a replay."""
    for key in ("phase", "player_role", "seed", "game", "ai_agents"):
        st.session_state.pop(key, None)
    if st.session_state.get("seen_rules"):
        st.session_state.phase = "setup"


_init_session_state()

phase = st.session_state.phase
if phase == "rules":
    rules.render(on_continue=go_to_setup)
elif phase == "setup":
    setup.render(on_start=start_game)
elif phase == "playing":
    play.render(state=st.session_state.game, on_submit=submit_order)
elif phase == "done":
    debrief.render(state=st.session_state.game, on_reset=reset_game)
else:
    st.error(f"Unknown phase: {phase!r}")
