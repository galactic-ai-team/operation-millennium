# Operation Millennium — Adversarial Review 01

Author: Ace — Galactic AI Team
Coordinator: Lumi
Research Director: Stephon
Date: 2026-11-25
Base: dev d6e385c
Status: Proposed coordinator rulings and pre-test amendments.

Phase 3 artifacts are merged.
The confirmatory test population remains unopened according
to the coordinator.

No confirmatory outcomes were accessed by Ace.
No new solver experiments or Lean builds were executed
for this review.

---

## 1. Executive decision

Phase 4 adversarial review: GO.

Final OM-C001-R2 freeze: CONDITIONAL GO.

Confirmatory test execution: NO-GO until the pre-execution
gates in this document have passed.

Retain the original primary hypothesis, population, width
feature, response variable, statistical models, branch
budget, bootstrap and practical effect threshold.

Do not optimize the primary experiment in response to
the negative pilot or the reported training outcomes.

The test split is a single confirmatory evaluation,
not another opportunity for model development.

A negative result is a valid research outcome.

---

## 2. Rulings on Dee's questions

### A1. Meaning of width estimates

RULING: Adopt Nova's canonical implementation.

The term "width estimate" in Discovery Round 01 means:

primal_min_fill_width

as specified in Section 3.3 of DISCOVERY_ROUND_01.md.

Construct the unsigned primal graph using all declared
variables, including isolated variables.

For each elimination step, minimize:

(number of missing edges among current neighbors,
 numerical variable identifier).

The width is the maximum current degree encountered
during that elimination ordering.

Return and retain the ordering.

This quantity is an upper bound on treewidth.

It is not:

- Exact treewidth.
- Resolution width.
- Treewidth of the original Tseitin graph.
- An invariant of arbitrary numerical relabeling.

For matched Tseitin instances, the unsigned primal graph
is the line graph of the underlying simple graph.

Remove the duplicate production min-fill implementation
from matched_instances.py, or turn it into a thin wrapper
around Nova's implementation.

Retain an independently implemented test oracle in the
test suite if useful.

Independent verification is desirable.
Duplicate production implementations are not.

### A2. Meaning of matched permutations

RULING: Explicit edge-variable and clause permutations
are the primary matched transformations.

For a pair of formulas F_even and F_odd:

1. Draw a bijection pi on the declared variable IDs.

2. Replace every positive literal x with pi(x).

3. Replace every negative literal -x with -pi(x).

4. Draw a permutation rho of clause positions.

5. Apply exactly the same pi and rho to both formulas.

6. Preserve literal order within each clause.

7. Transform any stored witness consistently.

Use independent deterministic PRNG streams for pi and rho.

For permutation seeds 100 through 119:

variable permutation:
    random.Random(2 * seed)

clause permutation:
    random.Random(2 * seed + 1)

Generate the variable permutation by shuffling the sorted
list of declared variable IDs.

Generate the clause permutation by shuffling the list
of clause positions.

Pin the Python interpreter version.

Retain both permutation arrays in the experiment log.

A vertex permutation of the underlying graph is allowed
as an additional metamorphic test.

However, it must induce a documented edge-ID bijection
and must transform the charge vector consistently.

Merely regenerating edge IDs after a vertex permutation
does not establish that both formulas received the same
variable permutation.

Do not independently shuffle the even and odd members
of a matched pair.

Do not randomly flip literal signs as part of this
permutation protocol.

### A3. Meaning of equality of unsigned graphs

RULING: Require exact labeled equality within each pair.

Define the primal signature of F as:

(
  declared variable IDs,
  sorted unique unordered variable co-occurrence edges
)

Include isolated declared variables.

Define the unsigned incidence signature as:

(
  declared variable IDs,
  number of clause positions,
  sorted variable-to-clause-position incidences
)

Clause positions are distinct even if clauses duplicate
one another.

For the original matched pair, require exact equality of
both signatures under the established correspondence
between local XOR clause positions.

After a shared permutation, require exact equality of
the transformed signatures.

When comparing an original formula to its relabeled
version, require graph isomorphism witnessed by the
recorded permutation, rather than literal equality of
numerical labels.

Additionally require:

- Identical variable counts.
- Identical clause counts.
- Identical clause-length multiset.
- Identical positive occurrence count for each variable.
- Identical negative occurrence count for each variable.

[Claim Level: Proved — elementary consequence]

A deterministic feature extractor receiving identical
labeled graph inputs returns identical graph features.

Therefore deterministic min-fill width and its ordering
must agree within each matched pair.

The width estimate need not remain unchanged between
different labelings of the same abstract graph.

### A4. Formal specification to attack

RULING: The normative attack targets are:

1. docs/phase3/DISCOVERY_ROUND_01.md

   Sections 5 and 6:
   structural indistinguishability, matched instances,
   and Mobius-ladder width bounds.

2. lean/Millennium/Tseitin.lean

   Especially:
   - TripleIncidenceMatches
   - xor3CNF_correct
   - vertexParity_eq_triple
   - tseitinCNF_odd_unsat

3. docs/phase3/TSEITIN_PROOF_SPEC.md

   Use this if present at the reviewed commit.
   Otherwise import Ace's submitted specification as a
   documentation artifact before final Phase 4 review.

4. This document, Sections 2 and 3.

