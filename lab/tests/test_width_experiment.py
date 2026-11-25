"""Tests for the OM-C001-R2 runner (DISCOVERY_ROUND_01.md Sections 3.4-3.7, 4, 7.1, 9.2).

No test here solves a confirmatory *test* instance (indices 70-99 of the
confirmatory population). Solver runs use pilot seeds (Nova's pilot prefix)
or small hand-built formulas. The confirmatory test split is only touched
through the authorisation guard and ``dry_run`` (seed listing, no solving).

[Claim Level: Empirical Observation] for everything verified here.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import random

import pytest

import _reference_solvers_ed6d557 as ed6d557
from om_lab.analyze_width import BUDGET_B, records_to_rows
from om_lab.certify import label_unsat_claim, reference_certificate
from om_lab.generators import generate_random_3sat
from om_lab.hard_instances import generate_php, generate_planted_3sat
from om_lab.matched_instances import generate_matched_tseitin_pair, petersen_graph
from om_lab.proof_check import check_drat
from om_lab.solvers import (
    SolveResult,
    Status,
    StopReason,
    Verification,
    check_sat_witness,
    solve_dpll,
    verify_cnf_assignment,
)
from om_lab import width_experiment as wx


def _pilot_specs(n_values=(30,), a_values=(426, 500), indices=range(0, 4)):
    return wx.build_specs("pilot", "train", n_values=list(n_values), a_values=list(a_values), indices=indices)


def _lines(records):
    return [wx.canonical_json(r) for r in records]


# --------------------------------------------------------------------------
# Population construction (Sections 3.4-3.5)
# --------------------------------------------------------------------------


def test_seed_scheme_matches_preregistration_text():
    # Independent re-derivation of Section 3.5, not via analyze_width.
    for n, a, i in [(30, 380, 0), (40, 426, 69), (60, 500, 70), (50, 460, 99)]:
        material = f"OM-C001-R2|{n}|{a}|{i}".encode("utf-8")
        expected = int.from_bytes(hashlib.sha256(material).digest()[:16], "big", signed=False)
        split = "train" if i <= 69 else "test"
        (spec,) = wx.build_specs("confirmatory", split, n_values=[n], a_values=[a], indices=[i])
        assert spec.seed == expected
        assert spec.m == (a * n + 50) // 100
        assert spec.instance_id == f"OM-C001-R2|{n}|{a}|{i}"


def test_population_shape_and_disjointness():
    train = wx.build_specs("confirmatory", "train")
    test = wx.build_specs("confirmatory", "test")  # seeds only; nothing is solved
    assert len(train) == 4 * 7 * 70 == 1960
    assert len(test) == 4 * 7 * 30 == 840
    assert {s.index for s in train} == set(range(70))
    assert {s.index for s in test} == set(range(70, 100))
    ids = [s.instance_id for s in train + test]
    seeds = [s.seed for s in train + test]
    assert len(set(ids)) == len(ids) == 2800
    assert len(set(seeds)) == 2800
    pilot = wx.build_specs("pilot", "train")
    assert not {s.seed for s in pilot} & set(seeds)
    doc = wx.seed_manifest_document()
    assert len(doc["rows"]) == 2800
    assert not doc["checks"]["has_collision"]
    assert doc["checks"]["disjoint_from_phase1_scheme"]
    assert doc["checks"]["disjoint_from_pilot_prefix"]


def test_build_specs_refuses_cross_split_and_unfrozen_cells():
    with pytest.raises(ValueError):
        wx.build_specs("confirmatory", "train", indices=[70])
    with pytest.raises(ValueError):
        wx.build_specs("confirmatory", "test", indices=[69])
    with pytest.raises(ValueError):
        wx.build_specs("confirmatory", "train", n_values=[35])
    with pytest.raises(ValueError):
        wx.build_specs("confirmatory", "train", a_values=[450])
    with pytest.raises(ValueError):
        wx.build_specs("nope", "train")


# --------------------------------------------------------------------------
# Confirmatory boundary: "No confirmatory results are generated before the freeze"
# --------------------------------------------------------------------------


def _authorised_freeze(path: Path, **overrides) -> Path:
    doc = wx.draft_freeze_manifest()
    doc.update(confirmatory_authorized=True, authorized_by="test-only", status="FROZEN")
    doc.update(overrides)
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def test_confirmatory_test_split_refused_without_valid_freeze(tmp_path):
    out = tmp_path / "out"
    with pytest.raises(wx.ConfirmatoryRunNotAuthorized):
        wx.run_split(population="confirmatory", split="test", out_dir=out)
    draft = tmp_path / "draft.json"
    draft.write_text(json.dumps(wx.draft_freeze_manifest()), encoding="utf-8")
    with pytest.raises(wx.ConfirmatoryRunNotAuthorized, match="confirmatory_authorized"):
        wx.run_split(population="confirmatory", split="test", out_dir=out, freeze_path=draft)
    tampered_sources = dict(wx.source_hashes(), **{"solvers.py": "0" * 64})
    tampered = _authorised_freeze(tmp_path / "tampered.json", source_sha256=tampered_sources)
    with pytest.raises(wx.ConfirmatoryRunNotAuthorized, match="source hashes"):
        wx.run_split(population="confirmatory", split="test", out_dir=out, freeze_path=tampered)
    wrong_budget = _authorised_freeze(tmp_path / "budget.json", protocol={**wx.protocol_constants(), "budget_b": 20000})
    with pytest.raises(wx.ConfirmatoryRunNotAuthorized, match="protocol"):
        wx.run_split(population="confirmatory", split="test", out_dir=out, freeze_path=wrong_budget)
    no_signer = _authorised_freeze(tmp_path / "unsigned.json", authorized_by=" ")
    with pytest.raises(wx.ConfirmatoryRunNotAuthorized, match="authorized_by"):
        wx.run_split(population="confirmatory", split="test", out_dir=out, freeze_path=no_signer)
    assert not out.exists()  # nothing was generated by any refused attempt


def test_authorised_freeze_passes_guard_in_dry_run_only(tmp_path):
    freeze = _authorised_freeze(tmp_path / "freeze.json")
    summary = wx.run_split(
        population="confirmatory", split="test", out_dir=tmp_path / "out", freeze_path=freeze, dry_run=True
    )
    assert summary["dry_run"] and summary["n_instances"] == 840
    assert summary["authorization"]["authorized_by"] == "test-only"
    assert not (tmp_path / "out").exists()


def test_cli_refuses_confirmatory_test_split(tmp_path, capsys):
    code = wx.main(["run", "--split", "test", "--out-dir", str(tmp_path / "out")])
    assert code == 2
    assert "REFUSED" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


def test_confirmatory_protocol_cannot_be_weakened(tmp_path):
    with pytest.raises(ValueError, match="frozen"):
        wx.run_split(population="confirmatory", split="train", out_dir=tmp_path, budget=500, indices=[0])
    with pytest.raises(ValueError, match="certificates"):
        wx.run_split(population="confirmatory", split="train", out_dir=tmp_path, certify=False, indices=[0])
    with pytest.raises(ValueError, match="fault injection"):
        wx.run_split(population="confirmatory", split="train", out_dir=tmp_path, indices=[0],
                     fault_injection={"x": {"raise": True}})


# --------------------------------------------------------------------------
# Primary solver: preserved baseline and deterministic branch counts
# --------------------------------------------------------------------------


def test_primary_solver_reproduces_ed6d557_exactly():
    rng = random.Random(2026)
    compared = 0
    for _ in range(150):
        n = rng.randint(5, 40)
        m = rng.randint(0, 6 * n)
        inst = generate_random_3sat(n, m, seed=rng.getrandbits(64))
        budget = rng.choice([None, 0, 1, 2, 5, 20, 100])
        old = ed6d557.solve_dpll(n, inst.clauses, max_decisions=budget)
        new = solve_dpll(n, inst.clauses, max_decisions=budget)
        assert (new.satisfiable, new.timed_out, new.decisions, new.propagations, new.model) == (
            old.satisfiable, old.timed_out, old.decisions, old.propagations, old.model
        )
        compared += 1
    assert compared == 150


def test_runner_branch_counts_match_ed6d557_on_pilot_instances():
    specs = _pilot_specs(n_values=(30, 40), a_values=(426, 500), indices=range(0, 3))
    out = wx.run_specs(specs, workers=0)
    for spec, rec in zip(specs, out.records):
        inst = generate_random_3sat(spec.n, spec.m, seed=spec.seed)
        old = ed6d557.solve_dpll(spec.n, inst.clauses, max_decisions=BUDGET_B)
        assert rec["decisions"] == old.decisions
        assert rec["propagations"] == old.propagations
        assert rec["satisfiable"] == old.satisfiable


def test_repeated_runs_are_deterministic_inline_and_in_workers():
    specs = _pilot_specs(n_values=(30,), a_values=(426, 460), indices=range(0, 3))
    first = wx.run_specs(specs, workers=0)
    second = wx.run_specs(specs, workers=0)
    pooled = wx.run_specs(specs, workers=2)
    assert _lines(first.records) == _lines(second.records) == _lines(pooled.records)
    assert not first.failures and not pooled.failures


def test_budget_boundary_convention():
    # Find an instance needing at least 3 branch attempts when unbudgeted.
    for seed in range(200):
        inst = generate_random_3sat(30, 128, seed=seed)
        free = solve_dpll(30, inst.clauses)
        if free.decisions >= 3:
            break
    d = free.decisions
    at_budget = solve_dpll(30, inst.clauses, max_decisions=d)
    assert at_budget.status == Status.UNKNOWN and at_budget.decisions == d
    assert at_budget.stop_reason == StopReason.DECISION_BUDGET
    above = solve_dpll(30, inst.clauses, max_decisions=d + 1)
    assert (above.status, above.decisions, above.model) == (free.status, free.decisions, free.model)
    # B = 0 makes even the empty formula UNKNOWN (budget checked at entry).
    assert solve_dpll(3, [], max_decisions=0).status == Status.UNKNOWN


# --------------------------------------------------------------------------
# Records: schema, verification semantics, UNKNOWN handling, analysis hand-off
# --------------------------------------------------------------------------


def test_records_schema_and_verification():
    specs = _pilot_specs(n_values=(30, 60), a_values=(426, 500), indices=range(0, 4))
    out = wx.run_specs(specs, workers=0)
    statuses = set()
    for spec, rec in zip(specs, out.records):
        assert set(rec) == wx.RECORD_KEYS
        statuses.add(rec["status"])
        inst = generate_random_3sat(spec.n, spec.m, seed=spec.seed)
        assert rec["width"] == rec["width_replay"]
        assert rec["y"] == math.log1p(rec["decisions"])
        assert rec["reference_agreement"] == "AGREE"
        assert rec["integrity_alarm"] is None
        if rec["status"] == Status.SAT:
            assert verify_cnf_assignment(inst.clauses, rec["model"])
            assert rec["verification_status"] == Verification.SAT_WITNESS_CHECKED
        else:
            assert rec["status"] == Status.UNSAT
            assert rec["model"] is None
            assert rec["verification_status"] == Verification.UNSAT_PROOF_CHECKED
            assert rec["reference"]["certificate"]["result"] == "VALID"
        assert rec["verified"] is True
    assert statuses == {Status.SAT, Status.UNSAT}
    report = wx.integrity_report(out.records, specs, budget=BUDGET_B)
    assert report["passed"] and report["verification_gate_ready"]


def test_unknown_is_retained_and_never_unsat():
    specs = _pilot_specs(n_values=(60,), a_values=(426,), indices=range(0, 4))
    out = wx.run_specs(specs, budget=5, workers=0)
    unknown = [r for r in out.records if r["status"] == Status.UNKNOWN]
    assert len(unknown) == 4
    for rec in unknown:
        assert rec["decisions"] == 5 and rec["budget_exhausted"] and rec["timed_out"]
        assert rec["y"] == math.log1p(5)
        assert not rec["satisfiable"] and not rec["verified"]
        assert rec["verification_status"] == Verification.NOT_APPLICABLE
        # The reference run is retained for secondary analysis but never
        # changes the primary status.
        assert rec["reference"]["status"] in {Status.SAT, Status.UNSAT}
        assert rec["reference_agreement"] == "NOT_APPLICABLE"
    rows = records_to_rows(out.records)
    assert [r["status"] for r in rows] == [Status.UNKNOWN] * 4
    assert all(r["verification_status"] == Verification.NOT_APPLICABLE for r in rows)


def test_analysis_handoff_excludes_error_rows_and_rejects_contradictions():
    specs = _pilot_specs(n_values=(30,), a_values=(426,), indices=range(0, 2))
    out = wx.run_specs(specs, workers=0)
    error = wx.error_record(specs[0], budget=BUDGET_B, kind="watchdog", attempts=3, detail="test")
    with pytest.warns(UserWarning, match="ERROR record"):
        rows = records_to_rows([error, out.records[1]])
    assert len(rows) == 1 and rows[0]["index"] == specs[1].index  # ERROR is missing data, never UNSAT
    contradictory = dict(out.records[1], status="UNKNOWN")
    with pytest.raises(ValueError, match="contradicts"):
        records_to_rows([contradictory])


# --------------------------------------------------------------------------
# Infrastructure failures: watchdog, crash, exception -> same-instance reruns
# --------------------------------------------------------------------------


def test_watchdog_crash_and_exception_are_rerun_with_same_instance():
    specs = _pilot_specs(n_values=(30,), a_values=(426,), indices=range(0, 4))
    ids = [s.instance_id for s in specs]
    faults = {
        ids[0]: {"sleep_s": 60, "fail_attempts": 1},   # watchdog kill, then succeeds
        ids[1]: {"exit_code": 13, "fail_attempts": 1},  # worker crash, then succeeds
        ids[2]: {"raise": True, "fail_attempts": 99},   # always fails -> ERROR
    }
    out = wx.run_specs(specs, workers=1, watchdog_s=3.0, max_attempts=2, fault_injection=faults)
    clean = wx.run_specs(specs, workers=0)
    assert [r["instance_id"] for r in out.records] == ids  # exactly one record each, in order
    assert _lines(out.records[:2]) == _lines(clean.records[:2])  # reruns reproduce the clean result
    assert out.records[3] == clean.records[3]
    error = out.records[2]
    assert error["status"] == Status.ERROR and error["y"] is None and error["decisions"] is None
    assert error["error"]["kind"] == "exception" and error["error"]["attempts"] == 2
    kinds = sorted((f["instance_id"], f["kind"]) for f in out.failures)
    assert kinds == sorted([(ids[0], "watchdog"), (ids[1], "worker_crash"), (ids[2], "exception"), (ids[2], "exception")])
    report = wx.integrity_report(out.records, specs, budget=BUDGET_B)
    assert report["n_records"] == report["n_expected"] == 4
    assert report["status_counts"][Status.ERROR] == 1
    assert not report["verification_gate_ready"]


# --------------------------------------------------------------------------
# Section 4.3 regression cases, mapped one-to-one
# --------------------------------------------------------------------------


def test_section_4_3_regression_cases():
    # Empty CNF: SAT.
    empty = solve_dpll(3, [])
    assert empty.status == Status.SAT and empty.verification_status == Verification.SAT_WITNESS_CHECKED
    # CNF containing an empty clause: UNSAT, certified through the reference path.
    for clauses in ([[1, 2], []], [[1], [-1]]):  # ... and contradictory units
        primary = solve_dpll(2, clauses)
        reference, _ = reference_certificate(2, clauses)
        assert primary.status == Status.UNSAT
        assert label_unsat_claim(primary, reference) == Verification.UNSAT_PROOF_CHECKED
    # Budget exhaustion: UNKNOWN.
    inst = generate_random_3sat(40, 170, seed=11)
    assert solve_dpll(40, inst.clauses, max_decisions=2).status == Status.UNKNOWN
    # Satisfiable formula with corrupted model: INVALID.
    sat = solve_dpll(40, generate_random_3sat(40, 120, seed=1).clauses)
    corrupted = [-lit for lit in sat.model]
    assert check_sat_witness(generate_random_3sat(40, 120, seed=1).clauses, corrupted) == Verification.INVALID
    # UNSAT claim with corrupted certificate: INVALID.
    unsat_inst = next(
        g for g in (generate_random_3sat(20, 110, seed=s) for s in range(100))
        if solve_dpll(20, g.clauses).status == Status.UNSAT
    )
    reference, _ = reference_certificate(20, unsat_inst.clauses)
    proof = reference.certificate["proof"]
    assert not check_drat(unsat_inst.clauses, proof[:-1]).valid
    rejected = SolveResult(
        solver_name="ref", satisfiable=False, model=None, elapsed_s=0.0, decisions=0,
        propagations=0, verified=False, verification_status=Verification.INVALID,
    )
    assert label_unsat_claim(solve_dpll(20, unsat_inst.clauses), rejected) == Verification.INVALID
    # Planted formula with its planted assignment: SAT witness checked.
    planted = generate_planted_3sat(n_vars=40, n_clauses=200, seed=4)
    hidden = [int(v) if val else -int(v) for v, val in planted.metadata["hidden_assignment"].items()]
    assert check_sat_witness(planted.clauses, hidden) == Verification.SAT_WITNESS_CHECKED
    # Repeated deterministic run: matching status and branch counts.
    a = solve_dpll(40, inst.clauses, max_decisions=BUDGET_B)
    b = solve_dpll(40, inst.clauses, max_decisions=BUDGET_B)
    assert (a.status, a.decisions, a.propagations) == (b.status, b.decisions, b.propagations)


# --------------------------------------------------------------------------
# Section 9.2 solver attacks
# --------------------------------------------------------------------------


def test_section_9_2_solver_attacks():
    rng = random.Random(92)
    sensitivity = []
    for seed in range(12):
        inst = generate_random_3sat(30, 128, seed=seed)
        base = solve_dpll(30, inst.clauses)
        perm = list(range(1, 31))
        rng.shuffle(perm)
        relabelled = [[(perm[abs(l) - 1]) * (1 if l > 0 else -1) for l in c] for c in inst.clauses]
        reordered = list(inst.clauses)
        rng.shuffle(reordered)
        literal_reordered = [list(reversed(c)) for c in inst.clauses]
        for variant in (relabelled, reordered, literal_reordered):
            res = solve_dpll(30, variant)
            assert res.status == base.status  # satisfiability is invariant
            if res.status == Status.SAT:
                assert verify_cnf_assignment(variant, res.model)
            sensitivity.append(res.decisions - base.decisions)
    # Branch counts are NOT required to be invariant (heuristic depends on
    # IDs and order); this records that they do move, as data.
    assert any(delta != 0 for delta in sensitivity)
    # Known contradictory and planted instances.
    odd = generate_matched_tseitin_pair(petersen_graph()).odd
    assert solve_dpll(odd.n_vars, [list(c) for c in odd.clauses]).status == Status.UNSAT
    assert solve_dpll(12, generate_php(3).clauses).status == Status.UNSAT
    planted = generate_planted_3sat(n_vars=30, n_clauses=150, seed=9)
    assert solve_dpll(30, planted.clauses).status == Status.SAT


# --------------------------------------------------------------------------
# Outputs, combine, audit, freeze draft, CLI
# --------------------------------------------------------------------------


def test_run_split_combine_and_audit_roundtrip(tmp_path):
    kwargs = dict(population="pilot", n_values=[30], a_values=[426, 500], workers=0)
    train = wx.run_split(split="train", out_dir=tmp_path, indices=range(0, 3), **kwargs)
    test = wx.run_split(split="test", out_dir=tmp_path, indices=range(70, 72), **kwargs)  # pilot test: no freeze needed
    assert train["integrity"]["passed"] and test["integrity"]["passed"]
    manifest = json.loads(Path(train["run_manifest_path"]).read_text())
    assert manifest["results_sha256"] == train["results_sha256"]
    assert set(manifest["source_sha256"]) == set(wx.FROZEN_SOURCE_FILES)
    combined = wx.combine_results(
        [train["results_path"], test["results_path"]], tmp_path / "results.jsonl",
        population="pilot", require_complete=False,
    )
    assert combined["integrity"]["n_records"] == 10
    records = wx.read_jsonl(combined["results_path"])
    audit = wx.audit_records(
        records, population="pilot", splits=["train", "test"],
        recompute_features=True, recheck_certificates=True,
    )
    # Coverage is checked against the full pilot splits, so the subset run
    # reports missing instances; every per-record check must pass.
    per_record = [f for f in audit["failures"] if "expected instance" not in f]
    assert per_record == []
    tampered = [dict(r) for r in records]
    sat_idx = next(i for i, r in enumerate(tampered) if r["status"] == Status.SAT)
    tampered[sat_idx]["model"] = [-lit for lit in tampered[sat_idx]["model"]]
    tampered[0]["formula_sha256"] = "0" * 64
    bad = wx.audit_records(tampered, population="pilot", splits=["train", "test"])
    assert any("fails re-verification" in f for f in bad["failures"])
    assert any("formula hash" in f for f in bad["failures"])


def test_combine_refuses_duplicates(tmp_path):
    run = wx.run_split(population="pilot", split="train", out_dir=tmp_path, n_values=[30], a_values=[426],
                       indices=range(0, 2), workers=0)
    with pytest.raises(ValueError, match="more than one primary record"):
        wx.combine_results([run["results_path"], run["results_path"]], tmp_path / "dup.jsonl",
                           population="pilot", require_complete=False)


def test_draft_freeze_manifest_is_unauthorised_and_complete():
    doc = wx.draft_freeze_manifest()
    assert doc["confirmatory_authorized"] is False and doc["authorized_by"] is None
    assert set(doc["source_sha256"]) == set(wx.FROZEN_SOURCE_FILES)
    assert "solvers.solve_dpll" in doc["function_sha256"]
    assert doc["protocol"]["budget_b"] == 10000 and doc["protocol"]["max_seconds"] is None
    assert doc["protocol"]["max_total_branch_attempts"] == 28_000_000
    assert doc["seed_manifest_sha256"] == wx.seed_manifest_sha256()


def test_cli_seeds_freeze_and_pilot_run(tmp_path):
    assert wx.main(["seeds", "--out", str(tmp_path / "seeds.json")]) == 0
    assert len(json.loads((tmp_path / "seeds.json").read_text())["rows"]) == 2800
    assert wx.main(["freeze", "--out", str(tmp_path / "freeze.json")]) == 0
    code = wx.main([
        "run", "--population", "pilot", "--split", "train", "--n-values", "30", "--a-values", "426",
        "--indices", "0", "1", "--workers", "0", "--out-dir", str(tmp_path / "pilot"),
    ])
    assert code == 0
    assert (tmp_path / "pilot" / "pilot_train_results.jsonl").exists()
