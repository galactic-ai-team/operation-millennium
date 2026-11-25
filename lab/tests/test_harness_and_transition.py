import json
from pathlib import Path

import pytest

from om_lab.generators import generate_random_3sat
from om_lab.harness import InvalidWitnessError, run_cnf_harness, write_jsonl
from om_lab.phase_transition import run_phase_transition
from om_lab.solvers import SolveResult, Status, StopReason, Verification, solve_dpll


def test_harness_and_jsonl(tmp_path: Path):
    instances = [generate_random_3sat(12, 51, seed=i) for i in range(4)]
    records = run_cnf_harness(instances)
    assert len(records) == 8  # 4 instances * 2 solvers
    # Strict semantics: SAT claims carry checked witnesses; UNSAT claims made
    # without a certificate are logged as UNVERIFIED, not hidden or relabelled.
    for rec in records:
        assert rec.status in {Status.SAT, Status.UNSAT}
        if rec.status == Status.SAT:
            assert rec.verified
            assert rec.verification_status == Verification.SAT_WITNESS_CHECKED
        else:
            assert not rec.verified
            assert rec.verification_status == Verification.UNVERIFIED

    log_path = write_jsonl(records, tmp_path / "run.jsonl")
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 8
    parsed = json.loads(lines[0])
    assert parsed["problem"] == "random_3sat"
    assert "elapsed_s" in parsed
    assert {"status", "verification_status", "timed_out", "stop_reason"} <= set(parsed)


def test_harness_logs_budget_exhaustion_as_unknown():
    """Section 4.2: budget exhaustion is a valid logged observation."""
    instances = [generate_random_3sat(40, 170, seed=11)]
    records = run_cnf_harness(
        instances, solvers=[lambda n, c: solve_dpll(n, c, max_decisions=2)]
    )
    assert len(records) == 1
    rec = records[0]
    assert rec.status == Status.UNKNOWN
    assert rec.timed_out
    assert rec.stop_reason == StopReason.DECISION_BUDGET
    assert not rec.satisfiable and not rec.verified
    assert rec.decisions == 2


def test_harness_rejects_invalid_sat_witness():
    def broken_solver(n, clauses):
        return SolveResult(
            solver_name="broken", satisfiable=True, model=[-1, -2], elapsed_s=0.0,
            decisions=0, propagations=0, verified=False,
            verification_status=Verification.INVALID,
        )

    with pytest.raises(InvalidWitnessError):
        run_cnf_harness([generate_random_3sat(12, 30, seed=0)], solvers=[broken_solver])


def test_phase_transition_smoke(tmp_path: Path):
    summaries, jsonl_path, plot_path = run_phase_transition(
        n_vars=18,
        trials=5,
        ratios=[2.5, 4.26, 6.0],
        base_seed=100,
        out_dir=tmp_path,
    )
    assert len(summaries) == 3
    assert summaries[0].sat_fraction >= summaries[-1].sat_fraction
    assert jsonl_path.exists() and jsonl_path.stat().st_size > 0
    assert plot_path.exists() and plot_path.stat().st_size > 1000
