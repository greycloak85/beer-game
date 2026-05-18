# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-18)

**Core value:** A player completes one Beer Game round in one sitting and *sees* the bullwhip effect emerge in the post-game debrief — charts and narrative make the lesson land without an instructor in the room.
**Current focus:** Phase 3 — Debrief Charts + Narrative (Phase 2 COMPLETE)

## Current Position

Phase: 3 of 4 (Debrief Charts + Narrative) — IN PROGRESS
Plan: 1 of 2 complete in current phase
Status: Plan 03-01 COMPLETE — debrief metrics (variance_bullwhip_ratio + per_echelon_amplification + cost_breakdown) + 4-panel chart builder shipped; Plan 03-02 (debrief view assembly + narrative) ready to plan/execute
Last activity: 2026-05-18 — Completed Plan 03-01 (engine/metrics.py extended with 4 new public symbols including CostRow; beergame/charts package with build_four_panel(state) -> go.Figure containing 8 traces + week-5 vline; canonical_done_state fixture mirrors GATE 2; 71/71 pytest green; AST guard 4/4 clean; canonical seed=42 variance ratio = 35.38, monotonic upstream amplification R=3.43/W=12.81/D=29.27/F=35.38)

Progress: [███████░░░] 70%

## Performance Metrics

**Velocity:**
- Total plans completed: 7
- Average duration: 3.4min
- Total execution time: 24min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Simulation Engine + AI | 3/3 ✅ | 10min | 3.3min |
| 2. UI Shell + Per-Turn Play | 3/3 ✅ | 9min | 3min |
| 3. Debrief Charts + Narrative | 1/2 | 5min | 5min |
| 4. Deploy to Streamlit Community Cloud | 0/TBD | — | — |

**Recent Trend:**
- Last 5 plans: 01-03 (3min, 2 tasks, 2 files), 02-01 (3min, 2 tasks, 4 files), 02-02 (3min, 3 tasks, 8 files), 02-03 (3min, 2 tasks, 2 files), 03-01 (5min, 3 tasks, 6 files)
- Trend: steady velocity, Phase 1 + Phase 2 COMPLETE, Phase 3 underway (Plan 1 of 2 shipped); 71/71 tests passing (15 new for metrics + charts); AST guard still 4/4 clean

