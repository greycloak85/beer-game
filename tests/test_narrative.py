"""Unit tests for ``beergame.narrative.narrative_for`` (DEB-05).

Pure-Python tests: NO streamlit, NO plotly. Uses ``dataclasses.replace`` to
swap the ``player_role`` on the canonical session-scoped done state so the
underlying histories (orders, inventory, costs) stay identical across roles
— only the template selection + interpolated cost vary.

Invariants enforced:
- ≤200 words post-interpolation per role.
- Literal ``"bullwhip"`` appears (case-insensitive).
- The role's display name appears (e.g. "Retailer").
- Deterministic: same state → same string across repeated calls.
- At least one markdown ``**bold**`` span.
- The role's interpolated cost number appears.
"""
from dataclasses import replace

from beergame.engine.metrics import cost_breakdown
from beergame.engine.state import Role
from beergame.narrative import narrative_for


_ROLE_DISPLAY = {
    Role.RETAILER: "Retailer",
    Role.WHOLESALER: "Wholesaler",
    Role.DISTRIBUTOR: "Distributor",
    Role.FACTORY: "Factory",
}


def test_narrative_under_two_hundred_words_for_each_role(canonical_done_state):
    """DEB-05 / RESEARCH Pitfall 4: every role's narrative ≤200 words after
    interpolation, on the canonical seed=42 run."""
    for role in Role:
        s = replace(canonical_done_state, player_role=role)
        text = narrative_for(s)
        wc = len(text.split())
        assert wc <= 200, f"{role.name}: {wc} words (expected ≤200)"


def test_narrative_mentions_bullwhip_for_each_role(canonical_done_state):
    """DEB-05: every template must name the bullwhip — the literal lesson
    the player just witnessed. Case-insensitive."""
    for role in Role:
        s = replace(canonical_done_state, player_role=role)
        text = narrative_for(s)
        assert "bullwhip" in text.lower(), f"{role.name}: missing 'bullwhip' mention"


def test_narrative_names_the_role(canonical_done_state):
    """Each role's narrative includes that role's display name (capitalized).
    This is what makes the paragraph station-specific instead of generic."""
    for role in Role:
        s = replace(canonical_done_state, player_role=role)
        text = narrative_for(s)
        display = _ROLE_DISPLAY[role]
        assert display in text, f"{role.name}: missing '{display}' in text"


def test_narrative_is_deterministic(canonical_done_state):
    """Same ``GameState`` MUST produce the same string on every call —
    no LLM, no random selection, no time-dependent text. Sanity-checks
    that the function has no hidden global mutation."""
    for role in Role:
        s = replace(canonical_done_state, player_role=role)
        first = narrative_for(s)
        second = narrative_for(s)
        assert first == second, f"{role.name}: non-deterministic narrative"


def test_narrative_returns_string_with_markdown_bold(canonical_done_state):
    """Templates use ``**...**`` for emphasis on role name, 'bullwhip
    effect', and the cost. ``st.markdown`` renders that as bold."""
    for role in Role:
        s = replace(canonical_done_state, player_role=role)
        text = narrative_for(s)
        assert "**" in text, f"{role.name}: no markdown bold spans"


def test_narrative_includes_cost_number_for_each_role(canonical_done_state):
    """The cost interpolation (``{cost:,.0f}``) should land somewhere in
    the output text. Skip the assertion only if the rendered cost happens
    to be ``"0"`` (degenerate; not the case for the canonical seed=42 run)."""
    rows = cost_breakdown(canonical_done_state)
    cost_by_role = {r.role: r.total for r in rows}
    for role in Role:
        s = replace(canonical_done_state, player_role=role)
        text = narrative_for(s)
        rendered = f"{cost_by_role[role]:,.0f}"
        if rendered == "0":
            continue
        assert rendered in text, (
            f"{role.name}: rendered cost {rendered!r} missing from narrative"
        )
