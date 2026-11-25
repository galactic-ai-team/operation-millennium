"""Regression tests from Claude's Phase 4 review of Dee's PR #8 (matched_instances.py).

Review: docs/phase4/reviews/REVIEW_PR8_CLAUDE.md. Finding IDs are CLAUDE-R8-NN.
Attacked commit: PR #8 merge c8e61a7 (target files byte-identical at dev f398de6).

* Tests named ``test_*`` assert behaviour that holds now.
* Tests marked ``xfail(strict=True)`` encode the behaviour the review asks
  for on an OPEN finding. When Dee's repair lands they XPASS, strict mode
  turns that into a failure, and the marker must then be removed. A fix can
  never pass unnoticed, and an unfixed finding never turns CI red.

Everything verified here is [Claim Level: Empirical Observation] on the
listed graphs, charge vectors and seeds. This file runs a CI-sized subset;
``python -m om_lab.review_pr8 --out-dir ...`` runs the full review suite.
"""

from __future__ import annotations

import itertools
import math
import random

import pytest

import om_lab.matched_instances as mi
from om_lab import review_pr8 as r8
from om_lab.generators import generate_random_3sat
from om_lab.width_features import primal_min_fill_width


def _all_vectors(n):
    return [("".join(map(str, b)), b) for b in itertools.product((0, 1), repeat=n)]


# --------------------------------------------------------------------------
# CLAUDE-R8-01/02/03: legitimate instances vs the independent oracle
# --------------------------------------------------------------------------


def test_r8_03_dee_constructors_match_independent_definitions():
    results = r8.check_dee_constructors()
    registered_4v = results.pop("moebius_ladder(2) (registered 4-vertex ladder)")
    assert all(results.values()), results
    assert r8.girth(r8.g_petersen()) == 5  # cubic, 10 vertices, girth 5: the Petersen graph
    assert registered_4v is False  # CLAUDE-R8-04, pinned below


@pytest.mark.xfail(strict=True, reason="CLAUDE-R8-04 OPEN: moebius_ladder(2) rejects the registered 4-vertex ladder")
def test_r8_04_registered_4_vertex_moebius_ladder_is_generated():
    assert mi.moebius_ladder(2).edges == r8.g_moebius(2).edges


def test_r8_01_exhaustive_small_graphs_agree_five_ways():
    """Every charge vector, with DPLL as a fifth independent status source."""
    graphs = [r8.g_k4(), r8.g_k33(), r8.g_prism(3), r8.g_moebius(4), r8.g_union(r8.g_k4(), r8.g_k4())]
    result = r8.sweep(graphs, lambda g: _all_vectors(g.n), id_variants=("default", "shuffled", "sparse"), dpll=True)
    assert result["mismatches"] == []
    assert result["instances"] == 3 * (16 + 64 + 64 + 256 + 256)
    assert result["per_graph"]["K4+K4"] == {"n_vertices": 8, "n_edges": 12, "SAT": 192, "UNSAT": 576}


def test_r8_01_exhaustive_ten_vertex_graphs_agree():
    graphs = [r8.g_petersen(), r8.g_moebius(5), r8.g_prism(5), r8.g_union(r8.g_k4(), r8.g_k33())]
    result = r8.sweep(graphs, lambda g: _all_vectors(g.n), id_variants=("default",))
    assert result["mismatches"] == []
    assert result["instances"] == 4 * 1024
    assert result["per_graph"]["petersen"]["SAT"] == 512  # connected: exactly the even-charge half


def test_r8_02_seed_suite_larger_graphs_agree():
    graphs = [r8.g_moebius(6), r8.g_moebius(12), r8.g_moebius(16), r8.g_union(r8.g_petersen(), r8.g_petersen())]
    result = r8.sweep(graphs, r8.seed_suite_charge_vectors, id_variants=("default",))
    assert result["mismatches"] == []


def test_seed_suite_vectors_are_documented_and_deterministic():
    g = r8.g_moebius(6)
    first = r8.seed_suite_charge_vectors(g)
    assert first == r8.seed_suite_charge_vectors(g)
    labels = [label for label, _ in first]
    assert labels[0] == "zero" and labels[-1] == "seed:31" and len(first) == 1 + 12 + 1 + 32


# --------------------------------------------------------------------------
# CLAUDE-R8-11/12: rejected malformed inputs and disconnected parity cases
# --------------------------------------------------------------------------

