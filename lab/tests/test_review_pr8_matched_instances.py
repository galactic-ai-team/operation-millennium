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

Gate B update (docs/phase4/reviews/REVIEW_PR24_CLAUDE.md): Dee's repair in
draft PR #24 (03b626d) fixes CLAUDE-R8-05/06/07/14/18 and the M16/M18 parts of
R8-09. The strict xfails for those findings XPASSed there; their markers are
removed and the tests that pinned the old behaviour now pin the repaired
behaviour. New Gate B findings are named CLAUDE-G24-NN.
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
    # Since PR #24 (03b626d): M01, M08, M10, M11, M16, M17 are rejected by
    # validate_metadata, and M04, M05, M18 are rejected by encode_tseitin.
    # Before the repair they were ACCEPTED_* (M18: REJECTED_BY_VALIDATOR).
    "M01": r8.REJECTED_BY_VALIDATOR, "M02": r8.REJECTED_AT_CONSTRUCTION, "M03": r8.REJECTED_AT_CONSTRUCTION,
    "M04": r8.REJECTED_AT_CONSTRUCTION, "M05": r8.REJECTED_AT_CONSTRUCTION, "M06": r8.ACCEPTED_CONSISTENT,
    "M07": r8.REJECTED_AT_CONSTRUCTION, "M08": r8.REJECTED_BY_VALIDATOR, "M09": r8.REJECTED_BY_VALIDATOR,
    "M10": r8.REJECTED_BY_VALIDATOR, "M11": r8.REJECTED_BY_VALIDATOR, "M12": r8.REJECTED_BY_VALIDATOR,
    "M13": r8.REJECTED_BY_VALIDATOR, "M14": r8.REJECTED_BY_VALIDATOR, "M15": r8.REJECTED_BY_VALIDATOR,
    "M16": r8.REJECTED_BY_VALIDATOR, "M17": r8.REJECTED_BY_VALIDATOR, "M18": r8.REJECTED_AT_CONSTRUCTION,
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


EXPECTED_REJECTION_REASONS = {  # PR #24: each repaired case is rejected for the right reason
    "M01": "clauses do not match", "M04": "must be int", "M05": "must be int", "M08": "n_vars",
    "M10": "clauses do not match", "M11": "clauses do not match", "M16": "family metadata mismatch",
    "M17": "clauses do not match", "M18": "cannot be overridden",
}


def test_g24_repaired_cases_are_rejected_for_the_right_reason(attack_matrix):
    for case_id, fragment in EXPECTED_REJECTION_REASONS.items():
        assert fragment in attack_matrix[case_id].rejected_by, (case_id, attack_matrix[case_id].rejected_by)


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
    # Still OPEN (Low): components() drops out-of-range edges, and the label
    # functions do not validate the graph, so the label flips if called anyway.
    assert notes["components_ignores_invalid_edges"] == ((0, 1, 2), (3, 4, 5))
    assert notes["dee_label_if_validate_graph_is_skipped"] == "UNSAT"
    assert notes["cnf_status"] == "SAT"
    # Repaired by PR #24 as a side effect of validate_encoding: validate_metadata
    # re-encodes, and the re-encode refuses the invalid endpoints.
    assert notes["validate_metadata_alone"] is False


def test_r8_05_pr10_certifier_rejects_integrity_attacks(attack_matrix):
    """PR #10's construction certifier re-encodes and compares. Since PR #24 Dee's
    validators reject these cases too; the certifier stays a second line of
    defence and must still reject them. Only legitimate cases are accepted now."""
    from om_lab.certify import certify_tseitin_by_construction

    for case_id in ("M01", "M08", "M10", "M11", "M16", "M17"):
        inst = attack_matrix[case_id].instance
        assert inst is not None, case_id
        status = str(certify_tseitin_by_construction(inst)["verification_status"])
        assert status == "INVALID", (case_id, status)
    statuses = r8.certifier_on_accepted_attacks(list(attack_matrix.values()))
    assert set(statuses) == {"M06", *EXPECTED_A5_LABELS}
    assert statuses["M06"] == "NOT_APPLICABLE"
    for case_id, label in EXPECTED_A5_LABELS.items():
        expected = "UNSAT_KNOWN_BY_CONSTRUCTION" if label == "UNSAT" else "NOT_APPLICABLE"
        assert statuses[case_id] == expected, (case_id, statuses[case_id])


def test_r8_07_unbounded_edge_ids_are_capped():
    """Repaired by PR #24: ids above MAX_DECLARED_VARS (10**6) are refused; the cap itself is allowed."""
    with pytest.raises(ValueError, match="MAX_DECLARED_VARS"):
        mi.encode_tseitin(mi.k4(), (0, 0, 0, 0), edge_ids=(1, 2, 3, 4, 5, 10**7))
    inst = mi.encode_tseitin(mi.k4(), (0, 0, 0, 0), edge_ids=(1, 2, 3, 4, 5, mi.MAX_DECLARED_VARS))
    assert inst.n_vars == mi.MAX_DECLARED_VARS == 10**6


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


