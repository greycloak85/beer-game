# Phase 2: UI Shell + Per-Turn Play - Research

**Researched:** 2026-05-18
**Domain:** Streamlit 1.57.0 single-script app — `st.session_state` phase routing, `st.form` order entry, per-turn state machine over a frozen-dataclass engine
**Confidence:** HIGH

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SETUP-01 | Before the first game, the user sees a Rules + Bullwhip Primer screen explaining the 4-station chain, the order/shipping mechanics, and what the bullwhip effect is | `views/rules.py` rendered when `phase == "rules"`; "first-visit" tracked via `seen_rules` flag in `session_state` (Architecture Pattern 4). Pitfall 16 mandates this primer. |
| SETUP-02 | At game start, the user picks which of the four stations to play via a radio control | `views/setup.py` uses `st.radio` with options from `Role` enum, stored in `st.session_state.player_role`. |
| SETUP-03 | At game start, the user can optionally set the random seed; default is fixed (`DEFAULT_SEED=42`) | `views/setup.py` uses `st.number_input(value=DEFAULT_SEED, step=1)` for the seed; read by the `start_game` callback. |
| SETUP-04 | A "Start game" action transitions from setup to the first turn | `st.form_submit_button("Start game", on_click=start_game)` inside `views/setup.py`. Callback builds the `GameState`, creates per-role Sterman agents, sets `phase = "playing"`. |
| PLAY-01 | Each week, player sees inventory, backlog, last week's shipments received, last week's orders received, and an order-history mini-chart of their own past orders | `views/play.py` builds `StationView` via `build_station_view(state, player_role)`. Uses `st.metric` for the scalars; uses `st.plotly_chart` for the mini-chart sourced from the player's `orders_placed_history` (already on the state). |
| PLAY-02 | Order quantity entered via `st.number_input(min_value=0, step=1)` inside `st.form`, submitted via "Advance week" button | Canonical Streamlit form-callback pattern (see Code Examples §"Per-Turn Form"). |
| PLAY-03 | Player cannot see other stations or future demand | Enforced by the engine — `views/play.py` ONLY ever reads `build_station_view(state, player_role)`, never `state.stations[other_index]`. `RetailerView` is the only view exposing `customer_demand`; non-retailer views raise `AttributeError` on access (Phase 1 ENG-10). |
| PLAY-04 | Week counter shows current week / 36 | `st.write(f"Week {state.week + 1} of {state.total_weeks}")` — see "Week numbering" gotcha in Common Pitfalls. |
| PLAY-05 | After 36 weeks, transition automatically to debrief | `submit_order` callback inspects `is_game_over(new_state)` after `advance_week`; if true, sets `phase = "done"`. `views/debrief.py` is rendered as a placeholder in this phase (real Phase 3 content). |
</phase_requirements>

## Summary

Phase 2 is the first time Streamlit enters the codebase. The engine, agents, and config are pure-Python and pytest-verified (44/44, bullwhip = 2.000). The work is purely a thin rendering shell over the existing four-function API (`new_game`, `advance_week`, `is_game_over`, `build_station_view`). Streamlit 1.57.0 + Plotly 6.7.0 on Python 3.12 are already locked by project-level research. The canonical Streamlit pattern is single-file `app.py` as a phase-router, `st.session_state` as the only persistence layer, `st.form` to batch the per-week order input, and `on_click` callbacks (NOT inline mutation) to mutate state.

The single most important design decision is that **`beergame.engine.tick.advance_week` already accepts `player_order: int` as a direct parameter** — there is no need to wrap the player as a `OneShotAgent`. The player's submitted `st.number_input` value is passed verbatim through the form callback into `advance_week(state, player_order=value, ai_agents=non_player_agents)`. Three Sterman agents are constructed once at `start_game` time, persist in `st.session_state.ai_agents` across reruns (their `smoothed_demand` state lives on the agent instances), and are passed unchanged on every tick.

Two Streamlit 1.57.0 specifics are NOT in the project research files and matter for this phase: (1) `use_container_width=True` is deprecated and removed-after-2025-12-31 — the modern replacement is `width="stretch"`; the 1.57.0 changelog explicitly lists "Remove deprecated kwargs from `plotly_chart` and `vega_lite_chart`"; (2) inside a form, only `st.form_submit_button` can have an `on_click` callback, and callbacks must read submitted widget values via `st.session_state[key]` (NOT via `args=`, which captures the value at form-render time, not at submit time — a well-known footgun).

**Primary recommendation:** Single `app.py` router (~60 lines) dispatching to four view modules via `st.session_state.phase`. Each view exposes `render()` (no args — views read session_state directly is fine for this small app, OR pass state via kwargs for testability — both are canonical). Player's per-week order goes through a single `submit_order` callback bound to the form submit button; the callback reads `st.session_state["order_input"]`, calls `advance_week`, replaces `st.session_state.game`, and flips `phase` to `"done"` if week == 36.

## Standard Stack

### Core (already locked at the project level)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| streamlit | 1.57.0 | Single-file Python web framework — session state, widgets, routing | Locked by project research. Already targets Community Cloud free tier. |
| plotly | 6.7.0 | Order-history mini-chart in `play.py`; 4-panel debrief in Phase 3 | Locked by project research. `st.plotly_chart` is first-class. |
| Python | 3.12 | Runtime | Locked. Pinned in `.python-version` and `pyproject.toml`. |

### Supporting (NEW for Phase 2 — install with phase)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` (already in dev) | 8.x | UI smoke test via `streamlit.testing.v1.AppTest` (optional, see "Test Strategy") | Use for SETUP-04, PLAY-02, PLAY-05 transition assertions if scope permits. |

### Alternatives Considered

