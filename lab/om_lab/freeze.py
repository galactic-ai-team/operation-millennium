"""Two-stage freeze, non-executing preflight and authorised execution (OM-C001-R2).

Implements ACE-PLAN-01 / ADVERSARIAL_REVIEW_01 B4 (NOVA-R10-01), the exact
population requirement of ACE-PLAN-02 (NOVA-R10-02/03) and the Gate E
architecture in Ace's gate review of dev b6d2b27:

    Stage A  immutable freeze manifest: code commit and clean tree, source,
             function, checker and backend hashes, protocol and amendment
             document hashes, exact interpreter and complete dependency
             inventory, frozen execution settings, the exact population
             schedules, the canonical training-record hash (equal to an
             independent reproduction) and the fitted-model hash.
    preflight  validates Stage A and constructs the exact 840-instance test
             schedule. It never launches a solver and needs no authorisation
             (this breaks the circular dependency Ace pointed out).
    Stage B  Lumi's authorisation record: the SHA-256 of the Stage A bytes,
             status FROZEN, identity, UTC time, and confirmation that the
             test split is unexposed. It is a separate file, so the execution
             commit never contains a hash of a manifest that names it.
    execution  ``width_experiment.run_split`` for the confirmatory test split
             calls :func:`verify_for_execution`, which re-verifies Stage B and
             Stage A against the running code, environment and requested
             settings, and refuses on any mismatch.

This is a procedural guard for a cooperative project (ACE-PLAN-06). It does
not stop someone from calling the solver functions directly, and the public
seed scheme is reproducible rather than blinded.

[Claim Level: Empirical Observation] for every check result reported here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
from importlib import metadata
import inspect
import json
import math
import os
from pathlib import Path
import platform
import re
import subprocess
from typing import Callable, Sequence
import weakref

from om_lab import width_experiment as wx

FREEZE_SCHEMA_VERSION = 2
STAGE_A_KIND = "OM-C001-R2/freeze-stage-a"
STAGE_B_KIND = "OM-C001-R2/freeze-stage-b"
MODEL_KIND = "OM-C001-R2/fitted-model"

#: Approved protocol document (B4 "approved protocol document hash").
PROTOCOL_DOC = "docs/phase3/DISCOVERY_ROUND_01.md"
#: Amendment documents (B4 "this amendment document's hash"; ACE-PLAN-01..06).
DEFAULT_AMENDMENT_DOCS = (
    "docs/phase4/ADVERSARIAL_REVIEW_01.md",
    "docs/phase4/reviews/REVIEW_PR11_ACE.md",
)
#: Tracked paths that must be clean and unchanged between the execution
#: commit and the run (B4 "no source or protocol changes may occur").
FROZEN_REPO_PATHS = (
    "lab/om_lab",
    "lab/pyproject.toml",
    "lab/requirements.txt",
    "lab/constraints-om-c001-r2.txt",
)
#: Exact execution settings pinned by Stage A ("Exact execution settings").
SETTINGS_KEYS = (
    "workers", "watchdog_s", "max_attempts", "worker_start_timeout_s",
    "budget_b", "max_seconds", "certify", "keep_certificates",
)
STAGE_A_KEYS = frozenset({
    "kind", "experiment", "freeze_schema_version", "runner_version", "orchestration_version",
    "created_utc", "code", "source_sha256", "function_sha256", "documents", "environment",
    "checker", "seed_manifest_sha256", "protocol", "settings", "population", "training", "model",
})
STAGE_B_KEYS = frozenset({
    "kind", "experiment", "freeze_schema_version", "stage_a_sha256", "status",
    "confirmatory_authorized", "authorized_by", "authorized_at_utc", "test_split_unexposed",
})
TRAINING_KEYS = frozenset({
    "records_path", "records_sha256", "n_records", "certificate_manifest_path",
    "certificate_manifest_sha256", "certificates_dir", "independent_reproduction_sha256",
    "reproduced_by",
})
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
#: Clock skew tolerated when checking that an authorisation is not in the future.
_CLOCK_SKEW = timedelta(minutes=5)


def _refuse(problems: Sequence[str]) -> None:
    if problems:
        raise wx.ConfirmatoryRunNotAuthorized("; ".join(problems))


# ---------------------------------------------------------------------------
# Strict primitives
# ---------------------------------------------------------------------------


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(Path(path).read_bytes())


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and bool(_HEX64.match(value))


def _no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    out: dict = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key {key!r}")
        out[key] = value
    return out


def _reject_constant(name: str) -> object:
    raise ValueError(f"non-finite JSON number {name}")


def load_json_strict(path: str | os.PathLike) -> tuple[bytes, dict]:
    """Read a JSON object: no duplicate keys, no NaN/Infinity, UTF-8 only."""
    data = Path(path).read_bytes()
    doc = json.loads(
        data.decode("utf-8"), object_pairs_hook=_no_duplicate_keys, parse_constant=_reject_constant
    )
    if not isinstance(doc, dict):
        raise ValueError("top-level JSON value must be an object")
    return data, doc


def _utc_timestamp(value: object) -> datetime | None:
    """Parse an ISO-8601 timestamp with an explicit UTC offset, else None."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        return None
    return parsed


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _write_json(path: Path, doc: dict) -> bytes:
    data = (json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data


def _resolve(base: Path, rel: object) -> Path | None:
    if not isinstance(rel, str) or not rel:
        return None
    path = Path(rel)
    return path if path.is_absolute() else (base / path)


def _relative(path: Path, base: Path) -> str:
    return os.path.relpath(Path(path).resolve(), base.resolve())


# ---------------------------------------------------------------------------
# Provenance of the running code and environment
# ---------------------------------------------------------------------------


def repo_root() -> Path | None:
    """Root of the git checkout that contains this package, or None."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], cwd=wx.lab_package_dir(),
            capture_output=True, text=True, timeout=20, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return Path(out.stdout.strip()) if out.returncode == 0 and out.stdout.strip() else None


def _git(root: Path, *args: str) -> tuple[int, str]:
    try:
        out = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, f"{type(exc).__name__}: {exc}"
    return out.returncode, out.stdout.strip()


def frozen_repo_paths(amendment_docs: Sequence[str] = DEFAULT_AMENDMENT_DOCS) -> list[str]:
    return [*FROZEN_REPO_PATHS, PROTOCOL_DOC, *amendment_docs]


def git_provenance(*, paths: Sequence[str], commit: str | None = None, root: Path | None = None) -> dict:
    """Commit, clean-tree and unchanged-since-commit facts for ``paths``.

    ``tree_clean`` means no tracked modification and no untracked,
    non-ignored file under ``paths``. ``changed_since_commit`` lists the
    paths whose committed content differs between ``commit`` and HEAD.
    """
    root = root if root is not None else repo_root()
    if root is None:
        return {"available": False, "head": None, "tree_clean": None, "dirty": [],
                "commit_exists": None, "changed_since_commit": None}
    rc, head = _git(root, "rev-parse", "HEAD")
    if rc != 0 or not _HEX40.match(head):
        return {"available": False, "head": None, "tree_clean": None, "dirty": [],
                "commit_exists": None, "changed_since_commit": None}
    rc, status = _git(root, "status", "--porcelain", "--untracked-files=all", "--", *paths)
    dirty = [line for line in status.splitlines() if line.strip()] if rc == 0 else ["<git status failed>"]
    out = {"available": True, "head": head, "tree_clean": rc == 0 and not dirty, "dirty": dirty[:50],
           "commit_exists": None, "changed_since_commit": None}
    if commit is not None:
        rc, kind = _git(root, "cat-file", "-t", commit)
        out["commit_exists"] = rc == 0 and kind == "commit"
        if out["commit_exists"]:
            rc, changed = _git(root, "diff", "--name-only", commit, "HEAD", "--", *paths)
            out["changed_since_commit"] = changed.splitlines() if rc == 0 else None
    return out


def python_identity() -> dict:
    """Exact interpreter (version and implementation are gates; the rest is provenance)."""
    return {
        "implementation": platform.python_implementation(),
        "version": platform.python_version(),
        "compiler": platform.python_compiler(),
        "build": list(platform.python_build()),
    }


def dependency_inventory() -> dict[str, str]:
    """Every installed distribution, PEP 503-normalised name -> version."""
    found: dict[str, set[str]] = {}
    for dist in metadata.distributions():
        name = dist.metadata["Name"]
        if not name:
            continue
        found.setdefault(re.sub(r"[-_.]+", "-", name).lower(), set()).add(dist.version)
    return {name: "|".join(sorted(versions)) for name, versions in sorted(found.items())}


def platform_identity() -> dict:
    """OS and architecture are gates; release and the platform string are provenance only."""
    return {
        "system": platform.system(),
        "machine": platform.machine(),
        "release": platform.release(),
        "platform": platform.platform(),
    }


def reference_backend_identity() -> dict:
    """CaDiCaL backend provenance: python-sat version and the compiled files' hashes."""
    dist = metadata.distribution("python-sat")
    compiled = {}
    for item in dist.files or []:
        if str(item).endswith((".so", ".pyd", ".dylib")):
            compiled[str(item)] = _sha256_file(Path(dist.locate_file(item)))
    return {
        "backend": f"pysat:{wx.REFERENCE_BACKEND}",
        "python_sat_version": dist.version,
        "compiled_files_sha256": dict(sorted(compiled.items())),
    }


def checker_identity(drat_trim: str | os.PathLike | None = None) -> dict:
    """The proof checker's identity; an external DRAT-trim binary by path and hash."""
    return {
        "name": wx.CHECKER_NAME,
        "version": wx.CHECKER_VERSION,
        "source_sha256": wx.checker_source_sha256(),
        "drat_trim": None if drat_trim is None else {"path": str(drat_trim), "sha256": _sha256_file(Path(drat_trim))},
    }


def document_hashes(amendment_docs: Sequence[str] = DEFAULT_AMENDMENT_DOCS, root: Path | None = None) -> dict:
    root = root if root is not None else repo_root()

    def entry(rel: str) -> dict:
        path = None if root is None else root / rel
        digest = _sha256_file(path) if path is not None and path.is_file() else None
        return {"path": rel, "sha256": digest}

    return {"protocol": entry(PROTOCOL_DOC), "amendments": [entry(rel) for rel in amendment_docs]}


def current_provenance(
    *,
    commit: str | None = None,
    amendment_docs: Sequence[str] = DEFAULT_AMENDMENT_DOCS,
    drat_trim: str | os.PathLike | None = None,
) -> dict:
    """Live snapshot of everything Stage A pins, taken from the running process."""
    return {
        "git": git_provenance(paths=frozen_repo_paths(amendment_docs), commit=commit),
        "python": python_identity(),
        "packages": dependency_inventory(),
        "platform": platform_identity(),
        "reference_backend": reference_backend_identity(),
        "checker": checker_identity(drat_trim),
        "documents": document_hashes(amendment_docs),
        "source_sha256": wx.source_hashes(),
        "function_sha256": wx.function_hashes(),
        "seed_manifest_sha256": wx.seed_manifest_sha256(),
        "protocol": wx.protocol_constants(),
    }


# ---------------------------------------------------------------------------
# Exact population schedules (ACE-PLAN-02)
# ---------------------------------------------------------------------------


def expected_training_specs() -> list[wx.InstanceSpec]:
    """The 1960-instance confirmatory training population, canonical order."""
    return wx.build_specs("confirmatory", "train")


def expected_test_specs() -> list[wx.InstanceSpec]:
    """The 840-instance confirmatory test population, canonical order."""
    return wx.build_specs("confirmatory", "test")


def schedule_rows(specs: Sequence[wx.InstanceSpec]) -> list[dict]:
    return [
        {"instance_id": s.instance_id, "n": s.n, "a_hundredths": s.a_hundredths, "m": s.m,
         "index": s.index, "seed_hex": f"{s.seed:032x}"}
        for s in specs
    ]


def schedule_sha256(specs: Sequence[wx.InstanceSpec]) -> str:
    return _sha256_bytes(wx.canonical_json(schedule_rows(specs)).encode("ascii"))


def population_summary(specs: Sequence[wx.InstanceSpec]) -> dict:
    cells = {(s.n, s.a_hundredths) for s in specs}
    per_cell = len(specs) // len(cells) if cells else 0
    return {"n_instances": len(specs), "n_cells": len(cells), "per_cell": per_cell,
            "schedule_sha256": schedule_sha256(specs)}


def validate_schedule(specs: Sequence[wx.InstanceSpec], split: str) -> list[str]:
    """Problems with a proposed confirmatory schedule for ``split`` (empty = exact).

    The schedule must equal the canonical population in canonical order: all
    28 cells, exactly 70 (train) or 30 (test) per cell, only this split's
    indices, no duplicates, no unexpected instances, and seeds and clause
    counts recomputed from the seed scheme.
    """
    problems: list[str] = []
    canonical = wx.build_specs("confirmatory", split)
    allowed = wx.split_indices(split)
    per_cell_expected = len(allowed)
    ids = [s.instance_id for s in specs]
    canonical_ids = [s.instance_id for s in canonical]
    if len(set(ids)) != len(ids):
        problems.append(f"{len(ids) - len(set(ids))} duplicate instance(s) in the schedule")
    missing = set(canonical_ids) - set(ids)
    unexpected = set(ids) - set(canonical_ids)
    if missing:
        problems.append(f"{len(missing)} canonical instance(s) missing from the schedule")
    if unexpected:
        problems.append(f"{len(unexpected)} unexpected instance(s) in the schedule")
    if ids != canonical_ids and not (missing or unexpected or len(set(ids)) != len(ids)):
        problems.append("schedule is not in canonical (n, A, index) order")
    cells: dict[tuple[int, int], int] = {}
    for spec in specs:
        cells[(spec.n, spec.a_hundredths)] = cells.get((spec.n, spec.a_hundredths), 0) + 1
        if spec.population != "confirmatory" or spec.split != split:
            problems.append(f"{spec.instance_id}: population/split is {spec.population}/{spec.split}")
        if spec.index not in allowed:
            problems.append(f"{spec.instance_id}: index {spec.index} is outside the {split} split")
        if spec.seed != wx.confirmatory_seed(spec.n, spec.a_hundredths, spec.index):
            problems.append(f"{spec.instance_id}: seed differs from the seed scheme")
        if spec.m != wx.clause_count(spec.n, spec.a_hundredths):
            problems.append(f"{spec.instance_id}: clause count differs from the protocol")
    expected_cells = {(n, a) for n in wx.N_VALUES for a in wx.A_VALUES}
    if set(cells) != expected_cells:
        problems.append(f"schedule covers {len(cells)} cells, expected the {len(expected_cells)} registered cells")
    bad_cells = sorted(c for c, k in cells.items() if k != per_cell_expected)
    if bad_cells:
        problems.append(f"{len(bad_cells)} cell(s) do not have exactly {per_cell_expected} instances")
    return problems


# ---------------------------------------------------------------------------
# Training artefacts and the frozen fitted model
# ---------------------------------------------------------------------------


def _jsonable(obj: object) -> object:
    """Fit dicts use (n, m) tuple keys; serialise them as 'n|m' strings."""
    if isinstance(obj, dict):
        out = {}
        for key, value in obj.items():
            skey = "|".join(str(k) for k in key) if isinstance(key, tuple) else str(key)
            out[skey] = _jsonable(value)
        return dict(sorted(out.items()))
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, float) and not math.isfinite(obj):
        raise ValueError("fitted model contains a non-finite number")
    return obj


