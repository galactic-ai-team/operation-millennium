"""Deterministic primal-graph min-fill elimination width.

Implements the exact width proxy from Section 3.3 of
``docs/phase3/DISCOVERY_ROUND_01.md`` (preregistration OM-C001-R2):

* the primal graph is the variable co-occurrence graph of the original
  CNF -- all ``n`` declared variables are vertices (including isolated
  ones), distinct variables are adjacent when they occur in the same
  clause, literal signs are ignored, duplicate edges are ignored, and
  the formula is not simplified before extraction;
* at each step the vertex minimising ``(fill(v), variable_id(v))`` is
  eliminated, where ``fill(v)`` is the number of unordered pairs of
  distinct neighbours of ``v`` that are not currently adjacent;
* the width ``W`` is the maximum degree of an eliminated vertex, over
  the whole elimination (fill edges are added as the elimination
  proceeds).

The returned width is a deterministic heuristic upper bound on primal
treewidth. It is **not** an exact treewidth algorithm, and it is **not**
a graph invariant: the numerical tie-break means a relabelling of the
variables can change the selected ordering (and, in principle, the
width). Relabelling sensitivity is tested separately; see
``lab/tests/test_width_features.py``.

No solver outcome, label, or test-set information is used anywhere in
this module. The only inputs are the formula's variables and clauses.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from om_lab.generators import CNFInstance

__all__ = [
    "MinFillResult",
    "primal_graph",
    "primal_min_fill_width",
    "primal_min_fill_width_from_graph",
    "replay_elimination_order",
]


@dataclass(frozen=True)
class MinFillResult:
    """Result of deterministic min-fill elimination."""

    width: int
    ordering: tuple[int, ...]


def primal_graph(
    n_vars: int, clauses: Sequence[Sequence[int]]
) -> dict[int, set[int]]:
    """Build the primal (variable co-occurrence) graph.

    Vertices are the declared variables ``1..n_vars``; every variable
    is present even if it occurs in no clause. Two distinct variables
    are adjacent when they occur together in at least one clause.
    Literal signs, clause order, and duplicate clauses do not affect
    the result.
    """
    if n_vars < 0:
        raise ValueError("n_vars must be non-negative")
    adj: dict[int, set[int]] = {v: set() for v in range(1, n_vars + 1)}
    for clause in clauses:
        vs = {abs(lit) for lit in clause}
        for lit in clause:
            if lit == 0 or abs(lit) > n_vars:
                raise ValueError(
                    f"literal {lit} out of range for n_vars={n_vars}"
                )
        for u in vs:
            adj[u].update(vs - {u})
    return adj


def _fill_count(adj: dict[int, set[int]], v: int) -> int:
    """Number of non-adjacent unordered neighbour pairs of ``v``."""
    neighbours = sorted(adj[v])
    count = 0
    for i, a in enumerate(neighbours):
        for b in neighbours[i + 1:]:
            if b not in adj[a]:
                count += 1
    return count


def primal_min_fill_width_from_graph(
    adj: dict[int, set[int]],
) -> MinFillResult:
    """Deterministic min-fill elimination on an explicit adjacency map.

    The input map is copied; the caller's graph is not modified.
    """
    remaining = set(adj)
    # Copy so elimination (fill edges + removals) never mutates the input.
    work: dict[int, set[int]] = {v: set(adj[v]) for v in adj}
    width = 0
    ordering: list[int] = []
    while remaining:
        # Smallest (fill, variable_id); variable_id is the 1-indexed
        # DIMACS id, exactly as specified in Section 3.3.
        v = min(remaining, key=lambda x: (_fill_count(work, x), x))
        width = max(width, len(work[v]))
        neighbours = sorted(work[v])
        for i, a in enumerate(neighbours):
            for b in neighbours[i + 1:]:
                work[a].add(b)
                work[b].add(a)
        for u in neighbours:
            work[u].discard(v)
        del work[v]
        remaining.remove(v)
        ordering.append(v)
    return MinFillResult(width=width, ordering=tuple(ordering))


def primal_min_fill_width(
    n_vars: int, clauses: Sequence[Sequence[int]]
) -> MinFillResult:
    """Min-fill width and elimination ordering for a CNF formula."""
    return primal_min_fill_width_from_graph(primal_graph(n_vars, clauses))


def replay_elimination_order(
    n_vars: int,
    clauses: Sequence[Sequence[int]],
    ordering: Sequence[int],
) -> int:
    """Independently replay an elimination ordering and return its width.

    This is a separate code path from the min-fill *selection* logic:
    it takes the ordering as given, rebuilds the primal graph from the
    clauses, eliminates vertices in that order (adding the same fill
    edges), and returns the maximum eliminated-vertex degree. It raises
    :class:`ValueError` unless ``ordering`` is a permutation of
    ``1..n_vars``.

    Use it to verify a reported width: for a correct
    :func:`primal_min_fill_width` result,
    ``replay_elimination_order(n, clauses, result.ordering)`` must equal
    ``result.width``.
    """
    order = list(ordering)
    if sorted(order) != list(range(1, n_vars + 1)):
        raise ValueError(
            "ordering must be a permutation of 1..n_vars, "
            f"got {order!r} for n_vars={n_vars}"
        )
    adj = primal_graph(n_vars, clauses)
    width = 0
    for v in order:
        width = max(width, len(adj[v]))
        neighbours = sorted(adj[v])
        for i, a in enumerate(neighbours):
            for b in neighbours[i + 1:]:
                adj[a].add(b)
                adj[b].add(a)
        for u in neighbours:
            adj[u].discard(v)
        del adj[v]
    return width


def min_fill_width(instance: CNFInstance) -> MinFillResult:
    """Min-fill width and elimination ordering for a :class:`CNFInstance`."""
    return primal_min_fill_width(instance.n_vars, instance.clauses)
