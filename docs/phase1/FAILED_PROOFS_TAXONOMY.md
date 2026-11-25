# Failed Proofs Taxonomy and Research Direction

**Operation Millennium | Phase 1 / Phase 5 bridge | Ace (theory lane) | 2026-11-24**

Status: proposed for review, not approved. Intended path: `docs/phase1/FAILED_PROOFS_TAXONOMY.md`. Reviewed `dev` at observed tip `395447601e2cca16481c298c9cc84c0166031822`: `docs/ROADMAP.md`, `docs/RULES.md`, `docs/phase1/LITERATURE_MAP.md`, `docs/phase1/BARRIER_CHECKLIST.md`, `lean/Millennium/Sat.lean`. This is option (a), documentation only. No novel theorem is asserted and no claim is promoted to Lean-Verified. Labels on established results identify cited theorems, not new team proofs or completed team reviews. Proposed definitions, review procedures and project decisions are specifications, not claims of mathematical discovery.

## 1. Research direction — decision memo to Lumi

**Recommendation:** make restricted proof complexity the theory spine; use the SAT lab to generate falsifiable questions, and Lean to validate semantics and bounded results. Treat unrestricted circuit lower bounds as a literature/learning track, not a deadline. Do not set a milestone requiring a solution to P vs NP.

| Phase | Deliverable | Acceptance / stop criterion |
|---|---|---|
| 2 Laboratory | Seeded 3-SAT, graph coloring, pigeonhole, Tseitin, and structured CNFs; paired DPLL/CDCL runs with checked certificates | Exact distribution and solver build recorded; SAT/UNSAT/UNKNOWN distinct; censored timeouts retained; repeat from clean checkout |
| 3 Discovery | Resolution proof metrics; structural features versus density; small exact bounds or restricted algorithm | Freeze statement and proof system before testing; compare against known results; no asymptotic claim from finite data |
| 4 Adversarial | Independent counterexample search, cost ledger, barrier audit, and source/novelty check | A counterexample closes the conjecture as stated; no promotion until every unresolved gap is closed |
| 5 Formal | Finite encoded SAT certificates, resolution checker soundness, coloring-to-SAT reduction, then bit-cost model | Kernel checks, explicit statement and dependencies, no sorry/custom axioms, independent clean `lake build`; semantic correctness is not complexity correctness |

### 1.1 Resolution as a tractable research target

[Claim Level: Proved — established literature] Haken's resolution lower bound [5] and Ben-Sasson–Wigderson's width/size relations [6] establish a mature restricted-model toolkit. Cook–Reckhow [7] show that a polynomially bounded propositional proof system exists iff NP = coNP. This does not say that resolution alone characterizes NP vs coNP. The absence of short proofs in one system does not exclude other proof systems or decision algorithms.

Proposed pipeline: define clauses as finite sets of signed variables, specify whether weakening is allowed, and distinguish tree size, DAG line count, total literal count, maximum clause width, and encoded bits. Implement a tiny exhaustive width-bounded closure for small n, with provenance for each resolvent. Check refutations independently; compare pigeonhole and Tseitin families with matched random controls. Reproduce known examples before claiming novelty. Treat proof logs from CDCL with preprocessing or RAT extensions as their actual proof format, not automatically as pure resolution proofs. An LRAT checker is a useful complementary certificate path [8].

A candidate Phase 5 exercise is the soundness of one resolution inference: if an assignment satisfies both C ∨ x and D ∨ ¬x, it satisfies C ∨ D, by cases on x. Then induct over a finite sequence of axioms and earlier-parent inferences; deriving the empty clause rules out every satisfying assignment. This is a proof plan, not a report of a Lean run. A bounded-width closure exhaustion can establish absence of a proof within a precisely specified finite system only after completeness of the enumerator for that restriction is justified.

### 1.2 Structural experiment with an explicit falsifier

[Claim Level: Conjecture — proposed, untested] On the finite experiment population defined below, adding a deterministic min-fill primal-graph elimination-width upper bound to a density-and-size baseline reduces held-out mean absolute error in predicting log(1 + DPLL decisions) among completed runs, by at least 5%, relative to the baseline. This is a finite, protocol-specific prediction, not a universal property of SAT. Elimination width is an upper bound from a heuristic, not exact treewidth. Failure to attain the registered improvement falsifies this operational hypothesis; report it even if a different feature works.

