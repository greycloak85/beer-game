---
phase: 02-ui-shell-per-turn-play
plan: 02
subsystem: ui-shell
tags: [ui, streamlit, session-state, phase-router, views, callbacks, agent-persistence]

# Dependency graph
requires:
  - phase: 02-ui-shell-per-turn-play
    plan: 01
    provides: "StationView.last_shipment_received (default 0), shipments_received_history on StationState, AST guard 4/4 at 51 tests"
provides:
  - "app.py @ repo root: Streamlit entry point, phase router, four callbacks (go_to_setup, start_game, submit_order, reset_game), guarded session_state init"
  - "beergame/views/ package: rules.py (Bullwhip Primer), setup.py (station+seed form), play.py (Plan-03 stub), debrief.py (Phase-3 placeholder)"
  - ".streamlit/config.toml: theme/server/browser defaults (amber primaryColor, headless, no usage stats)"
  - "requirements-dev.txt: streamlit==1.57.0 + plotly==6.7.0 pinned for dev"
  - "Sterman agent persistence pattern: ai_agents dict instantiated once in start_game, lives in session_state.ai_agents, threaded through every advance_week call"
affects: [02-03-per-turn-play-view, phase-03-debrief, phase-04-deploy]

# Tech tracking
tech-stack:
  added:
    - "streamlit==1.57.0 (dev only — Phase 4 ships requirements.txt)"
    - "plotly==6.7.0 (dev only — Plan 03 will consume for the per-turn mini-chart)"
  patterns:
    - "Phase-router pattern: single st.session_state.phase string dispatches to exactly one view.render() per rerun"
    - "Guarded session_state init: every assignment gated on `if \"key\" not in st.session_state` — Pitfall 1"
    - "Widget-key binding: setup.py's st.radio(key=\"player_role\") and st.number_input(key=\"seed\") bind to the same session_state slots app.py initializes; start_game reads via st.session_state.player_role, no args= needed"
    - "Pure-view contract: render functions take args + read session_state, call st.*, return None — they NEVER mutate session_state (mutation lives only in app.py callbacks)"
    - "Sterman agent persistence: dict[Role, Agent] instantiated ONCE in start_game and reused across all ticks so smoothed_demand accumulates — Pitfall 8"
    - "submit_order reads order via st.session_state[\"order_input\"] (NOT args=) — Pitfall 2: args captures value at form-render time, not submit time"

key-files:
  created:
    - app.py
    - beergame/views/__init__.py
    - beergame/views/rules.py
    - beergame/views/setup.py
    - beergame/views/play.py
    - beergame/views/debrief.py
    - .streamlit/config.toml
  modified:
    - requirements-dev.txt

key-decisions:
  - "streamlit + plotly are dev-only — added to requirements-dev.txt, NOT requirements.txt. Phase 4 owns the deploy-time pin file per ROADMAP."
  - "play.py shipped as a stub in Plan 02 to close the import graph (beergame/views/__init__.py imports play, app.py references play.render). Plan 03 replaces the body; the on_submit callback contract is already locked."
  - "submit_order is owned by app.py, NOT play.py — only app.py mutates session_state (Pattern 3 from 02-RESEARCH.md). Plan 03 just wires play.py's st.form_submit_button(on_click=on_submit) to the callback app.py already provides."
  - "reset_game pops phase/player_role/seed/game/ai_agents but deliberately NOT seen_rules — in-session replay skips the primer; browser refresh wipes everything including seen_rules so SETUP-01 still holds across sessions."
  - "Use `:beer_mug:` (not `:beer:`) consistently across all titles for Streamlit's shortcode set."
  - "Setup form binds widget values via key= alone (no value= parameter). The session_state defaults (Role.RETAILER, DEFAULT_SEED=42) flow through automatically — passing both key= and value= triggers StreamlitAPIException on widget-value conflict."

patterns-established:
  - "Pattern A — Repo-root entry point: app.py lives at /, NOT under beergame/. This is the path streamlit run + Streamlit Cloud target. Phase 4 deploy uses this same path."
  - "Pattern B — Engine/View import boundary: only beergame/views/* and app.py import streamlit. beergame/{engine,ai,config}/* remain pure-Python per ENG-01 and the AST guard."
  - "Pattern C — Callback ownership: each render(callback) takes the callback as an argument, never imports app.py. Inversion of control keeps views independently testable."

requirements-completed:
  - SETUP-01
  - SETUP-02
  - SETUP-03
  - SETUP-04

# Metrics
duration: 2m 59s
completed: 2026-05-18
---

# Phase 02 Plan 02: UI Shell Summary

**First Streamlit code in the codebase: app.py phase router + four view modules. Boots cleanly to the Rules screen; setup form drives the player into a Plan-03 play stub; 51/51 tests still pass; AST guard still 4/4 (engine layer streamlit-free).**

## Performance

- **Duration:** 2m 59s
- **Started:** 2026-05-18T20:57:06Z
- **Completed:** 2026-05-18T21:00:05Z
- **Tasks:** 3
- **Files created:** 7
- **Files modified:** 1

