---
phase: 02-ui-shell-per-turn-play
plan: 01
subsystem: engine
tags: [engine, station-view, history, regression-test, additive-api]

# Dependency graph
requires:
  - phase: 01-simulation-engine-ai
    provides: "StationState frozen-dataclass, five-step canonical tick, build_station_view, ConstantOrderAgent/ShipmentAnchorAndAdjustAgent, 44-test baseline suite"
provides:
  - "StationState.shipments_received_history: tuple[int, ...] (grows by one int per tick, in step 3 record_state)"
  - "StationState._pending_shipment_received transient (set in step 1 receive_shipments, consumed/zeroed in step 3 record_state)"
  - "StationView.last_shipment_received: int (default 0; built from history tail or EQUILIBRIUM_THROUGHPUT fallback)"
  - "RetailerView inherits last_shipment_received unchanged"
  - "tests/test_shipments_received_history.py — 7 targeted regression tests"
affects: [02-02-ui-shell, 02-03-per-turn-play-view, debrief-charts]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Additive engine API: new public field on view dataclass, default value lets RetailerView keep its own defaulted customer_demand field without reordering"
    - "Step-1-stash, step-3-record transient pattern (mirrors existing _demand_to_fill/_shipped_this_tick handling) preserves the 'all histories grow exactly once per tick, in step 3' invariant"

key-files:
  created:
    - tests/test_shipments_received_history.py
  modified:
    - beergame/engine/state.py
    - beergame/engine/tick.py
    - tests/test_costs.py

key-decisions:
  - "last_shipment_received uses default 0 on StationView (mirrors customer_demand=0 on RetailerView) so the frozen-dataclass subclass field order stays legal; empty-history fallback to EQUILIBRIUM_THROUGHPUT lives in build_station_view, not on the dataclass default"
  - "shipments_received_history append happens in step 3 (record_state), not step 1 — the canonical 'one history append per tick, in step 3' invariant is load-bearing for the determinism + tick-invariants tests"
  - "New transient _pending_shipment_received is compare=False, repr=False (same as the four existing transients) so state equality remains observable-state-only and test_determinism stays byte-identical under same-seed"

patterns-established:
  - "Pattern 1: Adding a new history tuple to StationState requires updating both new_game (init to ()) and the one direct constructor in tests/test_costs.py — there are only two StationState() callsites in the entire codebase, both grepped"
  - "Pattern 2: For each new history field, default the corresponding StationView field to 0 so RetailerView's customer_demand keeps its defaulted-field ordering (frozen-dataclass inheritance rule)"

requirements-completed:
  - PLAY-01

# Metrics
duration: 3m 6s
completed: 2026-05-18
---

# Phase 02 Plan 01: Engine API Extension Summary

**Additive engine API: `StationState.shipments_received_history` + `StationView.last_shipment_received` so PLAY-01's per-turn play view can render "last week's shipments received" directly. Bullwhip ratio still 2.0000; full suite 51/51.**

## Performance

- **Duration:** 3m 6s
- **Started:** 2026-05-18T20:50:16Z
- **Completed:** 2026-05-18T20:53:22Z
- **Tasks:** 2
- **Files modified:** 4 (3 modified + 1 created)

## Accomplishments

- Added `shipments_received_history: tuple[int, ...]` to `StationState` and routed step-1's consumed `incoming_shipments[0]` through a new `_pending_shipment_received` transient into the history in step 3 — keeping the canonical "all histories grow once per tick, in step 3" invariant intact.
- Added `last_shipment_received: int` to `StationView` (default 0; inherited unchanged by `RetailerView`); `build_station_view` returns the history tail or falls back to `EQUILIBRIUM_THROUGHPUT=4` when history is empty.
- Authored 7 targeted regression tests covering empty-init fallback, per-tick growth, view-tail projection, step-1/step-3 consumption symmetry, the Factory self-loop, and the canonical equilibrium invariant `(4,) * 36` for every station.
- Behavioral invariant preserved: bullwhip ratio still **2.0000** under seed=42, equilibrium inventory still **12** for 36 weeks, AST guard still streamlit-clean.
- Full pytest suite: **44 -> 51 passing**, zero regressions, zero behavioral drift.

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend StationState + tick.py to record shipments_received_history** - `9bffc20` (feat)
2. **Task 2: Add targeted regression test for shipments_received_history** - `94adfea` (test)

