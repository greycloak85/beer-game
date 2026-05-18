"""GATE 1: Equilibrium regression test (AI-04 + ENG-06).

Setup: customer demand is constant at 4 cases/week for all 36 weeks; all four
stations are played by ConstantOrderAgent(4). The canonical initial state has
inventory=12, backlog=0, every pipeline slot pre-loaded with 4 (INCLUDING
Factory's incoming_orders=(4,) -- the BLOCKER 1 fix).

Expected: every station's inventory_history is exactly (12,)*36 and
backlog_history is exactly (0,)*36 and orders_placed_history is exactly (4,)*36.
The system NEVER leaves equilibrium.

Why this gate uses ConstantOrderAgent(4) (NOT ShipmentAnchorAndAdjustAgent):
Empirical Sterman at a perfectly-equilibrated view evaluates to round(2.58) = 3
(see beergame/ai/sterman.py docstring), so "inventory==12 every week AND
orders==4 every week" is mutually unsatisfiable under empirical Sterman.
GATE 1 isolates engine arithmetic from heuristic drift; GATE 2 (test_bullwhip_emerges)
is the actual Sterman test.

Why this gate exists: it's the single most sensitive test of the Phase 1
engine arithmetic. Any of the following bugs makes this test fail:
  - Wrong initial inventory or backlog (ENG-06)
  - Empty initial pipeline slots (ENG-06)
  - ORDER_PIPELINE_LEN_FACTORY != 1 or Factory.incoming_orders != (4,) at init
    (the BLOCKER 1 fix -- Distributor->Factory order channel must use canonical
    1-week mailing delay; orders to Factory must NOT be discarded)
  - Wrong tick order, e.g., place_orders before record_state (ENG-07)
  - Lead-time queue off-by-one (any of ENG-04 / ENG-07)
  - Backlog accumulating spuriously (ENG-08)

The test is intentionally strict (== 12 every week, == 4 every order, exact
per-week cost) because a "close but not exactly 12" result indicates a bug
that GATE 2 will then amplify into a wrong bullwhip ratio.
"""
import pytest

from beergame.engine.tick import simulate_full_game
from beergame.engine.state import Role
from beergame.engine.demand import constant_demand
from beergame.config.scenarios import INITIAL_INVENTORY, TOTAL_WEEKS
from beergame.config.costs import HOLDING_COST
from beergame.ai.base import ConstantOrderAgent


def _all_constant_4_agents() -> dict[Role, ConstantOrderAgent]:
    """Fresh ConstantOrderAgent(4) per role. These are stateless -- each call returns 4."""
    return {r: ConstantOrderAgent(4) for r in Role}


def test_equilibrium_constant_demand_constant_orders():
    """AI-04: constant demand=4, all stations ConstantOrderAgent(4) -> inventory=12, backlog=0
    for all 36 weeks. Tests pure engine arithmetic with no heuristic drift."""
    final = simulate_full_game(
        seed=42, player_role=Role.RETAILER,
        agents=_all_constant_4_agents(),
        demand_fn=constant_demand,
    )

    assert final.week == TOTAL_WEEKS
    assert final.phase == "done"

    for station in final.stations:
        inv = station.inventory_history
        bl = station.backlog_history
        assert len(inv) == TOTAL_WEEKS, (
            f"{station.role.name}: inventory_history has {len(inv)} entries, expected {TOTAL_WEEKS}"
        )
        assert len(bl) == TOTAL_WEEKS, (
            f"{station.role.name}: backlog_history has {len(bl)} entries, expected {TOTAL_WEEKS}"
        )
        assert all(v == INITIAL_INVENTORY for v in inv), (
            f"{station.role.name}: inventory drifted from {INITIAL_INVENTORY}. "
            f"History: {inv}.\n"
            "Likely causes (in order):\n"
            "  1. ORDER_PIPELINE_LEN_FACTORY != 1 or Factory.incoming_orders != (4,) "
            "at init -- Distributor's orders to Factory are being silently discarded "
            "(BLOCKER 1 regression).\n"
            "  2. Wrong tick order (ENG-07) -- try test_tick_invariants first.\n"
            "  3. Pipeline off-by-one (ENG-04).\n"
            "  4. ConstantOrderAgent is somehow not returning 4 -- check beergame/ai/base.py."
        )
        assert all(v == 0 for v in bl), (
            f"{station.role.name}: backlog accumulated under equilibrium. "
            f"History: {bl}.\n"
            "Likely cause: tick order wrong (fill before receive starves the queue), "
            "or Factory's inbound order channel is dropping orders (BLOCKER 1 regression)."
        )


