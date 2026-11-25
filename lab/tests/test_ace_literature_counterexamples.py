# lab/tests/test_ace_literature_counterexamples.py
"""Finite regression witnesses for ACE-R11-04/10/12/18; not asymptotic proofs."""
from itertools import combinations, product


def balanced_cut(n, edges):
    return min(
        sum((u in side) != (v in side) for u, v in edges)
        for k in range((n + 2) // 3, (2 * n) // 3 + 1)
        for side in map(set, combinations(range(n), k))
    )


def test_t12_complete_graph_bound_counterexample():
    n = 8
    edges = list(combinations(range(n), 2))
    # tw(K_n)=Delta(K_n)=n-1. BSW Thm 4.4 gives width >= cut.
    assert balanced_cut(n, edges) == 15 > 2 * (n - 1)


def test_t10_star_short_resolution():
    for m in (3, 7, 11):
        edges = [(0, i) for i in range(1, m + 1)]
        assert balanced_cut(m + 1, edges) == (m + 3) // 3
        # Center charge 1 admits this all-positive input clause;
        # zero-charge leaves supply all negative unit clauses.
        proof = [frozenset({-i}) for i in range(1, m + 1)]
        proof.append(frozenset(range(1, m + 1)))
        for i in range(1, m + 1):
            left, right = proof[-1], proof[i - 1]
            assert i in left and -i in right
            proof.append((left - {i}) | (right - {-i}))
        assert proof[-1] == frozenset()
        assert len(proof) == 2 * m + 1


def test_t4_width_is_threshold_not_equality():
    # F=(x) AND (not x). Width exactly 1; Spoiler wins even
    # with one pebble by asking for x, hence also with 3 pebbles.
    clauses = ((1,), (-1,))
    for value in (False, True):
        assert any(not any(value == (lit > 0) for lit in c)
                   for c in clauses)
    assert set(clauses[0]) - {1} == set(clauses[1]) - {-1} == set()


def test_t18_clause_polynomial_sum_is_linear_over_f2():
    for rhs in (0, 1):
        forbidden = [a for a in product((0, 1), repeat=3)
                     if sum(a) % 2 != rhs]
        # Each wrong assignment has a degree-3 indicator polynomial.
        # Represent a multilinear monomial as a bitmask; XOR is addition.
        total = set()
        for a in forbidden:
            poly = {0}
            for i, bit in enumerate(a):
                shifted = {monomial | (1 << i) for monomial in poly}
                poly = shifted if bit else poly ^ shifted
            assert 7 in poly  # xyz coefficient is 1
            total ^= poly
        assert total == ({1, 2, 4} | ({0} if rhs else set()))
        for a in product((0, 1), repeat=3):
            mask = sum(bit << i for i, bit in enumerate(a))
            actual = sum((term & mask) == term for term in total) % 2
            assert actual == (sum(a) % 2) ^ rhs
