"""Freeze enforcement, exact scheduling and retained-certificate audit
(Claude, Phase 4 Gate B/D repair against dev b6d2b27).

Findings covered: NOVA-R10-01 (two-stage freeze, B4 / ACE-PLAN-01), the
non-executing preflight (Ace's gate review, section 3), NOVA-R10-02/03
(exact population and partial outputs, ACE-PLAN-02), NOVA-R10-04 (fault
injection refused at every execution layer, ACE-PLAN-06), NOVA-R10-05
(evidence, not status claims), NOVA-R10-15 / Gate D2 (retained
certificates, ACE-PLAN-05), and each attack in Ace's section 5. Every
attack must be REJECTED.

Nothing here executes a confirmatory test instance (indices 70-99). The
test split appears only as schedule objects, as refusals that happen before
any solver call, and as an authorised run intercepted before a worker
process can start (solver and worker entry points are replaced by stubs
that fail the test if reached). Training data is the 16-instance
confirmatory training subset of ``_freeze_fixtures`` plus pilot instances.

[Claim Level: Empirical Observation] for every result below. These tests
exercise the listed cases; they do not prove that the guard has no other
gap, and the guard is procedural, not cryptographic (ACE-PLAN-06).
"""

from __future__ import annotations

import copy
import dataclasses
import json
import os
import pickle
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from _freeze_fixtures import (
    HEAD,
    LATER,
    SETTINGS,
    STEM,
    build_training_base,
    clean_provenance,
    flip_hex,
    make_case,
    sha256_file,
    subset_specs,
)
from om_lab import freeze
from om_lab import width_experiment as wx
from om_lab.generators import generate_random_3sat
from om_lab.solvers import verify_cnf_assignment

#: The 840 confirmatory test specs as schedule objects. They are never run.
TEST_SPECS = wx.build_specs("confirmatory", "test")
REFUSED = wx.ConfirmatoryRunNotAuthorized


class Intercepted(Exception):
    """Raised by a stub at the exact point where execution would begin."""


def _forbidden(*args, **kwargs):
    raise AssertionError("a solver or worker was reached in a test that must not execute anything")


def _bump_patch(version: str) -> str:
    major, minor, patch = (version.split(".") + ["0", "0"])[:3]
    digits = "".join(ch for ch in patch if ch.isdigit()) or "0"
    return f"{major}.{minor}.{int(digits) + 1}"


@pytest.fixture(scope="module")
def training_base(tmp_path_factory):
    base = tmp_path_factory.mktemp("freeze_base")
    return base, build_training_base(base)


@pytest.fixture(scope="module")
def base_provenance():
    return clean_provenance()


@pytest.fixture
def case(tmp_path, monkeypatch, training_base, base_provenance):
    return make_case(tmp_path, monkeypatch, training_base[0], base_provenance)


@pytest.fixture
def no_execution(monkeypatch):
    """Every solver and worker entry point fails the test if it is reached."""
    import multiprocessing

    from om_lab import certify, solvers

    for target, name in [
        (wx, "solve_dpll"), (wx, "reference_certificate"), (solvers, "solve_dpll"),
        (solvers, "solve_pysat"), (certify, "solve_pysat"), (multiprocessing, "get_context"),
    ]:
        monkeypatch.setattr(target, name, _forbidden)


# ---------------------------------------------------------------------------
# NOVA-R10-01: the two-stage freeze (positive path)
# ---------------------------------------------------------------------------


def test_two_stage_freeze_issues_an_authorisation_for_exactly_this_stage_a(case):
    auth = case.verify()
    assert freeze.is_issued(auth)
    assert auth.stage_a_sha256 == sha256_file(case.stage_a)
    assert auth.stage_b_sha256 == sha256_file(case.stage_b)
    assert auth.execution_commit == HEAD and auth.head_commit == HEAD
    assert auth.authorized_by == "Lumi (test)"
    assert auth.test_schedule_sha256 == freeze.schedule_sha256(TEST_SPECS)
    assert auth.settings == freeze.make_settings(**SETTINGS)
    stage_b = case.stage_b_doc()
    assert set(stage_b) == freeze.STAGE_B_KEYS
    assert stage_b["status"] == "FROZEN" and stage_b["confirmatory_authorized"] is True
    assert stage_b["test_split_unexposed"] is True
    assert stage_b["stage_a_sha256"] == auth.stage_a_sha256


def test_stage_a_records_every_b4_field(case):
    doc = case.stage_a_doc()
    assert set(doc) == freeze.STAGE_A_KEYS
    assert doc["code"] == {"commit": HEAD, "frozen_paths": freeze.frozen_repo_paths(), "tree_clean": True}
    assert doc["runner_version"] == wx.RUNNER_VERSION
    assert doc["orchestration_version"] == wx.ORCHESTRATION_VERSION
    python = doc["environment"]["python"]
    assert python["implementation"] == platform.python_implementation()
    assert python["version"] == platform.python_version()
    packages = doc["environment"]["packages"]
    assert packages == freeze.dependency_inventory()
    assert {"numpy", "python-sat"} <= set(packages)
    assert doc["environment"]["reference_backend"]["compiled_files_sha256"]
    assert doc["source_sha256"] == wx.source_hashes() and "freeze.py" in doc["source_sha256"]
    assert doc["function_sha256"] == wx.function_hashes()
    assert doc["checker"]["source_sha256"] == wx.checker_source_sha256()
    assert doc["seed_manifest_sha256"] == wx.seed_manifest_sha256()
    assert doc["protocol"] == wx.protocol_constants()
    documents = doc["documents"]
    assert documents["protocol"]["path"] == freeze.PROTOCOL_DOC
    assert len(documents["protocol"]["sha256"]) == 64
    assert [a["path"] for a in documents["amendments"]] == list(freeze.DEFAULT_AMENDMENT_DOCS)
    assert all(len(a["sha256"]) == 64 for a in documents["amendments"])
    assert doc["settings"] == freeze.make_settings(**SETTINGS)
    assert doc["population"]["test"] == freeze.population_summary(TEST_SPECS)
    assert (doc["population"]["test"]["n_instances"], doc["population"]["test"]["n_cells"]) == (840, 28)
    training = doc["training"]
    assert training["records_sha256"] == sha256_file(case.records_path)
    assert training["independent_reproduction_sha256"] == training["records_sha256"]
    assert training["certificate_manifest_sha256"] == sha256_file(case.cert_manifest_path)
    assert doc["model"]["sha256"] == sha256_file(case.model)
    model = json.loads(case.model.read_text(encoding="utf-8"))
    assert model["n_train"] == 16 and isinstance(model["m0_m1"]["beta"], float)


def test_any_edit_to_stage_a_breaks_the_stage_b_binding(case):
    # Even a byte-level re-serialisation with identical content is a different Stage A.
    case.stage_a.write_text(json.dumps(case.stage_a_doc(), indent=4, sort_keys=True), encoding="utf-8")
    with pytest.raises(REFUSED, match="authorises a different Stage A"):
        case.verify(deep_training=False)


# ---------------------------------------------------------------------------
# NOVA-R10-01 / ACE-PLAN-01: every Stage A field missing or tampered is refused
# ---------------------------------------------------------------------------


def _set(path, value):
    """Mutation that sets (or transforms, when ``value`` is callable) a nested field."""

    def mutate(doc):
        target = doc
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value(target[path[-1]]) if callable(value) else value

    return mutate


def _first_amendment_hash(doc):
    doc["documents"]["amendments"][0]["sha256"] = flip_hex(doc["documents"]["amendments"][0]["sha256"])


def _records_hash_both(doc):
    new = flip_hex(doc["training"]["records_sha256"])
    doc["training"].update(records_sha256=new, independent_reproduction_sha256=new)


