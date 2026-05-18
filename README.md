# Beer Game

> Play the MIT Beer Distribution Game in your browser. See the bullwhip effect emerge.

## Play it

**Live app:** _(pending Streamlit Community Cloud deploy — Phase 4 Plan 02 will fill in the URL.)_

> First-time load takes about 30 seconds — Streamlit Community Cloud puts free-tier apps to sleep after a stretch of no traffic, so the first visitor of the day wakes the container up. Subsequent loads are instant.

## How to play

- You pick one of **four supply-chain stations** at game start: Retailer, Wholesaler, Distributor, or Factory. The other three are played by AI opponents using John Sterman's empirical anchor-and-adjust heuristic from his 1989 paper.
- The game runs for **36 weeks**. Each week you see your own station's inventory, backlog, incoming shipment, the order you received from downstream, and a mini-chart of your past orders — then you place a single order for the week.
- You only see **your own station** — never the others'. That information opacity is the point: you have to guess what's happening upstream and downstream from the orders and shipments crossing your boundary.
- Customer demand starts at **4 units/week** for weeks 1–4, then **steps up to 8 units/week** at week 5 and stays there for the rest of the game. That single modest step is enough to produce dramatic bullwhip in the upstream stations.

Costs: **\$0.50 per case per week** holding cost, **\$1.00 per case per week** backorder cost. The asymmetry is canonical — running out hurts more than over-stocking, which is what makes the over-ordering instinct feel safe and the lesson land.

## What is the bullwhip effect?

Small changes in customer demand get amplified as orders flow upstream through a supply chain. The Retailer sees an extra unit ordered, panics a little, and orders three more. The Wholesaler sees that three-unit jump, panics, and orders nine. By the time the Factory sees demand, it's been amplified out of all proportion to what actually changed.

After the 36th week you get a debrief: a 4-panel chart of orders and inventory across all four stations, an amplification ratio that quantifies the bullwhip in your game, a per-station cost breakdown, and a short narrative that points out exactly where the amplification emerged.

## Running locally

```bash
git clone https://github.com/greycloak85/beer-game.git
cd beer-game

# Create a Python 3.12 virtual environment
python3.12 -m venv .venv

# Install deploy + dev dependencies
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt

# Run the tests (engine + bullwhip calibration + AppTest smoke — all 82 should pass)
.venv/bin/python -m pytest -q

# Launch the app
.venv/bin/streamlit run app.py
```

The app opens at <http://localhost:8501>. A page refresh resets the game (state lives in `st.session_state` only — no database, no accounts).

To run a focused subset of the test suite:

```bash
.venv/bin/python -m pytest tests/test_bullwhip_emerges.py   # the bullwhip calibration gate
.venv/bin/python -m pytest tests/test_equilibrium.py        # the equilibrium regression gate
```

## Tech stack

- **Python 3.12**
- **Streamlit 1.57.0** — the entire web framework
- **Plotly 6.7.0** — the post-game 4-panel chart
- **stdlib only** for the simulation engine (no NumPy, no pandas — 4 stations × 36 weeks is plain Python territory)

## Cold-start note

The free Streamlit Community Cloud tier sleeps the container after a stretch of no traffic. The first request after a sleep takes around 30 seconds to wake up — you'll see a "Yes, get this app back up!" prompt or a loading spinner. After the wake-up, the app runs at full speed for the rest of the day.

## Credits

- **John Sterman**, *Modeling Managerial Behavior: Misperception of Feedback in a Dynamic Decision-Making Experiment*, *Management Science* 35(3), 1989 — the source of the four-station structure, the empirical anchor-and-adjust heuristic, and the canonical parameter set (α ≈ 0.26, β ≈ 0.34, θ ≈ 0.36, S′ ≈ 17).
- **MIT Sloan** — the source of the canonical costs (\$0.50 / \$1.00 per case per week), initial inventory (12), step demand (4 → 8 at week 5), and 36-week game length. See <https://web.mit.edu/jsterman/www/SDG/beergame.html>.
