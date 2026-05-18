---
phase: 01-simulation-engine-ai
verified: 2026-05-18T16:30:00Z
status: passed
score: 5/5 success criteria verified (14/14 requirements satisfied; 44/44 tests pass)
---

# Phase 1: Simulation Engine + AI Verification Report

**Phase Goal:** A pure-Python simulation engine and Sterman AI that demonstrably reproduce the canonical Beer Game equilibrium and bullwhip, verifiable by pytest without any Streamlit dependency.

**Verified:** 2026-05-18T16:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Phase 1 Success Criteria)

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1   | GATE 1 — `pytest tests/test_equilibrium.py` passes; constant demand=4, all-ConstantOrderAgent → inventory=12 for all 36 weeks | VERIFIED | 6/6 tests pass (`6 passed in 0.04s`); strict per-tick assertions on inventory, backlog, orders, costs; Factory inventory explicit guard. |
| 2   | GATE 2 — `pytest tests/test_bullwhip_emerges.py` passes; classic step demand, all-Sterman → max(factory_orders)/max(retailer_orders) ∈ [2.0, 4.0] | VERIFIED | 5/5 tests pass; live run yields `Retailer peak=11, Factory peak=22, Ratio=2.0000`; monotonic-upstream amplification confirmed. |
| 3   | `grep -r "import streamlit" beergame/engine beergame/ai beergame/config` returns zero matches | VERIFIED | Live grep returns exit=1 (no matches); AST-walk pytest guard `tests/test_no_streamlit_import.py` independently enforces this across all `.py` files. |
| 4   | Same seed → byte-identical traces; non-Retailer `StationView` raises `AttributeError` on `customer_demand` | VERIFIED | `tests/test_determinism.py` (3 tests, byte-identical history tuples). `tests/test_station_view_visibility.py` (5 tests, parametrized over W/D/F roles using `pytest.raises(AttributeError)`). |
| 5   | Tick sequence in canonical order — verified by `tests/test_tick_invariants.py` | VERIFIED | 7/7 tick-invariant tests pass; explicit assertion `advance_week == manual five-step compose`; transient `_pending_*` fields zeroed; spy-agent confirms agents see POST-fill state. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `beergame/engine/state.py` | Role enum, StationState, GameState, StationView, RetailerView, new_game(), build_station_view() | VERIFIED | 184 lines. All seven exports present; `Role(Enum)` with integer-indexed members; frozen+slotted dataclasses; `new_game()` pre-loads canonical equilibrium INCLUDING `Factory.incoming_orders=(4,)` (BLOCKER 1 fix); `build_station_view` returns `RetailerView` for retailer, plain `StationView` otherwise. |
| `beergame/engine/tick.py` | advance_week + 5 step functions + simulate_full_game | VERIFIED | 305 lines. All five named steps (`receive_shipments`, `fill_orders`, `record_state`, `place_orders`, `advance_pipelines`); `advance_week` composes them in canonical order; `simulate_full_game` runs until phase=="done". |
| `beergame/engine/costs.py` | weekly_cost(station), total_cost(state) | VERIFIED | 22 lines. Imports `HOLDING_COST` and `BACKORDER_COST` from config. Asymmetric formula: `0.50*inv + 1.00*backlog`. |
| `beergame/engine/demand.py` | demand_for_week (classic 4→8 step), constant_demand test helper | VERIFIED | 30 lines. `demand_for_week` returns 4 weeks 1-4, 8 weeks 5-36; `constant_demand` for GATE 1. |
| `beergame/engine/metrics.py` | peak_orders, bullwhip_ratio (Phase 1 scope; debrief expansion deferred) | VERIFIED | 22 lines. Functions used by gate tests. |
| `beergame/config/costs.py` | HOLDING_COST=0.50, BACKORDER_COST=1.00 | VERIFIED | 4 lines. Exact values match Sterman canonical asymmetry. |
| `beergame/config/scenarios.py` | CLASSIC_36W canonical constants; `ORDER_PIPELINE_LEN_FACTORY=1` | VERIFIED | 20 lines. `TOTAL_WEEKS=36`, `INITIAL_INVENTORY=12`, `EQUILIBRIUM_THROUGHPUT=4`, `SHIPPING_PIPELINE_LEN=2`, `ORDER_PIPELINE_LEN_RWD=1`, `ORDER_PIPELINE_LEN_FACTORY=1` (BLOCKER 1 fix). |
| `beergame/ai/base.py` | Agent Protocol + ConstantOrderAgent test helper | VERIFIED | 39 lines. `@runtime_checkable Agent(Protocol)` with `decide_order(view) -> int`. `ConstantOrderAgent(quantity)`. |
| `beergame/ai/sterman.py` | ShipmentAnchorAndAdjustAgent with Sterman 1989 empirical defaults | VERIFIED | 51 lines. `alpha=0.26, beta=0.34, theta=0.36, desired_inventory=17.0, smoothed_demand=4.0`. Sterman 1989 citation in module docstring with explicit empirical-vs-optimal warning. |
| `beergame/ai/__init__.py` | Re-exports Agent, ConstantOrderAgent, ShipmentAnchorAndAdjustAgent | VERIFIED | 4 lines. All three exports in `__all__`. |
| `pyproject.toml` | Local pip install -e; beergame package metadata; pytest + ruff config | VERIFIED | `name="beergame"`, `requires-python=">=3.12"`, pytest `testpaths=["tests"]`, ruff config present. |
| `.python-version` | Pins Python 3.12 | VERIFIED | Contents: `3.12`. |
| `requirements-dev.txt` | pytest, ruff | VERIFIED | `pytest>=8,<9`, `ruff>=0.6`. |
| `tests/test_equilibrium.py` | AI-04 + ENG-06 GATE 1 verification | VERIFIED | 245 lines, 6 tests pass. |
| `tests/test_bullwhip_emerges.py` | AI-03 GATE 2 verification | VERIFIED | 182 lines, 5 tests pass. |
| `tests/test_tick_invariants.py` | ENG-07 canonical five-step order | VERIFIED | 189 lines, 7 tests pass. |
| `tests/test_costs.py` | ENG-05 + ENG-08 asymmetric costs, backlog accumulation | VERIFIED | 51 lines, 5 tests pass. |
| `tests/test_determinism.py` | ENG-09 byte-identical traces from same seed | VERIFIED | 36 lines, 3 tests pass. |
| `tests/test_station_view_visibility.py` | ENG-10 RetailerView-only customer_demand | VERIFIED | 38 lines, 5 tests pass. |
| `tests/test_no_streamlit_import.py` | ENG-01 AST-walk streamlit guard | VERIFIED | 61 lines, 4 tests pass. |
| `tests/test_sterman_heuristic.py` | AI-01 + AI-02 Sterman formula + Protocol conformance | VERIFIED | 116 lines, 9 tests pass. |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `beergame/engine/tick.py::advance_week` | `beergame/engine/state.py` (StationState, GameState, build_station_view) | imports + dataclasses.replace mutation | WIRED | Confirmed at `tick.py:29` (`from dataclasses import replace`) and `tick.py:35-40` (`from beergame.engine.state import ...`). |
| `beergame/engine/tick.py::place_orders` | `beergame/ai/base.py::Agent.decide_order` | calls `agent.decide_order(view)` for each non-player role | WIRED | `tick.py:188`: `orders_placed[i] = max(0, int(ai_agents[role].decide_order(view)))`. Also `tick.py:302`: player path. |
| `beergame/engine/costs.py::weekly_cost` | `beergame/config/costs.py` (HOLDING_COST, BACKORDER_COST) | imports module-level constants | WIRED | `costs.py:7`: `from beergame.config.costs import BACKORDER_COST, HOLDING_COST`. |
| `beergame/ai/sterman.py::ShipmentAnchorAndAdjustAgent` | `beergame/ai/base.py::Agent` (Protocol) | structural typing; isinstance via @runtime_checkable | WIRED | `test_sterman_heuristic.py::test_protocol_conformance` asserts `isinstance(a, Agent)` and passes. |
| `beergame/ai/sterman.py::decide_order` | `beergame/engine/state.py::StationView` | reads view.inventory, view.backlog, view.supply_line, view.last_order_received | WIRED | `sterman.py:42-49` consumes all four fields. |
| `tests/test_no_streamlit_import.py` | `beergame/engine/, ai/, config/` trees | ast.parse + ast.walk on every .py file | WIRED | Parametric test over three subdirs; live grep also returns zero matches. |
| `tests/test_equilibrium.py` | `simulate_full_game + ConstantOrderAgent + constant_demand` | drives 36 weeks; asserts equilibrium invariants | WIRED | All 6 tests pass. |
| `tests/test_bullwhip_emerges.py` | `simulate_full_game + ShipmentAnchorAndAdjustAgent + demand_for_week` | drives 36 weeks; asserts ratio in [2.0, 4.0] | WIRED | All 5 tests pass; live ratio = 2.0000. |