Protocol: n in {30, 40, 50, 60}; alpha in {3.8, 4.0, 4.2, 4.26, 4.4, 4.6, 5.0}; m=floor(alpha*n+0.5); 100 seeds per cell (0–99), split 0–69 training and 70–99 test. Uniformly choose three distinct variables per clause and independent fair signs, sample clauses with replacement, retain duplicates. Pin PRNG, generator and solver implementation/version, tie-breaking (smallest variable ID for min-fill ties), fixed deterministic decision budget, and timeout policy in the preregistration. Use a fixed least-squares baseline on n and actual m/n (with their interaction and squared density), compare same features plus width; define 5% as MAE_aug <= 0.95*MAE_base with MAE_base > 0. Report per-cell completion, SAT/UNSAT separately, censoring rates, held-out error and stratified uncertainty; if no evaluable test population or baseline error zero, report inconclusive rather than silently changing the protocol. Keep held-out data sealed until implementation and metrics freeze. Any adjustment requires a new labeled experiment and fresh seeds. The completed-only analysis is selection-biased; report a separate budget-hit classification and never generalize to censored runs. Use small initial runs to confirm feasibility on free CPU; do not change the registered population after seeing results.

[Claim Level: Conjecture — literature estimate, not team result] The commonly quoted random 3-SAT threshold near 4.26 is a numerical prediction, not an exact theorem established by the original experiments [9,10]. Use a grid around it; measure SAT probability independently of runtime. Large-k threshold results [11] do not by themselves settle k=3. Separate solver-specific hardness, average-case distributional behavior and worst-case complexity. No empirical observation is claimed here; no runs were performed.

## 2. Audit intake (normative proposal)

Every candidate MUST provide: claim ID and revision; one of the four claim levels in RULES; exact language/problem and input encoding; quantifiers (including uniformity, constants and domain); deterministic/randomized model and cost metric; proof dependency graph with citations; complete algorithm or derivation; ledger for preprocessing, construction, arithmetic, memory, oracle calls, witness recovery and output; scope of each barrier; falsification tests; and reviewer disposition. A mathematical result must explicitly distinguish proof existence, proof search and verification.

Allowed audit dispositions per item: `PASS` (evidence attached), `FAIL` (counterexample or demonstrated gap), `OPEN` (not discharged), `N/A` (reason and exact scope). Unknown is never PASS. Barrier evasion alone is not proof. A restricted result may legitimately relativize or be natural without contradiction; do not reject it merely for that reason.

## 3. Taxonomy of recurring failure modes

### F01 — Relativization and unlicensed diagonalization

[Claim Level: Proved — established literature] Baker, Gill and Solovay [1] constructed oracles A and B for which P^A = NP^A and P^B != NP^B respectively. A proof of either equality or inequality that works relative to every common oracle would contradict one of these worlds.

Failure pattern: diagonalize over polynomial-time machines while silently assuming a uniform polynomial bound for their simulation; or use only black-box simulation and claim an unrelativized separation. A countable enumeration alone does not supply an NP decider for the diagonal language.

Required evidence: specify oracle semantics and show exactly which inference breaks under arbitrary common oracles, or scope the result to a restricted model. For diagonalization, state the enumeration, clock, input length, simulation overhead and membership verifier with one fixed polynomial exponent. Countercheck: if a proof still establishes both its hypotheses and conclusion for every oracle, reject the general claim. Do not infer that every diagonalization argument necessarily relativizes.

### F02 — Hidden exponential LP / SDP / hierarchy lift

Failure pattern: replace Boolean assignments with real variables and call a polynomial-time continuous solver; omit integrality, exponentially many constraints, lift dimension, coefficient encoding or precision. Example: clauses (x∨y), (¬x∨y), (x∨¬y), (¬x∨¬y) yield four linear inequalities of the form sum of literal values >= 1 with x,y in [0,1]. The fractional point (1/2,1/2) satisfies all four, yet each Boolean assignment falsifies one clause. This is a local counterexample to the naive relaxation, not to every LP encoding. Label: [Claim Level: Proved — elementary derivation supplied, pending team review].

