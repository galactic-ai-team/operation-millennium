# lab/tests/test_matched_instances.py
"""Tests for the matched Tseitin structural counterexample suite."""

from __future__ import annotations

from collections import Counter

import pytest

from om_lab.matched_instances import (
    all_zero_assignment,
    apply_vertex_permutation,
    clause_widths,
    connected_cubic_registry,
    disconnected_two_k4,
    duplicate_edge_graph,
    encode_tseitin,
    generate_matched_tseitin_pair,
    is_parity_satisfiable,
    k4,
    min_fill_width_estimate,
    non_cubic_graph,
    parity_obstruction,
    permute_matched_pair,
    replace_metadata,
    reverse_permutation,
    rotation_permutation,
    self_loop_graph,
    solver_effort,
    validate_all_zero_witness,
    validate_graph,
    validate_incidence_multiplicities,
    validate_metadata,
    xor3_clauses,
)


def _occurrence_counts(instance):
    positive = Counter()
    negative = Counter()
    for clause in instance.clauses:
        for lit in clause:
            if lit > 0:
                positive[abs(lit)] += 1
            else:
                negative[abs(lit)] += 1
    return positive, negative


def test_registry_graphs_are_connected_simple_cubic():
    registry = connected_cubic_registry()
    assert registry
    for name, graph in registry.items():
        validate_graph(graph, require_connected=True, require_cubic=True)
        assert graph.n_vertices > 0, name
        assert len(graph.edges) == 3 * graph.n_vertices // 2, name


def test_matched_pair_has_same_unsigned_graph_and_edge_ids():
    for name, graph in connected_cubic_registry().items():
        pair = generate_matched_tseitin_pair(graph)
        assert (
            pair.even.graph.unsigned_signature()
            == pair.odd.graph.unsigned_signature()
        ), name
        assert pair.even.edge_ids == pair.odd.edge_ids, name
        assert pair.even.n_vars == pair.odd.n_vars, name
        assert pair.even.graph.unsigned_signature() == graph.unsigned_signature()


def test_positive_and_negative_occurrence_counts_are_balanced():
    for name, graph in connected_cubic_registry().items():
        pair = generate_matched_tseitin_pair(graph)
        for instance in (pair.even, pair.odd):
            positive, negative = _occurrence_counts(instance)
            assert set(positive) == set(range(1, instance.n_vars + 1)), name
            assert set(negative) == set(range(1, instance.n_vars + 1)), name
            for var in range(1, instance.n_vars + 1):
                assert positive[var] == 4, (name, var, "positive")
                assert negative[var] == 4, (name, var, "negative")


def test_all_clauses_have_width_three():
    for name, graph in connected_cubic_registry().items():
        pair = generate_matched_tseitin_pair(graph)
        for instance in (pair.even, pair.odd):
            assert set(clause_widths(instance)) == {3}, name


def test_all_zero_witness_is_independently_validated():
    for name, graph in connected_cubic_registry().items():
        pair = generate_matched_tseitin_pair(graph)
        assert pair.even.metadata["charge_sum_mod2"] == 0, name
        assert validate_all_zero_witness(pair.even), name
        assert not validate_all_zero_witness(pair.odd), name


def test_odd_charge_parity_obstruction():
    for name, graph in connected_cubic_registry().items():
        pair = generate_matched_tseitin_pair(graph)
        assert not is_parity_satisfiable(pair.odd), name
        assert parity_obstruction(pair.odd), name


def test_matched_permutations_preserve_pair_structure():
    for name, graph in connected_cubic_registry().items():
        pair = generate_matched_tseitin_pair(graph)
        perms = (
            rotation_permutation(graph.n_vertices, 1),
            reverse_permutation(graph.n_vertices),
        )
        for perm in perms:
            permuted = permute_matched_pair(pair, perm)
            assert (
                permuted.even.graph.unsigned_signature()
                == permuted.odd.graph.unsigned_signature()
            ), name
            assert permuted.even.edge_ids == permuted.odd.edge_ids, name
            assert validate_all_zero_witness(permuted.even), name
            assert not is_parity_satisfiable(permuted.odd), name

            expected_graph = apply_vertex_permutation(graph, perm)
            assert (
                permuted.graph.unsigned_signature()
                == expected_graph.unsigned_signature()
            ), name


