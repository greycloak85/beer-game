---
phase: 01-simulation-engine-ai
plan: 02
subsystem: ai
tags: [python, dataclasses, pytest, sterman, beer-game, anchor-and-adjust, ast-walk, eng-01-guard]

# Dependency graph
requires:
  - phase: 01-simulation-engine-ai
    plan: 01
    provides: "StationView/RetailerView data model, runtime-checkable Agent Protocol, ConstantOrderAgent helper, beergame.ai package + tests/ tree, pyproject + venv"
provides:
  - "ShipmentAnchorAndAdjustAgent (Sterman 1989 empirical median fit) at beergame/ai/sterman.py"
  - "beergame.ai package re-exports Agent + ConstantOrderAgent + ShipmentAnchorAndAdjustAgent from a single module path"
  - "9 pytest tests verifying parameter defaults, Agent Protocol conformance, exact equilibrium-view order, exponential-smoothing math, backlog/supply-line sign sensitivity, zero floor, RetailerView compatibility"
  - "AST-walk pytest guard (ENG-01) preventing streamlit imports anywhere under beergame/engine/, beergame/ai/, beergame/config/ for the rest of the project's lifetime"
affects: [01-03-gates, 02-ui-shell]

# Tech tracking
tech-stack:
  added: []   # stdlib + pytest only, no new deps
  patterns:
    - "Mutable @dataclass (not frozen) for agents -- per-instance smoothed_demand must be writable across weeks"
    - "Per-agent forecast state carried on the agent, NOT threaded through StationView (keeps engine state separate from agent state)"
    - "AST-walk import guard parametrized across engine-layer subdirectories with file:line failure diagnostics"

key-files:
  created:
    - "beergame/ai/sterman.py -- ShipmentAnchorAndAdjustAgent with cited docstring + empirical 1989 defaults"
    - "tests/test_sterman_heuristic.py -- 9 tests for AI-01 (formula + defaults) and AI-02 (Protocol conformance)"
    - "tests/test_no_streamlit_import.py -- ENG-01 AST guard (3 parametric + 1 directory-existence sanity test)"
  modified:
    - "beergame/ai/__init__.py -- add ShipmentAnchorAndAdjustAgent to re-exports (preserves Plan 01's Agent + ConstantOrderAgent)"

key-decisions:
  - "Locked desired_inventory (S') = 17.0 per Sterman 1989 median; if Plan 03 GATE 2 misses [2.0, 4.0], adjust S' here, NEVER widen the test bounds."
  - "Used the EMPIRICAL parameters (alpha=0.26, beta=0.34, theta=0.36) — explicitly NOT the JASSS 2014 optimal values (alpha=beta=1, theta=0). The empirical parameters REPRODUCE the bullwhip; optimal MINIMIZES it. Reproduction is the teaching point."
  - "Agent is a mutable @dataclass (not frozen) because decide_order updates self.smoothed_demand each week. Per-agent forecast state is kept on the agent, not threaded through StationView, so engine state and agent state stay cleanly separated."
  - "smoothed_demand initial value = 4.0 (equilibrium throughput). This lets a week-1 view with last_order_received=4 produce the same smoothed_demand=4 after one update, so the system stays consistent until demand actually changes."
  - "AST-walk approach (not grep): catches both 'import streamlit' and 'from streamlit import x' nodes, ignores docstring/comment occurrences, prints file:line on failure, runs inside the same pytest green-bar that gates the rest of the phase."

# Metrics
duration: 2min
completed: 2026-05-18
---

# Phase 1 Plan 2: Sterman Agent + Engine-Layer Streamlit Guard

**ShipmentAnchorAndAdjustAgent with the EMPIRICAL Sterman 1989 median parameter fit, plus the ENG-01 AST-walk pytest guard that locks the engine/ai/config layers to stdlib-only Python for the remainder of the project.**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-05-18T20:11:55Z
- **Completed:** 2026-05-18T20:14:35Z
- **Tasks:** 2
- **Files created:** 3 (sterman.py + 2 test files); 1 modified (ai/__init__.py)
- **Tests:** 33 pass / 0 fail (20 from Plan 01 + 9 new Sterman + 4 new streamlit guard)

## Accomplishments

