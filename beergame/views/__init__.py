"""Streamlit-aware view modules. Each exposes a single render() function.

By contract, all view code lives here and in app.py. The engine, ai, and
config packages remain streamlit-free (ENG-01, enforced by
tests/test_no_streamlit_import.py).
"""
from beergame.views import debrief, play, rules, setup

__all__ = ["debrief", "play", "rules", "setup"]
