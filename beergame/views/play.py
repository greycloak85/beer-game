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

from beergame.config.costs import (
    BACKORDER_COST,
    HOLDING_COST,
    REVENUE_PER_UNIT_SHIPPED,
)
from beergame.engine.state import GameState, build_station_view


# CSS injected once per rerun to bump font sizes on st.metric, st.caption,
# st.info, and our bordered cards. Streamlit's defaults are sized for compact
# dashboards; this is a game UI that needs to be readable from across the room.
_PLAY_CSS = """
<style>
/* Bigger metric values (the dollar numbers in the money meter) */
[data-testid="stMetricValue"] {
    font-size: 3.8rem !important;
    font-weight: 700 !important;
}
[data-testid="stMetricLabel"] {
    font-size: 1.9rem !important;
}
/* Make captions a touch more legible */
[data-testid="stCaptionContainer"], .stCaption {
    font-size: 1.8rem !important;
}
/* Info / success / warning boxes — bump body text */
[data-testid="stAlert"] {
    font-size: 2.1rem !important;
    padding: 1.4rem 1.6rem !important;
    line-height: 1.45 !important;
}
/* Big-number font used in the status cards — applied via a custom class */
.bg-bignum {
    font-size: 6.8rem !important;
    font-weight: 700 !important;
    line-height: 1.05 !important;
    margin: 0.15rem 0 0.25rem 0 !important;
}
.bg-bignum-red    { color: #ff5d6a !important; }
.bg-bignum-orange { color: #ffa94d !important; }
.bg-bignum-green  { color: #4ade80 !important; }
.bg-bignum-blue   { color: #60a5fa !important; }
.bg-bignum-gray   { color: #cfd2d6 !important; }
.bg-cardlabel {
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-size: 1.56rem;
    color: #9aa0a6;
    font-weight: 600;
}
.bg-cardfoot {
    font-size: 1.7rem;
    color: #b8bcc2;
}
/* P&L meter cells — bigger than st.metric, color-coded by sign */
.pnl-cell {
    padding: 0.9rem 1.1rem;
    border-radius: 10px;
    background: #1a1e25;
    border: 1px solid #2a2f38;
}
.pnl-label {
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-size: 1.56rem;
    color: #9aa0a6;
    font-weight: 600;
}
.pnl-value {
    font-size: 3.6rem;
    font-weight: 700;
    line-height: 1.2;
    margin-top: 0.2rem;
}
.pnl-value-big {
    font-size: 4.8rem;
    font-weight: 700;
    line-height: 1.1;
    margin-top: 0.2rem;
}
.pnl-green  { color: #4ade80; }
.pnl-red    { color: #ff5d6a; }
.pnl-gray   { color: #cfd2d6; }
.pnl-foot {
    font-size: 1.6rem;
    color: #9aa0a6;
    margin-top: 0.2rem;
}
/* Order input — much larger numerals so 4 vs 40 vs 400 isn't a squint */
[data-testid="stNumberInput"] input {
    font-size: 3.2rem !important;
    font-weight: 600 !important;
    height: 5rem !important;
}
/* Form submit button — bigger, bolder */
[data-testid="stFormSubmitButton"] button {
    font-size: 2.2rem !important;
    font-weight: 600 !important;
    padding: 1rem 2rem !important;
}
</style>
"""


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


# --- Cost + P&L helpers ---------------------------------------------------- #
def _weekly_cost_split(inventory: int, backlog: int) -> tuple[float, float, float]:
    """Replicates ``engine.costs.weekly_cost`` but exposes the holding vs
    backorder split so the UI can name where the bleed is coming from.
    """
    holding = HOLDING_COST * max(0, inventory)
    backorder = BACKORDER_COST * backlog
    return holding, backorder, holding + backorder


