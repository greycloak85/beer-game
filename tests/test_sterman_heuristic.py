"""AI-01 + AI-02: Sterman heuristic with empirical 1989 parameters,
conforming to the Agent Protocol."""
from beergame.ai.sterman import ShipmentAnchorAndAdjustAgent
from beergame.ai.base import Agent
from beergame.engine.state import StationView, RetailerView, Role


def test_default_parameters_match_sterman_1989_empirical_fit():
    """AI-01: parameters MUST be the EMPIRICAL median fit, NOT the optimal alpha=beta=1, theta=0."""
    a = ShipmentAnchorAndAdjustAgent()
    assert a.alpha == 0.26, "alpha must be 0.26 (Sterman 1989 empirical), not optimal 1.0"
    assert a.beta == 0.34, "beta must be 0.34 (Sterman 1989 empirical), not optimal 1.0"
    assert a.theta == 0.36, "theta must be 0.36 (Sterman 1989 empirical), not optimal 0.0"
    assert a.desired_inventory == 17.0, "S' must be 17.0 per Sterman 1989 median"
    assert a.smoothed_demand == 4.0, "smoothed_demand should init to equilibrium throughput"


def test_protocol_conformance():
    """AI-02: agent satisfies the runtime_checkable Agent Protocol."""
    a = ShipmentAnchorAndAdjustAgent()
    assert isinstance(a, Agent)


def test_order_formula_returns_non_negative_int():
    """decide_order returns a non-negative int in all reachable parameter regimes."""
    a = ShipmentAnchorAndAdjustAgent()
    view = StationView(role=Role.WHOLESALER, week=1, inventory=12, backlog=0,
                       supply_line=8, last_order_received=4,
                       recent_orders_received=(4, 4, 4, 4))
    order = a.decide_order(view)
    assert isinstance(order, int)
    assert order >= 0


def test_order_at_perfect_equilibrium_view_is_3():
    """At inventory=12, backlog=0, supply_line=8, smoothed_demand=4 (init), last_order=4
    with empirical defaults, the formula evaluates to round(2.58) = 3 -- NOT 4.
    This is the GATE-1-cannot-use-Sterman result: empirical Sterman does not
    trivially maintain equilibrium because beta=0.34 underweights the supply line.
    Pin this exact value so a future "tweak" that flips alpha/beta/theta gets caught.
    """
    a = ShipmentAnchorAndAdjustAgent()
    view = StationView(role=Role.WHOLESALER, week=1, inventory=12, backlog=0,
                       supply_line=8, last_order_received=4,
                       recent_orders_received=(4, 4, 4, 4))
    assert a.decide_order(view) == 3, (
        "Empirical Sterman at perfectly-equilibrated view should order 3 "
        "(round(4 + 0.26*5 - 0.34*8) = round(2.58) = 3). If this is 4, someone "
        "swapped in 'optimal' alpha=beta=1, theta=0 parameters -- GATE 2 in Plan 03 "
        "will then fail because no bullwhip will emerge."
    )


def test_smoothed_demand_updates_via_exponential_smoothing():
    """L_t = theta * D_t + (1 - theta) * L_{t-1}, with theta=0.36 and initial L_0=4.0.

    After observing D=8 once: L = 0.36*8 + 0.64*4 = 5.44.
    After observing D=8 twice:  L = 0.36*8 + 0.64*5.44 ~ 6.4216.
    """
    a = ShipmentAnchorAndAdjustAgent()
    v8 = StationView(role=Role.WHOLESALER, week=1, inventory=12, backlog=0,
                     supply_line=8, last_order_received=8,
                     recent_orders_received=(4, 4, 4, 8))
    a.decide_order(v8)
    assert abs(a.smoothed_demand - 5.44) < 1e-9, f"got {a.smoothed_demand}"
    a.decide_order(v8)
    assert abs(a.smoothed_demand - (0.36 * 8 + 0.64 * 5.44)) < 1e-9


def test_high_backlog_drives_higher_order():
    """A station deep in backlog orders MORE than an equilibrated station."""
    a_eq = ShipmentAnchorAndAdjustAgent()
    a_bl = ShipmentAnchorAndAdjustAgent()
    v_eq = StationView(role=Role.WHOLESALER, week=1, inventory=12, backlog=0,
                       supply_line=8, last_order_received=4,
                       recent_orders_received=(4, 4, 4, 4))
    v_bl = StationView(role=Role.WHOLESALER, week=1, inventory=0, backlog=20,
                       supply_line=8, last_order_received=4,
                       recent_orders_received=(4, 4, 4, 4))
    assert a_bl.decide_order(v_bl) > a_eq.decide_order(v_eq)


def test_high_supply_line_dampens_order():
    """A station with lots already on the way orders LESS than one with empty pipeline.
    This is the supply-line term beta*SL_t in the heuristic."""
    a_low_sl = ShipmentAnchorAndAdjustAgent()
    a_high_sl = ShipmentAnchorAndAdjustAgent()
    v_low = StationView(role=Role.WHOLESALER, week=1, inventory=12, backlog=0,
                        supply_line=0, last_order_received=4,
                        recent_orders_received=(4, 4, 4, 4))
    v_high = StationView(role=Role.WHOLESALER, week=1, inventory=12, backlog=0,
                         supply_line=50, last_order_received=4,
                         recent_orders_received=(4, 4, 4, 4))
    assert a_low_sl.decide_order(v_low) > a_high_sl.decide_order(v_high), (
        "supply line term (beta) must dampen orders when pipeline is full"
    )


def test_order_floor_is_zero():
    """The formula clips at 0 -- no negative orders even when inventory is huge."""
    a = ShipmentAnchorAndAdjustAgent()
    v = StationView(role=Role.WHOLESALER, week=1, inventory=1000, backlog=0,
                    supply_line=1000, last_order_received=4,
                    recent_orders_received=(4, 4, 4, 4))
    assert a.decide_order(v) == 0


def test_retailer_view_also_works():
    """RetailerView is a subclass of StationView -- agent accepts it transparently."""
    a = ShipmentAnchorAndAdjustAgent()
    v = RetailerView(role=Role.RETAILER, week=1, inventory=12, backlog=0,
                     supply_line=8, last_order_received=4,
                     recent_orders_received=(4, 4, 4, 4),
                     customer_demand=4)
    order = a.decide_order(v)
    assert order >= 0