| Instead of | Could Use | Why we don't |
|------------|-----------|--------------|
| `st.form` for the order input | Plain `st.number_input` + `st.button` outside a form | Triggers a rerun on every keystroke (`1` then `12`) — wastes compute and risks widget-state bugs. Pitfall 12 in PITFALLS.md. |
| `st.session_state.phase = "playing"` router | Streamlit multipage `pages/` directory | Project research excluded multipage (one game flow). One state-machine `app.py` is the canonical pattern for our shape. |
| Per-rerun chart rebuild | `@st.fragment` around the order form | Unnecessary at this scale — entire script is ~50ms. Skip until measurable cost shows up (Phase 4 polish at earliest). |
| `OneShotAgent` wrapping player's order | Direct `advance_week(state, player_order=int_value, ai_agents=non_player)` | **Engine already takes `player_order: int` directly.** No wrapper needed. Cleaner — no new class in `ai/`. |

**No new installations needed.** Phase 2 adds files; `requirements.txt` is identical to Phase 1's planned deploy file.

## Architecture Patterns

### Recommended Project Structure (additive over Phase 1)

```
beergameNexStratus/
├── app.py                       # NEW — Streamlit entry point; only file that imports streamlit at top level
├── .streamlit/
│   └── config.toml              # NEW — page title, theme (defer Theming to Phase 4 if scope tight)
├── beergame/
│   ├── engine/   (Phase 1 — unchanged)
│   ├── ai/       (Phase 1 — unchanged)
│   ├── config/   (Phase 1 — unchanged)
│   └── views/                   # NEW — Streamlit-aware modules
│       ├── __init__.py
│       ├── setup.py             # render() — radio + seed + Start
│       ├── rules.py             # render() — primer screen
│       ├── play.py              # render() — per-turn view
│       └── debrief.py           # render() — PLACEHOLDER (real charts in Phase 3)
└── tests/
    └── test_app_smoke.py        # NEW — optional AppTest smoke (see "Test Strategy")
```

**Important — directory invariants from Phase 1:**

- `beergame/engine/`, `beergame/ai/`, `beergame/config/` **must remain free of `import streamlit`**. Phase 1 has an AST-walk pytest guard (`tests/test_no_streamlit_import.py`). Phase 2 must not regress this. All Streamlit imports live in `app.py` and `beergame/views/*.py`.
- `beergame/views/` is the FIRST place `import streamlit as st` appears.

### Pattern 1: Phase-Routed Streamlit Single-File App

**What:** `app.py` is a thin router. `st.session_state.phase` is a string flag in `{"rules", "setup", "playing", "done"}`. A top-level `if/elif/elif/elif` block calls exactly one view's `render()` per rerun.

**When to use:** Any multi-screen Streamlit app where the screens form a state machine. This is the canonical Streamlit pattern per their session-state docs.

**Example:**
```python
# Source: https://docs.streamlit.io/develop/concepts/architecture/session-state (canonical pattern)
# app.py
import streamlit as st

from beergame.engine.state import Role
from beergame.engine.tick import advance_week, is_game_over
from beergame.engine.state import new_game, build_station_view
from beergame.ai.sterman import ShipmentAnchorAndAdjustAgent
from beergame.config.scenarios import DEFAULT_SEED
from beergame.views import setup, rules, play, debrief

st.set_page_config(page_title="Beer Game", layout="centered")

# --- session_state init (runs every rerun; guard ensures it sets values only once) ---
def _init_session_state() -> None:
    if "phase" not in st.session_state:
        st.session_state.phase = "rules"          # first visit lands on rules
        st.session_state.seen_rules = False
        st.session_state.player_role = Role.RETAILER
        st.session_state.seed = DEFAULT_SEED
        st.session_state.game = None              # GameState | None
        st.session_state.ai_agents = None         # dict[Role, Agent] | None

# --- callbacks (mutate session_state; run BEFORE the rerun re-renders) ---
def go_to_setup() -> None:
    st.session_state.seen_rules = True
    st.session_state.phase = "setup"

def start_game() -> None:
    role = st.session_state.player_role        # already bound by widget key
    seed = int(st.session_state.seed)
    st.session_state.game = new_game(player_role=role, seed=seed)
    st.session_state.ai_agents = {
        r: ShipmentAnchorAndAdjustAgent()
        for r in Role if r != role
    }
    st.session_state.phase = "playing"

def submit_order() -> None:
    order_value = int(st.session_state.order_input)   # widget key, not args=
    new_state = advance_week(
        state=st.session_state.game,
        player_order=order_value,
        ai_agents=st.session_state.ai_agents,
    )
    st.session_state.game = new_state
    if is_game_over(new_state):
        st.session_state.phase = "done"

def reset_game() -> None:
    for key in ("phase", "seen_rules", "game", "ai_agents", "player_role", "seed"):
        st.session_state.pop(key, None)

_init_session_state()

# --- phase router ---
phase = st.session_state.phase
if phase == "rules":
    rules.render(on_continue=go_to_setup)
elif phase == "setup":
    setup.render(on_start=start_game)
elif phase == "playing":
    play.render(state=st.session_state.game, on_submit=submit_order)
elif phase == "done":
    debrief.render(state=st.session_state.game, on_reset=reset_game)
else:
    st.error(f"Unknown phase: {phase!r}")
```

### Pattern 2: Form-Batched Order Entry with Callback (PLAY-02)

**What:** Wrap `st.number_input` + `st.form_submit_button` in `st.form`. The submit button has `on_click=submit_order`. The callback reads the just-submitted value via `st.session_state["order_input"]` (NOT via `args=`).

**When to use:** Any "submit a form to advance the game state" pattern — exactly our per-week loop.

**Why `st.session_state[key]` and not `args=value`:** Per Streamlit docs and the well-known footgun: at the time `st.form(...)` renders the submit button, the widget value is the *previous* value (form widgets defer their state updates until submit). If you write `on_click=submit_order, args=(order,)`, the callback receives the OLD value. Reading `st.session_state["order_input"]` inside the callback returns the NEW (just-submitted) value because callbacks run *after* form submission and *before* the next script rerun.

