"""Tests for om_lab.width_features and om_lab.analyze_width (OM-C001-R2).

Graph-fixture expectations are hand-computed from the Section 3.3
min-fill definition (smallest ``(fill, variable_id)`` first). M0/M1
expectations are hand-computed from the Section 3.8 definitions.
Synthetic analysis rows use explicit ``y`` values so the fitted
models can be checked arithmetically; they are not solver data and
are labelled synthetic wherever they are used.
"""

import hashlib
import math

import pytest

from om_lab.analyze_width import (
    A_VALUES,
    BUDGET_B,
    N_VALUES,
    analyze_rows,
    capped_log_effort,
    check_seed_manifest,
    clause_count,
    confirmatory_seed,
    evaluate,
    fit_degree_adjusted,
    fit_m0_m1,
    generate_pilot_rows,
    integrity_gates,
    paired_stratified_bootstrap,
    records_to_rows,
    seed_manifest,
    verification_gates,
    _reproducibility,
)
from om_lab.generators import generate_random_3sat
from om_lab.hard_instances import generate_php
from om_lab.width_features import (
    primal_graph,
    primal_min_fill_width,
    replay_elimination_order,
)


# ---------------------------------------------------------------------------
# Section 3.3 graph fixtures
# ---------------------------------------------------------------------------


def test_fixture_table():
    cases = [
        # (n_vars, clauses, expected width)
        (0, [], 0),  # empty graph
        (4, [], 0),  # isolated vertices
        (2, [[1, 2]], 1),  # single edge
        (4, [[1, 2], [2, 3], [3, 4]], 1),  # path, >= 2 vertices
        (4, [[1, 2], [2, 3], [3, 4], [4, 1]], 2),  # cycle C4, >= 3 vertices
        (3, [[1, 2], [2, 3], [3, 1]], 2),  # cycle C3 == K3
        (3, [[1, 2, 3]], 2),  # K3
        (4, [[1, 2, 3, 4]], 3),  # K4
        (5, [[1, 2, 3, 4, 5]], 4),  # K5
    ]
    for n, clauses, expected in cases:
        result = primal_min_fill_width(n, clauses)
        assert result.width == expected, (n, clauses, result)
        assert sorted(result.ordering) == list(range(1, n + 1))
        assert replay_elimination_order(n, clauses, result.ordering) == expected


def test_hand_computed_orderings():
    # Path 1-2-3-4: leaves have fill 0, so 1 goes first, then 2, 3, 4.
    assert primal_min_fill_width(4, [[1, 2], [2, 3], [3, 4]]).ordering == (1, 2, 3, 4)
    # Cycle C4: every vertex has fill 1; smallest id first, then the
    # filled triangle eliminates in id order. Width 2.
    assert primal_min_fill_width(
        4, [[1, 2], [2, 3], [3, 4], [4, 1]]
    ).ordering == (1, 2, 3, 4)
    # Star centred at 1: leaves have fill 0 and go first (smallest id
    # first); after two leaves are gone, the centre (neighbours {4},
    # fill 0) ties with the last leaf (fill 0) and wins on smallest
    # id, so it goes third, then the last leaf. Width 1.
    assert primal_min_fill_width(
        4, [[1, 2], [1, 3], [1, 4]]
    ).ordering == (2, 3, 1, 4)
    assert primal_min_fill_width(4, [[1, 2], [1, 3], [1, 4]]).width == 1
    # K4: every vertex has fill 0 (neighbours form a clique), so id
    # order; the first eliminated vertex has degree 3.
    assert primal_min_fill_width(4, [[1, 2, 3, 4]]).ordering == (1, 2, 3, 4)


def test_repeatability_and_isolated_variables():
    clauses = [[1, 2], [2, 3], [3, 4]]
    first = primal_min_fill_width(6, clauses)
    second = primal_min_fill_width(6, clauses)
    assert first == second
    # Variables 5 and 6 are isolated; they are still vertices, they
    # appear in the ordering, and they do not raise the width.
    assert first.width == 1
    assert set(first.ordering) == {1, 2, 3, 4, 5, 6}


