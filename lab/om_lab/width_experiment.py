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
The confirmatory test split (indices 70-99) can only be run with a freeze
manifest whose ``confirmatory_authorized`` is ``true``, whose
``authorized_by`` is set, and whose source hashes, function hashes,
protocol constants, seed-manifest hash and Python/dependency versions match
the running code. ``python -m om_lab.width_experiment freeze`` writes the
draft; only Lumi flips the authorisation (Section 8). This is a procedural
guard against accidental unblinding, not cryptographic blinding.

Commands (run from ``lab/``)::

    python -m om_lab.width_experiment seeds --out results/om_c001_r2/seeds.json
    python -m om_lab.width_experiment validate-certifier --out results/om_c001_r2/certifier_validation.json
    python -m om_lab.width_experiment smoke --out-dir results/om_c001_r2/smoke
    python -m om_lab.width_experiment run --split train --out-dir results/om_c001_r2 --workers 4
    python -m om_lab.width_experiment freeze --out results/om_c001_r2/freeze.json
    # after Lumi authorises freeze.json:
    python -m om_lab.width_experiment run --split test --freeze results/om_c001_r2/freeze.json --out-dir results/om_c001_r2 --workers 4
    python -m om_lab.width_experiment combine --out results/om_c001_r2/results.jsonl results/om_c001_r2/confirmatory_train_results.jsonl results/om_c001_r2/confirmatory_test_results.jsonl
    python -m om_lab.width_experiment audit --population confirmatory --splits train test results/om_c001_r2/results.jsonl
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
    Status,
    StopReason,
    Verification,
    check_sat_witness,
    solve_dpll,
    verify_cnf_assignment,
)
from om_lab.width_features import primal_min_fill_width, replay_elimination_order

EXPERIMENT = "OM-C001-R2"
RUNNER_VERSION = "1.0.0"
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
) -> tuple[dict, dict, list[str] | None]:
    """Run one instance. Returns ``(primary_record, telemetry, proof_lines)``."""
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
) -> RunOutput:
    """Run every spec and return exactly one primary record per spec, in spec order.

    ``workers=0`` runs inline in this process (no watchdog; for tests and
    debugging). ``workers>=1`` uses worker processes with a per-instance
    watchdog; infrastructure failures are rerun with the same instance and
    budget up to ``max_attempts`` times.
    """
    if len({s.instance_id for s in specs}) != len(specs):
        raise ValueError("duplicate instances in spec list")
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    faults = dict(fault_injection or {})
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
                    fault=faults.get(spec.instance_id), keep_proof=keep_proof,
                )
            except Exception as exc:  # noqa: BLE001
                record_failure(spec, attempt, "exception", f"{type(exc).__name__}: {exc}", queue)
                continue
            accept(spec, payload)
    else:
        ctx = mp.get_context("spawn")
        config = {"budget": budget, "certify": certify, "fault_injection": faults, "keep_proof": keep_proof}

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


