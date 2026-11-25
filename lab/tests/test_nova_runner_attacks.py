"""Adversarial runner-integrity attacks (Nova, Phase 4 attack on PR #10).

Each test demonstrates one hole in the OM-C001-R2 runner or in the
analysis interface it feeds. A test PASSES while the hole is present:
it is a regression test for the fix, and must be inverted or removed
when the hole is closed (the NOVA-R10-xx finding cited in each test
says what the fix has to change). Nothing here executes a
confirmatory test instance (indices 70-99): dry-runs, the
confirmatory train split with one instance, and pilot instances only.

Findings are also written up in docs/phase4/reviews/REVIEW_PR10_NOVA.md.

Phase 4 Gate B/D repair (Claude, for Nova's review): the runner holes
NOVA-R10-01 to -08 are closed, so their pins are inverted below; each
inverted test says "Inverted by Claude" and keeps Nova's original attack.
The full matrix for the two-stage freeze, exact population and retained
certificates is in tests/test_freeze_enforcement.py. The records_to_rows
pins (NOVA-R10-09 onwards, Nova's lane) are unchanged.

[Claim Level: Empirical Observation] for every result below.
"""

from __future__ import annotations

import json
import sys

import pytest

from _freeze_fixtures import build_training_base, clean_provenance, make_case, sha256_file
from om_lab.analyze_width import (
    analyze_rows,
    confirmatory_seed,
    fit_fingerprint,
    fit_m0_m1,
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


# What the old guard did NOT check (NOVA-R10-01: exact code commit, clean
# tree, exact Python version + implementation, complete dependency
# manifest, protocol/amendment doc hashes, training-record and
# fitted-model hashes were unchecked or absent).
#
# Inverted by Claude (Phase 4 Gate B/D): a schema-1 manifest no longer
# authorises anything, and each formerly unchecked field is checked by the
# two-stage freeze. Each case pairs Nova's schema-1 mutation with the
# equivalent Stage A / Stage B / running-environment change.
@pytest.fixture(scope="module")
def two_stage_base(tmp_path_factory):
    base = tmp_path_factory.mktemp("nova_two_stage")
    build_training_base(base)
    return base


@pytest.fixture(scope="module")
def two_stage_provenance():
    return clean_provenance()


@pytest.fixture
def two_stage(tmp_path, monkeypatch, two_stage_base, two_stage_provenance):
    return make_case(tmp_path / "two_stage", monkeypatch, two_stage_base, two_stage_provenance)


_PATCH_999 = "%d.%d.999" % sys.version_info[:2]


@pytest.mark.parametrize(
    "label,mutate,two_stage_mutate,match",
    [
        ("status-left-draft", lambda m: m.update(status="DRAFT"),
         lambda c: c.edit_stage_b(lambda b: b.update(status="DRAFT")), "not FROZEN"),
        ("authorized-at-null", lambda m: m.update(authorized_at_utc=None),
         lambda c: c.edit_stage_b(lambda b: b.update(authorized_at_utc=None)), "authorized_at_utc"),
        ("python-patch-differs", lambda m: m["environment"].update(python_version=_PATCH_999),
         lambda c: c.live.provenance["python"].update(version=_PATCH_999), "exact Python version"),
        ("python-implementation-pypy", lambda m: m["environment"].update(python_implementation="PyPy"),
         lambda c: c.live.provenance["python"].update(implementation="PyPy"), "Python implementation"),
        ("platform-differs", lambda m: m["environment"].update(platform="other-platform-1.2.3"),
         lambda c: c.live.provenance["platform"].update(machine="other-arch"), "architecture"),
        ("matplotlib-version", lambda m: m["environment"]["packages"].update(matplotlib="0.0.0"),
         lambda c: c.live.provenance["packages"].update(matplotlib="0.0.0"), "installed dependencies differ"),
        ("om-lab-version", lambda m: m["environment"]["packages"].update(**{"om-lab": "9.9.9"}),
         lambda c: c.live.provenance["packages"].update({"om-lab": "9.9.9"}), "installed dependencies differ"),
        ("git-commit-zeroes", lambda m: m["git"].update(commit="0" * 40),
         lambda c: c.edit_stage_a(lambda a: a["code"].update(commit="0" * 40)), "not in this checkout"),
        ("git-dirty", lambda m: m["git"].update(lab_dirty=True),
         lambda c: c.live.provenance["git"].update(tree_clean=False, dirty=[" M lab/om_lab/solvers.py"]),
         "dirty now"),
        ("runner-version", lambda m: m.update(runner_version="9.9.9"),
         lambda c: c.edit_stage_a(lambda a: a.update(runner_version="9.9.9")), "runner_version differs"),
    ],
)
def test_freeze_formerly_unchecked_fields_now_refused(tmp_path, two_stage, label, mutate, two_stage_mutate, match):
    path = _tampered_manifest(tmp_path, mutate)
    with pytest.raises(ConfirmatoryRunNotAuthorized):
        check_confirmatory_authorization(path)
    two_stage_mutate(two_stage)
    with pytest.raises(ConfirmatoryRunNotAuthorized, match=match):
        two_stage.verify(deep_training=False)


def test_stage_a_has_the_b4_hash_fields(two_stage):
    # Inverted by Claude: the B4 hashes are in Stage A (the schema-1 draft is
    # a provenance snapshot only) and equal the hashes of the files.
    stage_a = two_stage.stage_a_doc()
    assert len(stage_a["documents"]["protocol"]["sha256"]) == 64  # protocol doc
    assert stage_a["documents"]["amendments"] and all(  # amendment docs
        len(a["sha256"]) == 64 for a in stage_a["documents"]["amendments"]
    )
    assert stage_a["training"]["records_sha256"] == sha256_file(two_stage.records_path)  # training records
    assert stage_a["model"]["sha256"] == sha256_file(two_stage.model)  # fitted model


# ---------------------------------------------------------------------------
# Scheduling / completeness (Gate E)
# ---------------------------------------------------------------------------


def test_dry_run_subset_is_refused(tmp_path):
    # Finding NOVA-R10-02: Gate E says a dry run schedules exactly 840
    # confirmatory test instances. Inverted by Claude: a subset of the
    # confirmatory test split is refused, dry run or not, with or without a
    # freeze; only the full 840-instance schedule is listed.
    freeze, _ = _authorized_manifest(tmp_path)
    for subset in (dict(indices=[70]), dict(n_values=[30], a_values=[400], indices=[70])):
        with pytest.raises(ConfirmatoryRunNotAuthorized):
            run_split(population="confirmatory", split="test", out_dir=tmp_path, dry_run=True,
                      freeze_path=freeze, **subset)
        with pytest.raises(ConfirmatoryRunNotAuthorized, match="exact frozen 840-instance population"):
            run_split(population="confirmatory", split="test", out_dir=tmp_path, dry_run=True, **subset)
    out = run_split(population="confirmatory", split="test", out_dir=tmp_path, dry_run=True)
    assert out["dry_run"] is True and out["n_instances"] == 840 and out["complete"] is True


def test_partial_confirmatory_train_run_is_marked_partial(tmp_path):
    # Finding NOVA-R10-03: a one-instance confirmatory train run used to
    # look like a complete run. Inverted by Claude: it must be requested as
    # a diagnostic subset, and it is written under a DIAGNOSTIC_SUBSET name
    # with complete=false / partial=true against the 1960-instance split.
    with pytest.raises(ValueError, match="diagnostic_subset"):
        run_split(population="confirmatory", split="train", out_dir=tmp_path, n_values=[30], a_values=[426],
                  indices=[0], workers=0, keep_certificates=True)
    out = run_split(
        population="confirmatory", split="train", out_dir=tmp_path,
        n_values=[30], a_values=[426], indices=[0], workers=0, keep_certificates=True, diagnostic_subset=True,
    )
    assert out["integrity"]["passed"] is True
    assert out["integrity"]["complete"] is False and out["integrity"]["n_population"] == 1960
    assert out["complete"] is False and out["run_mode"] == "DIAGNOSTIC_SUBSET"
    assert out["results_path"].endswith("confirmatory_train_DIAGNOSTIC_SUBSET_results.jsonl")
    manifest = json.loads(open(out["run_manifest_path"], encoding="utf-8").read())
    assert manifest["population"] == "confirmatory" and manifest["split"] == "train"
    assert manifest["partial"] is True and manifest["complete"] is False
    assert manifest["n_instances"] == 1 and manifest["n_population"] == 1960


def test_combine_partial_is_marked_and_must_be_named_partial(tmp_path):
    # Finding NOVA-R10-03 (continued): a 1-of-2800 combine carried no
    # partial marker. Inverted by Claude: it is refused unless the output
    # name says PARTIAL, and its combine manifest records complete=false.
    out = run_split(
        population="confirmatory", split="train", out_dir=tmp_path,
        n_values=[30], a_values=[426], indices=[0], workers=0, keep_certificates=True, diagnostic_subset=True,
    )
    with pytest.raises(ValueError, match="PARTIAL"):
        combine_results([out["results_path"]], tmp_path / "combined.jsonl",
                        population="confirmatory", require_complete=False)
    combined = combine_results(
        [out["results_path"]], tmp_path / "combined_PARTIAL.jsonl",
        population="confirmatory", require_complete=False,
    )
    assert combined["integrity"]["passed"] is True
    assert combined["complete"] is False
    assert combined["integrity"]["complete"] is False and combined["integrity"]["n_population"] == 2800
    manifest = json.loads(open(combined["combine_manifest_path"], encoding="utf-8").read())
    assert manifest["partial"] is True and manifest["n_records"] == 1


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


def test_fault_injection_refused_via_run_specs_for_confirmatory():
    # Finding NOVA-R10-04: the guard used to live only in run_split.
    # Inverted by Claude: run_specs and run_instance refuse it too, before
    # anything runs.
    spec = build_specs("confirmatory", "train", n_values=[30], a_values=[426], indices=[0])[0]
    with pytest.raises(ValueError, match="fault injection is refused"):
        run_specs([spec], workers=0, fault_injection={spec.instance_id: {"raise": True}}, max_attempts=2)
    with pytest.raises(ValueError, match="fault injection is refused"):
        run_instance(spec, budget=10000, certify=False, fault={"raise": True})


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


def test_integrity_report_reports_none_decisions():
    # Finding NOVA-R10-06: a non-ERROR record with decisions=None used to
    # raise TypeError. Inverted by Claude: passed=False with a failure that
    # names the record.
    spec, rec = _genuine_pilot_record("SAT")
    rec = dict(rec, decisions=None)
    report = integrity_report([rec], [spec], budget=10000)
    assert report["passed"] is False
    assert any(rec["instance_id"] in f and "decisions" in f for f in report["failures"])


def test_corrupted_sat_model_fails_integrity_and_audit():
    # Finding NOVA-R10-05: run/combine-time integrity used to trust the
    # stored verification claim. Inverted by Claude: integrity re-checks the
    # SAT model against the regenerated formula, as the audit does.
    from om_lab.generators import generate_random_3sat

    spec, rec = _genuine_pilot_record("SAT")
    inst = generate_random_3sat(n_vars=spec.n, n_clauses=spec.m, seed=spec.seed)
    bad = dict(rec, model=_break_model(inst.clauses, rec["model"]))
    report = integrity_report([bad], [spec], budget=10000)
    assert report["passed"] is False
    assert any("stored SAT model fails re-verification" in f for f in report["failures"])
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


def test_audit_recheck_distinguishes_never_retained_certificate():
    # Finding NOVA-R10-07: the audit used to report "regenerated
    # certificate differs or is invalid" when no certificate was ever
    # retained. Inverted by Claude: that case is a note saying the record
    # stores no certificate; a regenerated proof is extra evidence only.
    spec, rec = _genuine_pilot_record("UNSAT")
    assert rec["reference"] is None
    audit = audit_records(
        [rec], population="pilot", splits=["train"], recheck_certificates=True,
    )
    assert not any("regenerated certificate" in f for f in audit["failures"])
    assert any(rec["instance_id"] in n and "stores no certificate" in n for n in audit["notes"])


def test_read_jsonl_malformed_line_names_file_and_line(tmp_path):
    # Finding NOVA-R10-08 (minor): a malformed line used to raise a raw
    # json.JSONDecodeError. Inverted by Claude: a ValueError naming the file
    # and line.
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"ok": true}\nnot json\n', encoding="utf-8")
    with pytest.raises(ValueError, match=r"bad\.jsonl:2: malformed record") as info:
        read_jsonl(bad)
    assert not isinstance(info.value, json.JSONDecodeError)


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


