"""Canonical Beer Game tick — five named steps in fixed order.

SEQUENCE (Sterman 1989, JASSS 17(4):2 section 3):
    receive shipments -> fill orders -> record state -> place new orders -> advance pipelines.

Any rearrangement breaks the bullwhip. The order is asserted by
``tests/test_tick_invariants.py``.

FACTORY ASYMMETRY (critical, see also ``config/scenarios.py`` docstring):
    - Factory's INBOUND order channel (orders FROM Distributor) uses the SAME
      1-week mailing delay as every other inter-echelon order channel —
      ``ORDER_PIPELINE_LEN_FACTORY = 1``, ``Factory.incoming_orders`` is length 1,
      pre-loaded with ``(4,)`` at equilibrium.
    - Factory's OWN order->production path skips the mailing channel: when
      Factory decides to order N this week, N goes directly into Factory's own
      ``_pending_in_shipment`` (consumed in step 5 into its own
      ``incoming_shipments`` back slot), where it sits for
      ``SHIPPING_PIPELINE_LEN = 2`` weeks of production lead time.

TRANSIENT FIELDS — within a single tick:
    - ``_demand_to_fill`` and ``_shipped_this_tick`` are set by step 2 (fill_orders)
      and consumed by step 3 (record_state) to grow the orders_received_history
      and shipments_sent_history.
    - ``_pending_in_shipment`` and ``_pending_in_order`` are set by step 2 and
      step 4 and consumed by step 5 (advance_pipelines) to shift the pipelines.

All transient fields are zeroed by the end of step 5.
"""
from dataclasses import replace
from typing import Callable

from beergame.ai.base import Agent
from beergame.engine.costs import weekly_cost
from beergame.engine.demand import demand_for_week
from beergame.engine.state import (
    GameState,
    Role,
    build_station_view,
    new_game,
)


def _idx(role: Role) -> int:
    return role.value


def receive_shipments(state: GameState) -> GameState:
    """Step 1: add slot-0 of each station's ``incoming_shipments`` to inventory.

    The consumed slot is zeroed in-place; step 5 will shift the queue and
    drop it. We do NOT shift the queue here — that's step 5's job — so that
    step 2 still sees the same shipment length.
    """
    new_stations = []
    for s in state.stations:
        arriving = s.incoming_shipments[0] if s.incoming_shipments else 0
        if s.incoming_shipments:
            new_shipments = (0,) + s.incoming_shipments[1:]
        else:
            new_shipments = ()
        new_stations.append(replace(
            s,
            inventory=s.inventory + arriving,
            incoming_shipments=new_shipments,
        ))
    return replace(state, stations=tuple(new_stations))


def fill_orders(
    state: GameState,
    demand_fn: Callable[[int, int], int] = demand_for_week,
) -> GameState:
    """Step 2: receive this week's incoming order, ship what we can.

    Retailer's order is ``customer_demand(week)``; everyone else (including
    Factory) reads ``incoming_orders[0]`` — the order that was mailed to them
    one tick ago. Each station ships ``min(inventory, demand + backlog)`` to
    the downstream station, updates its post-fill inventory + backlog, and
    stashes transient fields so step 3 can grow the histories and step 5 can
    shift the pipelines.
    """
    next_week = state.week + 1
    customer_demand_this_week = demand_fn(next_week, state.total_weeks)
    new_customer_history = state.customer_demand_history + (customer_demand_this_week,)

    # Pass 1: determine demand each station must fill.
    demands = [0, 0, 0, 0]
    for role in Role:
        i = _idx(role)
        s = state.stations[i]
        if role == Role.RETAILER:
            demands[i] = customer_demand_this_week
        else:
            # Non-Retailer (including Factory): order arrives at slot 0 of incoming_orders.
            demands[i] = s.incoming_orders[0] if s.incoming_orders else 0

    # Pass 2: compute fills + post-fill positions.
    new_stations = list(state.stations)
    shipped = [0, 0, 0, 0]
    post_fill_inv = [0, 0, 0, 0]
    post_fill_bl = [0, 0, 0, 0]
    for role in Role:
        i = _idx(role)
        s = new_stations[i]
        total_need = demands[i] + s.backlog
        shipped[i] = min(s.inventory, total_need)
        post_fill_inv[i] = s.inventory - shipped[i]
        post_fill_bl[i] = total_need - shipped[i]

    # Pass 3: apply post-fill inventory/backlog + stash transients on each station.
    for role in Role:
        i = _idx(role)
        s = new_stations[i]
        new_stations[i] = replace(
            s,
            inventory=post_fill_inv[i],
            backlog=post_fill_bl[i],
            _demand_to_fill=demands[i],
            _shipped_this_tick=shipped[i],
        )

    # Pass 4: route each shipment to its DOWNSTREAM neighbor's _pending_in_shipment.
    # Retailer ships to the external customer — that leaves the system, no enqueue.
    for role in Role:
        i = _idx(role)
        if role == Role.RETAILER:
            continue
        downstream_idx = i - 1
        ds = new_stations[downstream_idx]
        new_stations[downstream_idx] = replace(
            ds,
            _pending_in_shipment=ds._pending_in_shipment + shipped[i],
        )

    return replace(
        state,
        stations=tuple(new_stations),
        customer_demand_history=new_customer_history,
    )


