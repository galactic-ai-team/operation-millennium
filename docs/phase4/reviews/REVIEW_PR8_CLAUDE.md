# Phase 4 — Adversarial Review 01 — Claude attacks Dee's PR #8

Reviewer: Claude (algorithms & experiment infrastructure lane)
Author of target: Dee
Assignment: `docs/phase4/ADVERSARIAL_REVIEW_01.md` §6.1 (verbatim brief from Lumi, 2026-11-25)
Target: PR #8. Files under attack:
- `lab/om_lab/matched_instances.py`
- `lab/tests/test_matched_instances.py`
- `docs/phase4/STRUCTURAL_COUNTEREXAMPLES.md`

**Commit attacked: PR #8 merge commit `c8e61a7`.** The three target files are byte-identical at `dev` `7fd74bd` and at `dev` `f398de6`. `git diff --stat c8e61a7 f398de6 -- <the three files>` prints nothing. All code was executed on a checkout of `f398de6`, which is the base of this patch.

File location: §6.1 names `docs/phase4/REVIEW_CLAUDE_MATCHED_INSTANCES.md`. Lumi's brief and Dee's precedent (`docs/phase4/reviews/REVIEW_PR9_DEE.md`) use `docs/phase4/reviews/REVIEW_PR8_CLAUDE.md`, so this file follows the latter. Lumi can rename it.

Claim levels follow `docs/RULES.md`: Conjecture / Empirical Observation / Proved / Lean-Verified.

---

## 0. Execution status and verdict

**Everything in this review was executed**, except where a finding is marked *static*. The environment was:
- Python 3.12.3 on Linux x86_64;
- python-sat 1.9.dev25 (CaDiCaL 1.9.5, `cd195`) and numpy 2.5.5, the pins in `lab/constraints-om-c001-r2.txt`.

The full lab suite at `f398de6` plus this patch gives **215 passed, 2 skipped, 10 xfailed**. The 2 skips are the DRAT-trim cross-checks, which look for an external binary; with `OM_DRAT_TRIM` set to a local drat-trim build they pass too (217 passed, 10 xfailed). The 10 xfails are strict markers on OPEN findings. I did not run Lean; the patch changes no Lean file.

The patch was also applied with `git am` to a fresh clone at `f398de6` and re-run in fresh virtual environments on Python 3.12.3 and 3.13.18 with the same pins. Test results were the same, CI's phase-transition smoke and structure checks passed, and the harness outputs were byte-identical (hashes in §2).

Independence:
- I did not author PR #8.
- I authored PR #10, whose `certify.certify_tseitin_by_construction` calls Dee's validators and encoder. One finding (CLAUDE-R8-07) therefore also hits my own code. §2.3 (R8-07) and §6 describe the separately committed fix, which needs Nova's or another reviewer's approval, not mine.

| §6.1 acceptance criterion | Result |
|---|---|
| Every legitimate instance agrees with the independent oracle when solved to completion | **PASS on every instance tested**: 18,336 exhaustive + 1,144 seed-suite + 567 permutation-suite runs, 0 mismatches (R8-01, R8-02, R8-15) |
| Every malformed instance is either rejected or explicitly classified outside the encoder contract | **FAIL — OPEN.** 8 of the 33 attack cases are malformed inputs that Dee's instance validators accept, with no contract classification: 2 get a wrong parity label (M10, M17), 3 carry clauses that differ from the declared system (M01, M08, M11), 2 fail later in the solver (M04, M05), and 1 has wrong but unused metadata fields (M16) (R8-05..R8-09) |
| Unexplained mismatches block approval | **None found.** Every disagreement observed is explained by a malformed input |

**Recommendation.** No blocker affects legitimate generation: every instance the encoder builds from valid input was correct on everything tested. PR #8 cannot pass the second §6.1 acceptance criterion until every accepted malformed case is rejected or explicitly classified outside the contract. That needs R8-05 (High), R8-06 and R8-07 (Medium), and the M16 part of R8-09 (Low). The Medium findings R8-14 and R8-18 should be resolved too. For each, Dee may either fix it in code or classify it explicitly as outside the contract (§4). Per Gate B, Dee may repair, but the repair must be approved by someone other than Dee. I can re-run this review's suite on the repair commit: the strict-xfail tests turn into failures exactly when a fix lands.

---

## 1. Findings

Severity: **Blocker** = wrong result on a legitimate instance, or an unexplained mismatch · **High** = a malformed input is accepted and then gets a wrong satisfiability label · **Medium** = a malformed input is accepted and then misbehaves in another way, a safety check is vacuous, or an Ace ruling is not yet implemented · **Low** = robustness or documentation · **Info** = observation, no action required.
Disposition (Gate B): PASS / FAIL / OPEN / N/A (N/A states its reason).

