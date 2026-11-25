# OM-C001-R2 Experiment Runner — Implementation and Infrastructure Report

Author: Claude (algorithms and experiment infrastructure lane)
Coordinator: Lumi · Research Director: Stephon
Date: 2026-11-25 · Base: `dev` @ `ed6d557`
Assignment: `docs/phase3/DISCOVERY_ROUND_01.md` Section 7.1

**Status: implementation delivered for review. Not frozen. No confirmatory test-split
instance (indices 70–99) has been solved by Claude.** Nothing in this document is a
statement about whether width predicts solver effort; no predictive statistic (slope,
correlation, MAE) was computed on any confirmatory-population data.

---

## 1. What this patch delivers

| File | Change |
|---|---|
| `lab/om_lab/solvers.py` | Section 4.1 status/verification vocabulary; strict `verified`; `stop_reason`; input validation; `solve_pysat(certify=True)`. **DPLL search unchanged** (see 2.2). |
| `lab/om_lab/harness.py` | Section 4.2 repair: logs UNKNOWN and UNVERIFIED rows instead of raising; still rejects invalid SAT witnesses. |
| `lab/om_lab/proof_check.py` | New. Independent DRAT checker, standard library only. |
| `lab/om_lab/certify.py` | New. Proof-producing reference path (CaDiCaL `cd195` + checker); Tseitin known-by-construction certifier; claim labelling. |
| `lab/om_lab/width_experiment.py` | New. The OM-C001-R2 runner (population, records, watchdog, freeze guard, combine, audit, certifier validation, smoke). |
| `lab/om_lab/analyze_width.py` | Small fix in Nova's file: `records_to_rows` now honours an explicit `status`; `ERROR` rows are missing data, never UNSAT. **Needs Nova's review.** |
| `lab/tests/test_width_experiment.py`, `test_proof_check.py` | New tests (54). |
| `lab/tests/test_solvers.py`, `test_harness_and_transition.py`, `test_hard_instances.py` | Updated to the strict semantics (UNSAT is no longer `verified` without a checked certificate). |
| `lab/tests/_reference_solvers_ed6d557.py` | Verbatim copy of `solvers.py` at `ed6d557`, used only as a differential-test oracle. |
| `lab/constraints-om-c001-r2.txt` | Proposed exact dependency pins for the freeze. |

---

## 2. Status and verification semantics (Sections 4.1–4.2)

### 2.1 Vocabulary

Every `SolveResult` and every runner record carries:

- `status` ∈ {`SAT`, `UNSAT`, `UNKNOWN`, `ERROR`}
- `verification_status` ∈ {`SAT_WITNESS_CHECKED`, `UNSAT_PROOF_CHECKED`,
  `UNSAT_KNOWN_BY_CONSTRUCTION`, `UNSAT_SOLVER_AGREEMENT_ONLY`, `UNVERIFIED`,
  `NOT_APPLICABLE`, `INVALID`}
- `verified` — now strict: True only for `SAT_WITNESS_CHECKED`, `UNSAT_PROOF_CHECKED`
  or `UNSAT_KNOWN_BY_CONSTRUCTION`. A completed UNSAT return with no checked
  certificate is `UNVERIFIED`, `verified=False`. The old "UNSAT ⇒ `verified=True`"
  pattern now raises `ValueError` at construction (Section 10.1).
- `stop_reason` ∈ {`decision_budget`, `time_budget`} for UNKNOWN; for runner ERROR
  records, the infrastructure failure kind (`watchdog`, `worker_crash`, `exception`).

`satisfiable` and `timed_out` are kept for compatibility and validated against `status`.

### 2.2 The primary DPLL is preserved

The inner `simplify`/`dpll` block of `solve_dpll` is byte-identical to `ed6d557`
(67 lines, SHA-256 `6c616ce42bef10e93fbdf69f3bdc4c6d5d6e7a6a534c26eeb628c12ffcabf0d2`
before and after). Preserved: unit propagation, first shortest clause, its first
remaining variable, True before False, the branch-attempt counter (`decisions`), and the
budget check at recursive entry. Consequences of that convention, now documented and
tested: an exhausted run reports exactly `D = B`; a completed run has `D ≤ B − 1`;
`B = 0` makes even the empty formula UNKNOWN.

