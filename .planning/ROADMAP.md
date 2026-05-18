# Roadmap: Beer Game

## Overview

A teaching simulator whose only correctness criterion is that the canonical bullwhip emerges in the debrief. We build engine-first (pure Python, zero `streamlit` imports) so pytest can verify the bullwhip *before* any UI work begins, then layer Streamlit play UI, then debrief charts + narrative, then deploy to Streamlit Community Cloud. Four phases, each delivering a coherent verifiable capability.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Simulation Engine + AI** - Pure-Python engine and Sterman AI; the canonical bullwhip is provable via pytest before any UI exists (completed 2026-05-18)
- [ ] **Phase 2: UI Shell + Per-Turn Play** - Streamlit setup/rules/play screens; a human can play all 36 weeks against three AI opponents
- [ ] **Phase 3: Debrief Charts + Narrative** - 4-panel chart, amplification ratio, cost breakdown, and ≤200-word per-station narrative
- [ ] **Phase 4: Deploy to Streamlit Community Cloud** - Public URL on Streamlit Community Cloud from `greycloak85/beer-game` with pinned Python 3.12

## Phase Details

### Phase 1: Simulation Engine + AI
**Goal**: A pure-Python simulation engine and Sterman AI that demonstrably reproduce the canonical Beer Game equilibrium and bullwhip, verifiable by pytest without any Streamlit dependency.
**Depends on**: Nothing (first phase)
**Requirements**: ENG-01, ENG-02, ENG-03, ENG-04, ENG-05, ENG-06, ENG-07, ENG-08, ENG-09, ENG-10, AI-01, AI-02, AI-03, AI-04
**Success Criteria** (what must be TRUE):
  1. **GATE 1 — Equilibrium regression**: `pytest tests/test_equilibrium.py` passes — given constant demand=4 and all four stations played by Sterman AI, inventory at every station equals 12 for all 36 weeks (no drift, no transient).
  2. **GATE 2 — Bullwhip calibration**: `pytest tests/test_bullwhip_emerges.py` passes — given the classic step demand (4→8 at week 5) and all four stations played by Sterman AI, `max(factory_orders) / max(retailer_orders) ∈ [2.0, 4.0]`.
  3. `grep -r "import streamlit" engine/ ai/` returns zero matches — the engine and AI modules are pure Python and import-clean.
  4. Running the engine twice with the same seed produces byte-identical state traces (determinism); a non-Retailer `StationView` raises `AttributeError` if code attempts to read `customer_demand`.
  5. The tick sequence executes in the exact canonical order — receive shipments → fill orders → record state → place new orders → advance pipelines — verified by `tests/test_tick_invariants.py`.
**Plans**: 3 plans in 3 waves (sequential — Plans 02 and 03 import artifacts from Plan 01; Plan 03 consumes the Sterman agent from Plan 02)
- [ ] 01-01-PLAN.md — Engine scaffolding + state/tick/costs/demand/metrics + Agent protocol + ConstantOrderAgent + 4 invariant tests (ENG-02..10, AI-02)
- [ ] 01-02-PLAN.md — Sterman empirical AI agent + heuristic test + AST no-streamlit-import guard (AI-01, AI-02, ENG-01)
- [ ] 01-03-PLAN.md — GATE 1 (equilibrium regression) + GATE 2 (bullwhip calibration ratio ∈ [2.0, 4.0]) — Phase 1 exit gates (AI-03, AI-04)

### Phase 2: UI Shell + Per-Turn Play
**Goal**: A Streamlit app shell with phase-routed navigation that lets a human pick a station, read the rules + bullwhip primer, and play a full 36-week game one week at a time against three Sterman AI opponents.
**Depends on**: Phase 1
**Requirements**: SETUP-01, SETUP-02, SETUP-03, SETUP-04, PLAY-01, PLAY-02, PLAY-03, PLAY-04, PLAY-05
**Success Criteria** (what must be TRUE):
  1. A user opening the app sees a Rules + Bullwhip Primer screen on first visit, then a setup screen with a radio for station choice (R/W/D/F), an optional seed input, and a "Start game" button that transitions to play.
  2. During play, the user sees ONLY their own station's inventory, backlog, last week's shipments received, last week's orders received, an order-history mini-chart, and a "Week N of 36" counter — and the app exposes no UI surface for viewing other stations' state or future demand.
  3. The user can submit an order each week via `st.number_input` (min 0, no upper cap) inside an `st.form`, click "Advance week", and the week counter increments while the AI opponents place their orders behind the scenes.
  4. After the user submits the order for week 36, the app automatically transitions to the debrief view (even if the debrief is still a placeholder in this phase).
  5. A page refresh resets the game cleanly (in-session `st.session_state` only — no stale state leaks between runs), and a full manual playthrough completes without exceptions.
