# Architecture Research

**Domain:** Single-player Streamlit simulation of the MIT Beer Distribution Game (Sterman, 1989), 4 stations, 3 AI opponents, 36-week classic step demand, in-session state only.
**Researched:** 2026-05-18
**Confidence:** HIGH

The architecture below is opinionated. It optimizes for one constraint above all others:

> **The simulation engine must be a pure-Python library that knows nothing about Streamlit.**

Every other decision (state model, tick sequence, agent interface, build order) flows from that. If the engine ever imports `streamlit`, the whole house of cards collapses: pytest won't run it cleanly, you can't reproduce a run from a seed, and you can't swap the UI later. Hold that line.

---

## Standard Architecture

### System Overview

```
┌───────────────────────────────────────────────────────────────────┐
│                       UI LAYER (Streamlit)                        │
│                                                                   │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐       │
│  │ Setup     │  │ Play      │  │ Debrief   │  │ Rules /   │       │
│  │ screen    │→ │ screen    │→ │ screen    │  │ Primer    │       │
│  │ (station, │  │ (per-week │  │ (4-panel  │  │           │       │
│  │  seed)    │  │  order)   │  │  charts)  │  │           │       │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └───────────┘       │
│        │              │              │                            │
│        │   reads/writes st.session_state["game"] (a GameState)    │
│        │              │              │                            │
│        ▼              ▼              ▼                            │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │       app.py  +  views/  +  charts/  (Streamlit-only)     │    │
│  └──────────────────────────────────────────────────────────┘     │
├───────────────────────────────────────────────────────────────────┤
│                ENGINE BOUNDARY (no streamlit import)              │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────┐    ┌─────────────────┐   ┌────────────────┐  │
│  │  engine/        │    │  ai/            │   │  config/       │  │
│  │  - state.py     │←──→│  - sterman.py   │   │  - scenarios.py│  │
│  │  - tick.py      │    │  - base.py      │   │  - costs.py    │  │
│  │  - demand.py    │    │  (Agent ABC)    │   │                │  │
│  │  - costs.py     │    └─────────────────┘   └────────────────┘  │
│  │  - metrics.py   │                                              │
│  └─────────────────┘                                              │
│                                                                   │
│            ↑ pure Python, deterministic, pytest-able              │
└───────────────────────────────────────────────────────────────────┘
```

The horizontal line in the middle is **the engine boundary**. The rule is: nothing below the line imports `streamlit`, and nothing above the line knows the internals of `GameState` beyond what the engine exposes as a public API. The UI calls four functions in total — `new_game(...)`, `submit_player_order(state, order)`, `is_game_over(state)`, `compute_debrief(state)` — and renders whatever they return.

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| `engine.state` | Defines the data shape of a game and per-station state. Immutable-ish dataclasses. | Frozen `@dataclass` + `dataclasses.replace` for updates, or plain mutable dataclasses if simpler. No I/O. |
| `engine.tick` | Implements the canonical week sequence. The *only* place game state mutates. | A single `advance_week(state, player_order) -> state` function that internally walks the 5-step sequence. |
| `engine.demand` | Generates customer demand each week (classic step demand for v1, pluggable later). | Function `demand_for_week(week, scenario) -> int`. |
| `engine.costs` | Holding + backorder cost calculation per week, per station, totals. | `weekly_cost(station, params) -> float`, `total_cost(state) -> float`. |
| `engine.metrics` | Post-game analytics: amplification ratio, station rankings, peak inventory/backlog. | Pure functions over a completed `GameState`. |
| `ai.base` | `Agent` interface. Single method: `decide_order(view) -> int`. | Protocol or ABC. Agents see only their own `StationView`, not the whole game. |
| `ai.sterman` | The anchor-and-adjust heuristic with configurable α, β, θ, L̂ smoothing. | Stateless class holding parameters; reads `StationView`. |
| `config.scenarios` | Demand patterns, lead times, initial inventories, game length. | Plain dataclasses / dict constants. |
| `config.costs` | Holding cost ($0.50/unit/week) and backorder cost ($1.00/unit/week). | Constants. |
| `app.py` | Streamlit entry point. Owns `st.session_state`. Routes to setup / play / debrief screens based on a `phase` flag. | Top-level script. ~50 lines, mostly routing. |
| `views/` | Per-screen rendering. `setup.py`, `play.py`, `debrief.py`, `rules.py`. | Each module exports `render(state)`. |
| `charts/` | Plotly figure builders that take engine data and return `go.Figure`. No `st.*` calls inside. | Pure functions returning figures; `views/debrief.py` calls `st.plotly_chart(fig)`. |
| `tests/` | pytest suite. Tests import `engine.*` and `ai.*` directly — never `streamlit`. | Determinism tests, tick-invariant tests, bullwhip-emergence tests. |

The reason `charts/` is a peer of `views/` and not inside it: chart builders are pure (data in, `go.Figure` out) and you may want to snapshot-test them with pytest. Keep `st.plotly_chart(...)` calls in `views/debrief.py` only.

---

## Recommended Project Structure