EXPECTED_CLASSIFICATION = {
    "M01": r8.ACCEPTED_INCONSISTENT, "M02": r8.REJECTED_AT_CONSTRUCTION, "M03": r8.REJECTED_AT_CONSTRUCTION,
    "M04": r8.ACCEPTED_DOWNSTREAM_FAILURE, "M05": r8.ACCEPTED_DOWNSTREAM_FAILURE, "M06": r8.ACCEPTED_CONSISTENT,
    "M07": r8.REJECTED_AT_CONSTRUCTION, "M08": r8.ACCEPTED_INCONSISTENT, "M09": r8.REJECTED_BY_VALIDATOR,
    "M10": r8.ACCEPTED_MISLABELED, "M11": r8.ACCEPTED_INCONSISTENT, "M12": r8.REJECTED_BY_VALIDATOR,
    "M13": r8.REJECTED_BY_VALIDATOR, "M14": r8.REJECTED_BY_VALIDATOR, "M15": r8.REJECTED_BY_VALIDATOR,
    "M16": r8.ACCEPTED_CONSISTENT, "M17": r8.ACCEPTED_MISLABELED, "M18": r8.REJECTED_BY_VALIDATOR,
    "M19": r8.REJECTED_AT_CONSTRUCTION, "M20": r8.REJECTED_AT_CONSTRUCTION, "M21": r8.REJECTED_BY_VALIDATOR,
    "M22": r8.REJECTED_AT_CONSTRUCTION, "M23": r8.REJECTED_AT_CONSTRUCTION, "M24": r8.REJECTED_AT_CONSTRUCTION,
    "M25": r8.REJECTED_AT_CONSTRUCTION, "M26": r8.ACCEPTED_CONSISTENT, "M27": r8.ACCEPTED_CONSISTENT,
    "M28": r8.ACCEPTED_CONSISTENT, "M29": r8.ACCEPTED_CONSISTENT, "M30": r8.ACCEPTED_CONSISTENT,
    "M31": r8.REJECTED_AT_CONSTRUCTION, "M32": r8.REJECTED_AT_CONSTRUCTION, "M33": r8.REJECTED_AT_CONSTRUCTION,
}


@pytest.fixture(scope="module")
def attack_matrix():
    return {o.case_id: o for o in r8.malformed_cases()}


def test_attack_matrix_matches_review_table(attack_matrix):
    assert {k: o.classification for k, o in attack_matrix.items()} == EXPECTED_CLASSIFICATION


EXPECTED_A5_LABELS = {"M26": "UNSAT", "M27": "SAT", "M28": "UNSAT", "M29": "SAT", "M30": "SAT"}


def test_r8_12_disconnected_and_a5_cases_are_labelled_correctly(attack_matrix):
    for case_id, status in EXPECTED_A5_LABELS.items():
        outcome = attack_matrix[case_id]
        assert outcome.dee_label == outcome.cnf_status == status, case_id
        assert outcome.encoding_matches, case_id


def test_r8_06_swapped_edge_map_makes_dee_reject_a_genuine_model(attack_matrix):
    notes = attack_matrix["M01"].notes
    assert notes["genuine_cnf_model_satisfies_clauses"] is True
    assert notes["dee_validate_tseitin_assignment_on_that_model"] is False


def test_r8_08_components_drop_invalid_edges_and_flip_the_label(attack_matrix):
    notes = attack_matrix["M21"].notes
    assert notes["components_ignores_invalid_edges"] == ((0, 1, 2), (3, 4, 5))
    assert notes["validate_metadata_alone"] is True
    assert notes["dee_label_if_validate_graph_is_skipped"] == "UNSAT"
    assert notes["cnf_status"] == "SAT"


def test_r8_05_pr10_certifier_rejects_integrity_attacks(attack_matrix):
    """PR #10's construction certifier re-encodes and compares, so it rejects the
    integrity attacks that Dee's validators accept, and certifies no accepted
    malformed case as UNSAT."""
    statuses = r8.certifier_on_accepted_attacks(list(attack_matrix.values()))
    for case_id in ("M01", "M08", "M10", "M11", "M17"):
        assert statuses[case_id] == "INVALID", (case_id, statuses[case_id])
    malformed = ("M01", "M04", "M05", "M08", "M10", "M11", "M16", "M17")
    assert all(statuses[c] != "UNSAT_KNOWN_BY_CONSTRUCTION" for c in malformed), statuses
    for case_id, label in EXPECTED_A5_LABELS.items():
        expected = "UNSAT_KNOWN_BY_CONSTRUCTION" if label == "UNSAT" else "NOT_APPLICABLE"
        assert statuses[case_id] == expected, (case_id, statuses[case_id])


def test_r8_07_unbounded_edge_ids_declare_unused_variables():
    inst = mi.encode_tseitin(mi.k4(), (0, 0, 0, 0), edge_ids=(1, 2, 3, 4, 5, 10**7))
    assert inst.n_vars == 10**7  # primal_graph / min_fill would allocate one entry per declared variable


