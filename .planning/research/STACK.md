# Stack Research

**Project:** Beer Game — single-player Streamlit simulation of the MIT Beer Distribution Game
**Domain:** Educational simulation web app (Python/Streamlit, in-session only, Streamlit Community Cloud)
**Researched:** 2026-05-18
**Confidence:** HIGH (Streamlit, Plotly, Python tooling verified against official docs and PyPI as of May 2026)

---

## TL;DR Stack Decision

| Layer | Choice | Version |
|-------|--------|---------|
| Runtime | Python | **3.12** (CC default) |
| Web framework | Streamlit | **1.57.0** (stable, Apr 28 2026) |
| Charts | Plotly (`plotly.graph_objects` + `plotly.subplots.make_subplots`) | **6.7.0** |
| Numerics | Plain Python + `dataclasses`; **no NumPy/pandas required** | stdlib |
| Tests | pytest | **8.x** |
| Lint+format | Ruff (single tool replaces black/isort/flake8) | **0.6+** |
| Types | Pyright in editor (Pylance); optional mypy in CI | latest |
| Dependency file | `requirements.txt` (pinned) — single file, repo root | n/a |
| Hosting | Streamlit Community Cloud free tier from public GitHub repo `greycloak85/beer-game` | n/a |

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Python** | **3.12** (3.13 acceptable) | Runtime | Streamlit Community Cloud (CC) default is 3.12 as of 2026. CC supports 3.10 / 3.11 / 3.12 / 3.13 / 3.14, but only versions still receiving security updates — no EOL, no prerelease. Pin to 3.12 in `.python-version` / CC "Advanced settings" for reproducibility. 3.13 works but a few libraries still lag on wheels; 3.12 is the safe default. |
| **Streamlit** | **1.57.0** (released 2026-04-28 on PyPI) | Single-file Python web framework — UI, state, routing | One-click deploy from public GitHub on Streamlit Community Cloud is the entire reason this project is Streamlit. 1.57.0 is the current stable. Features we will actually use: `st.session_state` (in-session game state), `st.fragment` (rerun only the order-input form on each weekly turn — avoids re-running the whole sim each click), `st.dialog` (modal for "How to play" pre-game primer and "End game" debrief launcher), `st.tabs` (split debrief into chart-panels), `st.button` / `st.number_input` (per-turn order entry), `st.cache_data` (memoize the post-game amplification-ratio computation keyed on the run seed). |
| **Plotly** | **6.7.0** (released 2026-04-09 on PyPI) | Post-game multi-panel time-series charts with annotations | The debrief is the project's payoff — four stacked subplots (one per station) showing orders, inventory, backorders across 36 weeks. Plotly's `make_subplots(rows=4, cols=1, shared_xaxes=True, subplot_titles=...)` is purpose-built for this. Native interactivity (hover, zoom, legend toggle) is free. Streamlit ships `st.plotly_chart()` as a first-class renderer. Beats the alternatives on three counts that matter here: (1) multi-trace annotations (`fig.add_vline(x=5, annotation_text="Demand step")`), (2) interactive hover for "what was my inventory in week 17?", (3) shared x-axis across panels makes the bullwhip amplification visually obvious without effort. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **pytest** | 8.x | Unit tests for sim engine | Deterministic simulation with fixed seed → `pytest` is the only test we need. Write a snapshot test: "given seed=42, classic step demand, Sterman parameters {θ, α_S, α_SL, β}, the per-station per-week orders array equals this golden fixture." Run on every commit. |
| **hypothesis** *(optional)* | 6.x | Property-based tests for invariants | Useful but **defer**. One nice property: "for any non-negative integer order stream and non-negative initial inventory, backorder is non-negative." Not blocking for v1. |
| **ruff** | 0.6+ | Lint + format (replaces black, isort, flake8) | One tool, one config, sub-second on this tiny codebase. `ruff check .` + `ruff format .` in a pre-commit hook. |
| **pyright** *(via Pylance)* | latest | Type checking in the editor | Editor-only; no CI requirement. Add type hints to `simulate()`, `sterman_order()`, and the dataclasses — the sim is the load-bearing logic and types pay for themselves. |
| **mypy** *(optional)* | 1.x | Type checking in CI | Only if a CI pipeline is added later. Pyright in editor is sufficient for v1. |

