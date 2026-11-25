"""Frozen OM-C001-R2 experiment runner.

Implements ``docs/phase3/DISCOVERY_ROUND_01.md`` Section 7.1 (Claude's
assignment) for the preregistered experiment in Section 3, under the
integrity gate of Section 4. Nova's frozen analysis
(:mod:`om_lab.analyze_width`) consumes the JSONL this runner writes.

[Claim Level: Empirical Observation] for every number this runner produces.
Nothing here is a statement about worst-case complexity, exact treewidth,
optimal algorithms or P vs NP.

What one run does, per instance
-------------------------------
1. Rebuilds the instance from the frozen seed scheme (Section 3.5):
   ``seed`` = first 16 bytes of SHA-256(UTF-8 ``"OM-C001-R2|n|A|i"``),
   ``m = (A*n + 50) // 100``, :func:`om_lab.generators.generate_random_3sat`
   with clause and literal order preserved. The seed scheme and constants
   are imported from :mod:`om_lab.analyze_width` (single source of truth).
2. Computes Nova's features from the original formula:
   ``primal_min_fill_width`` (plus an independent elimination-order replay),
   the reversed-ID width for relabelling sensitivity, and the
   co-occurrence mean degree.
3. Runs the primary solver exactly as preregistered (Section 3.6):
   :func:`om_lab.solvers.solve_dpll` with ``max_decisions=B=10000`` and
   ``max_seconds=None``. Its search code is unchanged from ed6d557.
4. Runs the proof-producing reference solver (CaDiCaL 1.9.5 via PySAT,
   ``cd195``) and checks its DRAT certificate with the independent checker
   :mod:`om_lab.proof_check`. A primary UNSAT claim is labelled
   ``UNSAT_PROOF_CHECKED`` only if that certificate is valid. The reference
   never changes the primary status: an UNKNOWN run stays UNKNOWN.
5. Emits exactly one deterministic primary record (no timestamps, no
   timings) plus a separate telemetry record (timings, attempts, pid).

Infrastructure protection
-------------------------
Instances run in long-lived worker processes. A per-instance wall-clock
watchdog (default 600 s) kills a stuck worker; a crash or exception is
also an infrastructure failure. Failures are rerun with the same instance
and the same budget (never a different seed), up to ``max_attempts``.
An instance that still fails gets one ``status="ERROR"`` record: missing
experimental data, never UNKNOWN and never UNSAT.

Confirmatory boundary
---------------------
The confirmatory test split (indices 70-99) runs only through the two-stage
freeze of :mod:`om_lab.freeze` (ACE-PLAN-01, B4): a Stage A manifest that
pins the code commit and clean tree, every source, function, checker,
backend and document hash, the exact interpreter and dependency inventory,
the execution settings, the population schedules, the training-record hash
and the fitted-model hash; a non-executing ``preflight``; and Lumi's Stage B
authorisation naming the Stage A hash. ``run_split`` re-verifies both
records, schedules exactly the 840-instance test population (ACE-PLAN-02)
and refuses any mismatch. This is a procedural guard against accidental
unblinding, not cryptographic blinding (ACE-PLAN-06).

Commands (run from ``lab/``)::

    python -m om_lab.width_experiment seeds --out results/om_c001_r2/seeds.json
    python -m om_lab.width_experiment validate-certifier --out results/om_c001_r2/certifier_validation.json
    python -m om_lab.width_experiment smoke --out-dir results/om_c001_r2/smoke
    python -m om_lab.width_experiment run --split train --out-dir results/om_c001_r2 --workers 4 --keep-certificates
    python -m om_lab.width_experiment stage-a --out-dir results/om_c001_r2/freeze --training-records results/om_c001_r2/confirmatory_train_results.jsonl --training-certificates-dir results/om_c001_r2/certificates --training-certificate-manifest results/om_c001_r2/confirmatory_train_certificate_manifest.json --reproduction-sha256 <independent reproduction hash> --reproduced-by <name> --workers 4
    python -m om_lab.width_experiment preflight --stage-a results/om_c001_r2/freeze/freeze_stage_a.json --out results/om_c001_r2/freeze/preflight.json
    # Lumi, after reviewing the preflight:
    python -m om_lab.width_experiment authorize --stage-a results/om_c001_r2/freeze/freeze_stage_a.json --authorized-by Lumi --confirm-test-split-unexposed --out results/om_c001_r2/freeze/freeze_stage_b.json
    python -m om_lab.width_experiment run --split test --stage-a results/om_c001_r2/freeze/freeze_stage_a.json --stage-b results/om_c001_r2/freeze/freeze_stage_b.json --out-dir results/om_c001_r2 --workers 4 --keep-certificates
    python -m om_lab.width_experiment combine --out results/om_c001_r2/results.jsonl --certificate-manifest results/om_c001_r2/confirmatory_train_certificate_manifest.json --certificate-manifest results/om_c001_r2/confirmatory_test_certificate_manifest.json results/om_c001_r2/confirmatory_train_results.jsonl results/om_c001_r2/confirmatory_test_results.jsonl
    python -m om_lab.width_experiment audit results/om_c001_r2/results.jsonl --population confirmatory --splits train test --certificates-dir results/om_c001_r2/certificates --certificate-manifest results/om_c001_r2/certificate_manifest.json
    python -m om_lab.analyze_width --records results/om_c001_r2/results.jsonl --population confirmatory --out-dir results/om_c001_r2/analysis
"""

from __future__ import annotations

import argparse
from collections import Counter, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import inspect
import json
import math
import multiprocessing as mp
from multiprocessing.connection import wait as mp_wait
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import time
import traceback
from typing import Callable, Iterable, Sequence

from om_lab.analyze_width import (
    A_VALUES,
    BOOTSTRAP_REPLICATES,
    BOOTSTRAP_SEED,
    BUDGET_B,
    CONFIRMATORY_SEED_PREFIX,
    EFFECT_THRESHOLD,
    N_VALUES,
    PILOT_SEED_PREFIX,
    TEST_INDEX_MIN,
    TRAIN_INDEX_MAX,
    capped_log_effort,
    check_seed_manifest,
    clause_count,
    confirmatory_seed,
    pilot_seed,
    seed_manifest,
)
from om_lab.certify import REFERENCE_BACKEND, label_unsat_claim, reference_certificate
from om_lab.features import extract_features_from_clauses
from om_lab.generators import generate_random_3sat
from om_lab.proof_check import (
    CHECKER_NAME,
    CHECKER_VERSION,
    check_drat,
    checker_source_sha256,
    dimacs_text,
    run_drat_trim,
)
from om_lab.solvers import (
    ALLOWED_VERIFICATION,
    Status,
    StopReason,
    Verification,
    check_sat_witness,
    solve_dpll,
    verify_cnf_assignment,
)
from om_lab.width_features import primal_min_fill_width, replay_elimination_order

EXPERIMENT = "OM-C001-R2"
#: Version of the per-instance record producer (``run_instance``). Unchanged
#: since PR #10, so primary record bytes, and therefore the training-file
#: hash an independent reproduction checks, are unchanged.
RUNNER_VERSION = "1.0.0"
#: Version of scheduling, verification and output handling (Phase 4 Gate B/D).
ORCHESTRATION_VERSION = "1.1.0"
RECORD_SCHEMA_VERSION = 1
FREEZE_SCHEMA_VERSION = 1
INDICES_PER_CELL = 100
POPULATIONS = ("confirmatory", "pilot")
SPLITS = ("train", "test")
#: Section 3.6: at most 28 million recorded branch attempts over the population.
MAX_TOTAL_BRANCH_ATTEMPTS = len(N_VALUES) * len(A_VALUES) * INDICES_PER_CELL * BUDGET_B
DEFAULT_WATCHDOG_S = 600.0
DEFAULT_MAX_ATTEMPTS = 3

#: Source files whose SHA-256 is pinned by the freeze manifest.
FROZEN_SOURCE_FILES = (
    "generators.py",
    "solvers.py",
    "proof_check.py",
    "certify.py",
    "features.py",
    "width_features.py",
    "analyze_width.py",
    "width_experiment.py",
    "freeze.py",
)

#: Required keys of every primary record (schema version 1).
RECORD_KEYS = frozenset(
    {
        "experiment", "record_schema_version", "runner_version", "population", "split",
        "instance_id", "problem", "n_vars", "n_clauses", "a_hundredths", "index", "seed",
        "seed_hex", "formula_sha256", "width", "width_replay", "width_ordering_sha256",
        "width_reversed", "degree_mean", "solver", "budget_b", "max_decisions", "max_seconds",
        "status", "stop_reason", "decisions", "propagations", "budget_exhausted", "satisfiable",
        "timed_out", "verified", "verification_status", "y", "model", "reference",
        "reference_agreement", "integrity_alarm", "error",
    }
)


class ConfirmatoryRunNotAuthorized(RuntimeError):
    """Raised when the confirmatory test split is requested without a valid freeze."""