- `ShipmentAnchorAndAdjustAgent` ships at `beergame/ai/sterman.py` with the EMPIRICAL Sterman 1989 Table 2 median fit (alpha=0.26, beta=0.34, theta=0.36, S'=17.0) and a module docstring that explicitly cites the paper and names the JASSS 2014 optimal-parameter trap.
- `beergame.ai.__init__` now re-exports BOTH `ConstantOrderAgent` (from Plan 01) AND `ShipmentAnchorAndAdjustAgent` (from this plan), so Plan 03 can write `from beergame.ai import ConstantOrderAgent, ShipmentAnchorAndAdjustAgent` and have both gates source from one module.
- 9 pytest tests pin the parameter defaults, Protocol conformance, and (critically) the exact `decide_order` result of 3 at a perfectly-equilibrated view -- this single test would catch any future PR that flipped alpha/beta/theta to the "optimal" values, because the formula would then return 4 instead of 3.
- AST-walk pytest guard (`tests/test_no_streamlit_import.py`) parametrizes over `beergame/engine/`, `beergame/ai/`, `beergame/config/` and fails fast on any `import streamlit` / `from streamlit.* import ...` node, printing the offending file:line. A separate sanity test guards against globbing bugs that would silently pass with empty file lists.
- Sabotage-verified: temporarily adding `import streamlit` to `beergame/engine/demand.py` made the guard FAIL with `beergame/engine/demand.py:7: import streamlit`. The sabotage was reverted; the post-revert `git diff` is empty.

## Task Commits

1. **Task 1: Sterman agent + 9 tests + beergame.ai re-exports** -- `e6d150c` (feat)
2. **Task 2: ENG-01 AST-walk streamlit-import guard + sabotage verification** -- `2b0bbb0` (feat)

## Files Created / Modified

**Created (Plan 02):**
- `beergame/ai/sterman.py` -- `ShipmentAnchorAndAdjustAgent` dataclass with cited docstring; empirical defaults locked at class-attribute level.
- `tests/test_sterman_heuristic.py` -- 9 tests covering AI-01 + AI-02.
- `tests/test_no_streamlit_import.py` -- ENG-01 AST-walk guard (3 parametric + 1 sanity).

**Modified (Plan 02):**
- `beergame/ai/__init__.py` -- added `ShipmentAnchorAndAdjustAgent` to imports + `__all__`. `Agent` and `ConstantOrderAgent` re-exports from Plan 01 preserved.

## The Locked Value: S' = 17.0

`desired_inventory = 17.0` is set at the class-attribute level in `ShipmentAnchorAndAdjustAgent`. This is the Sterman 1989 median empirical value per `.planning/research/SUMMARY.md` and `.planning/phases/01-simulation-engine-ai/01-RESEARCH.md`.

**If Plan 03 GATE 2 misses the [2.0, 4.0] bullwhip-ratio window, the fix is to tune S' here -- NEVER widen the test bounds.** The bounds are the contract; the agent parameter is the knob.

(For reference: the architecture sketch used S'=12 in places; the locked value is 17 per research. `test_default_parameters_match_sterman_1989_empirical_fit` pins this so a future "tweak" gets caught.)

## The 9 Sterman tests, and what each pins

| # | Test                                                  | What it pins (and why)                                                                                                                                                                                                       |
| - | ----------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1 | `test_default_parameters_match_sterman_1989_empirical_fit` | alpha=0.26, beta=0.34, theta=0.36, S'=17.0, smoothed_demand=4.0 -- exact equality, not approx. A bulk parameter swap to "optimal" (1, 1, 0) fails here.                                                                       |
| 2 | `test_protocol_conformance`                           | `isinstance(a, Agent)` -- catches accidental renames of `decide_order` or signature changes that break the runtime-checkable Protocol.                                                                                       |
| 3 | `test_order_formula_returns_non_negative_int`         | `decide_order` returns `int`, not `float` -- protects against silent float leakage that would break GameState's int-tuple histories.                                                                                          |
| 4 | `test_order_at_perfect_equilibrium_view_is_3`         | **THE BIG ONE.** At inv=12, bl=0, SL=8, smoothed=4, last_order=4 with empirical defaults: `round(4 + 0.26*5 - 0.34*8) = round(2.58) = 3`. If this returns 4, someone swapped in optimal alpha=beta=1, theta=0 -- GATE 2 would then fail silently. |
| 5 | `test_smoothed_demand_updates_via_exponential_smoothing` | `L = 0.36*8 + 0.64*4 = 5.44` after one D=8 observation, then `0.36*8 + 0.64*5.44` after two. Pins the smoothing math + theta value.                                                                                          |
| 6 | `test_high_backlog_drives_higher_order`               | Sign sensitivity: net_stock term must INCREASE order under backlog.                                                                                                                                                          |
| 7 | `test_high_supply_line_dampens_order`                 | Sign sensitivity: beta*supply_line term must DECREASE order. The empirical underweighting (beta=0.34) is what produces the bullwhip; this test ensures the term is at least directionally correct.                          |
| 8 | `test_order_floor_is_zero`                            | `max(0, round(...))` clip -- never negative orders.                                                                                                                                                                          |
| 9 | `test_retailer_view_also_works`                       | `RetailerView` (subclass of StationView) is accepted transparently -- structural typing works for both view types.                                                                                                            |

### Subtle behavior worth noting (carries into Plan 03)

**Empirical Sterman does NOT trivially maintain inventory=12 equilibrium.** Test #4 above pins the result that at the perfect-equilibrium view, the agent orders 3, not 4. This is the correct empirical behavior -- beta=0.34 underweights the supply line -- and is precisely WHY:

- **Plan 03 GATE 1** (engine arithmetic correctness) must use `ConstantOrderAgent(4)` + `constant_demand`, NOT Sterman. With Sterman, the system drifts to a different steady state and inventory does not stay at 12.
- **Plan 03 GATE 2** (bullwhip emergence under step demand) is where Sterman belongs. The same beta underweighting that prevents trivial equilibrium produces the bullwhip when demand steps from 4 to 8.

This split is documented in the plan; the test exists to catch anyone who later tries to "fix" this perceived bug by flipping to optimal parameters.

## The AST guard and the sabotage that proved it

`tests/test_no_streamlit_import.py` parametrizes over three subdirectories and `ast.walk`s every `.py` file under each, rejecting any `ast.Import` or `ast.ImportFrom` node naming streamlit. On failure it prints `path:line: import streamlit` so the fix is grep-trivial.

**Sabotage actually executed and reverted (not just reasoned about):**

1. `Edit` added `import streamlit  # SABOTAGE -- will be reverted` as line 7 of `beergame/engine/demand.py`.
2. `pytest tests/test_no_streamlit_import.py --noconftest -q` (the `--noconftest` flag is needed because the project's `conftest.py` eagerly imports `beergame.ai` which now indirectly imports the sabotaged `demand.py`, and streamlit isn't installed; this is itself a useful confirmation that streamlit really is absent from the runtime environment).
3. The parametric `[beergame/engine]` case FAILED with the exact message: `Failed: Streamlit imports found in engine layer (beergame/engine): beergame/engine/demand.py:7: import streamlit`. The other two parametric cases (`beergame/ai`, `beergame/config`) plus the directory-existence sanity test all passed -- so the guard correctly localizes the offending directory.
4. `Edit` reverted the sabotage line. `git diff beergame/engine/demand.py` is empty.
5. Full `pytest -q` from the repo root then passed all 33 tests.

## beergame.ai package surface after Plan 02

```python
from beergame.ai import Agent, ConstantOrderAgent, ShipmentAnchorAndAdjustAgent
```

All three are exported and visible via `beergame.ai.__all__`. Plan 03 can pull both agents from this single module path -- no need to reach into `beergame.ai.base` or `beergame.ai.sterman` directly.

## Patterns Plan 03 should follow

**GATE 1 (engine arithmetic, NOT bullwhip):**

```python
from beergame.ai import ConstantOrderAgent
from beergame.engine import Role, simulate_full_game
from beergame.engine.demand import constant_demand

state = simulate_full_game(
    seed=42,
    player_role=Role.RETAILER,
    agents={r: ConstantOrderAgent(4) for r in Role},
    demand_fn=constant_demand,
)
# Assert: every station's inventory_history is all 12, backlog_history all 0.
```

**GATE 2 (bullwhip emergence under step demand):**

```python
from beergame.ai import ShipmentAnchorAndAdjustAgent
from beergame.engine import Role, simulate_full_game
from beergame.engine.demand import demand_for_week
from beergame.engine.metrics import bullwhip_ratio

state = simulate_full_game(
    seed=42,
    player_role=Role.RETAILER,
    agents={r: ShipmentAnchorAndAdjustAgent() for r in Role},  # default empirical params
    demand_fn=demand_for_week,
)
ratio = bullwhip_ratio(state)
assert 2.0 <= ratio <= 4.0, (
    f"bullwhip ratio {ratio} outside Sterman empirical window [2.0, 4.0]. "
    f"Tune ShipmentAnchorAndAdjustAgent.desired_inventory in beergame/ai/sterman.py "
    f"(currently 17.0); do NOT widen the bounds."
)
```

**Note:** Each agent instance carries its own `smoothed_demand` state across weeks, so the comprehension `{r: ShipmentAnchorAndAdjustAgent() for r in Role}` is the right pattern (four independent agents, not one shared). Plan 01's `simulate_full_game` is already in place and calls `decide_order` once per role per week.

## Deviations from Plan

### Auto-fixed Issues

**None.** Plan 02 executed exactly as written.

### Notes on verify-command nuance (not a deviation, just useful documentation)

The plan's verify command for the sabotage test was `pytest tests/test_no_streamlit_import.py` (without `--noconftest`). Running it that way produces an `ImportError` during conftest collection because the project's `conftest.py` (added in Plan 01) imports `beergame.ai`, which now (post-Plan-02) imports `beergame.ai.sterman`, which imports `beergame.engine.state`, which loads `beergame.engine.__init__`, which loads `beergame.engine.tick`, which imports `beergame.engine.demand` -- and the sabotaged `demand.py` then does `import streamlit` at the Python level, raising `ModuleNotFoundError` because streamlit isn't installed.

That is itself a useful confirmation that streamlit truly is absent from the runtime environment, but it short-circuits the AST test from ever running. Using `--noconftest` for the sabotage verification bypasses the eager imports and lets the AST walk run, producing the clean file:line diagnostic. The actual project-day failure mode for a streamlit creep would depend on whether streamlit was installed (it will be, post-Plan-04), in which case the conftest import would succeed and the AST test would fire normally. No code change is needed; this is just a verification-technique note.

## Issues Encountered

None. Both tasks ran first-try without any rule-1/2/3 auto-fixes.

## Next Plan Readiness

- All Plan 03 (Phase 1 exit gates) prerequisites are now in place:
  - `simulate_full_game` driver from Plan 01.
  - `ConstantOrderAgent` + `ShipmentAnchorAndAdjustAgent` both exported from `beergame.ai`.
  - `constant_demand` + `demand_for_week` from Plan 01.
  - `bullwhip_ratio` stub from Plan 01 (Plan 03 fleshes out / verifies the metric).
  - ENG-01 streamlit-import guard already green -- Plan 03 inherits the same green-bar gate.

---

## Self-Check: PASSED

Files verified to exist:
- FOUND: /home/williamlefew/projects/beergameNexStratus/beergame/ai/sterman.py
- FOUND: /home/williamlefew/projects/beergameNexStratus/beergame/ai/__init__.py (modified)
- FOUND: /home/williamlefew/projects/beergameNexStratus/tests/test_sterman_heuristic.py
- FOUND: /home/williamlefew/projects/beergameNexStratus/tests/test_no_streamlit_import.py

Commits verified:
- FOUND: e6d150c (Task 1 -- Sterman agent + tests)
- FOUND: 2b0bbb0 (Task 2 -- AST-walk streamlit guard)

Pytest:
- Full suite: 33 passed / 0 failed.
- Targeted (`tests/test_sterman_heuristic.py tests/test_no_streamlit_import.py`): 13 passed / 0 failed.
- Sabotage round-trip verified: AST guard fires on `import streamlit` in `beergame/engine/demand.py:7` and the sabotage is fully reverted (clean `git diff`).

Requirements satisfied: AI-01, AI-02, ENG-01.

---
*Phase: 01-simulation-engine-ai*
*Completed: 2026-05-18*