def _current_repro_manifest(rows=None):
    """A FROZEN-shaped reproducibility manifest built from the
    current environment, so the fabricated population passes the
    DEE-R9-18 gate and the authorization check. The gates check the
    environment and the authorization fields, not the population
    identity -- which is exactly the NOVA-R10-12 finding: the
    fabricated rows pass them. When ``rows`` is given, the
    fitted-model hash is computed from those rows' training fit."""
    rep = _reproducibility("confirmatory")
    manifest = {
        "status": "FROZEN",
        "confirmatory_authorized": True,
        "environment": {"packages": {"numpy": rep["numpy_version"]}},
        "source_sha256": dict(rep["source_file_sha256"]),
    }
    if rows is not None:
        train = [r for r in rows if r["split"] == "train"]
        manifest["fitted_model_sha256"] = fit_fingerprint(fit_m0_m1(train))
    return manifest


def test_fabricated_population_still_passes_legacy_rows_path():
    # Finding NOVA-R10-12, SCOPE LIMITATION (Gate D repair): the
    # legacy analyze_rows path operates on pre-built ROWS, not raw
    # records, so it cannot validate population identity -- a
    # synthetic population with completely wrong seeds, labelled
    # confirmatory, still gets disposition PASS here with integrity
    # passed, even with a valid FROZEN manifest, because no gate in
    # this path looks at seeds. That is why the OFFICIAL path is
    # analyze_records (raw records validated against the canonical
    # seed manifest before conversion) and the CLI uses it; the
    # same fabricated population is REJECTED there -- see
    # test_nova_gate_d_attacks.py::test_final_authorization_wrong_identity_refused.
    # Any future production entrypoint must call analyze_records,
    # never analyze_rows directly on runner output.
    rows = _fabricated_confirmatory_rows(lambda cell, n, a, i: 10**9 + cell * 1000 + i)
    result = analyze_rows(
        rows, "confirmatory", bootstrap_replicates=200,
        reproducibility_manifest=_current_repro_manifest(rows),
    )
    assert result["integrity_gates"]["passed"] is True
    assert result["verification_gates"]["passed"] is True
    assert result["reproducibility_gates"]["passed"] is True
    assert result["primary_disposition"]["disposition"] == "PASS"
    assert result["primary_disposition"]["point_improvement"] > 0.05
    # Control: the identical rows with the true confirmatory seeds get
    # the identical disposition, proving this path never looks at
    # seeds at all.
    true_rows = _fabricated_confirmatory_rows(
        lambda cell, n, a, i: confirmatory_seed(n, a, i)
    )
    true_result = analyze_rows(
        true_rows, "confirmatory", bootstrap_replicates=200,
        reproducibility_manifest=_current_repro_manifest(true_rows),
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
