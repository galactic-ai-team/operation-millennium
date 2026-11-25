"""Empirical hardness analysis: which structural features track solver effort?

[Claim Level: Empirical Observation]

This script measures, on finite random 3-SAT instances at finite sizes
and seeds, how the structural features from ``om_lab.features`` correlate
with solver effort (DPLL decisions/propagations, PySAT decisions /
propagations / elapsed time). It does **not** prove anything about
worst-case complexity, about all ``n``, or about P vs NP. Correlation is
not causation, and a feature that tracks decisions at ``n = 30`` may not
track them at larger ``n`` or on structured (non-random) instances.

Two modes
---------
* ``--jsonl <path>`` -- read an existing harness JSONL log (e.g.
  ``results/phase_transition.jsonl``), regenerate each ``random_3sat``
  instance deterministically from its recorded ``seed`` / ``n_vars`` /
  ``n_clauses``, compute its features, and join them to the logged
  solver rows. Records that cannot be regenerated (missing seed, or a
  problem other than ``random_3sat``) are counted in ``skipped`` and
  excluded, never silently invented.
* No ``--jsonl`` -- generate a fresh sweep around the empirical
  threshold ``alpha ~ 4.26`` with :func:`run_cnf_harness`, write the
  JSONL log, then analyse it exactly as above.

PySAT conflicts
---------------
The harness JSONL schema (``lab/om_lab/harness.py``) logs PySAT
``decisions`` and ``propagations`` but **no conflict count**. In
``--jsonl`` mode conflicts are therefore reported as unavailable
(``pysat_conflicts_available: false``) rather than invented. In
generate mode this script additionally runs PySAT once per instance
directly (same clauses, ``cd195``) and records ``accum_stats()``
conflicts, so the fresh sweep *does* carry a conflict column; that
extra pass is labelled as such in the output.

DPLL decision spikes
--------------------
A "spike" is defined per solver as ``decisions`` at or above the 90th
percentile of that solver's decisions over the analysed rows. The
report compares mean feature values for spike vs non-spike rows. This
is a descriptive split, not a classifier and not a hardness proof.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import statistics

from om_lab.features import FEATURE_NAMES, extract_features_from_clauses
from om_lab.generators import CNFInstance, generate_random_3sat

CLAIM_LEVEL = "Empirical Observation"
DEFAULT_RATIOS = [3.0, 3.5, 3.8, 4.0, 4.2, 4.26, 4.4, 4.6, 5.0, 5.5]

# Features that are (near-)constant within a single sweep and therefore
# uninformative as *within-sweep* predictors, but still reported when
# they vary (e.g. across different n_vars in a merged log).
_CORRELATION_FEATURES = [f for f in FEATURE_NAMES if f not in {"n_vars"}]


def read_jsonl(path: str | Path) -> list[dict]:
    """Read harness JSONL records, skipping blank lines."""
    records: list[dict] = []
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _instance_key(record: dict) -> tuple | None:
    seed = record.get("seed")
    if not isinstance(seed, int):
        return None
    return (seed, int(record["n_vars"]), int(record["n_clauses"]))


def regenerate_instance(record: dict) -> CNFInstance | None:
    """Regenerate the instance behind a harness record, or None.

    Only ``random_3sat`` records carry enough information in the JSONL
    schema (seed + n_vars + n_clauses) to be regenerated exactly.
    """
    if record.get("problem") != "random_3sat":
        return None
    key = _instance_key(record)
    if key is None:
        return None
    seed, n_vars, n_clauses = key
    return generate_random_3sat(
        n_vars=n_vars, n_clauses=n_clauses, seed=seed
    )


def join_features(
    records: list[dict],
) -> tuple[list[dict], dict[str, int]]:
    """Attach structural features to each regenerable harness record.

    Returns ``(rows, counts)`` where each row is the original record
    plus a ``features`` dict, and ``counts`` reports how many records
    were joined vs skipped (and why).
    """
    cache: dict[tuple, dict] = {}
    rows: list[dict] = []
    counts = {"total": len(records), "joined": 0, "skipped_no_seed": 0,
              "skipped_other_problem": 0}
    for record in records:
        inst = regenerate_instance(record)
        if inst is None:
            if record.get("problem") != "random_3sat":
                counts["skipped_other_problem"] += 1
            else:
                counts["skipped_no_seed"] += 1
            continue
        key = _instance_key(record)
        assert key is not None
        if key not in cache:
            cache[key] = extract_features_from_clauses(
                inst.n_vars, inst.clauses
            ).to_dict()
        row = dict(record)
        row["features"] = cache[key]
        rows.append(row)
        counts["joined"] += 1
    counts["distinct_instances"] = len(cache)
    return rows, counts


def pearson(xs: list[float], ys: list[float]) -> float | None:
    """Pearson r, or None when undefined (n < 3 or zero variance)."""
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = math.sqrt(
        sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)
    )
    return num / den if den > 0 else None


def _ranks(values: list[float]) -> list[float]:
    """Average ranks (1-based) with ties averaged, as in Spearman."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1
    return ranks