def fitted_model_document(train_records: Sequence[dict]) -> dict:
    """The frozen fitted models (M0/M1, M2/M3) from training records only.

    Uses the analysis's own row conversion and fit functions, so the frozen
    coefficients are exactly what ``analyze_width`` computes from these
    records. Deterministic: pure-Python arithmetic over records in file order.
    """
    from om_lab import analyze_width as aw

    rows = aw.records_to_rows(list(train_records))
    if any(row["split"] != "train" for row in rows) or len(rows) != len(train_records):
        raise ValueError("the fitted model is built from complete training records only")
    fit_functions: dict[str, Callable] = {
        "analyze_width.records_to_rows": aw.records_to_rows,
        "analyze_width.fit_m0_m1": aw.fit_m0_m1,
        "analyze_width.fit_degree_adjusted": aw.fit_degree_adjusted,
    }
    return {
        "kind": MODEL_KIND,
        "experiment": wx.EXPERIMENT,
        "n_train": len(rows),
        "m0_m1": _jsonable(aw.fit_m0_m1(rows)),
        "degree_adjusted": _jsonable(aw.fit_degree_adjusted(rows)),
        "fit_source_sha256": {
            name: _sha256_bytes(inspect.getsource(fn).encode("utf-8")) for name, fn in fit_functions.items()
        },
    }