def test_equilibrium_customer_demand_history_constant():
    """The customer-demand-history recorded by the engine matches the demand function."""
    final = simulate_full_game(
        seed=42, player_role=Role.RETAILER,
        agents=_all_constant_4_agents(),
        demand_fn=constant_demand,
    )
    assert len(final.customer_demand_history) == TOTAL_WEEKS
    assert all(d == 4 for d in final.customer_demand_history), (
        f"customer demand drifted from 4: {final.customer_demand_history}"
    )


def test_equilibrium_costs_per_week_strict_monotonic():
    """Each station's per-week cumulative cost at equilibrium is exactly
    HOLDING_COST * INITIAL_INVENTORY * (week_index + 1) = 6.0 * (i+1).

    WHY STRICT PER-WEEK ASSERT (instead of just final == 216.0):
    A cumulative-only check (final cost == 216.0) can hide mid-game oscillation
    that integrates back to the right total. The per-week check catches mid-game
    drift: if week 5 cost is 30 (=6*5) but week 10 cost is 65 (instead of 60),
    the per-tick assert fails immediately at week 10 -- long before the integral
    recovers.

    Cumulative cost after 36 weeks = HOLDING_COST * 12 * 36 = 216.0 per station,
    and at every intermediate week i (1-indexed: i=1..36), cumulative cost is
    exactly 6.0 * i.
    """
    expected_per_week = HOLDING_COST * INITIAL_INVENTORY  # 0.5 * 12 = 6.0
    final = simulate_full_game(
        seed=42, player_role=Role.RETAILER,
        agents=_all_constant_4_agents(),
        demand_fn=constant_demand,
    )
    for station in final.stations:
        for i, c in enumerate(station.cost_history):
            expected = expected_per_week * (i + 1)
            assert abs(c - expected) < 1e-9, (
                f"{station.role.name} week {i+1}: cumulative cost {c:.4f}, "
                f"expected {expected:.4f} (6.0 * {i+1}).\n"
                "Mid-game cost oscillation detected -- even if the final cost "
                "totals to 216.0, this catches drift that integrates back to "
                f"the right total. Full cost_history: {station.cost_history}"
            )
        # And confirm the final cumulative IS 216.0 as a sanity end-cap:
        assert abs(station.cost_history[-1] - 216.0) < 1e-9, (
            f"{station.role.name}: cumulative cost {station.cost_history[-1]:.2f}, "
            f"expected 216.0 (= 0.5 * 12 * 36)."
        )


def test_equilibrium_orders_placed_are_all_four():
    """Every station should order exactly 4 every week -- this is the
    ConstantOrderAgent(4) contract directly."""
    final = simulate_full_game(
        seed=42, player_role=Role.RETAILER,
        agents=_all_constant_4_agents(),
        demand_fn=constant_demand,
    )
    for station in final.stations:
        assert station.orders_placed_history == (4,) * TOTAL_WEEKS, (
            f"{station.role.name}: orders_placed_history should be (4,)*36, "
            f"got {station.orders_placed_history}.\n"
            "ConstantOrderAgent(4).decide_order always returns 4, so any "
            "deviation means the agent is not being invoked or its return is "
            "being mutated. Check place_orders in tick.py."
        )