Required evidence: two-way feasibility equivalence (or exact objective gap), polynomial lift construction or valid polynomial-time separation oracle, bound on rows/columns or matrix dimension, coefficient bit lengths, memory, required accuracy and recovery. For SDPs distinguish weak/approximate optimization from exact feasibility; justify conditioning, gap and rounding with explicit bounds. At hierarchy level r, n^O(r) is not a fixed polynomial if r grows unboundedly with n; derive the actual total bound. Do not equate exponential constraint count with hardness if a valid efficient separation oracle exists.

[Claim Level: Proved — established literature] Fiorini et al. [4] give a superpolynomial extension-complexity obstruction for exact LP lifts of the TSP polytope. This does not rule out all SDP lifts, all approximations, nonpolyhedral methods or all TSP algorithms. Audit each model separately.

### F03 — Natural proofs: constructivity, largeness and nonconstructive witnesses

[Claim Level: Proved — conditional established literature] Razborov–Rudich [2] obstruct natural properties useful against general polynomial-size circuits under suitably strong pseudorandomness assumptions. The barrier is conditional and is not a blanket obstruction to algorithmic proofs of P = NP or every uniform complexity argument.

Specify a property Q_n of n-input Boolean truth tables (length N=2^n). Audit (i) constructivity in the applicable class on N-bit input (e.g., poly(N)), (ii) density at least 2^{-O(n)} in the relevant formulation, and (iii) usefulness against the specified circuit class (e.g., for each fixed k, eventually excludes circuits of size n^k for an almost-everywhere useful version). Record the exact quantifier convention from the cited theorem, as variants exist. Also identify the explicit target family and prove it has Q_n for the lengths needed by the claimed separation.

Failure pattern A: counting proves most truth tables are hard, then an unspecified choice of a hard table is claimed to define an NP language. Existence does not supply an NP verifier or a uniform construction. Failure pattern B: a hard-function property is defined nonconstructively and later assumed efficiently recognizable. Nonconstructivity can place a property outside the natural-proofs barrier, but does not supply the missing algorithm or explicit lower bound. Failure pattern C: treating a poly(2^n) truth-table test as poly(n) on a succinct circuit description.

Required evidence: explicit property, actual decision algorithm and cost, density argument, target-family membership proof, usefulness proof, PRF security hypothesis and exact scope. If one premise fails, record which; do not claim the barrier is disproved. A proof not meeting the naturalness conditions must still be mathematically complete.

### F04 — Representation, bit-length, uniformity and preprocessing

Failure pattern: count arithmetic operations on unbounded integers/reals as unit time; measure polynomial in an integer's numeric value rather than its bit encoding; hide exponentially many advice bits or lookups. Example: binary M=2^b needs b+1 bits, but M loop iterations take 2^b iterations. A polynomial in M is pseudo-polynomial in the encoded input. Label: [Claim Level: Proved — elementary derivation supplied, pending team review].

Required evidence: fix a finite alphabet and canonical/explicit encoding, use N=|input bits|, give worst-case time <= C(N+1)^d with fixed C,d independent of input, bound intermediate bit lengths and arithmetic cost, construction/preprocessing, output, recursion and memory. State whether advice, randomness, parallelism, oracle access, or exact real operations are allowed. A polynomial-depth search tree need not have polynomially many nodes; polynomial processor time with exponentially many processors is not ordinary polynomial work. Parameterized cost f(k)N^d does not prove membership in P if k is unrestricted. If a subroutine has an unproved cost or requires deciding SAT, leave the main claim OPEN.

### F05 — Algebrization is asymmetric

[Claim Level: Proved — established literature] Aaronson–Wigderson [3] extend relativization using low-degree oracle extensions. For an inclusion C ⊆ D, the relevant algebrizing condition is C^A ⊆ D^{Ã}; for a separation C ⊄ D, it is C^{Ã} ⊄ D^A, over the paper's permitted oracle/extension pairs. Giving the same augmented oracle to both sides is not the defining test.

Failure pattern: assume arithmetization alone escapes the barrier, or certify the wrong symmetric oracle test. Required evidence: write the direction and the correct asymmetric statement, specify field/extension access and uniformity, and identify the precise step that fails in the relevant algebraic oracle model. Non-algebrization is not sufficient for a separation. Apply only to the actual class result covered by [3].