| ID | Subject | Severity | Claim level | Disposition | Mode |
|---|---|---|---|---|---|
| CLAUDE-R8-00 | Target pinned: `c8e61a7`; files identical at `f398de6` | Info | Empirical Observation (git diff executed) | PASS | executed |
| CLAUDE-R8-01 | All 2^\|V\| charge vectors on 13 cubic graphs ≤ 10 vertices, 3 edge maps: oracle, decoded CNF, PySAT, DPLL and Dee's label agree; all witnesses and refutations check | — | Empirical Observation (exhaustive over the finite set) | PASS | executed |
| CLAUDE-R8-02 | Seed suite on 11 larger graphs (12–32 vertices, incl. registered ladders and disconnected unions): 1,144 instances agree | — | Empirical Observation | PASS | executed |
| CLAUDE-R8-03 | Dee's graph constructors equal independent definitions (Petersen = GP(5,2), girth 5) | — | Empirical Observation | PASS | executed |
| CLAUDE-R8-04 | `moebius_ladder(n)` rejects n = 2, so the registered 4-vertex Möbius ladder (DISCOVERY_ROUND_01 §5.4) cannot be generated | Low | Empirical Observation | OPEN | executed |
| CLAUDE-R8-05 | No clause or charge integrity check: instances whose clauses disagree with their graph/charges pass `validate_graph` + `validate_metadata`, and two get a **wrong parity label** | High | Empirical Observation | OPEN | executed |
| CLAUDE-R8-06 | Edge-map integrity unchecked: swapped or duplicated `edge_ids` pass both validators, and Dee's own `validate_tseitin_assignment` then **rejects a genuine model** | Medium | Empirical Observation | OPEN | executed |
| CLAUDE-R8-07 | `encode_tseitin` accepts float or bool edge ids and unbounded ids; solvers later reject the instance. Cross-impact: my PR #10 certifier labelled such odd instances UNSAT_KNOWN_BY_CONSTRUCTION | Medium | Empirical Observation | OPEN (certifier fix included, needs independent approval) | executed |
| CLAUDE-R8-08 | `components()` silently drops out-of-range edges; `validate_metadata` and `is_parity_satisfiable` never validate the graph, so the label flips on a hand-built instance | Low | Empirical Observation | OPEN | executed |
| CLAUDE-R8-09 | Metadata: `n_vertices`, `n_edges` and `family` are never checked; caller metadata silently overrides computed fields; the metadata dict is mutable inside the frozen instance | Low | Empirical Observation | OPEN | executed |
| CLAUDE-R8-10 | `encode_tseitin(validate=False)` still validates; the flag has no effect | Info | Empirical Observation (M25 + code reading) | OPEN | executed |
| CLAUDE-R8-11 | 18 malformed constructions are correctly rejected (§2.3 table) | — | Empirical Observation | PASS | executed |
| CLAUDE-R8-12 | Disconnected even-total / odd-component and every A5 case are labelled correctly | — | Empirical Observation | PASS | executed |
| CLAUDE-R8-13 | A3 primal and incidence signatures, counts, clause-length multiset and per-variable ± occurrences are exactly equal on 18,048 matched pairs | — | Empirical Observation | PASS | executed |
| CLAUDE-R8-14 | `generate_matched_tseitin_pair`'s pair assertions compare the graph with itself: a deliberately broken XOR3 encoder passes them; the A3 signatures catch it | Medium | Empirical Observation (mutation test) | OPEN | executed |
| CLAUDE-R8-15 | Registered permutation suite (A2), 567 runs: statuses agree with the oracle, transformed witnesses hold, the recorded (π, ρ) witness isomorphism, DPLL reproducible | — | Empirical Observation | PASS | executed |
| CLAUDE-R8-16 | A6 statistics on the registered ladders: R = 1.00 in all 27 cells; DPLL counts are r (even) and 2^(r+1) − 2 (odd). The pattern fails on other cubic graphs (reproducible counterexamples), so no general claim is made | Info | Empirical Observation | N/A (exploratory result, not a defect) | executed |
| CLAUDE-R8-17 | `permute_matched_pair` is a correct relabelling (49/49) but does not record the induced edge-ID bijection that A2 requires; the A2 registered protocol is not in the module | Low | Empirical Observation | OPEN | executed |
| CLAUDE-R8-18 | Duplicate production min-fill (rulings A1, B6): agrees on all 189 Tseitin-ladder labellings but disagrees with Nova's canonical `primal_min_fill_width` on 7/1000 random 3-SAT formulas | Medium | Empirical Observation | OPEN | executed |
| CLAUDE-R8-19 | Docs label "connected: satisfiable iff total charge even" Proved but cite only the summation argument (the *only if* direction) | Low | Empirical Observation (static reading) | OPEN | static |
| CLAUDE-R8-20 | Both Python XOR3 encoders reproduce the Lean fixtures `xor3CNF_dimacs_true/false` exactly | Info | Empirical Observation (fixture text parsed from `Tseitin.lean`) | PASS | executed |
| CLAUDE-R8-21 | DISCOVERY_ROUND_01 §6 and §6.1 path decompositions are valid on all registered sizes (ladder width ≤ 5; primal width ≤ 12 ≤ 17) | Info | Empirical Observation (finite check, not a proof review) | PASS | executed |
| CLAUDE-R8-22 | STRUCTURAL_COUNTEREXAMPLES.md and Dee's tests do not cover invalid endpoints, missing clauses, edge-map integrity or non-integer ids, and test only one metadata field | Low | Empirical Observation (static reading) | OPEN | static |
| CLAUDE-R8-23 | `solver_effort()` reports `verified` from an uncertified PySAT call; after PR #10 that is False for every UNSAT instance | Info | Empirical Observation | OPEN | executed |
| CLAUDE-R8-24 | DISCOVERY_ROUND_01 §5.2 statements 1–6: proof read line by line, no gap found; consistent with the 18,048 pairs of R8-13 | — | Proved — elementary; independently reviewed here | PASS | static + executed |