def test_clause_order_sign_and_duplicate_invariance():
    base = [[1, 2, -3], [-1, 2], [1, -3]]
    expected = primal_min_fill_width(3, base)
    # Clause order shuffled.
    assert primal_min_fill_width(3, [[1, -3], [1, 2, -3], [-1, 2]]) == expected
    # All literal signs flipped.
    assert primal_min_fill_width(3, [[-1, -2, 3], [1, -2], [-1, 3]]) == expected
    # Duplicate clauses added.
    assert primal_min_fill_width(3, base + base) == expected
    # A tautology clause [1, -1] adds no new primal edge beyond 1's
    # existing edges, and a duplicate literal adds none.
    assert primal_min_fill_width(3, base + [[1, -1]]) == expected


def test_primal_graph_includes_isolated_and_ignores_signs():
    adj = primal_graph(4, [[1, -2], [2, 3]])
    assert adj == {1: {2}, 2: {1, 3}, 3: {2}, 4: set()}
    with pytest.raises(ValueError):
        primal_graph(2, [[3]])
    with pytest.raises(ValueError):
        primal_graph(2, [[0]])


def test_replay_rejects_bad_orderings():
    clauses = [[1, 2], [2, 3]]
    with pytest.raises(ValueError):
        replay_elimination_order(3, clauses, (1, 2, 2))  # duplicate
    with pytest.raises(ValueError):
        replay_elimination_order(3, clauses, (1, 2))  # missing vertex
    with pytest.raises(ValueError):
        replay_elimination_order(3, clauses, (1, 2, 4))  # out of range
    with pytest.raises(ValueError):
        replay_elimination_order(3, clauses, (1, 2, 3, 1))  # too long


def test_replay_agrees_on_random_and_php_instances():
    for seed in range(5):
        inst = generate_random_3sat(n_vars=12, n_clauses=40, seed=seed)
        result = primal_min_fill_width(inst.n_vars, inst.clauses)
        assert replay_elimination_order(
            inst.n_vars, inst.clauses, result.ordering
        ) == result.width
    php = generate_php(3)
    result = primal_min_fill_width(php.n_vars, php.clauses)
    assert replay_elimination_order(
        php.n_vars, php.clauses, result.ordering
    ) == result.width


def test_relabelling_changes_ordering_and_can_change_width():
    # Ordering: reversing the IDs of a random 3-SAT instance changes
    # the tie-broken ordering (width happens to stay 4 here).
    inst = generate_random_3sat(n_vars=6, n_clauses=10, seed=0)
    perm = {v: 7 - v for v in range(1, 7)}
    relabelled = [
        [perm[abs(l)] if l > 0 else -perm[abs(l)] for l in c]
        for c in inst.clauses
    ]
    o0 = primal_min_fill_width(6, inst.clauses).ordering
    o1 = primal_min_fill_width(6, relabelled).ordering
    o1_back = tuple(perm[v] for v in o1)  # map back: new id -> old id
    # perm is its own inverse here, so mapping back uses the same dict.
    assert o0 != o1_back
    # Width itself is not a relabelling invariant either: this sparse
    # graph (binary clauses = edges) has width 3, and width 2 after
    # the stated relabelling. Same graph up to isomorphism.
    edges = [
        (1, 2), (1, 3), (1, 6), (2, 5), (2, 6), (3, 4),
        (3, 6), (4, 7), (5, 8), (6, 7), (6, 8), (8, 9),
    ]
    clauses = [[u, v] for u, v in edges]
    assert primal_min_fill_width(9, clauses).width == 3
    relabel_map = {old: new for old, new in zip(range(1, 10), [5, 4, 6, 8, 2, 3, 7, 9, 1])}
    clauses2 = [[relabel_map[u], relabel_map[v]] for u, v in edges]
    assert primal_min_fill_width(9, clauses2).width == 2


