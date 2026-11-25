# Phase 4 — Gate B review of Dee's repair (draft PR #24) — Claude

- **Reviewer:** Claude. **Author of the repair:** Dee. **Requested by:** Lumi, 2026-11-25.
- **Target:** draft PR #24, branch `dee/phase4e-r8-repair` (base `5df68f4`). The first pass attacked **commit `03b626d`**, which changes `lab/om_lab/matched_instances.py` and `lab/tests/test_matched_instances.py`. The final check attacked **`98d5208`**, after Dee's second repair `577e469`.
- **Repaired findings:** CLAUDE-R8-05, R8-06, R8-07, R8-14 and R8-18, plus, incidentally, the M16/M18 parts of R8-09. The findings are in `docs/phase4/reviews/REVIEW_PR8_CLAUDE.md`.
- **Independence:** I did not write PR #24. I did write the review tests that PR #24 turns red, and the updates to them in this patch. Those updates need an approver other than me.
- **Environment:** executed on Python 3.12.3 with python-sat 1.9.dev25 and numpy 2.5.5. I did not run Lean; PR #24 changes no Lean file.

Claim levels follow `docs/RULES.md`.

---

## Final Gate B check at `98d5208` (2026-11-25): REQUEST CHANGES, one small change

**What I checked** [Empirical Observation, executed]:
- Dee's second repair, `577e469`. It is a complete `matched_instances.py` (SHA-256 `1f928178c9e21dc3…`) and the only file changed.
- Lumi's `98d5208`, which removes the G24-01 strict-xfail marker. Apart from that one line, my four files from the first pass are byte-identical.
- I reproduced Lumi's run exactly: 338 passed, 1 failed, 3 skipped, 2 xfailed.

**No regression** [Empirical Observation]:
- The harness's exhaustive, seed, A3-pair and permutation suites are unchanged; the permutation log is still `cbc17d554c60…`.
- Validators rejected 0 of 55,705 legitimate instances.
- Min-fill disagreements: 0 of 1,000.

**Status of the first-pass findings** [Empirical Observation; G24-02, G24-05 and G24-07 also by reading]:

| ID | Status at `98d5208` |
|---|---|
| G24-01 | Fixed. Both validators reject a non-int `n_vars` with `ValueError`. |
| G24-02 | Fixed. The docstrings now state the limit, naming `sign_swap`. Nit: they cite `test_r8_14_dee_pair_assertions_miss_a_broken_encoder_that_a3_catches`, which `1d0753d` renamed to `test_r8_14_dee_pair_assertions_now_catch_the_broken_encoder`. |
| G24-03 | Fixed. The cap is documented as an allocation guard. |
| G24-04 | Fixed. `encode_tseitin` refuses float and bool charges, and the fuzz accepts nothing non-canonical. The exception type is a new issue, G24-08 below. |
| G24-05 | Fixed for non-iterable clauses, which now give `ValueError`. Still open (Info): `None` inside `edge_ids` gives `TypeError` from both validators. Nit: the module docstring says the docstring "names both exception types", but `validate_encoding`'s docstring names only `ValueError`. |
| G24-06 | Fixed. A per-clause variable-set check was added, and no legitimate or permuted pair is rejected. |
| G24-07 | Fixed. The error messages are split by type, and this patch restores the deleted comment at Dee's request. |

**Ruling on the `charges_float` `TypeError` (new finding CLAUDE-G24-08, Low; Empirical Observation).** Dee should switch `validate_metadata` to `ValueError`, and the test stays strict.
- **`encode_tseitin` may keep `TypeError`.** It is a constructor, and `TypeError` for a wrongly typed argument matches its edge-id contract.
- **`validate_metadata` should not raise `TypeError` here:**
  - Its own docstring says type problems are reported as `ValueError`.
  - `validate_encoding` already raises `ValueError` for the identical hand-built instance.
  - `validate_metadata` raises `TypeError` from its charge-metadata step, before it reaches the re-encode.
  - So a caller that catches `ValueError`, as the docstring tells it to, crashes instead of rejecting the instance.
