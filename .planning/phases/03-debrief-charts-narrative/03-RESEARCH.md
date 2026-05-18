# Phase 3: Debrief Charts + Narrative — Research

**Researched:** 2026-05-18
**Domain:** Streamlit + Plotly post-game debrief view; bullwhip amplification math; per-station cost decomposition; station-aware narrative copy
**Confidence:** HIGH (stack, Plotly subplot API, statistics module, project conventions all verified against project artifacts and current docs)

---

<phase_requirements>
## Phase Requirements

These six requirement IDs are in scope and MUST be addressed by Phase 3 plans.

| ID | Description (from REQUIREMENTS.md) | Research Support |
|----|------------------------------------|------------------|
| DEB-01 | 4-panel chart (one per station) with shared weeks x-axis plotting orders placed and inventory level over the full game | "Standard Stack" — Plotly 6.7 `make_subplots(rows=4, cols=1, shared_xaxes=True)`; "Architecture Patterns" — `charts/orders_inventory.py::build_four_panel(state) -> go.Figure`; "Code Examples" — 4-panel construction snippet |
| DEB-02 | Annotate the week-5 demand step (4 → 8) on the chart | "Code Examples" — `fig.add_vline(x=5, row="all", col=1, line_dash="dash", annotation_text="Customer demand: 4 → 8")`; verified Plotly 6.7 `add_vline` supports `row="all"` |
| DEB-03 | Show the bullwhip amplification ratio `variance(factory_orders) / variance(customer_demand)` plus per-echelon ratios | "Architecture Patterns" — extend `engine/metrics.py` with `variance_bullwhip_ratio(state)` and `per_echelon_amplification(state)`; "Code Examples" — `statistics.pvariance` formulas; "Don't Hand-Roll" — stdlib `statistics`, not custom variance |
| DEB-04 | Cost breakdown per station: holding, backorder, total | "Architecture Patterns" — `engine/metrics.py::cost_breakdown(state)` derives holding and backorder per-week from `inventory_history` and `backlog_history`, sums and totals; "Code Examples" — derivation snippet; reconciliation invariant against `cost_history[-1]` |
| DEB-05 | Narrative ≤200 words, adapted to player's station, names the bullwhip and points to where it shows up | "Architecture Patterns" — `narrative/__init__.py::narrative_for(role, state) -> str`; "Code Examples" — four template skeletons with f-string interpolation of metrics |
| DEB-06 | "Play again" returns to setup and resets state | Existing `app.py::reset_game` callback is already wired (verified in app.py:91-97); debrief view receives it as `on_reset` param |
</phase_requirements>

---

## Summary

Phase 3 is the project's lesson-delivery moment: after week 36 the player sees four stacked subplots that visually reproduce Sterman's canonical bullwhip, plus quantitative readouts (amplification ratio, cost breakdown) and a station-aware narrative that names what they just experienced. The entire phase is a thin Streamlit shell over (a) one new pure-Plotly module (`charts/`), (b) three small additions to `engine/metrics.py`, and (c) a static-template narrative module. No new dependencies are needed — every required capability is already in the stack (Plotly 6.7.0, Streamlit 1.57.0, Python 3.12 stdlib `statistics`).

The technical risk is low and the design risk is high. Every API call here is standard Plotly + Streamlit; the only correctness invariant that can fail silently is whether the chart actually *communicates* the bullwhip. Three pitfalls dominate: (1) the week-5 annotation is missing or unlabeled and the player can't see the demand step, (2) orders and inventory are plotted on the same y-axis with vastly different scales so one curve flattens against the axis, (3) the narrative is generic ("you played the supply chain") instead of station-specific. All three are caught by tests against `go.Figure` and by reviewing the rendered debrief at canonical seed=42.

The architecture follows the established Phase 1 + Phase 2 separation: `charts/` is pure Plotly with no `st.*` calls (mirrors `engine/` purity, makes builders unit-testable), `engine/metrics.py` is pure Python with no Plotly, and `views/debrief.py` is the only file that imports both. The narrative is intentionally a static-template module — four hand-written paragraphs with light f-string interpolation — not an LLM call or a generator. This keeps the deliverable deterministic, testable, and within the "no new dependencies" constraint.

**Primary recommendation:** Build `charts/orders_inventory.py` and `engine/metrics.py` additions FIRST as pure-Python modules with `go.Figure`-level unit tests. Then write `views/debrief.py` as a thin assembler that calls the builders and renders. Narrative module last (it only needs final amplification + total cost numbers from the metrics module).

---

## Standard Stack

