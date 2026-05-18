"""Agent protocol + the ``ConstantOrderAgent`` test helper.

The protocol is runtime-checkable so ``isinstance(obj, Agent)`` works for any
object that exposes ``decide_order(view) -> int``. Plan 02 adds the Sterman
agent; Plan 03's GATE 1 uses ``ConstantOrderAgent(4)`` everywhere to assert
that the engine itself is in canonical equilibrium independent of any
behavioral heuristic.

``StationView`` is referenced only in type annotations, so it is imported
under ``TYPE_CHECKING`` to avoid a circular import (engine.tick imports
``Agent`` from this module, and engine/__init__.py re-exports tick).
"""
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from beergame.engine.state import StationView


@runtime_checkable
class Agent(Protocol):
    """Order-placing agent. Sees only its own ``StationView``.

    Returns a non-negative integer order quantity for this week.
    """
    def decide_order(self, view: "StationView") -> int: ...


class ConstantOrderAgent:
    """Always orders the same quantity. Used in the equilibrium regression test
    (Plan 03 GATE 1). With ``ConstantOrderAgent(4)`` at every station and
    constant customer demand=4, the engine MUST stay at inventory=12, backlog=0
    for all 36 weeks — that is the canonical engine-correctness check
    independent of any Sterman heuristic behavior.
    """
    def __init__(self, quantity: int):
        self.quantity = int(quantity)

    def decide_order(self, view: "StationView") -> int:
        return self.quantity