STAGE_A_TAMPERING = [
    ("kind", _set(["kind"], "OM-C001-R2/freeze-stage-x"), "kind mismatch"),
    ("experiment", _set(["experiment"], "OM-C001-R1"), "experiment mismatch"),
    ("schema-version", _set(["freeze_schema_version"], 3), "freeze_schema_version"),
    ("schema-version-float", _set(["freeze_schema_version"], 2.0), "freeze_schema_version"),
    ("runner-version", _set(["runner_version"], "9.9.9"), "runner_version differs"),
    ("orchestration-version", _set(["orchestration_version"], "0.0.1"), "orchestration_version differs"),
    ("created-not-a-time", _set(["created_utc"], "yesterday"), "created_utc"),
    ("created-naive", _set(["created_utc"], "2026-11-25T00:00:00"), "created_utc"),
    ("commit-not-hex", _set(["code", "commit"], "z" * 40), "40-hex"),
    ("commit-unknown", _set(["code", "commit"], "0" * 40), "not in this checkout"),
    ("tree-recorded-dirty", _set(["code", "tree_clean"], False), "dirty tree"),
    ("frozen-paths-dropped", _set(["code", "frozen_paths"], lambda paths: paths[1:]), "frozen_paths"),
    ("source-hash", _set(["source_sha256", "solvers.py"], flip_hex), "source_sha256 differs"),
    ("source-hash-freeze-py", _set(["source_sha256", "freeze.py"], flip_hex), "source_sha256 differs"),
    ("function-hash", _set(["function_sha256", "solvers.solve_dpll"], flip_hex), "function_sha256 differs"),
    ("protocol-doc-hash", _set(["documents", "protocol", "sha256"], flip_hex), "document hashes differ"),
    ("amendment-doc-hash", _first_amendment_hash, "document hashes differ"),
    ("b4-amendment-dropped", _set(["documents", "amendments"], lambda a: a[1:]), "ADVERSARIAL_REVIEW_01"),
    ("python-patch", _set(["environment", "python", "version"], _bump_patch), "exact Python version"),
    ("python-implementation", _set(["environment", "python", "implementation"], "PyPy"), "Python implementation"),
    ("dependency-numpy", _set(["environment", "packages", "numpy"], "0.0.0"), "installed dependencies differ"),
    ("dependency-python-sat", _set(["environment", "packages", "python-sat"], "0.0.0"),
     "installed dependencies differ"),
    ("dependency-added", _set(["environment", "packages", "extra-package"], "1.0"), "installed dependencies differ"),
    ("dependency-removed", lambda d: d["environment"]["packages"].pop("numpy"), "installed dependencies differ"),
    ("architecture", _set(["environment", "platform", "machine"], "other-arch"), "architecture"),
    ("backend-provenance", _set(["environment", "reference_backend", "python_sat_version"], "0.0.0"),
     "backend provenance"),
    ("checker-hash", _set(["checker", "source_sha256"], flip_hex), "checker differs"),
    ("checker-drat-trim-added", _set(["checker", "drat_trim"], {"path": "/nonexistent/drat-trim", "sha256": "0" * 64}),
     "checker differs"),
    ("seed-manifest-hash", _set(["seed_manifest_sha256"], flip_hex), "seed_manifest_sha256 differs"),
    ("protocol-budget", _set(["protocol", "budget_b"], 20000), "protocol differs"),
    ("protocol-max-seconds", _set(["protocol", "max_seconds"], 60), "protocol differs"),
    ("settings-watchdog", _set(["settings", "watchdog_s"], 1200.0), "requested execution settings differ"),
    ("settings-retries", _set(["settings", "max_attempts"], 5), "requested execution settings differ"),
    ("settings-workers-zero", _set(["settings", "workers"], 0), "settings.workers"),
    ("settings-watchdog-int", _set(["settings", "watchdog_s"], 600), "settings.watchdog_s"),
    ("settings-no-certificates", _set(["settings", "keep_certificates"], False), "keep_certificates"),
    ("settings-budget", _set(["settings", "budget_b"], 9999), "settings.budget_b"),
    ("settings-extra-key", _set(["settings", "retry_override"], 9), "settings keys"),
    ("test-schedule-hash", _set(["population", "test", "schedule_sha256"], flip_hex), "population schedules differ"),
    ("test-population-size", _set(["population", "test", "n_instances"], 839), "population schedules differ"),
    ("train-population-size", _set(["population", "train", "n_instances"], 1959), "population schedules differ"),
    ("training-records-hash", _records_hash_both, "training records file hash differs"),
    ("training-not-reproduced", _set(["training", "independent_reproduction_sha256"], flip_hex),
     "not independently reproduced"),
    ("training-reproducer-blank", _set(["training", "reproduced_by"], " "), "reproduced_by"),
    ("training-count", _set(["training", "n_records"], 15), "n_records"),
    ("training-records-missing", _set(["training", "records_path"], "missing.jsonl"),
     "training records file is missing"),
    ("training-manifest-hash", _set(["training", "certificate_manifest_sha256"], flip_hex),
     "certificate manifest hash differs"),
    ("training-manifest-missing", _set(["training", "certificate_manifest_path"], "missing.json"),
     "certificate manifest is missing"),
    ("training-certificates-missing", _set(["training", "certificates_dir"], "no-such-dir"),
     "certificates directory is missing"),
    ("model-hash", _set(["model", "sha256"], flip_hex), "fitted model file hash differs"),
    ("model-missing", _set(["model", "path"], "no-such-model.json"), "fitted model file is missing"),
]


@pytest.mark.parametrize("key", sorted(freeze.STAGE_A_KEYS))
def test_stage_a_missing_field_refused(case, key):
    case.edit_stage_a(lambda doc: doc.pop(key))
    with pytest.raises(REFUSED, match="Stage A keys differ"):
        case.verify(deep_training=False)


def test_stage_a_unknown_field_refused(case):
    case.edit_stage_a(lambda doc: doc.update(note="added after the freeze"))
    with pytest.raises(REFUSED, match="Stage A keys differ"):
        case.verify(deep_training=False)


@pytest.mark.parametrize("label,mutate,match", STAGE_A_TAMPERING, ids=[c[0] for c in STAGE_A_TAMPERING])
def test_stage_a_tampered_field_refused_even_when_re_signed(case, label, mutate, match):
    # Stage B is re-signed for the edited bytes, so the refusal must come
    # from Stage A's own check of that field, not from the hash binding.
    case.edit_stage_a(mutate)
    with pytest.raises(REFUSED, match=match):
        case.verify(deep_training=False)


# ---------------------------------------------------------------------------
# Stage B: every field missing or tampered is refused
# ---------------------------------------------------------------------------


STAGE_B_TAMPERING = [
    ("kind", {"kind": freeze.STAGE_A_KIND}, "Stage B kind"),
    ("experiment", {"experiment": "OM-C001-R1"}, "Stage B experiment"),
    ("schema-version", {"freeze_schema_version": 1}, "freeze_schema_version"),
    ("other-stage-a", {"stage_a_sha256": "0" * 64}, "authorises a different Stage A"),
    ("status-draft", {"status": "DRAFT"}, "not FROZEN"),
    ("authorised-string-true", {"confirmatory_authorized": "true"}, "confirmatory_authorized"),
    ("authorised-false", {"confirmatory_authorized": False}, "confirmatory_authorized"),
    ("authorised-by-blank", {"authorized_by": "  "}, "authorized_by"),
    ("authorised-by-null", {"authorized_by": None}, "authorized_by"),
    ("authorised-at-null", {"authorized_at_utc": None}, "authorized_at_utc"),
    ("authorised-at-naive", {"authorized_at_utc": "2026-11-25T12:00:00"}, "authorized_at_utc"),
    ("authorised-at-not-utc", {"authorized_at_utc": "2026-11-25T12:00:00+01:00"}, "authorized_at_utc"),
    ("authorised-in-future", {"authorized_at_utc": "2999-01-01T00:00:00+00:00"}, "in the future"),
    ("authorised-before-stage-a", {"authorized_at_utc": "2000-01-01T00:00:00+00:00"}, "precedes"),
    ("test-split-exposed", {"test_split_unexposed": False}, "test_split_unexposed"),
    ("test-split-string", {"test_split_unexposed": "yes"}, "test_split_unexposed"),
    ("unknown-field", {"note": "x"}, "Stage B keys differ"),
]


@pytest.mark.parametrize("key", sorted(freeze.STAGE_B_KEYS))
def test_stage_b_missing_field_refused(case, key):
    case.edit_stage_b(lambda doc: doc.pop(key))
    with pytest.raises(REFUSED, match="Stage B keys differ"):
        case.verify(deep_training=False)


@pytest.mark.parametrize("label,update,match", STAGE_B_TAMPERING, ids=[c[0] for c in STAGE_B_TAMPERING])
def test_stage_b_tampered_field_refused(case, label, update, match):
    case.edit_stage_b(lambda doc: doc.update(update))
    with pytest.raises(REFUSED, match=match):
        case.verify(deep_training=False)


@pytest.mark.parametrize(
    "label,rewrite,match",
    [
        ("duplicate-key", lambda t: t.replace('"status": "FROZEN"', '"status": "DRAFT", "status": "FROZEN"'),
         "duplicate JSON key"),
        ("nan", lambda t: t.replace('"test_split_unexposed": true', '"test_split_unexposed": NaN'),
         "non-finite JSON number"),
        ("not-an-object", lambda t: "[]", "must be an object"),
        ("not-json", lambda t: t[:-10], "cannot read the freeze records"),
    ],
)
def test_stage_b_malformed_file_refused(case, label, rewrite, match):
    text = case.stage_b.read_text(encoding="utf-8")
    case.stage_b.write_text(rewrite(text), encoding="utf-8")
    with pytest.raises(REFUSED, match=match):
        case.verify(deep_training=False)


def test_missing_freeze_records_refused(case):
    with pytest.raises(REFUSED, match="requires --stage-a and --stage-b"):
        freeze.verify_for_execution(case.stage_a, None, requested_settings=freeze.make_settings(**SETTINGS))
    with pytest.raises(REFUSED, match="requires --stage-a and --stage-b"):
        freeze.verify_for_execution(None, case.stage_b, requested_settings=freeze.make_settings(**SETTINGS))
    case.stage_b.unlink()
    with pytest.raises(REFUSED, match="cannot read the freeze records"):
        case.verify(deep_training=False)


def test_authorisation_names_the_stage_b_bytes_that_were_verified(case, monkeypatch):
    # ACE-GATE-D-02, runner side: the analysis handoff binds the test run to
    # the run manifest's authorization.stage_b_sha256, so it must be the hash
    # of the Stage B bytes that were verified, and a Stage B replaced while
    # verification runs must stop the run.
    verified = case.stage_b.read_bytes()
    auth = case.verify(deep_training=False)
    assert auth.stage_b_sha256 == sha256_file(case.stage_b) == freeze._sha256_bytes(verified)
    real_verify_stage_a = freeze.verify_stage_a

    def replace_stage_b_during_verification(*args, **kwargs):
        case.stage_b.write_bytes(b"{}\n")  # not an authorisation
        return real_verify_stage_a(*args, **kwargs)

    monkeypatch.setattr(freeze, "verify_stage_a", replace_stage_b_during_verification)
    with pytest.raises(REFUSED, match="Stage B changed while it was being verified"):
        case.verify(deep_training=False)