def spearman(xs: list[float], ys: list[float]) -> float | None:
    """Spearman rank correlation, or None when undefined."""
    if len(xs) < 3:
        return None
    return pearson(_ranks(xs), _ranks(ys))


def _percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    k = (len(ordered) - 1) * pct / 100.0
    lo, hi = int(math.floor(k)), int(math.ceil(k))
    if lo == hi:
        return ordered[lo]
    return ordered[lo] * (hi - k) + ordered[hi] * (k - lo)


def correlation_table(
    rows: list[dict], solver_prefix: str, target: str
) -> list[dict]:
    """Rank features by |Spearman r| against one solver/target.

    ``target`` is a row key (``decisions``, ``propagations``,
    ``elapsed_s``) or ``conflicts`` (generate mode only). Decision /
    propagation / conflict targets use ``log1p`` because solver effort
    is heavy-tailed; ``elapsed_s`` is used raw and is timing-noise
    sensitive at small ``n`` -- see Limitations in the output.
    """
    group = [r for r in rows if str(r.get("solver", "")).startswith(solver_prefix)]
    if len(group) < 3:
        return []
    if target == "elapsed_s":
        ys = [float(r["elapsed_s"]) for r in group]
    else:
        ys = [math.log1p(float(r.get(target, 0) or 0)) for r in group]
    out: list[dict] = []
    for name in _CORRELATION_FEATURES:
        xs = [float(r["features"][name]) for r in group]
        r_pearson = pearson(xs, ys)
        r_spearman = spearman(xs, ys)
        if r_pearson is None and r_spearman is None:
            continue
        out.append(
            {
                "feature": name,
                "n": len(group),
                "pearson": r_pearson,
                "spearman": r_spearman,
            }
        )
    out.sort(key=lambda d: abs(d["spearman"] or 0.0), reverse=True)
    return out


def per_ratio_summary(rows: list[dict]) -> list[dict]:
    """Median solver effort and SAT fraction per clause ratio."""
    by_ratio: dict[float, list[dict]] = {}
    for row in rows:
        by_ratio.setdefault(float(row["ratio"]), []).append(row)
    summary: list[dict] = []
    for ratio in sorted(by_ratio):
        group = by_ratio[ratio]
        dpll = [r for r in group if r.get("solver") == "dpll"]
        pysat = [r for r in group if str(r.get("solver", "")).startswith("pysat")]
        summary.append(
            {
                "ratio": ratio,
                "n_instances": len({(r.get("seed"), r.get("n_vars")) for r in group}),
                "sat_fraction": (
                    statistics.fmean([1.0 if r["satisfiable"] else 0.0 for r in pysat])
                    if pysat
                    else None
                ),
                "dpll_median_decisions": (
                    statistics.median([r["decisions"] for r in dpll]) if dpll else None
                ),
                "dpll_median_propagations": (
                    statistics.median([r["propagations"] for r in dpll]) if dpll else None
                ),
                "pysat_median_decisions": (
                    statistics.median([r["decisions"] for r in pysat]) if pysat else None
                ),
                "pysat_median_propagations": (
                    statistics.median([r["propagations"] for r in pysat]) if pysat else None
                ),
                "pysat_zero_decision_fraction": (
                    statistics.fmean([1.0 if r["decisions"] == 0 else 0.0 for r in pysat])
                    if pysat
                    else None
                ),
            }
        )
    return summary