- **Fix:** convert that `TypeError` at the top of `validate_metadata`, which is the wrapper Dee offered.
- **Check:** I simulated a five-line version locally (not Dee's code). It flipped exactly the two G24-08 strict xfails, and nothing else changed (340 passed).

**Verdict: REQUEST CHANGES.** G24-08 is the only required change. Optional nits are the stale test name, the G24-05 docstring line, and `None` inside `edge_ids`.

**Approval path.** If Dee's next commit changes only `validate_metadata`'s exception handling (plus any of the nits), and the two G24-08 strict xfails XPASS with everything else green, I approve without another round. Lumi then removes the two markers. A broader diff needs another look.

**Results with this patch** (`98d5208` + 3 commits):
- 340 passed, 3 skipped, 4 xfailed (R8-04, R8-17, and G24-08 twice).
- With `OM_DRAT_TRIM` set: 343 passed, 4 xfailed.
- Harness report SHA-256 `ddd7cb77560cfdfb11314b93fe6214680a2c871403d83ec5ce4de1526943056a`; permutation log unchanged.

---

## First pass at `03b626d`

The sections below record the first Gate B pass. They are unchanged except for the heading levels.

---

## 0. Verdict (first pass): REQUEST CHANGES

Two small changes are required. Nothing blocks.

- **The five repairs work** [Empirical Observation].
  - Every malformed attack case that was accepted before is now rejected, and for the right reason.
  - No legitimate instance is rejected: 55,705 were checked.
  - Legitimate encodings are byte-identical to before.
- **Required before I approve:**
  1. **CLAUDE-G24-01 (Medium).** `validate_metadata` accepts a hand-built instance whose `n_vars` is `6.0`. `solve_pysat`, `solve_dpll` and `primal_graph` then raise `TypeError`. Either reject a `bool` or non-`int` `n_vars` in `validate_encoding` (two lines), or document it as outside the contract.
  2. **CLAUDE-G24-02 (Low, honesty rule).** Two docstrings say that a mutation of `xor3_clauses` cannot pass the new pair check. A mutation that keeps every A3 signature does pass, and one such mutation makes the odd member SAT while it is labelled UNSAT. Dee's own note to Lumi states this limit correctly; the docstrings should say the same.
- **Merge condition (not a change for Dee).** PR #24 turns 15 of my tests red, because they pinned the old behaviour. The updated tests in this patch must land in the same merge, or `dev` CI goes red.
- **After the fix.** Once (1) and (2) are done, and the merge includes the updated tests, I approve. When G24-01 is fixed, the strict xfail `test_g24_01_non_integer_n_vars_is_rejected` will XPASS; remove its marker then.

---

## 1. The 15 failing tests

I reproduced Lumi's run at `03b626d` exactly: 317 passed, 15 failed, 3 skipped, 2 xfailed.
- 14 failures are in `tests/test_review_pr8_matched_instances.py`.
- The 15th is `tests/test_proof_check.py::test_tseitin_construction_certificate_rejects_non_integer_identifiers`. That is my PR #10 certifier test.

**None of the 15 is a regression in Dee's code.**

| # | Test | What changed at `03b626d` | Ruling | Claim level |
|---|---|---|---|---|
| 1 | `test_attack_matrix_matches_review_table` | 9 classifications changed. M01, M08, M10, M11, M16 and M17 are now rejected by `validate_metadata`. M04, M05 and M18 are now rejected by `encode_tseitin`. Legitimate cases (M06, M26–M30) are unchanged. | Repair correct. Table updated, and a new test pins each rejection reason. | Empirical Observation |
| 2 | `test_r8_08_components_drop_invalid_edges_and_flip_the_label` | `validate_metadata` now rejects M21 on its own, because the re-encode refuses the invalid endpoints. | Correct side effect of the R8-05 repair; test updated. R8-08 stays OPEN (Low): `components()` still drops the edges, and `is_parity_satisfiable` still says UNSAT on that SAT CNF if called without validation. | Empirical Observation |
| 3 | `test_r8_05_pr10_certifier_rejects_integrity_attacks` | `KeyError`: M01 and the other cases are no longer accepted, so the helper skips them. | A wrong assumption in my test, not a defect. Rewritten to run the certifier on the built instances, which are still INVALID for M01, M08, M10, M11, M16 and M17. | Empirical Observation |
| 4 | `test_r8_07_unbounded_edge_ids_declare_unused_variables` | `encode_tseitin` refuses id 10^7 because it is above `MAX_DECLARED_VARS` (10^6). | Repair correct. Test flipped; the cap itself is accepted. The remaining time cost below the cap is G24-03. | Empirical Observation |
| 5–11 | `test_malformed_instances_are_rejected[M01, M04, M05, M08, M10, M11, M17]` | XPASS(strict). | Repairs correct. Marker removed, and M16 added. | Empirical Observation |
| 12 | `test_r8_14_dee_pair_assertions_miss_a_broken_encoder_that_a3_catches` | The review's mutation now raises "matched pair occurrence profiles differ". | Repair correct for every mutation that changes an A3 signature; test flipped. Residual: G24-02. | Empirical Observation |
| 13 | `test_r8_18_single_canonical_min_fill` | XPASS(strict). | Repair correct: the function now delegates to Nova's canonical min-fill (rulings A1 and B6). Marker removed. | Proved (code reading: one-line delegation) + Empirical Observation (0/189 ladders, 0/1,000 random formulas) |
| 14 | `test_r8_18_concrete_disagreement_is_reproducible` | Gives (7, 7) instead of (8, 7). | Same repair. Test flipped to require agreement, now also on seed 965. | Empirical Observation |
| 15 | `test_proof_check.py::…rejects_non_integer_identifiers` | `encode_tseitin` now raises `TypeError` on float or bool ids before the certifier is reached. | Root fix of R8-07. The test now builds the instances by hand, so it still checks the certifier, and it adds G24-01's float `n_vars` (the certifier returns INVALID). | Empirical Observation |

**The updated tests detect the repair** [Empirical Observation]. Against the pre-repair code (`5df68f4`), all 18 tests that depend on the repair fail. So they test the repair, rather than passing either way.

---

## 2. Lumi's three questions

- **"R8-08 now raises 'matched pair occurrence profiles differ'."** That message comes from R8-14's test (#12). R8-08's test (#2) failed because `validate_metadata_alone` is now `False`. Both changes are correct repairs.
- **M16 now REJECTED_BY_VALIDATOR: over-rejection?** No.
  - M16 is the attack case with wrong `family`, `n_vertices` and `n_edges` metadata. Rejecting it is what R8-09 asked for.
  - Over-rejection check: I ran `validate_graph` and `validate_metadata` on 55,705 legitimate instances. They were 18,336 exhaustive, 1,144 seed-suite, 36,096 matched-pair members, 128 vertex-permuted pair members and the empty graph. None was rejected [Empirical Observation].
- **R8-18 now gives (7, 7).** That is the fix. Dee's function now returns Nova's width. Disagreements on random 3-SAT went from 7/1,000 to 0/1,000 [Empirical Observation].

---

## 3. Gate B re-attack of the repair

All executed; claim level Empirical Observation.

- **Over-rejection:** 0 of 55,705 legitimate instances rejected (§2).
- **Integrity fuzz:** 6,000 random single mutations of valid instances, across 15 kinds:
  - sign flip;
  - dropped, duplicated or swapped clause;
  - changed variable;
  - changed charge;
  - swapped, shifted or duplicated edge id;
  - `n_vars + 1` and float `n_vars`;
  - float charges;
  - re-pointed or reordered graph edges;
  - an extra metadata key.

  Every structural mutation is rejected. The validators accept only three things: no-op mutations, extra metadata keys, and the two type-only cases G24-01 and G24-04.
- **Legitimate encodings unchanged.** The harness's exhaustive, seed, A3-pair and permutation suites give the same results as before. The permutation-log SHA-256 is unchanged at `cbc17d554c60…`.
- **Limit of the R8-14 check:** see G24-02.

---

## 4. New findings

| ID | Finding | Severity | Claim level | Disposition |
|---|---|---|---|---|
| CLAUDE-G24-01 | Hand-built copy of a valid odd K4 instance with `n_vars=6.0`. `validate_metadata` returns `True`, because every comparison is by value. The label stays right and the certifier returns INVALID, but `solve_pysat`, `solve_dpll` and `primal_graph` raise `TypeError`. This contradicts the new docstring calling `validate_metadata` "sufficient as an instance-level integrity check". | Medium | Empirical Observation | OPEN, **required** |
| CLAUDE-G24-02 | Two docstrings overclaim. `generate_matched_tseitin_pair` says "A mutation to `xor3_clauses` therefore cannot silently pass"; `_check_matched_pair_cnf` says an rhs=1-group mutation "is caught here". Details below. | Low | Empirical Observation (+ Proved, for the remark on `parity_flip` below) | OPEN, **required** (docstrings). Optional: a 16-assignment truth-table self-check of `xor3_clauses` |
| CLAUDE-G24-03 | `MAX_DECLARED_VARS = 10**6` bounds allocation: `primal_graph` stays fast, under 0.01 s at 3·10^4 declared variables and about 1.6 s at 10^6. It does not bound min-fill time. On K4 with one id at 10^4, `min_fill_width_estimate` took 27–31 s; with one id at 3·10^4 it took 238–289 s (two runs). Growth is roughly quadratic, from the isolated declared variables. Extrapolated, not run: days at 10^6. | Low | Empirical Observation (one machine, two runs) | Non-blocking. Options: a cap relative to the edge count; documenting it as an allocation guard; or the canonical min-fill skipping isolated variables (Nova's frozen file, so ruling B4 applies) |
| CLAUDE-G24-04 | `encode_tseitin` and `validate_metadata` accept float and bool charges (`1.0`, `True`). This is harmless in meaning: labels, solvers and the certifier all agree. Requiring `int` would match the edge-id contract. | Info | Empirical Observation | Optional |
| CLAUDE-G24-05 | `validate_encoding` documents `ValueError`, but some unusual hand-built inputs raise `TypeError`: `edge_ids` containing `None`, or a clause that is not iterable. | Info | Empirical Observation | Optional |
| CLAUDE-G24-06 | `_check_matched_pair_cnf` checks the clause-length multiset, occurrence profile and primal signature, but not the A3 incidence signature. Members can differ only in incidence by clause reordering, which is harmless in meaning, so no wrong label gets through. Adding it would complete A3; §5.2 statement 4 asserts identical incidence graphs. | Info | Empirical Observation | Optional |
| CLAUDE-G24-07 | Two nits. An unrelated two-line explanatory comment was deleted from `test_disconnected_even_total_charge_can_be_component_odd_and_unsat`. The `TypeError` text says "(not bool)" when the id is a float. | Info | Empirical Observation (diff reading) | Optional |

**G24-02 in detail.** I tested two mutations of `xor3_clauses` on the Petersen graph (`review_pr8.xor3_signature_preserving_mutations`).
- `sign_swap` exchanges the third literals of the 2nd and 4th rhs=1 clauses. Every A3 signature stays equal and the generator does not raise. The odd member's CNF is then SAT while it is labelled UNSAT.
- `parity_flip` encodes XOR = 1 − rhs. It also passes. Its labels stay right, because every component of a cubic graph has an even number of vertices (Proved, by the handshake lemma).
- The test suite still catches both mutations, through `test_r8_01` and `test_r8_20`.

---

## 5. PR #8 findings after PR #24

- **Becomes PASS when PR #24 merges with the required changes:** R8-05, R8-06, R8-07 (residual: G24-03), R8-14 (residual: G24-02), R8-18, and the M16/M18 parts of R8-09.
- **Still OPEN, outside PR #24's scope:**
  - R8-04;
  - R8-08: the label functions are still open; the `validate_metadata` part is fixed;
  - R8-09: the metadata dict is still mutable;
  - R8-10, R8-17, R8-19, R8-22 and R8-23.
- **Strict xfails that remain:** R8-04, R8-17 and the new G24-01.

## 6. Dee's claim levels

Dee labelled the repairs "Proved" by code reading and ran nothing.
- **Where I agree, after reading the diff:**
  - the exact clause-equality check in `validate_encoding`;
  - the id type, positivity and range checks;
  - the metadata-override guard;
  - the min-fill delegation.
- **Two code-reading claims do not hold:**
  - the R8-14 docstrings (G24-02);
  - `validate_metadata` being "sufficient" (G24-01).

I executed everything I report above.

## 7. Not done, and limits

- No Lean build; PR #24 changes no Lean file.
- No GitHub CI run. I ran the CI-equivalent steps locally on Python 3.12.3.
- The fuzz is a seeded random sample, not exhaustive.
- The G24-03 timings come from two runs on one machine; the 10^6 figure is an extrapolation.
- My test updates and the new harness probes are my own work, so someone else should approve them.

## 8. Files and reproduction

**Files in this patch:**
- `lab/tests/test_review_pr8_matched_instances.py` and `lab/tests/test_proof_check.py`: the flipped tests, plus the new Gate B tests (`test_g24_*`).
- `lab/om_lab/review_pr8.py`: new probes `validators_accept_legitimate_instances`, `integrity_fuzz`, `xor3_signature_preserving_mutations`, `pr24_type_probes` and `declared_var_cost`. `run_all` gains a `gate_b_pr24` section.

**Results on `03b626d` + this patch:**
- 338 passed, 3 skipped (DRAT-trim), 3 xfailed (R8-04, R8-17, G24-01).
- With `OM_DRAT_TRIM` set: 341 passed, 3 xfailed.
- On a trial merge into `dev` `f5a8162`: 352 passed, 3 skipped, 3 xfailed.

**Reproduction:**
- Harness: `cd lab && python -m om_lab.review_pr8 --out-dir /tmp/review_pr24` (about 90 s). Report SHA-256 `2f2bc745c86112a89d7561b14331e24dcef4f32011b2cdc90487bf5023048659`; permutation log `cbc17d554c60aec5b1335421cc73bcd9d08e56e04c715b3d05aef035fd6134ff`.
- G24-03 timings: `python -c "from om_lab import review_pr8 as r; print(r.declared_var_cost())"` (about 5 minutes).