*Updated after each plan completion*

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 01-simulation-engine-ai P01 | 5min | 2 tasks | 19 files |
| Phase 01-simulation-engine-ai P02 | 2min | 2 tasks | 4 files |
| Phase 01-simulation-engine-ai P03 | 3min | 2 tasks | 2 files |
| Phase 02-ui-shell-per-turn-play P01 | 3min | 2 tasks | 4 files |
| Phase 02-ui-shell-per-turn-play P02 | 3min | 3 tasks | 8 files |
| Phase 02-ui-shell-per-turn-play P03 | 3min | 2 tasks | 2 files |
| Phase 03-debrief-charts-narrative P01 | 5min | 3 tasks | 6 files |

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
- [Phase 03-debrief-charts-narrative]: engine/metrics.py is now two-phase: Phase 1's `peak_orders` + max-based `bullwhip_ratio` (GATE 2 calibration metric, ratio still 2.000 at seed=42, UNTOUCHED) coexist with Phase 3's `variance_bullwhip_ratio` + `per_echelon_amplification` + `cost_breakdown` + `CostRow` (debrief metrics, DEB-03 + DEB-04). Both ratios measure bullwhip; the variance-based ratio is the DEB-03 headline (35.38 at seed=42), the max-based ratio is the Phase 1 calibration gate.
- [Phase 03-debrief-charts-narrative]: `beergame/charts/` is a NEW package mirroring the engine/ai/config purity contract — zero streamlit imports. AST guard still covers only engine/ai/config (chart purity enforced by convention and grep checks). View layer (Plan 03-02) is the ONLY place that imports both streamlit AND beergame.charts.
- [Phase 03-debrief-charts-narrative]: Variance metrics use `statistics.pvariance` (POPULATION variance, ddof=0) — we have the full 36-week series, not a sample. NO numpy, NO pandas anywhere in beergame/. Three defensive-guard layers: empty/length-1 history raises StatisticsError → return 0.0; denom == 0 → return 0.0; otherwise numer/denom. Future plans MUST keep these guards.
- [Phase 03-debrief-charts-narrative]: `cost_breakdown` formula mirrors `engine/costs.py::weekly_cost` EXACTLY (HOLDING_COST * max(0, inv) + BACKORDER_COST * bl, summed over history tuples). The reconciliation invariant (`row.total == state.stations[role.value].cost_history[-1]` to 1¢) is load-bearing — drift breaks the debrief table's trustworthiness. Tested in `test_cost_breakdown_reconciles_with_engine_cost_history`.
- [Phase 03-debrief-charts-narrative]: Week-5 vline at `CLASSIC_STEP_BREAK_WEEK + 1` (= 5) NOT `CLASSIC_STEP_BREAK_WEEK` (= 4) — CLASSIC_STEP_BREAK_WEEK is the LAST pre-step week, demand fires AT week 5. Code comment in `build_four_panel` documents the +1; tests assert `abs(s.x0 - 5) < 1e-9` for all 4 shapes (Pitfall 1 from 03-RESEARCH.md).
- [Phase 03-debrief-charts-narrative]: `canonical_done_state` fixture in `tests/conftest.py` is session-scoped and uses ALL-Sterman (mirrors GATE 2's `_all_sterman_agents()`) — NOT player-plays-constant-4. Constant-4 Retailer absorbs the demand shock into its own backlog without changing orders PLACED, so Sterman at W/D/F sees flat orders_received forever and the bullwhip silently dies (variance returns 0.0). Future fixture additions in this phase MUST use simulate_full_game(all-Sterman) for canonical bullwhip assertions.
- [Phase 03-debrief-charts-narrative]: Canonical seed=42 numbers (Plan 03-02 sanity-check reference): variance bullwhip ratio = 35.38, per-echelon R=3.43 / W=12.81 / D=29.27 / F=35.38 (monotonic upstream amplification), cost ledger R=$222.50 / W=$299.00 / D=$498.50 / F=$421.50 (all reconciling exactly via cost_history[-1]). Max-based ratio still 2.000 (Phase 1 GATE 2 intact).
- [Phase 03-debrief-charts-narrative]: Plotly chart structure tested directly against `go.Figure` (`fig.data`, `fig.layout.shapes`, `fig.layout.annotations`, `fig.layout.xaxis4.title.text`) — NOT via AppTest, which returns UnknownElement for chart elements. Plan 03-02's view tests MUST use the same pattern for any chart-shape assertions; AppTest is reserved for transition smoke (debrief renders, "Play again" button present).

### Pending Todos

Plan 03-02 (debrief view assembly + narrative). Needs to: (1) replace `beergame/views/debrief.py` placeholder body to render `build_four_panel` via `st.plotly_chart(fig, key="debrief_four_panel", width="stretch")`; (2) show variance_bullwhip_ratio as headline metric + per_echelon_amplification as four `st.metric` tiles + cost_breakdown as `st.table([{...}, ...])` (no pandas); (3) create `beergame/narrative/` package with four station-specific templates (DEB-05) interpolating overall ratio, per-echelon ratio, player station cost; (4) wire "Play again" to existing `app.py::reset_game` callback (DEB-06, already plumbed via `on_reset` param); (5) extend `tests/test_app_smoke.py` with a debrief-renders smoke + add unit tests for `narrative_for(state)` (≤200 words, mentions "bullwhip", contains player's role name).

### Blockers/Concerns

None. Phase 1 invariants still intact (max-based bullwhip ratio = 2.000, equilibrium inventory = 12 for 36 weeks). AST guard 4/4 (engine/ai/config layers streamlit-free; charts/ also streamlit-free by design). 71/71 pytest passing (56 prior + 9 metrics + 6 charts). No numpy/pandas anywhere in beergame/. The 4-panel chart builder and three new metrics are unit-tested at the go.Figure / pure-function level — Plan 03-02 has a clean, tested foundation to assemble.

## Session Continuity

Last session: 2026-05-18T21:35:11Z
Stopped at: Completed 03-debrief-charts-narrative/03-01-PLAN.md — engine/metrics.py extended with variance_bullwhip_ratio + per_echelon_amplification + cost_breakdown (CostRow dataclass) alongside untouched Phase 1 peak_orders + bullwhip_ratio. NEW package beergame/charts/ with build_four_panel(state) -> go.Figure: 8 traces (4 stations × {orders, inventory}), 4 vertical-line shapes at x=5 (one per panel from row="all") each annotated "Customer demand: 4 → 8", shared x-axis, height=700, "Week" title on bottom panel only. canonical_done_state fixture (session-scoped, all-Sterman via simulate_full_game) replaces the broken constant-4-player approach (Rule 1 auto-fix — constant-4 Retailer kills the bullwhip signal). 15 new tests (9 metrics covering empty-history, canonical > 1.0, all 4 Role keys, monotonic F > R, tuple order, total = h + b, total == cost_history[-1] reconciliation, max(0,x) on holding, zero-denominator; 6 charts covering 8 traces, vline at x=5, '4'+'8' annotation, "Week" axis title, station-name subplot titles, state.total_weeks-driven x range) all green. 71/71 pytest passing; AST guard 4/4. Canonical seed=42: variance ratio 35.38, per-echelon R=3.43/W=12.81/D=29.27/F=35.38 (monotonic upstream), cost ledger exact reconciliation. Plan 03-02 unblocked.
Resume file: .planning/phases/03-debrief-charts-narrative/03-02-PLAN.md
