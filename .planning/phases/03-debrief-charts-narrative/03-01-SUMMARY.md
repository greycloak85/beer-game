---
phase: 03-debrief-charts-narrative
plan: 01
subsystem: charts
tags: [plotly, statistics, pvariance, dataclass, subplots, make_subplots, add_vline, bullwhip, debrief]

# Dependency graph
requires:
  - phase: 01-simulation-engine-ai
    provides: GameState, StationState history tuples (orders_placed_history, inventory_history, backlog_history, cost_history), Role enum, simulate_full_game, ShipmentAnchorAndAdjustAgent, peak_orders + max-based bullwhip_ratio (Phase 1 GATE 2 metrics kept intact)
  - phase: 02-ui-shell-per-turn-play
    provides: streamlit-purity precedent in beergame/ subpackages (Plan 03-01 mirrors the engine/ai/config AST-guarded purity contract for the new charts/ package)
provides:
  - "engine/metrics.py: 3 new public symbols (variance_bullwhip_ratio, per_echelon_amplification, cost_breakdown) + CostRow dataclass — Phase 1 peak_orders + bullwhip_ratio kept unchanged"
  - "beergame/charts package: 1 new public symbol (build_four_panel) returning go.Figure with 8 traces + week-5 vline annotated 'Customer demand: 4 → 8'"
  - "tests/conftest.py: session-scoped canonical_done_state fixture (all-Sterman seed=42, mirrors Phase 1 GATE 2) shared across metric + chart tests"
  - "Cost reconciliation invariant: per-station cost_breakdown total == cost_history[-1] to floating-point tolerance (1¢ via pytest.approx)"
  - "15 new pytest cases (9 metrics + 6 charts) verifying DEB-01, DEB-02, DEB-03, DEB-04 at the go.Figure / pure-function level"
affects: [03-02-debrief-view, narrative-module, debrief-render, future-chart-additions, plan-02-views-debrief]

# Tech tracking
tech-stack:
  added: []  # No new dependencies — plotly==6.7.0 and statistics stdlib already in requirements
  patterns:
    - "Pure-Plotly builder package (beergame/charts/) mirrors engine/ai/ purity contract — zero streamlit imports so go.Figure can be unit-tested without AppTest (which returns UnknownElement for chart elements)"
    - "Variance metrics via statistics.pvariance (population variance, ddof=0) wrapped in try/StatisticsError + zero-denominator guards — defensive against future flat-demand scenarios"
    - "Cost decomposition derived from inventory_history + backlog_history using the SAME formula as engine/costs.py::weekly_cost — guarantees reconciliation with cost_history[-1]"
    - "Test fixture canonical_done_state (session-scoped) re-uses Phase 1's simulate_full_game(all-Sterman, seed=42) — same canonical bullwhip both phases assert against"
    - "Plotly add_vline(row='all') paints one shape per subplot (4 shapes for 4 rows), each carrying the same annotation_text — tests must accept duplicate annotations"

key-files:
  created:
    - beergame/charts/__init__.py
    - beergame/charts/orders_inventory.py
    - tests/test_metrics_debrief.py
    - tests/test_charts_orders_inventory.py
  modified:
    - beergame/engine/metrics.py
    - tests/conftest.py

key-decisions:
  - "canonical_done_state fixture uses all-Sterman (mirrors GATE 2) NOT player-plays-constant-4: constant-4 Retailer absorbs the demand shock into its own backlog without changing the orders it PLACES, so Sterman at W/D/F sees flat orders_received forever, the bullwhip silently dies, and variance metrics return 0.0"
  - "pvariance (population variance, ddof=0) not variance (sample variance, ddof=1) — we have the complete 36-week series, not a sample, so population variance is the mathematically correct estimator"
  - "Existing peak_orders + max-based bullwhip_ratio kept untouched — Phase 1 GATE 2 (tests/test_bullwhip_emerges.py) requires the max-based metric and must continue passing"
  - "Cost decomposition mirrors engine/costs.py::weekly_cost EXACTLY (HOLDING_COST * max(0, inv) + BACKORDER_COST * bl) — any drift breaks the reconciliation invariant that makes the debrief table trustworthy"
  - "Week-5 vline uses CLASSIC_STEP_BREAK_WEEK + 1 (= 5) NOT CLASSIC_STEP_BREAK_WEEK (= 4) — Pitfall 1; CLASSIC_STEP_BREAK_WEEK is the LAST pre-step week and the demand fires AT week 5"
  - "build_four_panel uses state.total_weeks (not hard-coded 36) so future scenario configs with different game lengths render correctly"
  - "Test charts at the go.Figure level (introspect fig.data, fig.layout.shapes, fig.layout.annotations) NOT via AppTest — Streamlit's AppTest returns UnknownElement for plotly_chart and cannot inspect figure structure"

