"""ENG-07: tick executes the five named steps in canonical order:
   receive shipments -> fill orders -> record state -> place new orders -> advance pipelines.
"""
from beergame.ai.base import ConstantOrderAgent
from beergame.engine.demand import constant_demand
from beergame.engine.state import Role, build_station_view, new_game
from beergame.engine.tick import (
    advance_pipelines,
    advance_week,
    fill_orders,
    place_orders,
    receive_shipments,
    record_state,
)


def test_five_steps_callable_in_order():
    """Smoke: each step is a separate function and composes left-to-right."""
    state = new_game(player_role=Role.RETAILER, seed=42)
    s1 = receive_shipments(state)
    s2 = fill_orders(s1, demand_fn=constant_demand)
    s3 = record_state(s2)
    s4 = place_orders(
        s3,
        player_order=4,
        ai_agents={r: ConstantOrderAgent(4) for r in Role if r != Role.RETAILER},
    )
    s5 = advance_pipelines(s4)
    assert s5.week == 1
    # Transient fields zeroed after step 5:
    for st in s5.stations:
        assert st._pending_in_shipment == 0
        assert st._pending_in_order == 0
        assert st._demand_to_fill == 0
        assert st._shipped_this_tick == 0


def test_advance_week_composes_five_steps():
    """advance_week is observationally equivalent to manually invoking the 5 steps."""
    state = new_game(player_role=Role.RETAILER, seed=42)
    agents = {r: ConstantOrderAgent(4) for r in Role}
    ai = {r: agents[r] for r in Role if r != Role.RETAILER}
    manual = advance_pipelines(
        place_orders(
            record_state(fill_orders(receive_shipments(state), demand_fn=constant_demand)),
            player_order=4,
            ai_agents=ai,
        )
    )
    composed = advance_week(state, player_order=4, ai_agents=ai, demand_fn=constant_demand)
    assert manual == composed


def test_record_runs_before_order_decision_agents_see_post_fill_state():
    """The agent's view at order-placement time MUST reflect post-fill inventory.
    We use a spy agent that records the view it was given.
    """
    seen_views = {}

    class SpyAgent:
        def __init__(self, role):
            self.role = role

        def decide_order(self, view):
            seen_views[self.role] = view
            return 4

    state = new_game(player_role=Role.RETAILER, seed=42)
    ai = {
        Role.WHOLESALER: SpyAgent(Role.WHOLESALER),
        Role.DISTRIBUTOR: ConstantOrderAgent(4),
        Role.FACTORY: ConstantOrderAgent(4),
    }
    advance_week(state, player_order=4, ai_agents=ai, demand_fn=constant_demand)
    v = seen_views[Role.WHOLESALER]
    # Wholesaler in equilibrium (constant demand=4): received 4, shipped 4 to retailer,
    # so post-fill inventory == initial 12.
    assert v.inventory == 12, f"agent saw inventory={v.inventory}; expected post-fill 12"
    assert v.backlog == 0


def test_player_order_not_in_own_supply_line_next_tick():
    """A non-Factory player who orders 99 on tick 1 must NOT see 99 in their
    supply_line on tick 2. The order is in the UPSTREAM station's
    incoming_orders queue, not the player's incoming_shipments.
    """
    state = new_game(player_role=Role.WHOLESALER, seed=42)
    ai = {r: ConstantOrderAgent(4) for r in Role if r != Role.WHOLESALER}
    s1 = advance_week(state, player_order=99, ai_agents=ai, demand_fn=constant_demand)
    view = build_station_view(s1, Role.WHOLESALER)
    # Wholesaler's supply_line is sum of its OWN incoming_shipments — should
    # still be ~8 (two slots, each carrying the canonical 4 — no 99-shipment yet).
    # The 99 went into Distributor's incoming_orders pending slot, NOT into
    # Wholesaler's incoming_shipments.
    assert view.supply_line < 99, (
        f"player's own order of 99 leaked into their supply_line "
        f"({view.supply_line}) — tick order is wrong (orders should not fire instantly)."
    )