def test_r8_09_metadata_dict_is_mutable_inside_frozen_instance():
    inst = mi.encode_tseitin(mi.k4(), (0, 0, 0, 0))
    inst.metadata["charge_sum_mod2"] = 1  # no error although the dataclass is frozen
    with pytest.raises(ValueError, match="charge_sum_mod2"):
        mi.validate_metadata(inst)


def test_r8_23_solver_effort_verified_is_false_for_unsat():
    pytest.importorskip("pysat")
    odd = mi.generate_matched_tseitin_pair(mi.k4()).odd
    record = mi.solver_effort(odd)
    assert record["satisfiable"] is False and record["verified"] is False


# Desired behaviour for the OPEN malformed-input findings (CLAUDE-R8-05/06/07):
# Dee's instance-level validators (validate_graph + validate_metadata) should
# reject these, or the module should classify them explicitly outside its
# contract. Review section 4 lists both resolution paths.
@pytest.mark.parametrize("case_id", ["M01", "M04", "M05", "M08", "M10", "M11", "M17"])
@pytest.mark.xfail(strict=True, reason="CLAUDE-R8-05/06/07 OPEN: accepted malformed instance")
def test_malformed_instances_are_rejected(attack_matrix, case_id):
    assert attack_matrix[case_id].classification in (r8.REJECTED_AT_CONSTRUCTION, r8.REJECTED_BY_VALIDATOR)


# --------------------------------------------------------------------------
# CLAUDE-R8-13/14: A3 signatures, and the vacuity of the in-generator check
# --------------------------------------------------------------------------


def test_r8_13_a3_signatures_equal_on_every_matched_pair():
    graphs = [r8.g_k4(), r8.g_k33(), r8.g_prism(3), r8.g_moebius(4), r8.g_prism(4)]
    result = r8.a3_pair_sweep(graphs)
    assert result["failures"] == []
    assert result["pairs"] == 8 * 4 + 32 * 6 + 32 * 6 + 128 * 8 + 128 * 8


def test_r8_14_dee_pair_assertions_miss_a_broken_encoder_that_a3_catches():
    probe = r8.mutation_probe()
    assert probe["dee_pair_assertions"] == "passed"
    assert probe["a3_detects"] is True
    assert mi.xor3_clauses is r8.mi.xor3_clauses  # the probe restored the original encoder
    assert mi.xor3_clauses(1, 2, 3, 1)[0] == (1, 2, 3)


# --------------------------------------------------------------------------
# CLAUDE-R8-15/16: registered permutation suite (A2) and A6 statistics
# --------------------------------------------------------------------------


def test_registered_permutation_definition_matches_ruling_a2():
    pi, rho = r8.registered_permutation(6, 24, 100)
    expected_pi = [1, 2, 3, 4, 5, 6]
    random.Random(200).shuffle(expected_pi)
    expected_rho = list(range(24))
    random.Random(201).shuffle(expected_rho)
    assert (pi, rho) == (expected_pi, expected_rho)
    clauses = [(1, -2, 3), (-4, 5, 6)]
    permuted = r8.apply_permutation(clauses, [2, 1, 4, 3, 6, 5], [1, 0])
    assert permuted == [(-3, 6, 5), (2, -1, 4)]  # literal order and signs preserved