# ---------------------------------------------------------------------------
# Section 3.4 / 3.5 seeds
# ---------------------------------------------------------------------------


def test_clause_count_formula():
    assert clause_count(30, 426) == 128
    assert clause_count(30, 380) == 114
    assert clause_count(40, 426) == 170
    assert clause_count(60, 500) == 300
    assert clause_count(50, 400) == 200


def test_confirmatory_seed_matches_sha256_spec():
    # Independent recomputation from the spec text, not from the
    # implementation under test.
    material = "OM-C001-R2|30|426|7"
    expected = int.from_bytes(
        hashlib.sha256(material.encode("utf-8")).digest()[:16],
        byteorder="big",
        signed=False,
    )
    assert confirmatory_seed(30, 426, 7) == expected
    assert confirmatory_seed(30, 426, 7) == confirmatory_seed(30, 426, 7)
    assert confirmatory_seed(30, 426, 7) != confirmatory_seed(30, 426, 8)


def test_seed_manifest_shape_and_collisions():
    manifest = seed_manifest()
    assert len(manifest) == 2800
    checks = check_seed_manifest(manifest)
    assert checks["n_distinct_seeds"] == 2800
    assert checks["has_collision"] is False
    assert checks["disjoint_from_phase1_scheme"] is True
    assert sum(1 for r in manifest if r["split"] == "train") == 1960
    assert sum(1 for r in manifest if r["split"] == "test") == 840


# ---------------------------------------------------------------------------
# Synthetic rows for the frozen models (hand-computed)
# ---------------------------------------------------------------------------


def _current_repro_manifest():
    """A reproducibility manifest built from the current environment,
    so confirmatory-shaped tests pass the DEE-R9-18 gate (which
    compares the NumPy version and source hashes against the frozen
    manifest). The gate's failure modes are tested separately."""
    rep = _reproducibility("confirmatory")
    return {
        "environment": {"packages": {"numpy": rep["numpy_version"]}},
        "source_sha256": dict(rep["source_file_sha256"]),
    }


def _row(n, m, split, width, degree, y, index=0, status="SAT"):
    return {
        "n": n,
        "m": m,
        "a_hundredths": None,
        "index": index,
        "split": split,
        "seed": index,
        "width": width,
        "degree_mean": degree,
        "decisions": 0,
        "timed_out": False,
        "satisfiable": status == "SAT",
        "status": status,
        "verified": True,
        "verification_status": (
            "SAT_WITNESS_CHECKED"
            if status == "SAT"
            else "UNSAT_SOLVER_AGREEMENT_ONLY"
        ),
        "y": y,
        "width_reversed": None,
    }


def test_capped_log_effort():
    assert capped_log_effort(0, False) == pytest.approx(0.0)
    assert capped_log_effort(9, False) == pytest.approx(math.log(10))
    assert capped_log_effort(9999, False) == pytest.approx(math.log(10000))
    # Budget-exhausted runs are capped, even if D < B is recorded.
    assert capped_log_effort(500, True) == pytest.approx(math.log1p(BUDGET_B))
    assert capped_log_effort(99999, False) == pytest.approx(math.log1p(BUDGET_B))