## Accomplishments

- Stood up `app.py` at the **repo root** as the Streamlit entry point: phase router dispatching on `st.session_state.phase ∈ {"rules", "setup", "playing", "done"}` plus four callbacks (`go_to_setup`, `start_game`, `submit_order`, `reset_game`).
- Six session_state keys are guard-initialized on every rerun (phase, seen_rules, player_role, seed, game, ai_agents) — Pitfall 1 (unguarded init wipes state on click) is structurally avoided.
- Stood up `beergame/views/` package with four modules: `rules.py` (Bullwhip Primer + CTA), `setup.py` (station radio + seed input + Start-game form), `play.py` (Plan-03 stub — keeps the import graph closed), `debrief.py` (Phase-3 placeholder with `is_game_over` assertion + final-station metrics + Play-again button).
- Sterman agents are instantiated **once** in `start_game` (one `ShipmentAnchorAndAdjustAgent` per non-player Role) and persisted in `session_state.ai_agents` — Pitfall 8 (per-tick agent re-instantiation kills smoothed_demand) is structurally avoided.
- `submit_order` reads the player's order via `st.session_state["order_input"]`, NOT via `args=` — Pitfall 2 (args captures the value at form-render time) is structurally avoided.
- `.streamlit/config.toml` brands the app (amber primaryColor, headless server default, gatherUsageStats off). Phase 4 will extend with deploy-specific tweaks.
- Smoke test: `streamlit run app.py` serves HTTP 200; `_stcore/health` returns `ok`; no errors in the log.
- Full pytest suite: **51/51 passing** (no regression from Plan 01).
- AST guard `tests/test_no_streamlit_import.py`: **4/4 passing** — engine layer remains streamlit-free.

## Task Commits

Each task was committed atomically:

1. **Task 1: app.py phase router + session_state + four callbacks** — `08717ab` (feat)
2. **Task 2: views package (rules, setup, debrief)** — `5dfbd27` (feat)
3. **Task 3: play.py stub + .streamlit/config.toml + dev deps** — `3b00913` (feat)

## Files Created/Modified

### Created (7)

- `app.py` (112 lines) — Streamlit entry point, phase router, `_init_session_state`, callbacks (`go_to_setup`, `start_game`, `submit_order`, `reset_game`), top-level dispatch on `st.session_state.phase`.
- `beergame/views/__init__.py` — Re-exports the four view modules so `from beergame.views import rules, setup, play, debrief` resolves.
- `beergame/views/rules.py` — `render(on_continue)`: title + ~200-word primer (chain diagram, per-week sequence, visibility, $0.50/$1.00 cost asymmetry, bullwhip explanation, goal) + primary CTA.
- `beergame/views/setup.py` — `render(on_start)`: `st.form` containing `st.radio(key="player_role")`, `st.number_input(key="seed")`, `st.form_submit_button(on_click=on_start)`.
- `beergame/views/play.py` (stub) — `render(state, on_submit)`: yellow warning banner + debug line. Plan 03 replaces the body.
- `beergame/views/debrief.py` — `render(state, on_reset)`: asserts `is_game_over(state)`, shows station's total orders / final inventory / final backlog / final cumulative cost, "Play again" button.
- `.streamlit/config.toml` — Minimal theme + server + browser config.

### Modified (1)

- `requirements-dev.txt` — Added `streamlit==1.57.0` and `plotly==6.7.0` for local UI development. Phase 4 ships `requirements.txt` for Streamlit Cloud (deploy-time pin file is intentionally separate).

## Decisions Made

- **app.py lives at repo root, NOT under `beergame/`** — Streamlit Cloud and `streamlit run` both target the repo-root path; matching that path now means Phase 4 deploy is a no-op for app discovery.
- **play.py shipped as a Plan-02 stub** — Splitting the play view into its own plan (Plan 03) is intentional. Plan 03 benefits from a fresh context window for the heaviest UI work. Stubbing it in Plan 02 closes the import graph so SETUP-01..04 are end-to-end verifiable.
- **submit_order is owned by app.py** — Pattern 3 (research): only `app.py` mutates session_state. Plan 03's play view will pass `on_click=on_submit` to its form-submit button; the callback is already wired and waiting for `st.session_state["order_input"]`.
- **streamlit + plotly are dev-only deps** — Added to `requirements-dev.txt`, NOT `requirements.txt`. Phase 4 owns the deploy-time pin file per ROADMAP / Phase 1 decisions ("`uv.lock` is NOT committed; Streamlit Cloud's dependency-file priority would pick it up; yanked transitives can wedge builds").
- **`reset_game` preserves `seen_rules`** — In-session replay skips the primer (better UX); browser refresh still wipes everything (Streamlit default behavior), so SETUP-01's first-visit invariant still holds across browser sessions.
- **Setup-form widgets use `key=` ONLY (no `value=`)** — Streamlit raises `StreamlitAPIException` if a widget binds both `key` and `value`. The session_state slot supplies the default (Role.RETAILER, DEFAULT_SEED=42); the widget reads from and writes to that slot directly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Installed streamlit + plotly into venv and pinned in requirements-dev.txt**

