# Phase 2 Laboratory (`om_lab`)

Reproducible Python laboratory for generating NP-complete problem instances, running exact SAT solvers (PySAT CDCL and an instrumented pure-Python DPLL baseline), verifying witnesses, and studying empirical phase transitions.

> **Honesty Rule reminder:** Empirical hardness peaks and solver timings are `[Claim Level: Empirical Observation]` only. They are never proofs of worst-case complexity separations.

## Setup (Free, Local)

```bash
cd lab
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run Tests

```bash
pytest
```

## Run the Random 3-SAT Phase Transition Experiment

Sweeps clause-to-variable ratio $\alpha = m / n$ around the empirical threshold $\alpha_c \approx 4.26$ (Mitchell, Selman, & Levesque, 1992), logs per-trial JSONL results, and writes a two-panel plot to `lab/results/phase_transition.png`:

```bash
python -m om_lab.phase_transition --n-vars 30 --trials 25 --out-dir results
```

## Structural Features & Hardness Analysis

`om_lab.features` computes deterministic structural features of a CNF
instance (clause/variable ratio, literal polarity balance, variable
occurrence degree distribution / entropy, unit-clause density,
variable co-occurrence graph degree stats, and more). It computes no
backbone -- a backbone requires solving; unit-clause density is the
structural proxy included instead.

`om_lab.analyze_hardness` joins those features to harness JSONL logs
(regenerating each `random_3sat` instance from its recorded seed) and
reports Pearson / Spearman correlations with DPLL and PySAT solver
effort around α ≈ 4.26, plus a per-ratio summary and a 90th-percentile
decision-spike comparison:

```bash
# Fresh sweep (default: n=30, 20 trials/ratio, seed 2026)
python -m om_lab.analyze_hardness --out-dir results

# Analyse an existing log instead
python -m om_lab.analyze_hardness --jsonl results/phase_transition.jsonl --out-dir results
```

> **Honesty Rule reminder:** all output of `analyze_hardness` is
> `[Claim Level: Empirical Observation]` only -- finite instances,
> finite seeds, correlation is not causation, and nothing here is a
> proof about worst-case complexity. PySAT conflict counts are *not*
> in the harness JSONL schema, so `--jsonl` mode reports them as
> unavailable; the fresh-sweep mode records them via a separate,
> labelled direct-PySAT pass.

## Phase 3: Primal Min-Fill Width & OM-C001-R2 Prediction Analysis

`om_lab.width_features` implements the deterministic primal-graph
min-fill elimination width from Section 3.3 of
`docs/phase3/DISCOVERY_ROUND_01.md` (preregistration OM-C001-R2),
with an independent elimination-order replay.

`om_lab.analyze_width` implements the frozen prediction analysis
from Section 3 of that document exactly: models M0 (per-cell mean)
and M1 (per-cell mean + one shared within-cell slope on width),
degree-adjusted secondaries M2/M3, and the paired stratified
bootstrap (10,000 replicates, seed 9012026). It writes
`width_analysis.json`, `primary_result.json` (one machine-readable
disposition: PASS / FAIL / INCONCLUSIVE), `per_cell.csv`, and
per-cell plots.

```bash
# Validate the machinery on a small pilot population (pilot seeds --
# never the confirmatory seeds)
python -m om_lab.analyze_width --pilot --out-dir results/width-pilot

# Analyse runner records (Claude's frozen runner) once Lumi has
# authorised confirmatory execution
python -m om_lab.analyze_width --records results.jsonl --population confirmatory --out-dir results/width
```

> **Freeze warning:** the confirmatory population (Section 3.5,
> seed material `OM-C001-R2|n|A|i`) must only be run after Lumi
> freezes the implementation and authorises confirmatory execution.
> This script has no confirmatory-generation mode. A pilot or
> synthetic run is INCONCLUSIVE as a primary disposition by
> construction. UNSAT rows without a proof certificate fail the
> verification gate (Section 4.1); solver agreement alone is not
> proof evidence.