def model_bytes(model: dict) -> bytes:
    return (wx.canonical_json(model) + "\n").encode("ascii")


def verify_training_artifacts(
    *,
    records_path: str | os.PathLike,
    certificates_dir: str | os.PathLike,
    certificate_manifest_path: str | os.PathLike,
    expected_specs: Sequence[wx.InstanceSpec] | None = None,
    drat_trim: str | os.PathLike | None = None,
) -> dict:
    """Deep check of the locked training records before they are frozen.

    The records must be exactly the canonical training population in
    canonical order, pass the evidence-checking integrity report with the
    verification gate ready, and every proof-checked UNSAT claim must be
    backed by a retained certificate that checks against its retained CNF.
    Returns the record hash and the fitted model computed from the records.
    """
    expected = list(expected_training_specs() if expected_specs is None else expected_specs)
    problems: list[str] = []
    records_path = Path(records_path)
    try:
        data = records_path.read_bytes()
        records = wx.read_jsonl(records_path)
    except (OSError, ValueError) as exc:
        return {"passed": False, "problems": [f"cannot read training records: {exc}"]}
    if [r.get("instance_id") for r in records] != [s.instance_id for s in expected]:
        problems.append(
            f"training records are not exactly the {len(expected)}-instance training population in canonical order"
        )
    if any(r.get("population") != "confirmatory" or r.get("split") != "train" for r in records):
        problems.append("training records must all be confirmatory/train")
    integrity = wx.integrity_report(records, expected, budget=wx.BUDGET_B, full_population=expected)
    if not integrity["passed"]:
        problems.extend(f"training integrity: {f}" for f in integrity["failures"][:20])
    if not integrity["verification_gate_ready"]:
        problems.append("training verification gate is not ready (uncertified UNSAT, INVALID or ERROR records)")
    if integrity["complete"] is not True:
        problems.append("training records are not the complete training population")
    try:
        _, cert_manifest = wx.load_certificate_manifest(certificate_manifest_path)
    except (OSError, ValueError) as exc:
        problems.append(f"cannot read the training certificate manifest: {exc}")
        cert_manifest = None
    cert_audit = None
    if cert_manifest is not None:
        cert_audit = wx.audit_retained_certificates(
            records, specs=expected, certificates_dir=certificates_dir,
            certificate_manifest=cert_manifest, drat_trim=drat_trim,
        )
        if not cert_audit["passed"]:
            problems.extend(f"training certificates: {f}" for f in cert_audit["failures"][:20])
    model = None
    if not problems:
        try:
            model = fitted_model_document(records)
        except (ValueError, KeyError, TypeError) as exc:
            problems.append(f"cannot fit the frozen models: {exc}")
    return {
        "passed": not problems,
        "problems": problems,
        "records_sha256": _sha256_bytes(data),
        "n_records": len(records),
        "certificate_manifest_sha256": _sha256_file(Path(certificate_manifest_path))
        if Path(certificate_manifest_path).is_file() else None,
        "certificates_checked": None if cert_audit is None else cert_audit["checked"],
        "model": model,
        "model_sha256": None if model is None else _sha256_bytes(model_bytes(model)),
    }


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