# ---------------------------------------------------------------------------
# Hashing, environment and provenance
# ---------------------------------------------------------------------------


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def canonical_json(obj: object) -> str:
    """Deterministic JSON: sorted keys, compact separators, ASCII, no NaN."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def lab_package_dir() -> Path:
    return Path(__file__).resolve().parent


def source_hashes() -> dict[str, str]:
    """SHA-256 of every frozen source file."""
    base = lab_package_dir()
    return {name: _sha256_bytes((base / name).read_bytes()) for name in FROZEN_SOURCE_FILES}


def _frozen_functions() -> dict[str, Callable]:
    return {
        "generators.generate_random_3sat": generate_random_3sat,
        "solvers.solve_dpll": solve_dpll,
        "width_features.primal_min_fill_width": primal_min_fill_width,
        "proof_check.check_drat": check_drat,
        "analyze_width.capped_log_effort": capped_log_effort,
        "analyze_width.confirmatory_seed": confirmatory_seed,
    }


def function_hashes() -> dict[str, str]:
    """SHA-256 of the source text of each function the protocol depends on."""
    return {name: _sha256_text(inspect.getsource(fn)) for name, fn in _frozen_functions().items()}


def _package_version(dist: str) -> str | None:
    try:
        return metadata.version(dist)
    except metadata.PackageNotFoundError:
        return None


def environment_fingerprint() -> dict:
    return {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "packages": {
            dist: _package_version(dist)
            for dist in ("python-sat", "numpy", "matplotlib", "om-lab")
        },
    }


def git_state() -> dict:
    """Best-effort git provenance of the lab directory (never raises)."""
    def run(*args: str) -> str | None:
        try:
            out = subprocess.run(
                ["git", *args], cwd=lab_package_dir(), capture_output=True, text=True,
                timeout=10, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        return out.stdout.strip() if out.returncode == 0 else None

    status = run("status", "--porcelain", "--", ".")
    return {"commit": run("rev-parse", "HEAD"), "lab_dirty": None if status is None else bool(status)}


def protocol_constants() -> dict:
    return {
        "experiment": EXPERIMENT,
        "n_values": list(N_VALUES),
        "a_hundredths_values": list(A_VALUES),
        "clause_count": "m = (A*n + 50) // 100",
        "indices_per_cell": INDICES_PER_CELL,
        "train_indices": [0, TRAIN_INDEX_MAX],
        "test_indices": [TEST_INDEX_MIN, INDICES_PER_CELL - 1],
        "seed_scheme": (
            "seed = unsigned big-endian int of the first 16 bytes of "
            f"SHA-256(UTF-8 '{CONFIRMATORY_SEED_PREFIX}|n|A|i')"
        ),
        "primary_solver": "om_lab.solvers.solve_dpll",
        "budget_b": BUDGET_B,
        "max_decisions": BUDGET_B,
        "max_seconds": None,
        "max_total_branch_attempts": MAX_TOTAL_BRANCH_ATTEMPTS,
        "response": "Y = ln(1 + min(D, B))",
        "reference_backend": f"pysat:{REFERENCE_BACKEND}",
        "checker": {"name": CHECKER_NAME, "version": CHECKER_VERSION},
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "effect_threshold": EFFECT_THRESHOLD,
    }


# ---------------------------------------------------------------------------
# Population construction (Sections 3.4-3.5)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InstanceSpec:
    """One instance of the experiment population."""

    population: str
    split: str
    n: int
    a_hundredths: int
    m: int
    index: int
    seed: int

    @property
    def instance_id(self) -> str:
        prefix = CONFIRMATORY_SEED_PREFIX if self.population == "confirmatory" else PILOT_SEED_PREFIX
        return f"{prefix}|{self.n}|{self.a_hundredths}|{self.index}"


def split_indices(split: str) -> range:
    if split == "train":
        return range(0, TRAIN_INDEX_MAX + 1)
    if split == "test":
        return range(TEST_INDEX_MIN, INDICES_PER_CELL)
    raise ValueError(f"unknown split {split!r}")


def build_specs(
    population: str,
    split: str,
    *,
    n_values: Sequence[int] | None = None,
    a_values: Sequence[int] | None = None,
    indices: Iterable[int] | None = None,
) -> list[InstanceSpec]:
    """Instances of one split, ordered by (n, A, index).

    Indices 0-69 are training and 70-99 are confirmatory test for both
    populations. Confirmatory cells are frozen to Section 3.4; pilot cells
    use Nova's pilot seed prefix and can never collide with confirmatory
    seeds.
    """
    if population not in POPULATIONS:
        raise ValueError(f"unknown population {population!r}")
    allowed = split_indices(split)
    n_list = list(N_VALUES if n_values is None else n_values)
    a_list = list(A_VALUES if a_values is None else a_values)
    idx_list = list(allowed) if indices is None else sorted(set(int(i) for i in indices))
    for i in idx_list:
        if i not in allowed:
            raise ValueError(f"index {i} is not in the {split} split ({allowed.start}-{allowed.stop - 1})")
    if population == "confirmatory":
        if not set(n_list) <= set(N_VALUES) or not set(a_list) <= set(A_VALUES):
            raise ValueError("confirmatory cells are frozen to Section 3.4")
    for n in n_list:
        if n < 3:
            raise ValueError("random 3-SAT needs n >= 3")
    for a in a_list:
        if a <= 0:
            raise ValueError("A must be a positive number of hundredths")
    seed_fn = confirmatory_seed if population == "confirmatory" else pilot_seed
    return [
        InstanceSpec(population, split, n, a, clause_count(n, a), i, seed_fn(n, a, i))
        for n in n_list
        for a in a_list
        for i in idx_list
    ]


def seed_manifest_document() -> dict:
    """Full 2800-row confirmatory seed manifest with collision checks (no runs)."""
    rows = seed_manifest()
    for row in rows:
        row["instance_id"] = f"{CONFIRMATORY_SEED_PREFIX}|{row['n']}|{row['a_hundredths']}|{row['index']}"
        row["seed_hex"] = f"{row['seed']:032x}"
    pilot_seeds = {
        pilot_seed(r["n"], r["a_hundredths"], r["index"]) for r in rows
    }
    checks = check_seed_manifest(rows)
    checks["disjoint_from_pilot_prefix"] = not (pilot_seeds & {r["seed"] for r in rows})
    return {
        "experiment": EXPERIMENT,
        "seed_scheme": protocol_constants()["seed_scheme"],
        "rows": rows,
        "rows_sha256": _sha256_text(canonical_json(rows)),
        "checks": checks,
    }


def seed_manifest_sha256() -> str:
    return seed_manifest_document()["rows_sha256"]


# ---------------------------------------------------------------------------
# One instance
# ---------------------------------------------------------------------------


def _reversed_ids(n: int, clauses: Sequence[Sequence[int]]) -> list[list[int]]:
    return [[(n + 1 - abs(lit)) * (1 if lit > 0 else -1) for lit in clause] for clause in clauses]


def _apply_fault(fault: dict | None, attempt: int) -> None:
    """Test-only fault injection (refused for the confirmatory population)."""
    if not fault or attempt > int(fault.get("fail_attempts", 1 << 30)):
        return
    if "sleep_s" in fault:
        time.sleep(float(fault["sleep_s"]))
    if fault.get("raise"):
        raise RuntimeError("injected fault")
    if "exit_code" in fault:
        os._exit(int(fault["exit_code"]))


def run_instance(
    spec: InstanceSpec,
    *,
    budget: int = BUDGET_B,
    certify: bool = True,
    attempt: int = 1,
    fault: dict | None = None,
    keep_proof: bool = False,
    official: bool = False,
) -> tuple[dict, dict, list[str] | None]:
    """Run one instance. Returns ``(primary_record, telemetry, proof_lines)``.

    Fault injection is refused for every confirmatory instance (NOVA-R10-04),
    and a confirmatory test instance runs only when ``run_specs`` has checked
    an issued :class:`om_lab.freeze.AuthorizedFreeze`. ``official`` is internal:
    only ``run_specs`` sets it, after that check.
    """
    if spec.population == "confirmatory":
        if fault:
            raise ValueError("fault injection is refused for the confirmatory population")
        if spec.split == "test" and not official:
            raise ConfirmatoryRunNotAuthorized(
                "confirmatory test instances run only through the authorised production path"
            )
    t_start = time.perf_counter()
    _apply_fault(fault, attempt)
    inst = generate_random_3sat(n_vars=spec.n, n_clauses=spec.m, seed=spec.seed)
    clauses = inst.clauses
    n = spec.n

    t_feat = time.perf_counter()
    min_fill = primal_min_fill_width(n, clauses)
    width_replay = replay_elimination_order(n, clauses, min_fill.ordering)
    width_reversed = primal_min_fill_width(n, _reversed_ids(n, clauses)).width
    degree_mean = extract_features_from_clauses(n, clauses).to_dict()["cooccurrence_degree_mean"]
    features_s = time.perf_counter() - t_feat

    t_dpll = time.perf_counter()
    primary = solve_dpll(n, clauses, max_decisions=budget, max_seconds=None)
    dpll_s = time.perf_counter() - t_dpll

    reference = None
    reference_summary = None
    reference_s = 0.0
    if certify:
        t_ref = time.perf_counter()
        reference, reference_summary = reference_certificate(n, clauses)
        reference_s = time.perf_counter() - t_ref

    if primary.status == Status.SAT:
        verification = check_sat_witness(clauses, primary.model)
    elif primary.status == Status.UNSAT:
        verification = label_unsat_claim(primary, reference)
    else:
        verification = Verification.NOT_APPLICABLE

    agreement = "NOT_CHECKED"
    alarm = None
    if reference is not None:
        if primary.status in (Status.SAT, Status.UNSAT):
            agreement = "AGREE" if primary.status == reference.status else "DISAGREE"
        else:
            agreement = "NOT_APPLICABLE"
        if agreement == "DISAGREE":
            alarm = (
                f"primary {primary.status} vs reference {reference.status} "
                f"({reference.verification_status}); certification infrastructure suspect"
            )
            verification = Verification.INVALID
        if primary.status == Status.UNSAT and verification == Verification.INVALID and alarm is None:
            alarm = "reference certificate for this UNSAT claim was rejected by the checker"

    record = {
        "experiment": EXPERIMENT,
        "record_schema_version": RECORD_SCHEMA_VERSION,
        "runner_version": RUNNER_VERSION,
        "population": spec.population,
        "split": spec.split,
        "instance_id": spec.instance_id,
        "problem": "random_3sat",
        "n_vars": n,
        "n_clauses": spec.m,
        "a_hundredths": spec.a_hundredths,
        "index": spec.index,
        "seed": spec.seed,
        "seed_hex": f"{spec.seed:032x}",
        "formula_sha256": _sha256_text(dimacs_text(n, clauses)),
        "width": min_fill.width,
        "width_replay": width_replay,
        "width_ordering_sha256": _sha256_text(",".join(map(str, min_fill.ordering))),
        "width_reversed": width_reversed,
        "degree_mean": degree_mean,
        "solver": primary.solver_name,
        "budget_b": budget,
        "max_decisions": budget,
        "max_seconds": None,
        "status": primary.status,
        "stop_reason": primary.stop_reason,
        "decisions": primary.decisions,
        "propagations": primary.propagations,
        "budget_exhausted": primary.stop_reason == StopReason.DECISION_BUDGET,
        "satisfiable": primary.satisfiable,
        "timed_out": primary.timed_out,
        "verified": verification in Verification.CERTIFIED,
        "verification_status": verification,
        "y": capped_log_effort(primary.decisions, primary.timed_out, budget=budget),
        "model": primary.model if primary.status == Status.SAT else None,
        "reference": reference_summary,
        "reference_agreement": agreement,
        "integrity_alarm": alarm,
        "error": None,
    }
    telemetry = {
        "instance_id": spec.instance_id,
        "attempt": attempt,
        "features_s": features_s,
        "dpll_s": dpll_s,
        "reference_s": reference_s,
        "total_s": time.perf_counter() - t_start,
        "pid": os.getpid(),
    }
    proof = None
    if keep_proof and reference is not None and reference.certificate is not None:
        proof = list(reference.certificate["proof"])
    return record, telemetry, proof


def error_record(spec: InstanceSpec, *, budget: int, kind: str, attempts: int, detail: str) -> dict:
    """The single primary record of an instance whose every attempt failed."""
    try:
        inst = generate_random_3sat(n_vars=spec.n, n_clauses=spec.m, seed=spec.seed)
        formula_sha = _sha256_text(dimacs_text(spec.n, inst.clauses))
    except Exception:  # pragma: no cover - generation failure is itself the error
        formula_sha = None
    return {
        "experiment": EXPERIMENT,
        "record_schema_version": RECORD_SCHEMA_VERSION,
        "runner_version": RUNNER_VERSION,
        "population": spec.population,
        "split": spec.split,
        "instance_id": spec.instance_id,
        "problem": "random_3sat",
        "n_vars": spec.n,
        "n_clauses": spec.m,
        "a_hundredths": spec.a_hundredths,
        "index": spec.index,
        "seed": spec.seed,
        "seed_hex": f"{spec.seed:032x}",
        "formula_sha256": formula_sha,
        "width": None,
        "width_replay": None,
        "width_ordering_sha256": None,
        "width_reversed": None,
        "degree_mean": None,
        "solver": "dpll",
        "budget_b": budget,
        "max_decisions": budget,
        "max_seconds": None,
        "status": Status.ERROR,
        "stop_reason": kind,
        "decisions": None,
        "propagations": None,
        "budget_exhausted": False,
        "satisfiable": False,
        "timed_out": False,
        "verified": False,
        "verification_status": Verification.NOT_APPLICABLE,
        "y": None,
        "model": None,
        "reference": None,
        "reference_agreement": "NOT_APPLICABLE",
        "integrity_alarm": None,
        "error": {"kind": kind, "attempts": attempts, "detail": detail[-2000:]},
    }


# ---------------------------------------------------------------------------
# Worker pool with watchdog and same-instance reruns
# ---------------------------------------------------------------------------


#: Seconds a new worker may take to import the lab stack and report ready.
WORKER_START_TIMEOUT_S = 300.0


def _worker_main(conn, config: dict) -> None:  # pragma: no cover - runs in child processes
    # Imports are complete once this function runs; report readiness so the
    # parent's watchdog measures instance execution only, never start-up.
    conn.send(("ready", os.getpid()))
    while True:
        try:
            message = conn.recv()
        except (EOFError, OSError):
            return
        if message is None:
            return
        spec_fields, attempt = message
        spec = InstanceSpec(**spec_fields)
        try:
            payload = run_instance(
                spec,
                budget=config["budget"],
                certify=config["certify"],
                attempt=attempt,
                fault=config["fault_injection"].get(spec.instance_id),
                keep_proof=config["keep_proof"],
                official=config["official"],
            )
            conn.send(("ok", payload))
        except BaseException as exc:  # noqa: BLE001 - every failure must be reported
            conn.send(("exception", f"{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=8)}"))


@dataclass
class _Worker:
    process: object
    conn: object
    job: tuple[InstanceSpec, int, float] | None = None


@dataclass
class RunOutput:
    records: list[dict]
    telemetry: list[dict]
    failures: list[dict]
    proofs: dict[str, list[str]]


def run_specs(
    specs: Sequence[InstanceSpec],
    *,
    workers: int = 1,
    budget: int = BUDGET_B,
    certify: bool = True,
    watchdog_s: float = DEFAULT_WATCHDOG_S,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    fault_injection: dict[str, dict] | None = None,
    keep_proof: bool = False,
    progress: Callable[[int, int], None] | None = None,
    authorization: object = None,
) -> RunOutput:
    """Run every spec and return exactly one primary record per spec, in spec order.

    ``workers=0`` runs inline in this process (no watchdog; for tests and
    debugging). ``workers>=1`` uses worker processes with a per-instance
    watchdog; infrastructure failures are rerun with the same instance and
    budget up to ``max_attempts`` times.

    Refused before anything runs: fault injection with any confirmatory spec
    (NOVA-R10-04), and confirmatory test specs unless ``authorization`` is an
    :class:`om_lab.freeze.AuthorizedFreeze` issued by
    ``freeze.verify_for_execution`` in this process, ``specs`` is exactly the
    frozen test schedule, and these settings equal the frozen settings in
    value and type (ACE-PLAN-02/06).
    """
    if len({s.instance_id for s in specs}) != len(specs):
        raise ValueError("duplicate instances in spec list")
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    faults = dict(fault_injection or {})
    if faults and any(s.population == "confirmatory" for s in specs):
        raise ValueError("fault injection is refused for the confirmatory population")
    official = False
    if any(s.population == "confirmatory" and s.split == "test" for s in specs):
        from om_lab.freeze import is_issued, schedule_sha256, validate_schedule

        if not is_issued(authorization):
            raise ConfirmatoryRunNotAuthorized(
                "confirmatory test instances need an authorisation issued by om_lab.freeze.verify_for_execution"
            )
        problems = validate_schedule(list(specs), "test")
        if problems or schedule_sha256(list(specs)) != authorization.test_schedule_sha256:
            raise ConfirmatoryRunNotAuthorized(
                "official execution schedules exactly the frozen 840-instance test population: "
                + "; ".join(problems[:5] or ["schedule hash differs from Stage A"])
            )
        authorization.require_settings(
            workers=workers, watchdog_s=watchdog_s, max_attempts=max_attempts, budget_b=budget,
            certify=certify, keep_certificates=keep_proof,
            worker_start_timeout_s=float(WORKER_START_TIMEOUT_S), max_seconds=None,
        )
        official = True
    done: dict[str, tuple[dict, dict]] = {}
    failures: list[dict] = []
    proofs: dict[str, list[str]] = {}
    total = len(specs)

    def record_failure(spec: InstanceSpec, attempt: int, kind: str, detail: str, queue: deque) -> None:
        failures.append({"instance_id": spec.instance_id, "attempt": attempt, "kind": kind, "detail": detail[-2000:]})
        if attempt < max_attempts:
            queue.append((spec, attempt + 1))
        else:
            done[spec.instance_id] = (
                error_record(spec, budget=budget, kind=kind, attempts=attempt, detail=detail),
                {"instance_id": spec.instance_id, "attempt": attempt, "failed": True},
            )
            if progress:
                progress(len(done), total)

    def accept(spec: InstanceSpec, payload) -> None:
        record, telemetry, proof = payload
        done[spec.instance_id] = (record, telemetry)
        if proof is not None:
            proofs[spec.instance_id] = proof
        if progress:
            progress(len(done), total)

    queue: deque = deque((spec, 1) for spec in specs)
    if workers == 0:
        while queue:
            spec, attempt = queue.popleft()
            try:
                payload = run_instance(
                    spec, budget=budget, certify=certify, attempt=attempt,
                    fault=faults.get(spec.instance_id), keep_proof=keep_proof, official=official,
                )
            except Exception as exc:  # noqa: BLE001
                record_failure(spec, attempt, "exception", f"{type(exc).__name__}: {exc}", queue)
                continue
            accept(spec, payload)
    else:
        ctx = mp.get_context("spawn")
        config = {"budget": budget, "certify": certify, "fault_injection": faults, "keep_proof": keep_proof,
                  "official": official}

        def start_worker() -> _Worker:
            parent_conn, child_conn = ctx.Pipe()
            process = ctx.Process(target=_worker_main, args=(child_conn, config), daemon=True)
            process.start()
            child_conn.close()
            try:
                ready = parent_conn.poll(WORKER_START_TIMEOUT_S) and parent_conn.recv()
            except (EOFError, OSError):
                ready = None
            if not ready or ready[0] != "ready":
                process.kill()
                process.join(timeout=10)
                raise RuntimeError("runner worker failed to start (infrastructure failure, not data)")
            return _Worker(process=process, conn=parent_conn)

        def stop_worker(worker: _Worker) -> None:
            if worker.process.is_alive():
                worker.process.kill()
            worker.process.join(timeout=10)
            worker.conn.close()

        pool = [start_worker() for _ in range(max(1, min(workers, len(specs) or 1)))]
        try:
            while queue or any(w.job is not None for w in pool):
                for worker in pool:
                    if worker.job is None and queue:
                        spec, attempt = queue.popleft()
                        worker.conn.send((asdict(spec), attempt))
                        worker.job = (spec, attempt, time.monotonic())
                busy = [w for w in pool if w.job is not None]
                ready = mp_wait([w.conn for w in busy], timeout=0.2)
                for idx, worker in enumerate(pool):
                    if worker.job is None or worker.conn not in ready:
                        continue
                    spec, attempt, _ = worker.job
                    worker.job = None
                    try:
                        kind, payload = worker.conn.recv()
                    except (EOFError, OSError):
                        worker.process.join(timeout=10)
                        detail = f"worker exited with code {worker.process.exitcode}"
                        record_failure(spec, attempt, "worker_crash", detail, queue)
                        stop_worker(worker)
                        pool[idx] = start_worker()
                        continue
                    if kind == "ok":
                        accept(spec, payload)
                    else:
                        record_failure(spec, attempt, "exception", payload, queue)
                now = time.monotonic()
                for idx, worker in enumerate(pool):
                    if worker.job is not None and now - worker.job[2] > watchdog_s:
                        spec, attempt, _ = worker.job
                        worker.job = None
                        stop_worker(worker)
                        record_failure(spec, attempt, "watchdog", f"exceeded {watchdog_s} s wall clock", queue)
                        pool[idx] = start_worker()
        finally:
            for worker in pool:
                try:
                    worker.conn.send(None)
                except (OSError, ValueError):
                    pass
            for worker in pool:
                worker.process.join(timeout=5)
                stop_worker(worker)

    missing = [s.instance_id for s in specs if s.instance_id not in done]
    if missing:  # defensive: the loops above always settle every spec
        raise RuntimeError(f"runner lost {len(missing)} instances: {missing[:3]}")
    records = [done[s.instance_id][0] for s in specs]
    telemetry = [done[s.instance_id][1] for s in specs]
    return RunOutput(records=records, telemetry=telemetry, failures=failures, proofs=proofs)


# ---------------------------------------------------------------------------
# Integrity checks (shared by run, combine and audit)
# ---------------------------------------------------------------------------


_HEX64_CHARS = frozenset("0123456789abcdef")


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: object) -> bool:
    """A finite JSON number (int or float, never a bool).

    ``math.isfinite`` on a huge int raises ``OverflowError`` (it converts
    to float first), so the int path converts defensively: an int too
    large for a finite float is not a number here (NOVA-G28-01 -- the
    same guard Dee's ``_require_finite_number`` uses in analyze_width).
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, float):
        return math.isfinite(value)
    try:
        return math.isfinite(float(value))
    except OverflowError:
        return False


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= _HEX64_CHARS


