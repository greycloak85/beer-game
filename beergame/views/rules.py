"""Rules + Bullwhip Primer screen (SETUP-01).

The first screen a first-time visitor sees. Explains the chain, the per-week
sequence, the visibility rules, the cost asymmetry, and the bullwhip effect
in ~200 words. A single primary CTA routes to setup.
"""
import streamlit as st


_PRIMER_BODY = """
You're one station in a four-station supply chain. Your job: order beer
from your supplier each week so you can ship to your customer next week.

### The chain

```
Customer  <--  Retailer  <--  Wholesaler  <--  Distributor  <--  Factory
            shipments flow downstream  (-->)
            orders flow upstream       (<--)
```

### Each week, every station does the same three things

1. **Receive** last week's shipment from upstream.
2. **Fill** orders from inventory. Whatever you can't ship becomes backlog
   (you still owe it next week).
3. **Place** one order upstream. **This is your only decision.**

### What you can see

Only **your** station: your inventory, your backlog, the shipment you just
received, the order you just received. You **do not** see other stations,
upstream pipelines, or future demand.

### Costs

- Holding inventory: **\\$0.50 per case per week**.
- Backlog (unfilled orders): **\\$1.00 per case per week**.

Note the asymmetry — over-ordering "feels safe" but pile-ups still cost real
money.

### The bullwhip

Small changes in customer demand amplify into large order swings the further
upstream you go. The Factory typically swings **2-4x harder** than the
Retailer. That's the bullwhip effect — and it's why most teams lose more
money than they expect.

### Your goal

Keep inventory near 12. Avoid stockouts. Avoid pile-ups. 36 weeks. One
decision per week. Good luck.
"""


def render(on_continue) -> None:
    """Render the Bullwhip Primer screen.

    Args:
        on_continue: callback invoked when the user clicks "Got it" —
            app.py binds this to ``go_to_setup``.
    """
    # Wide layout would stretch this text across the whole viewport (>70 chars
    # per line = eye strain). Constrain to the middle 60% so reading width
    # stays comfortable while the play view continues to use the full width.
    _, center, _ = st.columns([1, 3, 1])
    with center:
        st.title("🍺 Beer Game — Rules")
        st.markdown(_PRIMER_BODY)
        st.button(
            "Got it — set up my game",
            on_click=on_continue,
            type="primary",
            key="rules_continue_btn",
        )
