"""Static narrative templates for the post-game debrief (DEB-05).

Four templates — one per player ``Role`` — written ≤180 words pre-interpolation
so they stay ≤200 words after numeric interpolation (see 03-RESEARCH.md
Pitfall 4). Each template names the bullwhip explicitly and points at where
it shows up in the player's specific game.

Format placeholders used at interpolation time:

- ``{ratio:.1f}`` — overall variance bullwhip ratio (Factory ÷ customer).
- ``{your_ratio:.1f}`` — this station's per-echelon amplification.
- ``{factory_ratio:.1f}`` — Factory's per-echelon amplification.
- ``{cost:,.0f}`` — this station's cumulative cost. The ``$`` literal in the
  prose is escaped as ``\\$`` so Streamlit does NOT interpret it as a LaTeX
  delimiter. KEEP the backslash — removing it makes Streamlit eat everything
  between the two dollar signs as math.
- ``{retailer_peak}`` and ``{factory_peak}`` — peak orders at Retailer and
  Factory (Retailer template only; the Wholesaler/Distributor/Factory
  templates lean on the variance ratios instead).

Determinism is required: same ``GameState`` → same string. No LLM, no random
selection, no time-dependent text. The unit tests in
``tests/test_narrative.py`` enforce determinism, ≤200-word ceiling, the
literal ``"bullwhip"`` mention, the role name appearing, and at least one
markdown ``**bold**`` span.
"""
from beergame.engine.state import Role


_TEMPLATES: dict[Role, str] = {
    Role.RETAILER: (
        "You played the **Retailer** — closest to the customer. Demand "
        "stepped from 4 to 8 at week 5 (a small jump), but watch what "
        "happened upstream: your orders peaked at {retailer_peak} units, "
        "the Factory's peaked at {factory_peak}. Across the chain, the "
        "variance of orders amplified **{ratio:.1f}×** from customer "
        "demand to Factory production starts. That amplification is the "
        "**bullwhip effect** — and you saw the start of it. Even though "
        "you saw the real demand, the lag in shipments meant you "
        "over-corrected once the step hit. Total cost at your station: "
        "**\\${cost:,.0f}**. Try playing the Factory next — the same "
        "demand shock arrives 4 weeks late and looks twice as violent. "
        "That's the lesson: small noise at the bottom of the chain "
        "becomes a crisis at the top."
    ),
    Role.WHOLESALER: (
        "You played the **Wholesaler** — one step removed from the "
        "customer. You never saw customer demand; you only saw the "
        "Retailer's orders. When the Retailer reacted to the week-5 "
        "step, their order spike arrived at your door with a one-week "
        "mailing delay, and you had to decide whether it was real or "
        "noise. The variance amplification from customer demand to your "
        "orders was **{your_ratio:.1f}×**; the Factory saw "
        "**{factory_ratio:.1f}×**. Your station's total cost: "
        "**\\${cost:,.0f}**. This is the **bullwhip effect**: each "
        "echelon amplifies the signal it sees, because nobody can tell "
        "signal from noise without looking downstream. The only fix is "
        "information sharing — the whole chain seeing the same customer "
        "demand. Try playing the Factory next and feel how the "
        "amplification stacks."
    ),
    Role.DISTRIBUTOR: (
        "You played the **Distributor** — two steps removed from the "
        "customer. The customer-demand step (4 → 8 at week 5) reached "
        "you only after the Retailer reacted, then the Wholesaler "
        "reacted, and then their order showed up at your dock. The "
        "variance amplification from customer demand to your orders was "
        "**{your_ratio:.1f}×**; the Factory saw **{factory_ratio:.1f}×**. "
        "Your total cost: **\\${cost:,.0f}**. This is the **bullwhip "
        "effect**: by the time a small real change reaches you, it's "
        "already amplified, and your response amplifies it again before "
        "sending it to the Factory. Look at the 4-panel chart — your "
        "orders curve overshoots more than the Wholesaler's and less "
        "than the Factory's. That monotonic growth upstream is the "
        "canonical bullwhip signature. The whole chain saw exactly "
        "**one** demand change."
    ),
    Role.FACTORY: (
        "You played the **Factory** — at the top of the chain. Every "
        "order you saw was already amplified twice: by the Retailer "
        "reacting to a demand step, by the Wholesaler reacting to the "
        "Retailer's reaction, and by the Distributor reacting to the "
        "Wholesaler's. The variance of your production starts was "
        "**{your_ratio:.1f}×** the variance of actual customer demand — "
        "which only changed once, in week 5. Your total cost: "
        "**\\${cost:,.0f}**. This is the **bullwhip effect** in its "
        "purest form: a one-time, small change in customer demand "
        "becomes a violent swing in factory production. It's not your "
        "fault — it's structural. The only ways to dampen it are "
        "shorter lead times or sharing the customer-demand signal "
        "across the whole chain. Try playing the Retailer next — same "
        "demand, same opponents, but you'll see how much smaller the "
        "swing looks from where the customer sits."
    ),
}