# ---------------------------------------------------------------------------
# Ace section 5: the running environment drifts after the freeze
# (Python patch version, pinned dependency, dirty tree, changed code)
# ---------------------------------------------------------------------------


LIVE_DRIFT = [
    ("python-patch", lambda p: p["python"].update(version=_bump_patch(p["python"]["version"])),
     "exact Python version"),
    ("python-implementation", lambda p: p["python"].update(implementation="PyPy"), "Python implementation"),
    ("pinned-numpy", lambda p: p["packages"].update(numpy="0.0.0"), "installed dependencies differ"),
    ("pinned-python-sat", lambda p: p["packages"].update({"python-sat": "0.0.0"}), "installed dependencies differ"),
    ("dependency-installed", lambda p: p["packages"].update({"new-dependency": "1.0"}),
     "installed dependencies differ"),
    ("dependency-uninstalled", lambda p: p["packages"].pop("numpy"), "installed dependencies differ"),
    ("architecture", lambda p: p["platform"].update(machine="other-arch"), "architecture"),
    ("backend-binary", lambda p: p["reference_backend"]["compiled_files_sha256"].update({"x.so": "0" * 64}),
     "backend provenance"),
    ("dirty-tree", lambda p: p["git"].update(tree_clean=False, dirty=[" M lab/om_lab/solvers.py"]), "dirty now"),
    ("untracked-file", lambda p: p["git"].update(tree_clean=False, dirty=["?? lab/om_lab/scratch.py"]),
     "dirty now"),
    ("git-unavailable", lambda p: p["git"].update(available=False), "git provenance is unavailable"),
    ("source-changed", lambda p: p["source_sha256"].update({"solvers.py": "0" * 64}), "source_sha256 differs"),
    ("function-changed", lambda p: p["function_sha256"].update({"solvers.solve_dpll": "0" * 64}),
     "function_sha256 differs"),
    ("checker-changed", lambda p: p["checker"].update(source_sha256="0" * 64), "checker differs"),
    ("protocol-doc-changed", lambda p: p["documents"]["protocol"].update(sha256="0" * 64), "document hashes differ"),
    ("seed-scheme-changed", lambda p: p.update(seed_manifest_sha256="0" * 64), "seed_manifest_sha256 differs"),
    ("protocol-constants-changed", lambda p: p["protocol"].update(budget_b=20000), "protocol differs"),
]


@pytest.mark.parametrize("label,drift,match", LIVE_DRIFT, ids=[c[0] for c in LIVE_DRIFT])
def test_environment_drift_after_the_freeze_refused(case, label, drift, match):
    drift(case.live.provenance)
    with pytest.raises(REFUSED, match=match):
        case.verify(deep_training=False)


def test_frozen_paths_changed_after_the_execution_commit_refused(case):
    case.live.provenance["git"]["head"] = LATER
    case.live.commits = {HEAD: ["lab/om_lab/solvers.py"], LATER: []}
    with pytest.raises(REFUSED, match="changed since the execution commit"):
        case.verify(deep_training=False)


def test_a_later_commit_that_leaves_frozen_paths_unchanged_is_accepted(case):
    # e.g. committing Stage B or a results note after the freeze: the
    # execution commit never has to contain a hash of a manifest naming it.
    case.live.provenance["git"]["head"] = LATER
    case.live.commits = {HEAD: [], LATER: []}
    auth = case.verify(deep_training=False)
    assert auth.execution_commit == HEAD and auth.head_commit == LATER


# ---------------------------------------------------------------------------
# Ace section 5: watchdog / retry / worker settings modified after the freeze
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "override", [dict(watchdog_s=1200.0), dict(watchdog_s=0.5), dict(max_attempts=5), dict(max_attempts=1),
                 dict(workers=8)],
    ids=["watchdog-up", "watchdog-down", "retries-up", "retries-down", "workers"],
)
def test_settings_changed_after_the_freeze_refused(case, override):
    settings = dict(SETTINGS, **override)
    with pytest.raises(REFUSED, match="requested execution settings differ"):
        case.verify(deep_training=False, requested_settings=freeze.make_settings(**settings))


@pytest.mark.parametrize("override", [dict(watchdog_s=1200.0), dict(max_attempts=5)], ids=["watchdog", "retries"])
def test_official_run_with_changed_settings_refused_before_scheduling(case, no_execution, monkeypatch, tmp_path,
                                                                      override):
    monkeypatch.setattr(wx, "run_specs", _forbidden)
    settings = dict(SETTINGS, **override)
    with pytest.raises(REFUSED, match="requested execution settings differ"):
        wx.run_split(population="confirmatory", split="test", out_dir=tmp_path / "out",
                     stage_a_path=case.stage_a, stage_b_path=case.stage_b, keep_certificates=True, **settings)
    assert not (tmp_path / "out").exists()


# ---------------------------------------------------------------------------
# Non-executing preflight (Ace gate review, section 3)
# ---------------------------------------------------------------------------


def test_preflight_builds_the_840_schedule_without_authorisation_or_any_solver(case, no_execution, monkeypatch,
                                                                              tmp_path):
    monkeypatch.setattr(wx, "run_instance", _forbidden)
    monkeypatch.setattr(wx, "run_specs", _forbidden)
    case.stage_b.unlink()  # no authorisation exists yet
    out = tmp_path / "preflight.json"
    report = freeze.preflight(case.stage_a, out_path=out)
    assert report["passed"] is True, report["problems"]
    assert report["solver_launched"] is False and report["authorization_required"] is False
    assert report["deep_training_checked"] is True
    schedule = report["test_schedule"]
    assert (schedule["n_instances"], schedule["n_cells"], schedule["per_cell"]) == (840, 28, 30)
    assert schedule["schedule_sha256"] == freeze.schedule_sha256(TEST_SPECS)
    assert (schedule["first"], schedule["last"]) == ("OM-C001-R2|30|380|70", "OM-C001-R2|60|500|99")
    assert schedule["indices"] == [70, 99]
    assert report["training_schedule"]["n_instances"] == 1960
    assert report["stage_a_sha256"] == sha256_file(case.stage_a)
    assert json.loads(out.read_text(encoding="utf-8"))["passed"] is True


def _alter_coefficient(case) -> None:
    model = json.loads(case.model.read_text(encoding="utf-8"))
    model["m0_m1"]["beta"] = model["m0_m1"]["beta"] + 1e-9
    case.model.write_bytes(freeze.model_bytes(model))


def test_preflight_reports_a_failing_stage_a(case, no_execution):
    _alter_coefficient(case)
    report = freeze.preflight(case.stage_a)
    assert report["passed"] is False and report["solver_launched"] is False
    assert any("fitted model file hash differs" in p for p in report["problems"])


def test_authorize_requires_confirmation_identity_and_a_passing_preflight(case, tmp_path):
    out = tmp_path / "stage_b.json"
    with pytest.raises(REFUSED, match="unexposed"):
        freeze.authorize(case.stage_a, authorized_by="Lumi", test_split_unexposed=False, out_path=out)
    with pytest.raises(REFUSED, match="name the coordinator"):
        freeze.authorize(case.stage_a, authorized_by=" ", test_split_unexposed=True, out_path=out)
    _alter_coefficient(case)
    with pytest.raises(REFUSED, match="preflight: fitted model file hash differs"):
        freeze.authorize(case.stage_a, authorized_by="Lumi", test_split_unexposed=True, out_path=out)
    assert not out.exists()


def test_attack_authorize_with_a_dirty_source_tree_rejected(case, tmp_path):
    out = tmp_path / "stage_b.json"
    case.live.provenance["git"].update(tree_clean=False, dirty=[" M lab/om_lab/width_experiment.py"])
    with pytest.raises(REFUSED, match="dirty now"):
        freeze.authorize(case.stage_a, authorized_by="Lumi", test_split_unexposed=True, out_path=out)
    assert not out.exists()


# ---------------------------------------------------------------------------
# Stage A construction refuses bad inputs (and writes nothing)
# ---------------------------------------------------------------------------


def _build(case, out_dir, **overrides):
    kwargs = dict(
        out_dir=out_dir, training_records_path=case.records_path, training_certificates_dir=case.cert_dir,
        training_certificate_manifest_path=case.cert_manifest_path,
        independent_reproduction_sha256=sha256_file(case.records_path), reproduced_by="reproducer",
        settings=freeze.make_settings(**SETTINGS),
    )
    kwargs.update(overrides)
    return freeze.build_stage_a(**kwargs)


BUILD_REFUSALS = [
    ("dirty-tree", lambda c: c.live.provenance["git"].update(tree_clean=False, dirty=[" M lab/om_lab/x.py"]), {},
     "not clean"),
    ("no-git", lambda c: c.live.provenance["git"].update(available=False, head=None), {},
     "git provenance is unavailable"),
    ("protocol-doc-missing", lambda c: c.live.provenance["documents"]["protocol"].update(sha256=None), {},
     "document is missing"),
    ("not-reproduced", None, {"independent_reproduction_sha256": "0" * 64}, "independent reproduction hash differs"),
    ("no-reproducer", None, {"reproduced_by": " "}, "reproduced_by"),
    ("workers-zero", None, {"settings": {**freeze.make_settings(**SETTINGS), "workers": 0}}, "settings.workers"),
    ("no-certificates", None, {"settings": {**freeze.make_settings(**SETTINGS), "keep_certificates": False}},
     "keep_certificates"),
]