The Lean source and actual theorem statements take
precedence over informal descriptions.

The Python generator is not automatically certified by
the existence of a Lean theorem.

### A5. Disconnected graph charge semantics

RULING: Dee is correct.

For a finite undirected graph with connected components
C_1, ..., C_k:

[Claim Level: Proved — known parity characterization]

The Tseitin system is satisfiable if and only if every
component has even total charge.

Necessity:

Sum the parity equations within one connected component.
Every edge of that component contributes twice.
The component's total charge must therefore be zero
in ZMod 2.

Sufficiency:

Choose a spanning tree in each nontrivial component.

Assign zero to non-tree edges.

Root the spanning tree.

Process non-root vertices from leaves toward the root,
assigning each parent edge to satisfy its vertex equation.

The root equation then follows from the even total charge.

For isolated vertices, the charge must be zero.

This gives a satisfying assignment for every component.

Combining the component assignments satisfies the graph.

Important distinction:

The existing Lean theorem proves global odd-charge
unsatisfiability.

It does not yet formalize this full componentwise
if-and-only-if characterization.

Do not promote the componentwise result to Lean-Verified
without a separate successful formalization.

Required counterexample:

Take two disconnected copies of K4.

Assign exactly one charged vertex in each component.

Global charge is even.
Both component charges are odd.
The formula is UNSAT.

Also test:

- Zero charged components: SAT.
- One odd component: UNSAT.
- Two odd components: UNSAT.
- Two charges within the same component: SAT.
- Empty graph: SAT under the empty-system convention.

### A6. Solver-effort stability

RULING: Distinguish reproducibility from robustness.

Reproducibility is an infrastructure requirement.

For the same exact CNF, same solver implementation,
same budget and same configuration, repeated runs must
return identical:

- Status.
- Decision/branch-attempt count.
- Propagation count.
- Budget-exhaustion classification.

Wall-clock time is excluded from exact equality.

Any unexplained mismatch is a FAIL for reproducibility.

Robustness to permutations is an exploratory property,
not a requirement for solver correctness.

Define for each graph and charge configuration:

Y_j = ln(1 + min(D_j, B))

for each registered permutation j.

Report:

- Median Y.
- Minimum and maximum Y.
- Interquartile range.
- Budget-hit fraction.
- Capped effort ratio:

    R = (1 + max_j min(D_j,B))
        /
        (1 + min_j min(D_j,B))

Proposed descriptive classification:

R <= 2:
    Low observed permutation sensitivity.

R > 2:
    High observed permutation sensitivity.

These are operational labels for this finite suite.
The threshold is a research-design convention, not
a universal mathematical stability boundary.

If runs are capped, R describes capped effort only.

Report the matched charge contrast separately:

delta_j = Y_odd,j - Y_even,j

Report its median, range, and fraction of positive,
zero and negative contrasts.

[Claim Level: Empirical Observation]

All measured effort, permutation sensitivity and charge
contrasts are empirical when actually executed.

There is no required direction of the charge contrast.

Phase 4 can pass even when the solver is highly sensitive
to permutations.

It cannot pass if representation-preserving transformations
produce an incorrect, independently adjudicated SAT status.

UNKNOWN is not an incorrect SAT status; it is an
incomplete computation.

---

## 3. Rulings on Claude's questions

### B1. The 10,000-branch budget

RULING: RETAIN.

[Claim Level: Empirical Observation — author-reported]

The reported maximum training branch count is 992.
The 10,000-branch cap reportedly did not bind.

This report awaits independent reproduction.

The absence of budget hits in training is not a reason
to lower the budget.

It also does not establish that no held-out instance
will reach the budget.

Retain:

B = 10000
max_decisions = B
max_seconds = None

Retain:

Y = ln(1 + min(D,B))

Changing the budget changes the measured response.

Do not increase or decrease B after observing test
outcomes.

The decision cap is not a wall-clock guarantee.

### B2. What UNSAT_PROOF_CHECKED certifies

RULING: Accept Claude's distinction.

An independently checked reference UNSAT certificate
establishes evidence that the exact input formula is
unsatisfiable.

It does not certify that DPLL:

- Explored the correct search tree.
- Correctly counted branches.
- Correctly counted propagations.
- Implemented the intended branching heuristic.
- Used a minimal proof.
- Had any particular asymptotic complexity.

Maintain three separate audit concepts:

A. Formula status evidence.
B. Solver implementation correctness.
C. Measurement reproducibility.

For example:

formula_status = UNSAT
formula_evidence = UNSAT_PROOF_CHECKED
measurement_audit = REPRODUCED

Retain compatibility with the existing record schema
where possible.

Document the meaning of every field.

A valid DRAT certificate is not a formal Lean proof
unless an applicable verified checker and proof path
are separately established.

Do not automatically call DRAT-checked UNSAT
Lean-Verified.

### B3. Runner settings not previously preregistered

RULING: Record the following as pre-test Amendment A01.

The primary scientific protocol remains unchanged.

Pin the execution configuration:

- Population: confirmatory.
- Workers: 4.
- Watchdog: 600 seconds per instance attempt.
- Maximum attempts: 3, including the original attempt.
- Primary decision budget: 10000.
- Primary wall-clock decision cutoff: none.
- Certification: enabled.
- Reference solver: PySAT cd195.
- Certificate checking: enabled.
- Certificate retention: enabled.
- Fault injection: prohibited.
- Generator ordering: unchanged.
- Primary DPLL branching: unchanged.

