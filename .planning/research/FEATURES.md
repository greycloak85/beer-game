# Feature Research

**Domain:** Single-player, web-based Beer Distribution Game simulator (teaching tool — Streamlit, in-session, solo-vs-AI)
**Researched:** 2026-05-18
**Confidence:** HIGH (canonical Sterman 1989 parameters cross-verified across MIT/Sterman, JASSS mathematical model paper, Columbia Stationary Beer Game paper, and multiple independent implementations)

---

## Canonical Sterman (1989) Parameters — Reference Card

These are the load-bearing numbers. Every "table stakes" feature below is calibrated to them. Sources cross-checked: MIT (web.mit.edu/jsterman), JASSS 17(4):2 mathematical model paper, Columbia Business School "Stationary Beer Game" paper, beergameapp.com, isixsigma.com.

| Parameter | Canonical Value | Confidence | Source |
|---|---|---|---|
| Stations | 4 (Retailer → Wholesaler → Distributor → Factory) | HIGH | All sources |
| Game length | 36 weeks (originally planned 50, halted at 36 to avoid horizon effects) | HIGH | MIT/Sterman, JASSS |
| Demand pattern | 4 cases/wk weeks 1–4, **step to 8 cases/wk** from week 5 onward, flat thereafter | HIGH | MIT/Sterman |
| Mailing/order delay | 1 week (retailer, wholesaler, distributor — order travels upstream) | HIGH | JASSS |
| Shipping delay | 2 weeks (between every echelon — product travels downstream) | HIGH | JASSS, Wikipedia |
| Production delay (factory) | 2 weeks (factory has no order delay, only production lag) | HIGH | JASSS |
| Total acquisition lag | **4 weeks** for R/W/D (1 order + 1 transit + 2 shipping in the standard staggering); **3 weeks** for factory (production only) | HIGH | JASSS, Lehigh paper |
| Holding cost | **$0.50 / case / week** | HIGH | MIT/Sterman, JASSS |
| Backorder cost | **$1.00 / case / week** | HIGH | MIT/Sterman, JASSS |
| Starting on-hand inventory | 12 cases per station | HIGH | MIT/Sterman, Consideo, Wikipedia |
| Starting backorder | 0 | HIGH | JASSS |
| Starting in-transit (pipeline) | 4 cases per delay slot (system starts in equilibrium at 4/wk throughput) | HIGH | JASSS |
| Initial player orders (weeks 1–4 hint) | 4 cases/wk (equilibrium) | HIGH | newpaltz, Consideo |

> **Note on "24 vs 36 vs 52 weeks":** Wikipedia's "24 rounds" reflects a classroom-shortened variant. Sterman's published 1989 protocol is 36 weeks (50 planned, truncated). We use 36 — matches PROJECT.md and is the published canonical figure.

> **Note on "$1/$1 costs":** Wikipedia mentions "one-point" symmetric costs as a generic board-game simplification. Sterman's published costs are asymmetric ($0.50 holding, $1.00 backorder) and the asymmetry is *load-bearing for the lesson* — over-ordering looks safer than under-ordering, fueling the bullwhip. **Use the asymmetric values.**

---

## Feature Landscape

### Table Stakes (Required — Without These, It Isn't the Beer Game)

Missing any of these means the simulator either doesn't reproduce the bullwhip honestly, doesn't teach it, or violates the canonical rules so badly that an instructor would refuse to use it.

