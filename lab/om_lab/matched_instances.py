# lab/om_lab/matched_instances.py
"""Matched Tseitin structural counterexample suite.

Claim levels
------------
- Tseitin parity criterion on connected graphs: **Proved** (standard GF(2)
  incidence argument: each edge variable appears exactly twice in the sum of
  vertex equations, so total charge must be even).
- Per-component parity criterion on disconnected graphs: **Proved** by applying
  the same argument separately to each connected component.
- All-zero witness for an all-zero-charge connected instance: **Proved** by
  construction.
- Balanced positive/negative occurrence counts in the cubic XOR3 encoding:
  **Proved** by counting, and checked empirically by tests.
- Min-fill width estimates and solver effort: **Empirical Observation** only.
  The min-fill number is a heuristic upper-bound proxy, not exact treewidth.

This module deliberately includes validators that reject malformed structures.
The rejection behaviour is a code contract, checked by pytest; it is not a new
mathematical theorem.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

Edge = tuple[int, int]


# ---------------------------------------------------------------------------
# Basic graph representation
# ---------------------------------------------------------------------------

def canonical_edge(u: int, v: int) -> Edge:
    """Return an undirected edge with the smaller endpoint first."""
    return (u, v) if u <= v else (v, u)


def normalize_edges(edges: Iterable[Edge]) -> tuple[Edge, ...]:
    """Canonicalise and sort edges without deduplicating invalid input."""
    return tuple(sorted(canonical_edge(u, v) for u, v in edges))


@dataclass(frozen=True)
class SimpleGraph:
    """A simple graph container that allows invalid instances for negative tests."""

    n_vertices: int
    edges: tuple[Edge, ...]

    def unsigned_signature(self) -> tuple[int, tuple[Edge, ...]]:
        """Unsigned graph representation used for matched-pair equality checks."""
        return (
            self.n_vertices,
            tuple(sorted(canonical_edge(u, v) for u, v in self.edges)),
        )


def k4() -> SimpleGraph:
    return SimpleGraph(
        4,
        normalize_edges(
            [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
        ),
    )


def k33() -> SimpleGraph:
    return SimpleGraph(
        6,
        normalize_edges([(i, 3 + j) for i in range(3) for j in range(3)]),
    )


def prism_graph(n: int) -> SimpleGraph:
    """Triangular prism generalisation: two n-cycles joined by a matching."""
    if n < 3:
        raise ValueError("prism_graph requires n >= 3")
    edges: list[Edge] = []
    for i in range(n):
        edges.append((i, (i + 1) % n))
        edges.append((n + i, n + ((i + 1) % n)))
        edges.append((i, n + i))
    return SimpleGraph(2 * n, normalize_edges(edges))


def moebius_ladder(n: int) -> SimpleGraph:
    """Möbius ladder on 2n vertices: a 2n-cycle plus opposite matching."""
    if n < 3:
        raise ValueError("moebius_ladder requires n >= 3")
    total = 2 * n
    edges: list[Edge] = []
    for i in range(total):
        edges.append((i, (i + 1) % total))
    for i in range(n):
        edges.append((i, i + n))
    return SimpleGraph(total, normalize_edges(edges))


def petersen_graph() -> SimpleGraph:
    # Outer 5-cycle, inner 5-star, and spokes.
    edges: list[Edge] = [
        (0, 1), (1, 2), (2, 3), (3, 4), (4, 0),
        (5, 7), (7, 9), (9, 6), (6, 8), (8, 5),
        (0, 5), (1, 6), (2, 7), (3, 8), (4, 9),
    ]
    return SimpleGraph(10, normalize_edges(edges))


def connected_cubic_registry() -> dict[str, SimpleGraph]:
    """Small deterministic connected simple 3-regular comparison graphs."""
    return {
        "k4": k4(),
        "k33": k33(),
        "prism3": prism_graph(3),
        "moebius3": moebius_ladder(3),
        "petersen": petersen_graph(),
    }


# ---------------------------------------------------------------------------
# Validation and structural checks
# ---------------------------------------------------------------------------

def components(graph: SimpleGraph) -> tuple[tuple[int, ...], ...]:
    """Connected components as sorted vertex tuples."""
    n = graph.n_vertices
    adj: list[list[int]] = [[] for _ in range(n)]
    for u, v in graph.edges:
        if 0 <= u < n and 0 <= v < n:
            adj[u].append(v)
            adj[v].append(u)

    seen: set[int] = set()
    comps: list[tuple[int, ...]] = []
    for start in range(n):
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        comp: list[int] = []
        while stack:
            x = stack.pop()
            comp.append(x)
            for y in adj[x]:
                if y not in seen:
                    seen.add(y)
                    stack.append(y)
        comps.append(tuple(sorted(comp)))
    return tuple(comps)


def is_connected(graph: SimpleGraph) -> bool:
    if graph.n_vertices == 0:
        return True
    return len(components(graph)) == 1


def validate_incidence_multiplicities(
    graph: SimpleGraph,
    *,
    require_cubic: bool = True,
) -> tuple[tuple[int, ...], ...]:
    """Validate edge endpoints, self-loops, duplicate edges, and incidence counts."""
    n = graph.n_vertices
    if n < 0:
        raise ValueError("n_vertices must be non-negative")
    incidence: list[list[int]] = [[] for _ in range(n)]
    seen: set[Edge] = set()
    for idx, (u, v) in enumerate(graph.edges):
        if not (0 <= u < n and 0 <= v < n):
            raise ValueError("edge endpoint out of range")
        if u == v:
            raise ValueError("self-loop is not allowed")
        e = canonical_edge(u, v)
        if e in seen:
            raise ValueError("duplicate edge is not allowed")
        seen.add(e)
        incidence[u].append(idx)
        incidence[v].append(idx)

    for vertex, inc in enumerate(incidence):
        if len(set(inc)) != len(inc):
            raise ValueError("repeated incidence multiplicity")
        if require_cubic and len(inc) != 3:
            raise ValueError(
                f"vertex {vertex} has degree {len(inc)}, expected 3"
            )
    return tuple(tuple(inc) for inc in incidence)


def validate_graph(
    graph: SimpleGraph,
    *,
    require_connected: bool = True,
    require_cubic: bool = True,
) -> None:
    validate_incidence_multiplicities(graph, require_cubic=require_cubic)
    if require_connected and not is_connected(graph):
        raise ValueError("graph is not connected")


# ---------------------------------------------------------------------------
# Tseitin instances
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TseitinInstance:
    graph: SimpleGraph
    charges: tuple[int, ...]
    edge_ids: tuple[int, ...]
    n_vars: int
    clauses: tuple[tuple[int, ...], ...]
    metadata: dict


@dataclass(frozen=True)
class MatchedTseitinPair:
    graph: SimpleGraph
    even: TseitinInstance
    odd: TseitinInstance
    flipped_vertex: int


def xor3_clauses(a: int, b: int, c: int, rhs: int) -> tuple[tuple[int, ...], ...]:
    """Strict 3-CNF encoding of a XOR b XOR c = rhs."""
    variables = (a, b, c)
    if any(v <= 0 for v in variables):
        raise ValueError("XOR3 variables must be positive integer identifiers")
    if len(set(variables)) != 3:
        raise ValueError("XOR3 variables must be distinct")
    if rhs not in (0, 1):
        raise ValueError("XOR3 rhs must be 0 or 1")

    if rhs == 1:
        return (
            (a, b, c),
            (a, -b, -c),
            (-a, b, -c),
            (-a, -b, c),
        )
    return (
        (-a, -b, -c),
        (-a, b, c),
        (a, -b, c),
        (a, b, -c),
    )


def component_charge_parities(
    graph: SimpleGraph,
    charges: Sequence[int],
) -> tuple[tuple[tuple[int, ...], int], ...]:
    if len(charges) != graph.n_vertices:
        raise ValueError("charges length must equal n_vertices")
    if any(c not in (0, 1) for c in charges):
        raise ValueError("charges must be 0 or 1")

    out: list[tuple[tuple[int, ...], int]] = []
    for comp in components(graph):
        out.append((comp, sum(charges[v] for v in comp) % 2))
    return tuple(out)


def encode_tseitin(
    graph: SimpleGraph,
    charges: Sequence[int],
    edge_ids: Sequence[int] | None = None,
    metadata: Mapping[str, object] | None = None,
    *,
    validate: bool = True,
) -> TseitinInstance:
    """Encode a cubic Tseitin parity formula as strict 3-CNF.

    The graph need not be connected.  Parity satisfiability is checked
    per component by ``parity_obstruction``.
    """
    if validate:
        validate_graph(graph, require_connected=False, require_cubic=True)

    n = graph.n_vertices
    m = len(graph.edges)

    charges = tuple(charges)
    if len(charges) != n:
        raise ValueError("charges length must equal n_vertices")
    if any(c not in (0, 1) for c in charges):
        raise ValueError("charges must be 0 or 1")

    if edge_ids is None:
        edge_ids = tuple(range(1, m + 1))
    else:
        edge_ids = tuple(edge_ids)

    if len(edge_ids) != m:
        raise ValueError("edge_ids length must equal number of edges")
    if len(set(edge_ids)) != m:
        raise ValueError("repeated edge identifiers are not allowed")
    if any(edge_id <= 0 for edge_id in edge_ids):
        raise ValueError("edge identifiers must be positive")

    incidence = validate_incidence_multiplicities(graph, require_cubic=True)

    clauses: list[tuple[int, ...]] = []
    for vertex, incident_indices in enumerate(incidence):
        if len(incident_indices) != 3:
            raise ValueError(
                f"Tseitin 3-CNF requires degree 3, vertex {vertex} has "
                f"degree {len(incident_indices)}"
            )
        a, b, c = (edge_ids[idx] for idx in incident_indices)
        clauses.extend(xor3_clauses(a, b, c, charges[vertex]))

    n_vars = max(edge_ids) if edge_ids else 0
    md: dict[str, object] = {
        "family": "Tseitin",
        "n_vertices": n,
        "n_edges": m,
        "n_vars": n_vars,
        "n_clauses": len(clauses),
        "charge_sum_mod2": sum(charges) % 2,
        "component_charge_parities": component_charge_parities(graph, charges),
        "claim_level": (
            "Parity criterion Proved; width and solver-effort observations "
            "are Empirical Observation"
        ),
    }
    if metadata is not None:
        md.update(metadata)

    return TseitinInstance(
        graph=graph,
        charges=charges,
        edge_ids=edge_ids,
        n_vars=n_vars,
        clauses=tuple(clauses),
        metadata=md,
    )


def validate_metadata(
    instance: TseitinInstance,
    metadata: Mapping[str, object] | None = None,
) -> bool:
    """Validate charge metadata against the actual graph and charges."""
    md = instance.metadata if metadata is None else metadata

    expected_sum = sum(instance.charges) % 2
    if md.get("charge_sum_mod2") != expected_sum:
        raise ValueError("charge_sum_mod2 metadata mismatch")

    expected_comps = component_charge_parities(
        instance.graph, instance.charges
    )
    raw_comps = md.get("component_charge_parities")
    if raw_comps is None:
        raise ValueError("missing component_charge_parities metadata")
    normalized = tuple(
        (tuple(comp), int(par)) for comp, par in raw_comps  # type: ignore[misc]
    )
    if normalized != expected_comps:
        raise ValueError("component_charge_parities metadata mismatch")

    if md.get("n_vars") != instance.n_vars:
        raise ValueError("n_vars metadata mismatch")
    if md.get("n_clauses") != len(instance.clauses):
        raise ValueError("n_clauses metadata mismatch")
    return True


def replace_metadata(instance: TseitinInstance, **kwargs: object) -> TseitinInstance:
    """Return a copy with selected metadata fields replaced."""
    md = dict(instance.metadata)
    md.update(kwargs)
    return TseitinInstance(
        graph=instance.graph,
        charges=instance.charges,
        edge_ids=instance.edge_ids,
        n_vars=instance.n_vars,
        clauses=instance.clauses,
        metadata=md,
    )


def generate_matched_tseitin_pair(
    graph: SimpleGraph,
    base_charge: Sequence[int] | None = None,
    flip_vertex: int = 0,
) -> MatchedTseitinPair:
    """Generate matched even-charge and odd-charge formulas on the same graph."""
    validate_graph(graph, require_connected=True, require_cubic=True)
    n = graph.n_vertices
    if not (0 <= flip_vertex < n):
        raise ValueError("flip_vertex out of range")

    if base_charge is None:
        base = tuple([0] * n)
    else:
        base = tuple(base_charge)

    if len(base) != n:
        raise ValueError("base_charge length must equal n_vertices")
    if any(c not in (0, 1) for c in base):
        raise ValueError("base_charge entries must be 0 or 1")
    if sum(base) % 2 != 0:
        raise ValueError("base_charge must have even total charge on a connected graph")

    odd = list(base)
    odd[flip_vertex] ^= 1

    even_instance = encode_tseitin(graph, base)
    odd_instance = encode_tseitin(graph, tuple(odd))

    if even_instance.graph.unsigned_signature() != odd_instance.graph.unsigned_signature():
        raise AssertionError("matched pair graph signatures differ")
    if even_instance.edge_ids != odd_instance.edge_ids:
        raise AssertionError("matched pair edge identifiers differ")

    return MatchedTseitinPair(
        graph=graph,
        even=even_instance,
        odd=odd_instance,
        flipped_vertex=flip_vertex,
    )


# ---------------------------------------------------------------------------
# Independent witness and parity validation
# ---------------------------------------------------------------------------

def evaluate_cnf(
    instance: TseitinInstance,
    assignment: Mapping[int, bool],
) -> bool:
    for clause in instance.clauses:
        clause_satisfied = False
        for lit in clause:
            value = bool(assignment.get(abs(lit), False))
            if (lit > 0 and value) or (lit < 0 and not value):
                clause_satisfied = True
                break
        if not clause_satisfied:
            return False
    return True


def validate_tseitin_assignment(
    instance: TseitinInstance,
    assignment: Mapping[int, bool],
) -> bool:
    """Independently check CNF clauses and every vertex parity equation."""
    if not evaluate_cnf(instance, assignment):
        return False

    incidence = validate_incidence_multiplicities(
        instance.graph, require_cubic=True
    )
    for vertex, incident_indices in enumerate(incidence):
        parity = 0
        for idx in incident_indices:
            edge_var = instance.edge_ids[idx]
            parity ^= int(bool(assignment.get(edge_var, False)))
        if parity != instance.charges[vertex]:
            return False
    return True


def all_zero_assignment(instance: TseitinInstance) -> dict[int, bool]:
    return {edge_var: False for edge_var in instance.edge_ids}


def validate_all_zero_witness(instance: TseitinInstance) -> bool:
    if any(instance.charges):
        return False
    return validate_tseitin_assignment(instance, all_zero_assignment(instance))


def parity_obstruction(instance: TseitinInstance) -> tuple[tuple[int, ...], ...]:
    """Return components with odd total charge; non-empty implies UNSAT."""
    return tuple(
        comp
        for comp, parity in component_charge_parities(
            instance.graph, instance.charges
        )
        if parity == 1
    )


def is_parity_satisfiable(instance: TseitinInstance) -> bool:
    return not parity_obstruction(instance)


# ---------------------------------------------------------------------------
# Deterministic matched permutations
# ---------------------------------------------------------------------------

def rotation_permutation(n: int, shift: int) -> tuple[int, ...]:
    if n < 0:
        raise ValueError("n must be non-negative")
    return tuple((i + shift) % n for i in range(n))


def reverse_permutation(n: int) -> tuple[int, ...]:
    if n < 0:
        raise ValueError("n must be non-negative")
    return tuple(reversed(range(n)))


def is_permutation(perm: Sequence[int], n: int) -> bool:
    return sorted(perm) == list(range(n))


def apply_vertex_permutation(
    graph: SimpleGraph,
    perm: Sequence[int],
) -> SimpleGraph:
    if not is_permutation(perm, graph.n_vertices):
        raise ValueError("perm must be a permutation of 0..n_vertices-1")
    new_edges = [
        canonical_edge(perm[u], perm[v]) for u, v in graph.edges
    ]
    return SimpleGraph(graph.n_vertices, tuple(sorted(new_edges)))


def apply_charge_permutation(
    charges: Sequence[int],
    perm: Sequence[int],
) -> tuple[int, ...]:
    if len(charges) != len(perm):
        raise ValueError("charges and perm lengths must match")
    if not is_permutation(perm, len(charges)):
        raise ValueError("perm must be a permutation")
    out = [0] * len(charges)
    for old, new in enumerate(perm):
        out[new] = charges[old]
    return tuple(out)


def permute_matched_pair(
    pair: MatchedTseitinPair,
    perm: Sequence[int],
) -> MatchedTseitinPair:
    new_graph = apply_vertex_permutation(pair.graph, perm)
    even_charges = apply_charge_permutation(pair.even.charges, perm)
    odd_charges = apply_charge_permutation(pair.odd.charges, perm)

    new_even = encode_tseitin(new_graph, even_charges)
    new_odd = encode_tseitin(new_graph, odd_charges)

    return MatchedTseitinPair(
        graph=new_graph,
        even=new_even,
        odd=new_odd,
        flipped_vertex=perm[pair.flipped_vertex],
    )


# ---------------------------------------------------------------------------
# Width-estimate and solver-effort probes
# ---------------------------------------------------------------------------

def clause_widths(instance: TseitinInstance) -> tuple[int, ...]:
    return tuple(sorted(len(clause) for clause in instance.clauses))


def primal_graph(instance: TseitinInstance) -> dict[int, set[int]]:
    adj: dict[int, set[int]] = {
        v: set() for v in range(1, instance.n_vars + 1)
    }
    for clause in instance.clauses:
        variables = [abs(lit) for lit in clause]
        for i in range(len(variables)):
            for j in range(i + 1, len(variables)):
                a, b = variables[i], variables[j]
                if a == b:
                    continue
                adj.setdefault(a, set()).add(b)
                adj.setdefault(b, set()).add(a)
    return adj


def min_fill_width_estimate(instance: TseitinInstance) -> int:
    """Deterministic min-fill elimination width estimate on the primal graph.

    This is **Empirical Observation** as a proxy only.  It is not exact
    treewidth and is not a proof of any complexity separation.
    """
    adj = {v: set(neigh) for v, neigh in primal_graph(instance).items()}
    width = 0

    while adj:
        best_vertex: int | None = None
        best_key: tuple[int, int, int] | None = None

        for vertex, neighbours in adj.items():
            neigh_list = list(neighbours)
            missing = 0
            for i in range(len(neigh_list)):
                for j in range(i + 1, len(neigh_list)):
                    if neigh_list[j] not in adj[neigh_list[i]]:
                        missing += 1
            key = (missing, len(neighbours), vertex)
            if best_key is None or key < best_key:
                best_key = key
                best_vertex = vertex

        assert best_vertex is not None
        neighbours = set(adj[best_vertex])
        width = max(width, len(neighbours))

        neigh_list = list(neighbours)
        for i in range(len(neigh_list)):
            for j in range(i + 1, len(neigh_list)):
                a, b = neigh_list[i], neigh_list[j]
                adj[a].add(b)
                adj[b].add(a)

        for u in neighbours:
            adj[u].discard(best_vertex)
        del adj[best_vertex]

    return width


def solver_effort(
    instance: TseitinInstance,
    solver_name: str = "cd195",
) -> dict[str, object]:
    """Run PySAT and return an empirical effort record."""
    from .solvers import solve_pysat

    result = solve_pysat(
        instance.n_vars,
        [list(clause) for clause in instance.clauses],
        solver_name=solver_name,
    )
    return {
        "solver": result.solver_name,
        "satisfiable": result.satisfiable,
        "decisions": result.decisions,
        "propagations": result.propagations,
        "elapsed_s": result.elapsed_s,
        "verified": result.verified,
    }


# ---------------------------------------------------------------------------
# Negative-test constructors
# ---------------------------------------------------------------------------

def disconnected_two_k4() -> SimpleGraph:
    """Two disjoint K4 components: valid cubic simple graph, disconnected."""
    g = k4()
    edges = list(g.edges)
    edges.extend((u + 4, v + 4) for u, v in g.edges)
    return SimpleGraph(8, tuple(sorted(edges)))


def duplicate_edge_graph() -> SimpleGraph:
    g = k4()
    return SimpleGraph(g.n_vertices, tuple(sorted(list(g.edges) + [(0, 1)])))


def self_loop_graph() -> SimpleGraph:
    g = k4()
    return SimpleGraph(g.n_vertices, tuple(sorted(list(g.edges) + [(0, 0)])))


def non_cubic_graph() -> SimpleGraph:
    return SimpleGraph(4, ((0, 1), (1, 2), (2, 3)))


__all__ = [
    "Edge",
    "SimpleGraph",
    "TseitinInstance",
    "MatchedTseitinPair",
    "canonical_edge",
    "normalize_edges",
    "k4",
    "k33",
    "prism_graph",
    "moebius_ladder",
    "petersen_graph",
    "connected_cubic_registry",
    "components",
    "is_connected",
    "validate_incidence_multiplicities",
    "validate_graph",
    "xor3_clauses",
    "component_charge_parities",
    "encode_tseitin",
    "validate_metadata",
    "replace_metadata",
    "generate_matched_tseitin_pair",
    "evaluate_cnf",
    "validate_tseitin_assignment",
    "all_zero_assignment",
    "validate_all_zero_witness",
    "parity_obstruction",
    "is_parity_satisfiable",
    "rotation_permutation",
    "reverse_permutation",
    "is_permutation",
    "apply_vertex_permutation",
    "apply_charge_permutation",
    "permute_matched_pair",
    "clause_widths",
    "primal_graph",
    "min_fill_width_estimate",
    "solver_effort",
    "disconnected_two_k4",
    "duplicate_edge_graph",
    "self_loop_graph",
    "non_cubic_graph",
]