## Files Created/Modified

- `beergame/engine/state.py` - Added `shipments_received_history` field + `_pending_shipment_received` transient to `StationState`; added `last_shipment_received: int = 0` to `StationView`; updated `new_game` initializer and `build_station_view` projection.
- `beergame/engine/tick.py` - `receive_shipments` (step 1) now stashes the arriving value in `_pending_shipment_received`; `record_state` (step 3) appends it to `shipments_received_history` and zeroes the transient.
- `tests/test_costs.py` - Updated the `_station` test helper to include `shipments_received_history=()` (required for the new mandatory field on `StationState`).
- `tests/test_shipments_received_history.py` - New file with 7 regression tests.

## Decisions Made

- **Default last_shipment_received to 0 on StationView**: Required to keep frozen-dataclass subclass field order legal (RetailerView already has a defaulted `customer_demand: int = 0`). The "real" fallback (EQUILIBRIUM_THROUGHPUT=4 when history is empty) is computed in `build_station_view`, not on the dataclass default — keeping the dataclass shape simple.
- **Append in step 3, not step 1**: All other histories grow exactly once per tick, in step 3 (record_state). Routing through a transient preserves that invariant; otherwise the determinism + tick-invariants tests would have to be re-reasoned-about.
- **Transient is compare=False, repr=False**: Matches the four existing transients (`_pending_in_shipment`, `_pending_in_order`, `_demand_to_fill`, `_shipped_this_tick`); keeps `test_determinism`'s byte-identical state equality intact.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated tests/test_costs.py _station helper for new required field**
- **Found during:** Task 1 verification (`pytest tests/`)
- **Issue:** `tests/test_costs.py::_station` directly instantiates `StationState(...)` with all positional/keyword history fields; adding the new mandatory `shipments_received_history: tuple[int, ...]` (no default — it's a regular field, not a transient) raised `TypeError: StationState.__init__() missing 1 required positional argument: 'shipments_received_history'` in 5 cost tests.
- **Fix:** Added `shipments_received_history=()` alongside the other `()`-initialized history fields in the helper.
- **Files modified:** tests/test_costs.py
- **Verification:** Full test suite passes (44/44 at end of Task 1, 51/51 at end of Task 2).
- **Committed in:** `9bffc20` (Task 1 commit, since the test_costs helper became broken by the StationState shape change in the same task).

`grep StationState\(` confirmed only two callsites exist in the entire repo (`tests/test_costs.py` + `beergame/engine/state.py::new_game`), both updated.

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The fix was a mechanical follow-on from the additive field — strictly required for the existing test suite to compile/run. No scope creep, no behavioral change.

## Issues Encountered

None — plan executed cleanly. No streamlit imports leaked into the engine, the bullwhip calibration ratio stayed at 2.0000 (confirmed by `tests/test_bullwhip_emerges.py::test_bullwhip_factory_retailer_peak_ratio_in_canonical_range`), and all 44 pre-existing Phase 1 tests continue to pass byte-identically.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 02 (UI shell) and Plan 03 (per-turn play view) may now consume `view.last_shipment_received` directly to satisfy PLAY-01's "last week's shipments received" display requirement. The engine no longer needs derived-history fragility in the view layer.
- The new field is also available to downstream callers (debrief charts, narrative templates) as a first-class history alongside `shipments_sent_history`, `orders_received_history`, etc. — improving API symmetry between sent/received.
- Zero behavioral drift means GATE 1 (equilibrium) and GATE 2 (bullwhip ratio = 2.0000) are still demonstrably green.

## Self-Check: PASSED

- FOUND: beergame/engine/state.py (shipments_received_history present at line 54)
- FOUND: beergame/engine/tick.py (_pending_shipment_received present in receive_shipments + record_state)
- FOUND: tests/test_shipments_received_history.py (7 test functions)
- FOUND: commit 9bffc20 (feat: shipments_received_history)
- FOUND: commit 94adfea (test: regression tests)
- VERIFIED: 51/51 tests passing
- VERIFIED: bullwhip ratio still 2.0000 (`tests/test_bullwhip_emerges.py::test_bullwhip_factory_retailer_peak_ratio_in_canonical_range` passes)
- VERIFIED: AST guard still streamlit-clean (`tests/test_no_streamlit_import.py` 4/4)

---
*Phase: 02-ui-shell-per-turn-play*
*Completed: 2026-05-18*