def make_settings(*, workers: int, watchdog_s: float, max_attempts: int) -> dict:
    """The execution settings in canonical form (the frozen values plus Lumi's choices)."""
    return {
        "workers": workers,
        "watchdog_s": float(watchdog_s) if _is_int(watchdog_s) else watchdog_s,
        "max_attempts": max_attempts,
        "worker_start_timeout_s": float(wx.WORKER_START_TIMEOUT_S),
        "budget_b": wx.BUDGET_B,
        "max_seconds": None,
        "certify": True,
        "keep_certificates": True,
    }


def validate_settings(settings: object) -> list[str]:
    if not isinstance(settings, dict):
        return ["settings must be an object"]
    problems: list[str] = []
    if set(settings) != set(SETTINGS_KEYS):
        problems.append(f"settings keys must be exactly {sorted(SETTINGS_KEYS)}")
        return problems
    if not _is_int(settings["workers"]) or settings["workers"] < 1:
        problems.append("settings.workers must be an int >= 1 (the watchdog needs worker processes)")
    if not isinstance(settings["watchdog_s"], float) or not math.isfinite(settings["watchdog_s"]) \
            or settings["watchdog_s"] <= 0:
        problems.append("settings.watchdog_s must be a positive finite float")
    if not _is_int(settings["max_attempts"]) or settings["max_attempts"] < 1:
        problems.append("settings.max_attempts must be an int >= 1")
    if settings["worker_start_timeout_s"] != float(wx.WORKER_START_TIMEOUT_S) \
            or not isinstance(settings["worker_start_timeout_s"], float):
        problems.append("settings.worker_start_timeout_s differs from the runner")
    if not _is_int(settings["budget_b"]) or settings["budget_b"] != wx.BUDGET_B:
        problems.append(f"settings.budget_b must be {wx.BUDGET_B}")
    if settings["max_seconds"] is not None:
        problems.append("settings.max_seconds must be null")
    if settings["certify"] is not True or settings["keep_certificates"] is not True:
        problems.append("settings.certify and settings.keep_certificates must be true")
    return problems


# ---------------------------------------------------------------------------
# Stage A
# ---------------------------------------------------------------------------