def test_factory_incoming_orders_canonical_init():
    """Factory's INBOUND order channel uses the canonical 1-week mailing delay
    (ORDER_PIPELINE_LEN_FACTORY=1) — same as R/W/D. At game start, Factory's
    incoming_orders is pre-loaded with (4,) at equilibrium throughput, NOT empty.

    This is the structural fix for the original 'Factory drops upstream orders'
    bug: with ORDER_PIPELINE_LEN_FACTORY=0 + incoming_orders=(), Distributor's
    order to Factory was silently discarded by advance_pipelines (the
    ``else: new_orders = ()`` branch). With the canonical 1-week delay it now
    correctly mails Distributor's orders to Factory.
    """
    state = new_game(player_role=Role.RETAILER, seed=42)
    assert state.stations[Role.FACTORY.value].incoming_orders == (4,), (
        f"Factory incoming_orders should be (4,) at equilibrium init, "
        f"got {state.stations[Role.FACTORY.value].incoming_orders}"
    )
    # After 5 ticks under ConstantOrderAgent(4) + constant demand, the queue STAYS
    # at (4,) because every tick the slot-0 (4,) is consumed in fill_orders,
    # Distributor's just-placed order of 4 lands in _pending_in_order, and
    # advance_pipelines makes incoming_orders=(4,) again.
    agents = {r: ConstantOrderAgent(4) for r in Role}
    for _ in range(5):
        state = advance_week(
            state,
            player_order=4,
            ai_agents={r: agents[r] for r in Role if r != Role.RETAILER},
            demand_fn=constant_demand,
        )
    assert state.stations[Role.FACTORY.value].incoming_orders == (4,), (
        f"Factory incoming_orders should stay (4,) under equilibrium for 5 ticks, "
        f"got {state.stations[Role.FACTORY.value].incoming_orders}"
    )


def test_initial_state_is_canonical_equilibrium():
    """ENG-06: new_game produces inventory=12, backlog=0, every pipeline slot
    pre-loaded with 4 AT EVERY STATION INCLUDING FACTORY (Factory's
    incoming_orders=(4,), not empty).
    """
    state = new_game(player_role=Role.RETAILER, seed=42)
    for s in state.stations:
        assert s.inventory == 12
        assert s.backlog == 0
        assert all(slot == 4 for slot in s.incoming_shipments)
        assert s.incoming_orders == (4,), (
            f"{s.role.name}: incoming_orders should be (4,), got {s.incoming_orders}"
        )
    assert state.week == 0
    assert state.phase == "playing"
    assert state.customer_demand_history == ()


def test_factory_inventory_stays_at_12_under_constant_demand():
    """Tick 1 trace (the BLOCKER 1 fix verification): with
    ORDER_PIPELINE_LEN_FACTORY=1 and Factory.incoming_orders=(4,) at init,
    under all-ConstantOrderAgent(4) and constant customer demand=4, Factory
    inventory MUST stay at 12 after tick 1 (NOT 16, which was the
    broken-design symptom).

    Walkthrough:
      - Step 1: Factory.inventory = 12 + 4 = 16
      - Step 2: Factory faces order from incoming_orders[0] = 4. Ships
                min(16, 4)=4 to Distributor. Factory.inventory = 16 - 4 = 12.
      - Step 3: records inventory=12, backlog=0.

    With the old broken design (Factory.incoming_orders=()), step 2's
    ``demands[FACTORY] = s.incoming_orders[0] if s.incoming_orders else 0`` = 0,
    so Factory shipped 0 and inventory ended at 16. Distributor never got restocked.
    """
    state = new_game(player_role=Role.RETAILER, seed=42)
    agents = {r: ConstantOrderAgent(4) for r in Role}
    s1 = advance_week(
        state,
        player_order=4,
        ai_agents={r: agents[r] for r in Role if r != Role.RETAILER},
        demand_fn=constant_demand,
    )
    factory = s1.stations[Role.FACTORY.value]
    assert factory.inventory == 12, (
        f"Factory inventory should be 12 after tick 1 (received 4, shipped 4 to "
        f"Distributor); got {factory.inventory}. If this is 16, "
        f"ORDER_PIPELINE_LEN_FACTORY is wrong or Factory.incoming_orders is not "
        f"pre-loaded with (4,)."
    )
    distributor = s1.stations[Role.DISTRIBUTOR.value]
    assert distributor.incoming_shipments == (4, 4), (
        f"Distributor should have received shipment of 4 from Factory; "
        f"got incoming_shipments={distributor.incoming_shipments}"
    )