```
beergameNexStratus/
├── app.py                          # Streamlit entry point — owns session_state, routes screens
├── requirements.txt                # streamlit, plotly, pandas, numpy, pytest
├── .streamlit/
│   └── config.toml                 # theme, page config (for Cloud deploy)
├── beergame/                       # The package — `pip install -e .` for tests
│   ├── __init__.py
│   ├── engine/                     # PURE PYTHON. No streamlit imports. Ever.
│   │   ├── __init__.py             # Re-exports new_game, advance_week, etc.
│   │   ├── state.py                # GameState, StationState, StationView dataclasses
│   │   ├── tick.py                 # advance_week() — the canonical 5-step sequence
│   │   ├── demand.py               # step_demand(), demand generators
│   │   ├── costs.py                # holding/backorder cost calc
│   │   └── metrics.py              # amplification ratio, totals, debrief math
│   ├── ai/                         # PURE PYTHON.
│   │   ├── __init__.py
│   │   ├── base.py                 # Agent protocol/ABC
│   │   └── sterman.py              # ShipmentAnchorAndAdjust agent (the heuristic)
│   ├── config/                     # PURE PYTHON. Constants and scenario configs.
│   │   ├── __init__.py
│   │   ├── scenarios.py            # CLASSIC_36W, lead times, initial state
│   │   └── costs.py                # HOLDING_COST, BACKORDER_COST
│   ├── views/                      # Streamlit-aware. Each module: render(state).
│   │   ├── __init__.py
│   │   ├── setup.py                # Station picker, seed, "start game"
│   │   ├── rules.py                # Rules + bullwhip primer
│   │   ├── play.py                 # Per-week panel + order input + "advance week"
│   │   └── debrief.py              # 4-panel chart + amplification + cost + narrative
│   └── charts/                     # Pure Plotly figure builders. No st.* calls.
│       ├── __init__.py
│       ├── orders_inventory.py     # The 4-panel debrief figure
│       └── cost_breakdown.py
├── tests/
│   ├── __init__.py
│   ├── test_determinism.py         # Same seed → same final state
│   ├── test_tick_invariants.py     # Conservation: shipments don't vanish
│   ├── test_sterman_heuristic.py   # α/β edge cases, formula correctness
│   ├── test_bullwhip_emerges.py    # Classic demand + all-AI → amplification > 2x
│   └── test_costs.py               # Cost accounting math
└── README.md
```

### Structure Rationale