def build_stage_a(
    *,
    out_dir: str | os.PathLike,
    training_records_path: str | os.PathLike,
    training_certificates_dir: str | os.PathLike,
    training_certificate_manifest_path: str | os.PathLike,
    independent_reproduction_sha256: str,
    reproduced_by: str,
    settings: dict,
    amendment_docs: Sequence[str] = DEFAULT_AMENDMENT_DOCS,
    drat_trim: str | os.PathLike | None = None,
    provenance: dict | None = None,
) -> dict:
    """Write ``freeze_stage_a.json`` and ``fitted_model.json`` into ``out_dir``.

    Refuses (raises ``ConfirmatoryRunNotAuthorized``) unless the checkout is
    clean, the settings are valid, the training artefacts pass the deep check
    and the independent reproduction hash equals the training-record hash.
    ``provenance`` is for tests; the production commands always take a live
    snapshot.
    """
    out = Path(out_dir)
    prov = provenance if provenance is not None else current_provenance(
        amendment_docs=amendment_docs, drat_trim=drat_trim
    )
    problems: list[str] = []
    git = prov["git"]
    if not git.get("available") or not git.get("head"):
        problems.append("git provenance is unavailable; a freeze needs the exact execution commit")
    elif git.get("tree_clean") is not True:
        problems.append(f"the frozen paths are not clean: {git.get('dirty')}")
    if any(entry["sha256"] is None for entry in [prov["documents"]["protocol"], *prov["documents"]["amendments"]]):
        problems.append("a protocol or amendment document is missing")
    problems.extend(validate_settings(settings))
    if not isinstance(reproduced_by, str) or not reproduced_by.strip():
        problems.append("reproduced_by must name who independently reproduced the training records")
    training = verify_training_artifacts(
        records_path=training_records_path, certificates_dir=training_certificates_dir,
        certificate_manifest_path=training_certificate_manifest_path, drat_trim=drat_trim,
    )
    problems.extend(training["problems"])
    if training.get("records_sha256") and independent_reproduction_sha256 != training["records_sha256"]:
        problems.append("the independent reproduction hash differs from the training-record hash")
    _refuse(problems)

    model_path = out / "fitted_model.json"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_bytes(model_bytes(training["model"]))
    stage_a = {
        "kind": STAGE_A_KIND,
        "experiment": wx.EXPERIMENT,
        "freeze_schema_version": FREEZE_SCHEMA_VERSION,
        "runner_version": wx.RUNNER_VERSION,
        "orchestration_version": wx.ORCHESTRATION_VERSION,
        "created_utc": utc_now(),
        "code": {"commit": git["head"], "frozen_paths": frozen_repo_paths(amendment_docs), "tree_clean": True},
        "source_sha256": prov["source_sha256"],
        "function_sha256": prov["function_sha256"],
        "documents": prov["documents"],
        "environment": {
            "python": prov["python"],
            "packages": prov["packages"],
            "platform": prov["platform"],
            "reference_backend": prov["reference_backend"],
        },
        "checker": prov["checker"],
        "seed_manifest_sha256": prov["seed_manifest_sha256"],
        "protocol": prov["protocol"],
        "settings": settings,
        "population": {
            "train": population_summary(expected_training_specs()),
            "test": population_summary(expected_test_specs()),
        },
        "training": {
            "records_path": _relative(Path(training_records_path), out),
            "records_sha256": training["records_sha256"],
            "n_records": training["n_records"],
            "certificate_manifest_path": _relative(Path(training_certificate_manifest_path), out),
            "certificate_manifest_sha256": training["certificate_manifest_sha256"],
            "certificates_dir": _relative(Path(training_certificates_dir), out),
            "independent_reproduction_sha256": independent_reproduction_sha256,
            "reproduced_by": reproduced_by.strip(),
        },
        "model": {"path": "fitted_model.json", "sha256": _sha256_file(model_path)},
    }
    stage_a_path = out / "freeze_stage_a.json"
    data = _write_json(stage_a_path, stage_a)
    return {"stage_a_path": str(stage_a_path), "stage_a_sha256": _sha256_bytes(data), "model_path": str(model_path)}