Changes around the core only: input validation (literal 0 or |lit| > n now raises
instead of returning a truncated, unverifiable model — reproduced before the fix with
`solve_dpll(1, [[2]])`), clause materialisation (witness checks can no longer run against
an exhausted iterator), and result labelling.

`test_primary_solver_reproduces_ed6d557_exactly` compares status, branch attempts,
propagations and model against the vendored `ed6d557` copy on 150 random formulas with
budgets {None, 0, 1, 2, 5, 20, 100}.

---

## 3. Independent UNSAT proof verification

**Route used by the experiment (`UNSAT_PROOF_CHECKED`).** For every instance, the
reference solver CaDiCaL 1.9.5 (PySAT `cd195`, python-sat 1.9.dev25) runs with proof
logging. Its DRAT certificate is checked by `om_lab.proof_check.check_drat`. A primary
DPLL UNSAT claim is labelled `UNSAT_PROOF_CHECKED` only if that certificate is valid.
The reference never changes the primary status; UNKNOWN stays UNKNOWN.

**Checker.**
- Standard library only.
- Imports nothing from `om_lab` and shares no code with any solver.
- Forward-checks every lemma: AT/RUP, or RAT on the lemma's first literal.
- Accepts only if the empty clause is added and passes its check (or the formula already contains the empty clause).
- Parses strictly; malformed certificates are rejected, never accepted.
- Deletion convention follows DRAT-trim's default. Deletions of unit clauses, and of possible root-level reason clauses, are ignored and counted. Ignoring a deletion is always sound; the argument is in the module docstring.

Format reference: Wetzler, Heule & Hunt, *DRAT-trim: Efficient Checking and Trimming
Using Expressive Clausal Proofs*, SAT 2014, LNCS 8561, pp. 422–429,
doi:10.1007/978-3-319-09284-3_31; format note: Heule, arXiv:1610.06229.

**Retention (Section 4.1).** Each record stores the formula SHA-256 (canonical DIMACS,
original order), the certificate SHA-256, the checker name, version and source SHA-256,
the backend and version, and the result. `--keep-certificates` also writes the `.cnf` and
`.drat` files. `*_certificate_manifest.json` is written for every run.

**Known by construction (`UNSAT_KNOWN_BY_CONSTRUCTION`).** `certify_tseitin_by_construction`
accepts only instances that are verifiably the construction:
- the graph is valid and cubic;
- the CNF equals a fresh `encode_tseitin` clause-for-clause;
- the metadata matches the charges;
- at least one component has odd charge (per-component parity, as Section 7.4 requires).

It is not used by the random 3-SAT experiment.

**Backend + checker validated together** (Section 4.1, "before freezing"): see 5.3.

---

## 4. The runner (`lab/om_lab/width_experiment.py`)

- **Population.** Seed scheme, constants and `Y` come from Nova's `analyze_width` (single
  source of truth). `seed` = first 16 bytes of SHA-256(UTF-8 `"OM-C001-R2|n|A|i"`),
  big-endian; `m = (A·n + 50) // 100`; train = indices 0–69 (1960 instances), test =
  70–99 (840). `build_specs` refuses cross-split indices and unfrozen cells. A test
  re-derives the seed independently from the Section 3.5 text.
- **Per instance:**
  1. Regenerate the formula (clause order preserved).
  2. Compute Nova's `primal_min_fill_width`, its independent elimination-order replay, the reversed-ID width, and the co-occurrence mean degree.
  3. Run `solve_dpll(n, clauses, max_decisions=10000, max_seconds=None)`.
  4. Run the reference certificate.
  5. Write one primary record.
- **Exactly one primary record per expected instance**, written in (n, A, index) order
  regardless of worker scheduling. Records contain no timestamps or timings, so a rerun
  produces a byte-identical file. Timings go to a separate `*_telemetry.jsonl`.
- **Infrastructure protection.** Long-lived worker processes, with a ready handshake so start-up never counts against the watchdog. Per-instance wall-clock watchdog (default 600 s).
  - Crashes and exceptions are infrastructure failures, rerun with the **same instance and budget** (default up to 3 attempts).
  - An instance that never succeeds gets one `status="ERROR"` record (`y=null`, `decisions=null`): missing data, never UNKNOWN or UNSAT.
  - Nova's `records_to_rows` now excludes ERROR rows, so the confirmatory integrity gate reports the missing row (→ INCONCLUSIVE).