def spike_comparison(rows: list[dict], solver_prefix: str) -> dict | None:
    """Mean feature values for decision-spike vs non-spike rows."""
    group = [r for r in rows if str(r.get("solver", "")).startswith(solver_prefix)]
    if len(group) < 10:
        return None
    threshold = _percentile([float(r["decisions"]) for r in group], 90.0)
    spikes = [r for r in group if float(r["decisions"]) >= threshold]
    rest = [r for r in group if float(r["decisions"]) < threshold]
    if not spikes or not rest:
        return None
    diffs = []
    for name in _CORRELATION_FEATURES:
        spike_vals = [r["features"][name] for r in spikes]
        rest_vals = [r["features"][name] for r in rest]
        spike_mean = statistics.fmean(spike_vals)
        rest_mean = statistics.fmean(rest_vals)
        # Standardised difference, so features on different scales
        # (e.g. n_clauses ~ 128 vs a fraction ~ 0.3) can be compared.
        pooled = statistics.pstdev(spike_vals + rest_vals)
        diffs.append(
            {
                "feature": name,
                "spike_mean": spike_mean,
                "non_spike_mean": rest_mean,
                "difference": spike_mean - rest_mean,
                "standardised_difference": (
                    (spike_mean - rest_mean) / pooled if pooled > 0 else 0.0
                ),
            }
        )
    diffs.sort(key=lambda d: abs(d["standardised_difference"]), reverse=True)
    return {
        "solver": solver_prefix,
        "threshold_decisions": threshold,
        "n_spike": len(spikes),
        "n_non_spike": len(rest),
        "feature_mean_differences": diffs,
    }


def _pysat_conflicts_map(instances: list[CNFInstance]) -> dict[tuple, int]:
    """Direct PySAT ``accum_stats`` conflicts per instance (generate mode).

    The harness does not log conflicts, so this is a separate,
    explicitly labelled pass over the same clauses. Returns a map
    ``(seed, n_vars, n_clauses) -> conflicts``; empty on import error.
    """
    try:
        from pysat.solvers import Solver as PySATSolver
    except ImportError:
        return {}
    out: dict[tuple, int] = {}
    for inst in instances:
        seed = inst.metadata.get("seed")
        if not isinstance(seed, int):
            continue
        with PySATSolver(name="cd195", bootstrap_with=inst.clauses) as solver:
            solver.solve()
            stats = solver.accum_stats() if hasattr(solver, "accum_stats") else {}
        out[(seed, inst.n_vars, inst.n_clauses)] = int(stats.get("conflicts", 0))
    return out


def generate_fresh_sweep(
    n_vars: int,
    trials: int,
    ratios: list[float],
    base_seed: int,
    out_dir: str | Path,
):
    """Run a fresh sweep, log JSONL, and return (records, conflicts_map)."""
    # Imported lazily so ``--jsonl`` mode does not need the solver stack.
    from om_lab.harness import run_cnf_harness, write_jsonl
    from om_lab.solvers import solve_dpll, solve_pysat

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    all_records = []
    instances: list[CNFInstance] = []
    for r_idx, ratio in enumerate(ratios):
        n_clauses = max(1, round(ratio * n_vars))
        batch = [
            generate_random_3sat(
                n_vars=n_vars,
                n_clauses=n_clauses,
                seed=base_seed + r_idx * 10_000 + t,
            )
            for t in range(trials)
        ]
        instances.extend(batch)
        all_records.extend(
            run_cnf_harness(
                batch,
                solvers=[
                    lambda n, c: solve_pysat(n, c, solver_name="cd195"),
                    lambda n, c: solve_dpll(n, c),
                ],
            )
        )
    jsonl_path = write_jsonl(all_records, out_path / "hardness.jsonl")
    records = read_jsonl(jsonl_path)
    return records, _pysat_conflicts_map(instances), jsonl_path