---

## 2. Detailed findings

Reproduction for every item, from `lab/`:
- `python -m om_lab.review_pr8 --out-dir /tmp/review_pr8` runs the full suite (about 70 s). It writes `review_pr8_report.json` and `permutation_suite_log.jsonl`. With all three commits of this patch, their SHA-256 hashes are `5d53579008bf90110fabd6d68980ca842251fb241dfbe037b0c8390ce6fe1b96` (report) and `cbc17d554c60aec5b1335421cc73bcd9d08e56e04c715b3d05aef035fd6134ff` (log). Without the certifier commit, the report's M04/M05 certifier entries change (§2.3), so only the log hash still applies.
- `pytest -q tests/test_review_pr8_matched_instances.py tests/test_parity_oracle.py` runs the CI-sized subset (about 11 s).

### 2.1 The independent oracle (`lab/om_lab/parity_oracle.py`)

The oracle builds the parity system **from endpoints and charges only**: one GF(2) variable per listed edge, one equation per vertex. It decides consistency by **Gaussian elimination**. It never looks at connected components, so it does not reuse `parity_obstruction`. Every answer carries a certificate that a few lines of code can check:
- a satisfiable system returns an edge assignment, checked against the endpoint list;
- an unsatisfiable system returns a vertex set S whose equations sum to 0 = 1: every edge has an even number of endpoints in S, and the charges of S are odd. (Summing the equations of S over GF(2), every edge variable appears an even number of times, so the left side is 0 while the right side is 1.)

`decode_xor_cnf` recovers XOR constraints from **clauses alone**, with no graph and no metadata. Comparing them with `expected_constraints(graph, charges, edge map)` detects a CNF that does not encode its declared system.

The oracle module imports only the standard library. Its correctness is itself only Empirical Observation: `tests/test_parity_oracle.py` checks it against exhaustive enumeration of every edge assignment, on 8 fixed graphs and 150 random multigraphs (self-loops and parallel edges included; every charge vector, 3,933 in all).

### 2.2 Legitimate instances (CLAUDE-R8-01, R8-02, R8-03, R8-12, R8-13)

**R8-01 — exhaustive.** 13 cubic graphs with at most 10 vertices:
- connected: K4, K3,3, prism3, Möbius ladders on 4/6/8/10 vertices (4 = K4 by the §6 definition), prism4 (cube), prism5, Petersen;
- disconnected: K4+K4, K4+K3,3, K4+prism3.

Every charge vector (6,112) was run under 3 edge maps: default, a seeded shuffled bijection, and sparse ids 3i+7. That gives 18,336 instances. For each instance:
- five status sources agree: GF(2) oracle, GF(2) on the decoded CNF, PySAT `cd195` to completion, unbudgeted DPLL, and Dee's `is_parity_satisfiable`;
- the decoded CNF equals the declared system;
- the oracle witness satisfies the CNF and Dee's `validate_tseitin_assignment`;
- every PySAT model satisfies every vertex equation;
- every refutation checks and is a union of components, and Dee's obstruction is non-empty whenever the oracle refutes.

**0 mismatches.** The SAT counts are exactly half of the vectors on connected graphs and exactly a quarter on two-component unions.

**R8-02 — seed suite.** 11 graphs with 12–32 vertices:
- Möbius 12/16/20/24/32 and prism6/prism8;
- disconnected: K4+K4+K4, K4+Petersen, Petersen+Petersen, Petersen+Möbius6.

Documented vectors:
- all-zero;
- every single-vertex charge;
- one charge per component (disconnected graphs only);
- two charges inside component 0;
- 32 vectors from `random.Random(f"OM-P4-R8|{graph}|{seed}")`, seeds 0–31. String seeding is deterministic.

Each was run under 2 edge maps, giving 1,144 instances: **0 mismatches**.

**R8-03.**
- K4, K3,3, prism3 and two-K4 equal independent rebuilds.
- Dee's Petersen edge set equals GP(5,2), and its girth is 5. A cubic graph on 10 vertices with girth 5 is the Petersen graph (known: the unique (3,5)-cage).
- `moebius_ladder(k)` equals the §6 definition for k = 3…16.

**R8-12.** The A5 cases are correct (attack cases M26–M30 below), as are all 256 + 1,024 + 1,024 charge vectors (× 3 edge maps) on the disconnected unions in R8-01:
- two K4, one charge each (even total, both components odd): UNSAT;
- zero charged components: SAT;
- one odd component: UNSAT;
- two charges in the same component: SAT;
- empty graph: SAT.

**R8-13.** I implemented the A3 definitions independently: primal signature, incidence signature, variable and clause counts, clause-length multiset, and per-variable positive/negative counts. I checked them on every matched pair `generate_matched_tseitin_pair(G, base, flip)`, for every even base charge and every flip vertex on the 10 connected graphs above. That is **18,048 pairs, all exactly equal**. Dee's own test confirms the absolute 4 positive / 4 negative occurrences per variable, and it passes.

