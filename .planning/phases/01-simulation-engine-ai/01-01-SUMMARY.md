---
phase: 01-simulation-engine-ai
plan: 01
subsystem: engine
tags: [python, dataclasses, pytest, sterman, beer-game, simulation, frozen-dataclass]

# Dependency graph
requires:
  - phase: 00-roadmap-and-research
    provides: Phase 1 research, canonical tick sequence, Sterman parameter specification, requirements ENG-02..ENG-10 + AI-02
provides:
  - "Frozen-dataclass GameState/StationState data model with int-valued Role enum"
  - "new_game() canonical equilibrium init (inv=12, bl=0, shipping=(4,4), inbound orders=(4,) at every station INCLUDING Factory)"
  - "5-step canonical tick (receive_shipments, fill_orders, record_state, place_orders, advance_pipelines) composed by advance_week"
  - "simulate_full_game(seed, player_role, agents, demand_fn) driver — Plan 03 GATE 1/GATE 2 consume this directly"
  - "Asymmetric weekly_cost (0.50 holding, 1.00 backlog) + cumulative cost_history"
  - "demand_for_week (4→8 step) + constant_demand (test helper) — both pure, no global RNG"
  - "Runtime-checkable Agent Protocol + ConstantOrderAgent test helper"
  - "RetailerView vs StationView visibility split — only Retailer view exposes customer_demand"
  - "20 passing pytest invariant tests across 4 files covering ENG-05, ENG-06, ENG-07, ENG-08, ENG-09, ENG-10"
affects: [01-02-sterman-agent, 01-03-gates, 02-ui-shell, 03-debrief-charts]

# Tech tracking
tech-stack:
  added: [pytest>=8 (dev), ruff>=0.6 (dev), setuptools editable build]
  patterns:
    - "Frozen + slotted dataclasses with dataclasses.replace for state updates"
    - "Transient intra-tick fields (compare=False, repr=False) carry data between named tick steps"
    - "Pure-function tick steps composed left-to-right by advance_week"
    - "Integer-valued Role enum used as tuple index into GameState.stations"
    - "Protocol + TYPE_CHECKING import to break ai/base ↔ engine.tick circular dependency"

key-files:
  created:
    - "beergame/engine/state.py — data model"
    - "beergame/engine/tick.py — 5-step tick + simulate_full_game"
    - "beergame/engine/costs.py — weekly_cost / total_cost"
    - "beergame/engine/demand.py — demand_for_week / constant_demand"
    - "beergame/engine/metrics.py — peak_orders / bullwhip_ratio (stub)"
    - "beergame/config/costs.py — HOLDING_COST=0.50 / BACKORDER_COST=1.00"
    - "beergame/config/scenarios.py — TOTAL_WEEKS=36, ORDER_PIPELINE_LEN_FACTORY=1, etc."
    - "beergame/ai/base.py — Agent Protocol + ConstantOrderAgent"
    - "tests/test_determinism.py — ENG-09"
    - "tests/test_tick_invariants.py — ENG-06, ENG-07 + BLOCKER 1 fix verification"
    - "tests/test_costs.py — ENG-05, ENG-08"
    - "tests/test_station_view_visibility.py — ENG-10"
    - "tests/conftest.py — shared fixtures"
    - "pyproject.toml / requirements-dev.txt / .python-version — dev install"
    - ".gitignore — venv + caches"
  modified: []

