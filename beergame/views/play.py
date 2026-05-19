"""Per-turn play view — PLAY-01..05.

This is the heart of the human-playable loop. Each rerun renders the player's
current station view via ``build_station_view`` (the ONLY allowed cross-station
read path — engine-enforced visibility from Phase 1's ENG-10 + Plan 02-01's
``last_shipment_received`` addition), shows locally-knowable status with strong
visual hierarchy and dollar-cost framing, plots the player's own signals
(orders placed, downstream demand received, upstream shipments received), and
exposes an ``st.form`` with a single ``st.number_input`` + "Advance week" submit.

PLAY-03 enforcement: this view NEVER reads ``state.stations[i]`` for any
``i != state.player_role.value``, and NEVER reads
``state.customer_demand_history``. The only allowed reads from ``state`` are
``state.week``, ``state.total_weeks``, ``state.player_role``, and the player's
OWN ``state.stations[role.value]`` history tuples (intrinsically the player's
own data — orders they placed, shipments they received, costs they incurred).
All cross-station info flows through ``build_station_view(state, role)``.

Anti-feature guardrail (AF-3 in research/FEATURES.md): we surface dollar costs
and dynamic situational commentary, but we DO NOT suggest an order quantity or
hint at an "optimal" number. The bullwhip discovery moment requires that the
player make their own decision under uncertainty.
"""
import plotly.graph_objects as go
import streamlit as st

from beergame.config.costs import BACKORDER_COST, HOLDING_COST
from beergame.engine.state import GameState, build_station_view


# --- Health classification ------------------------------------------------- #
# Four states the player's station can be in. Drives the hero pill color, the
# inventory/backlog card tinting, and the diagnostic copy.
#
# Thresholds are deliberately a bit loose: a station with backlog=5 and inv=10
# is "strained" not "stable" — we want the visual feedback to fire before the
# situation is catastrophic, so the player can connect their order decisions
# to the trajectory.
_HEALTH_CRISIS = "crisis"
_HEALTH_STRAINED = "strained"
_HEALTH_STABLE = "stable"
_HEALTH_SURPLUS = "surplus"

_HEALTH_LABELS = {
    _HEALTH_CRISIS:   ("CRISIS",   "red",    "Stockouts piling up — every week you can't ship costs you money."),
    _HEALTH_STRAINED: ("STRAINED", "orange", "Demand is outrunning inventory. You're starting to bleed."),
    _HEALTH_STABLE:   ("STABLE",   "green",  "On equilibrium. Watch the demand signal — anything can change."),
    _HEALTH_SURPLUS:  ("SURPLUS",  "blue",   "Inventory is piling up. Holding fees accumulate every week."),
}


def _classify_health(inventory: int, backlog: int) -> str:
    if backlog >= 20 and backlog > inventory:
        return _HEALTH_CRISIS
    if backlog >= 5 and backlog > inventory:
        return _HEALTH_STRAINED
    if inventory >= 30 and backlog == 0:
        return _HEALTH_SURPLUS
    return _HEALTH_STABLE


def _color_for_health(health: str) -> str:
    """Map health bucket to a Streamlit-supported markdown color name."""
    return _HEALTH_LABELS[health][1]


# --- Cost helpers ---------------------------------------------------------- #
def _weekly_cost_split(inventory: int, backlog: int) -> tuple[float, float, float]:
    """Replicates ``engine.costs.weekly_cost`` but exposes the holding vs
    backorder split so the UI can name where the bleed is coming from.
    """
    holding = HOLDING_COST * max(0, inventory)
    backorder = BACKORDER_COST * backlog
    return holding, backorder, holding + backorder


