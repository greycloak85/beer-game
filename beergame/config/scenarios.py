"""Canonical Beer Game scenario constants (Sterman 1989 / MIT Sloan)."""
TOTAL_WEEKS: int = 36
CLASSIC_STEP_BREAK_WEEK: int = 4   # demand is PRE through week 4, POST from week 5
CLASSIC_PRE_STEP_DEMAND: int = 4
CLASSIC_POST_STEP_DEMAND: int = 8
INITIAL_INVENTORY: int = 12
INITIAL_BACKLOG: int = 0
EQUILIBRIUM_THROUGHPUT: int = 4    # pre-fills every pipeline slot
SHIPPING_PIPELINE_LEN: int = 2     # all four stations; 2-week shipment delay
ORDER_PIPELINE_LEN_RWD: int = 1    # 1-week mailing delay for R/W/D
# Factory's INBOUND order channel (orders FROM Distributor) uses the same canonical
# 1-week mailing delay as R/W/D. The phrase "no order delay at Factory" in the
# Sterman literature refers ONLY to Factory's OWN order->production path:
# Factory's placed order goes immediately into its own incoming_shipments queue
# (skipping the order-mailing channel entirely) where it sits for SHIPPING_PIPELINE_LEN
# weeks of production lead time. The Distributor->Factory order channel is unchanged
# from the canonical R/W/D pattern.
ORDER_PIPELINE_LEN_FACTORY: int = 1
RECENT_ORDERS_WINDOW: int = 4      # number of past weeks the StationView exposes
DEFAULT_SEED: int = 42