def test_r8_15_permutation_suite_smoke():
    log, summary = r8.run_permutation_suite(vertex_counts=(4, 6, 8, 12), seeds=range(100, 106))
    assert summary["status_failures"] == []
    assert len(log) == 4 * 3 * 7
    assert all(r["isomorphism_witnessed"] and r["dpll_reproducible"] for r in log)
    assert all(r["witness_transformed_ok"] for r in log if r["oracle_sat"])
    assert all(len(r["pi"]) == 3 * r["vertex_count"] // 2 and len(r["rho"]) == 4 * r["vertex_count"] for r in log)


def test_r8_16_observed_branch_counts_on_registered_ladders():
    """Empirical Observation on these sizes and seeds only (see the next test)."""
    log, summary = r8.run_permutation_suite(vertex_counts=(6, 8, 10), seeds=range(100, 104), repeat_for_reproducibility=False)
    for row in log:
        k = row["vertex_count"] // 2
        r = k + 1  # cycle rank of a connected cubic graph on 2k vertices
        expected = 2 ** (r + 1) - 2 if row["variant"] == "one" else r
        assert row["dpll_decisions"] == expected
    assert all(cell["R"] == 1.0 for cell in summary["cells"])


def test_r8_16_cycle_rank_pattern_fails_on_other_cubic_graphs():
    """The ladder pattern r / 2^(r+1) - 2 is not a property of cubic Tseitin formulas."""
    rows = {row["graph"]: row for row in r8.cycle_rank_counterexamples()}
    a, b = rows["G10a"], rows["G10b"]
    assert a["connected"] and b["connected"] and a["cycle_rank"] == b["cycle_rank"] == 6
    assert a["sat"] and a["identity_decisions"] == 6 and a["registered_seed_decisions"] == [6, 10]
    assert not b["sat"] and b["identity_decisions"] == 126 and b["registered_seed_decisions"] == [126, 130, 138, 162]
    for name in ("G10a", "G10b"):
        g = r8.Graph(name, 10, r8.CYCLE_RANK_COUNTEREXAMPLES[name][0])
        assert r8.girth(g) == 3
        for i in range(len(g.edges)):  # bridgeless: removing any edge keeps the graph connected
            assert len(r8.components_of(10, g.edges[:i] + g.edges[i + 1:])) == 1


# --------------------------------------------------------------------------
# CLAUDE-R8-17: vertex-permutation metamorphic transform
# --------------------------------------------------------------------------


def test_r8_17_permute_matched_pair_is_a_correct_relabelling():
    for g in (r8.g_k4(), r8.g_petersen()):
        for perm in (mi.rotation_permutation(g.n, 1), mi.reverse_permutation(g.n)):
            assert r8.check_vertex_permutation_metamorphic(g, perm)["relabelling_correct"]


@pytest.mark.xfail(strict=True, reason="CLAUDE-R8-17 OPEN: induced edge-ID bijection is not recorded (A2)")
def test_r8_17_permute_matched_pair_records_edge_bijection():
    g = r8.g_k4()
    assert r8.check_vertex_permutation_metamorphic(g, mi.rotation_permutation(4, 1))["edge_bijection_recorded"]


# --------------------------------------------------------------------------
# CLAUDE-R8-18: duplicate min-fill implementation (ruling A1)
# --------------------------------------------------------------------------


def _dee_width(n, clauses):
    stub = mi.encode_tseitin(mi.k4(), (0, 0, 0, 0))
    return mi.min_fill_width_estimate(r8.replace(stub, n_vars=n, clauses=tuple(map(tuple, clauses))))


def test_r8_18_duplicate_min_fill_agrees_on_registered_tseitin_family():
    result = r8.minfill_comparison()
    assert result["compared"] == 9 * 21 and result["disagreements"] == 0


@pytest.mark.xfail(strict=True, reason="CLAUDE-R8-18 OPEN: two production min-fill implementations disagree (A1)")
def test_r8_18_single_canonical_min_fill():
    inst = generate_random_3sat(11, 23, seed=172)
    assert _dee_width(11, inst.clauses) == primal_min_fill_width(11, inst.clauses).width


def test_r8_18_concrete_disagreement_is_reproducible():
    inst = generate_random_3sat(11, 23, seed=172)
    assert (_dee_width(11, inst.clauses), primal_min_fill_width(11, inst.clauses).width) == (8, 7)


# --------------------------------------------------------------------------
# CLAUDE-R8-20/21: Lean fixture correspondence; Moebius width-bound constructions
# --------------------------------------------------------------------------


def test_r8_20_python_xor3_encoders_match_lean_fixtures():
    result = r8.lean_fixture_check()
    if not result["available"]:
        pytest.skip("lean/Millennium/Tseitin.lean not present in this checkout")
    assert result["matched_instances.xor3_clauses"] and result["hard_instances._xor3_clauses"]


def test_r8_21_moebius_path_decompositions_valid_on_registered_sizes():
    result = r8.moebius_decomposition_check()
    for row in result["results"]:
        assert row["ladder_decomposition_valid"] and row["ladder_width"] <= 5, row
        assert row["primal_decomposition_valid"] and row["primal_width"] <= 17, row
        assert row["nova_min_fill_width_identity"] <= row["primal_width"], row
    assert {row["vertex_count"] for row in result["results"]} == set(r8.REGISTERED_MOEBIUS_VERTEX_COUNTS)


def test_y_definition_used_in_a6_statistics():
    log, _ = r8.run_permutation_suite(vertex_counts=(24,), seeds=(100,), repeat_for_reproducibility=False)
    odd = next(r for r in log if r["variant"] == "one" and r["seed"] == 100)
    assert odd["budget_hit"] and odd["dpll_status"] == "UNKNOWN"
    assert odd["y"] == math.log1p(r8.PERMUTATION_SUITE_BUDGET)
