"""Gate D attack tests (Nova lane, Ace sections 5-6).

Tests the official analysis path (:func:`analyze_records`) against
the integration attacks Ace listed before confirmatory
authorization. All data here is synthetic: the identity fields
(seed, instance_id, seed_hex, formula_sha256) are REAL --
regenerated from the canonical seed scheme exactly as the runner
does -- while the solver measurements (decisions, statuses) are
fabricated from width, so these tests exercise the VALIDATION
machinery, not the science. The model on a SAT row is a placeholder
assignment, not a verified witness; witness validity is the audit's
job (Claude's lane), not the analysis's. No confirmatory test
instance is executed; no held-out outcome is involved.

Every result below is [Claim Level: Empirical Observation]
(executed tests, not proofs).
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

_LAB_DIR = Path(__file__).resolve().parent.parent
if str(_LAB_DIR) not in sys.path:
    sys.path.insert(0, str(_LAB_DIR))

from om_lab.analyze_width import (
    A_VALUES,
    BUDGET_B,
    CONFIRMATORY_SEED_PREFIX,
    N_VALUES,
    TRAIN_INDEX_MAX,
    _expected_formula_sha256,
    _reproducibility,
    analyze_records,
    clause_count,
    confirmatory_seed,
    fit_fingerprint,
    fit_m0_m1,
    pilot_seed,
    records_to_rows,
    validate_population_identity,
    validate_record_types,
)


def _make_record(n, a, index, *, seed=None, instance_id=None, status=None,
                 decisions=None):
    """One runner-shaped record with REAL identity, fabricated measurements.

    The seed / instance_id / seed_hex / formula_sha256 are the
    canonical ones for (n, a, index) unless overridden, so the record
    passes population identity. Width varies within a cell and
    decisions track it (20 + 30 * width), giving a strong M1 signal
    for the positive control. Status is SAT unless index % 3 == 0
    (UNSAT), with plausible verification labels.
    """
    m = clause_count(n, a)
    seed = confirmatory_seed(n, a, index) if seed is None else seed
    iid = (
        f"{CONFIRMATORY_SEED_PREFIX}|{n}|{a}|{index}"
        if instance_id is None
        else instance_id
    )
    width = 5 + (index % 11)
    if decisions is None:
        decisions = 20 + 30 * width
    if status is None:
        status = "SAT" if index % 3 != 0 else "UNSAT"
    satisfiable = status == "SAT"
    return {
        "experiment": "OM-C001-R2",
        "record_schema_version": 1,
        "runner_version": "1.0.0",
        "population": "confirmatory",
        "split": "train" if index <= TRAIN_INDEX_MAX else "test",
        "instance_id": iid,
        "problem": "random_3sat",
        "n_vars": n,
        "n_clauses": m,
        "a_hundredths": a,
        "index": index,
        "seed": seed,
        "seed_hex": f"{seed:032x}",
        "formula_sha256": _expected_formula_sha256(n, m, seed),
        "width": width,
        # The replayed elimination-order width (an int, equal to width
        # here); the runner writes replay_elimination_order(...) into
        # this field, not a boolean (NOVA-G28-02).
        "width_replay": width,
        "width_ordering_sha256": hashlib.sha256(
            f"order-{n}-{a}-{index}".encode()
        ).hexdigest(),
        "width_reversed": width,
        "degree_mean": 5.0 + 0.1 * width,
        "solver": "dpll",
        "budget_b": BUDGET_B,
        "max_decisions": BUDGET_B,
        "max_seconds": None,
        "status": status,
        "stop_reason": None,
        "decisions": decisions,
        "propagations": decisions // 2,
        "budget_exhausted": False,
        "satisfiable": satisfiable,
        "timed_out": False,
        "verified": True,
        "verification_status": (
            "SAT_WITNESS_CHECKED" if satisfiable else "UNSAT_PROOF_CHECKED"
        ),
        "y": math.log1p(min(decisions, BUDGET_B)),
        # Placeholder assignment, not a verified witness (see module
        # docstring). The analysis checks the label, not the model.
        "model": list(range(1, n + 1)) if satisfiable else None,
        "reference": {"solver": "pysat:cd195", "status": status},
        "reference_agreement": "AGREE",
        "integrity_alarm": None,
        "error": None,
    }


_COMPLETE = None


def _complete_records():
    """The full 2800-record synthetic confirmatory population.

    Built once per process (formula generation is ~2.5 s) and
    deep-copied per test so mutations do not leak between tests.
    """
    global _COMPLETE
    if _COMPLETE is None:
        _COMPLETE = [
            _make_record(n, a, i)
            for n in N_VALUES
            for a in A_VALUES
            for i in range(100)
        ]
    return copy.deepcopy(_COMPLETE)


def _frozen_manifest_for(records, *, status="FROZEN", authorized=True,
                         fit_hash=True):
    """A FROZEN-shaped manifest with valid source hashes.

    The fitted-model hash is computed from the records themselves
    (converted exactly as the analyzer converts them), so the fit
    gate passes for an untampered dataset and only the check under
    test can block the disposition. ``fit_hash=False`` omits the
    pinned hash (B4 gap); ``status``/``authorized`` shape the
    authorization fields.
    """
    rep = _reproducibility("confirmatory")
    manifest = {
        "status": status,
        "confirmatory_authorized": authorized,
        "environment": {"packages": {"numpy": rep["numpy_version"]}},
        "source_sha256": dict(rep["source_file_sha256"]),
    }
    if fit_hash:
        rows = records_to_rows(records)
        train = [r for r in rows if r["split"] == "train"]
        manifest["fitted_model_sha256"] = fit_fingerprint(fit_m0_m1(train))
    return manifest


def _run_official(records, manifest=None):
    if manifest is None:
        manifest = _frozen_manifest_for(records)
    return analyze_records(
        records, "confirmatory", bootstrap_replicates=200,
        reproducibility_manifest=manifest,
    )


# --- Positive control -----------------------------------------------------


def test_official_path_passes_on_complete_correct_dataset():
    """Positive control: the complete correct synthetic population
    passes every gate and the official path issues PASS. The
    measurements are fabricated, so this is a pipeline control,
    not a scientific result."""
    records = _complete_records()
    summary, rows = _run_official(records)
    assert len(rows) == 2800
    assert summary["integrity_gates"]["passed"] is True
    assert summary["verification_gates"]["passed"] is True
    assert summary["reproducibility_gates"]["passed"] is True
    assert summary["fitted_model_gate"]["passed"] is True
    assert summary["primary_disposition"]["disposition"] == "PASS"
    assert summary["counts"]["n_error_rows"] == 0


# --- Ace section 5 attacks (Nova-owned) -----------------------------------


def test_replace_all_test_ids_rejected():
    """Ace §5: replace all 840 test IDs with different IDs while
    keeping row counts. The shape is right; the identities are
    wrong. Must REJECT."""
    records = _complete_records()
    for rec in records:
        if rec["split"] == "test":
            rec["instance_id"] = (
                f"OM-C001-R2-FORGED|{rec['n_vars']}|{rec['a_hundredths']}|{rec['index']}"
            )
    with pytest.raises(ValueError, match="instance_id"):
        _run_official(records)


def test_swap_seeds_between_instances_rejected():
    """Ace §5: swap valid seeds between instances. Each record stays
    internally consistent (its formula hash matches its swapped
    seed), so only the canonical-manifest comparison can catch it.
    Must REJECT."""
    records = _complete_records()
    a, b = records[0], records[1]  # same cell, indices 0 and 1
    for field in ("seed", "seed_hex", "formula_sha256"):
        a[field], b[field] = b[field], a[field]
    with pytest.raises(ValueError, match="seed"):
        _run_official(records)


def test_error_record_forces_official_inconclusive():
    """Ace §5: add an ERROR record alongside an otherwise complete
    dataset. Here one train record is replaced by an ERROR record
    with valid identity (its measurements are missing, not wrong),
    so identity passes and the official disposition is INCONCLUSIVE
    with the ERROR reason and the raw count in the metadata."""
    records = _complete_records()
    error = records[0]
    error.update(
        {
            "status": "ERROR",
            "stop_reason": "watchdog",
            "decisions": None,
            "propagations": None,
            "y": None,
            "width": None,
            "width_replay": None,
            "width_ordering_sha256": None,
            "width_reversed": None,
            "degree_mean": None,
            "formula_sha256": error["formula_sha256"],
            "model": None,
            "reference": None,
            "error": {"kind": "watchdog", "attempts": 3, "detail": "timeout"},
        }
    )
    summary, _rows = _run_official(records)
    assert summary["counts"]["n_error_rows"] == 1
    assert summary["primary_disposition"]["disposition"] == "INCONCLUSIVE"
    assert any(
        "ERROR row" in r for r in summary["primary_disposition"]["reasons"]
    )


def test_extra_error_record_with_duplicate_identity_rejected():
    """Ace §5, reject branch: an ERROR record added on top of the
    complete dataset, duplicating an existing instance's identity,
    is rejected as a duplicate -- it cannot smuggle a second row
    for the same instance past identity validation."""
    records = _complete_records()
    duplicate = copy.deepcopy(records[0])
    duplicate.update(
        {
            "status": "ERROR",
            "stop_reason": "watchdog",
            "decisions": None,
            "propagations": None,
            "y": None,
            "width": None,
            "width_replay": None,
            "width_ordering_sha256": None,
            "width_reversed": None,
            "degree_mean": None,
            "model": None,
            "reference": None,
            "error": {"kind": "watchdog", "attempts": 3, "detail": "timeout"},
        }
    )
    records.append(duplicate)
    with pytest.raises(ValueError, match="duplicate"):
        _run_official(records)


@pytest.mark.parametrize(
    "field,value",
    [
        ("satisfiable", "false"),  # bool("false") is True: the D4 bug
        ("satisfiable", 1),
        ("n_vars", "30"),
        ("n_vars", 30.0),
        ("decisions", True),
        ("seed", 30.5),
        ("verified", "yes"),
        ("index", "70"),
    ],
)
def test_strict_record_types_reject_coercible_values(field, value):
    """Ace §5 / Gate D4: supply "false" instead of JSON false, and
    other values a coercing converter would silently accept. The
    strict validator rejects every one (NOVA-R10-09/11)."""
    record = _make_record(30, 400, 0)
    record[field] = value
    with pytest.raises(ValueError, match=field):
        validate_record_types(record)


def test_string_false_rejected_on_the_official_path():
    """The "false" attack end to end: one record in an otherwise
    complete dataset carries satisfiable="false". Must REJECT
    before any analysis runs."""
    records = _complete_records()
    records[0]["satisfiable"] = "false"
    with pytest.raises(ValueError, match="satisfiable"):
        _run_official(records)


def test_alter_frozen_training_coefficient_rejected():
    """Ace §5 (shared with Claude): alter a frozen training
    coefficient. Changing one training record's decisions changes
    the fitted model, so its fingerprint no longer matches the
    manifest's pinned hash. Must refuse a PASS (INCONCLUSIVE with
    the fitted-model reason)."""
    records = _complete_records()
    manifest = _frozen_manifest_for(records)
    records[0]["decisions"] += 100
    records[0]["y"] = math.log1p(records[0]["decisions"])
    summary, _rows = analyze_records(
        records, "confirmatory", bootstrap_replicates=200,
        reproducibility_manifest=manifest,
    )
    assert summary["fitted_model_gate"]["passed"] is False
    assert summary["primary_disposition"]["disposition"] == "INCONCLUSIVE"
    assert any(
        "fitted model" in r for r in summary["primary_disposition"]["reasons"]
    )


def test_alter_manifest_fitted_model_hash_rejected():
    """Same attack from the other side: the data is untouched but
    the manifest's pinned fitted-model hash is altered. Must refuse
    a PASS."""
    records = _complete_records()
    manifest = _frozen_manifest_for(records)
    manifest["fitted_model_sha256"] = "0" * 64
    summary, _rows = analyze_records(
        records, "confirmatory", bootstrap_replicates=200,
        reproducibility_manifest=manifest,
    )
    assert summary["fitted_model_gate"]["passed"] is False
    assert summary["primary_disposition"]["disposition"] == "INCONCLUSIVE"


def test_unpinned_fitted_model_hash_blocks():
    """B4 fail-closed: a manifest that does not pin the fitted-model
    hash cannot authorize a confirmatory PASS, even with valid
    source hashes and correct data."""
    records = _complete_records()
    manifest = _frozen_manifest_for(records, fit_hash=False)
    summary, _rows = analyze_records(
        records, "confirmatory", bootstrap_replicates=200,
        reproducibility_manifest=manifest,
    )
    assert summary["fitted_model_gate"]["passed"] is False
    assert summary["primary_disposition"]["disposition"] == "INCONCLUSIVE"
    assert any(
        "not pinned" in r for r in summary["primary_disposition"]["reasons"]
    )


@pytest.mark.parametrize(
    "status,authorized",
    [
        ("DRAFT", False),  # the actual draft shape
        ("FROZEN", "true"),  # string "true" is not authorization (B5.2)
        ("FROZEN", False),
        (None, None),  # no authorization fields at all
    ],
)
def test_draft_manifest_rejected_by_confirmatory_analyzer(status, authorized):
    """Ace §5: supply a DRAFT manifest to the confirmatory analyzer.
    Only status FROZEN with confirmatory_authorized exactly True
    authorizes; anything else forces INCONCLUSIVE."""
    records = _complete_records()
    manifest = _frozen_manifest_for(records, status=status, authorized=authorized)
    if status is None:
        manifest.pop("status", None)
        manifest.pop("confirmatory_authorized", None)
    summary, _rows = analyze_records(
        records, "confirmatory", bootstrap_replicates=200,
        reproducibility_manifest=manifest,
    )
    assert summary["reproducibility_gates"]["passed"] is False
    assert summary["primary_disposition"]["disposition"] == "INCONCLUSIVE"
    assert any(
        "not a FROZEN authorized manifest" in r
        for r in summary["primary_disposition"]["reasons"]
    )


def test_wrong_experiment_identifier_rejected():
    """Ace §5: valid-looking data with an incorrect experiment
    identifier. Must REJECT before identity validation or analysis."""
    records = _complete_records()
    for rec in records:
        rec["experiment"] = "OM-C001-R2-FORGED"
    with pytest.raises(ValueError, match="experiment"):
        _run_official(records)
    # Single-record unit check: the validator names the field.
    record = _make_record(30, 400, 0)
    record["experiment"] = "OTHER-EXPERIMENT"
    with pytest.raises(ValueError, match="experiment"):
        validate_record_types(record)


def test_final_authorization_wrong_identity_refused():
    """Ace's final authorization test: exactly 28 cells, exactly
    70 train / 30 test per cell, apparently excellent width
    prediction, plausible verification labels, a reproducibility
    manifest with valid source hashes and the correct fitted-model
    hash -- but WRONG population identity (seeds, IDs and formula
    hashes from a different seed prefix, internally consistent).
    The official analyzer must refuse a confirmatory PASS. This is
    the regression test for NOVA-R10-12: the same shape of data got
    PASS 0.856 in Phase 4 before identity validation existed."""
    records = []
    forged_prefix = "OM-C001-R2-FORGED"
    for n in N_VALUES:
        for a in A_VALUES:
            for i in range(100):
                seed = int.from_bytes(
                    __import__("hashlib").sha256(
                        f"{forged_prefix}|{n}|{a}|{i}".encode()
                    ).digest()[:16],
                    "big",
                )
                records.append(
                    _make_record(
                        n, a, i, seed=seed,
                        instance_id=f"{forged_prefix}|{n}|{a}|{i}",
                    )
                )
    # The manifest is fully valid for THIS dataset (correct fit hash
    # and source hashes), so identity is the only thing that can
    # block the disposition -- and it must.
    manifest = _frozen_manifest_for(records)
    with pytest.raises(ValueError, match="population identity"):
        analyze_records(
            records, "confirmatory", bootstrap_replicates=200,
            reproducibility_manifest=manifest,
        )


def test_identity_validation_accepts_pilot_population_unchanged():
    """Scope: identity validation is confirmatory-only. A pilot
    population is not rejected for having pilot seeds."""
    records = _complete_records()
    report = validate_population_identity(records, "pilot")
    assert report["passed"] is True


# --- ACE-GATE-D-01: the CLI path -------------------------------------------


def _write_jsonl(path, records):
    with open(path, "w", encoding="utf-8") as handle:
        for rec in records:
            handle.write(json.dumps(rec) + "\n")


def _run_cli(records_path, manifest_path, out_dir):
    return subprocess.run(
        [
            sys.executable, "-m", "om_lab.analyze_width",
            "--records", str(records_path),
            "--population", "confirmatory",
            "--reproducibility-manifest", str(manifest_path),
            "--out-dir", str(out_dir),
        ],
        cwd=_LAB_DIR,
        capture_output=True,
        text=True,
        timeout=600,
    )


def test_cli_carries_raw_error_count_into_output(tmp_path):
    """ACE-GATE-D-01 regression: exercise the ACTUAL CLI path, not
    just analyze_rows. The raw ERROR count must reach the
    machine-readable output (counts + primary disposition), not
    just the stdout warning."""
    records = _complete_records()
    error = records[0]
    error.update(
        {
            "status": "ERROR",
            "stop_reason": "watchdog",
            "decisions": None,
            "propagations": None,
            "y": None,
            "width": None,
            "width_replay": None,
            "width_ordering_sha256": None,
            "width_reversed": None,
            "degree_mean": None,
            "model": None,
            "reference": None,
            "error": {"kind": "watchdog", "attempts": 3, "detail": "timeout"},
        }
    )
    records_path = tmp_path / "records.jsonl"
    manifest_path = tmp_path / "freeze.json"
    _write_jsonl(records_path, records)
    manifest_path.write_text(
        json.dumps(_frozen_manifest_for(records)), encoding="utf-8"
    )
    result = _run_cli(records_path, manifest_path, tmp_path / "out")
    assert result.returncode == 0, result.stderr[-2000:]
    assert "WARNING: 1 ERROR record(s)" in result.stdout
    analysis = json.loads((tmp_path / "out" / "width_analysis.json").read_text())
    assert analysis["counts"]["n_error_rows"] == 1
    primary = json.loads((tmp_path / "out" / "primary_result.json").read_text())
    assert primary["disposition"] == "INCONCLUSIVE"
    assert any("ERROR row" in r for r in primary["reasons"])


def test_cli_rejects_wrong_identity(tmp_path):
    """CLI end to end: a wrong-identity population is rejected with
    a non-zero exit, and no analysis output is written."""
    records = _complete_records()
    for rec in records:
        if rec["split"] == "test":
            rec["instance_id"] = "OM-C001-R2-FORGED|" + rec["instance_id"].split("|", 1)[1]
    records_path = tmp_path / "records.jsonl"
    manifest_path = tmp_path / "freeze.json"
    _write_jsonl(records_path, records)
    manifest_path.write_text(
        json.dumps(_frozen_manifest_for(records)), encoding="utf-8"
    )
    result = _run_cli(records_path, manifest_path, tmp_path / "out")
    assert result.returncode != 0
    assert "population identity" in result.stderr
    assert not (tmp_path / "out" / "width_analysis.json").exists()


# --- DEE-G26-01: non-finite numeric fields -------------------------------


@pytest.mark.parametrize("field,value", [
    ("degree_mean", float("nan")),
    ("degree_mean", float("inf")),
    ("degree_mean", float("-inf")),
    ("degree_mean", 10**309),          # int too large for finite float
    ("y", float("nan")),
    ("y", float("inf")),
    ("max_seconds", float("nan")),
])
def test_non_finite_numeric_fields_rejected(field, value):
    """DEE-G26-01: NaN / inf / int-overflow in a numeric field is
    rejected by the strict validator, so it cannot contaminate the
    M2/M3 output or produce invalid JSON."""
    record = _make_record(30, 400, 0)
    record[field] = value
    with pytest.raises(ValueError, match=field):
        validate_record_types(record)


def test_non_finite_degree_mean_does_not_reach_analysis_output():
    """DEE-G26-01 end-to-end: an otherwise-complete dataset with one
    NaN in ``degree_mean`` is rejected by ``analyze_records`` at the
    type-validation step, so ``width_analysis.json`` is never
    written with a NaN token."""
    records = _complete_records()
    records[0]["degree_mean"] = float("nan")
    with pytest.raises(ValueError, match="degree_mean"):
        _run_official(records)


# --- NOVA-G28-02: the validator must accept genuine runner records --------


def test_validate_record_types_accepts_genuine_runner_records(tmp_path):
    """NOVA-G28-02: ``validate_record_types`` must accept records the
    runner actually writes. The Gate D validator required ``width_replay``
    to be a bool, but the runner writes the replayed elimination-order
    width (an int, equal to ``width``) into that field, so every genuine
    record was rejected and the official path could not analyse real
    runner output. This test runs a real 1-instance confirmatory train
    subset and validates its records, so the fixture cannot drift from
    the runner's schema again."""
    from om_lab import width_experiment as wx

    out_dir = tmp_path / "run"
    wx.run_split(
        population="confirmatory", split="train", out_dir=out_dir, workers=0,
        keep_certificates=True, diagnostic_subset=True,
        n_values=[30], a_values=[426], indices=[0],
    )
    result_files = sorted(out_dir.glob("*_results.jsonl"))
    assert len(result_files) == 1
    records = wx.read_jsonl(result_files[0])
    assert len(records) == 1
    for record in records:
        validate_record_types(record)
        assert isinstance(record["width_replay"], int) and not isinstance(record["width_replay"], bool)
        assert record["width_replay"] == record["width"]