key-decisions:
  - "ORDER_PIPELINE_LEN_FACTORY = 1 (NOT 0): Factory inbound order channel uses canonical 1-week mailing delay. The 'no order delay at Factory' phrase refers ONLY to Factory's own order→production path, not the Distributor→Factory inbound channel."
  - "Factory's own placed order routes to its OWN _pending_in_shipment (production start), bypassing any order-mailing channel. Step 5 then places it in Factory.incoming_shipments back slot for SHIPPING_PIPELINE_LEN=2 weeks of production lead time."
  - "Transient fields _pending_in_shipment / _pending_in_order / _demand_to_fill / _shipped_this_tick on StationState (compare=False, repr=False) carry data between named tick steps; zeroed at end of step 5 / step 3."
  - "Agent Protocol uses TYPE_CHECKING import for StationView to break engine/__init__.py → tick → ai.base → engine.state circular dependency. The StationView reference appears only in annotations, so runtime import is unnecessary."
  - "v1 limitation accepted: build_station_view at top of simulate_full_game loop reads last week's recorded customer_demand; for week 0 it falls back to CLASSIC_PRE_STEP_DEMAND=4. Both supplied demand_fns (demand_for_week, constant_demand) start at 4, so v1 is consistent. Structural fix (thread demand_fn through build_station_view) deferred to v2."

patterns-established:
  - "Frozen, slotted, hashable dataclasses + dataclasses.replace — never mutate state"
  - "Each tick step is a separate pure function (GameState, ...) -> GameState; advance_week composes them in fixed source order"
  - "History tuples grow by exactly one entry per tick, in step 3 (record_state)"
  - "Engine package is stdlib-only — zero numpy, pandas, or streamlit imports"
  - "Plan 02 places Sterman agent at beergame/ai/sterman.py, conforms to the same Agent Protocol"

requirements-completed: [ENG-02, ENG-03, ENG-04, ENG-05, ENG-06, ENG-07, ENG-08, ENG-09, ENG-10, AI-02]

# Metrics
duration: 5min
completed: 2026-05-18
---

# Phase 1 Plan 1: Simulation Engine Foundation Summary

**Pure-Python Beer Game engine — frozen-dataclass state, 5-step canonical tick, asymmetric costs, Agent Protocol — with 20 passing pytest invariant tests proving correctness independent of any AI.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-05-18T20:02:53Z
- **Completed:** 2026-05-18T20:07:59Z
- **Tasks:** 2
- **Files created:** 19 (engine + config + ai + tests + pyproject + gitignore)
- **Tests:** 20 pass / 0 fail

## Accomplishments

