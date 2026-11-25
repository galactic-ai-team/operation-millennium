"""Adversarial runner-integrity attacks (Nova, Phase 4 attack on PR #10).

Each test demonstrates one hole in the OM-C001-R2 runner or in the
analysis interface it feeds. A test PASSES while the hole is present:
it is a regression test for the fix, and must be inverted or removed
when the hole is closed (the NOVA-R10-xx finding cited in each test
says what the fix has to change). Nothing here executes a
confirmatory test instance (indices 70-99): dry-runs, the
confirmatory train split with one instance, and pilot instances only.

Findings are also written up in docs/phase4/reviews/REVIEW_PR10_NOVA.md.

[Claim Level: Empirical Observation] for every result below.
"""

from __future__ import annotations

import json

import pytest

from om_lab.analyze_width import (
    analyze_rows,
    confirmatory_seed,
    make_row,
    records_to_rows,
    _reproducibility,
)
from om_lab.width_experiment import (
    A_VALUES,
    N_VALUES,
    ConfirmatoryRunNotAuthorized,
    audit_records,
    build_specs,
    check_confirmatory_authorization,
    clause_count,
    combine_results,
    draft_freeze_manifest,
    integrity_report,
    read_jsonl,
    run_instance,
    run_specs,
    run_split,
)
from om_lab.solvers import verify_cnf_assignment


# ---------------------------------------------------------------------------
# Freeze manifest (Section 8 / ADVERSARIAL_REVIEW_01 B4)
# ---------------------------------------------------------------------------


def _authorized_manifest(tmp_path):
    """A manifest that authorises the confirmatory test split, built
    from the draft by flipping exactly the coordinator fields."""
    manifest = draft_freeze_manifest()
    manifest["confirmatory_authorized"] = True
    manifest["authorized_by"] = "Lumi"
    manifest["authorized_at_utc"] = "2026-11-25T00:00:00+00:00"
    manifest["status"] = "FROZEN"
    path = tmp_path / "freeze.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path, manifest


def _tampered_manifest(tmp_path, mutate):
    _, manifest = _authorized_manifest(tmp_path)
    mutate(manifest)
    path = tmp_path / "freeze.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


def _flip_hex(value: str) -> str:
    return ("0" if value[0] != "0" else "1") + value[1:]


# Tampering the guard is specified to check: every one of these must
# be refused. (NOVA-R10-01 is about what it does NOT check.)
@pytest.mark.parametrize(
    "label,mutate",
    [
        ("draft", lambda m: m.update(confirmatory_authorized=False)),
        ("string-true", lambda m: m.update(confirmatory_authorized="true")),
        ("blank-authorized-by", lambda m: m.update(authorized_by="")),
        ("null-authorized-by", lambda m: m.update(authorized_by=None)),
        ("source-hash", lambda m: m.update(source_sha256={k: _flip_hex(v) for k, v in m["source_sha256"].items()})),
        ("function-hash", lambda m: m.update(function_sha256={k: _flip_hex(v) for k, v in m["function_sha256"].items()})),
        ("checker-hash", lambda m: m.update(checker_sha256=_flip_hex(m["checker_sha256"]))),
        ("seed-manifest-hash", lambda m: m.update(seed_manifest_sha256=_flip_hex(m["seed_manifest_sha256"]))),
        ("protocol-budget-b", lambda m: m["protocol"].update(budget_b=m["protocol"]["budget_b"] + 1)),
        ("protocol-max-seconds", lambda m: m["protocol"].update(max_seconds=60)),
        ("schema-version", lambda m: m.update(freeze_schema_version=99)),
        ("experiment", lambda m: m.update(experiment="OM-C001-R1")),
        ("python-3.11", lambda m: m["environment"].update(python_version="3.11.0")),
        ("python-sat-version", lambda m: m["environment"]["packages"].update(**{"python-sat": "0.0.0"})),
        ("numpy-version", lambda m: m["environment"]["packages"].update(numpy="0.0.0")),
    ],
)
def test_freeze_tampering_refused(tmp_path, label, mutate):
    path = _tampered_manifest(tmp_path, mutate)
    with pytest.raises(ConfirmatoryRunNotAuthorized):
        check_confirmatory_authorization(path)


