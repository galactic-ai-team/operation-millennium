# OM-C001-R2 Experiment Runner — Implementation and Infrastructure Report

Author: Claude (algorithms and experiment infrastructure lane)
Coordinator: Lumi · Research Director: Stephon
Date: 2026-11-25 · Base: `dev` @ `ed6d557`
Assignment: `docs/phase3/DISCOVERY_ROUND_01.md` Section 7.1

**Updated 2026-11-25 for the Phase 4 Gate B/D repair (base `dev` @ `b6d2b27`).** The
single-file freeze is replaced by the two-stage freeze, the non-executing preflight
and one production entrypoint (Section 10). Sections 4, 6 and 7 are updated to match;
Sections 1-3 and 5 are the original report.

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
- **Confirmatory boundary (updated, Section 10).** `run --split test` (confirmatory
  population) runs only with a Stage A freeze manifest and Lumi's Stage B
  authorisation (`--stage-a`, `--stage-b`). Both are re-verified against the running
  code, checkout, interpreter, dependency inventory, documents, training records,
  fitted model and requested settings, and the run schedules exactly the frozen
  840-instance test population. The single-file `freeze` manifest (schema 1) no
  longer authorises anything. Fault injection, a non-frozen budget and `--no-certify`
  are refused for the confirmatory population, at every execution layer. It is a
  procedural guard against accidental unblinding, not cryptographic blinding
  (Section 3.5, ACE-PLAN-06).
- **Integrity report** (run, combine, audit and the freeze). Checks:
  - one record per instance, with identity fields matching the seed scheme;
  - strict JSON types (a malformed record is reported as a failure, never a crash);
  - UNKNOWN rows make no claim and have `D = B` and `Y = ln(1+B)`;
  - completed rows have `D < B` and `Y = ln(1+D)`;
  - the evidence behind every claim, not the stored status (Section 10.5): the
    formula is regenerated and its hash compared, every SAT model is re-verified,
    and every `UNSAT_PROOF_CHECKED` claim needs a VALID certificate summary from this
    checker;
  - `verified` is consistent with `verification_status`, and width equals its replay;
  - no integrity alarms are set.

  `verification_gate_ready` is true only if every UNSAT row is certified and there are
  no INVALID or ERROR rows. `complete` says whether the records are the full population.
