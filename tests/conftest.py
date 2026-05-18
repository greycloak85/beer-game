import pytest

from beergame.ai.base import ConstantOrderAgent
from beergame.engine.state import Role, new_game


@pytest.fixture
def initial_game():
    """Canonical fresh game with RETAILER as player."""
    return new_game(player_role=Role.RETAILER, seed=42)


@pytest.fixture
def constant_4_agents():
    """All four stations always order 4 — used for equilibrium regression."""
    return {r: ConstantOrderAgent(4) for r in Role}
