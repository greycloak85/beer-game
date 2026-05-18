---
phase: 02-ui-shell-per-turn-play
verified: 2026-05-18T17:30:00Z
status: passed
score: 5/5 success criteria verified (9/9 requirements satisfied, 56/56 tests passing)
---

# Phase 2: UI Shell + Per-Turn Play Verification Report

**Phase Goal:** A Streamlit app shell with phase-routed navigation that lets a human pick a station, read the rules + bullwhip primer, and play a full 36-week game one week at a time against three Sterman AI opponents.

**Verified:** 2026-05-18T17:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth (Success Criterion) | Status | Evidence |
| --- | --- | --- | --- |
| 1 | User opens app to Rules + Bullwhip Primer on first visit; "Got it" -> setup (radio R/W/D/F + seed input + Start game) -> play | VERIFIED | `app.py:31-32` defaults `phase="rules"`; `rules.py:64-71` renders primer + "Got it" CTA bound to `go_to_setup`; `setup.py:30-47` form has `st.radio(options=list(Role), key="player_role")` + `st.number_input(key="seed")` + `st.form_submit_button("Start game", on_click=on_start)`; `app.py::start_game` flips phase to "playing". AppTest `test_first_visit_lands_on_rules`, `test_rules_continue_goes_to_setup`, `test_start_game_transitions_to_playing` all pass. |
| 2 | During play, user sees ONLY their own station's view (no surface exposes other stations or future demand) | VERIFIED | `play.py:42` `view = build_station_view(state, role)` is the only cross-station read; `play.py:71` `me = state.stations[role.value]` reads only the player's own station for `orders_placed_history`; grep confirms NO reads of `state.stations[other_index]` and NO reads of `state.customer_demand_history` (only mentioned in negative-form docstring at line 12). |
| 3 | Per-week: `st.number_input(min_value=0, step=1)` inside `st.form` + "Advance week" advances one week | VERIFIED | `play.py:101-118` exact pattern: `with st.form("turn_form", clear_on_submit=True): st.number_input(..., min_value=0, step=1, value=4, key="order_input"); st.form_submit_button("Advance week", on_click=on_submit)`. AppTest `test_submit_order_advances_one_week` proves `state.week` advances 0->1 and `orders_placed_history == (4,)`. |
| 4 | After week-36 submit, app auto-transitions to debrief view (placeholder OK) | VERIFIED | `app.py::submit_order` (lines 80-88): after `advance_week`, calls `is_game_over(new_state)` and flips `phase = "done"`; router (line 109-110) dispatches `phase == "done"` to `debrief.render`. `debrief.py:21-23` asserts `is_game_over(state)` defensively. AppTest `test_week_36_submission_transitions_to_done` proves after 36 submits `state.week == 36`, `phase == "done"`, and "Play again" button is visible on debrief. |
| 5 | Page refresh resets cleanly; full manual playthrough completes without exceptions | VERIFIED | `_init_session_state` (app.py:25-42) uses guarded `if "<key>" not in st.session_state` for all six keys (phase, seen_rules, player_role, seed, game, ai_agents); browser refresh wipes session_state, next rerun re-initializes to phase="rules". AppTest end-to-end 36-week submission test runs to completion with `not at.exception` assertion — no exceptions throughout. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `app.py` | Phase router + 4 callbacks + session_state init | VERIFIED | 112 lines; 4 callbacks (`go_to_setup`, `start_game`, `submit_order`, `reset_game`); 6 guarded session_state keys; router dispatches phase in {"rules", "setup", "playing", "done"}; imports streamlit, ShipmentAnchorAndAdjustAgent, Role, new_game, advance_week, is_game_over, and all 4 views. |
| `beergame/views/__init__.py` | Package re-exporting render entries | VERIFIED | 9 lines; re-exports rules, setup, play, debrief. |
| `beergame/views/rules.py` | Primer screen + "Got it" button | VERIFIED | 71 lines; defines `render(on_continue)`; renders `:beer_mug: Beer Game — Rules` title, chain diagram, week sequence, visibility/costs/bullwhip explanation; primary CTA wired to `on_continue`. |
| `beergame/views/setup.py` | `st.form` with radio + seed + submit | VERIFIED | 47 lines; defines `render(on_start)`; `st.form("setup_form")` contains `st.radio(options=list(Role), key="player_role")` + `st.number_input(min_value=0, step=1, key="seed")` + `st.form_submit_button("Start game", on_click=on_start)`. |
| `beergame/views/play.py` | Full per-turn view | VERIFIED | 118 lines; defines `render(state, on_submit)`; only cross-station read is `build_station_view(state, role)`; five metrics (inventory, backlog, last_shipment_received, last_order_received, supply_line); Plotly chart with `width="stretch"`, `key="player_order_history"`; form contains `st.number_input(min_value=0, step=1, value=4, key="order_input")` + `st.form_submit_button("Advance week", on_click=on_submit)`. |
| `beergame/views/debrief.py` | Placeholder + `is_game_over` assert | VERIFIED | 48 lines; defines `render(state, on_reset)`; line 21 asserts `is_game_over(state)`; renders 4 summary metrics + "Play again" button bound to `on_reset`. |
| `.streamlit/config.toml` | Theme + server config | VERIFIED | 13 lines; `[theme]` (base="light", primaryColor="#7B3F00"), `[server]` (headless=true), `[browser]` (gatherUsageStats=false). |
| `tests/test_app_smoke.py` | AppTest transition coverage | VERIFIED | 120 lines; 5 AppTest tests, ALL 5 PASSING (planner specified 3-4 with up to 1 skippable; actually exceeded — 5/5 pass including the full 36-week game-over transition test). |
| `tests/test_shipments_received_history.py` | Plan 01 regression test | VERIFIED | Part of 56-test suite; all pass. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `app.py::start_game` | `new_game` + `ShipmentAnchorAndAdjustAgent` | dict comprehension over non-player Roles persisted to `session_state.ai_agents` | WIRED | `app.py:64-68` exact pattern; agents instantiated ONCE per game; `submit_order` (line 84) passes the same dict to every `advance_week` call so `smoothed_demand` accumulates (Pitfall 8 mitigation). |
| `app.py::_init_session_state` | `st.session_state.phase` | Guarded `if "phase" not in st.session_state` | WIRED | `app.py:31-42` — all six keys guarded; pattern repeated identically for each. |
| `app.py` top-level dispatch | `rules.render` / `setup.render` / `play.render` / `debrief.render` | if/elif on `st.session_state.phase` | WIRED | `app.py:103-112` exact pattern. Unknown phase falls through to `st.error` for defense. |
| `setup.py::st.form_submit_button` | `app.py::start_game` | `on_click=on_start` (the param the render takes) | WIRED | `setup.py:43-47` form_submit_button receives `on_click=on_start`; app.py passes `start_game` as the `on_start` arg. |
| `play.py::render` | `build_station_view(state, state.player_role)` | Only cross-station read path | WIRED | `play.py:41-42`: `role = state.player_role; view = build_station_view(state, role)`. No alternative read paths exist. |
| `play.py::st.form_submit_button` | `app.py::submit_order` | `on_click=on_submit` | WIRED | `play.py:114-118`; signature `render(state, on_submit)` receives the callback from `app.py:108`. |
| `play.py::st.number_input` | `st.session_state['order_input']` | `key="order_input"` matches `submit_order`'s read | WIRED | `play.py:110` declares `key="order_input"`; `app.py:80` reads `int(st.session_state.order_input)` — keys match exactly. Pitfall 2 mitigation (no `args=`). |
| `play.py::st.plotly_chart` | `Plotly Figure from orders_placed_history` | `width="stretch"`, `key="player_order_history"` | WIRED | `play.py:74-94`; uses `width="stretch"` (NOT deprecated `use_container_width=True`); `key="player_order_history"` for stable identity. |
| `tests/test_app_smoke.py` | `app.py` phase transitions | `AppTest.from_file('app.py').run()` | WIRED | All 5 AppTest tests use `AppTest.from_file("app.py", default_timeout=...)` and assert against `at.session_state.phase`, `at.session_state.game.week`, etc. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| SETUP-01 | 02-02 | First-visit Rules + Bullwhip Primer screen | SATISFIED | `rules.py` renders primer text covering chain diagram, week sequence, visibility, costs ($0.50 hold / $1.00 backlog), bullwhip (2-4x amplification). `_init_session_state` defaults phase="rules" on first visit. AppTest `test_first_visit_lands_on_rules` passes. |
| SETUP-02 | 02-02 | Station radio (R/W/D/F) | SATISFIED | `setup.py:30-36`: `st.radio("Your station", options=list(Role), format_func=..., key="player_role", horizontal=True)`. Renders 4 stations. |
| SETUP-03 | 02-02 | Optional seed input with fixed default for canonical run | SATISFIED | `setup.py:37-42`: `st.number_input("Random seed...", min_value=0, step=1, key="seed")`; default comes via session_state from `DEFAULT_SEED` (app.py:38). |
| SETUP-04 | 02-02 | "Start game" transitions setup -> first turn | SATISFIED | `setup.py:43-47`: `st.form_submit_button("Start game", on_click=on_start, type="primary")`. `start_game` callback constructs GameState + 3 Sterman agents + flips phase to "playing". AppTest `test_start_game_transitions_to_playing` passes. |
| PLAY-01 | 02-01, 02-03 | Inventory, backlog, last_shipment_received, last_order_received, order-history mini-chart | SATISFIED | `play.py:56-64` renders 5 metrics from `view`; `play.py:71-96` renders Plotly mini-chart of `me.orders_placed_history`. Plan 02-01 added `shipments_received_history` engine field + `last_shipment_received` view field (7 regression tests pass). |
| PLAY-02 | 02-03 | `st.number_input(min_value=0)` inside `st.form` + "Advance week" | SATISFIED | `play.py:101-118` exact pattern with `min_value=0, step=1, value=4, key="order_input"` inside `st.form("turn_form", clear_on_submit=True)`; submit button labeled "Advance week" bound to `on_submit`. No `max_value` — bullwhip not silently capped. |
| PLAY-03 | 02-03 | No cross-station reads, no future demand visible | SATISFIED | Grep confirms `play.py` only reads `state.stations[role.value]` (player's own station); zero reads of `state.customer_demand_history` (mentioned only in negative-form docstring at line 12 explaining what NOT to read). All cross-station data flows through `build_station_view` which Phase 1 engine-enforced to expose only locally-knowable info. |
| PLAY-04 | 02-03 | Week counter "Week N of 36" | SATISFIED | `play.py:47-50` `st.title(f":beer_mug: Week {state.week + 1} of {state.total_weeks} — You are the {role.name.title()}")`. Uses `state.week + 1` so first rendered week reads "Week 1 of 36" (Pitfall 6 mitigation). |
| PLAY-05 | 02-03 | After 36 weeks, auto-transition to debrief | SATISFIED | `app.py::submit_order` flips `phase="done"` when `is_game_over(new_state)` returns True; router dispatches to `debrief.render`. AppTest `test_week_36_submission_transitions_to_done` runs 36 submissions and asserts `state.week == 36`, `phase == "done"`, "Play again" button on debrief. |

**ORPHANED requirements check:** REQUIREMENTS.md maps 9 IDs (SETUP-01..04, PLAY-01..05) to Phase 2. Plans 02-01..02-03 collectively claim all 9 IDs (02-01 claims PLAY-01; 02-02 claims SETUP-01..04; 02-03 claims PLAY-01..05). **Zero orphaned requirements.**

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| - | - | None detected | - | Code is clean: no TODO/FIXME/HACK/placeholder comments in any phase-2 artifact. No `use_container_width=True` (only mentioned in a comment explaining what NOT to use). No `time.sleep()`. No `@st.cache_data`/`@st.cache_resource`. No `import pandas`/`numpy` in views. The "work in progress" stub from Plan 02 was replaced by the real implementation in Plan 03. |

### Specific Verification Points (from request)

| Check | Status | Evidence |
| --- | --- | --- |
| `play.py` MUST NOT render `state.stations[other_role]` or `state.customer_demand_history` for non-Retailer (PLAY-03 enforcement) | PASSED | Only `state.stations[role.value]` (player's own); zero `customer_demand_history` reads (line 12 mention is a negative-form docstring). `build_station_view` is the only cross-station path. |
| Sterman agents instantiated ONCE in `start_game` and persisted in `session_state.ai_agents` (not re-created per tick) | PASSED | `app.py:64-68` constructs `{r: ShipmentAnchorAndAdjustAgent() for r in Role if r != role}` once inside `start_game`; `submit_order` (line 84) reads the persisted dict, never re-instantiates. AppTest asserts `len(at.session_state.ai_agents) == 3`. |
| Engine remains streamlit-free (AST guard test passes) | PASSED | `tests/test_no_streamlit_import.py` — 4 tests pass. Direct grep over `beergame/engine`, `beergame/ai`, `beergame/config` returns zero matches for `import streamlit` / `from streamlit`. |
| Both pytest GATEs from Phase 1 still pass (no regression) | PASSED | `tests/test_bullwhip_emerges.py` — 5 tests pass; `tests/test_equilibrium.py` — 6 tests pass. Full suite: 56/56 tests pass (44 Phase 1 + 7 Plan 02-01 + 5 Plan 02-03 = 56). |

### Test Suite Status

```
tests/test_app_smoke.py ..... (5 pass)
tests/test_bullwhip_emerges.py ..... (5 pass)
tests/test_costs.py (passes — in count)
tests/test_determinism.py (passes — in count)
tests/test_equilibrium.py ...... (6 pass)
tests/test_no_streamlit_import.py .... (4 pass)
tests/test_shipments_received_history.py ....... (7 pass — Plan 02-01)
tests/test_station_view_visibility.py (passes)
tests/test_sterman_heuristic.py (passes)
tests/test_tick_invariants.py (passes)

TOTAL: 56 passed in 1.02s
```

### Human Verification Required

None for status=passed. The 5 AppTest tests cover all four critical transitions (rules->setup, setup->playing, single-week-advance, week-36->done) including a real 36-week playthrough with `not at.exception` assertion. A live `streamlit run app.py` walkthrough would only re-confirm the same observable behaviors AppTest already proves headlessly.

Optional UX confirmations (NOT blocking; status=passed regardless):
- Visual styling of the amber primaryColor (#7B3F00) on primary buttons
- Plotly chart rendering quality / hover interactions
- Markdown rendering of the chain diagram code-block in `rules.py`

### Gaps Summary

No gaps. All 5 ROADMAP success criteria are met, all 9 requirements (SETUP-01..04, PLAY-01..05) are satisfied, all 9 must-have key links are wired, all required artifacts are substantive (not stubs), full 56/56 test suite passes including 5 end-to-end AppTest transitions, AST guard confirms engine layer remains streamlit-free, and Sterman agents are instantiated once + persisted correctly per Pitfall 8.

Phase 2 exit posture: ready for Phase 3 (Debrief Charts + Narrative). The play -> done -> debrief routing is in place; the debrief view is a working placeholder that Phase 3 will fill in.

---

_Verified: 2026-05-18T17:30:00Z_
_Verifier: Claude (gsd-verifier)_
