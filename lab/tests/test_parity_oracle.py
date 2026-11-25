"""Self-tests for the independent GF(2) parity oracle (om_lab.parity_oracle).

The oracle is checked against exhaustive enumeration of every edge
assignment on small graphs and multigraphs, so the review of PR #8 does
not rest on an untested oracle. [Claim Level: Empirical Observation] on
the fixtures and seeds below.
"""

from __future__ import annotations

import itertools
import random

import pytest

from om_lab.parity_oracle import (
    check_refutation,
    check_witness,
    decode_xor_cnf,
    edge_witness_to_model,
    expected_constraints,
    gf2_solve,
    model_to_edge_witness,
    parity_system,
    solve_decoded,
    tseitin_oracle,
)


def _image_by_enumeration(n, edges):
    """All charge vectors reachable by some edge assignment (brute force)."""
    image = set()
    for bits in itertools.product((0, 1), repeat=len(edges)):
        parity = [0] * n
        for (u, v), b in zip(edges, bits):
            if b:
                parity[u] ^= 1
                parity[v] ^= 1
        image.add(tuple(parity))
    return image


def _components(n, edges):
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for u, v in edges:
        parent[find(u)] = find(v)
    groups = {}
    for v in range(n):
        groups.setdefault(find(v), set()).add(v)
    return list(groups.values())


SMALL_GRAPHS = {
    "k4": (4, [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]),
    "k33": (6, [(i, 3 + j) for i in range(3) for j in range(3)]),
    "two_triangles": (6, [(0, 1), (1, 2), (0, 2), (3, 4), (4, 5), (3, 5)]),
    "path_plus_isolated": (5, [(0, 1), (1, 2), (2, 3)]),
    "empty_graph": (0, []),
    "isolated_vertices": (3, []),
    # Outside the encoder contract, inside the oracle's multigraph domain:
    "double_edge": (2, [(0, 1), (0, 1)]),
    "self_loop": (3, [(0, 0), (0, 1), (1, 2)]),
}


def _random_multigraph(rng, max_n=6, max_m=10):
    n = rng.randint(1, max_n)
    m = rng.randint(0, max_m)
    return n, [(rng.randrange(n), rng.randrange(n)) for _ in range(m)]


@pytest.mark.parametrize("name", sorted(SMALL_GRAPHS))
def test_oracle_matches_exhaustive_enumeration_on_fixed_graphs(name):
    n, edges = SMALL_GRAPHS[name]
    image = _image_by_enumeration(n, edges)
    for charges in itertools.product((0, 1), repeat=n):
        result = tseitin_oracle(n, edges, charges)
        assert result.consistent == (charges in image), (name, charges)
        if result.consistent:
            assert check_witness(n, edges, charges, result.witness)
        else:
            assert check_refutation(n, edges, charges, result.refutation)


def test_oracle_matches_exhaustive_enumeration_on_random_multigraphs():
    rng = random.Random("OM-P4-R8|oracle-self-test")
    checked = 0
    for _ in range(150):
        n, edges = _random_multigraph(rng)
        image = _image_by_enumeration(n, edges)
        for charges in itertools.product((0, 1), repeat=n):
            result = tseitin_oracle(n, edges, charges)
            assert result.consistent == (charges in image)
            if result.consistent:
                assert check_witness(n, edges, charges, result.witness)
            else:
                assert check_refutation(n, edges, charges, result.refutation)
            checked += 1
    assert checked > 1000


def test_refutation_is_a_union_of_odd_charge_components():
    # For loop-free graphs an even endpoint count in S for every edge forces S
    # to be a union of connected components; its total charge must be odd.
    rng = random.Random("OM-P4-R8|refutation-shape")
    for _ in range(100):
        n = rng.randint(2, 8)
        edges = [(u, v) for u, v in ((rng.randrange(n), rng.randrange(n)) for _ in range(rng.randint(0, 10))) if u != v]
        charges = [rng.randint(0, 1) for _ in range(n)]
        result = tseitin_oracle(n, edges, charges)
        if result.consistent:
            continue
        chosen = set(result.refutation)
        for comp in _components(n, edges):
            assert comp <= chosen or not (comp & chosen)
        assert sum(charges[v] for v in chosen) % 2 == 1


def test_certificate_checkers_reject_bad_certificates():
    n, edges = SMALL_GRAPHS["k4"]
    charges = (1, 0, 0, 0)
    result = tseitin_oracle(n, edges, charges)
    assert not result.consistent and check_refutation(n, edges, charges, result.refutation)
    assert not check_refutation(n, edges, charges, [0])  # edges leave S
    assert not check_refutation(n, edges, (1, 1, 0, 0), range(4))  # even charge
    assert not check_refutation(n, edges, charges, [])
    even = tseitin_oracle(n, edges, (0, 0, 0, 0))
    assert check_witness(n, edges, (0, 0, 0, 0), even.witness)
    assert not check_witness(n, edges, (0, 0, 0, 0), (1, 0, 0, 0, 0, 0))
    assert not check_witness(n, edges, (0, 0, 0, 0), (0, 0, 0))