**Plans**: 3 plans in 3 waves (sequential — Plan 02 consumes Plan 01's `last_shipment_received`; Plan 03 replaces Plan 02's `play.py` stub and depends on the app router's `submit_order` callback being wired)
- [ ] 02-01-PLAN.md — Engine API extension: `shipments_received_history` on StationState, `last_shipment_received` on StationView/RetailerView, +7 regression tests (enables PLAY-01)
- [ ] 02-02-PLAN.md — App shell: `app.py` (phase router, session_state, 4 callbacks) + `beergame/views/` package (rules, setup, debrief placeholder, play stub) + `.streamlit/config.toml` (SETUP-01..04)
- [ ] 02-03-PLAN.md — Full play view replacing the stub + `tests/test_app_smoke.py` AppTest coverage of 4 key transitions (PLAY-01..05)

### Phase 3: Debrief Charts + Narrative
**Goal**: A post-game debrief that visually reproduces the canonical bullwhip pattern, quantifies amplification and cost, and explains in plain language what the player just experienced — so the lesson lands without an instructor.
**Depends on**: Phase 2
**Requirements**: DEB-01, DEB-02, DEB-03, DEB-04, DEB-05, DEB-06
**Success Criteria** (what must be TRUE):
  1. After week 36, the user sees a 4-panel chart (one panel per station, shared weeks x-axis) plotting orders and inventory across the full game, with an annotated vertical line at week 5 marking the customer-demand step from 4 to 8.
  2. The debrief displays an amplification ratio `variance(factory_orders) / variance(customer_demand)` plus per-echelon ratios; on a canonical all-default run the ratio is recognizably > 1 and visibly increases moving upstream.
  3. The debrief displays a per-station cost breakdown table with holding cost, backorder cost, and total — and the totals reconcile with the engine's internal cost ledger.
  4. The debrief shows a ≤200-word narrative paragraph adapted to the player's chosen station that names the bullwhip and points to where it shows up in their game.
  5. A "Play again" button on the debrief returns the user to the setup screen and resets `st.session_state` so a fresh game can begin.
**Plans**: TBD

### Phase 4: Deploy to Streamlit Community Cloud
**Goal**: The app is live at a public Streamlit Community Cloud URL, deployed from the public GitHub repo with pinned dependencies and Python 3.12, and reachable by anyone with the link.
**Depends on**: Phase 3
**Requirements**: DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04, DEPLOY-05, DEPLOY-06
**Success Criteria** (what must be TRUE):
  1. The repo at `github.com/greycloak85/beer-game` is public and contains `requirements.txt` (pinned `streamlit==1.57.0` and `plotly==6.7.0` only), `.python-version` (`3.12`), and a `.gitignore` that excludes `.streamlit/secrets.toml`, `__pycache__/`, `.venv/`, `*.pyc`, and `uv.lock`.
  2. `uv.lock`, `Pipfile`, `pyproject.toml`, and `environment.yml` are NOT committed to the repo (verified via `git ls-files`), so Streamlit Cloud's dependency-file priority resolves to `requirements.txt`.
  3. The Streamlit Community Cloud deployment is reachable at a public URL, has Python set to 3.12 in the CC "Advanced settings" dropdown, and the deploy log confirms CC selected Python 3.12.
  4. A first-time visitor can open the live URL (tolerating ~30s cold start), play a full 36-week game, and reach the debrief without errors.
  5. The repo `README.md` explains how to play, links to the live app, and notes the ~30-second cold-start delay.
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Simulation Engine + AI | 0/3 | Complete    | 2026-05-18 |
| 2. UI Shell + Per-Turn Play | 0/3 | Not started | - |
| 3. Debrief Charts + Narrative | 0/TBD | Not started | - |
| 4. Deploy to Streamlit Community Cloud | 0/TBD | Not started | - |

---
*Roadmap created: 2026-05-18*
*Phase 1 planned: 2026-05-18 — 3 plans in 3 waves covering ENG-01..10 + AI-01..04*
*Phase 2 planned: 2026-05-18 — 3 plans in 3 waves covering SETUP-01..04 + PLAY-01..05; engine extension `shipments_received_history` precedes UI work*
