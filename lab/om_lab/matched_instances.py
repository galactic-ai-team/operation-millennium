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

Review repairs (Phase 4, per REVIEW_PR8_CLAUDE.md)
--------------------------------------------------
- CLAUDE-R8-05: ``validate_encoding`` re-encodes from the declared
  (graph, charges, edge_ids) and requires clause equality.  Catches
  missing/extra/substituted clauses and charge/clause disagreements.
- CLAUDE-R8-06: caught by ``validate_encoding`` (a swapped edge map
  produces different clauses than the declared one).
- CLAUDE-R8-07: ``encode_tseitin`` rejects non-int, bool, and
  unreasonably-large edge identifiers.
- CLAUDE-R8-14: ``generate_matched_tseitin_pair`` asserts A3 clause-level
  signatures (occurrence profile, primal signature, clause-length
  multiset) on the pair members.
- CLAUDE-R8-18: ``min_fill_width_estimate`` delegates to
  ``width_features.primal_min_fill_width``; ``min_fill_width_with_ordering``
  exposes the elimination ordering per ruling A1.
- CLAUDE-R8-09 (incidental): ``validate_metadata`` now also checks
  n_vertices / n_edges / family, and ``encode_tseitin`` refuses to
  override computed metadata keys.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

Edge = tuple[int, int]

# Guard against unbounded declared-variable allocations downstream
# (CLAUDE-R8-07: edge_ids=(..., 10**7) currently allocates 10^7 entries
# in primal_graph and downstream consumers).  Sparse ids up to 10^6 are
# still allowed.
MAX_DECLARED_VARS = 1_000_000

# Metadata keys whose values are computed by ``encode_tseitin`` and must
# not be overridden by a caller (CLAUDE-R8-09 / M18).
COMPUTED_METADATA_KEYS = frozenset({
    "family",
    "n_vertices",
    "n_edges",
    "n_vars",
    "n_clauses",
    "charge_sum_mod2",
    "component_charge_parities",
})


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


# ---------------------------------------------------------------------------
# A3 clause-level signatures (CLAUDE-R8-14)
# ---------------------------------------------------------------------------

def _clause_length_multiset(
    clauses: Sequence[Sequence[int]],
) -> tuple[int, ...]:
    """Sorted multiset of clause lengths (A3 clause-length signature)."""
    return tuple(sorted(len(c) for c in clauses))