def test_equilibrium_factory_inventory_explicit():
    """Explicit BLOCKER 1 regression guard: Factory's inventory MUST stay at 12,
    not 16. With the old broken design (ORDER_PIPELINE_LEN_FACTORY=0,
    Factory.incoming_orders=()), Distributor's order to Factory was silently
    discarded and Factory shipped 0 to Distributor every tick -- Factory inventory
    would climb to 16 (receive 4, ship 0).
    """
    final = simulate_full_game(
        seed=42, player_role=Role.RETAILER,
        agents=_all_constant_4_agents(),
        demand_fn=constant_demand,
    )
    factory_inv = final.stations[Role.FACTORY.value].inventory_history
    assert all(v == 12 for v in factory_inv), (
        f"Factory inventory drifted from 12. History: {factory_inv}.\n"
        "If Factory inventory is 16 every week, ORDER_PIPELINE_LEN_FACTORY=0 "
        "and Factory.incoming_orders=() -- Distributor's orders are being silently "
        "discarded by advance_pipelines (BLOCKER 1 regression). Verify "
        "beergame/config/scenarios.py has ORDER_PIPELINE_LEN_FACTORY=1, and "
        "beergame/engine/state.py's new_game() pre-loads Factory.incoming_orders=(4,)."
    )
    # And Factory MUST be shipping to Distributor every tick:
    factory_ships = final.stations[Role.FACTORY.value].shipments_sent_history
    assert all(v == 4 for v in factory_ships), (
        f"Factory shipments to Distributor drifted from 4. History: {factory_ships}.\n"
        "If shipments are all 0, the Distributor->Factory order channel is broken."
    )


def test_equilibrium_tick_1_trace_explicit():
    """Manually re-derived tick 1 trace for the documentation in the SUMMARY.
    Under ConstantOrderAgent(4) + constant_demand=4, after tick 1:
      - Every station: inventory=12, backlog=0, incoming_shipments=(4,4).
      - Wholesaler / Distributor / Factory: incoming_orders=(4,) -- they receive
        the order placed in step 4 by their downstream neighbor.
      - Retailer: incoming_orders=(0,) -- no upstream station routes orders TO
        the Retailer (the customer's demand arrives via demand_fn inside
        fill_orders step 2, NOT via the incoming_orders pipeline). So Retailer's
        _pending_in_order stays 0 across step 4 and step 5 shifts the pipeline
        from the initial (4,) to (0,).

    The IMPORTANT shape for equilibrium preservation is that the OBSERVABLE
    state (inventory, backlog) stays at 12/0 -- which it does for ALL four
    stations every week -- this is what the other 5 tests already pin. This
    test is the explicit BLOCKER 1 regression guard at the upstream end: it
    checks that Wholesaler/Distributor/Factory all have incoming_orders=(4,)
    at tick 1, NOT (0,). With the old broken design Factory.incoming_orders
    would still be () (the empty tuple) and orders would be silently dropped.
    """
    from beergame.engine.state import new_game
    from beergame.engine.tick import advance_week
    state = new_game(player_role=Role.RETAILER, seed=42)
    agents = _all_constant_4_agents()
    s1 = advance_week(state, player_order=4,
                      ai_agents={r: agents[r] for r in Role if r != Role.RETAILER},
                      demand_fn=constant_demand)
    assert s1.week == 1
    for station in s1.stations:
        assert station.inventory == 12, (
            f"{station.role.name}: tick 1 inventory={station.inventory}, expected 12"
        )
        assert station.backlog == 0
        assert station.incoming_shipments == (4, 4), (
            f"{station.role.name}: tick 1 incoming_shipments={station.incoming_shipments}, "
            "expected (4, 4)"
        )

    # Wholesaler, Distributor, Factory: incoming_orders=(4,) -- BLOCKER 1
    # regression check (especially Factory, which historically had incoming_orders=()).
    for role in (Role.WHOLESALER, Role.DISTRIBUTOR, Role.FACTORY):
        station = s1.stations[role.value]
        assert station.incoming_orders == (4,), (
            f"{role.name}: tick 1 incoming_orders={station.incoming_orders}, "
            "expected (4,) -- including Factory (BLOCKER 1 regression check). "
            "If Factory.incoming_orders is () here, ORDER_PIPELINE_LEN_FACTORY=0 "
            "regression -- orders from Distributor are being silently dropped."
        )

    # Retailer: incoming_orders=(0,) -- no upstream station routes to Retailer.
    # Customer demand arrives via demand_fn in fill_orders, not via this pipeline.
    retailer = s1.stations[Role.RETAILER.value]
    assert retailer.incoming_orders == (0,), (
        f"RETAILER: tick 1 incoming_orders={retailer.incoming_orders}, expected (0,). "
        "No upstream station routes orders to the Retailer -- customer demand is "
        "consumed directly inside fill_orders step 2 via demand_fn. If Retailer's "
        "incoming_orders is anything other than (0,) after tick 1, somebody is "
        "spuriously routing orders to the most-downstream station."
    )
