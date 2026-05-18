# Pitfalls Research

**Domain:** Beer Distribution Game (single-player teaching simulator, Streamlit)
**Researched:** 2026-05-18
**Confidence:** HIGH for simulation mechanics (Sterman 1989 + JASSS 2014 mathematical model verified), HIGH for Streamlit traps (official docs + 2024-2026 community threads), MEDIUM for Streamlit Community Cloud quirks (active discussion threads, behavior changes year-to-year).

**Critical success criterion this document protects:** An instructor must recognize the canonical bullwhip pattern in the post-game debrief. Every Critical Pitfall below can silently break that pattern while still producing a "working" app.

---

## Critical Pitfalls

These are the pitfalls that, if made, cause the project to fail its teaching goal. They produce an app that *runs* but shows the wrong curves.

### Pitfall 1: Wrong order-of-operations within a week

**What goes wrong:**
The four mechanical steps + one decision step in a Beer Game week have a strict canonical order. If the player's order is placed *before* receiving incoming shipments and incoming orders, the station decides with stale information. Inventory and backlog numbers drift away from the published baseline and the bullwhip amplitude flattens or shifts in time.

**Canonical sequence each week (per Sterman / MIT Sloan / beergame.org):**
1. **Receive inventory** — shipment that was in transit `shipping_delay` weeks ago arrives now (factory: production that started `production_delay` weeks ago).
2. **Fill orders & ship** — ship as much as on-hand inventory allows to the downstream neighbor; unfilled demand becomes (or adds to) backlog.
3. **Receive incoming orders** — new order from downstream arrives (after `order_delay`). This becomes part of next-week's demand to fill.
4. **Record state** — on-hand inventory, backlog, supply line.
5. **Place order** (the only decision) — order upstream based on the state *after* steps 1–4.

**Why it happens:**
Developers think of "a turn" as receiving a single user input and updating everything. They wire it up in code order rather than process order. A second flavor: putting the player's order into the supply line *immediately* (week N) instead of having it arrive upstream at week N + order_delay.

**How to avoid:**
Implement the week as five named functions called in a fixed order from a single `advance_week()` driver. Write the order in a comment block at the top of the function. Snapshot every state variable into a per-week log before mutating, so you can replay it in tests.

**Warning signs:**
- Cost numbers in week 1 are nonzero (in equilibrium with demand=4 and orders=4, costs should be exactly the holding cost on initial inventory).
- Inventory dips and the order spike happen the *same* week instead of the order lagging the dip.
- Player's just-placed order shows up in their own supply line immediately rather than after the order delay.

**Phase to address:** Engine (Phase 1 — simulation core). Write the canonical sequence into the engine before any UI exists.

---

### Pitfall 2: Wrong lead-time values (or off-by-one in the lead-time queue)

**What goes wrong:**
Sterman uses a **2-week order (mailing) delay + 2-week shipping delay** = 4-week total acquisition lag for retailer/wholesaler/distributor. The factory has **no order delay + 2-week production delay**. Some implementations use 1+1, some use 2+2 but apply it as 2+2 = "shipment arrives 2 weeks later" while still counting the order arrival as same-week. Either flattens the bullwhip dramatically because amplification is driven by the delay-induced phase lag.

The JASSS (2014) mathematical model formalizes it as:
- `mailing_delay_time (mdt) = 1` week (retailer/wholesaler/distributor); `0` for factory
- `shipment_time (st) = 2` weeks (wholesaler/distributor/factory shipments)
- `production_lead_time (plt) = 2` weeks (factory production)

**Note on the "2+2" vs "1+2" discrepancy:** Wikipedia and many teaching write-ups say "2 weeks delay" because they include the in-flight cell. JASSS counts the queue cells. Pick one accounting and stick with it. The total *acquisition lag* from "I order" to "I receive" should be **4 weeks** for non-factory stations.

**Why it happens:**
Lead-time queues are normally implemented as Python lists (`shipping_pipeline = [units, units, ...]`) and the developer either:
- (a) appends today's shipment then immediately pops it (zero effective delay),
- (b) initializes the pipeline empty (so the first 4 weeks have nothing arriving — game starts disequilibrated),
- (c) pops on the wrong side of the list (FIFO vs LIFO confusion).

**How to avoke:**
Model the pipeline as a fixed-length deque with explicit slots: `[arrives_this_week, arrives_next_week]` for a 2-step pipeline. Initialize *every* pipeline slot with the equilibrium throughput (4 units) so weeks 1–4 stay in equilibrium when demand is still 4. Test: with constant demand = 4 and constant orders = 4, inventory must stay flat at 12 for all 36 weeks. If it drifts, the queue is wrong.

**Warning signs:**
- Week 1 already shows inventory ≠ 12.
- Bullwhip onset happens at week 1 instead of week 5 (where the demand step is).
- Factory's order curve doesn't lag and amplify the Distributor's — if Factory peaks *earlier* or with *smaller* amplitude than Distributor, the lead-time queue is broken upstream.
- Reducing all lead times to 1 doesn't reduce the bullwhip amplitude (it should reduce it dramatically — that's literally the system-dynamics insight).