def _occurrence_profile(
    clauses: Sequence[Sequence[int]],
    n_vars: int,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Per-variable positive/negative occurrence counts (A3 A-occurrence)."""
    pos = [0] * (n_vars + 1)
    neg = [0] * (n_vars + 1)
    for c in clauses:
        for lit in c:
            if lit > 0:
                pos[lit] += 1
            elif lit < 0:
                neg[-lit] += 1
            # lit == 0 rejected earlier; nothing to do here.
    return (tuple(pos), tuple(neg))


def _cnf_primal_signature(instance: TseitinInstance) -> tuple:
    """Sorted per-vertex neighbourhood list from the CNF primal graph.

    Uses ``primal_graph(instance)`` so it is independent of clause
    order and of the declared edge map, and covers all n_vars
    vertices including isolated ones.
    """
    adj = primal_graph(instance)
    return tuple(
        (v, tuple(sorted(adj[v]))) for v in sorted(adj)
    )


def _check_matched_pair_cnf(
    even: TseitinInstance,
    odd: TseitinInstance,
) -> None:
    """Assert A3 clause-level signatures match between pair members.

    Called from ``generate_matched_tseitin_pair`` and
    ``permute_matched_pair``.  A mutation to ``xor3_clauses`` that
    changes one rhs=1 group (and therefore only the odd instance in a
    matched pair) is caught here; a mutation to the pair-construction
    logic that produces structurally different CNFs is caught here.
    """
    if _clause_length_multiset(even.clauses) != _clause_length_multiset(
        odd.clauses
    ):
        raise AssertionError("matched pair clause-length multisets differ")
    if _occurrence_profile(even.clauses, even.n_vars) != _occurrence_profile(
        odd.clauses, odd.n_vars
    ):
        raise AssertionError("matched pair occurrence profiles differ")
    if _cnf_primal_signature(even) != _cnf_primal_signature(odd):
        raise AssertionError("matched pair primal signatures differ")


# ---------------------------------------------------------------------------
# Encoding and integrity
# ---------------------------------------------------------------------------

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

    Edge-identifier contract (CLAUDE-R8-07): ids must be ``int`` (not
    ``bool``), strictly positive, distinct, and not greater than
    ``MAX_DECLARED_VARS``.  Sparse ids are allowed, but a declared
    variable count that large is refused as a DoS guard.

    Metadata contract (CLAUDE-R8-09 / M18): keys in
    ``COMPUTED_METADATA_KEYS`` may not be overridden by the caller.
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
    for edge_id in edge_ids:
        # Reject bool before int: isinstance(True, int) is True.
        if isinstance(edge_id, bool) or not isinstance(edge_id, int):
            raise TypeError(
                f"edge identifier must be int (not bool), got {edge_id!r}"
            )
        if edge_id <= 0:
            raise ValueError("edge identifiers must be positive")
    if len(set(edge_ids)) != m:
        raise ValueError("repeated edge identifiers are not allowed")
    if edge_ids and max(edge_ids) > MAX_DECLARED_VARS:
        raise ValueError(
            f"edge identifier {max(edge_ids)} exceeds "
            f"MAX_DECLARED_VARS={MAX_DECLARED_VARS}"
        )

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
        for key in metadata:
            if key in COMPUTED_METADATA_KEYS:
                raise ValueError(
                    f"metadata key {key!r} is computed by encode_tseitin "
                    "and cannot be overridden"
                )
        md.update(metadata)

    return TseitinInstance(
        graph=graph,
        charges=charges,
        edge_ids=edge_ids,
        n_vars=n_vars,
        clauses=tuple(clauses),
        metadata=md,
    )


def validate_encoding(instance: TseitinInstance) -> bool:
    """Verify ``instance.clauses`` equal a fresh encoding of its declared inputs.

    Detects hand-edited instances (CLAUDE-R8-05, R8-06): missing or
    duplicated clauses (M10, M11), clauses whose sign pattern does not
    match the declared charges (M17), and clauses whose variable
    structure does not match the declared edge map (M01, M08).

    Re-encodes from ``(graph, charges, edge_ids)`` and requires exact
    clause equality; also checks that ``n_vars`` equals the maximum
    edge identifier.  Raises ``ValueError`` on any mismatch.
    """
    # 1. Clause literals must be ints (not bools) in range ±[1..n_vars].
    for clause in instance.clauses:
        for lit in clause:
            if isinstance(lit, bool) or not isinstance(lit, int):
                raise ValueError(
                    f"clause literal {lit!r} is not an int"
                )
            if lit == 0 or abs(lit) > instance.n_vars:
                raise ValueError(
                    f"clause literal {lit} out of range for "
                    f"n_vars={instance.n_vars}"
                )

    # 2. n_vars must equal max(edge_ids), per encode_tseitin.
    expected_n_vars = max(instance.edge_ids) if instance.edge_ids else 0
    if instance.n_vars != expected_n_vars:
        raise ValueError(
            f"n_vars {instance.n_vars} != max(edge_ids) {expected_n_vars}"
        )

    # 3. Re-encode from the declared inputs and require exact match.
    try:
        rebuilt = encode_tseitin(
            instance.graph,
            instance.charges,
            edge_ids=instance.edge_ids,
            validate=False,
        )
    except (ValueError, TypeError) as exc:
        raise ValueError(
            f"instance cannot be re-encoded: {exc}"
        ) from exc
    if tuple(tuple(c) for c in rebuilt.clauses) != tuple(
        tuple(c) for c in instance.clauses
    ):
        raise ValueError(
            "clauses do not match encode_tseitin(graph, charges, edge_ids)"
        )
    return True


def validate_metadata(
    instance: TseitinInstance,
    metadata: Mapping[str, object] | None = None,
) -> bool:
    """Validate charge metadata against the actual graph and charges.

    Also validates structural metadata (``family``, ``n_vertices``,
    ``n_edges``) and — as the last step — re-encodes the instance to
    require clause equality (CLAUDE-R8-05/06).  ``validate_metadata`` is
    therefore sufficient as an instance-level integrity check: any
    caller that trusts ``validate_metadata(instance)`` has confirmed
    both the metadata fields and the clause content against the
    declared ``(graph, charges, edge_ids)``.
    """
    md = instance.metadata if metadata is None else metadata

    # Structural metadata (CLAUDE-R8-09 / M16).
    if md.get("family") != "Tseitin":
        raise ValueError("family metadata mismatch")
    if md.get("n_vertices") != instance.graph.n_vertices:
        raise ValueError("n_vertices metadata mismatch")
    if md.get("n_edges") != len(instance.graph.edges):
        raise ValueError("n_edges metadata mismatch")

    # Charge metadata.
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

    # Clause / edge-map integrity (CLAUDE-R8-05/06).  Runs last so that
    # callers who only care about metadata mismatches still see the
    # specific message above.
    validate_encoding(instance)
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
    """Generate matched even-charge and odd-charge formulas on the same graph.

    The pair assertions compare the A3 clause-level signatures of the
    two encoded instances (occurrence profile, primal signature,
    clause-length multiset) in addition to the graph signature and
    edge identifiers.  A mutation to ``xor3_clauses`` therefore cannot
    silently pass; see CLAUDE-R8-14.
    """
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
        raise ValueError(
            "base_charge must have even total charge on a connected graph"
        )

    odd = list(base)
    odd[flip_vertex] ^= 1

    even_instance = encode_tseitin(graph, base)
    odd_instance = encode_tseitin(graph, tuple(odd))

    if even_instance.graph.unsigned_signature() != odd_instance.graph.unsigned_signature():
        raise AssertionError("matched pair graph signatures differ")
    if even_instance.edge_ids != odd_instance.edge_ids:
        raise AssertionError("matched pair edge identifiers differ")
    _check_matched_pair_cnf(even_instance, odd_instance)

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
    """Independently check CNF clauses and every vertex parity equation.

    Callers should first call ``validate_metadata(instance)`` (which
    now runs ``validate_encoding``).  If the instance's clauses do not
    match ``encode_tseitin(graph, charges, edge_ids)``, this function
    is still checking the model against the *declared* equations, not
    the stored clauses — the mismatch will show up as a rejected model.
    Rejecting the model is correct behaviour for a malformed instance;
    it is the malformed instance that should be rejected earlier, by
    ``validate_metadata``.
    """
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
    _check_matched_pair_cnf(new_even, new_odd)

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
    """Thin wrapper over ``width_features.primal_min_fill_width``.

    Rulings A1 and B6 (CLAUDE-R8-18): there is one canonical min-fill
    implementation, ``om_lab.width_features.primal_min_fill_width``.
    This function returns only the width for historical compatibility;
    callers that need the elimination ordering (ruling A1: "must be
    returned and retained") should call ``min_fill_width_with_ordering``.

    Empirical Observation as a proxy only; not exact treewidth.
    """
    from .width_features import primal_min_fill_width
    return primal_min_fill_width(instance.n_vars, instance.clauses).width


def min_fill_width_with_ordering(instance: TseitinInstance):
    """Canonical min-fill width **and** elimination ordering.

    Per ruling A1, the elimination ordering must be returned and
    retained.  Returns a ``width_features.MinFillResult`` with
    ``.width`` and ``.ordering``.
    """
    from .width_features import primal_min_fill_width
    return primal_min_fill_width(instance.n_vars, instance.clauses)


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
    "MAX_DECLARED_VARS",
    "COMPUTED_METADATA_KEYS",
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
    "validate_encoding",
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
    "min_fill_width_with_ordering",
    "solver_effort",
    "disconnected_two_k4",
    "duplicate_edge_graph",
    "self_loop_graph",
    "non_cubic_graph",
]
