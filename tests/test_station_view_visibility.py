"""ENG-10: only Retailer view exposes customer_demand; others raise AttributeError."""
import pytest

from beergame.engine.state import (
    RetailerView,
    Role,
    StationView,
    build_station_view,
    new_game,
)


def test_retailer_view_is_retailer_view():
    state = new_game(player_role=Role.RETAILER, seed=42)
    view = build_station_view(state, Role.RETAILER)
    assert isinstance(view, RetailerView)
    # Attribute access does not raise:
    _ = view.customer_demand


@pytest.mark.parametrize("role", [Role.WHOLESALER, Role.DISTRIBUTOR, Role.FACTORY])
def test_non_retailer_view_has_no_customer_demand(role):
    state = new_game(player_role=Role.RETAILER, seed=42)
    view = build_station_view(state, role)
    assert isinstance(view, StationView)
    assert not isinstance(view, RetailerView)
    with pytest.raises(AttributeError):
        _ = view.customer_demand


def test_view_does_not_leak_other_stations():
    """A non-Retailer view exposes only its own locally-knowable state."""
    state = new_game(player_role=Role.RETAILER, seed=42)
    view = build_station_view(state, Role.WHOLESALER)
    for forbidden in ("customer_demand", "stations", "other_inventory"):
        assert not hasattr(view, forbidden), (
            f"non-Retailer view leaked attribute `{forbidden}`"
        )