### Core (no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Streamlit | 1.57.0 | UI shell, `st.plotly_chart`, `st.metric`, `st.markdown`, `st.button`, `st.columns`, `st.dataframe` (or `st.table`) | Already in `requirements.txt`. `st.plotly_chart` is first-class for `go.Figure`. |
| Plotly | 6.7.0 | `plotly.graph_objects.Figure`, `plotly.graph_objects.Scatter`, `plotly.subplots.make_subplots`, `Figure.add_vline` | Already in `requirements.txt`. `make_subplots(rows=4, cols=1, shared_xaxes=True)` is purpose-built for the DEB-01 4-panel layout. `add_vline(x=5, row="all", col=1, annotation_text=...)` directly satisfies DEB-02. |
| Python stdlib `statistics` | 3.12 | `statistics.pvariance` for amplification ratios (DEB-03) | No NumPy in this project. `pvariance` is the population variance (correct choice since we have the full 36-week series, not a sample). |
| Python stdlib `dataclasses` (already used) | 3.12 | Optional: a `CostRow` dataclass for the breakdown table | Frozen dataclasses are the project convention for any structured-data passed between modules. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 8.x | Unit tests for `charts/`, `metrics`, `narrative` | Test against `go.Figure` directly (e.g., `assert len(fig.data) == 8`, `assert fig.layout.shapes[0].x0 == 5`). AppTest cannot inspect Plotly charts (returns `UnknownElement()`) — see Pitfall 6. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff | Decision |
|------------|-----------|----------|----------|
| `make_subplots(rows=4, cols=1, shared_xaxes=True)` | 4 separate `st.plotly_chart` calls (one per station) | Loses shared x-axis; harder to visually align the bullwhip amplification across echelons | **Reject.** The shared x-axis is what makes the bullwhip *visible* — orders that look fine in isolation amplify obviously when stacked. |
| Single y-axis per panel with two traces (orders + inventory) | Dual y-axis (secondary_y=True) per panel | Inventory (~0–30) and orders (~0–80 at Factory) have similar magnitudes after the step — a single y-axis with two clearly-colored lines reads cleaner and avoids two-axis label clutter | **Accept single y-axis** as the default; revisit only if visual review at seed=42 shows one curve flattening. |
| Cost breakdown as `st.dataframe` / `st.table` | Plotly bar chart | A table reconciles obviously (player can read holding/backorder/total per station and verify it matches the engine's cost ledger); a bar chart is visually busier and adds another chart on top of the 4-panel hero | **Accept table.** This is a debrief reconciliation, not a hero visualization. |
| Static narrative templates | LLM-generated text per run | Determinism, no new dependencies, no API keys, no cold-start cost, fully testable | **Accept static templates.** Four hand-written variants, light f-string interpolation. |
| 5-panel chart (customer demand + 4 stations) | 4-panel chart + week-5 annotation | The canonical Sterman visual is 4-panel; adding a 5th would dilute "this is what each echelon did" | **Accept 4-panel + annotation.** The week-5 vline tells the demand-step story without a dedicated panel. |
| `statistics.variance` (sample variance, ddof=1) | `statistics.pvariance` (population variance, ddof=0) | We have the FULL series (n=36 weeks, not a sample). Population variance is the correct estimator. | **Use `pvariance`.** Both produce a recognizably > 1 ratio at canonical seed=42; pvariance is mathematically correct here. |
| Extend `StationState` with `holding_cost_history` + `backorder_cost_history` tuples | Derive holding/backorder from `inventory_history` + `backlog_history` at debrief time | Engine extension means touching Phase 1 invariants (frozen dataclass, tick records) — risk regressing 56/56 tests. Derivation is O(36) Python, no engine change, trivially testable. | **Accept derivation.** Add `cost_breakdown(state)` to `engine/metrics.py` (pure derivation, no engine state change). |

**Installation:** No new packages. Current `requirements.txt` (`streamlit==1.57.0`, `plotly==6.7.0`) is sufficient.

---

## Architecture Patterns

### Recommended Module Layout

```
beergame/
├── charts/                       # NEW package — pure Plotly, no `st.*` calls
│   ├── __init__.py               # exports: build_four_panel, build_cost_table_figure (optional)
│   └── orders_inventory.py       # build_four_panel(state) -> go.Figure
├── engine/
│   └── metrics.py                # EXTEND (don't replace): add three functions
│       # existing: peak_orders, bullwhip_ratio (max-based)
│       # add: variance_bullwhip_ratio, per_echelon_amplification, cost_breakdown
├── narrative/                    # NEW package — pure string templates
│   ├── __init__.py               # exports: narrative_for
│   └── templates.py              # four station-specific templates as module constants
├── views/
│   └── debrief.py                # REWRITE (replace placeholder): full debrief render
```

**Rationale for the splits:**
- `charts/` parallels `engine/` and `views/` in the existing architecture: pure-Python, no `st.*` imports, unit-testable in isolation. This is the same principle that protected Phases 1 and 2 from engine/UI confusion.
- `engine/metrics.py` is extended (not replaced) so the existing `bullwhip_ratio` (max-based, used by Phase 1 calibration tests) keeps its meaning. Phase 3 adds the *variance-based* ratio DEB-03 specifies — both ratios coexist and measure different things.
- `narrative/` is a new package (not inline in `views/debrief.py`) so the four templates are testable as pure strings and the view stays a thin assembler.

### Pattern 1: Pure-Plotly Builder Module (no `st.*`)

**What:** Chart-construction functions return `go.Figure` objects. The view layer renders them via `st.plotly_chart`. No streamlit imports in `charts/`.

**When to use:** Every chart in this phase. Establishes the precedent for any future charts.

**Why:** Lets you unit-test the figure structure (number of traces, presence of week-5 vline, axis labels) without spinning up a Streamlit session. AppTest cannot inspect Plotly charts (returns `UnknownElement()` per Streamlit docs).

**Example:**
```python
# beergame/charts/orders_inventory.py
# Source: Plotly 6.7 docs https://plotly.com/python/subplots/
#         Plotly 6.7 docs https://plotly.com/python/horizontal-vertical-shapes/
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from beergame.engine.state import GameState, Role
from beergame.config.scenarios import CLASSIC_STEP_BREAK_WEEK


_STATION_TITLES = ("Retailer", "Wholesaler", "Distributor", "Factory")


def build_four_panel(state: GameState) -> go.Figure:
    """4-panel chart of orders placed + inventory across all 36 weeks.

    DEB-01: 4 panels (one per station), shared weeks x-axis, orders + inventory.
    DEB-02: vertical line at the week-5 demand step, annotated "Customer demand: 4 → 8".

    Returns a `go.Figure`. The view layer renders it via `st.plotly_chart(fig, key=..., width="stretch")`.
    """
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        subplot_titles=_STATION_TITLES,
    )

    # x-axis: weeks 1..total_weeks (history is 0-indexed, weeks are 1-indexed in UX).
    weeks = list(range(1, state.total_weeks + 1))

    for role in Role:
        s = state.stations[role.value]
        row = role.value + 1  # Role.RETAILER -> row 1, Role.FACTORY -> row 4

        # Two traces per station: orders placed (primary visual) + inventory level.
        # Plotly's default qualitative palette puts orders in one color, inventory in another.
        fig.add_trace(
            go.Scatter(
                x=weeks,
                y=list(s.orders_placed_history),
                mode="lines+markers",
                name="Orders placed",
                legendgroup="orders",
                showlegend=(row == 1),  # legend only once at the top
                line=dict(color="#1f77b4"),
            ),
            row=row, col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=weeks,
                y=list(s.inventory_history),
                mode="lines",
                name="Inventory",
                legendgroup="inventory",
                showlegend=(row == 1),
                line=dict(color="#ff7f0e", dash="dot"),
            ),
            row=row, col=1,
        )

    # DEB-02: week-5 step marker on every panel (row="all", col=1).
    # CLASSIC_STEP_BREAK_WEEK = 4 (last pre-step week); the step *fires* at week 5.
    fig.add_vline(
        x=CLASSIC_STEP_BREAK_WEEK + 1,  # = 5
        line_dash="dash",
        line_color="rgba(128,128,128,0.6)",
        annotation_text="Customer demand: 4 → 8",
        annotation_position="top right",
        row="all", col=1,
    )

    fig.update_layout(
        height=700,
        margin=dict(l=30, r=30, t=50, b=30),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="right", x=1),
    )
    fig.update_xaxes(title_text="Week", row=4, col=1)  # only on bottom (shared)
    fig.update_yaxes(title_text="Units", col=1)

    return fig
```

### Pattern 2: Stdlib-Variance Metrics (no NumPy)

**What:** Population variance via `statistics.pvariance` on plain tuples/lists. No NumPy, no pandas, no manual sum-of-squares math.

**When to use:** Every place in this phase that says "variance".

**Why:** `pvariance` handles edge cases (empty, length-1) correctly with built-in `StatisticsError`. Pure stdlib keeps the no-new-dependencies invariant.

**Example:**
```python
# beergame/engine/metrics.py  (additions; keep existing peak_orders + bullwhip_ratio)
# Source: Python docs https://docs.python.org/3/library/statistics.html#statistics.pvariance
from dataclasses import dataclass
from statistics import pvariance, StatisticsError

from beergame.config.costs import BACKORDER_COST, HOLDING_COST
from beergame.engine.state import GameState, Role


def variance_bullwhip_ratio(state: GameState) -> float:
    """DEB-03 headline metric: variance(factory_orders) / variance(customer_demand).

    Returns 0.0 if customer demand has zero variance (degenerate case — shouldn't
    happen with the canonical step demand, but defensively handled).
    """
    factory = state.stations[Role.FACTORY.value]
    try:
        denom = pvariance(state.customer_demand_history)
        numer = pvariance(factory.orders_placed_history)
    except StatisticsError:
        return 0.0
    if denom == 0:
        return 0.0
    return numer / denom


def per_echelon_amplification(state: GameState) -> dict[Role, float]:
    """DEB-03 per-echelon ratios: variance(role_orders) / variance(customer_demand).

    Retailer's ratio is typically near 1 (Retailer sees demand directly);
    upstream stations' ratios grow with the bullwhip.
    """
    try:
        denom = pvariance(state.customer_demand_history)
    except StatisticsError:
        return {r: 0.0 for r in Role}
    if denom == 0:
        return {r: 0.0 for r in Role}

    out: dict[Role, float] = {}
    for role in Role:
        s = state.stations[role.value]
        try:
            numer = pvariance(s.orders_placed_history)
        except StatisticsError:
            out[role] = 0.0
            continue
        out[role] = numer / denom
    return out


@dataclass(frozen=True, slots=True)
class CostRow:
    role: Role
    holding: float        # sum over weeks of HOLDING_COST * inventory_history[w]
    backorder: float      # sum over weeks of BACKORDER_COST * backlog_history[w]
    total: float          # == holding + backorder; MUST equal cost_history[-1]


def cost_breakdown(state: GameState) -> tuple[CostRow, ...]:
    """DEB-04: per-station decomposition of cumulative cost into holding vs backorder.

    Derived from inventory_history and backlog_history using the same constants as
    engine/costs.py::weekly_cost. The total for each station MUST equal
    s.cost_history[-1] (a debug invariant — engine.costs.weekly_cost computes the
    same formula tick-by-tick).
    """
    rows = []
    for role in Role:
        s = state.stations[role.value]
        holding = HOLDING_COST * sum(max(0, x) for x in s.inventory_history)
        backorder = BACKORDER_COST * sum(s.backlog_history)
        total = holding + backorder
        rows.append(CostRow(role=role, holding=holding, backorder=backorder, total=total))
    return tuple(rows)
```

### Pattern 3: Static Narrative Templates with Light Interpolation

**What:** Four hand-written paragraphs (one per Role), each ≤200 words, parameterized by 2–3 numbers from the run (overall amplification ratio, player's total cost, peak order, etc.). No LLM, no random selection — same input always produces same output.

**When to use:** DEB-05. Don't add another path for narrative generation in v1.

**Why:** Determinism makes the narrative testable (`assert "bullwhip" in text`, `assert len(text.split()) <= 200`). Static templates make the lesson predictable for instructors. No new dependencies.

**Example:**
```python
# beergame/narrative/__init__.py
# Source: Phase 3 design (no external lib).
from beergame.engine.metrics import (
    per_echelon_amplification,
    variance_bullwhip_ratio,
    cost_breakdown,
)
from beergame.engine.state import GameState, Role


_TEMPLATES: dict[Role, str] = {
    Role.RETAILER: (
        "You played the **Retailer** — closest to the customer. Demand stepped "
        "from 4 to 8 at week 5 (a small jump), but watch what happened upstream: "
        "your orders peaked at {retailer_peak} units, the Factory's peaked at "
        "{factory_peak}. Across the chain, the variance of orders amplified "
        "{ratio:.1f}× from customer demand to Factory production starts. That "
        "amplification is the **bullwhip effect** — and you saw the start of "
        "it. Even though you saw the real demand, the lag in shipments meant "
        "you over-corrected once the step hit. Total cost at your station: "
        "**\\${cost:,.0f}**. Try playing the Factory next — the same demand "
        "shock arrives 4 weeks late and looks twice as violent. That's the "
        "lesson: small noise at the bottom of the chain becomes a crisis at "
        "the top."
    ),
    Role.WHOLESALER: (
        "You played the **Wholesaler** — one step removed from the customer. "
        "You never saw customer demand; you only saw the Retailer's orders. "
        "When the Retailer reacted to the week-5 step, their order spike "
        "arrived at your door with a one-week mailing delay, and you had to "
        "decide whether it was real or noise. The variance amplification from "
        "customer demand to your orders was **{your_ratio:.1f}×**; the Factory "
        "saw **{factory_ratio:.1f}×**. Your station's total cost: "
        "**\\${cost:,.0f}**. This is the **bullwhip effect**: each echelon "
        "amplifies the signal it sees, because nobody can tell signal from "
        "noise without looking downstream. The only fix is information sharing "
        "— the whole chain seeing the same customer demand. Try playing the "
        "Factory next and feel how the amplification stacks."
    ),
    Role.DISTRIBUTOR: (
        "You played the **Distributor** — two steps removed from the customer. "
        "The customer-demand step (4 → 8 at week 5) reached you only after the "
        "Retailer reacted, then the Wholesaler reacted, and then their order "
        "showed up at your dock. The variance amplification from customer "
        "demand to your orders was **{your_ratio:.1f}×**; the Factory saw "
        "**{factory_ratio:.1f}×**. Your total cost: **\\${cost:,.0f}**. This "
        "is the **bullwhip effect**: by the time a small real change reaches "
        "you, it's already amplified, and your response amplifies it again "
        "before sending it to the Factory. Look at the 4-panel chart — your "
        "orders curve overshoots more than the Wholesaler's and less than the "
        "Factory's. That monotonic growth upstream is the canonical bullwhip "
        "signature. The whole chain saw exactly **one** demand change."
    ),
    Role.FACTORY: (
        "You played the **Factory** — at the top of the chain. Every order "
        "you saw was already amplified twice: by the Retailer reacting to a "
        "demand step, by the Wholesaler reacting to the Retailer's reaction, "
        "and by the Distributor reacting to the Wholesaler's. The variance of "
        "your production starts was **{your_ratio:.1f}×** the variance of "
        "actual customer demand — which only changed once, in week 5. Your "
        "total cost: **\\${cost:,.0f}**. This is the **bullwhip effect** in "
        "its purest form: a one-time, small change in customer demand becomes "
        "a violent swing in factory production. It's not your fault — it's "
        "structural. The only ways to dampen it are shorter lead times or "
        "sharing the customer-demand signal across the whole chain. Try "
        "playing the Retailer next — same demand, same Sterman opponents, "
        "but you'll see how much smaller the swing looks from where the "
        "customer sits."
    ),
}


def narrative_for(state: GameState) -> str:
    """DEB-05: ≤200 words, station-specific, interpolated with the player's metrics.

    Returns a single Markdown string. The view renders it with `st.markdown(...)`.
    """
    role = state.player_role
    me = state.stations[role.value]
    factory = state.stations[Role.FACTORY.value]
    retailer = state.stations[Role.RETAILER.value]

    ratios = per_echelon_amplification(state)
    overall = variance_bullwhip_ratio(state)
    rows = cost_breakdown(state)
    my_cost = next(r.total for r in rows if r.role == role)

    return _TEMPLATES[role].format(
        retailer_peak=max(retailer.orders_placed_history),
        factory_peak=max(factory.orders_placed_history),
        ratio=overall,
        your_ratio=ratios[role],
        factory_ratio=ratios[Role.FACTORY],
        cost=my_cost,
    )
```

### Pattern 4: View as Thin Assembler

**What:** `views/debrief.py` imports from `charts/`, `engine/metrics`, and `narrative/`, and renders with `st.title`, `st.markdown`, `st.metric`, `st.plotly_chart`, `st.table` (or `st.dataframe`), and `st.button`. The view does no math.

**When to use:** Always. Phase 2 established this pattern; Phase 3 extends it.

**Why:** Keeps the view diff-able by line count, lets all logic stay in pure modules, makes the "Play again" plumbing identical to the existing placeholder (`on_reset` arg matches `app.py::reset_game`).

**Example:**
```python
# beergame/views/debrief.py  (replaces placeholder)
import streamlit as st

from beergame.charts.orders_inventory import build_four_panel
from beergame.engine.metrics import (
    cost_breakdown,
    per_echelon_amplification,
    variance_bullwhip_ratio,
)
from beergame.engine.state import GameState, Role
from beergame.engine.tick import is_game_over
from beergame.narrative import narrative_for


def render(state: GameState, on_reset) -> None:
    assert is_game_over(state), (
        f"Debrief called with phase={state.phase!r} (week={state.week})"
    )

    # Headline metric — the "what just happened" number.
    overall = variance_bullwhip_ratio(state)
    ratios = per_echelon_amplification(state)
    rows = cost_breakdown(state)

    st.title(":beer_mug: Game complete")
    st.markdown(
        f"### Your supply chain amplified demand by **{overall:.1f}×**"
    )
    st.caption(
        "Variance of Factory production starts ÷ variance of actual customer demand. "
        "Customer demand changed exactly once (4 → 8 at week 5)."
    )

    # 4-panel chart (DEB-01, DEB-02). Stable key for chart identity across reruns.
    fig = build_four_panel(state)
    st.plotly_chart(fig, key="debrief_four_panel", width="stretch")

    # Per-echelon amplification (DEB-03 secondary readouts) as four metric tiles.
    cols = st.columns(4)
    for i, role in enumerate(Role):
        with cols[i]:
            st.metric(
                role.name.title(),
                f"{ratios[role]:.1f}×",
                help="variance(this station's orders) / variance(customer demand)",
            )

    # Cost breakdown table (DEB-04). Plain list-of-dicts → st.table avoids pandas.
    st.subheader("Cost breakdown")
    st.table([
        {
            "Station": r.role.name.title(),
            "Holding ($)": f"{r.holding:,.2f}",
            "Backorder ($)": f"{r.backorder:,.2f}",
            "Total ($)": f"{r.total:,.2f}",
        }
        for r in rows
    ])

    # Narrative (DEB-05).
    st.subheader("What just happened")
    st.markdown(narrative_for(state))

    # Play again (DEB-06).
    st.button(
        "Play again",
        on_click=on_reset,
        type="primary",
        key="debrief_reset_btn",
    )
```

### Anti-Patterns to Avoid

- **Putting `st.*` calls in `charts/`.** Breaks the unit-testability contract that `engine/` and `ai/` already follow. If you find yourself reaching for `st.something` inside a chart builder, the call belongs in the view.
- **Computing variance/cost in `views/debrief.py`.** Moves load-bearing math into a Streamlit-imported file, which can't be tested without AppTest. Always: math in `engine/metrics.py`, chart in `charts/`, render in `views/`.
- **Hard-coding total_weeks=36 in the chart.** Use `state.total_weeks` so future scenario configs don't silently fall over.
- **`use_container_width=True`.** Deprecated in 1.57.0 in favor of `width="stretch"`. Phase 2's `play.py` already uses the new form — match it.
- **Calling the chart builder without a stable `key=`.** Required by `st.plotly_chart` for stable identity across reruns (Pitfall 10 in PITFALLS.md). Use `key="debrief_four_panel"`.
- **Plotting orders and inventory on separate y-axes (secondary_y=True) by default.** Adds visual clutter and an extra axis label per panel. Use single y-axis with two clearly-colored lines; only switch to secondary_y if seed=42 review shows one curve flattening to the axis.
- **A 5th panel for customer demand.** The canonical 4-station chart is the recognizable visual; an extra panel dilutes it. The week-5 vline + annotation_text carries the demand-step story.
- **Computing chart inside the main script body (not inside `views.debrief.render`).** Pitfall 11 — would re-run on every rerun.
- **Extending `StationState` with `holding_cost_history` / `backorder_cost_history` tuples.** Adds engine-frozen-dataclass churn for zero gain — the derivation is trivial and pure.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Population variance | Manual `sum((x - mean(xs))**2 for x in xs) / len(xs)` | `statistics.pvariance(xs)` | Handles empty/length-1 with `StatisticsError`; numerically stable (Welford / two-pass); zero new deps. |
| 4-panel chart with shared x-axis | Four separate `go.Figure` + manual layout alignment | `plotly.subplots.make_subplots(rows=4, cols=1, shared_xaxes=True)` | Purpose-built for this exact layout; gives synchronized zoom/hover for free; lays out subplot titles automatically. |
| Vertical line at week 5 across all subplots | Manually add 4 shapes via `fig.add_shape(...)` for each row | `fig.add_vline(x=5, row="all", col=1, annotation_text=...)` | `add_vline` accepts `row="all"`, places annotation in the correct subplot coords, handles the case where future scenarios change the step week. |
| Cost breakdown table | Custom HTML via `st.markdown(html, unsafe_allow_html=True)` | `st.table([dict, dict, ...])` | Built-in styling, no pandas dependency, no unsafe HTML. |
| Reset session state | Manual `for k in list(st.session_state): del st.session_state[k]` | Existing `app.py::reset_game` callback (already wired) | Already preserves `seen_rules` correctly (verified in `app.py:91-97`); already covered by `tests/test_app_smoke.py::test_week_36_submission_transitions_to_done`. |
| Narrative generation | LLM call, prompt-template engine, Jinja, etc. | Four static module-level strings + `str.format` | Determinism, no new deps, no API keys, fully testable. |
| Word counting for ≤200-word constraint | `re.findall(r'\w+', text)` heuristics | `len(text.split())` | Same answer for English prose at this length; one-liner; testable. |
| Markdown rendering | Custom HTML | `st.markdown(text)` | Built-in; supports the **bold** in templates. |
| Holding vs backorder cost decomposition | Custom math reading the cost ledger | Re-derive from `inventory_history` + `backlog_history` using `HOLDING_COST` + `BACKORDER_COST` from `config/costs.py` | Engine's `weekly_cost` uses the same formula tick-by-tick — derivation is mathematically identical and lets us reconcile (total MUST equal `cost_history[-1]`). |
| Mapping `Role` → station name | Hand-rolled `{Role.RETAILER: "Retailer", ...}` dict | `role.name.title()` | `Role` is already an `Enum` with descriptive names; `.title()` already used in `play.py:48`. |

**Key insight:** Every "I could build this in 10 lines" temptation in this phase is a single stdlib or library call. The Plotly subplot + vline API and Python's `statistics.pvariance` cover the entire math + chart surface. The cost breakdown is a one-line list comprehension. The narrative is four string constants. The reset is one already-tested callback. The whole phase is composition.

---

## Common Pitfalls

### Pitfall 1: Week-5 marker placed on wrong week or missing

**What goes wrong:** The vertical line lands at week 4 (one off) or doesn't render because `row="all"` was forgotten, or the annotation collides with a subplot title and becomes unreadable.

**Why it happens:** `CLASSIC_STEP_BREAK_WEEK = 4` is the *last pre-step week*; demand jumps *at* week 5. Easy off-by-one. Also, `add_vline` without `row="all"` defaults differently across Plotly versions.

**How to avoid:**
- Use `CLASSIC_STEP_BREAK_WEEK + 1` (= 5) as the `x` argument, not `CLASSIC_STEP_BREAK_WEEK`. Add a code comment showing the derivation.
- Always pass `row="all", col=1` explicitly.
- Unit-test: `assert any(s.x0 == 5 for s in fig.layout.shapes)` — the shape exists with the right x. (`add_vline` translates internally into a `Shape` entry in `fig.layout.shapes`.)
- Use `annotation_position="top right"` to avoid the subplot title at the top center.

**Warning signs:** Annotation text overlaps the subplot title; the line appears on only the top panel; the line is at week 4 (one panel before the demand jump becomes visible in the data).

---

### Pitfall 2: Orders + inventory share one y-axis, one curve flattens

**What goes wrong:** Orders at the Factory peak at 30–80; inventory swings between roughly -20 (backlog visualized as 0) and 40. Plotted on one y-axis, both fit. But if the Factory orders peak much higher than expected (some seeds push to 80+), inventory at all four stations compresses to a thin band near 0 and the inventory story is invisible.

**Why it happens:** Default Plotly y-axis is `autorange` with all traces sharing one range. Worst case, one trace dominates.

**How to avoid:**
- Visually verify with canonical `seed=42` (known bullwhip ratio = 2.000 max-based, Factory peak ≈ 8 × retailer peak ≈ 4 on max). At seed=42 both curves fit cleanly on one axis.
- If a future seed pushes one curve off-screen, switch to `make_subplots(... specs=[[{"secondary_y": True}], ...] * 4)` and put inventory on the secondary y-axis with `secondary_y=True` on its `add_trace` call.
- Test: `assert max(s.orders_placed_history) < 200` (sanity bound; if the test ever fails, revisit the y-axis strategy).

**Warning signs:** In manual seed=42 review, one of orders/inventory looks like a flat line near zero in any panel.

---

### Pitfall 3: Cost breakdown doesn't reconcile with `cost_history[-1]`

**What goes wrong:** The table's "Total" column for a station doesn't equal `state.stations[role.value].cost_history[-1]`. Player loses faith in the numbers; if anyone digs in, the bug is real.

**Why it happens:** `engine/costs.py::weekly_cost` uses `HOLDING_COST * max(0, station.inventory) + BACKORDER_COST * station.backlog`. If the debrief derivation drops the `max(0, ...)` or uses `inventory_history` indices the wrong way, totals diverge.

**How to avoid:**
- Mirror `weekly_cost` *exactly* in `cost_breakdown`: `HOLDING_COST * sum(max(0, x) for x in s.inventory_history)` + `BACKORDER_COST * sum(s.backlog_history)`. The engine's `inventory` and `backlog` fields are non-negative integers (Phase 1 invariant), but `max(0, ...)` matches the engine formula symbolically.
- Add an invariant unit test: for each role, `cost_row.total == pytest.approx(state.stations[role.value].cost_history[-1])`. Tolerance: `abs=0.01` (one-cent rounding).

**Warning signs:** Manual play-through with canonical seed=42 shows the table total ≠ the engine's cumulative cost (visible if you also `st.metric` the cumulative).

---

### Pitfall 4: Narrative > 200 words after interpolation

**What goes wrong:** A template that's 195 words clean becomes 215 after a 4-digit cost number and a multi-digit peak interpolate in. Player sees a wall of text.

**Why it happens:** Word-count budget assumed against the template, not the rendered output.

**How to avoid:**
- Author each template at ≤180 words to leave headroom for interpolated numbers.
- Test: `assert len(narrative_for(state).split()) <= 200` for all four station-runs at canonical seed=42.
- Use `f"\\${cost:,.0f}"` (no decimals) rather than `f"\\${cost:.2f}"` so cost prints "1,234" not "1,234.56" (saves words/chars).

**Warning signs:** Reading the rendered output feels long; test asserting word count fails.

---

### Pitfall 5: Plotly chart flickers / re-renders on rerun

**What goes wrong:** Player clicks "Play again" → Streamlit rerun → the 4-panel chart visibly flashes before disappearing. Or the chart re-mounts on any later rerun and loses zoom state.

**Why it happens:** `st.plotly_chart` without `key=` re-creates the chart element on every rerun. PITFALLS.md Pitfall 10 documents this is a known Plotly+Streamlit issue (GitHub #8782).

**How to avoid:**
- Always pass `key="debrief_four_panel"`. Stable across reruns → Streamlit reuses the chart DOM.
- The debrief view is rendered only when `phase == "done"`, so there's no in-game rerun pressure — but the "Play again" click triggers exactly one rerun that takes the user back to setup, which is fine.
- The chart is built only once per render (inside `render()`); don't compute it at module top-level.

**Warning signs:** Visible flash on chart load; zoom state resets between reruns.

---

### Pitfall 6: AppTest can't inspect Plotly charts → test the figure directly

**What goes wrong:** Author writes `at.plotly_chart[0]` or `at.get("plotly_chart")` expecting introspection. Streamlit returns `UnknownElement()`. Test produces no useful assertion.

**Why it happens:** Streamlit's AppTest doesn't support chart elements (confirmed in 2026 docs).

**How to avoid:**
- Test chart structure by calling the *builder* directly, not via AppTest:
  ```python
  from beergame.charts.orders_inventory import build_four_panel
  fig = build_four_panel(canonical_done_state)
  assert len(fig.data) == 8  # 4 stations × (orders + inventory) traces
  assert len(fig.layout.annotations) >= 4  # 4 subplot titles + annotation_text from add_vline
  assert any(s.x0 == 5 for s in fig.layout.shapes)  # the week-5 vline
  ```
- Use AppTest only for the *transition* assertion (debrief renders without raising; "Play again" button is present). The existing `test_week_36_submission_transitions_to_done` already covers this for the placeholder; extend it to also assert the new section headers (`assert any("amplified demand" in m.value for m in at.markdown)`).

**Warning signs:** AppTest test passes trivially with `UnknownElement()` and gives false confidence.

---

### Pitfall 7: `variance(customer_demand) == 0` edge case crashes the debrief

**What goes wrong:** Customer demand at canonical scenario is `(4, 4, 4, 4, 8, 8, ..., 8)` — nonzero variance. But a future scenario (or a misconfigured demand_fn) with constant demand would produce `pvariance == 0`, causing `ZeroDivisionError` in the headline metric.

**Why it happens:** No defensive guard.

**How to avoid:**
- Both `variance_bullwhip_ratio` and `per_echelon_amplification` check `if denom == 0: return 0.0` (or `dict.fromkeys(Role, 0.0)`).
- Render path: if `overall == 0.0`, show a caption like "No variance to amplify in this scenario." rather than `0.0×`.
- Unit-test with a constant-demand fake `GameState` to verify no crash.

**Warning signs:** ZeroDivisionError stack trace when running a non-canonical scenario in dev.

---

### Pitfall 8: Subplot titles overlap the week-5 annotation

**What goes wrong:** `subplot_titles=("Retailer", ...)` places titles at the *top* of each panel. `annotation_position="top right"` on the vline puts the annotation at top-right of each subplot — sometimes colliding with the title text.

**Why it happens:** Plotly defaults; no automatic collision avoidance.

**How to avoid:**
- Set `vertical_spacing=0.04` (already in example) to give titles breathing room.
- Use `annotation_position="top right"` (corner away from center-aligned titles) OR `annotation_position="bottom right"` if testing shows collisions.
- Visual review at seed=42 is the final check.

**Warning signs:** Manual seed=42 screenshot shows overlapping text in any panel header.

---

### Pitfall 9: Forgetting `width="stretch"` (use_container_width is deprecated)

**What goes wrong:** Chart renders at a fixed default width (~700px) inside a wider container, leaving wasted whitespace, or `use_container_width=True` emits a deprecation warning on every render.

**Why it happens:** Old Streamlit habit; 1.57.0 deprecated `use_container_width` in favor of `width="stretch"` / `width="content"` / `width=N` (verified against current Streamlit docs).

**How to avoid:** Always `st.plotly_chart(fig, key="...", width="stretch")`. Match `play.py:94` which already does this correctly.

**Warning signs:** Browser console deprecation warning; chart narrower than the container.

---

### Pitfall 10: "Play again" doesn't fully reset the run

**What goes wrong:** Player clicks "Play again", lands on setup, picks a new station, starts game — but week counter starts at 7 (or weird state from previous game). Some session-state key wasn't cleared.

**Why it happens:** `reset_game` (in `app.py`) pops a specific set of keys; if Phase 3 adds new session-state keys (it shouldn't, but might via widget `key=`), those linger.

**How to avoid:**
- Don't add new `st.session_state` keys in the debrief — use widget `key=` only on the chart and the button (their internal state doesn't affect game logic).
- If new keys are added, update `app.py::reset_game` to pop them. Per `app.py:96`, the reset pops `("phase", "player_role", "seed", "game", "ai_agents")` — anything else added would also need popping.
- AppTest already covers the reset transition (or should — add a test that simulates the "Play again" → setup → start → playing path).

**Warning signs:** Manual replay leaves stale data; AppTest replay test fails.

---

## Code Examples

(See "Architecture Patterns" above for full Pattern 1–4 examples. Quick-reference verified snippets below.)

### `make_subplots` with 4 rows and shared x-axis
```python
# Source: https://plotly.com/python/subplots/ (verified 2026-05-18, Plotly 6.7.0)
from plotly.subplots import make_subplots

fig = make_subplots(
    rows=4, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.04,
    subplot_titles=("Retailer", "Wholesaler", "Distributor", "Factory"),
)
```

### `add_vline` across all subplots with annotation
```python
# Source: https://plotly.com/python/horizontal-vertical-shapes/ (verified 2026-05-18)
fig.add_vline(
    x=5,
    line_dash="dash",
    line_color="rgba(128,128,128,0.6)",
    annotation_text="Customer demand: 4 → 8",
    annotation_position="top right",
    row="all", col=1,
)
```

### Population variance with edge handling
```python
# Source: https://docs.python.org/3/library/statistics.html (verified 2026-05-18, Python 3.12)
from statistics import pvariance, StatisticsError

try:
    v = pvariance(data)
except StatisticsError:
    v = 0.0   # empty or singleton
```

### Streamlit chart render (matches project convention)
```python
# Source: https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart (verified 2026-05-18, Streamlit 1.57.0)
# Matches beergame/views/play.py:89-94 (Phase 2 convention).
st.plotly_chart(fig, key="debrief_four_panel", width="stretch")
```

### Pure-Python cost decomposition (no NumPy)
```python
from beergame.config.costs import HOLDING_COST, BACKORDER_COST

holding = HOLDING_COST * sum(max(0, x) for x in s.inventory_history)
backorder = BACKORDER_COST * sum(s.backlog_history)
total = holding + backorder
# Invariant: total == s.cost_history[-1] (engine.costs.weekly_cost computes the same per tick).
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `st.plotly_chart(fig, use_container_width=True)` | `st.plotly_chart(fig, width="stretch", key="...")` | Streamlit 1.56–1.57 (2026 release notes) | Deprecation warning if you still use `use_container_width`. Project's `views/play.py` already updated. |
| Build chart in main script body | Build inside `views.render()`, key it for stable identity | Streamlit 1.35+ (Plotly flicker issue #8782 fix) | Reruns no longer rebuild DOM; zoom/hover state survives. |
| `plotly.figure_factory` for shapes | `Figure.add_vline` / `Figure.add_vrect` / `Figure.add_hline` | Plotly 4.12+ (years stable now) | One-liner instead of manual `add_shape` math; supports `row="all"`. |
| NumPy/pandas for any "data" work in Streamlit | Plain Python where the problem size allows | Project decision (STACK.md, 2026-05-18) | Beer Game is 4 × 36 = 144 cells — `statistics.pvariance` is faster than the NumPy import alone. |
| `pickle`/JSON serialization of game state for replay | In-session only via `st.session_state` | Project decision (PROJECT.md) | "Play again" resets state via callback — no persistence layer needed. |

**Deprecated/outdated:**
- `use_container_width=True` (deprecated in Streamlit 1.57; project moved to `width="stretch"` in Phase 2).
- `@st.cache` (legacy, deprecated since 1.18 / 2023; use `@st.cache_data` if any memoization is needed — though for this phase the debrief is rendered once per game, so no caching is required).
- Manual `add_shape({"type": "line", ...})` for vertical lines — `add_vline` is the modern API.

---

## Open Questions

1. **Should holding cost be derived from PRE-fill inventory or POST-fill inventory?**
   - What we know: `engine/costs.py::weekly_cost` is called from `engine/tick.py::record_state` (step 3 — AFTER fill_orders). So `s.inventory` at that moment is the *post-fill* inventory. `s.inventory_history` records post-fill values.
   - What's unclear: nothing — the engine already commits to post-fill. The debrief's `cost_breakdown` derivation will use `inventory_history` (post-fill values) and produce identical results to `cost_history`.
   - Recommendation: derive from `inventory_history` directly; assert reconciliation in the test. Already reflected in Code Example above.

2. **Should the "headline number" be variance-ratio (DEB-03's formula) or peak-ratio (existing `engine/metrics.bullwhip_ratio`)?**
   - What we know: DEB-03 explicitly says variance-based. Phase 1's calibration test (`tests/test_bullwhip_emerges.py`) uses peak-based (max/max). Both exist, both measure bullwhip, but they have different magnitudes.
   - What's unclear: which number reads better as "your supply chain over-ordered N× compared to actual demand."
   - Recommendation: USE THE VARIANCE-BASED RATIO for the headline (DEB-03 mandates it). Keep peak-based `bullwhip_ratio` as the internal calibration metric. Display the variance ratio as the prominent "{ratio:.1f}×" headline; the per-echelon tiles also use variance.

3. **`st.table` vs `st.dataframe` for the cost breakdown?**
   - What we know: `st.table` renders a static fixed table from a list-of-dicts; `st.dataframe` is interactive (sortable, scrollable) and accepts pandas. We have no pandas. `st.table` accepts list-of-dicts directly.
   - What's unclear: whether the interactivity of `st.dataframe` is worth bringing in pandas.
   - Recommendation: USE `st.table` with a list-of-dicts. No pandas, fixed layout matches the debrief's "look at the numbers" intent. The table is 4 rows × 4 columns — no need for sort/scroll.

4. **Should we show the customer-demand series anywhere on the 4-panel chart?**
   - What we know: The week-5 vline + annotation already communicates "customer demand changed here." A 5th panel or overlay would be redundant for the canonical scenario (customer demand is just a step function).
   - What's unclear: whether seasoned operations-management instructors expect to see the customer-demand line on the chart.
   - Recommendation: DEFER. The vline + annotation_text is canonical and sufficient. If post-Phase-3 user testing shows confusion, adding a `go.Scatter(x=weeks, y=customer_demand_history, line=dict(color="green"))` overlay on row 1 (Retailer) is a 3-line change.

5. **Test fixture: should we cache the canonical seed=42 final `GameState` for chart-builder tests?**
   - What we know: Running `simulate_full_game(seed=42, ...)` takes <100ms — easily fast enough for a fresh run per test. Phase 1's tests already do this.
   - What's unclear: whether a module-level fixture is worth the indirection.
   - Recommendation: Use a `conftest.py` fixture (`canonical_done_state`) so every chart/metric test shares one simulation. Phase 1's conftest already has `initial_game` and `constant_4_agents`; mirror that.

---

## Sources

### Primary (HIGH confidence)
- **Project artifacts (in-repo, current):**
  - `/home/williamlefew/projects/beergameNexStratus/beergame/engine/state.py` — `GameState`, `StationState`, history tuple field names, `Role` enum
  - `/home/williamlefew/projects/beergameNexStratus/beergame/engine/tick.py` — tick sequence, `weekly_cost` invocation point, `is_game_over`
  - `/home/williamlefew/projects/beergameNexStratus/beergame/engine/costs.py` — `weekly_cost(station)` formula (mirrors `cost_breakdown` derivation)
  - `/home/williamlefew/projects/beergameNexStratus/beergame/engine/metrics.py` — existing `peak_orders` and max-based `bullwhip_ratio` (Phase 3 EXTENDS, not replaces)
  - `/home/williamlefew/projects/beergameNexStratus/beergame/config/scenarios.py` — `CLASSIC_STEP_BREAK_WEEK = 4`, `TOTAL_WEEKS = 36`
  - `/home/williamlefew/projects/beergameNexStratus/beergame/config/costs.py` — `HOLDING_COST = 0.50`, `BACKORDER_COST = 1.00`
  - `/home/williamlefew/projects/beergameNexStratus/beergame/views/play.py` — Phase 2 convention for `st.plotly_chart(fig, key=..., width="stretch")`
  - `/home/williamlefew/projects/beergameNexStratus/beergame/views/debrief.py` — current placeholder, `on_reset` interface contract
  - `/home/williamlefew/projects/beergameNexStratus/app.py` — `reset_game` callback (DEB-06 already wired)
  - `/home/williamlefew/projects/beergameNexStratus/tests/test_bullwhip_emerges.py` — canonical seed=42 bullwhip baseline (Factory/Retailer peak ratio in [2.0, 4.0])
  - `/home/williamlefew/projects/beergameNexStratus/tests/test_app_smoke.py` — AppTest pattern for transition tests
  - `/home/williamlefew/projects/beergameNexStratus/.planning/research/STACK.md` — stack decisions (Plotly 6.7.0, Streamlit 1.57.0, Python 3.12, no NumPy)
  - `/home/williamlefew/projects/beergameNexStratus/.planning/research/PITFALLS.md` — Pitfalls 10, 11, 19, 20 are the chart/debrief traps Phase 3 must avoid
  - `/home/williamlefew/projects/beergameNexStratus/.planning/research/SUMMARY.md` — Phase 3 outline
  - `/home/williamlefew/projects/beergameNexStratus/.planning/REQUIREMENTS.md` lines 47–52 — DEB-01..DEB-06 verbatim
- **Plotly docs (2026-05-18):**
  - https://plotly.com/python/subplots/ — `make_subplots(rows, cols, shared_xaxes, vertical_spacing, subplot_titles)` verified
  - https://plotly.com/python/horizontal-vertical-shapes/ — `add_vline(x, line_dash, line_color, annotation_text, annotation_position, row, col)` with `row="all"` verified
  - https://plotly.com/python-api-reference/generated/plotly.subplots.make_subplots.html — 6.7.0 API reference
- **Streamlit docs (2026-05-18):**
  - https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart — `width="stretch"` is current, `use_container_width` deprecated, `key=` for stable identity
- **Python stdlib (3.12):**
  - https://docs.python.org/3/library/statistics.html#statistics.pvariance — population variance, raises `StatisticsError` on empty input

### Secondary (MEDIUM confidence)
- https://github.com/streamlit/streamlit/issues/8782 — Plotly flicker bug; mitigated by stable `key=` (matches our usage in `play.py`)
- Streamlit community thread, AppTest + plotly_chart returns `UnknownElement` — confirms we cannot inspect `go.Figure` via AppTest and must unit-test the builder directly

### Tertiary (LOW confidence)
- None used as load-bearing. All claims above are anchored in project files or current official docs.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every library is already in the project's `requirements.txt` and verified against current PyPI / official docs (2026-05-18).
- Architecture: HIGH — `charts/` + `views/` + `engine/metrics` split mirrors the precedent set in Phase 1 + 2 and is enforceable via static module boundaries.
- Pitfalls: HIGH — five of the ten pitfalls are project-specific gotchas already documented in PITFALLS.md (just elaborated for this phase); five are new but each has a unit test or visual review backstop.
- Don't hand-roll: HIGH — every "use this instead" is a stdlib or already-installed library call.
- Open questions: All 5 have concrete recommendations; none are blockers.

**Research date:** 2026-05-18
**Valid until:** 30 days (stable stack, no fast-moving deps in scope)