def _record_type_problems(rec: dict) -> list[str]:
    """Strict JSON types of a primary record; nothing is coerced (NOVA-R10-06)."""
    problems: list[str] = []

    def need(key: str, ok: Callable[[object], bool], what: str) -> None:
        if not ok(rec[key]):
            problems.append(f"{key} is not {what}")

    for key in ("n_vars", "n_clauses", "a_hundredths", "index", "seed", "budget_b", "max_decisions"):
        need(key, _is_int, "an int")
    for key in ("satisfiable", "timed_out", "budget_exhausted", "verified"):
        need(key, lambda v: isinstance(v, bool), "a bool")
    for key in ("experiment", "runner_version", "population", "split", "instance_id", "problem", "solver",
                "seed_hex", "reference_agreement"):
        need(key, lambda v: isinstance(v, str), "a string")
    for key in ("stop_reason", "integrity_alarm"):
        need(key, lambda v: v is None or isinstance(v, str), "a string or null")
    need("status", lambda v: isinstance(v, str) and v in Status.ALL, "a known status")
    need("verification_status", lambda v: isinstance(v, str) and v in Verification.ALL, "a known verification status")
    need("record_schema_version", lambda v: v == RECORD_SCHEMA_VERSION and _is_int(v), f"{RECORD_SCHEMA_VERSION}")
    need("max_seconds", lambda v: v is None, "null")
    if rec["status"] != Status.ERROR:
        need("decisions", lambda v: _is_int(v) and v >= 0, "a non-negative int")
        need("propagations", lambda v: _is_int(v) and v >= 0, "a non-negative int")
        need("y", _is_number, "a finite number")
        for key in ("width", "width_replay", "width_reversed"):
            need(key, lambda v: _is_int(v) and v >= 0, "a non-negative int")
        need("degree_mean", _is_number, "a finite number")
        need("formula_sha256", _is_sha256, "a SHA-256")
        need("width_ordering_sha256", _is_sha256, "a SHA-256")
        need("reference", lambda v: v is None or isinstance(v, dict), "an object or null")
        need("error", lambda v: v is None, "null")
    else:
        need("error", lambda v: isinstance(v, dict), "an object")
    return problems