Use --keep-certificates for both splits.

Retain original CNF bytes and proof bytes for completed
reference UNSAT claims.

A watchdog expiry, worker failure or infrastructure
exception must be classified as ERROR if attempts
are exhausted.

It must not be classified as ordinary decision-budget
UNKNOWN.

Rerun the same instance, not a replacement seed.

Record all failures and attempts.

If infrastructure errors remain after the frozen
retry procedure, the final disposition is INCONCLUSIVE.

No arbitrary resource escalation is authorized.

Pin the exact Python interpreter version, dependencies,
checker identity and external checker version used for
independent verification.

These settings are chosen for reproducibility and
artifact retention, not for improving prediction accuracy.

### B4. Freeze regeneration

RULING: Regenerate after all Phase 4 pre-execution
blocking fixes have merged.

Do not authorize a freeze generated from an obsolete
feature branch.

The currently reviewed runner checks source, function,
checker, protocol and seed-manifest hashes.

Its authorization check compares Python major/minor
versions and selected package versions.

It does not enforce every recorded Git provenance field
or every operational setting.

Therefore strengthen the freeze boundary.

Require:

- Exact code commit.
- Clean tracked source tree.
- Exact Python version and implementation.
- Complete dependency manifest.
- Source hashes.
- Function hashes.
- Checker source and executable hashes.
- Seed-manifest hash.
- Approved protocol document hash.
- This amendment document's hash.
- Exact execution settings.
- Independently reproduced training-record hash.
- Frozen fitted-model hash.
- Coordinator identity and authorization time.
- Explicit status FROZEN.

Avoid a self-referential Git hash.

The freeze manifest should identify the frozen
execution-code commit.

The authorization manifest may be stored in a subsequent
documentation-only commit or an external immutable
experiment artifact.

No source or protocol changes may occur between the
identified execution commit and the authorized run.

Record both commits if applicable.

A manifest containing a Git hash is not sufficient
unless that hash is actually verified.

The authorization mechanism is procedural.

It is not cryptographic protection against an agent
deliberately calling the underlying solver functions.

The public seed scheme remains reproducible rather
than genuinely blinded.

### B5. Analysis and labeling fixes

RULING: Nova must review Claude's records_to_rows fix,
but a non-author must approve the final analysis changes.

The following issues are blocking.

#### B5.1 Population identity

The confirmatory analyzer must reject pilot, synthetic
or mixed-population records.

Do not trust a caller-supplied population label alone.

Check every record against the expected manifest:

- Experiment identifier.
- Population.
- Split.
- Cell.
- Index.
- Exact seed.
- Instance identifier.
- Formula hash.
- Budget.
- Schema version.

Require the exact expected record set.

Reject duplicates and unexpected entries.

The current records_to_rows path accepts several
legacy fields and does not retain all provenance in
its simplified analysis rows.

Run strict validation on raw records before conversion.

#### B5.2 Explicit status

Require:

SAT
UNSAT
UNKNOWN
ERROR

as distinct states.

Check consistency with legacy satisfiable, timed_out,
and verification fields.

Do not use permissive bool(...) conversions on
unvalidated serialized values.

For example, bool("false") is true in Python.

Malformed record types must fail validation rather than
silently becoming legitimate observations.

#### B5.3 Response recomputation

Recompute Y from validated integer branch counts and
the frozen budget.

Require UNKNOWN to reflect legitimate branch-budget
exhaustion in this experiment.

Do not trust a stored Y field without verification.

Reject negative, impossible or inconsistent counts.

#### B5.4 Pilot versus confirmatory disposition

The pilot cannot decide OM-C001-R2.

Its official confirmatory disposition is INCONCLUSIVE
because it is not the registered confirmatory population.

Its effect estimate can still be negative.

Distinguish:

- Population-level experimental disposition.
- Exploratory numerical effect.
- Effort-only diagnostic disposition.

Do not imply the pilot supports the primary hypothesis.

#### B5.5 Secondary model denominators

M2 and M3 must report their exact comparison baseline.

Define:

I20 = 1 - MAE2 / MAE0

I30 = 1 - MAE3 / MAE0

I32 = 1 - MAE3 / MAE2

I32 measures the incremental improvement obtained by
adding width to the degree-adjusted model.

The primary outcome remains:

I10 = 1 - MAE1 / MAE0

An M3 improvement over M0 does not establish an
improvement over M2.

[Claim Level: Empirical Observation — pilot-derived
calculation using coordinator-reported rounded values]

If the reported M2 = +0.167 and M3 = +0.127 both use
M0 as their denominator, then:

MAE2 / MAE0 = 0.833

MAE3 / MAE0 = 0.873

I32 = 1 - 0.873 / 0.833

approximately -0.048.

Thus adding width to the degree model appears to worsen
pilot prediction error by approximately 4.8%.

This interpretation is conditional on the reported
denominator convention and rounded values.

Nova must confirm it from the original pilot outputs.

This is useful negative evidence.

It is not grounds for promoting M2 to the primary model.

#### B5.6 Bootstrap and decision rules

Retain the preregistered paired, stratified bootstrap:

- 10000 replicates.
- PCG64.
- Seed 9012026.
- Resample 30 paired errors per test cell.
- 28 cells.
- Fixed fitted models.
- Linear percentile interpolation.

Any undefined bootstrap replicate caused by zero
resampled baseline MAE triggers INCONCLUSIVE.

Record this explicit interpretation before test execution.

The effort-only diagnostic must not report PASS when
the corresponding numerical prerequisites are undefined.

#### B5.7 Original statistical model

Keep the exact cell-mean baseline and the single
within-cell least-squares width slope.

The baseline mean is intentional, even though MAE is
the evaluation loss.

A cell-median baseline may be investigated as an
exploratory robustness comparison.

Do not replace the primary baseline after observing
pilot or test behavior.

### B6. Duplicate min-fill implementations

RULING: Consolidate production code before the freeze.

Nova owns the canonical implementation.

Dee consumes it.

An independent implementation may remain in tests
as a comparison oracle.

Require agreement on:

- Width.
- Selected elimination ordering.
- Replayed maximum degree.
- Empty and isolated graph cases.
- Deterministic tie-breaking.

Add a test using graphs whose optimal min-fill
choice is tied across multiple vertex IDs.

Do not require an arbitrary relabeling to preserve
the selected ordering or its width.

If consolidation changes training features, invalidate
the old training artifact and regenerate it.

---

## 4. Ruling on Gemini's T12

RULING: REPLACE the existing theorem entry.

Do not merely remove the [VERIFY] marker.

The current proposed inequality involving tw(G)
and tw(G)+Delta is not the precise theorem established
by the cited paper.

[Claim Level: Proved — established literature]

For a connected simple graph G and an odd marking
phi, the minimum width of a resolution refutation
of the standard Tseitin contradiction satisfies:

W(T(G,phi) |- empty)
    = max(Delta(G), tw(L(G))).

Here:

- Delta(G) is the maximum vertex degree.
- L(G) is the line graph of G.
- tw uses the usual maximum-bag-size-minus-one
  convention.
- W measures resolution refutation width under
  the source's definitions.

Source:

Nicola Galesi, Navid Talebanfard, Jacobo Toran.

Cops-Robber Games and the Resolution of Tseitin
Formulas.

ECCC TR18-170, 2018.

https://eccc.weizmann.ac.il/report/2018/170/

Primary paper:

https://eccc.weizmann.ac.il/report/2018/170/download/

Relevant results:

Corollary 8, printed page 12:

W(T(G,phi) |- empty) = max(Delta(G), ec(G)-1).

Corollary 16, printed page 15:

ec(G) = tw(L(G))+1.

Substitution gives the stated exact characterization.

Journal publication:

ACM Transactions on Computation Theory, 2020.

https://doi.org/10.1145/3378667

The theorem numbering above refers specifically
to the 2018 ECCC version.

### 4.1 Connection to our experiment

[Claim Level: Proved — elementary consequence]

For the standard strict 3-CNF encoding of a simple
cubic Tseitin graph, the unsigned CNF primal graph
is L(G).

Therefore for the connected odd-charge family:

W(T(G,phi) |- empty)
    = max(3, tw(primal(T(G,phi)))).

Our min-fill proxy is an upper bound on the exact
primal treewidth.

It follows that:

W(T(G,phi) |- empty)
    <= max(3, primal_min_fill_width(T(G,phi))).

This does not mean that the heuristic estimate is
the exact minimum resolution width.

It does not predict the runtime of our DPLL baseline.

It does not apply to the satisfiable matched formula
as a refutation-width theorem.

There is no refutation of a satisfiable formula.

Do not extrapolate this characterization to arbitrary
random 3-SAT instances.

### 4.2 Replacement T12 table row

ID:
T12

Result:
Exact resolution-width characterization for connected
simple odd-charge Tseitin contradictions.

Model:
General resolution.

Graph representation:
Line graph L(G), equivalent to the unsigned primal
graph of the standard Tseitin encoding.

Statement:
W(T(G,phi) |- empty) =
max(Delta(G), tw(L(G))).

Claim level:
Proved — established literature.

Reference:
Galesi, Talebanfard and Toran, ECCC TR18-170,
Corollaries 8 and 16.

Limit:
No direct statement about proof length, general SAT
algorithm runtime or P vs NP.

---

## 5. Formal preregistration amendments

The following amendments are proposed after the pilot
and training reports, but before confirmatory test
outcomes have been seen.

They must be dated and approved explicitly.

They are not a retroactive claim that these details
were present in the initial registration.

A01 — Execution settings

Pin the operational configuration in Section 3,
including watchdog, retry policy, certificate retention,
worker count and exact software environment.

A02 — Verification semantics

Separate formula-status evidence from DPLL measurement
correctness and reproduction.

Require retained evidence, not merely a verified flag.

A03 — Data integrity

Validate raw records against the frozen seed manifest
before analysis.

Reject mixed populations, malformed types, duplicate
records, inconsistent statuses, and incorrect features
or response values.

A04 — Statistical edge cases

Clarify that undefined bootstrap replicates or other
undefined required numerical quantities yield
INCONCLUSIVE.

A05 — Secondary reporting

Report M2 versus M0, M3 versus M0 and M3 versus M2
with explicit denominators.

Do not alter the primary model comparison.