- **Found during:** Task 0 (environment check, before Task 1).
- **Issue:** Neither `streamlit` nor `plotly` was installed in `.venv`; without them, `streamlit run app.py` (required by the Plan's end-to-end smoke and by the success criterion "running `.venv/bin/streamlit run app.py` brings up a working flow") could not run.
- **Fix:** Installed `streamlit==1.57.0` + `plotly==6.7.0` via `.venv/bin/pip install`, then added both to `requirements-dev.txt` (not `requirements.txt` — Phase 4 ships the deploy-time pin file).
- **Why dev-only:** Phase 1 decision ("Phase 4 deploy uses `requirements.txt` only; `uv.lock` is NOT committed") and environment notes both say deploy deps live in `requirements.txt` (Phase 4 territory). Local dev deps belong in `requirements-dev.txt`.
- **Files modified:** `requirements-dev.txt` (committed alongside Task 3 since the streamlit dep is exactly what makes the Task-3 smoke test runnable).
- **Verification:** `.venv/bin/streamlit run app.py --server.headless true --server.port 8501` boots; HTTP 200 served at `/`; `_stcore/health` returns `ok`; no errors in log.
- **Committed in:** `3b00913` (Task 3 commit — bundled with `play.py` stub + `.streamlit/config.toml` since all three are prerequisites for the same smoke test).

**Total deviations:** 1 auto-fixed (1 blocking).
**Impact on plan:** None on behavior or scope — strictly an environment prerequisite. No engine-layer code touched.

## Issues Encountered

None. The plan was unusually clean — the architectural patterns (phase router, guarded init, agent persistence, view/engine boundary) were spelled out precisely in 02-RESEARCH.md, and the three-task split mapped exactly to the three logical concerns (router, content, infrastructure). No checkpoints triggered; no Rule-4 architectural decisions surfaced.

## User Setup Required

None for development — `streamlit run app.py` works out of the box once `pip install -r requirements-dev.txt` is run.

For Phase 4 deploy: Phase 4's plan will need to produce a `requirements.txt` (deploy-time pinning) including `streamlit==1.57.0` and `plotly==6.7.0`. Streamlit Community Cloud reads this file at build time.

## Next Phase Readiness

- **Plan 03 (per-turn play view) is fully unblocked.** Replace `beergame/views/play.py`'s body with the real per-turn view: metrics for the player's StationView (inventory, backlog, last_shipment_received, last_order_received, customer_demand if RETAILER, supply_line), a Plotly mini-chart over `recent_orders_received`, and an `st.form("play_form")` with `st.number_input(min_value=0, max_value=999, step=1, key="order_input")` plus `st.form_submit_button("Advance week", on_click=on_submit)`. The `on_submit` callback in `app.py` is already wired up and reads `st.session_state["order_input"]`.
- **Sterman agents persist correctly.** Plan 03's play view does NOT need to touch `ai_agents` — `app.py::submit_order` already threads `session_state.ai_agents` through every `advance_week` call.
- **Phase 3 (debrief charts) handoff:** Replace `beergame/views/debrief.py`'s placeholder body with the real charts + narrative. The render signature `(state: GameState, on_reset)` is locked, and `app.py::reset_game` (the on_reset target) is already wired.
- **Phase 4 (deploy) handoff:** `app.py` is at the repo root where Streamlit Cloud expects it; `.streamlit/config.toml` is in place. Phase 4 needs only to: (1) write `requirements.txt`, (2) configure secrets (none in v1), (3) point Streamlit Cloud at `app.py`.

## Self-Check: PASSED

- FOUND: `app.py` (at repo root, 112 lines, parses OK)
- FOUND: `beergame/views/__init__.py` (re-exports rules, setup, play, debrief)
- FOUND: `beergame/views/rules.py` (`render(on_continue)` callable)
- FOUND: `beergame/views/setup.py` (`render(on_start)` callable, uses `st.form`)
- FOUND: `beergame/views/play.py` (`render(state, on_submit)` callable — stub, Plan 03 replaces)
- FOUND: `beergame/views/debrief.py` (`render(state, on_reset)` callable, asserts `is_game_over`)
- FOUND: `.streamlit/config.toml` (theme + server + browser sections)
- FOUND: `requirements-dev.txt` includes `streamlit==1.57.0` + `plotly==6.7.0`
- FOUND: commit `08717ab` (feat: app.py phase router)
- FOUND: commit `5dfbd27` (feat: views package)
- FOUND: commit `3b00913` (feat: play stub + config.toml + dev deps)
- VERIFIED: 51/51 tests passing (no regression from Plan 01)
- VERIFIED: AST guard `tests/test_no_streamlit_import.py` 4/4 (engine layer streamlit-free)
- VERIFIED: `streamlit run app.py` boots, serves HTTP 200, `_stcore/health` returns `ok`
- VERIFIED: import chain `from beergame.views import rules, setup, play, debrief` closes cleanly

---
*Phase: 02-ui-shell-per-turn-play*
*Completed: 2026-05-18*