- Engine reaches `week=36 phase=done` with **all four stations at inventory=12** under all-ConstantOrderAgent(4) + constant demand=4 — the BLOCKER 1 fix verified (Factory no longer stuck at 16). This is the canonical equilibrium that Plan 03 GATE 1 will formalize.
- Five-step tick fully decomposed (receive_shipments → fill_orders → record_state → place_orders → advance_pipelines) with intra-tick transient fields; advance_week composes them in fixed order.
- Determinism (ENG-09) proven: two same-seed runs produce field-by-field identical traces; player_role choice does not change the engine trace (it's UI-only).
- Cost asymmetry (ENG-05) and view visibility (ENG-10) enforced and tested.
- Engine is stdlib-only: `grep -rn "import streamlit\|numpy\|pandas" beergame/` returns nothing.

## Task Commits

Each task was committed atomically:

1. **Task 1: Scaffold beergame package, state, demand, costs, Agent protocol** — `d90e8a6` (feat)
2. **Task 2: 5-step tick + four invariant test suites** — `1435309` (feat)

## Files Created/Modified

**Engine (pure Python, stdlib-only):**
- `beergame/__init__.py` — empty
- `beergame/engine/__init__.py` — public-API re-exports (Role, StationState, GameState, StationView, RetailerView, new_game, build_station_view, advance_week, simulate_full_game, is_game_over)
- `beergame/engine/state.py` — Role enum, StationState (frozen + slotted, with 4 transient fields), GameState, StationView, RetailerView, new_game(), build_station_view()
- `beergame/engine/tick.py` — receive_shipments, fill_orders, record_state, place_orders, advance_pipelines, advance_week, is_game_over, simulate_full_game
- `beergame/engine/costs.py` — weekly_cost, total_cost
- `beergame/engine/demand.py` — demand_for_week (classic 4→8 step), constant_demand (helper for GATE 1)
- `beergame/engine/metrics.py` — peak_orders, bullwhip_ratio (stubs; Phase 3 fleshes out)

**Configuration:**
- `beergame/config/__init__.py` — empty
- `beergame/config/costs.py` — HOLDING_COST=0.50, BACKORDER_COST=1.00
- `beergame/config/scenarios.py` — canonical Sterman constants; ORDER_PIPELINE_LEN_FACTORY=1 with extended docstring explaining the asymmetry

**AI:**
- `beergame/ai/__init__.py` — re-exports Agent, ConstantOrderAgent
- `beergame/ai/base.py` — runtime-checkable Agent Protocol + ConstantOrderAgent test helper (StationView imported under TYPE_CHECKING to break circular import)

**Tests (4 invariant suites, 20 total tests):**
- `tests/__init__.py` — empty
- `tests/conftest.py` — initial_game / constant_4_agents fixtures
- `tests/test_determinism.py` — 3 tests (ENG-09)
- `tests/test_tick_invariants.py` — 7 tests (ENG-06, ENG-07, BLOCKER 1 fix verification)
- `tests/test_costs.py` — 5 tests (ENG-05, ENG-08)
- `tests/test_station_view_visibility.py` — 5 tests (ENG-10, including 3 parametrized non-Retailer roles)

**Build / dev tooling:**
- `pyproject.toml` — minimal beergame package metadata + pytest + ruff config
- `requirements-dev.txt` — pytest, ruff
- `.python-version` — 3.12
- `.gitignore` — venv + caches

## Decisions Made

### Factory inbound order channel — canonical 1-week mailing delay (BLOCKER 1 fix)

`ORDER_PIPELINE_LEN_FACTORY = 1` (NOT 0). Factory's `incoming_orders` at game init is `(4,)`, NOT empty. This is the explicit fix for the v1 design's BLOCKER 1: with the old (0, empty) configuration, `fill_orders` saw `s.incoming_orders[0] if s.incoming_orders else 0` evaluate to 0, so Factory shipped nothing and its inventory grew unboundedly while Distributor starved. The "no order delay at Factory" phrase in the Sterman / JASSS literature refers ONLY to Factory's own order→production path (Factory's placed order goes straight into its own `_pending_in_shipment`, skipping any mailing channel), NOT to the Distributor→Factory inbound order channel (which uses the same canonical 1-week mailing delay as R/W/D).

### Transient field pattern on StationState

Four `compare=False, repr=False` fields carry intra-tick data between named steps:
- `_demand_to_fill` — set by step 2, consumed by step 3 (appended to orders_received_history)
- `_shipped_this_tick` — set by step 2, consumed by step 3 (appended to shipments_sent_history)
- `_pending_in_shipment` — set by step 2 (downstream shipping) and step 4 (Factory production), consumed by step 5 (becomes incoming_shipments back slot)
- `_pending_in_order` — set by step 4 (R/W/D upstream orders), consumed by step 5 (becomes incoming_orders back slot)

All four are zeroed at end of step 5 (the latter two) / step 3 (the former two). `compare=False` keeps GameState equality based on observable state only — two states with different transient-field histories but the same observable state compare equal, which keeps the determinism test simple.

### TYPE_CHECKING for StationView in ai/base.py

`beergame/engine/__init__.py` re-exports from `tick`, and `tick` imports `Agent` from `ai.base`. If `ai.base` then imports `StationView` from `engine.state` eagerly, Python re-enters the partially-initialized `engine` package and raises `ImportError`. `StationView` is referenced only in Protocol annotations, so importing under `TYPE_CHECKING` and using a forward reference resolves the cycle cleanly without adding indirection.

### v1 limitation: build_station_view in simulate_full_game