def test_m0_m1_hand_computed_two_cells():
    # Cell A: (W,Y) = (10,1),(12,2),(14,3); cell B: (20,4),(22,5).
    # Centred sums: A Sxy=4, Sxx=8; B Sxy=1, Sxx=2; beta = 5/10 = 0.5.
    train = [
        _row(30, 120, "train", 10, 5.0, 1.0, index=0),
        _row(30, 120, "train", 12, 5.0, 2.0, index=1),
        _row(30, 120, "train", 14, 5.0, 3.0, index=2),
        _row(40, 160, "train", 20, 5.0, 4.0, index=0),
        _row(40, 160, "train", 22, 5.0, 5.0, index=1),
    ]
    fit = fit_m0_m1(train)
    assert fit["beta"] == pytest.approx(0.5)
    assert fit["cell_mean_y"][(30, 120)] == pytest.approx(2.0)
    assert fit["cell_mean_y"][(40, 160)] == pytest.approx(4.5)
    test = [
        _row(30, 120, "test", 13, 5.0, 2.5, index=70),
        _row(40, 160, "test", 23, 5.0, 6.0, index=70),
    ]
    fit_deg = fit_degree_adjusted(train)
    ev = evaluate(test, fit, fit_deg)
    # M0: |2.5-2| + |6-4.5| over 2 = 1.0. M1: 2.5 and 5.5 -> 0.25.
    assert ev["mae_m0"] == pytest.approx(1.0)
    assert ev["mae_m1"] == pytest.approx(0.25)
    assert ev["improvement"] == pytest.approx(0.75)
    # Degree is constant in training, so M2/M3 are unidentifiable.
    assert ev["mae_m2"] is None
    assert ev["mae_m3"] is None


def test_fit_uses_training_rows_only_no_leakage():
    train = [
        _row(30, 120, "train", 10, 5.0, 1.0, index=0),
        _row(30, 120, "train", 14, 5.0, 3.0, index=1),
    ]
    fit_before = fit_m0_m1(train)
    # Perturb test rows arbitrarily; refitting on the same training
    # rows must give identical cell means and slope.
    fit_after = fit_m0_m1(train)
    assert fit_before == fit_after
    # And a test row with an extreme width/Y does not enter the fit:
    # its M1 prediction is the training cell mean plus beta * centred
    # width, with beta from training only (beta = ( -2*-1 + 2*1 ) / 8 = 0.5).
    assert fit_before["beta"] == pytest.approx(0.5)


def test_slope_denominator_zero_is_inconclusive_not_a_new_proxy():
    # Width is constant within the only training cell.
    train = [
        _row(30, 120, "train", 21, 5.0, 1.0, index=0),
        _row(30, 120, "train", 21, 5.0, 2.0, index=1),
    ]
    test = [_row(30, 120, "test", 21, 5.0, 1.5, index=70)]
    fit = fit_m0_m1(train)
    assert fit["beta"] is None
    summary = analyze_rows(train + test, "synthetic", bootstrap_replicates=50)
    assert summary["primary_disposition"]["disposition"] == "INCONCLUSIVE"
    assert any(
        "denominator" in r for r in summary["primary_disposition"]["reasons"]
    )
    assert summary["evaluation"] is None


def test_degree_adjusted_m2_hand_computed_and_m3_singular():
    # Y tracks degree exactly: degree 10->2, 12->4, 14->6 (beta_d = 1).
    train = [
        _row(30, 120, "train", 21, 10.0, 2.0, index=0),
        _row(30, 120, "train", 21, 12.0, 4.0, index=1),
        _row(30, 120, "train", 21, 14.0, 6.0, index=2),
    ]
    fit_deg = fit_degree_adjusted(train)
    assert fit_deg["m2_beta_degree"] == pytest.approx(1.0)
    # Width is constant, so the M3 system is singular.
    assert fit_deg["m3"]["singular"] is True
    # Degree and width perfectly collinear -> also singular.
    train2 = [
        _row(30, 120, "train", 20, 10.0, 2.0, index=0),
        _row(30, 120, "train", 21, 11.0, 3.0, index=1),
        _row(30, 120, "train", 22, 12.0, 4.0, index=2),
    ]
    assert fit_degree_adjusted(train2)["m3"]["singular"] is True