# --- Hero + cards ---------------------------------------------------------- #
def _render_hero(role_name: str, week: int, total_weeks: int, health: str) -> None:
    """Role + week + status pill. Top of the page, sets the emotional tone."""
    label, color, _ = _HEALTH_LABELS[health]
    left, right = st.columns([3, 2])
    with left:
        st.markdown(
            f"### \U0001F37A {role_name} · "
            f"<span style='opacity:0.7;font-weight:400'>Week {week} of {total_weeks}</span>",
            unsafe_allow_html=True,
        )
    with right:
        # The pill is intentionally large and right-aligned — it's the first
        # thing the player should read each turn.
        st.markdown(
            f"<div style='text-align:right;font-size:1.5em;font-weight:700;"
            f"color:{_PILL_CSS_COLOR[health]};letter-spacing:0.05em;'>"
            f"● {label}</div>",
            unsafe_allow_html=True,
        )


# CSS color names map (Streamlit's :color[] markdown supports named colors but
# the inline HTML pill above needs a real CSS color).
_PILL_CSS_COLOR = {
    _HEALTH_CRISIS:   "#d62728",
    _HEALTH_STRAINED: "#ff7f0e",
    _HEALTH_STABLE:   "#2ca02c",
    _HEALTH_SURPLUS:  "#1f77b4",
}


def _trend_delta(history: tuple[int, ...]) -> str | None:
    """Return a 'X (+N)' or 'X (-N)' delta string vs the entry before last,
    or None if we don't have two data points yet."""
    if len(history) < 2:
        return None
    diff = history[-1] - history[-2]
    if diff == 0:
        return "no change"
    sign = "+" if diff > 0 else ""
    return f"{sign}{diff} vs last week"


def _render_status_cards(view, station_inventory_history: tuple[int, ...],
                          station_backlog_history: tuple[int, ...]) -> None:
    """Four bordered cards stacked vertically. The caller places this inside an
    outer column so each card spans that column's full width — gives the labels
    room to breathe (e.g., "Order from downstream this week").

    Inventory and backlog get color-coded big numbers; shipments-in and
    orders-out get neutral numbers with trend annotation.
    """
    inv = view.inventory
    bl = view.backlog

    inv_color = "red" if inv == 0 else ("orange" if inv < 4 else "green" if inv <= 30 else "blue")
    bl_color = "red" if bl >= 20 else ("orange" if bl >= 5 else "green" if bl == 0 else "gray")

    with st.container(border=True):
        st.caption("On-hand inventory")
        st.markdown(f"# :{inv_color}[{inv}]")
        inv_delta = _trend_delta(station_inventory_history)
        st.caption(inv_delta or "first week")

    with st.container(border=True):
        st.caption("Backlog (unfilled orders)")
        st.markdown(f"# :{bl_color}[{bl}]")
        bl_delta = _trend_delta(station_backlog_history)
        st.caption(bl_delta or "first week")

    with st.container(border=True):
        st.caption("Shipment that just arrived")
        st.markdown(f"# {view.last_shipment_received}")
        st.caption(f"Supply line: **{view.supply_line}** still in transit")

    with st.container(border=True):
        st.caption("Order from downstream this week")
        order_pulse_color = ("red" if view.last_order_received >= 20
                             else "orange" if view.last_order_received >= 10
                             else "gray")
        st.markdown(f"# :{order_pulse_color}[{view.last_order_received}]")
        recent = view.recent_orders_received
        if len(recent) >= 2:
            pulse = recent[-1] - recent[0]
            if pulse > 0:
                st.caption(f":red[+{pulse} vs {len(recent)} weeks ago] (demand climbing)")
            elif pulse < 0:
                st.caption(f":green[{pulse} vs {len(recent)} weeks ago] (demand cooling)")
            else:
                st.caption("steady demand")
        else:
            st.caption("first reading")


def _render_money_meter(this_week_holding: float, this_week_backorder: float,
                        this_week_total: float, cumulative_total: float) -> None:
    """The dollar bleed, all in one strip. This is the new thing the user asked
    for — make the cost legible every turn so the lesson lands turn-by-turn,
    not just at the debrief.
    """
    with st.container(border=True):
        st.markdown("**:moneybag: This week**")
        a, b, c, d = st.columns(4)
        a.metric("Holding cost", f"${this_week_holding:.2f}",
                 help="$0.50 per case per week of inventory you sat on.")
        b.metric("Backorder cost", f"${this_week_backorder:.2f}",
                 help="$1.00 per case per week of demand you couldn't fill. "
                      "Twice as expensive as holding inventory.")
        c.metric("Week total", f"${this_week_total:.2f}")
        d.metric("Cumulative", f"${cumulative_total:.2f}",
                 help="Your station's total cost since week 1.")


