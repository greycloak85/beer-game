"""4-panel orders+inventory chart for the debrief view (DEB-01, DEB-02).

Pure Plotly — no Streamlit imports, no NumPy, no pandas. Returns a
``plotly.graph_objects.Figure`` that the view layer renders.

API references (verified 2026-05-18):
- ``plotly.subplots.make_subplots``: https://plotly.com/python/subplots/
- ``Figure.add_vline``: https://plotly.com/python/horizontal-vertical-shapes/

Layout: 4 vertically stacked panels (one per station, top-to-bottom in Role
order: Retailer, Wholesaler, Distributor, Factory) sharing the weeks x-axis.
Each panel has two traces — ``orders_placed_history`` and ``inventory_history``
— so the figure has exactly 8 traces.

DEB-02 week-5 marker: ``Figure.add_vline`` at ``x = CLASSIC_STEP_BREAK_WEEK + 1``
(= 5, NOT 4 — see Pitfall 1 in 03-RESEARCH.md). The annotation text
"Customer demand: 4 → 8" names the canonical step. ``row="all"`` paints the
line across every panel.
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from beergame.config.scenarios import CLASSIC_STEP_BREAK_WEEK
from beergame.engine.state import GameState, Role


_STATION_TITLES = ("Retailer", "Wholesaler", "Distributor", "Factory")

# DEB-02: the customer-demand step fires AT week 5 — CLASSIC_STEP_BREAK_WEEK
# (= 4) is the LAST pre-step week. The vertical line goes at the first
# post-step week so the visual cleanly separates the equilibrium era from the
# bullwhip era. Off-by-one trap is Pitfall 1 in 03-RESEARCH.md.
_STEP_WEEK = CLASSIC_STEP_BREAK_WEEK + 1  # = 5

# Dark-mode-friendly palette — vivid enough to read on a #222730 background.
# Orders curve is the primary visual (the one that amplifies upstream).
_ORDERS_COLOR = "#60a5fa"      # cool blue
_INVENTORY_COLOR = "#ffa94d"   # warm orange, dotted (distinguishable monochrome)


def build_four_panel(state: GameState) -> go.Figure:
    """Build the 4-panel orders+inventory chart (DEB-01) with the week-5 demand-step marker (DEB-02).

    Args:
        state: Any ``GameState`` — typically a fully-played 36-week game,
            but the builder uses ``state.total_weeks`` so partial games and
            future scenario configs also work.

    Returns:
        A ``plotly.graph_objects.Figure`` with exactly 8 ``go.Scatter`` traces
        (4 stations × {orders, inventory}) and a vertical line at x=5 annotated
        "Customer demand: 4 → 8". The view layer renders this via
        ``st.plotly_chart(fig, key="debrief_four_panel", width="stretch")``.
    """
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        subplot_titles=_STATION_TITLES,
    )

    # x-axis: weeks 1..total_weeks (1-indexed for UX; matches play.py's
    # mini-chart convention — see Pitfall 6 in 02-RESEARCH.md).
    weeks = list(range(1, state.total_weeks + 1))

    for role in Role:
        s = state.stations[role.value]
        row = role.value + 1  # Role.RETAILER -> row 1, Role.FACTORY -> row 4

        # Orders placed: the primary visual — this is the curve that
        # amplifies upstream.
        fig.add_trace(
            go.Scatter(
                x=weeks,
                y=list(s.orders_placed_history),
                mode="lines+markers",
                name="Orders placed",
                legendgroup="orders",
                showlegend=(row == 1),  # legend rendered once at the top
                line=dict(color=_ORDERS_COLOR, width=3),
                marker=dict(size=6),
            ),
            row=row, col=1,
        )
        # Inventory: secondary visual — dotted line so it doesn't compete with
        # the orders curve. Sterman's hallmark "overshoot then collapse to
        # negative inventory (= backlog)" pattern shows up here.
        fig.add_trace(
            go.Scatter(
                x=weeks,
                y=list(s.inventory_history),
                mode="lines",
                name="Inventory",
                legendgroup="inventory",
                showlegend=(row == 1),
                line=dict(color=_INVENTORY_COLOR, dash="dot", width=3),
            ),
            row=row, col=1,
        )

    # DEB-02: week-5 demand-step marker spanning every panel.
    # x = CLASSIC_STEP_BREAK_WEEK + 1 = 5 (NOT CLASSIC_STEP_BREAK_WEEK = 4).
    # row="all" paints the line on every subplot; col=1 is required syntax.
    fig.add_vline(
        x=_STEP_WEEK,
        line_dash="dash",
        line_color="rgba(128,128,128,0.6)",
        annotation_text="Customer demand: 4 → 8",
        annotation_position="top right",
        row="all", col=1,
    )

    fig.update_layout(
        template="plotly_dark",
        # Match the secondaryBackgroundColor from .streamlit/config.toml so the
        # chart blends with surrounding cards.
        paper_bgcolor="#222730",
        plot_bgcolor="#222730",
        height=720,
        margin=dict(l=40, r=30, t=70, b=40),
        hovermode="x unified",
        font=dict(size=14, color="#E8EAED"),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.04,
            xanchor="right", x=1,
            font=dict(size=14),
        ),
    )
    # Bottom panel only — the x-axis is shared across all rows.
    fig.update_xaxes(
        title=dict(font=dict(size=15)),
        tickfont=dict(size=13),
        gridcolor="#2e333c",
    )
    fig.update_yaxes(
        title=dict(text="Units", font=dict(size=14)),
        tickfont=dict(size=12),
        gridcolor="#2e333c",
        col=1,
    )
    fig.update_xaxes(title_text="Week", row=4, col=1)

    # Subplot titles ("Retailer", "Wholesaler" ...) are rendered as annotations
    # by make_subplots — bump their font size for legibility.
    for annotation in fig.layout.annotations:
        if annotation.text in _STATION_TITLES:
            annotation.font = dict(size=15, color="#E8EAED")

    return fig
