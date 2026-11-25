# Phase 4 — Adversarial Review 01 — Nova attacks Claude's PR #10

Reviewer: Nova (Muse Spark) — AI-driven mathematical discovery / pattern recognition
Author of target: Claude
Target: PR #10 (OM-C001-R2 runner, DRAT checker, UNSAT certification)
Merge commit attacked: **d115ced** (commits ecfad66 DRAT checker,
2dffe37 status/verification semantics + UNSAT certification,
7cbe990 runner)
Dev tip at review time: **f398de6** (merge of Dee's PR #13)
Scope: `lab/om_lab/width_experiment.py` (1415 lines),
`lab/om_lab/proof_check.py`, `lab/om_lab/certify.py`, and the PR #10
changes to `lab/om_lab/solvers.py`, `lab/om_lab/harness.py`, and
`lab/om_lab/analyze_width.py` (`records_to_rows`), plus their tests.
Convention: **executed** = the attack was run and the result
observed; **static** = derived from reading the source.
Claim levels per `docs/RULES.md`: Conjecture / Empirical Observation /
Proved / Lean-Verified.

---

## 0. Execution status

Everything below was run locally on dev f398de6 (Python 3.12.3,
python-sat 1.9.dev25, NumPy, pytest; persistent venv
`~/workspace/om-venv`). **No confirmatory test instance (index
70–99) was executed at any point.** Dry-runs, the confirmatory
*train* split (one instance for the partial-run test, and a full
1960-instance reproduction), and pilot instances only.

What was run:

- Full confirmatory *train* reproduction (1960 instances, workers=2,
  `--keep-certificates`) and a full audit of the reproduced file
  (`--recompute-features --recheck-certificates`).
- Freeze-manifest attacks: 17 tamper cases (all refused) and 10
  unchecked-field bypasses (all authorised).
- Dry-run subset scheduling, a 1-instance partial confirmatory train
  run, a partial combine, direct `run_specs` fault injection, a
  watchdog expiration.
- `integrity_report` / `audit_records` on genuine pilot records with
  corrupted SAT models, None decisions, and never-retained
  certificates.
- `records_to_rows` on legacy (no explicit status) records with
  string booleans, missing keys, and string numbers.
- A synthetic 28-cell population with wrong seeds labelled
  "confirmatory", run through `analyze_rows`, with a true-seed
  control.
- DRAT differential: `om_lab.proof_check.check_drat` vs a separately
  written independent checker (`lab/tests/_nova_independent_drat.py`,
  stdlib only) on genuine CaDiCaL proofs, mutations, transplants,
  12 malformed-syntax cases, RAT/RUP edge cases, deletion cases,
  and 300 random fuzz cases; plus drat-trim (built from source) on
  8 spot-checked cases.
- DPLL branch accounting: `solve_dpll` vs a separately written tiny
  tracer (`lab/tests/_nova_dpll_tracer.py`, one-unit-at-a-time UP)
  on fixtures, 200 random 3-SAT cases with budgets
  {None, 0, 1, 2, 5, 20, 100}, 24 pilot instances, and the
  budget-boundary convention.

What was NOT run:

- No confirmatory test instance, by design (Section 6.3).
- Worker crash via an `exit_code` fault was not executed; only the
  watchdog expiration was (NOVA-PASS-06). The crash path uses the
  same `record_failure` machinery, but that is an inference, not an
  observation.
- Certificate-file substitution was not executed end to end; the
  retained `.drat` files are never read by any tool, so the finding
  (NOVA-R10-15) is by code reading.
- Lean / Gate C items are out of scope for this review.

---

## 1. Findings

| ID | Subject | Severity | Claim level | Disposition |
|---|---|---|---|---|
| NOVA-R10-01 | Freeze guard does not meet B4 (unchecked fields authorise; B4 hash fields absent) | Medium | Empirical Observation | OPEN |
| NOVA-R10-02 | Dry-run subset scheduling: authorised dry run with one index schedules 28, not 840 | Low | Empirical Observation | OPEN |
| NOVA-R10-03 | Partial runs look complete (1-instance train run and partial combine report integrity passed, no partial marker) | Medium | Empirical Observation | OPEN |
| NOVA-R10-04 | Fault-injection guard lives only in `run_split`; direct `run_specs`/`run_instance` applies faults to confirmatory specs | Medium | Empirical Observation | OPEN |
| NOVA-R10-05 | Run/combine-time integrity trusts verification claims; a corrupted SAT model passes `integrity_report` (only `audit` re-verifies) | Medium | Empirical Observation | OPEN |
| NOVA-R10-06 | `integrity_report` raises `TypeError` on `decisions=None` instead of reporting a failure | Low | Empirical Observation | OPEN |
| NOVA-R10-07 | Audit recheck reports "regenerated certificate differs or is invalid" when no certificate was ever retained; proof-hash equality is stricter than validity | Low | Empirical Observation | OPEN |
| NOVA-R10-08 | `read_jsonl` raises a raw `json.JSONDecodeError` on a malformed line | Info | Empirical Observation | OPEN |
| NOVA-R10-09 | `records_to_rows` `bool()` coercion fabricates a certified SAT claim from `satisfiable="false"` (B5.2) | Medium | Empirical Observation | OPEN |
| NOVA-R10-10 | `records_to_rows` raises unhandled `KeyError` on explicit status with no `satisfiable` key | Low | Empirical Observation | OPEN |
| NOVA-R10-11 | `records_to_rows` silently coerces string numbers (`decisions="7"` → 7) | Info | Empirical Observation | OPEN |
| NOVA-R10-12 | Population identity is never validated in the analysis path (B5.1); a fabricated confirmatory population gets PASS | High | Empirical Observation | OPEN |
| NOVA-R10-13 | `make_row` lone-UNSAT default `UNSAT_SOLVER_AGREEMENT_ONLY` overstates (no second solver ran) | Info | Empirical Observation | Fix proposed in this patch, awaiting Dee's review |
| NOVA-R10-14 | Propagation count is implementation-defined; §3.6 pins the branch counter but not the UP interleaving | Medium | Empirical Observation | OPEN |
| NOVA-R10-15 | Retained certificate files are never re-read by audit, so a substituted `.drat` is undetectable | Info | Proved (code reading) | OPEN |

Dispositions follow Gate B (PASS / FAIL / OPEN / N/A). Every finding
above is OPEN: each needs an author fix and an independent approval
before it closes. NOVA-R10-13's fix is proposed in the accompanying
PR #9 repair batch in this same patch (Dee remains the reviewer of
those fixes).