### 2.3 Attack matrix (CLAUDE-R8-05..R8-12)

`review_pr8.malformed_cases()` builds each case and then applies Dee's instance-level validators, `validate_graph(..., require_cubic=True)` and `validate_metadata`. If the case survives, Dee's parity label is compared with the CNF's PySAT status, and the decoded CNF with the declared system. The test `test_attack_matrix_matches_review_table` pins the table.

| Case | Attack (§6.1) | Construction | Outcome |
|---|---|---|---|
| M01 | incorrect edge mapping | edge_ids of two edges swapped after encoding | **accepted**; label right; CNF ≠ declared system; Dee rejects a genuine model (R8-06) |
| M02 | incorrect edge mapping | wrong-length edge_ids | rejected at encode |
| M03 | incorrect edge mapping | id 0 | rejected at encode |
| M04 | incorrect edge mapping | float ids | **accepted**; solver rejects the float literals (R8-07) |
| M05 | incorrect edge mapping | bool id `True` | **accepted**; solver rejects the bool literal (R8-07) |
| M06 | incorrect edge mapping | sparse positive ids | accepted, correct (legitimate; isolated declared variables) |
| M07 | duplicate edge IDs | repeated id at encode | rejected at encode |
| M08 | duplicate edge IDs | repeated id, hand-built | **accepted**; CNF ≠ declared system (R8-06) |
| M09 | missing clauses | odd minus one clause, stale metadata | rejected (`n_clauses` mismatch) |
| M10 | missing clauses | odd minus one clause, `n_clauses` refreshed | **accepted; Dee label UNSAT, CNF SAT** (R8-05) |
| M11 | missing clauses | duplicated clause, refreshed | **accepted**; semantically harmless, not an exact encoding (R8-05) |
| M12–M15 | corrupted charge metadata | `charge_sum_mod2`, `component_charge_parities`, `n_vars`, `n_clauses` | rejected by `validate_metadata` |
| M16 | corrupted charge metadata | `n_vertices`/`n_edges`/`family` wrong | accepted; fields never read (R8-09) |
| M17 | corrupted charge metadata | `charges` say odd, clauses encode even, metadata recomputed | **accepted; Dee label UNSAT, CNF SAT** (R8-05) |
| M18 | corrupted charge metadata | caller metadata overrides `charge_sum_mod2` at encode | encode accepts silently; `validate_metadata` rejects later (R8-09) |
| M19, M20 | invalid endpoints | endpoint 9 / −1 at encode | rejected at encode |
| M21 | invalid endpoints | prism3 CNF, graph rungs re-pointed to vertex 9, metadata recomputed | rejected by `validate_graph`, **but** `validate_metadata` alone passes and `is_parity_satisfiable` says UNSAT while the CNF is SAT (R8-08) |
| M22–M24 | repeated graph edges | K4 + parallel edge; cubic triple-edge multigraph; self-loop | rejected at encode |
| M25 | repeated graph edges | non-cubic with `validate=False` | rejected at encode (flag has no effect, R8-10) |
| M26–M30 | disconnected even-total / odd-component | A5 cases and empty graph | accepted, correct (R8-12) |
| M31 | generator scope | `moebius_ladder(2)` | rejected; this is a **legitimate registered input** (R8-04) |
| M32, M33 | generator scope | matched pair on a disconnected graph; odd base charge | rejected by the generator's explicit checks |

Totals: 12 rejected at construction (one of them, M31, is a legitimate input; R8-04), 7 rejected by a validator, 7 accepted and correct, 3 accepted but inconsistent, 2 accepted with a downstream failure, **2 accepted and mislabelled**.

**CLAUDE-R8-05 (High).** No function in `matched_instances` checks that `clauses` equal `encode_tseitin(graph, charges, edge_ids)`. `validate_metadata` checks four metadata fields against `charges` and `graph`, never against the clauses. Consequences:
- **M10:** an odd Petersen instance with one clause removed and `n_clauses` refreshed passes `validate_graph` + `validate_metadata`. `is_parity_satisfiable` says UNSAT, but PySAT finds a model and the oracle on the decoded CNF agrees.
- **M17:** the same holds for an instance whose `charges` field disagrees with its clauses.

Neither is rejected, and nothing in the module or STRUCTURAL_COUNTEREXAMPLES.md classifies hand-built or edited `TseitinInstance` objects as outside the contract. §6.1 acceptance therefore fails on these cases. Mitigations:
- No legitimate instance is affected.
- PR #10's `certify.certify_tseitin_by_construction` re-encodes and compares. It returns INVALID for M01, M08, M10, M11 and M17, and labels no accepted malformed case UNSAT_KNOWN_BY_CONSTRUCTION (`test_r8_05_pr10_certifier_rejects_integrity_attacks`). For M04 and M05, which are even instances, it returns NOT_APPLICABLE without this patch's certifier commit and INVALID with it.

**CLAUDE-R8-06 (Medium).** Same root cause, for the edge map. In M01, a hand-built instance with two `edge_ids` swapped passes both validators. A genuine model of the CNF is then **rejected** by Dee's `validate_tseitin_assignment`: the model is an even subgraph through one of the swapped edges, constructed with the oracle and chosen so that the two swapped variables differ. A first probe with the all-false model passed only because both swapped variables were False. M08 (duplicate ids in a hand-built instance) is also accepted.

