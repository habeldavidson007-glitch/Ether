"""Autonomy control-plane primitives for incremental rollout.

This module is intentionally small and deterministic so Ether can evolve toward
more autonomy without destabilizing the existing user-driven pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from heapq import heappop, heappush
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass(order=True)
class Task:
    """Priority task with FIFO tie-break based on insertion order."""

    sort_index: Tuple[int, int] = field(init=False, repr=False)
    priority: int
    sequence: int
    task_id: str
    kind: str
    payload: Dict[str, Any]

    def __post_init__(self) -> None:
        # lower number => higher priority
        self.sort_index = (self.priority, self.sequence)


class TaskQueue:
    """Minimal priority queue used for future background scheduling."""

    def __init__(self) -> None:
        self._heap: List[Task] = []
        self._sequence = 0

    def enqueue(self, task_id: str, kind: str, payload: Dict[str, Any], priority: int = 5) -> Task:
        task = Task(
            priority=priority,
            sequence=self._sequence,
            task_id=task_id,
            kind=kind,
            payload=payload,
        )
        self._sequence += 1
        heappush(self._heap, task)
        return task

    def dequeue(self) -> Optional[Task]:
        if not self._heap:
            return None
        return heappop(self._heap)

    def size(self) -> int:
        return len(self._heap)


class SafetyBudget:
    """Simple budget policy for autonomous task execution."""

    def __init__(self, max_units: int = 10) -> None:
        self.max_units = max_units
        self.used_units = 0

    def can_spend(self, units: int) -> bool:
        return units >= 0 and self.used_units + units <= self.max_units

    def spend(self, units: int) -> bool:
        if not self.can_spend(units):
            return False
        self.used_units += units
        return True

    def remaining(self) -> int:
        return self.max_units - self.used_units

    def reset(self) -> None:
        self.used_units = 0


def planner_executor_critic_cycle(
    task: Task,
    planner: Callable[[Task], Dict[str, Any]],
    executor: Callable[[Dict[str, Any]], Dict[str, Any]],
    critic: Callable[[Dict[str, Any]], Dict[str, Any]],
    max_retries: int = 1,
) -> Dict[str, Any]:
    """Run a bounded planner -> executor -> critic cycle.

    Returns structured output for logging/auditing and future scheduling hooks.
    """

    attempt = 0
    history: List[Dict[str, Any]] = []

    plan = planner(task)
    while attempt <= max_retries:
        execution = executor(plan)
        review = critic(execution)
        history.append({"attempt": attempt + 1, "execution": execution, "review": review})

        if review.get("approved", False):
            return {
                "task_id": task.task_id,
                "status": "approved",
                "attempts": attempt + 1,
                "history": history,
            }

        attempt += 1
        if attempt <= max_retries:
            # planner can incorporate critic feedback in next cycle
            plan = planner(task)

    return {
        "task_id": task.task_id,
        "status": "rejected",
        "attempts": attempt,
        "history": history,
    }
