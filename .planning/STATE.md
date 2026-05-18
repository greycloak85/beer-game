# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-18)

**Core value:** A player completes one Beer Game round in one sitting and *sees* the bullwhip effect emerge in the post-game debrief — charts and narrative make the lesson land without an instructor in the room.
**Current focus:** Phase 3 — Debrief Charts + Narrative (Phase 2 COMPLETE)

## Current Position

Phase: 2 of 4 (UI Shell + Per-Turn Play) — COMPLETE
Plan: 3 of 3 complete in current phase
Status: Phase 2 COMPLETE — full per-turn play view + AppTest smoke coverage shipped; Phase 3 (Debrief Charts + Narrative) unblocked
Last activity: 2026-05-18 — Completed Plan 02-03 (beergame/views/play.py full per-turn UI with 5 metrics + Plotly mini-chart + st.form order input; tests/test_app_smoke.py with 5 AppTest tests; 56/56 pytest green; AST guard 4/4; streamlit run app.py drives a complete 36-week playthrough ending on the debrief placeholder)

Progress: [██████░░░░] 60%

## Performance Metrics

**Velocity:**
- Total plans completed: 6
- Average duration: 3.2min
- Total execution time: 19min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Simulation Engine + AI | 3/3 ✅ | 10min | 3.3min |
| 2. UI Shell + Per-Turn Play | 3/3 ✅ | 9min | 3min |
| 3. Debrief Charts + Narrative | 0/TBD | — | — |
| 4. Deploy to Streamlit Community Cloud | 0/TBD | — | — |

**Recent Trend:**
- Last 5 plans: 01-02 (2min, 2 tasks, 4 files), 01-03 (3min, 2 tasks, 2 files), 02-01 (3min, 2 tasks, 4 files), 02-02 (3min, 3 tasks, 8 files), 02-03 (3min, 2 tasks, 2 files)
- Trend: steady velocity, Phase 1 + Phase 2 both COMPLETE, 56/56 tests passing (added 5 AppTest smokes), AST guard still 4/4 clean