---

## 2. Detailed findings

### NOVA-R10-01 — Freeze guard does not meet B4

**executed. Claim level: Empirical Observation. Severity: Medium.
Disposition: OPEN.**

`check_confirmatory_authorization` checks the experiment, the freeze
schema version, `confirmatory_authorized is True`, a non-blank
`authorized_by`, the source/function/checker/seed-manifest hashes,
the protocol constants, the Python major.minor, and the python-sat
and NumPy versions. All 17 tamper cases were refused (see
NOVA-PASS-03). But B4 (ADVERSARIAL_REVIEW_01 §B4) requires the
freeze to pin the exact code commit, a clean tree, the exact Python
version *and implementation*, the complete dependency manifest, the
checker executable hashes, the protocol doc hash, the amendment doc
hash, the exact execution settings, an independently reproduced
training-record hash, the frozen fitted-model hash, the coordinator
identity/time, and an explicit FROZEN status. Of those, the guard
checks none of the following, and all ten still authorise:

- `status` left as `"DRAFT"` (the status field is never read);
- `authorized_at_utc` set to `None` (never read);
- exact Python version `3.12.9` vs the frozen `3.12.3` (only
  major.minor is compared);
- `python_implementation` set to `"PyPy"` (never read);
- `platform` set to an arbitrary string (never read);
- `matplotlib` version `0.0.0` and `om-lab` version `9.9.9` (only
  python-sat and NumPy are compared);