def analyze_records(
    records: list[dict],
    conflicts_map: dict[tuple, int] | None = None,
    source: str = "",
) -> dict:
    """Full empirical analysis of (already-read) harness records."""
    rows, counts = join_features(records)
    if conflicts_map:
        for row in rows:
            key = _instance_key(row)
            if key is not None and key in conflicts_map:
                row["conflicts"] = conflicts_map[key]
    has_conflicts = any("conflicts" in r for r in rows)
    pysat_rows = [r for r in rows if str(r.get("solver", "")).startswith("pysat")]
    dpll_rows = [r for r in rows if r.get("solver") == "dpll"]

    correlations: dict[str, list[dict]] = {}
    for solver_prefix, targets in [
        ("dpll", ["decisions", "propagations", "elapsed_s"]),
        ("pysat", ["decisions", "propagations", "elapsed_s"]),
    ]:
        for target in targets:
            correlations[f"{solver_prefix}:{target}"] = correlation_table(
                rows, solver_prefix, target
            )
    if has_conflicts:
        correlations["pysat:conflicts"] = correlation_table(
            rows, "pysat", "conflicts"
        )

    # Near-transition check: the across-ratio correlations above are
    # dominated by alpha itself (at fixed n, alpha, n_clauses, and
    # var_occurrence_mean are the same quantity up to a constant).
    # Restricting to 4.0 <= alpha <= 4.6 asks the sharper question:
    # at (nearly) fixed clause density, does any *other* structural
    # feature still track solver effort?
    near = [r for r in rows if 4.0 <= float(r["ratio"]) <= 4.6]
    near_transition: dict[str, list[dict]] = {}
    for solver_prefix, targets in [
        ("dpll", ["decisions", "propagations"]),
        ("pysat", ["decisions", "propagations"]),
    ]:
        for target in targets:
            near_transition[f"{solver_prefix}:{target}"] = correlation_table(
                near, solver_prefix, target
            )
    if has_conflicts:
        near_transition["pysat:conflicts"] = correlation_table(
            near, "pysat", "conflicts"
        )

    return {
        "claim_level": CLAIM_LEVEL,
        "source": source,
        "scope": (
            "Random 3-SAT only, finite n and seeds (see reproducibility). "
            "Correlations are descriptive; they do not establish causation, "
            "do not generalise to structured instances, and say nothing "
            "about worst-case complexity or P vs NP."
        ),
        "counts": counts,
        "n_rows_analysed": len(rows),
        "n_dpll_rows": len(dpll_rows),
        "n_pysat_rows": len(pysat_rows),
        "pysat_conflicts_available": has_conflicts,
        "pysat_zero_decision_fraction": (
            statistics.fmean([1.0 if r["decisions"] == 0 else 0.0 for r in pysat_rows])
            if pysat_rows
            else None
        ),
        "per_ratio": per_ratio_summary(rows),
        "correlations": correlations,
        "near_transition_correlations": near_transition,
        "near_transition_n_rows": len(near),
        "spikes": [
            s
            for s in (
                spike_comparison(rows, "dpll"),
                spike_comparison(rows, "pysat"),
            )
            if s is not None
        ],
        "limitations": [
            "Across-ratio correlations are dominated by alpha itself: "
            "at fixed n, alpha, n_clauses, and var_occurrence_mean are "
            "the same quantity up to a constant, so they cannot be "
            "separated in a sweep that varies alpha. See the "
            "near-transition (4.0 <= alpha <= 4.6) table for the "
            "fixed-density check.",
            "PySAT decisions/propagations are 0 on many easy (low-alpha) "
            "instances that CaDiCaL solves without branching; that floor "
            "effect attenuates PySAT correlations at low alpha.",
            "Elapsed-time correlations are timing-noise sensitive at "
            "n <= 50; prefer decisions/propagations over elapsed_s.",
            "Features are computed from the formula alone; solver "
            "heuristics, restarts, and learned clauses are not features.",
            "No backbone is computed here: unit_clause_fraction and "
            "pure_literal_fraction are structural proxies, not backbones.",
        ],
    }


