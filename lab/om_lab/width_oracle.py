"""Independent oracle for primal-graph elimination width.

This module deliberately does **not** import ``width_features``. It
re-implements the primal-graph construction and the elimination-width
computation from the definitions in ``docs/phase3/DISCOVERY_ROUND_01.md``
Section 3.3, so it can be used to check the implementation it is meant
to audit.

Provides:

* ``primal_graph_from_clauses`` -- independent primal-graph builder.
* ``elimination_width_for_order`` -- width of one specific elimination order.
* ``exact_min_elimination_width_from_graph`` -- exact minimum width by
  brute-force enumeration of all orderings (small graphs only).
* ``exact_min_elimination_width`` -- convenience wrapper taking clauses.
* ``is_valid_elimination_order`` -- permutation check.
* ``replay_elimination_order_independent`` -- replay an order and return
  its width, independent of ``width_features.replay_elimination_order``.
* ``validate_min_fill_result`` -- check a ``MinFillResult``-like object
  against the oracle: valid ordering, replay matches reported width, and
  reported width is at least the exact minimum.

Claim level for every function here: **Proved (code reading)** for the
algorithmic properties. Any empirical claim (that the oracle actually
produces the expected number on a fixture) requires running the tests.

Usage::

    from om_lab.width_oracle import (
        exact_min_elimination_width,
        elimination_width_for_order,
        is_valid_elimination_order,
        replay_elimination_order_independent,
        validate_min_fill_result,
    )
"""
from __future__ import annotations

from itertools import permutations
from typing import Sequence

__all__ = [
    "primal_graph_from_clauses",
    "elimination_width_for_order",
    "exact_min_elimination_width_from_graph",
    "exact_min_elimination_width",
    "is_valid_elimination_order",
    "replay_elimination_order_independent",
    "validate_min_fill_result",
]


# Brute-force cap.  8! = 40320 permutations; 9! ~ 363k; 10! ~ 3.6M.
# The cap is a guard, not a claim about what is feasible with more time.
DEFAULT_MAX_N_FOR_BRUTE_FORCE = 8


def primal_graph_from_clauses(
    n_vars: int, clauses: Sequence[Sequence[int]]
) -> dict[int, set[int]]:
    """Independent primal-graph builder.

    Vertices are ``1..n_vars`` (all present, even if isolated).  Two
    distinct variables are adjacent iff they occur together in at least
    one clause.  Literal signs are ignored; repeated literals in one
    clause do not create a self-loop.
    """
    if n_vars < 0:
        raise ValueError("n_vars must be non-negative")
    adj: dict[int, set[int]] = {v: set() for v in range(1, n_vars + 1)}
    for clause in clauses:
        vars_in_clause: set[int] = set()
        for lit in clause:
            v = abs(lit)
            if v == 0 or v > n_vars:
                raise ValueError(
                    f"literal {lit} out of range for n_vars={n_vars}"
                )
            vars_in_clause.add(v)
        for u in vars_in_clause:
            for w in vars_in_clause:
                if u != w:
                    adj[u].add(w)
    return adj


def elimination_width_for_order(
    adj: dict[int, set[int]], order: Sequence[int]
) -> int:
    """Width of one specific elimination order on ``adj``.

    The width is the maximum, over the whole elimination, of the degree
    of the eliminated vertex in the *current* graph (fill edges from
    earlier eliminations included).  Fill edges among the eliminated
    vertex's neighbours are added *after* the eliminated vertex's degree
    is recorded -- exactly the convention in
    ``width_features.replay_elimination_order``.
    """
    work: dict[int, set[int]] = {v: set(adj[v]) for v in adj}
    width = 0
    for v in order:
        if v not in work:
            raise ValueError(
                f"elimination order contains {v!r}, not a vertex of the graph"
            )
        width = max(width, len(work[v]))
        neighbours = list(work[v])
        for i in range(len(neighbours)):
            for j in range(i + 1, len(neighbours)):
                work[neighbours[i]].add(neighbours[j])
                work[neighbours[j]].add(neighbours[i])
        for u in neighbours:
            work[u].discard(v)
        del work[v]
    if work:
        raise ValueError(
            f"elimination order left vertices {sorted(work)} uneliminated"
        )
    return width