def integrity_report(records: Sequence[dict], specs: Sequence[InstanceSpec], *, budget: int) -> dict:
    """Structural checks of a record set against its expected instances."""
    failures: list[str] = []
    ids = [r.get("instance_id") for r in records]
    expected = [s.instance_id for s in specs]
    counts = Counter(ids)
    duplicates = sorted(i for i, c in counts.items() if c > 1)
    missing = sorted(set(expected) - set(ids))
    unexpected = sorted(set(ids) - set(expected))
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
    for rec in records:
        missing_keys = RECORD_KEYS - set(rec)
        if missing_keys:
            failures.append(f"{rec.get('instance_id')}: missing keys {sorted(missing_keys)}")
            continue
        status = rec["status"]
        verification = rec["verification_status"]
        status_counts[status] += 1
        verification_counts[verification] += 1
        spec = by_spec.get(rec["instance_id"])
        if spec is not None:
            if (rec["n_vars"], rec["n_clauses"], rec["a_hundredths"], rec["index"], rec["seed"], rec["split"]) != (
                spec.n, spec.m, spec.a_hundredths, spec.index, spec.seed, spec.split
            ):
                failures.append(f"{rec['instance_id']}: identity fields differ from the seed scheme")
        if rec["integrity_alarm"]:
            alarms += 1
        if status == Status.ERROR:
            if rec["y"] is not None or rec["decisions"] is not None:
                failures.append(f"{rec['instance_id']}: ERROR record carries effort values")
            continue
        total_attempts += int(rec["decisions"])
        if rec["width_replay"] != rec["width"]:
            failures.append(f"{rec['instance_id']}: elimination-order replay width != reported width")
        if status == Status.UNKNOWN:
            if rec["satisfiable"] or not rec["timed_out"] or verification != Verification.NOT_APPLICABLE:
                failures.append(f"{rec['instance_id']}: UNKNOWN record makes a satisfiability claim")
            if rec["stop_reason"] == StopReason.DECISION_BUDGET and rec["decisions"] != budget:
                failures.append(f"{rec['instance_id']}: budget-exhausted record has D != B")
            if rec["y"] != cap:
                failures.append(f"{rec['instance_id']}: UNKNOWN record has Y != ln(1+B)")
        else:
            if rec["timed_out"] or rec["decisions"] >= budget:
                failures.append(f"{rec['instance_id']}: completed record at or over the budget")
            if rec["y"] != math.log1p(int(rec["decisions"])):
                failures.append(f"{rec['instance_id']}: Y does not equal ln(1+D)")
        if status == Status.SAT and verification != Verification.SAT_WITNESS_CHECKED:
            failures.append(f"{rec['instance_id']}: SAT record without a checked witness")
        if status == Status.UNSAT and verification == Verification.INVALID:
            failures.append(f"{rec['instance_id']}: UNSAT record with an invalid certificate")
        if bool(rec["verified"]) != (verification in Verification.CERTIFIED):
            failures.append(f"{rec['instance_id']}: verified flag inconsistent with verification_status")
    if alarms:
        failures.append(f"{alarms} record(s) carry an integrity alarm")
    n_unsat = status_counts[Status.UNSAT]
    n_unsat_certified = sum(
        1 for r in records
        if r.get("status") == Status.UNSAT
        and r.get("verification_status") in (Verification.UNSAT_PROOF_CHECKED, Verification.UNSAT_KNOWN_BY_CONSTRUCTION)
    )
    return {
        "passed": not failures,
        "failures": failures,
        "n_expected": len(expected),
        "n_records": len(records),
        "duplicates": duplicates[:20],
        "missing": missing[:20],
        "unexpected": unexpected[:20],
        "status_counts": dict(sorted(status_counts.items())),
        "verification_counts": dict(sorted(verification_counts.items())),
        "unsat_certified": n_unsat_certified,
        "unsat_total": n_unsat,
        "verification_gate_ready": n_unsat_certified == n_unsat
        and verification_counts[Verification.INVALID] == 0
        and status_counts[Status.ERROR] == 0,
        "total_branch_attempts": total_attempts,
        "max_total_branch_attempts_population": MAX_TOTAL_BRANCH_ATTEMPTS,
    }


# ---------------------------------------------------------------------------
# Freeze manifest and the confirmatory guard (Section 8)
# ---------------------------------------------------------------------------


def draft_freeze_manifest() -> dict:
    """Draft freeze manifest. ``confirmatory_authorized`` is always False here."""
    return {
        "experiment": EXPERIMENT,
        "freeze_schema_version": FREEZE_SCHEMA_VERSION,
        "runner_version": RUNNER_VERSION,
        "status": "DRAFT",
        "confirmatory_authorized": False,
        "authorized_by": None,
        "authorized_at_utc": None,
        "git": git_state(),
        "environment": environment_fingerprint(),
        "source_sha256": source_hashes(),
        "function_sha256": function_hashes(),
        "checker_sha256": checker_source_sha256(),
        "seed_manifest_sha256": seed_manifest_sha256(),
        "protocol": protocol_constants(),
        "instructions": (
            "Lumi: after approving the preregistration, set confirmatory_authorized "
            "to true, authorized_by and authorized_at_utc, set status to FROZEN, and "
            "commit this file. The runner refuses the confirmatory test split unless "
            "every hash, the protocol, Python major.minor and the pinned package "
            "versions match the running code."
        ),
    }