- **`engine/` is a sibling of `views/`, not a subfolder.** This is the load-bearing decision. They are equals. Treating engine as "logic for the UI" subtly invites Streamlit imports to creep in.
- **`beergame/` is a real installable package.** `pip install -e .` from the project root lets tests do `from beergame.engine import advance_week` without `sys.path` hacks. Streamlit Cloud is fine with this.
- **`charts/` is separate from `views/`.** Charts are pure (data → `go.Figure`). Views are Streamlit (call `st.plotly_chart`). Splitting them lets pytest snapshot the figure JSON without spinning up Streamlit.
- **`config/` instead of magic numbers.** Cost constants and scenario parameters are research-defensible (Sterman's paper uses specific values). Centralizing makes "did you use $0.50 or $1.00 for holding cost?" a one-line answer.
- **No `models/` or `domain/` folder.** This isn't a CRUD app. The "domain model" *is* the engine. Keeping the vocabulary lean (engine/ai/views) prevents people from looking for things in the wrong place.

---

## State Model

**Recommendation: frozen `@dataclass` everywhere. No pydantic, no plain dicts.**

Why not pydantic? You don't have untrusted input (no API, no DB). Pydantic's value is validation; you don't need it here, and its overhead per-tick is real if a debrief runs 36 ticks × 4 stations.

Why not dicts? Refactoring is a nightmare and IDEs can't help you. `state.stations[0].inventory` autocompletes; `state["stations"][0]["inventory"]` does not.

Why frozen? Forces every tick step to *return a new state* instead of mutating in place. Makes time-travel debugging trivial (`history` is just a list of past states), makes Streamlit reruns safe (no aliasing surprises), and makes pytest assertions cleaner (compare full states).

### Field-Level Sketch

```python
# beergame/engine/state.py
from dataclasses import dataclass, field
from enum import Enum

class Role(str, Enum):
    RETAILER = "retailer"
    WHOLESALER = "wholesaler"
    DISTRIBUTOR = "distributor"
    FACTORY = "factory"

@dataclass(frozen=True)
class StationState:
    role: Role
    inventory: int                        # on-hand units
    backlog: int                          # unfilled downstream orders
    # Lead-time queues. Index 0 = arrives THIS week (after the "advance pipelines"
    # step), index -1 = just placed this week. Length = lead_time.
    incoming_shipments: tuple[int, ...]   # units in transit from upstream
    incoming_orders: tuple[int, ...]      # orders in transit from downstream
    # History (append-only, used for charts + debrief). Length == current_week.
    inventory_history: tuple[int, ...]
    backlog_history: tuple[int, ...]
    orders_placed_history: tuple[int, ...]
    orders_received_history: tuple[int, ...]
    shipments_sent_history: tuple[int, ...]
    cost_history: tuple[float, ...]       # cumulative per week

@dataclass(frozen=True)
class GameState:
    week: int                             # 0-indexed; week 0 is initial state, first tick produces week 1
    total_weeks: int                      # 36
    seed: int
    player_role: Role
    stations: tuple[StationState, ...]    # always length 4, ordered RETAILER→FACTORY
    customer_demand_history: tuple[int, ...]   # what the retailer faced each week
    phase: str                            # "setup" | "playing" | "done"

@dataclass(frozen=True)
class StationView:
    """What an AI agent (or the player UI) sees on its turn. A read-only window
    onto its own StationState, plus the info needed to decide an order."""
    role: Role
    inventory: int
    backlog: int
    supply_line: int                      # sum of incoming_shipments (units on the way)
    last_order_received: int              # downstream demand this week
    recent_orders_received: tuple[int, ...]   # for L̂ smoothing
    week: int
```

A few design notes:

- **Tuples, not lists, for histories and queues.** Frozen dataclass + tuple = genuinely immutable. Cheap to copy by reference between ticks.
- **Per-station pipelines, not a global pipeline map.** `incoming_shipments[i]` lives on the *receiving* station, not the sender. This makes "what arrives this week at the wholesaler?" a one-field lookup.
- **No `desired_inventory` field on the state.** That's an *agent parameter*, not a state attribute. It belongs in `ai.sterman.ShipmentAgent.__init__`. State is "what happened"; agent config is "how I'd decide."
- **History tuples on each station are duplicative on purpose.** Yes you could derive `inventory_history` from a list of past `GameState`s, but charts want columns and you'll regret recomputing them on every Streamlit rerun. Append once per tick, render forever.

---

## The Canonical Tick Sequence

This is the heart of the engine. Get it wrong and the bullwhip won't emerge correctly, or worse, will emerge spuriously and you'll think it's working.

**The order, per Sterman (verified against MIT Sloan Beer Game documentation and the JASSS mathematical model paper):**

```
For each week:

  1. RECEIVE SHIPMENTS
     For each station: pop the front of incoming_shipments queue,
     add those units to inventory.

  2. RECEIVE & FILL ORDERS
     For each station: pop the front of incoming_orders queue.
     Combine with existing backlog. Ship min(inventory, demand+backlog)
     downstream. Update inventory and backlog accordingly.
     (The factory's "downstream" is the retailer's customer? NO —
     the factory ships to the distributor. The retailer ships to
     the external customer; customer demand is the input to the
     retailer's incoming_orders pipeline.)

  3. RECORD STATE
     Append inventory, backlog, orders_received, shipments_sent,
     and weekly cost to each station's history.

  4. PLACE NEW ORDERS
     For each station: call the agent (or read the player's input)
     to get this week's order quantity. Enqueue that order onto
     the upstream station's incoming_orders queue (i.e., push to
     the back of the queue, which will arrive after the order lead time).
     The factory's "order" becomes a production start — push it
     onto the factory's own incoming_shipments queue (production
     delay).

  5. ADVANCE PIPELINES
     Shift every queue forward by one slot. (If you implemented the
     queues as fixed-length tuples where index 0 is "ready this week,"
     this is just slicing.)

  Increment week. If week == total_weeks, set phase = "done".
```

### Why this order matters

**Receive before fill.** If you fill first, this-week's arrivals can't help fill this-week's backlog — you've artificially extended delays by one week and the bullwhip will be too large.

**Fill before record.** Recording before fill means your "inventory" chart shows pre-shipment levels and the cost calc double-counts. Subtle, but breaks the debrief.

**Record before order.** Agents must decide based on the *post-shipment* state (what they actually have, post-fill). Recording first means the agent's view is consistent with what's plotted, which makes debrief explanations match the agent's decision.

**Order before pipeline advance.** Orders placed this week go to the *back* of the queue (they don't arrive next week, they arrive in `lead_time` weeks). Advancing first and then ordering would put new orders into a slot that's about to fire — instant arrival, no lead time, no bullwhip.

### Public API for the tick

```python
# beergame/engine/tick.py

def advance_week(state: GameState, player_order: int,
                 ai_agents: dict[Role, Agent]) -> GameState:
    """Advance one week. Returns a NEW GameState (frozen dataclass).
    
    `player_order` is the order quantity the human entered for their station.
    `ai_agents` is a dict mapping the OTHER three roles to their agents.
    
    The function is the only place GameState changes. Pure, deterministic
    given (state, player_order, ai_agents) — the seed is baked into state
    and used only for demand generation, not agent randomness (agents are
    deterministic in v1).
    """
    ...
```

The UI calls this once per "advance week" button press. Pytest calls this in a loop with a stub player agent to simulate full games.

---

## The AI Agent Interface

```python
# beergame/ai/base.py
from typing import Protocol

class Agent(Protocol):
    def decide_order(self, view: StationView) -> int:
        """Return order quantity for this week. Non-negative integer."""
        ...
```

That's it. One method. The agent sees a `StationView` (read-only window onto its own state) and returns an integer. No mutation, no game-wide state access, no peeking at other stations. This matches the real game: each player only sees their own station.

### Sterman Anchor-and-Adjust Implementation

The published heuristic (Sterman 1989, formalized in many follow-ups including MIT dspace papers):

```
O_t = max(0, L̂_t + α·(S' - S_t) - β·SL_t  + ε)
       ────                ──────────   ──────
       │                       │             │
       anchor on              adjust for     supply-line
       expected demand        inventory gap  adjustment
                                             (β often ~0.34 in
                                              fitted human data;
                                              optimal = 1.0)
```

Where:
- `L̂_t` = forecast of incoming orders, exponentially smoothed with parameter `θ`: `L̂_t = θ·orders_received_{t-1} + (1-θ)·L̂_{t-1}`
- `S'` = desired inventory level (agent parameter, e.g., 12 units)
- `S_t` = current on-hand inventory minus backlog (net inventory)
- `SL_t` = supply line (units already on order but not yet arrived)
- `α` ∈ [0, 1] = stock adjustment fraction (Sterman's median fit: ~0.26)
- `β` ∈ [0, 1] = supply line weight (Sterman's median fit: ~0.34 — humans underweight; optimal is 1.0)
- `ε` = noise; in v1 set to 0 for determinism

Translated to code:

```python
# beergame/ai/sterman.py
from dataclasses import dataclass

@dataclass
class ShipmentAnchorAndAdjustAgent:
    """Sterman 1989 anchor-and-adjust ordering heuristic.

    Default parameters match Sterman's median empirical fit (humans
    underweighting the supply line is what produces the bullwhip)."""
    alpha: float = 0.26      # stock adjustment fraction
    beta: float = 0.34       # supply line weight (1.0 = rational)
    theta: float = 0.36      # demand smoothing weight
    desired_inventory: int = 12   # S'
    
    # Per-instance forecast carry. One agent instance per station per game.
    _smoothed_demand: float = 4.0   # init to expected steady-state
    
    def decide_order(self, view: StationView) -> int:
        # Update demand forecast with this week's observed order.
        self._smoothed_demand = (
            self.theta * view.last_order_received
            + (1 - self.theta) * self._smoothed_demand
        )
        net_inventory = view.inventory - view.backlog
        order = (
            self._smoothed_demand
            + self.alpha * (self.desired_inventory - net_inventory)
            - self.beta * view.supply_line
        )
        return max(0, round(order))
```

### Why a stateful class rather than a pure function

The smoothed demand `L̂` carries across weeks. You can implement that either by (a) passing the previous `L̂` in the `StationView`, or (b) letting the agent hold it as instance state. Option (b) is cleaner: the agent owns its forecasting logic, and `StationView` stays a pure data window onto game state.

The agent instance lives in `st.session_state["ai_agents"]` (a dict of Role → Agent) for the duration of a game. Because Streamlit reruns the script, the dict survives reruns but the agent's `_smoothed_demand` survives with it.

### Swapping heuristics later

Because every agent implements the same `decide_order(view) -> int` protocol, you can later add:

- `NaiveBaseAgent` — always order = last_demand
- `OptimalSterman` — same formula with β=1.0, α=1.0
- `RLAgent` — a trained model

…and the engine doesn't change. The setup screen just lets the user pick which `Agent` class each non-player station uses.

---

## Streamlit Reruns and `session_state`

Streamlit's execution model: **every interaction reruns the script top to bottom.** This is the biggest gotcha and the source of the engine/UI separation rule. If your engine state lived in a module-level global, every rerun would reset it. The only thing that persists across reruns is `st.session_state`.

### The Pattern

```python
# app.py
import streamlit as st
from beergame.engine import new_game, advance_week, is_game_over
from beergame.ai.sterman import ShipmentAnchorAndAdjustAgent
from beergame.engine.state import Role
from beergame.views import setup, play, debrief, rules

st.set_page_config(page_title="Beer Game", layout="wide")

def init_session():
    if "phase" not in st.session_state:
        st.session_state.phase = "setup"   # "setup" | "rules" | "playing" | "done"
        st.session_state.game = None
        st.session_state.ai_agents = None

def start_game(player_role: Role, seed: int):
    """Callback for 'Start Game' button."""
    st.session_state.game = new_game(player_role=player_role, seed=seed)
    st.session_state.ai_agents = {
        role: ShipmentAnchorAndAdjustAgent()
        for role in Role if role != player_role
    }
    st.session_state.phase = "playing"

def submit_order(order: int):
    """Callback for 'Advance Week' button."""
    st.session_state.game = advance_week(
        st.session_state.game,
        player_order=order,
        ai_agents=st.session_state.ai_agents,
    )
    if is_game_over(st.session_state.game):
        st.session_state.phase = "done"

def reset_game():
    """Callback for 'New Game' button."""
    for key in ("phase", "game", "ai_agents"):
        del st.session_state[key]

init_session()

# Route to the right screen based on phase
if st.session_state.phase == "setup":
    setup.render(on_start=start_game, on_show_rules=lambda: st.session_state.update(phase="rules"))
elif st.session_state.phase == "rules":
    rules.render(on_back=lambda: st.session_state.update(phase="setup"))
elif st.session_state.phase == "playing":
    play.render(state=st.session_state.game, on_submit=submit_order)
elif st.session_state.phase == "done":
    debrief.render(state=st.session_state.game, on_reset=reset_game)
```

### Key Streamlit Idioms

**Callbacks via `on_click=`.** This is the canonical Streamlit pattern (per Streamlit docs on session state). The callback runs *before* the script reruns, so by the time the rerun renders, `st.session_state.game` is already updated to the new week.

```python
st.button("Advance Week", on_click=submit_order, args=(order_value,))
```

**Forms for the order input.** Wrap the number input + advance button in `st.form` so the entire form submits atomically on Enter:

```python
with st.form("order_form"):
    order = st.number_input("Your order", min_value=0, value=4, step=1)
    st.form_submit_button("Advance Week →", on_click=submit_order, args=(order,))
```

**`st.fragment` for the debrief?** Tempting, but unnecessary for v1. The debrief is rendered once when phase flips to "done"; there's no partial-update use case. Skip `@st.fragment` until you have a measurable rerun-cost problem.

**Never put `time.sleep()` in the rerun path.** Beginners reach for it to "animate" turns. Don't. Each button click is one tick; if you want a "play all weeks" demo mode, build it into the engine as `simulate_full_game(state, agents) -> state` and render the result.

**Caching: don't.** `@st.cache_data` on `advance_week` is a trap — same inputs give same output, sure, but caching the *whole game state* by hash defeats the point. Skip caching in v1.

### Where session_state lives in the code

Only `app.py` and the callback functions touch `st.session_state` directly. Views receive state as an argument:

```python
# views/play.py
def render(state: GameState, on_submit: Callable[[int], None]) -> None:
    station = state.stations[role_index(state.player_role)]
    st.write(f"Week {state.week} of {state.total_weeks}")
    st.metric("Inventory", station.inventory)
    st.metric("Backlog", station.backlog)
    # ... order form ...
```

This means views are easy to unit-test (just construct a `GameState` and call `render` — well, you can't easily test Streamlit rendering, but you can at least call it without a session). More importantly: it means if you ever rewrite the UI in Flask, the engine and the views' data contracts are unchanged.

---

## Charts

**Recommendation: one Plotly figure with `make_subplots`, 2x2 grid, for the 4-panel debrief. Separate small Plotly figures for cost breakdown and per-station detail.**

### Why Plotly over Altair/Matplotlib

- **Plotly**: interactive (hover tooltips show exact values per week — important for a debrief), Streamlit's `st.plotly_chart` is first-class, renders cleanly on Cloud, and `make_subplots` handles 2x2 layouts well.
- **Altair**: nice declarative API and faceting, but slower to render with 4 stations × 36 weeks × multiple series, and tooltip customization is fiddlier.
- **Matplotlib**: static images, no hover, no zoom — wrong for a debrief that's the whole teaching payoff.

### The 4-panel figure

```python
# beergame/charts/orders_inventory.py
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from beergame.engine.state import GameState

def build_four_panel(state: GameState) -> go.Figure:
    """2x2 grid: one panel per station. Each panel plots:
    - orders_placed_history (line)
    - inventory_history (line)
    - backlog_history (negative line, or shaded area below 0)
    Customer demand overlaid on the retailer panel as a reference line."""
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[s.role.value.title() for s in state.stations],
        shared_xaxes=True,
    )
    # ... add traces ...
    return fig
```

The view layer calls it once:

```python
# views/debrief.py
from beergame.charts.orders_inventory import build_four_panel

def render(state, on_reset):
    fig = build_four_panel(state)
    st.plotly_chart(fig, use_container_width=True)
```

### Why subplots, not four separate `st.plotly_chart` calls

Shared x-axis. The whole point of the bullwhip debrief is "look how the amplitude grows as you go upstream" — that comparison is visually obvious when all four panels share an x-axis and a coordinated zoom. Four independent charts lose that.

Caveat: `make_subplots` with shared x-axis on Plotly is well-supported but the legend gets crowded. Use one legend entry per series type (Orders, Inventory, Backlog) and group traces with `legendgroup`.

---

## Data Flow

### "Advance Week" Flow

```
[User clicks "Advance Week →" with order=N]
            │
            ▼
   ┌─────────────────────┐
   │ Streamlit callback   │
   │ submit_order(N)      │
   └──────────┬──────────┘
              │
              ▼
   ┌──────────────────────────────────────────────────────────┐
   │ engine.tick.advance_week(state, N, ai_agents)             │
   │                                                           │
   │   1. receive_shipments(state)                             │
   │   2. fill_orders(state)  ← uses customer demand for      │
   │                            the retailer's incoming_orders │
   │   3. record_history(state)                                │
   │   4. for each non-player station:                         │
   │        view = build_station_view(state, role)             │
   │        order = ai_agents[role].decide_order(view)         │
   │        place_order(state, role, order)                    │
   │      place_order(state, player_role, N)                   │
   │   5. advance_pipelines(state)                             │
   │   6. state.week += 1                                      │
   │                                                           │
   │   returns new GameState                                   │
   └──────────────────────┬───────────────────────────────────┘
                          │
                          ▼
   ┌──────────────────────────────────────────────────────────┐
   │ st.session_state.game = new_state                         │
   │ if new_state.week >= 36: phase = "done"                   │
   └──────────────────────┬───────────────────────────────────┘
                          │
                          ▼ (Streamlit reruns the script)
   ┌──────────────────────────────────────────────────────────┐
   │ app.py → views/play.py (or debrief.py if done)            │
   │  - reads st.session_state.game                            │
   │  - renders the new week's metrics + chart                 │
   └──────────────────────────────────────────────────────────┘
```

### Key Data Flows

1. **Customer demand → retailer.** Each week, `engine.demand.demand_for_week(week, scenario)` produces an int, which is pushed onto the retailer's `incoming_orders` queue. The retailer never "sees" the demand directly — it just processes its incoming orders queue like any other station. (Cleaner than special-casing the retailer.)

2. **Player order → station's outgoing order.** The player's input from the order form is passed to `advance_week` as `player_order`. Inside step 4, it's enqueued onto the upstream station's `incoming_orders` queue (or, if the player is the factory, onto the factory's own `incoming_shipments` queue as a production start).

3. **AI agents → upstream orders.** Each non-player station's agent receives a `StationView` and returns an integer. Same enqueue path as the player.

4. **State history → debrief charts.** During step 3 (record_history), each station appends to its history tuples. At game end, those tuples are passed straight to `charts.orders_inventory.build_four_panel`.

---

## Suggested Build Order

The right order respects two constraints: (1) build dependencies bottom-up, (2) prove the simulation is correct *before* you build UI on top of a broken engine.

```
Phase 1: Engine skeleton (no AI, no UI yet)
   ├─ state.py           — dataclasses, new_game() factory
   ├─ demand.py          — step demand generator
   ├─ costs.py           — holding/backorder calc
   └─ tick.py            — advance_week with a STUB player that always orders 4
       └─ pytest: test_determinism (same seed → same final state)
       └─ pytest: test_tick_invariants (units conserved, no negatives)

Phase 2: AI agent
   ├─ ai/base.py         — Agent protocol
   └─ ai/sterman.py      — ShipmentAnchorAndAdjustAgent
       └─ pytest: test_sterman_heuristic (formula correctness)
       └─ pytest: test_bullwhip_emerges (4 agents on classic demand → 
                                         factory amplification > 2x retailer)

   ★ CHECKPOINT: At this point, with zero UI, you can run
     simulate_full_game(state, {role: Agent() for role in Role}) and
     plot the bullwhip from pytest. If the curves don't match Sterman's
     published baseline, fix the engine BEFORE writing any Streamlit.
     This is the most important gate in the whole build.

Phase 3: Metrics + Charts (still no Streamlit)
   ├─ engine/metrics.py   — amplification ratio, totals
   └─ charts/orders_inventory.py  — build_four_panel returns go.Figure
       └─ pytest: snapshot the figure JSON

Phase 4: Minimal Streamlit shell
   ├─ app.py              — phase routing
   ├─ views/setup.py      — pick role, seed, start
   └─ views/play.py       — show current state, take order, advance
       └─ Manual: play through a full game in the browser

Phase 5: Debrief
   ├─ views/debrief.py    — render 4-panel chart + amplification + costs
   └─ Narrative copy      — "you were the X, you faced Y demand, your
                             amplification was Z, here's why"

Phase 6: Rules screen + polish
   ├─ views/rules.py      — primer on bullwhip + how to play
   ├─ charts/cost_breakdown.py
   └─ .streamlit/config.toml — theme

Phase 7: Deploy
   ├─ Public GitHub repo (greycloak85/beer-game)
   ├─ requirements.txt
   └─ Streamlit Community Cloud deploy
```

**The Phase 2 checkpoint is the single most important moment in the build.** If you skip pytest verification of bullwhip emergence and barrel straight into Streamlit, every UI bug looks like a possible engine bug, and you'll spend days debugging the wrong layer. Prove the engine reproduces Sterman's published results in pytest first. Then the UI is just rendering.

---

## Architectural Patterns

### Pattern 1: Engine-Returns-New-State

**What:** Every engine function that "changes" state returns a new `GameState`. The input state is never mutated.

**When to use:** Always, in this app. The frozen dataclass + `dataclasses.replace` pattern enforces it.

**Trade-offs:** Tiny allocation overhead per tick (irrelevant at 36 ticks × 4 stations). In exchange: trivial time-travel debugging, safe Streamlit reruns, easy pytest comparisons (`assert state_after == expected`).

**Example:**
```python
from dataclasses import replace

def receive_shipments(state: GameState) -> GameState:
    new_stations = tuple(
        replace(
            s,
            inventory=s.inventory + s.incoming_shipments[0],
            incoming_shipments=s.incoming_shipments[1:],
        )
        for s in state.stations
    )
    return replace(state, stations=new_stations)
```

### Pattern 2: Phase-Routed Streamlit

**What:** `st.session_state.phase` is a string flag ("setup" / "playing" / "done"). `app.py` is a router that dispatches to one view based on phase. Each view receives state and callbacks; views don't read `st.session_state` directly.

**When to use:** Any multi-screen Streamlit app. This is the canonical Streamlit pattern per their session state docs.

**Trade-offs:** A few more callback args versus letting views grab from `session_state`. Pays off when you split views into modules — they remain testable in isolation.

### Pattern 3: View-Onto-Own-State for Agents

**What:** Agents see a `StationView` (a read-only window onto their own station + recent demand), never the full `GameState`. The engine constructs the view before calling `agent.decide_order`.

**When to use:** Whenever the simulated entity should only know "what it could see in real life." Faithful to the original game.

**Trade-offs:** Slight engine complexity to build the view. Pays off the moment you add a second AI strategy or want to honestly compare human vs AI.

**Example:**
```python
def build_station_view(state: GameState, role: Role) -> StationView:
    s = state.stations[role_index(role)]
    return StationView(
        role=role,
        inventory=s.inventory,
        backlog=s.backlog,
        supply_line=sum(s.incoming_shipments),
        last_order_received=s.orders_received_history[-1],
        recent_orders_received=s.orders_received_history[-4:],
        week=state.week,
    )
```

---

## Anti-Patterns

### Anti-Pattern 1: `import streamlit` in the engine

**What people do:** Add `st.warning(...)` inside `advance_week` to flag negative inventory. Or wrap `engine.demand.step_demand` with `@st.cache_data` because "it's a pure function, why not."

**Why it's wrong:** Now pytest needs Streamlit installed, scripts can't import the engine outside a Streamlit context, and the cache key breaks determinism when seeds change.

**Do this instead:** Engine raises plain exceptions or returns warning data in the `GameState` (e.g., a `warnings: tuple[str, ...]` field). The UI layer formats it with `st.warning`. Engine never imports `streamlit`.

### Anti-Pattern 2: Mutating state in the agent

**What people do:** Agent's `decide_order` modifies `view.inventory` or stores per-game state on the view object.

**Why it's wrong:** Couples agent to engine internals; breaks the "agents see what real players see" contract; makes swapping agents risky.

**Do this instead:** Agent holds its own state (e.g., `_smoothed_demand`) on `self`. `StationView` is read-only data (a frozen dataclass enforces this).

### Anti-Pattern 3: Storing the entire history as a list of past GameStates

**What people do:** `st.session_state.history = []`, append the full state every tick.

**Why it's wrong:** O(N²) memory across the game; charts have to recompute everything every rerun; you lose the "single source of truth for state" property.

**Do this instead:** History tuples *on each station* (inventory_history, etc.) — appended once per tick, read directly by charts. The "current" GameState contains its own history.

### Anti-Pattern 4: Mixing chart construction with `st.*` calls

**What people do:** A function that takes state, builds a Plotly figure, *and* calls `st.plotly_chart`.

**Why it's wrong:** Can't snapshot-test the figure in pytest; can't reuse the chart in a different layout; the function does two things.

**Do this instead:** `charts/*.py` returns `go.Figure`. `views/debrief.py` calls `st.plotly_chart(build_four_panel(state))`.

### Anti-Pattern 5: One mega-`session_state.game_data` dict

**What people do:** `st.session_state.game_data = {"week": ..., "inventory": ..., "backlog": ..., ...}` with everything flat.

**Why it's wrong:** No type checking, easy typos, charts and engine need conventions on key names, refactoring is painful.

**Do this instead:** `st.session_state.game = GameState(...)`. One typed object. Auto-complete works. Tests are trivial.

### Anti-Pattern 6: Non-deterministic engine

**What people do:** Use `random.randint(...)` inside the engine without threading a seeded RNG.

**Why it's wrong:** Can't reproduce a player's run; pytest can't assert outcomes; the published bullwhip pattern won't replicate.

**Do this instead:** Pass `seed` to `new_game`, store it in `GameState`, and use `random.Random(seed)` instances inside the engine. For v1 with deterministic agents and step demand, you barely need RNG at all — but bake the seed in from day one so v2 noise additions don't require a refactor.

---

## Scaling Considerations

This app is single-session, single-player, in-memory. It's not a SaaS. "Scaling" here means user concurrency on Streamlit Cloud, not throughput.

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1-50 concurrent users | No changes needed. Streamlit Cloud free tier handles this with each user getting their own session. |
| 50-500 concurrent users | Free tier may rate-limit. Upgrade to Streamlit Cloud paid tier or move to a single-instance Cloud Run deployment. No code changes. |
| 500+ concurrent users | Move off Streamlit. At this point you want a real backend (FastAPI) + a React UI, sharing the same `beergame.engine` package — this is *why* the engine has no Streamlit imports. The engine becomes the core of an API; you write a thin Flask/FastAPI shell. |

### Scaling Priorities

1. **First bottleneck: per-session memory.** Streamlit Cloud free tier has ~1 GB of RAM shared across all sessions. A `GameState` with 36 weeks × 4 stations × ~10 history fields is tiny (single-digit KB), so even hundreds of concurrent games fit. No action needed.
2. **Second bottleneck: rerun latency.** Plotly figure construction can be slow on the debrief screen with lots of traces. Mitigation if it shows up: pre-compute the figure into `st.session_state` when phase flips to "done" instead of rebuilding on every rerun.

The whole point of the engine/UI separation is that *if* this thing ever needs to scale, you change the UI and keep the engine. So scaling is a UI concern, not an architecture concern.

---

## Test Seams

Where pytest plugs into the system, in order of importance:

1. **`advance_week(state, player_order, ai_agents)`** — the canonical engine entry point. With a stub `ai_agents = {role: ConstantOrderAgent(4) for role in non_player_roles}`, you can simulate any scenario.

2. **`new_game(player_role, seed)`** — returns a fully-formed initial `GameState`. Determinism test: `new_game(role, 42) == new_game(role, 42)`.

3. **`simulate_full_game(seed, agents) -> GameState`** — a convenience function that loops `advance_week` 36 times. Used by `test_bullwhip_emerges` to assert that on the classic step demand, the factory's order amplitude is > 2× the retailer's. This is the *integration test* of the engine.

4. **`Agent.decide_order(view)`** — pure function, trivial unit tests. Test boundary cases for α, β.

5. **`engine.metrics.amplification_ratio(state)`** — pure function, easy to verify.

6. **`charts.build_four_panel(state)`** — returns a `go.Figure`. Snapshot test: assert `fig.to_json()` matches a stored fixture (regenerated when intentional changes happen).

**Anti-seam:** `app.py` and `views/*`. Don't try to pytest these. Streamlit's testing story is improving (there's `st.testing.v1`) but it's not worth the time for a small app. Manual smoke-test the UI; rely on the engine tests for correctness.

---

## Integration Points

### External Services

None. This is the whole point. No DB, no auth, no external APIs. That's what makes Streamlit Cloud free-tier deployment trivial.

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `app.py` ↔ `engine/*` | Direct function calls returning new `GameState` | The four-function API: `new_game`, `advance_week`, `is_game_over`, `compute_debrief` |
| `app.py` ↔ `views/*` | Function calls passing state + callbacks | Views never touch `st.session_state` directly |
| `engine/*` ↔ `ai/*` | Engine constructs `StationView`, passes to `Agent.decide_order` | Agents are dependency-injected into `advance_week` |
| `views/*` ↔ `charts/*` | Views call `build_*(state)` to get a `go.Figure`, then `st.plotly_chart(fig)` | Charts never import streamlit |
| `engine/*` ↔ `config/*` | Engine reads constants/scenarios | Config is data only, no logic |

---

## Sources

- John Sterman, "Modeling Managerial Behavior: Misperceptions of Feedback in a Dynamic Decision Making Experiment," *Management Science*, 1989 — original heuristic formulation. [MIT dspace: Booms, Busts, and Beer](https://dspace.mit.edu/bitstream/handle/1721.1/121087/Sterman%20Beh%20Ops%20Handbook%20Chapter%20140210.pdf?sequence=1&isAllowed=y) — HIGH confidence on heuristic formula and α/β fitted values.
- MIT Sloan Beer Game documentation: [Flight Simulators for Management Education](https://web.mit.edu/jsterman/www/SDG/beergame.html) — HIGH confidence on tick sequence and rules.
- [Beer distribution game — Wikipedia](https://en.wikipedia.org/wiki/Beer_distribution_game) — corroborating overview.
- [A Mathematical Model of the Beer Game (JASSS, vol. 17 no. 4)](https://www.jasss.org/17/4/2.html) — HIGH confidence on the period-by-period operation order (receive → fill → record → order → ship).
- [Order Stability in Supply Chains (Sterman & Croson, MIT dspace)](https://dspace.mit.edu/bitstream/handle/1721.1/88134/Sterman_Order%20stability.pdf?sequence=1&isAllowed=y) — α, β, θ values for anchor-and-adjust.
- [Effect of Lead Time on Anchor-and-Adjust Ordering Policy (System Dynamics Society 2014)](https://proceedings.systemdynamics.org/2014/proceed/papers/P1061.pdf) — supply line weighting evidence.
- [Streamlit Session State docs](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state) — HIGH confidence on callback pattern.
- [Streamlit Button behavior & examples](https://docs.streamlit.io/develop/concepts/design/buttons) — HIGH confidence on `on_click` callbacks running before rerun.
- [Add statefulness to apps — Streamlit Docs](https://docs.streamlit.io/develop/concepts/architecture/session-state) — phase-routing pattern.

---
*Architecture research for: single-player Streamlit Beer Distribution Game simulator*
*Researched: 2026-05-18*