def _model_problem(model: object, n_vars: int) -> str | None:
    """A complete SAT model lists +/-v at position v-1 for every variable."""
    if not isinstance(model, list) or not all(_is_int(lit) for lit in model):
        return "SAT model is not a list of int literals"
    if [abs(lit) for lit in model] != list(range(1, n_vars + 1)):
        return "SAT model is not a complete assignment in variable order"
    return None


def _certificate_summary_problem(rec: dict) -> str | None:
    """Is a proof-checked UNSAT claim backed by a consistent certificate summary?"""
    ref = rec["reference"]
    cert = ref.get("certificate") if isinstance(ref, dict) else None
    if not isinstance(ref, dict) or ref.get("status") != Status.UNSAT or not isinstance(cert, dict):
        return "UNSAT_PROOF_CHECKED claim has no reference UNSAT certificate"
    if cert.get("result") != "VALID" or cert.get("kind") != "DRAT":
        return "UNSAT_PROOF_CHECKED claim rests on a certificate that is not a VALID DRAT proof"
    if (cert.get("checker"), cert.get("checker_version"), cert.get("checker_sha256")) != (
        CHECKER_NAME, CHECKER_VERSION, checker_source_sha256()
    ):
        return "UNSAT_PROOF_CHECKED claim names a different proof checker"
    if not _is_sha256(cert.get("proof_sha256")):
        return "UNSAT_PROOF_CHECKED claim has no proof hash"
    if rec["reference_agreement"] != "AGREE":
        return "UNSAT_PROOF_CHECKED claim without primary/reference agreement"
    return None


def integrity_report(
    records: Sequence[dict],
    specs: Sequence[InstanceSpec],
    *,
    budget: int,
    full_population: Sequence[InstanceSpec] | None = None,
) -> dict:
    """Checks of a record set against its expected instances.

    Structural checks (one record per expected instance, identity fields,
    strict field types that never crash on bad input, status/verification
    consistency) and the evidence behind each claim, which a stored status
    alone never satisfies (NOVA-R10-05): the formula is regenerated from the
    seed and its hash compared, every SAT model is re-verified against it,
    and every ``UNSAT_PROOF_CHECKED`` claim must carry a VALID certificate
    summary from this checker. The retained proof files themselves are
    checked by :func:`audit_retained_certificates`. ``complete`` is True
    only when the records are exactly ``full_population`` (None when it is
    not given).
    """
    failures: list[str] = []
    ids = [r.get("instance_id") if isinstance(r, dict) else None for r in records]
    expected = [s.instance_id for s in specs]
    counts = Counter(ids)
    duplicates = sorted(str(i) for i, c in counts.items() if c > 1)
    missing = sorted(set(expected) - set(ids))
    unexpected = sorted(str(i) for i in set(ids) - set(expected))
    if duplicates:
        failures.append(f"{len(duplicates)} instance(s) have more than one primary record")
    if missing:
        failures.append(f"{len(missing)} expected instance(s) have no primary record")
    if unexpected:
        failures.append(f"{len(unexpected)} record(s) are not in the expected population")
    by_spec = {s.instance_id: s for s in specs}
    cap = math.log1p(budget)
    status_counts: Counter = Counter()
    verification_counts: Counter = Counter()
    total_attempts = 0
    alarms = 0
    evidence_checked = 0
    for rec in records:
        if not isinstance(rec, dict):
            failures.append("a record is not a JSON object")
            continue
        rid = rec.get("instance_id")
        missing_keys = RECORD_KEYS - set(rec)
        extra_keys = set(rec) - RECORD_KEYS
        if missing_keys or extra_keys:
            failures.append(f"{rid}: missing keys {sorted(missing_keys)} / unexpected keys {sorted(extra_keys)}")
            continue
        type_problems = _record_type_problems(rec)
        if type_problems:
            failures.append(f"{rid}: {'; '.join(type_problems)}")
            continue
        status = rec["status"]
        verification = rec["verification_status"]
        status_counts[status] += 1
        verification_counts[verification] += 1
        spec = by_spec.get(rid)
        if spec is not None:
            if (rec["population"], rec["n_vars"], rec["n_clauses"], rec["a_hundredths"], rec["index"], rec["seed"],
                    rec["split"], rec["seed_hex"]) != (spec.population, spec.n, spec.m, spec.a_hundredths, spec.index,
                                                       spec.seed, spec.split, f"{spec.seed:032x}"):
                failures.append(f"{rid}: identity fields differ from the seed scheme")
        if rec["experiment"] != EXPERIMENT or rec["budget_b"] != budget or rec["max_decisions"] != budget:
            failures.append(f"{rid}: experiment or budget fields differ from the protocol")
        if rec["runner_version"] != RUNNER_VERSION:
            failures.append(f"{rid}: runner_version {rec['runner_version']} differs from this runner ({RUNNER_VERSION})")
        if rec["integrity_alarm"]:
            alarms += 1
        if verification not in ALLOWED_VERIFICATION.get(status, frozenset()):
            failures.append(f"{rid}: verification status {verification} is not allowed for {status}")
        if status == Status.ERROR:
            if rec["y"] is not None or rec["decisions"] is not None:
                failures.append(f"{rid}: ERROR record carries effort values")
            continue
        total_attempts += rec["decisions"]
        if rec["satisfiable"] != (status == Status.SAT):
            failures.append(f"{rid}: satisfiable flag contradicts status {status}")
        if rec["width_replay"] != rec["width"]:
            failures.append(f"{rid}: elimination-order replay width != reported width")
        if status == Status.UNKNOWN:
            if rec["satisfiable"] or not rec["timed_out"] or verification != Verification.NOT_APPLICABLE:
                failures.append(f"{rid}: UNKNOWN record makes a satisfiability claim")
            if rec["stop_reason"] == StopReason.DECISION_BUDGET and rec["decisions"] != budget:
                failures.append(f"{rid}: budget-exhausted record has D != B")
            if rec["y"] != cap:
                failures.append(f"{rid}: UNKNOWN record has Y != ln(1+B)")
        else:
            if rec["timed_out"] or rec["decisions"] >= budget:
                failures.append(f"{rid}: completed record at or over the budget")
            if rec["y"] != math.log1p(rec["decisions"]):
                failures.append(f"{rid}: Y does not equal ln(1+D)")
        if status == Status.SAT and verification != Verification.SAT_WITNESS_CHECKED:
            failures.append(f"{rid}: SAT record without a checked witness")
        if status == Status.UNSAT and verification == Verification.INVALID:
            failures.append(f"{rid}: UNSAT record with an invalid certificate")
        if verification == Verification.UNSAT_KNOWN_BY_CONSTRUCTION:
            failures.append(f"{rid}: a construction certificate is impossible for a random 3-SAT record")
        if rec["verified"] != (verification in Verification.CERTIFIED):
            failures.append(f"{rid}: verified flag inconsistent with verification_status")
        if status != Status.SAT and rec["model"] is not None:
            failures.append(f"{rid}: a non-SAT record carries a model")
        if verification == Verification.UNSAT_PROOF_CHECKED:
            problem = _certificate_summary_problem(rec)
            if problem:
                failures.append(f"{rid}: {problem}")
        if spec is not None:
            inst = generate_random_3sat(n_vars=spec.n, n_clauses=spec.m, seed=spec.seed)
            if rec["formula_sha256"] != _sha256_text(dimacs_text(spec.n, inst.clauses)):
                failures.append(f"{rid}: formula hash does not match the regenerated formula")
            if status == Status.SAT:
                problem = _model_problem(rec["model"], spec.n)
                if problem:
                    failures.append(f"{rid}: {problem}")
                elif not verify_cnf_assignment(inst.clauses, rec["model"]):
                    failures.append(f"{rid}: stored SAT model fails re-verification")
            evidence_checked += 1
    if alarms:
        failures.append(f"{alarms} record(s) carry an integrity alarm")
    n_unsat = status_counts[Status.UNSAT]
    n_unsat_certified = sum(
        1 for r in records
        if isinstance(r, dict) and r.get("status") == Status.UNSAT
        and r.get("verification_status") == Verification.UNSAT_PROOF_CHECKED
    )
    complete = None
    if full_population is not None:
        full_ids = [s.instance_id for s in full_population]
        complete = not duplicates and len(ids) == len(full_ids) and set(ids) == set(full_ids)
    return {
        "passed": not failures,
        "failures": failures,
        "n_expected": len(expected),
        "n_records": len(records),
        "n_population": None if full_population is None else len(full_population),
        "complete": complete,
        "evidence_checked_records": evidence_checked,
        "duplicates": duplicates[:20],
        "missing": missing[:20],
        "unexpected": unexpected[:20],
        "status_counts": dict(sorted(status_counts.items())),
        "verification_counts": dict(sorted(verification_counts.items())),
        "unsat_certified": n_unsat_certified,
        "unsat_total": n_unsat,
        "verification_gate_ready": not failures
        and n_unsat_certified == n_unsat
        and verification_counts[Verification.INVALID] == 0
        and status_counts[Status.ERROR] == 0,
        "total_branch_attempts": total_attempts,
        "max_total_branch_attempts_population": MAX_TOTAL_BRANCH_ATTEMPTS,
    }


# ---------------------------------------------------------------------------
# Legacy single-file freeze (schema 1): a provenance snapshot only
# ---------------------------------------------------------------------------


def draft_freeze_manifest() -> dict:
    """Schema-1 provenance snapshot. It never authorises anything any more.

    Kept because ``analyze_width.reproducibility_gates`` reads its
    ``source_sha256`` and ``environment.packages.numpy``. The confirmatory
    test split needs the two-stage freeze of :mod:`om_lab.freeze`.
    """
    return {
        "experiment": EXPERIMENT,
        "freeze_schema_version": FREEZE_SCHEMA_VERSION,
        "runner_version": RUNNER_VERSION,
        "status": "DRAFT",
        "confirmatory_authorized": False,
        "authorized_by": None,
        "authorized_at_utc": None,
        "superseded_by": "om_lab.freeze Stage A + Stage B (NOVA-R10-01, ACE-PLAN-01)",
        "git": git_state(),
        "environment": environment_fingerprint(),
        "source_sha256": source_hashes(),
        "function_sha256": function_hashes(),
        "checker_sha256": checker_source_sha256(),
        "seed_manifest_sha256": seed_manifest_sha256(),
        "protocol": protocol_constants(),
        "instructions": (
            "Provenance snapshot only. Build Stage A with the stage-a command, run the "
            "non-executing preflight, and let Lumi write Stage B with the authorize command."
        ),
    }