def _pnl_snapshot(shipments_sent: tuple[int, ...],
                  cost_history: tuple[float, ...]) -> dict:
    """Compute the per-week and cumulative P&L for the player's station.

    Revenue model is a UI-side concept (see beergame/config/costs.py):
    each unit shipped downstream pays REVENUE_PER_UNIT_SHIPPED. Cost is the
    engine's already-recorded holding + backorder cost. Net = revenue - cost.

    Returns a dict with this-week and cumulative figures so the meter and the
    hero strip both render the same numbers without recomputing.
    """
    cum_shipped = sum(shipments_sent)
    cum_revenue = cum_shipped * REVENUE_PER_UNIT_SHIPPED
    cum_cost = cost_history[-1] if cost_history else 0.0
    cum_net = cum_revenue - cum_cost

    if shipments_sent:
        this_week_shipped = shipments_sent[-1]
        this_week_revenue = this_week_shipped * REVENUE_PER_UNIT_SHIPPED
    else:
        this_week_shipped = 0
        this_week_revenue = 0.0

    if len(cost_history) >= 2:
        this_week_cost = cost_history[-1] - cost_history[-2]
    elif cost_history:
        this_week_cost = cost_history[0]
    else:
        this_week_cost = 0.0

    this_week_net = this_week_revenue - this_week_cost

    return {
        "this_week_shipped": this_week_shipped,
        "this_week_revenue": this_week_revenue,
        "this_week_cost": this_week_cost,
        "this_week_net": this_week_net,
        "cum_revenue": cum_revenue,
        "cum_cost": cum_cost,
        "cum_net": cum_net,
        "cum_shipped": cum_shipped,
    }


def _pnl_class(value: float) -> str:
    """Sign-to-color CSS class. Zero is grey, positive green, negative red."""
    if value > 0.01:
        return "pnl-green"
    if value < -0.01:
        return "pnl-red"
    return "pnl-gray"


def _signed_dollars(value: float) -> str:
    """Format a dollar value with an explicit sign so winning vs losing is
    unambiguous at a glance. +$24.50 / -$187.00 / $0.00."""
    if value > 0.01:
        return f"+${value:,.2f}"
    if value < -0.01:
        return f"-${abs(value):,.2f}"
    return "$0.00"


