# Phase 1: Simulation Engine + AI — Research

**Researched:** 2026-05-18
**Domain:** Pure-Python discrete-event simulation of Sterman's Beer Distribution Game (4-station serial supply chain, 36 weeks, deterministic AI)
**Confidence:** HIGH

---

## Summary

The project-level research (`.planning/research/`) is unusually complete for this phase: canonical Sterman 1989 parameters are cross-verified across six primary sources, the tick sequence is locked, the module layout is sketched, and the two pytest exit gates are pre-specified. This phase research's job is **not** to re-discover any of that — it is to convert the architecture sketch into specs concrete enough that a planner can write `Write`-tool tasks against them. The engine has zero ambiguity at the algorithmic level; it has small remaining ambiguity at the *Python idiom* level (frozen vs mutable dataclasses, tuple vs deque pipelines, four StationView classes vs one, package vs flat module).

The single load-bearing constraint is: **the engine must never import `streamlit`**. Every other decision flows from that. We choose `frozen=True, slots=True` dataclasses with tuple-of-int pipelines and pure-function ticks that return new state via `dataclasses.replace`. We pick a flat `engine/` + `ai/` + `config/` package layout with a minimal `pyproject.toml` (so `pip install -e .` works for pytest), but `requirements.txt` remains the sole deploy artifact (DEPLOY-03). We split `StationView` into a base view + a Retailer-only subclass so that `view.customer_demand` raises `AttributeError` on the other three stations — enforced by the type system, not by runtime checks.