- `git.commit` set to all zeroes and `lab_dirty` set to `True`
  (git provenance is recorded in the manifest but never checked);
- `runner_version` set to `9.9.9` (never read).

The manifest has no fields at all for the protocol doc hash, the
amendment doc hash, the training-record hash, or the fitted-model
hash, so those B4 requirements cannot be checked even in principle.
Claude's own doc (`docs/phase3/OM-C001-R2_RUNNER.md`) honestly
documents the weaker check, so this is a gap against B4, not a
misrepresentation.

**Reproduction:** `lab/tests/test_nova_runner_attacks.py` —
`test_freeze_unchecked_fields_still_authorise` (10 cases) and
`test_freeze_manifest_has_no_b4_hash_fields`.

**Suggested fix:** check `status == "FROZEN"`, require a non-null
`authorized_at_utc`, compare the exact Python version and
implementation, compare the full package map, compare the git
commit and require a clean tree, and add the four missing hash
fields to the manifest and the check.

### NOVA-R10-02 — Dry-run subset scheduling

**executed. Claim level: Empirical Observation. Severity: Low.
Disposition: OPEN.**

Gate E says a dry run schedules exactly 840 confirmatory test
instances. An authorised dry run with `indices=[70]` schedules 28
(one per cell) and raises no complaint; with `n_values=[30]`,
`a_values=[400]`, `indices=[70]` it schedules 1. Nothing in
`run_split` checks that a dry run (or a run) covers the full
population. This is dry-run only and produces no data, but it means
the dry-run check cannot catch a mis-scoped run.

**Reproduction:** `test_dry_run_subset_schedules_silently`.

**Suggested fix:** in `run_split`, when the population is
confirmatory, require the spec list to be the full population
(1960 train / 840 test) unless an explicit, logged
`--partial` / `--subset` flag is given.

### NOVA-R10-03 — Partial runs look complete

**executed. Claim level: Empirical Observation. Severity: Medium.
Disposition: OPEN.**

A 1-instance confirmatory *train* run (`n_values=[30]`,
`a_values=[426]`, `indices=[0]`, workers=0) reports integrity
passed=True with `n_records == n_expected == 1`, writes the same
`confirmatory_train_results.jsonl` filename and the same manifest
shape as a complete run, and nothing in the manifest marks it
partial. `combine_results` with `require_complete=False` on that
1-of-1960 file likewise reports integrity passed=True with
`n_expected=1` and no failures, and the combined file carries no
partial marker. The downstream `integrity_gates` shape check
(28 cells / 70 train / 30 test) would catch a partial confirmatory
file at analysis time, so the protection against a false
disposition currently rests entirely on that one downstream check.

**Reproduction:** `test_partial_confirmatory_train_run_looks_complete`,
`test_combine_partial_reports_integrity_passed`.

**Suggested fix:** record `n_expected` for the full population and
a `complete: bool` / `n_instances` field in every run manifest and
combined file, and have `combine_results` refuse (or loudly warn
on) a `require_complete=False` combine that is later analysed as
confirmatory.

### NOVA-R10-04 — Fault-injection guard lives only in `run_split`

**executed. Claim level: Empirical Observation. Severity: Medium.
Disposition: OPEN.**

`run_split` refuses fault injection for the confirmatory
population (`ValueError: fault injection is refused for the
confirmatory population`). But the guard is in the wrapper, not in
the layer that executes: a direct `run_specs` call with
confirmatory train specs and an injected `{"raise": True}` fault
applies the fault (ERROR record after 2 attempts, `max_attempts=2`),
and `run_instance` applies faults unconditionally via
`_apply_fault` at its top. Any caller that bypasses `run_split` —
a programming error, a test, a future tool — can inject faults
into a confirmatory run.

**Reproduction:** `test_fault_injection_applies_via_run_specs_for_confirmatory`
(attack succeeds) and
`test_fault_injection_refused_by_run_split_for_confirmatory`
(control).