def record_state(state: GameState) -> GameState:
    """Step 3: append post-fill inventory/backlog/orders_received/shipments_sent
    + cumulative cost. Zeroes the ``_demand_to_fill`` / ``_shipped_this_tick``
    transients (step 2 set them, step 3 consumes them).
    """
    new_stations = []
    for s in state.stations:
        w_cost = weekly_cost(s)
        prev_cum = s.cost_history[-1] if s.cost_history else 0.0
        new_stations.append(replace(
            s,
            inventory_history=s.inventory_history + (s.inventory,),
            backlog_history=s.backlog_history + (s.backlog,),
            orders_received_history=s.orders_received_history + (s._demand_to_fill,),
            shipments_sent_history=s.shipments_sent_history + (s._shipped_this_tick,),
            cost_history=s.cost_history + (prev_cum + w_cost,),
            _demand_to_fill=0,
            _shipped_this_tick=0,
        ))
    return replace(state, stations=tuple(new_stations))


def place_orders(
    state: GameState,
    player_order: int,
    ai_agents: dict[Role, Agent],
) -> GameState:
    """Step 4: each station decides this week's order.

    R/W/D route their order to the UPSTREAM station's ``_pending_in_order``
    (sits one tick in ``incoming_orders`` before being filled). Factory routes
    its own order to ITS OWN ``_pending_in_shipment`` — Factory's order is a
    production start, going directly into its own incoming_shipments back slot
    in step 5, where it sits for SHIPPING_PIPELINE_LEN weeks of production.

    The Distributor->Factory order channel is unchanged from R/W/D: Distributor's
    order routes to Factory's ``_pending_in_order``, which then sits in Factory's
    length-1 ``incoming_orders`` pipeline for one tick before being filled.
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

    # Append each station's placed order to its own history.
    for role in Role:
        i = _idx(role)
        s = new_stations[i]
        new_stations[i] = replace(
            s,
            orders_placed_history=s.orders_placed_history + (orders_placed[i],),
        )

    # Route the orders.
    for role in Role:
        i = _idx(role)
        o = orders_placed[i]
        if role == Role.FACTORY:
            fs = new_stations[i]
            new_stations[i] = replace(
                fs,
                _pending_in_shipment=fs._pending_in_shipment + o,
            )
        else:
            up_idx = i + 1
            us = new_stations[up_idx]
            new_stations[up_idx] = replace(
                us,
                _pending_in_order=us._pending_in_order + o,
            )

    return replace(state, stations=tuple(new_stations))


def advance_pipelines(state: GameState) -> GameState:
    """Step 5: shift pipelines forward by one slot. Pending values flow into
    the back slot of each pipeline; all transient fields are zeroed.
    """
    new_stations = []
    for s in state.stations:
        if s.incoming_shipments:
            new_shipments = s.incoming_shipments[1:] + (s._pending_in_shipment,)
        else:
            new_shipments = ()
        if s.incoming_orders:
            new_orders = s.incoming_orders[1:] + (s._pending_in_order,)
        else:
            new_orders = ()
        new_stations.append(replace(
            s,
            incoming_shipments=new_shipments,
            incoming_orders=new_orders,
            _pending_in_shipment=0,
            _pending_in_order=0,
        ))
    next_week = state.week + 1
    new_phase = "done" if next_week >= state.total_weeks else "playing"
    return replace(
        state,
        week=next_week,
        stations=tuple(new_stations),
        phase=new_phase,
    )


def advance_week(
    state: GameState,
    player_order: int,
    ai_agents: dict[Role, Agent],
    demand_fn: Callable[[int, int], int] = demand_for_week,
) -> GameState:
    """Single canonical tick. Returns a NEW ``GameState``.

    SEQUENCE: receive shipments -> fill orders -> record state -> place new
    orders -> advance pipelines.
    """
    assert state.phase == "playing", f"Cannot advance: phase={state.phase}"
    s1 = receive_shipments(state)
    s2 = fill_orders(s1, demand_fn=demand_fn)
    s3 = record_state(s2)
    s4 = place_orders(s3, player_order, ai_agents)
    s5 = advance_pipelines(s4)
    return s5


def is_game_over(state: GameState) -> bool:
    return state.phase == "done"


def simulate_full_game(
    seed: int,
    player_role: Role,
    agents: dict[Role, Agent],
    demand_fn: Callable[[int, int], int] = demand_for_week,
    total_weeks: int | None = None,
) -> GameState:
    """Convenience driver: run all ticks until ``phase == "done"``.

    ``agents`` must include the ``player_role`` (the "player" is treated as
    just another Agent here, which is what GATE 1 and GATE 2 need).

    v1 limitation: ``build_station_view`` at the top of the loop uses last
    week's recorded demand; for week 0 it falls back to
    ``CLASSIC_PRE_STEP_DEMAND``. Both supplied demand_fns (``demand_for_week``,
    ``constant_demand``) start at 4 so this is consistent for v1. A structural
    fix would require threading ``demand_fn`` through ``build_station_view``
    and is deferred to v2.
    """
    kwargs: dict = {"player_role": player_role, "seed": seed}
    if total_weeks is not None:
        kwargs["total_weeks"] = total_weeks
    state = new_game(**kwargs)
    while state.phase == "playing":
        player_view = build_station_view(state, player_role)
        player_order = agents[player_role].decide_order(player_view)
        ai_subset = {r: a for r, a in agents.items() if r != player_role}
        state = advance_week(state, player_order, ai_subset, demand_fn=demand_fn)
    return state