def test_freeze_draft_refused(tmp_path):
    path = tmp_path / "freeze.json"
    path.write_text(json.dumps(draft_freeze_manifest(), indent=2), encoding="utf-8")
    with pytest.raises(ConfirmatoryRunNotAuthorized):
        check_confirmatory_authorization(path)


def test_freeze_missing_file_refused(tmp_path):
    with pytest.raises(ConfirmatoryRunNotAuthorized):
        check_confirmatory_authorization(tmp_path / "no-such-freeze.json")


# What the guard does NOT check: every one of these still authorises.
# Finding NOVA-R10-01: the guard does not meet B4 (exact code commit,
# clean tree, exact Python version + implementation, complete
# dependency manifest, protocol/amendment doc hashes, training-record
# and fitted-model hashes are all unchecked or absent).
@pytest.mark.parametrize(
    "label,mutate",
    [
        ("status-left-draft", lambda m: m.update(status="DRAFT")),
        ("authorized-at-null", lambda m: m.update(authorized_at_utc=None)),
        ("python-patch-differs", lambda m: m["environment"].update(python_version="3.12.9")),
        ("python-implementation-pypy", lambda m: m["environment"].update(python_implementation="PyPy")),
        ("platform-differs", lambda m: m["environment"].update(platform="other-platform-1.2.3")),
        ("matplotlib-version", lambda m: m["environment"]["packages"].update(matplotlib="0.0.0")),
        ("om-lab-version", lambda m: m["environment"]["packages"].update(**{"om-lab": "9.9.9"})),
        ("git-commit-zeroes", lambda m: m["git"].update(commit="0" * 40)),
        ("git-dirty", lambda m: m["git"].update(lab_dirty=True)),
        ("runner-version", lambda m: m.update(runner_version="9.9.9")),
    ],
)
def test_freeze_unchecked_fields_still_authorise(tmp_path, label, mutate):
    path = _tampered_manifest(tmp_path, mutate)
    result = check_confirmatory_authorization(path)
    assert result["authorized_by"] == "Lumi"


def test_freeze_manifest_has_no_b4_hash_fields(tmp_path):
    _, manifest = _authorized_manifest(tmp_path)
    for field in (
        "protocol_doc_sha256",
        "amendment_doc_sha256",
        "training_record_sha256",
        "fitted_model_sha256",
    ):
        assert field not in manifest, f"B4 field {field} unexpectedly present"


# ---------------------------------------------------------------------------
# Scheduling / completeness (Gate E)
# ---------------------------------------------------------------------------


def test_dry_run_subset_schedules_silently(tmp_path):
    # Finding NOVA-R10-02: Gate E says a dry run schedules exactly 840
    # confirmatory test instances. An authorised dry run with a single
    # index schedules 28 (one per cell) and raises no complaint.
    freeze, _ = _authorized_manifest(tmp_path)
    out = run_split(
        population="confirmatory", split="test", out_dir=tmp_path,
        dry_run=True, indices=[70], freeze_path=freeze,
    )
    assert out["dry_run"] is True
    assert out["n_instances"] == 28
    out = run_split(
        population="confirmatory", split="test", out_dir=tmp_path,
        dry_run=True, n_values=[30], a_values=[400], indices=[70],
        freeze_path=freeze,
    )
    assert out["n_instances"] == 1


def test_partial_confirmatory_train_run_looks_complete(tmp_path):
    # Finding NOVA-R10-03: a one-instance confirmatory train run
    # reports integrity passed=True and writes the same results file
    # name and manifest shape as a complete run. Nothing marks it
    # partial, so a later combine/analysis cannot tell it apart from
    # a complete run except by counting records.
    out = run_split(
        population="confirmatory", split="train", out_dir=tmp_path,
        n_values=[30], a_values=[426], indices=[0], workers=0,
    )
    assert out["integrity"]["passed"] is True
    assert out["integrity"]["n_records"] == 1
    assert out["integrity"]["n_expected"] == 1
    assert out["results_path"].endswith("confirmatory_train_results.jsonl")
    manifest = json.loads(open(out["run_manifest_path"], encoding="utf-8").read())
    assert manifest["population"] == "confirmatory"
    assert manifest["split"] == "train"
    assert "partial" not in json.dumps(manifest).lower()


