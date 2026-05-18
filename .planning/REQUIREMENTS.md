# Requirements: Beer Game

**Defined:** 2026-05-18
**Core Value:** A player completes one Beer Game round in one sitting and *sees* the bullwhip effect emerge in the post-game debrief — charts and narrative make the lesson land without an instructor in the room.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases. Every requirement here is "table stakes" per research — the lesson doesn't land without it.

### Simulation Engine

- [ ] **ENG-01**: Engine module is pure Python with zero `streamlit` imports so pytest can run determinism tests headlessly
- [ ] **ENG-02**: Engine models a 4-station serial supply chain: Retailer → Wholesaler → Distributor → Factory
- [ ] **ENG-03**: Engine runs a fixed 36-week game with classic step demand (4 cases/wk weeks 1–4, then 8 cases/wk weeks 5–36)
- [ ] **ENG-04**: Engine uses canonical lead times — 2-week shipping between every echelon, 1-week order/mailing delay for R/W/D, 2-week factory production delay (no order delay at Factory)
- [ ] **ENG-05**: Engine uses canonical asymmetric costs — $0.50 holding / $1.00 backorder per case per week
- [ ] **ENG-06**: Engine starts each game in canonical equilibrium — inventory=12, backlog=0, every pipeline slot pre-loaded with 4 units
- [ ] **ENG-07**: Each week ticks in the canonical sequence — receive shipments → fill orders → record state → place new orders → advance pipelines
- [ ] **ENG-08**: Engine accumulates backlog when demand exceeds available inventory, with backorder cost charged weekly
- [ ] **ENG-09**: Engine returns deterministic results for a given seed (no hidden randomness)
- [ ] **ENG-10**: Engine API exposes a per-station `StationView` that contains ONLY locally-knowable information (the Retailer is the only station whose view includes customer demand)

### AI Agents

