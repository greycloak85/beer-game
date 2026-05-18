---
phase: 03-debrief-charts-narrative
plan: 02
subsystem: debrief-view
tags: [streamlit, plotly, narrative, st-metric, st-table, st-plotly-chart, apptest, parametrize, debrief, bullwhip]

# Dependency graph
requires:
  - phase: 03-debrief-charts-narrative
    plan: 01
    provides: variance_bullwhip_ratio + per_echelon_amplification + cost_breakdown (CostRow) in engine/metrics.py; build_four_panel(state) -> go.Figure in beergame/charts; canonical_done_state session-scoped fixture in tests/conftest.py
  - phase: 02-ui-shell-per-turn-play
    provides: app.py phase-router with reset_game callback (preserves seen_rules); st.plotly_chart(fig, key=..., width="stretch") convention; AppTest 1.57.0 patterns (at.button covers both st.button and st.form_submit_button)
provides:
  - "beergame/narrative package: public narrative_for(state) -> str + four station-specific templates (Retailer/Wholesaler/Distributor/Factory), each ≤200 words post-interpolation on canonical seed=42 run, all mention 'bullwhip', all use markdown **bold**"
  - "beergame/views/debrief.py: full Phase-3 layout — title + headline 2dp st.metric + 4-panel chart + 4 per-echelon st.metric tiles + cost breakdown st.table + narrative st.markdown + Play again st.button"
  - "tests/test_narrative.py: 6 pure-Python tests (≤200 words per role, 'bullwhip' literal, role name, determinism, markdown bold, cost number interpolation)"
  - "tests/test_app_smoke.py: 2 new AppTest tests (Retailer debrief content check + parametrized over all 4 roles) — 7 → 10 smoke tests total"
  - "DEB-01 through DEB-06 visually delivered end-to-end on the canonical seed=42 run"
affects: [streamlit-run-bootable, phase-3-complete, debrief-experience, future-narrative-additions, future-playable-content]

# Tech tracking
tech-stack:
  added: []  # No new dependencies — uses existing streamlit==1.57.0, plotly==6.7.0, statistics stdlib
  patterns:
    - "Static-template narrative module (beergame/narrative/) mirrors engine/ai/charts purity contract — zero streamlit imports; views layer is the ONLY place Streamlit + narrative meet"
    - "Format-string templates with light interpolation (≤200 words post-substitution); markdown **bold** for emphasis on role name + 'bullwhip effect' + cost; \\$ literal escapes the dollar so st.markdown doesn't interpret it as LaTeX"
    - "Debrief view as thin assembler — math in engine/metrics, chart construction in charts/, narrative copy in narrative/; views/debrief.py is glue + Streamlit primitives only"
    - "AppTest parametrize-over-roles via @pytest.mark.parametrize + at.session_state.player_role mutation (the radio key in setup.py is bound to player_role)"
    - "AppTest accessors used: at.metric (.label, .value), at.subheader (.value), at.button (.label), at.session_state, at.exception — covers headline metric, section titles, Play again button, exception handling"

key-files:
  created:
    - beergame/narrative/__init__.py
    - beergame/narrative/templates.py
    - tests/test_narrative.py
  modified:
    - beergame/views/debrief.py
    - tests/test_app_smoke.py

key-decisions:
  - "Narrative templates copied verbatim from 03-RESEARCH.md Pattern 3 (Plan 03-02 environment notes confirm ≤200 words target with 2dp format strings) — kept as static format-strings, no LLM, no random selection, deterministic by construction"
  - "Display headline as 2 decimals (`{overall:.2f}×`) not the 1-decimal RESEARCH.md sample — orchestrator's locked decision per environment notes; per-echelon tiles also 2dp for visual consistency with the headline"
  - "Set player_role via at.session_state.player_role before submitting the setup form (NOT at.radio[0].set_value(Role.X)) — the setup form's radio is keyed to player_role, so writing to session_state and then submitting goes through the same start_game callback path the real user flow uses"
  - "AppTest cannot inspect Plotly charts (at.plotly_chart returns UnknownElement). The load-bearing chart check at the AppTest layer is `not at.exception`; chart structure is covered by Plan 01's tests/test_charts_orders_inventory.py at the go.Figure level (8 traces, vline at x=5, '4→8' annotation, 'Week' axis title)"
  - "Cost interpolation uses `{cost:,.0f}` (integer dollars, comma-grouped). Templates escape the literal $ as `\\$` so st.markdown renders the dollar sign instead of interpreting it as a LaTeX delimiter (Streamlit treats unescaped $...$ as inline math)"
  - "Empty-history fallbacks (Retailer/Factory peaks): narrative_for guards with `if history else 0` even though canonical 36-week games never produce empty histories — defensive for partial-game states the user might force"