def check_confirmatory_authorization(freeze_path: str | os.PathLike | None) -> dict:
    """Validate a freeze manifest for the confirmatory test split, or raise."""
    if freeze_path is None:
        raise ConfirmatoryRunNotAuthorized(
            "the confirmatory test split requires --freeze with an authorised freeze manifest"
        )
    path = Path(freeze_path)
    try:
        freeze = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfirmatoryRunNotAuthorized(f"cannot read freeze manifest {path}: {exc}") from exc
    problems: list[str] = []
    if freeze.get("experiment") != EXPERIMENT:
        problems.append("experiment mismatch")
    if freeze.get("freeze_schema_version") != FREEZE_SCHEMA_VERSION:
        problems.append("freeze_schema_version mismatch")
    if freeze.get("confirmatory_authorized") is not True:
        problems.append("confirmatory_authorized is not true")
    if not isinstance(freeze.get("authorized_by"), str) or not freeze["authorized_by"].strip():
        problems.append("authorized_by is not set")
    if freeze.get("source_sha256") != source_hashes():
        problems.append("source hashes differ from the running code")
    if freeze.get("function_sha256") != function_hashes():
        problems.append("function hashes differ from the running code")
    if freeze.get("checker_sha256") != checker_source_sha256():
        problems.append("checker hash differs from the running code")
    if freeze.get("seed_manifest_sha256") != seed_manifest_sha256():
        problems.append("seed manifest hash differs")
    if freeze.get("protocol") != protocol_constants():
        problems.append("protocol constants differ from the running code")
    env_frozen = freeze.get("environment") or {}
    env_now = environment_fingerprint()
    major_minor = lambda v: ".".join(str(v).split(".")[:2])  # noqa: E731
    if major_minor(env_frozen.get("python_version")) != major_minor(env_now["python_version"]):
        problems.append("Python major.minor differs from the frozen environment")
    for dist in ("python-sat", "numpy"):
        if (env_frozen.get("packages") or {}).get(dist) != env_now["packages"].get(dist):
            problems.append(f"{dist} version differs from the frozen environment")
    if problems:
        raise ConfirmatoryRunNotAuthorized("; ".join(problems))
    return {"freeze_path": str(path), "freeze_sha256": _sha256_bytes(path.read_bytes()), "authorized_by": freeze["authorized_by"]}


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------