- [ ] **AI-01**: Three AI opponents play the non-player stations using Sterman's *empirical* anchor-and-adjust heuristic (α≈0.26, β≈0.34, θ≈0.36, S′≈17) with the Sterman 1989 source cited in the code
- [ ] **AI-02**: AI implementation conforms to an `Agent` protocol with a single `decide_order(view) -> int` method so heuristics are swappable
- [ ] **AI-03**: When all four stations are played by Sterman AI with classic step demand, the Factory peak / Retailer peak order ratio falls within [2.0, 4.0] (canonical bullwhip calibration)
- [ ] **AI-04**: Engine equilibrium regression — when all four stations are played by a trivial `ConstantOrderAgent(4)` with constant customer demand=4, inventory stays at 12 for all 36 weeks (this tests engine correctness; Sterman's bullwhip behavior is verified separately by AI-03)

### Game Setup & Rules

- [ ] **SETUP-01**: Before the first game, the user sees a Rules + Bullwhip Primer screen explaining the 4-station chain, the order/shipping mechanics, and what the bullwhip effect is
- [ ] **SETUP-02**: At game start, the user picks which of the four stations to play (Retailer / Wholesaler / Distributor / Factory) via a radio control
- [ ] **SETUP-03**: At game start, the user can optionally set the random seed (for reproducibility) — default seed is fixed so a fresh visit always plays the canonical run
- [ ] **SETUP-04**: A "Start game" action transitions from setup to the first turn

### Per-Turn Play

- [ ] **PLAY-01**: Each week, the player sees their station's current inventory, backlog, last week's shipments received, last week's orders received, and an order-history mini-chart of their own past orders
- [ ] **PLAY-02**: Each week, the player enters an order quantity via a `st.number_input` (min 0, no artificial upper cap) inside an `st.form` and submits via "Advance week" button
- [ ] **PLAY-03**: During play, the player CANNOT see other stations' inventory, backlog, or orders, and CANNOT see future customer demand
- [ ] **PLAY-04**: A week counter shows current week / 36
- [ ] **PLAY-05**: After 36 weeks, the game transitions automatically to the debrief

### Debrief

- [ ] **DEB-01**: Debrief shows a 4-panel chart (one panel per station) with shared x-axis (weeks) plotting orders placed and inventory level over the full game
- [ ] **DEB-02**: Debrief annotates the week-5 demand step (customer demand 4 → 8) on the chart
- [ ] **DEB-03**: Debrief shows the bullwhip amplification ratio (variance(factory orders) / variance(customer demand)) plus per-echelon ratios
- [ ] **DEB-04**: Debrief shows a cost breakdown per station (holding cost, backorder cost, total)
- [ ] **DEB-05**: Debrief shows a narrative explanation (≤200 words) adapted to the player's station that explains what the bullwhip is and where it shows up in their game
- [ ] **DEB-06**: Debrief offers a "Play again" action that returns to setup

### Deployment

- [ ] **DEPLOY-01**: Code lives in a public GitHub repository at `github.com/greycloak85/beer-game`
- [ ] **DEPLOY-02**: App is deployed to Streamlit Community Cloud and reachable at a public URL
- [ ] **DEPLOY-03**: Deployment uses `requirements.txt` with pinned versions only (`uv.lock`, `Pipfile`, `pyproject.toml` are NOT used to declare deploy deps)
- [ ] **DEPLOY-04**: Python version is pinned via `.python-version` AND set in Streamlit Cloud's "Advanced settings" dropdown to 3.12
- [ ] **DEPLOY-05**: README explains how to play, links to the live app, and notes the ~30-second cold-start delay
- [ ] **DEPLOY-06**: `.gitignore` excludes `.streamlit/secrets.toml`, `__pycache__/`, `.venv/`, `*.pyc`, and `uv.lock` (defensively)

## v2 Requirements

Acknowledged but deferred. Not in current roadmap.

### Differentiators

- **D2-01**: Per-week narration / annotation overlay on the debrief chart explaining what happened at key moments
- **D2-02**: Bullwhip score (0–100) with novice-percentile benchmark
- **D2-03**: Lead-time / pipeline visualization mid-game (player sees their own pipeline only)
- **D2-04**: CSV export of the full game log from the debrief
- **D2-05**: Shareable static image of the debrief chart

### Multiplayer

- **D2-06**: 4 humans in different browsers join via game code, each plays one station (requires shared state, out of Streamlit Cloud free-tier comfort zone)

### Configurability

- **D2-07**: Selectable demand pattern (step, ramp, seasonal, random spike)
- **D2-08**: Selectable AI difficulty / heuristic
- **D2-09**: Configurable game length

## Out of Scope

| Feature | Reason |
|---------|--------|
| Authentication / user accounts | No persistence, no accounts needed for a teaching demo |
| Save / resume across sessions | In-session only — page refresh resets the game. Acceptable for a teaching demo. |
| Leaderboards / persistent scoring | Requires user identity and a database; not needed for the teaching goal |
| Mobile-optimized UI | Streamlit defaults are fine; desktop/tablet is the target |
| Show all stations' state during play | Anti-feature — collapses the bullwhip lesson (the player needs to *not* see what the others are doing) |
| Show future demand or hint at the step | Anti-feature — the discovery moment at week 5 is part of the lesson |
| Recommended order quantity / "optimal" hint | Anti-feature — destroys the gap that the debrief explains |
| Symmetric $1/$1 costs | Anti-feature — changes the equilibrium and breaks the "over-ordering feels safe" lesson |
| NumPy / pandas | Adds ~50MB against the 1 GB Streamlit Cloud limit for zero benefit at 4 × 36 = 144 cells |
| Interactive guided tutorial with tooltips | Rules screen + primer is enough for v1 |
| `uv.lock` committed to repo | Streamlit Cloud's dependency-file priority picks `uv.lock` first; a yanked transitive can wedge builds |

## Traceability

Populated by `gsd-roadmapper` on 2026-05-18. Every v1 requirement maps to exactly one phase.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ENG-01 | Phase 1: Simulation Engine + AI | Pending |
| ENG-02 | Phase 1: Simulation Engine + AI | Pending |
| ENG-03 | Phase 1: Simulation Engine + AI | Pending |
| ENG-04 | Phase 1: Simulation Engine + AI | Pending |
| ENG-05 | Phase 1: Simulation Engine + AI | Pending |
| ENG-06 | Phase 1: Simulation Engine + AI | Pending |
| ENG-07 | Phase 1: Simulation Engine + AI | Pending |
| ENG-08 | Phase 1: Simulation Engine + AI | Pending |
| ENG-09 | Phase 1: Simulation Engine + AI | Pending |
| ENG-10 | Phase 1: Simulation Engine + AI | Pending |
| AI-01 | Phase 1: Simulation Engine + AI | Pending |
| AI-02 | Phase 1: Simulation Engine + AI | Pending |
| AI-03 | Phase 1: Simulation Engine + AI | Pending |
| AI-04 | Phase 1: Simulation Engine + AI | Pending |
| SETUP-01 | Phase 2: UI Shell + Per-Turn Play | Pending |
| SETUP-02 | Phase 2: UI Shell + Per-Turn Play | Pending |
| SETUP-03 | Phase 2: UI Shell + Per-Turn Play | Pending |
| SETUP-04 | Phase 2: UI Shell + Per-Turn Play | Pending |
| PLAY-01 | Phase 2: UI Shell + Per-Turn Play | Pending |
| PLAY-02 | Phase 2: UI Shell + Per-Turn Play | Pending |
| PLAY-03 | Phase 2: UI Shell + Per-Turn Play | Pending |
| PLAY-04 | Phase 2: UI Shell + Per-Turn Play | Pending |
| PLAY-05 | Phase 2: UI Shell + Per-Turn Play | Pending |
| DEB-01 | Phase 3: Debrief Charts + Narrative | Pending |
| DEB-02 | Phase 3: Debrief Charts + Narrative | Pending |
| DEB-03 | Phase 3: Debrief Charts + Narrative | Pending |
| DEB-04 | Phase 3: Debrief Charts + Narrative | Pending |
| DEB-05 | Phase 3: Debrief Charts + Narrative | Pending |
| DEB-06 | Phase 3: Debrief Charts + Narrative | Pending |
| DEPLOY-01 | Phase 4: Deploy to Streamlit Community Cloud | Pending |
| DEPLOY-02 | Phase 4: Deploy to Streamlit Community Cloud | Pending |
| DEPLOY-03 | Phase 4: Deploy to Streamlit Community Cloud | Pending |
| DEPLOY-04 | Phase 4: Deploy to Streamlit Community Cloud | Pending |
| DEPLOY-05 | Phase 4: Deploy to Streamlit Community Cloud | Pending |
| DEPLOY-06 | Phase 4: Deploy to Streamlit Community Cloud | Pending |

**Coverage:**
- v1 requirements: 33 total
- Mapped to phases: 33 (100%) ✓
- Unmapped: 0 ✓
- Duplicates (in >1 phase): 0 ✓

**Per-Phase Counts:**
- Phase 1 (Engine + AI): 14 requirements (ENG-01 … ENG-10, AI-01 … AI-04)
- Phase 2 (UI Shell + Play): 9 requirements (SETUP-01 … SETUP-04, PLAY-01 … PLAY-05)
- Phase 3 (Debrief): 6 requirements (DEB-01 … DEB-06)
- Phase 4 (Deploy): 6 requirements (DEPLOY-01 … DEPLOY-06)

---
*Requirements defined: 2026-05-18*
*Last updated: 2026-05-18 after roadmap creation — traceability populated*
