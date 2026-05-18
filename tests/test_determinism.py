"""ENG-09: deterministic results for a given seed -> byte-identical traces."""
from beergame.ai.base import ConstantOrderAgent
from beergame.engine.state import Role
from beergame.engine.tick import simulate_full_game


def _const_agents() -> dict[Role, ConstantOrderAgent]:
    return {r: ConstantOrderAgent(4) for r in Role}


def test_same_seed_same_final_state():
    a = simulate_full_game(seed=42, player_role=Role.RETAILER, agents=_const_agents())
    b = simulate_full_game(seed=42, player_role=Role.RETAILER, agents=_const_agents())
    assert a == b


def test_same_seed_byte_identical_traces():
    a = simulate_full_game(seed=42, player_role=Role.RETAILER, agents=_const_agents())
    b = simulate_full_game(seed=42, player_role=Role.RETAILER, agents=_const_agents())
    for sa, sb in zip(a.stations, b.stations):
        assert sa.inventory_history == sb.inventory_history
        assert sa.backlog_history == sb.backlog_history
        assert sa.orders_placed_history == sb.orders_placed_history
        assert sa.orders_received_history == sb.orders_received_history
        assert sa.shipments_sent_history == sb.shipments_sent_history
        assert sa.cost_history == sb.cost_history
    assert a.customer_demand_history == b.customer_demand_history


def test_different_player_role_does_not_change_engine_trace():
    """Player role choice is UI-only — agents play all stations identically."""
    a = simulate_full_game(seed=42, player_role=Role.RETAILER, agents=_const_agents())
    b = simulate_full_game(seed=42, player_role=Role.FACTORY, agents=_const_agents())
    for sa, sb in zip(a.stations, b.stations):
        assert sa.inventory_history == sb.inventory_history
        assert sa.orders_placed_history == sb.orders_placed_history