def test_width_estimates_are_recorded_not_asserted_invariant():
    """Min-fill is a heuristic; this test records estimates under permutations.

    It deliberately does not assert invariance.  Instability of heuristic width
    estimates is an Empirical Observation, not a theorem.
    """
    for name, graph in connected_cubic_registry().items():
        pair = generate_matched_tseitin_pair(graph)
        estimates = []
        for perm in (
            rotation_permutation(graph.n_vertices, 1),
            reverse_permutation(graph.n_vertices),
        ):
            permuted = permute_matched_pair(pair, perm)
            width = min_fill_width_estimate(permuted.even)
            assert isinstance(width, int), name
            assert width >= 2, name
            estimates.append(width)
        assert len(estimates) == 2, name


def test_pysat_confirms_even_sat_and_odd_unsat_small_registry():
    pytest.importorskip("pysat")
    for name, graph in connected_cubic_registry().items():
        pair = generate_matched_tseitin_pair(graph)
        even = solver_effort(pair.even)
        odd = solver_effort(pair.odd)
        assert even["satisfiable"] is True, name
        assert odd["satisfiable"] is False, name


# ---------------------------------------------------------------------------
# Negative cases
# ---------------------------------------------------------------------------

def test_disconnected_even_total_charge_can_be_component_odd_and_unsat():
    graph = disconnected_two_k4()
    validate_graph(graph, require_connected=False, require_cubic=True)

    with pytest.raises(ValueError, match="not connected"):
        validate_graph(graph, require_connected=True, require_cubic=True)

    # Each K4 component has odd charge.  Total charge is even, but the formula
    # is still UNSAT because parity must hold separately in every component.
    charges = (1, 0, 0, 0, 1, 0, 0, 0)
    instance = encode_tseitin(graph, charges)

    assert sum(charges) % 2 == 0
    assert not is_parity_satisfiable(instance)
    obstruction = parity_obstruction(instance)
    assert len(obstruction) == 2


def test_pysat_disconnected_component_parity_counterexample():
    pytest.importorskip("pysat")
    graph = disconnected_two_k4()
    charges = (1, 0, 0, 0, 1, 0, 0, 0)
    instance = encode_tseitin(graph, charges)
    result = solver_effort(instance)
    assert result["satisfiable"] is False


def test_duplicate_edge_rejected():
    graph = duplicate_edge_graph()
    with pytest.raises(ValueError, match="duplicate edge"):
        validate_graph(graph, require_connected=False, require_cubic=False)
    with pytest.raises(ValueError, match="duplicate edge"):
        validate_incidence_multiplicities(graph, require_cubic=False)


def test_self_loop_rejected():
    graph = self_loop_graph()
    with pytest.raises(ValueError, match="self-loop"):
        validate_graph(graph, require_connected=False, require_cubic=False)


def test_non_cubic_graph_rejected():
    graph = non_cubic_graph()
    with pytest.raises(ValueError, match="degree"):
        validate_graph(graph, require_connected=False, require_cubic=True)


def test_repeated_edge_identifiers_rejected():
    graph = k4()
    with pytest.raises(ValueError, match="repeated edge identifiers"):
        encode_tseitin(
            graph,
            (0, 0, 0, 0),
            edge_ids=(1, 1, 2, 3, 4, 5),
        )


def test_malformed_xor_encodings_rejected():
    with pytest.raises(ValueError, match="distinct"):
        xor3_clauses(1, 1, 2, 0)
    with pytest.raises(ValueError, match="rhs"):
        xor3_clauses(1, 2, 3, 2)
    with pytest.raises(ValueError, match="positive"):
        xor3_clauses(0, 2, 3, 0)


def test_incorrect_charge_metadata_rejected():
    instance = encode_tseitin(k4(), (0, 0, 0, 0))
    bad = replace_metadata(instance, charge_sum_mod2=1)
    with pytest.raises(ValueError, match="charge_sum_mod2"):
        validate_metadata(bad)


def test_incidence_multiplicities_are_exactly_two_per_edge():
    graph = k4()
    incidence = validate_incidence_multiplicities(graph, require_cubic=True)
    assert all(len(vertices) == 3 for vertices in incidence)
    flat = [idx for vertices in incidence for idx in vertices]
    expected = list(range(len(graph.edges))) * 2
    assert sorted(flat) == sorted(expected)