def test_combine_partial_reports_integrity_passed(tmp_path):
    # Finding NOVA-R10-03 (continued): combine_results with
    # require_complete=False on a 1-of-1960 file reports integrity
    # passed=True with n_expected=1 and no failures, and the combined
    # file carries no partial marker.
    out = run_split(
        population="confirmatory", split="train", out_dir=tmp_path,
        n_values=[30], a_values=[426], indices=[0], workers=0,
    )
    combined = combine_results(
        [out["results_path"]], tmp_path / "combined.jsonl",
        population="confirmatory", require_complete=False,
    )
    assert combined["integrity"]["passed"] is True
    assert combined["integrity"]["n_expected"] == 1
    assert combined["integrity"]["failures"] == []


# ---------------------------------------------------------------------------
# Fault injection guard is only in the CLI wrapper (NOVA-R10-04)
# ---------------------------------------------------------------------------


def test_fault_injection_refused_by_run_split_for_confirmatory(tmp_path):
    with pytest.raises(ValueError, match="fault injection is refused"):
        run_split(
            population="confirmatory", split="train", out_dir=tmp_path,
            n_values=[30], a_values=[426], indices=[0], workers=0,
            fault_injection={"x": {"raise": True}},
        )


def test_fault_injection_applies_via_run_specs_for_confirmatory():
    # The guard lives in run_split, not in run_specs/run_instance:
    # a direct run_specs call with confirmatory specs and an injected
    # fault applies the fault (ERROR record after 2 attempts).
    spec = build_specs("confirmatory", "train", n_values=[30], a_values=[426], indices=[0])[0]
    out = run_specs(
        [spec], workers=0,
        fault_injection={spec.instance_id: {"raise": True}}, max_attempts=2,
    )
    assert out.records[0]["status"] == "ERROR"
    assert out.records[0]["error"]["attempts"] == 2
    assert len(out.failures) == 2


def test_watchdog_expires_a_sleeping_worker():
    # Negative result retained: the watchdog does fire. A worker that
    # sleeps 30 s with a 0.05 s watchdog is killed and the instance
    # becomes an ERROR record after one attempt.
    spec = build_specs("pilot", "train", n_values=[30], a_values=[426], indices=[0])[0]
    out = run_specs(
        [spec], workers=1, watchdog_s=0.05, max_attempts=1,
        fault_injection={spec.instance_id: {"sleep_s": 30}},
    )
    assert out.records[0]["status"] == "ERROR"
    assert out.records[0]["error"]["kind"] == "watchdog"


# ---------------------------------------------------------------------------
# integrity_report trusts verification claims (NOVA-R10-05, -06)
# ---------------------------------------------------------------------------


def _genuine_pilot_record(status_wanted, certify=False):
    for i in range(10):
        spec = build_specs("pilot", "train", n_values=[30], a_values=[426], indices=[i])[0]
        rec, _, _ = run_instance(spec, budget=10000, certify=certify)
        if rec["status"] == status_wanted:
            return spec, rec
    pytest.skip(f"no {status_wanted} pilot record in indices 0-9")


def _break_model(clauses, model):
    """Flip a variable that is the sole satisfier of some clause, so
    the model provably stops satisfying the formula. The model is a
    signed-literal list: variable ``v`` holds literal ``+v``/``-v``
    at position ``v - 1``."""
    for clause in clauses:
        true_lits = [lit for lit in clause if model[abs(lit) - 1] == lit]
        if len(true_lits) == 1:
            var = abs(true_lits[0])
            broken = list(model)
            broken[var - 1] = -broken[var - 1]
            assert not verify_cnf_assignment(clauses, broken)
            return broken
    pytest.skip("no clause with a unique satisfying literal")


def test_integrity_report_crashes_on_none_decisions():
    # Finding NOVA-R10-06: a non-ERROR record with decisions=None
    # raises TypeError instead of reporting a failure. The desired
    # behaviour is passed=False with a failure naming the record;
    # this test pins the current crash and must be inverted on fix.
    spec, rec = _genuine_pilot_record("SAT")
    rec = dict(rec, decisions=None)
    with pytest.raises(TypeError):
        integrity_report([rec], [spec], budget=10000)