**Explicitly NOT in the dependency list:** NumPy, pandas, Altair, matplotlib, scipy. See "What NOT to Use" below.

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **uv** | Local dev: fast venv + pip-compatible installer | Streamlit Community Cloud already uses `uv` internally to install from `requirements.txt`. Mirroring locally with `uv pip install -r requirements.txt` matches what CC does — fewer "works on my machine" surprises. Do **not** ship `uv.lock` (see below). |
| **pre-commit** | Run ruff + pytest before each commit | Optional but cheap. One `.pre-commit-config.yaml` with ruff hooks. |
| **GitHub Actions** *(optional)* | CI: pytest + ruff on PR | Single workflow file. Free for public repos. Defer until after v1 ships. |

---

## Installation

### `requirements.txt` (commit this — CC reads it on deploy)

```
streamlit==1.57.0
plotly==6.7.0
```

That's the entire production dependency list. The sim itself is stdlib only.

### `requirements-dev.txt` (local only, do NOT deploy)

```
pytest>=8,<9
ruff>=0.6
# pyright is editor-only via Pylance — not pip-installed unless you want CLI runs
```

### Local setup

```bash
# One-time
uv venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt -r requirements-dev.txt

# Dev loop
streamlit run app.py
pytest -q
ruff check . && ruff format .
```

### `.python-version` (commit this — pins local + Streamlit CC if both honor it)

```
3.12
```

Also set "Python version: 3.12" in the Streamlit Community Cloud **Advanced settings** modal at deploy time (the dropdown is the authoritative source for CC).

---

## Alternatives Considered

### Charting: Plotly vs Altair vs Matplotlib vs Streamlit-native

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| **Plotly** | Altair (Vega-Lite) | Choose Altair only if you prefer grammar-of-graphics composition and won't exceed Altair's hard **5,000-row** dataset limit. Our sim is 4 stations × 36 weeks × handful of series ≈ <1,000 rows, so Altair is *technically* fine — but Plotly's `make_subplots` with `shared_xaxes=True` produces the bullwhip-comparison view in fewer lines and with better hover UX. |
| **Plotly** | Matplotlib | Choose matplotlib only if you need *publication-quality static PNG/PDF output* (e.g., bundling charts into a paper). Static-only; no hover, no zoom. Wrong tool for an interactive web debrief. |
| **Plotly** | `st.line_chart` (native) | Use native charts for throwaway prototypes or simple KPIs. **Cannot** handle 4-panel layouts with shared x-axis, demand-step annotations, or cost-breakdown overlays. We need the full chart library here — the debrief is the product. |

### Numerics: plain Python vs NumPy/pandas

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| **Plain Python `list`/`dict` + `@dataclass`** | NumPy arrays | Only justified if simulation grows to thousands of stations or Monte-Carlo runs with 10k+ trajectories. Our problem size is 4 × 36 = 144 cells per series — a Python list is faster than the NumPy import overhead and far easier to reason about, test, and pickle. |
| **Plain Python** | pandas DataFrame | Only if we needed groupby/resample/join semantics. For passing a per-station orders timeline into Plotly, a `list[dict]` or `dict[str, list[int]]` is enough. Pandas would add ~30MB of memory pressure against the **1GB Streamlit CC limit** for zero benefit. |