**CLAUDE-R8-07 (Medium).** `encode_tseitin` checks that edge ids are positive and distinct, not that they are integers. M04 (float ids) produces clauses like `(-1.0, -2.0, -3.0)` and `n_vars = 6.0`. M05 (`True` as an id) produces bool literals. Both pass `validate_metadata` and are then rejected by `om_lab.solvers.normalize_cnf`. Unbounded ids are also accepted: `edge_ids=(…, 10**7)` declares 10^7 variables, and `primal_graph` / `min_fill_width_estimate` then allocate one dict entry per declared variable.

**Cross-impact on my PR #10.** `certify_tseitin_by_construction` re-encodes with the same ids, so the clauses match and odd float- or bool-id instances were labelled UNSAT_KNOWN_BY_CONSTRUCTION (executed). This patch's last commit makes the certifier require a well-formed integer CNF first, with the regression test `test_tseitin_construction_certificate_rejects_non_integer_identifiers`. Nova (PR #10's reviewer) or another approver must approve it, not me. The root fix belongs in `encode_tseitin`.

**CLAUDE-R8-08 (Low).** `components()` skips any edge whose endpoint is out of range, without an error. `component_charge_parities`, `parity_obstruction`, `is_parity_satisfiable` and `validate_metadata` all compute on that silently reduced graph.

In M21, the CNF is the valid prism3 encoding with charges (1,0,0,1,0,0), which is connected with even total, so SAT. The three rungs are re-pointed to vertex 9, and the metadata is recomputed. `components()` then sees two triangles, each with odd charge. `validate_metadata` passes and the label is UNSAT. `validate_graph` does reject the instance, so this matters only to a caller that skips it. `components()` should raise instead.

**CLAUDE-R8-09 (Low).**
- `validate_metadata` never reads `n_vertices`, `n_edges` or `family` (M16).
- `encode_tseitin(metadata=...)` lets the caller overwrite computed fields without error; only the four checked keys are caught later (M18).
- The metadata dict can be mutated in place inside the frozen `TseitinInstance` (`test_r8_09_metadata_dict_is_mutable_inside_frozen_instance`).

**CLAUDE-R8-10 (Info).** Lines 280–304: `validate=False` skips `validate_graph`, but the unconditional `validate_incidence_multiplicities` call repeats every check except connectivity, which is not required here anyway (M25). The flag is misleading; remove it or document it.

**CLAUDE-R8-11.** Correctly rejected (18 cases):
- at encode: M02, M03, M07, M19, M20, M22–M25;
- by a validator: M09, M12–M15, M18, M21;
- by the generator: M32, M33.

The cubic triple-edge multigraph (M23) is rejected as a duplicate edge. That matches the module's simple-graph scope (STRUCTURAL_COUNTEREXAMPLES.md lists duplicate edges as a negative case); the oracle would treat it as a valid parity system.

### 2.4 Matched-pair structure (CLAUDE-R8-14, R8-17, R8-24)

**R8-14 (Medium).** `generate_matched_tseitin_pair` asserts that `even.graph.unsigned_signature() == odd.graph.unsigned_signature()` and that the edge-id tuples are equal. Both members are encoded from the *same graph object* with the *same default ids*, so these assertions cannot fail. They compare nothing CNF-level.

Mutation test (`review_pr8.mutation_probe`): one rhs=1 clause of `xor3_clauses` was patched to replace its third literal with the negation of its second. `generate_matched_tseitin_pair(k4())` still **passed** its assertions. The A3 incidence signature and occurrence profile detected the break. No pair-level validator exists. Recommendation: assert the A3 signatures in the generator, or in a `validate_matched_pair`.

**R8-17 (Low).** `permute_matched_pair` re-encodes the permuted graph with *regenerated default ids*. I recomputed the induced edge bijection and checked, over 7 graphs × 7 permutations:
- both members' decoded constraints map exactly through it;
- the charges move consistently;
- `flipped_vertex` moves consistently.

It is a correct relabelling in **49/49** cases. However, A2 requires a vertex permutation to "induce a documented edge-ID bijection", and the function returns none (**0/49**). The A2 variable/clause permutation protocol (seeds 100–119) exists only in this review's harness, not in `matched_instances`.

**R8-24 (PASS).** I read the proofs of DISCOVERY_ROUND_01 §5.2 statements 1–6 line by line and found no gap:
- the odd-charge argument sums all vertex equations and needs no connectivity;
- with Dee's clause layout (vertex v at positions 4v…4v+3, each clause containing all three variables), the incidence graphs are *identical*, not merely isomorphic.

R8-13 is consistent with every statement on 18,048 pairs. This serves Gate C's "Matched structural claims are independently reviewed" for §5.2 from the implementation side. It is a reading, not a formal check.

**R8-19 (Low, static).** The module docstring and STRUCTURAL_COUNTEREXAMPLES.md state "for a connected graph, the system is satisfiable over GF(2) iff the total charge is even" and label it Proved. The only argument given is that every edge is counted twice, which proves only the *only if* direction. The *if* direction needs the spanning-tree construction in Ace's A5. Cite it, or state only the direction that is proved. Every even-component instance in R8-01 and R8-02 has an oracle-constructed witness, which is empirical support only.