@pytest.mark.parametrize("label,prepare,overrides,match", BUILD_REFUSALS, ids=[c[0] for c in BUILD_REFUSALS])
def test_build_stage_a_refuses(case, tmp_path, label, prepare, overrides, match):
    if prepare is not None:
        prepare(case)
    out_dir = tmp_path / "new_freeze"
    with pytest.raises(REFUSED, match=match):
        _build(case, out_dir, **overrides)
    assert not out_dir.exists()


def test_build_stage_a_refuses_an_incomplete_training_population(case, monkeypatch, tmp_path):
    bigger = wx.build_specs("confirmatory", "train", n_values=[30, 40], a_values=[426, 500], indices=range(0, 5))
    monkeypatch.setattr(freeze, "expected_training_specs", lambda: list(bigger))
    with pytest.raises(REFUSED, match="not exactly the 20-instance training population"):
        _build(case, tmp_path / "new_freeze")


def test_build_stage_a_refuses_training_with_an_error_record(case, tmp_path):
    records = case.records()
    spec = subset_specs()[0]
    records[0] = wx.error_record(spec, budget=wx.BUDGET_B, kind="watchdog", attempts=3, detail="test")
    case.write_records(records)
    with pytest.raises(REFUSED, match="verification gate is not ready"):
        _build(case, tmp_path / "new_freeze")


# ---------------------------------------------------------------------------
# Ace section 5: substitute a retained .drat / forge a verification status /
# alter a frozen training coefficient (deep verification at execution time)
# ---------------------------------------------------------------------------


def test_attack_substituted_training_drat_rejected_at_execution(case):
    u1, u2 = case.unsat_ids()[:2]
    shutil.copyfile(case.cert_files(u2)[1], case.cert_files(u1)[1])
    with pytest.raises(REFUSED, match="retained proof bytes differ"):
        case.verify()
    assert freeze.preflight(case.stage_a)["passed"] is False


def _forge_training_record(case, mutate) -> None:
    records = case.records()
    mutate(records)
    case.write_records(records)
    new = sha256_file(case.records_path)
    case.edit_stage_a(lambda d: d["training"].update(records_sha256=new, independent_reproduction_sha256=new))


def _first_with(records, status):
    return next(r for r in records if r["status"] == status)


def _sole_satisfier_flip(spec, model):
    inst = generate_random_3sat(n_vars=spec.n, n_clauses=spec.m, seed=spec.seed)
    for clause in inst.clauses:
        true_lits = [lit for lit in clause if model[abs(lit) - 1] == lit]
        if len(true_lits) == 1:
            broken = list(model)
            broken[abs(true_lits[0]) - 1] = -broken[abs(true_lits[0]) - 1]
            assert not verify_cnf_assignment(inst.clauses, broken)
            return broken
    pytest.skip("no clause with a unique satisfying literal")


def _spec_of(record):
    return next(s for s in subset_specs() if s.instance_id == record["instance_id"])


FORGED_TRAINING_STATUS = [
    ("unsat-by-construction",
     lambda rs: _first_with(rs, "UNSAT").update(verification_status="UNSAT_KNOWN_BY_CONSTRUCTION"),
     "construction certificate is impossible"),
    ("unsat-invalid-certificate",
     lambda rs: _first_with(rs, "UNSAT")["reference"]["certificate"].update(result="INVALID"),
     "not a VALID DRAT proof"),
    ("unsat-without-reference", lambda rs: _first_with(rs, "UNSAT").update(reference=None),
     "no reference UNSAT certificate"),
    ("sat-model-broken",
     lambda rs: _first_with(rs, "SAT").update(
         model=_sole_satisfier_flip(_spec_of(_first_with(rs, "SAT")), _first_with(rs, "SAT")["model"])),
     "fails re-verification"),
]


@pytest.mark.parametrize("label,mutate,match", FORGED_TRAINING_STATUS, ids=[c[0] for c in FORGED_TRAINING_STATUS])
def test_attack_forged_training_verification_status_rejected(case, label, mutate, match):
    # The records file, Stage A's hashes and Stage B are all made consistent
    # with the forgery; deep verification must still refuse it.
    _forge_training_record(case, mutate)
    with pytest.raises(REFUSED, match=match):
        case.verify()


def test_attack_altered_frozen_coefficient_rejected(case):
    _alter_coefficient(case)
    with pytest.raises(REFUSED, match="fitted model file hash differs"):
        case.verify(deep_training=False)


def test_attack_altered_coefficient_with_rehashed_stage_a_rejected_by_recomputation(case):
    _alter_coefficient(case)
    new = sha256_file(case.model)
    case.edit_stage_a(lambda d: d["model"].update(sha256=new))
    with pytest.raises(REFUSED, match="recomputed from the training records"):
        case.verify()


# ---------------------------------------------------------------------------
# NOVA-R10-02 / ACE-PLAN-02: exact population; one test index refused
# ---------------------------------------------------------------------------


def test_canonical_schedules_validate_exactly():
    assert freeze.validate_schedule(TEST_SPECS, "test") == []
    train = wx.build_specs("confirmatory", "train")
    assert freeze.validate_schedule(train, "train") == []
    test_summary = freeze.population_summary(TEST_SPECS)
    train_summary = freeze.population_summary(train)
    assert (test_summary["n_instances"], test_summary["n_cells"], test_summary["per_cell"]) == (840, 28, 30)
    assert (train_summary["n_instances"], train_summary["n_cells"], train_summary["per_cell"]) == (1960, 28, 70)
    assert not {s.instance_id for s in train} & {s.instance_id for s in TEST_SPECS}


_TRAIN_69 = wx.build_specs("confirmatory", "train", n_values=[60], a_values=[500], indices=[69])[0]
WRONG_SCHEDULES = [
    ("one-index", lambda: [s for s in TEST_SPECS if s.index == 70], "missing"),
    ("single-instance", lambda: TEST_SPECS[:1], "missing"),
    ("one-cell", lambda: [s for s in TEST_SPECS if (s.n, s.a_hundredths) == (30, 426)], "cells"),
    ("empty", lambda: [], "missing"),
    ("duplicate-preserving-count", lambda: TEST_SPECS[:-1] + [TEST_SPECS[0]], "duplicate"),
    ("reordered", lambda: TEST_SPECS[1:] + TEST_SPECS[:1], "canonical"),
    ("training-split", lambda: wx.build_specs("confirmatory", "train"), "unexpected"),
    ("training-index-in-test", lambda: TEST_SPECS[:-1] + [_TRAIN_69], "outside the test split"),
    ("pilot-population", lambda: wx.build_specs("pilot", "test"), "population/split"),
    ("wrong-seed", lambda: [dataclasses.replace(TEST_SPECS[0], seed=TEST_SPECS[0].seed ^ 1)] + TEST_SPECS[1:],
     "seed differs"),
    ("wrong-clause-count", lambda: [dataclasses.replace(TEST_SPECS[0], m=TEST_SPECS[0].m + 1)] + TEST_SPECS[1:],
     "clause count"),
]


@pytest.mark.parametrize("label,build,match", WRONG_SCHEDULES, ids=[c[0] for c in WRONG_SCHEDULES])
def test_wrong_test_schedules_are_rejected(label, build, match):
    problems = freeze.validate_schedule(build(), "test")
    assert problems and any(match in p for p in problems), problems


@pytest.mark.parametrize(
    "subset", [dict(indices=[70]), dict(n_values=[30], a_values=[400], indices=[70]), dict(n_values=[30]),
               dict(a_values=[426])],
    ids=["one-index", "one-instance", "one-n", "one-A"],
)
@pytest.mark.parametrize("dry_run", [False, True], ids=["official", "dry-run"])
def test_attack_test_split_subset_rejected_even_with_authorisation(case, no_execution, monkeypatch, tmp_path,
                                                                   subset, dry_run):
    monkeypatch.setattr(wx, "run_specs", _forbidden)
    with pytest.raises(REFUSED, match="exact frozen 840-instance population"):
        wx.run_split(population="confirmatory", split="test", out_dir=tmp_path / "out",
                     stage_a_path=case.stage_a, stage_b_path=case.stage_b, keep_certificates=True,
                     dry_run=dry_run, **SETTINGS, **subset)
    with pytest.raises(REFUSED, match="exact frozen 840-instance population"):
        wx.run_split(population="confirmatory", split="test", out_dir=tmp_path / "out", diagnostic_subset=True,
                     stage_a_path=case.stage_a, stage_b_path=case.stage_b, keep_certificates=True,
                     dry_run=dry_run, **SETTINGS, **subset)
    assert not (tmp_path / "out").exists()


def test_authorised_full_dry_run_is_accepted_and_runs_nothing(case, no_execution, monkeypatch, tmp_path):
    monkeypatch.setattr(wx, "run_specs", _forbidden)
    summary = wx.run_split(population="confirmatory", split="test", out_dir=tmp_path / "out", dry_run=True,
                           stage_a_path=case.stage_a, stage_b_path=case.stage_b, **SETTINGS)
    assert summary["dry_run"] is True and summary["solver_launched"] is False
    assert summary["n_instances"] == summary["n_population"] == 840 and summary["complete"] is True
    assert summary["schedule_sha256"] == freeze.schedule_sha256(TEST_SPECS)
    assert summary["authorization"]["stage_a_sha256"] == sha256_file(case.stage_a)
    assert summary["authorization"]["authorized_by"] == "Lumi (test)"
    assert not (tmp_path / "out").exists()