def test_bootstrap_is_deterministic_for_a_fixed_seed():
    # Paired errors from the two-cell hand-computed example, repeated
    # to give two cells of test rows.
    train = [
        _row(30, 120, "train", 10, 5.0, 1.0, index=0),
        _row(30, 120, "train", 12, 5.0, 2.0, index=1),
        _row(30, 120, "train", 14, 5.0, 3.0, index=2),
    ]
    test = [
        _row(30, 120, "test", 13, 5.0, 2.5, index=70 + i) for i in range(6)
    ]
    fit = fit_m0_m1(train)
    ev = evaluate(test, fit, fit_degree_adjusted(train))
    b1 = paired_stratified_bootstrap(ev["paired"], replicates=200, seed=9012026)
    b2 = paired_stratified_bootstrap(ev["paired"], replicates=200, seed=9012026)
    assert b1 == b2
    assert b1["n_defined"] == 200
    assert b1["n_undefined"] == 0
    assert b1["ci_lower_2.5"] <= b1["ci_upper_97.5"]


def _synthetic_population(signal: str, n_cells=4, n_train=20, n_test=30):
    """Deterministic synthetic population.

    ``signal="width"``: Y = cell mean + 0.5 * centred width + tiny
    noise, so M1 should pass. ``signal="none"``: Y = cell mean +
    balanced +/-0.1 noise orthogonal to width, so beta = 0 and M1
    cannot improve (FAIL). All rows are SAT with checked witnesses,
    so the verification gate passes.
    """
    import random

    rng = random.Random(42)
    rows = []
    for c in range(n_cells):
        n, m = 30 + 10 * c, 120 + 40 * c
        cell_mean = 2.0 + 0.5 * c
        for i in range(n_train + n_test):
            width = 20 + (i % 5)
            if signal == "width":
                y = cell_mean + 0.5 * (width - 22) + rng.uniform(-0.05, 0.05)
            else:  # "none": noise balanced across widths, beta == 0
                y = cell_mean + (0.1 if i % 2 == 0 else -0.1)
            rows.append(
                _row(
                    n, m,
                    "train" if i < n_train else "test",
                    width, 16.0, y, index=i,
                )
            )
    return rows


def _confirmatory_synthetic(signal: str, unsat_verification: str | None = None):
    """Full confirmatory-shaped synthetic population: 28 cells,
    70 train + 30 test per cell, 2800 rows.

    ``signal="width"``: Y = cell mean + 0.5 * centred width + tiny
    noise, so M1 should pass. ``signal="none"``: Y = cell mean +
    balanced +/-0.1 noise orthogonal to width over each 10-row
    period, so the fitted slope is exactly 0 and M1 cannot improve
    (FAIL). All rows are SAT with checked witnesses unless
    ``unsat_verification`` is given, in which case test rows are
    UNSAT with that verification status.
    """
    import random

    rng = random.Random(42)
    rows = []
    for c, (n, a) in enumerate([(n, a) for n in N_VALUES for a in A_VALUES]):
        m = clause_count(n, a)
        cell_mean = 2.0 + 0.1 * c
        for i in range(100):
            width = 20 + (i % 5)
            if signal == "width":
                y = cell_mean + 0.5 * (width - 22) + rng.uniform(-0.05, 0.05)
            else:  # "none"
                y = cell_mean + (0.1 if i % 2 == 0 else -0.1)
            split = "train" if i <= 69 else "test"
            status = "SAT"
            verification = "SAT_WITNESS_CHECKED"
            if split == "test" and unsat_verification is not None:
                status = "UNSAT"
                verification = unsat_verification
            rows.append(
                {
                    **_row(n, m, split, width, 16.0, y, index=i, status=status),
                    "a_hundredths": a,
                    "seed": c * 10_000 + i,
                    "verification_status": verification,
                }
            )
    return rows


def test_analyze_rows_pass_on_strong_width_signal():
    # A synthetic (non-confirmatory) population is INCONCLUSIVE by
    # construction; the PASS decision rule is tested on the full
    # confirmatory-shaped population.
    rows = _synthetic_population("width")
    summary = analyze_rows(rows, "synthetic", bootstrap_replicates=100)
    assert summary["primary_disposition"]["disposition"] == "INCONCLUSIVE"
    rows = _confirmatory_synthetic("width")
    summary = analyze_rows(rows, "confirmatory", bootstrap_replicates=200,
        reproducibility_manifest=_current_repro_manifest())
    assert summary["integrity_gates"]["passed"] is True
    assert summary["verification_gates"]["passed"] is True
    assert summary["primary_disposition"]["disposition"] == "PASS"
    assert summary["primary_disposition"]["point_improvement"] >= 0.05
    assert summary["primary_disposition"]["bootstrap_ci_lower_2.5"] > 0
    assert summary["evaluation"]["improvement"] is not None
    assert len(summary["evaluation"]["per_cell"]) == 28
    assert all(
        c["spearman_width_y"] is not None
        for c in summary["evaluation"]["per_cell"]
    )