At the top of the `simulate_full_game` loop, the player's `RetailerView.customer_demand` is built from `state.customer_demand_history[-1]` — i.e., last week's recorded demand. For week 0 (history is empty) it falls back to `CLASSIC_PRE_STEP_DEMAND = 4`. Both supplied `demand_fn`s (`demand_for_week`, `constant_demand`) start at 4 in week 1, so the v1 fallback is consistent. A structural fix would require threading `demand_fn` through `build_station_view` so it can compute next-week demand; deferred to v2.

### S' = 17 lives in Plan 02

This plan establishes `EQUILIBRIUM_THROUGHPUT = 4` (the constant that pre-fills every pipeline slot). The Sterman empirical desired stock S'=17 is the Plan 02 agent contract, not a Plan 01 deliverable; it does not appear here.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Resolved circular import between `beergame.ai.base` and `beergame.engine.tick`**

- **Found during:** Task 2 (first `pytest` invocation after writing `tick.py`)
- **Issue:** `beergame/engine/__init__.py` (written in Task 1) re-exports symbols from `beergame.engine.tick`. `tick.py` imports `Agent` from `beergame.ai.base`. `beergame.ai.base` (as originally written in Task 1) eagerly imported `StationView` from `beergame.engine.state`, which re-entered the still-loading `beergame.engine` package and raised `ImportError: cannot import name 'Agent' from partially initialized module 'beergame.ai.base'`. Plan 01 anticipated that Task 1's `engine/__init__.py` could not be imported until Task 2's `tick.py` existed, but did not anticipate the circularity caused by `ai.base` itself reaching into the engine package.
- **Fix:** Moved the `StationView` import in `beergame/ai/base.py` under `if TYPE_CHECKING:` and switched the two `StationView` annotations to forward references (`"StationView"`). The Protocol no longer needs `StationView` at runtime — only type checkers consume it. The cycle is broken without changing any public behavior. `isinstance(ConstantOrderAgent(7), Agent)` still returns `True`.
- **Files modified:** `beergame/ai/base.py`
- **Verification:** `python -m pytest tests/ -v` → 20 passed; `python -c "from beergame.engine import new_game, advance_week, simulate_full_game, Role; print('engine API: OK')"` → "engine API: OK"; `python -c "from beergame.ai.base import Agent, ConstantOrderAgent; print(isinstance(ConstantOrderAgent(7), Agent))"` → True.
- **Committed in:** `1435309` (Task 2 commit)

**2. [Rule 2 - Missing Critical] Added `.gitignore` for venv and Python caches**

- **Found during:** Task 1 (pre-commit `git status` showed `.venv/`, `__pycache__/`, `beergame.egg-info/` as untracked)
- **Issue:** No `.gitignore` existed. Without one, ad-hoc `git add` would silently include the local venv and bytecode caches on developer machines.
- **Fix:** Added a minimal `.gitignore` covering `.venv/`, `__pycache__/`, `*.egg-info/`, `*.pyc`, `.pytest_cache/`, `.ruff_cache/`.
- **Files modified:** `.gitignore`
- **Verification:** `git status --short` no longer shows the cache directories after the commit.
- **Committed in:** `d90e8a6` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 missing critical hygiene file)
**Impact on plan:** Both auto-fixes essential. The circular-import fix was required for any test to load; the `.gitignore` prevents accidental commits of build artifacts.

## Issues Encountered

- **Cannot use `python3.12 -m venv` directly on this WSL machine** (ensurepip not bundled). Worked around by creating `--without-pip` venv and bootstrapping pip via `get-pip.py`. The fix is environment-specific and does not affect any committed file — only the local dev install procedure (which is dev-only, not a deploy concern; Phase 4 owns deploy).

## simulate_full_game readiness for Plan 03

`beergame.engine.tick.simulate_full_game(seed, player_role, agents, demand_fn, total_weeks=None)` is implemented and verified. Plan 03 (engine gates) needs only to write two test files:

- **GATE 1** (`tests/test_engine_gates.py::test_equilibrium_under_constant_agents`): call `simulate_full_game(seed=42, player_role=Role.RETAILER, agents={r: ConstantOrderAgent(4) for r in Role}, demand_fn=constant_demand)` and assert every station's `inventory_history` is all 12s and `backlog_history` is all zeros. This is already proven manually in the verify command above — the engine reaches `week=36 phase=done` with `[12, 12, 12, 12]` final inventories.
- **GATE 2** (bullwhip ratio): once Plan 02 ships `beergame.ai.sterman.StermanAgent`, call `simulate_full_game(seed=42, ..., agents={r: StermanAgent(...) for r in Role}, demand_fn=demand_for_week)` and assert `bullwhip_ratio(state)` is within `[2.0, 4.0]`. `metrics.bullwhip_ratio` is in place.

## Patterns for Plan 02 to follow

- Sterman agent file: `beergame/ai/sterman.py`. Class `StermanAgent` (or similar) conforming to the `Agent` Protocol — implements `decide_order(view: StationView) -> int`. Re-export from `beergame/ai/__init__.py`.
- Empirical parameters: α≈0.26 (inventory adjustment), β≈0.34 (supply line adjustment), θ≈0.36 (demand smoothing), S'≈17 (desired stock). NOT the JASSS 2014 "optimal" values.
- Plan 02 also adds the streamlit-import guard: `tests/test_no_streamlit_import.py` runs `grep -rn "import streamlit" beergame/` (or equivalent AST walk) and asserts zero matches. The codebase already satisfies this; Plan 02 just formalizes it.
- All new code uses the same conventions established here: stdlib-only, frozen dataclasses + `dataclasses.replace`, pure functions, no global RNG state.

## Next Phase Readiness

- ✅ Engine ready for Plan 02 (Sterman agent) and Plan 03 (engine gates).
- ✅ `simulate_full_game` driver in place; Plan 03 needs only to write the two gate-test files.
- ✅ Cost / view / determinism / canonical-tick invariants all proven via pytest.
- ⚠️ Reminder for Phase 4 (deploy): `requirements.txt` (separate from `requirements-dev.txt`) does not yet exist — Phase 4 owns that file per the DEPLOY-03 decision in PROJECT.md.

---

## Self-Check: PASSED

Files verified to exist:
- FOUND: /home/williamlefew/projects/beergameNexStratus/beergame/engine/state.py
- FOUND: /home/williamlefew/projects/beergameNexStratus/beergame/engine/tick.py
- FOUND: /home/williamlefew/projects/beergameNexStratus/beergame/engine/costs.py
- FOUND: /home/williamlefew/projects/beergameNexStratus/beergame/engine/demand.py
- FOUND: /home/williamlefew/projects/beergameNexStratus/beergame/engine/metrics.py
- FOUND: /home/williamlefew/projects/beergameNexStratus/beergame/config/costs.py
- FOUND: /home/williamlefew/projects/beergameNexStratus/beergame/config/scenarios.py
- FOUND: /home/williamlefew/projects/beergameNexStratus/beergame/ai/base.py
- FOUND: /home/williamlefew/projects/beergameNexStratus/tests/test_determinism.py
- FOUND: /home/williamlefew/projects/beergameNexStratus/tests/test_tick_invariants.py
- FOUND: /home/williamlefew/projects/beergameNexStratus/tests/test_costs.py
- FOUND: /home/williamlefew/projects/beergameNexStratus/tests/test_station_view_visibility.py
- FOUND: /home/williamlefew/projects/beergameNexStratus/pyproject.toml
- FOUND: /home/williamlefew/projects/beergameNexStratus/.gitignore

Commits verified:
- FOUND: d90e8a6 (Task 1)
- FOUND: 1435309 (Task 2)

Pytest: 20 passed / 0 failed.

---
*Phase: 01-simulation-engine-ai*
*Completed: 2026-05-18*
