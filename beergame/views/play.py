"""Per-turn play view — PLAY-01..05.

This is the heart of the human-playable loop. Each rerun renders the player's
current station view via ``build_station_view`` (the ONLY allowed cross-station
read path — engine-enforced visibility from Phase 1's ENG-10 + Plan 02-01's
``last_shipment_received`` addition), shows the five locally-knowable metrics,
plots the player's own order history, and exposes an ``st.form`` with a single
``st.number_input`` + "Advance week" submit button.

PLAY-03 enforcement: this view NEVER reads ``state.stations[i]`` for any
``i != state.player_role.value`` (other-station data is engine-private), and
NEVER reads ``state.customer_demand_history`` (that would leak future weeks
even for the Retailer mid-game). The only allowed reads from ``state`` are:
    - ``state.week`` and ``state.total_weeks`` (week counter — PLAY-04).
    - ``state.player_role`` (which station to project).
    - ``state.stations[role.value]`` (the player's OWN station — only for
      ``orders_placed_history``, which is intrinsically the player's own data).
All other cross-station info flows through ``build_station_view(state, role)``.

The order form follows Pitfall 12 (form batches keystrokes so reruns don't
fire on every digit) and Pitfall 2 (the ``key="order_input"`` matches the
``st.session_state["order_input"]`` read in ``app.py::submit_order`` — args=
would capture the value at render time, not submit time).
"""
import plotly.graph_objects as go
import streamlit as st

from beergame.engine.state import GameState, build_station_view


def render(state: GameState, on_submit) -> None:
    """Render the per-turn play view.

    Args:
        state: the current GameState. Read paths are constrained to the player's
            own station + ``build_station_view(state, state.player_role)``.
        on_submit: callback invoked when the player clicks "Advance week" —
            ``app.py`` binds this to ``submit_order``, which reads the order via
            ``st.session_state["order_input"]`` and calls ``advance_week``.
    """
    role = state.player_role
    view = build_station_view(state, role)

    # PLAY-04: human-readable week counter. state.week is 0-indexed; before the
    # player has submitted any order for week N, state.week == N-1, so the
    # first rendered week reads "Week 1 of 36".
    st.title(
        f":beer_mug: Week {state.week + 1} of {state.total_weeks} "
        f"— You are the {role.name.title()}"
    )

    # PLAY-01: five metrics covering the player's locally-knowable position.
    # All five derive from ``view`` (which is the only engine-sanctioned cross-
    # station projection). No information leak — every value is something this
    # station could physically observe in the real game.
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Inventory on hand", view.inventory)
        st.metric("Backlog", view.backlog)
    with col2:
        st.metric("Last shipment received", view.last_shipment_received)
        st.metric("Last order from downstream", view.last_order_received)

    st.metric("Units in transit to you (supply line)", view.supply_line)

    # PLAY-01: order-history mini-chart of the player's OWN placed orders.
    # Reading ``state.stations[role.value]`` is permitted here because it's
    # the player's own station, and ``orders_placed_history`` is intrinsically
    # the player's own data (they placed the orders). The PLAY-03 rule against
    # cross-station reads applies to OTHER stations, not the player's own.
    me = state.stations[role.value]
    if me.orders_placed_history:
        weeks = list(range(1, len(me.orders_placed_history) + 1))
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=weeks,
            y=list(me.orders_placed_history),
            mode="lines+markers",
            name="Your orders",
        ))
        fig.update_layout(
            height=200,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_title="Week",
            yaxis_title="Order qty",
            showlegend=False,
            title=dict(text="Your orders so far", x=0.0, xanchor="left"),
        )
        # width="stretch" (NOT use_container_width=True — deprecated in 1.57.0,
        # Pitfall 4). key= gives the chart a stable identity across reruns so
        # Plotly preserves zoom/hover state (Pitfall 3 flicker mitigation).
        # X-axis extends to len(orders_placed_history), NEVER hard-coded to 36
        # (Pitfall 18 — would imply future weeks the player hasn't played).
        st.plotly_chart(fig, key="player_order_history", width="stretch")
    else:
        st.caption("Your order-history chart will appear after your first order.")

    # PLAY-02: order form. st.form batches the rerun so reruns don't fire on
    # every keystroke (Pitfall 12). clear_on_submit=True resets the input to
    # value=4 after each submit so the player consciously decides each week.
    with st.form("turn_form", clear_on_submit=True):
        st.number_input(
            "Your order this week",
            min_value=0,   # blocks negatives at the UI (Pitfall 5)
            step=1,        # blocks floats (Pitfall 5)
            value=4,       # equilibrium throughput default
            # CRITICAL: key="order_input" matches the read in app.py's
            # submit_order callback. Pitfall 2 — DO NOT pass args= to the
            # form_submit_button; that would capture the value at render time.
            key="order_input",
            # NO max_value: the canonical bullwhip can drive Factory orders to
            # 30-80+; capping silently truncates (anti-feature AF-4 in research).
        )
        st.form_submit_button(
            "Advance week",
            on_click=on_submit,
            type="primary",
        )