def test_analyze_rows_fail_when_width_carries_no_signal():
    rows = _confirmatory_synthetic("none")
    summary = analyze_rows(rows, "confirmatory", bootstrap_replicates=200,
        reproducibility_manifest=_current_repro_manifest())
    assert summary["primary_disposition"]["disposition"] == "FAIL"
    assert summary["primary_disposition"]["point_improvement"] < 0.05
    assert summary["primary_disposition"]["point_improvement"] == pytest.approx(0.0)


def test_missing_training_cell_is_inconclusive():
    train = [_row(30, 120, "train", 10, 5.0, 1.0, index=0)]
    test = [_row(40, 160, "test", 10, 5.0, 1.0, index=70)]
    summary = analyze_rows(train + test, "synthetic", bootstrap_replicates=50)
    assert summary["primary_disposition"]["disposition"] == "INCONCLUSIVE"
    assert summary["integrity_gates"]["passed"] is False


def test_duplicate_rows_fail_integrity_gates():
    row = _row(30, 120, "train", 10, 5.0, 1.0, index=0)
    gates = integrity_gates([row, row], "synthetic")
    assert gates["passed"] is False
    assert any("duplicate" in f for f in gates["failures"])


def test_verification_gate_blocks_pass_for_uncertified_unsat():
    # Strong width signal, but every test row is UNSAT with only
    # solver-agreement verification: effort-only PASS, primary
    # INCONCLUSIVE.
    rows = _confirmatory_synthetic(
        "width", unsat_verification="UNSAT_SOLVER_AGREEMENT_ONLY"
    )
    summary = analyze_rows(rows, "confirmatory", bootstrap_replicates=200,
        reproducibility_manifest=_current_repro_manifest())
    assert summary["primary_disposition"]["disposition"] == "INCONCLUSIVE"
    assert summary["primary_disposition"]["effort_only_disposition"] == "PASS"
    assert summary["verification_gates"]["passed"] is False
    # The same rows with proof-checked UNSAT pass the gate and PASS.
    rows2 = _confirmatory_synthetic(
        "width", unsat_verification="UNSAT_PROOF_CHECKED"
    )
    summary2 = analyze_rows(rows2, "confirmatory", bootstrap_replicates=200,
        reproducibility_manifest=_current_repro_manifest())
    assert summary2["verification_gates"]["passed"] is True
    assert summary2["primary_disposition"]["disposition"] == "PASS"


def test_non_confirmatory_population_is_inconclusive_by_construction():
    rows = _synthetic_population("width")
    summary = analyze_rows(rows, "pilot", bootstrap_replicates=100)
    assert summary["primary_disposition"]["disposition"] == "INCONCLUSIVE"
    assert any(
        "not the frozen confirmatory population" in r
        for r in summary["primary_disposition"]["reasons"]
    )


