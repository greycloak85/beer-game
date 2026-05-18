# Beer Game

## What This Is

A web-based, single-player simulation of the MIT Beer Distribution Game (Sterman, 1989) — the canonical exercise that teaches the bullwhip effect in supply chains. The player picks one of the four stations (Retailer, Wholesaler, Distributor, Factory) and plays against three AI agents using Sterman's anchor-and-adjust heuristic. Built as a Streamlit app for one-click public hosting on Streamlit Community Cloud.

## Core Value

A player can play a full Beer Game round in one sitting and *see* the bullwhip effect emerge in the post-game debrief — charts and narrative make the lesson land without an instructor in the room.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Faithful Beer Game simulation engine (4 stations, weekly turns, shipping/order lead times, holding/backorder costs)
- [ ] Player picks one of the four stations at game start
- [ ] Three remaining stations played by Sterman anchor-and-adjust AI
- [ ] Classic step demand: 4/week for weeks 1–4, then 8/week through week 36
- [ ] Fixed 36-week game length
- [ ] Per-turn UI: current state of the player's station, an order input, "advance week" button
- [ ] Rules + bullwhip primer screen before first game
- [ ] Post-game debrief: 4-panel chart (orders/inventory across all stations), amplification ratio, cost breakdown, narrative explanation
- [ ] Deploy publicly on Streamlit Community Cloud from public GitHub repo `greycloak85/beer-game`

### Out of Scope

- **Multiplayer (multiple human players)** — Adds shared-state complexity (websockets/DB) that doesn't fit Streamlit Cloud's free tier model. Deferred to potential v2.
- **Save / resume across sessions** — In-session only (Streamlit `session_state`). A page refresh resets the game. Acceptable for a teaching demo.
- **Shareable run links / leaderboards** — Not needed for the teaching goal. Possible v2.
- **Configurable demand patterns / sandbox mode** — Classic step demand only in v1; reproducing the canonical bullwhip is the teaching point.
- **Selectable AI difficulty** — One published Sterman heuristic for v1; comparing humans against the same baseline is what makes the debrief honest.
- **Interactive guided tutorial** — A rules screen + primer is enough for v1; full tooltipped tutorial is v2.
- **Mobile-optimized UI** — Streamlit defaults are fine; desktop/tablet is the target.
- **Authentication / user accounts** — No persistence, no accounts.

## Context

- **Domain:** The Beer Distribution Game originated at MIT Sloan in the 1960s and was formalized by John Sterman in his 1989 paper *Modeling Managerial Behavior*. Rules and parameters are public, widely taught, and not trademarked. Multiple open implementations exist (web, Excel, board) so we can validate behavior against known baselines.
- **Audience:** Operations / supply-chain students, MBA programs, ops practitioners curious about the bullwhip. People who've heard of the game but never played it.
- **Hosting story:** Streamlit Community Cloud deploys directly from a public GitHub repo on push — that's the entire deploy pipeline. Keeping the app pure-Streamlit (no external DB, no auth) is what makes this work.
- **Naming:** Keeping "Beer Game" — academic term of art, no trademark, immediately recognizable to the target audience.

## Constraints

- **Tech stack:** Streamlit (Python) — chosen for one-click public hosting on Streamlit Community Cloud.
- **Hosting:** Streamlit Community Cloud free tier — pushes constraints toward stateless, single-session, no external services.
- **Repo:** Must be a public GitHub repository under the user's `greycloak85` account.
- **State:** In-session only (`st.session_state`) — no database, no auth, no persistence across refreshes.
- **Simulation fidelity:** AI agent and game mechanics must reproduce the canonical bullwhip on the classic step demand — if a researcher can't recognize the curves, the teaching goal fails.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Streamlit (not Flask/FastAPI + React) | One-click public hosting on Streamlit Community Cloud is the easiest path to a public URL the user wanted | — Pending |
| Solo-vs-AI only in v1 | Multiplayer requires shared state across browser sessions; doesn't fit Streamlit Cloud or the in-session constraint | — Pending |
| Sterman anchor-and-adjust as the sole AI | Academically faithful; reliably produces the bullwhip; honest baseline for player comparison | — Pending |
| Classic step demand (4 → 8 at week 5), 36 weeks fixed | The canonical setup; reproducing the published bullwhip pattern is the teaching payoff | — Pending |
| Player picks station at game start | Each role has a different feel (Retailer sees real demand; Factory absorbs the worst amplification) — maximizes replayability | — Pending |
| Keep the name "Beer Game" | Term of art, no trademark, immediate recognition with target audience | — Pending |
| In-session state only (no DB) | Matches "easy hosting" goal; keeps Streamlit Cloud free tier viable; acceptable for a teaching demo | — Pending |

---
*Last updated: 2026-05-18 after initialization*