**Phase to address:** Engine (Phase 1). Add a regression test for the equilibrium case as the very first engine test.

---

### Pitfall 3: Sterman heuristic with wrong parameters (α, β, θ, S')

**What goes wrong:**
The bullwhip in the published Beer Game results emerges from Sterman's *empirical* anchor-and-adjust parameters — values fit to real human players. Many implementations use either (a) "optimal" parameters from later theoretical papers, which produce a *flat* or near-flat order curve (no bullwhip — that's the whole point of "optimal"), or (b) made-up values like α=0.5, β=0.5 that produce chaotic / oscillating curves unlike the canonical pattern.

**Canonical values to use (Sterman 1989, mean estimated parameters across subjects):**
- α (stock adjustment fraction) ≈ **0.26** (range across subjects ~0.20–0.40)
- β (supply line weight) ≈ **0.34** (the key insight: humans underweight the supply line; β < 1 causes bullwhip)
- θ (demand-smoothing factor) ≈ **0.36** (exponential smoothing on observed demand)
- S' (desired inventory + desired supply line coverage) ≈ **17** units

The JASSS (2014) paper reports the *optimal* (cost-minimizing) parameters as α=1, β=1, θ=0, S'≈28 (20 for factory) — **do not use these**. The optimal parameters produce no bullwhip. The empirical parameters do.

**Why it happens:**
Developers find the JASSS paper, copy the "optimal" parameters because they look authoritative, and end up with three AI stations that calmly track demand. The player sees no bullwhip and the lesson fails. Alternatively: implementer reads Sterman's order equation but skips the parameter estimation section and just picks numbers that "look reasonable."