# --- Hero + cards ---------------------------------------------------------- #
def _render_hero(role_name: str, week: int, total_weeks: int,
                  health: str, cum_net: float) -> None:
    """Role + week + running P&L + status pill. Three cells across the top so
    the player can see at a glance: who they are, how much money they're up or
    down, and how their station's state is trending.
    """
    label, _color, _ = _HEALTH_LABELS[health]
    left, mid, right = st.columns([3, 2, 2])
    with left:
        st.markdown(
            f"<div style='font-size:4.4rem;font-weight:700;line-height:1.1;'>"
            f"\U0001F37A {role_name} "
            f"<span style='opacity:0.55;font-weight:500;font-size:0.7em;'>"
            f"· Week {week} of {total_weeks}</span></div>",
            unsafe_allow_html=True,
        )
    with mid:
        # Cumulative P&L — the headline scoreboard number.
        pnl_class = _pnl_class(cum_net)
        st.markdown(
            f"<div style='text-align:center;line-height:1.15;'>"
            f"<div class='pnl-label' style='text-align:center;'>NET PROFIT</div>"
            f"<div class='pnl-value-big {pnl_class}'>{_signed_dollars(cum_net)}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with right:
        # Health pill on the far right.
        st.markdown(
            f"<div style='text-align:right;font-size:3.6rem;font-weight:700;"
            f"color:{_PILL_CSS_COLOR[health]};letter-spacing:0.08em;"
            f"line-height:1.4;'>"
            f"● {label}</div>",
            unsafe_allow_html=True,
        )


# CSS color names map (Streamlit's :color[] markdown supports named colors but
# the inline HTML pill above needs a real CSS color).
_PILL_CSS_COLOR = {
    _HEALTH_CRISIS:   "#ff5d6a",   # vivid red — pops on dark background
    _HEALTH_STRAINED: "#ffa94d",
    _HEALTH_STABLE:   "#4ade80",
    _HEALTH_SURPLUS:  "#60a5fa",
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


def _bignum(value, color: str) -> str:
    """Render an HTML big-number block via the .bg-bignum CSS class.
    ``color`` is one of red / orange / green / blue / gray (matches the CSS
    color modifiers defined in _PLAY_CSS).
    """
    return (
        f"<div class='bg-bignum bg-bignum-{color}'>{value}</div>"
    )


def _cardlabel(text: str) -> str:
    return f"<div class='bg-cardlabel'>{text}</div>"


def _cardfoot(text: str) -> str:
    return f"<div class='bg-cardfoot'>{text}</div>"


def _render_status_cards(view, station_inventory_history: tuple[int, ...],
                          station_backlog_history: tuple[int, ...]) -> None:
    """Four bordered cards arranged in a 2x2 grid inside the caller's column.
    Big-number CSS class scales the value to ~3.4rem (vs Streamlit's default
    h1 of ~2rem), so the player can read the state at a glance without
    leaning into the screen.
    """
    inv = view.inventory
    bl = view.backlog

    inv_color = "red" if inv == 0 else ("orange" if inv < 4 else "green" if inv <= 30 else "blue")
    bl_color = "red" if bl >= 20 else ("orange" if bl >= 5 else "green" if bl == 0 else "gray")

    row1_left, row1_right = st.columns(2)
    with row1_left:
        with st.container(border=True):
            st.markdown(_cardlabel("On-hand inventory"), unsafe_allow_html=True)
            st.markdown(_bignum(inv, inv_color), unsafe_allow_html=True)
            inv_delta = _trend_delta(station_inventory_history)
            st.markdown(_cardfoot(inv_delta or "first week"), unsafe_allow_html=True)
    with row1_right:
        with st.container(border=True):
            st.markdown(_cardlabel("Backlog (unfilled orders)"), unsafe_allow_html=True)
            st.markdown(_bignum(bl, bl_color), unsafe_allow_html=True)
            bl_delta = _trend_delta(station_backlog_history)
            st.markdown(_cardfoot(bl_delta or "first week"), unsafe_allow_html=True)

    row2_left, row2_right = st.columns(2)
    with row2_left:
        with st.container(border=True):
            st.markdown(_cardlabel("Shipment just arrived"), unsafe_allow_html=True)
            st.markdown(_bignum(view.last_shipment_received, "gray"),
                        unsafe_allow_html=True)
            st.markdown(
                _cardfoot(f"Supply line: <b>{view.supply_line}</b> in transit"),
                unsafe_allow_html=True,
            )
    with row2_right:
        with st.container(border=True):
            st.markdown(_cardlabel("Order from downstream"), unsafe_allow_html=True)
            order_pulse_color = ("red" if view.last_order_received >= 20
                                 else "orange" if view.last_order_received >= 10
                                 else "gray")
            st.markdown(_bignum(view.last_order_received, order_pulse_color),
                        unsafe_allow_html=True)
            recent = view.recent_orders_received
            if len(recent) >= 2:
                pulse = recent[-1] - recent[0]
                if pulse > 0:
                    foot = (f"<span style='color:#ff8b94'>+{pulse} vs "
                            f"{len(recent)}w ago</span> — demand climbing")
                elif pulse < 0:
                    foot = (f"<span style='color:#4ade80'>{pulse} vs "
                            f"{len(recent)}w ago</span> — demand cooling")
                else:
                    foot = "steady demand"
            else:
                foot = "first reading"
            st.markdown(_cardfoot(foot), unsafe_allow_html=True)


def _render_pnl_meter(pnl: dict) -> None:
    """Profit-and-loss meter — revenue from shipping, cost of carrying
    inventory + backlog, net (the score). Big-number, color-coded cells so
    winning vs losing is obvious at a glance.
    """
    with st.container(border=True):
        st.markdown(
            "<div style='font-weight:600;font-size:2.1rem;margin-bottom:0.5rem;'>"
            "\U0001F4B0 This week's P&amp;L"
            "</div>",
            unsafe_allow_html=True,
        )
        a, b, c, d = st.columns(4)

        with a:
            st.markdown(
                f"<div class='pnl-cell'>"
                f"<div class='pnl-label'>REVENUE</div>"
                f"<div class='pnl-value pnl-green'>"
                f"+${pnl['this_week_revenue']:,.2f}</div>"
                f"<div class='pnl-foot'>{pnl['this_week_shipped']} cases shipped "
                f"× ${REVENUE_PER_UNIT_SHIPPED:.2f}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with b:
            st.markdown(
                f"<div class='pnl-cell'>"
                f"<div class='pnl-label'>COSTS</div>"
                f"<div class='pnl-value pnl-red'>"
                f"-${pnl['this_week_cost']:,.2f}</div>"
                f"<div class='pnl-foot'>holding + backorder fees</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with c:
            net_class = _pnl_class(pnl['this_week_net'])
            verdict = ("WINNING" if pnl['this_week_net'] > 0.01
                       else "LOSING" if pnl['this_week_net'] < -0.01
                       else "BREAK-EVEN")
            st.markdown(
                f"<div class='pnl-cell'>"
                f"<div class='pnl-label'>NET THIS WEEK</div>"
                f"<div class='pnl-value {net_class}'>"
                f"{_signed_dollars(pnl['this_week_net'])}</div>"
                f"<div class='pnl-foot'>{verdict}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with d:
            cum_class = _pnl_class(pnl['cum_net'])
            st.markdown(
                f"<div class='pnl-cell'>"
                f"<div class='pnl-label'>GAME TOTAL</div>"
                f"<div class='pnl-value {cum_class}'>"
                f"{_signed_dollars(pnl['cum_net'])}</div>"
                f"<div class='pnl-foot'>"
                f"${pnl['cum_revenue']:,.0f} rev − ${pnl['cum_cost']:,.0f} cost"
                f"</div>"
                f"</div>",
                unsafe_allow_html=True,
            )


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
    # Section header lives OUTSIDE the Plotly figure so it doesn't collide
    # with the horizontal legend (which sits at y=1.04 inside the figure).
    st.markdown(
        "<div style='font-weight:600;font-size:2.1rem;margin:0.6rem 0 0.4rem 0;'>"
        "\U0001F4C8 Your signals over time"
        "</div>",
        unsafe_allow_html=True,
    )

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
        line=dict(color="#60a5fa", width=7),
        marker=dict(size=14),
    ))
    if orders_received:
        recv_weeks = list(range(1, len(orders_received) + 1))
        fig.add_trace(go.Scatter(
            x=recv_weeks,
            y=list(orders_received),
            mode="lines+markers",
            name="Demand from downstream",
            line=dict(color="#ff5d6a", width=7, dash="dot"),
            marker=dict(size=13),
        ))
    if shipments_received:
        ship_weeks = list(range(1, len(shipments_received) + 1))
        fig.add_trace(go.Scatter(
            x=ship_weeks,
            y=list(shipments_received),
            mode="lines+markers",
            name="Shipments you got",
            line=dict(color="#4ade80", width=7, dash="dash"),
            marker=dict(size=13),
        ))

    fig.update_layout(
        template="plotly_dark",
        # Match the secondaryBackgroundColor from config.toml so the chart
        # blends seamlessly with the surrounding cards.
        paper_bgcolor="#222730",
        plot_bgcolor="#222730",
        height=460,
        margin=dict(l=30, r=30, t=70, b=40),
        font=dict(size=30, color="#E8EAED"),
        xaxis=dict(
            title=dict(text="Week", font=dict(size=30)),
            tickfont=dict(size=28),
            gridcolor="#2e333c",
        ),
        yaxis=dict(
            title=dict(text="Units", font=dict(size=30)),
            tickfont=dict(size=28),
            gridcolor="#2e333c",
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.04,
            xanchor="left", x=0.0,
            font=dict(size=28),
        ),
        # No in-figure title — it would collide with the horizontal legend.
        # The section header is rendered above the chart via st.markdown so
        # both elements have their own space.
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
    # Inject typography CSS once per rerun. Streamlit dedupes identical
    # <style> blocks so this is cheap even though it fires every script run.
    st.markdown(_PLAY_CSS, unsafe_allow_html=True)

    role = state.player_role
    view = build_station_view(state, role)
    me = state.stations[role.value]

    # Per-turn cost decomposition. The engine's ``cost_history`` is cumulative;
    # we want to surface the *delta* this week so the bleed is felt turn-by-turn.
    this_week_holding, this_week_backorder, this_week_total = _weekly_cost_split(
        view.inventory, view.backlog,
    )

    # P&L snapshot — render-only scoring concept layered on top of the engine's
    # cost ledger. Revenue model in beergame/config/costs.py.
    pnl = _pnl_snapshot(
        shipments_sent=state.stations[role.value].shipments_sent_history,
        cost_history=me.cost_history,
    )

    health = _classify_health(view.inventory, view.backlog)

    # PLAY-04: human-readable week counter. state.week is 0-indexed before the
    # player has submitted any order for week N, so the first rendered week
    # reads "Week 1 of 36".
    _render_hero(
        role_name=role.name.title(),
        week=state.week + 1,
        total_weeks=state.total_weeks,
        health=health,
        cum_net=pnl["cum_net"],
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
        # P&L meter — the winning/losing scoreboard.
        _render_pnl_meter(pnl)

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
            st.markdown(
                "<div style='font-weight:600;font-size:2.4rem;"
                "margin-bottom:0.6rem;'>"
                "How many cases will you order this week?</div>",
                unsafe_allow_html=True,
            )
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