**Example:**
```python
# Source: https://docs.streamlit.io/develop/concepts/architecture/forms (verbatim pattern)
# views/play.py
import streamlit as st
import plotly.graph_objects as go
from beergame.engine.state import GameState, build_station_view

def render(state: GameState, on_submit) -> None:
    view = build_station_view(state, state.player_role)
    st.subheader(f"You are: {state.player_role.name.title()}")
    st.write(f"**Week {state.week + 1} of {state.total_weeks}**")  # week is 0-indexed in state

    # Read-only info panel — only this player's view.
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Inventory", view.inventory)
        st.metric("Backlog", view.backlog)
    with col2:
        st.metric("Last shipment received",
                  state.stations[state.player_role.value].incoming_shipments[0] if False else
                  _last_shipment_received(state))
        st.metric("Last order received from downstream", view.last_order_received)

    # Order-history mini-chart (player's own placed orders only).
    _render_mini_chart(state)

    # Per-week form.
    with st.form("turn_form", clear_on_submit=True):
        st.number_input(
            "Your order this week",
            min_value=0,
            step=1,
            value=4,            # default to equilibrium throughput
            key="order_input",  # CRITICAL — callback reads via this key
        )
        st.form_submit_button("Advance week", on_click=on_submit)
```

**Critical:** `clear_on_submit=True` resets the input back to `value=4` between weeks, so the player consciously decides each week. Without it, the previous order is pre-filled — minor pedagogical loss.

### Pattern 3: Engine Boundary Preserved — Views Never Mutate

**What:** Views read `GameState` and call back into `app.py` via passed-in callbacks. They never call `advance_week` directly, never touch `st.session_state.game` directly.

**Why:** Keeps `app.py` as the single place where game state mutates. Makes views nominally testable (you can call `render(state, on_submit=Mock())`). Mirrors the engine's "advance returns new state" purity at the UI layer.

**Anti-pattern to avoid:** Views directly calling `st.session_state.game = advance_week(...)` from inside a button click. Works, but spreads mutation across modules. Stay disciplined.

### Pattern 4: First-Visit Rules Routing

**What:** On first session, `phase` is initialized to `"rules"` (not `"setup"`). The rules screen has a "Got it, set up my game" button (`on_click=go_to_setup`) that flips `seen_rules=True` and `phase="setup"`. After that, the rules screen is reachable only via an explicit "Help" link (defer to Phase 4 polish).

**Why this order (rules → setup → playing → done):**
- Pitfall 16 (PITFALLS.md): "Player jumps in cold, places orders for 36 weeks, sees four charts in the debrief — has no idea what to look for."
- Reading rules before picking a station is pedagogically correct: the player learns the chain structure before choosing their position.
- The "back to setup" button on the rules screen handles the (rare) case where the player wants to re-read rules before locking in their station choice.

**Open question:** Whether to show rules BEFORE or AFTER station selection. Recommendation: **rules first.** The rules screen explains "you'll play ONE of these four stations" — informed station choice requires understanding the chain first.

### Anti-Patterns to Avoid

- **`import streamlit` in `beergame/engine/` or `beergame/ai/`.** Will break the Phase 1 AST-walk pytest guard (`tests/test_no_streamlit_import.py`). All Streamlit imports must be in `app.py` or `beergame/views/`.
- **Mutating `st.session_state` from inline script body after a widget renders.** Streamlit raises `StreamlitAPIException: cannot be modified after the widget with key '...' was instantiated`. Pitfall 9. Always mutate via `on_click` / `on_change` callbacks.
- **Reading a widget value from `args=(value,)` on a form submit button.** Captures the OLD value at render time, not the submitted value. Read via `st.session_state[key]` inside the callback.
- **Caching the game state with `@st.cache_data`.** Trap: same inputs → same output, but caching the *whole game* by hash defeats the entire per-tick model. Don't cache anything in Phase 2.
- **Putting `time.sleep()` anywhere in `app.py`.** Streamlit's rerun model fights it. No animations.
- **Re-running the simulation from scratch each tick.** The engine is incremental; one click = one `advance_week` call.
- **Exposing other stations' state in any view.** PLAY-03 + Pitfall 17. `views/play.py` only ever reads `build_station_view(state, state.player_role)`. Confirmed at the engine level: non-Retailer views raise `AttributeError` on `customer_demand` access (ENG-10 verified).
- **Showing future customer demand on any chart axis.** Pitfall 18. The mini-chart's x-axis extends only to `state.week` (i.e., weeks completed so far), never to 36.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Phase routing across screens | A custom dispatcher class with `register()` decorators | A flat `if phase == "...": view.render()` block in `app.py` | At 4 phases, indirection costs more than it saves. Canonical Streamlit pattern. |
| Per-key keystroke debouncing on `st.number_input` | A custom debounce wrapper or `on_change` throttle | `st.form` — by design batches all widget changes to a single submit | `st.form` is purpose-built. Pitfall 12. |
| Tracking "have I shown rules before?" cookie/localStorage | Set up `streamlit-cookies-controller` or query-param hacks | A `seen_rules: bool` in `st.session_state` | In-session-only is a stated project constraint (no DB, no auth, no persistence across refreshes). A page refresh resets cleanly — that's intentional. |
| "Player as Agent" wrapper to call `advance_week` uniformly | `OneShotAgent(qty)` class injected into `ai_agents` | Pass `player_order=int_value` directly to `advance_week` | `advance_week(state, player_order: int, ai_agents: dict[Role, Agent])` already separates the two. Adding a wrapper layer in `ai/` is more complexity for zero gain. |
| Custom Plotly mini-chart "don't flicker" wrapper | A `@st.cache_resource` builder + key-stabilization hack | Pass `key="orders_history_chart"` to `st.plotly_chart` for a stable element identity, and accept that small per-rerun re-renders are fine at our data size (≤36 points) | Verified against Streamlit 1.57 docs: `key` parameter is the canonical stability lever. Plotly flicker (Pitfall 10) is real for big interactive charts; a 150px line of 1-36 ints isn't large enough to flicker noticeably. |
| Custom widget for the rules screen's supply-chain diagram | An SVG, Lottie, or `streamlit-extras` flowchart | A static PNG/SVG asset OR pure-markdown ASCII diagram + `st.markdown` | One-time visual. Adding a custom component to ship more JS to Cloud Cold Start (Pitfall 14) is bad ROI. Use markdown + an inline SVG/ASCII chain. |
| File path resolution for any asset (rules screen image, etc.) | `open("assets/diagram.png")` (cwd-relative) | `Path(__file__).parent / "assets" / "diagram.png"` | Pitfall 15 — relative paths break on Streamlit Cloud. Apply preemptively even though Phase 2 has no certain asset loads. |