### Dependency file: `requirements.txt` vs `pyproject.toml` vs `uv.lock` vs `Pipfile`

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| **`requirements.txt`** | `pyproject.toml` (poetry) | CC supports it but it sits last in CC's priority order and you don't need PEP 621 metadata for a deploy-only repo. Skip unless this becomes a library you publish. |
| **`requirements.txt`** | `uv.lock` | CC will *use* `uv.lock` if present (it's first in priority order) but uv lockfiles are still maturing and pin transitively-versioned hashes that can hard-fail CC builds if a sub-dependency yanks a wheel. Pin only your top-level deps in `requirements.txt` and let CC's uv-backed pip resolver handle the rest. |
| **`requirements.txt`** | `environment.yml` (conda) | Only if you need C-extension binaries from conda-forge. We don't. |
| **`requirements.txt`** | `Pipfile` | No reason. Pipenv is in maintenance mode. |

**CC priority order (verified from official docs, 2026):** `uv.lock` → `Pipfile` → `environment.yml` → `requirements.txt` → `pyproject.toml`. Only the first one found is used. Ship only `requirements.txt` to avoid ambiguity.

### Linting/formatting: Ruff vs Black+isort+flake8

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| **Ruff** (formatter + linter) | Black + isort + flake8 | Stick with the legacy trio only if you already have a tuned config you don't want to migrate. For a greenfield repo there is no reason — ruff is >99.9% Black-compatible on output, 30–100× faster, and one binary instead of three. |

### Type checking: Pyright vs mypy

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| **Pyright (via Pylance in editor)** | mypy in CI | Add mypy if you set up GitHub Actions later. For v1 the editor feedback loop is enough; the codebase is one sim engine file plus one Streamlit app file. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **`st.experimental_*` APIs** | Most are renamed/removed in 1.5x; `st.experimental_rerun` → `st.rerun`, `st.experimental_dialog` → `st.dialog`, `st.experimental_fragment` → `st.fragment` as of 1.36+. | Use the stable names — they've been GA for >12 months. |
| **`@st.cache` (the legacy decorator)** | Deprecated in favor of `st.cache_data` / `st.cache_resource` since 1.18 (2023). Still imports but emits warnings. | `st.cache_data` for the amplification-ratio / cost summary; we don't need `st.cache_resource` at all (no DB, no model). |
| **Multipage `pages/` directory** | We have one game flow — pre-game → play → debrief. A single `app.py` with `st.session_state["phase"]` switching renders cleaner than CC's auto-discovered multipage sidebar. | One `app.py`. Use `st.session_state["phase"]` as a state machine: `"intro"` / `"playing"` / `"debrief"`. |
| **NumPy/pandas** | Adds ~50MB to image, slower cold-start, eats into the 1GB CC limit for zero benefit at this problem size. | `list[int]`, `dict[str, list[int]]`, `@dataclass`. |
| **SQLAlchemy / SQLite / any DB** | PROJECT.md is explicit: in-session only. CC's filesystem is ephemeral and per-rerun — DBs don't survive. | `st.session_state`. |
| **`pickle` for state persistence** | Same reason: in-session only. Pickle also opens up arbitrary-code-execution if you ever reload from disk. | `st.session_state` (lives only in the running Python process). |
| **Authentication libraries (`streamlit-authenticator`, OAuth)** | PROJECT.md explicitly excludes accounts. Adds attack surface and CC-limit pressure. | No auth. Public app. |
| **`st.experimental_get_query_params` / manual URL state** | The whole game is in-session by design. Re-hydrating from query string contradicts the "refresh resets the game" constraint. | Don't. |
| **`streamlit-aggrid`, `streamlit-extras` heavy components** | Custom components ship JS bundles → slower cold start under CC's 1GB cap. | Stick to built-in widgets. |
| **`matplotlib` for the debrief** | Static images, no hover, no zoom, no legend toggle. The whole point of the debrief is letting the player *explore* the four panels. | Plotly. |
| **Altair for the debrief** | 5,000-row hard limit and weaker subplot-with-shared-axis ergonomics. Not a blocker at our data size but no upside over Plotly here. | Plotly. |
| **`asyncio` / threads inside the Streamlit handler** | Streamlit's rerun model fights anything that holds state outside `session_state`. Threads survive across reruns and cause subtle bugs. | Synchronous code. The sim is microseconds. |
| **`uv.lock` committed to repo** | CC will prefer it over `requirements.txt`, and a yanked transitive wheel can wedge deploys. | `requirements.txt` with top-level pins only. |
| **`black`, `isort`, `flake8`, `autoflake`, `pyupgrade` as separate tools** | Ruff does all of these in one binary, faster. | `ruff check` + `ruff format`. |

---

## Streamlit Community Cloud — Free Tier Constraints to Know Before You Push

These are platform realities, not opinions. Build for them.

| Constraint | Value | Implication for Beer Game |
|------------|-------|---------------------------|
| **Memory limit** | **~1 GB** per app (CPU + RAM combined budget) | Easy budget for our use case. Stay out of NumPy/pandas and the headroom is huge. |
| **App sleep** | After **12 hours** of no traffic (recently tightened from 24h) | First visitor of the day gets a ~30s cold start while the container spins up. Show a quick "Waking the app…" splash if you want polish, or accept the default Streamlit boot screen. **Do not** try to keep the app awake with cron pings — it violates CC's communal-resource policy. |
| **Apps per user** | 3 free apps | Plenty. |
| **Update rate limit** | 5 GitHub-triggered redeploys per minute | Won't hit this. |
| **Host region** | US-only (not configurable) | Latency irrelevant for this synchronous turn-based UI. |
| **Base image** | Debian 11 ("bullseye") | Pure-Python stack so no `apt` packages needed. If you ever need fonts (e.g., for matplotlib — which we're not using), they'd go in `packages.txt`. |
| **Secrets** | `st.secrets` reads `.streamlit/secrets.toml` locally, and a TOML blob pasted into CC's "Advanced settings" in prod. **Never commit `.streamlit/secrets.toml`.** Add it to `.gitignore`. | We have no secrets to ship (no API keys, no DB). Add `.streamlit/secrets.toml` to `.gitignore` defensively so you don't accidentally commit one later. |
| **Filesystem** | Ephemeral per rerun. Writes don't persist across container restarts. | Don't write logs/checkpoints/saves to disk. Use `st.session_state`. |
| **HTTPS / custom domain** | HTTPS auto, custom domain not supported on free tier | Public URL will be `https://<app-slug>.streamlit.app`. Fine for v1. |
| **Python version selection** | Set explicitly in CC "Advanced settings" → "Python version" dropdown. Default is **3.12**. | Pin to **3.12** in CC's dropdown *and* commit `.python-version` for local parity. |
| **Build cache invalidation** | Triggered by `requirements.txt` change or manual "Reboot" | Pin top-level deps to exact versions to avoid surprise rebuilds when a transitive yanks. |
| **Cold-start time** | ~20–40s for small pure-Python apps | First-load UX matters. Keep `import` cost low (don't import pandas/numpy/scipy at module scope if you ever add them). |

### Specific Streamlit features we WILL use (verified in 1.57.0)

| API | Why for Beer Game |
|-----|------------------|
| `st.session_state` | The entire game state — current week, per-station inventory/backorder/orders-in-pipeline, player station, RNG seed. |
| `st.fragment` (decorator) | Wrap the weekly "submit order" form. Only that fragment reruns when the player clicks "Advance week" — the rules/header don't re-render and the post-game chart placeholder stays stable. Stable since 1.36; current in 1.57. |
| `st.dialog` (decorator) | "How to play" modal before first game; "Confirm end game" / "View debrief" modal. Stable since 1.35. |
| `st.tabs` | Debrief: tab per view ("Orders", "Inventory", "Costs", "Amplification ratio"). |
| `st.cache_data` | Memoize cost-breakdown DataFrame-equivalent and amplification-ratio computation keyed on `(seed, player_station)` — recomputing after every rerun is wasteful even at small N. |
| `st.plotly_chart(fig, use_container_width=True)` | The debrief renderer. |
| `st.button`, `st.number_input`, `st.radio`, `st.metric` | Standard inputs/outputs. |

### Features we will NOT use (and why)

- `st.experimental_*` — none, all our needs are in stable APIs
- `st.cache_resource` — no resources to cache (no DB, no model)
- `st.connection` — no external services
- Multipage `pages/` — single state-machine `app.py` is clearer
- `st.form` — `st.fragment` is the modern replacement for our use case (form was the pre-fragment workaround)

---

## Stack Patterns by Variant

**If we keep v1 truly in-session (current plan):**
- Use only `streamlit` + `plotly` in `requirements.txt`
- Game state lives in `st.session_state`
- Sim engine is a pure-function module (`sim/engine.py`) that the Streamlit app calls — keeps the engine testable in pytest without importing streamlit

**If v2 adds shareable run links (deferred):**
- Add `streamlit-pydantic` or hand-rolled query-param serialization
- Encode the final game state as a compressed base64 URL fragment (~hundreds of bytes — fits)
- Still no DB

**If v2 adds multiplayer (out of scope per PROJECT.md):**
- Outgrows Streamlit Community Cloud — switch to FastAPI + WebSockets backend, or use Streamlit's `st.connection` to a hosted Redis/Postgres
- This is a different project; do not architect v1 around it

---

## Version Compatibility

| Package | Version | Compatible With | Notes |
|---------|---------|-----------------|-------|
| streamlit | 1.57.0 | Python 3.10 – 3.14 | CC default is 3.12. Use 3.12. |
| plotly | 6.7.0 | Python 3.8 – 3.13 | Streamlit renders it via `st.plotly_chart`. No version pin conflict. |
| pytest | 8.x | Python 3.8+ | Dev-only, doesn't ship to CC. |
| ruff | 0.6+ | Python 3.8+ | Dev-only, doesn't ship to CC. |

**Known good combo:** `streamlit==1.57.0` + `plotly==6.7.0` on Python 3.12 on Streamlit Community Cloud — verified as the current released stack on PyPI as of 2026-05-18.

---

## Sources

- [Streamlit on PyPI](https://pypi.org/project/streamlit/) — **HIGH** — 1.57.0 stable, released 2026-04-28, supports Python ≥3.10
- [Streamlit 2026 release notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2026) — **HIGH** — 1.53–1.57 features verified
- [Streamlit Community Cloud — App dependencies](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies) — **HIGH** — dependency-file priority order, single-file rule, uv-backed pip
- [Streamlit Community Cloud — Status & limitations](https://docs.streamlit.io/deploy/streamlit-community-cloud/status) — **HIGH** — Debian 11, US hosting, 5/min update cap, supported Python versions
- [Streamlit Community Cloud — Upgrade Python](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/upgrade-python) — **HIGH** — Python version dropdown in Advanced settings
- [Streamlit Community Cloud — Secrets management](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management) — **HIGH** — `.streamlit/secrets.toml`, never commit, paste at deploy
- [Streamlit blog — Resource limits](https://blog.streamlit.io/common-app-problems-resource-limits) — **MEDIUM** — 1GB cap, 12h sleep window (corroborated by community discussion)
- [Streamlit forum — Sleep mode discussion](https://discuss.streamlit.io/t/how-to-prevent-the-app-enter-the-sleep-mode/87959) — **MEDIUM** — confirms 12h sleep tightening
- [st.fragment docs](https://docs.streamlit.io/develop/api-reference/execution-flow/st.fragment) — **HIGH** — fragment semantics, session_state interaction
- [st.dialog docs](https://docs.streamlit.io/develop/api-reference/execution-flow/st.dialog) — **HIGH** — modal dialog API
- [Streamlit caching docs](https://docs.streamlit.io/develop/concepts/architecture/caching) — **HIGH** — `cache_data` vs `cache_resource` guidance; legacy `@st.cache` deprecated
- [Plotly on PyPI](https://pypi.org/project/plotly/) — **HIGH** — 6.7.0 stable, released 2026-04-09
- [Plotly subplots docs](https://plotly.com/python/subplots/) — **HIGH** — `make_subplots` API for multi-panel time-series
- [Squadbase — Streamlit chart library comparison](https://dev.to/squadbase/streamlit-chart-libraries-comparison-a-frontend-developers-guide-54il) — **MEDIUM** — Plotly vs Altair vs matplotlib tradeoffs; Altair 5k-row limit
- [Astral — Ruff formatter](https://astral.sh/blog/the-ruff-formatter) — **HIGH** — >99.9% Black compatibility, 30× faster
- [Ruff GitHub](https://github.com/astral-sh/ruff) — **HIGH** — single-tool replacement for black/isort/flake8

---
*Stack research for: single-player Streamlit simulation of the MIT Beer Distribution Game*
*Researched: 2026-05-18*