**How to avoid:**
Hardcode the empirical parameter set (α=0.26, β=0.34, θ=0.36, S'=17) and *cite Sterman 1989 in the code comment*. Reference equation: `O_t = max(0, L_t + α·(S' − I_t − β·SL_t))` where `L_t = θ·D_t + (1−θ)·L_{t−1}` (smoothed expected demand). Add a calibration test: run all-4-stations-AI on the step-demand scenario and assert the Factory's peak order is ≥ 2× the Retailer's peak order (the canonical amplification ratio is roughly 2–4×).

**Warning signs:**
- All four stations track demand with low amplitude — no bullwhip visible.
- Order curves oscillate wildly with no clear "peak then collapse" pattern (parameters too aggressive).
- Amplification ratio (Factory peak / Retailer peak) is < 1.5 or > 6 — outside the canonical range.
- Factory orders never go to 0 in the post-peak phase — Sterman's curve has a dramatic collapse to ~0 after the overshoot.

**Phase to address:** Engine (Phase 1 — AI agent). The calibration test is the single most important quality gate in the project.

---

### Pitfall 4: Retailer-only customer-demand visibility violated

**What goes wrong:**
The teaching point of the Beer Game is that *each station only sees orders from its immediate downstream neighbor*. Only the Retailer sees actual end-customer demand. The Wholesaler sees Retailer's orders, the Distributor sees Wholesaler's orders, the Factory sees Distributor's orders. If any non-Retailer station has access to customer demand — even read-only — the bullwhip can be reasoned away and the lesson is dead.

**Why it happens:**
- Implementer puts a single `current_demand` field in the global game state and shows it on every station's panel by accident.
- Debug UI gets shipped to production with full state visible.
- AI agents are coded to read `customer_demand` directly instead of their own incoming-order pipeline.
- The Streamlit sidebar shows "current week's customer demand" globally.

**How to avoid:**
Each station has its own `incoming_order` field. The Retailer's `incoming_order` comes from the customer demand function; every other station's `incoming_order` comes from the downstream station's *placed order* delayed by `order_delay`. AI agents take only their own station's state as input — no global state pointer. The Streamlit UI renders only the active player's station view; the other stations' states are computed but *not displayed* until the post-game debrief.

**Warning signs:**
- Player playing as Factory can predict the demand step at week 5.
- AI agents respond to the demand step the same week it happens, regardless of their position in the chain.
- The "current state" panel shows a "customer demand" field even when the player is not the Retailer.

**Phase to address:** Engine (Phase 1 — encapsulation) + UI (Phase 2 — view scoping). Enforce information hiding in the engine API, not just the UI.

---

### Pitfall 5: Backlog not carrying over (or not costing anything)

**What goes wrong:**
When a station can't fill an incoming order in full, the unfilled portion must (a) carry over to next week as additional demand, (b) accrue backlog cost at $1.00/case/week until cleared, and (c) be filled as soon as inventory allows. Many implementations either drop unfilled demand on the floor (no carryover) or count backlog only once instead of every week it persists. Result: cost curves are far too gentle, and there's no penalty for the overshoot-then-collapse pattern that defines the Factory's pain.

**Why it happens:**
Modeling backlog as "this week's unfilled" instead of "running unfilled balance." Or, treating backlog cost as a one-time event when the backlog is created instead of a recurring weekly charge.

**How to avoid:**
Model backlog as a running scalar per station. Each week: `backlog += new_unfilled_demand; backlog_cost += backlog * 1.00`. Shipping logic: ship `min(on_hand, demand_this_week + backlog)`, reducing backlog before any new demand. Test: with a 1-week stockout and immediate recovery, backlog cost should equal the unfilled units × $1.00. With a 3-week stockout, the cost should triple.

**Warning signs:**
- Factory's cost in the post-overshoot weeks looks like the cost in the equilibrium weeks (it should be much higher due to inventory pile-up after over-ordering).
- Total team cost in a "good" run vs. a "bad" run differs by less than 2× — the canonical spread is ~5–10×.
- Backlog briefly appears and disappears without any cost trace.

**Phase to address:** Engine (Phase 1 — state mechanics).

---

### Pitfall 6: Initial conditions not in equilibrium

**What goes wrong:**
The canonical setup has the system in steady-state equilibrium for weeks 1–4: every station has **12 units on-hand**, **0 backlog**, **4 units in every shipping/order pipeline slot**, customer demand is 4, and every station orders 4. The system should sit *perfectly flat* until the demand step at week 5 perturbs it. If initial inventory is wrong (e.g., 0, or 20) or pipelines are empty or holding the wrong values, the bullwhip starts at week 1 from initial-condition transient noise, not from the actual demand shock — destroying the "look, the step-change at week 5 is what caused this!" pedagogical moment.

**Why it happens:**
Implementer initializes everything to zero (default Python behavior) and intuits that "the game will settle into equilibrium." It won't — the supply line transient takes 4+ weeks to wash out, which collides with the demand step.

**How to avoid:**
Document and hardcode initial state in one place:
```
inventory[s] = 12, backlog[s] = 0,
order_pipeline[s] = [4, 4],     # each station has 4 units of order in flight
shipping_pipeline[s] = [4, 4],  # each station has 4 units of shipment in flight
demand[1..4] = 4,               # equilibrium phase
demand[5..36] = 8,              # post-step phase
```
Regression test: run the game with all four stations played by an AI that always orders 4. Assert inventory stays at 12 and cost is `12 × 0.50 × 36 = 216` for every station, until the demand step — then post-step the system should diverge.

**Warning signs:**
- Inventory deviates from 12 before week 5.
- Charts show a "bullwhip" at weeks 1–4 before any demand change happens.
- The all-AI run with constant demand never converges to a flat line.

**Phase to address:** Engine (Phase 1 — initialization).

---

### Pitfall 7: Factory production cost not modeled, or modeled differently

**What goes wrong:**
The Factory's upstream "supplier" is the production line — there is no infinite upstream warehouse. Some implementations model the Factory with a magic infinite-supply order channel (so the Factory never has a supply-line concern), which collapses the four-station structure into a three-station chain. The canonical model has the Factory order from a 2-week *production delay* pipeline that behaves identically to the other shipping pipelines, with the only difference that there is no order-mailing delay (the Factory schedules production directly).

Holding/backlog costs at the Factory are the **same rates** as other stations ($0.50/week and $1.00/week). Don't add a "production cost" — there isn't one in the canonical game.

**Why it happens:**
Mental model of "factory makes stuff from raw materials" leaks into the implementation; developer adds a raw-materials cost or makes Factory production instantaneous "because it's a factory."

**How to avoid:**
Treat all four stations as symmetric except for two parameters: `order_delay` (0 for Factory, 1 for others) and the source of incoming orders (downstream station's placed order). Use a single `Station` class with no special-cased Factory branch except in initialization.

**Warning signs:**
- Factory station code has its own `produce()` method distinct from `receive_shipment()` — fold them.
- Factory orders show no supply-line lag (no overshoot pattern) — it can't be hitting an empty pipeline because its pipeline doesn't exist in your code.
- Total cost at the Factory in a bad run is suspiciously low — it's not paying for the inventory pile-up because there is none.

**Phase to address:** Engine (Phase 1 — station symmetry).

---

## Streamlit-Specific Pitfalls

### Pitfall 8: Game state not in `st.session_state` (or wiped on re-run)

**What goes wrong:**
Streamlit re-runs the entire script top-to-bottom on every widget interaction. Any plain Python variable holding game state (`game = Game()` at the top of the script) gets re-instantiated every time the player clicks "advance week," wiping all prior state. Game appears frozen at week 1 forever, or jumps to random states depending on widget order.

**Why it happens:**
Developer treats Streamlit like a normal Python script. The execution-model surprise is the #1 newcomer pitfall (confirmed by the official Streamlit docs' "Add statefulness to apps" section, which exists specifically because of this).

**How to avoid:**
Single rule: **anything that must persist across re-runs lives in `st.session_state`**. Initialize once with the `if "game" not in st.session_state: st.session_state.game = Game()` pattern. Mutate via `st.session_state.game.advance_week()`. Never re-instantiate.

**Warning signs:**
- Clicking "Advance Week" appears to do nothing (state resets before you can see the change).
- The current week always shows 1 or 2 regardless of how many clicks.
- Print/log statements show the `Game()` constructor running on every interaction.

**Phase to address:** UI (Phase 2 — Streamlit scaffolding).

---

### Pitfall 9: Mutating `session_state` from inside a widget render (StreamlitAPIException)

**What goes wrong:**
Code like `st.session_state.player_order = st.number_input("Order", value=st.session_state.player_order)` after the widget has been instantiated with a `key=` raises `StreamlitAPIException: cannot be modified after the widget with key '...' was instantiated`. The fix is non-obvious to first-time Streamlit developers and crashes the app.

**Why it happens:**
Streamlit owns the widget's session_state slot once you give it a `key`. Modifications must go through callbacks (`on_click`, `on_change`), not direct assignment after instantiation.

**How to avoid:**
Use `on_click=callback` for buttons that mutate game state. Inside the callback, read widget values via `st.session_state[widget_key]` and mutate game state. Never set `st.session_state[widget_key]` directly after the widget renders.

```python
def submit_order():
    order = st.session_state.order_input
    st.session_state.game.advance_week(order)

