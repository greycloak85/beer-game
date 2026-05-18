"""PLAY-01: ``StationState.shipments_received_history`` and
``StationView.last_shipment_received``.

Regression coverage for the Plan 02-01 engine extension that lets the per-turn
play view (Plan 03) render "last week's shipments received" verbatim without
deriving it from indirect slices of other histories. The change is strictly
additive: it must not alter any agent's decisions or the bullwhip arithmetic.

These tests exercise the new field via the same public surface the UI will use
(``new_game`` -> ``advance_week`` / ``simulate_full_game`` -> ``build_station_view``),
mirroring the import style of ``tests/test_tick_invariants.py``.
"""
from beergame.ai.base import ConstantOrderAgent
from beergame.ai.sterman import ShipmentAnchorAndAdjustAgent
from beergame.config.scenarios import EQUILIBRIUM_THROUGHPUT, TOTAL_WEEKS
from beergame.engine.demand import constant_demand, demand_for_week
from beergame.engine.state import Role, build_station_view, new_game
from beergame.engine.tick import advance_week, simulate_full_game


def _equilibrium_agents() -> dict[Role, ConstantOrderAgent]:
    """All four stations order 4/wk — the canonical engine-correctness setup."""
    return {r: ConstantOrderAgent(4) for r in Role}


def test_initial_state_has_empty_history():
    """``new_game`` starts every station with shipments_received_history=().

    The view falls back to ``EQUILIBRIUM_THROUGHPUT`` (4) when the history is
    empty — the same convention ``last_order_received`` already uses.
    """
    state = new_game(player_role=Role.RETAILER, seed=42)
    for s in state.stations:
        assert s.shipments_received_history == (), (
            f"{s.role.name}: shipments_received_history should start empty, "
            f"got {s.shipments_received_history}"
        )
    for role in Role:
        v = build_station_view(state, role)
        assert v.last_shipment_received == EQUILIBRIUM_THROUGHPUT, (
            f"{role.name}: pre-tick last_shipment_received should fall back to "
            f"EQUILIBRIUM_THROUGHPUT={EQUILIBRIUM_THROUGHPUT}, "
            f"got {v.last_shipment_received}"
        )


def test_one_tick_appends_one_value_per_station():
    """After one tick at canonical equilibrium, every station's history has
    length 1 and the appended value equals EQUILIBRIUM_THROUGHPUT (4) because
    the shipping pipeline is pre-loaded with (4, 4).
    """
    state = new_game(player_role=Role.RETAILER, seed=42)
    agents = _equilibrium_agents()
    s1 = advance_week(
        state,
        player_order=4,
        ai_agents={r: agents[r] for r in Role if r != Role.RETAILER},
        demand_fn=constant_demand,
    )
    for s in s1.stations:
        assert len(s.shipments_received_history) == 1, (
            f"{s.role.name}: expected len 1 after one tick, "
            f"got {len(s.shipments_received_history)}"
        )
        assert s.shipments_received_history[0] == EQUILIBRIUM_THROUGHPUT, (
            f"{s.role.name}: first received shipment should be the pre-loaded "
            f"pipeline value 4, got {s.shipments_received_history[0]}"
        )


def test_n_ticks_appends_n_values():
    """Drive 10 equilibrium ticks; every station's history has length 10 and
    every value equals 4 (equilibrium throughput).
    """
    state = new_game(player_role=Role.RETAILER, seed=42)
    agents = _equilibrium_agents()
    for _ in range(10):
        state = advance_week(
            state,
            player_order=4,
            ai_agents={r: agents[r] for r in Role if r != Role.RETAILER},
            demand_fn=constant_demand,
        )
    for s in state.stations:
        assert len(s.shipments_received_history) == 10, (
            f"{s.role.name}: expected len 10, got {len(s.shipments_received_history)}"
        )
        assert all(v == 4 for v in s.shipments_received_history), (
            f"{s.role.name}: equilibrium should yield (4,)*10, "
            f"got {s.shipments_received_history}"
        )


