---
phase: 02-ui-shell-per-turn-play
plan: 03
subsystem: per-turn-play-view
tags: [ui, streamlit, plotly, play-view, station-view, app-test, smoke-tests]

# Dependency graph
requires:
  - phase: 02-ui-shell-per-turn-play
    plan: 02
    provides: "app.py phase router + submit_order callback reading st.session_state['order_input'] + persisted ai_agents dict + play.py stub"
  - phase: 02-ui-shell-per-turn-play
    plan: 01
    provides: "StationView.last_shipment_received + shipments_received_history on StationState"
provides:
  - "beergame/views/play.py: full per-turn render(state, on_submit) — five-metric panel + Plotly orders-history mini-chart + st.form with st.number_input(key='order_input') + 'Advance week' submit button"
  - "tests/test_app_smoke.py: 5 AppTest smoke tests covering rules->setup, setup->playing, submit-advances-week, week-36-transitions-done, plus a first-visit sanity check"
  - "Phase 2 exit: SETUP-01..04 and PLAY-01..05 all satisfied; ready for Phase 3 (debrief charts + narrative)"
affects: [phase-03-debrief, phase-04-deploy]

# Tech tracking
tech-stack:
  added:
    - "plotly.graph_objects (already in requirements-dev.txt at plotly==6.7.0 from Plan 02-02; first runtime usage lands here)"
  patterns:
    - "PLAY-03 enforcement-by-construction: render() reads cross-station data ONLY via build_station_view(state, state.player_role). The only direct read of state.stations[i] is for the player's OWN station (i == state.player_role.value) to access orders_placed_history for the mini-chart — intrinsically the player's own data."
    - "Plotly width='stretch' replaces deprecated use_container_width=True (Streamlit 1.57.0)."
    - "Plotly key='player_order_history' gives the chart stable identity across reruns — Plotly preserves zoom/hover state instead of flickering (Pitfall 3 mitigation)."
    - "st.form(clear_on_submit=True) wrapping st.number_input(min_value=0, step=1, value=4, key='order_input') — Pitfall 12 (form batches keystrokes) + Pitfall 5 (min_value=0, step=1 block negatives/floats at the UI) + Pitfall 2 (key matches app.py's session_state read; no args= on form_submit_button)."
    - "No max_value on the number_input: AF-4 in research warns capping silently truncates Factory bullwhip orders (which can hit 30-80+)."
    - "Mini-chart x-axis bounded by len(orders_placed_history), NEVER hard-coded to 36 (Pitfall 18 — would imply future weeks the player hasn't played)."
    - "AppTest in Streamlit 1.57.0 exposes st.form_submit_button via at.button[i] (no separate at.form_submit_button accessor). Widget indexing is by render order; documented in test docstring."

key-files:
  created:
    - tests/test_app_smoke.py
  modified:
    - beergame/views/play.py

key-decisions:
  - "Five-metric layout: 2x2 grid (inventory, backlog | last_shipment_received, last_order_received) + standalone supply_line below. Orchestrator-approved mid-game disclosure of supply_line — it's the player's own pipeline, no information leak."
  - "Reading state.stations[role.value] for the player's OWN orders_placed_history is permitted by PLAY-03 — the rule blocks reads of OTHER stations' data, not the player's own. build_station_view does not expose orders_placed_history (it's a strategy artifact, not a directly observable view field)."
  - "value=4 default on the order input (equilibrium throughput) combined with clear_on_submit=True so the player consciously decides each week rather than rubber-stamping the prior value."
  - "Mini-chart title 'Your orders so far' is set via fig.update_layout(title=...) rather than st.subheader to keep the chart self-contained as one visual block."
  - "AppTest tests are 5 (not 3-4 as the plan estimated): the form_submit_button indexing turned out to be reliable in 1.57.0 (no widget-indexing brittleness), so all five tests pass cleanly. No tests skipped."