st.number_input("Order", min_value=0, max_value=99, key="order_input")
st.button("Advance Week", on_click=submit_order)
```

**Warning signs:**
- Red error banner mentioning "modified after the widget with key '...' was instantiated."
- Order input value doesn't survive the page rerun (because you're fighting Streamlit's widget ownership).

**Phase to address:** UI (Phase 2 — input handling).

---

### Pitfall 10: Chart re-rendered from scratch every week (flicker)

**What goes wrong:**
During gameplay, if the per-week sparkline / debrief preview chart is re-built fresh on each `advance_week()` interaction, the chart flashes/flickers because Streamlit tears down and rebuilds the DOM element. With Plotly specifically, version 1.35+ has known flicker issues on rerun (GitHub issue #8782, fixed in later versions but still surfaces with scrollbar interactions).

**Why it happens:**
Returning a fresh `fig` object from a non-cached function on every rerun. Streamlit can't tell it's the same chart conceptually.

**How to avoid:**
- For the in-game per-turn UI, don't show the full debrief chart at all — show a minimal text/metric view (st.metric for inventory, backlog, cost). This is also pedagogically correct: the player shouldn't see the whole-system view until debrief.
- For the post-game debrief: build the chart once after the game ends, render with `st.altair_chart` or `st.plotly_chart`. The debrief isn't interactive so flicker doesn't apply.
- If a per-turn chart is desired, use Altair (less flicker-prone than Plotly per community reports) and use `use_container_width=True` with a stable `key=`.

**Warning signs:**
- Visible flash/flicker when clicking "Advance Week."
- Chart briefly shows old data before updating.
- Browser console shows full chart re-mount events.

**Phase to address:** UI (Phase 2 — render strategy) + Debrief (Phase 3 — chart construction).

---

### Pitfall 11: Heavy computation in main script body

**What goes wrong:**
Putting `game.run_full_36_weeks()` or chart construction at the top of the script outside any guard means it runs on every keystroke / widget interaction. App feels sluggish (200ms+ per click on Streamlit Cloud's small free-tier container).

**Why it happens:**
Streamlit re-runs everything top-to-bottom. Developers who treat the script as "load once" get burned.

**How to avoid:**
- Game advances are cheap (one week of arithmetic) — fine to run on each click.
- Debrief computation (statistics, chart objects) should be triggered by a button or computed *once* in a `@st.cache_data` function keyed on `(game_history_tuple,)`. Convert the game history to an immutable tuple before passing in.
- Do not put `time.sleep()` or any network call in the main script body.

**Warning signs:**
- Streamlit Cloud "Running..." spinner shows on every click for >1 second.
- App becomes noticeably slower as the game progresses (week 36 click slower than week 5 click).

**Phase to address:** UI (Phase 2) + Debrief (Phase 3).

---

### Pitfall 12: `st.form` confusion — order input not batched with submit

**What goes wrong:**
If "Order" is a `st.number_input` and "Advance Week" is a `st.button`, the number_input fires a rerun on every keystroke as the user types "12" (rerun on "1", rerun on "12"). This is wasteful and can cause widget-state bugs. Conversely, putting both inside an `st.form` batches them — the rerun happens only on submit.

**Why it happens:**
Mental model from web forms (HTML forms always have a submit button) doesn't match Streamlit's default (every widget triggers rerun).

**How to avoid:**
Wrap the per-turn input in `st.form("turn")`:
```python
with st.form("turn_form"):
    order = st.number_input("Order", 0, 99, key="order_input")
    submitted = st.form_submit_button("Advance Week")
    if submitted:
        st.session_state.game.advance_week(order)
