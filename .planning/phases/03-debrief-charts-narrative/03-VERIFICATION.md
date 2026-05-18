---
phase: 03-debrief-charts-narrative
verified: 2026-05-18T22:00:00Z
status: human_needed
score: 6/6 must-haves verified (1 deviation flagged for human review)
human_verification:
  - test: "Click 'Play again' on debrief and confirm it returns to setup (NOT rules)"
    expected: "After clicking 'Play again', the user lands directly on the setup screen with the station radio + seed input — NOT on the rules screen requiring an extra 'Got it' click"
    why_human: "Phase 3 Success Criterion 5 says 'returns to setup'. Implementation pops phase from session_state, which defaults to 'rules' on next rerun. seen_rules=True is preserved, but the rules view does NOT auto-skip to setup when seen_rules is True. A human should decide whether (a) the extra rules click is acceptable UX, or (b) reset_game should set phase='setup' explicitly, or (c) the rules view should auto-redirect when seen_rules is True. AppTest trace confirmed: phase=='rules' after Play again click."
---

# Phase 3: Debrief Charts + Narrative Verification Report

**Phase Goal:** A post-game debrief that visually reproduces the canonical bullwhip pattern, quantifies amplification and cost, and explains in plain language what the player just experienced.

**Verified:** 2026-05-18T22:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                                        | Status     | Evidence                                                                                                          |
| --- | ------------------------------------------------------------------------------------------------------------ | ---------- | ----------------------------------------------------------------------------------------------------------------- |
| 1   | 4-panel chart with shared x-axis, one panel per station, week-5 vline annotated "Customer demand: 4 → 8"     | ✓ VERIFIED | `build_four_panel` returns Figure with 8 traces, 4 shapes (vline replicated per panel), x0=5, annotation matches  |
| 2   | Variance amplification ratio computable; canonical seed=42 > 1 and monotonically increases R<W<D<F           | ✓ VERIFIED | Canonical seed=42: overall=35.3804, R=3.4258 < W=12.8145 < D=29.2671 < F=35.3804                                  |
| 3   | Per-station cost breakdown reconciles with `cost_history[-1]` to floating-point tolerance                    | ✓ VERIFIED | All 4 roles reconcile with delta=0.0 (R=222.50, W=299.00, D=498.50, F=421.50)                                     |
| 4   | ≤200-word narrative for each of 4 player roles, mentions "bullwhip", names role, deterministic               | ✓ VERIFIED | R=127, W=121, D=124, F=142 words; all mention "bullwhip"; all use markdown bold; all reference role display name  |
| 5   | "Play again" button visible in debrief view                                                                  | ✓ VERIFIED | `st.button("Play again", on_click=on_reset, ...)` in debrief.py:101; app.py:110 binds `on_reset=reset_game`        |
| 6   | "Play again" resets session_state and returns to setup                                                       | ? UNCERTAIN | `reset_game` pops session_state correctly, but phase defaults to "rules" on next rerun (not "setup"). See human_verification. |

**Score:** 5/6 truths verified, 1 needs human review

### Required Artifacts

| Artifact                                       | Expected                                                                                 | Status     | Details                                                                                            |
| ---------------------------------------------- | ---------------------------------------------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------- |
| `beergame/engine/metrics.py`                   | `variance_bullwhip_ratio`, `per_echelon_amplification`, `cost_breakdown`, `CostRow`      | ✓ VERIFIED | All 4 new symbols exported; existing `peak_orders` + `bullwhip_ratio` preserved (lines 29-41)      |
| `beergame/charts/__init__.py`                  | Re-exports `build_four_panel`                                                            | ✓ VERIFIED | `from beergame.charts.orders_inventory import build_four_panel; __all__ = ["build_four_panel"]`     |
| `beergame/charts/orders_inventory.py`          | `build_four_panel(state) -> go.Figure` with 8 traces + week-5 vline                      | ✓ VERIFIED | 8 Scatter traces, `add_vline(x=_STEP_WEEK)` where `_STEP_WEEK = CLASSIC_STEP_BREAK_WEEK + 1 = 5`   |
| `beergame/narrative/__init__.py`               | `narrative_for(state) -> str` entry point                                                | ✓ VERIFIED | Selects `_TEMPLATES[role]` by `state.player_role`, interpolates 6 placeholders                     |
| `beergame/narrative/templates.py`              | 4 station-specific templates                                                             | ✓ VERIFIED | `_TEMPLATES: dict[Role, str]` with all 4 Role keys; each template ≤180 words pre-interpolation     |
| `beergame/views/debrief.py`                    | Full Phase-3 layout: title + headline + chart + per-echelon tiles + cost table + narrative + Play again | ✓ VERIFIED | All 7 elements present (debrief.py:53-106); thin assembler — no math here                          |
| `tests/conftest.py`                            | `canonical_done_state` session-scoped fixture                                            | ✓ VERIFIED | All 4 stations Sterman; uses `simulate_full_game(seed=42)`                                          |
| `tests/test_metrics_debrief.py`                | Unit tests for new metrics + cost reconciliation                                         | ✓ VERIFIED | 9 tests passing                                                                                    |
| `tests/test_charts_orders_inventory.py`        | Pure-Python tests against go.Figure (8 traces, vline at x=5, "Week" axis)                | ✓ VERIFIED | 6 tests passing                                                                                    |
| `tests/test_narrative.py`                      | ≤200-word check per role + "bullwhip" mention + determinism + markdown bold              | ✓ VERIFIED | 6 tests passing                                                                                    |
| `tests/test_app_smoke.py`                      | Extended with parametrized over-role debrief smoke                                       | ✓ VERIFIED | 10 tests (5 original + 1 retailer content check + 4 parametrized over Role); all pass              |

