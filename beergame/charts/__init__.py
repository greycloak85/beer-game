"""Pure-Plotly chart builders for the debrief view.

This package mirrors the engine/ai/ purity contract: zero ``streamlit`` imports
so Plotly figures can be unit-tested against ``go.Figure`` without spinning up
an AppTest session (Streamlit's AppTest returns ``UnknownElement()`` for chart
elements and cannot introspect them — see PITFALLS.md / 03-RESEARCH.md
Pitfall 6).

The view layer (``beergame/views/debrief.py``) is the only place that may
import both ``streamlit`` and these builders; it renders the returned
``go.Figure`` via ``st.plotly_chart(fig, key=..., width="stretch")``.
"""
from beergame.charts.orders_inventory import build_four_panel

__all__ = ["build_four_panel"]