patterns-established:
  - "Pattern D — View-engine read constraint: cross-station projection via build_station_view; own-station own-data reads OK. Future views (debrief, charts) MUST follow the same boundary or document why their use case differs."
  - "Pattern E — Plotly-in-Streamlit-1.57.0: st.plotly_chart(fig, key='...', width='stretch'). Never use_container_width=True."
  - "Pattern F — AppTest as soft smoke: 5 tests cover the critical phase transitions; manual 36-week playthrough remains primary verification. Tests use at.button[i] indexing for both st.button and st.form_submit_button."

requirements-completed:
  - PLAY-01
  - PLAY-02
  - PLAY-03
  - PLAY-04
  - PLAY-05

# Metrics
duration: 2m 50s
completed: 2026-05-18
---

# Phase 02 Plan 03: Per-Turn Play View Summary

**Replaced the Plan-02 play stub with the full per-turn UI (five metrics + Plotly order-history mini-chart + st.form with number_input + 'Advance week' button) and added 5 AppTest smoke tests. Phase 2 exit: 56/56 pytest green, AST guard 4/4, streamlit run boots cleanly, full 36-week playthrough lands on the debrief placeholder.**

## Performance

- **Duration:** 2m 50s
- **Started:** 2026-05-18T21:04:09Z
- **Completed:** 2026-05-18T21:06:59Z
- **Tasks:** 2
- **Files created:** 1 (`tests/test_app_smoke.py`)
- **Files modified:** 1 (`beergame/views/play.py` — full replacement)

## Accomplishments

- **`beergame/views/play.py` rewritten as a 118-line, PLAY-01..05-compliant render function.** Reads cross-station data ONLY through `build_station_view(state, state.player_role)`; reads `state.stations[role.value]` ONLY for the player's own `orders_placed_history` (to plot the mini-chart). No reads of other stations' state. No reads of `state.customer_demand_history` (would leak future-week info).
- **Five-metric panel (PLAY-01):** inventory, backlog (left column); last shipment received, last order from downstream (right column); supply line (full-width below). All five sourced from the `StationView` projection — last_shipment_received via Plan 01's engine extension; supply_line via `sum(s.incoming_shipments)`.
- **Plotly order-history mini-chart (PLAY-01):** `st.plotly_chart(fig, key="player_order_history", width="stretch")`. X-axis weeks come from `range(1, len(orders_placed_history)+1)` — never hard-coded to 36 (Pitfall 18). Empty-state caption shown when the player hasn't yet placed an order. `use_container_width=True` deliberately avoided (deprecated in Streamlit 1.57.0; Pitfall 4).
- **Order form (PLAY-02):** `st.form("turn_form", clear_on_submit=True)` wrapping `st.number_input(min_value=0, step=1, value=4, key="order_input")` + `st.form_submit_button("Advance week", on_click=on_submit, type="primary")`. `key="order_input"` matches `app.py::submit_order`'s `st.session_state["order_input"]` read (Pitfall 2). No `max_value` — capping would silently truncate canonical bullwhip orders (AF-4).
- **Week counter (PLAY-04):** `f"Week {state.week + 1} of {state.total_weeks}"` — `state.week` is 0-indexed; first render shows "Week 1 of 36"; "Week 36 of 36" is the final render before the submit transitions to debrief.
- **Week-36 -> done transition (PLAY-05):** handled transparently by the existing `app.py::submit_order` callback (`is_game_over(new_state)` check after `advance_week` flips `phase` to `"done"`). The play view itself is week-agnostic — it just renders the current state every rerun.
- **`tests/test_app_smoke.py`:** 5 AppTest smoke tests, ALL PASSING (none skipped):
  - `test_first_visit_lands_on_rules` — SETUP-01: fresh session => `phase=="rules"`, `seen_rules is False`.
  - `test_rules_continue_goes_to_setup` — SETUP-02: rules-button click => `phase=="setup"`, `seen_rules is True`.
  - `test_start_game_transitions_to_playing` — SETUP-03/04: setup-form submit => `phase=="playing"`, `game.week==0`, `len(ai_agents)==3`.
  - `test_submit_order_advances_one_week` — PLAY-02: 'Advance week' click => `game.week==1`, `orders_placed_history==(4,)`.
  - `test_week_36_submission_transitions_to_done` — PLAY-05: 36 submits => `phase=="done"`, debrief screen shows 'Play again' button.