patterns-established:
  - "Pure-Plotly chart builder: returns go.Figure, no streamlit imports, view layer renders via st.plotly_chart(fig, key=..., width='stretch')"
  - "Variance metric: try pvariance / except StatisticsError → 0.0; if denom == 0 → 0.0; otherwise numer/denom"
  - "Cost decomposition: tuple of frozen-slotted CostRow dataclasses in Role iteration order, total reconciled to engine ledger via pytest.approx(abs=0.01)"
  - "Test fixture: session-scoped canonical_done_state shared between metric tests and chart tests; constructed via simulate_full_game(seed=42, all-Sterman) to match Phase 1 GATE 2"

requirements-completed:
  - DEB-01
  - DEB-02
  - DEB-03
  - DEB-04

# Metrics
duration: 5min 21s
completed: 2026-05-18
---

# Phase 3 Plan 01: Debrief Metrics + 4-Panel Chart Summary

**Three new pure-Python metrics in engine/metrics.py (variance_bullwhip_ratio, per_echelon_amplification, cost_breakdown) plus a pure-Plotly 4-panel chart builder in the new beergame/charts/ package — load-bearing computational core that Plan 03-02's view layer will assemble into the post-game debrief.**

## Performance

- **Duration:** 5 min 21 s
- **Started:** 2026-05-18T21:29:50Z
- **Completed:** 2026-05-18T21:35:11Z
- **Tasks:** 3
- **Files created:** 4 (`beergame/charts/__init__.py`, `beergame/charts/orders_inventory.py`, `tests/test_metrics_debrief.py`, `tests/test_charts_orders_inventory.py`)
- **Files modified:** 2 (`beergame/engine/metrics.py`, `tests/conftest.py`)
- **Tests:** 56 prior + 15 new = 71 passing, 0 failed (9 new metric tests + 6 new chart tests)

## Accomplishments