### Requirements Coverage

All 14 Phase 1 requirement IDs are accounted for. ROADMAP.md/REQUIREMENTS.md traceability maps every ID to a Phase 1 plan; verified each is exercised by at least one passing test.

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| ENG-01 | 01-02 | Engine module is pure Python with zero `streamlit` imports | SATISFIED | `tests/test_no_streamlit_import.py` (4 tests pass); live `grep -r "import streamlit"` returns no matches. |
| ENG-02 | 01-01 | 4-station serial supply chain: Retailer → Wholesaler → Distributor → Factory | SATISFIED | `Role(Enum)` in `state.py:28-33` with RETAILER=0, WHOLESALER=1, DISTRIBUTOR=2, FACTORY=3; `tests/test_tick_invariants.py::test_initial_state_is_canonical_equilibrium` iterates all four stations. |
| ENG-03 | 01-01 | Fixed 36-week game with classic step demand (4 wk 1-4, 8 wk 5-36) | SATISFIED | `TOTAL_WEEKS=36`, `CLASSIC_STEP_BREAK_WEEK=4`, `demand_for_week()` returns 4 or 8 per spec; `tests/test_bullwhip_emerges.py::test_bullwhip_demand_step_recorded` asserts the exact step shape. |
| ENG-04 | 01-01 | Canonical lead times — 2-week shipping, 1-week order delay, 1-week Factory inbound | SATISFIED | `SHIPPING_PIPELINE_LEN=2`, `ORDER_PIPELINE_LEN_RWD=1`, `ORDER_PIPELINE_LEN_FACTORY=1` (BLOCKER 1 fix); `tests/test_tick_invariants.py::test_factory_incoming_orders_canonical_init` verifies. |
| ENG-05 | 01-01 | Asymmetric costs — $0.50 holding / $1.00 backorder | SATISFIED | `config/costs.py` constants exact; `tests/test_costs.py::test_cost_asymmetry` asserts backorder = 2× holding. |
| ENG-06 | 01-03 | Equilibrium start — inventory=12, backlog=0, pipeline pre-loaded with 4 | SATISFIED | `new_game()` in `state.py:97-142`; `tests/test_tick_invariants.py::test_initial_state_is_canonical_equilibrium` AND `tests/test_equilibrium.py::test_equilibrium_constant_demand_constant_orders` both verify. |
| ENG-07 | 01-01 | Canonical tick order — receive → fill → record → place → advance | SATISFIED | `advance_week` in `tick.py:253-270`; `tests/test_tick_invariants.py::test_advance_week_composes_five_steps` asserts manual==composed; `test_record_runs_before_order_decision_agents_see_post_fill_state` proves order. |
| ENG-08 | 01-01 | Backlog accumulates when demand exceeds inventory + cost charged weekly | SATISFIED | `fill_orders` step 2 computes `post_fill_bl[i] = total_need - shipped[i]`; `record_state` step 3 charges weekly_cost; `tests/test_costs.py::test_backlog_accumulates_across_three_week_stockout`. |
| ENG-09 | 01-01 | Deterministic results for given seed | SATISFIED | `tests/test_determinism.py` (3 tests, byte-identical history tuples). |
| ENG-10 | 01-01 | StationView with only locally-knowable info; Retailer-only customer_demand | SATISFIED | `StationView` + `RetailerView(StationView)` split in `state.py:75-94`; `tests/test_station_view_visibility.py` parametrized over W/D/F with `pytest.raises(AttributeError)`. |
| AI-01 | 01-02 | Sterman empirical fit (α=0.26, β=0.34, θ=0.36, S′=17) + cited source | SATISFIED | `sterman.py:24-32` exact defaults; module docstring cites Sterman 1989, Management Science 35(3):321-339, Table 2; `tests/test_sterman_heuristic.py::test_default_parameters_match_sterman_1989_empirical_fit`. |
| AI-02 | 01-01 / 01-02 | Agent Protocol with single decide_order method | SATISFIED | `base.py:19-25` `@runtime_checkable Agent(Protocol)`; `tests/test_sterman_heuristic.py::test_protocol_conformance` asserts isinstance. |
| AI-03 | 01-03 | All-Sterman with step demand → Factory/Retailer peak ratio in [2.0, 4.0] | SATISFIED | `tests/test_bullwhip_emerges.py::test_bullwhip_factory_retailer_peak_ratio_in_canonical_range` passes; live ratio = 2.0000. |
| AI-04 | 01-03 | All-ConstantOrderAgent(4) + constant demand=4 → inventory=12 for all 36 weeks | SATISFIED | `tests/test_equilibrium.py` (6 tests pass with strict per-week assertions). |