def write_jsonl(records: Iterable[dict], path: Path) -> str:
    """Write canonical JSON lines and return the file's SHA-256."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = "".join(canonical_json(rec) + "\n" for rec in records).encode("ascii")
    path.write_bytes(data)
    return _sha256_bytes(data)


def read_jsonl(path: str | os.PathLike) -> list[dict]:
    out: list[dict] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                out.append(json.loads(line))
    return out


def certificate_manifest(records: Sequence[dict]) -> list[dict]:
    """Section 4.1 retention: formula hash, certificate hash, checker identity, result."""
    out = []
    for rec in records:
        ref = rec.get("reference") or {}
        cert = ref.get("certificate")
        out.append(
            {
                "instance_id": rec["instance_id"],
                "formula_sha256": rec["formula_sha256"],
                "primary_status": rec["status"],
                "verification_status": rec["verification_status"],
                "reference_status": ref.get("status"),
                "certificate": cert,
            }
        )
    return out


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
    fault_injection: dict[str, dict] | None = None,
    keep_certificates: bool = False,
    dry_run: bool = False,
    command: Sequence[str] | None = None,
    progress: bool = False,
) -> dict:
    """Run one split and write its results, telemetry, certificates and manifest."""
    if population == "confirmatory":
        if budget != BUDGET_B:
            raise ValueError(f"the confirmatory budget is frozen at B={BUDGET_B}")
        if not certify:
            raise ValueError("confirmatory runs must produce certificates (Section 4.1)")
        if fault_injection:
            raise ValueError("fault injection is refused for the confirmatory population")
    authorization = None
    if population == "confirmatory" and split == "test":
        authorization = check_confirmatory_authorization(freeze_path)
    specs = build_specs(population, split, n_values=n_values, a_values=a_values, indices=indices)
    if dry_run:
        return {"dry_run": True, "n_instances": len(specs), "authorization": authorization,
                "first": specs[0].instance_id if specs else None, "last": specs[-1].instance_id if specs else None}

    started = datetime.now(timezone.utc).isoformat()

    def report(done: int, total: int) -> None:
        if progress and (done == total or done % 50 == 0):
            print(f"[{EXPERIMENT}] {population}/{split}: {done}/{total}", file=sys.stderr, flush=True)

    output = run_specs(
        specs, workers=workers, budget=budget, certify=certify, watchdog_s=watchdog_s,
        max_attempts=max_attempts, fault_injection=fault_injection,
        keep_proof=keep_certificates, progress=report,
    )
    integrity = integrity_report(output.records, specs, budget=budget)
    if not (integrity["n_records"] == integrity["n_expected"] == len(specs)) or integrity["duplicates"]:
        raise RuntimeError("one-record-per-instance invariant violated")

    out = Path(out_dir)
    stem = f"{population}_{split}"
    results_path = out / f"{stem}_results.jsonl"
    results_sha = write_jsonl(output.records, results_path)
    telemetry_path = out / f"{stem}_telemetry.jsonl"
    write_jsonl(output.telemetry + [{"failure": f} for f in output.failures], telemetry_path)
    cert_path = out / f"{stem}_certificate_manifest.json"
    cert_path.write_text(json.dumps(certificate_manifest(output.records), indent=1, sort_keys=True), encoding="utf-8")
    if keep_certificates:
        cert_dir = out / "certificates"
        cert_dir.mkdir(parents=True, exist_ok=True)
        for spec in specs:
            proof = output.proofs.get(spec.instance_id)
            if proof is None:
                continue
            inst = generate_random_3sat(n_vars=spec.n, n_clauses=spec.m, seed=spec.seed)
            stem_i = _sha256_text(spec.instance_id)[:16]
            (cert_dir / f"{stem_i}.cnf").write_text(dimacs_text(spec.n, inst.clauses), encoding="ascii")
            (cert_dir / f"{stem_i}.drat").write_text("".join(f"{line}\n" for line in proof), encoding="ascii")
    manifest = {
        "experiment": EXPERIMENT,
        "runner_version": RUNNER_VERSION,
        "record_schema_version": RECORD_SCHEMA_VERSION,
        "population": population,
        "split": split,
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
        "authorization": authorization,
        "fault_injection": sorted(fault_injection) if fault_injection else None,
        "results_file": results_path.name,
        "results_sha256": results_sha,
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
        "integrity": integrity,
        "failures": output.failures,
    }


def combine_results(
    paths: Sequence[str | os.PathLike],
    out_path: str | os.PathLike,
    *,
    population: str = "confirmatory",
    require_complete: bool = True,
) -> dict:
    """Merge split files into one analysis file with full-population accounting."""
    records: list[dict] = []
    for path in paths:
        records.extend(read_jsonl(path))
    expected = build_specs(population, "train") + build_specs(population, "test")
    present = {r["instance_id"] for r in records}
    if require_complete:
        specs = expected
    else:
        specs = [s for s in expected if s.instance_id in present]
    report = integrity_report(records, specs, budget=BUDGET_B)
    if report["duplicates"] or report["unexpected"] or (require_complete and report["missing"]):
        raise ValueError(f"cannot combine: {report['failures']}")
    order = {s.instance_id: k for k, s in enumerate(expected)}
    records.sort(key=lambda r: order[r["instance_id"]])
    out = Path(out_path)
    sha = write_jsonl(records, out)
    cert_path = out.with_name("certificate_manifest.json")
    cert_path.write_text(json.dumps(certificate_manifest(records), indent=1, sort_keys=True), encoding="utf-8")
    return {"results_path": str(out), "results_sha256": sha, "certificate_manifest_path": str(cert_path), "integrity": report}


def audit_records(
    records: Sequence[dict],
    *,
    population: str,
    splits: Sequence[str],
    recompute_features: bool = False,
    recheck_certificates: bool = False,
    drat_trim: str | None = None,
) -> dict:
    """Independent re-verification of a results file (for Lumi, Section 8).

    Always: one record per expected instance, field consistency, seed
    scheme, formula hash regenerated from the seed, SAT models re-checked
    against the regenerated formula, Y recomputed. Optionally: features
    recomputed, reference certificates regenerated and re-checked (and, with
    ``drat_trim``, also checked by DRAT-trim).
    """
    expected: list[InstanceSpec] = []
    for split in splits:
        expected.extend(build_specs(population, split))
    report = integrity_report(records, expected, budget=BUDGET_B)
    failures = list(report["failures"])
    by_id = {s.instance_id: s for s in expected}
    rechecked_certificates = 0
    drat_trim_verified = 0
    for rec in records:
        spec = by_id.get(rec.get("instance_id"))
        if spec is None or rec.get("status") == Status.ERROR:
            continue
        inst = generate_random_3sat(n_vars=spec.n, n_clauses=spec.m, seed=spec.seed)
        if rec["formula_sha256"] != _sha256_text(dimacs_text(spec.n, inst.clauses)):
            failures.append(f"{spec.instance_id}: formula hash does not match the regenerated formula")
        if rec["status"] == Status.SAT and not verify_cnf_assignment(inst.clauses, rec["model"]):
            failures.append(f"{spec.instance_id}: stored SAT model fails re-verification")
        if recompute_features:
            if primal_min_fill_width(spec.n, inst.clauses).width != rec["width"]:
                failures.append(f"{spec.instance_id}: width differs on recomputation")
            degree = extract_features_from_clauses(spec.n, inst.clauses).to_dict()["cooccurrence_degree_mean"]
            if degree != rec["degree_mean"]:
                failures.append(f"{spec.instance_id}: degree_mean differs on recomputation")
        if recheck_certificates and rec["status"] == Status.UNSAT:
            result, summary = reference_certificate(spec.n, inst.clauses)
            stored = (rec.get("reference") or {}).get("certificate") or {}
            fresh = summary.get("certificate") or {}
            if fresh.get("result") != "VALID" or fresh.get("proof_sha256") != stored.get("proof_sha256"):
                failures.append(f"{spec.instance_id}: regenerated certificate differs or is invalid")
            rechecked_certificates += 1
            if drat_trim:
                verdict = run_drat_trim(drat_trim, spec.n, inst.clauses, result.certificate["proof"])["verdict"]
                if verdict == "VERIFIED":
                    drat_trim_verified += 1
                else:
                    failures.append(f"{spec.instance_id}: DRAT-trim verdict {verdict}")
    return {
        "passed": not failures,
        "failures": failures[:200],
        "n_failures": len(failures),
        "integrity": report,
        "rechecked_certificates": rechecked_certificates,
        "drat_trim_verified": drat_trim_verified if drat_trim else None,
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

    p_freeze = sub.add_parser("freeze", help="write a DRAFT freeze manifest for Lumi")
    p_freeze.add_argument("--out", required=True)

    p_run = sub.add_parser("run", help="run one split")
    p_run.add_argument("--population", default="confirmatory", choices=POPULATIONS)
    p_run.add_argument("--split", required=True, choices=SPLITS)
    p_run.add_argument("--out-dir", required=True)
    p_run.add_argument("--workers", type=int, default=1)
    p_run.add_argument("--n-values", nargs="+")
    p_run.add_argument("--a-values", nargs="+")
    p_run.add_argument("--indices", nargs="+", help="subset of the split's indices (e.g. reruns)")
    p_run.add_argument("--budget", type=int, default=BUDGET_B, help="pilot only; frozen for confirmatory")
    p_run.add_argument("--no-certify", action="store_true", help="pilot only")
    p_run.add_argument("--watchdog-s", type=float, default=DEFAULT_WATCHDOG_S)
    p_run.add_argument("--max-attempts", type=int, default=DEFAULT_MAX_ATTEMPTS)
    p_run.add_argument("--freeze", help="authorised freeze manifest (required for the confirmatory test split)")
    p_run.add_argument("--keep-certificates", action="store_true", help="also write .cnf/.drat files")
    p_run.add_argument("--dry-run", action="store_true", help="list the instances and check authorisation only")

    p_combine = sub.add_parser("combine", help="merge split result files into results.jsonl")
    p_combine.add_argument("--out", required=True)
    p_combine.add_argument("--population", default="confirmatory", choices=POPULATIONS)
    p_combine.add_argument("--allow-partial", action="store_true")
    p_combine.add_argument("paths", nargs="+")

    p_audit = sub.add_parser("audit", help="independently re-verify a results file")
    p_audit.add_argument("path")
    p_audit.add_argument("--population", default="confirmatory", choices=POPULATIONS)
    p_audit.add_argument("--splits", nargs="+", default=["train"], choices=SPLITS)
    p_audit.add_argument("--recompute-features", action="store_true")
    p_audit.add_argument("--recheck-certificates", action="store_true")
    p_audit.add_argument("--drat-trim")
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
        print(f"Wrote DRAFT freeze manifest to {args.out} (confirmatory_authorized=false)")
        return 0
    if args.cmd == "run":
        try:
            summary = run_split(
                population=args.population, split=args.split, out_dir=args.out_dir,
                workers=args.workers, n_values=_int_list(args.n_values),
                a_values=_int_list(args.a_values), indices=_int_list(args.indices),
                budget=args.budget, certify=not args.no_certify, watchdog_s=args.watchdog_s,
                max_attempts=args.max_attempts, freeze_path=args.freeze,
                keep_certificates=args.keep_certificates, dry_run=args.dry_run,
                command=command, progress=True,
            )
        except ConfirmatoryRunNotAuthorized as exc:
            print(f"REFUSED: confirmatory test split not authorised: {exc}", file=sys.stderr)
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
        for failure in integ["failures"]:
            print(f"  - {failure}")
        print(f"results: {summary['results_path']} sha256={summary['results_sha256']}")
        print(f"manifest: {summary['run_manifest_path']}")
        return 0 if integ["passed"] else 1
    if args.cmd == "combine":
        summary = combine_results(args.paths, args.out, population=args.population, require_complete=not args.allow_partial)
        print(f"Wrote {summary['results_path']} sha256={summary['results_sha256']} integrity_passed={summary['integrity']['passed']}")
        return 0 if summary["integrity"]["passed"] else 1
    if args.cmd == "audit":
        report = audit_records(
            read_jsonl(args.path), population=args.population, splits=args.splits,
            recompute_features=args.recompute_features,
            recheck_certificates=args.recheck_certificates, drat_trim=args.drat_trim,
        )
        if args.out:
            Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print(f"audit passed={report['passed']} failures={report['n_failures']} "
              f"rechecked_certificates={report['rechecked_certificates']} drat_trim_verified={report['drat_trim_verified']}")
        for failure in report["failures"][:20]:
            print(f"  - {failure}")
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
    sys.exit(main())