def test_unauthorised_full_dry_run_lists_the_schedule_only(no_execution, tmp_path):
    summary = wx.run_split(population="confirmatory", split="test", out_dir=tmp_path / "out", dry_run=True)
    assert summary["n_instances"] == 840 and summary["authorization"] is None
    assert summary["solver_launched"] is False
    train = wx.run_split(population="confirmatory", split="train", out_dir=tmp_path / "out", dry_run=True)
    assert train["n_instances"] == 1960 and train["complete"] is True and train["run_mode"] == "OFFICIAL"
    assert not (tmp_path / "out").exists()


def test_authorised_official_run_hands_exactly_the_frozen_schedule_to_the_runner(case, no_execution, monkeypatch,
                                                                                 tmp_path):
    seen: dict = {}

    def intercept(specs, **kwargs):
        seen["specs"], seen["kwargs"] = list(specs), kwargs
        raise Intercepted

    monkeypatch.setattr(wx, "run_specs", intercept)
    with pytest.raises(Intercepted):
        wx.run_split(population="confirmatory", split="test", out_dir=tmp_path / "out",
                     stage_a_path=case.stage_a, stage_b_path=case.stage_b, keep_certificates=True, **SETTINGS)
    assert [s.instance_id for s in seen["specs"]] == [s.instance_id for s in TEST_SPECS]
    kwargs = seen["kwargs"]
    assert freeze.is_issued(kwargs["authorization"])
    assert kwargs["authorization"].stage_a_sha256 == sha256_file(case.stage_a)
    assert (kwargs["workers"], kwargs["watchdog_s"], kwargs["max_attempts"]) == (2, 600.0, 3)
    assert kwargs["budget"] == wx.BUDGET_B and kwargs["certify"] is True and kwargs["keep_proof"] is True
    assert not kwargs.get("fault_injection")
    assert not (tmp_path / "out").exists()


def _run_specs_kwargs(auth, **override):
    kwargs = dict(workers=2, watchdog_s=600.0, max_attempts=3, keep_proof=True, authorization=auth)
    kwargs.update(override)
    return kwargs


def test_run_specs_guard_accepts_the_issued_authorisation_for_the_exact_schedule(case, monkeypatch):
    auth = case.verify()
    monkeypatch.setattr(wx, "run_instance", _forbidden)

    def intercept(*args, **kwargs):  # where the first worker process would be created
        raise Intercepted

    monkeypatch.setattr(wx.mp, "get_context", intercept)
    with pytest.raises(Intercepted):
        wx.run_specs(TEST_SPECS, **_run_specs_kwargs(auth))


RUN_SPECS_WRONG_SCHEDULE = [
    ("one-index", lambda: [s for s in TEST_SPECS if s.index == 70]),
    ("single-instance", lambda: TEST_SPECS[:1]),
    ("missing-one", lambda: TEST_SPECS[:-1]),
    ("reordered", lambda: list(reversed(TEST_SPECS))),
    ("duplicate-preserving-count", lambda: TEST_SPECS[:-1] + [TEST_SPECS[0]]),
    ("training-index-swapped-in", lambda: TEST_SPECS[:-1] + [_TRAIN_69]),
    ("wrong-seed", lambda: [dataclasses.replace(TEST_SPECS[0], seed=TEST_SPECS[0].seed ^ 1)] + TEST_SPECS[1:]),
]


@pytest.mark.parametrize("label,build", RUN_SPECS_WRONG_SCHEDULE, ids=[c[0] for c in RUN_SPECS_WRONG_SCHEDULE])
def test_run_specs_refuses_any_other_schedule_even_when_authorised(case, no_execution, monkeypatch, label, build):
    monkeypatch.setattr(wx, "run_instance", _forbidden)
    auth = case.verify(deep_training=False)
    with pytest.raises((REFUSED, ValueError)):
        wx.run_specs(build(), **_run_specs_kwargs(auth))


@pytest.mark.parametrize(
    "override",
    [dict(watchdog_s=1200.0), dict(watchdog_s=600), dict(max_attempts=5), dict(workers=1), dict(keep_proof=False),
     dict(certify=False), dict(budget=9999)],
    ids=["watchdog", "watchdog-int", "retries", "workers", "no-proofs", "no-certify", "budget"],
)
def test_run_specs_refuses_settings_that_differ_from_the_freeze(case, no_execution, monkeypatch, override):
    monkeypatch.setattr(wx, "run_instance", _forbidden)
    auth = case.verify(deep_training=False)
    with pytest.raises(REFUSED, match="differs from the frozen value"):
        wx.run_specs(TEST_SPECS, **_run_specs_kwargs(auth, **override))


def test_run_specs_refuses_an_authorisation_it_did_not_issue(case, no_execution, monkeypatch):
    monkeypatch.setattr(wx, "run_instance", _forbidden)
    auth = case.verify(deep_training=False)
    changed = tuple(sorted({**auth.settings, "watchdog_s": 1200.0}.items()))
    forged = [
        None, "authorised", auth.summary(), dataclasses.replace(auth),
        dataclasses.replace(auth, settings_items=changed), copy.copy(auth), pickle.loads(pickle.dumps(auth)),
    ]
    for item in forged:
        with pytest.raises(REFUSED, match="issued by"):
            wx.run_specs(TEST_SPECS, **_run_specs_kwargs(item))
    # The settings view is a copy: editing it cannot change what was frozen.
    auth.settings["watchdog_s"] = 1200.0
    assert auth.settings["watchdog_s"] == 600.0


def test_run_instance_refuses_confirmatory_test_specs_outside_the_official_path(no_execution, monkeypatch):
    monkeypatch.setattr(wx, "generate_random_3sat", _forbidden)
    with pytest.raises(REFUSED, match="authorised production path"):
        wx.run_instance(TEST_SPECS[0], budget=wx.BUDGET_B, certify=True)
    with pytest.raises(REFUSED, match="issued by"):
        wx.run_specs(TEST_SPECS[:1], workers=0)


# ---------------------------------------------------------------------------
# NOVA-R10-04 / ACE-PLAN-06: fault injection refused at every execution layer
# ---------------------------------------------------------------------------


def test_fault_injection_refused_for_confirmatory_specs_at_every_layer(no_execution, monkeypatch, tmp_path):
    monkeypatch.setattr(wx, "generate_random_3sat", _forbidden)
    train_spec = subset_specs()[0]
    pilot_spec = wx.build_specs("pilot", "train", n_values=[30], a_values=[426], indices=[0])[0]
    fault = {"raise": True}
    for spec in (train_spec, TEST_SPECS[0]):
        with pytest.raises(ValueError, match="fault injection is refused"):
            wx.run_instance(spec, budget=wx.BUDGET_B, certify=True, fault=fault)
    with pytest.raises(ValueError, match="fault injection is refused"):
        wx.run_specs([train_spec], workers=0, fault_injection={train_spec.instance_id: fault})
    with pytest.raises(ValueError, match="fault injection is refused"):  # fault aimed at a pilot spec in a mixed list
        wx.run_specs([pilot_spec, train_spec], workers=0, fault_injection={pilot_spec.instance_id: fault})
    with pytest.raises(ValueError, match="fault injection is refused"):
        wx.run_split(population="confirmatory", split="train", out_dir=tmp_path / "out", workers=0,
                     n_values=[30], a_values=[426], indices=[0], diagnostic_subset=True, keep_certificates=True,
                     fault_injection={train_spec.instance_id: fault})
    assert not (tmp_path / "out").exists()


# ---------------------------------------------------------------------------
# NOVA-R10-03: partial outputs are explicitly marked
# ---------------------------------------------------------------------------


def test_confirmatory_training_subsets_need_the_diagnostic_flag(no_execution, tmp_path):
    out = tmp_path / "out"
    with pytest.raises(ValueError, match="diagnostic_subset"):
        wx.run_split(population="confirmatory", split="train", out_dir=out, indices=[0], keep_certificates=True,
                     workers=0)
    with pytest.raises(ValueError, match="explicit subset"):
        wx.run_split(population="confirmatory", split="train", out_dir=out, diagnostic_subset=True,
                     keep_certificates=True, workers=0, dry_run=True)
    with pytest.raises(ValueError, match="confirmatory population only"):
        wx.run_split(population="pilot", split="train", out_dir=out, indices=[0], diagnostic_subset=True, workers=0)
    with pytest.raises(ValueError, match="retain certificates"):
        wx.run_split(population="confirmatory", split="train", out_dir=out, indices=[0], diagnostic_subset=True,
                     workers=0)
    assert not out.exists()