- **DEB-03 (variance amplification):** `variance_bullwhip_ratio(state)` computes `pvariance(factory_orders) / pvariance(customer_demand)` with defensive guards against empty/length-1 histories and zero-denominator scenarios. `per_echelon_amplification(state)` returns a `dict[Role, float]` keyed by every Role member. Both use `statistics.pvariance` (population variance, ddof=0) — no NumPy, no pandas.
- **DEB-04 (cost breakdown):** `cost_breakdown(state)` returns `tuple[CostRow, ...]` (one frozen-slotted dataclass per Role) decomposing cumulative cost into holding (`HOLDING_COST * sum(max(0, x) for x in inventory_history)`) and backorder (`BACKORDER_COST * sum(backlog_history)`) components. The decomposition formula mirrors `engine/costs.py::weekly_cost` EXACTLY so per-station totals reconcile with `cost_history[-1]` to 1¢ tolerance.
- **DEB-01 + DEB-02 (4-panel chart):** `beergame/charts/build_four_panel(state)` returns a `plotly.graph_objects.Figure` with exactly 8 traces (4 stations × {orders, inventory}) and 4 vertical-line shapes at x=5 (one per panel from `row="all"`) each annotated "Customer demand: 4 → 8". Layout: height=700, shared x-axis, hovermode="x unified", horizontal legend above chart, "Week" title on bottom panel only.
- **Test fixture:** Session-scoped `canonical_done_state` fixture in `conftest.py` simulates the canonical 36-week game (seed=42, all-Sterman) — same configuration as Phase 1's GATE 2 — so the new metric and chart tests assert against the same canonical bullwhip that Phase 1 already proves emerges.
- **Phase 1 invariants intact:** Existing `peak_orders` and max-based `bullwhip_ratio` untouched (GATE 2 still passes, max-based ratio still exactly 2.000 at seed=42). AST guard 4/4 clean (engine/ai/config remain streamlit-free; charts/ is also streamlit-free by design even though it's not under the guard).

## Canonical seed=42 Numbers (all four Sterman, 36 weeks)

These are the load-bearing reference values Plan 03-02 should sanity-check its rendered output against.

| Metric | Value |
|--------|-------|
| Variance bullwhip ratio (overall, DEB-03) | **35.38** |
| Max-based bullwhip ratio (Phase 1 GATE 2) | **2.000** (unchanged) |
| Per-echelon amplification — Retailer | 3.43 |
| Per-echelon amplification — Wholesaler | 12.81 |
| Per-echelon amplification — Distributor | 29.27 |
| Per-echelon amplification — Factory | **35.38** |

**Cost breakdown (ledger-reconciled to 1¢):**

| Station | Holding | Backorder | Total | `cost_history[-1]` |
|---------|---------|-----------|-------|--------------------|
| Retailer | $38.50 | $184.00 | $222.50 | $222.50 ✓ |
| Wholesaler | $181.00 | $118.00 | $299.00 | $299.00 ✓ |
| Distributor | $297.50 | $201.00 | $498.50 | $498.50 ✓ |
| Factory | $248.50 | $173.00 | $421.50 | $421.50 ✓ |

Per-echelon amplification grows **monotonically** upstream (R=3.4 → W=12.8 → D=29.3 → F=35.4) — the canonical bullwhip signature. Variance-based ratio (35.4) is ~17× larger than the max-based ratio (2.0) because variance is sensitive to the full overshoot+collapse waveform Sterman produces, not just the single peak.

## Task Commits

1. **Task 1: Extend engine/metrics.py with variance + cost-breakdown for debrief** — `ee2bb76` (feat)
2. **Task 2: Add beergame/charts package with build_four_panel** — `f28aa86` (feat)
3. **Task 3: Add canonical_done_state fixture + debrief metric/chart unit tests** — `1994b1a` (test)

## Files Created/Modified

**Created:**
- `beergame/charts/__init__.py` — Re-exports `build_four_panel`; module docstring documents the pure-Plotly purity contract.
- `beergame/charts/orders_inventory.py` — `build_four_panel(state) -> go.Figure`: 4 vertically stacked subplots with shared x-axis, orders + inventory traces per panel, week-5 demand-step vline. Uses `state.total_weeks` (not hard-coded 36).
- `tests/test_metrics_debrief.py` — 9 tests: empty-history guard, canonical ratio > 1.0, dict has all 4 roles, Factory > Retailer (monotonic upstream amplification), tuple in Role order, total = holding + backorder, total == cost_history[-1] (load-bearing reconciliation), max(0,x) ignores negative inventories, zero-denominator returns 0.0.
- `tests/test_charts_orders_inventory.py` — 6 tests: 8 traces, vline at x=5 (off-by-one trap), annotation mentions "4" and "8", x-axis title "Week" on bottom panel, all 4 station names in subplot titles, x-axis covers 1..state.total_weeks.

**Modified:**
- `beergame/engine/metrics.py` — Added 4 new public symbols (`CostRow`, `variance_bullwhip_ratio`, `per_echelon_amplification`, `cost_breakdown`) + imports (`dataclass`, `pvariance`, `StatisticsError`, `BACKORDER_COST`, `HOLDING_COST`). Kept existing `peak_orders` + `bullwhip_ratio` unchanged. New module docstring documents the two-phase role (Phase 1 calibration + Phase 3 debrief).
- `tests/conftest.py` — Added session-scoped `canonical_done_state` fixture wrapping `simulate_full_game(seed=42, all-Sterman)`. Existing `initial_game` + `constant_4_agents` fixtures unchanged.

## Decisions Made

- **canonical_done_state uses all-Sterman, NOT player-plays-constant-4.** The plan as written specified a constant-4 Retailer, but that silently destroys the bullwhip: Retailer plays the same order every week regardless of customer demand, so Sterman agents at W/D/F see flat `orders_received_history` forever and produce no amplification. Variance metrics correctly return 0.0 on flat data, but then they can't be tested. Mirroring GATE 2 (all four stations Sterman) is the right move and aligns with the canonical bullwhip Phase 1 already calibrated.
- **pvariance (population), not variance (sample).** We have the complete 36-week series, not a random sample drawn from a distribution. Population variance (ddof=0) is the mathematically correct estimator.
- **Phase 1 metrics kept intact.** `peak_orders` and max-based `bullwhip_ratio` are load-bearing for `tests/test_bullwhip_emerges.py` (GATE 2). The new variance-based ratio coexists; the max-based ratio remains the Phase 1 calibration gate.
- **Cost decomposition mirrors `weekly_cost` exactly.** Any drift between `cost_breakdown` and the engine's per-tick `weekly_cost` would break the reconciliation invariant and make the debrief table untrustworthy. The formula `HOLDING_COST * max(0, x) + BACKORDER_COST * bl` is copied verbatim and summed over the history tuples.
- **Week-5 vline at `CLASSIC_STEP_BREAK_WEEK + 1`.** Pitfall 1 (off-by-one): `CLASSIC_STEP_BREAK_WEEK = 4` is the LAST pre-step week; the demand jumps AT week 5. Code comment explains the derivation so future contributors don't "fix" it back to 4.
- **Tests introspect `go.Figure` directly.** AppTest cannot inspect Plotly charts (returns `UnknownElement()`). All chart tests call `build_four_panel(...)` and assert on `fig.data`, `fig.layout.shapes`, `fig.layout.annotations`, `fig.layout.xaxis4.title.text`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] canonical_done_state fixture: player plays Sterman, not constant-4**
- **Found during:** Task 3 (running new tests after fixture creation)
- **Issue:** Plan said "Retailer (player) plays a naive constant-4 — what we care about for Phase 3 is whatever bullwhip the Sterman AI produces upstream." This is incorrect: when the Retailer plays constant-4, the demand shock is absorbed into the Retailer's own backlog without changing the orders the Retailer PLACES. Wholesaler/Distributor/Factory Sterman agents only see `orders_received` from their downstream neighbor (= orders the downstream station PLACED, not customer demand). With Retailer placing constant 4 every week, W/D/F see flat orders forever and produce no amplification. Both variance tests (`test_variance_bullwhip_ratio_canonical_is_greater_than_one` and `test_per_echelon_amplification_factory_exceeds_retailer`) failed with 0.0 ratios.
- **Fix:** Changed fixture to use `simulate_full_game(seed=42, agents={r: ShipmentAnchorAndAdjustAgent() for r in Role})` — all four stations Sterman, mirroring Phase 1 GATE 2's `_all_sterman_agents()` setup exactly. The Retailer's Sterman heuristic responds to the actual demand shock, places amplifying orders, and the bullwhip propagates upstream as designed.
- **Files modified:** `tests/conftest.py`
- **Verification:** All 71 tests pass (15 new tests included). Canonical numbers reproduce: overall variance ratio = 35.38, per-echelon R=3.43 / W=12.81 / D=29.27 / F=35.38, cost ledger reconciles exactly.
- **Committed in:** `1994b1a` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug — plan misstated fixture semantics)
**Impact on plan:** Single fixture-construction fix; no scope creep. All other plan instructions (function signatures, file paths, test names, success criteria) followed exactly. Canonical numbers documented above so Plan 03-02 can sanity-check its rendered debrief.