### Key Link Verification

| From                                                    | To                                                            | Via                                                  | Status   | Details                                                                                                    |
| ------------------------------------------------------- | ------------------------------------------------------------- | ---------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------- |
| `engine/metrics.py::cost_breakdown`                     | `config/costs.py (HOLDING_COST, BACKORDER_COST)`              | imported constants; mirrors `engine/costs.py::weekly_cost` formula | ✓ WIRED  | line 25: `from beergame.config.costs import BACKORDER_COST, HOLDING_COST`; reconciliation delta=0.0       |
| `charts/orders_inventory.py`                            | `plotly.subplots.make_subplots`                               | imported, called with rows=4, cols=1, shared_xaxes=True | ✓ WIRED  | line 56: `make_subplots(rows=4, cols=1, shared_xaxes=True, ...)`                                           |
| `charts/orders_inventory.py::build_four_panel`          | `Figure.add_vline at x=CLASSIC_STEP_BREAK_WEEK + 1`           | `fig.add_vline(x=_STEP_WEEK, ..., row="all", col=1)` | ✓ WIRED  | line 104-111; `_STEP_WEEK = CLASSIC_STEP_BREAK_WEEK + 1` (= 5)                                            |
| `views/debrief.py`                                      | `beergame.charts.build_four_panel`                            | `st.plotly_chart(fig, key="debrief_four_panel", width="stretch")` | ✓ WIRED  | line 68-69; uses `width="stretch"` (Streamlit 1.57 compliant)                                              |
| `views/debrief.py`                                      | `beergame.engine.metrics` (3 fns)                             | called and displayed via `st.metric` and `st.table`  | ✓ WIRED  | lines 56, 73, 85: `variance_bullwhip_ratio(state)`, `per_echelon_amplification(state)`, `cost_breakdown(state)` |
| `views/debrief.py`                                      | `beergame.narrative.narrative_for`                            | `st.markdown(narrative_for(state))`                  | ✓ WIRED  | line 98                                                                                                    |
| `views/debrief.py`                                      | `app.py::reset_game`                                          | `on_reset` parameter bound to `st.button(on_click=on_reset)` | ✓ WIRED  | debrief.py:103 (`on_click=on_reset`); app.py:110 (`debrief.render(state=..., on_reset=reset_game)`)        |
| `narrative/__init__.py::narrative_for`                  | `engine.metrics` + `state.player_role`                        | selects template by `state.player_role`, interpolates ratios + cost | ✓ WIRED  | __init__.py:37,46: `role = state.player_role`; `_TEMPLATES[role].format(...)`                              |

### Requirements Coverage

| Requirement | Source Plan(s) | Description                                                                                                                            | Status        | Evidence                                                                                                                              |
| ----------- | -------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| DEB-01      | 03-01, 03-02   | Debrief shows a 4-panel chart (one panel per station) with shared x-axis (weeks) plotting orders placed and inventory level            | ✓ SATISFIED   | `build_four_panel` produces 8 traces (4 stations × {orders, inventory}); rendered in debrief.py via `st.plotly_chart`                  |
| DEB-02      | 03-01, 03-02   | Debrief annotates the week-5 demand step (customer demand 4 → 8) on the chart                                                          | ✓ SATISFIED   | `fig.add_vline(x=5, annotation_text="Customer demand: 4 → 8", row="all")`; verified in test_build_four_panel_has_week_five_vline      |
| DEB-03      | 03-01, 03-02   | Debrief shows the bullwhip amplification ratio (variance(factory orders) / variance(customer demand)) plus per-echelon ratios          | ✓ SATISFIED   | Headline `st.metric` with 35.38× at canonical seed=42; 4 per-echelon tiles in `st.columns(4)` (R/W/D/F)                                |
| DEB-04      | 03-01, 03-02   | Debrief shows a cost breakdown per station (holding cost, backorder cost, total)                                                       | ✓ SATISFIED   | `st.table` with Station/Holding ($)/Backorder ($)/Total ($); reconciliation invariant proved by test_cost_breakdown_reconciles        |
| DEB-05      | 03-02          | Debrief shows a narrative explanation (≤200 words) adapted to the player's station                                                     | ✓ SATISFIED   | 4 templates, max 142 words at canonical seed=42; rendered via `st.markdown(narrative_for(state))`; all mention "bullwhip" literally   |
| DEB-06      | 03-02          | Debrief offers a "Play again" action that returns to setup                                                                             | ? NEEDS HUMAN | Button present + wired to `reset_game`. BUT: after click, phase defaults to "rules" not "setup". seen_rules=True is preserved but the rules screen still renders. See human_verification. |