def test_last_shipment_received_tracks_history_tail():
    """``build_station_view`` returns the LAST history value (not the first or
    a window).  Drive 5 ticks under classic step demand + all-Sterman opponents
    and assert ``view.last_shipment_received == history[-1]`` at the player's
    station.
    """
    state = new_game(player_role=Role.RETAILER, seed=42)
    ai = {r: ShipmentAnchorAndAdjustAgent() for r in Role if r != Role.RETAILER}
    for _ in range(5):
        state = advance_week(
            state,
            player_order=4,
            ai_agents=ai,
            demand_fn=demand_for_week,
        )
    player_role = Role.RETAILER
    s = state.stations[player_role.value]
    v = build_station_view(state, player_role)
    assert v.last_shipment_received == s.shipments_received_history[-1], (
        f"view.last_shipment_received ({v.last_shipment_received}) must equal "
        f"history tail ({s.shipments_received_history[-1]})"
    )


def test_shipments_received_matches_incoming_shipments_consumption():
    """Step 1 consumes ``incoming_shipments[0]`` and step 3 appends that exact
    value to ``shipments_received_history``. Verify that across 3 ticks the
    recorded sequence equals the sequence of front-of-pipeline values at the
    start of each tick.
    """
    state = new_game(player_role=Role.RETAILER, seed=42)
    agents = _equilibrium_agents()
    ai = {r: agents[r] for r in Role if r != Role.RETAILER}
    # Track Retailer's incoming_shipments[0] before each tick — that is the
    # value step 1 will consume and step 3 will append for the Retailer.
    expected_retailer = []
    for _ in range(3):
        rs = state.stations[Role.RETAILER.value]
        expected_retailer.append(rs.incoming_shipments[0] if rs.incoming_shipments else 0)
        state = advance_week(
            state,
            player_order=4,
            ai_agents=ai,
            demand_fn=constant_demand,
        )
    retailer = state.stations[Role.RETAILER.value]
    assert retailer.shipments_received_history == tuple(expected_retailer), (
        f"shipments_received_history {retailer.shipments_received_history} "
        f"should equal sequence of consumed slot-0 values {tuple(expected_retailer)}"
    )


def test_factory_self_shipments_recorded_through_pipeline():
    """Factory's self-shipments (its own placed order routed through its own
    SHIPPING_PIPELINE_LEN=2 production pipeline) are recorded just like any
    other station's received shipments. After 4 ticks under classic step
    demand + all-Sterman, Factory.shipments_received_history must have length
    4 and every value must be a non-negative int.
    """
    state = new_game(player_role=Role.RETAILER, seed=42)
    ai = {r: ShipmentAnchorAndAdjustAgent() for r in Role if r != Role.RETAILER}
    for _ in range(4):
        state = advance_week(
            state,
            player_order=4,
            ai_agents=ai,
            demand_fn=demand_for_week,
        )
    factory = state.stations[Role.FACTORY.value]
    assert len(factory.shipments_received_history) == 4, (
        f"Factory history len should be 4, got {len(factory.shipments_received_history)}"
    )
    assert all(isinstance(v, int) and v >= 0 for v in factory.shipments_received_history), (
        f"Factory shipments_received_history must be non-negative ints, "
        f"got {factory.shipments_received_history}"
    )


def test_constant_demand_equilibrium_shipments_received_all_four():
    """The single strongest invariant: under the canonical equilibrium
    (constant demand=4, ConstantOrderAgent(4) everywhere) every station
    receives exactly 4 cases per week for all 36 weeks. The recorded
    ``shipments_received_history`` must therefore equal ``(4,) * 36`` for each
    of the four stations.

    If this breaks, the new field is mutating engine behavior somewhere — the
    plan's explicit non-goal.
    """
    state = simulate_full_game(
        seed=42,
        player_role=Role.RETAILER,
        agents=_equilibrium_agents(),
        demand_fn=constant_demand,
    )
    expected = (4,) * TOTAL_WEEKS
    for s in state.stations:
        assert s.shipments_received_history == expected, (
            f"{s.role.name}: equilibrium history should be (4,)*{TOTAL_WEEKS}, "
            f"got {s.shipments_received_history}"
        )