def exact_min_elimination_width_from_graph(
    adj: dict[int, set[int]],
    max_n: int = DEFAULT_MAX_N_FOR_BRUTE_FORCE,
) -> tuple[int, tuple[int, ...]]:
    """Exact minimum elimination width by brute-force enumeration.

    Returns ``(min_width, one_optimal_ordering)``.  Raises ``ValueError``
    if the graph has more than ``max_n`` vertices (raise ``max_n`` at
    your own risk -- the cost is factorial).
    """
    vertices = sorted(adj)
    n = len(vertices)
    if n == 0:
        return 0, ()
    if n > max_n:
        raise ValueError(
            f"brute-force enumeration refused for {n} vertices "
            f"(max_n={max_n}); factorial cost"
        )
    best_width: int | None = None
    best_order: tuple[int, ...] | None = None
    for perm in permutations(vertices):
        w = elimination_width_for_order(adj, perm)
        if best_width is None or w < best_width:
            best_width = w
            best_order = perm
    assert best_width is not None and best_order is not None
    return best_width, best_order


def exact_min_elimination_width(
    n_vars: int,
    clauses: Sequence[Sequence[int]],
    max_n: int = DEFAULT_MAX_N_FOR_BRUTE_FORCE,
) -> tuple[int, tuple[int, ...]]:
    """Convenience wrapper: exact minimum width for a CNF formula."""
    adj = primal_graph_from_clauses(n_vars, clauses)
    return exact_min_elimination_width_from_graph(adj, max_n=max_n)


def is_valid_elimination_order(n_vars: int, ordering: Sequence[int]) -> bool:
    """True iff ``ordering`` is a permutation of ``1..n_vars``."""
    return sorted(ordering) == list(range(1, n_vars + 1))


def replay_elimination_order_independent(
    n_vars: int,
    clauses: Sequence[Sequence[int]],
    ordering: Sequence[int],
) -> int:
    """Replay an elimination order and return its width.

    This is an independent code path from
    ``width_features.replay_elimination_order``: it rebuilds the primal
    graph with ``primal_graph_from_clauses`` (not
    ``width_features.primal_graph``) and computes the width with
    ``elimination_width_for_order``.  Raises ``ValueError`` unless
    ``ordering`` is a permutation of ``1..n_vars``.
    """
    if not is_valid_elimination_order(n_vars, ordering):
        raise ValueError(
            "ordering must be a permutation of 1..n_vars, "
            f"got {list(ordering)!r} for n_vars={n_vars}"
        )
    adj = primal_graph_from_clauses(n_vars, clauses)
    return elimination_width_for_order(adj, list(ordering))


def validate_min_fill_result(
    n_vars: int,
    clauses: Sequence[Sequence[int]],
    result,
    exact_max_n: int = DEFAULT_MAX_N_FOR_BRUTE_FORCE,
) -> dict:
    """Check a ``MinFillResult``-like object against the oracle.

    ``result`` must have ``width`` (int) and ``ordering`` (iterable of
    int).  Returns a dict with:

    * ``ordering_valid``: ``ordering`` is a permutation of ``1..n_vars``.
    * ``replay_width``: width of ``result.ordering`` replayed by the
      oracle (``None`` if the ordering is invalid).
    * ``reported_width``: ``result.width``.
    * ``replay_matches_reported``: ``replay_width == reported_width``.
    * ``exact_min_width``: exact minimum (``None`` if ``n_vars`` exceeds
      ``exact_max_n``).
    * ``heuristic_ge_exact``: ``reported_width >= exact_min_width``
      (``None`` if exact is unavailable).
    * ``ok``: conjunction of the checks that are available.
    """
    ordering = list(result.ordering)
    reported = int(result.width)
    ordering_valid = is_valid_elimination_order(n_vars, ordering)
    replay_width: int | None = None
    if ordering_valid:
        replay_width = replay_elimination_order_independent(
            n_vars, clauses, ordering
        )
    replay_matches = replay_width is not None and replay_width == reported
    exact_width: int | None = None
    heuristic_ge_exact: bool | None = None
    if n_vars <= exact_max_n:
        exact_width, _ = exact_min_elimination_width(
            n_vars, clauses, max_n=exact_max_n
        )
        heuristic_ge_exact = reported >= exact_width
    checks = [ordering_valid, replay_matches]
    if heuristic_ge_exact is not None:
        checks.append(heuristic_ge_exact)
    return {
        "ordering_valid": ordering_valid,
        "replay_width": replay_width,
        "reported_width": reported,
        "replay_matches_reported": replay_matches,
        "exact_min_width": exact_width,
        "heuristic_ge_exact": heuristic_ge_exact,
        "ok": all(checks),
    }