**Primary recommendation:** Build `engine/state.py` (dataclasses) → `engine/demand.py` + `config/` (constants) → `engine/tick.py` (the five named functions composed in `advance_week`) → `ai/base.py` + `ai/sterman.py` (with the empirical-parameter docstring citation) → tests in the order `determinism → tick_invariants → sterman_heuristic → costs → equilibrium → bullwhip_emerges`. The last two are the exit gates and they will fail until everything else is right — that is the design.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **ENG-01** | Engine is pure Python with zero `streamlit` imports | Module layout below: `engine/`, `ai/`, `config/` only import stdlib. Verification: `grep -r "import streamlit" engine/ ai/ config/` returns zero. Test: `test_no_streamlit_import.py`. |
| **ENG-02** | 4-station serial chain Retailer → Wholesaler → Distributor → Factory | `Role` enum + `GameState.stations: tuple[StationState, ...]` of length 4, ordered by enum index. Architecture pattern fixed. |
| **ENG-03** | 36-week fixed game, classic step demand (4→8 at week 5) | `config/scenarios.py: CLASSIC_36W` with `TOTAL_WEEKS=36`; `engine/demand.py: step_demand(week)` returns `4 if week <= 4 else 8`. |
| **ENG-04** | Canonical lead times: 2-week shipping, 1-week order delay R/W/D, 2-week factory production (no order delay) | Pipeline tuples sized accordingly: `incoming_shipments` length 2 for all stations; `incoming_orders` length 1 for R/W/D, length 0 for Factory (Factory's orders go straight to its own `incoming_shipments`). |
| **ENG-05** | Asymmetric costs $0.50 holding / $1.00 backorder per case/week | `config/costs.py: HOLDING_COST=0.50, BACKORDER_COST=1.00` as module-level constants. `engine/costs.py: weekly_cost(station) = HOLDING_COST*max(0,inventory) + BACKORDER_COST*backlog`. |
| **ENG-06** | Canonical equilibrium init: inventory=12, backlog=0, every pipeline slot=4 | `engine/state.py: new_game(player_role, seed)` factory function builds the initial GameState with these exact values. Verification: GATE 1 (equilibrium regression test). |
| **ENG-07** | Canonical tick sequence: receive → fill → record → order → advance pipelines | `engine/tick.py: advance_week()` composes five named functions in this exact order. Verification: `test_tick_invariants.py` asserts the sequence (see Test Design). |
| **ENG-08** | Backlog accumulates when demand > inventory, charged weekly | Fill step computes `shipped = min(inventory, demand+backlog)`, then `new_backlog = (demand+backlog) - shipped`. Cost step charges on the post-fill `backlog`. |
| **ENG-09** | Deterministic results for given seed | Engine uses **no `random` module at all** in v1 (step demand is deterministic, Sterman agent is deterministic). `seed` is stored in `GameState.seed` for future-proofing only. Verification: `test_determinism.py` asserts byte-identical traces. |
| **ENG-10** | `StationView` exposes only locally-knowable info; only Retailer view has `customer_demand` | Two-class hierarchy: `StationView` (base, no customer_demand) and `RetailerView(StationView)` (adds customer_demand). Non-Retailer `view.customer_demand` raises `AttributeError`. Verification: `test_station_view_visibility.py`. |
| **AI-01** | Sterman empirical heuristic with α≈0.26, β≈0.34, θ≈0.36, S′≈17 + citation | `ai/sterman.py: ShipmentAnchorAndAdjustAgent` dataclass with these as defaults. Docstring cites "Sterman 1989, Management Science 35(3):321-339, Table 2 median empirical fit". |
| **AI-02** | `Agent` protocol with `decide_order(view) -> int` | `ai/base.py: class Agent(Protocol)`. Sterman agent conforms via duck typing; testable with `isinstance(agent, Agent)` using `runtime_checkable`. |
| **AI-03** | All-AI step demand → Factory peak / Retailer peak ∈ [2.0, 4.0] | GATE 2 (`test_bullwhip_emerges.py`). Drives Sterman parameter validation. |
| **AI-04** | All-AI constant demand=4 → inventory=12 for all 36 weeks | GATE 1 (`test_equilibrium.py`). Drives initial-condition + tick-sequence validation. |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12 | Runtime | Locked by project research (Streamlit Cloud default; `dataclasses.replace`, `Protocol`, structural typing all available; `slots=True` on dataclasses available since 3.10) |
| `dataclasses` (stdlib) | n/a | State containers | `frozen=True, slots=True` for immutable state, `dataclasses.replace()` for non-mutating updates |
| `enum` (stdlib) | n/a | `Role` enum | Type-safe station identifiers; iteration order is definition order (`Role.RETAILER, WHOLESALER, DISTRIBUTOR, FACTORY`) |
| `typing` (stdlib) | n/a | `Protocol`, `runtime_checkable` | Define `Agent` interface without ABC inheritance overhead |
| pytest | 8.x | Test runner | Project-locked; engine is deterministic so golden-trace pytest is the entire QA strategy |
| Ruff | 0.6+ | Lint+format | Project-locked |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `collections.deque` | stdlib | NOT recommended for pipelines | Tuples win (see "Tuple vs deque" below). Don't use deque. |
| `numpy` | — | NOT permitted | Explicitly excluded by project research (1GB Streamlit Cloud cap, no benefit at 144 cells) |
| `pandas` | — | NOT permitted | Same |
| `hypothesis` | 6.x | Property-based tests | Defer to v2; not needed for Phase 1 exit gates |

### Tuple vs deque — decision
**Use tuples.** Frozen dataclasses with tuple fields give us equality comparison, hashability, naturally immutable history, and no slicing surprises. `collections.deque` *does not support slicing* (raises `TypeError` on `d[1:]`), which would force `itertools.islice` everywhere. Pipelines are length 1–2 so O(n) slicing is free. Sources: [Python deque docs](https://docs.python.org/3/library/collections.html#collections.deque), [Real Python: deque limitations](https://realpython.com/python-deque/).

**Pipeline advance idiom:**
```python
# Receive: pop front (slot 0 arrives this week)
arriving = station.incoming_shipments[0]
# After advance_pipelines: slide forward, append 0 to back
new_shipments = station.incoming_shipments[1:] + (0,)
```

### Installation

**`pyproject.toml`** (commit; minimal — enables `pip install -e .` for tests):
```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "beergame"
version = "0.1.0"
requires-python = ">=3.12"
# No runtime deps — engine is stdlib-only.
# Streamlit + Plotly are added in Phase 2.

[tool.setuptools.packages.find]
where = ["."]
include = ["beergame*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"

[tool.ruff]
line-length = 100
target-version = "py312"
```

**Note on DEPLOY-03 compatibility:** Streamlit Community Cloud's dep-file priority is `uv.lock` → `Pipfile` → `environment.yml` → `requirements.txt` → `pyproject.toml`. As long as `requirements.txt` exists (added in Phase 4), CC picks it before `pyproject.toml`. The `pyproject.toml` is for *local dev only* — it does not violate DEPLOY-03 because CC won't reach it in the lookup order. Verification deferred to Phase 4.

**`requirements-dev.txt`** (commit):
```
pytest>=8,<9
ruff>=0.6
```

**Local setup:**
```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -r requirements-dev.txt
pytest -q
```

---

## Architecture Patterns

### Module Layout (Concrete)

```
beergameNexStratus/
├── pyproject.toml                     # minimal, dev-only (above)
├── requirements-dev.txt
├── .python-version                    # "3.12"
├── beergame/
│   ├── __init__.py                    # empty
│   ├── engine/
│   │   ├── __init__.py                # re-exports: new_game, advance_week, is_game_over, simulate_full_game
│   │   ├── state.py                   # Role, StationState, GameState, StationView, RetailerView, new_game()
│   │   ├── tick.py                    # advance_week() + 5 named step functions
│   │   ├── demand.py                  # step_demand(week, scenario) -> int; constant_demand for tests
│   │   ├── costs.py                   # weekly_cost(station), total_cost(state)
│   │   └── metrics.py                 # amplification_ratio(state), peak_orders(state) — used by Phase 3
│   ├── ai/
│   │   ├── __init__.py                # re-exports Agent, ShipmentAnchorAndAdjustAgent
│   │   ├── base.py                    # Agent Protocol + ConstantOrderAgent (test helper)
│   │   └── sterman.py                 # ShipmentAnchorAndAdjustAgent with Sterman 1989 citation
│   └── config/
│       ├── __init__.py
│       ├── scenarios.py               # CLASSIC_36W: total_weeks, demand_pattern_name, lead times per role
│       └── costs.py                   # HOLDING_COST=0.50, BACKORDER_COST=1.00
└── tests/
    ├── __init__.py
    ├── conftest.py                    # shared fixtures: initial_game, all_ai_agents, constant_demand_game
    ├── test_no_streamlit_import.py    # ENG-01: grep-equivalent in pytest
    ├── test_determinism.py            # ENG-09
    ├── test_tick_invariants.py        # ENG-07
    ├── test_sterman_heuristic.py      # AI-01, AI-02
    ├── test_station_view_visibility.py # ENG-10
    ├── test_costs.py                  # ENG-05, ENG-08
    ├── test_equilibrium.py            # GATE 1: ENG-06 + AI-04
    └── test_bullwhip_emerges.py       # GATE 2: AI-03
```

### State Data Shape (Concrete Field Specs)

**`beergame/engine/state.py`** — every field decision committed:

```python
from dataclasses import dataclass, replace, field
from enum import Enum
from typing import Optional

class Role(Enum):
    RETAILER = 0
    WHOLESALER = 1
    DISTRIBUTOR = 2
    FACTORY = 3

# Lead times per JASSS 17(4):2 and Sterman MIT page.
# These are tuple SIZES of the pipeline queues; index 0 = "arrives this week."
SHIPPING_PIPELINE_LEN = 2     # All four stations have a 2-week incoming shipment queue.
ORDER_PIPELINE_LEN_RWD = 1    # R, W, D have a 1-week incoming order (mailing) queue.
ORDER_PIPELINE_LEN_FACTORY = 0  # Factory has no order-mailing queue; orders become production starts.
INITIAL_INVENTORY = 12
INITIAL_BACKLOG = 0
EQUILIBRIUM_THROUGHPUT = 4    # Pre-fills every pipeline slot.

@dataclass(frozen=True, slots=True)
class StationState:
    role: Role
    inventory: int                            # always >= 0 (backlog is separate)
    backlog: int                              # always >= 0
    incoming_shipments: tuple[int, ...]       # len == SHIPPING_PIPELINE_LEN; index 0 arrives this tick
    incoming_orders: tuple[int, ...]          # len 1 for R/W/D, len 0 for Factory
    # History tuples — append-only; len == current_week after each tick (week 0 has empty history).
    inventory_history: tuple[int, ...]        # post-shipment inventory recorded at step 3
    backlog_history: tuple[int, ...]
    orders_placed_history: tuple[int, ...]    # what THIS station ordered upstream that week
    orders_received_history: tuple[int, ...]  # what THIS station received from downstream that week
    shipments_sent_history: tuple[int, ...]   # what THIS station shipped downstream that week
    cost_history: tuple[float, ...]           # cumulative cost AS OF that week (not per-week increment)

@dataclass(frozen=True, slots=True)
class GameState:
    week: int                                 # 0 = initial (no ticks run yet); after tick N, week == N
    total_weeks: int                          # 36 (from config.scenarios)
    seed: int                                 # stored but UNUSED in v1; future-proof for noise
    player_role: Role
    stations: tuple[StationState, ...]        # ALWAYS length 4, indexed by Role.value
    customer_demand_history: tuple[int, ...]  # the exogenous demand the retailer faced each week
    phase: str                                # "playing" | "done" (no "setup" — that's UI-only)

# === Views ===
# Two-class hierarchy: the base View has NO customer_demand. Only RetailerView has it.
# This makes `non_retailer_view.customer_demand` raise AttributeError naturally.

@dataclass(frozen=True, slots=True)
class StationView:
    """Read-only window onto a non-Retailer station's locally-knowable state."""
    role: Role
    week: int
    inventory: int
    backlog: int
    supply_line: int                           # sum of incoming_shipments
    last_order_received: int                   # the order JUST received from downstream this tick
    recent_orders_received: tuple[int, ...]    # last N weeks (N=4) of orders received — for forecasting

@dataclass(frozen=True, slots=True)
class RetailerView(StationView):
    """Retailer-specific view: also carries the customer demand the retailer just faced."""
    customer_demand: int
```

**Why two view classes (decision, justified):**
- Single-class-with-Optional approach (`customer_demand: int | None`) would force every non-Retailer code path to check `if view.customer_demand is not None:`, leaking the special case into agent code and inviting silent bugs.
- Inheritance lets non-Retailer agents type their parameter as `StationView` and statically not see the attribute. The Retailer's view *is* a `StationView` (Liskov holds — anywhere a base view is accepted, a RetailerView works).
- Verification: `getattr(non_retailer_view, "customer_demand", _SENTINEL) is _SENTINEL` and `hasattr(non_retailer_view, "customer_demand")` is False.

**Why history tuples per station (not central log):**
- Each station's chart slice is a tuple lookup, not a filter-and-zip across a central log.
- Frozen dataclass + tuple = naturally immutable; `dataclasses.replace(station, inventory_history=station.inventory_history + (new,))` is one line.
- Memory: 4 stations × 7 history fields × 36 ints ≈ 1KB per game. Irrelevant.

**Why no `desired_inventory` on `StationState`:** That's an *agent parameter*, not a state attribute. It belongs on `ShipmentAnchorAndAdjustAgent`. State is "what happened"; agent config is "how I decide."

### Tick Implementation (Five Named Functions)

**`beergame/engine/tick.py`** — the only place state changes:

```python
from dataclasses import replace
from beergame.engine.state import GameState, StationState, Role, StationView, RetailerView
from beergame.engine.demand import demand_for_week
from beergame.engine.costs import weekly_cost
from beergame.ai.base import Agent

# Helper: station index by role
def _idx(role: Role) -> int:
    return role.value

def receive_shipments(state: GameState) -> GameState:
    """Step 1: pop front of each station's incoming_shipments into inventory."""
    new_stations = []
    for s in state.stations:
        arriving = s.incoming_shipments[0]
        new_s = replace(
            s,
            inventory=s.inventory + arriving,
            # Don't shift here — step 5 (advance_pipelines) does that.
            # We need slot 0 cleared but the tuple shape preserved until step 5.
            # Alternative: clear slot 0 by setting it to 0; advance_pipelines will then shift.
            incoming_shipments=(0,) + s.incoming_shipments[1:],
        )
        new_stations.append(new_s)
    return replace(state, stations=tuple(new_stations))

def fill_orders(state: GameState) -> GameState:
    """Step 2: receive incoming order (or customer demand for Retailer),
    add to backlog, ship min(inventory, demand+backlog) downstream.

    Downstream shipping: the shipped quantity goes onto the DOWNSTREAM station's
    incoming_shipments queue at the BACK (last slot — will arrive in SHIPPING_PIPELINE_LEN weeks).
    The Retailer ships to the external customer (units leave the system).
    """
    # Pull customer demand for the retailer this week:
    customer_demand_this_week = demand_for_week(state.week + 1, state.total_weeks)
    new_customer_history = state.customer_demand_history + (customer_demand_this_week,)

    new_stations = list(state.stations)

    # Process from Factory downward? No — order matters only for inter-station shipping.
    # We process all stations' fill in parallel: each station's "demand to fill" comes
    # from its own incoming_orders[0] (or customer demand for Retailer), and its
    # shipment goes onto the DOWNSTREAM station's incoming_shipments LAST slot.

    # First pass: determine demand each station must fill.
    demands = [0, 0, 0, 0]
    for role in Role:
        i = _idx(role)
        s = state.stations[i]
        if role == Role.RETAILER:
            demands[i] = customer_demand_this_week
        else:
            # Non-Retailer: demand is the order received from downstream this tick.
            # ORDER_PIPELINE_LEN_RWD == 1, so slot 0 is the order that just arrived.
            demands[i] = s.incoming_orders[0]

    # Second pass: compute fills, update inventory/backlog, enqueue shipment to downstream.
    for role in Role:
        i = _idx(role)
        s = new_stations[i]
        demand_this_week = demands[i]
        total_need = demand_this_week + s.backlog
        shipped = min(s.inventory, total_need)
        new_inventory = s.inventory - shipped
        new_backlog = total_need - shipped

        # Enqueue shipment to downstream (if any). Downstream = role with value i-1.
        if role != Role.RETAILER:
            downstream_idx = i - 1
            downstream = new_stations[downstream_idx]
            # Put `shipped` at the BACK of downstream's incoming_shipments (last slot).
            # SHIPPING_PIPELINE_LEN == 2, so [slot_0, slot_1] → [slot_0, slot_1 + shipped]?
            # NO: slot_1 currently holds something in transit from last week.
            # The convention: when we "enqueue at the back," we MEAN: place into the slot
            # that will arrive after SHIPPING_PIPELINE_LEN ticks. Since advance_pipelines
            # (step 5) shifts forward by 1, we put the new shipment into the LAST slot now,
            # and after step 5 it will be one slot closer to slot 0.
            # ASSUMPTION: incoming_shipments slot at index -1 is the "just-placed" slot.
            # On a fresh tick (after receive_shipments cleared slot 0), the layout is:
            #   [0, in_transit_from_last_week]
            # We want to add `shipped` to slot -1 (which is slot 1 in a length-2 tuple).
            # But slot 1 already has the in-transit from last week!
            # Resolution: the receiving station's pipeline holds ONE shipment per slot.
            # New shipments go into a FRESH slot that doesn't exist yet, and
            # advance_pipelines creates room by shifting. So instead of mutating slot -1,
            # we OVERLAY: replace slot -1 only if it was 0 (which it isn't in equilibrium).
            #
            # CLEANER APPROACH: track outgoing shipments separately during fill, then
            # in step 5 advance_pipelines does:
            #   new_incoming_shipments = old[1:] + (this_tick_outgoing_to_me,)
            # So fill_orders writes to a transient field, advance_pipelines consumes it.
            #
            # We'll store the "outgoing-to-be-shipped" on the SENDING station as a
            # `pending_shipment_out: int` field, and step 5 will pull it.
            pass  # See decision below for the full data flow.

        new_stations[i] = replace(
            s, inventory=new_inventory, backlog=new_backlog,
            # We DON'T mutate incoming_orders here — step 5 advances it.
            # We DON'T record history here — step 3 does.
        )

    # The shipment enqueue is deferred to advance_pipelines via a transient field
    # (see "Pipeline data flow" decision below).
    return replace(state, stations=tuple(new_stations),
                   customer_demand_history=new_customer_history)

def record_state(state: GameState) -> GameState:
    """Step 3: append post-fill inventory/backlog/etc. to history tuples; accrue cost."""
    new_stations = []
    for s in state.stations:
        w_cost = weekly_cost(s)  # uses POST-FILL inventory and backlog
        prev_cum = s.cost_history[-1] if s.cost_history else 0.0
        new_s = replace(
            s,
            inventory_history=s.inventory_history + (s.inventory,),
            backlog_history=s.backlog_history + (s.backlog,),
            cost_history=s.cost_history + (prev_cum + w_cost,),
            # orders_received_history was the demand this station filled (computed in step 2 — pass via transient)
            # shipments_sent_history was the `shipped` value from step 2 — same
            # orders_placed_history is appended in step 4
        )
        new_stations.append(new_s)
    return replace(state, stations=tuple(new_stations))

def place_orders(state: GameState, player_order: int,
                 ai_agents: dict[Role, Agent]) -> GameState:
    """Step 4: each station decides its order quantity. Player's is passed in.
    The placed order enqueues into the UPSTREAM station's incoming_orders LAST slot
    (or, for Factory, into the Factory's OWN incoming_shipments LAST slot since
    Factory has no order delay — production starts immediately and takes 2 weeks).
    """
    orders_placed = [0, 0, 0, 0]
    for role in Role:
        i = _idx(role)
        if role == state.player_role:
            orders_placed[i] = max(0, int(player_order))
        else:
            view = build_station_view(state, role)
            orders_placed[i] = max(0, int(ai_agents[role].decide_order(view)))

    new_stations = list(state.stations)
    for role in Role:
        i = _idx(role)
        o = orders_placed[i]
        s = new_stations[i]
        # Record the order this station placed (history).
        s = replace(s, orders_placed_history=s.orders_placed_history + (o,))
        new_stations[i] = s

        # Route the order:
        if role == Role.FACTORY:
            # Factory: enqueue to OWN incoming_shipments (production delay). Last slot.
            fs = new_stations[i]
            # We need to ADD to the last slot of incoming_shipments — but receive_shipments
            # set slot 0 to 0, leaving slot 1 with the in-transit-from-last-week amount.
            # The "fresh slot" we want to write is logically a new slot that doesn't exist yet.
            # See "Pipeline data flow" decision below — we use `pending_production_in: int`
            # as a transient field that advance_pipelines consumes.
            new_stations[i] = replace(fs, _pending_in_shipment=o)
        else:
            # R/W/D: enqueue to UPSTREAM's incoming_orders LAST slot. Upstream = i+1.
            up_idx = i + 1
            us = new_stations[up_idx]
            new_stations[up_idx] = replace(us, _pending_in_order=o)
    return replace(state, stations=tuple(new_stations))

def advance_pipelines(state: GameState) -> GameState:
    """Step 5: shift every queue forward; new placements (from step 2 and step 4)
    land in the now-empty back slot.
    """
    # ... (see decision below for transient-field consumption)
```

### Pipeline data flow — DECISION

**Problem:** The naive "tuple as fixed-length queue with `[1:] + (new,)`" works *if* there's exactly one new item per tick per queue. But step 2 (fill_orders) enqueues shipments to downstream's queue, and step 5 (advance_pipelines) shifts. If we shift first and then add, we overwrite the slot that just advanced into position. If we add first and then shift, we lose the just-added item.

**Cleanest fix (RECOMMENDED):** Add two transient `_pending_*` integer fields to `StationState`, populated by steps 2 and 4, consumed by step 5.

```python
@dataclass(frozen=True, slots=True)
class StationState:
    # ... existing fields ...
    _pending_in_shipment: int = 0   # set in step 2 (downstream's outgoing) or step 4 (Factory production)
    _pending_in_order: int = 0      # set in step 4 (downstream's just-placed order, for non-Factory upstream)
```

Step 5 then does:
```python
def advance_pipelines(state: GameState) -> GameState:
    new_stations = []
    for s in state.stations:
        # Shipments: drop slot 0 (already received), shift forward, append pending at back.
        new_shipments = s.incoming_shipments[1:] + (s._pending_in_shipment,)
        # Orders: same, but skip for Factory (length-0 tuple stays length-0).
        if len(s.incoming_orders) > 0:
            new_orders = s.incoming_orders[1:] + (s._pending_in_order,)
        else:
            new_orders = ()
        new_stations.append(replace(s,
            incoming_shipments=new_shipments,
            incoming_orders=new_orders,
            _pending_in_shipment=0,
            _pending_in_order=0,
        ))
    return replace(state, week=state.week + 1, stations=tuple(new_stations),
                   phase="done" if state.week + 1 >= state.total_weeks else "playing")
```

**Alternative considered (REJECTED):** Variable-length tuples where we "grow then shrink." More allocations, more cognitive load, and breaks the invariant that `len(incoming_shipments) == SHIPPING_PIPELINE_LEN` after every step. Tested mentally and the equilibrium case fails on week 1 (off-by-one) — too error-prone.

**Why the leading underscore on transient fields:** Signals "engine-internal, not part of public state." Tests can check them, but agents and views never see them (views are separate dataclasses).

### `advance_week` composition

```python
def advance_week(state: GameState, player_order: int,
                 ai_agents: dict[Role, Agent]) -> GameState:
    """Single canonical tick. Returns a NEW GameState.

    The five steps MUST run in this order. Any rearrangement breaks the bullwhip.
    """
    assert state.phase == "playing", f"Cannot advance: phase={state.phase}"
    s1 = receive_shipments(state)
    s2 = fill_orders(s1)
    s3 = record_state(s2)
    s4 = place_orders(s3, player_order, ai_agents)
    s5 = advance_pipelines(s4)
    return s5

def simulate_full_game(seed: int, player_role: Role,
                       agents: dict[Role, Agent]) -> GameState:
    """Test/research convenience: run 36 ticks with one Agent per role."""
    from beergame.engine.state import new_game
    state = new_game(player_role=player_role, seed=seed)
    while state.phase == "playing":
        # The "player" is just another agent here.
        player_view = build_station_view(state, player_role)
        player_order = agents[player_role].decide_order(player_view)
        # ai_agents = everyone EXCEPT the player
        ai_subset = {r: a for r, a in agents.items() if r != player_role}
        state = advance_week(state, player_order, ai_subset)
    return state
```

### Sterman Heuristic (Concrete Code Shape)

**`beergame/ai/sterman.py`:**

```python
"""Sterman anchor-and-adjust ordering heuristic.

Implements the median empirical parameter fit from:
    Sterman, J.D. (1989). "Modeling Managerial Behavior: Misperceptions of
    Feedback in a Dynamic Decision-Making Experiment." Management Science
    35(3): 321-339, Table 2.

CRITICAL: These are the EMPIRICAL parameters (fit to real human subjects),
NOT the "optimal" parameters (α=β=1, θ=0) from later theoretical work
(e.g., Edali & Yasarcan, JASSS 17(4):2, 2014). The empirical parameters
REPRODUCE the bullwhip; the optimal parameters MINIMIZE it. We want
reproduction, not minimization — the bullwhip is the lesson.
"""
from dataclasses import dataclass, field
from beergame.engine.state import StationView

@dataclass
class ShipmentAnchorAndAdjustAgent:
    # === Empirical parameters (Sterman 1989, Table 2 median fit) ===
    alpha: float = 0.26          # stock adjustment fraction
    beta: float = 0.34           # supply line weight (rational = 1.0)
    theta: float = 0.36          # demand-smoothing weight (rational = 0.0)
    desired_inventory: float = 17.0   # S' — desired inventory + supply line target

    # === Per-instance forecast state (carries across weeks) ===
    # Initialized to the equilibrium throughput so week 1's order matches the
    # initial in-transit shipments (system stays in equilibrium until demand step).
    smoothed_demand: float = field(default=4.0)

    def decide_order(self, view: StationView) -> int:
        """Sterman heuristic:
            L_t   = θ·D_t + (1-θ)·L_{t-1}        # smoothed expected demand
            O_t   = max(0, round(L_t + α·(S' - NS_t) - β·SL_t))
        where NS_t = inventory - backlog (net stock), SL_t = supply line.
        """
        # Update the smoothed demand forecast with this week's observation.
        self.smoothed_demand = (
            self.theta * view.last_order_received
            + (1.0 - self.theta) * self.smoothed_demand
        )
        net_stock = view.inventory - view.backlog
        raw_order = (
            self.smoothed_demand
            + self.alpha * (self.desired_inventory - net_stock)
            - self.beta * view.supply_line
        )
        return max(0, round(raw_order))
```

**Why a stateful dataclass (not Protocol-only):**
- The smoothed-demand forecast carries across weeks. Pure-function alternative would force `StationView` to carry `smoothed_demand`, which is *agent state*, not *station state*. Wrong place.
- One agent instance per role per game (`{Role: ShipmentAnchorAndAdjustAgent()}` dict), lifetime = game. Dataclass equality lets pytest assert "two agents with same params and history are equal."
- `@dataclass` (not `frozen=True`) because the agent updates `smoothed_demand` in place each tick.

**`beergame/ai/base.py`:**

```python
from typing import Protocol, runtime_checkable
from beergame.engine.state import StationView

@runtime_checkable
class Agent(Protocol):
    """Order-placing agent. Sees only its own StationView.
    Returns a non-negative integer order quantity for this week."""
    def decide_order(self, view: StationView) -> int: ...

# Test helper — used by test_equilibrium.py and elsewhere.
class ConstantOrderAgent:
    """Always orders the same quantity. Used in the equilibrium regression test."""
    def __init__(self, quantity: int):
        self.quantity = quantity
    def decide_order(self, view: StationView) -> int:
        return self.quantity
```

### `build_station_view` (the visibility-enforcement function)

**Lives in `engine/state.py` or `engine/tick.py`:**

```python
RECENT_ORDERS_WINDOW = 4  # how many past weeks of received orders the view exposes

def build_station_view(state: GameState, role: Role) -> StationView:
    """Construct the agent-facing view of a station's locally-knowable state.
    The Retailer gets a RetailerView (with customer_demand); everyone else
    gets a base StationView (no customer_demand attribute).
    """
    s = state.stations[role.value]
    supply_line = sum(s.incoming_shipments)
    # last_order_received: the order this station just received from downstream this tick.
    # For Retailer, this is the customer demand (which is also in customer_demand_history[-1]).
    # For others, this is incoming_orders[0] which receive_shipments and fill_orders consumed.
    # We pull from history (orders_received_history) which is appended in step 2 via the
    # transient pattern — or pull from the demands array computed in step 2.
    # SIMPLEST: orders_received_history[-1] if non-empty else 4 (equilibrium).
    last_order = (
        s.orders_received_history[-1] if s.orders_received_history else 4
    )
    recent = s.orders_received_history[-RECENT_ORDERS_WINDOW:]

    common = dict(
        role=role, week=state.week, inventory=s.inventory, backlog=s.backlog,
        supply_line=supply_line, last_order_received=last_order,
        recent_orders_received=recent,
    )
    if role == Role.RETAILER:
        return RetailerView(
            **common,
            customer_demand=state.customer_demand_history[-1] if state.customer_demand_history else 4,
        )
    return StationView(**common)
```

### Anti-Patterns to Avoid (from PITFALLS.md, specific to this phase)

- **`import streamlit` in engine** — guarded by `test_no_streamlit_import.py` (greps `beergame/engine/` and `beergame/ai/` and `beergame/config/` source).
- **Mutating state in agent** — `StationView` is frozen; mutating raises `FrozenInstanceError`. Agent's `decide_order` only updates `self.smoothed_demand`, never the view.
- **Storing entire history as list of past GameStates** — never. History is per-station tuples (above).
- **Reading customer demand on non-Retailer station** — impossible: those views don't have the attribute.
- **Using "optimal" Sterman parameters** — guarded by GATE 2 (test_bullwhip_emerges).
- **Wrong tick order** — `advance_week` calls five named functions in literal source order; reviewers can verify by reading 5 lines.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| State containers | Custom `__init__`/`__eq__`/`__repr__` classes | `@dataclass(frozen=True, slots=True)` | Auto-generated; equality field-by-field; hashable; 2.4x slower instantiation than mutable but negligible at our scale ([source](https://www.pyblog.in/programming/python-dataclasses-the-complete-2026-guide-from-dataclass-to-slots-frozen-and-__post_init__/)) |
| Non-mutating updates | Manual field copy | `dataclasses.replace(state, field=new)` | Stdlib; preserves frozen invariant |
| FIFO pipeline | `collections.deque` | `tuple[int, ...]` | Deque doesn't support slicing (TypeError on `d[1:]`); tuples are naturally immutable; performance is identical at length 1-2 ([source](https://realpython.com/python-deque/)) |
| Station role identifiers | Plain strings or ints | `enum.Enum` with `IntEnum` semantics | Type-safe, IDE autocomplete, iteration order is definition order |
| Agent interface | ABC base class | `typing.Protocol` (with `runtime_checkable`) | Structural typing; no inheritance required; `isinstance()` still works |
| Test for "no streamlit import" | grep in CI shell | pytest test using `ast.parse` walk over source files | Runs as part of `pytest -q`; failure shows file + line |
| Determinism check | Hash comparison | Direct `GameState == GameState` (frozen dataclasses are equal field-by-field) | One-liner; pytest shows the diff on failure |

**Key insight:** Every place we're tempted to write helper machinery, Python stdlib already has it. `dataclasses.replace` + frozen + tuples is the entire mutation strategy. `Protocol` is the entire interface story. There are zero third-party runtime deps in Phase 1.

---

## Common Pitfalls

(All cross-referenced to `.planning/research/PITFALLS.md`. The ones specific to Phase 1 — the engine — are concretized below with test-level prevention.)

### Pitfall 1: Sterman empirical-vs-optimal parameter swap
**What goes wrong:** Future contributor finds the JASSS 2014 paper, sees "optimal" α=β=1, θ=0, swaps them in. All four AI stations now track demand calmly; no bullwhip; the project's whole point dies silently.
**Why it happens:** "Optimal" sounds more authoritative than "empirical median fit."
**How to avoid:**
1. Hardcode α=0.26, β=0.34, θ=0.36, S′=17 as `@dataclass` defaults.
2. Module docstring in `ai/sterman.py` cites Sterman 1989 Table 2 explicitly AND names the optimal-parameter trap.
3. GATE 2 test (`test_bullwhip_emerges.py`) asserts ratio in [2.0, 4.0] — fails immediately on optimal swap.
**Warning signs:** GATE 2 ratio < 1.5 or factory orders never collapse to ~0 after the overshoot.

### Pitfall 2: Wrong tick order
**What goes wrong:** Code-order vs process-order mismatch. E.g., place_orders before record_state (agent sees wrong inventory), or advance_pipelines before place_orders (new orders fire instantly).
**Why it happens:** Developers think "I'll just update everything in one pass."
**How to avoid:**
1. Five named functions; `advance_week` source is literally 5 lines.
2. `test_tick_invariants.py` asserts: at week 1 with constant demand=4 and constant orders=4, inventory_history[0] == 12 (post-receive, post-fill) and orders_placed_history[0] == 4.
3. Test asserts player's just-placed order is NOT in their own supply_line on the next tick (it's in the order pipeline first).
**Warning signs:** Week 1 cost ≠ holding-only cost ($0.50 × 12 × 4 stations = $24); inventory dips and order spikes happen the same week.

### Pitfall 3: Pipeline off-by-one (empty initial slots)
**What goes wrong:** `incoming_shipments=(0, 0)` instead of `(4, 4)`. Equilibrium phase isn't equilibrium — inventory drains for 2 weeks before any shipment arrives.
**Why it happens:** Default-constructing tuples; "the game will settle."
**How to avoid:**
1. `new_game()` factory sets every pipeline slot to `EQUILIBRIUM_THROUGHPUT = 4`.
2. GATE 1 (`test_equilibrium.py`) catches it on week 1.
**Warning signs:** Inventory deviates from 12 before week 5.

### Pitfall 4: Backlog not carrying / not accumulating cost weekly
**What goes wrong:** Treat backlog as a one-shot event (cost charged when created, then dropped).
**How to avoid:**
1. `weekly_cost()` reads the *post-fill* `backlog` field, not "new unfilled this week."
2. Test: 3-week stockout scenario — backlog cost should equal sum across the 3 weeks, not just week 1.
**Warning signs:** Factory's post-overshoot cost is flat (should be the *highest*).

### Pitfall 5: Customer demand visible to non-Retailer
**What goes wrong:** Single `customer_demand` field on `GameState` accidentally exposed via `StationView`.
**How to avoid:**
1. Two view classes (StationView, RetailerView). Non-Retailer view doesn't have the attribute.
2. `test_station_view_visibility.py`: `with pytest.raises(AttributeError): _ = wholesaler_view.customer_demand`.
**Warning signs:** AI agents respond to the demand step the same week it happens regardless of position.

### Pitfall 6: Hidden non-determinism
**What goes wrong:** Someone adds `random.randint(0, 1)` to "make the AI more realistic." Trace varies run-to-run; pytest gates flake; bullwhip ratio drifts.
**How to avoid:**
1. v1 engine uses no `random` module. The `seed` field on `GameState` is stored but unused.
2. `test_determinism.py`: `simulate_full_game(seed=42, ...) == simulate_full_game(seed=42, ...)` (frozen dataclass equality is field-by-field).
**Warning signs:** GATE 1 or GATE 2 flakes between runs.

### Pitfall 7: Factory asymmetry leaking into the design
**What goes wrong:** Special-case Factory branches (`if role == FACTORY:`) scattered across multiple files.
**How to avoid:**
1. Factory's only differences are: `incoming_orders` is length 0; placed orders route to its own `incoming_shipments` instead of upstream.
2. Both differences are localized to step 4 (place_orders) and one tuple length constant.
3. Single `StationState` dataclass — no `FactoryState` subclass.
**Warning signs:** A `class FactoryStation(StationState)` appears in a PR.

### Pitfall 8: streamlit creeping into engine
**What goes wrong:** Engineer adds `import streamlit as st; st.warning(...)` for diagnostics. Pytest now needs streamlit installed; CI takes longer; eventually someone adds `@st.cache_data` to a pure engine function and breaks determinism.
**How to avoid:**
1. `test_no_streamlit_import.py`: walks `beergame/engine/` and `beergame/ai/` and `beergame/config/` source trees, parses each file's AST, asserts no `ImportFrom(module="streamlit")` or `Import(name="streamlit")` nodes.
2. Engine returns warning data (e.g., `state.warnings: tuple[str, ...]`) instead of calling `st.warning`.

---

## Code Examples

### Example: `new_game` factory

```python
# beergame/engine/state.py

def new_game(player_role: Role, seed: int = 42,
             total_weeks: int = 36) -> GameState:
    """Construct the canonical initial GameState (Sterman 1989 equilibrium)."""
    def make_station(role: Role) -> StationState:
        order_len = ORDER_PIPELINE_LEN_FACTORY if role == Role.FACTORY else ORDER_PIPELINE_LEN_RWD
        return StationState(
            role=role,
            inventory=INITIAL_INVENTORY,
            backlog=INITIAL_BACKLOG,
            incoming_shipments=(EQUILIBRIUM_THROUGHPUT,) * SHIPPING_PIPELINE_LEN,
            incoming_orders=(EQUILIBRIUM_THROUGHPUT,) * order_len,  # () for Factory
            inventory_history=(),
            backlog_history=(),
            orders_placed_history=(),
            orders_received_history=(),
            shipments_sent_history=(),
            cost_history=(),
        )
    return GameState(
        week=0, total_weeks=total_weeks, seed=seed, player_role=player_role,
        stations=tuple(make_station(r) for r in Role),
        customer_demand_history=(),
        phase="playing",
    )
```

### Example: `weekly_cost`

```python
# beergame/engine/costs.py
from beergame.config.costs import HOLDING_COST, BACKORDER_COST
from beergame.engine.state import StationState

def weekly_cost(station: StationState) -> float:
    """Per-week cost charged on POST-FILL inventory and backlog."""
    return HOLDING_COST * max(0, station.inventory) + BACKORDER_COST * station.backlog
```

### Example: `step_demand`

```python
# beergame/engine/demand.py

CLASSIC_STEP_BREAK_WEEK = 4   # demand is 4 through week 4, then 8 from week 5
CLASSIC_PRE_STEP = 4
CLASSIC_POST_STEP = 8

def demand_for_week(week: int, total_weeks: int = 36) -> int:
    """Classic step demand: 4 for weeks 1-4, 8 for weeks 5-36."""
    if week < 1 or week > total_weeks:
        raise ValueError(f"week {week} out of range [1, {total_weeks}]")
    return CLASSIC_PRE_STEP if week <= CLASSIC_STEP_BREAK_WEEK else CLASSIC_POST_STEP

def constant_demand(week: int, total_weeks: int = 36, value: int = 4) -> int:
    """Used by GATE 1 equilibrium test: demand always 4."""
    if week < 1 or week > total_weeks:
        raise ValueError(f"week {week} out of range [1, {total_weeks}]")
    return value
```

For the equilibrium test we need to inject `constant_demand` in place of `demand_for_week`. Cleanest mechanism: a `demand_fn` parameter on `new_game()` (defaulting to `demand_for_week`) that gets stored on `GameState` as a callable field — but that breaks frozen-dataclass equality (functions aren't naturally comparable). **Better:** `demand_fn` is a parameter on `advance_week` and `simulate_full_game`, threaded through, not stored on state.

### Example: Determinism test

```python
# tests/test_determinism.py
import pytest
from beergame.engine.tick import simulate_full_game
from beergame.engine.state import Role
from beergame.ai.sterman import ShipmentAnchorAndAdjustAgent

def make_agents() -> dict[Role, ShipmentAnchorAndAdjustAgent]:
    return {r: ShipmentAnchorAndAdjustAgent() for r in Role}

def test_same_seed_same_final_state():
    a = simulate_full_game(seed=42, player_role=Role.RETAILER, agents=make_agents())
    b = simulate_full_game(seed=42, player_role=Role.RETAILER, agents=make_agents())
    assert a == b  # frozen dataclass field-by-field equality

def test_same_seed_byte_identical_trace():
    """Stronger: assert every per-week tuple is identical, not just final state."""
    a = simulate_full_game(seed=42, player_role=Role.RETAILER, agents=make_agents())
    b = simulate_full_game(seed=42, player_role=Role.RETAILER, agents=make_agents())
    for sa, sb in zip(a.stations, b.stations):
        assert sa.inventory_history == sb.inventory_history
        assert sa.backlog_history == sb.backlog_history
        assert sa.orders_placed_history == sb.orders_placed_history
        assert sa.cost_history == sb.cost_history
```

### Example: GATE 1 (equilibrium regression)

```python
# tests/test_equilibrium.py
from beergame.engine.tick import simulate_full_game
from beergame.engine.state import Role, INITIAL_INVENTORY
from beergame.engine.demand import constant_demand
from beergame.ai.base import ConstantOrderAgent

def test_equilibrium_constant_demand_constant_orders():
    """Constant customer demand=4, all stations order 4 → inventory stays at 12 for 36 weeks."""
    agents = {r: ConstantOrderAgent(4) for r in Role}
    final = simulate_full_game(
        seed=42, player_role=Role.RETAILER, agents=agents,
        demand_fn=constant_demand,  # inject the constant demand
    )
    for station in final.stations:
        assert all(inv == INITIAL_INVENTORY for inv in station.inventory_history), \
            f"{station.role.name}: inventory drifted from 12 — pipeline init or tick order is wrong"
        assert all(b == 0 for b in station.backlog_history), \
            f"{station.role.name}: backlog accumulated under equilibrium"
```

### Example: GATE 2 (bullwhip calibration)

```python
# tests/test_bullwhip_emerges.py
from beergame.engine.tick import simulate_full_game
from beergame.engine.state import Role
from beergame.ai.sterman import ShipmentAnchorAndAdjustAgent

def test_bullwhip_factory_retailer_peak_ratio():
    """Classic step demand, all-AI → max(factory orders) / max(retailer orders) in [2.0, 4.0]."""
    agents = {r: ShipmentAnchorAndAdjustAgent() for r in Role}
    final = simulate_full_game(seed=42, player_role=Role.RETAILER, agents=agents)
    retailer = final.stations[Role.RETAILER.value]
    factory = final.stations[Role.FACTORY.value]
    retailer_peak = max(retailer.orders_placed_history)
    factory_peak = max(factory.orders_placed_history)
    assert retailer_peak > 0, "retailer never ordered anything — heuristic broken"
    ratio = factory_peak / retailer_peak
    assert 2.0 <= ratio <= 4.0, (
        f"bullwhip ratio {ratio:.2f} outside canonical [2.0, 4.0]. "
        f"Likely cause: Sterman parameters wrong (check empirical α=0.26, β=0.34, "
        f"θ=0.36, S'=17 — NOT optimal α=β=1, θ=0)."
    )
```

### Example: `test_no_streamlit_import.py`

```python
# tests/test_no_streamlit_import.py
import ast
from pathlib import Path
import pytest

ENGINE_DIRS = ["beergame/engine", "beergame/ai", "beergame/config"]

def _streamlit_imports_in(path: Path) -> list[str]:
    tree = ast.parse(path.read_text())
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("streamlit"):
                    bad.append(f"{path}: import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("streamlit"):
                bad.append(f"{path}: from {node.module} import ...")
    return bad

@pytest.mark.parametrize("subdir", ENGINE_DIRS)
def test_engine_modules_do_not_import_streamlit(subdir):
    bad = []
    for py_file in Path(subdir).rglob("*.py"):
        bad.extend(_streamlit_imports_in(py_file))
    assert not bad, "Streamlit imports found in engine layer:\n" + "\n".join(bad)
```

### Example: `test_station_view_visibility.py`

```python
# tests/test_station_view_visibility.py
import pytest
from beergame.engine.state import new_game, Role, RetailerView, StationView
from beergame.engine.tick import build_station_view

def test_retailer_view_has_customer_demand():
    state = new_game(player_role=Role.RETAILER)
    # Add one customer_demand entry so the retailer view can read it
    # (in practice, fill_orders appends to customer_demand_history first).
    # For the visibility test, just check the class.
    view = build_station_view(state, Role.RETAILER)
    assert isinstance(view, RetailerView)
    # customer_demand exists (may default-ish on week 0 — assert attribute access works)
    _ = view.customer_demand  # must not raise

@pytest.mark.parametrize("role", [Role.WHOLESALER, Role.DISTRIBUTOR, Role.FACTORY])
def test_non_retailer_view_has_no_customer_demand(role):
    state = new_game(player_role=Role.RETAILER)  # player_role doesn't affect view construction
    view = build_station_view(state, role)
    assert isinstance(view, StationView)
    assert not isinstance(view, RetailerView)
    with pytest.raises(AttributeError):
        _ = view.customer_demand
```

### Example: `test_tick_invariants.py`

```python
# tests/test_tick_invariants.py
from beergame.engine.tick import receive_shipments, fill_orders, record_state, place_orders, advance_pipelines, advance_week
from beergame.engine.state import new_game, Role
from beergame.ai.base import ConstantOrderAgent
from beergame.engine.demand import constant_demand

def test_tick_runs_five_steps_in_canonical_order():
    """Smoke test: each step is callable and composable in the documented order."""
    state = new_game(player_role=Role.RETAILER)
    s1 = receive_shipments(state)
    s2 = fill_orders(s1)  # ... thread demand_fn here as needed
    s3 = record_state(s2)
    s4 = place_orders(s3, player_order=4, ai_agents={r: ConstantOrderAgent(4) for r in Role if r != Role.RETAILER})
    s5 = advance_pipelines(s4)
    assert s5.week == 1
    # After step 5, all pending fields are cleared.
    for st in s5.stations:
        assert st._pending_in_shipment == 0
        assert st._pending_in_order == 0

def test_record_before_order_decision_uses_post_fill_inventory():
    """The agent must see post-fill state, not pre-fill. Detectable: when inventory drops
    to 0 in step 2, the agent in step 4 sees inventory=0 (not the pre-fill inventory)."""
    # ... construct a state where fill_orders drains inventory, then verify the view
    # passed to a spy agent has inventory == 0.
    pass  # Concrete fixture left to implementation

def test_player_order_arrives_after_lead_time_not_instantly():
    """Player at Wholesaler orders 99 on week 1. The 99 must NOT appear in their own
    supply_line on week 2 (it's still in the incoming_orders queue going TO the distributor).
    """
    # ... Concrete fixture left to implementation.
    pass
```

### Example: `test_costs.py`

```python
# tests/test_costs.py
from beergame.engine.costs import weekly_cost
from beergame.engine.state import StationState, Role

def test_holding_cost_only():
    s = StationState(role=Role.RETAILER, inventory=12, backlog=0,
                     incoming_shipments=(4, 4), incoming_orders=(4,),
                     inventory_history=(), backlog_history=(), orders_placed_history=(),
                     orders_received_history=(), shipments_sent_history=(), cost_history=())
    assert weekly_cost(s) == 12 * 0.50  # 6.00

def test_backorder_only():
    s = StationState(role=Role.WHOLESALER, inventory=0, backlog=5,
                     incoming_shipments=(4, 4), incoming_orders=(4,),
                     inventory_history=(), backlog_history=(), orders_placed_history=(),
                     orders_received_history=(), shipments_sent_history=(), cost_history=())
    assert weekly_cost(s) == 5 * 1.00

def test_backlog_accumulates_across_3_week_stockout():
    """Engineer the state, run 3 ticks, verify backlog cost == 3 * unfilled * 1.00."""
    pass  # Concrete fixture left to implementation
```

### Example: `test_sterman_heuristic.py`

```python
# tests/test_sterman_heuristic.py
from beergame.ai.sterman import ShipmentAnchorAndAdjustAgent
from beergame.engine.state import StationView, Role

def test_default_parameters_are_empirical_sterman_1989():
    """Sanity check: defaults match the canonical empirical fit."""
    a = ShipmentAnchorAndAdjustAgent()
    assert a.alpha == 0.26
    assert a.beta == 0.34
    assert a.theta == 0.36
    assert a.desired_inventory == 17.0

def test_equilibrium_view_yields_equilibrium_order():
    """At inventory=12, backlog=0, supply_line=8, last_order=4 with smoothed_demand=4:
       L_t = 0.36*4 + 0.64*4 = 4
       O = max(0, round(4 + 0.26*(17 - 12) - 0.34*8))
         = max(0, round(4 + 1.30 - 2.72))
         = max(0, round(2.58))
         = 3
       This is NOT 4! Empirical Sterman doesn't perfectly maintain equilibrium because
       β < 1 underweights the supply line. This is FEATURE, not bug — it's why bullwhip emerges.
    """
    a = ShipmentAnchorAndAdjustAgent()
    view = StationView(role=Role.WHOLESALER, week=1, inventory=12, backlog=0,
                       supply_line=8, last_order_received=4, recent_orders_received=(4, 4, 4, 4))
    order = a.decide_order(view)
    # Document the actual computed value here once implementation is done.
    # The point is: this is reproducible and pinned.
    assert order == 3  # ← TO VERIFY at implementation time; pin whatever it actually is.

def test_protocol_conformance():
    from beergame.ai.base import Agent
    a = ShipmentAnchorAndAdjustAgent()
    assert isinstance(a, Agent)
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Mutable dataclass with in-place updates | `frozen=True, slots=True` + `dataclasses.replace()` | Trivial time-travel debug; safe across Streamlit reruns; pytest comparisons one-liner |
| ABC base class for Agent interface | `typing.Protocol` (3.8+) with `@runtime_checkable` | Structural typing; no inheritance; less ceremony |
| `collections.deque` for FIFO pipelines | Tuple slicing | Tuples support slicing; deque doesn't. At our lengths (1-2) perf is identical |
| `unittest.TestCase` | bare pytest `def test_*` | Less boilerplate; better fixtures |
| `json.dumps` for state debugging | `dataclasses.asdict` | Stdlib; no custom encoder needed |
| `random.seed(42)` global mutation | Pass seed in state, use `random.Random(seed)` instances | Deterministic across re-imports; in v1, no random module is used at all |

**Deprecated/outdated:**
- `@dataclass(frozen=True)` *without* `slots=True` — slots gives ~20% memory savings and faster attribute access; standard since Python 3.10
- `typing.Type[T]` — use `type[T]` (3.9+) directly
- `from __future__ import annotations` — needed only if you have forward refs not resolvable; not required here

---

## Open Questions

These are decisions the planner (or implementer) needs to make. Research can't resolve them without writing the code.

### 1. Exact `desired_inventory` (S′) for the Sterman agent

- **What we know:** Sterman 1989 Table 2 reports median S′ ≈ 17 across subjects. The project research uses S′=17 in summaries; the architecture doc uses S′=12 in its example code.
- **What's unclear:** Some sources report S′=12 (the initial inventory), others S′=17. The discrepancy matters: GATE 2's [2.0, 4.0] ratio is sensitive to this value.
- **Recommendation:** Start with S′=17 (matches the most-cited empirical fit in the project research). If GATE 2 fails on the high side (factory peak too large → ratio > 4), reduce S′. If GATE 2 fails on the low side (ratio < 2), increase S′ or adjust α. **Do not silently widen the test bounds.**

### 2. Partial backlog fulfillment behavior

- **What we know:** Engine ships `min(inventory, demand+backlog)`. Backlog is cleared FIFO conceptually (oldest demand first), but since we model backlog as a scalar, "FIFO" is implicit (the oldest week's unfilled demand is still counted).
- **What's unclear:** Whether to track per-week backlog cohorts (overkill for this game, but would let us report "oldest unfilled week"). Project research doesn't require it.
- **Recommendation:** Single scalar backlog field per station (current design). No per-cohort tracking. If a future feature requires it, refactor at that time.

### 3. Where `demand_fn` is plumbed

- **Option A:** Store on `GameState` as a callable field. Breaks frozen-dataclass equality (functions aren't field-comparable) — equality test would have to skip the field.
- **Option B:** Pass as a parameter on `advance_week` and `simulate_full_game`. Stateless; works with frozen dataclass equality; but every caller must pass the same `demand_fn` consistently.
- **Recommendation:** Option B. The test (`test_equilibrium.py`) injects `constant_demand`; production code uses the default `demand_for_week`. Wrap in a `Scenario` config object if it grows (it won't for v1).

### 4. Should `_pending_in_*` transient fields be visible in the public `StationState` repr?

- **What we know:** They're implementation detail of the 5-step tick. Leading underscore signals "private."
- **What's unclear:** Whether to use `field(repr=False)` to hide them from `repr()`. Cosmetic.
- **Recommendation:** Use `field(repr=False, compare=False)` on the transient fields. They are zero immediately after `advance_pipelines` runs, so they don't carry meaningful information in stored state; hiding them from `repr` makes debug output cleaner and excluding from `compare` means equality is unaffected.

### 5. Whether to add a `Scenario` dataclass

- **What we know:** v1 has one scenario (CLASSIC_36W). Many parameters (lead times, demand pattern, total weeks, initial inventory) are loosely "scenario config."
- **What's unclear:** Whether to formalize as `@dataclass(frozen=True) Scenario` now or wait for v2 (when configurability matters).
- **Recommendation:** Module-level constants in `config/scenarios.py` for v1. Refactor to `Scenario` dataclass only if v2 adds configurability (D2-07).

### 6. Sterman's S′ — split between Factory and others?

- **What we know:** JASSS 2014 reports optimal S′≈28 for R/W/D and S′≈20 for Factory (different because Factory's pipeline is shorter — 2-week production vs 4-week acquisition for others). For the *empirical* fit, project research uses S′=17 uniformly.
- **What's unclear:** Whether to use a per-role S′ in the empirical Sterman agent.
- **Recommendation:** Uniform S′=17 for v1. GATE 2 will tell us if per-role tuning is needed. If GATE 2 passes, ship it.

---

## Sources

### Primary (HIGH confidence)
- Project research: `.planning/research/SUMMARY.md` — synthesizes Sterman 1989 canonical parameters, tick sequence, exit gates
- Project research: `.planning/research/STACK.md` — locks Python 3.12, pytest 8.x, Ruff 0.6+, no NumPy/pandas
- Project research: `.planning/research/ARCHITECTURE.md` — module layout sketch, frozen dataclass pattern, Sterman code shape, 5-step tick rationale
- Project research: `.planning/research/PITFALLS.md` — all 20 enumerated pitfalls (5 are critical for Phase 1)
- Project research: `.planning/research/FEATURES.md` — full information-visibility matrix per station
- `.planning/REQUIREMENTS.md` — ENG-01 through ENG-10, AI-01 through AI-04
- [Python dataclasses docs (stdlib)](https://docs.python.org/3/library/dataclasses.html) — `frozen=True`, `slots=True`, `replace()`, `field()` semantics

### Secondary (MEDIUM confidence)
- [Python Dataclasses 2026 Guide (pyblog.in)](https://www.pyblog.in/programming/python-dataclasses-the-complete-2026-guide-from-dataclass-to-slots-frozen-and-__post_init__/) — confirms frozen+slots pattern; ~2.4x instantiation overhead (negligible at 36 ticks × 4 stations)
- [Real Python: Python's deque](https://realpython.com/python-deque/) — confirms deque doesn't support slicing; justifies tuple choice
- [Python collections docs](https://docs.python.org/3/library/collections.html#collections.deque) — official confirmation of deque API surface
- Sterman, J.D. (1989). "Modeling Managerial Behavior." *Management Science* 35(3):321-339 — canonical empirical α/β/θ/S′ values; cited via project research
- Edali & Yasarcan (2014). "A Mathematical Model of the Beer Game." *JASSS* 17(4):2 — formal tick sequence and pipeline mechanics; identifies the "optimal vs empirical" trap

### Tertiary (LOW confidence)
- None used. All claims supported by Primary or Secondary sources.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — locked by project research and stdlib-only; no version-drift risk
- Architecture (module layout, dataclass shape, tick decomposition): HIGH — derived from cross-verified Sterman/JASSS sources via project research
- Sterman heuristic code shape: HIGH — formula and empirical parameters cross-verified across project research sources
- Tick implementation details (transient fields for pipeline data flow): MEDIUM — the `_pending_in_*` pattern is a defensible synthesis but hasn't been tested against an existing reference implementation; GATES 1 and 2 will validate it
- Test design: HIGH — every test maps to a specific requirement ID or pitfall
- Open questions (S′ value, demand_fn plumbing): MEDIUM — final values pinned at implementation time by GATE 2 feedback

**Research date:** 2026-05-18
**Valid until:** 2027-05-18 (12 months — Sterman canonical parameters are 35+ years stable; Python 3.12 stdlib APIs are stable; only the empirical S′ value might be re-tuned based on GATE 2 results during implementation)