**Key insight:** Phase 2's work is overwhelmingly *calling well-known Streamlit APIs in the canonical order*. Resist the urge to abstract — three callbacks (`go_to_setup`, `start_game`, `submit_order`, `reset_game`) and four view modules will be ~150 lines of code total.

## Common Pitfalls

These are the Phase 2 specific risks. Phase 1 engine pitfalls (1–7) are already mitigated by the verified Phase 1 deliverables.

### Pitfall 1: `session_state` initialized in the script body instead of inside a guard

**What goes wrong:** `st.session_state.phase = "rules"` at the top of `app.py` resets `phase` on every rerun. Click "Start game" → callback flips phase to `"playing"` → rerun → top-of-script line clobbers it back to `"rules"`. App appears frozen on the rules screen.

**Why it happens:** Newcomer error. Streamlit's rerun-everything model is unintuitive.

**How to avoid:** Wrap every `session_state` initial assignment in an `if "key" not in st.session_state` guard. Use `_init_session_state()` helper for cleanliness (see Code Examples).

**Warning signs:** Phase doesn't transition after a button click. Counter always shows week 1. Test: add a `print(f"phase={st.session_state.phase}")` at the top of `app.py` and click around — should change after each callback.

### Pitfall 2: Reading widget value via `args=` instead of `st.session_state[key]`

**What goes wrong:** `st.form_submit_button("Advance", on_click=submit_order, args=(order,))` passes the *previous-render* value of the number input, not the just-submitted value. The player types "8" and submits, but `advance_week` sees the default `4`. Bullwhip won't form correctly because the player's orders never reach the upstream agents.

**Why it happens:** Looks idiomatic; `args` works for regular `st.button` outside a form. Inside `st.form`, widget values batch on submit but `args` is evaluated at form render time, before the user types.

**How to avoid:** Always read submitted values via `st.session_state[widget_key]` inside the callback. Never pass form-internal widget values through `args`.

**Warning signs:** Order placed != order entered, off-by-one rerun behavior, player's `orders_placed_history` doesn't match what they typed.

### Pitfall 3: Mini-chart flickers on every "Advance week"

**What goes wrong:** Plotly chart remounts on each rerun. Pitfall 10 in PITFALLS.md.

**Why it happens:** `st.plotly_chart(build_figure(state))` returns a fresh `go.Figure` object each rerun; Streamlit can't tell it's the same chart.

**How to avoid:** Pass a stable `key` to `st.plotly_chart`: `st.plotly_chart(fig, key="player_orders_history", width="stretch")`. For our data size (≤36 ints) flicker is unlikely to be visible, but `key` is the canonical stability lever.

**Warning signs:** Visible flash on each click. Verified in 1.57 docs: `key` parameter exists and is documented as providing "a stable identity."

### Pitfall 4: `use_container_width=True` raises a deprecation warning (and will break in a future minor)

**What goes wrong:** `st.plotly_chart(fig, use_container_width=True)` — the API we'd reach for from training data and Stack Overflow snippets — is deprecated as of late 2025 and the 1.57.0 changelog lists "Remove deprecated kwargs from `plotly_chart` and `vega_lite_chart`."

**Why it happens:** Pre-2026 examples everywhere. Training data is stale.

**How to avoid:** Use `width="stretch"` instead. New signature: `st.plotly_chart(fig, width="stretch", key="...")`. For a fixed-pixel small chart, use `width=<pixels>` and `height=<pixels>`.

**Warning signs:** Deprecation warning in app logs, or worse, a hard error after a Cloud auto-upgrade.

**Source:** Streamlit 1.57.0 release notes (GitHub releases) — "Remove deprecated kwargs from `plotly_chart` and `vega_lite_chart`."

### Pitfall 5: Number input accepts negative or floating-point values

**What goes wrong:** Player enters `-5` or `4.5`. `advance_week` receives an int after `max(0, int(player_order))` is applied (engine defends), but the UX is confusing.

**How to avoid:** `st.number_input("...", min_value=0, step=1, value=4)`. `min_value=0` blocks negatives at the UI; `step=1` blocks floats. No `max_value` — PLAY-02 explicitly forbids artificial upper caps because the canonical bullwhip can drive Factory orders to 30–80+.

**Warning signs:** Player types `-1`, app says "Value must be >= 0" — that's the intended behavior, not a bug.

### Pitfall 6: Week counter shows `state.week` but `state.week` is 0-indexed

**What goes wrong:** `state.week` starts at 0 (Phase 1 `new_game` sets `week=0` initially). After the first `advance_week`, `state.week == 1`. PLAY-04 wants "Week N of 36" — the player sees "Week 0 of 36" before placing their first order.

**How to avoid:** Display `state.week + 1` BEFORE the order form (i.e., "you are now planning week 1 of 36"). After 36 ticks `state.week == 36`, the post-final-tick rerun sets `phase = "done"` and `views/play.py` is never re-rendered for week 36 — the debrief takes over. Confirm via `is_game_over(state)` which returns `state.phase == "done"` (set by `advance_pipelines` when `next_week >= total_weeks`).

**Warning signs:** First visible week shows 0; last playable week shows 35.