def check_confirmatory_authorization(freeze_path: str | os.PathLike | None) -> dict:
    """Retired schema-1 guard: always refuses (NOVA-R10-01).

    A single-file manifest cannot meet B4 (it has no training, model or
    document hashes and is self-authorising); use :mod:`om_lab.freeze`.
    """
    raise ConfirmatoryRunNotAuthorized(
        "single-file freeze manifests (schema 1) no longer authorise the confirmatory test split "
        "(NOVA-R10-01); verify Stage A and Stage B with om_lab.freeze"
    )


# ---------------------------------------------------------------------------
# Outputs and retained certificates
# ---------------------------------------------------------------------------


def write_jsonl(records: Iterable[dict], path: Path) -> str:
    """Write canonical JSON lines and return the file's SHA-256."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = "".join(canonical_json(rec) + "\n" for rec in records).encode("ascii")
    path.write_bytes(data)
    return _sha256_bytes(data)


def _no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    out: dict = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key {key!r}")
        out[key] = value
    return out


def _reject_constant(name: str) -> object:
    raise ValueError(f"non-finite JSON number {name}")


def read_jsonl(path: str | os.PathLike) -> list[dict]:
    """Read JSON lines strictly: objects only, no duplicate keys, no NaN.

    A malformed line raises ``ValueError`` naming the file and line
    (NOVA-R10-08) instead of a bare ``JSONDecodeError``.
    """
    out: list[dict] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line, object_pairs_hook=_no_duplicate_keys, parse_constant=_reject_constant)
            except ValueError as exc:
                raise ValueError(f"{path}:{line_no}: malformed record ({exc})") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: a record must be a JSON object")
            out.append(value)
    return out


def certificate_file_names(instance_id: str) -> tuple[str, str]:
    """Retained ``.cnf`` / ``.drat`` file names of one instance."""
    stem = _sha256_text(instance_id)[:16]
    return f"{stem}.cnf", f"{stem}.drat"


def certificate_manifest(records: Sequence[dict], retained: dict[str, dict] | None = None) -> list[dict]:
    """Section 4.1 retention: formula hash, certificate summary, checker identity, result.

    ``retained`` maps instance ids to the files written for them: file names
    and the SHA-256 of their exact bytes (ACE-PLAN-05).
    """
    out = []
    for rec in records:
        ref = rec.get("reference") or {}
        out.append(
            {
                "instance_id": rec["instance_id"],
                "formula_sha256": rec["formula_sha256"],
                "primary_status": rec["status"],
                "verification_status": rec["verification_status"],
                "reference_status": ref.get("status"),
                "certificate": ref.get("certificate"),
                "retained_files": (retained or {}).get(rec["instance_id"]),
            }
        )
    return out


def load_certificate_manifest(path: str | os.PathLike) -> tuple[bytes, list[dict]]:
    """Read a certificate manifest strictly (a JSON list of objects)."""
    data = Path(path).read_bytes()
    doc = json.loads(data.decode("utf-8"), object_pairs_hook=_no_duplicate_keys, parse_constant=_reject_constant)
    if not isinstance(doc, list) or not all(isinstance(entry, dict) for entry in doc):
        raise ValueError("a certificate manifest is a JSON list of objects")
    return data, doc


def retain_certificates(out_dir: Path, specs: Sequence[InstanceSpec], proofs: dict[str, list[str]]) -> dict[str, dict]:
    """Write each retained CNF and proof; return their names and byte hashes."""
    cert_dir = out_dir / "certificates"
    cert_dir.mkdir(parents=True, exist_ok=True)
    retained: dict[str, dict] = {}
    for spec in specs:
        proof = proofs.get(spec.instance_id)
        if proof is None:
            continue
        inst = generate_random_3sat(n_vars=spec.n, n_clauses=spec.m, seed=spec.seed)
        cnf_name, proof_name = certificate_file_names(spec.instance_id)
        cnf_bytes = dimacs_text(spec.n, inst.clauses).encode("ascii")
        proof_bytes = "".join(f"{str(line).strip()}\n" for line in proof).encode("ascii")
        (cert_dir / cnf_name).write_bytes(cnf_bytes)
        (cert_dir / proof_name).write_bytes(proof_bytes)
        retained[spec.instance_id] = {
            "cnf_file": cnf_name, "cnf_sha256": _sha256_bytes(cnf_bytes),
            "proof_file": proof_name, "proof_sha256": _sha256_bytes(proof_bytes),
        }
    return retained


def parse_dimacs_strict(text: str) -> tuple[int, list[list[int]]]:
    """Parse canonical DIMACS (as written by ``dimacs_text``); raise ValueError otherwise."""
    if not text.endswith("\n"):
        raise ValueError("DIMACS text does not end with a newline")
    lines = text[:-1].split("\n")
    header = lines[0].split(" ")
    if len(header) != 4 or header[:2] != ["p", "cnf"] or not all(t.isdigit() for t in header[2:]):
        raise ValueError("bad DIMACS header")
    n_vars, n_clauses = int(header[2]), int(header[3])
    if len(lines) - 1 != n_clauses:
        raise ValueError("DIMACS clause count differs from the header")
    clauses: list[list[int]] = []
    for line_no, line in enumerate(lines[1:], start=2):
        tokens = line.split(" ")
        try:
            values = [int(t) for t in tokens]
        except ValueError as exc:
            raise ValueError(f"line {line_no}: non-integer token") from exc
        if values[-1] != 0 or 0 in values[:-1] or any(abs(v) > n_vars for v in values[:-1]):
            raise ValueError(f"line {line_no}: malformed clause")
        clauses.append(values[:-1])
    if dimacs_text(n_vars, clauses) != text:
        raise ValueError("DIMACS text is not in canonical form")
    return n_vars, clauses


def audit_retained_certificates(
    records: Sequence[dict],
    *,
    specs: Sequence[InstanceSpec],
    certificates_dir: str | os.PathLike,
    certificate_manifest: Sequence[dict],
    drat_trim: str | None = None,
) -> dict:
    """Check the retained certificate files themselves (ACE-PLAN-05, NOVA-R10-15).

    For every retained pair named by the manifest, and for every
    ``UNSAT_PROOF_CHECKED`` record (which must have one): the manifest entry
    must agree with the record's formula and proof hashes; the exact bytes of
    the retained ``.cnf`` and ``.drat`` files must hash to those values; the
    retained CNF must be the canonical DIMACS of this instance's regenerated
    formula; and the independent checker must accept the retained proof
    against the retained CNF (optionally also DRAT-trim). Retained files of
    these instances that the manifest does not name are failures.
    Regenerating a proof is extra evidence and is not done here.
    """
    failures: list[str] = []
    cert_dir = Path(certificates_dir)
    by_spec = {s.instance_id: s for s in specs}
    entries: dict[str, dict] = {}
    for entry in certificate_manifest:
        iid = entry.get("instance_id")
        if not isinstance(iid, str):
            failures.append("certificate manifest entry without an instance id")
        elif iid in entries:
            failures.append(f"{iid}: duplicate certificate manifest entry")
        else:
            entries[iid] = entry
    checked = 0
    drat_trim_verified = 0
    legacy_entries = 0
    referenced: set[str] = set()
    for rec in records:
        iid = rec.get("instance_id") if isinstance(rec, dict) else None
        spec = by_spec.get(iid)
        if spec is None:
            continue
        claims_proof = rec.get("status") == Status.UNSAT and rec.get("verification_status") == Verification.UNSAT_PROOF_CHECKED
        entry = entries.get(iid)
        cert = ((rec.get("reference") or {}).get("certificate") or {}) if isinstance(rec.get("reference"), dict) else {}
        cnf_name, proof_name = certificate_file_names(iid)
        files = entry.get("retained_files") if entry is not None else None
        if entry is not None and files is None and "retained_files" not in entry \
                and (cert_dir / cnf_name).is_file() and (cert_dir / proof_name).is_file():
            # Manifest written before retained-file hashes existed: the
            # association is by deterministic name and the record's hashes.
            files = {"cnf_file": cnf_name, "cnf_sha256": rec.get("formula_sha256"),
                     "proof_file": proof_name, "proof_sha256": cert.get("proof_sha256")}
            legacy_entries += 1
        if files is None:
            if claims_proof:
                failures.append(f"{iid}: proof-checked UNSAT claim has no retained certificate")
            continue
        if not isinstance(files, dict) or files.get("cnf_file") != cnf_name or files.get("proof_file") != proof_name:
            failures.append(f"{iid}: certificate manifest names unexpected retained files")
            continue
        referenced.update((cnf_name, proof_name))
        if entry.get("formula_sha256") != rec.get("formula_sha256") or files.get("cnf_sha256") != rec.get("formula_sha256"):
            failures.append(f"{iid}: certificate manifest formula hash differs from the record")
        if claims_proof and (files.get("proof_sha256") != cert.get("proof_sha256")
                             or (entry.get("certificate") or {}).get("proof_sha256") != cert.get("proof_sha256")):
            failures.append(f"{iid}: certificate manifest proof hash differs from the record")
        try:
            cnf_bytes = (cert_dir / cnf_name).read_bytes()
            proof_bytes = (cert_dir / proof_name).read_bytes()
        except OSError as exc:
            failures.append(f"{iid}: retained certificate file missing ({exc.__class__.__name__})")
            continue
        if _sha256_bytes(cnf_bytes) != files.get("cnf_sha256"):
            failures.append(f"{iid}: retained CNF bytes differ from the manifest hash")
        if _sha256_bytes(proof_bytes) != files.get("proof_sha256"):
            failures.append(f"{iid}: retained proof bytes differ from the manifest hash")
        try:
            n_vars, clauses = parse_dimacs_strict(cnf_bytes.decode("ascii"))
            proof_lines = proof_bytes.decode("ascii").splitlines()
        except (UnicodeDecodeError, ValueError) as exc:
            failures.append(f"{iid}: retained certificate files are malformed ({exc})")
            continue
        inst = generate_random_3sat(n_vars=spec.n, n_clauses=spec.m, seed=spec.seed)
        if n_vars != spec.n or clauses != [list(c) for c in inst.clauses]:
            failures.append(f"{iid}: retained CNF is not this instance's formula")
            continue
        result = check_drat(clauses, proof_lines)
        if not result.valid:
            failures.append(f"{iid}: retained proof does not refute the retained CNF ({result.reason})")
            continue
        checked += 1
        if drat_trim:
            verdict = run_drat_trim(drat_trim, n_vars, clauses, proof_lines)["verdict"]
            if verdict == "VERIFIED":
                drat_trim_verified += 1
            else:
                failures.append(f"{iid}: DRAT-trim verdict on the retained proof: {verdict}")
    stems = {certificate_file_names(s.instance_id)[0][:-4] for s in specs}
    if cert_dir.is_dir():
        for path in sorted(cert_dir.iterdir()):
            if path.stem in stems and path.name not in referenced:
                failures.append(f"{path.name}: retained file is not referenced by the certificate manifest")
    elif any(isinstance(r, dict) and r.get("verification_status") == Verification.UNSAT_PROOF_CHECKED for r in records):
        failures.append("the retained certificates directory is missing")
    return {
        "passed": not failures,
        "failures": failures,
        "checked": checked,
        "legacy_manifest_entries": legacy_entries,
        "drat_trim_verified": drat_trim_verified if drat_trim else None,
    }


def _settings_summary(*, workers: int, watchdog_s: float, max_attempts: int, budget: int, certify: bool,
                      keep_certificates: bool) -> dict:
    return {"workers": workers, "watchdog_s": watchdog_s, "max_attempts": max_attempts,
            "worker_start_timeout_s": float(WORKER_START_TIMEOUT_S), "budget_b": budget, "max_seconds": None,
            "certify": certify, "keep_certificates": keep_certificates}


def run_split(
    *,
    population: str,
    split: str,
    out_dir: str | os.PathLike,
    workers: int = 1,
    n_values: Sequence[int] | None = None,
    a_values: Sequence[int] | None = None,
    indices: Iterable[int] | None = None,
    budget: int = BUDGET_B,
    certify: bool = True,
    watchdog_s: float = DEFAULT_WATCHDOG_S,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    freeze_path: str | os.PathLike | None = None,
    stage_a_path: str | os.PathLike | None = None,
    stage_b_path: str | os.PathLike | None = None,
    diagnostic_subset: bool = False,
    fault_injection: dict[str, dict] | None = None,
    keep_certificates: bool = False,
    dry_run: bool = False,
    command: Sequence[str] | None = None,
    progress: bool = False,
) -> dict:
    """Run one split and write its results, telemetry, certificates and manifest.

    Confirmatory population (ACE-PLAN-02, NOVA-R10-02/03): the test split is
    the single production entrypoint; it schedules exactly the frozen
    840-instance population after :func:`om_lab.freeze.verify_for_execution`
    passes, and refuses any subset. A training subset must be requested as
    ``diagnostic_subset`` and is written under a ``DIAGNOSTIC_SUBSET`` name
    with ``complete: false``. Every manifest records ``run_mode``,
    ``complete``, ``n_instances`` and ``n_population``.
    """
    subset_requested = n_values is not None or a_values is not None or indices is not None
    run_mode = "PILOT" if population == "pilot" else "OFFICIAL"
    if population == "confirmatory":
        if budget != BUDGET_B:
            raise ValueError(f"the confirmatory budget is frozen at B={BUDGET_B}")
        if not certify:
            raise ValueError("confirmatory runs must produce certificates (Section 4.1)")
        if fault_injection:
            raise ValueError("fault injection is refused for the confirmatory population")
        if freeze_path is not None:
            check_confirmatory_authorization(freeze_path)
        if split == "test" and (subset_requested or diagnostic_subset):
            raise ConfirmatoryRunNotAuthorized(
                "the confirmatory test split runs only as the exact frozen 840-instance population; "
                "subset and recovery runs are refused (ACE-PLAN-02)"
            )
        if split == "train" and subset_requested and not diagnostic_subset:
            raise ValueError(
                "a confirmatory training subset must be requested with diagnostic_subset=True "
                "(--diagnostic-subset); it is written as partial output (ACE-PLAN-02)"
            )
        if diagnostic_subset:
            if not subset_requested:
                raise ValueError("diagnostic_subset needs an explicit subset selection")
            run_mode = "DIAGNOSTIC_SUBSET"
        if split == "test" and not dry_run and (stage_a_path is None or stage_b_path is None):
            raise ConfirmatoryRunNotAuthorized(
                "the confirmatory test split requires --stage-a and --stage-b (authorised freeze)"
            )
        if not keep_certificates and not dry_run:
            raise ValueError("confirmatory runs must retain certificates (--keep-certificates, ACE-PLAN-05)")
    elif diagnostic_subset:
        raise ValueError("diagnostic_subset applies to the confirmatory population only")
    full_specs = build_specs(population, split)
    specs = build_specs(population, split, n_values=n_values, a_values=a_values, indices=indices)
    watchdog_s = float(watchdog_s)
    settings = _settings_summary(workers=workers, watchdog_s=watchdog_s, max_attempts=max_attempts,
                                 budget=budget, certify=certify, keep_certificates=keep_certificates)
    authorization = None
    from om_lab import freeze

    if population == "confirmatory" and split == "test":
        schedule_problems = freeze.validate_schedule(specs, "test")
        if schedule_problems:
            raise ConfirmatoryRunNotAuthorized("; ".join(schedule_problems[:5]))
        if not dry_run or stage_a_path is not None or stage_b_path is not None:
            authorization = freeze.verify_for_execution(
                stage_a_path, stage_b_path,
                requested_settings=freeze.make_settings(workers=workers, watchdog_s=watchdog_s,
                                                        max_attempts=max_attempts),
            )
    if dry_run:
        return {"dry_run": True, "run_mode": run_mode, "n_instances": len(specs), "n_population": len(full_specs),
                "complete": [s.instance_id for s in specs] == [s.instance_id for s in full_specs],
                "schedule_sha256": freeze.schedule_sha256(specs), "solver_launched": False,
                "authorization": None if authorization is None else authorization.summary(),
                "first": specs[0].instance_id if specs else None, "last": specs[-1].instance_id if specs else None}

    started = datetime.now(timezone.utc).isoformat()

    def report(done: int, total: int) -> None:
        if progress and (done == total or done % 50 == 0):
            print(f"[{EXPERIMENT}] {population}/{split}: {done}/{total}", file=sys.stderr, flush=True)

    output = run_specs(
        specs, workers=workers, budget=budget, certify=certify, watchdog_s=watchdog_s,
        max_attempts=max_attempts, fault_injection=fault_injection,
        keep_proof=keep_certificates, progress=report, authorization=authorization,
    )
    integrity = integrity_report(output.records, specs, budget=budget, full_population=full_specs)
    if integrity["n_records"] != len(specs) or integrity["duplicates"]:
        raise RuntimeError("one-record-per-instance invariant violated")
    complete = integrity["complete"] is True

    out = Path(out_dir)
    stem = f"{population}_{split}" + ("_DIAGNOSTIC_SUBSET" if run_mode == "DIAGNOSTIC_SUBSET" else "")
    results_path = out / f"{stem}_results.jsonl"
    results_sha = write_jsonl(output.records, results_path)
    telemetry_path = out / f"{stem}_telemetry.jsonl"
    write_jsonl(output.telemetry + [{"failure": f} for f in output.failures], telemetry_path)
    retained = retain_certificates(out, specs, output.proofs) if keep_certificates else {}
    cert_path = out / f"{stem}_certificate_manifest.json"
    cert_path.write_text(json.dumps(certificate_manifest(output.records, retained), indent=1, sort_keys=True),
                         encoding="utf-8")
    manifest = {
        "experiment": EXPERIMENT,
        "runner_version": RUNNER_VERSION,
        "orchestration_version": ORCHESTRATION_VERSION,
        "record_schema_version": RECORD_SCHEMA_VERSION,
        "population": population,
        "split": split,
        "run_mode": run_mode,
        "complete": complete,
        "partial": not complete,
        "n_instances": len(specs),
        "n_population": len(full_specs),
        "schedule_sha256": freeze.schedule_sha256(specs),
        "claim_level": "Empirical Observation",
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "command": list(command) if command else None,
        "host": socket.gethostname(),
        "workers": workers,
        "watchdog_s": watchdog_s,
        "max_attempts": max_attempts,
        "budget_b": budget,
        "certify": certify,
        "settings": settings,
        "authorization": None if authorization is None else authorization.summary(),
        "fault_injection": sorted(fault_injection) if fault_injection else None,
        "results_file": results_path.name,
        "results_sha256": results_sha,
        "certificate_manifest_file": cert_path.name,
        "certificate_manifest_sha256": _sha256_bytes(cert_path.read_bytes()),
        "certificates_retained": len(retained),
        "infrastructure_failures": len(output.failures),
        "integrity": integrity,
        "environment": environment_fingerprint(),
        "git": git_state(),
        "source_sha256": source_hashes(),
        "function_sha256": function_hashes(),
        "checker_sha256": checker_source_sha256(),
        "seed_manifest_sha256": seed_manifest_sha256(),
        "protocol": protocol_constants(),
    }
    manifest_path = out / f"{stem}_run_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return {
        "results_path": str(results_path),
        "results_sha256": results_sha,
        "telemetry_path": str(telemetry_path),
        "certificate_manifest_path": str(cert_path),
        "run_manifest_path": str(manifest_path),
        "run_mode": run_mode,
        "complete": complete,
        "integrity": integrity,
        "failures": output.failures,
    }


def combine_results(
    paths: Sequence[str | os.PathLike],
    out_path: str | os.PathLike,
    *,
    population: str = "confirmatory",
    require_complete: bool = True,
    certificate_manifests: Sequence[str | os.PathLike] | None = None,
) -> dict:
    """Merge split files into one analysis file with full-population accounting.

    Writes ``<out>_combine_manifest.json`` with ``complete`` / ``partial``
    against the full population (NOVA-R10-03). A partial confirmatory combine
    must be written to a file whose name contains ``PARTIAL``. Given the
    per-split certificate manifests, their retained-file entries are merged
    into the combined ``certificate_manifest.json``.
    """
    records: list[dict] = []
    inputs: list[dict] = []
    for path in paths:
        inputs.append({"path": str(path), "sha256": _sha256_bytes(Path(path).read_bytes())})
        records.extend(read_jsonl(path))
    expected = build_specs(population, "train") + build_specs(population, "test")
    present = {r.get("instance_id") for r in records}
    specs = expected if require_complete else [s for s in expected if s.instance_id in present]
    report = integrity_report(records, specs, budget=BUDGET_B, full_population=expected)
    if report["duplicates"] or report["unexpected"] or (require_complete and report["missing"]):
        raise ValueError(f"cannot combine: {report['failures']}")
    complete = report["complete"] is True
    out = Path(out_path)
    if population == "confirmatory" and not complete and "PARTIAL" not in out.name:
        raise ValueError(
            "a partial confirmatory combine must be written to a file whose name contains PARTIAL (NOVA-R10-03)"
        )
    order = {s.instance_id: k for k, s in enumerate(expected)}
    records.sort(key=lambda r: order[r["instance_id"]])
    sha = write_jsonl(records, out)
    retained: dict[str, dict] = {}
    for manifest_path in certificate_manifests or []:
        _, entries = load_certificate_manifest(manifest_path)
        for entry in entries:
            if entry.get("instance_id") in present and entry.get("retained_files") is not None:
                if entry["instance_id"] in retained:
                    raise ValueError(f"{entry['instance_id']}: retained in more than one certificate manifest")
                retained[entry["instance_id"]] = entry["retained_files"]
    cert_path = out.with_name("certificate_manifest.json")
    cert_path.write_text(json.dumps(certificate_manifest(records, retained), indent=1, sort_keys=True),
                         encoding="utf-8")
    combine_manifest = {
        "kind": "OM-C001-R2/combine",
        "experiment": EXPERIMENT,
        "orchestration_version": ORCHESTRATION_VERSION,
        "population": population,
        "complete": complete,
        "partial": not complete,
        "n_records": len(records),
        "n_population": len(expected),
        "results_file": out.name,
        "results_sha256": sha,
        "certificate_manifest_file": cert_path.name,
        "certificate_manifest_sha256": _sha256_bytes(cert_path.read_bytes()),
        "inputs": inputs,
        "integrity": report,
    }
    manifest_path = out.with_name(f"{out.stem}_combine_manifest.json")
    manifest_path.write_text(json.dumps(combine_manifest, indent=2, sort_keys=True), encoding="utf-8")
    return {"results_path": str(out), "results_sha256": sha, "certificate_manifest_path": str(cert_path),
            "combine_manifest_path": str(manifest_path), "complete": complete, "integrity": report}


def audit_records(
    records: Sequence[dict],
    *,
    population: str,
    splits: Sequence[str],
    recompute_features: bool = False,
    recheck_certificates: bool = False,
    drat_trim: str | None = None,
    certificates_dir: str | os.PathLike | None = None,
    certificate_manifest_path: str | os.PathLike | None = None,
) -> dict:
    """Independent re-verification of a results file (for Lumi, Section 8).

    Always: the evidence-checking integrity report (one record per expected
    instance, strict types, seed scheme, regenerated formula hash, SAT models
    re-checked, certificate summaries). With ``certificates_dir`` and
    ``certificate_manifest_path``: the retained ``.cnf``/``.drat`` files
    themselves (ACE-PLAN-05); this is required for a passing confirmatory
    audit. Optionally: features recomputed, and certificates regenerated as
    additional evidence (a regenerated proof that is valid but has a
    different hash is reported as a note, not a failure; NOVA-R10-07).
    """
    expected: list[InstanceSpec] = []
    for split in splits:
        expected.extend(build_specs(population, split))
    report = integrity_report(records, expected, budget=BUDGET_B, full_population=expected)
    failures = list(report["failures"])
    notes: list[str] = []
    retained_report = None
    if certificates_dir is not None and certificate_manifest_path is not None:
        try:
            _, manifest = load_certificate_manifest(certificate_manifest_path)
        except (OSError, ValueError) as exc:
            failures.append(f"cannot read the certificate manifest: {exc}")
        else:
            retained_report = audit_retained_certificates(
                records, specs=expected, certificates_dir=certificates_dir,
                certificate_manifest=manifest, drat_trim=drat_trim,
            )
            failures.extend(retained_report["failures"])
    elif population == "confirmatory":
        failures.append("the confirmatory audit requires the retained certificates "
                        "(--certificates-dir and --certificate-manifest)")
    by_id = {s.instance_id: s for s in expected}
    rechecked_certificates = 0
    regenerated_drat_trim_verified = 0
    for rec in records:
        spec = by_id.get(rec.get("instance_id")) if isinstance(rec, dict) else None
        if spec is None or rec.get("status") == Status.ERROR:
            continue
        inst = generate_random_3sat(n_vars=spec.n, n_clauses=spec.m, seed=spec.seed)
        if recompute_features:
            if primal_min_fill_width(spec.n, inst.clauses).width != rec.get("width"):
                failures.append(f"{spec.instance_id}: width differs on recomputation")
            degree = extract_features_from_clauses(spec.n, inst.clauses).to_dict()["cooccurrence_degree_mean"]
            if degree != rec.get("degree_mean"):
                failures.append(f"{spec.instance_id}: degree_mean differs on recomputation")
        if recheck_certificates and rec.get("status") == Status.UNSAT:
            reference = rec.get("reference")
            stored = ((reference.get("certificate") if isinstance(reference, dict) else None) or {})
            result, summary = reference_certificate(spec.n, inst.clauses)
            fresh = summary.get("certificate") or {}
            rechecked_certificates += 1
            if fresh.get("result") != "VALID":
                failures.append(f"{spec.instance_id}: regenerated certificate is invalid")
            elif not stored:
                notes.append(f"{spec.instance_id}: the record stores no certificate; a regenerated proof is valid "
                             "(extra evidence only, not the stored certificate)")
            elif fresh.get("proof_sha256") != stored.get("proof_sha256"):
                notes.append(f"{spec.instance_id}: regenerated proof is valid but differs from the stored proof hash")
            if drat_trim and fresh.get("result") == "VALID":
                verdict = run_drat_trim(drat_trim, spec.n, inst.clauses, result.certificate["proof"])["verdict"]
                if verdict == "VERIFIED":
                    regenerated_drat_trim_verified += 1
                else:
                    failures.append(f"{spec.instance_id}: DRAT-trim verdict on the regenerated proof: {verdict}")
    return {
        "passed": not failures,
        "failures": failures[:200],
        "n_failures": len(failures),
        "notes": notes[:200],
        "integrity": report,
        "retained_certificates": retained_report,
        "rechecked_certificates": rechecked_certificates,
        "drat_trim_verified": None if retained_report is None else retained_report["drat_trim_verified"],
        "regenerated_drat_trim_verified": regenerated_drat_trim_verified if drat_trim and recheck_certificates else None,
    }


# ---------------------------------------------------------------------------
# Certifier validation and smoke tests
# ---------------------------------------------------------------------------


def _max_satisfiable_prefix(clauses: Sequence[Sequence[int]]) -> list[list[int]]:
    from pysat.solvers import Solver

    lo, hi = 0, len(clauses)
    while hi - lo > 1:
        mid = (lo + hi) // 2
        with Solver(name="g4", bootstrap_with=clauses[:mid]) as solver:
            if solver.solve():
                lo = mid
            else:
                hi = mid
    return [list(c) for c in clauses[:lo]]


def validate_certifier(
    *,
    n_values: Sequence[int] = (30, 40, 50, 60),
    a_values: Sequence[int] = (426, 460, 500),
    indices: Iterable[int] = range(0, 20),
    drat_trim: str | None = None,
) -> dict:
    """Validate backend + checker together on pilot instances (Section 4.1).

    Genuine certificates must be accepted; each certificate replayed against
    the largest satisfiable clause prefix of its formula must be rejected
    (a sound checker can never accept a refutation of a satisfiable formula).
    Uses pilot seeds only, never confirmatory seeds.
    """
    specs = build_specs("pilot", "train", n_values=n_values, a_values=a_values, indices=indices)
    counts = Counter()
    problems: list[str] = []
    for spec in specs:
        inst = generate_random_3sat(n_vars=spec.n, n_clauses=spec.m, seed=spec.seed)
        result, summary = reference_certificate(spec.n, inst.clauses)
        if result.status == Status.SAT:
            counts["sat"] += 1
            counts["sat_witness_checked"] += int(result.verification_status == Verification.SAT_WITNESS_CHECKED)
            continue
        counts["unsat"] += 1
        proof = result.certificate["proof"]
        if summary["certificate"]["result"] == "VALID":
            counts["genuine_accepted"] += 1
        else:
            problems.append(f"{spec.instance_id}: genuine certificate rejected ({summary['certificate']['reason']})")
        prefix = _max_satisfiable_prefix(inst.clauses)
        if check_drat(prefix, proof).valid:
            problems.append(f"{spec.instance_id}: certificate accepted for a satisfiable prefix (UNSOUND)")
        else:
            counts["transplant_rejected"] += 1
        if drat_trim:
            if run_drat_trim(drat_trim, spec.n, inst.clauses, proof)["verdict"] == "VERIFIED":
                counts["drat_trim_genuine_verified"] += 1
            else:
                problems.append(f"{spec.instance_id}: DRAT-trim rejected a certificate om_lab accepted")
            if run_drat_trim(drat_trim, spec.n, prefix, proof)["verdict"] != "VERIFIED":
                counts["drat_trim_transplant_rejected"] += 1
            else:
                problems.append(f"{spec.instance_id}: DRAT-trim accepted a transplanted certificate")
    return {
        "claim_level": "Empirical Observation",
        "population": "pilot",
        "backend": f"pysat:{REFERENCE_BACKEND}",
        "backend_version": f"python-sat {_package_version('python-sat')}",
        "checker": {"name": CHECKER_NAME, "version": CHECKER_VERSION, "sha256": checker_source_sha256()},
        "drat_trim": drat_trim,
        "n_instances": len(specs),
        "counts": dict(sorted(counts.items())),
        "passed": not problems,
        "problems": problems,
    }


def smoke(out_dir: str | os.PathLike, *, workers: int = 2) -> dict:
    """Infrastructure smoke test on pilot instances (never confirmatory seeds).

    1. Two independent runs of the same pilot population (separate worker
       processes) must produce byte-identical primary records.
    2. A pilot run with a tiny budget (B=20) must produce UNKNOWN records
       with D == B and Y == ln(1+B), and never UNSAT for them.
    """
    out = Path(out_dir)
    kwargs = dict(population="pilot", split="train", n_values=[30, 60], a_values=[426, 500], indices=range(0, 6), workers=workers)
    first = run_split(out_dir=out / "run1", **kwargs)
    second = run_split(out_dir=out / "run2", **kwargs)
    tiny = run_split(out_dir=out / "tiny_budget", population="pilot", split="train", n_values=[60], a_values=[426], indices=range(0, 6), budget=20, workers=workers)
    tiny_records = read_jsonl(tiny["results_path"])
    unknown = [r for r in tiny_records if r["status"] == Status.UNKNOWN]
    checks = {
        "repeat_runs_byte_identical": first["results_sha256"] == second["results_sha256"],
        "repeat_run_integrity": first["integrity"]["passed"] and second["integrity"]["passed"],
        "tiny_budget_has_unknown": bool(unknown),
        "tiny_budget_unknown_rows_consistent": all(
            r["decisions"] == 20 and r["y"] == math.log1p(20) and not r["satisfiable"]
            and r["verification_status"] == Verification.NOT_APPLICABLE for r in unknown
        ),
        "tiny_budget_integrity": tiny["integrity"]["passed"],
    }
    return {"passed": all(checks.values()), "checks": checks, "results_sha256": first["results_sha256"]}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _int_list(values: Sequence[str] | None) -> list[int] | None:
    return None if values is None else [int(v) for v in values]


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(
        prog="python -m om_lab.width_experiment",
        description=f"{EXPERIMENT} frozen experiment runner [Claim Level: Empirical Observation].",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_seeds = sub.add_parser("seeds", help="write the confirmatory seed manifest (no runs)")
    p_seeds.add_argument("--out", required=True)

    p_freeze = sub.add_parser("freeze", help="write a schema-1 provenance snapshot (never authorises; see stage-a)")
    p_freeze.add_argument("--out", required=True)

    p_stage_a = sub.add_parser("stage-a", help="write the Stage A freeze manifest and fitted model (B4)")
    p_stage_a.add_argument("--out-dir", required=True)
    p_stage_a.add_argument("--training-records", required=True)
    p_stage_a.add_argument("--training-certificates-dir", required=True)
    p_stage_a.add_argument("--training-certificate-manifest", required=True)
    p_stage_a.add_argument("--reproduction-sha256", required=True,
                           help="SHA-256 of the independently reproduced training-record file")
    p_stage_a.add_argument("--reproduced-by", required=True)
    p_stage_a.add_argument("--workers", type=int, required=True)
    p_stage_a.add_argument("--watchdog-s", type=float, default=DEFAULT_WATCHDOG_S)
    p_stage_a.add_argument("--max-attempts", type=int, default=DEFAULT_MAX_ATTEMPTS)
    p_stage_a.add_argument("--amendment-docs", nargs="+")
    p_stage_a.add_argument("--drat-trim")

    p_preflight = sub.add_parser("preflight", help="validate Stage A and build the 840-instance schedule (runs nothing)")
    p_preflight.add_argument("--stage-a", required=True)
    p_preflight.add_argument("--out")

    p_authorize = sub.add_parser("authorize", help="Lumi: write Stage B after a passing preflight")
    p_authorize.add_argument("--stage-a", required=True)
    p_authorize.add_argument("--authorized-by", required=True)
    p_authorize.add_argument("--confirm-test-split-unexposed", action="store_true")
    p_authorize.add_argument("--out", required=True)

    p_run = sub.add_parser("run", help="run one split")
    p_run.add_argument("--population", default="confirmatory", choices=POPULATIONS)
    p_run.add_argument("--split", required=True, choices=SPLITS)
    p_run.add_argument("--out-dir", required=True)
    p_run.add_argument("--workers", type=int, default=1)
    p_run.add_argument("--n-values", nargs="+")
    p_run.add_argument("--a-values", nargs="+")
    p_run.add_argument("--indices", nargs="+", help="subset of the split's indices (pilot, or with --diagnostic-subset)")
    p_run.add_argument("--budget", type=int, default=BUDGET_B, help="pilot only; frozen for confirmatory")
    p_run.add_argument("--no-certify", action="store_true", help="pilot only")
    p_run.add_argument("--watchdog-s", type=float, default=DEFAULT_WATCHDOG_S)
    p_run.add_argument("--max-attempts", type=int, default=DEFAULT_MAX_ATTEMPTS)
    p_run.add_argument("--freeze", help="retired schema-1 manifest: always refused for the confirmatory population")
    p_run.add_argument("--stage-a", help="Stage A freeze manifest (confirmatory test split)")
    p_run.add_argument("--stage-b", help="Stage B authorisation (confirmatory test split)")
    p_run.add_argument("--diagnostic-subset", action="store_true",
                       help="confirmatory training subset, written as DIAGNOSTIC_SUBSET partial output")
    p_run.add_argument("--keep-certificates", action="store_true",
                       help="write .cnf/.drat files (required for the confirmatory population)")
    p_run.add_argument("--dry-run", action="store_true", help="build the schedule and check authorisation; runs nothing")

    p_combine = sub.add_parser("combine", help="merge split result files into results.jsonl")
    p_combine.add_argument("--out", required=True)
    p_combine.add_argument("--population", default="confirmatory", choices=POPULATIONS)
    p_combine.add_argument("--allow-partial", action="store_true")
    p_combine.add_argument("--certificate-manifest", action="append", default=[], dest="certificate_manifests",
                           help="a per-split certificate manifest whose retained files the combined manifest "
                                "names (repeat the option for each split)")
    p_combine.add_argument("paths", nargs="+")

    p_audit = sub.add_parser("audit", help="independently re-verify a results file")
    p_audit.add_argument("path")
    p_audit.add_argument("--population", default="confirmatory", choices=POPULATIONS)
    p_audit.add_argument("--splits", nargs="+", default=["train"], choices=SPLITS)
    p_audit.add_argument("--recompute-features", action="store_true")
    p_audit.add_argument("--recheck-certificates", action="store_true")
    p_audit.add_argument("--drat-trim")
    p_audit.add_argument("--certificates-dir", help="retained .cnf/.drat directory (required for confirmatory)")
    p_audit.add_argument("--certificate-manifest", help="certificate manifest naming the retained files")
    p_audit.add_argument("--out")

    p_val = sub.add_parser("validate-certifier", help="validate backend + checker on pilot instances")
    p_val.add_argument("--out", required=True)
    p_val.add_argument("--n-values", nargs="+", default=["30", "40", "50", "60"])
    p_val.add_argument("--a-values", nargs="+", default=["426", "460", "500"])
    p_val.add_argument("--count", type=int, default=20)
    p_val.add_argument("--drat-trim")

    p_smoke = sub.add_parser("smoke", help="infrastructure smoke test on pilot instances")
    p_smoke.add_argument("--out-dir", required=True)
    p_smoke.add_argument("--workers", type=int, default=2)

    args = parser.parse_args(argv)
    command = ["python", "-m", "om_lab.width_experiment", *argv]

    if args.cmd == "seeds":
        doc = seed_manifest_document()
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(doc, indent=1, sort_keys=True), encoding="utf-8")
        print(f"Wrote {len(doc['rows'])} seeds to {args.out}; checks={doc['checks']}")
        return 0 if not doc["checks"]["has_collision"] else 1
    if args.cmd == "freeze":
        doc = draft_freeze_manifest()
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(doc, indent=2, sort_keys=True), encoding="utf-8")
        print(f"Wrote a schema-1 provenance snapshot to {args.out}. It never authorises a run: "
              "use stage-a, preflight and authorize.")
        return 0
    if args.cmd in ("stage-a", "preflight", "authorize"):
        from om_lab import freeze

        try:
            if args.cmd == "stage-a":
                result = freeze.build_stage_a(
                    out_dir=args.out_dir, training_records_path=args.training_records,
                    training_certificates_dir=args.training_certificates_dir,
                    training_certificate_manifest_path=args.training_certificate_manifest,
                    independent_reproduction_sha256=args.reproduction_sha256, reproduced_by=args.reproduced_by,
                    settings=freeze.make_settings(workers=args.workers, watchdog_s=args.watchdog_s,
                                                  max_attempts=args.max_attempts),
                    amendment_docs=tuple(args.amendment_docs or freeze.DEFAULT_AMENDMENT_DOCS),
                    drat_trim=args.drat_trim,
                )
                print(f"Wrote Stage A {result['stage_a_path']} sha256={result['stage_a_sha256']}")
                print("Next: run preflight on it, then Lumi runs authorize.")
                return 0
            if args.cmd == "preflight":
                report = freeze.preflight(args.stage_a, out_path=args.out)
                print(json.dumps({k: report[k] for k in ("passed", "stage_a_sha256", "solver_launched",
                                                        "authorization_required", "test_schedule")}, indent=2))
                for problem in report["problems"][:40]:
                    print(f"  - {problem}")
                return 0 if report["passed"] else 1
            result = freeze.authorize(
                args.stage_a, authorized_by=args.authorized_by,
                test_split_unexposed=args.confirm_test_split_unexposed, out_path=args.out,
            )
            print(f"Wrote Stage B {result['stage_b_path']} for Stage A sha256={result['stage_a_sha256']}")
            return 0
        except ConfirmatoryRunNotAuthorized as exc:
            print(f"REFUSED: {exc}", file=sys.stderr)
            return 2
    if args.cmd == "run":
        try:
            summary = run_split(
                population=args.population, split=args.split, out_dir=args.out_dir,
                workers=args.workers, n_values=_int_list(args.n_values),
                a_values=_int_list(args.a_values), indices=_int_list(args.indices),
                budget=args.budget, certify=not args.no_certify, watchdog_s=args.watchdog_s,
                max_attempts=args.max_attempts, freeze_path=args.freeze,
                stage_a_path=args.stage_a, stage_b_path=args.stage_b,
                diagnostic_subset=args.diagnostic_subset,
                keep_certificates=args.keep_certificates, dry_run=args.dry_run,
                command=command, progress=True,
            )
        except ConfirmatoryRunNotAuthorized as exc:
            print(f"REFUSED: confirmatory test split not authorised: {exc}", file=sys.stderr)
            return 2
        except ValueError as exc:
            print(f"REFUSED: {exc}", file=sys.stderr)
            return 2
        if summary.get("dry_run"):
            print(json.dumps(summary, indent=2))
            return 0
        integ = summary["integrity"]
        print(f"[Claim Level: Empirical Observation] {EXPERIMENT} {args.population}/{args.split}")
        print(f"records={integ['n_records']}/{integ['n_expected']} status={integ['status_counts']}")
        print(f"verification={integ['verification_counts']} infrastructure_failures={len(summary['failures'])}")
        print(f"total_branch_attempts={integ['total_branch_attempts']} (population cap {MAX_TOTAL_BRANCH_ATTEMPTS})")
        print(f"integrity_passed={integ['passed']} verification_gate_ready={integ['verification_gate_ready']}")
        print(f"run_mode={summary['run_mode']} complete={summary['complete']} "
              f"(records {integ['n_records']} of a {integ['n_population']}-instance population)")
        for failure in integ["failures"]:
            print(f"  - {failure}")
        print(f"results: {summary['results_path']} sha256={summary['results_sha256']}")
        print(f"manifest: {summary['run_manifest_path']}")
        return 0 if integ["passed"] else 1
    if args.cmd == "combine":
        try:
            summary = combine_results(args.paths, args.out, population=args.population,
                                      require_complete=not args.allow_partial,
                                      certificate_manifests=args.certificate_manifests)
        except ValueError as exc:
            print(f"REFUSED: {exc}", file=sys.stderr)
            return 2
        print(f"Wrote {summary['results_path']} sha256={summary['results_sha256']} "
              f"integrity_passed={summary['integrity']['passed']} complete={summary['complete']}")
        if not summary["complete"]:
            print(f"PARTIAL: {summary['integrity']['n_records']} of {summary['integrity']['n_population']} instances")
        return 0 if summary["integrity"]["passed"] else 1
    if args.cmd == "audit":
        try:
            records = read_jsonl(args.path)
        except ValueError as exc:
            print(f"audit passed=False: {exc}", file=sys.stderr)
            return 1
        report = audit_records(
            records, population=args.population, splits=args.splits,
            recompute_features=args.recompute_features,
            recheck_certificates=args.recheck_certificates, drat_trim=args.drat_trim,
            certificates_dir=args.certificates_dir, certificate_manifest_path=args.certificate_manifest,
        )
        if args.out:
            Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        retained = report["retained_certificates"]
        print(f"audit passed={report['passed']} failures={report['n_failures']} "
              f"retained_certificates_checked={None if retained is None else retained['checked']} "
              f"drat_trim_verified={report['drat_trim_verified']} "
              f"rechecked_certificates={report['rechecked_certificates']} "
              f"regenerated_drat_trim_verified={report['regenerated_drat_trim_verified']}")
        for failure in report["failures"][:20]:
            print(f"  - {failure}")
        for note in report["notes"][:20]:
            print(f"  note: {note}")
        return 0 if report["passed"] else 1
    if args.cmd == "validate-certifier":
        report = validate_certifier(
            n_values=_int_list(args.n_values), a_values=_int_list(args.a_values),
            indices=range(0, args.count), drat_trim=args.drat_trim,
        )
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print(f"certifier validation passed={report['passed']} counts={report['counts']}")
        for problem in report["problems"][:20]:
            print(f"  - {problem}")
        return 0 if report["passed"] else 1
    if args.cmd == "smoke":
        report = smoke(args.out_dir, workers=args.workers)
        print(json.dumps(report, indent=2))
        return 0 if report["passed"] else 1
    return 2  # pragma: no cover


if __name__ == "__main__":
    # Under ``python -m`` this file runs as ``__main__`` while om_lab.freeze
    # imports ``om_lab.width_experiment``: two module objects with two
    # ConfirmatoryRunNotAuthorized classes. Run the canonical module's main
    # so refusals raised in om_lab.freeze are caught and reported (exit 2).
    from om_lab.width_experiment import main as _canonical_main

    sys.exit(_canonical_main())