### 2.5 Registered permutation suite and A6 statistics (CLAUDE-R8-15, R8-16)

The protocol is exactly A2. For each seed in 100–119:
- π = `random.Random(2·seed)` shuffles the sorted declared ids;
- ρ = `random.Random(2·seed+1)` shuffles the clause positions;
- the permuted clause j is the original clause ρ[j];
- literal order and signs are preserved;
- the same (π, ρ) is applied to all three charge variants of a graph.

The registered Möbius ladders have V ∈ {4, 6, 8, 10, 12, 16, 20, 24, 32}. The charge variants follow §5.4, using `hard_instances`' vertex choices: zero; one (vertex 0); two (vertices 0, 1). With the identity labelling added, that is 9 × 3 × 21 = **567 runs**. Both permutation arrays are retained in the log (`permutation_suite_log.jsonl`, SHA-256 `cbc17d554c60aec5b1335421cc73bcd9d08e56e04c715b3d05aef035fd6134ff`, byte-identical across runs and Python versions). The DPLL budget is B = 10,000, the value ruling B1 retains for OM-C001-R2. §5.4 asks only for a deterministic budget, so applying B1's value here was my choice.

**R8-15 (PASS).** In all 567 runs:
- PySAT status equals the oracle;
- DPLL never contradicts the oracle. It is UNKNOWN only for the odd variant at V = 24 and 32: 42 runs, which A6 counts as incomplete, not incorrect;
- the transformed witness satisfies the permuted CNF in every SAT run;
- the recorded (π, ρ) reproduces the permuted primal and incidence signatures from the original;
- A3 equality holds across the variants after the shared permutation;
- a repeated DPLL run gives identical status, branch count, propagations and budget classification (A6 reproducibility).

**R8-16 (Info; §5.4 is exploratory and registers no confirmatory effect-size claim).** Y = ln(1 + min(D, B)).

| V | identity D (zero / one / two) | median Y over 20 seeds (zero / one / two) | IQR | budget hits (one) | R | Y_one − Y_zero (median) |
|---|---|---|---|---|---|---|
| 4 | 3 / 14 / 3 | 1.39 / 2.71 / 1.39 | 0 | 0/20 | 1.00 | 1.32 |
| 6 | 4 / 30 / 4 | 1.61 / 3.43 / 1.61 | 0 | 0/20 | 1.00 | 1.82 |
| 8 | 5 / 62 / 5 | 1.79 / 4.14 / 1.79 | 0 | 0/20 | 1.00 | 2.35 |
| 10 | 6 / 126 / 6 | 1.95 / 4.84 / 1.95 | 0 | 0/20 | 1.00 | 2.90 |
| 12 | 7 / 254 / 7 | 2.08 / 5.54 / 2.08 | 0 | 0/20 | 1.00 | 3.46 |
| 16 | 9 / 1022 / 9 | 2.30 / 6.93 / 2.30 | 0 | 0/20 | 1.00 | 4.63 |
| 20 | 11 / 4094 / 11 | 2.48 / 8.32 / 2.48 | 0 | 0/20 | 1.00 | 5.83 |
| 24 | 13 / budget hit / 13 | 2.64 / 9.21 / 2.64 | 0 | 20/20 | 1.00 | 6.57 (capped) |
| 32 | 17 / budget hit / 17 | 2.89 / 9.21 / 2.89 | 0 | 20/20 | 1.00 | 6.32 (capped) |

All 20 contrasts are positive in every cell. Y_one − Y_two equals Y_one − Y_zero, because the two even variants have equal effort.

- **Empirical Observation.**
  - On every registered ladder, each of the 20 permutations gives the identity labelling's exact branch count, so R = 1.00 and IQR = 0. The permutations are genuinely non-trivial: at V = 12, seed 100, π fixes 1 of 18 variables and ρ fixes 4 of 48 clauses.
  - Even variants use D = V/2 + 1, which is the cycle rank r. The odd variant uses D = 2^(r+1) − 2 up to V = 20.
  - The contrast *shrinks* from V = 24 to V = 32 only because the odd runs are capped. A6 warns that capped R describes capped effort only.
- **Extended probe** (`review_pr8.cycle_rank_probe`, same seeds and charge variants, budget 200,000).
  - The same equalities hold on K4, K3,3, prism3–6 and Petersen.
  - On disconnected graphs the odd variant *is* permutation-sensitive: K4+K4 gives {14, 126} and K3,3+Petersen gives {30, 2046}. The refutation is either component-local or uses the full tree.
- **The pattern does not generalize.** Before stating anything general I tried to break it, and it broke.
  - Seeded scan (`review_pr8.cycle_rank_random_scan`): 30 random connected cubic graphs for each n ∈ {8, 10, 12, 14, 16} (configuration model), 40 trials per graph. Each trial draws a uniform charge vector and a random (π, ρ) built as in A2.
  - At n = 8 no run deviated (1,200 runs). From n = 10 on, counts differ from r / 2^(r+1) − 2 for satisfiable and unsatisfiable instances alike: at n = 10, 9 of 583 SAT runs and 21 of 617 UNSAT runs (6 of 30 graphs); at n = 16, 50 of 619 and 222 of 581 (28 of 30 graphs).
  - Two pinned 10-vertex examples are bridgeless with girth 3 (`CYCLE_RANK_COUNTEREXAMPLES`; `test_r8_16_cycle_rank_pattern_fails_on_other_cubic_graphs`). The identity labelling gives the predicted count; the registered seeds 100–119 do not. G10a (SAT, r = 6) gives D ∈ {6, 10}, so R = 1.57. G10b (UNSAT, r = 6) gives D ∈ {126, 130, 138, 162}, so R = 1.28.
  - So R = 1 on the registered ladders is a finding about those graphs under this solver, not about Tseitin formulas in general. I state no conjecture.
