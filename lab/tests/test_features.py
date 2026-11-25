"""Unit tests for om_lab.features (structural CNF feature extraction).

All expected values below are hand-computed from the definitions in
``om_lab.features.extract_features_from_clauses``; they are not
learned from a model and not fitted to solver output.
"""

import math

import pytest

from om_lab.features import (
    FEATURE_NAMES,
    extract_features,
    extract_features_from_clauses,
)
from om_lab.generators import (
    CNFInstance,
    generate_graph_coloring,
    generate_random_3sat,
)


def test_hand_computed_small_instance():
    # Clauses: [1, 2, -3], [-1, 2], [1];  n_vars = 3
    feats = extract_features_from_clauses(
        3, [[1, 2, -3], [-1, 2], [1]]
    )
    assert feats.n_vars == 3
    assert feats.n_clauses == 3
    assert feats.alpha == pytest.approx(1.0)
    # Clause lengths 3, 2, 1
    assert feats.clause_len_mean == pytest.approx(2.0)
    assert feats.clause_len_std == pytest.approx(math.sqrt(2 / 3))
    assert feats.clause_len_min == pytest.approx(1.0)
    assert feats.clause_len_max == pytest.approx(3.0)
    assert feats.clause_len_entropy == pytest.approx(math.log2(3))
    assert feats.unit_clause_fraction == pytest.approx(1 / 3)
    assert feats.binary_clause_fraction == pytest.approx(1 / 3)
    assert feats.ternary_clause_fraction == pytest.approx(1 / 3)
    # 4 positive / 6 total literals
    assert feats.pos_literal_fraction == pytest.approx(2 / 3)
    assert feats.polarity_balance == pytest.approx(1 / 3)
    # Degrees: var1 = 3, var2 = 2, var3 = 1
    assert feats.var_occurrence_mean == pytest.approx(2.0)
    assert feats.var_occurrence_std == pytest.approx(math.sqrt(2 / 3))
    assert feats.var_occurrence_max == pytest.approx(3.0)
    assert feats.var_occurrence_cv == pytest.approx(math.sqrt(2 / 3) / 2)
    expected_entropy = -(
        0.5 * math.log2(0.5)
        + (1 / 3) * math.log2(1 / 3)
        + (1 / 6) * math.log2(1 / 6)
    )
    assert feats.var_occurrence_entropy == pytest.approx(expected_entropy)
    assert feats.var_occurrence_entropy_norm == pytest.approx(
        expected_entropy / math.log2(3)
    )
    assert feats.isolated_var_fraction == pytest.approx(0.0)
    assert feats.singleton_var_fraction == pytest.approx(1 / 3)
    # var2 is positive-only, var3 is negative-only; var1 is mixed
    assert feats.pure_literal_fraction == pytest.approx(2 / 3)
    # Every pair co-occurs in the first clause
    assert feats.cooccurrence_degree_mean == pytest.approx(2.0)
    assert feats.cooccurrence_degree_max == pytest.approx(2.0)
    assert feats.cooccurrence_isolated_fraction == pytest.approx(0.0)
    assert feats.tautology_clause_fraction == pytest.approx(0.0)
    assert feats.duplicate_clause_fraction == pytest.approx(0.0)


def test_empty_formula_is_all_zeros_except_isolated():
    feats = extract_features_from_clauses(4, [])
    assert feats.n_vars == 4
    assert feats.n_clauses == 0
    assert feats.alpha == pytest.approx(0.0)
    assert feats.clause_len_mean == pytest.approx(0.0)
    assert feats.unit_clause_fraction == pytest.approx(0.0)
    assert feats.pos_literal_fraction == pytest.approx(0.0)
    assert feats.polarity_balance == pytest.approx(0.0)
    assert feats.var_occurrence_mean == pytest.approx(0.0)
    assert feats.var_occurrence_entropy == pytest.approx(0.0)
    assert feats.isolated_var_fraction == pytest.approx(1.0)
    assert feats.singleton_var_fraction == pytest.approx(0.0)
    assert feats.pure_literal_fraction == pytest.approx(0.0)
    assert feats.cooccurrence_isolated_fraction == pytest.approx(1.0)
    # No NaN / inf anywhere
    assert all(math.isfinite(v) for v in feats.to_dict().values())


def test_zero_vars_empty_formula():
    feats = extract_features_from_clauses(0, [])
    assert feats.alpha == pytest.approx(0.0)
    assert all(math.isfinite(v) for v in feats.to_dict().values())


