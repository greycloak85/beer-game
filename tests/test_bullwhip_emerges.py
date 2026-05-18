"""GATE 2: Bullwhip calibration test (AI-03).

Setup: classic step demand (4/wk weeks 1-4, then 8/wk weeks 5-36); all four
stations are played by ShipmentAnchorAndAdjustAgent with empirical Sterman
1989 defaults.

Expected: max(factory.orders_placed_history) / max(retailer.orders_placed_history)
lies in [2.0, 4.0]. This is the canonical bullwhip amplification ratio
published in the Sterman literature and cross-verified across MIT Sloan,
JASSS 17(4):2, Columbia, and Kaminsky/Berkeley.

Why bounds [2.0, 4.0]: tight enough to catch parameter-swap bugs (the
"optimal" alpha=beta=1, theta=0 produces ratio < 1.5 -- flat curves, no
bullwhip). Wide enough to tolerate the legitimate variability across
empirical fits within the Sterman 1989 subject pool. The BLOCKER 1 fix
(ORDER_PIPELINE_LEN_FACTORY = 1, Factory.incoming_orders=(4,) at init)
adds one tick of inbound order lag at Factory, which makes the bullwhip
slightly LARGER (more lag = more over-correction) -- but still inside the
canonical bounds.

If this test fails marginally (e.g., 1.95 or 4.1):
  - DO NOT widen the test bounds -- they are load-bearing.
  - Re-verify the empirical Sterman parameters (alpha=0.26, beta=0.34,
    theta=0.36, desired_inventory=17.0). The most common cause of marginal
    failure is desired_inventory being tuned wrong -- try values in [12, 20]
    and pick the one inside [2.0, 4.0] with the cleanest collapse-to-zero
    post-overshoot pattern.
  - If many tunings fail, the engine's tick order or lead-time pipeline is
    wrong -- GATE 1 should have caught it but a subtle order-of-operations bug
    can pass GATE 1 (steady state) and still mishandle the demand step.
  - DO NOT regress ORDER_PIPELINE_LEN_FACTORY from 1 back to 0 "to shrink the
    bullwhip" -- that breaks GATE 1 (Factory inventory climbs to 16).
"""
import pytest

from beergame.engine.tick import simulate_full_game
from beergame.engine.state import Role
from beergame.engine.demand import demand_for_week
from beergame.config.scenarios import TOTAL_WEEKS
from beergame.ai.sterman import ShipmentAnchorAndAdjustAgent


BULLWHIP_RATIO_MIN = 2.0
BULLWHIP_RATIO_MAX = 4.0


def _all_sterman_agents() -> dict[Role, ShipmentAnchorAndAdjustAgent]:
    return {r: ShipmentAnchorAndAdjustAgent() for r in Role}


def test_bullwhip_factory_retailer_peak_ratio_in_canonical_range():
    """AI-03: classic step demand, all-Sterman-AI -> max(factory)/max(retailer) in [2.0, 4.0]."""
    final = simulate_full_game(
        seed=42, player_role=Role.RETAILER,
        agents=_all_sterman_agents(),
        demand_fn=demand_for_week,
    )
    retailer = final.stations[Role.RETAILER.value]
    factory = final.stations[Role.FACTORY.value]

    retailer_peak = max(retailer.orders_placed_history)
    factory_peak = max(factory.orders_placed_history)

    assert retailer_peak > 0, (
        "Retailer never ordered anything -- Sterman agent is broken or "
        "demand step never reached it. Check fill_orders + customer_demand routing."
    )

    ratio = factory_peak / retailer_peak

    assert BULLWHIP_RATIO_MIN <= ratio <= BULLWHIP_RATIO_MAX, (
        f"Bullwhip ratio {ratio:.2f} (factory_peak={factory_peak}, "
        f"retailer_peak={retailer_peak}) is OUTSIDE the canonical "
        f"[{BULLWHIP_RATIO_MIN}, {BULLWHIP_RATIO_MAX}] range.\n\n"
        "Most likely causes (in order):\n"
        "  1. Sterman EMPIRICAL parameters were swapped for OPTIMAL "
        "(alpha=beta=1, theta=0). Confirm beergame/ai/sterman.py defaults "
        "are alpha=0.26, beta=0.34, theta=0.36, desired_inventory=17.0.\n"
        "  2. Lead-time pipeline off-by-one or wrong tick order in "
        "engine/tick.py. Re-run test_equilibrium.py and test_tick_invariants.py.\n"
        "  3. desired_inventory (S') needs tuning within [12, 20]. DO NOT "
        "widen the test bounds -- tune S' and re-run.\n"
        "  4. ORDER_PIPELINE_LEN_FACTORY regression: if Factory's inbound "
        "order channel is broken (= 0 instead of 1), GATE 1 catches it first. "
        "DO NOT regress ORDER_PIPELINE_LEN_FACTORY from 1 to 0 to shrink the "
        "bullwhip -- the BLOCKER 1 fix is mandatory.\n\n"
        f"Full retailer orders: {retailer.orders_placed_history}\n"
        f"Full factory orders: {factory.orders_placed_history}"
    )