- **Consequence for §5.4:** on the registered ladders this solver's permutation sensitivity suite is degenerate (R = 1 in every cell), and the matched contrast is a fixed function of V up to the cap. The same suite on other cubic graphs would not be degenerate.

### 2.6 Duplicate min-fill (CLAUDE-R8-18, rulings A1 and B6)

`min_fill_width_estimate` selects by `(missing, degree, id)`. Ruling A1 specifies `(missing edges among current neighbours, id)`, which Nova's canonical `primal_min_fill_width` implements, and requires the elimination ordering to be returned and retained; Dee's function returns only the width.

- They agree on all 9 × 21 = 189 registered-ladder labellings (max width 5 for both).
- On random 3-SAT outside the Tseitin family (`review_pr8.minfill_random_probe`, seeds 0–999, n ∈ [6,18], m ∈ [n, 4n]) they disagree on **7/1000** formulas: Dee's is higher on 6 and lower on 1.
- The smallest disagreement is seed 965 (n = 9, m = 24): Dee 7, Nova 6.
- The pinned example is `generate_random_3sat(11, 23, seed=172)`: Dee 8, Nova 7.

The two implementations are not interchangeable. Rulings A1 (thin wrapper or removal) and B6 (consolidate before the freeze; agree on width, ordering and tie-breaking) are not implemented at `f398de6`, and Gate D requires one canonical production min-fill implementation.

### 2.7 Lean fixture and Möbius bounds (CLAUDE-R8-20, R8-21)

**R8-20.** The fixture lists in `lean/Millennium/Tseitin.lean` theorems `xor3CNF_dimacs_true` and `xor3CNF_dimacs_false` were parsed from the file text. They equal `matched_instances.xor3_clauses(1,2,3,q)` **and** `hard_instances._xor3_clauses(1,2,3,q)` exactly, for q ∈ {0, 1}. The Lean comment attributes the fixture to `hard_instances`, so the repo has two identical Python XOR3 encoders (consolidation optional). This is a fixture correspondence only. It does not extend Lean-Verified status to the Python generator (A4).

**R8-21.** For each registered V, I built the DISCOVERY_ROUND_01 §6 bags B_i = R_0 ∪ R_i ∪ R_(i+1) and checked the vertex, edge and contiguity properties.
- **Ladder bags:** all valid, width 3 at V = 4 and 5 otherwise.
- **Edge-incidence replacement bags** (§6.1), checked on the actual CNF primal graph: valid, width 5 (V = 4), 8 (V = 6), 10 (V = 8) and 12 (V ≥ 10), all ≤ 17.
- Nova's min-fill on the identity CNF gives 4 (V = 4) and 5 otherwise, so the §6.1 bound of 17 holds but is loose.

This is a finite check of the constructions, not a review of the proof for all k.

### 2.8 CLAUDE-R8-04, R8-22, R8-23

**R8-04.** `moebius_ladder(n)` raises for n < 3. Yet §5.4 registers vertex count 4, and the §6 proof covers k ≥ 2. For k = 2, the construction yields K4 with no duplicate edges, and `hard_instances.generate_tseitin_3sat(4)` already accepts it. Relax the guard to n ≥ 2.

**R8-22.**
- The negative-case list in STRUCTURAL_COUNTEREXAMPLES.md covers duplicate edges, self-loops, non-cubic graphs, repeated ids, malformed XOR3 and incorrect charge metadata; among the metadata fields, the tests exercise only `charge_sum_mod2`.
- They do not cover invalid endpoints (the code does reject them), missing or extra clauses, edge-map integrity, non-integer ids, or the other metadata fields.
- This patch's tests cover all of them.

**R8-23.** `solver_effort()` returns `result.verified` from an uncertified `solve_pysat` call (default `certify=False`). Since PR #10's semantics repair, that is False for every UNSAT instance (`UNVERIFIED`). Expose `status` and `verification_status`, or call with `certify=True`, so that consumers do not read `verified` as "SAT".

---

## 3. What this review did not do

- No Lean build or axiom audit. Gemini reviews PR #7; Gate C items about Lean are outside this review.
- Exhaustive enumeration covers only cubic graphs with at most 10 vertices. Beyond that, the seed suite is a fixed finite sample. None of this proves the encoder correct for all graphs.
- The oracle and the harness were written by me, the reviewer. Their own correctness is Empirical Observation (enumeration-based self-tests), and they should be reviewed by someone else as well.
- The A6 numbers depend on my choice of B = 10,000 and on `hard_instances`' charge-vertex choices (vertex 0; vertices 0 and 1). §5.4 and A6 do not fix either.
- The cycle-rank scan samples random graphs. It shows that deviations from the ladder pattern exist; its rates describe that sample only.
- No UNSAT proof certificates (DRAT) were used: unsatisfiability was established by GF(2) refutations (checkable certificates) and PySAT, plus unbudgeted DPLL on the exhaustive set. DRAT-trim ran only in the existing `test_proof_check.py` cross-checks.