def _diagnostic_message(view, health: str,
                        this_week_holding: float,
                        this_week_backorder: float) -> str:
    """A single-paragraph 'what's actually happening' read on the player's
    situation, anchored in real numbers from this turn. No order suggestions —
    the bullwhip lesson requires the player to decide for themselves.
    """
    bl = view.backlog
    inv = view.inventory
    last_order = view.last_order_received
    sl = view.supply_line

    if health == _HEALTH_CRISIS:
        return (
            f"You're in a hole. **{bl} units of backlog** at $1.00/unit/week = "
            f"**${this_week_backorder:.2f} just this week** in unfilled-order fees — "
            f"and that keeps charging every week until you can ship. "
            f"Your supply line has only **{sl} units in transit** and downstream is "
            f"asking for **{last_order} more**. Every order you place now won't "
            f"arrive for several weeks."
        )
    if health == _HEALTH_STRAINED:
        return (
            f"Demand is outpacing your inventory. **{bl} backlog + {inv} on hand**, "
            f"costing **${this_week_backorder:.2f}** in backorder fees this week alone. "
            f"Downstream just asked for **{last_order}** and your supply line is at "
            f"**{sl}**. Lag matters — your order today won't land for ~4 weeks."
        )
    if health == _HEALTH_SURPLUS:
        return (
            f"Inventory is piling up — **{inv} units sitting on the shelf** at "
            f"$0.50/unit/week = **${this_week_holding:.2f}** in holding fees this "
            f"week. Downstream ordered **{last_order}**. Holding is half the cost of "
            f"backorders, but it still adds up."
        )
    # stable
    return (
        f"You're near equilibrium. **${this_week_holding + this_week_backorder:.2f}** "
        f"in costs this week, mostly holding inventory. Downstream just asked for "
        f"**{last_order}**; supply line **{sl}** in transit. Stay alert — small "
        f"changes upstream can amplify by the time they reach you."
    )


def _render_history_chart(orders_placed: tuple[int, ...],
                          orders_received: tuple[int, ...],
                          shipments_received: tuple[int, ...]) -> None:
    """Three traces: what you ordered (you), what you were asked for (demand
    signal from downstream), and what you actually got (supply signal from
    upstream). Lets the player see the lag between asking and receiving — the
    physical mechanism the bullwhip exploits.
    """
    if not orders_placed:
        st.caption("Your history chart will appear after your first order.")
        return

    weeks = list(range(1, len(orders_placed) + 1))
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=weeks,
        y=list(orders_placed),
        mode="lines+markers",
        name="Your orders",
        line=dict(color="#1f77b4", width=3),
    ))
    if orders_received:
        recv_weeks = list(range(1, len(orders_received) + 1))
        fig.add_trace(go.Scatter(
            x=recv_weeks,
            y=list(orders_received),
            mode="lines",
            name="Demand from downstream",
            line=dict(color="#d62728", width=2, dash="dot"),
        ))
    if shipments_received:
        ship_weeks = list(range(1, len(shipments_received) + 1))
        fig.add_trace(go.Scatter(
            x=ship_weeks,
            y=list(shipments_received),
            mode="lines",
            name="Shipments you got",
            line=dict(color="#2ca02c", width=2, dash="dash"),
        ))

    fig.update_layout(
        height=280,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis_title="Week",
        yaxis_title="Units",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0),
        title=dict(text="Your signals over time", x=0.0, xanchor="left",
                   font=dict(size=14)),
    )
    # Don't force a y-range — the prior version forced 3-5 which hid all the
    # action when downstream orders spike to 20-40+.
    st.plotly_chart(fig, key="player_order_history", width="stretch")