def test_single_unit_clause():
    feats = extract_features_from_clauses(2, [[1]])
    assert feats.unit_clause_fraction == pytest.approx(1.0)
    assert feats.pos_literal_fraction == pytest.approx(1.0)
    assert feats.polarity_balance == pytest.approx(1.0)
    assert feats.isolated_var_fraction == pytest.approx(0.5)
    assert feats.singleton_var_fraction == pytest.approx(0.5)
    assert feats.pure_literal_fraction == pytest.approx(1.0)
    assert feats.cooccurrence_isolated_fraction == pytest.approx(1.0)


def test_all_negative_polarity():
    feats = extract_features_from_clauses(2, [[-1, -2], [-1]])
    assert feats.pos_literal_fraction == pytest.approx(0.0)
    assert feats.polarity_balance == pytest.approx(-1.0)
    # var1 occurs twice (both negative), var2 once (negative): both pure
    assert feats.pure_literal_fraction == pytest.approx(1.0)


def test_tautology_and_duplicate_clauses():
    feats = extract_features_from_clauses(
        2, [[1, -1, 2], [1, -1, 2], [2]]
    )
    assert feats.tautology_clause_fraction == pytest.approx(2 / 3)
    assert feats.duplicate_clause_fraction == pytest.approx(1 / 3)


def test_uniform_occurrence_entropy_is_maximal():
    # Four variables, each occurring exactly once: entropy = log2(4) = 2
    feats = extract_features_from_clauses(4, [[1], [2], [3], [4]])
    assert feats.var_occurrence_entropy == pytest.approx(2.0)
    assert feats.var_occurrence_entropy_norm == pytest.approx(1.0)
    assert feats.var_occurrence_cv == pytest.approx(0.0)


def test_cooccurrence_isolated_variable():
    # var3 never shares a clause with anyone
    feats = extract_features_from_clauses(3, [[1, 2], [3]])
    assert feats.cooccurrence_degree_mean == pytest.approx(2 / 3)
    assert feats.cooccurrence_degree_max == pytest.approx(1.0)
    assert feats.cooccurrence_isolated_fraction == pytest.approx(1 / 3)


def test_extract_features_accepts_cnf_instance():
    inst = CNFInstance(n_vars=3, clauses=[[1, 2, -3], [-1, 2], [1]])
    feats = extract_features(inst)
    assert feats.n_clauses == 3
    assert feats.alpha == pytest.approx(1.0)


def test_random_3sat_features_are_finite_and_in_range():
    inst = generate_random_3sat(n_vars=20, n_clauses=85, seed=7)
    feats = extract_features(inst)
    assert feats.alpha == pytest.approx(85 / 20)
    assert feats.ternary_clause_fraction == pytest.approx(1.0)
    assert feats.unit_clause_fraction == pytest.approx(0.0)
    d = feats.to_dict()
    assert list(d.keys()) == FEATURE_NAMES
    assert all(math.isfinite(v) for v in d.values())
    for name in (
        "unit_clause_fraction",
        "binary_clause_fraction",
        "ternary_clause_fraction",
        "pos_literal_fraction",
        "isolated_var_fraction",
        "pure_literal_fraction",
        "tautology_clause_fraction",
        "duplicate_clause_fraction",
        "var_occurrence_entropy_norm",
    ):
        assert 0.0 <= d[name] <= 1.0
    assert -1.0 <= d["polarity_balance"] <= 1.0
    assert d["var_occurrence_entropy"] <= math.log2(20) + 1e-9
    # Deterministic: same instance, same features
    assert extract_features(inst).to_dict() == d


def test_graph_coloring_cnf_features():
    g = generate_graph_coloring(n_vertices=4, edge_prob=0.5, k_colors=3, seed=3)
    feats = extract_features(g.to_cnf())
    assert feats.n_vars == 12
    assert feats.n_clauses > 0
    assert feats.alpha == pytest.approx(feats.n_clauses / 12)
    assert all(math.isfinite(v) for v in feats.to_dict().values())


def test_php_structured_instance_features():
    # Dee's PHP_3^(4): 4 pigeons x 3 holes = 12 vars; 4 ternary clauses
    # (one hole per pigeon) + 3 holes x C(4, 2) binary clauses = 22 total.
    from om_lab.hard_instances import generate_php

    feats = extract_features(generate_php(3))
    assert feats.n_vars == 12
    assert feats.n_clauses == 22
    assert feats.alpha == pytest.approx(22 / 12)
    assert feats.ternary_clause_fraction == pytest.approx(4 / 22)
    assert feats.binary_clause_fraction == pytest.approx(18 / 22)
    assert feats.unit_clause_fraction == pytest.approx(0.0)
    assert all(math.isfinite(v) for v in feats.to_dict().values())


def test_invalid_literals_raise():
    with pytest.raises(ValueError):
        extract_features_from_clauses(2, [[3]])
    with pytest.raises(ValueError):
        extract_features_from_clauses(2, [[0]])
    with pytest.raises(ValueError):
        extract_features_from_clauses(-1, [])