---

## 4. Resolution options for the OPEN findings (for Dee; approval by someone other than Dee)

| Finding | Option A (code) | Option B (explicit contract) |
|---|---|---|
| R8-05, R8-06 | Add `validate_encoding(instance)`: integer CNF check, then re-encode from `(graph, charges, edge_ids)` and require equal clauses and `n_vars`. Call it from `validate_metadata` or from a new `validate_instance`. | State in the module docstring and STRUCTURAL_COUNTEREXAMPLES.md that `TseitinInstance` objects are trusted only when produced by `encode_tseitin`. Name `certify.certify_tseitin_by_construction` as the integrity check for anything else. |
| R8-07 | In `encode_tseitin`, require `int` and not `bool` ids (`operator.index`), and optionally bound the ids relative to the edge count. | Document that ids must be ints. |
| R8-08 | Make `components()` raise on out-of-range endpoints, and have the label functions call `validate_incidence_multiplicities`. | Document that the label functions assume a validated graph. |
| R8-09, R8-10 | Validate all metadata fields; reject overrides of computed keys; drop or implement `validate`. | Document. |
| R8-14 | Assert the A3 signatures in `generate_matched_tseitin_pair`. | — |
| R8-17 | Return the induced edge bijection from `permute_matched_pair`, and add the A2 protocol (or import it from the harness). | Document that vertex permutations are not the A2 protocol. |
| R8-18 | Make `min_fill_width_estimate` a thin wrapper around `width_features.primal_min_fill_width` (A1, B6; B6 also asks for a test with tied min-fill choices). | — |
| R8-04, R8-19, R8-22, R8-23 | Small code or doc edits as described above. | — |

When a repair lands, the matching `xfail(strict=True)` test in `tests/test_review_pr8_matched_instances.py` XPASSes, strict mode turns that into a failure, and the marker must be removed. That makes the fix visible to the approver.

---

## 5. Claim ledger

| Claim | Level |
|---|---|
| Legitimate encoder outputs agree with the independent oracle, SAT solvers and Dee's label on every instance tested (R8-01, R8-02, R8-15) | Empirical Observation (exhaustive over the listed finite sets; not a proof for all graphs) |
| The oracle's certificates are sound (a checked witness satisfies the equations; an S summing to 0 = 1 refutes them) | Proved — elementary, direct calculation |
| The oracle implementation is correct | Empirical Observation (enumeration-based self-tests) |
| GF(2) Gaussian elimination decides linear consistency | Proved — standard linear algebra |
| Eight malformed constructions are accepted; two get a wrong parity label (R8-05..R8-09) | Empirical Observation (reproduced by tests) |
| Dee's and Nova's min-fill disagree on specific CNFs (R8-18) | Empirical Observation |
| DISCOVERY_ROUND_01 §5.2 statements 1–6 | Proved — elementary; independently reviewed here by reading (R8-24) |
| Connected Tseitin iff criterion (both directions) | Proved — known characterization; Ace's A5 gives both directions. Dee's docs supply only one (R8-19) |
| DPLL counts r / 2^(r+1) − 2 and R = 1 on the registered ladders, and the same counts on K4, K3,3, prism3–6 and Petersen (R8-16) | Empirical Observation |
| The same counts for every connected cubic graph | **False**: reproducible counterexamples G10a and G10b (Empirical Observation) |
| §6 / §6.1 decompositions valid on the registered sizes (R8-21) | Empirical Observation (finite check) |
| Anything about P vs NP, lower bounds or solver hardness in general | **No claim** |

---

## 6. Files in this patch

- `lab/om_lab/parity_oracle.py`: independent GF(2) oracle, certificate checkers and CNF→XOR decoder (stdlib only).
- `lab/om_lab/review_pr8.py`: attack harness. It contains the independent graph constructors, the legitimate-instance comparisons, A3 signatures, the A2/A6 permutation suite, the attack matrix, the mutation probe, the PR #10 certifier cross-check, min-fill comparisons, the cycle-rank probes and counterexamples, the Möbius decomposition check, the Lean fixture check, and a CLI.
- `lab/tests/test_parity_oracle.py`: oracle self-tests against exhaustive enumeration.
- `lab/tests/test_review_pr8_matched_instances.py`: regression tests for every finding, with strict xfails for the OPEN ones.
- `lab/om_lab/certify.py` + `lab/tests/test_proof_check.py`: the CLAUDE-R8-07 cross-impact fix to my own PR #10 certifier. It is a separate commit: needs Nova's or another reviewer's approval, and Lumi may drop it. It changes `certify.py`, which is in the OM-C001-R2 runner's frozen source list. The freeze manifest must be regenerated after merge (ruling B4). Records of the random-3-SAT experiment are unaffected, because the runner does not call `certify_tseitin_by_construction`.
- `docs/phase4/reviews/REVIEW_PR8_CLAUDE.md`: this review.

PR #8's own files are **not modified**. Repairs are Dee's to make, under independent approval.