def _print_report(summary: dict) -> None:
    print(f"[Claim Level: {summary['claim_level']}]")
    print(f"Source: {summary['source']}")
    print(
        f"Rows analysed: {summary['n_rows_analysed']} "
        f"(DPLL {summary['n_dpll_rows']}, PySAT {summary['n_pysat_rows']}) "
        f"from {summary['counts'].get('distinct_instances')} distinct instances; "
        f"skipped: {summary['counts']['skipped_no_seed']} no-seed, "
        f"{summary['counts']['skipped_other_problem']} other-problem."
    )
    if summary["pysat_zero_decision_fraction"] is not None:
        print(
            "PySAT rows with 0 decisions: "
            f"{summary['pysat_zero_decision_fraction']:.2f} "
            "(CaDiCaL solves many easy instances without branching)."
        )
    print("PySAT conflicts available: "
          f"{summary['pysat_conflicts_available']} "
          "(False in --jsonl mode: the harness JSONL has no conflict field.)")
    print("\nPer-ratio summary (median decisions):")
    for s in summary["per_ratio"]:
        print(
            f"  alpha={s['ratio']:4.2f}  P(SAT)={s['sat_fraction'] if s['sat_fraction'] is None else round(s['sat_fraction'], 2)}  "
            f"DPLL med_dec={s['dpll_median_decisions']}  "
            f"PySAT med_dec={s['pysat_median_decisions']}  "
            f"PySAT zero-dec frac={s['pysat_zero_decision_fraction']:.2f}"
            if s["pysat_zero_decision_fraction"] is not None
            else f"  alpha={s['ratio']:4.2f}"
        )
    print("\nTop features by |Spearman r| (log1p target, unless elapsed_s):")
    for key, table in summary["correlations"].items():
        top = table[:5]
        if not top:
            print(f"  {key}: n < 3 or no varying feature -- no correlation computed")
            continue
        print(f"  {key}:")
        for entry in top:
            print(
                f"    {entry['feature']:32s} "
                f"Spearman={entry['spearman']:+.3f}  Pearson={entry['pearson']:+.3f}  n={entry['n']}"
            )
    print("\nNear-transition correlations (4.0 <= alpha <= 4.6 only):")
    for key, table in summary["near_transition_correlations"].items():
        top = table[:3]
        if not top:
            print(f"  {key}: no correlation computed")
            continue
        print(f"  {key} (n_rows in band: {summary['near_transition_n_rows']}):")
        for entry in top:
            print(
                f"    {entry['feature']:32s} "
                f"Spearman={entry['spearman']:+.3f}  Pearson={entry['pearson']:+.3f}  n={entry['n']}"
            )
    print("\nDecision spikes (>= 90th percentile per solver):")
    for spike in summary["spikes"]:
        print(
            f"  {spike['solver']}: threshold={spike['threshold_decisions']:.0f} "
            f"decisions, n_spike={spike['n_spike']}, n_non_spike={spike['n_non_spike']}"
        )
        for d in spike["feature_mean_differences"][:5]:
            print(
                f"    {d['feature']:32s} spike_mean={d['spike_mean']:.3f} "
                f"non_spike_mean={d['non_spike_mean']:.3f} diff={d['difference']:+.3f} "
                f"std_diff={d['standardised_difference']:+.2f}"
            )
    print("\nLimitations (see JSON for the full list):")
    for item in summary["limitations"]:
        print(f"  - {item}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Empirical hardness analysis. [Claim Level: Empirical Observation] "
            "Correlates CNF structural features with solver effort around "
            "alpha ~ 4.26. No proof claims are made."
        )
    )
    parser.add_argument(
        "--jsonl", type=str, default=None,
        help="Existing harness JSONL log to analyse (default: generate a fresh sweep).",
    )
    parser.add_argument("--n-vars", type=int, default=30)
    parser.add_argument("--trials", type=int, default=20)
    parser.add_argument(
        "--ratios", type=float, nargs="+", default=list(DEFAULT_RATIOS),
        help="Clause/variable ratios for a fresh sweep.",
    )
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--out-dir", type=str, default="results")
    parser.add_argument(
        "--out-json", type=str, default=None,
        help="Where to write the JSON summary (default: <out-dir>/hardness_analysis.json).",
    )
    args = parser.parse_args()

    if args.jsonl:
        records = read_jsonl(args.jsonl)
        summary = analyze_records(records, source=f"jsonl:{args.jsonl}")
        summary["reproducibility"] = {
            "input_jsonl": args.jsonl,
            "note": "Instances regenerated from recorded seed/n_vars/n_clauses.",
        }
    else:
        records, conflicts_map, jsonl_path = generate_fresh_sweep(
            n_vars=args.n_vars,
            trials=args.trials,
            ratios=args.ratios,
            base_seed=args.seed,
            out_dir=args.out_dir,
        )
        summary = analyze_records(
            records, conflicts_map=conflicts_map,
            source=f"fresh sweep -> {jsonl_path}",
        )
        summary["reproducibility"] = {
            "n_vars": args.n_vars,
            "trials": args.trials,
            "ratios": args.ratios,
            "base_seed": args.seed,
            "jsonl": str(jsonl_path),
            "solver": "pysat:cd195 + dpll (om_lab.harness)",
        }
        print(f"Wrote JSONL log: {jsonl_path}")

    out_json = Path(args.out_json) if args.out_json else Path(args.out_dir) / "hardness_analysis.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _print_report(summary)
    print(f"\nWrote JSON summary: {out_json}")


if __name__ == "__main__":
    main()