- **Audit (for Lumi's independent verification).** `audit` re-verifies a results file:
  - the integrity report above (formula hashes, SAT models, certificate summaries);
  - with `--certificates-dir` and `--certificate-manifest`, the retained `.cnf` and
    `.drat` files themselves (Section 10.6); required for a passing confirmatory audit;
  - with `--recompute-features`, recomputes width and degree;
  - with `--recheck-certificates`, regenerates and re-checks every UNSAT certificate
    as extra evidence (a valid regenerated proof with a different hash is a note, not
    a failure);
  - with `--drat-trim PATH`, also checks the retained proofs (and any regenerated
    ones) with DRAT-trim.

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

Updated for the two-stage freeze. The positional results path of `audit` comes
**before** `--splits` (argparse would otherwise read it as a split name; the original
version of this section had that ordering defect).

```bash
cd lab
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -c constraints-om-c001-r2.txt && pip install -e .
pytest -q                     # DRAT-trim tests skip without OM_DRAT_TRIM
OUT=results/om_c001_r2
python -m om_lab.width_experiment seeds --out $OUT/seeds.json
python -m om_lab.width_experiment validate-certifier --out $OUT/certifier_validation.json   # add --drat-trim /path/to/drat-trim
python -m om_lab.width_experiment smoke --out-dir $OUT/smoke

# 1. Training split (complete population; certificates retained)
python -m om_lab.width_experiment run --split train --out-dir $OUT --workers 4 --keep-certificates
sha256sum $OUT/confirmatory_train_results.jsonl   # expect 0e193993bddc89a09005c5e04d04710189162a59362745a9206d0ce635e08339
python -m om_lab.width_experiment audit $OUT/confirmatory_train_results.jsonl --splits train \
    --certificates-dir $OUT/certificates --certificate-manifest $OUT/confirmatory_train_certificate_manifest.json \
    --recompute-features

# 2. Stage A (from a clean checkout of the execution commit, in the execution environment)
python -m om_lab.width_experiment stage-a --out-dir $OUT/freeze \
    --training-records $OUT/confirmatory_train_results.jsonl \
    --training-certificates-dir $OUT/certificates \
    --training-certificate-manifest $OUT/confirmatory_train_certificate_manifest.json \
    --reproduction-sha256 <SHA-256 of the independently reproduced training file> \
    --reproduced-by <who reproduced it> --workers 4

# 3. Non-executing preflight (no authorisation needed; runs no solver)
python -m om_lab.width_experiment preflight --stage-a $OUT/freeze/freeze_stage_a.json --out $OUT/freeze/preflight.json

# 4. Lumi only: Stage B
python -m om_lab.width_experiment authorize --stage-a $OUT/freeze/freeze_stage_a.json \
    --authorized-by Lumi --confirm-test-split-unexposed --out $OUT/freeze/freeze_stage_b.json

# 5. The one production run (same --workers/--watchdog-s/--max-attempts as Stage A)
python -m om_lab.width_experiment run --split test --dry-run --workers 4 --out-dir $OUT \
    --stage-a $OUT/freeze/freeze_stage_a.json --stage-b $OUT/freeze/freeze_stage_b.json
python -m om_lab.width_experiment run --split test --workers 4 --keep-certificates --out-dir $OUT \
    --stage-a $OUT/freeze/freeze_stage_a.json --stage-b $OUT/freeze/freeze_stage_b.json

# 6. Combine and audit
python -m om_lab.width_experiment combine --out $OUT/results.jsonl \
    --certificate-manifest $OUT/confirmatory_train_certificate_manifest.json \
    --certificate-manifest $OUT/confirmatory_test_certificate_manifest.json \
    $OUT/confirmatory_train_results.jsonl $OUT/confirmatory_test_results.jsonl
python -m om_lab.width_experiment audit $OUT/results.jsonl --splits train test \
    --certificates-dir $OUT/certificates --certificate-manifest $OUT/certificate_manifest.json
python -m om_lab.analyze_width --records $OUT/results.jsonl --population confirmatory \
    --stage-a $OUT/freeze/freeze_stage_a.json --stage-b $OUT/freeze/freeze_stage_b.json \
    --test-run-manifest $OUT/confirmatory_test_run_manifest.json \
    --combine-manifest $OUT/results_combine_manifest.json --out-dir $OUT/analysis
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
| 6 | The confirmatory guard refuses the test split without a valid Stage A and Stage B that match the running code, checkout, environment, artefacts and settings (Section 10). | Empirical Observation (the tested cases in `test_freeze_enforcement.py`); procedural, not cryptographic |
| 7 | PHP n=3…7 UNSAT claims carry checked certificates. | Empirical Observation |
| 8 | Odd-charge Tseitin instances validated by `certify_tseitin_by_construction` are UNSAT. | Relies on the parity argument, `DISCOVERY_ROUND_01.md` §5.2: Proved, pending review. Not Lean-Verified by this patch. |
| 9 | Anything about width predicting DPLL effort. | **No claim.** No predictive statistic was computed. |
| 10 | Official execution schedules exactly the 840-instance test population; every subset, duplicate, reordering, wrong seed or wrong population tested is refused, dry run or not. | Empirical Observation (tested cases) |
| 11 | Integrity no longer accepts a status claim without its evidence (Section 10.5). | Empirical Observation (tested forgeries) |
| 12 | The retained-certificate audit reads the stored `.cnf`/`.drat` bytes, checks their hashes and association, and checks the stored proof against the stored CNF; every tested substitution was rejected (Section 10.6). | Empirical Observation (tested cases). The checker itself is not claimed correct in general (row 4). |
| 13 | Propagation-count semantics in Section 10.8 describe the frozen source. | Documentation read from the source, pinned by four small tests; not a theorem |

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

---

## 10. Phase 4 Gate B/D repair: freeze enforcement, exact scheduling, certificate audit

Author: Claude (lane: freeze enforcement, exact scheduling, certificate auditing,
production entrypoint). Independent reviewer: Nova. Base: `dev` @ `b6d2b27`.
Findings: NOVA-R10-01/-02/-03/-05/-15 and Ace's gate review (2026-11-25) sections 3
and 5; ACE-PLAN-01/02/05/06; ACE-PLAN-04 documentation. Every result in this section
is **[Claim Level: Empirical Observation]** unless marked otherwise.

### 10.1 Two-stage freeze (`lab/om_lab/freeze.py`, ACE-PLAN-01 / B4)

**Stage A** (`stage-a` command, `freeze_stage_a.json` + `fitted_model.json`). It is
written only from a checkout whose frozen paths are clean, and only if the training
artefacts pass the deep check (10.6) and the independent reproduction hash equals the
training-record hash. Fields:

| Field | Content | Checked at verification |
|---|---|---|
| `code` | execution commit (40-hex), frozen paths, `tree_clean: true` | commit exists in the checkout; frozen paths clean now; no frozen path changed between the commit and HEAD |
| `source_sha256`, `function_sha256` | the 9 runner source files (now including `freeze.py`) and the frozen functions | equal to the running code |
| `checker` | proof checker name, version, source SHA-256; DRAT-trim path and SHA-256 if used | equal |
| `environment.python` | implementation, exact version (gates); compiler, build (provenance) | implementation and exact `x.y.z` version equal |
| `environment.packages` | every installed distribution, PEP 503 name → version | equal as a whole (no change, addition or removal) |
| `environment.platform` | system, machine (gates); release, platform string (provenance) | system and machine equal |
| `environment.reference_backend` | python-sat version and the SHA-256 of each compiled extension module it installs (`pysolvers`, which contains the compiled solvers including CaDiCaL, `pyformula`, `pycard`) | equal |
| `documents` | SHA-256 of `docs/phase3/DISCOVERY_ROUND_01.md` and the amendment documents (default `docs/phase4/ADVERSARIAL_REVIEW_01.md`, `docs/phase4/reviews/REVIEW_PR11_ACE.md`) | equal; ADVERSARIAL_REVIEW_01.md must be listed |
| `seed_manifest_sha256`, `protocol` | seed manifest hash and protocol constants | equal |
| `settings` | `workers`, `watchdog_s`, `max_attempts`, `worker_start_timeout_s`, `budget_b`, `max_seconds`, `certify`, `keep_certificates` | valid, and equal in value and type to the run's settings |
| `population` | schedule summaries (count, cells, per cell, schedule SHA-256) of the train and test populations | equal to the canonical populations |
| `training` | records path and SHA-256, record count, certificate manifest path and SHA-256, certificates directory, independent reproduction SHA-256 and who reproduced it | files present with those hashes; reproduction hash equal; deep check passes |
| `model` | `fitted_model.json` path and SHA-256 (M0/M1 and degree-adjusted fits from the training records, via `analyze_width`'s own functions) | file hash equal, and equal to the model recomputed from the training records |
| `kind`, `experiment`, `freeze_schema_version` (2), `runner_version`, `orchestration_version`, `created_utc` | identity | equal / valid UTC timestamp |

Unknown or missing keys are refused. JSON with duplicate keys or NaN is refused.

**Stage B** (`authorize` command, Lumi only): `stage_a_sha256` (the SHA-256 of the exact
Stage A bytes), `status: "FROZEN"`, `confirmatory_authorized: true`, `authorized_by`,
`authorized_at_utc` (UTC, not in the future, not before Stage A), and
`test_split_unexposed: true`. `authorize` writes Stage B only after a passing preflight
of that Stage A and an explicit `--confirm-test-split-unexposed`.

**No self-referential commit hash.** Stage A names the execution commit; Stage B names
Stage A's bytes; neither is inside the commit. Committing Stage B (or anything outside
the frozen paths) later is allowed: verification checks that the frozen paths are
unchanged between the execution commit and HEAD.

**Versions.** `RUNNER_VERSION` stays `1.0.0` because the per-instance records are
unchanged, so the training-record bytes (and the hash an independent reproduction
checks) are unchanged. The scheduling, verification and output changes carry
`ORCHESTRATION_VERSION = "1.1.0"`, recorded in Stage A and every run manifest.

### 10.2 Non-executing preflight (Ace, section 3)

`preflight --stage-a` verifies Stage A (including the deep training check) and builds
the canonical test schedule: 840 instances, 28 cells × 30, indices 70-99, first
`OM-C001-R2|30|380|70`, last `OM-C001-R2|60|500|99`, and its schedule SHA-256. It needs
no Stage B, launches no solver and no worker, and reports `solver_launched: false`,
`authorization_required: false` and the Stage A hash that Stage B must name. This
removes the circular dependency (authorise → dry run → authorise).

### 10.3 One production entrypoint, exact population (ACE-PLAN-02/06, NOVA-R10-02)

- `run --split test` needs `--stage-a` and `--stage-b`. `run_split` calls
  `freeze.verify_for_execution`, which re-verifies Stage B and Stage A (10.1) against
  the live checkout and environment and the requested settings, and returns an
  `AuthorizedFreeze`.
- The test split is never a subset: `--indices`, `--n-values`, `--a-values` and
  `--diagnostic-subset` are refused for it, in dry runs too. A dry run with the freeze
  records verifies them and reports the authorised schedule; a dry run without them
  only lists the schedule. Neither runs anything.
- `run_specs` refuses confirmatory test specs unless it is given an `AuthorizedFreeze`
  issued by `verify_for_execution` in this process (a hand-built, copied, pickled or
  `dataclasses.replace`d one is refused), the specs equal the canonical schedule
  exactly (order, seeds, clause counts, no duplicates, no training index) with the
  frozen schedule hash, and its settings equal the frozen settings in value and type.
- `run_instance` refuses a confirmatory test spec unless `run_specs` passed that check.
- Fault injection is refused for any confirmatory spec in `run_split`, `run_specs`
  (also when the fault targets a pilot spec in a mixed list) and `run_instance`
  (NOVA-R10-04).

### 10.4 Partial outputs are marked (NOVA-R10-03)

- A confirmatory training subset needs `--diagnostic-subset`. Its files are named
  `confirmatory_train_DIAGNOSTIC_SUBSET_*`, and its manifest has
  `run_mode: "DIAGNOSTIC_SUBSET"`, `complete: false`, `partial: true`, `n_instances`
  and `n_population` (1960).
- Every run manifest records `run_mode` (`OFFICIAL`, `DIAGNOSTIC_SUBSET` or `PILOT`),
  `complete`, `partial`, `n_instances`, `n_population`, `schedule_sha256`, the settings,
  the authorisation summary and the number of retained certificates.
- `combine` writes `<out>_combine_manifest.json` (`complete`, `partial`, `n_records`,
  `n_population` = 2800, input file hashes). A partial confirmatory combine is refused
  unless the output file name contains `PARTIAL`.
- Confirmatory runs must use `--keep-certificates`.

### 10.5 Evidence, not status claims (NOVA-R10-05)

The integrity report regenerates each formula from its seed and compares
`formula_sha256`; re-verifies every SAT model (a complete signed assignment in
variable order) against the regenerated formula; requires, for every
`UNSAT_PROOF_CHECKED` claim, a reference UNSAT result with a VALID DRAT certificate
summary naming this checker (name, version, source SHA-256), a proof hash and
primary/reference agreement; and rejects `UNSAT_KNOWN_BY_CONSTRUCTION` for random
3-SAT. Field types are checked strictly (booleans are not integers, NaN is not a
number, unknown or missing keys fail), so malformed records produce failures instead
of exceptions (NOVA-R10-06). The summary only says a proof was checked; the stored
proof itself is checked in 10.6. These are runner-side checks; the analysis's
`records_to_rows` typing (B5.2) is Nova's and is unchanged here.

### 10.6 Retained-certificate audit (NOVA-R10-15, Gate D2, ACE-PLAN-05)

`audit_retained_certificates` works from the retained files, not from a regenerated
proof. For every retained pair named in the certificate manifest, and for every
`UNSAT_PROOF_CHECKED` record (which must have one):

1. the manifest entry names this instance's files (`<sha256(instance_id)[:16]>.cnf/.drat`)
   and agrees with the record's formula hash and proof hash;
2. the exact bytes of both files hash to the manifest values (retained proofs are
   written one stripped line per step, so the file hash equals the record's
   `proof_sha256`);
3. the retained CNF parses as canonical DIMACS and equals this instance's regenerated
   formula;
4. `om_lab.proof_check` accepts the retained proof against the retained CNF
   (and DRAT-trim too with `--drat-trim`);
5. retained files of these instances that the manifest does not name are failures.

Manifests written before this change (no `retained_files`) fall back to the
conventional file names and the record's hashes, and are counted as legacy entries.
`--recheck-certificates` regenerates proofs as extra evidence only; it cannot replace
the retained audit, which a confirmatory audit requires. Different valid proofs are
allowed: a regenerated proof with another hash is a note, not a failure (NOVA-R10-07).
Stage A's deep check runs this audit on the training certificates.

### 10.7 Ace's section 5 attacks (all rejected)

Synthetic, training and pilot data, and non-executing schedules only.
Tests are in `lab/tests/test_freeze_enforcement.py` unless noted.

| Attack | Rejected by | Tests |
|---|---|---|
| Substitute a retained `.drat` file | byte hash vs manifest; manifest vs record; stored proof checked against stored CNF; Stage A deep check | `test_attack_substituted_training_drat_rejected_at_execution`, `test_d2_*` |
| Forged verification status | evidence checks (10.5) and the retained audit, including after the records hash, Stage A and Stage B are made consistent with the forgery | `test_attack_forged_training_verification_status_rejected[*]`, `test_forged_evidence_fails_integrity[*]` |
| Alter a frozen training coefficient | model file hash; model recomputed from the training records | `test_attack_altered_frozen_coefficient_rejected`, `..._with_rehashed_stage_a_rejected_by_recomputation` |
| Authorise a manifest with a dirty source tree | live git check in preflight / `authorize` / execution; `stage-a` refuses too | `test_attack_authorize_with_a_dirty_source_tree_rejected`, `test_attack_dirty_tree_end_to_end_with_real_git`, `test_build_stage_a_refuses[dirty-tree]` |
| Modify watchdog or retry settings after the freeze | requested vs frozen settings; Stage B hash binding; `run_specs` settings check | `test_settings_changed_after_the_freeze_refused[*]`, `test_official_run_with_changed_settings_refused_before_scheduling[*]`, `test_run_specs_refuses_settings_that_differ_from_the_freeze[*]` |
| Request one test index in official execution mode | subset refusal in `run_split`; exact-schedule check in `run_specs` | `test_attack_test_split_subset_rejected_even_with_authorisation[*]`, `test_run_specs_refuses_any_other_schedule_even_when_authorised[*]` |
| Change the Python patch version or a pinned dependency | exact version and whole dependency inventory | `test_environment_drift_after_the_freeze_refused[python-patch, pinned-numpy, pinned-python-sat, ...]` |

ACE-PLAN-01's required regression (every required field tampered or missing) is
`test_stage_a_missing_field_refused[*]`, `test_stage_a_tampered_field_refused_even_when_re_signed[*]`
(Stage B is re-signed, so each refusal comes from the field's own check),
`test_stage_b_missing_field_refused[*]` and `test_stage_b_tampered_field_refused[*]`.
ACE-PLAN-02's regressions are `test_authorised_full_dry_run_is_accepted_and_runs_nothing`,
`test_attack_test_split_subset_rejected_even_with_authorisation[one-index-dry-run]`,
`test_wrong_test_schedules_are_rejected[pilot-population, training-split, ...]`,
`test_wrong_test_schedules_are_rejected[duplicate-preserving-count]` and
`test_partial_confirmatory_combine_must_be_named_partial`.

How the tests avoid executing the test split: solver and worker entry points are
replaced by stubs that fail the test if reached, and the one accepted official run is
intercepted where `run_specs` would start the first worker. The live environment is a
deterministic double (`tests/_freeze_fixtures.py`); the real git probe is tested on a
temporary repository, and one end-to-end test uses real git and real provenance.

### 10.8 Propagation-count semantics of the frozen DPLL (ACE-PLAN-04)

Read from `solvers.solve_dpll` (unchanged since `ed6d557`) and pinned by
`test_propagation_count_semantics_ace_plan_04` (the vendored `ed6d557` copy gives the
same counts on those four formulas). **[Documentation of the source, not a theorem.]**

- `decisions` counts branch attempts (each of True, then False), as in 2.2. The
  primary response depends only on it.
- `propagations` counts each previously unassigned variable that receives a value
  from a unit-clause batch. On every recursive entry (after the budget checks) the
  solver loops: simplify the clause list under the current assignment (drop
  satisfied clauses and false literals; an empty clause ends the call as a conflict;
  no clauses left means SAT); collect the batch of unit clauses in clause order;
  stop if there are none; otherwise assign the batch in order.
- Within a batch, a unit whose variable is already assigned the same value is not
  counted; a unit that contradicts an assignment stops the batch at once (the
  conflicting unit is not counted; units earlier in the batch stay counted; later
  units are not assigned). Units are not propagated into each other within a batch:
  clauses that become unit or empty because of the batch are found by the next
  simplification.
- The counter is global: propagations in branches that are later refuted, and in a
  run that exhausts its budget, are included. Branch assignments are decisions, not
  propagations.
- The experiment's formulas have three distinct variables per clause, so the Phase 2
  duplicate-literal issue (9) cannot arise in them.

Per ACE-PLAN-04, an independent tracer need not reproduce this counter unless it copies
this batch order; a propagation-only discrepancy does not affect the primary estimand.

### 10.9 Limitations and proposed scoped limitations

- **Procedural, not cryptographic (ACE-PLAN-06).** The guard stops accidental
  unblinding through the supported paths. It does not stop deliberate circumvention
  inside the process (calling `run_instance(..., official=True)` or the solvers
  directly, editing the issued-authorisation registry), and Stage B is a JSON file,
  not a signature: anyone who can write files can write one. The seed scheme is
  public.
- **Proposed scoped limitation: no test-split recovery mode.** The test split runs only
  as the full population. If an instance still fails after `max_attempts`, its ERROR
  record stays missing data (INCONCLUSIVE under the protocol). A recovery run of
  named test instances would need authorisation rules that Lumi and Ace have not set,
  so it is refused rather than guessed at.
- **Proposed scoped limitation: platform gate.** OS and architecture are gates; the
  kernel release and platform string are recorded but not gated, because they change
  on routine updates and the records contain no platform-dependent field except the
  floats discussed in Section 6. Lumi can ask for them to be gated.
- **Proposed scoped limitation: legacy certificate manifests.** Manifests without
  `retained_files` are audited by conventional file names and the record's hashes,
  and are counted, not refused. The training certificates should be regenerated with
  this version before Stage A, so this path should not be needed for the freeze.
- The canonical environment (Ace recommends CPython 3.12.3), the closure ledger and
  the training-reproduction verification are Lumi's; Stage A records whatever
  environment it is built in and refuses any later difference.
- The `freeze` command still writes the schema-1 provenance snapshot, because
  `analyze_width.reproducibility_gates` reads its `source_sha256` and
  `environment.packages.numpy`; Stage A carries the same two fields, and the
  official analysis derives them from the verified Stage A instead of from a
  hand-written manifest (Section 10.11).

### 10.10 Checks run for this repair

All **[Claim Level: Empirical Observation]**, on one Linux x86_64 machine (2 CPUs,
CPython 3.12.3, python-sat 1.9.dev25, numpy 2.5.5), training data only.

- Full confirmatory training split rerun with this code (`run --split train --workers 2
  --keep-certificates`, 71 s): 1960/1960 records, SAT 1097, UNSAT 863, integrity and
  evidence checks passed, `complete: true`, and the results file SHA-256 is again
  `0e193993bddc89a09005c5e04d04710189162a59362745a9206d0ce635e08339`, so the record
  bytes are unchanged by this repair.
- Retained-certificate audit of that run (`audit ... --certificates-dir
  --certificate-manifest --drat-trim`): 0 failures; 863/863 retained proofs accepted by
  `om_lab.proof_check` against their retained CNFs and 863/863 VERIFIED by DRAT-trim.
- `stage-a` from a checkout with uncommitted changes under `lab/om_lab` is refused.

### 10.11 Analysis authorization interface (ACE-GATE-D-02)

`analyze_width.reproducibility_gates` and `verify_frozen_fit` expect one
manifest, but execution authorization is two artifacts and neither stage
alone satisfies the interface: Stage A has no `status` /
`confirmatory_authorized`, Stage B has no environment or source hashes,
and neither stage pins `fitted_model_sha256`. The whole-file SHA-256 of
`fitted_model.json` is not `fit_fingerprint` either, so no single-manifest
fix works -- a hand-derived manifest passes the reproducibility gate and
still fails the fitted-model gate. The repair is the trusted analysis
handoff, `analyze_width.build_analysis_handoff(stage_a_path,
stage_b_path, *, test_run_manifest_path, combine_manifest_path=None,
records_path=None, provenance=None, deep_training=True) -> dict`.

It verifies Stage B against Stage A (hash binding plus authorization,
via `freeze.verify_stage_b`) and Stage A against the running code,
environment, checkout and training artefacts (via
`freeze.verify_stage_a`, deep training check by default), and only then
derives the single-manifest view the gates read (`status`,
`confirmatory_authorized`, `environment`, `source_sha256`,
`fitted_model_sha256`). Any failure raises `ValueError`: a forged,
mismatched or unauthorized input is refused, not analysed. The function
never writes an authorized artifact and constructs no
`confirmatory_authorized: true` JSON by hand.

The two fitted-model hashes are kept separate and clearly named in the
handoff: `fitted_model_sha256` is the `fit_fingerprint` of the frozen
M0/M1 coefficients, derived from the verified `fitted_model.json`
(what `verify_frozen_fit` compares), while `fitted_model_file_sha256`
is Stage A's whole-file SHA-256 of `fitted_model.json` (what pins the
file bytes). They are not interchangeable.

The combined analysis input is bound to its frozen sources. The test
run manifest must name this Stage A and Stage B in its `authorization`
record, name the frozen test schedule, be a complete OFFICIAL run, and
carry the test output hash; the combine manifest must list the frozen
training file (Stage A `training.records_sha256`) and that test output
among its inputs, and its `results_sha256` must be the hash of the
supplied records file. The handoff carries the whole binding
(`stage_a_sha256`, `stage_b_sha256`, `training_records_sha256`,
`test_results_sha256`, `test_run_manifest_sha256`,
`combine_manifest_sha256`, `records_sha256`, `records_bound`), and
`analyze_rows` echoes it in the summary under `analysis_handoff`, so
the output itself shows whether the disposition rested on a verified
handoff or on a legacy single manifest. The `--reproducibility-manifest`
flag remains for reviewer and diagnostic use (and for the existing CLI
regression tests, which analyse fabricated populations that no Stage A
can be built over); it is not the official path, and it cannot be
combined with the handoff flags. The official final analysis command
is step 6 above.