def verify_stage_a(
    stage_a_path: str | os.PathLike,
    *,
    provenance: dict | None = None,
    deep_training: bool = True,
) -> dict:
    """Check a Stage A manifest against the running code, environment and artefacts."""
    path = Path(stage_a_path)
    try:
        data, doc = load_json_strict(path)
    except (OSError, ValueError) as exc:
        return {"passed": False, "problems": [f"cannot read Stage A {path}: {exc}"], "stage_a_sha256": None}
    sha = _sha256_bytes(data)
    problems: list[str] = []
    if set(doc) != STAGE_A_KEYS:
        missing = sorted(STAGE_A_KEYS - set(doc))
        extra = sorted(set(doc) - STAGE_A_KEYS)
        return {"passed": False, "stage_a_sha256": sha,
                "problems": [f"Stage A keys differ (missing {missing}, unexpected {extra})"]}
    if doc["kind"] != STAGE_A_KIND:
        problems.append("Stage A kind mismatch")
    if doc["experiment"] != wx.EXPERIMENT:
        problems.append("experiment mismatch")
    if doc["freeze_schema_version"] != FREEZE_SCHEMA_VERSION or not _is_int(doc["freeze_schema_version"]):
        problems.append("freeze_schema_version mismatch")
    if doc["runner_version"] != wx.RUNNER_VERSION:
        problems.append("runner_version differs from the running code")
    if doc["orchestration_version"] != wx.ORCHESTRATION_VERSION:
        problems.append("orchestration_version differs from the running code")
    if _utc_timestamp(doc["created_utc"]) is None:
        problems.append("created_utc is not an ISO-8601 UTC timestamp")

    documents = doc["documents"]
    amendments: list[str] = []
    if not isinstance(documents, dict) or set(documents) != {"protocol", "amendments"} \
            or not isinstance(documents.get("amendments"), list) or not documents["amendments"]:
        problems.append("documents must record the protocol and at least one amendment document")
    else:
        amendments = [a.get("path") for a in documents["amendments"] if isinstance(a, dict)]
        if any(not isinstance(p, str) for p in amendments):
            problems.append("amendment paths must be strings")
            amendments = []
        if "docs/phase4/ADVERSARIAL_REVIEW_01.md" not in amendments:
            problems.append("the B4 amendment document (ADVERSARIAL_REVIEW_01.md) is not recorded")

    code = doc["code"]
    commit = None
    if not isinstance(code, dict) or set(code) != {"commit", "frozen_paths", "tree_clean"}:
        problems.append("code must record exactly commit, frozen_paths and tree_clean")
    else:
        commit = code["commit"] if isinstance(code["commit"], str) and _HEX40.match(code["commit"]) else None
        if commit is None:
            problems.append("code.commit is not a 40-hex git commit")
        if code["tree_clean"] is not True:
            problems.append("Stage A was made from a dirty tree (code.tree_clean is not true)")
        if code["frozen_paths"] != frozen_repo_paths(amendments):
            problems.append("code.frozen_paths differs from the required frozen paths")

    checker = doc["checker"]
    drat_trim = None
    if isinstance(checker, dict) and isinstance(checker.get("drat_trim"), dict):
        drat_trim = checker["drat_trim"].get("path")
    if provenance is None:
        try:
            provenance = current_provenance(commit=commit, amendment_docs=amendments or DEFAULT_AMENDMENT_DOCS,
                                            drat_trim=drat_trim)
        except (OSError, metadata.PackageNotFoundError) as exc:
            problems.append(f"cannot capture the running environment: {exc}")
            return {"passed": False, "problems": problems, "stage_a_sha256": sha}
    prov = provenance

    git = prov["git"]
    if not git.get("available"):
        problems.append("git provenance is unavailable at verification")
    else:
        if git.get("tree_clean") is not True:
            problems.append(f"the frozen paths are dirty now: {git.get('dirty')}")
        if commit is not None and git.get("commit_exists") is not True:
            problems.append("the execution commit is not in this checkout")
        elif commit is not None and git.get("changed_since_commit") != []:
            problems.append(f"frozen paths changed since the execution commit: {git.get('changed_since_commit')}")

    for key in ("source_sha256", "function_sha256", "seed_manifest_sha256", "protocol", "checker"):
        if doc[key] != prov[key]:
            problems.append(f"{key} differs from the running code")
    if documents != prov["documents"]:
        problems.append("protocol or amendment document hashes differ")

    env = doc["environment"]
    if not isinstance(env, dict) or set(env) != {"python", "packages", "platform", "reference_backend"}:
        problems.append("environment must record python, packages, platform and reference_backend")
    else:
        py = env["python"] if isinstance(env["python"], dict) else {}
        if set(py) != {"implementation", "version", "compiler", "build"}:
            problems.append("environment.python keys differ")
        if py.get("implementation") != prov["python"]["implementation"]:
            problems.append("Python implementation differs from the frozen environment")
        if py.get("version") != prov["python"]["version"]:
            problems.append("exact Python version differs from the frozen environment")
        if env["packages"] != prov["packages"]:
            frozen_pk = env["packages"] if isinstance(env["packages"], dict) else {}
            changed = sorted(set(frozen_pk.items()) ^ set(prov["packages"].items()))
            problems.append(f"installed dependencies differ from the frozen inventory: {changed[:6]}")
        plat = env["platform"] if isinstance(env["platform"], dict) else {}
        if set(plat) != {"system", "machine", "release", "platform"}:
            problems.append("environment.platform keys differ")
        if plat.get("system") != prov["platform"]["system"] or plat.get("machine") != prov["platform"]["machine"]:
            problems.append("operating system or architecture differs from the frozen environment")
        if env["reference_backend"] != prov["reference_backend"]:
            problems.append("reference solver backend provenance differs")

    problems.extend(validate_settings(doc["settings"]))
    expected_population = {"train": population_summary(expected_training_specs()),
                           "test": population_summary(expected_test_specs())}
    if doc["population"] != expected_population:
        problems.append("population schedules differ from the canonical train/test populations")

    base = path.parent
    training = doc["training"]
    model = doc["model"]
    if not isinstance(training, dict) or set(training) != TRAINING_KEYS:
        problems.append(f"training must record exactly {sorted(TRAINING_KEYS)}")
        training = None
    if not isinstance(model, dict) or set(model) != {"path", "sha256"}:
        problems.append("model must record exactly path and sha256")
        model = None
    records_path = cert_manifest_path = cert_dir = model_path = None
    if training is not None:
        records_path = _resolve(base, training["records_path"])
        cert_manifest_path = _resolve(base, training["certificate_manifest_path"])
        cert_dir = _resolve(base, training["certificates_dir"])
        for name in ("records_sha256", "certificate_manifest_sha256", "independent_reproduction_sha256"):
            if not _is_sha256(training[name]):
                problems.append(f"training.{name} is not a SHA-256")
        if training["independent_reproduction_sha256"] != training["records_sha256"]:
            problems.append("training records were not independently reproduced (hash differs)")
        if not isinstance(training["reproduced_by"], str) or not training["reproduced_by"].strip():
            problems.append("training.reproduced_by is not set")
        if training["n_records"] != expected_population["train"]["n_instances"] or not _is_int(training["n_records"]):
            problems.append("training.n_records differs from the training population")
        if records_path is None or not records_path.is_file():
            problems.append("training records file is missing")
        elif _sha256_file(records_path) != training["records_sha256"]:
            problems.append("training records file hash differs from Stage A")
        if cert_manifest_path is None or not cert_manifest_path.is_file():
            problems.append("training certificate manifest is missing")
        elif _sha256_file(cert_manifest_path) != training["certificate_manifest_sha256"]:
            problems.append("training certificate manifest hash differs from Stage A")
        if cert_dir is None or not cert_dir.is_dir():
            problems.append("training certificates directory is missing")
    if model is not None:
        model_path = _resolve(base, model["path"])
        if model_path is None or not model_path.is_file():
            problems.append("fitted model file is missing")
        elif _sha256_file(model_path) != model["sha256"]:
            problems.append("fitted model file hash differs from Stage A (a frozen coefficient was changed)")

    deep = None
    if deep_training and not problems:
        deep = verify_training_artifacts(
            records_path=records_path, certificates_dir=cert_dir,
            certificate_manifest_path=cert_manifest_path, drat_trim=drat_trim,
        )
        problems.extend(deep["problems"])
        if deep["passed"]:
            if model_path.read_bytes() != model_bytes(deep["model"]):
                problems.append("fitted model differs from the model recomputed from the training records")
            if deep["records_sha256"] != training["records_sha256"]:
                problems.append("training records changed during verification")
    return {"passed": not problems, "problems": problems, "stage_a_sha256": sha,
            "deep_training_checked": deep is not None and deep["passed"], "stage_a": doc,
            "head_commit": git.get("head")}