- **Full pytest suite: 56/56 passing** (51 from Plan 02-02 + 5 new AppTest tests). No regressions.
- **AST guard `tests/test_no_streamlit_import.py`: 4/4 passing** — engine/ai/config layers remain streamlit-free.
- **`streamlit run app.py` smoke:** HTTP 200, `_stcore/health` returns `ok`, no errors/exceptions/tracebacks in the server log.

## Task Commits

Each task was committed atomically:

1. **Task 1: replace play view stub with full per-turn UI** — `d0a65b1` (feat)
2. **Task 2: add AppTest smoke coverage for four key transitions** — `6e78b24` (test)

## Files Created/Modified

### Created (1)

- `tests/test_app_smoke.py` (120 lines) — 5 AppTest smoke tests using `streamlit.testing.v1.AppTest`. Module docstring captures the "soft inclusion" rationale and the 1.57.0 AppTest API gotcha (`st.form_submit_button` reached via `at.button[i]`, no separate accessor).

### Modified (1)

- `beergame/views/play.py` (118 lines, full replacement of the 23-line stub) — `render(state, on_submit) -> None`. Same signature as the stub so `app.py`'s router call site needs no update. Imports: `plotly.graph_objects as go`, `streamlit as st`, `from beergame.engine.state import GameState, build_station_view`.

## Decisions Made

