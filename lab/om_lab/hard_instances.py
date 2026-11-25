"""Adversarial and hard CNF instance generators for Phase 2 stress tests.

All generators are deterministic: no global RNG state, fixed seeds where randomness
is needed, and canonical variable numbering.

Claim levels (see docs/RULES.md):

- ``generate_php(n)``: the CNF encoding of PHP_n^(n+1). The family is
  **Proved** unsatisfiable for every n (Haken, 1985, Theoret. Comput. Sci. 39,
  297-308). The generator itself is a construction; the tests only empirically
  confirm UNSAT for small n, which is an **Empirical Observation**.
- ``generate_tseitin_3sat(..., charge_pattern="unsat")``: a 3-CNF Tseitin
  parity formula on a connected 3-regular graph. Odd total charge implies
  **Proved** unsatisfiability (standard parity argument).
- Planted 3-SAT and complete-graph colouring are satisfiable by construction;
  their witnesses are verified by ``om_lab.solvers.verify_cnf_assignment``.

This module never asserts a complexity separation. Timings and decision counts
are **Empirical Observations** only.
"""

from __future__ import annotations

import random
from typing import Sequence

from .generators import CNFInstance

__all__ = [
    "generate_php",
    "generate_tseitin_3sat",
    "generate_planted_3sat",
    "generate_complete_graph_coloring",
]


# ---------------------------------------------------------------------------
# Pigeonhole principle PHP_n^(n+1)
# ---------------------------------------------------------------------------

def generate_php(n: int) -> CNFInstance:
    """Return the standard CNF encoding of PHP_n^(n+1).

    n holes, n+1 pigeons.  Variable ``x_{i,j}`` (1-indexed) means pigeon i
    sits in hole j.  Clauses:

    * each pigeon sits in at least one hole (length-n clauses);
    * each hole contains at most one pigeon (binary clauses).

    The formula is **Proved** unsatisfiable for every n (Haken 1985).  This
    function merely constructs the canonical encoding.
    """
    if n < 1:
        raise ValueError("n must be >= 1")
    n_pigeons = n + 1
    n_holes = n

    def var(pigeon: int, hole: int) -> int:
        return pigeon * n_holes + hole + 1

    clauses: list[list[int]] = []
    # At least one hole per pigeon.
    for p in range(n_pigeons):
        clauses.append([var(p, h) for h in range(n_holes)])
    # At most one pigeon per hole.
    for h in range(n_holes):
        for p1 in range(n_pigeons):
            for p2 in range(p1 + 1, n_pigeons):
                clauses.append([-var(p1, h), -var(p2, h)])

    return CNFInstance(
        n_vars=n_pigeons * n_holes,
        clauses=clauses,
        metadata={
            "family": "PHP",
            "n_holes": n_holes,
            "n_pigeons": n_pigeons,
            "claim_level": "Proved (Haken 1985)",
        },
    )


# ---------------------------------------------------------------------------
# Tseitin parity formulas encoded in strict 3-CNF
# ---------------------------------------------------------------------------

def _tseitin_mobius_edges(n_vertices: int) -> list[tuple[int, int]]:
    """Deterministic 3-regular Möbius-ladder graph on an even number of vertices."""
    if n_vertices < 4 or n_vertices % 2 != 0:
        raise ValueError("n_vertices must be even and >= 4")
    edges: list[tuple[int, int]] = []
    # Cycle.
    for i in range(n_vertices):
        edges.append((i, (i + 1) % n_vertices))
    # Perfect matching across the ladder.
    half = n_vertices // 2
    for i in range(half):
        edges.append((i, i + half))
    # Canonical order.
    return sorted(set(edges))


def _xor3_clauses(a: int, b: int, c: int, rhs: int) -> list[list[int]]:
    """Strict 3-CNF encoding of ``a XOR b XOR c = rhs``."""
    if rhs == 1:
        return [[a, b, c], [a, -b, -c], [-a, b, -c], [-a, -b, c]]
    if rhs == 0:
        return [[-a, -b, -c], [-a, b, c], [a, -b, c], [a, b, -c]]
    raise ValueError("rhs must be 0 or 1")