### Anti-Patterns Found

| File                                | Line | Pattern                                                | Severity | Impact                                                                                          |
| ----------------------------------- | ---- | ------------------------------------------------------ | -------- | ----------------------------------------------------------------------------------------------- |
| `beergame/narrative/templates.py`   | 8    | Docstring mentions "Format placeholders"                | ℹ️ Info  | False positive — docstring describes interpolation placeholders, not a stub                     |
| `beergame/views/play.py`            | 89   | Comment references `use_container_width=True`           | ℹ️ Info  | False positive — comment explains why kwarg is NOT used; no actual function call                |

No blockers. No actual stubs. No NumPy/pandas imports. No Streamlit imports in engine/ai/config/charts/narrative.

### Purity & Compliance Checks

| Check                                                                       | Result    |
| --------------------------------------------------------------------------- | --------- |
| `beergame/engine`, `ai`, `config` Streamlit-free (AST guard)                | ✓ PASS    |
| `beergame/charts` Streamlit-free (grep)                                     | ✓ PASS    |
| `beergame/narrative` Streamlit-free (grep)                                  | ✓ PASS    |
| No NumPy / pandas imports anywhere under `beergame/`                        | ✓ PASS    |
| No `use_container_width=True` as a function call (only in comments)         | ✓ PASS    |
| Phase 1 invariants intact (test_bullwhip_emerges, test_equilibrium)         | ✓ PASS    |
| Phase 2 invariants intact (test_app_smoke originals, test_station_view_*)   | ✓ PASS    |
| Full test suite                                                             | ✓ 82/82 PASS |

### Canonical Seed=42 Numbers (DEB-03 / DEB-04 verification)

```
variance_bullwhip_ratio(canonical):     35.3804  (spec: ~35.38) ✓
per_echelon_amplification:
  RETAILER:    3.4258
  WHOLESALER: 12.8145
  DISTRIBUTOR: 29.2671
  FACTORY:    35.3804   (Monotonic R<W<D<F: True ✓)
cost_breakdown reconciliation (delta = |row.total - cost_history[-1]|):
  RETAILER:    delta = 0.000000  ✓
  WHOLESALER:  delta = 0.000000  ✓
  DISTRIBUTOR: delta = 0.000000  ✓
  FACTORY:     delta = 0.000000  ✓
```

### Human Verification Required

#### 1. "Play again" → setup vs. rules navigation

**Test:** Complete a 36-week game, then click "Play again" on the debrief.

**Expected:** The user lands directly on the **setup** screen (station radio + seed input + "Start game" button). Per Phase 3 Success Criterion 5: "Play again button resets session_state and returns to setup."

**Actual (programmatically traced via AppTest):** After clicking "Play again", `session_state.phase == "rules"` (not "setup"). `reset_game` in `app.py:91-97` pops `phase`, but `_init_session_state` defaults `phase` to `"rules"` when it's missing. `seen_rules=True` is preserved (good — the user shouldn't have to re-read rules), but `rules.render` is still called and the user must click "Got it — set up my game" to reach setup. This is one extra click between debrief and a fresh game.

**Why human:** This is a UX judgment, not a bug. Three valid resolutions:
- (a) Accept the extra click — the rules screen is short and the second visit serves as a brief "deep breath" between games.
- (b) Modify `reset_game` to set `phase = "setup"` directly so the second game starts at setup.
- (c) Modify `rules.render` (or the app.py router) to skip the rules screen when `seen_rules=True` and auto-route to setup.

**Test plan if accepting (a):** Manual playthrough confirms the rules screen renders, "Got it" works, and the user can immediately start a new game with previous role/seed remembered (or defaults).

**Test plan if patching (b/c):** Change one line, re-run `tests/test_app_smoke.py` to confirm no regression, and verify by AppTest that `phase == "setup"` after Play again click.

### Gaps Summary

**Functionality gap:** None — all Phase 3 must-haves implemented and wired.

**Spec ambiguity:** Success Criterion 5 says "returns to setup" but the implementation returns to "rules". This is technically a literal-spec deviation but functionally a near-equivalent (same number of clicks if the user has already seen rules; one extra view in between). The 03-02 SUMMARY acknowledges `reset_game` preserves `seen_rules` but does not call out that the next phase will be "rules" rather than "setup".

**Test coverage:** Strong. 82 tests passing, no regressions. The reconciliation invariant (DEB-04) is tested with `pytest.approx(abs=0.01)` and reconciles to delta=0.0. The variance ratio (DEB-03) is tested for both the headline and per-echelon monotonicity. The chart (DEB-01/DEB-02) is tested against `go.Figure` (8 traces, vline at x=5, "4 → 8" annotation, "Week" axis title). The narrative (DEB-05) is tested for word count, bullwhip mention, role name, determinism, markdown bold, and cost interpolation.

**Test status:** 82/82 passing (4 AST guard tests + 6 chart structure + 9 metrics + 6 narrative + 10 app_smoke + others).

---

*Verified: 2026-05-18T22:00:00Z*
*Verifier: Claude (gsd-verifier)*