- **Five-metric layout: 2x2 columns + 1 wide row.** Inventory and backlog on the left, last_shipment_received and last_order_received on the right, supply_line spanning the full width below. Clean readable grouping (own state | flow info | pipeline).
- **Mid-game supply-line disclosure** is explicitly part of the player's own data (their own pipeline pre-shipped to them). Orchestrator approved.
- **Reading `state.stations[role.value]` for the player's own `orders_placed_history`** is permitted because `orders_placed_history` is intrinsically the player's own data — they placed the orders. PLAY-03's no-cross-station rule applies to OTHER stations, not the player's own.
- **`build_station_view` does not expose `orders_placed_history`** (it's a strategy artifact, not a directly-observable view field), so the chart reads the player's own StationState directly. This is intentional and Plan 02-01's view-field set was explicitly scoped to *observable* quantities.
- **`value=4` default on the order input** (equilibrium throughput) combined with `clear_on_submit=True` — resets after each submit so the player consciously decides each week rather than rubber-stamping the prior value.
- **No `max_value` on the order input.** AF-4 in the research warns capping silently truncates canonical bullwhip orders, which can reach 30-80+ at the Factory under empirical Sterman. The whole point of the game is to see the bullwhip; capping it kills the lesson.
- **Mini-chart x-axis bounded by `len(orders_placed_history)`**, never hard-coded to 36 (Pitfall 18 — would imply future weeks). Each rerun, the chart shows exactly the weeks played so far.
- **Plotly mini-chart title set via `fig.update_layout(title=...)`** rather than `st.subheader`, keeping the chart self-contained as one visual block (clean for screenshots and Phase 3 chart extensions).
- **AppTest count: 5 (not 3-4 as estimated).** The plan flagged AppTest widget-indexing as potentially brittle in 1.57.0. In practice, `at.button[i]` cleanly indexes both `st.button` and `st.form_submit_button` (form_submit is reached via the same `at.button` collection — there is no separate `at.form_submit_button` accessor in this version). All 5 tests pass without skips.

## Deviations from Plan

### Auto-fixed Issues

None.

### Plan-vs-execution adjustments (documented, not deviations)

**1. AppTest API path: `at.button[i]` (not `at.form_submit_button[i]`)**

- **Found during:** Task 2 (AppTest API probe before writing test bodies).
- **Plan assumption:** Test code stubbed `at.form_submit_button[0]` as a possible accessor.
- **Reality (Streamlit 1.57.0):** `at.form_submit_button` does not exist as an AppTest attribute (`AttributeError`). Both `st.button` and `st.form_submit_button` widgets are exposed via the single `at.button` collection, indexed by render order.
- **Action:** Tests use `at.button[i]` throughout. Documented in test file's module docstring. Not a behavior change — same widgets exercised, same assertions made.
- **Files affected:** `tests/test_app_smoke.py` only.

**Total deviations:** 0 auto-fixed.
**Impact on plan:** None on behavior or scope. The Pattern-F note ("AppTest as soft smoke") in this summary captures the 1.57.0 API quirk for future plans.

## Issues Encountered

None. The plan was unusually clean — Plan 02-02 had locked the callback contract (`submit_order` reading `st.session_state["order_input"]`), Plan 02-01 had locked the engine projection (`last_shipment_received` in `StationView`), so this plan's work was almost entirely visual + form wiring. AppTest cooperated; widget indexing was reliable. No checkpoints triggered; no Rule-4 architectural decisions surfaced.

## User Setup Required

None for development. `.venv/bin/streamlit run app.py` works end-to-end:

1. Rules screen renders. Primer text visible. "Got it" button at bottom.
2. Click "Got it" → Setup screen renders. Radio shows 4 stations. Seed input default=42. "Start game" submit button.
3. Submit → Play view renders. Title: "Week 1 of 36 — You are the &lt;Role&gt;". Five metrics. Mini-chart caption (no orders yet). Order input default=4. "Advance week" button.
4. Submit 36 times → app auto-transitions to debrief ("Game complete!"); "Play again" returns to setup (NOT rules — `seen_rules` sticks within the session).

## Next Phase Readiness

- **Phase 2 is COMPLETE.** All 9 Phase-2 requirements satisfied: SETUP-01..04 (verified end-to-end via the manual smoke + first three AppTest tests) and PLAY-01..05 (verified via the play view's implementation + the two playing-phase AppTest tests).
- **Phase 3 (Debrief Charts + Narrative) is UNBLOCKED.** Replace `beergame/views/debrief.py`'s placeholder body with the real charts (orders-placed across all 4 stations, inventory-vs-backlog, cumulative cost) + narrative ("here's the bullwhip you just made"). The render signature `(state: GameState, on_reset)` is locked, and `app.py::reset_game` (the `on_reset` target) is already wired. The Plotly + width="stretch" + key= pattern is established here in Plan 02-03 and should carry forward.
- **Phase 4 (Deploy) is still on track.** `app.py` at the repo root, `.streamlit/config.toml` in place. Phase 4 needs only `requirements.txt` (with `streamlit==1.57.0` + `plotly==6.7.0` from `requirements-dev.txt` + the v1 engine deps).

## Self-Check: PASSED

- FOUND: `beergame/views/play.py` (118 lines, full implementation, `render(state, on_submit)` signature intact)
- FOUND: `tests/test_app_smoke.py` (120 lines, 5 tests defined)
- FOUND: commit `d0a65b1` (feat 02-03: replace play view stub with full per-turn UI)
- FOUND: commit `6e78b24` (test 02-03: add AppTest smoke coverage)
- VERIFIED: 56/56 pytest passing (51 prior + 5 new AppTest)
- VERIFIED: AST guard `tests/test_no_streamlit_import.py` 4/4 (engine/ai/config still streamlit-free)
- VERIFIED: `streamlit run app.py` boots, HTTP 200, `_stcore/health` returns `ok`, no errors in log
- VERIFIED: `play.render` signature is `(state, on_submit)` — unchanged from the stub
- VERIFIED: play view contains `build_station_view(state, role)` call (PLAY-03 enforced read path)
- VERIFIED: play view contains `st.form` + `key="order_input"` + `width="stretch"` (PLAY-02 + Pitfall 2 + Pitfall 4)
- VERIFIED: AppTest end-to-end shows 36 submits => `phase=="done"` and debrief 'Play again' button visible
- VERIFIED: AppTest end-to-end shows submit_order advances `state.week` by exactly 1

---
*Phase: 02-ui-shell-per-turn-play*
*Completed: 2026-05-18*
