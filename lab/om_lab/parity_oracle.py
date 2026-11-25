"""Independent GF(2) parity oracle for Tseitin formulas.

Written by Claude for the Phase 4 adversarial review of Dee's PR #8
(``docs/phase4/ADVERSARIAL_REVIEW_01.md`` Section 6.1). It is deliberately
independent of :mod:`om_lab.matched_instances`. It imports only the Python
standard library and nothing from ``om_lab``.

What it decides, and how
------------------------
For a finite graph given as ``n_vertices`` and a list of edge endpoint
pairs, with one GF(2) variable ``x_i`` per listed edge, the Tseitin system
is::

    for every vertex v:   sum over listed edges i of  m(v, i) * x_i  =  charge(v)   (mod 2)

where ``m(v, i)`` is the number of endpoints of edge ``i`` equal to ``v``.
The equations are derived only from the endpoints and the charges.
Consistency is decided by Gaussian elimination over GF(2). It does not use
connected components, so it does not reuse Dee's component-parity decision
function. Both outcomes carry a certificate that a few lines of code can
check:

* consistent: an explicit edge assignment (``witness``), checked by
  :func:`check_witness` directly against the endpoint list;
* inconsistent: a vertex set ``S`` whose equations sum to ``0 = 1``. Every
  edge has an even number of endpoints in ``S`` and the charges in ``S``
  sum to 1 mod 2. It is checked by :func:`check_refutation`.

:func:`decode_xor_cnf` works in the other direction. It reads a CNF's clauses
alone (no graph, no metadata) and recovers the XOR constraints the clauses
encode, or reports why the clauses are not exactly a conjunction of complete
parity encodings. Comparing the decoded constraints with
:func:`expected_constraints` detects a CNF that does not encode the system
its declared graph, charges and edge-variable map imply. Examples are a
missing clause, a wrong edge mapping, or charges that disagree with the
clauses.

Domain
------
Each listed edge is its own variable, so repeated edges are distinct
variables. A self-loop contributes its variable twice to its vertex, which
cancels in GF(2), so its variable is free. This is broader than the encoder
under review, which accepts only simple cubic graphs. The broader domain lets
the review state what the parity system would be for inputs outside the
encoder contract. Out-of-range endpoints have no meaning and raise
``ValueError``.

Claim levels
------------
* Deciding the consistency of a linear system by Gaussian elimination over a
  field is standard linear algebra; it is not re-proved here.
* The certificates are sound by direct calculation. A checked witness
  satisfies every equation. If the equations of ``S`` sum to ``0 = 1``,
  the system has no solution.
* "This implementation is correct" is **[Claim Level: Empirical
  Observation]**. It is tested against exhaustive enumeration of all edge
  assignments on small graphs and multigraphs (``lab/tests/test_parity_oracle.py``).
"""

from __future__ import annotations

from dataclasses import dataclass
import operator
from typing import Iterable, Sequence

__all__ = [
    "DecodedXorCnf",
    "OracleResult",
    "ParitySystem",
    "XorConstraint",
    "check_refutation",
    "check_witness",
    "decode_xor_cnf",
    "edge_witness_to_model",
    "expected_constraints",
    "gf2_solve",
    "model_to_edge_witness",
    "parity_system",
    "solve_decoded",
    "tseitin_oracle",
]