### F06 — Search/verification, quantifiers and model scope

Failure pattern: a witness verifier is mistaken for a solver; an observed solver timeout becomes UNSAT; a proof lower bound is generalized to all algorithms; NP vs P/poly is conflated with P vs NP. A failed heuristic, a finite benchmark and an asymptotic universal lower bound are different propositions. An unrestricted SAT decider claim needs correctness on both yes and no instances and a uniform worst-case bound; SAT search via decision queries requires the query cost and self-reduction to be accounted for. Require exact quantifiers, proof system, language, certificate semantics and both directions of any reduction. Under RULES, no benchmark or AI-generated proof sketch is promoted merely because independent agents agree.

## 4. Phase 5 bridge — finite certificates and reduction contracts

Review of `Sat.lean`: `Assignment := Nat → Bool`; `verifyCertificate φ σ := evalCNF φ σ`; `verifyCertificate_sound` is definitional implication (the hypothesis is the conclusion after unfolding). This is a valid semantic warm-up, not a proof of finite certificate size, executable polynomial cost, or full encoded-language membership. `mem_empty_clause_unsat` and its corollary concern semantics. No compilation is asserted in this review.

Proposed next modules (not delivered code):

1. `Encoding.lean`: explicit binary encoding/decoding with reject-on-malformed behavior; count actual input bits. For sparse variable IDs, sort/deduplicate occurring indices and map them to consecutive IDs, not an array sized by max ID. Prove evaluation correspondence under renaming and bounded encoded witness length. E.g. a one-literal CNF with variable ID 2^b has short binary representation but a dense array indexed by max ID would be exponential in b.
2. `Certificate.lean`: finite Boolean vector indexed by compact support, or explicit association list with uniqueness and coverage checks; prove semantic soundness and completeness relative to existence of a satisfying assignment. Test empty formula, empty clause, duplicate literals, tautological clauses, sparse IDs, malformed/truncated certificates, out-of-range indices. No arbitrary function witness at the executable boundary.
3. `Resolution.lean`: finite sequence of input or resolvent steps, parents strictly earlier; normalized clauses and explicit pivot; checker validates provenance and exact conclusion; prove acceptance of empty clause implies unsatisfiability. Completeness and proof-size bounds are separate obligations; LRAT semantics require additional rules beyond this checker.
4. `Reduction.lean`: bitstring languages A,B; total computable map f, membership equivalence for every bitstring (including malformed source inputs by mapping to a fixed no-instance where needed), and polynomial-time execution in a chosen concrete machine/cost model. First target: explicitly encoded 3-coloring to CNF SAT. Use variables X(v,c) for three colors, at-least-one and pairwise at-most-one clauses per vertex, and negative pair clauses per edge per color. Semantic proof in both directions; explicit vertex/edge list representation; reject invalid encodings and handle self-loops (unsatisfiable). Bound construction and output bits including identifiers. This direction supports the lab; it alone does not prove SAT NP-hard or 3-coloring NP-hard.
5. `Cost.lean`: select a deterministic finite-alphabet machine model (e.g. multitape TM with output) or prove an implementation-cost simulation into it. Define PolyTime(f) by existence of a fixed machine computing f with a step bound C(N+1)^d on every encoded input. Do not define it by attaching an arbitrary cost function unrelated to evaluation. A verifier for L requires a deterministic polytime relation on encoded pairs (x,w), fixed polynomial p with |w| <= p(|x|), and x in L iff an accepted bounded witness exists. Include pair-encoding overhead and rejection of malformed inputs. Reduction composition needs both cost and output-length bounds; semantic equivalence alone is insufficient.

Phase 5 promotion gate: checked-in toolchain/version and `lake build` output from independent clean run; grep/CI for placeholders plus `#print axioms` on named theorem declarations and their dependencies; only RULES-approved standard axioms; explicit review of theorem statement vs intended claim. A theorem about an abstract model is not automatically a theorem about compiled Python or solver behavior. Investigate existing Lean complexity libraries before building a new cost model; pin dependency and license if adopted.

## 5. Suggested corrections to existing Phase 1 documents (separate review)

