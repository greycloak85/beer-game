# Project Research Summary

**Project:** Beer Game — single-player Streamlit simulation of the MIT Beer Distribution Game (Sterman 1989 canonical)
**Domain:** Educational systems-dynamics simulator (Python/Streamlit, in-session, Streamlit Community Cloud)
**Researched:** 2026-05-18
**Confidence:** HIGH

---

## Executive Summary

This is a teaching simulator, not a game and not an engineering exercise. The single product requirement is: a learner plays one station of a 4-station supply chain for 36 weeks against three AI opponents running Sterman's anchor-and-adjust heuristic, then sees a post-game debrief that reproduces the canonical bullwhip pattern recognizable to any operations-management instructor. Everything else — the stack, the architecture, the UI flow — is in service of that one moment of recognition. If the bullwhip doesn't visibly emerge in the debrief, the project failed regardless of how polished the rest is.

The expert approach is opinionated and narrow: lock to Sterman's canonical parameters (no configuration), build a pure-Python simulation engine with zero Streamlit imports, gate UI work behind two pytest invariants (equilibrium regression + bullwhip calibration), and deploy via `requirements.txt` only to Streamlit Community Cloud. The stack is intentionally minimal — `streamlit==1.57.0` + `plotly==6.7.0` on Python 3.12 — because NumPy/pandas add cold-start cost and 1GB-cap pressure for zero benefit at this problem size (4 × 36 = 144 cells per series). The architecture splits cleanly into `engine/` (pytest-able, no streamlit), `ai/` (Sterman heuristic implementing a single `Agent.decide_order(view)` protocol), `views/` (Streamlit), and `charts/` (pure Plotly figure builders).

The risks are almost entirely silent correctness failures — bugs that produce a working-looking app with the wrong curves. Eight load-bearing landmines must be surfaced in any implementation plan: (1) using Sterman's *empirical* α≈0.26 / β≈0.34 / θ≈0.36 / S′≈17 rather than JASSS 2014 "optimal" α=β=1 / θ=0 (the optimal parameters produce no bullwhip — they minimize it, silently killing the lesson); (2) keeping `streamlit` out of the engine module so pytest can run determinism tests; (3) the non-negotiable tick sequence *receive shipments → fill orders → record state → place orders → advance pipelines*; (4) asymmetric cost structure $0.50 holding / $1.00 backorder (symmetric breaks the teaching point that over-ordering "feels safe"); (5) information visibility — only the Retailer sees customer demand, every other station sees only orders from its immediate downstream; (6) canonical initial state with inventory=12, backlog=0, every pipeline slot pre-filled with 4 units; (7) two pytest gates before any UI work — equilibrium regression (constant demand→flat at 12) and bullwhip calibration (all-AI step demand → Factory/Retailer peak ratio in [2.0, 4.0]); (8) Streamlit Cloud deploys via `requirements.txt` only — do NOT commit `uv.lock` (its presence wins the lookup order and a yanked transitive can wedge builds).

---

## Key Findings

### Recommended Stack

Minimal pure-Python stack designed to fit Streamlit Community Cloud's free-tier constraints (1GB RAM, 12h sleep, ephemeral filesystem, US-only). The sim engine is stdlib-only; the only production deps are Streamlit and Plotly. Detailed rationale in `STACK.md`.