A06 — Freeze provenance

Require the final reviewed execution commit,
operational configuration, independently reproduced
training records, fitted models and protocol hashes.

A07 — Independent execution

Only Lumi authorizes and initiates confirmatory execution.

No teammate may inspect the confirmatory outcomes
before the complete raw dataset is locked.

A08 — Reproduction policy

Allow independent reruns of exactly the same frozen
test population solely to verify reproducibility.

These reruns are not additional independent samples.

Do not replace the first complete result with a more
favorable rerun.

Retain both results and document discrepancies.

A09 — Post-unblinding failures

A material implementation or protocol failure discovered
after unblinding invalidates the confirmatory disposition.

Record INCONCLUSIVE and publish the failure.

A corrected experiment using the same exposed population
must be identified as a post-unblinding reanalysis.

A new confirmatory claim requires a new registered
protocol and a fresh held-out population.

### Unchanged primary protocol

- Experiment: OM-C001-R2.
- Variable counts: 30, 40, 50, 60.
- Seven original clause-density settings.
- 28 exact size/density cells.
- 1960 training instances.
- 840 test instances.
- Original seed scheme.
- Original primary min-fill width.
- Branch cap B=10000.
- Original capped log-effort response.
- Original M0 and M1 definitions.
- Original MAE improvement statistic.
- Original 5% practical effect threshold.
- Original bootstrap method.

Primary disposition:

PASS:
    All required gates pass.
    I10 >= 0.05.
    Bootstrap lower endpoint > 0.

FAIL:
    All required gates pass.
    All required numerical quantities are defined.
    I10 < 0.05.

INCONCLUSIVE:
    A required gate fails or remains unresolved.
    A required quantity is undefined.
    Or I10 >= 0.05 with a bootstrap lower
    endpoint <= 0.

A PASS is not a 95% confidence demonstration that
the true population improvement exceeds 5%.

A FAIL rejects this registered operational target,
not every possible structural predictor.

---

## 6. Phase 4 independent review assignments

Review arrangement:

Artifact author != primary adversarial reviewer.

Every merged Phase 3 artifact receives an independent
attack.

Artifact authors may repair issues discovered by
reviewers.

They may not be the sole approver of their own fixes.

### 6.1 Claude attacks Dee's PR #8

Target:

lab/om_lab/matched_instances.py

Task:

Construct an independent GF(2) parity oracle.

The oracle must derive its equations from graph
endpoints and charges, rather than reuse Dee's
component-parity decision function.

Compare oracle results, SAT results and constructed
witnesses on:

- K4.
- K3,3.
- Triangular prism.
- Petersen graph.
- Registered Mobius ladders.
- Disconnected copies of cubic graphs.

Exhaust every charge vector for small graphs with
at most 10 vertices.

For larger graphs, use a fixed documented seed suite.

Attack:

- Incorrect edge mappings.
- Duplicate edge IDs.
- Missing clauses.
- Corrupted charge metadata.
- Invalid endpoints.
- Repeated graph edges.
- Disconnected even-total but odd-component cases.

Check both matched primal and incidence signatures.

Run the registered permutation suite.

Deliver:

docs/phase4/REVIEW_CLAUDE_MATCHED_INSTANCES.md

plus independent oracle code and regression tests.

Acceptance:

Every legitimate instance agrees with the independent
oracle when solved to completion.

Every malformed instance is either rejected or
explicitly classified outside the encoder contract.

Unexplained mismatches block approval.

### 6.2 Gemini attacks Ace's PR #7

Target:

lean/Millennium/Tseitin.lean

Task:

Independently inspect theorem statements and attempt
to identify vacuous or insufficient assumptions.

Run a clean Lean build at the pinned toolchain.

Audit every exported theorem's axiom dependencies.

Pay particular attention to:

- Exact Nat incidence multiplicities.
- Vertex-list coverage.
- Finite endpoint maps.
- Self-loops and parallel edges.
- Repeated variable IDs.
- Empty types.
- Global versus componentwise charge.
- Boolean-to-ZMod-2 correspondence.

Construct a concrete K4 odd-charge instantiation in
Lean using finite vertex and edge identifiers.

Discharge the actual TripleIncidenceMatches and
coverage obligations.

Apply tseitinCNF_odd_unsat to the constructed CNF.

Do not simply introduce the desired unsatisfiability
conclusion as an assumption.

Also add a small even-charge satisfiable fixture
to check the intended encoding semantics.

Deliver:

docs/phase4/REVIEW_GEMINI_TSEITIN_LEAN.md

plus independent Lean instantiation tests.

Acceptance:

- Clean build.
- No admitted proofs.
- No custom axioms.
- Only permitted standard axiom dependencies.
- Concrete nonvacuous instantiation succeeds.
- No unresolved mismatch between theorem and
  intended mathematical statement.

### 6.3 Nova attacks Claude's PR #10

Target:

lab/om_lab/width_experiment.py

and the associated solver and certificate infrastructure.

Task:

Attempt to bypass the runner's integrity and
authorization checks using synthetic or pilot records.

Do not execute confirmatory test instances.

Attack:

- Unauthorized freeze.
- Tampered source hash.
- Tampered protocol hash.
- Wrong Python or dependency version.
- Wrong execution commit.
- Mixed populations.
- Incorrect seeds.
- Duplicate rows.
- Missing rows.
- Altered decision counts.
- Inconsistent status fields.
- Corrupted SAT witnesses.
- Corrupted or mismatched UNSAT certificates.
- Worker crashes.
- Watchdog expiration.
- Decision-budget boundary.
- Certificate-file substitution.

Compare the internal proof checker against an
independent DRAT checker on controlled valid and
invalid fixtures.

Include malformed proof syntax, incorrect clause
deletions, RAT/RUP edge cases, and proofs attached
to the wrong input formula.

A checker disagreement must be investigated, not
settled by majority vote.

Use a separately written tiny DPLL reference tracer
on small fixtures to audit branch-attempt accounting.

Deliver:

docs/phase4/REVIEW_NOVA_RUNNER.md

plus fault-injection and certificate regression tests.

Acceptance:

No invalid authorization passes.

No known-invalid certificate receives a checked
status.

No incomplete run is relabeled UNSAT.

Branch counts match the specified search semantics
on the independent tiny reference cases.

### 6.4 Dee attacks Nova's PR #9

Target:

lab/om_lab/width_features.py
lab/om_lab/analyze_width.py

Task:

Build independent feature and statistical oracles.

For small graphs, enumerate elimination orders to
determine exact minimum elimination width where
computationally feasible.

Verify the canonical heuristic:

- Produces a valid ordering.
- Replays to its reported width.
- Never reports less than the exact width.
- Matches the specified tie-breaking rule.

Use fixed graph fixtures and relabelings.

For the statistical analysis, construct synthetic
datasets with analytically predictable outcomes.

Include:

1. Width has no within-cell variation.
2. Width predicts effort perfectly within cells.
3. Width appears useful only because density varies.
4. Degree predicts effort but width adds no information.
5. Width worsens held-out predictions.
6. Budget-exhausted rows.
7. Missing cells.
8. Undefined baseline MAE.
9. Undefined bootstrap replicates.
10. Deliberate train/test contamination.

Independently calculate M0, M1, M2, M3 and their
error comparisons.

Verify that the primary classification follows
the registered decision rules.

Deliver:

docs/phase4/REVIEW_DEE_WIDTH_ANALYSIS.md

plus independent oracle and synthetic regression tests.

Acceptance:

All defined feature and statistical outputs match
the independent specifications within a fixed
documented floating-point tolerance.

Every undefined or invalid case is classified
appropriately.

No test outcomes are used to change the primary model.

### 6.5 Ace attacks Gemini's PR #11

Target:

docs/phase3/WIDTH_TSEITIN_LITERATURE.md

Task:

Perform a theorem-by-theorem scope and provenance audit.

Priority entries:

- T12: exact resolution-width characterization.
- T11: branchwidth/treewidth inequalities.
- T13/T14: proof-system separations.
- T15: CDCL simulation assumptions.
- T16: DRAT versus extended resolution.
- T17: algebraic solving and graph connectivity.
- T18: polynomial calculus field dependence.
- T19: parity-aware proof systems.

For every audited entry require:

- Primary source.
- Exact theorem or corollary locator.
- Graph parameter convention.
- Proof system definition.
- Quantifiers.
- Assumptions.
- Input encoding.
- Bound direction.
- Conditional versus unconditional status.
- Explicit limitations.

Reject theorem statements that merge results from
different models or silently strengthen a cited bound.

The T12 correction is supplied in Section 4.

Other entries remain subject to the independent audit.

Deliver:

docs/phase4/REVIEW_ACE_LITERATURE.md

with a disposition for every theorem-table row.

Acceptance:

Every retained Proved entry has source-supported
assumptions and conclusions.

Unsupported entries are corrected, removed, or
downgraded.

A verified bibliographic citation alone does not
establish that the associated theorem statement
is accurate.

---

## 7. Lumi's independent reproduction duty

Lumi owns authorization and confirmatory execution.

No original artifact author should be the only party
checking its correctness.

Before authorizing test execution:

1. Obtain all five independent review reports.

2. Resolve blocking findings.

3. Merge reviewed fixes into dev.

4. Identify the final execution-code commit.

5. Run the complete relevant test suite.

6. Validate the reference solver and proof checkers.

7. Independently reproduce all 1960 training instances
   using the final code and frozen environment.

8. Compare the reproduced records against Claude's
   original training artifacts.

9. Investigate every discrepancy.

10. Fit M0/M1 using the final validated training records.

11. Retain and hash fitted coefficients and cell means.

12. Generate the new freeze manifest.

13. Record unanimous disclosure of whether any agent
    accessed test-split outcomes.

14. Commit the approved protocol amendments.

15. Authorize the freeze only after all blockers close.

Training reproduction must include the DPLL search
measurements, not just reference certificate validation.

The runner's certificate audit can regenerate and
recheck evidence, but that is not equivalent to
independently reproducing the primary branch counts.

---

## 8. Confirmatory execution

### 8.1 Who runs it?

Lumi.

Claude provides the runner.
Nova provides the analysis.
Dee provides adversarial checks.
Gemini and Ace provide mathematical review.

None of these roles authorizes early test execution.

Lumi should perform the run from a clean checkout of
the frozen execution code.

### 8.2 Example commands

The following command sequence is illustrative of the
current runner interface.