## Issues Encountered

None beyond the deviation above. AST guard 4/4 still passes (engine + ai + config layers remain streamlit-free). Phase 1 invariants intact: max-based bullwhip ratio still 2.000 at seed=42, equilibrium inventory still 12 for 36 weeks under all-ConstantOrderAgent(4).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Plan 03-02 (debrief view) is fully unblocked.** It needs to:
1. Import `build_four_panel`, `variance_bullwhip_ratio`, `per_echelon_amplification`, `cost_breakdown` from their public surfaces.
2. Render the figure via `st.plotly_chart(fig, key="debrief_four_panel", width="stretch")` (match Plan 02-03's convention).
3. Display the headline metric (e.g., "Your supply chain amplified demand by 35.4×" at seed=42).
4. Render per-echelon ratios as four `st.metric` tiles.
5. Render cost breakdown as `st.table([{...}, ...])` (no pandas).
6. Pull the narrative from a yet-to-be-created `beergame/narrative/` package (DEB-05, also Plan 03-02 scope).
7. Wire "Play again" to the existing `app.py::reset_game` callback (DEB-06, already plumbed via `on_reset` param).

The 4-panel chart is unit-tested at the `go.Figure` level; the view layer is a thin assembler. No new dependencies, no NumPy, no pandas, no Streamlit in `beergame/charts/` or `beergame/engine/`.

---
*Phase: 03-debrief-charts-narrative*
*Completed: 2026-05-18*

## Self-Check: PASSED

- FOUND: `beergame/engine/metrics.py` (modified)
- FOUND: `beergame/charts/__init__.py`
- FOUND: `beergame/charts/orders_inventory.py`
- FOUND: `tests/conftest.py` (modified)
- FOUND: `tests/test_metrics_debrief.py`
- FOUND: `tests/test_charts_orders_inventory.py`
- FOUND: commit `ee2bb76` (Task 1)
- FOUND: commit `f28aa86` (Task 2)
- FOUND: commit `1994b1a` (Task 3)
