"""Analysis authorization interface (Nova, ACE-GATE-D-02).

``analyze_width.reproducibility_gates`` and ``verify_frozen_fit`` expect
one manifest, but execution authorization is two artifacts
(``freeze_stage_a.json`` + ``freeze_stage_b.json``) and the whole-file
SHA-256 of ``fitted_model.json`` is not ``fit_fingerprint``. The repair
is :func:`analyze_width.build_analysis_handoff`: it verifies Stage B
against Stage A and Stage A against the running code, environment,
checkout and training artefacts, and only then derives the
single-manifest view the gates need -- with the file hash and the
fingerprint kept as separate, clearly named fields -- and binds the
combined analysis input to the frozen training records and the
authorized test-run output.

Fixtures are the shared ``_freeze_fixtures`` case (a real Stage A over
the 16-instance confirmatory training subset, plus a Stage B written by
``freeze.authorize`` -- the library's own authorization path, never a
hand-written authorized JSON). The test-run and combine manifests in
these tests are synthetic records of a run, built from the verified
case values; the synthetic test records carry real canonical identity
for three test instances with fabricated measurements and are used
only as file bytes for the hash binding -- they are never analysed,
audited, or run. Nothing here executes a confirmatory test instance
(indices 70-99); the three synthetic test records are file bytes for
hash binding only, and no solver is called on them.

[Claim Level: Empirical Observation] for every result below.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import sys
from pathlib import Path

import pytest

from _freeze_fixtures import (
    build_training_base,
    clean_provenance,
    flip_hex,
    make_case,
    sha256_file,
)
from om_lab import analyze_width as aw
from om_lab import freeze
from om_lab import width_experiment as wx


@pytest.fixture(scope="module")
def training_base(tmp_path_factory):
    base = tmp_path_factory.mktemp("handoff_base")
    return base, build_training_base(base)


@pytest.fixture(scope="module")
def base_provenance():
    return clean_provenance()


@pytest.fixture
def case(tmp_path, monkeypatch, training_base, base_provenance):
    return make_case(tmp_path, monkeypatch, training_base[0], base_provenance)


# --- Synthetic run manifests (hash-binding fixtures only) ------------------


def _synthetic_test_records() -> list[dict]:
    """Three test records: real canonical identity, fabricated measurements.

    Identity fields (instance_id, seed, seed_hex, formula hash) are the
    canonical ones for (30, 400, 70..72), so the records are well-formed;
    the measurements are invented. They are file bytes for the hash
    binding only -- never analysed or audited in these tests.
    """
    records = []
    for i in (70, 71, 72):
        n, a = 30, 400
        seed = aw.confirmatory_seed(n, a, i)
        m = aw.clause_count(n, a)
        width = 5 + (i % 11)
        decisions = 20 + 30 * width
        records.append({
            "experiment": "OM-C001-R2",
            "record_schema_version": 1,
            "runner_version": "1.0.0",
            "population": "confirmatory",
            "split": "test",
            "problem": "random_3sat",
            "n_vars": n,
            "n_clauses": m,
            "a_hundredths": a,
            "index": i,
            "instance_id": f"OM-C001-R2|{n}|{a}|{i}",
            "seed": seed,
            "seed_hex": f"{seed:032x}",
            "formula_sha256": aw._expected_formula_sha256(n, m, seed),
            "status": "SAT",
            "satisfiable": True,
            "timed_out": False,
            "decisions": decisions,
            "propagations": decisions // 2,
            "y": math.log1p(min(decisions, aw.BUDGET_B)),
            "width": width,
            "width_replay": width,
            "width_ordering_sha256": hashlib.sha256(
                f"order-{n}-{a}-{i}".encode()
            ).hexdigest(),
            "width_reversed": width,
            "degree_mean": 5.0 + 0.1 * width,
            "solver": "dpll",
            "budget_b": aw.BUDGET_B,
            "max_decisions": aw.BUDGET_B,
            "max_seconds": None,
            "stop_reason": None,
            "budget_exhausted": False,
            "verified": True,
            "verification_status": "SAT_WITNESS_CHECKED",
            "model": list(range(1, n + 1)),
            "reference": {"solver": "pysat:cd195", "status": "SAT"},
            "reference_agreement": "AGREE",
            "integrity_alarm": None,
            "error": None,
        })
    return records


def _write_jsonl(path: Path, records: list[dict]) -> str:
    with open(path, "w", encoding="utf-8") as handle:
        for rec in records:
            handle.write(json.dumps(rec) + "\n")
    return sha256_file(path)


def _test_run_manifest(case, test_sha: str) -> dict:
    """Synthetic manifest of the authorized test run, built from the
    verified Stage A / Stage B values of the case."""
    stage_a = case.stage_a_doc()
    stage_b = case.stage_b_doc()
    schedule = stage_a["population"]["test"]["schedule_sha256"]
    return {
        "experiment": "OM-C001-R2",
        "population": "confirmatory",
        "split": "test",
        "run_mode": "OFFICIAL",
        "complete": True,
        "n_instances": 3,
        "n_population": 840,
        "schedule_sha256": schedule,
        "authorization": {
            "stage_a_sha256": sha256_file(case.stage_a),
            "stage_b_sha256": sha256_file(case.stage_b),
            "authorized_by": stage_b["authorized_by"],
            "authorized_at_utc": stage_b["authorized_at_utc"],
            "test_schedule_sha256": schedule,
        },
        "results_file": "test_results.jsonl",
        "results_sha256": test_sha,
    }


def _handoff_inputs(case, tmp_path: Path) -> dict:
    """Write the synthetic test file, the combined records file and both
    manifests for the case; return every path and hash the tests need."""
    stage_a = case.stage_a_doc()
    test_path = tmp_path / "test_results.jsonl"
    test_sha = _write_jsonl(test_path, _synthetic_test_records())
    combined_path = tmp_path / "results.jsonl"
    combined_path.write_bytes(case.records_path.read_bytes() + test_path.read_bytes())
    combined_sha = sha256_file(combined_path)
    test_manifest_path = tmp_path / "confirmatory_test_run_manifest.json"
    test_manifest_path.write_text(
        json.dumps(_test_run_manifest(case, test_sha), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    combine_path = tmp_path / "results_combine_manifest.json"
    combine_path.write_text(
        json.dumps({
            "kind": "OM-C001-R2/combine",
            "experiment": "OM-C001-R2",
            "population": "confirmatory",
            "complete": True,
            "partial": False,
            "n_records": 19,
            "results_file": "results.jsonl",
            "results_sha256": combined_sha,
            "inputs": [
                {"path": case.records_path.name,
                 "sha256": stage_a["training"]["records_sha256"]},
                {"path": "test_results.jsonl", "sha256": test_sha},
            ],
        }, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return {
        "test_path": test_path,
        "test_sha": test_sha,
        "combined_path": combined_path,
        "combined_sha": combined_sha,
        "test_manifest_path": test_manifest_path,
        "combine_path": combine_path,
    }


def _build(case, inputs: dict, **overrides) -> dict:
    kwargs = {
        "test_run_manifest_path": inputs["test_manifest_path"],
        "combine_manifest_path": inputs["combine_path"],
        "records_path": inputs["combined_path"],
    }
    kwargs.update(overrides)
    return aw.build_analysis_handoff(case.stage_a, case.stage_b, **kwargs)


# --- Valid handoff ----------------------------------------------------------


def test_valid_handoff_passes_and_gates_pass(case, tmp_path):
    """ACE-GATE-D-02 positive path: a verified Stage A / Stage B pair
    derives a handoff that satisfies both gates, with the file hash and
    the fingerprint kept separate."""
    inputs = _handoff_inputs(case, tmp_path)
    handoff = _build(case, inputs)
    assert handoff["kind"] == aw.HANDOFF_KIND
    assert handoff["status"] == "FROZEN"
    assert handoff["confirmatory_authorized"] is True
    assert handoff["records_bound"] is True
    assert handoff["records_sha256"] == inputs["combined_sha"]
    assert handoff["test_results_sha256"] == inputs["test_sha"]
    assert handoff["training_records_sha256"] == case.stage_a_doc()["training"]["records_sha256"]
    # The two fitted-model hashes are different things, both pinned.
    assert handoff["fitted_model_file_sha256"] == case.stage_a_doc()["model"]["sha256"]
    assert handoff["fitted_model_sha256"] != handoff["fitted_model_file_sha256"]
    # The fingerprint is the fingerprint of the frozen coefficients:
    # it equals the fingerprint of the fit from the frozen training records.
    rows = aw.records_to_rows(case.records())
    assert handoff["fitted_model_sha256"] == aw.fit_fingerprint(aw.fit_m0_m1(rows))
    assert aw.reproducibility_gates(handoff)["passed"] is True
    assert aw.verify_frozen_fit(aw.fit_m0_m1(rows), handoff)["passed"] is True
    summary = aw.analyze_rows(rows, "confirmatory", reproducibility_manifest=handoff)
    assert summary["reproducibility_gates"]["passed"] is True
    assert summary["fitted_model_gate"]["passed"] is True
    echo = summary["analysis_handoff"]
    assert echo is not None
    assert echo["stage_a_sha256"] == handoff["stage_a_sha256"]
    assert echo["records_bound"] is True


def test_handoff_without_records_file_is_unbound(case, tmp_path):
    """Library-level use without a records file derives the same gates
    but records that no file bytes were bound."""
    inputs = _handoff_inputs(case, tmp_path)
    handoff = _build(case, inputs, combine_manifest_path=None, records_path=None)
    assert handoff["records_bound"] is False
    assert handoff["records_sha256"] is None
    assert aw.reproducibility_gates(handoff)["passed"] is True


def test_records_file_without_combine_manifest_refused(case, tmp_path):
    """Fail closed: a records file with no combine manifest cannot be
    bound to the frozen inputs."""
    inputs = _handoff_inputs(case, tmp_path)
    with pytest.raises(ValueError, match="needs its combine manifest"):
        _build(case, inputs, combine_manifest_path=None)


# --- Tampered / unauthorized inputs fail closed -----------------------------


def test_tampered_stage_a_refused(case, tmp_path):
    """A Stage A whose source hashes no longer match the running code
    is refused even after Stage B is re-signed to the new bytes."""
    inputs = _handoff_inputs(case, tmp_path)
    case.edit_stage_a(
        lambda doc: doc["source_sha256"].update(
            {"analyze_width.py": flip_hex(doc["source_sha256"]["analyze_width.py"])}
        ),
        resign=True,
    )
    with pytest.raises(ValueError, match="differs from the running code"):
        _build(case, inputs)


def test_stage_b_wrong_stage_a_hash_refused(case, tmp_path):
    """Stage B naming a different Stage A hash is refused."""
    inputs = _handoff_inputs(case, tmp_path)
    case.edit_stage_b(
        lambda doc: doc.update(stage_a_sha256=flip_hex(doc["stage_a_sha256"]))
    )
    with pytest.raises(ValueError, match="different Stage A"):
        _build(case, inputs)


@pytest.mark.parametrize(
    "update, match",
    [
        ({"confirmatory_authorized": False}, "confirmatory_authorized is not true"),
        ({"confirmatory_authorized": "true"}, "confirmatory_authorized is not true"),
        ({"status": "DRAFT"}, "status is not FROZEN"),
    ],
)
def test_unauthorized_stage_b_refused(case, tmp_path, update, match):
    """An unauthorized Stage B (not True, string "true", or DRAFT)
    cannot authorise a handoff."""
    inputs = _handoff_inputs(case, tmp_path)
    case.edit_stage_b(lambda doc: doc.update(update))
    with pytest.raises(ValueError, match=match):
        _build(case, inputs)


def test_altered_fitted_model_file_refused(case, tmp_path):
    """A fitted-model file whose bytes no longer match Stage A is refused."""
    inputs = _handoff_inputs(case, tmp_path)
    data = bytearray(case.model.read_bytes())
    data[-3] = ord("0") if data[-3] != ord("0") else ord("1")
    case.model.write_bytes(bytes(data))
    with pytest.raises(ValueError, match="fitted model file hash differs"):
        _build(case, inputs)


def test_recomputed_fitted_model_mismatch_refused(case, tmp_path):
    """A fitted-model file that does not match the model recomputed
    from the frozen training records is refused, even when Stage A
    was re-signed over its hash."""
    inputs = _handoff_inputs(case, tmp_path)
    altered = copy.deepcopy(case.records())
    altered[0]["decisions"] += 100
    model = freeze.fitted_model_document(altered)
    case.model.write_bytes(freeze.model_bytes(model))
    case.edit_stage_a(
        lambda doc: doc["model"].update(sha256=sha256_file(case.model)),
        resign=True,
    )
    with pytest.raises(ValueError, match="fitted model differs from the model recomputed"):
        _build(case, inputs)


def test_missing_test_output_hashes_refused(case, tmp_path):
    """A test run manifest with no results hash, no authorization
    record, or a run that is not the authorized OFFICIAL test run
    cannot bind the test output."""
    inputs = _handoff_inputs(case, tmp_path)

    def rewrite(mutate):
        doc = json.loads(inputs["test_manifest_path"].read_text(encoding="utf-8"))
        mutate(doc)
        inputs["test_manifest_path"].write_text(
            json.dumps(doc, indent=2, sort_keys=True), encoding="utf-8"
        )

    rewrite(lambda doc: doc.pop("results_sha256"))
    with pytest.raises(ValueError, match="no results_sha256"):
        _build(case, inputs)
    rewrite(lambda doc: doc.update(_test_run_manifest(case, inputs["test_sha"])))
    rewrite(lambda doc: doc.pop("authorization"))
    with pytest.raises(ValueError, match="no authorization record"):
        _build(case, inputs)
    rewrite(lambda doc: doc.update(_test_run_manifest(case, inputs["test_sha"])))
    rewrite(lambda doc: doc.update(run_mode="DIAGNOSTIC_SUBSET"))
    with pytest.raises(ValueError, match="not an OFFICIAL run"):
        _build(case, inputs)


def test_combine_manifest_missing_test_input_refused(case, tmp_path):
    """A combine manifest that does not list the authorized test
    output among its inputs cannot bind the combined file."""
    inputs = _handoff_inputs(case, tmp_path)
    doc = json.loads(inputs["combine_path"].read_text(encoding="utf-8"))
    doc["inputs"] = doc["inputs"][:1]
    inputs["combine_path"].write_text(
        json.dumps(doc, indent=2, sort_keys=True), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="do not include the authorized test output"):
        _build(case, inputs)


def test_records_file_hash_mismatch_refused(case, tmp_path):
    """A records file whose bytes differ from the combine manifest
    is refused."""
    inputs = _handoff_inputs(case, tmp_path)
    with open(inputs["combined_path"], "a", encoding="utf-8") as handle:
        handle.write("{}\n")
    with pytest.raises(ValueError, match="differs from the combine manifest"):
        _build(case, inputs)


# --- CLI --------------------------------------------------------------------


def _run_cli_main(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", argv)
    return aw.main()


def test_cli_handoff_reaches_analysis_on_incomplete_fixture(case, tmp_path, monkeypatch):
    """CLI wiring: the official command accepts the handoff and gets
    to the analysis. The fixture population is incomplete (16 train +
    3 test records, not the full 2800), so the analysis itself must
    refuse on population identity -- the handoff must not be the
    thing that refuses."""
    inputs = _handoff_inputs(case, tmp_path)
    argv = [
        "analyze_width", "--records", str(inputs["combined_path"]),
        "--population", "confirmatory",
        "--stage-a", str(case.stage_a),
        "--stage-b", str(case.stage_b),
        "--test-run-manifest", str(inputs["test_manifest_path"]),
        "--combine-manifest", str(inputs["combine_path"]),
        "--out-dir", str(tmp_path / "out"),
    ]
    with pytest.raises(ValueError, match="population identity"):
        _run_cli_main(monkeypatch, argv)
    assert not (tmp_path / "out" / "width_analysis.json").exists()


def test_cli_handoff_refused_on_tampered_stage_a(case, tmp_path, monkeypatch):
    """CLI wiring: a tampered Stage A fails closed before any analysis
    output is written."""
    inputs = _handoff_inputs(case, tmp_path)
    case.edit_stage_a(
        lambda doc: doc["source_sha256"].update(
            {"analyze_width.py": flip_hex(doc["source_sha256"]["analyze_width.py"])}
        ),
        resign=True,
    )
    argv = [
        "analyze_width", "--records", str(inputs["combined_path"]),
        "--population", "confirmatory",
        "--stage-a", str(case.stage_a),
        "--stage-b", str(case.stage_b),
        "--test-run-manifest", str(inputs["test_manifest_path"]),
        "--combine-manifest", str(inputs["combine_path"]),
        "--out-dir", str(tmp_path / "out"),
    ]
    with pytest.raises(ValueError, match="analysis handoff refused"):
        _run_cli_main(monkeypatch, argv)
    assert not (tmp_path / "out" / "width_analysis.json").exists()


def test_cli_handoff_and_legacy_manifest_mixed_refused(case, tmp_path, monkeypatch):
    """CLI wiring: the handoff flags and --reproducibility-manifest
    cannot be combined."""
    inputs = _handoff_inputs(case, tmp_path)
    argv = [
        "analyze_width", "--records", str(inputs["combined_path"]),
        "--population", "confirmatory",
        "--stage-a", str(case.stage_a),
        "--stage-b", str(case.stage_b),
        "--test-run-manifest", str(inputs["test_manifest_path"]),
        "--combine-manifest", str(inputs["combine_path"]),
        "--reproducibility-manifest", str(tmp_path / "freeze.json"),
        "--out-dir", str(tmp_path / "out"),
    ]
    with pytest.raises(SystemExit):
        _run_cli_main(monkeypatch, argv)