Revalidate CLI compatibility after blocking fixes.

From lab/:

    python -m om_lab.width_experiment seeds \
      --out results/om_c001_r2/seeds.json

    python -m om_lab.width_experiment validate-certifier \
      --out results/om_c001_r2/certifier_validation.json

    python -m om_lab.width_experiment smoke \
      --out-dir results/om_c001_r2/smoke

    python -m om_lab.width_experiment run \
      --split train \
      --out-dir results/om_c001_r2 \
      --workers 4 \
      --watchdog-s 600 \
      --max-attempts 3 \
      --keep-certificates

Generate the draft freeze only after independent
training reproduction and review.

    python -m om_lab.width_experiment freeze \
      --out results/om_c001_r2/freeze.json

Approve and authorize the final manifest using the
reviewed freeze procedure.

Confirm authorization with a dry run.

    python -m om_lab.width_experiment run \
      --split test \
      --freeze results/om_c001_r2/freeze.json \
      --out-dir results/om_c001_r2 \
      --workers 4 \
      --watchdog-s 600 \
      --max-attempts 3 \
      --keep-certificates \
      --dry-run

Verify that exactly 840 instances are scheduled.

Only then execute the same command without --dry-run.

Do not use subset flags for the initial complete test.

The watchdog retry policy handles infrastructure
failures.

If any subsequent diagnostic rerun is necessary,
retain original records and authorization history.

### 8.3 Output locking

Before analyzing test outcomes:

- Lock the raw test JSONL.
- Lock the telemetry JSONL.
- Lock the certificate manifest.
- Hash all retained CNF and proof files.
- Record the frozen execution commit.
- Record the complete invocation.
- Verify exact population completeness.
- Preserve all failure records.

Then combine the validated training and test records.

Run the strict integrity audit.

Recheck the retained UNSAT proofs against the
corresponding original CNF files.

Run the frozen statistical analysis once.

Publish the complete primary result, regardless
of PASS, FAIL or INCONCLUSIVE.

Do not change the registered primary model after
viewing its outcome.

### 8.4 Independent reproduction

Reproduce the same frozen experiment on the same
population.

The independent rerun verifies measurement stability.

It is not a second independent statistical sample.

Record discrepancies between:

- Formula hashes.
- Features and elimination orderings.
- Solver statuses.
- Branch and propagation counts.
- Verification evidence.
- Model coefficients.
- Primary error statistics.
- Bootstrap interval.
- Final disposition.

Wall-clock times, process identifiers and timestamps
need not match.

Different valid proof certificates need not have the
same bytes.

However, each retained certificate must match the
formula it certifies and pass the required checker.

---

## 9. Claim-level audit

### PR #7 — Ace

[Claim Level: Lean-Verified — coordinator-reported]

The repaired Lean implementation reportedly builds
with zero warnings and only permitted standard axioms.

Accept this status for the named successfully checked
theorems, subject to retaining the build and axiom logs.

The original failed submission was not Lean-Verified.

The parentheses repair d365743 is part of the accepted
formalization history.

Do not extend the status to:

- The full Python generator.
- Every disconnected-graph converse.
- Resolution lower bounds.
- Polynomial-time SAT verification.
- P vs NP.

Ace has inspected the repaired source but has not
independently run Lean in this review.

### PR #8 — Dee

[Claim Level: Empirical Observation]

18/18 tests reportedly pass.

Independent Minisat22 observations reportedly give
SAT/UNSAT results consistent with the parity
construction on five cubic graphs.

These tests do not establish correctness for every
possible graph or input.

[Claim Level: Proved — mathematical result]

The structural indistinguishability construction and
component parity characterization have mathematical
derivations.

They must be distinguished from implementation tests.

Do not label the entire Python suite Lean-Verified.

### PR #9 — Nova

[Claim Level: Empirical Observation]

Reported pilot:

M1 improvement = -0.042.

Bootstrap interval = [-0.151,+0.051].

M2 improvement = +0.167.

M3 improvement = +0.127.

Official OM-C001-R2 disposition remains INCONCLUSIVE
because the registered confirmatory test has not run.

The pilot's negative M1 point estimate should be
reported plainly.

Do not describe the pilot as evidence of a successful
width predictor.

The pilot is not a definitive rejection of every
width-based predictor either.

Secondary models remain secondary.

### PR #10 — Claude

[Claim Level: Empirical Observation — author-reported]

1960 training instances reportedly completed with
appropriate certification.

Independent reproduction remains pending.

Maximum reported branch count: 992.

Downgrade any wording suggesting these training
results have already been independently reproduced.

Certificate checking concerns formula status.

It does not independently prove the DPLL branch
counter correct.

The confirmatory hypothesis remains a Conjecture.

### PR #11 — Gemini

[Claim Level: Proved — established literature]

Retain only theorem statements accurately supported
by their cited sources.

Citation-count verification is not equivalent to
theorem-level verification.

T12's original wording is not accepted as Proved.

Replace it with Section 4's source-supported exact
characterization.

Other rows with unresolved assumptions, ambiguous
models or unverifiable bounds remain under review.

They may not inherit Proved status from nearby
verified citations.

### Project-wide audit

No new general complexity lower bound has been
established by Phase 3.

No unrestricted SAT algorithm improvement has been
established.

No result resolving P vs NP has been established.

The current research value is:

- Known-result formalization.
- Reproducible tooling.
- Controlled hypothesis testing.
- Structural counterexamples.
- Improved mathematical specifications.
- Better evidence and proof standards.

---

## 10. Checkable Phase 4 completion criteria

### Gate A: Independent review coverage

[ ] Claude independently reviews Dee's PR #8.
[ ] Gemini independently reviews Ace's PR #7.
[ ] Nova independently reviews Claude's PR #10.
[ ] Dee independently reviews Nova's PR #9.
[ ] Ace independently reviews Gemini's PR #11.

Every review identifies the exact commit attacked.

### Gate B: Finding disposition

[ ] Every review finding has a unique identifier.
[ ] Every finding has a documented severity.
[ ] Every blocker has a reviewed resolution.
[ ] Every accepted limitation is explicitly scoped.
[ ] Every negative result is retained.
[ ] No author is the sole approver of their own fix.

Use these dispositions:

PASS
FAIL
OPEN
N/A

N/A requires a stated reason.

### Gate C: Mathematical integrity

[ ] Lean clean build passes.
[ ] Actual axiom outputs are retained.
[ ] No admitted proofs or custom axioms.
[ ] Concrete graph instantiation succeeds.
[ ] Matched structural claims are independently reviewed.
[ ] Componentwise parity limitation is documented.
[ ] T12 is corrected.
[ ] Literature-table theorem scope audit is complete.

### Gate D: Laboratory integrity

[ ] One canonical production min-fill implementation.
[ ] Independent feature replay succeeds.
[ ] Runner fault-injection tests pass.
[ ] Solver measurement accounting is audited.
[ ] Valid SAT witnesses are independently checked.
[ ] UNSAT certificate evidence is retained and checked.
[ ] UNKNOWN and ERROR remain distinct.
[ ] Population identity is validated.
[ ] Statistical synthetic fixtures pass.
[ ] No unresolved certificate-checker disagreements.

### Gate E: Pre-execution freeze

[ ] All 1960 training records independently reproduced.
[ ] Training coefficients and model artifacts frozen.
[ ] All pre-test amendments approved.
[ ] Execution commit and environment pinned.
[ ] Seed-manifest hashes verified.
[ ] Runner and analysis hashes verified.
[ ] Authorization manifest finalized.
[ ] Test population remains unexposed.
[ ] Dry run schedules exactly 840 instances.

Only after Gates A through E pass may Lumi authorize
confirmatory execution.

### Gate F: Confirmatory reporting

[ ] Raw test output locked before analysis.
[ ] Exactly 840 expected test records accounted for.
[ ] Missing, invalid or failed records disclosed.
[ ] Independent certificate audit performed.
[ ] Frozen analysis executed.
[ ] Primary disposition recorded.
[ ] Secondary results explicitly labeled.
[ ] Independent reproduction attempted and documented.
[ ] All discrepancies resolved or explicitly retained.
[ ] Final research report published without hiding
    negative results.

Phase 4 completion requires all mandatory review
and reporting obligations to be resolved.

A valid terminal empirical disposition may be:

PASS
FAIL
INCONCLUSIVE

A scientific failure of the registered hypothesis is
not a failure to complete Phase 4.

However, unresolved software integrity failures must
not be described as a successful confirmatory experiment.

If an integrity blocker cannot be repaired, Lumi may
close the round with a documented failed or
inconclusive execution rather than authorize an
unsupported claim.

---

## 11. Recommended direction after Phase 4

Do not switch research direction solely to rescue
the width conjecture.

If M1 fails, preserve the result.

The secondary degree model may motivate a separate
Round 02 hypothesis, but cannot retroactively become
the primary Round 01 result.

A particularly promising independent track is:

Certified CNF-to-parity extraction.

Proposed pipeline:

1. Receive ordinary CNF clauses.

2. Recognize complete XOR clause patterns without
   generator metadata.

3. Produce an explicit extraction certificate identifying
   the source clauses.

4. Apply GF(2) equation elimination.

5. Produce a contradiction certificate.

6. Independently check every extraction and algebraic
   step against the original CNF.

The existing xor3CNF_correct theorem supplies an
important semantic foundation for this work.

[Claim Level: Conjecture — untested]

Certified parity extraction may substantially reduce
the measured effort required to establish contradictions
on some structured CNF populations.

The extraction and verification costs must be included.

No claim is made that every CNF contains exploitable
parity structure.

No claim is made that this approach solves general
SAT in polynomial time.

---

## 12. Handoff and limitations

Ace reviewed the relevant merged repository source
at dev d6e385c.

The T12 correction was checked against the original
ECCC paper, including Corollaries 8 and 16.

The remaining theorem-table rows require the full
independent review assigned in Section 6.5.

Phase 3 test counts, Lean build results, training
counts and pilot statistics are coordinator-reported
unless explicitly indicated otherwise.

No new empirical solver experiment was executed.

No Lean build was executed by Ace for this review.

No confirmatory test outcomes were accessed.

No new branch, commit or PR was created.

The operational amendments and robustness thresholds
are proposed research-design decisions.

They require coordinator approval before freeze.

Submit this document against dev.

Never merge to main without Stephon's explicit
approval.

Free resources only.
No credentials or secrets.

Ace — Galactic AI Team
Operation Millennium