def test_diagnostic_training_subset_is_written_and_marked_partial(training_base):
    _, run = training_base
    assert run["run_mode"] == "DIAGNOSTIC_SUBSET" and run["complete"] is False
    assert Path(run["results_path"]).name == f"{STEM}_results.jsonl"
    manifest = json.loads(Path(run["run_manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["run_mode"] == "DIAGNOSTIC_SUBSET"
    assert manifest["complete"] is False and manifest["partial"] is True
    assert (manifest["n_instances"], manifest["n_population"]) == (16, 1960)
    assert manifest["integrity"]["complete"] is False and manifest["integrity"]["n_population"] == 1960
    assert manifest["orchestration_version"] == wx.ORCHESTRATION_VERSION
    assert manifest["runner_version"] == wx.RUNNER_VERSION
    assert manifest["schedule_sha256"] == freeze.schedule_sha256(subset_specs())
    assert manifest["certificates_retained"] == manifest["integrity"]["status_counts"]["UNSAT"]


def test_partial_confirmatory_combine_must_be_named_partial(training_base, tmp_path):
    _, run = training_base
    with pytest.raises(ValueError, match="no primary record"):
        wx.combine_results([run["results_path"]], tmp_path / "results.jsonl")
    with pytest.raises(ValueError, match="PARTIAL"):
        wx.combine_results([run["results_path"]], tmp_path / "results.jsonl", require_complete=False)
    assert not (tmp_path / "results.jsonl").exists()
    out = wx.combine_results([run["results_path"]], tmp_path / "results_PARTIAL.jsonl", require_complete=False,
                             certificate_manifests=[run["certificate_manifest_path"]])
    assert out["complete"] is False
    manifest = json.loads(Path(out["combine_manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["complete"] is False and manifest["partial"] is True
    assert (manifest["n_records"], manifest["n_population"]) == (16, 2800)
    assert manifest["inputs"] == [{"path": run["results_path"], "sha256": sha256_file(run["results_path"])}]
    combined = json.loads(Path(out["certificate_manifest_path"]).read_text(encoding="utf-8"))
    retained = [e for e in combined if e["retained_files"]]
    assert len(retained) == run["integrity"]["status_counts"]["UNSAT"]
    audit = wx.audit_records(
        wx.read_jsonl(out["results_path"]), population="confirmatory", splits=["train"],
        certificates_dir=Path(run["results_path"]).parent / "certificates",
        certificate_manifest_path=out["certificate_manifest_path"],
    )
    assert audit["retained_certificates"]["passed"] is True
    assert audit["retained_certificates"]["checked"] == len(retained)
    assert audit["passed"] is False  # a 16-instance subset is not the training population
    assert all("no primary record" in f for f in audit["failures"])


# ---------------------------------------------------------------------------
# NOVA-R10-05: status claims are not evidence
# ---------------------------------------------------------------------------


def _subset_records(training_base):
    return wx.read_jsonl(training_base[1]["results_path"])


def test_genuine_training_records_pass_with_every_claim_rechecked(training_base):
    report = wx.integrity_report(_subset_records(training_base), subset_specs(), budget=wx.BUDGET_B,
                                 full_population=subset_specs())
    assert report["passed"] is True and report["verification_gate_ready"] is True
    assert report["complete"] is True and report["evidence_checked_records"] == 16


EVIDENCE_FORGERIES = [
    ("sat-model-broken", "SAT", lambda r, s: r.update(model=_sole_satisfier_flip(s, r["model"])),
     "fails re-verification"),
    ("sat-model-truncated", "SAT", lambda r, s: r.update(model=r["model"][:-1]), "complete assignment"),
    ("sat-model-bools", "SAT", lambda r, s: r.update(model=[True] * s.n), "int literals"),
    ("sat-model-missing", "SAT", lambda r, s: r.update(model=None), "SAT model is not a list"),
    ("formula-hash", "SAT", lambda r, s: r.update(formula_sha256="0" * 64), "formula hash"),
    ("unsat-no-certificate", "UNSAT", lambda r, s: r.update(reference=None), "no reference UNSAT certificate"),
    ("unsat-reference-not-unsat", "UNSAT", lambda r, s: r["reference"].update(status="UNKNOWN"),
     "no reference UNSAT certificate"),
    ("unsat-invalid-certificate", "UNSAT", lambda r, s: r["reference"]["certificate"].update(result="INVALID"),
     "not a VALID DRAT proof"),
    ("unsat-other-checker", "UNSAT", lambda r, s: r["reference"]["certificate"].update(checker_sha256="0" * 64),
     "different proof checker"),
    ("unsat-no-proof-hash", "UNSAT", lambda r, s: r["reference"]["certificate"].update(proof_sha256=None),
     "no proof hash"),
    ("unsat-disagreement", "UNSAT", lambda r, s: r.update(reference_agreement="DISAGREE"), "agreement"),
    ("unsat-by-construction", "UNSAT", lambda r, s: r.update(verification_status="UNSAT_KNOWN_BY_CONSTRUCTION"),
     "construction certificate is impossible"),
    ("verified-flag", "SAT", lambda r, s: r.update(verified=False), "verified flag inconsistent"),
]


@pytest.mark.parametrize("label,status,mutate,match", EVIDENCE_FORGERIES, ids=[c[0] for c in EVIDENCE_FORGERIES])
def test_forged_evidence_fails_integrity(training_base, label, status, mutate, match):
    records = _subset_records(training_base)
    target = _first_with(records, status)
    mutate(target, _spec_of(target))
    report = wx.integrity_report(records, subset_specs(), budget=wx.BUDGET_B)
    assert report["passed"] is False
    assert any(match in f for f in report["failures"]), report["failures"]


TYPE_FORGERIES = [
    ("decisions-none", lambda r: r.update(decisions=None), "decisions is not"),
    ("decisions-string", lambda r: r.update(decisions="7"), "decisions is not"),
    ("decisions-bool", lambda r: r.update(decisions=True), "decisions is not"),
    ("decisions-negative", lambda r: r.update(decisions=-1), "decisions is not"),
    ("satisfiable-string", lambda r: r.update(satisfiable="false"), "satisfiable is not a bool"),
    ("y-nan", lambda r: r.update(y=float("nan")), "y is not a finite number"),
    ("width-float", lambda r: r.update(width=5.0), "width is not"),
    ("status-unknown", lambda r: r.update(status="MAYBE"), "status is not a known status"),
    ("verification-unknown", lambda r: r.update(verification_status="TRUST_ME"), "known verification status"),
    ("n-vars-string", lambda r: r.update(n_vars="30"), "n_vars is not an int"),
    ("schema-version", lambda r: r.update(record_schema_version=99), "record_schema_version"),
    ("max-seconds", lambda r: r.update(max_seconds=60), "max_seconds is not null"),
    ("alarm-not-string", lambda r: r.update(integrity_alarm=True), "integrity_alarm is not"),
    ("error-on-completed-record", lambda r: r.update(error={"kind": "x"}), "error is not null"),
    ("runner-version", lambda r: r.update(runner_version="9.9.9"), "runner_version 9.9.9 differs"),
    ("extra-key", lambda r: r.update(trusted=True), "unexpected keys"),
    ("missing-key", lambda r: r.pop("verification_status"), "missing keys"),
]


@pytest.mark.parametrize("label,mutate,match", TYPE_FORGERIES, ids=[c[0] for c in TYPE_FORGERIES])
def test_malformed_records_are_reported_not_crashed_on(training_base, label, mutate, match):
    records = _subset_records(training_base)
    mutate(_first_with(records, "SAT"))
    report = wx.integrity_report(records, subset_specs(), budget=wx.BUDGET_B)
    assert report["passed"] is False
    assert any(match in f for f in report["failures"]), report["failures"]


def test_non_object_record_is_reported(training_base):
    records = _subset_records(training_base)
    records[0] = ["not", "a", "record"]
    report = wx.integrity_report(records, subset_specs(), budget=wx.BUDGET_B)
    assert report["passed"] is False
    assert any("not a JSON object" in f for f in report["failures"])


# ---------------------------------------------------------------------------
# NOVA-R10-15 / Gate D2 / ACE-PLAN-05: the retained certificate files
# ---------------------------------------------------------------------------


def test_retained_certificates_are_read_hashed_associated_and_checked(case):
    report = case.audit_certificates()
    assert report["passed"] is True, report["failures"]
    assert report["checked"] == len(case.unsat_ids()) >= 2
    assert report["legacy_manifest_entries"] == 0
    for iid in case.unsat_ids():
        cnf, drat = case.cert_files(iid)
        entry = next(e for e in case.cert_manifest() if e["instance_id"] == iid)
        record = next(r for r in case.records() if r["instance_id"] == iid)
        assert entry["retained_files"]["cnf_sha256"] == sha256_file(cnf) == record["formula_sha256"]
        assert entry["retained_files"]["proof_sha256"] == sha256_file(drat)
        assert sha256_file(drat) == record["reference"]["certificate"]["proof_sha256"]


def _rehash_entry(case, iid, *, proof: bool = False, cnf: bool = False, record: bool = False) -> None:
    cnf_path, drat_path = case.cert_files(iid)
    entries = case.cert_manifest()
    entry = next(e for e in entries if e["instance_id"] == iid)
    if proof:
        new = sha256_file(drat_path)
        entry["retained_files"]["proof_sha256"] = new
        entry["certificate"]["proof_sha256"] = new
    if cnf:
        new = sha256_file(cnf_path)
        entry["retained_files"]["cnf_sha256"] = new
        entry["formula_sha256"] = new
    case.write_cert_manifest(entries)
    if record:
        records = case.records()
        rec = next(r for r in records if r["instance_id"] == iid)
        if proof:
            rec["reference"]["certificate"]["proof_sha256"] = sha256_file(drat_path)
        if cnf:
            rec["formula_sha256"] = sha256_file(cnf_path)
        case.write_records(records)


def test_d2_substituted_proof_bytes_rejected(case):
    u1, u2 = case.unsat_ids()[:2]
    shutil.copyfile(case.cert_files(u2)[1], case.cert_files(u1)[1])
    failures = case.audit_certificates()["failures"]
    assert any(f.startswith(u1) and "retained proof bytes differ" in f for f in failures), failures


def test_d2_substituted_proof_with_rehashed_manifest_rejected(case):
    u1, u2 = case.unsat_ids()[:2]
    shutil.copyfile(case.cert_files(u2)[1], case.cert_files(u1)[1])
    _rehash_entry(case, u1, proof=True)
    failures = case.audit_certificates()["failures"]
    assert any(f.startswith(u1) and "proof hash differs from the record" in f for f in failures), failures


def test_d2_fully_rehashed_non_refuting_proof_rejected_by_the_checker(case):
    # Manifest, record and file all agree on the substituted proof, and the
    # record still claims VALID: only checking the stored proof against the
    # stored CNF can catch this.
    u1 = case.unsat_ids()[0]
    drat = case.cert_files(u1)[1]
    lines = [line for line in drat.read_text(encoding="ascii").splitlines() if line.strip() != "0"]
    drat.write_text("".join(f"{line}\n" for line in lines), encoding="ascii")
    _rehash_entry(case, u1, proof=True, record=True)
    assert wx.integrity_report(case.records(), subset_specs(), budget=wx.BUDGET_B)["passed"] is True
    failures = case.audit_certificates()["failures"]
    assert any(f.startswith(u1) and "does not refute the retained CNF" in f for f in failures), failures


def test_d2_swapped_cnf_rejected(case):
    u1, u2 = case.unsat_ids()[:2]
    shutil.copyfile(case.cert_files(u2)[0], case.cert_files(u1)[0])
    failures = case.audit_certificates()["failures"]
    assert any(f.startswith(u1) and "retained CNF bytes differ" in f for f in failures), failures


def test_d2_swapped_cnf_with_rehashed_association_rejected(case):
    u1, u2 = case.unsat_ids()[:2]
    shutil.copyfile(case.cert_files(u2)[0], case.cert_files(u1)[0])
    _rehash_entry(case, u1, cnf=True, record=True)
    failures = case.audit_certificates()["failures"]
    assert any(f.startswith(u1) and "not this instance's formula" in f for f in failures), failures


def test_d2_non_canonical_cnf_rejected(case):
    u1 = case.unsat_ids()[0]
    cnf = case.cert_files(u1)[0]
    cnf.write_text("c retained by hand\n" + cnf.read_text(encoding="ascii"), encoding="ascii")
    _rehash_entry(case, u1, cnf=True, record=True)
    failures = case.audit_certificates()["failures"]
    assert any(f.startswith(u1) and "malformed" in f for f in failures), failures


def test_d2_missing_proof_file_rejected(case):
    u1 = case.unsat_ids()[0]
    case.cert_files(u1)[1].unlink()
    failures = case.audit_certificates()["failures"]
    assert any(f.startswith(u1) and "retained certificate file missing" in f for f in failures), failures


def test_d2_missing_certificates_directory_rejected(case):
    shutil.rmtree(case.cert_dir)
    failures = case.audit_certificates()["failures"]
    assert any("directory is missing" in f for f in failures), failures


def test_d2_missing_manifest_entry_rejected(case):
    u1 = case.unsat_ids()[0]
    case.write_cert_manifest([e for e in case.cert_manifest() if e["instance_id"] != u1])
    failures = case.audit_certificates()["failures"]
    assert any(f.startswith(u1) and "has no retained certificate" in f for f in failures), failures
    assert any("not referenced by the certificate manifest" in f for f in failures), failures


def test_d2_null_retained_files_for_a_proof_claim_rejected(case):
    u1 = case.unsat_ids()[0]
    entries = case.cert_manifest()
    next(e for e in entries if e["instance_id"] == u1)["retained_files"] = None
    case.write_cert_manifest(entries)
    failures = case.audit_certificates()["failures"]
    assert any(f.startswith(u1) and "has no retained certificate" in f for f in failures), failures


def test_d2_duplicate_manifest_entry_rejected(case):
    u1 = case.unsat_ids()[0]
    entries = case.cert_manifest()
    entries.append(copy.deepcopy(next(e for e in entries if e["instance_id"] == u1)))
    case.write_cert_manifest(entries)
    failures = case.audit_certificates()["failures"]
    assert any("duplicate certificate manifest entry" in f for f in failures), failures


def test_d2_manifest_naming_another_instances_files_rejected(case):
    u1, u2 = case.unsat_ids()[:2]
    entries = case.cert_manifest()
    by_id = {e["instance_id"]: e for e in entries}
    by_id[u1]["retained_files"] = copy.deepcopy(by_id[u2]["retained_files"])
    case.write_cert_manifest(entries)
    failures = case.audit_certificates()["failures"]
    assert any(f.startswith(u1) and "unexpected retained files" in f for f in failures), failures


def test_d2_unreferenced_extra_proof_rejected(case):
    s1 = case.sat_ids()[0]
    u1 = case.unsat_ids()[0]
    shutil.copyfile(case.cert_files(u1)[1], case.cert_files(s1)[1])
    failures = case.audit_certificates()["failures"]
    assert any(case.cert_files(s1)[1].name in f and "not referenced" in f for f in failures), failures


def test_d2_legacy_manifest_uses_the_record_hashes(case):
    entries = case.cert_manifest()
    for entry in entries:
        entry.pop("retained_files")
    case.write_cert_manifest(entries)
    report = case.audit_certificates()
    assert report["passed"] is True, report["failures"]
    assert report["legacy_manifest_entries"] == report["checked"] == len(case.unsat_ids())
    u1, u2 = case.unsat_ids()[:2]
    shutil.copyfile(case.cert_files(u2)[1], case.cert_files(u1)[1])
    failures = case.audit_certificates()["failures"]
    assert any(f.startswith(u1) and "retained proof bytes differ" in f for f in failures), failures


@pytest.mark.skipif(not os.environ.get("OM_DRAT_TRIM"), reason="set OM_DRAT_TRIM=/path/to/drat-trim")
def test_d2_retained_proofs_also_verified_by_drat_trim(case):
    report = case.audit_certificates(drat_trim=os.environ["OM_DRAT_TRIM"])
    assert report["passed"] is True, report["failures"]
    assert report["drat_trim_verified"] == report["checked"] == len(case.unsat_ids())


def test_confirmatory_audit_requires_the_retained_files_and_regeneration_cannot_replace_them(training_base):
    records = _subset_records(training_base)
    audit = wx.audit_records(records, population="confirmatory", splits=["train"])
    assert any("requires the retained certificates" in f for f in audit["failures"])
    audit = wx.audit_records(records, population="confirmatory", splits=["train"], recheck_certificates=True)
    assert any("requires the retained certificates" in f for f in audit["failures"])
    assert audit["rechecked_certificates"] == sum(r["status"] == "UNSAT" for r in records)


# ---------------------------------------------------------------------------
# Retired schema-1 manifests never authorise
# ---------------------------------------------------------------------------


def test_schema1_manifests_never_authorise(no_execution, monkeypatch, tmp_path):
    monkeypatch.setattr(wx, "run_specs", _forbidden)
    doc = wx.draft_freeze_manifest()
    doc.update(confirmatory_authorized=True, authorized_by="Lumi", status="FROZEN",
               authorized_at_utc="2026-11-25T00:00:00+00:00")
    path = tmp_path / "freeze.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(REFUSED, match="schema 1"):
        wx.check_confirmatory_authorization(path)
    for split in ("test", "train"):
        with pytest.raises(REFUSED, match="schema 1"):
            wx.run_split(population="confirmatory", split=split, out_dir=tmp_path / "out", freeze_path=path,
                         keep_certificates=True, dry_run=True)
    assert doc["superseded_by"].startswith("om_lab.freeze")
    assert not (tmp_path / "out").exists()


# ---------------------------------------------------------------------------
# The live git probe, on a real temporary repository
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false",
         *args],
        cwd=repo, check=True, capture_output=True, text=True,
    )
    return out.stdout.strip()


def _make_repo(root: Path, files: dict[str, str]) -> str:
    root.mkdir(parents=True)
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "initial")
    return _git(root, "rev-parse", "HEAD")


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_git_provenance_detects_dirty_untracked_and_changed_frozen_paths(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    c1 = _make_repo(repo, {"lab/om_lab/solvers.py": "x = 1\n", "docs/protocol.md": "p\n", "README.md": "r\n",
                           ".gitignore": "__pycache__/\n"})
    paths = ["lab/om_lab", "docs/protocol.md"]
    solvers = repo / "lab" / "om_lab" / "solvers.py"
    probe = freeze.git_provenance(paths=paths, commit=c1, root=repo)
    assert probe["available"] is True and probe["head"] == c1 and probe["tree_clean"] is True
    assert probe["commit_exists"] is True and probe["changed_since_commit"] == []
    (repo / "lab" / "om_lab" / "__pycache__").mkdir()
    (repo / "lab" / "om_lab" / "__pycache__" / "solvers.cpython-312.pyc").write_bytes(b"\0")
    assert freeze.git_provenance(paths=paths, root=repo)["tree_clean"] is True  # ignored files are not dirt
    solvers.write_text("x = 2\n", encoding="utf-8")
    probe = freeze.git_provenance(paths=paths, root=repo)
    assert probe["tree_clean"] is False and any("solvers.py" in line for line in probe["dirty"])
    _git(repo, "add", "lab/om_lab/solvers.py")  # staged but not committed is still dirty
    assert freeze.git_provenance(paths=paths, root=repo)["tree_clean"] is False
    _git(repo, "reset", "-q", "--hard")
    (repo / "lab" / "om_lab" / "scratch.py").write_text("", encoding="utf-8")
    assert freeze.git_provenance(paths=paths, root=repo)["tree_clean"] is False  # untracked under a frozen path
    (repo / "lab" / "om_lab" / "scratch.py").unlink()
    (repo / "README.md").write_text("changed\n", encoding="utf-8")
    assert freeze.git_provenance(paths=paths, root=repo)["tree_clean"] is True  # outside the frozen paths
    _git(repo, "checkout", "-q", "--", "README.md")
    solvers.write_text("x = 3\n", encoding="utf-8")
    _git(repo, "commit", "-q", "-am", "change a frozen file")
    c2 = _git(repo, "rev-parse", "HEAD")
    probe = freeze.git_provenance(paths=paths, commit=c1, root=repo)
    assert probe["tree_clean"] is True and probe["changed_since_commit"] == ["lab/om_lab/solvers.py"]
    (repo / "README.md").write_text("later\n", encoding="utf-8")
    _git(repo, "commit", "-q", "-am", "change outside the frozen paths")
    probe = freeze.git_provenance(paths=paths, commit=c2, root=repo)
    assert probe["head"] != c2 and probe["changed_since_commit"] == []
    assert freeze.git_provenance(paths=paths, commit="0" * 40, root=repo)["commit_exists"] is False
    plain = tmp_path / "not-a-repo"
    plain.mkdir()
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    assert freeze.git_provenance(paths=paths, root=plain)["available"] is False


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_attack_dirty_tree_end_to_end_with_real_git(tmp_path, monkeypatch, training_base):
    # Real git, real provenance (no FakeLive): a checkout whose frozen paths
    # are modified, or changed after the execution commit, cannot be authorised.
    repo_files = {rel: "frozen\n" for rel in (
        "lab/om_lab/__init__.py", "lab/pyproject.toml", "lab/requirements.txt", "lab/constraints-om-c001-r2.txt",
        freeze.PROTOCOL_DOC, *freeze.DEFAULT_AMENDMENT_DOCS,
    )}
    repo = tmp_path / "repo"
    commit = _make_repo(repo, repo_files)
    monkeypatch.setattr(freeze, "repo_root", lambda: repo)
    specs = subset_specs()
    monkeypatch.setattr(freeze, "expected_training_specs", lambda: list(specs))
    shutil.copytree(training_base[0] / "train", tmp_path / "train")
    train = tmp_path / "train"
    records = train / f"{STEM}_results.jsonl"
    built = freeze.build_stage_a(
        out_dir=tmp_path / "freeze", training_records_path=records, training_certificates_dir=train / "certificates",
        training_certificate_manifest_path=train / f"{STEM}_certificate_manifest.json",
        independent_reproduction_sha256=sha256_file(records), reproduced_by="reproducer",
        settings=freeze.make_settings(**SETTINGS),
    )
    assert json.loads(Path(built["stage_a_path"]).read_text(encoding="utf-8"))["code"]["commit"] == commit
    assert freeze.preflight(built["stage_a_path"])["passed"] is True
    stage_b = tmp_path / "freeze" / "freeze_stage_b.json"
    (repo / "lab" / "om_lab" / "__init__.py").write_text("edited after the freeze\n", encoding="utf-8")
    with pytest.raises(REFUSED, match="dirty now"):
        freeze.authorize(built["stage_a_path"], authorized_by="Lumi", test_split_unexposed=True, out_path=stage_b)
    assert not stage_b.exists()
    _git(repo, "commit", "-q", "-am", "commit the edit")
    with pytest.raises(REFUSED, match="changed since the execution commit"):
        freeze.authorize(built["stage_a_path"], authorized_by="Lumi", test_split_unexposed=True, out_path=stage_b)
    assert not stage_b.exists()


# ---------------------------------------------------------------------------
# The production entrypoint (CLI)
# ---------------------------------------------------------------------------


def test_cli_freeze_commands_and_refusals(case, no_execution, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(wx, "run_specs", _forbidden)
    out_dir = tmp_path / "cli"
    stage_a = out_dir / "freeze_stage_a.json"
    stage_b = out_dir / "freeze_stage_b.json"
    results = tmp_path / "results"
    assert wx.main([
        "stage-a", "--out-dir", str(out_dir), "--training-records", str(case.records_path),
        "--training-certificates-dir", str(case.cert_dir),
        "--training-certificate-manifest", str(case.cert_manifest_path),
        "--reproduction-sha256", sha256_file(case.records_path), "--reproduced-by", "Nova", "--workers", "2",
    ]) == 0
    assert wx.main(["preflight", "--stage-a", str(stage_a), "--out", str(out_dir / "preflight.json")]) == 0
    assert json.loads((out_dir / "preflight.json").read_text(encoding="utf-8"))["solver_launched"] is False
    assert wx.main(["authorize", "--stage-a", str(stage_a), "--authorized-by", "Lumi", "--out", str(stage_b)]) == 2
    assert not stage_b.exists()
    assert wx.main(["authorize", "--stage-a", str(stage_a), "--authorized-by", "Lumi",
                    "--confirm-test-split-unexposed", "--out", str(stage_b)]) == 0
    capsys.readouterr()
    common = ["--stage-a", str(stage_a), "--stage-b", str(stage_b), "--workers", "2", "--out-dir", str(results)]
    assert wx.main(["run", "--split", "test", "--dry-run", *common]) == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["n_instances"] == 840 and printed["solver_launched"] is False
    assert printed["authorization"]["authorized_by"] == "Lumi"
    assert wx.main(["run", "--split", "test", "--indices", "70", "--keep-certificates", *common]) == 2
    assert wx.main(["run", "--split", "test", "--watchdog-s", "1200", "--keep-certificates", *common]) == 2
    assert wx.main(["run", "--split", "test", "--max-attempts", "5", "--keep-certificates", *common]) == 2
    assert wx.main(["run", "--split", "test", "--keep-certificates", "--workers", "2",
                    "--out-dir", str(results)]) == 2
    assert wx.main(["run", "--split", "train", "--indices", "0", "--keep-certificates", "--workers", "0",
                    "--out-dir", str(results)]) == 2
    assert "REFUSED" in capsys.readouterr().err
    assert not results.exists()


def _module_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    lab_dir = Path(wx.__file__).resolve().parent.parent
    env = dict(os.environ, PYTHONPATH=str(lab_dir) + os.pathsep + os.environ.get("PYTHONPATH", ""))
    return subprocess.run([sys.executable, "-m", "om_lab.width_experiment", *args], cwd=cwd, env=env,
                          capture_output=True, text=True, timeout=300)


def test_module_entrypoint_reports_refusals_without_a_traceback(tmp_path):
    # ``python -m`` runs the module as __main__; refusals raised in
    # om_lab.freeze must still be reported as REFUSED (exit 2). Every
    # command here is refused before anything is scheduled.
    out = str(tmp_path / "out")
    refused = [
        ("run", "--split", "test", "--indices", "70", "--out-dir", out),
        ("run", "--split", "test", "--keep-certificates", "--out-dir", out),
        ("run", "--split", "test", "--keep-certificates", "--out-dir", out,
         "--stage-a", str(tmp_path / "missing_a.json"), "--stage-b", str(tmp_path / "missing_b.json")),
        ("stage-a", "--out-dir", str(tmp_path / "freeze"), "--training-records", str(tmp_path / "none.jsonl"),
         "--training-certificates-dir", str(tmp_path), "--training-certificate-manifest", str(tmp_path / "no.json"),
         "--reproduction-sha256", "0" * 64, "--reproduced-by", "nobody", "--workers", "2"),
        ("authorize", "--stage-a", str(tmp_path / "missing_a.json"), "--authorized-by", "Lumi",
         "--confirm-test-split-unexposed", "--out", str(tmp_path / "b.json")),
    ]
    for args in refused:
        proc = _module_cli(*args, cwd=tmp_path)
        assert proc.returncode == 2, (args, proc.stderr[-2000:])
        assert "REFUSED" in proc.stderr and "Traceback" not in proc.stderr, (args, proc.stderr[-2000:])
    assert not (tmp_path / "out").exists() and not (tmp_path / "b.json").exists()
    assert not (tmp_path / "freeze").exists()


def test_cli_combine_and_audit_report_partial_and_retained_state(training_base, tmp_path, capsys):
    _, run = training_base
    out = tmp_path / "results.jsonl"
    assert wx.main(["combine", "--out", str(out), "--allow-partial", run["results_path"]]) == 2
    assert "PARTIAL" in capsys.readouterr().err and not out.exists()
    partial = tmp_path / "results_PARTIAL.jsonl"
    assert wx.main(["combine", "--out", str(partial), "--allow-partial",
                    "--certificate-manifest", run["certificate_manifest_path"], run["results_path"]]) == 0
    assert "PARTIAL: 16 of 2800" in capsys.readouterr().out
    assert wx.main(["audit", str(partial), "--population", "confirmatory", "--splits", "train"]) == 1
    assert "requires the retained certificates" in capsys.readouterr().out
    assert wx.main(["audit", str(partial), "--population", "confirmatory", "--splits", "train",
                    "--certificates-dir", str(Path(run["results_path"]).parent / "certificates"),
                    "--certificate-manifest", str(tmp_path / "certificate_manifest.json")]) == 1
    printed = capsys.readouterr().out
    assert f"retained_certificates_checked={run['integrity']['status_counts']['UNSAT']}" in printed
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"a": 1}\nnot json\n', encoding="utf-8")
    assert wx.main(["audit", str(bad), "--population", "pilot"]) == 1
    assert "bad.jsonl:2" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# NOVA-R10-08: strict JSON lines
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,match",
    [('{"a": 1}\nnot json\n', ":2: malformed record"), ('{"a": 1}\n[1, 2]\n', ":2: a record must be a JSON object"),
     ('{"a": 1, "a": 2}\n', ":1: malformed record.*duplicate JSON key"), ('{"a": NaN}\n', ":1: malformed record")],
    ids=["not-json", "not-object", "duplicate-key", "nan"],
)
def test_read_jsonl_names_the_file_and_line(tmp_path, text, match):
    path = tmp_path / "records.jsonl"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match=match):
        wx.read_jsonl(path)