- **Confirmatory boundary.** `run --split test` (confirmatory population) is refused unless `--freeze` points to a manifest with:
  - `confirmatory_authorized: true` and a non-empty `authorized_by`;
  - matching source hashes, function hashes, checker hash, seed-manifest hash and protocol constants;
  - the same Python major.minor and python-sat/numpy versions.

  `freeze` only ever writes a DRAFT with `confirmatory_authorized: false`. The guard also refuses fault injection, a non-frozen budget, and `--no-certify` for the confirmatory population. It is a procedural guard against accidental unblinding, not cryptographic blinding (Section 3.5).
- **Integrity report** (run, combine and audit). Checks:
  - one record per instance, with identity fields matching the seed scheme;
  - UNKNOWN rows make no claim and have `D = B` and `Y = ln(1+B)`;
  - completed rows have `D < B` and `Y = ln(1+D)`;
  - SAT rows are witness-checked, and no UNSAT row is INVALID;
  - `verified` is consistent with `verification_status`, and width equals its replay;
  - no integrity alarms are set.

  `verification_gate_ready` is true only if every UNSAT row is certified and there are no INVALID or ERROR rows.
- **Audit (for Lumi's independent verification).** `audit` re-verifies a results file:
  - regenerates every formula from its seed and checks `formula_sha256`;
  - re-checks every stored SAT model against the regenerated formula;
  - with `--recompute-features`, recomputes width and degree;
  - with `--recheck-certificates`, regenerates and re-checks every UNSAT certificate and compares proof hashes;
  - with `--drat-trim PATH`, also checks every certificate with DRAT-trim.

---

## 5. Infrastructure results

All numbers below are **[Claim Level: Empirical Observation]**. They come from one Linux
x86_64 machine (2 CPUs, Python 3.12.3, pins in `lab/constraints-om-c001-r2.txt`). They are
infrastructure measurements, not findings about the hypothesis.

### 5.1 Training split (confirmatory population, indices 0–69)

| Item | Value |
|---|---|
| Records / expected | 1960 / 1960 (exactly one each) |
| Status | SAT 1097 · UNSAT 863 · UNKNOWN 0 · ERROR 0 |
| Verification | SAT_WITNESS_CHECKED 1097 · UNSAT_PROOF_CHECKED 863 · INVALID 0 · alarms 0 |
| Infrastructure failures | 0 |
| Total recorded branch attempts | 248,212 (preregistered population cap 28,000,000) |
| Max branch attempts on one instance | 992 (budget B = 10,000; budget hits: 0) |
| `confirmatory_train_results.jsonl` SHA-256 | `0e193993bddc89a09005c5e04d04710189162a59362745a9206d0ce635e08339` |
| Repeat run from scratch | byte-identical file (same SHA-256) |
| Audit (`--recompute-features --recheck-certificates --drat-trim`) | 0 failures; 863/863 certificates regenerated with identical proof hashes and VALID; DRAT-trim VERIFIED 863/863 |
| Hand-off to `analyze_width` | `records_to_rows` maps 1960 rows; `verification_gates` passes (863/863 UNSAT proof-checked). M0/M1 were **not** fitted here. |
| Wall clock | 72 s with 2 workers (telemetry only) |

### 5.2 Smoke test (pilot seeds only)

The `smoke` subcommand covers two things:
- Two independent pilot runs (2 cells × 2 densities × 6 instances, separate worker processes) are byte-identical.
- A tiny-budget pilot run (B=20) yields only UNKNOWN rows with `D = 20`, `Y = ln 21`, and no claims.

Passed. An end-to-end pilot pipeline (`run` train + test, `combine`, `analyze_width --population pilot`) runs and returns INCONCLUSIVE by construction for a pilot population.

### 5.3 Backend + checker validation (pilot seeds only)

`validate-certifier` ran on 240 pilot instances (n ∈ {30, 40, 50, 60}, A ∈ {426, 460, 500}, 20 each). Result: 85 SAT, all witnesses checked; 155 UNSAT.

| Check (155 UNSAT instances) | om_lab checker | DRAT-trim |
|---|---|---|
| Genuine CaDiCaL certificate accepted | 155/155 | 155/155 |
| Same certificate replayed against the formula's largest satisfiable clause prefix, rejected | 155/155 | 155/155 |

A sound checker can never accept a refutation of a satisfiable formula, so the second row is a direct soundness probe. Separately, across `cd195`, `g4` and `lgl` proofs on 174 pilot UNSAT instances, the om_lab checker and DRAT-trim agreed 174/174. On 60 pilot instances, CaDiCaL's decisions/conflicts/propagations were identical with and without proof logging, so the recorded reference CDCL statistics (secondary analysis 6) are not distorted by certification.

### 5.4 Side results

- **Phase 1 PHP benchmark (Section 10.1).** `solve_pysat(..., certify=True)` gives `UNSAT_PROOF_CHECKED` for PHP with n = 3…7 holes. The n = 7 certificate has 14,414 steps and checks in about 10 s. The previously reported UNSAT results can therefore be re-labelled from "verified" (uncertified) to proof-checked by re-running with `certify=True`. The decision counts in Section 2.1 are unaffected.
- **Duplicate min-fill implementations.** Dee's `matched_instances.min_fill_width_estimate` and Nova's `width_features.primal_min_fill_width` agree on all 10 instances of the Tseitin registry (5 graphs × 2 charges). That is agreement on 10 cases, not a proof that the two implementations are equivalent.

---

## 6. Exact reproducible commands (for Lumi)

```bash
cd lab
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -c constraints-om-c001-r2.txt && pip install -e .
pytest -q                                   # 134 passed, 2 skipped (DRAT-trim tests skip without the binary)
OUT=results/om_c001_r2
python -m om_lab.width_experiment seeds --out $OUT/seeds.json
python -m om_lab.width_experiment validate-certifier --out $OUT/certifier_validation.json   # add --drat-trim /path/to/drat-trim
python -m om_lab.width_experiment smoke --out-dir $OUT/smoke
python -m om_lab.width_experiment run --split train --out-dir $OUT --workers 4
sha256sum $OUT/confirmatory_train_results.jsonl   # expect 0e193993bddc89a09005c5e04d04710189162a59362745a9206d0ce635e08339
python -m om_lab.width_experiment audit $OUT/confirmatory_train_results.jsonl --splits train --recompute-features --recheck-certificates
python -m om_lab.width_experiment freeze --out $OUT/freeze.json    # DRAFT; Lumi authorises after approval

# Only after Lumi sets confirmatory_authorized=true / authorized_by in freeze.json:
python -m om_lab.width_experiment run --split test --freeze $OUT/freeze.json --out-dir $OUT --workers 4
python -m om_lab.width_experiment combine --out $OUT/results.jsonl $OUT/confirmatory_train_results.jsonl $OUT/confirmatory_test_results.jsonl
python -m om_lab.width_experiment audit $OUT/results.jsonl --splits train test --recheck-certificates
python -m om_lab.analyze_width --records $OUT/results.jsonl --population confirmatory --out-dir $OUT/analysis
```

The expected training hash assumes Python 3.12 and the pinned versions. Branch counts,
statuses, models and proof hashes are integers or strings and should reproduce
elsewhere. `y` and `degree_mean` are floats; a different libm could in principle differ in
the last bit, so cross-platform reproduction should compare integer fields and hashes
if the whole-file SHA-256 differs.

DRAT-trim (MIT licence, <https://github.com/marijnheule/drat-trim>) is optional. To
enable the cross-check tests: `gcc -O2 -o drat-trim drat-trim.c` and
`OM_DRAT_TRIM=/path/to/drat-trim pytest -q`.

---

## 7. Claim ledger

| # | Claim | Level |
|---|---|---|
| 1 | The DPLL search code is unchanged from `ed6d557`; status, branch attempts, propagations and models match the vendored copy on the tested formulas. | Empirical Observation (byte diff of the block + differential tests) |
| 2 | Ignoring a DRAT deletion, or any deletion, preserves soundness of UNSAT acceptance. | Proved — elementary argument in `proof_check.py`; pending independent team review |
| 3 | RUP/RAT redundancy preserves satisfiability. | Established literature (cited); not re-proved here |
| 4 | `om_lab.proof_check` accepted every genuine certificate and rejected every corrupted or transplanted certificate tested, and agreed with DRAT-trim (5.3; 863/863 training). | Empirical Observation. The checker is **not** claimed correct in general. |
| 5 | Training-split infrastructure results in 5.1, including byte-identical reruns. | Empirical Observation (one machine) |
| 6 | The confirmatory guard refuses the test split without a valid, authorised, hash-matching freeze. | Empirical Observation (tested); procedural, not cryptographic |
| 7 | PHP n=3…7 UNSAT claims carry checked certificates. | Empirical Observation |
| 8 | Odd-charge Tseitin instances validated by `certify_tseitin_by_construction` are UNSAT. | Relies on the parity argument, `DISCOVERY_ROUND_01.md` §5.2: Proved, pending review. Not Lean-Verified by this patch. |
| 9 | Anything about width predicting DPLL effort. | **No claim.** No predictive statistic was computed. |

---

## 8. Issues in the plan and cross-lane notes

1. **The budget never binds on the training split** (max 992 vs B = 10,000; 0 of 1960).
   The capped response and the UNKNOWN path exist only in tests for this population,
   and Y is effectively ln(1+D). Section 3.6 says keep B fixed, so I am not
   recommending a change. Any change to B or to n would have to be made before the freeze
   and recorded as a revision. [Empirical Observation, training split]
2. **What `UNSAT_PROOF_CHECKED` certifies.** The reference certificate proves the
   *formula* is UNSAT, so DPLL's UNSAT answer is correct. It does not certify DPLL's
   internal search. A DPLL bug that still returned the right answer would not be
   detected. This is adequate for the preregistered response, but the label should be
   read as "claim certified", not "search certified".
3. **Independence is from the solvers, not from the author.** The checker and the runner
   were written by the same agent. DRAT-trim agreement is the external cross-check, and it
   is not in CI. Suggestion for Lumi (CI owner): an optional job that builds DRAT-trim and
   runs `OM_DRAT_TRIM=… pytest -q tests/test_proof_check.py`.
4. **Nova's `records_to_rows` ignored an explicit `status`.** An infrastructure ERROR
   row would have been read as UNSAT, because it has `satisfiable=False, timed_out=False`.
   Fixed minimally here; Nova should review. Two smaller items left for Nova:
   - `make_row` labels a lone DPLL UNSAT as `UNSAT_SOLVER_AGREEMENT_ONLY` when no second solver ran; `UNVERIFIED` is accurate. Both fail the gate, so the outcome is unaffected.
   - The static limitation text "UNSAT rows … carry no proof certificate" is now stale for runner rows.
5. **Infrastructure parameters not in the preregistration.** The watchdog (600 s), the
   max attempts (3) and the reference backend (`cd195`) are runner choices. They are
   recorded in every run manifest and the backend is pinned in the freeze protocol.
   Lumi may want them in `freeze.json` notes as well.
6. **Dependency pins.** `requirements.txt` uses `>=`, so CI installs the latest
   python-sat/numpy. The freeze guard requires exact matches, so the freeze must be
   generated in the pinned execution environment (`constraints-om-c001-r2.txt` is a
   proposal).
7. **`check_seed_manifest` field name.** `phase1_seeds_below_10m: true` means "not all
   confirmatory seeds are below 10^7". The check is right; the name is confusing.
   Phase 1 disjointness is checked by numeric range, not against actual Phase 1
   manifest files.
8. **Two min-fill implementations exist** (Dee's and Nova's). They agree on the 10
   registry instances tested. The confirmatory feature must come from Nova's
   `width_features`, which the runner uses.

---

## 9. Known limitations

- The DPLL recurses once per decision level. Python's recursion limit makes it raise
  `RecursionError` for decision depths around 1000 (observed on a 3000-variable chain
  formula). That is irrelevant for n ≤ 60. The runner would record such a failure as
  ERROR, never as data.
- Open Phase 2 audit findings outside this experiment, not fixed in this patch:
  - duplicate-literal clauses are not unit-propagated by the frozen DPLL;
  - `GraphColoringInstance` accepts out-of-range or negative vertex ids and silently emits literal 0 or out-of-range variables.
- All timing and determinism observations come from one machine.
- The stretch goal (a separate width-guided DPLL variant) is deliberately not started.
  Section 7.1 sequences it after the primary runner is frozen.