```

**Warning signs:**
- Console / network tab shows a rerun on every keystroke in the order field.
- Widget state-management bugs that "sometimes" reproduce — often a race between keystroke reruns and the click rerun.

**Phase to address:** UI (Phase 2 — input handling).

---

### Pitfall 13: Streamlit Cloud Python version not pinned (or `runtime.txt` ignored)

**What goes wrong:**
Streamlit Community Cloud defaults to Python 3.13 as of late 2025/early 2026. Multiple users have reported `runtime.txt` being ignored in 2024–2026 deploys, forcing Python 3.13 even when 3.11 is specified. If your code or a dependency requires <3.13 (some scientific libraries had issues at 3.13 launch), the app fails to deploy on Cloud despite working locally.

**Why it happens:**
Streamlit Cloud's deploy pipeline has had intermittent issues honoring `runtime.txt`. The newer `.python-version` file is more reliably read but undocumented for some periods.

**How to avoid:**
- Pin Python with **both** `runtime.txt` (containing `python-3.11`) **and** `.python-version` (containing `3.11`). Streamlit's deploy reads whichever it currently honors.
- Target Python 3.11 or 3.12 — well-supported, stable, broad library compatibility.
- In `requirements.txt`: pin `streamlit==<exact>`, pin numpy/pandas/altair to known-working versions. Don't use loose `>=` for the core stack — silent upgrades have broken Streamlit apps before.
- Test the deploy from a clean fork before announcing.

**Warning signs:**
- Cloud build log shows "Using Python 3.13" when you specified 3.11 in `runtime.txt`.
- Local works, cloud fails with import errors.
- Streamlit version mismatch between local and cloud changes app behavior (widget keys, session_state).

**Phase to address:** Deployment (Phase 4).

---

### Pitfall 14: Streamlit Cloud cold-start (sleep) surprises users

**What goes wrong:**
Free-tier Streamlit Community Cloud apps **go to sleep after 12 hours of no traffic** and take 30–60 seconds to wake up on next visit. A first-time visitor sees a "Yes, get this app back up!" button instead of the app, or a long blank load. They bounce.

**Why it happens:**
Free-tier resource conservation. Documented but easy to overlook.

**How to avoid:**
- Add a one-line note in the README and on the landing page: "App may take ~30 seconds to wake up on first visit — Streamlit Cloud free tier."
- Optionally: add a UptimeRobot ping every 10 hours to keep it warm (only if instructor sessions need predictable load times — generally not needed).
- Keep `requirements.txt` lean so cold-boot package install is fast (no torch, no heavyweight ML libs that aren't actually used).

**Warning signs:**
- First visit on Monday morning takes 45+ seconds.
- "Yes, get this app back up" landing page reported by users.

**Phase to address:** Deployment (Phase 4) + Onboarding screen (Phase 2).

---

### Pitfall 15: File paths that work locally but not on Streamlit Cloud

**What goes wrong:**
Loading an asset with `open("data/foo.csv")` works locally because the cwd is the project root. Streamlit Cloud's cwd may differ depending on the deploy structure (especially for multipage apps). The file is "missing" in production.

**Why it happens:**
Relative paths are relative to cwd, not the script location.

**How to avoid:**
Resolve all file paths relative to the script file:
```python
from pathlib import Path
DATA_DIR = Path(__file__).parent / "data"
df = pd.read_csv(DATA_DIR / "foo.csv")
```
For the Beer Game this is a low-risk pitfall (no data files in v1) but flag it because future content (lesson primers, narrative text) may live in markdown files.

**Phase to address:** Deployment (Phase 4) — apply preemptively in Phase 2 if any file loads exist.

---

## Teaching / UX Pitfalls

### Pitfall 16: No pre-game bullwhip primer

**What goes wrong:**
Player jumps in cold, places orders for 36 weeks, sees four charts in the debrief — has no idea what to look for. The pedagogical payoff requires the player to know in advance: "demand will change once; watch your orders amplify upstream." Without the primer, the debrief is just colored squiggles.

**How to avoid:**
A 30-second primer screen before the game: one paragraph defining the bullwhip effect, a small illustrative graphic (canonical 4-panel chart from a *generic* example, not the one they're about to see), and the prompt "Your job is to keep inventory near 12 and avoid stockouts. Watch what happens upstream." Then start the game.

**Phase to address:** UI (Phase 2 — onboarding screen).

---

### Pitfall 17: Showing the player too much during the game

**What goes wrong:**
Sidebar shows all four stations' inventories and orders in real time → player can reason about the whole system → bullwhip isn't a surprise, just a calculation. Lesson trivialized.

**How to avoid:**
During gameplay, show **only the player's station**: their inventory, backlog, the most recent shipment received, the most recent order received from downstream, total cost so far. Other stations' state is hidden until the debrief. (See Pitfall 4 — this is the UI-side enforcement of the engine-side rule.)

**Warning signs:**
- Test players say "I could see what was coming."
- Debrief feels anticlimactic to the player who already understood mid-game.

**Phase to address:** UI (Phase 2 — view scoping).

---

### Pitfall 18: Future customer demand visible (intentionally or by leaking)

**What goes wrong:**
The week-5 demand step is the surprise that creates the bullwhip. If the player sees a "future demand: 8 at week 5" hint, or worse if a chart axis shows all 36 weeks of customer demand pre-populated, the surprise is gone.

**How to avoid:**
Even the Retailer only learns each week's customer demand when that week begins. Charts during gameplay show only weeks completed so far. The customer-demand function lives inside the engine and is not exposed via any read-only accessor.

**Warning signs:**
- Player playing as Retailer pre-orders 8 starting at week 4.
- Any chart axis extends to week 36 with pre-drawn demand line.

**Phase to address:** Engine (Phase 1) + UI (Phase 2).

---

### Pitfall 19: Debrief charts without labels / annotations

**What goes wrong:**
Four-panel chart of orders + inventory across stations, no axis labels, no week-5 demand-step marker, no peak annotation, no amplification ratio readout → player sees curves but doesn't know which one is the bullwhip. The instructor recognition test fails.

**How to avoid:**
Debrief chart MUST include:
- Vertical line at week 5 labeled "Customer demand: 4 → 8."
- Each panel labeled with the station name and "Orders placed" or "Inventory on hand."
- Y-axis units visible.
- A "Peak amplification" metric displayed: `Factory peak order / Retailer peak order = X.X×`.
- A short narrative below the chart explaining: "Customer demand doubled once. Your Factory's peak order was X× the Retailer's. This is the bullwhip effect."

**Phase to address:** Debrief (Phase 3).

---

### Pitfall 20: Debrief too text-heavy or skipped entirely

**What goes wrong:**
After 36 weeks of clicking, player sees one chart and a "thanks for playing" message. No takeaway. Alternatively: 800 words of dense pedagogical text that the player skims and closes.

**How to avoid:**
Debrief structure: (1) the 4-panel chart up top, (2) three short bullets ("Your Factory ordered up to X units when peak demand was 8 — that's the bullwhip," "Total team cost: $X. The minimum achievable is roughly $Y," "Try playing a different station — Factory feels different from Retailer"), (3) a "Play again" button. Keep all debrief copy under 200 words.

**Phase to address:** Debrief (Phase 3).

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Game state as a dict instead of a `Game` dataclass | Faster to prototype | Untyped state, hard to refactor, no IDE help, tests become brittle | Never — pay this up-front |
| Hardcode all constants inline | Skip a `constants.py` file | Tuning parameters means hunting through code; can't write a calibration test that varies them | Never |
| Use globals for game state instead of `session_state` | Works in a notebook | Breaks immediately on first Streamlit deploy; rewrite required | Notebook prototyping only — never in `app.py` |
| Skip the equilibrium regression test | Save 30 minutes | All other tests built on a broken baseline; bug-hunting from the wrong end | Never |
| Use `print()` for debugging in the deployed app | No setup | Console clutter on Streamlit Cloud, no log persistence | Local dev only; remove before deploy |
| Pin nothing in requirements.txt | Easy initial setup | App breaks silently when Streamlit auto-upgrades on a deploy | Never in production |
| Copy Sterman's *optimal* parameters because they're the most recent published | Looks rigorous | No bullwhip emerges; project fails its teaching goal | Never |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Streamlit Community Cloud | Assume local Python version is used | Pin via both `runtime.txt` and `.python-version`; test on a clean fork |
| GitHub → Streamlit Cloud auto-deploy | Push and pray | Watch the deploy log for the first push; check Python version actually selected |
| `requirements.txt` resolution | Loose version specifiers (`streamlit>=1.30`) | Pin Streamlit exactly; pin numpy/pandas/altair to known-good versions |
| Streamlit `session_state` + widget keys | Modify state after widget renders | Mutate via `on_click`/`on_change` callbacks only |
| Altair vs Plotly for debrief | Pick whatever's familiar | Altair: smaller bundle, less flicker, better for the small static debrief; Plotly: heavier, more flicker reports on rerun |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Rebuilding charts every rerun | Visible flicker on every click | Use `@st.cache_data` on chart builder; or only build charts post-game | First click on Streamlit Cloud (cold container) |
| Heavy imports at top of script | Cold start > 60s | Lean `requirements.txt`; lazy-import any large optional libs | First user visit after sleep (every 12h) |
| Re-running the entire 36-week game on each click | App slows linearly with week count | Advance only one week per click; never replay history | Week 20+ in a 36-week game |
| Streaming events / live polling | App pegs CPU | Beer Game has no real-time component — don't add `st.autorefresh` or sleeps | Any deploy |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Committing `.streamlit/secrets.toml` | Public exposure of any secret (none in v1, but flag for future) | Add `.streamlit/secrets.toml` to `.gitignore` from the first commit |
| Loading user-uploaded files (future) | Path traversal, unbounded memory | v1 has no upload — keep it that way |
| Embedding repo-local `.env` files | API keys leak to public repo | No `.env` in v1; if added later, gitignore |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No "What is this?" landing screen | Player lands on game with no context | One-paragraph "About + how to play" before first turn |
| Per-turn UI shows raw numbers only, no chart of player's own history | Can't see their own trajectory | Small inline chart of player's inventory + orders over weeks 1–N |
| Order input accepts negative numbers or > 99 | Engine breaks, error banner | `min_value=0, max_value=99` on `number_input` |
| No way to restart without page refresh | Friction for replay | "Play again" button that resets `session_state.game` |
| Long page that scrolls during play | Disorienting between turns | Fixed-height layout; player's panel always in same place |

## "Looks Done But Isn't" Checklist

- [ ] **Engine:** Equilibrium regression test passes — constant demand=4, all orders=4 → inventory stays at 12 for 36 weeks at every station.
- [ ] **Engine:** Bullwhip calibration test passes — all-AI run with classic step demand produces Factory peak order ≥ 2× Retailer peak order.
- [ ] **Engine:** Backlog cost accumulates weekly, not once — verify with a 3-week stockout scenario.
- [ ] **Engine:** Player's just-placed order is *not* in their own supply line this week (it should arrive at week + order_delay).
- [ ] **Engine:** Factory has no order delay but does have production delay — symmetric in every other respect.
- [ ] **AI:** Hardcoded Sterman *empirical* parameters (α≈0.26, β≈0.34, θ≈0.36, S'≈17), not "optimal" ones.
- [ ] **UI:** During gameplay, non-player stations' state is computed but not displayed.
- [ ] **UI:** Customer demand for future weeks is not visible to any station.
- [ ] **UI:** `st.session_state.game` initialized once with `if "game" not in st.session_state` guard.
- [ ] **UI:** Order input + advance button wrapped in `st.form` to avoid keystroke reruns.
- [ ] **Debrief:** 4-panel chart has week-5 step marker, axis labels, station labels, amplification ratio readout.
- [ ] **Debrief:** Copy under 200 words; not a wall of text.
- [ ] **Deploy:** `runtime.txt` AND `.python-version` both present, both pinned to 3.11 or 3.12.
- [ ] **Deploy:** `requirements.txt` pins Streamlit exactly + altair/numpy/pandas to known-good versions.
- [ ] **Deploy:** `.streamlit/secrets.toml` (if it ever exists) is gitignored.
- [ ] **Deploy:** Cold-start note shown on landing page or README.
- [ ] **Repo:** Public repo at `greycloak85/beer-game` — verify no accidental private fork; verify license file present.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Wrong order-of-operations within a week | MEDIUM | Refactor `advance_week()` to call the five steps as named functions in the canonical order; rerun calibration test. |
| Wrong lead times / off-by-one queue | LOW (if caught early) / HIGH (if downstream tests depend on broken baseline) | Re-implement pipeline as fixed-length deque with named slots; add equilibrium test; verify amplification ratio. |
| Sterman parameters wrong | LOW | Change four constants in one place; rerun calibration test. The plumbing is fine — only the values were wrong. |
| Backlog cost not accumulating | LOW | One-line fix in the cost calculator; add 3-week-stockout test. |
| Initial conditions wrong | LOW | One-line fix in `Game.__init__`; equilibrium test catches it. |
| Customer demand leaking to non-Retailer stations | MEDIUM | Refactor engine API so stations only expose their own state; refactor UI to render only one station's state. |
| Game state not in `session_state` | LOW (if before UI is rich) / MEDIUM (if widgets reference stale state) | Wrap `Game()` init in the session_state guard; replace all `game.x` references with `st.session_state.game.x`. |
| Streamlit Cloud Python version wrong | LOW | Add both `runtime.txt` and `.python-version`; redeploy. |
| Charts flicker on every rerun | MEDIUM | Move chart construction post-game-end; or switch Plotly → Altair; or cache chart builder. |
| Debrief unrecognizable to instructor | HIGH (project failure if not caught) | This is what the calibration test prevents — invest in it up-front. Recovery means rebuilding the AI parameter set from scratch. |

## Pitfall-to-Phase Mapping

Suggested phase structure (informs roadmap):
- **Phase 1: Simulation Engine** — game state, week sequence, lead-time pipelines, AI, equilibrium + calibration tests
- **Phase 2: Streamlit UI** — session_state plumbing, per-turn view, input handling
- **Phase 3: Debrief** — 4-panel chart, narrative, amplification metric, replay button
- **Phase 4: Deployment** — pinned requirements, runtime/python-version, README, public repo verification

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| 1. Wrong week-step order | Phase 1 | Five named functions called in fixed order; week-1 cost == holding-only cost |
| 2. Wrong lead times / queue off-by-one | Phase 1 | Equilibrium test: inventory stays at 12 for 36 weeks under constant demand |
| 3. Wrong Sterman parameters | Phase 1 | Calibration test: Factory peak / Retailer peak ratio in [2.0, 4.0] |
| 4. Demand visibility leak | Phase 1 (API) + Phase 2 (UI) | Code search: no `customer_demand` accessor on non-Retailer station |
| 5. Backlog not carrying / not costing | Phase 1 | 3-week stockout test: backlog cost = unfilled × 3 × $1.00 |
| 6. Initial conditions wrong | Phase 1 | Equilibrium test (same test as #2) |
| 7. Factory asymmetry | Phase 1 | Code review: single `Station` class, only `order_delay` differs |
| 8. State not in session_state | Phase 2 | Click "Advance Week" twice; week counter must increment to 2 |
| 9. Mutating state after widget render | Phase 2 | No `StreamlitAPIException` in any user flow |
| 10. Chart flicker | Phase 2 / 3 | Visual QA: no flicker on "Advance Week" click |
| 11. Heavy compute in main body | Phase 2 / 3 | Click latency < 500ms on Streamlit Cloud |
| 12. `st.form` not used for input | Phase 2 | Keystroke in order field does not trigger rerun |
| 13. Python version not pinned | Phase 4 | Deploy log shows expected Python version |
| 14. Cold start surprise | Phase 4 | README + landing page mention 30-second cold start |
| 15. File paths break in cloud | Phase 4 | Any file load uses `Path(__file__).parent` |
| 16. No bullwhip primer | Phase 2 | Pre-game screen exists with one-paragraph primer |
| 17. Too much visible during game | Phase 2 | Only player's station rendered during gameplay |
| 18. Future demand visible | Phase 1 + Phase 2 | Customer demand function is private to engine; UI charts show only completed weeks |
| 19. Debrief charts unlabeled | Phase 3 | Chart has axis labels, station labels, week-5 marker, amplification ratio |
| 20. Debrief too text-heavy / missing | Phase 3 | Debrief copy < 200 words; chart is the centerpiece |

## Sources

- **Sterman (1989), "Modeling Managerial Behavior: Misperception of Feedback in a Dynamic Decision-Making Experiment,"** *Management Science* 35(3): 321–339 — canonical source for the anchor-and-adjust heuristic, empirical parameter estimates (α, β, θ, S'), and the four-station structure. [HIGH confidence — primary source]
- **Edali & Yasarcan (2014), "A Mathematical Model of the Beer Game,"** *JASSS* 17(4): 2. https://www.jasss.org/17/4/2.html — formal mathematical model with explicit lead-time structure (mdt, st, plt), initial conditions, and *optimal* (not empirical) parameter values. [HIGH confidence — peer-reviewed primary source for the math]
- **MIT Sloan / Sterman's beer game page** — https://web.mit.edu/jsterman/www/SDG/beergame.html — official game description, costs ($0.50/$1.00), initial inventory (12), step demand. [HIGH confidence — official]
- **beergame.org "Structure & Rules"** — https://beergame.org/the-game/structure-rules/ — canonical week sequence, station structure. [MEDIUM confidence — third-party teaching resource, matches Sterman]
- **Streamlit docs, "Add statefulness to apps"** — https://docs.streamlit.io/develop/concepts/architecture/session-state — official guidance on `session_state` and the re-run model. [HIGH confidence — official]
- **Streamlit docs, "Widget behavior"** — https://docs.streamlit.io/develop/concepts/architecture/widget-behavior — the StreamlitAPIException pattern, key management, callback model. [HIGH confidence — official]
- **Streamlit docs, "App dependencies"** — https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies — runtime.txt, requirements.txt, Python version pinning. [HIGH confidence — official]
- **Streamlit Community Cloud status & limitations** — https://docs.streamlit.io/deploy/streamlit-community-cloud/status — 12-hour sleep behavior, free-tier resources. [HIGH confidence — official]
- **Streamlit discuss threads on runtime.txt being ignored (2024–2026)** — https://discuss.streamlit.io/t/streamlit-cloud-using-python-3-13-despite-runtime-txt-specifying-3-11/113759 and related — community confirmation that runtime.txt pinning has been unreliable; rationale for dual `.python-version` + `runtime.txt`. [MEDIUM confidence — community reports, ongoing issue]
- **Streamlit GitHub issue #8782 (Plotly flicker)** — https://github.com/streamlit/streamlit/issues/8782 — confirmed flicker with Plotly post-1.35.0. [MEDIUM confidence — bug report, partially resolved]
- **Streamlit discuss, "Is there a way to speed up rendering with Altair"** — https://discuss.streamlit.io/t/is-there-a-way-to-speed-up-rendering-time-with-altair/61155 — Altair vs Plotly performance tradeoffs. [MEDIUM confidence — community discussion]

---
*Pitfalls research for: Beer Distribution Game (single-player Streamlit teaching simulator)*
*Researched: 2026-05-18*