patterns-established:
  - "Static narrative module: format-string templates keyed by Role, single public function narrative_for(state) -> str, all interpolation values pulled from beergame.engine.metrics (variance ratios + cost breakdown)"
  - "Debrief view structure: title → headline st.metric → st.plotly_chart → st.subheader + st.columns(4) of st.metric → st.subheader + st.table → st.subheader + st.markdown → st.button. Reusable for future debrief sections (just append more subheader/element pairs)"
  - "AppTest parametrize-over-roles: @pytest.mark.parametrize(\"role_name\", [...]) + at.session_state[key] = value before form submit. Use Role[role_name] to convert the string param back to the enum"

requirements-completed:
  - DEB-01  # 4-panel chart rendered in debrief view
  - DEB-02  # Week-5 vline + annotation visible in chart (from Plan 01)
  - DEB-03  # Headline st.metric + 4 per-echelon st.metric tiles (2dp)
  - DEB-04  # Cost breakdown st.table with Station/Holding/Backorder/Total
  - DEB-05  # Narrative paragraph per role via st.markdown(narrative_for(state))
  - DEB-06  # Play again button bound to app.py::reset_game

# Metrics
duration: 4min 26s
completed: 2026-05-18
---

# Phase 3 Plan 02: Debrief View Assembly + Narrative Templates Summary

**Plan 01's pure-Python math + chart wired into the live Streamlit debrief view; four static narrative templates (Retailer/Wholesaler/Distributor/Factory) ≤200 words each; AppTest smoke confirms all four player roles reach a no-exception debrief at week 36. Phase 3 — the bullwhip lesson lands without an instructor — is complete.**

## Performance

- **Duration:** 4 min 26 s
- **Started:** 2026-05-18T21:40:07Z
- **Completed:** 2026-05-18T21:44:33Z
- **Tasks:** 3
- **Files created:** 3 (`beergame/narrative/__init__.py`, `beergame/narrative/templates.py`, `tests/test_narrative.py`)
- **Files modified:** 2 (`beergame/views/debrief.py`, `tests/test_app_smoke.py`)
- **Tests:** 71 prior + 11 new = 82 passing, 0 failed (6 new narrative + 5 new AppTest smoke — 1 Retailer content check + 4 parametrized over Role)

## Accomplishments