# ---------------------------------------------------------------------------
# Non-executing preflight (Ace, gate review section 3)
# ---------------------------------------------------------------------------


def preflight(
    stage_a_path: str | os.PathLike,
    *,
    provenance: dict | None = None,
    deep_training: bool = True,
    out_path: str | os.PathLike | None = None,
) -> dict:
    """Validate Stage A and construct the exact test schedule. Runs no solver.

    Needs no Stage B: this is the check Lumi runs before deciding to
    authorise. The report carries the Stage A hash that Stage B must name.
    """
    report = verify_stage_a(stage_a_path, provenance=provenance, deep_training=deep_training)
    problems = list(report["problems"])
    test_specs = wx.build_specs("confirmatory", "test")
    problems.extend(f"test schedule: {p}" for p in validate_schedule(test_specs, "test"))
    train_specs = wx.build_specs("confirmatory", "train")
    problems.extend(f"training schedule: {p}" for p in validate_schedule(train_specs, "train"))
    stage_a = report.get("stage_a") or {}
    frozen_test = (stage_a.get("population") or {}).get("test") if isinstance(stage_a.get("population"), dict) else None
    if frozen_test != population_summary(test_specs):
        problems.append("Stage A's test schedule hash differs from the constructed schedule")
    result = {
        "kind": "OM-C001-R2/preflight",
        "claim_level": "Empirical Observation",
        "passed": not problems,
        "problems": problems,
        "stage_a_path": str(stage_a_path),
        "stage_a_sha256": report["stage_a_sha256"],
        "deep_training_checked": report.get("deep_training_checked", False),
        "solver_launched": False,
        "authorization_required": False,
        "test_schedule": {
            **population_summary(test_specs),
            "first": test_specs[0].instance_id,
            "last": test_specs[-1].instance_id,
            "indices": [wx.TEST_INDEX_MIN, wx.INDICES_PER_CELL - 1],
        },
        "training_schedule": population_summary(train_specs),
        "checked_utc": utc_now(),
    }
    if out_path is not None:
        _write_json(Path(out_path), result)
    return result


# ---------------------------------------------------------------------------
# Stage B and authorised execution
# ---------------------------------------------------------------------------


def verify_stage_b(stage_b: dict, *, stage_a_sha256: str, stage_a_created_utc: object = None,
                   now: datetime | None = None) -> list[str]:
    problems: list[str] = []
    if set(stage_b) != STAGE_B_KEYS:
        return [f"Stage B keys differ (missing {sorted(STAGE_B_KEYS - set(stage_b))}, "
                f"unexpected {sorted(set(stage_b) - STAGE_B_KEYS)})"]
    if stage_b["kind"] != STAGE_B_KIND:
        problems.append("Stage B kind mismatch")
    if stage_b["experiment"] != wx.EXPERIMENT:
        problems.append("Stage B experiment mismatch")
    if stage_b["freeze_schema_version"] != FREEZE_SCHEMA_VERSION or not _is_int(stage_b["freeze_schema_version"]):
        problems.append("Stage B freeze_schema_version mismatch")
    if stage_b["stage_a_sha256"] != stage_a_sha256:
        problems.append("Stage B authorises a different Stage A (stage_a_sha256 mismatch)")
    if stage_b["status"] != "FROZEN":
        problems.append("Stage B status is not FROZEN")
    if stage_b["confirmatory_authorized"] is not True:
        problems.append("confirmatory_authorized is not true")
    if not isinstance(stage_b["authorized_by"], str) or not stage_b["authorized_by"].strip():
        problems.append("authorized_by is not set")
    when = _utc_timestamp(stage_b["authorized_at_utc"])
    if when is None:
        problems.append("authorized_at_utc is not an ISO-8601 UTC timestamp")
    else:
        now = now or datetime.now(timezone.utc)
        if when > now + _CLOCK_SKEW:
            problems.append("authorized_at_utc is in the future")
        created = _utc_timestamp(stage_a_created_utc)
        if created is not None and when < created:
            problems.append("authorized_at_utc precedes the Stage A it authorises")
    if stage_b["test_split_unexposed"] is not True:
        problems.append("test_split_unexposed is not true")
    return problems


def authorize(
    stage_a_path: str | os.PathLike,
    *,
    authorized_by: str,
    test_split_unexposed: bool,
    out_path: str | os.PathLike,
    provenance: dict | None = None,
    deep_training: bool = True,
) -> dict:
    """Lumi's Stage B: written only after a passing preflight of this exact Stage A."""
    problems: list[str] = []
    if test_split_unexposed is not True:
        problems.append("authorisation requires confirming that the test split is unexposed")
    if not isinstance(authorized_by, str) or not authorized_by.strip():
        problems.append("authorized_by must name the coordinator")
    report = preflight(stage_a_path, provenance=provenance, deep_training=deep_training)
    problems.extend(f"preflight: {p}" for p in report["problems"])
    _refuse(problems)
    stage_b = {
        "kind": STAGE_B_KIND,
        "experiment": wx.EXPERIMENT,
        "freeze_schema_version": FREEZE_SCHEMA_VERSION,
        "stage_a_sha256": report["stage_a_sha256"],
        "status": "FROZEN",
        "confirmatory_authorized": True,
        "authorized_by": authorized_by.strip(),
        "authorized_at_utc": utc_now(),
        "test_split_unexposed": True,
    }
    data = _write_json(Path(out_path), stage_b)
    return {"stage_b_path": str(out_path), "stage_b_sha256": _sha256_bytes(data),
            "stage_a_sha256": report["stage_a_sha256"]}


#: Authorisations issued by :func:`verify_for_execution` in this process.
_ISSUED: "weakref.WeakSet[AuthorizedFreeze]" = weakref.WeakSet()