### Pitfall 7: Refresh of the browser doesn't reset cleanly

**What goes wrong:** Streamlit Cloud occasionally persists `session_state` across same-tab refreshes (depending on browser/cookie state). The success criterion explicitly requires "page refresh resets cleanly."

**How to avoid:** This is largely Streamlit's default — `session_state` IS reset on a hard reload (Ctrl+Shift+R) and in incognito tabs. Soft refresh (F5) may or may not. **No code change needed**, but test the success criterion explicitly: open in browser, play 5 weeks, F5, confirm app is back on rules screen.

**Warning signs:** Refresh keeps the player on week N — would indicate a Cloud-side session persistence we don't want. Report and investigate; do not paper over with manual `del st.session_state[...]` calls.

### Pitfall 8: Sterman agents lose their `smoothed_demand` state across reruns

**What goes wrong:** `ShipmentAnchorAndAdjustAgent` is a dataclass with `smoothed_demand: float = field(default=4.0)`. Its forecasting state lives on the instance. If `start_game()` re-instantiates the agents on every rerun, they reset to `smoothed_demand=4.0` each week — bullwhip flattens.

**Why it happens:** The agent dict in `st.session_state.ai_agents` must be created ONCE in `start_game` and never overwritten until `reset_game`.

**How to avoid:** Construct `ai_agents` once in `start_game()`, store in `st.session_state.ai_agents`, never re-create. The `submit_order` callback passes the same dict to `advance_week` each tick. `advance_week` will mutate each agent's `smoothed_demand` (the dataclass is NOT frozen, only mutable in this single attribute — verified `sterman.py:24` uses `@dataclass`, no `frozen=True`).

**Warning signs:** Bullwhip ratio in Phase 2 play differs noticeably from Phase 1's verified 2.0000 under same seed. Run a comparison: simulate via UI playthrough at default seed, then run `tests/test_bullwhip_emerges.py` and confirm the histories match.

### Pitfall 9: Top-level `import` of `pyplot` or heavy module slows cold start

**What goes wrong:** Streamlit Cloud cold-start is 20–40s on free tier. Heavy imports at top of `app.py` (e.g., `import pandas`, `import numpy` for "convenience") add seconds.

**How to avoid:** Stick to the locked stack — `import streamlit as st`, `import plotly.graph_objects as go`, plus our `beergame.*` modules (all pure-Python stdlib internally). No pandas, no numpy. (Already a Phase 1 invariant, but re-verify in Phase 2 PR review.)

**Warning signs:** First click after a 12-hour Cloud sleep takes >60s. Run `python -X importtime app.py` locally to spot heavy imports.

### Pitfall 10: Debrief view called before game is actually done

**What goes wrong:** Race condition — `submit_order` callback flips `phase` to `"done"` only AFTER `advance_week`. If a developer adds a button outside the form (e.g., a "Skip to debrief" debug button), it could land at `phase == "done"` with `state.week < 36`. `views/debrief.py` then crashes or shows incorrect data.

**How to avoid:** In Phase 2, `views/debrief.py` is a placeholder ("Game complete! Charts coming in Phase 3.") — it doesn't read history beyond `state.week`. Add an assertion `assert is_game_over(state)` at the top of `debrief.render()` for safety.

**Warning signs:** Debrief shows "Week 36 of 36" before the player has submitted week 36 — means `phase` is being set prematurely.

## Code Examples

### Example 1: Full `app.py` Skeleton

```python
# Source: synthesized from Streamlit official session-state docs +
# https://docs.streamlit.io/develop/concepts/architecture/session-state
# https://docs.streamlit.io/develop/concepts/architecture/forms
import streamlit as st

from beergame.ai.sterman import ShipmentAnchorAndAdjustAgent
from beergame.config.scenarios import DEFAULT_SEED
from beergame.engine.state import Role, new_game
from beergame.engine.tick import advance_week, is_game_over
from beergame.views import debrief, play, rules, setup

st.set_page_config(page_title="Beer Game", page_icon=":beer:", layout="centered")


def _init_session_state() -> None:
    if "phase" not in st.session_state:
        st.session_state.phase = "rules"
        st.session_state.seen_rules = False
        st.session_state.player_role = Role.RETAILER
        st.session_state.seed = DEFAULT_SEED
        st.session_state.game = None
        st.session_state.ai_agents = None


def go_to_setup() -> None:
    st.session_state.seen_rules = True
    st.session_state.phase = "setup"


def start_game() -> None:
    role = st.session_state.player_role
    seed = int(st.session_state.seed)
    st.session_state.game = new_game(player_role=role, seed=seed)
    st.session_state.ai_agents = {
        r: ShipmentAnchorAndAdjustAgent() for r in Role if r != role
    }
    st.session_state.phase = "playing"


def submit_order() -> None:
    order_value = int(st.session_state.order_input)
    new_state = advance_week(
        state=st.session_state.game,
        player_order=order_value,
        ai_agents=st.session_state.ai_agents,
    )
    st.session_state.game = new_state
    if is_game_over(new_state):
        st.session_state.phase = "done"


def reset_game() -> None:
    for key in ("phase", "seen_rules", "player_role", "seed", "game", "ai_agents"):
        st.session_state.pop(key, None)


_init_session_state()

phase = st.session_state.phase
if phase == "rules":
    rules.render(on_continue=go_to_setup)
elif phase == "setup":
    setup.render(on_start=start_game)
elif phase == "playing":
    play.render(state=st.session_state.game, on_submit=submit_order)
elif phase == "done":
    debrief.render(state=st.session_state.game, on_reset=reset_game)
else:
    st.error(f"Unknown phase: {phase!r}")
```

### Example 2: `views/setup.py`