def test_corrupted_sat_model_passes_integrity_but_fails_audit():
    # Finding NOVA-R10-05: run/combine-time integrity trusts the
    # stored verification claim and never re-checks the SAT model.
    # Only the separate audit re-verifies it.
    from om_lab.generators import generate_random_3sat

    spec, rec = _genuine_pilot_record("SAT")
    inst = generate_random_3sat(n_vars=spec.n, n_clauses=spec.m, seed=spec.seed)
    bad = dict(rec, model=_break_model(inst.clauses, rec["model"]))
    report = integrity_report([bad], [spec], budget=10000)
    assert report["passed"] is True
    assert report["failures"] == []
    audit = audit_records([bad], population="pilot", splits=["train"])
    assert any("stored SAT model fails re-verification" in f for f in audit["failures"])


def test_sat_with_invalid_verification_fails_integrity():
    # Control (negative result retained): a SAT record whose
    # verification is INVALID is correctly rejected by integrity.
    spec, rec = _genuine_pilot_record("SAT")
    bad = dict(rec, verification_status="INVALID", verified=False)
    report = integrity_report([bad], [spec], budget=10000)
    assert report["passed"] is False
    assert any("SAT record without a checked witness" in f for f in report["failures"])
    assert report["verification_gate_ready"] is False


def test_unsat_unverified_passes_integrity_but_gate_not_ready():
    # Control (negative result retained): an UNSAT record with
    # UNVERIFIED verification passes integrity (it makes no false
    # certified claim) but the verification gate is correctly not
    # ready.
    spec, rec = _genuine_pilot_record("UNSAT")
    assert rec["verification_status"] != "UNSAT_PROOF_CHECKED"
    rec = dict(rec, verification_status="UNVERIFIED", verified=False)
    report = integrity_report([rec], [spec], budget=10000)
    assert report["passed"] is True
    assert report["verification_gate_ready"] is False


def test_audit_recheck_flags_never_retained_certificate():
    # Finding NOVA-R10-07: audit with recheck_certificates=True on a
    # --no-certify UNSAT record reports "regenerated certificate
    # differs or is invalid" when no certificate was ever retained.
    # The stored certificate is absent, not different; the message
    # should distinguish the two cases.
    spec, rec = _genuine_pilot_record("UNSAT")
    assert rec["reference"] is None
    audit = audit_records(
        [rec], population="pilot", splits=["train"], recheck_certificates=True,
    )
    assert any("regenerated certificate differs or is invalid" in f for f in audit["failures"])


def test_read_jsonl_malformed_line_raises_raw_error(tmp_path):
    # Finding NOVA-R10-08 (minor): a malformed JSONL line raises a
    # raw json.JSONDecodeError instead of a validation failure naming
    # the file and line.
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"ok": true}\nnot json\n', encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        read_jsonl(bad)


# ---------------------------------------------------------------------------
# records_to_rows type coercion (B5.2; NOVA-R10-09, -10, -11)
# ---------------------------------------------------------------------------


def _legacy_record(**overrides):
    rec = {
        "n_vars": 30,
        "n_clauses": 128,
        "decisions": 7,
        "timed_out": False,
        "satisfiable": True,
        "verified": True,
        "width": 5,
        "degree_mean": 2.5,
        "split": "train",
        "index": 0,
        "a_hundredths": 426,
        "seed": 123,
    }
    rec.update(overrides)
    return rec


def test_records_to_rows_string_false_becomes_certified_sat():
    # Finding NOVA-R10-09: bool("false") is True in Python. A legacy
    # record (no explicit status) with satisfiable="false" and
    # verified="false" becomes a SAT row with a checked witness: a
    # fabricated certified SAT claim.
    rows = records_to_rows([_legacy_record(satisfiable="false", verified="false")])
    assert rows[0]["satisfiable"] is True
    assert rows[0]["verified"] is True
    assert rows[0]["verification_status"] == "SAT_WITNESS_CHECKED"


def test_records_to_rows_string_false_timed_out_becomes_unknown():
    # Finding NOVA-R10-09 (continued): timed_out="false" (string)
    # becomes True, so a completed SAT row is relabelled UNKNOWN.
    rows = records_to_rows([_legacy_record(timed_out="false")])
    assert rows[0]["timed_out"] is True
    assert rows[0]["status"] == "UNKNOWN"