*Updated after each plan completion*

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 01-simulation-engine-ai P01 | 5min | 2 tasks | 19 files |
| Phase 01-simulation-engine-ai P02 | 2min | 2 tasks | 4 files |
| Phase 01-simulation-engine-ai P03 | 3min | 2 tasks | 2 files |
| Phase 02-ui-shell-per-turn-play P01 | 3min | 2 tasks | 4 files |
| Phase 02-ui-shell-per-turn-play P02 | 3min | 3 tasks | 8 files |
| Phase 02-ui-shell-per-turn-play P03 | 3min | 2 tasks | 2 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Phase 1]: Engine is pure-Python — zero `streamlit` imports — so pytest can verify the canonical bullwhip headlessly before any UI work.
- [Phase 1]: Sterman *empirical* parameters (α≈0.26, β≈0.34, θ≈0.36, S′≈17), not JASSS 2014 "optimal" values — empirical produces the lesson, optimal silently kills it.
- [Phase 1]: Two pytest gates exit Phase 1 — equilibrium regression and bullwhip calibration (ratio ∈ [2.0, 4.0]). No UI work begins until both pass.
- [Phase 4]: Deploy uses `requirements.txt` only — `uv.lock` is NOT committed (Streamlit Cloud's dependency-file priority would pick it up; yanked transitives can wedge builds).
- [Phase 01-simulation-engine-ai]: ORDER_PIPELINE_LEN_FACTORY = 1 (NOT 0); Factory inbound order channel uses canonical 1-week mailing delay (BLOCKER 1 fix verified — Factory inventory stays at 12, not 16, under equilibrium)
- [Phase 01-simulation-engine-ai]: Transient intra-tick fields on StationState (compare=False, repr=False) carry data between named tick steps; zeroed in step 3 and step 5
- [Phase 01-simulation-engine-ai]: Agent Protocol imports StationView under TYPE_CHECKING to break engine.tick <-> ai.base circular import; runtime isinstance check still works via runtime_checkable
- [Phase 01-simulation-engine-ai]: S' (desired_inventory) locked at 17.0 in beergame/ai/sterman.py per Sterman 1989 median. If Plan 03 GATE 2 misses [2.0, 4.0], tune S' here — NEVER widen the test bounds.
- [Phase 01-simulation-engine-ai]: ShipmentAnchorAndAdjustAgent is a mutable @dataclass (not frozen) because decide_order updates self.smoothed_demand each week; per-agent forecast state kept on the agent, not threaded through StationView.
- [Phase 01-simulation-engine-ai]: ENG-01 enforced structurally via AST-walk pytest test (not grep) — catches `import streamlit` and `from streamlit.* import ...` cleanly, prints file:line on failure, sabotage-verified.
- [Phase 01-simulation-engine-ai]: GATE 1 uses ConstantOrderAgent(4) (per updated AI-04), NOT ShipmentAnchorAndAdjustAgent — empirical Sterman orders 3 at perfect equilibrium, so "inv=12 AND order=4 forever" is mutually unsatisfiable under Sterman. GATE 1 isolates engine arithmetic; GATE 2 measures bullwhip.
- [Phase 01-simulation-engine-ai]: GATE 2 canonical bullwhip ratio = 2.000 under seed=42 (factory_peak=22, retailer_peak=11) — inside [2.0, 4.0]. No S' tuning required; S' remains 17.0. Monotonic upstream amplification: R=11 <= W=16 <= D=21 <= F=22.
- [Phase 01-simulation-engine-ai]: BLOCKER 1 fix verified at full-simulation level — Factory inventory stays at 12 for all 36 weeks under all-ConstantOrderAgent(4); the old broken design (ORDER_PIPELINE_LEN_FACTORY=0) would have produced Factory inventory=16. Future contributors forbidden from regressing this to shrink the bullwhip.
- [Phase 01-simulation-engine-ai]: Bullwhip ratio bounds [2.0, 4.0] are load-bearing — only correctness check before Phase 2. The GATE 2 failure message explicitly names empirical-vs-optimal Sterman trap (cause #1), points to S' tuning in [12, 20] as the ONLY acceptable knob, and forbids regressing ORDER_PIPELINE_LEN_FACTORY.
- [Phase 02-ui-shell-per-turn-play]: Engine API extended additively for PLAY-01 — `StationState.shipments_received_history: tuple[int, ...]` mirrors `shipments_sent_history`, growing once per tick in step 3 (record_state). View layer reads `view.last_shipment_received` directly instead of deriving from indirect history slices.
- [Phase 02-ui-shell-per-turn-play]: New transient `_pending_shipment_received` (compare=False, repr=False) carries step-1's `incoming_shipments[0]` into step-3's history append. Preserves the "all histories grow exactly once per tick, in step 3" invariant; mirrors the existing `_demand_to_fill` / `_shipped_this_tick` pattern.
- [Phase 02-ui-shell-per-turn-play]: `StationView.last_shipment_received: int = 0` (defaulted) — required so RetailerView's existing `customer_demand: int = 0` keeps a legal frozen-dataclass subclass field order. Empty-history fallback to EQUILIBRIUM_THROUGHPUT lives in `build_station_view`, not on the dataclass default.
- [Phase 02-ui-shell-per-turn-play]: Plan 02-01 verified zero behavioral drift — bullwhip ratio still exactly 2.0000 under seed=42, equilibrium inventory still 12 for 36 weeks, AST guard still streamlit-clean. Future contributors forbidden from re-deriving `last_shipment_received` in the view layer.
- [Phase 02-ui-shell-per-turn-play]: app.py lives at repo ROOT, not under beergame/. This is the path `streamlit run` and Streamlit Cloud both target; Phase 4 deploy is a no-op for app discovery.
- [Phase 02-ui-shell-per-turn-play]: Streamlit import boundary enforced — only `app.py` and `beergame/views/*` import streamlit. `beergame/{engine,ai,config}/*` remain pure-Python (AST guard 4/4 still passes). Future contributors forbidden from importing streamlit anywhere under the engine layer.
- [Phase 02-ui-shell-per-turn-play]: Phase-router pattern — single `st.session_state.phase` string dispatches to exactly one `view.render()` per rerun (rules/setup/playing/done). Top-level dispatch is the ONLY place phase is read from session_state; all writes go through the four callbacks (go_to_setup, start_game, submit_order, reset_game).
- [Phase 02-ui-shell-per-turn-play]: Sterman agent persistence — `start_game` instantiates `ShipmentAnchorAndAdjustAgent` ONCE per non-player Role and stores the dict in `session_state.ai_agents`. The same dict is threaded through every `advance_week` call so `smoothed_demand` accumulates across ticks (Pitfall 8). Future contributors MUST NOT re-instantiate agents in `submit_order`.
- [Phase 02-ui-shell-per-turn-play]: `submit_order` reads the player's order via `st.session_state["order_input"]`, NEVER via `args=` (Pitfall 2: args captures the value at form-render time, not submit time). Plan 03's play view MUST use the matching `key="order_input"` on its `st.number_input`.
- [Phase 02-ui-shell-per-turn-play]: `play.py` shipped as a Plan-02 stub to close the import graph; Plan 03 replaces the body. The on_submit callback contract is already locked (reads `st.session_state["order_input"]`).
- [Phase 02-ui-shell-per-turn-play]: streamlit + plotly added to `requirements-dev.txt`, NOT `requirements.txt`. Phase 4 owns the deploy-time pin file. Both pins: `streamlit==1.57.0`, `plotly==6.7.0`.
- [Phase 02-ui-shell-per-turn-play]: `reset_game` deliberately preserves `seen_rules` so in-session replay skips the primer; browser refresh still wipes everything (Streamlit default), preserving SETUP-01's first-visit invariant across browser sessions.
- [Phase 02-ui-shell-per-turn-play]: Setup-form widgets use `key=` ONLY (no `value=`) — passing both raises StreamlitAPIException. The session_state slot supplies the default; widget reads from + writes to that slot directly.
- [Phase 02-ui-shell-per-turn-play]: PLAY-03 enforced in play.py: render() reads cross-station data ONLY via `build_station_view(state, state.player_role)`. The only direct `state.stations[i]` read is for the player's OWN station (i == player_role.value) for `orders_placed_history` (intrinsically the player's own data — they placed the orders). NO reads of other stations' state, NO reads of `state.customer_demand_history`. Future plans MUST honor this boundary or document why their use case differs.
- [Phase 02-ui-shell-per-turn-play]: Plotly chart calls in 1.57.0 use `st.plotly_chart(fig, key="...", width="stretch")` — NEVER `use_container_width=True` (deprecated, removed-after-grace in 1.57.0). Stable `key=` gives the chart identity across reruns so zoom/hover state survives (Pitfall 3 flicker mitigation).
- [Phase 02-ui-shell-per-turn-play]: Per-turn order form: `st.form("turn_form", clear_on_submit=True)` wrapping `st.number_input(min_value=0, step=1, value=4, key="order_input")` + `st.form_submit_button("Advance week", on_click=on_submit, type="primary")`. NO `max_value` (AF-4: capping silently truncates canonical bullwhip orders that reach 30-80+ at Factory). NO `args=` on the submit button (Pitfall 2: args captures value at render time, not submit time — the callback reads `st.session_state["order_input"]`).
- [Phase 02-ui-shell-per-turn-play]: Mini-chart x-axis bounded by `len(orders_placed_history)`, NEVER hard-coded to 36 (Pitfall 18 — would imply future weeks the player hasn't played).
- [Phase 02-ui-shell-per-turn-play]: AppTest in Streamlit 1.57.0 exposes `st.form_submit_button` via `at.button[i]` (the same `at.button` collection holds both `st.button` AND `st.form_submit_button` widgets, indexed by render order). There is NO `at.form_submit_button` accessor. Future test plans MUST use `at.button[i]` to reach form submits.

### Pending Todos

None — Plan 02-03 complete; Phase 2 COMPLETE. Next: Phase 3 (Debrief Charts + Narrative) is fully unblocked. Phase 3 will replace `beergame/views/debrief.py`'s placeholder body with the real charts (orders-placed across all 4 stations, inventory-vs-backlog, cumulative cost) + narrative explaining the bullwhip the player just produced.

### Blockers/Concerns

None. Phase 1 invariants still intact (bullwhip ratio = 2.000, equilibrium inventory = 12 for 36 weeks). AST guard 4/4 (engine/ai/config layers streamlit-free). 56/56 pytest passing (51 prior + 5 new AppTest smoke). `streamlit run app.py` smoke test passes (HTTP 200, `_stcore/health` = ok), full 36-week playthrough completes without exceptions and lands on the debrief placeholder.

## Session Continuity

Last session: 2026-05-18T21:06:59Z
Stopped at: Completed 02-ui-shell-per-turn-play/02-03-PLAN.md — Per-turn play view fully implemented: 5 metrics (inventory, backlog, last_shipment_received, last_order_received, supply_line) + Plotly orders-history mini-chart (width="stretch", key="player_order_history") + st.form with st.number_input(min_value=0, step=1, value=4, key="order_input") + "Advance week" form_submit_button. PLAY-03 enforced — cross-station reads ONLY via build_station_view. 5 AppTest smoke tests cover: rules->setup, setup->playing, submit-advances-week, week-36-transitions-done, first-visit-sanity. 56/56 pytest green; AST guard 4/4. Phase 2 COMPLETE.
Resume file: .planning/phases/03-debrief-charts-narrative/ (Phase 3 to be planned)