```python
# views/setup.py
import streamlit as st
from beergame.engine.state import Role
from beergame.config.scenarios import DEFAULT_SEED


def render(on_start) -> None:
    st.title(":beer: Beer Game — Setup")
    st.write("Pick a station to play. You'll see only that station's view during the game.")

    with st.form("setup_form"):
        st.radio(
            "Your station",
            options=list(Role),
            format_func=lambda r: r.name.title(),
            key="player_role",
            horizontal=True,
        )
        st.number_input(
            "Random seed (advanced — leave as default for the canonical run)",
            min_value=0,
            step=1,
            value=DEFAULT_SEED,
            key="seed",
        )
        st.form_submit_button("Start game", on_click=on_start)
```

### Example 3: `views/play.py`

```python
# views/play.py
import plotly.graph_objects as go
import streamlit as st

from beergame.engine.state import GameState, build_station_view


def render(state: GameState, on_submit) -> None:
    role = state.player_role
    view = build_station_view(state, role)
    me = state.stations[role.value]

    st.title(f":beer: Week {state.week + 1} of {state.total_weeks} — You are the {role.name.title()}")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Inventory on hand", view.inventory)
        st.metric("Backlog", view.backlog)
    with col2:
        # "Last week's shipments received" = the units that just arrived (step 1 of last tick).
        # On the post-tick state we just rendered, that's already folded into inventory; we expose
        # the back-slot of the SHIPPED history as a proxy. NOTE: this is the most recent value the
        # player observed; PLAY-01 wants this surfaced.
        last_shipment_received = me.shipments_sent_history[-1] if me.shipments_sent_history else 0
        # Actually for the PLAYER's "shipments received" we need orders_received history? No -
        # PLAY-01 says "shipments RECEIVED" which is incoming_shipments arrivals. The cleanest
        # surface for the planner is to add a tiny helper to engine if needed; for now derive
        # from history.  [PLANNER: validate this — see Open Question 1]
        st.metric("Last shipment received", last_shipment_received)
        st.metric("Last order from downstream", view.last_order_received)

    # Order-history mini-chart — player's own placed orders only.
    if me.orders_placed_history:
        fig = go.Figure()
        weeks = list(range(1, len(me.orders_placed_history) + 1))
        fig.add_trace(go.Scatter(
            x=weeks,
            y=list(me.orders_placed_history),
            mode="lines+markers",
            name="Your orders",
        ))
        fig.update_layout(
            height=180,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_title="Week",
            yaxis_title="Order qty",
            showlegend=False,
        )
        st.plotly_chart(fig, key="player_order_history", width="stretch")
    else:
        st.caption("Your order history chart will appear after your first order.")

    # Per-week order form.
    with st.form("turn_form", clear_on_submit=True):
        st.number_input(
            "Your order this week",
            min_value=0,
            step=1,
            value=4,
            key="order_input",
        )
        st.form_submit_button("Advance week", on_click=on_submit)
```

**Note for planner:** The "Last shipment received" derivation needs validation. The engine's `StationView` exposes `inventory`, `backlog`, `supply_line`, `last_order_received`, `recent_orders_received` — it does NOT currently expose "last shipment received." Two options for the planner:

1. **Cheap (recommended):** Derive in `play.py` from the station's history tuples directly. The player's `shipments_sent_history[-1]` is what they sent downstream (wrong); the units they *received* are the front slot of `incoming_shipments` from one tick ago, which is no longer in state (consumed in step 1 of the same tick). The cleanest derivation is: the last week's inventory delta, or expose a new history field `shipments_received_history` in the engine.
2. **Cleaner (small Phase 1 engine extension):** Add `shipments_received_history: tuple[int, ...]` to `StationState`, appended in `record_state` (step 3) from `arriving = incoming_shipments[0]` snapshotted in step 1. Surface it on `StationView` as `last_shipment_received: int`. This is a small, additive change that strictly improves API symmetry. **Recommend the planner consult the user on this — it's a tiny scope tweak that makes PLAY-01 verbatim-satisfiable.**

### Example 4: `views/rules.py`

```python
# views/rules.py
import streamlit as st


_PRIMER_MD = """
## The Beer Game in 60 seconds

You're one of **4 stations** in a beer supply chain:

```
Customer  ←  Retailer  ←  Wholesaler  ←  Distributor  ←  Factory
                          (orders flow this way → → → → → →)
                          (← ← ← ← ← shipments flow this way)
```

Each week, every station:

1. **Receives** the shipment that was sent 2 weeks ago.
2. **Fills** the order that arrived 1 week ago (ships from inventory; unfilled becomes backlog).
3. **Places one new order** to its upstream neighbor — *this is your only decision*.

You see only YOUR station's view: your inventory, your backlog, the last shipment you got, the
last order from your downstream neighbor. You do NOT see other stations or future demand.

### Costs

- Holding inventory: **$0.50** per case per week.
- Backlog (unfilled orders): **$1.00** per case per week.

### What is the "bullwhip effect"?

When customer demand changes slightly, orders **amplify** as they travel upstream. The Factory
ends up swinging 2–4× harder than the Retailer faced — even when every player is rational.
You're about to see why.

Your job: try to keep inventory near 12 and avoid both stockouts (backlog) and pile-ups.
36 weeks. One decision per week. Good luck.
"""


def render(on_continue) -> None:
    st.title(":beer: Beer Game — Rules")
    st.markdown(_PRIMER_MD)
    st.button("Got it — set up my game", on_click=on_continue, type="primary")
```

### Example 5: `views/debrief.py` (placeholder — real charts in Phase 3)

```python
# views/debrief.py
import streamlit as st
from beergame.engine.state import GameState
from beergame.engine.tick import is_game_over


def render(state: GameState, on_reset) -> None:
    assert is_game_over(state), f"Debrief called with phase={state.phase!r} (week={state.week})"

    st.title(":beer: Game complete!")
    st.write(f"You played the **{state.player_role.name.title()}** through 36 weeks.")
    st.info("Charts and narrative debrief are coming in Phase 3.")

    # Minimal sanity data for the placeholder.
    me = state.stations[state.player_role.value]
    st.metric("Your total orders placed", sum(me.orders_placed_history))
    st.metric("Final inventory", me.inventory)
    st.metric("Final backlog", me.backlog)
    st.metric("Final cumulative cost", f"${me.cost_history[-1]:.2f}" if me.cost_history else "$0.00")

    st.button("Play again", on_click=on_reset, type="primary")
```