- **DEB-05 narrative:** `beergame/narrative/` package shipped — `narrative_for(state) -> str` selects one of four templates by `state.player_role` and interpolates the canonical metrics (`variance_bullwhip_ratio`, `per_echelon_amplification[role]`, `per_echelon_amplification[FACTORY]`, this role's `cost_breakdown` total, and Retailer/Factory order peaks for the Retailer template). All four templates: ≤200 words post-interpolation on canonical seed=42 run, mention "bullwhip" literally, use markdown bold, escape `\$` to dodge Streamlit's LaTeX interpretation.
- **Debrief view rewrite (DEB-01..06):** `beergame/views/debrief.py` replaced end-to-end with the full Phase-3 layout — title, headline `st.metric("Bullwhip amplification", "35.38×")`, 4-panel chart via `st.plotly_chart(fig, key="debrief_four_panel", width="stretch")`, four per-echelon `st.metric` tiles in `st.columns(4)`, cost breakdown `st.table([dict, ...])` (no pandas, no `st.dataframe`), narrative paragraph via `st.markdown(narrative_for(state))`, and `st.button("Play again", on_click=on_reset, ...)`. The view is a thin assembler — no math, no chart construction, no narrative copy lives here.
- **AppTest smoke extension:** `tests/test_app_smoke.py` now has 10 tests (5 original + 1 canonical-Retailer debrief content check + 4 parametrized over all `Role` members). The content check asserts the headline metric label, the "Cost breakdown" and "What just happened" subheaders, and the "Play again" button label all appear in the rendered debrief; the parametrized test proves the narrative module renders without exception for every role.
- **Streamlit boot verified:** `.venv/bin/streamlit run app.py` boots cleanly on port 8765, HTTP 200 on `/_stcore/health`. The app is end-to-end playable (rules → setup → 36 weeks of play → debrief with chart + narrative + Play again).
- **Purity invariants intact:** AST guard 4/4 still passes (engine + ai + config remain streamlit-free); `beergame/charts/` and `beergame/narrative/` also streamlit-free by design. No numpy / pandas anywhere in `beergame/`. The `use_container_width` deprecated kwarg appears nowhere as an actual function call (one reference exists in a pre-existing comment in `play.py` explaining why we DON'T use it).
- **Phase 1 invariants intact:** Max-based bullwhip ratio still 2.000 at seed=42 (GATE 2 untouched); equilibrium inventory still 12 for 36 weeks under all-ConstantOrderAgent(4); variance-based ratio still 35.38 at seed=42 (matches Plan 01 canonical numbers).

## Canonical seed=42 Verification

Per-role rendered word counts (matches the ≤200 ceiling well, leaves margin for future template tweaks):

| Role | Words (post-interpolation) | Headline Display |
|------|---------------------------:|------------------|
| Retailer | 127 | `35.38×` |
| Wholesaler | 121 | `35.38×` |
| Distributor | 124 | `35.38×` |
| Factory | 142 | `35.38×` |

The headline display is the same across roles (it's the overall variance-bullwhip ratio, not per-role). What changes per role: the template body (different paragraph) and the interpolated `{cost}` (per-station total from `cost_breakdown`):

- Retailer cost interpolation: `$223` (rendered as `**\$223**` in markdown, displays as `$223`)
- Wholesaler cost: `$299`
- Distributor cost: `$499`  (`$498.50` rounded by `{cost:,.0f}`)
- Factory cost: `$422`  (`$421.50` rounded)

The `{cost:,.0f}` format rounds to the nearest dollar; the full cost table (in the debrief view above the narrative) displays 2dp via `{:.2f}` so the precise figure is still visible to the player.

## Task Commits

1. **Task 1: Create beergame/narrative/ package with four station templates and narrative_for(state)** — `e7889ab` (feat)
2. **Task 2: Rewrite views/debrief.py to render headline + 4-panel chart + per-echelon tiles + cost table + narrative + Play again** — `38b860b` (feat)
3. **Task 3: Extend AppTest smoke to assert the rich debrief renders without exception (all four player roles)** — `0dd7de6` (test)

## Files Created/Modified

**Created:**
- `beergame/narrative/__init__.py` — Public `narrative_for(state)` entry point. Pulls `variance_bullwhip_ratio`, `per_echelon_amplification`, `cost_breakdown` from `beergame.engine.metrics`; selects `_TEMPLATES[role]` and interpolates. Defensive empty-history fallbacks for Retailer/Factory peaks. `__all__ = ["narrative_for"]`.
- `beergame/narrative/templates.py` — Four `Role`-keyed format strings, written ≤180 words pre-interpolation so they stay ≤200 post. Each names "bullwhip" literally, uses markdown bold for emphasis, escapes `\$` (LaTeX dodge), and references the player's specific game (peaks for Retailer; per-echelon ratios for W/D/F).
- `tests/test_narrative.py` — 6 pure-Python tests covering ≤200 words per role, "bullwhip" literal (case-insensitive), role display name appearance, determinism (same input → same output), markdown bold spans (`**...**`), and per-role cost interpolation appearance.

**Modified:**
- `beergame/views/debrief.py` — Rewritten end-to-end. Replaces the Plan-02 placeholder body (which showed "Charts and narrative debrief are coming in Phase 3") with the full Phase-3 layout. Imports `build_four_panel`, the three new metrics functions, `narrative_for`, plus the existing `GameState` / `Role` / `is_game_over`. Asserts `is_game_over(state)` defensively. Renders 7 elements top-to-bottom: title, headline metric (2dp), 4-panel chart with stable `key=` and `width="stretch"`, "Amplification by station" subheader + 4-column metric grid, "Cost breakdown" subheader + `st.table`, "What just happened" subheader + `st.markdown(narrative_for(state))`, "Play again" button.
- `tests/test_app_smoke.py` — Added `pytest` + `Role` imports; appended two new tests after the existing 5: `test_debrief_renders_with_real_content_after_36_weeks_as_retailer` (asserts headline metric label + subheader text + Play again button + `not at.exception`); `test_debrief_renders_for_each_player_role` (parametrized over `["RETAILER", "WHOLESALER", "DISTRIBUTOR", "FACTORY"]` — drives a full 36-week run as each role, verifies `phase == "done"`, narrative subheader present, Play again button present, no exception).

## Decisions Made

- **2-decimal headline display (`{overall:.2f}×`)** — Plan environment notes confirmed this as the orchestrator's locked decision. Per-echelon tiles also use 2dp for visual consistency. The RESEARCH.md Pattern 4 sample showed 1dp but the locked spec wins; the narrative module still uses 1dp inside the prose (`{ratio:.1f}×`) because the prose reads more naturally at 1dp (a paragraph saying "35.4×" reads cleaner than "35.38×").
- **Static narrative templates verbatim from RESEARCH.md Pattern 3** — No paraphrasing, no LLM augmentation, no random selection. Deterministic by construction. The four templates each name the bullwhip in a slightly different framing (Retailer: "saw the start of it"; Wholesaler: "each echelon amplifies"; Distributor: "monotonic growth upstream"; Factory: "in its purest form") so a player who replays as multiple roles sees a different angle each time.
- **AppTest role-setting via `at.session_state.player_role`** — The setup view's radio is keyed to `player_role`, so writing to session_state before clicking the setup form's submit button reuses the real `start_game` callback path. The plan permitted either `at.radio[0].set_value(Role.X)` or the session_state approach; session_state is more robust because it sidesteps the AppTest 1.57.0 question of how radio accepts enum values.
- **`not at.exception` is the load-bearing chart check at the AppTest layer.** AppTest cannot inspect Plotly charts (returns `UnknownElement`). Chart structure is covered by Plan 01's `test_charts_orders_inventory.py` at the `go.Figure` level (8 traces, vline at x=5, "4 → 8" annotation, "Week" axis title on bottom panel). The AppTest smoke layer just confirms the chart renders end-to-end without raising.
- **`reset_game` covers all session-state keys.** The existing `app.py::reset_game` pops `("phase", "player_role", "seed", "game", "ai_agents")` — preserves `seen_rules`. This plan introduces NO new session-state keys (widget `key=` attributes only, which have widget-local state Streamlit manages itself). Verified by re-reading `app.py:91-97` against the new `debrief.py` — match.

## AppTest Accessor Quirks Encountered

For the next developer extending the AppTest smoke suite:

- `at.metric` returns a list. Each element exposes `.label` and `.value` (both strings). The headline metric has `label == "Bullwhip amplification"` and `value` like `"35.38×"`. The 4 per-echelon tiles have `label` matching each role's display name.
- `at.subheader` returns a list with `.value` (string). NOT `.label`. The three new subheaders are "Amplification by station", "Cost breakdown", "What just happened".
- `at.button` includes BOTH `st.button` and `st.form_submit_button` widgets, indexed by render order (Plan 02-03's discovery). The "Play again" button uses `at.button[-1]` on the debrief screen (it's the only button on debrief, but render-order indexing is more robust than label-matching for click-actions).
- The deprecation warning for `width="stretch"` does NOT appear in AppTest's exception list — `not at.exception` is True even though Streamlit prints deprecation warnings to stderr at startup. Don't rely on AppTest to catch deprecated kwargs; grep is the right tool for that.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Module-docstring mention of `use_container_width` triggered the grep-based verify check**
- **Found during:** Task 2 (running the `<verify>` block's `grep -n use_container_width beergame/views/debrief.py`)
- **Issue:** The new `debrief.py` module docstring had a sentence reading "`use_container_width=True` is deprecated" — meant as a why-we-don't-use-it note. The verify command `grep -n use_container_width beergame/views/debrief.py && echo 'DEPRECATED FOUND'` triggered on the docstring match.
- **Fix:** Rewrote the docstring sentence to say "the older container-width kwarg is deprecated" without using the literal token. The actual function call on line 68 is unchanged: `st.plotly_chart(fig, key="debrief_four_panel", width="stretch")`.
- **Files modified:** `beergame/views/debrief.py` (docstring only — no behavior change)
- **Verification:** `grep -n 'use_container_width' beergame/views/debrief.py` now returns nothing. The file's actual rendering behavior is identical.
- **Committed in:** `38b860b` (Task 2 commit — caught and fixed before the commit was made)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug — docstring token tripped a grep verifier).
**Impact on plan:** Zero functional impact; docstring polish only. All other plan instructions followed exactly (file paths, function signatures, test names, layout order, format strings, key attributes).

## Issues Encountered

None beyond the deviation above. All 82 tests pass on the first run after each task. AST guard 4/4 clean. Streamlit boots cleanly (HTTP 200 on `/_stcore/health`).

## User Setup Required

None — no external service configuration. The app is ready for `.venv/bin/streamlit run app.py` and a full playthrough.

## Next Phase Readiness

**Phase 3 is COMPLETE.** Both plans shipped:
- Plan 03-01 (engine metrics + chart builder): 71/71 tests passing.
- Plan 03-02 (debrief view + narrative + AppTest smoke): 82/82 tests passing.

DEB-01 through DEB-06 all visually delivered. The bullwhip lesson lands without an instructor: a player completes 36 weeks → sees the 35.38× headline → sees the 4-panel chart with the week-5 demand-step annotation → sees four per-echelon tiles showing R=3.43 / W=12.81 / D=29.27 / F=35.38 (monotonic upstream amplification) → sees the cost breakdown reconciling with the engine ledger → reads a paragraph in their own role's voice naming the bullwhip → clicks Play again to reset (preserves rules-already-seen).

**Phase 4 (Deploy to Streamlit Community Cloud)** is unblocked. The app is bootable, all invariants hold, the lesson works end-to-end. Phase 4 needs to:
1. Commit `requirements.txt` with `streamlit==1.57.0` and `plotly==6.7.0` pins (currently in `requirements-dev.txt`).
2. NOT commit `uv.lock` (Streamlit Cloud's dependency-file priority would pick it up; yanked transitives can wedge builds — locked decision from Phase 4 planning).
3. Push to the deploy branch / configure Streamlit Cloud to point at `app.py` at repo root (already at the correct path).

---
*Phase: 03-debrief-charts-narrative*
*Completed: 2026-05-18*

## Self-Check: PASSED

- FOUND: `beergame/narrative/__init__.py`
- FOUND: `beergame/narrative/templates.py`
- FOUND: `beergame/views/debrief.py` (modified)
- FOUND: `tests/test_narrative.py`
- FOUND: `tests/test_app_smoke.py` (modified)
- FOUND: `.planning/phases/03-debrief-charts-narrative/03-02-SUMMARY.md`
- FOUND: commit `e7889ab` (Task 1 — narrative package)
- FOUND: commit `38b860b` (Task 2 — debrief view rewrite)
- FOUND: commit `0dd7de6` (Task 3 — AppTest smoke extension)