def generate_tseitin_3sat(
    n_vertices: int,
    charge_pattern: str = "unsat",
) -> CNFInstance:
    """Tseitin parity formula on a 3-regular Möbius ladder, encoded in 3-CNF.

    Edge variables ``x_e`` are 1-indexed.  For every vertex v we enforce

        XOR_{e incident to v} x_e = charge(v).

    For a connected graph, the formula is **Proved** satisfiable iff the sum
    of charges is even modulo 2.  ``charge_pattern``:

    * ``"unsat"``: one vertex charge 1, all others 0 -> odd total -> UNSAT;
    * ``"sat"``: all charges 0 -> satisfiable;
    * ``"sat_two"``: two vertices charge 1, all others 0 -> satisfiable.

    This is a genuine 3-CNF encoding: every vertex has degree 3, so each parity
    constraint is written with four clauses of width 3.
    """
    edges = _tseitin_mobius_edges(n_vertices)
    edge_to_var = {edge: idx + 1 for idx, edge in enumerate(edges)}
    n_vars = len(edges)

    if charge_pattern == "unsat":
        charges = [1] + [0] * (n_vertices - 1)
    elif charge_pattern == "sat":
        charges = [0] * n_vertices
    elif charge_pattern == "sat_two":
        charges = [1, 1] + [0] * (n_vertices - 2)
    else:
        raise ValueError("charge_pattern must be 'unsat', 'sat', or 'sat_two'")

    clauses: list[list[int]] = []
    for v in range(n_vertices):
        incident = sorted(edge_to_var[e] for e in edges if v in e)
        if len(incident) != 3:
            raise ValueError("Möbius ladder is not 3-regular for this n_vertices")
        clauses.extend(_xor3_clauses(*incident, charges[v]))

    return CNFInstance(
        n_vars=n_vars,
        clauses=clauses,
        metadata={
            "family": "Tseitin",
            "n_vertices": n_vertices,
            "charge_pattern": charge_pattern,
            "claim_level": "Proved for parity; Empirical Observation for solver behaviour",
        },
    )


# ---------------------------------------------------------------------------
# Planted / forced-satisfiable 3-SAT
# ---------------------------------------------------------------------------

def generate_planted_3sat(
    n_vars: int,
    n_clauses: int,
    seed: int = 0,
) -> CNFInstance:
    """Planted 3-SAT: a hidden assignment satisfies every clause.

    The instance is satisfiable by construction.  It is a **forced-satisfiable**
    family useful for checking that a solver does not falsely report UNSAT.
    Claim level for satisfiability: **Proved** by construction; solver
    behaviour is an **Empirical Observation**.
    """
    if n_vars < 3:
        raise ValueError("n_vars must be >= 3")
    rng = random.Random(seed)
    hidden = {v: rng.choice([True, False]) for v in range(1, n_vars + 1)}
    clauses: list[list[int]] = []
    for _ in range(n_clauses):
        chosen = rng.sample(range(1, n_vars + 1), 3)
        clause: list[int] = []
        for v in chosen:
            if rng.random() < 0.5:
                clause.append(v if hidden[v] else -v)
            else:
                clause.append(-v if hidden[v] else v)
        clauses.append(clause)

    return CNFInstance(
        n_vars=n_vars,
        clauses=clauses,
        metadata={
            "family": "planted_3sat",
            "seed": seed,
            "hidden_assignment": {str(k): bool(v) for k, v in hidden.items()},
            "claim_level": "Proved satisfiable by construction",
        },
    )


# ---------------------------------------------------------------------------
# Tricky graph-colouring edge case
# ---------------------------------------------------------------------------

def generate_complete_graph_coloring(k: int) -> CNFInstance:
    """k-colouring of K_k: satisfiable, but colour choices are highly symmetric.

    K_k is k-colourable, and every colouring uses all k colours.  A naive DPLL
    may explore many symmetric permutations.  Satisfiability is **Proved**;
    solver effort is an **Empirical Observation**.
    """
    if k < 1:
        raise ValueError("k must be >= 1")
    n_vertices = k

    def var(vertex: int, color: int) -> int:
        return vertex * k + color + 1

    clauses: list[list[int]] = []
    # Each vertex gets at least one colour.
    for v in range(n_vertices):
        clauses.append([var(v, c) for c in range(k)])
    # Each vertex gets at most one colour.
    for v in range(n_vertices):
        for c1 in range(k):
            for c2 in range(c1 + 1, k):
                clauses.append([-var(v, c1), -var(v, c2)])
    # Adjacent vertices (all pairs in K_k) differ.
    for u in range(n_vertices):
        for v in range(u + 1, n_vertices):
            for c in range(k):
                clauses.append([-var(u, c), -var(v, c)])

    return CNFInstance(
        n_vars=n_vertices * k,
        clauses=clauses,
        metadata={
            "family": "complete_graph_coloring",
            "k": k,
            "n_vertices": n_vertices,
            "claim_level": "Proved satisfiable (K_k is k-colourable)",
        },
    )