### Example 6: Optional `.streamlit/config.toml`

```toml
# .streamlit/config.toml
[theme]
base = "light"
primaryColor = "#7B3F00"  # amber/beer color

[server]
headless = true            # for local CLI / containers; CC sets its own
```

**Defer non-essential theming to Phase 4.** A minimal `config.toml` is fine; the project doesn't ship one yet.

### Example 7: Optional AppTest Smoke Test

```python
# tests/test_app_smoke.py
"""Optional Phase 2 smoke test via streamlit.testing.v1.AppTest.

This is a SOFT requirement — manual smoke test (playing through in browser) is
the primary verification. AppTest checks are nice-to-have for CI.
"""
from streamlit.testing.v1 import AppTest


def test_first_visit_lands_on_rules():
    at = AppTest.from_file("app.py", default_timeout=5)
    at.run()
    assert at.session_state.phase == "rules"
    assert at.session_state.seen_rules is False


def test_rules_continue_goes_to_setup():
    at = AppTest.from_file("app.py").run()
    at.button[0].click()  # "Got it — set up my game"
    at.run()
    assert at.session_state.phase == "setup"


def test_start_game_transitions_to_playing():
    at = AppTest.from_file("app.py").run()
    at.button[0].click()  # to setup
    at.run()
    # In setup form: radio[0] defaults to Retailer; submit
    at.form[0].number_input[0].set_value(42)  # seed
    at.form[0].submit_button[0].click()
    at.run()
    assert at.session_state.phase == "playing"
    assert at.session_state.game is not None
    assert at.session_state.game.week == 0


def test_submit_order_advances_one_week():
    at = AppTest.from_file("app.py").run()
    at.button[0].click(); at.run()  # rules -> setup
    at.form[0].submit_button[0].click(); at.run()  # setup -> playing
    at.form[0].number_input[0].set_value(4)  # order
    at.form[0].submit_button[0].click()
    at.run()
    assert at.session_state.game.week == 1
```

**Caveat (LOW confidence):** `AppTest` widget indexing (`at.button[0]`, `at.form[0].number_input[0]`) is brittle — order is by render order, which couples tests to view layout. If we adopt AppTest, prefer the keyed-access variant: `at.number_input(key="order_input").set_value(4)` and `at.form_submit_button(key="...").click()` (if form keys can be set). See "Open Questions" #3.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `st.plotly_chart(fig, use_container_width=True)` | `st.plotly_chart(fig, width="stretch")` | 1.50.0 introduced `width=`; 1.57.0 removed deprecated kwargs | Hard error after 2025-12-31 grace period. Use `width="stretch"` from day one. |
| `st.experimental_rerun()` | `st.rerun()` | Renamed in 1.27 (2023); experimental name removed | Use stable name. We don't need explicit reruns in Phase 2 (callbacks already trigger them). |
| `st.experimental_fragment` | `@st.fragment` | Stabilized in 1.36 (2024) | Not used in Phase 2 (defer to Phase 4 polish if needed). |
| `@st.cache` (legacy) | `@st.cache_data` / `@st.cache_resource` | Deprecated since 1.18 (2023) | Not used in Phase 2. Don't cache `advance_week`. |
| Tests via `subprocess` + Selenium | `streamlit.testing.v1.AppTest` | Stabilized in 1.28+ (2024) | Optional Phase 2 use; primary verification remains manual smoke test. |
| `st.session_state["k"]` with widget-key conflicts | Same — guard with `if "k" not in st.session_state` | Pattern unchanged since `session_state` GA in 1.10 (2022) | Canonical idiom; no `setdefault` shorthand. |

**Deprecated/outdated:**
- `use_container_width` parameter: removed-after grace period for `st.plotly_chart` in 1.57.0. Use `width="stretch"`.
- Variable `**kwargs` for Plotly config on `st.plotly_chart`: deprecated in 1.52, removed in 1.57. Use the explicit `config=` parameter instead.

## Open Questions

1. **Add `shipments_received_history` to engine?**
   - What we know: PLAY-01 requires displaying "last week's shipments received." Phase 1's `StationView` exposes `last_order_received` but NOT `last_shipment_received`. The data is computable from history (delta of inventory minus net production), but exposing it as a first-class field is cleaner.
   - What's unclear: Is this an in-scope Phase 2 engine extension, or should the planner derive in `views/play.py`?
   - Recommendation: **Small additive engine change** — add `shipments_received_history: tuple[int, ...]` to `StationState`, append in `record_state` (step 3) the value snapshotted at the top of `receive_shipments` (step 1). Surface as `last_shipment_received: int` on `StationView`. ~10-line change, fully testable in Phase 1 style. **Planner: get user sign-off if this is acceptable; otherwise plan derivation in `views/play.py`.**

2. **Rules screen ordering: before or after setup?**
   - What we know: Both options satisfy SETUP-01 (rules shown on first visit). Pitfall 16 says "primer before they play."
   - What's unclear: User preference. Pedagogical argument favors rules-first; UX argument might favor setup-first (faster path to play for repeat users).
   - Recommendation: **Rules first** for v1 (`phase` starts at `"rules"`). After click-through, `seen_rules=True` and `phase=="setup"`. On second visit within a session (impossible currently — refresh resets), we'd skip rules; defer that polish to Phase 4.

3. **`streamlit.testing.v1.AppTest` for automated verification — in or out of scope?**
   - What we know: The API is stable and supports forms, buttons, session_state introspection. PROJECT.md emphasizes manual smoke testing as the primary verification.
   - What's unclear: Is the planner expected to write AppTest coverage, or only manual smoke?
   - Recommendation: **Out of scope for primary verification; nice-to-have if time permits.** Add `tests/test_app_smoke.py` as a "soft" task with 4 simple transition assertions (rules→setup→playing→after-week-1). Don't gate the phase on these. Manual playthrough is the success criterion.