**Suggested fix:** move the refusal into `run_specs` (and
`run_instance`): refuse a non-empty `fault_injection` whenever
any spec has `population == "confirmatory"`.

### NOVA-R10-05 — Run/combine-time integrity trusts verification claims

**executed. Claim level: Empirical Observation. Severity: Medium.
Disposition: OPEN.**

`integrity_report` checks that a SAT record's
`verification_status` is `SAT_WITNESS_CHECKED` and that the
`verified` flag is consistent with it, but it never re-checks the
model itself. A genuine SAT record whose model is corrupted (one
variable flipped so the model provably stops satisfying the
formula) passes `integrity_report` with `passed=True` and no
failures, because the stored claim still says checked. Only the
separate `audit_records` re-verifies the model, and it does catch
it (`"stored SAT model fails re-verification"`). So the run/combine
path will happily write and merge a record whose certified claim
is false; the audit is a separate, optional step that must be
remembered.

**Reproduction:** `test_corrupted_sat_model_passes_integrity_but_fails_audit`.
Controls: a SAT record with `verification_status="INVALID"` is
correctly rejected by integrity, and an UNSAT record with
`verification_status="UNVERIFIED"` passes integrity with
`verification_gate_ready=False` (see NOVA-PASS-04).

**Suggested fix:** have `integrity_report` (or `run_split` /
`combine_results`) re-verify SAT models against the regenerated
formula, as `audit_records` already does — or document that
run/combine integrity is structural only and that the audit is a
mandatory step before any analysis.

### NOVA-R10-06 — `integrity_report` crashes on `decisions=None`

**executed. Claim level: Empirical Observation. Severity: Low.
Disposition: OPEN.**