def test_records_to_rows_explicit_status_missing_satisfiable_crashes():
    # Finding NOVA-R10-10: an explicit status with no "satisfiable"
    # key raises an unhandled KeyError instead of a validation error.
    rec = _legacy_record(status="SAT")
    del rec["satisfiable"]
    with pytest.raises(KeyError):
        records_to_rows([rec])


def test_records_to_rows_string_numbers_coerce_silently():
    # Finding NOVA-R10-11 (minor): string numbers are coerced without
    # complaint (decisions="7" -> 7), so a malformed record is silently
    # accepted instead of rejected.
    rows = records_to_rows([_legacy_record(decisions="7", n_vars="30")])
    assert rows[0]["decisions"] == 7
    assert rows[0]["n"] == 30


# ---------------------------------------------------------------------------
# Population identity is never validated in the analysis path (B5.1)
# ---------------------------------------------------------------------------


def _fabricated_confirmatory_rows(seed_fn):
    """28 cells x 70 train / 30 test rows with a strong width -> Y
    signal, labelled confirmatory, with seeds from ``seed_fn``."""
    rows = []
    for cell, (n, a) in enumerate([(n, a) for n in N_VALUES for a in A_VALUES]):
        m = clause_count(n, a)
        for i in range(100):
            split = "train" if i <= 69 else "test"
            width = 5 + (i % 11)
            decisions = 20 + 30 * width
            rows.append(make_row(
                n=n, m=m, a_hundredths=a, index=i, split=split,
                seed=seed_fn(cell, n, a, i), width=width,
                degree_mean=2.0 + (i % 5) * 0.1, decisions=decisions,
                timed_out=False, satisfiable=True, verified=True,
                verification_status="SAT_WITNESS_CHECKED",
            ))
    return rows


def _current_repro_manifest():
    """A reproducibility manifest built from the current environment,
    so the fabricated population passes the DEE-R9-18 gate. The gate
    checks the environment, not the population identity -- which is
    exactly the NOVA-R10-12 finding: the fabricated rows pass it."""
    rep = _reproducibility("confirmatory")
    return {
        "environment": {"packages": {"numpy": rep["numpy_version"]}},
        "source_sha256": dict(rep["source_file_sha256"]),
    }


def test_fabricated_confirmatory_population_gets_pass():
    # Finding NOVA-R10-12: the analysis path never checks experiment,
    # population, seed, formula hash, budget or schema against the
    # manifest, and never calls the runner audit. A synthetic
    # population with completely wrong seeds, labelled confirmatory,
    # gets disposition PASS with integrity passed -- even with a
    # valid reproducibility manifest, because that gate only checks
    # the environment.
    rows = _fabricated_confirmatory_rows(lambda cell, n, a, i: 10**9 + cell * 1000 + i)
    result = analyze_rows(
        rows, "confirmatory", bootstrap_replicates=200,
        reproducibility_manifest=_current_repro_manifest(),
    )
    assert result["integrity_gates"]["passed"] is True
    assert result["verification_gates"]["passed"] is True
    assert result["reproducibility_gates"]["passed"] is True
    assert result["primary_disposition"]["disposition"] == "PASS"
    assert result["primary_disposition"]["point_improvement"] > 0.05
    # Control: the identical rows with the true confirmatory seeds get
    # the identical disposition, proving the analysis never looks at
    # seeds at all.
    true_rows = _fabricated_confirmatory_rows(
        lambda cell, n, a, i: confirmatory_seed(n, a, i)
    )
    true_result = analyze_rows(
        true_rows, "confirmatory", bootstrap_replicates=200,
        reproducibility_manifest=_current_repro_manifest(),
    )
    assert true_result["primary_disposition"] == result["primary_disposition"]
    assert true_result["evaluation"] == result["evaluation"]


def test_make_row_lone_unsat_defaults_to_unverified():
    # Fixed in the accompanying PR #9 repair (DEE-R9-04 batch):
    # a lone DPLL UNSAT with no second solver is now labelled
    # UNVERIFIED, not UNSAT_SOLVER_AGREEMENT_ONLY -- no second
    # solver ran, so there is no agreement to report (NOVA-R10-13).
    row = make_row(
        n=30, m=128, a_hundredths=426, index=0, split="train", seed=1,
        width=5, degree_mean=2.0, decisions=10, timed_out=False,
        satisfiable=False, verified=False,
    )
    assert row["verification_status"] == "UNVERIFIED"