# CLAUDE-R8-05/06/07 and the M16 part of R8-09, repaired by PR #24 (03b626d):
# Dee's instance-level validators (validate_graph + validate_metadata) or
# encode_tseitin now reject every malformed case that was accepted before.
@pytest.mark.parametrize("case_id", ["M01", "M04", "M05", "M08", "M10", "M11", "M16", "M17"])
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


def test_r8_14_dee_pair_assertions_now_catch_the_broken_encoder():
    """Repaired by PR #24: the generator asserts A3 signatures and catches the review's mutation."""
    probe = r8.mutation_probe()
    assert probe["dee_pair_assertions"] == "raised: matched pair occurrence profiles differ"
    assert mi.xor3_clauses is r8.mi.xor3_clauses  # the probe restored the original encoder
    assert mi.xor3_clauses(1, 2, 3, 1)[0] == (1, 2, 3)


def test_g24_02_signature_preserving_xor3_mutations_pass_the_generator():
    """CLAUDE-G24-02: the limit Dee states. A bug that keeps every A3 signature
    passes the pair assertions; ``sign_swap`` even makes the odd member SAT while
    it is labelled UNSAT. The docstrings that say such a mutation "cannot
    silently pass" overstate the check. This test flips if a semantic self-check
    of xor3_clauses is added; then update it."""
    rows = r8.xor3_signature_preserving_mutations()
    swap, flip = rows["sign_swap"], rows["parity_flip"]
    assert swap["generator_raised"] is None and swap["a3_all_equal"] is True
    assert swap["odd"]["declared_label"] == "UNSAT" and swap["odd"]["cnf_status"] == "SAT"
    assert swap["odd"]["decodes_to_exact_xor"] is False
    assert flip["generator_raised"] is None and flip["a3_all_equal"] is True
    assert mi.xor3_clauses is r8.mi.xor3_clauses


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


def test_r8_18_single_canonical_min_fill():
    inst = generate_random_3sat(11, 23, seed=172)
    assert _dee_width(11, inst.clauses) == primal_min_fill_width(11, inst.clauses).width


def test_r8_18_former_disagreements_now_agree():
    """Repaired by PR #24: min_fill_width_estimate delegates to the canonical
    implementation (rulings A1, B6). Before the repair these gave (8, 7) and (7, 6)."""
    for n, m, seed in ((11, 23, 172), (9, 24, 965)):
        inst = generate_random_3sat(n, m, seed=seed)
        assert _dee_width(n, inst.clauses) == primal_min_fill_width(n, inst.clauses).width
    probe = r8.minfill_random_probe(seeds=range(200))
    assert probe["compared"] == 200 and probe["disagreements"] == 0


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


# --------------------------------------------------------------------------
# Gate B re-attack of Dee's repair (draft PR #24, 03b626d): CLAUDE-G24-NN
# --------------------------------------------------------------------------


def test_g24_validators_accept_every_legitimate_instance():
    """No over-rejection: validate_metadata now re-encodes, so every legitimate
    instance must still pass (CI-sized; the CLI runs the full sweep)."""
    result = r8.validators_accept_legitimate_instances(full=False)
    assert result["n_rejected"] == 0, result["rejected"]
    assert result["total"] == 1761


def test_g24_integrity_fuzz_rejects_every_structural_mutation():
    """6,000 random single mutations (clauses, charges, edge map, n_vars, graph):
    the validators accept only no-op mutations, extra metadata keys, and the two
    type-only gaps CLAUDE-G24-01 (float n_vars) and G24-04 (float charges)."""
    result = r8.integrity_fuzz()
    assert set(result["accepted_noncanonical_kinds"]) <= {"n_vars_float", "charges_float"}
    assert all(v["escaped_non_valueerror"] == 0 for v in result["by_kind"].values())
    assert sum(v["tried"] for v in result["by_kind"].values()) == 6000


@pytest.mark.xfail(strict=True, reason="CLAUDE-G24-01 OPEN: validate_metadata accepts a non-int n_vars")
def test_g24_01_non_integer_n_vars_is_rejected():
    """A hand-built copy of a valid instance with n_vars=6.0 passes validate_metadata,
    then solve_pysat, solve_dpll and primal_graph raise TypeError on it."""
    odd = mi.encode_tseitin(mi.k4(), (1, 0, 0, 0))
    with pytest.raises(ValueError):
        mi.validate_metadata(r8.replace(odd, n_vars=6.0))


def test_g24_01_consequence_is_a_downstream_type_error_not_a_wrong_label():
    rows = r8.pr24_type_probes()
    row = rows["n_vars_float"]
    assert row["is_parity_satisfiable"] is False  # the label is still right
    assert row["solve_pysat"] == row["solve_dpll"] == row["primal_graph"] == "raises TypeError"
    assert row["certify_tseitin_by_construction"] == "INVALID"