A non-ERROR record with `decisions=None` raises
`TypeError: int() argument must be ... not 'NoneType'` from
`total_attempts += int(rec["decisions"])` instead of reporting a
failure. The crash aborts the integrity check rather than
reporting the malformed record. (The sibling hazard in
`analyze_width.integrity_gates` on `float(None)` is DEE-R9-04,
fixed in the accompanying PR #9 repair batch.)

**Reproduction:** `test_integrity_report_crashes_on_none_decisions`.

**Suggested fix:** treat a None `decisions`/`y`/`width` on a
non-ERROR record as a failure naming the record, and continue.

### NOVA-R10-07 — Audit recheck false positive; proof-hash strictness

**executed. Claim level: Empirical Observation. Severity: Low.
Disposition: OPEN.**

`audit_records(..., recheck_certificates=True)` on a `--no-certify`
UNSAT record (no certificate was ever retained; `reference` is
`None`) reports `"regenerated certificate differs or is invalid"`.
The stored certificate is absent, not different; the message
misstates the cause. Related strictness note: the recheck requires
a byte-identical regenerated proof hash, so a different-but-valid
proof would also be flagged as a failure. The audit is
conservative in the safe direction here (it fails rather than
passes a bad certificate), but the message misleads the reader
about what went wrong.

**Reproduction:** `test_audit_recheck_flags_never_retained_certificate`.

**Suggested fix:** distinguish "no stored certificate" from
"stored certificate differs or is invalid", and consider
accepting a regenerated proof that validates even when its hash
differs (with the hash difference reported separately).

### NOVA-R10-08 — `read_jsonl` raises a raw `JSONDecodeError`

**executed. Claim level: Empirical Observation. Severity: Info.
Disposition: OPEN.**

A malformed JSONL line raises a raw `json.JSONDecodeError` with no
file or line context. Loud, not silent, but unhelpful for
diagnosing which input file is corrupt.

**Reproduction:** `test_read_jsonl_malformed_line_raises_raw_error`.

**Suggested fix:** wrap the decode in a `ValueError` naming the
file and line number.

### NOVA-R10-09 — `records_to_rows` `bool()` coercion fabricates a certified SAT claim

**executed. Claim level: Empirical Observation. Severity: Medium.
Disposition: OPEN.**

This is a B5.2 violation, in PR #10's own change to
`analyze_width.records_to_rows`. For a legacy record (no explicit
`status`), the code does `bool(rec["satisfiable"])` and
`bool(rec.get("verified", False))` — and `bool("false")` is `True`
in Python. A record with `satisfiable="false"` and
`verified="false"` becomes a SAT row with `verified=True` and
`verification_status="SAT_WITNESS_CHECKED"`: a fabricated certified
SAT claim, produced from a record that says the opposite. The
explicit-status contradiction check is skipped entirely for legacy
records, so nothing catches it. Likewise `timed_out="false"`
(string) becomes `True`, relabelling a completed SAT row UNKNOWN.
The runner's own records always carry an explicit status and real
booleans, so the runner path is safe; the hole is the legacy path,
which is the documented entry point for older/harness records.

**Reproduction:** `test_records_to_rows_string_false_becomes_certified_sat`,
`test_records_to_rows_string_false_timed_out_becomes_unknown`.

**Suggested fix:** reject non-bool `satisfiable` / `timed_out` /
`verified` values (or parse `"true"`/`"false"` strings
explicitly) instead of passing them through `bool()`; apply the
same strictness to the explicit-status contradiction check.

### NOVA-R10-10 — `records_to_rows` `KeyError` on explicit status without `satisfiable`

**executed. Claim level: Empirical Observation. Severity: Low.
Disposition: OPEN.**

A record with an explicit `status` but no `satisfiable` key raises
an unhandled `KeyError` from `bool(rec["satisfiable"])` instead of
a validation error naming the missing field.

**Reproduction:** `test_records_to_rows_explicit_status_missing_satisfiable_crashes`.

**Suggested fix:** validate the required keys up front and raise a
`ValueError` naming the record and the missing key.

### NOVA-R10-11 — `records_to_rows` silently coerces string numbers

**executed. Claim level: Empirical Observation. Severity: Info.
Disposition: OPEN.**

`int(rec["decisions"])` and `int(rec["n_vars"])` accept strings
(`decisions="7"` → 7), so a malformed record is silently accepted
instead of rejected. `int()` coercion is at least explicit, unlike
the `bool()` case, which is why this is Info rather than Medium.

**Reproduction:** `test_records_to_rows_string_numbers_coerce_silently`.

**Suggested fix:** same strict typing as NOVA-R10-09: reject
non-int numerics.

### NOVA-R10-12 — Population identity is never validated in the analysis path

**executed. Claim level: Empirical Observation. Severity: High.
Disposition: OPEN.**

B5.1 requires strict population-identity validation of raw records
before analysis (experiment, population, split, cell, index, exact
seed, instance id, formula hash, budget, schema version; reject
mixed populations and duplicates). `analyze_rows` checks none of
it, and never calls the runner's audit. A synthetic 28-cell
population with completely wrong seeds (`10^9 + cell*1000 + i`),
labelled "confirmatory", with a strong width→Y signal, gets
disposition **PASS** with point improvement **0.856**, bootstrap
CI lower endpoint 0.849, integrity passed and verification passed —
even with a valid reproducibility manifest, because that gate only
checks the environment. The control is decisive: the identical
rows with the true confirmatory seeds get the identical
disposition and identical evaluation, proving the analysis never
looks at seeds at all.

**Reproduction:** `test_fabricated_confirmatory_population_gets_pass`
in `lab/tests/test_nova_runner_attacks.py`.

**Suggested fix:** validate every record's identity against the
seed manifest (exact seed, formula hash, budget, schema version)
before analysis, and run the runner's `audit_records` (or an
equivalent) as a precondition of a confirmatory `analyze_rows`;
reject mixed populations and duplicates outright.

### NOVA-R10-13 — `make_row` lone-UNSAT label overstates agreement

**executed. Claim level: Empirical Observation. Severity: Info.
Disposition: Fix proposed in this patch, awaiting Dee's review.**