**No orphaned requirements** — every Phase 1 ID is claimed by at least one plan (`01-01` claims ENG-02..10 + AI-02; `01-02` claims AI-01, AI-02, ENG-01; `01-03` claims AI-03, AI-04). REQUIREMENTS.md traceability table confirms 14/14 mapping to Phase 1.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |

None. `grep -rn -E "TODO\|FIXME\|XXX\|HACK\|PLACEHOLDER\|placeholder\|coming soon" beergame/ tests/` returned no matches. All artifacts are substantive (1625 lines across engine/ai/config/tests, no empty stubs).

The `metrics.py` module docstring says "intentionally a stub here -- Phase 3 will flesh it out with the debrief-chart helpers" — this is a known scope decision, not a defect: it still provides `peak_orders` and `bullwhip_ratio` which are the only Phase 1 dependencies (used by gate tests indirectly). Phase 3 will expand it.

### Human Verification Required

None. Phase 1 is a pure-engine layer with no UI; all observable truths are programmatically verifiable via pytest and have been verified to pass.

### Gaps Summary

No gaps. Phase 1 goal fully achieved:

- **Pure Python:** zero `streamlit` imports across `beergame/engine/`, `beergame/ai/`, `beergame/config/` (live grep + AST-walk pytest guard).
- **Canonical equilibrium:** GATE 1 passes — under `ConstantOrderAgent(4)` everywhere + constant demand=4, every station's inventory_history is exactly `(12,)*36`, backlog_history is exactly `(0,)*36`, orders_placed_history is exactly `(4,)*36`, cumulative cost grows strictly monotonic at 6.0/week.
- **Canonical bullwhip:** GATE 2 passes — under all-Sterman with empirical 1989 parameters + classic step demand, factory/retailer peak ratio = 2.0000 (within [2.0, 4.0]); monotonic upstream amplification confirmed.
- **Determinism:** Same seed → byte-identical traces across all six history tuples and customer_demand_history.
- **View visibility:** Non-Retailer `StationView` raises `AttributeError` on `customer_demand` (parametric pytest over W/D/F).
- **Tick order:** Five-step canonical sequence enforced; `advance_week == manual five-step compose`; agents see post-fill state.
- **44/44 pytest tests pass** in 0.13 seconds.

Phase 2 (Streamlit UI shell) is unblocked.

---

_Verified: 2026-05-18T16:30:00Z_
_Verifier: Claude (gsd-verifier)_
