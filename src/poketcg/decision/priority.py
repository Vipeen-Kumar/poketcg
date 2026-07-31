"""Rule ordering helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from heapq import heappop, heappush
from typing import Protocol

from .exceptions import CircularPriorityError, DecisionConfigurationError


DEFAULT_ALWAYS_END_TURN_PRIORITY = 300
DEFAULT_FIRST_LEGAL_ACTION_PRIORITY = 200
DEFAULT_FALLBACK_PRIORITY = -1000


class RuleOrderable(Protocol):
    """Minimal protocol required to sort rules."""

    name: str
    priority: int
    runs_before: tuple[str, ...]
    runs_after: tuple[str, ...]


def sort_rules(
    rules: Sequence[RuleOrderable],
    *,
    priority_overrides: Mapping[str, int] | None = None,
) -> tuple[RuleOrderable, ...]:
    """Return rules ordered by priority while respecting dependencies."""

    overrides = dict(priority_overrides or {})
    rule_map = {rule.name: rule for rule in rules}
    if len(rule_map) != len(rules):
        raise DecisionConfigurationError("Duplicate rule names cannot be ordered.")

    edges: dict[str, set[str]] = {name: set() for name in rule_map}
    in_degree: dict[str, int] = {name: 0 for name in rule_map}

    for rule in rules:
        for target in rule.runs_before:
            if target not in rule_map:
                raise DecisionConfigurationError(f"Rule {rule.name} references unknown dependency {target}.")
            if target not in edges[rule.name]:
                edges[rule.name].add(target)
                in_degree[target] += 1
        for source in rule.runs_after:
            if source not in rule_map:
                raise DecisionConfigurationError(f"Rule {rule.name} references unknown dependency {source}.")
            if rule.name not in edges[source]:
                edges[source].add(rule.name)
                in_degree[rule.name] += 1

    ready: list[tuple[int, str]] = []
    for name, degree in in_degree.items():
        if degree == 0:
            priority = overrides.get(name, rule_map[name].priority)
            heappush(ready, (-priority, name))

    ordered: list[RuleOrderable] = []
    while ready:
        _, name = heappop(ready)
        ordered.append(rule_map[name])
        for target in edges[name]:
            in_degree[target] -= 1
            if in_degree[target] == 0:
                priority = overrides.get(target, rule_map[target].priority)
                heappush(ready, (-priority, target))

    if len(ordered) != len(rules):
        raise CircularPriorityError("Rule ordering contains a circular dependency.")

    return tuple(ordered)
