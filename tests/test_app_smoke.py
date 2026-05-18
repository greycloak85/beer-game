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
import pytest
from streamlit.testing.v1 import AppTest

from beergame.engine.state import Role


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


def test_debrief_renders_with_real_content_after_36_weeks_as_retailer():
    """Phase 3 / Plan 02 / DEB-01..06: after a 36-week canonical RETAILER
    playthrough, the rewritten debrief view renders every Phase-3 element
    without exception:

    - Headline ``st.metric`` labeled "Bullwhip amplification" (DEB-03).
    - ``st.subheader`` "Cost breakdown" (DEB-04).
    - ``st.subheader`` "What just happened" (DEB-05).
    - ``st.button`` "Play again" (DEB-06).

    NOTE on AppTest limits (RESEARCH.md Pitfall 6): AppTest CANNOT inspect
    Plotly charts (``at.plotly_chart`` returns UnknownElement). The chart
    presence is covered by ``not at.exception`` here and structurally by
    ``tests/test_charts_orders_inventory.py`` at the go.Figure level.
    """
    at = AppTest.from_file("app.py", default_timeout=30).run()
    at.button[0].click()
    at.run()  # rules -> setup
    at.button[0].click()
    at.run()  # setup -> playing

    for _ in range(36):
        at.number_input[0].set_value(4)
        at.button[0].click()
        at.run()

    assert at.session_state.phase == "done"
    assert not at.exception, (
        f"Debrief rendered an exception: {[str(e) for e in at.exception]}"
    )

    metric_labels = [m.label for m in at.metric]
    assert any("Bullwhip amplification" in lbl for lbl in metric_labels), (
        f"Headline metric missing. Got labels: {metric_labels}"
    )

    subheader_values = [s.value for s in at.subheader]
    assert any("Cost breakdown" in v for v in subheader_values), (
        f"Cost breakdown subheader missing. Got: {subheader_values}"
    )
    assert any("What just happened" in v for v in subheader_values), (
        f"Narrative subheader missing. Got: {subheader_values}"
    )

    button_labels = [b.label for b in at.button]
    assert "Play again" in button_labels, (
        f"Play again button missing. Got: {button_labels}"
    )


@pytest.mark.parametrize(
    "role_name",
    ["RETAILER", "WHOLESALER", "DISTRIBUTOR", "FACTORY"],
)
def test_debrief_renders_for_each_player_role(role_name):
    """DEB-05 + AppTest end-to-end: a 36-week playthrough as each of the
    four player roles routes to the debrief and the narrative module
    renders without exception. Verifies all four templates are valid
    format strings and all interpolations resolve at runtime.

    The player role is set via ``at.session_state.player_role`` BEFORE
    clicking the setup form's "Start game" submit (the radio key in
    setup.py is bound to ``player_role``, so this is the supported
    pattern when the AppTest radio accessor doesn't accept the Role enum
    directly).
    """
    at = AppTest.from_file("app.py", default_timeout=30).run()
    at.button[0].click()
    at.run()  # rules -> setup

    # Set the player role via session_state, then submit setup form.
    at.session_state.player_role = Role[role_name]
    at.button[0].click()
    at.run()  # setup -> playing
    assert at.session_state.phase == "playing"
    assert at.session_state.game.player_role == Role[role_name]

    for _ in range(36):
        at.number_input[0].set_value(4)
        at.button[0].click()
        at.run()

    assert at.session_state.phase == "done", (
        f"{role_name}: expected phase=='done' after 36 weeks"
    )
    assert not at.exception, (
        f"{role_name}: debrief raised: {[str(e) for e in at.exception]}"
    )

    # Sanity-check the narrative section header rendered (the narrative
    # module ran successfully for this role).
    subheader_values = [s.value for s in at.subheader]
    assert any("What just happened" in v for v in subheader_values), (
        f"{role_name}: narrative subheader missing"
    )

    button_labels = [b.label for b in at.button]
    assert "Play again" in button_labels, (
        f"{role_name}: Play again button missing"
    )