**Core technologies:**
- **Python 3.12** — CC default; pin in `.python-version` *and* CC "Advanced settings" dropdown for reproducibility
- **Streamlit 1.57.0** — single-file web framework; uses `st.session_state`, `st.fragment`, `st.dialog`, `st.tabs`, `st.plotly_chart`
- **Plotly 6.7.0** — `make_subplots(rows=4, cols=1, shared_xaxes=True)` for the 4-station debrief; native hover/zoom/legend-toggle
- **pytest 8.x** (dev-only) — engine is deterministic, so pytest golden-trace tests are the entire QA strategy
- **Ruff 0.6+** (dev-only) — single tool replaces black/isort/flake8
- **Plain Python `list`/`dict` + `@dataclass`** — *no NumPy/pandas* (saves ~50MB and cold-start time; problem size doesn't justify them)

**Explicitly excluded:** NumPy, pandas, Altair, matplotlib, SQLAlchemy, auth libraries, `streamlit-aggrid`, `uv.lock` in repo, `@st.cache` (legacy), multipage `pages/` directory, `pickle` persistence.

### Expected Features

The Beer Game has a published canonical specification (Sterman 1989) cross-verified across MIT, JASSS 17(4):2, Columbia Business School, and the Kaminsky/Berkeley computerized version. Our differentiator is "locked-canonical, no configuration, no login, narrative debrief replaces the instructor." Detailed feature matrix and information-visibility rules in `FEATURES.md`.

**Must have (table stakes — TS-1 through TS-27, all P1 for v1):**
- 4-station serial chain (Retailer → Wholesaler → Distributor → Factory), 36 weeks, classic step demand (4 cases/wk weeks 1–4, then 8 cases/wk through week 36)
- 2-week shipping delay between every echelon, 1-week order/mailing delay R/W/D, 2-week factory production delay (no order delay at factory) — 4-week total acquisition lag for R/W/D, 3-week for Factory
- **Asymmetric costs: $0.50/case/week holding, $1.00/case/week backorder** (asymmetry is load-bearing — over-ordering "feels safe" is the textbook lesson)
- Canonical equilibrium initial state: 12 on-hand, 0 backlog, every pipeline slot pre-loaded with 4
- 3 AI opponents running Sterman anchor-and-adjust with empirical parameters (α≈0.26, β≈0.34, θ≈0.36, S′≈17)
- Per-turn local-only info panel (no cross-station visibility during play)
- Pre-game rules + bullwhip primer screen
- Post-game debrief: 4-panel chart, amplification ratio, per-station cost breakdown, narrative debrief adapted to player's station
- Play again from debrief

**Should have (post-v1 differentiators):**
- D-2: Per-week narration / annotation overlay on debrief chart
- D-3: Bullwhip score (0–100) with novice-percentile benchmark
- D-5: Lead-time / pipeline visualization mid-game
- D-8: CSV export of game log
- D-9: Shareable static image of the debrief chart

**Anti-features (do NOT build — they break the experiment):**
- Show all stations during play (AF-1) — collapses the lesson
- Show future demand or hint at the step (AF-2) — removes the discovery moment
- Recommended order quantity / "optimal" hint (AF-3) — destroys the gap the debrief explains
- Slider with low upper bound (AF-4) — silently truncates 30–80+ orders at the Factory
- Symmetric $1/$1 costs (AF-7) — changes the equilibrium and breaks the lesson
- Configurable lead times / demand — confuses the teaching goal
- Multiplayer, auth, save/resume, leaderboards — out of scope per PROJECT.md

### Architecture Approach

One load-bearing rule: **the simulation engine must be a pure-Python library that never imports `streamlit`.** Every other decision flows from that. Pytest plugs into the engine directly; Streamlit becomes a thin rendering shell over a four-function API (`new_game`, `advance_week`, `is_game_over`, `compute_debrief`). State is a frozen `@dataclass` returned-new-from-each-tick (not mutated in place). Detailed structure in `ARCHITECTURE.md`.

**Major components:**
1. **`engine/`** (pure Python, no streamlit) — `state.py`, `tick.py`, `demand.py`, `costs.py`, `metrics.py`
2. **`ai/`** (pure Python) — `base.py` (Agent protocol), `sterman.py` (ShipmentAnchorAndAdjustAgent)
3. **`config/`** (pure Python constants) — `scenarios.py` (CLASSIC_36W), `costs.py` ($0.50/$1.00)
4. **`views/`** (Streamlit-aware) — `setup.py`, `rules.py`, `play.py`, `debrief.py`
5. **`charts/`** (pure Plotly, no `st.*` calls) — `orders_inventory.py`, `cost_breakdown.py`
6. **`app.py`** — phase-routed Streamlit entry point; only file touching `st.session_state` directly
7. **`tests/`** — `test_determinism.py`, `test_tick_invariants.py`, `test_sterman_heuristic.py`, `test_bullwhip_emerges.py`, `test_costs.py`, `test_equilibrium.py`

**The canonical tick sequence (non-negotiable, in this exact order):**
1. RECEIVE SHIPMENTS — pop front of `incoming_shipments`, add to inventory
2. FILL ORDERS — pop `incoming_orders`, combine with backlog, ship `min(inventory, demand + backlog)` downstream
3. RECORD STATE — append to history tuples
4. PLACE NEW ORDERS — call player or agent; enqueue to upstream's `incoming_orders` (Factory enqueues to own `incoming_shipments`)
5. ADVANCE PIPELINES — shift every queue forward one slot

Receive *before* fill (else this-week arrivals can't fill this-week backlog → bullwhip too large). Fill *before* record (else inventory chart shows pre-shipment levels). Record *before* order (so agents decide on post-shipment state). Order *before* pipeline advance (else new orders fire instantly with zero lead time).

### Critical Pitfalls

These are silent-failure pitfalls — app runs and looks fine, but the bullwhip is wrong. Full set in `PITFALLS.md`. The most dangerous five:

1. **Sterman parameters: use EMPIRICAL, not "optimal"** — Hardcode α≈0.26, β≈0.34, θ≈0.36, S′≈17 (Sterman 1989 median empirical fit). JASSS 2014's "optimal" α=1, β=1, θ=0 *minimize* the bullwhip → flat order curve → no lesson. Cite Sterman 1989 in the code comment. Gate: calibration test asserts Factory peak / Retailer peak ∈ [2.0, 4.0] on classic step demand with all-AI.
2. **Engine must not import `streamlit`** — Pytest must run determinism tests headlessly. The moment anything in `engine/` or `ai/` does `import streamlit`, the published bullwhip can't be verified in CI. Engine returns warning data; UI formats it with `st.warning`.
3. **Tick sequence is fixed: receive → fill → record → order → advance pipelines** — Any other order produces a working-looking app with subtly wrong curves. Implement as five named functions called from a single `advance_week` driver.
4. **Information visibility — Retailer is the ONLY station that sees customer demand** — Every other station sees only orders from its immediate downstream. Enforce at the engine API level (no `customer_demand` accessor on non-Retailer station), not just the UI. AI agents take only their own `StationView`.
5. **Canonical equilibrium initial state: inventory=12, backlog=0, every pipeline slot pre-filled with 4, costs $0.50/$1.00** — Empty pipelines cause a 4-week startup transient that collides with the week-5 demand step. Symmetric $1/$1 costs change equilibrium and bullwhip shape. Two pytest gates before any UI work: (a) **equilibrium regression** — constant demand=4, all-AI orders=4 → inventory flat at 12 for 36 weeks; (b) **bullwhip calibration** — classic step demand, all-AI → Factory peak / Retailer peak ∈ [2.0, 4.0].

Plus three deploy-critical traps:
- **Do NOT commit `uv.lock`** — CC's dependency-file priority is `uv.lock` → `Pipfile` → `environment.yml` → `requirements.txt` → `pyproject.toml`; only the first found is used. A yanked transitive in `uv.lock` can wedge builds. Ship only `requirements.txt` with top-level pins.
- **Pin Python in *both* `.python-version` *and* CC's "Advanced settings" dropdown** — `runtime.txt` has been intermittently ignored on CC in 2024–2026. Target 3.12.
- **`st.session_state` initialization must be guarded** (`if "game" not in st.session_state: ...`) — Streamlit re-runs top-to-bottom on every interaction; unguarded init wipes state on every click.

---

## Implications for Roadmap

Research overwhelmingly converges on **a strictly engine-first build order with two pytest gates before any UI work.** This is not stylistic preference — it's the only way to verify the canonical bullwhip emerges before investing in UI that would otherwise mask engine bugs. Four phases recommended (plus optional polish).

### Phase 1: Simulation Engine + AI

**Rationale:** Engine is the load-bearing component. Every UI bug looks like a possible engine bug if the engine isn't verified first. PITFALLS 1–7 all live here.

**Delivers:**
- `engine/state.py`, `engine/tick.py`, `engine/demand.py`, `engine/costs.py`, `engine/metrics.py`
- `ai/base.py` (`Agent` protocol), `ai/sterman.py` (with Sterman 1989 citation in code comment)
- `config/scenarios.py` + `config/costs.py` — canonical constants
- `tests/test_determinism.py`, `test_tick_invariants.py`, `test_sterman_heuristic.py`, `test_costs.py`
- **`tests/test_equilibrium.py` — GATE 1: constant demand=4, all-AI orders=4 → inventory stays at 12 for 36 weeks**
- **`tests/test_bullwhip_emerges.py` — GATE 2: classic step demand, all-AI → Factory peak / Retailer peak ∈ [2.0, 4.0]**

**Exit criterion:** Both pytest gates pass. No Streamlit code exists yet.

### Phase 2: Streamlit UI Shell + Per-Turn Play

**Delivers:**
- `app.py` — phase-routed entry (`setup`/`rules`/`playing`/`done`), owns `st.session_state`, callbacks (`start_game`, `submit_order`, `reset_game`)
- `views/setup.py` — station picker (radio), seed input, "Start game"
- `views/rules.py` — rules + bullwhip primer + supply-chain diagram
- `views/play.py` — local-only per-turn panel, player order history mini-chart, `st.form` wrapping `st.number_input(min_value=0, step=1)` + submit button with `on_click=submit_order`
- `.streamlit/config.toml`
- Manual smoke test: play through one full 36-week game

### Phase 3: Debrief Charts + Narrative

**Delivers:**
- `charts/orders_inventory.py` — `build_four_panel(state) -> go.Figure` with `make_subplots(rows=4, cols=1, shared_xaxes=True)`, vertical line at week 5 "Customer demand: 4 → 8"
- `charts/cost_breakdown.py`
- `views/debrief.py` — `st.tabs` for Orders/Costs/Amplification; calls `st.plotly_chart(fig, use_container_width=True)`; narrative ≤200 words adapted to player's station + amplification ratio; "Play again" button
- `tests/test_chart_snapshot.py` — `fig.to_json()` matches fixture
- Amplification ratio: `variance(factory_orders) / variance(customer_demand)` plus per-echelon

### Phase 4: Deploy to Streamlit Community Cloud

**Delivers:**
- `requirements.txt` (commit) — pinned `streamlit==1.57.0`, `plotly==6.7.0` only
- `requirements-dev.txt` (commit, not deployed)
- `.python-version` (commit) — `3.12`
- `.gitignore` — `.streamlit/secrets.toml`, `__pycache__/`, `.venv/`, `*.pyc`, **and `uv.lock`** (defensively)
- Streamlit Community Cloud deploy from `greycloak85/beer-game` with Python 3.12 set in CC "Advanced settings"
- README note: "App may take ~30 seconds to wake up on first visit"
- Deploy log verification: CC actually selected Python 3.12

### Phase Ordering Rationale

- **Engine before UI** is non-negotiable: the bullwhip-emergence test is the correctness criterion and only runs against the engine. Any other order produces "engine bug or UI bug?" debugging time.
- **Pytest gates before Phase 2:** skipping verification means every UI symptom could be an engine bug. The two gates are cheap and pay back every hour spent later.
- **Charts as a separate phase from per-turn UI:** chart construction has its own concerns (Plotly builders, snapshot tests, narrative copy).
- **Deploy as its own phase:** Streamlit Cloud has its own family of silent-failure traps that need dedicated attention.

### Research Flags

**Phases needing research:** None. All four files converge on a high-confidence path. Sterman canonical parameters, tick sequence, lead-time structure, and Streamlit patterns are all well-documented with HIGH-confidence primary sources.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Streamlit 1.57.0 + Plotly 6.7.0 verified against PyPI 2026-05-18; CC constraints verified against official docs; alternatives evaluated with explicit rationale. |
| Features | HIGH | Sterman 1989 canonical parameters cross-checked across MIT, JASSS 17(4):2, Columbia, Kaminsky/Berkeley, Consideo, SUNY New Paltz. Information-visibility matrix is canonical and unambiguous. |
| Architecture | HIGH | Engine/UI separation is standard; `session_state` + callback model verified against official Streamlit docs; tick sequence verified against Sterman + JASSS mathematical model paper. |
| Pitfalls | HIGH | All eight critical pitfalls have explicit prevention strategies, warning signs, and pytest gates. Streamlit-specific traps verified against 2024–2026 community threads. |

**Overall confidence:** HIGH

### Gaps to Address

- **"Optimal vs empirical" parameter naming.** Sterman agent docstring must explicitly label "EMPIRICAL Sterman 1989 fit — produces canonical bullwhip" and cite the source. Future contributors who find JASSS 2014's "optimal" values will otherwise silently substitute them.
- **Amplification ratio target range.** Research gives [2.0, 4.0] as canonical Factory/Retailer peak ratio. If calibration test fails marginally (1.95 or 4.1), re-verify the heuristic rather than widening test bounds. Bounds are load-bearing.
- **Narrative debrief copy.** ≤200 words per station × 4 stations need drafting during Phase 3, not punted to copy editing.

---

## Sources

### Primary (HIGH confidence)
- Sterman 1989, "Modeling Managerial Behavior," *Management Science* — α/β/θ empirical parameters, canonical anchor-and-adjust heuristic
- Sterman, MIT — https://web.mit.edu/jsterman/www/SDG/beergame.html — canonical parameters, costs, demand, 36-week duration
- Edali & Yasarcan, JASSS 17(4):2 — https://www.jasss.org/17/4/2.html — formal lead-time structure, tick sequence, optimal-vs-empirical parameter distinction
- Columbia Business School, "The Stationary Beer Game" — Sterman parameter confirmation
- Kaminsky & Simchi-Levi, Berkeley — UI conventions for computerized versions
- Streamlit on PyPI — 1.57.0 stable (2026-04-28)
- Streamlit Community Cloud docs — app dependencies, status, Python version, secrets, session state
- Plotly on PyPI — 6.7.0 stable (2026-04-09); subplots docs

### Secondary (MEDIUM confidence)
- Wikipedia, "Beer distribution game" — overview; some variant numbers diverge from Sterman canonical
- Zensimu Debriefing Instructor Guide; beergameapp.com Ultimate Guide; isixsigma.com; Lehigh tech paper
- Streamlit blog — resource limits (1GB cap, 12h sleep)
- Streamlit discuss threads — `runtime.txt` intermittently ignored 2024–2026

---
*Research completed: 2026-05-18*
*Ready for roadmap: yes*
