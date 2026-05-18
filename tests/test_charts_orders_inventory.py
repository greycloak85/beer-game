"""Unit tests for the Phase 3 debrief chart builder in
``beergame/charts/orders_inventory.py``.

Tests run directly against ``go.Figure`` — AppTest cannot inspect Plotly
charts (returns ``UnknownElement()`` per Streamlit docs, Pitfall 6). So we
verify the figure's structure (trace count, shapes, annotations, axis titles)
by introspecting the returned Figure object.

Covers DEB-01 (4-panel chart structure) and DEB-02 (week-5 demand-step marker).
"""
from beergame.charts import build_four_panel


def test_build_four_panel_has_eight_traces(canonical_done_state):
    """DEB-01: 4 stations × {orders, inventory} = 8 traces. A missing trace
    means one station's data isn't rendered."""
    fig = build_four_panel(canonical_done_state)
    assert len(fig.data) == 8, (
        f"Expected 8 traces (4 stations × 2 lines), got {len(fig.data)}."
    )


def test_build_four_panel_has_week_five_vline(canonical_done_state):
    """DEB-02 off-by-one trap (Pitfall 1): the vertical line MUST be at x=5
    (first post-step week), NOT x=4 (last pre-step week). Plotly translates
    add_vline into a Shape entry on fig.layout.shapes."""
    fig = build_four_panel(canonical_done_state)
    assert any(abs(s.x0 - 5) < 1e-9 for s in fig.layout.shapes), (
        f"No vertical line at x=5. Shapes found: "
        f"{[(s.x0, s.line.dash if s.line else None) for s in fig.layout.shapes]}"
    )


def test_build_four_panel_vline_annotation_mentions_step(canonical_done_state):
    """DEB-02: the annotation MUST name the demand levels (4 → 8) so the
    player sees what changed at week 5 even without reading the rules. We
    accept any annotation containing both "4" and "8" — robust to spacing
    or arrow-glyph variations."""
    fig = build_four_panel(canonical_done_state)
    has_step_annotation = any(
        a.text and "4" in a.text and "8" in a.text
        for a in fig.layout.annotations
    )
    assert has_step_annotation, (
        f"No annotation mentioning '4' and '8' (the customer-demand step "
        f"levels). Annotations: {[a.text for a in fig.layout.annotations]}"
    )


def test_build_four_panel_x_axis_label_is_week(canonical_done_state):
    """X-axis title appears only on the bottom (shared) panel — xaxis4. If
    it shows up on other panels the layout breaks visually (each panel gets
    its own redundant "Week" label)."""
    fig = build_four_panel(canonical_done_state)
    assert fig.layout.xaxis4.title.text == "Week"


def test_build_four_panel_subplot_titles_are_station_names(canonical_done_state):
    """The four subplot titles ("Retailer", "Wholesaler", "Distributor",
    "Factory") MUST be present so the player can tell which echelon each
    panel represents — without them the chart is unreadable."""
    fig = build_four_panel(canonical_done_state)
    annotation_texts = [a.text for a in fig.layout.annotations if a.text]
    for name in ("Retailer", "Wholesaler", "Distributor", "Factory"):
        assert any(name in t for t in annotation_texts), (
            f"Subplot title '{name}' missing. Annotations: {annotation_texts}"
        )


def test_build_four_panel_uses_state_total_weeks(canonical_done_state):
    """The x-axis must cover 1..state.total_weeks (NOT a hard-coded 36).
    For the canonical state total_weeks == 36, so the first trace's x array
    has length 36. If a future scenario changes total_weeks the chart should
    follow automatically."""
    fig = build_four_panel(canonical_done_state)
    assert len(fig.data[0].x) == canonical_done_state.total_weeks
    assert fig.data[0].x[0] == 1   # weeks are 1-indexed
    assert fig.data[0].x[-1] == canonical_done_state.total_weeks