4. **"Advance week" inside the form vs. outside?**
   - What we know: PLAY-02 specifies "`st.number_input` inside `st.form` + 'Advance week' button." Inside-the-form is the canonical pattern (Pitfall 12 mandates form for keystroke-rerun avoidance).
   - What's unclear: Whether the submit button counts as "inside the form."
   - Recommendation: **Inside the form** — use `st.form_submit_button("Advance week", on_click=submit_order)`. This is the only widget kind that *can* have a callback inside a form (verified against Streamlit forms docs). Don't put a separate `st.button` outside.

5. **Show the player's own incoming-shipments pipeline (the "supply line they own") mid-game?**
   - What we know: The `StationView.supply_line` field is the sum of incoming shipments — this is info the player owns. The Sterman heuristic itself weights it (β-term).
   - What's unclear: Whether displaying it goes beyond PLAY-01's spec.
   - Recommendation: **Show it.** Add a fourth metric: "Units in transit to you (supply line)" = `view.supply_line`. The player owns this info and Sterman's whole insight is that humans *underweight* it. Surfacing it lets the player play better; the bullwhip still emerges because Sterman AI opponents still underweight theirs. This is information visibility (PLAY-03) respected — only the player's own data.

6. **Plotly mini-chart vs. `st.line_chart` native?**
   - What we know: `st.line_chart` works for a single series with minimal config. Plotly is heavier but more controllable.
   - What's unclear: Whether using Plotly here (mini-chart, 1-36 ints) is worth the import cost / consistency vs. native chart.
   - Recommendation: **Plotly** — keeps the chart toolkit consistent with Phase 3's debrief, which is Plotly. Cold-start cost is one-time. The 180px-height styling is easier in Plotly than `st.line_chart`.

## Sources

### Primary (HIGH confidence)

- [Streamlit Session State docs](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state) — canonical `if "k" not in st.session_state` guard pattern; field-based API.
- [Streamlit Forms docs](https://docs.streamlit.io/develop/concepts/architecture/forms) — verbatim "do not pass values to the callback directly through `args` or `kwargs`; assign a key and read from `st.session_state` inside the callback."
- [Streamlit Add statefulness to apps](https://docs.streamlit.io/develop/concepts/architecture/session-state) — callback semantics: "callbacks are executed as a prefix to the script rerunning."
- [st.fragment docs](https://docs.streamlit.io/develop/api-reference/execution-flow/st.fragment) — fragment-vs-full-rerun semantics; safe to mutate session_state from inside.
- [st.plotly_chart docs](https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart) — current signature: `width` accepts `"stretch"` / `"content"` / int; `key` parameter for stable identity.
- [streamlit.testing.v1.AppTest docs](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest) — official testing API; `from_file()` + widget-by-index access; supports forms and submit buttons.
- [Streamlit GitHub Releases](https://github.com/streamlit/streamlit/releases) — 1.57.0 changelog: "Remove deprecated kwargs from `plotly_chart` and `vega_lite_chart`"; "Add pills, segmented_control properties and dataframe key to AppTest."
- Phase 1 deliverables (verified at this repo) — `beergame/engine/state.py`, `tick.py`, `demand.py`, `ai/sterman.py`, `ai/base.py`. The `advance_week(state, player_order: int, ai_agents: dict[Role, Agent])` signature is the API Phase 2 consumes.
- [.planning/research/SUMMARY.md](../../../research/SUMMARY.md), [STACK.md](../../../research/STACK.md), [ARCHITECTURE.md](../../../research/ARCHITECTURE.md), [PITFALLS.md](../../../research/PITFALLS.md) — project-level synthesis with HIGH confidence on stack and patterns.

### Secondary (MEDIUM confidence)

- [Streamlit 2025 release notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2025) — historical `width=` parameter rollout across chart components.
- [Streamlit discuss — use_container_width deprecation](https://discuss.streamlit.io/t/cursorrules-for-deprecated-use-container-width/119576) — deprecation warning text and migration path.
- [Streamlit discuss — Plotly flicker (issue #8782)](https://github.com/streamlit/streamlit/issues/8782) — confirmed flicker reports post-1.35.0; partial resolution via `key=` parameter.

### Tertiary (LOW confidence — flagged for validation)

- Third-party blogs claiming `width="content"` is the replacement for `use_container_width=True` — contradicted by official docs (which say `width="stretch"` is the replacement; `"content"` is for content-sized charts). **Trust the official docs.**
- Specific 1.57.0 release-note text not directly readable from the 2026 release-notes URL (it caps at 1.56.0 in the docs render); inferred from GitHub releases page. Re-verify before code review.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Streamlit 1.57.0 + Plotly 6.7.0 + Python 3.12 already locked in project research and Phase 1 deploy plan.
- Architecture: HIGH — phase routing + callbacks pattern is canonical Streamlit, verified against official docs.
- Engine API: HIGH — `advance_week(state, player_order: int, ai_agents)` signature is directly read from `beergame/engine/tick.py` lines 253-270 of the verified Phase 1 code.
- Pitfalls: HIGH — Phase-2-specific pitfalls 8–18 from PITFALLS.md plus 1.57.0-specific deprecations cross-verified against Streamlit GitHub releases.
- AppTest scope: MEDIUM — API exists and is stable; precise widget-indexing semantics may need adjustment in code review.
- "Show last shipment received" derivation: MEDIUM — engine extension recommended; planner needs user sign-off.

**Research date:** 2026-05-18
**Valid until:** ~2026-08-18 (90 days; Streamlit minor releases happen monthly so re-verify if Phase 2 stalls past mid-August). Note specifically: `use_container_width` may break harder in 1.58+ — track the next release.
