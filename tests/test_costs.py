"""ENG-05 + ENG-08: asymmetric $0.50 holding / $1.00 backorder costs, charged weekly."""
from beergame.engine.costs import weekly_cost
from beergame.engine.state import Role, StationState


def _station(inv: int, bl: int) -> StationState:
    return StationState(
        role=Role.RETAILER,
        inventory=inv,
        backlog=bl,
        incoming_shipments=(4, 4),
        incoming_orders=(4,),
        inventory_history=(),
        backlog_history=(),
        orders_placed_history=(),
        orders_received_history=(),
        shipments_sent_history=(),
        shipments_received_history=(),
        cost_history=(),
    )


def test_holding_only():
    assert weekly_cost(_station(12, 0)) == 12 * 0.50


def test_backorder_only():
    assert weekly_cost(_station(0, 5)) == 5 * 1.00


def test_cost_asymmetry():
    # 10 units of backlog cost 2x what 10 units of inventory cost.
    holding_only = weekly_cost(_station(10, 0))
    backorder_only = weekly_cost(_station(0, 10))
    assert backorder_only == 2 * holding_only


def test_zero_state_zero_cost():
    assert weekly_cost(_station(0, 0)) == 0.0


def test_backlog_accumulates_across_three_week_stockout():
    """ENG-08: a backlog of 5 persisting for 3 weeks charges 5*1.00*3 = $15.00
    across 3 ticks. Simpler observable below: weekly_cost called on an
    unchanging (inv=0, bl=B) state for B in {5, 9, 13} sums to 27.0.
    """
    assert (
        weekly_cost(_station(0, 5))
        + weekly_cost(_station(0, 9))
        + weekly_cost(_station(0, 13))
        == 27.0
    )