def test_bullwhip_factory_peak_exceeds_retailer_peak():
    """A weaker prerequisite: factory MUST overshoot more than retailer does.
    If this fails the heuristic isn't producing amplification at all."""
    final = simulate_full_game(
        seed=42, player_role=Role.RETAILER,
        agents=_all_sterman_agents(),
        demand_fn=demand_for_week,
    )
    retailer_peak = max(final.stations[Role.RETAILER.value].orders_placed_history)
    factory_peak = max(final.stations[Role.FACTORY.value].orders_placed_history)
    assert factory_peak > retailer_peak, (
        f"No amplification: factory_peak={factory_peak}, retailer_peak={retailer_peak}. "
        "The bullwhip is INVERTED or absent -- empirical-vs-optimal parameter swap "
        "is the most common cause."
    )


def test_bullwhip_amplification_monotonically_grows_upstream():
    """The bullwhip pattern: peak orders amplify monotonically as we go upstream.
    retailer_peak <= wholesaler_peak <= distributor_peak <= factory_peak.

    This is a softer check than the ratio test -- it catches the case where
    amplification exists but doesn't follow the canonical shape (e.g., if
    the Distributor overshoots more than the Factory due to a bug)."""
    final = simulate_full_game(
        seed=42, player_role=Role.RETAILER,
        agents=_all_sterman_agents(),
        demand_fn=demand_for_week,
    )
    peaks = [max(final.stations[r.value].orders_placed_history) for r in Role]
    # Role order is RETAILER, WHOLESALER, DISTRIBUTOR, FACTORY.
    for i in range(1, len(peaks)):
        assert peaks[i] >= peaks[i - 1], (
            f"Peak orders not monotonically growing upstream: "
            f"R={peaks[0]}, W={peaks[1]}, D={peaks[2]}, F={peaks[3]}. "
            "Expected R <= W <= D <= F (the canonical bullwhip shape)."
        )


def test_bullwhip_demand_step_recorded():
    """Sanity: the customer-demand-history reflects the actual step from 4 to 8 at week 5."""
    final = simulate_full_game(
        seed=42, player_role=Role.RETAILER,
        agents=_all_sterman_agents(),
        demand_fn=demand_for_week,
    )
    assert final.customer_demand_history[:4] == (4, 4, 4, 4), (
        f"weeks 1-4 should be demand=4, got {final.customer_demand_history[:4]}"
    )
    assert final.customer_demand_history[4] == 8, (
        f"week 5 should be demand=8 (step), got {final.customer_demand_history[4]}"
    )
    assert final.customer_demand_history[-1] == 8, (
        f"week 36 should still be demand=8, got {final.customer_demand_history[-1]}"
    )
    assert len(final.customer_demand_history) == TOTAL_WEEKS


def test_bullwhip_retailer_responds_at_or_after_week_5():
    """Tick 5 sensitivity: when demand jumps from 4 to 8 at week 5, the Retailer's
    inventory should drop (it can't fully fill 8 from its post-receive inventory
    without drawing on the equilibrium 12) AND the Retailer's order at week 5+
    should exceed the order at week 4 (Sterman responds to the demand shock).

    This is the 'tick 5 confirmation' that the demand step IS reaching the Retailer
    and is propagating into the Sterman heuristic correctly."""
    final = simulate_full_game(
        seed=42, player_role=Role.RETAILER,
        agents=_all_sterman_agents(),
        demand_fn=demand_for_week,
    )
    retailer = final.stations[Role.RETAILER.value]
    # The Retailer's inventory at week 5 (index 4) should be LOWER than at week 4 (index 3),
    # because customer demand jumped 4->8 and the supply pipeline still reflects the
    # pre-step ordering.
    assert retailer.inventory_history[4] < retailer.inventory_history[3], (
        f"Retailer inventory should drop at week 5 due to demand step. "
        f"Got: week 4 inv = {retailer.inventory_history[3]}, "
        f"week 5 inv = {retailer.inventory_history[4]}. "
        "If inventory did not drop, fill_orders is not applying the new customer demand "
        "(check that customer_demand_this_week is correctly computed from demand_fn at week 5)."
    )
    # Retailer's Sterman agent should have ordered MORE at some point after week 5
    # than at week 1 (the demand step propagates into the heuristic).
    retailer_max_after_step = max(retailer.orders_placed_history[4:])
    retailer_at_week_1 = retailer.orders_placed_history[0]
    assert retailer_max_after_step > retailer_at_week_1, (
        f"Retailer's post-step peak order ({retailer_max_after_step}) should exceed "
        f"week 1 order ({retailer_at_week_1}). Sterman is not responding to the shock -- "
        "check decide_order's view.last_order_received update."
    )
