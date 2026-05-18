---
phase: 01-simulation-engine-ai
plan: 03
subsystem: tests
tags: [pytest, beer-game, bullwhip, equilibrium, exit-gates, sterman, blocker-1, phase-1-complete]

# Dependency graph
requires:
  - phase: 01-simulation-engine-ai
    plan: 01
    provides: "simulate_full_game driver, constant_demand + demand_for_week, ConstantOrderAgent, frozen-dataclass GameState/StationState, canonical equilibrium init (Factory.incoming_orders=(4,) -- BLOCKER 1 fix)"
  - phase: 01-simulation-engine-ai
    plan: 02
    provides: "ShipmentAnchorAndAdjustAgent (empirical Sterman 1989 fit) + ENG-01 AST-walk streamlit-import guard"
provides:
  - "GATE 1 (AI-04 / ENG-06) -- 6 pytest tests using ConstantOrderAgent(4) at all four stations + constant_demand=4; proves engine arithmetic correctness in isolation from any heuristic"
  - "GATE 2 (AI-03) -- 5 pytest tests using ShipmentAnchorAndAdjustAgent at all four stations + classic step demand; proves the canonical bullwhip ratio in [2.0, 4.0]"
  - "Phase 1 exit: 44/44 pytest tests pass, zero streamlit imports, same-seed byte-identical determinism, ratio = 2.000 under seed=42"
affects: [02-ui-shell, 03-debrief-charts]

# Tech tracking
tech-stack:
  added: []  # stdlib + pytest only; no new dependencies
  patterns:
    - "Per-week strict monotonicity assertion (catches mid-game drift that integrates back to the right total)"
    - "Failure message names empirical-vs-optimal Sterman parameter trap + S' tuning range [12, 20] + the forbidden ORDER_PIPELINE_LEN_FACTORY regression"
    - "Tick-N sensitivity test (week 5 demand step) confirms the shock propagates from demand_fn into the Sterman heuristic"

key-files:
  created:
    - "tests/test_equilibrium.py -- GATE 1, 6 tests (AI-04, ENG-06, BLOCKER 1 regression guard)"
    - "tests/test_bullwhip_emerges.py -- GATE 2, 5 tests (AI-03, canonical bullwhip ratio)"
  modified: []

key-decisions:
  - "GATE 1 uses ConstantOrderAgent(4) -- NOT ShipmentAnchorAndAdjustAgent -- per the updated AI-04 requirement. Empirical Sterman at a perfectly-equilibrated view orders 3 (not 4), so 'inventory==12 every week AND orders==4 every week' is mutually unsatisfiable under Sterman; GATE 1 isolates engine correctness, GATE 2 measures bullwhip."
  - "Bullwhip bounds [2.0, 4.0] are load-bearing -- the only correctness check before Phase 2. Tightening below 2.0 or raising above 4.0 silently lets empirical-vs-optimal parameter swaps pass. If GATE 2 marginally fails, the ONLY acceptable knob is desired_inventory (S') in [12, 20]."
  - "ORDER_PIPELINE_LEN_FACTORY=1 is mandatory; regressing to 0 to 'shrink the bullwhip' is explicitly forbidden in the GATE 2 failure message because it breaks GATE 1 (Factory inventory climbs to 16)."
  - "Tick-1 trace test asserts Wholesaler/Distributor/Factory have incoming_orders=(4,) after tick 1 (the upstream end -- BLOCKER 1 guard) but Retailer has incoming_orders=(0,) because no upstream station routes orders to the Retailer -- customer demand arrives via demand_fn inside fill_orders step 2, not via the order pipeline."

requirements-completed: [AI-03, AI-04, ENG-06]

# Metrics
duration: 3min
completed: 2026-05-18
---

# Phase 1 Plan 3: Phase 1 Exit Gates Summary

**Two pytest gates closing Phase 1 -- GATE 1 (equilibrium regression with ConstantOrderAgent) and GATE 2 (canonical bullwhip ratio = 2.000 in [2.0, 4.0] with empirical Sterman) -- 44/44 tests pass, zero Streamlit code exists, Phase 2 UI work is unblocked.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-05-18T20:18:22Z
- **Completed:** 2026-05-18T20:21:52Z
- **Tasks:** 2
- **Files created:** 2 (tests/test_equilibrium.py, tests/test_bullwhip_emerges.py)
- **Tests:** 44 pass / 0 fail (33 from Plans 01-02 + 6 GATE 1 + 5 GATE 2 = 44)