@dataclass(frozen=True, eq=False)
class AuthorizedFreeze:
    """Proof, inside one process, that :func:`verify_for_execution` passed.

    Only instances issued by :func:`verify_for_execution` are accepted by the
    runner (:func:`is_issued`): one constructed by hand, or copied with
    ``dataclasses.replace`` to change a field, is refused. The frozen
    settings are stored as immutable items. This is a procedural guard
    against accidental misuse inside a cooperative project (ACE-PLAN-06),
    not a defence against deliberate tampering with the interpreter.
    """

    stage_a_path: str
    stage_a_sha256: str
    stage_b_path: str
    stage_b_sha256: str
    authorized_by: str
    authorized_at_utc: str
    execution_commit: str
    head_commit: str
    verified_at_utc: str
    test_schedule_sha256: str
    settings_items: tuple = ()

    @property
    def settings(self) -> dict:
        return dict(self.settings_items)

    def require_settings(self, **actual: object) -> None:
        """Refuse unless the run's settings equal the frozen settings exactly (value and type)."""
        frozen = self.settings
        mismatched = sorted(
            key for key, value in actual.items()
            if key not in frozen or frozen[key] != value or type(frozen[key]) is not type(value)
        )
        if set(frozen) != set(actual):
            mismatched.append("<the set of settings>")
        _refuse([f"execution setting {key} differs from the frozen value" for key in mismatched])

    def summary(self) -> dict:
        return {
            "stage_a_path": self.stage_a_path, "stage_a_sha256": self.stage_a_sha256,
            "stage_b_path": self.stage_b_path, "stage_b_sha256": self.stage_b_sha256,
            "authorized_by": self.authorized_by, "authorized_at_utc": self.authorized_at_utc,
            "execution_commit": self.execution_commit, "head_commit_at_verification": self.head_commit,
            "verified_at_utc": self.verified_at_utc, "test_schedule_sha256": self.test_schedule_sha256,
            "settings": self.settings,
        }


def is_issued(authorization: object) -> bool:
    """True only for an :class:`AuthorizedFreeze` issued by :func:`verify_for_execution` here."""
    return isinstance(authorization, AuthorizedFreeze) and authorization in _ISSUED


def verify_for_execution(
    stage_a_path: str | os.PathLike | None,
    stage_b_path: str | os.PathLike | None,
    *,
    requested_settings: dict,
    provenance: dict | None = None,
    deep_training: bool = True,
) -> AuthorizedFreeze:
    """Verify Stage B and Stage A for the confirmatory test split, or raise.

    Refuses on a missing record, any Stage B defect, any Stage A mismatch
    against the running code, environment, checkout or artefacts, and any
    difference between the requested and the frozen execution settings.
    """
    if stage_a_path is None or stage_b_path is None:
        _refuse(["the confirmatory test split requires --stage-a and --stage-b (authorised freeze)"])
    try:
        stage_a_bytes = Path(stage_a_path).read_bytes()
        stage_b_bytes, stage_b = load_json_strict(stage_b_path)
    except (OSError, ValueError) as exc:
        _refuse([f"cannot read the freeze records: {exc}"])
    stage_a_sha = _sha256_bytes(stage_a_bytes)
    try:
        created = json.loads(stage_a_bytes.decode("utf-8")).get("created_utc")
    except (ValueError, AttributeError):
        created = None
    problems = verify_stage_b(stage_b, stage_a_sha256=stage_a_sha, stage_a_created_utc=created)
    report = verify_stage_a(stage_a_path, provenance=provenance, deep_training=deep_training)
    if report["stage_a_sha256"] != stage_a_sha:
        problems.append("Stage A changed while it was being verified")
    # The authorisation (and the run manifest the analysis handoff binds to)
    # names the Stage B bytes verified above, so they must still be on disk.
    try:
        stage_b_unchanged = Path(stage_b_path).read_bytes() == stage_b_bytes
    except OSError:
        stage_b_unchanged = False
    if not stage_b_unchanged:
        problems.append("Stage B changed while it was being verified")
    problems.extend(report["problems"])
    requested = dict(requested_settings)
    if _is_int(requested.get("watchdog_s")):
        requested["watchdog_s"] = float(requested["watchdog_s"])
    problems.extend(validate_settings(requested))
    stage_a = report.get("stage_a") or {}
    if requested != stage_a.get("settings"):
        diff = sorted(k for k in SETTINGS_KEYS if requested.get(k) != (stage_a.get("settings") or {}).get(k))
        problems.append(f"requested execution settings differ from the frozen settings: {diff}")
    _refuse(problems)
    head = report.get("head_commit")
    authorization = AuthorizedFreeze(
        stage_a_path=str(stage_a_path), stage_a_sha256=stage_a_sha,
        stage_b_path=str(stage_b_path), stage_b_sha256=_sha256_bytes(stage_b_bytes),
        authorized_by=stage_b["authorized_by"], authorized_at_utc=stage_b["authorized_at_utc"],
        execution_commit=stage_a["code"]["commit"], head_commit=head or "",
        verified_at_utc=utc_now(), test_schedule_sha256=stage_a["population"]["test"]["schedule_sha256"],
        settings_items=tuple(sorted(stage_a["settings"].items())),
    )
    _ISSUED.add(authorization)
    return authorization


__all__ = [
    "AuthorizedFreeze", "DEFAULT_AMENDMENT_DOCS", "FREEZE_SCHEMA_VERSION", "FROZEN_REPO_PATHS",
    "PROTOCOL_DOC", "SETTINGS_KEYS", "STAGE_A_KEYS", "STAGE_B_KEYS", "authorize", "build_stage_a",
    "current_provenance", "dependency_inventory", "expected_test_specs", "expected_training_specs",
    "fitted_model_document", "git_provenance", "is_issued", "load_json_strict", "make_settings", "model_bytes",
    "population_summary", "preflight", "schedule_rows", "schedule_sha256", "validate_schedule",
    "validate_settings", "verify_for_execution", "verify_stage_a", "verify_stage_b",
    "verify_training_artifacts",
]
