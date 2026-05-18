"""Streamlit AppTest smoke coverage (PLAY-01..05 transition checks).

These are SOFT smoke tests: they exercise the four highest-value transitions
to give CI a safety net, but the primary verification for this phase remains
a manual 36-week playthrough. If AppTest behavior is surprising (widget
indexing is by render order and can shift if view layout changes), prefer
patching the test rather than reshaping the view.

Decisions captured here (from the planner orchestrator):
- AppTest is "soft inclusion" — 4 transition tests are enough.
- Manual playthrough is the fallback when AppTest doesn't cooperate.

# AppTest widget indexing in Streamlit 1.57.0 is by render order. If a future
# view-layout change shifts the button order, these tests may need to update
# their indices. The session_state assertions are the load-bearing part; the
# widget-path is the smoke layer over them.

Notes on the 1.57.0 AppTest API discovered while writing these tests:
- ``at.button`` includes BOTH ``st.button`` and ``st.form_submit_button``
  widgets, indexed by render order.
- ``at.form_submit_button`` is NOT a separate accessor in this version, so
  form-submits are reached via ``at.button[i]``.
- On the rules screen there is exactly one button ("Got it"), so ``at.button[0]``.
- On the setup screen there is exactly one button (the form's "Start game"
  submit), so ``at.button[0]``.
- On the play screen there is exactly one button (the form's "Advance week"
  submit), so ``at.button[0]``.
- On the debrief screen the only button is "Play again".
"""
from streamlit.testing.v1 import AppTest


def test_first_visit_lands_on_rules():
    """SETUP-01: a fresh session boots to the rules screen with seen_rules=False."""
    at = AppTest.from_file("app.py", default_timeout=5)
    at.run()
    assert at.session_state.phase == "rules"
    assert at.session_state.seen_rules is False
    assert not at.exception


def test_rules_continue_goes_to_setup():
    """SETUP-02: clicking the rules CTA flips phase to 'setup' and sets seen_rules=True."""
    at = AppTest.from_file("app.py", default_timeout=5).run()
    # The single button on the rules screen is "Got it — set up my game".
    at.button[0].click()
    at.run()
    assert at.session_state.phase == "setup"
    assert at.session_state.seen_rules is True
    assert not at.exception


def test_start_game_transitions_to_playing():
    """SETUP-03/04: submitting the setup form constructs a GameState + 3 AI
    agents and routes to the play view with state.week == 0."""
    at = AppTest.from_file("app.py", default_timeout=5).run()
    at.button[0].click()
    at.run()  # rules -> setup
    assert at.session_state.phase == "setup"
    # The only button on the setup screen is the form's "Start game" submit.
    # Defaults from app.py::_init_session_state: player_role=RETAILER, seed=42.
    at.button[0].click()
    at.run()  # setup -> playing
    assert at.session_state.phase == "playing"
    assert at.session_state.game is not None
    assert at.session_state.game.week == 0
    assert at.session_state.ai_agents is not None
    # Exactly 3 non-player Sterman agents (player is RETAILER by default).
    assert len(at.session_state.ai_agents) == 3
    assert not at.exception


def test_submit_order_advances_one_week():
    """PLAY-02: submitting an order via the form's 'Advance week' button
    advances state.week by exactly 1 and keeps phase=='playing'."""
    at = AppTest.from_file("app.py", default_timeout=5).run()
    at.button[0].click()
    at.run()  # rules -> setup
    at.button[0].click()
    at.run()  # setup -> playing
    assert at.session_state.phase == "playing"
    assert at.session_state.game.week == 0

    # Submit an order at the default value of 4.
    at.number_input[0].set_value(4)
    at.button[0].click()
    at.run()

    assert at.session_state.phase == "playing"
    assert at.session_state.game.week == 1
    # Player's own orders_placed_history grew by one — the submit reached the engine.
    me = at.session_state.game.stations[at.session_state.game.player_role.value]
    assert me.orders_placed_history == (4,)
    assert not at.exception


def test_week_36_submission_transitions_to_done():
    """PLAY-05: after the 36th order submit, app.py::submit_order detects
    is_game_over(new_state) and flips phase to 'done'. The next rerun routes
    to the debrief screen.
    """
    at = AppTest.from_file("app.py", default_timeout=30).run()
    at.button[0].click()
    at.run()  # rules -> setup
    at.button[0].click()
    at.run()  # setup -> playing

    # Submit 36 orders. Order value doesn't matter for this test; we only
    # check the phase transition at the boundary.
    for _ in range(36):
        at.number_input[0].set_value(4)
        at.button[0].click()
        at.run()

    assert at.session_state.game.week == 36
    assert at.session_state.phase == "done"
    # Debrief screen should now expose the "Play again" button.
    debrief_buttons = [b.label for b in at.button]
    assert "Play again" in debrief_buttons
    assert not at.exception