When `verification_status` is not supplied, `make_row` labelled a
lone DPLL UNSAT `UNSAT_SOLVER_AGREEMENT_ONLY`. No second solver
ran at all, so there is no agreement to report; `UNVERIFIED` is
the accurate label. (Claude's own doc, §8.4, already flags this.)
Fixed in the accompanying PR #9 repair batch in this same patch:
the default is now `UNVERIFIED`, with the test updated to assert
it. Dee remains the reviewer of that fix.

**Reproduction:** `test_make_row_lone_unsat_defaults_to_unverified`
in `lab/tests/test_nova_runner_attacks.py`.

### NOVA-R10-14 — Propagation count is implementation-defined

**executed. Claim level: Empirical Observation. Severity: Medium.
Disposition: OPEN.**

Section 3.6 pins the branch-attempt counter ("increments for each
attempted branch value") but says nothing about how propagations
are counted. `solve_dpll` assigns all unit literals from one
simplified snapshot in a batch and counts each newly assigned
variable; an independently written tracer (one unit at a time,
re-simplifying after each) counts differently whenever a conflict
is detected mid-batch: the batch version stops counting at the
next re-simplification, while the one-at-a-time version assigns
the units that became available between snapshot units first.
The disagreement goes in both directions, so it is not an
off-by-one. Measured: decisions/status/model agree everywhere
(200/200 random cases, 24/24 pilot cases, all fixtures, and the
budget-boundary convention), while propagations agree on only
158/200 random cases and 2/24 pilot cases. The primary response
(Y uses decisions only) is unaffected. But ADVERSARIAL_REVIEW_01
§7 requires an independent reproduction to match "branch and
propagation counts": a genuinely independent reproducer will fail
on propagations while agreeing on everything that matters.

**Reproduction:** `lab/tests/test_nova_dpll_tracer.py` —
`test_propagation_counts_differ_across_implementations` (the
divergence is pinned, with a greedily shrunk 13-clause
counterexample in the test comments), plus the strict
decision/status/model agreement tests.

**Suggested fix:** either pin the counting rule in §3.6 (e.g.
"propagations count unit assignments in the frozen batch
implementation's order") or scope the §7 reproduction gate to the
branch-attempt counter and treat propagations as
implementation-defined.

### NOVA-R10-15 — Retained certificate files are never re-read

**static. Claim level: Proved (code reading). Severity: Info.
Disposition: OPEN.**

`run_split` writes per-instance `.cnf` / `.drat` files under
`certificates/`, and the certificate manifest records each proof's
SHA-256. But `audit_records` regenerates every certificate from
the seed and compares hashes; no tool ever opens the retained
`.drat` files. So a substituted or corrupted `.drat` file on disk
is undetectable *and* irrelevant to every check that exists — the
retained files are not the certificate record, the manifest is.
That is fine as long as nobody later treats the files as the
certificates; if an external auditor does, a substitution would
surface only as a hash mismatch against the manifest, and only if
they think to compare.

**Suggested fix:** either verify the retained files against the
manifest in `audit_records`, or document that the manifest (not
the files) is the certificate record of authority.

---

## 3. Independently verified claims (negative results retained)

### NOVA-PASS-01 — Training reproduction is byte-identical

**executed. Claim level: Empirical Observation.**

A full confirmatory *train* run (1960 instances, workers=2,
`--keep-certificates`) reproduced Claude's claimed results file
byte for byte: SHA-256
`0e193993bddc89a09005c5e04d04710189162a59362745a9206d0ce635e08339`,
exactly matching OM-C001-R2_RUNNER.md §5.1. 1960/1960 records, SAT
1097 / UNSAT 863, all UNSAT proof-checked, total branch attempts
248212, max 992, integrity passed, `verification_gate_ready`
True, 0 infrastructure failures. The audit on the reproduced
file (`--recompute-features --recheck-certificates`) passed with
0 failures and 863 certificates rechecked (regenerated with
identical proof hashes, all VALID).

### NOVA-PASS-02 — DRAT checker agrees three ways

**executed. Claim level: Empirical Observation.**

`om_lab.proof_check.check_drat` agrees with a separately written
independent checker (`lab/tests/_nova_independent_drat.py`,
stdlib only, list-based database, fixpoint unit propagation, same
documented DRAT-trim deletion convention, independently
implemented, plus a strict-deletions mode) on every case tested:
genuine CaDiCaL proofs (random 3-SAT, PHP(3), Petersen Tseitin),
mutations (truncate, corrupt lemma, remove empty-clause line,
reverse), wrong-formula and satisfiable-prefix transplants, 12
malformed-syntax cases, RAT/RUP edge cases, deletion cases (unit
ignored, root-reason ignored, applied deletion honoured, missing
deletion ignored+counted), and 300 random fuzz cases. Zero
disagreements. A third checker, drat-trim (built from source),
agreed with both Python checkers on all 8 spot-checked cases.
The strict-deletion mode disagrees in exactly the expected
direction (it rejects a proof that deletes a unit then relies on
it) — a documented sound-incompleteness trade-off, not a bug.
Suite: `lab/tests/test_nova_drat_attack.py`, 29 passed, 1 skipped
(the drat-trim test runs when `OM_DRAT_TRIM` is set; verified
passing with the built binary).

### NOVA-PASS-03 — Freeze tampering is refused

**executed. Claim level: Empirical Observation.**

All 17 tamper cases were refused: draft manifest, string
`"true"`, blank/null `authorized_by`, tampered source hash,
function hash, checker hash, seed-manifest hash, protocol
`budget_b`, protocol `max_seconds`, schema version 99, experiment
mismatch, Python 3.11, python-sat version, NumPy version, and a
missing file. The guard's checked fields work; the gap is only
what it does not check (NOVA-R10-01).

### NOVA-PASS-04 — Status-consistency controls are correct

**executed. Claim level: Empirical Observation.**

A SAT record with `verification_status="INVALID"` is correctly
rejected by `integrity_report`, and an UNSAT record with
`verification_status="UNVERIFIED"` passes integrity with
`verification_gate_ready=False`. The status/verification
consistency checks do what they claim.

### NOVA-PASS-05 — Branch accounting matches the independent tracer

**executed. Claim level: Empirical Observation.**

`solvers.solve_dpll` and the separately written tiny tracer agree
on status, branch attempts (`decisions`), and model on every case
tested: hand-built fixtures (empty CNF, empty clause, unit
contradictions, chains, 2-var parity, 3-var cube, duplicate
literals), PHP and Tseitin fixtures, 200 random 3-SAT cases with
budgets {None, 0, 1, 2, 5, 20, 100}, 24 pilot instances, and the
budget-boundary convention (a run that would finish with exactly
B decisions is UNKNOWN with D == B; with B+1 it completes
identically to the free run). The vendored
`_reference_solvers_ed6d557` copy was NOT used as the oracle: it
is byte-identical code to the thing under test and cannot audit it.

### NOVA-PASS-06 — Watchdog fires; fault injection refused at the CLI

**executed. Claim level: Empirical Observation.**

A worker that sleeps 30 s with a 0.05 s watchdog is killed and the
instance becomes an ERROR record after one attempt. And
`run_split` refuses fault injection for the confirmatory
population (the control for NOVA-R10-04).

---

## 4. What is wrong in the plan (per the brief)

1. **B4 is not implementable as specified by the guard alone.**
   ADVERSARIAL_REVIEW_01 B4 requires the freeze to pin the exact
   code commit, clean tree, exact Python version+implementation,
   complete dependency manifest, checker executable hashes,
   protocol/amendment doc hashes, training-record hash, and
   fitted-model hash. The runner's guard checks a subset and the
   manifest lacks four of the hash fields entirely (NOVA-R10-01).
   Either the guard must be strengthened to B4, or B4 must be
   narrowed to what the guard actually enforces — the current
   state (doc says one thing, code does another) is the worst
   option.
2. **Gate E's "dry run schedules exactly 840" is unenforced.**
   Nothing in `run_split` checks the spec list against the full
   population (NOVA-R10-02), and nothing marks a partial run
   partial (NOVA-R10-03). A mis-scoped run is silent.
3. **B5.1 has no implementation in the analysis path.** The
   analysis accepts any rows labelled "confirmatory" and will
   PASS on fabricated data (NOVA-R10-12). The runner's audit is
   the only identity check, and it is never invoked by
   `analyze_rows`. Until the analysis validates identity (or is
   required to run on audited files only), a confirmatory PASS
   does not establish that the confirmatory population was
   analysed.
4. **§7's reproduction gate is over-specified for propagations.**
   It requires "branch and propagation counts" to match, but the
   propagation count is implementation-defined (NOVA-R10-14).
   Scope the gate to the branch-attempt counter, or pin the
   counting rule in §3.6.
5. **B5.2 is violated by the analysis's own record reader**
   (NOVA-R10-09): permissive `bool()` on unvalidated serialized
   values is exactly what B5.2 forbids, and it fabricates a
   certified claim.

---

## 5. Summary and next steps

- **Strongest parts of PR #10:** the runner reproduces byte for
  byte (NOVA-PASS-01); the DRAT checker agrees with two
  independent checkers on every case, including malformed and
  adversarial proofs (NOVA-PASS-02); the freeze guard's checked
  fields all refuse tampering (NOVA-PASS-03); the branch-attempt
  counter — the preregistered response — matches an independently
  written tracer everywhere (NOVA-PASS-05).
- **Most urgent to fix before any confirmatory run:** NOVA-R10-12
  (analysis accepts fabricated confirmatory data and PASSES),
  NOVA-R10-01 (freeze does not meet B4), and NOVA-R10-05
  (run/combine integrity trusts verification claims). NOVA-R10-09
  (bool coercion) should be fixed in the same pass since it is a
  one-line strictness change in the same reader.
- **Every finding needs an author fix and an independent approval**
  per Gate B; the author of an artifact is never its primary
  reviewer, so Claude (or another agent) fixes PR #10's findings
  and Nova reviews the fixes, while Dee reviews the PR #9
  repairs in this same patch.
- **Tests delivered with this review** (all passing on dev
  f398de6): `lab/tests/test_nova_runner_attacks.py` (46 tests),
  `lab/tests/test_nova_drat_attack.py` (29 passed, 1 skipped),
  `lab/tests/_nova_independent_drat.py` (checker),
  `lab/tests/test_nova_dpll_tracer.py` (7 tests),
  `lab/tests/_nova_dpll_tracer.py` (tracer). Full lab suite: 263
  passed, 3 skipped.
- **PR #9 repairs delivered in the same patch (secondary):**
  DEE-R9-01 (exhaustive integrity failures), DEE-R9-02
  ("bootstrap unavailable"), DEE-R9-03 (M3 1e-12 documented),
  DEE-R9-04 (ERROR rows filtered/counted; None values are gate
  failures), DEE-R9-05 + DEE-R9-20 (one documented
  `PHASE1_SEED_MAX` constant; `phase1_seeds_below_10m` now matches
  its name), DEE-R9-17 (equal-cell-weighted point MAE and
  bootstrap, fixed 30 per cell), DEE-R9-18 (reproducibility gate
  + `--reproducibility-manifest`), DEE-R9-19 (effort-only gated
  on integrity gates). Pilot numbers recomputed with the corrected
  bootstrap: M1 −0.042 (unchanged), M2 +0.167, M3 +0.127, CI
  [−0.084, −0.002] (was [−0.151, +0.051]); the narrowing is
  expected — the pilot cells have only 5 test rows while the
  bootstrap now draws the §3.10 fixed 30 per cell, and the pilot
  CI is illustrative only. Dee's regression tests in
  `test_width_synthetic.py` were updated to assert the fixed
  behaviour, as their class docstring invites. Dee remains the
  reviewer of these fixes.
