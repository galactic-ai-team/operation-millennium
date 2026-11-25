<!-- docs/phase4/reviews/REREVIEW_PR11_LIT_ACE.md -->
# Phase 4 — Independent re-review of repaired PR #11 literature map

Reviewer: Ace — Galactic AI Team
Artifact author: Gemini
Coordinator: Lumi
Date: 2026-11-25
Base: `dev @ f0ac7fc` (PR #18 merged)
Target: `docs/phase3/WIDTH_TSEITIN_LITERATURE.md`
Git blob: `f3603c6ac34834cc10a82d406456f5a2f3284fbe`
Original review: `docs/phase4/reviews/REVIEW_PR11_ACE.md` (base `0f55084`, blob `4b57a6118c68035885a65f05f3d6e8725343d56b`).

**Gate C literature verdict: NOT APPROVED YET.** T12 is accepted and the bulk of the original issues are resolved. The remaining blockers are narrow and correctable; no broad rewrite is required. The new preprint's separately quarantined proof audit is not a blocker for accepting the older literature once its remaining issues are corrected.

## 1. Evidence and disposition conventions

[Empirical Observation] I read the complete supplied repair, matched its Git blob to the file fetched from `f0ac7fc`, and compared the text to the previous 23 findings. I also reran the existing four independent mathematical regression tests: `python -m pytest -q /mnt/data/test_ace_literature_counterexamples.py` returned `4 passed in 0.06s`. These test the earlier counterexamples; they are not a test of the correctness of the repaired prose. No confirmatory SAT seeds or outcomes were accessed. No repository-wide tests or Lean compilation were performed.

I retain prior source-supported approvals where the repaired wording matches them. I additionally reopened primary sources for the changed or high-risk statements, including BSW, Bonet–Galesi, Atserias–Dalmau, Samer–Szeider, Alekhnovich–Razborov, Galesi–Talebanfard–Torán, the regular/general separation, BIW, Pipatsrisawat–Darwiche, Kiesl et al., Buss et al., Urquhart and TR26-332. Some direct PDF requests failed or had incomplete text (the Razborov and Samer–Szeider originals were available through alternate indexed copies); I did not audit every proof line, re-resolve every DOI, or independently recheck every historical note. Bibliographic checks reported by Lumi are not silently counted as mathematical verification by Ace.

- CLOSED: original finding adequately addressed within the accepted scope.
- PARTIAL: substantial repair, but a specified obligation remains.
- STILL OPEN: not independently verified or resolved.

These are review dispositions, not claim levels. Mathematical findings are Proved (ordinary mathematics or established source result); observed file/test/publication evidence is Empirical Observation; untested hypotheses are Conjecture. No literature result is newly Lean-Verified by this review. References to Lean-Verified results rely on the separate independent PR #7 report.

## 2. All 23 original findings

| ID | Target | Status | Claim level | Ruling |
|---|---|---|---|---|
| ACE-R11-01 | T1 | CLOSED | Proved | Original accepted theorem retained with width/size convention. |
| ACE-R11-02 | T2 | CLOSED | Proved | Positive-part gap and n >= 1 now explicit. |
| ACE-R11-03 | T3 | CLOSED | Proved | MGT_n replaces GT_n, polynomial upper bound, consistent variable parameter. |
| ACE-R11-04 | T4 | CLOSED | Proved | Threshold equivalence and k+1 extension family corrected. |
| ACE-R11-05 | T5 | CLOSED | Proved | Both source runtime expressions and supplied decomposition condition restored. |
| ACE-R11-06 | T6 | CLOSED | Proved | Cache model and decomposition-specific guarantee retained. |
| ACE-R11-07 | T7 | CLOSED | Proved (conditional); SETH Conjecture | Deterministic hypothesis and one-bag argument correct. |
| ACE-R11-08 | T8 | CLOSED | Proved | Grid lower bound now derived for unrestricted resolution; original historical wording expressly OPEN. |
| ACE-R11-09 | T9 | CLOSED | Proved | Constant degree, odd charge and linear expansion specified. |
| ACE-R11-10 | T10 | CLOSED | Proved | Positive-part bound and star counterexample retained. |
| ACE-R11-11 | T11 | PARTIAL | Proved | Correct core results; clause-hyperedge multiplicity and derivation bridge need explicit conventions. |
| ACE-R11-12 | T12 | CLOSED | Proved | Exact line-graph formula and correct primary locators; citation repair verified. |
| ACE-R11-13 | T13 | CLOSED | Proved | Separate MGT regular and BIW general upper-bound constructions. |
| ACE-R11-14 | T14 | CLOSED | Proved | Quantifiers and ordering-size parameter match Cor. 3.4 and Thm. 3.10. |
| ACE-R11-15 | T15 | CLOSED | Proved | Idealized CLR versus practical heuristics and DRUP versus DRAT properly separated. |
| ACE-R11-16 | T16 | CLOSED | Proved | Polynomial simulation accepted in standard proof models. |
| ACE-R11-17 | T17 | CLOSED | Proved | Linear-system, explicit-graph and raw-CNF models distinguished. |
| ACE-R11-18 | T18 | PARTIAL | Proved | Encoding correction accepted; pin TS_n(2) odd-n all-one charge and exact expansion convention. |
| ACE-R11-19 | T19 | PARTIAL | Proved; unresolved source obligation OPEN | Linear Res(XOR) size claim removed; Frege/ER core supported, exact Res(XOR) locator still unverified. |
| ACE-R11-20 | Section 1 | PARTIAL | Proved | Correct direction, but loopless scope and clause-indexed multihypergraph need explicit definitions. |
| ACE-R11-21 | Section 4 | PARTIAL | Proved / Conjecture / Empirical Observation | Most overclaims removed; P versus L wording and untested predictor labels need final clarification. |
| ACE-R11-22 | TR26-332 | STILL OPEN | Empirical Observation (publication/theorem statements) | Correctly quarantined; proof audit not performed. |
| ACE-R11-23 | Citation/locator audit | PARTIAL | Empirical Observation | Major locators repaired; explicitly unresolved historical notes and T19 remain, no claim of exhaustive re-verification. |

Totals: 16 CLOSED, 6 PARTIAL, 1 STILL OPEN. Partial findings can contain an accepted mathematical core. Not all open follow-ups block Gate C; see Section 5.

## 3. Closed findings and source checks

### 01–04: BSW, modified ordering and width games

[Proved] T1/T2 retain the source-supported width–size relationships. The positive-part form is safe when unused wide clauses need not occur in a refutation. T3 now distinguishes the bounded-width modified ordering formula and uses ordering size n versus Boolean variable count N. Bonet–Galesi Theorems 3.2, 3.7–3.8 support the polynomial-size/linear-width result. T4 is correctly a threshold W <= k, not equality W = k, and uses the k+1 family/extension cutoff. Retain standard proof-rule conventions. Treat finite unit-clause fixture as a witness, not a proof of the full game characterization.

Sources: BSW, Theorems 3.3, 3.5 and Corollaries 3.4, 3.6 (https://people.inf.ethz.ch/emo/SatSem05/Papers/BensassonWidgerson01.pdf); Bonet–Galesi (https://www.cs.upc.edu/~bonet/revistas/computational_complexity.pdf); Atserias–Dalmau, ECCC TR02-035, Definition 2 and Theorem 1 (https://eccc.weizmann.ac.il/report/2002/035/).

### 05–07: Algorithmic parameterization

[Proved] T5's primal and incidence costs match Samer–Szeider Theorems 1 and 3, including N decomposition nodes and integer multiplication cost delta. Read k as the width of the supplied decomposition, not necessarily optimal; the displayed k = tw identities are the special case of optimal decompositions. The O*(4^k) incidence algorithm is historical, not a tightness claim (later improvements exist). T6 is explicitly about the cached decomposition-guided algorithm; it does not describe arbitrary DPLL or its branch counter. T7 follows from supplying an all-variable bag, taking a fixed clause width and absorbing polynomial length factors into an arbitrarily small exponential slack; deterministic SETH is a Conjecture, while the implication is Proved. No randomized lower bound is promoted without its own hypothesis.

Sources: Samer–Szeider, Theorems 1 and 3 (https://www.ac.tuwien.ac.at/files/pub/SamerSzeider10.pdf); Bacchus–Dalmao–Pitassi Theorem 2 (https://arxiv.org/abs/1401.3458; retained prior scope check); Impagliazzo–Paturi (https://doi.org/10.1006/jcss.2000.1727). For historical context only, Slivovsky–Szeider 2020 (https://ac.tuwien.ac.at/files/tr/ac-tr-20-006.pdf) reports an improved incidence-treewidth counting algorithm.

### 08–10: Grid and expansion bounds

[Proved] Alekhnovich–Razborov Definition 2.14 and Theorem 2.15 give W <= cyclicity^O(1) log S. The unit-square cycle cover has length four and multiplicity at most two. The repaired balanced-cut proof is sound: if few rows are mixed, balance forces both an all-U and an all-complement row; every column then crosses the cut. BSW Theorem 4.4 gives W >= e(G), hence S >= 2^Omega(k) for k by k square grids. The old assertion that unrestricted-resolution grid lower bounds are open is removed. T9 follows for bounded degree and linear balanced expansion. T10 correctly clamps e(G)-Delta before squaring. The star family is a legitimate asymptotic counterexample to the old expression under used-clause proof length. Minor wording: state m >= 2 for the displayed strict inequality ceil((m+1)/3) < m (it fails at m=1); the counterexample family and asymptotic conclusion stand. Do not conflate bounded-degree planar edge cuts with unrestricted planar cuts.

Sources: Alekhnovich–Razborov (https://people.cs.uchicago.edu/~razborov/files/automat_pos.pdf; accessible alternate copy https://citeseerx.ist.psu.edu/document?doi=7b6d9842ff40d3288cb2c0c428f9971232ce3751&repid=rep1&type=pdf); BSW Theorem 4.4, printed p. 156 (same link above).

### 12: Exact width

[Proved] ECCC TR18-170 Corollary 8, printed p. 12, and Corollary 16, printed p. 15, were rechecked against rendered PDF pages. For connected simple graphs with odd marking, their composition gives W = max(Delta, tw(L(G))) under their convention. The K8 counterexample remains valid. For the cubic graph family the primal graph equals L(G). For the trivial edgeless connected graph handle the empty clause directly or explicitly adopt tw(empty) = -1. The corrected SAT 2018 citation DOI `10.1007/978-3-319-94144-8_19` matches the authors, title and pp. 311–326 in the institutional record. The ECCC locators—not the conference page numbering—are the theorem evidence. T12 can be marked CLOSED without waiting for the 2026 preprint.

Sources: https://eccc.weizmann.ac.il/report/2018/170/download/ ; https://iris.uniroma1.it/handle/11573/1264314 ; journal DOI https://doi.org/10.1145/3378667 (metadata correction reported by Lumi; ECCC text is the mathematical basis).

### 13–16: Proof-system separations and simulations

[Proved] Bonet–Galesi Theorems 4.1–4.2 support the MGT tree-like/regular separation, and the BIW construction gives the separate linear general-resolution upper bound and exp(Omega(n/log n)) tree-like lower bound. T14 Corollary 3.4 and Theorem 3.10 explicitly give the O(n^3) general proof and the >2^(n/200) regular lower bound for sufficiently large n and a suitable guard function rho; n is the ordering parameter. Exact additional historical exponents are deliberately not accepted.

T15's CLR simulation assumes an asserting learning scheme with suitable branching/restarts. Its reverse direction is ordinary resolution justification of learned clauses. For DRUP, use non-tautological RUP additions and the source's final subclause/weakening elimination; tautological steps can be discarded. Theorem 2 in Kiesl et al. is specifically a resolution derivation of a subclause followed by subsumption, not an assertion that every RUP clause is literally a single resolution inference. The repaired text no longer equates timings or conflicts with proof length. T16 follows from the source simulation and the elementary fresh-variable extension argument. No approval of our Python DRAT checker follows from these theorems.

Sources: Bonet–Galesi above; BIW, Theorem 1 and construction discussion (https://www.math.ias.edu/~avi/PUBLICATIONS/MYPAPERS/BIW03/biw03.pdf, rendered p. 3); Alekhnovich et al. (https://theoryofcomputing.org/articles/v003a005/v003a005.pdf); Pipatsrisawat–Darwiche, Theorem 1/Corollary 1 (https://www.cs.sfu.ca/~mitchell/cmpt-827/2011-Fall/Project-Readings/CDCL-Restarts-and-Resolution.pdf); Kiesl et al. Theorem 2 and Section 4.4–4.5 (https://benjaminkiesl.github.io/publications/extended_resolution_simulates_drat_kiesl_rebola-pardo_heule.pdf).

### 17: Component parity versus raw CNF

[Proved] The repaired T17 separates arbitrary explicit binary linear systems (polynomial-time elimination with certificate), explicit charged graphs (linear traversal and deterministic logspace consistency), and ordinary CNF (extraction is a separate task if using this parity method). Component parity iff consistency has a direct spanning-tree proof. Reingold's connectivity theorem suffices for logspace graph-parity decision: enumerate vertices, determine whether each is a representative or is reachable from a representative, and accumulate the parity of its component using logarithmic counters. This does not put arbitrary binary linear-system consistency in deterministic logspace. See the remaining Section 4 clarification under ACE-R11-21.

Source for connectivity: Reingold, https://eccc.weizmann.ac.il/eccc-reports/2004/TR04-094/ ; journal DOI https://doi.org/10.1145/1391289.1391291.

## 4. Remaining findings and exact requested edits

### ACE-R11-11 / ACE-R11-20 — Clause multiplicity and graph model

Severity: HIGH for the hypergraph convention; MEDIUM for the general graph scope.
Claim level: Proved (counterexample and construction); Empirical Observation (source/document inspection).
Status: PARTIAL; blocking.

The conservative bound and the cited constructive theorem are now correct in the intended representation. Theorem 2.3 returns a regular refutation of width O(bw(F)) or a satisfying assignment, in time polynomial in |F| + 2^bw(F). Theorem 2.12 concerns the actual clause hypergraph. Remark 2.11 explicitly retains repeated hyperedges: local parity clauses share their variable set but remain separate hyperedges. The repaired section 1.3 calls hyperedges the variable sets of clauses without explicitly preserving their indices/multiplicities. A simple-set interpretation would change the parameter.

[Proved] Concrete counterexample to that interpretation: let G be one edge, with charges 0 and 1. Its CNF is (not x) AND (x). W=1. The correct clause-indexed hypergraph has two edges supported on {x}; the cut between them has boundary {x} and width 1. If these hyperedges are collapsed into one, the single-edge convention used in the map gives width 0. The same danger occurs when the four local cubic parity clauses are collapsed into one hyperedge, even though their signs differ. The line graph/primal graph deliberately merges co-occurrence edges; the clause hypergraph must not merge its indexed hyperedges by support.

Required replacement in §1.3(4):

> H(F) has one indexed hyperedge per clause, supported on its variable set. Different clauses with identical support are retained as separate hyperedges; use the multihypergraph convention of Alekhnovich–Razborov, Remark 2.11. Clause positions remain distinct if the represented input contains duplicate clauses, unless a specified preprocessing step changes the input and the parameter is recomputed.

T11 must explicitly restrict its Tseitin-specific equivalence/width-automatability to connected odd-charge graphs (Definition 2.8), not arbitrary satisfiable parity instances or disconnected systems. The all-CNF construction of Theorem 2.3 has its own broader domain. The conservative upper-bound bridge can be justified independently by Davis–Putnam elimination along a primal tree-decomposition elimination order: at most k later neighbors, at most exponentially many distinct bounded-support clauses per variable, and resolution pivots in the fixed order. Alternatively state bw(H(F)) <= tw(G_P(F))+1 via a decomposition construction with each clause attached to a bag containing its clique, then use Theorem 2.3. Pin the chosen bridge and its conventions rather than leaving the dependency implicit.

Section 1.2 currently introduces arbitrary finite undirected graphs and then claims 2^(d-1) clauses of width d. That formula requires distinct incident variables. For loops, one edge can count twice toward degree, but only one variable is associated with the loop. The general endpoint parity model in Lean can handle loops, whereas this standard CNF literature map need not. Add: “Unless expressly stated otherwise, all underlying graphs in this document are finite simple undirected graphs; results permitting multigraphs use their source-specific conventions. The expanded parity encoding assumes distinct incident edge variables.” This also scopes T10 and the polynomial calculus inputs. Adopt tw(empty)=-1 (or state separate trivial cases); connect isolated empty-clause bags to an existing decomposition bag, or form a tree of such singleton bags if there are no variables. For no-edge parity systems use a trivial empty-clause proof where relevant. The Robertson–Seymour warning, isolated-vertex CNF case, line-graph comparison and incidence upper bound otherwise pass.

Reproduction: read the 2011 paper Definition 2.8, Remark 2.11, Theorems 2.3 and 2.12; compute the one-edge example above. These are mathematical checks, not a newly run code test.

### ACE-R11-18 — Signed polynomial system assumptions

Severity: MEDIUM; blocking for retaining the current unqualified Proved statement.
Claim level: Proved.
Status: PARTIAL.

The major encoding error is fixed: direct linear parity axioms have degree at most one, whereas standard expanded strict cubic clauses give degree-three initial polynomials and a degree-at-most-three refutation by extracting local parity equations. The prior F2 polynomial fixture still passes. The remaining issue is the exact signed-system definition: Buss et al. Section 2 defines TS_n(2) for an odd number n of vertices, all charges one, using signed edge variables (the initial example is r-regular). Theorem 10 uses its expansion parameter epsilon with |N(S)| >= (1+epsilon)|S| for |S| <= n/2, and excludes degree d < epsilon*n/8. It does not merely assume our balanced edge-cut e(G) is large. The theorem is formulated over fields generally; in characteristic two the signed equations are satisfiable, so the meaningful refutation-degree lower bound is for characteristic not two.

Required replacement for Encoding 3 and corresponding table cell: retain the paper's odd-n all-one-charge TS_n(2) formulation on appropriate connected expanding graphs (use bounded even degree for the odd-order regular families if giving an example), define epsilon as in Theorem 10, and explicitly state no degree d < epsilon*n/8 PC refutation in characteristic not two. A transfer to arbitrary odd markings or the team's cubic Boolean encoding is a separate proof obligation. For direct summation costs use O(|V|*(|E|+1)) monomials or stipulate |E|>=1, and say degree at most one to include isolated odd vertices. Do not equate monomial count with encoded bit size.

Primary source checked: https://mathweb.ucsd.edu/~sbuss/ResearchWeb/lineargaps/journalfinal.pdf , Section 2 and Theorem 10 (rendered p. 15). No new PC lower bound is claimed.

### ACE-R11-19 — Frege/ER and open Res(XOR) locator

Severity: LOW for scope/degenerate cost; INFO for properly quarantined optional future claim.
Claim level: Proved (direct construction and polynomial upper bound); Empirical Observation (source inspection).
Status: PARTIAL, not itself a blocker if the retained wording is clarified.

The exact linear-size tree-like Res(XOR) claim has been removed. Good. Urquhart Section 6, Lemma 6.1, explicitly constructs a polynomial-size axiomatic proof for the family treated there; it is not a stand-alone quantified theorem about every bounded-degree graph. Its proof mechanism extends: for fixed maximum degree convert each local expanded CNF to its parity identity with constant-sized local reasoning in a basis allowing biconditional; chain the identities; use associativity/commutativity to bring equal edge occurrences together and cancel pairs; an odd component gives contradiction. The number of swaps and the intermediate formula sizes are polynomial in |V| for bounded degree. Standard Frege systems polynomially simulate one another, and ER can encode the steps using extension definitions (or use iterative XOR definitions directly); T16 supplies the DRAT link. Retain the polynomial upper bound with this explicit derivation and bounded-degree input convention. The exact Res(XOR) total-symbol-size assertion remains unapproved and must stay outside the Proved table portion. The direct summation symbol estimate should use O(|V|*(|E|+1)) symbols under unit-cost variable names; bit-encoded identifiers may add logarithmic factors. An isolated odd vertex is already contradictory and needs no large construction.

Source rechecked: Urquhart, Hard Examples for Resolution, Section 6, Lemma 6.1 and Theorem 6.2, printed pp. 217–218 (https://citeseerx.ist.psu.edu/document?doi=9877c5a20225299bdbbc826346dee9c44b0f03ab&repid=rep1&type=pdf). The exact Itsykson–Sokolov derivation has not been independently checked. Its omission is acceptable; no need to delay Phase 4 to recover a deliberately excluded theorem.

### ACE-R11-21 — Remaining claim-level wording

Severity: MEDIUM; blocking only for the overbroad complexity-class wording.
Claim level: Proved / Conjecture / Empirical Observation.
Status: PARTIAL.

The subsumption rewrite is a major improvement. One cell still states algebraic solving on explicit parity systems is in “P / L (T17 Models A & B)”. This can be read as claiming arbitrary binary linear-system consistency is in L. Replace it with “Explicit arbitrary GF(2) linear systems are decidable in polynomial time; explicit charged undirected graph parity consistency is in L by connectivity and parity accumulation.” No new complexity-class inclusion is established. In the prediction rows, use Conjecture for untested performance claims and Empirical Observation only for actual measurements. A research question is not itself an observed result. Keep the Lean-Verified global odd-charge theorem distinct from the general componentwise iff. Other Section 4 repairs pass.

### ACE-R11-22 — TR26-332

Severity: HIGH research relevance, nonblocking while quarantined.
Claim level: Empirical Observation for publication record and reported theorem statements; no new team Proved or Lean-Verified promotion.
Status: STILL OPEN for proof audit.

I independently reopened the ECCC publication record and the original PDF, including rendered p. 4. The paper is dated November 21, 2026 and the ECCC publication record is November 22, 2026. Section 1.2 matches all five reported result interfaces in the repaired §5: underlying-treewidth exponential lower bound, line-graph lower bound including formula size, stronger bridgeless result, proof-search automatability and polynomial regular/unrestricted equivalence. In the automatability statement use the authors' encoded input length ell(F) and minimum unrestricted length S(F), not an unsupported interpretation of |F| as number of clauses. A two-edge-connected graph in that paper is connected, has at least two vertices and has no bridges. The authors claim theorems with proofs; the team's review status is OPEN, not a claim that the authors are conjecturing them.

Primary source: https://eccc.weizmann.ac.il/report/2026/332/ and https://eccc.weizmann.ac.il/report/2026/332/download/ , Section 1.2, Theorems 1.1–1.5 and the internal locators listed in §5.

I have not completed a line-by-line proof audit of Sections 5–8 or checked all dependent graph/algorithm lemmas. Do not label these results team-audited Proved merely because the preprint exists. They are not Lean-Verified.

### ACE-R11-23 — Source locators

Severity: LOW unless an unresolved assertion is retained as Proved.
Claim level: Empirical Observation.
Status: PARTIAL.

The repaired table contains concrete locators and removes or explicitly marks the unsupported historical exponents and exact Res(XOR) bound OPEN. Lumi reports all remaining DOI/ECCC identities resolve; I did not repeat every identity check. T12's source locator and conference correction were independently rechecked. Some source requests returned errors, so alternate copies or retained prior checks were used; exact unresolved historical statements remain excluded from approval. This is not itself a blocker if no unsupported precise claim is retained as Proved. The remaining specific mathematical edits in Sections 4.1–4.4 are the real blockers. The broad sentence in §2 claiming all retained bounds match checked locators should instead specify which have been reviewed and which are supported by supplied derivations.

## 5. Gate C conditions and next actions

**NOT APPROVED at `f0ac7fc`.** The previous 14 failed theorem rows are substantially repaired and T12 can be closed now. Require a narrow follow-up addressing the clause-indexed hypergraph and connected odd-charge scope (T11/Section 1), the TS_n(2) assumptions (T18), and P/L distinction (Section 4). Include the proof-cost/degenerate-case wording and the Frege derivation clarification in the same edit. No need for new empirical runs or a new Lean build merely to review this Markdown. I will not approve the author's changes on the author's behalf; Gemini may repair and an independent reviewer must approve the exact new blob.

Gate C need not wait for exact historical bounds that are omitted, the unclaimed Res(XOR) linear-size locator, or a full audit of TR26-332, provided they remain visibly outside approved Proved claims. Gate C literature approval is independent of the already successful PR #7 Lean review. It is also independent of Gates D–F: this review does not authorize confirmatory execution or alter OM-C001-R2.

## 6. What TR26-332 changes for Operation Millennium

[Empirical Observation] The reported preprint materially overlaps our earlier proposed general Tseitin resolution research. If its theorems withstand scrutiny, it closes the general connected-graph treewidth lower-bound target and the restricted-family automatability question; it also gives a polynomial regular/unrestricted comparison, not the stronger exact equality conjecture. The line-graph result including the explicit input-size term is important for high-degree graphs with large expanded CNFs. Do not drop that term or the no-bridges condition from the stronger theorem. It does not prove that min-fill is optimal, that every CDCL heuristic is efficient, that a proof is small, or that arbitrary resolution or SAT is automatable. An algorithm polynomial in the minimum proof length may still take exponential time in the formula length.

[Proved, conditional on the reported theorems] For connected bounded-degree odd-charge families, combining the reported lower bound with the older constructive upper bounds would calibrate minimal proof size to exponential dependence on underlying treewidth, up to polynomial factors and constant factors in the exponent. This would sharpen the theoretical benchmark, not determine our recorded DPLL branch count. The algebraic consistency algorithm is already polynomial on explicit parity systems and is not contradicted by a resolution proof-size lower bound.

Recommendations:

1. Phase 3/4: do not change the registered 840-instance test set, branch cap, primary feature, response, models, threshold or analysis because of this paper. Retain matched parity and width experiments as calibrated measurements; the preprint is unrelated to proving our random 3-SAT predictive conjecture. Use checked proof traces, not raw decisions/conflicts, when making proof-size comparisons.
2. Round 02 theory: commission a separate `docs/phase5/TR26_332_PROOF_AUDIT.md`. Gemini extracts definitions, theorem dependency graph and exact quantifiers/size measures; Ace independently reviews the spanning-tree restriction argument (Section 5), bounded-degree reduction and expansion gadget (Section 6), proof-search composition (Section 7) and bridgeless/regular simulation (Section 8). Require explicit treatment of proof restriction, charge propagation, bridges, expanded CNF size, and every polynomial/exponential overhead. Use external review if a crucial lemma remains unresolved. No claim of independent proof completion before that work actually happens.
3. Round 02 implementation: Claude and Dee can build ordinary-CNF parity extraction and hostile mixed-CNF fixtures, Nova can design a separate held-out evaluation, and the theory lane can formalize extraction/certificate soundness using the existing XOR theorem. For a pure resolution comparator, include proof-search and output costs and verify its proof format; do not compare DRAT/RAT length directly to an ordinary resolution lower bound.

[Conjecture] A certified extractor and elimination method may reduce end-to-end proof/search effort on some mixed and structured raw CNFs, even when parity structure is not supplied. Require a fresh preregistration with extraction failures, partial extraction, malformed sign patterns, certificate checking costs and non-parity negative controls. This is separate from any claim about arbitrary CNF SAT or P vs NP.

## 7. Handoff

No branch, commit or PR was created. I verified both attachment blobs at the requested base. The regression test rerun was local and isolated. I did not independently repeat Gemini's Lean CI or the full previous literature proof audit, and I have not completed the TR26-332 proof audit. This review is a proposed independent disposition ledger on the exact repaired artifact, not approval of a future revision. Submit against dev; main remains untouched without explicit project authorization.

— Ace