- `BARRIER_CHECKLIST.md` §3: replace symmetric augmented-oracle question with F05's direction-sensitive test. §2: require the precise strength of cryptographic assumption and property usefulness quantifiers. Add explicit N/A reasoning and do not treat barrier evasion as sufficient.
- `LITERATURE_MAP.md` §3: qualify natural proofs as conditional and circuit-lower-bound-specific; not every P=NP route must separately defeat that barrier. §5: describe 4.26 as a numerical/heuristic location, not an exact theorem. §2: distinguish Cook's original oracle/Turing-reduction formulation from modern SAT many-one NP-completeness; tautology and satisfiability are not interchangeable as languages via a yes-preserving complement operation. These are proposed edits, not changes made to the existing documents.
- `ROADMAP.md` Phase 4: change 'no surviving counterexamples' to 'all proof obligations discharged for promotion'; no finite search certifies a universal statement by itself. Phase 2: require independent UNSAT evidence or mark result unverified; timeout is UNKNOWN.

## 6. Proposed promotion checklist

- [ ] Claim statement, scope and quantifiers frozen; label recorded.
- [ ] Relevant F01–F06 dispositions and proof/cost ledger attached.
- [ ] Counterexamples and negative runs retained with seed and configuration.
- [ ] Literature checked for known results and prior art; citations link to primary/publisher/authoritative records.
- [ ] Independent proof review completed; no mathematical gap hidden in an empirical claim.
- [ ] If Lean-Verified requested: exact theorem, commit, toolchain, build and axiom audit attached.
- [ ] PR targets dev; no main merge without director approval.

## References (records checked; not a full literature-survey revalidation)

[1] Baker, Gill, Solovay, *Relativizations of the P =? NP Question* (1975), SIAM: https://doi.org/10.1137/0204037

[2] Razborov, Rudich, *Natural Proofs* (1997), publisher: https://www.sciencedirect.com/science/article/pii/S002200009791494X

[3] Aaronson, Wigderson, *Algebrization: A New Barrier in Complexity Theory* (2009), author bibliography with paper: https://scottaaronson.com/papers/ ; institutional record: https://cris.huji.ac.il/en/publications/algebrization-a-new-barrier-in-complexity-theory-2/

[4] Fiorini, Massar, Pokutta, Tiwary, de Wolf, *Exponential Lower Bounds for Polytopes in Combinatorial Optimization*: https://arxiv.org/abs/1111.0837

[5] Haken, *The Intractability of Resolution* (1985): https://doi.org/10.1016/0304-3975(85)90144-6

[6] Ben-Sasson, Wigderson, *Short Proofs are Narrow – Resolution made Simple*, ECCC TR99-022: https://eccc.weizmann.ac.il/report/1999/022/

[7] Cook, Reckhow, *The Relative Efficiency of Propositional Proof Systems* (1979), publisher: https://www.cambridge.org/core/journals/journal-of-symbolic-logic/article/relative-efficiency-of-propositional-proof-systems/218048250981F835B4B2A4080205A0BA

[8] Cruz-Filipe, Heule, Hunt, Kaufmann, Schneider-Kamp, *Efficient Certified RAT Verification*: https://arxiv.org/abs/1612.02353

[9] Mitchell, Selman, Levesque, *Hard and Easy Distributions of SAT Problems* (1992), DBLP: https://dblp.org/rec/conf/aaai/MitchellSL92.html

[10] *On the Satisfiability of Random 3-SAT Formulas with k-Wise Independent Clauses* (2025), proceedings: https://drops.dagstuhl.de/storage/00lipics/lipics-vol351-esa2025/html/LIPIcs.ESA.2025.103/LIPIcs.ESA.2025.103.html

[11] Ding, Sly, Sun, *Proof of the satisfiability conjecture for large k*: https://arxiv.org/abs/1411.0650

[12] Cook, *The P versus NP Problem*, Clay official problem description linked from https://www.claymath.org/millennium/p-vs-np/

---

Handoff: place this file at `docs/phase1/FAILED_PROOFS_TAXONOMY.md` on a new branch from dev. GitHub integration returned HTTP 403 when attempting branch creation; no branch, commit, or PR is claimed. Codex CLI and Lean/lake were not available in the local environment. No code, CI, experimental runs, or new Lean verification were performed. Existing docs remain unchanged. Citation records above were checked for this memo, not every entry in the repository literature map. Free resources only; no credentials included.
