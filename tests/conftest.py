import pytest

from beergame.ai.base import ConstantOrderAgent
from beergame.ai.sterman import ShipmentAnchorAndAdjustAgent
from beergame.engine.state import Role, new_game
from beergame.engine.tick import simulate_full_game


@pytest.fixture
def initial_game():
    """Canonical fresh game with RETAILER as player."""
    return new_game(player_role=Role.RETAILER, seed=42)


@pytest.fixture
def constant_4_agents():
    """All four stations always order 4 — used for equilibrium regression."""
    return {r: ConstantOrderAgent(4) for r in Role}


@pytest.fixture(scope="session")
def canonical_done_state():
    """A fully-played canonical 36-week game (seed=42, all four stations
    driven by ``ShipmentAnchorAndAdjustAgent`` — same setup as Phase 1 GATE 2).

    Session-scoped: simulating 36 weeks costs ~30ms; sharing the result across
    chart + metric tests avoids redundant work. Phase 1's
    ``test_bullwhip_emerges`` proves this exact configuration produces a
    canonical bullwhip (max ratio in [2.0, 4.0]); Phase 3 tests build on that
    result to verify the variance-based amplification metric and the
    cost-breakdown reconciliation.

    All four stations (including the Retailer player slot) play Sterman so the
    demand shock at week 5 propagates upstream and amplifies — the canonical
    bullwhip the debrief is designed to visualise. A naive constant-4 Retailer
    would absorb the shock as backlog without changing the orders it PLACES, so
    the Wholesaler/Distributor/Factory would see flat orders_received forever
    and Sterman upstream would have no signal to amplify. Phase 3 metrics are
    intentionally tested against the real canonical bullwhip, mirroring the
    GATE 2 configuration exactly (see ``test_bullwhip_emerges.py``).
    """
    return simulate_full_game(
        seed=42,
        player_role=Role.RETAILER,
        agents={r: ShipmentAnchorAndAdjustAgent() for r in Role},
    )