# --- Main entry point ------------------------------------------------------ #
def render(state: GameState, on_submit) -> None:
    """Render the per-turn play view.

    Args:
        state: the current GameState. Read paths are constrained to the player's
            own station + ``build_station_view(state, state.player_role)``.
        on_submit: callback invoked when the player clicks "Advance week".
    """
    role = state.player_role
    view = build_station_view(state, role)
    me = state.stations[role.value]

    # Per-turn cost decomposition. The engine's ``cost_history`` is cumulative;
    # we want to surface the *delta* this week so the bleed is felt turn-by-turn.
    this_week_holding, this_week_backorder, this_week_total = _weekly_cost_split(
        view.inventory, view.backlog,
    )
    cumulative = me.cost_history[-1] if me.cost_history else 0.0

    health = _classify_health(view.inventory, view.backlog)

    # PLAY-04: human-readable week counter. state.week is 0-indexed before the
    # player has submitted any order for week N, so the first rendered week
    # reads "Week 1 of 36".
    _render_hero(
        role_name=role.name.title(),
        week=state.week + 1,
        total_weeks=state.total_weeks,
        health=health,
    )

    # Status pill subtitle (one line under the hero strip).
    _, _, subtitle = _HEALTH_LABELS[health]
    st.caption(subtitle)

    st.divider()

    # Two-column main body. Wide layout (set in app.py) gives us ~1100px to
    # work with — splitting roughly 40/60 puts the four status cards in a
    # comfortable left rail and gives the chart the wider half of the screen.
    # The order form sits CENTERED beneath both columns so the player doesn't
    # have to scroll between "read state" and "decide order".
    left, right = st.columns([2, 3], gap="large")

    with left:
        # PLAY-01: status cards. All values derive from ``view`` (engine-
        # sanctioned cross-station projection) or the player's OWN history
        # tuples on me.* — never another station's.
        _render_status_cards(
            view=view,
            station_inventory_history=me.inventory_history,
            station_backlog_history=me.backlog_history,
        )

    with right:
        # The dollar-cost meter.
        _render_money_meter(
            this_week_holding=this_week_holding,
            this_week_backorder=this_week_backorder,
            this_week_total=this_week_total,
            cumulative_total=cumulative,
        )

        # Single-paragraph diagnostic naming what's happening and why it costs.
        # No order suggestion — that would collapse the bullwhip discovery
        # moment (AF-3). Just the dollars and the lag.
        st.info(_diagnostic_message(view, health, this_week_holding, this_week_backorder))

        # PLAY-01: signals chart. Three traces tell the lag story: orders out,
        # demand in, shipments in. Reading me.orders_placed_history etc. is
        # permitted — it's the player's own station's history.
        _render_history_chart(
            orders_placed=me.orders_placed_history,
            orders_received=me.orders_received_history,
            shipments_received=me.shipments_received_history,
        )

    st.divider()

    # PLAY-02: order form, centered beneath both columns via a 1:2:1 spacer
    # so the input itself isn't stretched all the way to 1100px. The whole
    # play-and-decide flow now lives without any vertical scrolling on a
    # standard 1080p display.
    _, center, _ = st.columns([1, 2, 1])
    with center:
        with st.form("turn_form", clear_on_submit=True, border=True):
            st.markdown("##### How many cases will you order this week?")
            st.number_input(
                "Order quantity",
                min_value=0,   # blocks negatives at the UI (Pitfall 5)
                step=1,        # blocks floats (Pitfall 5)
                value=4,       # equilibrium throughput default
                # CRITICAL: key="order_input" matches the read in app.py's
                # submit_order callback. Pitfall 2 — DO NOT pass args= to the
                # form_submit_button; that would capture the value at render
                # time.
                key="order_input",
                label_visibility="collapsed",
                # NO max_value: the canonical bullwhip can drive Factory orders
                # to 30-80+; capping silently truncates (anti-feature AF-4).
            )
            st.form_submit_button(
                "Advance to next week →",
                on_click=on_submit,
                type="primary",
            )