def test_records_to_rows_regenerates_width_and_rejects_bad_records():
    records = [
        {
            "n_vars": 12,
            "n_clauses": 40,
            "seed": 7,
            "problem": "random_3sat",
            "index": 3,
            "split": "train",
            "decisions": 42,
            "timed_out": False,
            "satisfiable": True,
            "verified": True,
        }
    ]
    rows = records_to_rows(records)
    assert len(rows) == 1
    inst = generate_random_3sat(n_vars=12, n_clauses=40, seed=7)
    assert rows[0]["width"] == primal_min_fill_width(12, inst.clauses).width
    assert rows[0]["y"] == pytest.approx(math.log1p(42))
    assert rows[0]["status"] == "SAT"
    # A record with no seed and no width cannot be regenerated.
    with pytest.raises(ValueError):
        records_to_rows(
            [
                {
                    "n_vars": 12,
                    "n_clauses": 40,
                    "problem": "graph_coloring",
                    "index": 0,
                    "split": "train",
                    "decisions": 1,
                    "timed_out": False,
                    "satisfiable": True,
                    "verified": True,
                }
            ]
        )
    # A budget-exhausted record is UNKNOWN, never UNSAT.
    rows2 = records_to_rows(
        [
            {
                "n_vars": 12,
                "n_clauses": 40,
                "seed": 7,
                "problem": "random_3sat",
                "index": 70,
                "split": "test",
                "decisions": 10000,
                "timed_out": True,
                "satisfiable": False,
                "verified": False,
            }
        ]
    )
    assert rows2[0]["status"] == "UNKNOWN"
    assert rows2[0]["y"] == pytest.approx(math.log1p(BUDGET_B))


def test_generate_pilot_rows_smoke(tmp_path):
    rows = generate_pilot_rows(
        n_values=[30], a_values=[426], n_train=3, n_test=2
    )
    assert len(rows) == 5
    assert sum(1 for r in rows if r["split"] == "train") == 3
    assert sum(1 for r in rows if r["split"] == "test") == 2
    assert all(r["status"] in {"SAT", "UNSAT", "UNKNOWN"} for r in rows)
    assert all(r["width_reversed"] is not None for r in rows)
    # Pilot seeds are not confirmatory seeds.
    assert all(
        r["seed"] != confirmatory_seed(r["n"], r["a_hundredths"], r["index"])
        for r in rows
    )
    summary = analyze_rows(rows, "pilot", bootstrap_replicates=100)
    assert summary["primary_disposition"]["disposition"] == "INCONCLUSIVE"
    assert summary["evaluation"] is not None
    assert len(summary["evaluation"]["per_cell"]) == 1


# ---------------------------------------------------------------------------
# Phase 4 PR #9 repairs (Nova; Dee remains the reviewer of the fixes)
# ---------------------------------------------------------------------------


def _paired_fixture():
    """Paired test rows for bootstrap tests: cell A (2 rows) with
    err_m0=1, err_m1=1; cell B (4 rows) with err_m0=2, err_m1=0."""
    paired = []
    for (n, m), err0, err1, count in [
        ((30, 380), 1.0, 1.0, 2),
        ((40, 400), 2.0, 0.0, 4),
    ]:
        for k in range(count):
            paired.append(
                {
                    "n": n,
                    "m": m,
                    "err_m0": err0,
                    "err_m1": err1,
                }
            )
    return paired


def test_DEE_R9_17_bootstrap_is_equal_cell_weighted():
    # With constant errors per cell, every replicate gives the same
    # equal-cell-weighted improvement: 1 - 0.5/1.5 = 2/3. Row-weighted
    # would give 0.8.
    result = paired_stratified_bootstrap(
        _paired_fixture(), replicates=50, seed=123
    )
    assert result["n_defined"] == 50
    assert result["n_undefined"] == 0
    assert result["ci_lower_2.5"] == pytest.approx(2 / 3)
    assert result["ci_upper_97.5"] == pytest.approx(2 / 3)
    assert result["mean"] == pytest.approx(2 / 3)


def test_DEE_R9_17_bootstrap_samples_exactly_30_per_cell():
    # Section 3.10 fixes the per-cell resample size at 30,
    # regardless of the cell's size. Record the size argument of
    # every rng.integers call the bootstrap makes.
    import numpy as np
    from unittest import mock

    sizes: list[int] = []
    real_default_rng = np.random.default_rng

    def recording(seed):
        rng = real_default_rng(seed)

        class Rec:
            def integers(self, low, high=None, size=None, **kwargs):
                sizes.append(size)
                return rng.integers(low, high, size=size, **kwargs)

        return Rec()

    with mock.patch.object(np.random, "default_rng", side_effect=recording):
        paired_stratified_bootstrap(_paired_fixture(), replicates=3, seed=7)
    assert sizes, "expected the bootstrap to draw from the RNG"
    assert all(s == 30 for s in sizes), sizes
    assert len(sizes) == 3 * 2  # 3 replicates x 2 cells