## Task Commits

| # | Task                              | Commit    | Files                                 |
| - | --------------------------------- | --------- | ------------------------------------- |
| 1 | GATE 1: equilibrium regression    | `dcd0819` | `tests/test_equilibrium.py` (6 tests) |
| 2 | GATE 2: bullwhip calibration      | `692d7a1` | `tests/test_bullwhip_emerges.py` (5 tests) |

## GATE 1 (AI-04 / ENG-06) -- Equilibrium Regression

**Setup:** customer demand constant at 4/wk for all 36 weeks; all four stations played by `ConstantOrderAgent(4)`. The canonical initial state has inventory=12, backlog=0, every pipeline slot pre-loaded with 4 -- INCLUDING `Factory.incoming_orders = (4,)` (the BLOCKER 1 fix).

**Confirmation of GATE 1 using ConstantOrderAgent(4), NOT ShipmentAnchorAndAdjustAgent:** Per the updated AI-04 requirement (the BLOCKER 2 fix). Empirical Sterman at a perfectly-equilibrated view evaluates to `round(2.58) = 3` (pinned by Plan 02's `test_order_at_perfect_equilibrium_view_is_3`), so the assertion "inventory==12 every week AND orders==4 every week" is mutually unsatisfiable under empirical Sterman. GATE 1 isolates engine arithmetic from any heuristic-induced drift; the real Sterman test is GATE 2.

**Confirmation of strict per-week cost assertion (WARNING 2 mitigation):** `test_equilibrium_costs_per_week_strict_monotonic` walks every week index `i` in 0..35 and asserts `cost_history[i] == 6.0 * (i+1)` exactly. No mid-game cost oscillation can hide behind the cumulative total of 216.0 -- if week 10 cumulative cost drifted to 65 instead of 60, the assert fails at week 10, long before the integral recovers.

### GATE 1 measured trace (seed=42, demand=4, all-ConstantOrderAgent(4))

```
customer_demand_history[:5] = (4, 4, 4, 4, 4)
RETAILER     inv[:5]=(12, 12, 12, 12, 12)  inv[-5:]=(12, 12, 12, 12, 12)  final_cost=216.0
WHOLESALER   inv[:5]=(12, 12, 12, 12, 12)  inv[-5:]=(12, 12, 12, 12, 12)  final_cost=216.0
DISTRIBUTOR  inv[:5]=(12, 12, 12, 12, 12)  inv[-5:]=(12, 12, 12, 12, 12)  final_cost=216.0
FACTORY      inv[:5]=(12, 12, 12, 12, 12)  inv[-5:]=(12, 12, 12, 12, 12)  final_cost=216.0
```

**BLOCKER 1 regression smoke test at the full-simulation level:** `Factory inv: (12, 12, 12, 12, 12) ... last: 12` -- the explicit guard fires on EVERY tick for the Factory across all 36 weeks. With the old broken design (ORDER_PIPELINE_LEN_FACTORY=0, Factory.incoming_orders=()), Factory inventory would climb to 16 every week because Distributor's orders to Factory would be silently discarded.

### The 6 GATE 1 tests

| # | Test                                                  | What it pins                                                                                                                                      |
| - | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1 | `test_equilibrium_constant_demand_constant_orders`    | Inventory and backlog histories are exactly (12,)*36 and (0,)*36 for all 4 stations. Failure message lists 4 likely causes in order of likelihood. |
| 2 | `test_equilibrium_customer_demand_history_constant`   | `customer_demand_history == (4,) * 36` -- demand function recorded correctly.                                                                     |
| 3 | `test_equilibrium_costs_per_week_strict_monotonic`    | Per-week cumulative cost == 6.0 * (week+1) at EVERY week, plus final == 216.0 sanity end-cap. Catches mid-game cost oscillation.                  |
| 4 | `test_equilibrium_orders_placed_are_all_four`         | `orders_placed_history == (4,) * 36` for every station -- ConstantOrderAgent contract is honored.                                                 |
| 5 | `test_equilibrium_factory_inventory_explicit`         | **BLOCKER 1 regression guard.** Factory inventory_history all 12s AND Factory shipments_sent_history all 4s.                                      |
| 6 | `test_equilibrium_tick_1_trace_explicit`              | After tick 1: every station inv=12, bl=0, incoming_shipments=(4,4); W/D/F incoming_orders=(4,); Retailer incoming_orders=(0,).                    |

## GATE 2 (AI-03) -- Bullwhip Calibration

**Setup:** classic step demand (4/wk weeks 1-4, 8/wk weeks 5-36); all four stations played by `ShipmentAnchorAndAdjustAgent` with empirical Sterman 1989 defaults (alpha=0.26, beta=0.34, theta=0.36, S'=17.0).

**Measured bullwhip ratio under seed=42:**

```
RETAILER     peak_order=11  orders[:12]=(3, 3, 3, 3, 4, 6, 8, 9, 9, 9, 10, 10)
WHOLESALER   peak_order=16  orders[:12]=(4, 3, 3, 3, 3, 3, 5, 8, 10, 10, 10, 13)
DISTRIBUTOR  peak_order=21  orders[:12]=(4, 4, 3, 3, 3, 3, 3, 4, 7, 10, 11, 12)
FACTORY      peak_order=22  orders[:12]=(4, 4, 4, 3, 3, 3, 3, 3, 3, 6, 8, 11)

Bullwhip ratio = factory_peak (22) / retailer_peak (11) = 2.000
In canonical [2.0, 4.0]? True
```

**Ratio = 2.000.** Exactly at the lower bound of the canonical [2.0, 4.0] window -- inside, but tight. This is the canonical Beer Game bullwhip emerging under the BLOCKER 1 fix (ORDER_PIPELINE_LEN_FACTORY=1 adds one extra tick of inbound order lag at Factory, which slightly LARGER bullwhip than the broken design's zero-pipeline; the lower bound here reflects that we're now also amplifying that extra tick).

**No tuning of S' was required to land inside the bounds.** S' remains at the Plan 02 value of 17.0. If a future change to the engine narrows the margin further (e.g., changing tick order or pipeline lengths), the documented recovery path is to tune `desired_inventory` in `beergame/ai/sterman.py` within [12, 20] -- NEVER widen the test bounds.

**Monotonic upstream amplification (R<=W<=D<=F):** 11 <= 16 <= 21 <= 22 -- canonical bullwhip shape confirmed. Notice the lag in peak timing: each successive station peaks later in the simulation as the order shock propagates upstream through the 1-week order mailing channels.

### The 5 GATE 2 tests

| # | Test                                                              | What it pins                                                                                                                                                            |
| - | ----------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1 | `test_bullwhip_factory_retailer_peak_ratio_in_canonical_range`    | **THE GATE.** `factory_peak / retailer_peak in [2.0, 4.0]`. Failure message names empirical-vs-optimal parameter swap, points to S' tuning in [12, 20], forbids ORDER_PIPELINE_LEN_FACTORY regression. |
| 2 | `test_bullwhip_factory_peak_exceeds_retailer_peak`                | Weaker prerequisite: factory MUST overshoot more than retailer (otherwise no amplification at all).                                                                     |
| 3 | `test_bullwhip_amplification_monotonically_grows_upstream`        | Peaks grow R <= W <= D <= F. Catches the case where amplification exists but doesn't follow the canonical shape (e.g., Distributor overshoots more than Factory due to a bug). |
| 4 | `test_bullwhip_demand_step_recorded`                              | Customer-demand-history shows (4,4,4,4) weeks 1-4, 8 from week 5 onward, length 36. Sanity check on demand routing.                                                     |
| 5 | `test_bullwhip_retailer_responds_at_or_after_week_5`              | **Tick-5 confirmation.** Retailer inventory drops at week 5 (the demand step IS reaching fill_orders) AND Retailer's post-step peak order > week-1 order (Sterman responds to the shock). |

## Phase 1 Exit Gate Verification

Per ROADMAP.md's 5 Phase 1 success criteria:

| #   | Criterion                                            | Status | Evidence                                                                                                                   |
| --- | ---------------------------------------------------- | ------ | -------------------------------------------------------------------------------------------------------------------------- |
| 1   | GATE 1 -- equilibrium regression passes              | PASS   | `pytest tests/test_equilibrium.py -v` -> 6/6 pass                                                                          |
| 2   | GATE 2 -- bullwhip ratio in [2.0, 4.0]               | PASS   | `pytest tests/test_bullwhip_emerges.py -v` -> 5/5 pass; measured ratio = 2.000 under seed=42                                |
| 3   | Zero streamlit imports in engine/ai/config           | PASS   | `grep -rn "import streamlit" beergame/engine beergame/ai beergame/config` -> empty; ENG-01 AST guard also green             |
| 4   | Same-seed byte-identical determinism                 | PASS   | Two `simulate_full_game(seed=42, ...)` runs: all 4 stations' histories byte-identical, GameState equality holds            |
| 5   | Tick order canonical (5-step Sterman sequence)       | PASS   | Plan 01's `test_tick_invariants.py` (7 tests) green; GATE 1's per-week cost monotonicity + GATE 2's tick-5 sensitivity also verify it indirectly |

## Full Test Suite (44 tests across 8 files)

| File                                       | Tests | Provides                                                                                |
| ------------------------------------------ | ----- | --------------------------------------------------------------------------------------- |
| `tests/test_determinism.py`                | 3     | ENG-09 -- same-seed runs produce identical traces                                       |
| `tests/test_tick_invariants.py`            | 7     | ENG-06, ENG-07 -- 5-step canonical tick order + BLOCKER 1 fix verification              |
| `tests/test_costs.py`                      | 5     | ENG-05, ENG-08 -- asymmetric holding/backorder cost + cumulative growth                 |
| `tests/test_station_view_visibility.py`    | 5     | ENG-10 -- StationView vs RetailerView visibility split                                  |
| `tests/test_sterman_heuristic.py`          | 9     | AI-01, AI-02 -- Sterman empirical parameters + Agent Protocol conformance               |
| `tests/test_no_streamlit_import.py`        | 4     | ENG-01 -- AST-walk guard against streamlit imports in engine/ai/config                  |
| **`tests/test_equilibrium.py`** (NEW)      | **6** | **GATE 1: AI-04, ENG-06 -- equilibrium regression with ConstantOrderAgent**             |
| **`tests/test_bullwhip_emerges.py`** (NEW) | **5** | **GATE 2: AI-03 -- canonical bullwhip ratio with empirical Sterman**                    |
| **Total**                                  | 44    | **All 14 Phase 1 requirement IDs (ENG-01..10, AI-01..04) now demonstrably verified**    |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed mis-derived assertion in `test_equilibrium_tick_1_trace_explicit`**

- **Found during:** Task 1 (first `pytest tests/test_equilibrium.py -v` after writing the file).
- **Issue:** The plan's `<action>` block dictated `assert station.incoming_orders == (4,)` for every station after tick 1, including the Retailer. The engine produced `(0,)` for the Retailer, failing the assertion with `RETAILER: tick 1 incoming_orders=(0,), expected (4,)`. The engine behavior is correct: in `place_orders` (step 4), R/W/D route their orders to the UPSTREAM station's `_pending_in_order` (Retailer routes to Wholesaler, Wholesaler to Distributor, Distributor to Factory; Factory routes to its OWN `_pending_in_shipment`). No station routes orders DOWNSTREAM to the Retailer -- the Retailer is the most-downstream node and customer demand arrives via `demand_fn` inside `fill_orders` step 2, not via the order pipeline. The plan's tick-1 walkthrough text was correct for W/D/F but mis-stated the result for the Retailer.
- **Fix:** Split the tick-1 assertion into two pieces:
  - `for role in (WHOLESALER, DISTRIBUTOR, FACTORY): assert incoming_orders == (4,)` -- the BLOCKER 1 regression guard at the upstream end (especially Factory).
  - `assert retailer.incoming_orders == (0,)` -- the most-downstream node has no upstream order source, so its pipeline shifts to (0,) after tick 1.
- **Files modified:** `tests/test_equilibrium.py` (test 6 of 6)
- **Verification:** `pytest tests/test_equilibrium.py -v` -> 6/6 pass after the fix.
- **Committed in:** `dcd0819` (Task 1 commit -- the fix landed before the commit was created, so there's no separate fix commit).

### Notes

No Rule 2 (missing critical), Rule 3 (blocking), or Rule 4 (architectural) deviations. Task 2 (GATE 2) passed on first run without any tuning -- bullwhip ratio of 2.000 landed inside [2.0, 4.0] with the locked Sterman parameters (alpha=0.26, beta=0.34, theta=0.36, S'=17.0) and the BLOCKER 1 fix in place.

## Issues Encountered

None beyond the single Rule 1 fix above.

## S' (desired_inventory) Tuning Performed

**None.** `desired_inventory = 17.0` remained at the Plan 02 default. GATE 2 ratio landed at 2.000 on the first attempt -- the lower bound of [2.0, 4.0] but inside.

If a future engine change (e.g., a planner intentionally varies pipeline lengths or tick ordering) shifts the ratio above 4.0 or below 2.0, the documented recovery path is in `tests/test_bullwhip_emerges.py`'s failure message:

1. Confirm Sterman defaults are still EMPIRICAL (0.26 / 0.34 / 0.36 / 17.0), not "optimal" (1 / 1 / 0 / anything).
2. Re-run `test_equilibrium.py` and `test_tick_invariants.py` to rule out engine arithmetic bugs.
3. Tune `desired_inventory` in `beergame/ai/sterman.py` within [12, 20] until the ratio lands cleanly inside [2.0, 4.0] with a clean post-overshoot collapse-to-zero pattern.
4. Do NOT widen the [2.0, 4.0] test bounds.
5. Do NOT regress `ORDER_PIPELINE_LEN_FACTORY` from 1 to 0 to shrink the bullwhip -- that breaks GATE 1.

## Phase 1 Is Complete

- All 14 Phase 1 requirement IDs (ENG-01..10, AI-01..04) are demonstrably verified by the pytest suite.
- The canonical Beer Game bullwhip emerges from `simulate_full_game(seed=42, agents=all-Sterman, demand=4->8 step)` with ratio = 2.000, inside the canonical [2.0, 4.0] window.
- Engine + AI + config layers contain ZERO Streamlit imports. The codebase is ready for Phase 2 to introduce `beergame/views/`, `beergame/charts/`, `app.py` -- none of which exist yet.
- Same-seed runs are byte-identical (the determinism contract for Phase 4 deploy and Phase 3 debrief).
- Phase 2 (UI Shell + Per-Turn Play) can begin.

## Next Phase Readiness

- Phase 2 entry checklist: all green.
  - `beergame.engine.simulate_full_game` is a stable API (frozen-dataclass GameState returned, deterministic, no Streamlit deps).
  - `RetailerView` / `StationView` already separate what the player sees from internal state -- Phase 2's per-turn UI consumes these.
  - `ShipmentAnchorAndAdjustAgent` is the AI for the 3 stations the player doesn't choose.
  - Two pytest gates remain green for the rest of the project; Phase 2 must not break them.

---

## Self-Check: PASSED

Files verified to exist:
- FOUND: /home/williamlefew/projects/beergameNexStratus/tests/test_equilibrium.py
- FOUND: /home/williamlefew/projects/beergameNexStratus/tests/test_bullwhip_emerges.py

Commits verified:
- FOUND: dcd0819 (Task 1 -- GATE 1 equilibrium regression)
- FOUND: 692d7a1 (Task 2 -- GATE 2 bullwhip calibration)

Pytest:
- `pytest tests/test_equilibrium.py -v` -> 6/6 pass
- `pytest tests/test_bullwhip_emerges.py -v` -> 5/5 pass
- `pytest tests/ -v` -> 44/44 pass across 8 files
- Bullwhip ratio under seed=42: 2.000 (inside [2.0, 4.0])
- Factory inventory under GATE 1 setup: (12, 12, 12, 12, 12) ... last=12 (BLOCKER 1 fix verified)
- Streamlit import grep: empty
- Same-seed determinism: all 4 stations' histories byte-identical, GameState equality holds

Requirements satisfied (this plan): AI-03, AI-04, ENG-06 (re-verified at the gate level).
Phase 1 requirements satisfied overall: ENG-01..10, AI-01..04 (all 14).

---
*Phase: 01-simulation-engine-ai*
*Completed: 2026-05-18*
