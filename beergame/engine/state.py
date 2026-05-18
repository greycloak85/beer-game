"""Canonical Beer Game state model.

All state is frozen + slotted. Use ``dataclasses.replace`` to derive new states.
Mutation is never allowed; every tick step returns a fresh ``GameState``.

Roles are an integer-valued ``Enum`` so that ``role.value`` indexes
``GameState.stations`` (tuple of length 4). Order matters:
    RETAILER (0) -> WHOLESALER (1) -> DISTRIBUTOR (2) -> FACTORY (3)
Downstream index = i - 1, upstream index = i + 1 (Factory has no upstream).
"""
from dataclasses import dataclass, field
from enum import Enum

from beergame.config.scenarios import (
    CLASSIC_PRE_STEP_DEMAND,
    DEFAULT_SEED,
    EQUILIBRIUM_THROUGHPUT,
    INITIAL_BACKLOG,
    INITIAL_INVENTORY,
    ORDER_PIPELINE_LEN_FACTORY,
    ORDER_PIPELINE_LEN_RWD,
    RECENT_ORDERS_WINDOW,
    SHIPPING_PIPELINE_LEN,
    TOTAL_WEEKS,
)


class Role(Enum):
    """Integer-valued so ``role.value`` indexes into ``GameState.stations``."""
    RETAILER = 0
    WHOLESALER = 1
    DISTRIBUTOR = 2
    FACTORY = 3


@dataclass(frozen=True, slots=True)
class StationState:
    """A single echelon's state. All history tuples grow by one entry per tick
    (in step 3, record_state). Transient ``_pending_*`` and ``_demand_to_fill`` /
    ``_shipped_this_tick`` fields carry data between tick steps within a single tick
    and are zeroed at end of step 5 / step 3 respectively.
    """
    role: Role
    inventory: int
    backlog: int
    incoming_shipments: tuple[int, ...]
    incoming_orders: tuple[int, ...]

    inventory_history: tuple[int, ...]
    backlog_history: tuple[int, ...]
    orders_placed_history: tuple[int, ...]
    orders_received_history: tuple[int, ...]
    shipments_sent_history: tuple[int, ...]
    shipments_received_history: tuple[int, ...]
    cost_history: tuple[float, ...]

    # Transient fields — set by one step and consumed by a later step in the
    # same tick. ``compare=False`` keeps equality based on observable state only.
    _pending_in_shipment: int = field(default=0, repr=False, compare=False)
    _pending_in_order: int = field(default=0, repr=False, compare=False)
    _demand_to_fill: int = field(default=0, repr=False, compare=False)
    _shipped_this_tick: int = field(default=0, repr=False, compare=False)
    _pending_shipment_received: int = field(default=0, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class GameState:
    week: int
    total_weeks: int
    seed: int
    player_role: Role
    stations: tuple[StationState, ...]
    customer_demand_history: tuple[int, ...]
    phase: str  # "playing" | "done"


@dataclass(frozen=True, slots=True)
class StationView:
    """The slice of state an agent (or non-Retailer player) is allowed to see.

    Deliberately omits ``customer_demand``: only the Retailer can observe the
    external customer. ``RetailerView`` extends this with that one field.
    """
    role: Role
    week: int
    inventory: int
    backlog: int
    supply_line: int                   # sum of incoming_shipments
    last_order_received: int           # most recent orders_received entry
    recent_orders_received: tuple[int, ...]
    # Defaulted so RetailerView (which adds another defaulted field) keeps a
    # valid frozen-dataclass field order under inheritance.
    last_shipment_received: int = 0    # most recent shipments_received entry


@dataclass(frozen=True, slots=True)
class RetailerView(StationView):
    """Retailer is the only role that observes external customer demand."""
    customer_demand: int = 0


def new_game(
    player_role: Role,
    seed: int = DEFAULT_SEED,
    total_weeks: int = TOTAL_WEEKS,
) -> GameState:
    """Build the canonical equilibrium initial state.

    Every station: inventory=12, backlog=0, shipping pipeline pre-loaded with
    ``(4, 4)``. Every station — INCLUDING the Factory — has an inbound order
    queue pre-loaded with ``(4,)`` (length 1, the standard one-week mailing
    delay). Factory's inbound order channel uses the canonical mailing delay
    just like R/W/D; the "no order delay at Factory" phrase from the literature
    refers only to Factory's own order->production path, NOT to the
    Distributor->Factory inbound channel.
    """
    factory_order_pipeline_len = ORDER_PIPELINE_LEN_FACTORY  # = 1, same as R/W/D

    stations: list[StationState] = []
    for role in Role:
        if role == Role.FACTORY:
            inbound_order_pipeline = (EQUILIBRIUM_THROUGHPUT,) * factory_order_pipeline_len
        else:
            inbound_order_pipeline = (EQUILIBRIUM_THROUGHPUT,) * ORDER_PIPELINE_LEN_RWD
        stations.append(StationState(
            role=role,
            inventory=INITIAL_INVENTORY,
            backlog=INITIAL_BACKLOG,
            incoming_shipments=(EQUILIBRIUM_THROUGHPUT,) * SHIPPING_PIPELINE_LEN,
            incoming_orders=inbound_order_pipeline,
            inventory_history=(),
            backlog_history=(),
            orders_placed_history=(),
            orders_received_history=(),
            shipments_sent_history=(),
            shipments_received_history=(),
            cost_history=(),
        ))

    return GameState(
        week=0,
        total_weeks=total_weeks,
        seed=seed,
        player_role=player_role,
        stations=tuple(stations),
        customer_demand_history=(),
        phase="playing",
    )


def build_station_view(state: GameState, role: Role) -> StationView:
    """Project the public-to-this-station slice of ``state``.

    Returns a ``RetailerView`` (with ``customer_demand``) for the Retailer;
    a plain ``StationView`` (no ``customer_demand`` attribute) for everyone else.
    """
    s = state.stations[role.value]
    last_order_received = (
        s.orders_received_history[-1]
        if s.orders_received_history
        else EQUILIBRIUM_THROUGHPUT
    )
    last_shipment_received = (
        s.shipments_received_history[-1]
        if s.shipments_received_history
        else EQUILIBRIUM_THROUGHPUT
    )
    supply_line = sum(s.incoming_shipments)
    recent_orders_received = s.orders_received_history[-RECENT_ORDERS_WINDOW:]

    if role == Role.RETAILER:
        customer_demand = (
            state.customer_demand_history[-1]
            if state.customer_demand_history
            else CLASSIC_PRE_STEP_DEMAND
        )
        return RetailerView(
            role=role,
            week=state.week,
            inventory=s.inventory,
            backlog=s.backlog,
            supply_line=supply_line,
            last_order_received=last_order_received,
            recent_orders_received=recent_orders_received,
            last_shipment_received=last_shipment_received,
            customer_demand=customer_demand,
        )
    return StationView(
        role=role,
        week=state.week,
        inventory=s.inventory,
        backlog=s.backlog,
        supply_line=supply_line,
        last_order_received=last_order_received,
        recent_orders_received=recent_orders_received,
        last_shipment_received=last_shipment_received,
    )