def test_gf2_solve_edge_cases():
    assert gf2_solve([], []) == (True, 0, 0, None)
    consistent, rank, solution, combination = gf2_solve([0b11, 0b11], [0, 1])
    assert not consistent and combination == 0b11 and solution is None
    consistent, rank, solution, _ = gf2_solve([0b011, 0b110, 0b101], [1, 1, 0])
    assert consistent and rank == 2
    assert all(bin(row & solution).count("1") % 2 == b for row, b in zip([0b011, 0b110, 0b101], [1, 1, 0]))
    assert gf2_solve([0], [1])[0] is False


def test_parity_system_rejects_malformed_input():
    with pytest.raises(ValueError):
        parity_system(3, [(0, 3)], (0, 0, 0))
    with pytest.raises(ValueError):
        parity_system(3, [(0, -1)], (0, 0, 0))
    with pytest.raises(ValueError):
        parity_system(3, [(0, 1)], (0, 0))
    with pytest.raises(ValueError):
        parity_system(3, [(0, 1)], (0, 2, 0))
    with pytest.raises(ValueError):
        parity_system(3, [(0, 1.0)], (0, 0, 0))
    with pytest.raises(ValueError):
        parity_system(3, [(0, 1, 2)], (0, 0, 0))


# --------------------------------------------------------------------------
# CNF decoding
# --------------------------------------------------------------------------


def _independent_xor_encoding(variables, rhs, rng):
    """Exclude every assignment of wrong parity; shuffled clause and literal order."""
    clauses = []
    for bits in itertools.product((0, 1), repeat=len(variables)):
        if sum(bits) % 2 != rhs:
            clause = [v if b == 0 else -v for v, b in zip(variables, bits)]
            rng.shuffle(clause)
            clauses.append(clause)
    rng.shuffle(clauses)
    return clauses


def test_decode_round_trip_and_semantics():
    rng = random.Random("OM-P4-R8|decode")
    for _ in range(200):
        n_vars = rng.randint(1, 8)
        cons = []
        clauses = []
        for _ in range(rng.randint(1, 5)):
            k = rng.randint(1, min(4, n_vars))
            variables = sorted(rng.sample(range(1, n_vars + 1), k))
            rhs = rng.randint(0, 1)
            if any(tuple(variables) == c[0] for c in cons):
                continue
            cons.append((tuple(variables), rhs))
            clauses.extend(_independent_xor_encoding(variables, rhs, rng))
        decoded = decode_xor_cnf(clauses)
        assert decoded.exact, decoded.problems
        assert sorted((c.variables, c.rhs) for c in decoded.constraints) == sorted(cons)
        consistent, assignment, _ = solve_decoded(decoded)
        brute = any(
            all(sum(bits[v - 1] for v in vs) % 2 == r for vs, r in cons)
            for bits in itertools.product((0, 1), repeat=n_vars)
        )
        assert consistent == brute
        if consistent:
            assert all(sum(assignment[v] for v in vs) % 2 == r for vs, r in cons)


def test_decode_reports_non_exact_encodings():
    full = [[1, 2, 3], [1, -2, -3], [-1, 2, -3], [-1, -2, 3]]  # XOR = 1
    assert decode_xor_cnf(full).exact
    assert [c.rhs for c in decode_xor_cnf(full).constraints] == [1]
    assert not decode_xor_cnf(full[:3]).exact  # missing clause
    assert not decode_xor_cnf(full + [[1, 2, 3]]).exact  # duplicate clause
    assert not decode_xor_cnf(full + [[-1, -2, -3]]).exact  # mixed parities
    assert not decode_xor_cnf([[1, 1, 2]]).exact  # repeated variable
    empty = decode_xor_cnf([[]])
    assert empty.exact and empty.constraints[0].rhs == 1 and not solve_decoded(empty)[0]
    units = decode_xor_cnf([[3], [-4]])
    assert [(c.variables, c.rhs) for c in units.constraints] == [((3,), 1), ((4,), 0)]


def test_expected_constraints_and_model_mapping():
    n, edges = SMALL_GRAPHS["k4"]
    edge_vars = [10, 11, 12, 13, 14, 15]
    cons = expected_constraints(n, edges, (1, 0, 0, 1), edge_vars)
    assert cons[0] == ((10, 11, 12), 1)
    assert len(cons) == 4
    model = edge_witness_to_model((1, 0, 1, 0, 0, 0), edge_vars, n_vars=16)
    assert model_to_edge_witness(model, edge_vars) == (1, 0, 1, 0, 0, 0)
    assert len(model) == 16 and model[0] == -1  # unused declared variables are False
    # Self-loop variable cancels from its vertex's equation.
    assert expected_constraints(2, [(0, 0), (0, 1)], (0, 0), [1, 2]) == [((2,), 0), ((2,), 0)]