def test_DEE_R9_18_reproducibility_gate_unevaluated_blocks_confirmatory():
    # No manifest supplied: the gate is unevaluated, which forces
    # INCONCLUSIVE for the confirmatory population even on a strong
    # width signal.
    rows = _confirmatory_synthetic("width")
    summary = analyze_rows(rows, "confirmatory", bootstrap_replicates=200)
    assert summary["reproducibility_gates"]["evaluated"] is False
    assert summary["reproducibility_gates"]["passed"] is False
    assert summary["primary_disposition"]["disposition"] == "INCONCLUSIVE"
    assert any(
        "reproducibility gate not evaluated" in r
        for r in summary["primary_disposition"]["reasons"]
    )


def test_DEE_R9_18_reproducibility_gate_fails_on_numpy_mismatch():
    rows = _confirmatory_synthetic("width")
    manifest = _current_repro_manifest()
    manifest["environment"]["packages"]["numpy"] = "0.0.0"
    summary = analyze_rows(
        rows, "confirmatory", bootstrap_replicates=200,
        reproducibility_manifest=manifest,
    )
    assert summary["reproducibility_gates"]["passed"] is False
    assert any(
        "numpy version differs" in f
        for f in summary["reproducibility_gates"]["failures"]
    )
    assert summary["primary_disposition"]["disposition"] == "INCONCLUSIVE"


def test_DEE_R9_18_reproducibility_gate_fails_on_source_hash_mismatch():
    rows = _confirmatory_synthetic("width")
    manifest = _current_repro_manifest()
    manifest["source_sha256"]["analyze_width.py"] = "0" * 64
    summary = analyze_rows(
        rows, "confirmatory", bootstrap_replicates=200,
        reproducibility_manifest=manifest,
    )
    assert summary["reproducibility_gates"]["passed"] is False
    assert any(
        "source hash differs for analyze_width.py" in f
        for f in summary["reproducibility_gates"]["failures"]
    )
    assert summary["primary_disposition"]["disposition"] == "INCONCLUSIVE"


def test_DEE_R9_02_bootstrap_none_reason_is_unavailable():
    # With a strong point improvement but no bootstrap, the reason
    # must say the bootstrap is unavailable, not that the interval
    # includes zero.
    from om_lab.analyze_width import primary_disposition

    out = primary_disposition(
        {"improvement": 0.5},
        None,
        {"passed": True, "failures": []},
        {"passed": True, "failures": []},
        {"beta": 1.0},
        eval_error="bootstrap exploded",
    )
    assert out["disposition"] == "INCONCLUSIVE"
    assert any("bootstrap unavailable" in r for r in out["reasons"])
    assert not any("includes zero" in r for r in out["reasons"])


def test_DEE_R9_19_effort_only_gated_on_integrity_gates():
    # Integrity gates failing force effort_only to INCONCLUSIVE even
    # when the point improvement is strong; verification-gate-only
    # failures still report the effort signal (see
    # test_verification_gate_blocks_pass_for_uncertified_unsat).
    from om_lab.analyze_width import primary_disposition

    out = primary_disposition(
        {"improvement": 0.5},
        {"ci_lower_2.5": 0.1, "ci_upper_97.5": 0.9, "n_undefined": 0},
        {"passed": False, "failures": ["duplicate seeds"]},
        {"passed": False, "failures": ["uncertified UNSAT"]},
        {"beta": 1.0},
    )
    assert out["disposition"] == "INCONCLUSIVE"
    assert out["effort_only_disposition"] == "INCONCLUSIVE"