def _as_int(value: object, what: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{what}: bool is not an integer here")
    try:
        return operator.index(value)  # rejects floats and strings
    except TypeError as exc:
        raise ValueError(f"{what}: expected an integer, got {value!r}") from exc


def _as_bit(value: object, what: str) -> int:
    bit = _as_int(value, what)
    if bit not in (0, 1):
        raise ValueError(f"{what}: expected 0 or 1, got {bit}")
    return bit


def _popcount_parity(x: int) -> int:
    return bin(x).count("1") & 1


# ---------------------------------------------------------------------------
# Generic GF(2) elimination with combination tracking
# ---------------------------------------------------------------------------


def gf2_solve(rows: Sequence[int], rhs: Sequence[int]) -> tuple[bool, int, int | None, int | None]:
    """Solve ``rows[k] . x = rhs[k]`` over GF(2); rows are column bitmasks.

    Returns ``(consistent, rank, solution, combination)``:

    * consistent: ``solution`` is a bitmask solution with free columns set to 0,
      ``combination`` is None;
    * inconsistent: ``solution`` is None and ``combination`` is a bitmask of
      equation indices whose rows XOR to 0 while their right-hand sides XOR
      to 1.
    """
    if len(rows) != len(rhs):
        raise ValueError("rows and rhs must have the same length")
    pivots: dict[int, tuple[int, int, int]] = {}  # leading column -> (row, rhs, combination)
    for k, (row, b) in enumerate(zip(rows, rhs)):
        combo = 1 << k
        row = int(row)
        b = int(b) & 1
        while row:
            lead = row.bit_length() - 1
            pivot = pivots.get(lead)
            if pivot is None:
                pivots[lead] = (row, b, combo)
                break
            prow, pb, pcombo = pivot
            row ^= prow
            b ^= pb
            combo ^= pcombo
        else:
            if b:
                return False, len(pivots), None, combo
    solution = 0
    for lead in sorted(pivots):  # every other bit of a pivot row is a lower column
        prow, pb, _ = pivots[lead]
        if pb ^ _popcount_parity(prow & solution & ~(1 << lead)):
            solution |= 1 << lead
    return True, len(pivots), solution, None


def _bits(mask: int, width: int) -> tuple[int, ...]:
    return tuple((mask >> i) & 1 for i in range(width))


def _members(mask: int) -> tuple[int, ...]:
    out = []
    k = 0
    while mask:
        if mask & 1:
            out.append(k)
        mask >>= 1
        k += 1
    return tuple(out)


# ---------------------------------------------------------------------------
# The Tseitin system derived from endpoints and charges
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ParitySystem:
    """``rows[v]`` is the bitmask of edges with odd endpoint multiplicity at ``v``."""

    n_vertices: int
    edges: tuple[tuple[int, int], ...]
    charges: tuple[int, ...]
    rows: tuple[int, ...]

    @property
    def n_edges(self) -> int:
        return len(self.edges)


def parity_system(
    n_vertices: int,
    edges: Iterable[Sequence[int]],
    charges: Sequence[int],
) -> ParitySystem:
    """Build the Tseitin parity system from endpoints and charges only."""
    n = _as_int(n_vertices, "n_vertices")
    if n < 0:
        raise ValueError("n_vertices must be non-negative")
    edge_list: list[tuple[int, int]] = []
    rows = [0] * n
    for i, edge in enumerate(edges):
        pair = tuple(edge)
        if len(pair) != 2:
            raise ValueError(f"edge {i}: expected two endpoints, got {pair!r}")
        u = _as_int(pair[0], f"edge {i} endpoint")
        v = _as_int(pair[1], f"edge {i} endpoint")
        if not (0 <= u < n and 0 <= v < n):
            raise ValueError(f"edge {i}: endpoint out of range for n_vertices={n}: {pair!r}")
        rows[u] ^= 1 << i
        rows[v] ^= 1 << i  # a self-loop cancels: coefficient 2 = 0 in GF(2)
        edge_list.append((u, v))
    charge_list = [_as_bit(c, "charge") for c in charges]
    if len(charge_list) != n:
        raise ValueError(f"expected {n} charges, got {len(charge_list)}")
    return ParitySystem(n, tuple(edge_list), tuple(charge_list), tuple(rows))


@dataclass(frozen=True)
class OracleResult:
    consistent: bool
    rank: int
    witness: tuple[int, ...] | None  # one bit per listed edge
    refutation: tuple[int, ...] | None  # sorted vertex indices


def tseitin_oracle(
    n_vertices: int,
    edges: Iterable[Sequence[int]],
    charges: Sequence[int],
) -> OracleResult:
    """Decide the Tseitin system by GF(2) elimination and return a certificate."""
    system = parity_system(n_vertices, edges, charges)
    consistent, rank, solution, combination = gf2_solve(system.rows, system.charges)
    if consistent:
        return OracleResult(True, rank, _bits(solution, system.n_edges), None)
    return OracleResult(False, rank, None, _members(combination))


def check_witness(
    n_vertices: int,
    edges: Sequence[Sequence[int]],
    charges: Sequence[int],
    witness: Sequence[int],
) -> bool:
    """Every vertex's incident edge bits (counted per endpoint) sum to its charge."""
    if len(witness) != len(edges) or any(b not in (0, 1) for b in witness):
        return False
    parity = [0] * n_vertices
    for (u, v), bit in zip(edges, witness):
        if bit:
            parity[u] ^= 1
            parity[v] ^= 1
    return parity == [int(c) for c in charges]


def check_refutation(
    n_vertices: int,
    edges: Sequence[Sequence[int]],
    charges: Sequence[int],
    vertices: Iterable[int],
) -> bool:
    """The equations of ``vertices`` sum to 0 = 1."""
    chosen = set(vertices)
    if not chosen or any(not (0 <= v < n_vertices) for v in chosen):
        return False
    for u, v in edges:
        if ((u in chosen) + (v in chosen)) % 2:
            return False
    return sum(int(charges[v]) for v in chosen) % 2 == 1


# ---------------------------------------------------------------------------
# Edge assignment <-> CNF model, through an explicit edge -> variable map
# ---------------------------------------------------------------------------


def edge_witness_to_model(witness: Sequence[int], edge_vars: Sequence[int], n_vars: int) -> list[int]:
    """CNF model (signed literals 1..n_vars) for an edge assignment.

    Declared variables that no edge uses are set False.
    """
    value = {int(var): bool(bit) for var, bit in zip(edge_vars, witness)}
    return [v if value.get(v, False) else -v for v in range(1, n_vars + 1)]


def model_to_edge_witness(model: Sequence[int], edge_vars: Sequence[int]) -> tuple[int, ...]:
    truth = {abs(lit): lit > 0 for lit in model}
    return tuple(int(truth.get(int(var), False)) for var in edge_vars)


# ---------------------------------------------------------------------------
# Decoding a CNF back into XOR constraints (clauses only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class XorConstraint:
    variables: tuple[int, ...]  # sorted distinct variable ids
    rhs: int
    clause_positions: tuple[int, ...]


@dataclass(frozen=True)
class DecodedXorCnf:
    """XOR constraints recovered from clauses; ``problems`` explains any non-exactness."""

    constraints: tuple[XorConstraint, ...]
    problems: tuple[str, ...]

    @property
    def exact(self) -> bool:
        """True iff the clauses are exactly a conjunction of complete parity encodings."""
        return not self.problems


def decode_xor_cnf(clauses: Sequence[Sequence[int]]) -> DecodedXorCnf:
    """Recover XOR constraints from clauses alone.

    Clauses are grouped by their variable set. A group over ``k`` distinct
    variables encodes ``XOR = q`` exactly when it consists of ``2**(k-1)``
    distinct clauses, each excluding one assignment, and the excluded
    assignments are precisely those of parity ``1 - q``. Anything else
    (missing or extra clauses, mixed parities, duplicates, a variable
    repeated inside a clause, literal 0) is reported in ``problems``. An
    empty clause decodes to the contradiction ``XOR() = 1``.
    """
    groups: dict[frozenset[int], list[tuple[int, tuple[int, ...]]]] = {}
    problems: list[str] = []
    for pos, clause in enumerate(clauses):
        lits = tuple(_as_int(lit, f"clause {pos} literal") for lit in clause)
        if any(lit == 0 for lit in lits):
            problems.append(f"clause {pos}: literal 0")
            continue
        variables = [abs(lit) for lit in lits]
        if len(set(variables)) != len(variables):
            problems.append(f"clause {pos}: a variable occurs twice")
            continue
        groups.setdefault(frozenset(variables), []).append((pos, lits))

    constraints: list[XorConstraint] = []
    for key, members in groups.items():
        variables = tuple(sorted(key))
        positions = tuple(pos for pos, _ in members)
        excluded: list[tuple[int, ...]] = []
        for _, lits in members:
            sign = {abs(lit): lit > 0 for lit in lits}
            # The only assignment falsifying the clause sets every literal false.
            excluded.append(tuple(0 if sign[v] else 1 for v in variables))
        distinct = set(excluded)
        if len(distinct) != len(excluded):
            problems.append(f"variables {variables}: duplicate clause(s) at positions {positions}")
        parities = {sum(a) & 1 for a in distinct}
        k = len(variables)
        expected_count = 1 if k == 0 else 2 ** (k - 1)
        if len(parities) == 1 and len(distinct) == expected_count:
            constraints.append(XorConstraint(variables, 1 - parities.pop(), positions))
        else:
            problems.append(
                f"variables {variables}: clauses at positions {positions} exclude "
                f"{len(distinct)} of {2 ** k} assignments with parities {sorted(parities)}; "
                "not a complete parity encoding"
            )
    constraints.sort(key=lambda c: c.clause_positions[0])
    return DecodedXorCnf(tuple(constraints), tuple(problems))


def solve_decoded(decoded: DecodedXorCnf) -> tuple[bool, dict[int, int] | None, tuple[int, ...] | None]:
    """Solve the decoded XOR constraints over the CNF variables.

    Returns ``(consistent, assignment, refutation)``; ``assignment`` maps
    each variable to 0/1, and ``refutation`` lists constraint indices whose
    equations sum to 0 = 1.
    """
    variables = sorted({v for c in decoded.constraints for v in c.variables})
    column = {v: i for i, v in enumerate(variables)}
    rows = []
    for c in decoded.constraints:
        mask = 0
        for v in c.variables:
            mask |= 1 << column[v]
        rows.append(mask)
    consistent, _, solution, combination = gf2_solve(rows, [c.rhs for c in decoded.constraints])
    if consistent:
        return True, {v: (solution >> column[v]) & 1 for v in variables}, None
    return False, None, _members(combination)


def expected_constraints(
    n_vertices: int,
    edges: Sequence[Sequence[int]],
    charges: Sequence[int],
    edge_vars: Sequence[int],
) -> list[tuple[tuple[int, ...], int]]:
    """``(sorted variable ids, rhs)`` per vertex, implied by endpoints, charges and the edge map.

    A variable whose edge has an even number of endpoints at a vertex
    (a self-loop) cancels from that vertex's equation.
    """
    if len(edge_vars) != len(edges):
        raise ValueError("edge_vars must have one entry per edge")
    system = parity_system(n_vertices, edges, charges)
    out = []
    for v in range(n_vertices):
        row = system.rows[v]
        var_ids = sorted(int(edge_vars[i]) for i in range(system.n_edges) if (row >> i) & 1)
        out.append((tuple(var_ids), system.charges[v]))
    return out