| # | Feature | Why Required | Complexity | Notes |
|---|---|---|---|---|
| TS-1 | **4-station serial supply chain** (Retailer, Wholesaler, Distributor, Factory) | Defines the game. Fewer stations = no upstream amplification to observe. | S | Plain list/dict of 4 station objects; no graph needed. |
| TS-2 | **Weekly turn-based loop, 36 weeks fixed** | Canonical Sterman length; long enough for the bullwhip to manifest, short enough for a ~10-min play. | S | Single integer counter in session_state. |
| TS-3 | **2-week shipping delay between every echelon** | Core mechanism of the bullwhip. Removing it kills the lesson. | S | FIFO queue of length 2 per shipping link. |
| TS-4 | **1-week order/mailing delay R↔W, W↔D, D↔F** | Asymmetric upstream/downstream lag is what makes anchoring fail. | S | FIFO queue of length 1 per order link. |
| TS-5 | **2-week factory production delay (no order delay at factory)** | Factory has different lag structure (production only) — this asymmetry is why factory experiences the worst amplification. | S | FIFO queue of length 2 at factory. |
| TS-6 | **Holding cost $0.50/case/week, backorder cost $1.00/case/week** | Canonical, and the asymmetry is the load-bearing teaching point (over-ordering "feels safe"). | S | Two multiplications per station per week. |
| TS-7 | **Classic step demand: 4/wk weeks 1–4, then 8/wk through week 36** | The canonical setup that produces the recognizable, reproducible bullwhip curves. | S | Hardcoded array. |
| TS-8 | **Player picks 1 of 4 stations at game start** | Each role has a different bullwhip experience; choosing is part of the lesson. | S | Radio button on start screen. |
| TS-9 | **3 AI agents play the other stations using Sterman anchor-and-adjust** | Without a faithful AI baseline, the player's behavior can't be compared to the published bullwhip. | M | Order = max(0, expected_demand + α·(target_inv − on_hand) + β·(target_pipe − pipeline)). See ARCHITECTURE.md for parameters. |
| TS-10 | **Starting in equilibrium** — 12 on-hand, 0 backorder, 4-case shipments pre-loaded in every pipeline slot | Standard initial conditions; without them the bullwhip is contaminated by start-up transients. | S | Initialize all queues with 4s. |
| TS-11 | **Per-turn local-only information panel** — player sees ONLY: on-hand inventory, backorder, last-week incoming order (from downstream), incoming shipment due this week, last week's outgoing order, current cumulative cost | The *defining constraint* of the Beer Game. Sterman: "people are directed not to communicate; information is passed through orders and shipments." | S | One small table widget. **See "Information visibility per station" matrix below.** |
| TS-12 | **Order decision input** — non-negative integer, no upper bound, applied to current week | The single decision the player makes each week. | S | `st.number_input(min_value=0, step=1)`. **Do NOT show a recommendation** (see anti-features). |
| TS-13 | **"Advance week" button** to commit order and step simulation | Discrete turn boundary; player must consciously commit. | S | Single button triggering one tick of the sim. |
| TS-14 | **Settlement order per week** (canonical): (1) receive inbound shipment, (2) receive inbound order from downstream, (3) fill orders from inventory (backlog FIFO), (4) ship to downstream, (5) advance order/shipping queues, (6) place new order upstream, (7) accrue costs | Subtle but load-bearing: getting the order wrong shifts what the player sees by a week and breaks bullwhip reproduction. | M | Pure function; unit-test with golden traces. |
| TS-15 | **Retailer faces exogenous customer demand** (the step), other stations face only their downstream's order | Information asymmetry: only the retailer sees "real" demand. | S | Conditional in step function. |
| TS-16 | **Factory has effectively infinite raw material** (production constrained only by 2-week lag, never by inputs) | Canonical: factory's only constraint is the production delay, never a shortage upstream. | S | Don't model a 5th node. |
| TS-17 | **Rules + bullwhip primer screen before first play** | First-time players will not understand the lesson without it. ~30s read; supply-chain diagram + the four station roles + cost rules. | S | Static markdown + one diagram (PNG or st.graphviz). |
| TS-18 | **Supply-chain diagram in rules screen** showing the 4 stations, the upstream order arrows, the downstream shipping arrows, and the delays on each arrow | Visual schema; players who don't see this can't reason about why their order takes 4 weeks to arrive. | S | Static graphviz or PNG. |
| TS-19 | **Post-game 4-panel chart** — for each station (rows), two series (orders placed, on-hand inventory net of backorder) over 36 weeks (x-axis) | The single most important deliverable. The bullwhip *is* this picture. | M | matplotlib or altair, 2×2 or 4×1 facet. |
| TS-20 | **Amplification ratio metric** displayed in debrief — variance(factory orders) / variance(customer demand), plus the same ratio at each upstream level | The canonical quantitative summary of the bullwhip. Numbers like "factory orders varied 4× more than customer demand" make the lesson concrete. | S | `np.var()` calls; display 4 numbers. |
| TS-21 | **Cost breakdown per station** in debrief — holding cost, backorder cost, total — for each of the 4 stations and the supply chain total | Standard Beer Game scoring; lets the player see how badly upstream stations were punished. | S | Table widget. |
| TS-22 | **Narrative debrief text** explaining (a) why their station's orders amplified, (b) what the canonical bullwhip looks like, (c) the typical instructor framing (small demand changes → large upstream swings) | Without an instructor in the room, the simulator must do the teaching. PROJECT.md core value depends on this. | S | Templated markdown that adapts to which station the player chose + their amplification ratio (e.g., "You played factory and your orders varied 6.2× more than retail demand — this is the bullwhip"). |
| TS-23 | **Game reset / play again** from debrief screen | Players will want to try a different station. Trivial via session_state clear. | S | Button → `st.session_state.clear()` + rerun. |
| TS-24 | **No-communication rule enforced by UI** (player physically cannot see other stations' state mid-game) | This *is* the experimental constraint. Violating it breaks the experiment. | S | Just don't render other stations' panels until the debrief. |
| TS-25 | **Deterministic AI seed** so two players who picked the same station see the same AI behavior | Honest baseline — the only variable should be the player's decisions. | S | Fixed Sterman parameters; no RNG needed (deterministic demand + deterministic agents). |
| TS-26 | **Order history visible to player** — list/small chart of the player's own past on-hand, backorder, incoming demand, and orders placed for every prior week | Players need to anchor on their own recent history (this is literally what anchor-and-adjust models). Hiding it would be cruel and unrealistic. | S | Scrollable table or single-panel mini-chart. |
| TS-27 | **Negative-inventory display = backorder** (never a negative number to the player; show "Backorder: N" separately from "On hand: 0") | Standard Beer Game presentation. Players who see "-5 inventory" get confused. | S | Display logic only. |

### Information Visibility per Station — Canonical Rules (HIGH confidence)

This is the load-bearing per-station matrix. Get this wrong and the simulator is not the Beer Game.

| Information | Retailer sees? | Wholesaler sees? | Distributor sees? | Factory sees? | Notes |
|---|---|---|---|---|---|
| Own on-hand inventory | YES | YES | YES | YES | Always visible. |
| Own backorder | YES | YES | YES | YES | Always visible. |
| Own cumulative cost | YES | YES | YES | YES | Standard. |
| Own outgoing order history | YES | YES | YES | YES | The player's own decisions. |
| Incoming order this week (from downstream customer) | YES (customer demand) | YES (retailer's order) | YES (wholesaler's order) | YES (distributor's order) | Each station sees only what its immediate downstream just ordered. |
| **Future customer demand** | **NO** | **NO** | **NO** | **NO** | **The retailer does NOT know the step is coming. This is the entire experiment.** |
| **Other stations' on-hand inventory** | **NO** | **NO** | **NO** | **NO** | No cross-station visibility during play. |
| **Other stations' backorders** | **NO** | **NO** | **NO** | **NO** | Same. |
| **Other stations' orders placed** | **NO** | **NO** | **NO** | **NO** | Critical — wholesaler can't see distributor's order. |
| Incoming shipment due this week | YES | YES | YES | YES | Player must know what just arrived (the front of the shipping queue). |
| Incoming shipment due next week | YES | YES | YES | YES (next week of production output) | Most implementations show the next 1–2 pipeline slots. Sterman's protocol: player can mentally track their own pipeline since they placed those orders. Showing "in transit" is permissible and standard in computerized versions (kaminsky/Berkeley). |
| Order placed last week that hasn't arrived yet | YES | YES | YES | N/A (factory has no order) | Same — pipeline visibility for the player's own orders is allowed and standard. |
| Upstream supplier's inventory | NO | NO | NO | N/A | The whole point. |

**Implementation note:** During play, the UI must render one station view only. The 4-panel chart of every station's behavior is shown **only on the debrief screen**, after the game ends.

---

### Differentiators (Make It Stand Out — Defer Past v1)

These are not in PROJECT.md's "Active" requirements but would distinguish this simulator from the dozen existing ones. Listed roughly in order of value-per-effort.

| # | Feature | Value Proposition | Complexity | Notes |
|---|---|---|---|---|
| D-1 | **"What if I had played perfectly?" replay** — after the debrief, replay the same demand with the player's station also running the Sterman heuristic, and show the cost delta | Lets the player see "the gap between you and the textbook-optimal anchor-and-adjust" — quantifies personal contribution to the bullwhip. | M | Re-run the same sim with the player slot also driven by AI; compare totals. |
| D-2 | **Per-week narration / annotation overlay on the 4-panel chart** — markers at "week 5: demand step", "week ~9: your first overreaction", "week ~14: peak inventory at factory" | Turns the chart from a picture into a story. The single biggest UX improvement over generic implementations. | M | Heuristic markers: detect first peak after the step, first backorder crossing, max amplitude week. |
| D-3 | **Bullwhip score (0–100)** — a single number derived from the amplification ratio chain, with a percentile vs. "typical novice" benchmark | Gives the player a shareable summary. Single most viral piece of post-game UX. | S | Map amplification ratio to a 0–100 scale; reference distribution from Sterman 1989 published results (~mean amplification factor ~2× per echelon). |
| D-4 | **AI agent transparency panel** in the debrief — show the Sterman heuristic parameters and how each AI made its decision each week | Teaching multiplier: helps the player see that the AI used the *same* heuristic they did, yet still produced amplification — the lesson is structural, not human. | M | Render the formula + a per-week table. |
| D-5 | **Lead-time visualization mid-game** — small "pipeline" widget showing the player's outgoing-order queue and incoming-shipment queue as a literal pipeline of boxes | Many players don't internalize "the order I place today won't arrive for 4 weeks". A visual pipeline fixes that mid-game. | S | 4 small box widgets labeled with weeks-out. |
| D-6 | **Optional "compare to canonical Sterman result" overlay** on the debrief chart | Lets the player see how their game compares to the published curves. Builds credibility ("this matches the textbook"). | M | Pre-compute one canonical "all four stations run by AI" trace; overlay as dashed lines. |
| D-7 | **Short pre-game video / animation (10s)** of the bullwhip emerging | Hooks the player on why this matters before they read rules. | M | Pre-rendered GIF or st.video. |
| D-8 | **Downloadable game log (CSV)** | Power users (students, instructors) want the data. Trivial once the sim object exists. | S | One pandas.to_csv call from the debrief. |
| D-9 | **Shareable static image of the debrief 4-panel chart** | Virality — students post their bullwhip on LinkedIn / Slack. | S | matplotlib `savefig` + `st.download_button`. |
| D-10 | **Audio cues / haptic feedback on backorder spike** | Some implementations beep when inventory crashes. Probably not worth it in Streamlit. | L | Nice-to-have only; Streamlit audio support is awkward. |

---

### Anti-Features (Deliberately NOT Building — and Why)

These are common requests, common implementation choices, or seemingly-helpful additions that would either (a) break the Beer Game's experimental premise, (b) ruin the bullwhip lesson, or (c) violate canonical rules to the point that an instructor would not trust the result.

| # | Anti-Feature | Why Requested | Why It Breaks the Game | Do Instead |
|---|---|---|---|---|
| AF-1 | **Show all 4 stations' state during play (multi-panel "god view")** | "I want to see what's happening upstream so I can make better decisions." | This *is* the experiment. The bullwhip is caused by limited visibility; revealing all state collapses the lesson. The player will outperform any real supply chain and learn nothing. | Reveal all state in the post-game debrief only. |
| AF-2 | **Show future customer demand (or even hint at the step)** | "It's just 4 then 8 — why hide it?" | Sterman's protocol depends on the player *discovering* the step and overreacting. Showing it removes the demand-signal noise and the player simply orders 8 forever. No bullwhip, no lesson. | Hide demand entirely. Even the retailer learns it only one week at a time. |
| AF-3 | **Recommended order quantity / "optimal" hint each week** | "Help the player who's stuck." | Anchors the player to the AI's number. The whole point is to let the player *fail* in the canonical way, then explain why. Hints destroy the gap that the debrief explains. | Show order history and let them anchor on their own past behavior, like real humans. |
| AF-4 | **Slider input with a low upper bound (e.g., 0–20)** | UI cleanliness. | Bullwhip orders genuinely reach 30–80+ at the factory. A capped slider silently truncates and hides the bullwhip itself. | Plain integer input with min=0, no max. |
| AF-5 | **Auto-fill or "use last week's order" button** | Convenience. | Removes the deliberate cognitive friction of committing to a number. The friction *is* the data. | Make the player type/select each week. |
| AF-6 | **Allow negative orders (returns)** | "What if I have too much?" | Not canonical. Real supply chains can't un-ship. Allowing returns dampens the bullwhip artificially. | Enforce min=0. |
| AF-7 | **Symmetric $1/$1 costs ("simpler to explain")** | Cleaner story. | The $0.50 holding / $1.00 backorder asymmetry is what makes over-ordering feel rational and is the textbook lesson. Symmetric costs change the equilibrium and the bullwhip shape. | Use canonical asymmetric $0.50 / $1.00. |
| AF-8 | **Shortened lead times "to make games faster"** | UX speed. | Cutting lead times to 1 week dramatically reduces the bullwhip — the lesson literally won't appear in the debrief. | Keep canonical 2/2/2 weeks. If speed is wanted, cut weeks before cutting lead times. |
| AF-9 | **Random / noisy customer demand** | "Realism." | Adds variance that confounds the bullwhip — the player can't tell whether their orders amplified the signal or the signal was noisy. Sterman uses deterministic step *because* it isolates structural amplification. | Keep deterministic step. (Configurable demand is anyway out of scope per PROJECT.md.) |
| AF-10 | **Skip-the-debrief option** | "I just want to play." | The core value (per PROJECT.md) is "the player sees the bullwhip in the debrief." Without debrief there is no product. | Force the debrief; let them play again from inside it. |
| AF-11 | **Multiplayer / shared session** | "Real Beer Game has 4 players." | Explicitly out of scope in PROJECT.md (Streamlit Cloud free-tier doesn't fit shared state). Solo-vs-AI is the design. | One human + 3 AI, deterministic. |
| AF-12 | **Configurable lead times / costs / demand** | "Sandbox mode." | Out of scope in PROJECT.md; also confuses the teaching goal (the canonical setup is what the student should remember). | Single canonical config in v1. |
| AF-13 | **Real-time multi-tab god view for instructors** | "Live classroom." | Out of scope; would require shared state. | Future v2 if there is an instructor mode at all. |
| AF-14 | **Save/resume across browser sessions** | "I want to come back tomorrow." | Out of scope per PROJECT.md (in-session state only — matches Streamlit Cloud free tier). 36 weeks at ~10 seconds/week = one sitting by design. | Make the play loop fast enough that you don't *need* save. |
| AF-15 | **Authentication / user accounts** | "Track my progress." | Out of scope per PROJECT.md. | No accounts. |
| AF-16 | **Mobile-first responsive UI** | "Phone play." | Out of scope; tablet/desktop only. Charts don't read on phones anyway. | Default Streamlit layout. |
| AF-17 | **Difficulty selector (easy / medium / hard AI)** | "Replay value." | Out of scope per PROJECT.md. Also: comparing player vs. *one canonical AI* is what makes the debrief honest. | Single Sterman heuristic for all 3 AI seats. |
| AF-18 | **Leaderboard / score sharing** | "Competitive." | Out of scope; requires persistence. | Downloadable image (D-9) is the lightweight equivalent. |
| AF-19 | **Tooltips that explain "you should order X because Y"** | Hand-holding. | Same as AF-3 — destroys the gap between player and optimal that the debrief explains. | Rules screen + primer up front; let the game itself teach. |
| AF-20 | **Animated shipments traveling between stations during play** | Eye candy. | Distracting; Streamlit doesn't animate well; adds engineering effort with no teaching value. | Static pipeline widget (D-5) is the right level. |

---

## Feature Dependencies

```
TS-3 (shipping delay queues) ──┐
TS-4 (order delay queues)      ├──> TS-14 (settlement order) ──> TS-19 (4-panel chart)
TS-5 (production delay)        │                              ├──> TS-20 (amplification ratio)
TS-15 (exogenous demand)       │                              └──> TS-21 (cost breakdown)
TS-7 (step demand array)       │
TS-10 (equilibrium init)       │
TS-6 (cost rates)              │
TS-16 (factory infinite raw)   │
                               │
TS-9 (Sterman AI) ─────────────┘
TS-25 (deterministic seed) ──> TS-9

TS-17 (rules screen) ─────> TS-8 (station picker) ─────> TS-12 (order input)
TS-18 (diagram) ──enhances──> TS-17

TS-11 (per-turn local panel) ──> TS-12 (order input) ──> TS-13 (advance week)
TS-26 (order history) ──enhances──> TS-11
TS-27 (backorder display) ──enhances──> TS-11
TS-24 (no-communication UI) ──enforces──> TS-11

TS-19 (4-panel chart) ──> TS-22 (narrative)
TS-20 (amplification ratio) ──> TS-22
TS-21 (cost breakdown) ──> TS-22
TS-22 (narrative) ──> TS-23 (play again)

D-1 (perfect-play replay) ──requires──> TS-9, TS-19
D-2 (chart annotations) ──requires──> TS-19
D-3 (bullwhip score) ──requires──> TS-20
D-4 (AI transparency) ──requires──> TS-9
D-6 (canonical overlay) ──requires──> TS-19
```

### Dependency Notes

- **The sim engine (TS-3, TS-4, TS-5, TS-14) is the spine.** Everything debrief-related (TS-19/20/21/22) is a read-only consumer of the per-week trace the engine produces. Build the engine first, with golden-trace tests, before any UI.
- **TS-9 (Sterman AI) needs the engine but the engine does not need it.** The engine should accept any callable `(station_state) -> order_quantity`; the AI is one such callable, the human is another.
- **TS-17 + TS-18 (rules + diagram) gate TS-8 (station picker)** in the user flow. Player must see the chain structure before choosing a role, or the choice is meaningless.
- **TS-24 (no-communication UI) is not a feature, it's a non-feature** — it's the constraint that says "render only one station's state during play." Calling it out so it doesn't get accidentally violated by an "improvement."
- **D-1 (perfect-play replay) and D-2 (chart annotations) both require the full debrief chart (TS-19);** they're cheap *after* TS-19 ships.

---

## MVP Definition

### Launch With (v1) — Aligns with PROJECT.md "Active" Requirements

All of these are P1. Skipping any breaks the core value ("player completes one game and sees the bullwhip").

- [ ] TS-1 through TS-27 (all table stakes)

That's the entire v1. The "Active" checklist in PROJECT.md maps cleanly onto TS-1, TS-2 (engine), TS-7 (demand), TS-8 (picker), TS-9 (AI), TS-11/12/13 (per-turn UI), TS-17/18 (rules + primer), TS-19/20/21/22 (debrief).

### Add After Validation (v1.x)

Trigger: once table-stakes is shipped and used in at least one classroom, pick *one* differentiator based on which gap students complain about most.

- [ ] D-2 (chart annotations) — if students say "I get the picture but not the story" → annotate
- [ ] D-3 (bullwhip score) — if students want a shareable summary → score
- [ ] D-5 (pipeline widget) — if students report "I didn't understand the lag" → visualize it mid-game
- [ ] D-8 (CSV export) — if any instructor asks for the data → trivial to add
- [ ] D-9 (debrief image download) — if anyone organically tries to screenshot → make it a button

### Future Consideration (v2+) — Most of These Are Already Out of Scope per PROJECT.md

- [ ] D-1 (perfect-play replay) — defer; doubles the sim runtime per game and risks confusing the "you caused this" story
- [ ] D-4 (AI transparency panel) — defer; advanced learners only
- [ ] D-6 (canonical overlay) — defer; needs careful UI to not clutter the bullwhip picture
- [ ] D-7 (intro video) — defer; static rules screen is enough for v1

---

## Feature Prioritization Matrix

P1 = required for launch (table stakes). P2 = first differentiator to add post-launch. P3 = defer.

| Feature | User Value | Implementation Cost | Priority |
|---|---|---|---|
| TS-1 4-station chain | HIGH | LOW | P1 |
| TS-2 36-week loop | HIGH | LOW | P1 |
| TS-3/4/5 Delay queues | HIGH | LOW | P1 |
| TS-6 Asymmetric costs | HIGH | LOW | P1 |
| TS-7 Step demand | HIGH | LOW | P1 |
| TS-8 Station picker | HIGH | LOW | P1 |
| TS-9 Sterman AI | HIGH | MEDIUM | P1 |
| TS-10 Equilibrium init | HIGH | LOW | P1 |
| TS-11 Local-only info panel | HIGH | LOW | P1 |
| TS-12 Order input | HIGH | LOW | P1 |
| TS-13 Advance-week button | HIGH | LOW | P1 |
| TS-14 Settlement order | HIGH | MEDIUM | P1 |
| TS-15 Retailer-only customer demand | HIGH | LOW | P1 |
| TS-16 Infinite factory raw material | HIGH | LOW | P1 |
| TS-17 Rules screen | HIGH | LOW | P1 |
| TS-18 Supply-chain diagram | HIGH | LOW | P1 |
| TS-19 4-panel debrief chart | HIGH | MEDIUM | P1 |
| TS-20 Amplification ratio | HIGH | LOW | P1 |
| TS-21 Cost breakdown | HIGH | LOW | P1 |
| TS-22 Narrative debrief | HIGH | LOW | P1 |
| TS-23 Play again | MEDIUM | LOW | P1 |
| TS-24 No-communication UI (constraint) | HIGH | LOW | P1 |
| TS-25 Deterministic AI seed | MEDIUM | LOW | P1 |
| TS-26 Player order history | HIGH | LOW | P1 |
| TS-27 Backorder display | MEDIUM | LOW | P1 |
| D-1 Perfect-play replay | MEDIUM | MEDIUM | P3 |
| D-2 Chart annotations | HIGH | MEDIUM | P2 |
| D-3 Bullwhip score | MEDIUM | LOW | P2 |
| D-4 AI transparency panel | LOW | MEDIUM | P3 |
| D-5 Pipeline widget | MEDIUM | LOW | P2 |
| D-6 Canonical overlay | MEDIUM | MEDIUM | P3 |
| D-7 Intro video | LOW | MEDIUM | P3 |
| D-8 CSV export | LOW | LOW | P2 |
| D-9 Debrief image download | MEDIUM | LOW | P2 |
| D-10 Audio cues | LOW | HIGH | P3 |

---

## Competitor Feature Analysis

Major existing implementations surveyed: MIT Sloan Beer Game Online, Zensimu, beergameapp.com, transentis (BPTK), Kaminsky/Berkeley computerized beer game, the original board version.

| Feature | MIT Sloan Online | Zensimu | beergameapp.com | Transentis BPTK | Our Approach |
|---|---|---|---|---|---|
| Solo vs. AI | Yes (single-player mode) | Yes (vs. bots) | Multiplayer-first; solo possible | Solo simulation | **Solo-vs-AI is the only mode** |
| Canonical Sterman params | Yes | Configurable, defaults Sterman-ish | Configurable | Configurable | **Locked to canonical, no config** |
| Step demand 4→8 | Yes | Configurable | Configurable | Configurable | **Locked to canonical** |
| 4-panel debrief chart | Yes | Yes (auto-charts) | Yes | Yes | **Yes, plus narrative** |
| Amplification ratio | Implicit (chart) | Yes | Yes | Yes | **Yes, explicit number + percentile** |
| Cost breakdown | Yes | Yes | Yes | Yes | **Yes** |
| Narrative debrief text | Light | Instructor-driven | Light | Light | **Heavy — replaces the instructor** |
| Hide future demand | Yes | Yes | Yes | Yes | **Yes (canonical)** |
| Hide other stations during play | Yes | Yes | Yes | Yes | **Yes (canonical)** |
| Recommended order hint | No | No | No | No | **No (anti-feature)** |
| Slider w/ low cap | No | No | No | No | **No — unbounded integer input** |
| Configurable lead times | No (locked) | Yes | Yes | Yes | **No (locked to canonical)** |
| Hosting | MIT login | SaaS | SaaS | Self-host | **Streamlit Cloud, no login** |

**Where we differ:** Most competitors are configurable instructor-led tools. **Our differentiator is "drop the player into the canonical Sterman setup, no setup screen, no config, in a public URL with no login — and let the debrief teach them."** The narrative debrief + locked-canonical setup is the wedge.

---

## Quality Gate Verification

- [x] Canonical Sterman 1989 parameters cited (lead times, costs) — see Reference Card; HIGH confidence, multiple sources
- [x] Per-station information visibility rules documented (what each station can/can't see) — see matrix; canonical rule of zero cross-station visibility documented and enforced
- [x] Debrief content categorized — what an instructor would point to: 4-panel chart (TS-19), amplification ratio (TS-20), cost breakdown (TS-21), narrative (TS-22)
- [x] Anti-features include the "show everything" trap (AF-1) and "let player see future demand" trap (AF-2)
- [x] Each feature has a complexity hint (S/M/L equivalent: LOW/MEDIUM/HIGH)

---

## Sources

- John Sterman, "Flight Simulators for Management Education: The Beer Distribution Game," MIT (canonical parameters, costs, demand, duration). https://web.mit.edu/jsterman/www/SDG/beergame.html — HIGH confidence
- "A Mathematical Model of the Beer Game," JASSS 17(4):2 (lead times, holding/backorder costs, initial conditions, Sterman optimal parameters). https://www.jasss.org/17/4/2.html — HIGH confidence
- Wikipedia, "Beer distribution game" (general rules, 2-week shipping, board-game variant notes). https://en.wikipedia.org/wiki/Beer_distribution_game — MEDIUM confidence (variant numbers differ from Sterman canonical)
- Columbia Business School, "The Stationary Beer Game" (Sterman parameter confirmation). https://business.columbia.edu/sites/default/files-efs/pubfiles/4345/stationary%20beer%20game.pdf — HIGH confidence
- Kaminsky & Simchi-Levi, "A New Computerized Beer Game," Berkeley (UI conventions, what's shown each turn). https://kaminsky.ieor.berkeley.edu/Reprints/PK_DSL_98b.pdf — HIGH confidence
- Lehigh University tech paper on order quantity variability (lead-time confirmation). https://engineering.lehigh.edu/sites/engineering.lehigh.edu/files/_DEPARTMENTS/ise/pdf/tech-papers/09/09t_019.pdf — MEDIUM confidence
- Zensimu Debriefing Instructor Guide (debrief content, instructor narrative landmarks). https://zensimu.com/resources/debriefing-instructor-guide/ — MEDIUM confidence
- beergameapp.com Ultimate Guide (decision UI, information shown per turn, debrief analytics). https://beergameapp.com/ultimate-guide-beer-game-supply-chain-training/ — MEDIUM confidence
- isixsigma.com, "The Beer Distribution Game" (parameter cross-check). https://www.isixsigma.com/training-materials-aids/the-beer-distribution-game/ — MEDIUM confidence
- MIT News, "The secrets of the system" (information-asymmetry rationale). https://news.mit.edu/2012/manufacturing-beer-game-0503 — MEDIUM confidence
- Consideo Beergame English manual (initial conditions: 12 cases, 4/wk equilibrium). https://www.consideo.com/files/consideo/Beergame-English.pdf — MEDIUM confidence (PDF binary; values cross-confirmed via newpaltz instructions)
- SUNY New Paltz, "Instructions for Running the Beer Distribution Game" (initial orders, equilibrium setup). https://www2.newpaltz.edu/~liush/OM/beer%20game.htm — MEDIUM confidence

---

*Feature research for: single-player Streamlit Beer Distribution Game simulator (Sterman 1989 canonical)*
*Researched: 2026-05-18*
