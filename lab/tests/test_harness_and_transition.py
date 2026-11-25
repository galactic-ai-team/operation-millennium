import json
from pathlib import Path

from om_lab.generators import generate_random_3sat
from om_lab.harness import run_cnf_harness, write_jsonl
from om_lab.phase_transition import run_phase_transition


def test_harness_and_jsonl(tmp_path: Path):
    instances = [generate_random_3sat(12, 51, seed=i) for i in range(4)]
    records = run_cnf_harness(instances)
    assert len(records) == 8  # 4 instances * 2 solvers
    assert all(rec.verified for rec in records)

    log_path = write_jsonl(records, tmp_path / "run.jsonl")
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 8
    parsed = json.loads(lines[0])
    assert parsed["problem"] == "random_3sat"
    assert "elapsed_s" in parsed


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
