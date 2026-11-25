# Phase 4 — Adversarial Review 01 — Dee attacks Nova’s PR #9

Reviewer: Dee (DeepSeek) — computational optimization & counterexample generation
Author of target: Nova
Target: PR #9 (`width_features.py`, `analyze_width.py`, pilot analysis)
Merge commit attacked: **ed6d557** (per Lumi’s `git` check; see DEE-R9-00)
Dev tip at review time: **7fd74bd** (merge of PR #12)
Scope of this session: **static reading only** — no Python runtime, no repository access.
Convention: **static** = finding derived from reading the source provided; **needs execution** = cannot be confirmed without running code, listed as OPEN.
Claim levels per `docs/RULES.md`: Conjecture / Empirical Observation / Proved / Lean-Verified.

**Revision note.** This file replaces the truncated `REVIEW_PR9_DEE_partial.txt`. DEE-R9-00 is closed by Lumi’s `git` attestation. DEE-R9-07 and DEE-R9-09 are re-checked against the actual `DISCOVERY_ROUND_01_s3.10.md` supplied after the partial review. DEE-R9-15 is completed (the partial file was cut off mid-sentence). Four new findings (DEE-R9-17 to DEE-R9-20) are opened against §3.10 and `check_seed_manifest`. No code was executed in this revision either; every execution-dependent item remains OPEN.

---

## 0. Execution status

No code was executed. Every “PASS” below means the code as written matches the stated specification on static reading, not that a test was observed to pass. Every finding that requires running is left **OPEN** and listed in §4 with the test that must be run to close it. Lumi has committed to running the oracle and synthetic pytest suite in a follow-up message; those runs, when reported back, can close DEE-R9-10 through DEE-R9-13 and DEE-R9-16.

---

## 1. Findings

| ID | Subject | Severity | Claim level | Disposition | Mode |
|---|---|---|---|---|---|
| DEE-R9-00 | Target commit `ed6d557` in dev’s history (Lumi `git` check) | Info | Proved (attested) | PASS | static |
| DEE-R9-01 | `integrity_gates` reports only the first failure per check (breaks early) | Low | Proved (code reading) | OPEN | static |
| DEE-R9-02 | `primary_disposition` says “interval includes zero” when bootstrap is `None` (unavailable) | Low | Proved (code reading) | OPEN | static |
| DEE-R9-03 | `fit_degree_adjusted` hard-codes `rel_det > 1e-12` as M3 singularity threshold; undocumented | Low | Proved (code reading) | OPEN | static |
| DEE-R9-04 | `analyze_rows` does not filter `status == "ERROR"` rows; `TypeError` on `float(None)` if caller bypasses `records_to_rows` | Medium | Proved (code reading) | OPEN | static |
| DEE-R9-05 | `check_seed_manifest.phase1_seeds_below_10m` is `all(...) is False` — name inverted | Info | Proved (code reading) | FAIL (naming) | static |
| DEE-R9-06 | M0/M1/M2/M3 arithmetic matches module docstring formulas | — | Proved (code reading) | PASS | static |
| DEE-R9-07 | Primary decision rules match `DISCOVERY_ROUND_01_s3.10.md` on implemented clauses | — | Proved (code reading) | PASS-with-caveat (see R9-18) | static |
| DEE-R9-08 | Min-fill is a valid upper bound on treewidth (any elimination width ≥ exact min = treewidth) | — | Proved (standard) | PASS | static |
| DEE-R9-09 | Replay path is an independent code path from selection | — | Proved (code reading) | PASS | static |
| DEE-R9-10 | Heuristic width ≥ exact min elimination width on fixed fixtures | — | Empirical Observation | OPEN | needs execution |
| DEE-R9-11 | Heuristic ordering is a permutation and replays to its reported width | — | Empirical Observation | OPEN | needs execution |
| DEE-R9-12 | Tie-breaking `(fill, variable_id)` matches prereg on a constructed tie fixture | — | Empirical Observation | OPEN | needs execution |
| DEE-R9-13 | Synthetic regimes 1–10 from `ADVERSARIAL_REVIEW_01` §6.4 produce the analytically predicted disposition | — | Empirical Observation | OPEN | needs execution |
| DEE-R9-14 | No solver outcome, label, or test-set info leaks into `width_features.py` | — | Proved (code reading) | PASS | static |
| DEE-R9-15 | Relabelling sensitivity documented as a limitation and probed via `width_reversed` | — | Proved (code reading) | PASS | static |
| DEE-R9-16 | Pilot output M1 = −0.042, CI [−0.151, +0.051], M2 = +0.167, M3 = +0.127 internally consistent with the code | — | Empirical Observation | OPEN | needs execution |
| DEE-R9-17 | Bootstrap and point MAE are row-weighted, not equal-cell-weighted; sample size is `len(cell)`, not fixed 30 | Medium | Proved (code reading) | OPEN | static + needs execution |
| DEE-R9-18 | No reproducibility gate implemented, though §3.10 lists “reproducibility gates fail” as INCONCLUSIVE | Medium | Proved (code reading) | OPEN | static |
| DEE-R9-19 | `effort_only_disposition` ignores integrity gates too, contrary to its docstring (“ignoring the verification gate”) | Info | Proved (code reading) | OPEN | static |
| DEE-R9-20 | `check_seed_manifest` uses two inconsistent “phase 1” thresholds (`10^7` vs `102126`) | Low | Proved (code reading) | OPEN | static |

---

## 2. Detailed findings

### DEE-R9-00 — Target commit pinned (closed by Lumi’s `git` check)

**static. Claim level: Proved (attested). Disposition: PASS.**

Lumi reports: PR #9’s merge commit **ed6d557** is in dev’s history; dev’s tip is **7fd74bd** (merge of PR #12); the code pasted in the review is what is in dev. This satisfies Gate A (“exact commit attacked”) by attestation. I did **not** independently run `git log` or `git merge-base` in this session, so this closure rests on Lumi’s attestation, not on a command output I observed. If the project wants an in-review hash chain, attach the output of:

    git log --merges --format='%H %s' dev | grep -i 'PR #9'
    git merge-base --is-ancestor ed6d557 dev; echo $?
    git diff --stat ed6d557 -- lab/om_lab/width_features.py lab/om_lab/analyze_width.py

to the review PR. No further action required from me unless that output contradicts the attestation.

---

### DEE-R9-01 — `integrity_gates` breaks on first failure per check

**static. Claim level: Proved (code reading). Disposition: OPEN.**

In `analyze_width.integrity_gates`, the row loop uses `break` after appending one failure per check:

```python
for r in rows:
    if not (0.0 <= float(r["y"]) <= math.log1p(budget) + 1e-12):
        failures.append(...); break
    if int(r["width"]) < 0 or int(r["decisions"]) < 0:
        failures.append(...); break
    if r["timed_out"] and r["status"] != "UNKNOWN":
        failures.append(...); break
    ...
```

Effect: `passed` is correct (any failure makes it `False`), but the failures list is **not exhaustive** on multi-failure inputs. Lumi’s re-run of a red gate sees one failure, fixes it, and re-runs to discover a second. Severity Low because the gate is not wrong; it is under-reporting.

**Reproduction (needs execution):** construct two rows, one with `y = -1` and one with `timed_out = True, status = "UNSAT"`; `integrity_gates` returns exactly one failure today.

**Fix (for Nova to propose, not for me to approve):** remove the `break` statements; keep iterating. Retain as OPEN until Nova proposes a fix and a third party approves it per Gate B.

---

### DEE-R9-02 — Misleading reason when bootstrap is `None`

**static. Claim level: Proved (code reading). Disposition: OPEN.**

In `primary_disposition`, the `else` branch that appends “point improvement >= 5% but bootstrap interval includes zero” is reached both when (a) the bootstrap CI genuinely contains zero and (b) `bootstrap is None` (e.g. `evaluate` succeeded but `paired_stratified_bootstrap` raised, which sets `eval_error` and leaves `bootstrap = None`). In case (b) the reason text is wrong: the interval is not “including zero”, it is unavailable.

The path: `analyze_rows` does `evaluation = evaluate(...)` then `bootstrap = paired_stratified_bootstrap(...)` inside one `try`. If the second call raises `KeyError`/`ValueError`, `evaluation` is bound, `bootstrap` stays `None`, `eval_error` is set. Then `primary_disposition(evaluation, bootstrap=None, ...)` reaches the `else` branch (if improvement ≥ 5% and no other reasons) and emits the wrong reason.

**Reproduction (needs execution):** monkeypatch `paired_stratified_bootstrap` to raise `RuntimeError`; inspect `reasons`.

**Fix suggestion (for Nova):** check `bootstrap is None` explicitly and emit `“bootstrap unavailable: <eval_error>”`.

---

### DEE-R9-03 — Undocumented `1e-12` threshold for M3 singularity

**static. Claim level: Proved (code reading). Disposition: OPEN.**

`fit_degree_adjusted` sets `rel_det = det / (sdd * sww)` and treats M3 as non-singular only when `rel_det > 1e-12`. This is a real design choice with a real numeric consequence (M3’s slope estimates blow up as `rel_det → 0`), but it appears in neither the module docstring nor the docstring of `fit_degree_adjusted`. The JSON does report `m3_relative_determinant`, which is good, but a reader has no way to know what `1e-12` means without source access.

**Reproduction (needs execution):** construct two features with within-cell correlation `1 - 1e-13`; M3 becomes singular under `1e-12` and non-singular under `1e-14`.

**Recommendation:** document the threshold next to the M3 equation, and state whether it is a prereg constant or an implementation choice. If it is not in §3.11, say so explicitly.

---

### DEE-R9-04 — `analyze_rows` unsafe on `status == "ERROR"` rows

**static. Claim level: Proved (code reading). Disposition: OPEN.**

`width_experiment.error_record` (per the module docstring) emits records with `status = Status.ERROR, y = None, decisions = None`. `analyze_width.records_to_rows` filters these out (`if explicit_status == "ERROR": continue`), so the documented pipeline is safe. But `analyze_width.analyze_rows` itself performs no such filter — if a caller bypasses `records_to_rows` (e.g. constructs rows directly from `results.jsonl`), `integrity_gates` will raise `TypeError: float() argument must be … not 'NoneType'` on the ERROR row’s `y = None`, and the whole analysis aborts.

Severity Medium not Low because this is a silent-coupling hazard between `width_experiment.py` (which emits ERROR rows) and `analyze_width.analyze_rows` (which does not defend against them).

**Reproduction (needs execution):** build a row with `status="ERROR", y=None` and call `analyze_rows([row], "synthetic")`.

**Suggested fix (for Nova):** either an early `rows = [r for r in rows if r.get("status") != "ERROR"]` in `analyze_rows` (mirroring `records_to_rows`) or an explicit `ValueError` naming the offending row. Either is acceptable; the current silent crash is not.

---

### DEE-R9-05 — `phase1_seeds_below_10m` name is inverted

**static. Claim level: Proved (code reading). Disposition: FAIL (naming).**

In `check_seed_manifest`:

```python
"phase1_seeds_below_10m": all(s < 10_000_000 for s in seeds) is False,
```

is `True` when **not all** seeds are below 10M, i.e. the name says “below 10M” but the boolean is “some seed is above 10M”. Cosmetic, but a reviewer reading the JSON without reading the code will misread it.

**Suggested rename:** `phase1_seed_set_has_above_10m`, or invert the expression to match the name. (See also DEE-R9-20, which identifies a second inconsistency in the same function.)

---

### DEE-R9-17 — Bootstrap uses row-weighted MAE, not equal cell weights; sample size is `len(cell)`, not fixed 30

**static (code property) + needs execution (confirmatory-equivalence check). Claim level: Proved (code reading) for the weighting property; the confirmatory-equivalence claim is Empirical Observation, OPEN.**

`paired_stratified_bootstrap` accumulates `total_err0 += rows[int(j)]["err_m0"]` over all resampled rows and divides by `total_n = sum(len(rows) for cell in cells)`. That is a **row-weighted** MAE, not an equal-cell-weighted MAE. §3.10 requires “Retain equal cell weights.” The point estimate in `evaluate` is likewise row-weighted (`statistics.fmean` over all paired test rows).

Also, `idx = rng.integers(0, len(rows), size=len(rows))` samples `len(rows)` per cell, not the fixed 30 that §3.10 names.

For the frozen confirmatory population, `integrity_gates` enforces 70 train / 30 test per cell, so all 28 test cells have exactly 30 rows and row weighting coincides with equal cell weighting, and `len(rows) == 30`. For `population in {"pilot", "synthetic"}`, and for the “compute anyway” branch (`elif fit.get("beta") is not None and test_rows and not gates["passed"]:`), cell sizes may deviate from 30, and both properties fail.

Severity Medium because it is correct for the frozen confirmatory population but silently deviates elsewhere and in the gate-failure branch.

**Reproduction (needs execution):** build two populations, one with equal cell sizes and one with unequal, run `paired_stratified_bootstrap`, and compare the CI to a reference equal-cell-weighted implementation.

**Suggested fix (for Nova):** either (a) in the confirmatory path, assert `len(rows) == 30` per cell before bootstrapping and document that row-weighting is equivalent, or (b) compute per-cell improvement and average with equal weights explicitly. Pick one and state it in the docstring.

---

### DEE-R9-18 — No reproducibility gate implemented

**static. Claim level: Proved (code reading). Disposition: OPEN.**

§3.10 lists “Verification or reproducibility gates fail” as an INCONCLUSIVE trigger. `primary_disposition` takes `gates` (integrity) and `verification` but no reproducibility gate, and `analyze_rows` computes no reproducibility gate. `_reproducibility` only *reports* Python / NumPy / Matplotlib versions and source-file SHA-256 hashes; it returns no pass/fail. Consequently no code path can set the disposition to INCONCLUSIVE for a reproducibility-gate failure.

`_reproducibility` reports `numpy_version` (satisfying the “report” half of “Pin NumPy version”), but nothing checks it against a pinned value, and nothing compares the source hashes to a frozen manifest.

Severity Medium because §3.10 explicitly makes this a disposition trigger.

**Reproduction (static):** `grep -n reproduc analyze_width.py` — only `_reproducibility` (reporting) exists.

**Suggested fix (for Nova):** add a `reproducibility_gates(...)` function (e.g. compare `numpy_version` and source SHA-256s to a frozen manifest) and pass its result into `primary_disposition`, or document that reproducibility is enforced outside the code and update §3.10 accordingly. Do not treat this as closed until either the gate exists or the prereg is amended by the authorised process.

---

### DEE-R9-19 — `effort_only_disposition` ignores integrity gates too

**static. Claim level: Proved (code reading). Disposition: OPEN.**

`primary_disposition`’s docstring says the effort-only disposition ignores “the verification gate”. The implementation computes `effort_only` without consulting `gates` (integrity) at all: it is set purely from `evaluation["improvement"]` and `bootstrap["ci_lower_2.5"]`. So a row set that fails an integrity gate (duplicate seeds, Y out of range, etc.) can still report `effort_only_disposition == "PASS"`.

If the intent is to hide only verification-gate failures (as the parenthetical says), integrity-gate failures should still force `effort_only` to INCONCLUSIVE. Severity Info: it is a labelling/interpretation issue, not a primary-disposition bug (the primary disposition still becomes INCONCLUSIVE via `reasons`).

**Suggested fix:** either reword the docstring to “ignoring all gates” or gate `effort_only` on `gates["passed"]`.

---

### DEE-R9-20 — `check_seed_manifest` uses two inconsistent “phase 1” thresholds

**static. Claim level: Proved (code reading). Disposition: OPEN.**

`check_seed_manifest` returns two booleans that both claim to characterize phase-1 seed separation but use different thresholds:

- `phase1_seeds_below_10m`: compares to `10_000_000` (10^7), matching the docstring’s “all below 10**7”.
- `disjoint_from_phase1_scheme`: compares to `phase1_max = 2026 + 10*10_000 + 100 = 102126`.

A hypothetical phase-1 seed of, say, `500000` would satisfy `disjoint_from_phase1_scheme` (`500000 > 102126`) but would not be “below 10M” under the other key’s threshold — the two checks disagree about what “phase 1” means. If `102126` is the true phase-1 maximum, the docstring is wrong; if `10^7` is the true bound, `disjoint_from_phase1_scheme` is too weak.

Severity Low.

**Reproduction (static):** compute both booleans on a manifest containing one seed in `(102126, 10_000_000)`.

**Suggested fix:** derive both from one documented constant and state that constant in the docstring.

---

## 3. Independently verified claims

### DEE-R9-06 — M0/M1/M2/M3 arithmetic

**static. Claim level: Proved (code reading). Disposition: PASS.**

I re-read the arithmetic in `fit_m0_m1`, `_within_cell_centered_sums`, `fit_degree_adjusted`, and the four `predict_*` functions against the module docstring’s formulas. The pooled within-cell centred sums, the slope `Swidthy / Swidthwidth`, the 2×2 normal equations for M3, and the clipping to `[0, ln(1+B)]` all match. This is a **static** claim that the code matches its own stated formula; it does not establish that the formula is the right one for the prereg — that is DEE-R9-07’s scope.

### DEE-R9-07 — Primary decision rules match §3.10 (implemented clauses)

**static, verified against `DISCOVERY_ROUND_01_s3.10.md`. Claim level: Proved (code reading). Disposition: PASS-with-caveat (see DEE-R9-18).**

§3.10’s decision rules are:

- **PASS:** data-integrity and verification gates pass; point improvement ≥ 5%; bootstrap lower endpoint > 0.
- **FAIL:** data-integrity gates pass; point improvement < 5%.
- **INCONCLUSIVE:** point improvement ≥ 5% but interval includes zero or negative; missing confirmatory rows; verification or reproducibility gates fail; baseline error or slope undefined; bootstrap improvement cannot be computed reliably.

`primary_disposition` implements:

- `reasons` non-empty → INCONCLUSIVE (covers integrity-gate failures, verification-gate failures, undefined slope, undefined improvement, undefined bootstrap replicates);
- otherwise, improvement ≥ 5% AND `bootstrap["ci_lower_2.5"] > 0` → PASS;
- otherwise, improvement < 5% → FAIL (the `elif` is only reached when `reasons` is empty, i.e. gates pass);
- otherwise → INCONCLUSIVE with reason “point improvement >= 5% but bootstrap interval includes zero”.

Mapping to §3.10: the PASS clause matches; the FAIL clause matches; the INCONCLUSIVE clauses match for improvement-≥-5%-with-zero-or-negative-interval, missing rows (via the integrity gate), verification-gate failure, undefined baseline/slope, and unreliable bootstrap. **One §3.10 clause is not implemented: “reproducibility gates fail”** — there is no reproducibility gate in the code (see DEE-R9-18). On the clauses that are implemented, the code is a faithful translation. The bootstrap machinery itself also matches §3.10 on the points that do not depend on cell-weighting: 10000 replicates, `np.random.default_rng(seed)` (PCG64 by default), seed 9012026, paired resampling of `err_m0`/`err_m1` (same `j` index), linear-interpolation percentiles, and models fixed during the bootstrap.

Disposition: **PASS on implemented clauses; contingent on DEE-R9-18 being accepted as out-of-scope or fixed.**

### DEE-R9-08 — Min-fill is a valid upper bound (Proved)

**static / Proved (standard). Disposition: PASS.**

For any graph `G` and any valid elimination order `σ`, `elimination_width(σ) ≥ min_σ elimination_width(σ) = treewidth(G)`. The heuristic returns one specific `σ`; its width is trivially ≥ the minimum. This is a **Proved** statement, not an empirical one. What is empirical — and what remains OPEN as DEE-R9-10 — is whether Nova’s specific implementation returns the width of its own `σ` without arithmetic error, on each instance.

### DEE-R9-09 — Replay is an independent code path

**static. Claim level: Proved (code reading). Disposition: PASS.**

`replay_elimination_order` rebuilds the primal graph from clauses, does not call `_fill_count`, does not call `primal_min_fill_width_from_graph`, and recomputes width from a caller-supplied ordering. This is genuinely independent of selection and is the right design. §3.10 does not bear on the replay path; the only open question is whether its output matches the selection’s reported width — DEE-R9-11.

### DEE-R9-14 — No solver outcome leaks into feature computation

**static. Claim level: Proved (code reading). Disposition: PASS.**

`width_features.py` imports only `dataclasses`, `typing`, and `om_lab.generators.CNFInstance`. `primal_graph`, `_fill_count`, `primal_min_fill_width_from_graph`, `primal_min_fill_width`, `replay_elimination_order`, and `min_fill_width` read only the formula variables and clauses (or an explicit adjacency map). No `solve_dpll`, no `pysat`, no label, no budget. This closes the “no test outcomes change the primary model” concern for the feature-extraction layer.

### DEE-R9-15 — Relabelling limitation documented and probed

**static. Claim level: Proved (code reading). Disposition: PASS.**

The module docstring correctly states: “the numerical tie-break means a relabelling of the variables can change the selected ordering (and, in principle, the width). Relabelling sensitivity is tested separately; see `lab/tests/test_width_features.py`.” The implementation matches this framing: `primal_min_fill_width_from_graph` uses the deterministic key `(_fill_count(work, x), x)`, and the pilot path records `width_reversed` by reversing variable IDs and recomputing the width; `analyze_rows` reports `relabel_sensitivity` when any row carries it. The docstring does not overclaim invariance — it says the width is a deterministic heuristic bound, not exact treewidth, and not a graph invariant.

---

## 4. Needs-execution items and tests to close

These are the OPEN items that cannot be closed by reading. The follow-up message will supply `width_oracle.py` (exact minimum elimination width by enumeration for small graphs, plus validity and replay checks) and a pytest suite covering as many of `ADVERSARIAL_REVIEW_01` §6.4 synthetic regimes as possible. Lumi will run them and report the real results.

| ID | Test that closes it |
|---|---|
| DEE-R9-10 | `width_oracle.exact_min_elimination_width` on fixed small graphs; assert `primal_min_fill_width(...).width >= exact`. |
| DEE-R9-11 | For each fixture, assert `sorted(result.ordering) == 1..n` and `replay_elimination_order(n, clauses, result.ordering) == result.width`. |
| DEE-R9-12 | Construct a graph with a genuine `(fill, variable_id)` tie; assert the selected variable is the smaller ID. |
| DEE-R9-13 | Synthetic regimes 1–10 from §6.4; assert the disposition produced by `analyze_rows` matches the analytically predicted one. |
| DEE-R9-16 | Independently reproduce the pilot numbers (M1 = −0.042, CI [−0.151, +0.051], M2 = +0.167, M3 = +0.127) from the pilot rows and the frozen bootstrap seed. |
| DEE-R9-17 | Run `paired_stratified_bootstrap` on an unequal-cell fixture and compare to a reference equal-cell-weighted implementation; also assert the confirmatory path samples exactly 30 per cell. |

---

## 5. Summary and next steps

- **Closed as PASS:** DEE-R9-00 (attested), DEE-R9-06, DEE-R9-08, DEE-R9-09, DEE-R9-14, DEE-R9-15.
- **PASS-with-caveat:** DEE-R9-07 (matches §3.10 on implemented clauses; see DEE-R9-18).
- **FAIL (naming only):** DEE-R9-05.
- **OPEN, static:** DEE-R9-01, DEE-R9-02, DEE-R9-03, DEE-R9-04, DEE-R9-17, DEE-R9-18, DEE-R9-19, DEE-R9-20.
- **OPEN, needs execution:** DEE-R9-10, DEE-R9-11, DEE-R9-12, DEE-R9-13, DEE-R9-16, and the confirmatory-equivalence half of DEE-R9-17.

The two findings I would most want Nova to address before any confirmatory run are **DEE-R9-04** (silent `TypeError` on ERROR rows if the caller bypasses `records_to_rows`) and **DEE-R9-18** (no reproducibility gate, though §3.10 makes it a disposition trigger). DEE-R9-17 matters for the honesty of the reported CI on non-confirmatory populations and in the gate-failure branch; it is benign on the frozen confirmatory population only because `integrity_gates` enforces 30 test rows per cell.

I have not run anything. The next message will contain `width_oracle.py` and the pytest suite for the §6.4 synthetic cases, for Lumi to run and report back.