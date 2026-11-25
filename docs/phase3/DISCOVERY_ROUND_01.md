# Operation Millennium — Discovery Round 01

## Structural SAT Complexity, Controlled Experiments and Parity

Author: Ace — Galactic AI Team
Coordinator: Lumi
Research Director: Stephon
Date: 2026-11-25
Base: dev a70f89c
Status: Proposed preregistration; requires coordinator approval and freeze.

No new experimental runs or Lean verification are claimed in this document.
Established mathematical results are distinguished from project conjectures.
All promotion decisions remain subject to docs/RULES.md.

---

## 1. Strategic recommendation

The first discovery round should investigate the relationship between
formula structure, solver search effort, and restricted proof complexity.

Do not make the first round an unrestricted attempt at P vs NP.

Instead, establish three connected deliverables:

A. A controlled empirical test of structural SAT hardness prediction.

B. A matched-instance mathematical investigation using Tseitin formulas.

C. A machine-checked parity theorem connecting the mathematical model
   to the existing CNF semantics.

The three deliverables must remain logically independent.

A failed prediction experiment does not invalidate the parity theorem.
A successful parity theorem does not validate a prediction model.
Neither establishes a general complexity separation.

The scientific objective is to learn which structural information
predicts solver effort, which information is insufficient, and which
claims can actually be established mathematically.

---

## 2. Phase 1 evidence assessment

### 2.1 Pigeonhole benchmark

[Claim Level: Empirical Observation — coordinator-reported]

For PHP with n = 3, 4, 5, 6, 7 holes:

| Holes | DPLL decisions | PySAT cd195 decisions |
|---|---:|---:|
| 3 | 10 | 6 |
| 4 | 62 | 35 |
| 5 | 482 | 168 |
| 6 | 4790 | 1356 |
| 7 | 59010 | 8534 |

All instances were reported UNSAT without timeouts.

These measurements are useful regression benchmarks.

They are not an empirical proof of exponential asymptotic growth.
Five measurements cannot establish a universal lower bound.

Moreover, PHP_n^(n+1) contains n(n+1) Boolean variables.
Scaling in n holes must not be confused with scaling in total
Boolean variables or encoded input length.

DPLL branch attempts and CaDiCaL's internal decisions also have
different operational meanings. Their raw counts should not be
treated as perfectly interchangeable units of computational work.

### 2.2 Nova's structural results

[Claim Level: Empirical Observation — coordinator-reported]

At n = 30:

- Median DPLL decisions peaked at alpha = 4.6, with median 47.
- Co-occurrence mean degree had pooled Spearman correlations of
  approximately +0.48 with DPLL decisions and +0.54 with CDCL conflicts.
- At fixed densities between 4.0 and 4.6, all reported absolute
  correlations were at most 0.32.

Interpretation:

The pooled correlations may substantially reflect changes in density.
The fixed-density results do not establish that structural features
are useless, nor do they establish a reliable predictive relationship.

Treat this analysis as exploratory.

Do not reuse its instances as the confirmatory test population.

The observed solver-effort peak at 4.6 must not be interpreted
as an estimate of the satisfiability threshold itself.

---

## 3. Preregistration: OM-C001-R2

### 3.1 Exact research hypothesis

[Claim Level: Conjecture — untested]

For the specified random 3-SAT experiment population, adding
a deterministic primal-graph min-fill elimination-width feature
to a model controlling exactly for variable count and clause count
reduces held-out mean absolute error in predicting budget-capped
logarithmic DPLL branch effort by at least 5%.

This is a finite, operational prediction hypothesis.

It is not a claim about:

- Every SAT instance.
- Exact treewidth.
- Optimal SAT algorithms.
- Worst-case computational complexity.
- Causal effects of treewidth.
- P vs NP.

Revision note:

The original Phase 1 proposal used completed-only runs and a
polynomial regression on size and density.

This revision deliberately strengthens the density control by using
exact (n,m) cell effects and avoids dropping budget-exhausted runs
by introducing a capped target.

The original proposed model and completed-only target are retained
as secondary analyses.

These changes are made before collection of confirmatory outcomes.
Record this revision explicitly rather than silently replacing C001.

### 3.2 Primary graph representation

Use the primal graph, also called the variable co-occurrence graph.

For a CNF with declared variables 1,...,n:

- Include all n variables as vertices, including isolated variables.
- Connect distinct variables u and v if they occur in the same clause.
- Ignore literal signs.
- Ignore duplicate edges.
- Do not simplify the formula before extracting this feature.

The graph is constructed from the original input formula.

Reason for choosing the primal graph:

It matches the graph already used by features.py.
It has a direct interpretation in variable elimination.
It is smaller than the corresponding incidence graph for this
experiment population.

Incidence-graph width is not the primary feature.

### 3.3 Exact width proxy

Name: primal_min_fill_width

Algorithm:

1. Build mutable adjacency sets for the primal graph.
2. Set W = 0.
3. For each remaining vertex v, calculate:

   fill(v) = number of unordered pairs of distinct neighbors
             of v that are not currently adjacent.

4. Select the vertex minimizing the pair:

   (fill(v), variable_id(v))

   The smallest numerical variable ID breaks ties.

5. Set W = max(W, current_degree(v)).
6. Add every missing edge between neighbors of v.
7. Remove v and all edges incident to v.
8. Repeat until no vertices remain.
9. Return W and the complete elimination ordering.

Return width 0 for the empty graph.

This is a deterministic heuristic upper bound on primal treewidth.
It is not an exact treewidth algorithm.

Do not select between min-fill, min-degree or incidence width
after inspecting confirmatory outcomes.

Alternative proxies belong to a separately labeled exploratory
analysis and require a new preregistration if promoted.

Required feature tests:

| Graph | Expected elimination width |
|---|---:|
| Empty graph | 0 |
| Isolated vertices | 0 |
| Single edge | 1 |
| Path with at least two vertices | 1 |
| Cycle with at least three vertices | 2 |
| Complete graph K_k | k-1 |

Also verify:

- Repeatability.
- Clause-order invariance.
- Literal-sign invariance.
- Duplicate-clause invariance.
- Elimination-order replay.
- Valid handling of isolated variables.

Do not require invariance under arbitrary variable relabeling:
the numerical tie-breaking rule may change the selected ordering.

Instead, test relabeling sensitivity separately.

### 3.4 Experiment population

Use four variable counts:

n = {30, 40, 50, 60}

Use seven requested clause densities:

alpha = {3.8, 4.0, 4.2, 4.26, 4.4, 4.6, 5.0}

Represent these exactly as integer hundredths:

A = {380, 400, 420, 426, 440, 460, 500}

Calculate clause count using integer arithmetic:

m = (A*n + 50) // 100

Generate 100 independently seeded instances per (n,A) cell.

Total:

4 * 7 * 100 = 2800 instances.

Training split:

70 instances per cell = 1960 instances.

Confirmatory test split:

30 instances per cell = 840 instances.

Use the actual clause count m, not rounded display density,
when constructing statistical controls.

### 3.5 Generator and seeds

Use generate_random_3sat from lab/om_lab/generators.py.

Preserve its distribution:

- Three distinct variables sampled uniformly per clause.
- Independent fair literal signs.
- Clauses sampled independently with replacement.
- Duplicate clauses retained.
- Original clause and literal ordering preserved.

Do not sort clauses before sending them to DPLL.

Generate fresh integer seeds using SHA-256.

For cell n,A and index i in 0,...,99:

seed_material = UTF-8("OM-C001-R2|n|A|i")

Replace n, A and i with their base-10 integer representations.

seed = unsigned big-endian integer represented by the first
       16 bytes of SHA-256(seed_material).

Indices 0 through 69 are training.
Indices 70 through 99 are confirmatory test.

Check the generated seed manifest for collisions and against
available Phase 1 experiment manifests.

Do not replace individual instances because they appear unusual.

Pin:

- Python interpreter version.
- Generator source hash.
- Solver source hash.
- Dependency versions.
- Feature implementation hash.
- Statistical analysis implementation hash.

Lumi must retain confirmatory outcomes until the model, metrics,
and acceptance criteria are frozen.

The public deterministic seed scheme is reproducible, not
cryptographically blinded. Agents must not run confirmatory seeds
before the authorized evaluation.

### 3.6 Primary solver

Use the existing pure-Python DPLL implementation at the frozen commit.

Preserve:

- Unit propagation.
- Selection of the first shortest clause.
- Selection of that clause's first remaining variable.
- True-before-False branch ordering.
- Existing branch-attempt counter.

The current counter increments for each attempted branch value.
Refer to it as branch attempts, while retaining the field name
"decisions" for compatibility.

Do not introduce width-guided branching into the primary experiment.

That would change the response variable being predicted.

Primary deterministic decision budget:

B = 10000 branch attempts per instance.

Use max_decisions=B and max_seconds=None.

The current implementation checks its budget at recursive entry.
A run reaching B may therefore be reported UNKNOWN even if the
next recursive evaluation would immediately finish.

Keep this convention fixed.

Use a separate process watchdog only for infrastructure protection.
A watchdog failure is missing experimental data, not a normal
decision-budget exhaustion.

Rerun infrastructure failures with the same instance and budget.
Do not substitute a different seed.

The experiment permits at most 28 million recorded branch attempts
across its primary population. This is a work-counter budget,
not a wall-clock or CPU-time guarantee.

### 3.7 Primary response variable

For each instance i:

Y_i = ln(1 + min(D_i, B))

Where:

- D_i is the number of recorded branch attempts.
- Budget-exhausted runs receive Y_i = ln(1+B).
- Completed runs use their recorded attempt count.
- ln is the natural logarithm.

This measures capped search effort.

It does not estimate the unknown total effort beyond the cap.

An UNKNOWN run must remain UNKNOWN.
It must never become an UNSAT example.

### 3.8 Primary prediction models

Define a cell c by the exact pair (n,m).

Model M0: saturated size-and-density baseline.

For each cell, calculate the mean Y using only training instances
from that cell.

M0 predicts that training mean for every test instance in the cell.

Model M1: same baseline plus one width feature.

Within each training cell calculate:

mean_Y_c = mean of Y
mean_W_c = mean of primal_min_fill_width

Estimate a single shared slope:

beta =
  sum((W_i - mean_W_c)*(Y_i - mean_Y_c))
  /
  sum((W_i - mean_W_c)^2)

Both sums include training instances only.

For a test instance:

prediction_M1 =
  mean_Y_c + beta*(W_i - mean_W_c)

Clip both models' predictions to [0, ln(1+B)].

Do not use:

- Feature selection.
- Hyperparameter tuning.
- Regularization searches.
- Solver status as a predictor.
- Test-set normalization.
- Runtime as a predictor.
- Test-set coefficient estimation.

If the slope denominator is zero, the feature is unidentifiable.
Record the result as INCONCLUSIVE rather than changing proxies.

This model asks whether width carries information within cells
after controlling for both variable count and clause count.

It does not merely ask whether larger or denser formulas are harder.

### 3.9 Primary statistic

For the 840 held-out instances:

MAE_0 = mean(abs(Y_i - prediction_M0_i))

MAE_1 = mean(abs(Y_i - prediction_M1_i))

Improvement = 1 - MAE_1 / MAE_0

The proposed practical effect threshold is 0.05.

Because the test population has 30 instances per cell, each cell
receives equal weight in the pooled statistic.

If MAE_0 = 0, the percentage improvement is undefined.
Return INCONCLUSIVE.

### 3.10 Uncertainty and acceptance criteria

Use a paired, stratified percentile bootstrap.

- 10000 bootstrap replicates.
- NumPy Generator with PCG64.
- Bootstrap seed: 9012026.
- Pin NumPy version.
- Within each of the 28 test cells, sample 30 test rows with
  replacement.
- Resample the paired errors of M0 and M1 together.
- Retain equal cell weights.
- Recalculate the improvement for each replicate.
- Report the 2.5th and 97.5th percentiles using linear interpolation.

The fitted models remain fixed during this bootstrap.

The interval quantifies test-sample variability conditional
on the frozen fitted models. It does not quantify every possible
source of training or model-selection uncertainty.

Decision rules:

PASS:

- Data integrity and verification gates pass.
- Point improvement is at least 5%.
- Lower endpoint of the bootstrap interval is greater than zero.

FAIL:

- Data integrity gates pass.
- Point improvement is below 5%.

INCONCLUSIVE:

- Point improvement is at least 5%, but the interval includes
  zero or negative improvement.
- Missing confirmatory rows remain.
- Verification or reproducibility gates fail.
- The baseline error or slope is undefined.
- Bootstrap improvement cannot be computed reliably.

The finite 5% target is not met when point improvement is below 5%.

FAIL does not prove that structural information is useless.
PASS does not prove that the population improvement is at least
5% with 95% confidence.

Report effect size and interval regardless of disposition.

Do not run another test population until obtaining PASS.
A failed result remains in the permanent research record.

### 3.11 Secondary analyses

All of the following are secondary and cannot rescue a failed
primary test:

1. Original C001-style completed-only regression, using size,
   actual density, size-density interaction, squared density,
   and an added min-fill-width feature.

2. Per-cell Spearman correlations between width and effort.
   Report every cell, including undefined correlations.

3. Degree-adjusted models:

   M2 = exact cell effects + co-occurrence mean degree.
   M3 = exact cell effects + mean degree + min-fill width.

   Compare M2 and M3 using the same held-out MAE statistic.

4. Separate performance summaries for SAT, independently
   certified UNSAT, and UNKNOWN instances.

5. Budget-hit prediction and per-cell completion rates.

6. CDCL conflicts and decisions as separate solver-specific
   responses.

7. Min-degree and incidence-graph width comparisons.

8. Relabeling and clause-order sensitivity.

The degree-adjusted analysis is particularly important given
Nova's original degree correlation.

A positive M0/M1 result alone does not establish that width
contains information beyond every other graph feature.

All secondary analyses must be labeled secondary or exploratory.
No post-hoc feature may be promoted without a new test protocol.

---

## 4. Mandatory laboratory integrity gate

Repository review at a70f89c identified the following issues.

### 4.1 UNSAT verification semantics

In solvers.py, both the PySAT and DPLL paths set verified=True
for completed UNSAT results without independently checking
an UNSAT proof certificate.

This is not independent UNSAT verification.

Do not represent the current field as proof certification.

Proposed replacement semantics:

status:

- SAT
- UNSAT
- UNKNOWN
- ERROR

verification_status:

- SAT_WITNESS_CHECKED
- UNSAT_PROOF_CHECKED
- UNSAT_KNOWN_BY_CONSTRUCTION
- UNSAT_SOLVER_AGREEMENT_ONLY
- UNVERIFIED
- NOT_APPLICABLE
- INVALID

Known-by-construction requires a justified mathematical statement
and validation that the generated instance matches that construction.

Agreement between two solvers is useful cross-checking.
It is not independently checked UNSAT proof evidence.

For random UNSAT instances, implement a proof-producing reference
solver and independent proof checker using free software.

Retain the original formula, certificate hash, checker identity,
checker version, and result.

Do not assume that every PySAT backend supports proof logging.

Validate the selected backend and checker together before
freezing the experiment.

### 4.2 Timeout handling

The current SolveResult contains timed_out.

However, the ExperimentRecord in harness.py does not preserve it.

The current harness also raises an assertion for unverified results,
which prevents ordinary budget exhaustion from becoming a valid
logged observation.

This must be repaired before OM-C001-R2.

Requirements:

- Preserve explicit status.
- Preserve timeout/budget reason.
- Preserve decision and propagation counts.
- Retain UNKNOWN rows.
- Reject invalid SAT witnesses.
- Do not count UNKNOWN as UNSAT.
- Do not silently exclude unverified UNSAT rows.

The confirmatory experiment may record operational measurements
from uncertified runs, but cannot receive its final PASS
disposition until its verification gates are satisfied.

### 4.3 Required regression cases

- Empty CNF: SAT.
- CNF containing an empty clause: UNSAT.
- Contradictory units: UNSAT.
- Budget exhaustion: UNKNOWN.
- Satisfiable formula with corrupted model: INVALID.
- UNSAT claim with corrupted certificate: INVALID.
- Planted formula with its planted assignment: SAT witness checked.
- Repeated deterministic run: matching status and branch counts.

---

## 5. Discovery Round 01: matched structural instances

### 5.1 Central research question

How much information about SAT and solver effort is lost when
a formula is reduced to its unsigned variable interaction graph?

Use the existing Tseitin generator as the central test family.

This connects the empirical experiment with a mathematical
result that can be proved and formalized.

### 5.2 Exact structural indistinguishability result

[Claim Level: Proved — elementary derivation supplied;
pending independent team review]

Let G be a finite simple 3-regular graph with at least one vertex.

Associate a Boolean variable x_e with each edge e.

At each vertex v impose the parity equation:

XOR of incident edge variables = charge(v).

Encode every parity equation on its three incident variables
using the four width-three clauses that exclude the assignments
with incorrect parity.

Define two formulas on the same graph:

F_even: every vertex has charge zero.

F_odd: exactly one vertex has charge one.

Then:

1. F_even is satisfiable.
2. F_odd is unsatisfiable.
3. Their unsigned primal graphs are identical.
4. Their unsigned incidence graphs are isomorphic, and can
   be made identical under corresponding clause indexing.
5. Their variable counts and clause counts are identical.
6. Their positive and negative literal occurrence counts
   are identical for each variable.

Proof:

For F_even, assigning zero to every edge variable satisfies
every vertex parity equation.

For F_odd, sum every vertex parity equation modulo two.
Every edge appears at its two endpoints, so its contribution
to the sum is zero.

The left-hand side is therefore zero.

Exactly one vertex has charge one, so the right-hand side is one.

This gives the contradiction 0 = 1.

For either charge value, each local parity equation is encoded
by four clauses containing the same three distinct variables.

Changing the charge changes signs, not variable incidence.

The primal and unsigned incidence graphs therefore remain
unchanged up to the stated correspondence.

In either parity encoding, each of the three local variables
appears positively twice and negatively twice.

Consequently, changing the charge also preserves each variable's
total positive and negative occurrence counts.

This proves all six statements.

This is an elementary consequence of the standard Tseitin
construction, not a novelty claim.

### 5.3 Immediate implication

[Claim Level: Proved — elementary consequence;
pending independent team review]

No deterministic classifier whose only input is the unsigned
primal graph can correctly decide satisfiability for every
formula in the above matched family.

Proof:

The classifier receives identical graph inputs for F_even
and F_odd and must return the same answer for both.

One formula is satisfiable and the other is unsatisfiable.

Therefore, at least one answer must be wrong.

This also applies to classifiers depending exclusively on
any deterministic features of that unsigned graph.

Scope:

This is an information-loss result about a deliberately
restricted representation.

It is NOT a general SAT algorithm lower bound.
It does NOT imply P != NP.
It does NOT establish that treewidth cannot predict solver effort.

An algorithm inspecting literal signs or parity constraints
is outside the restricted representation.

### 5.4 Matched-pair solver hypothesis

[Claim Level: Conjecture — exploratory]

The even-charge and odd-charge Tseitin pairs may exhibit
substantially different DPLL effort despite having identical
unsigned structural features.

This is not assumed to hold universally.

Test on Mobius-ladder vertex counts:

{4, 6, 8, 10, 12, 16, 20, 24, 32}

For each graph, compare:

- All-zero charge.
- Exactly one nonzero charge.
- Exactly two nonzero charges.

Use a deterministic decision budget and retain UNKNOWN runs.

Apply matched variable-ID permutations and matched clause
permutations to each charge variant.

Use seeds 100 through 119 for the permutation sensitivity suite.

Do not independently reorder the two members of a matched pair.

Report paired effort differences, completion status, and
permutation variability.

Do not assume that UNSAT is necessarily harder than SAT.
The direction of the difference is an empirical question.

No confirmatory effect-size claim is registered for this
exploratory matched-pair experiment.

---

## 6. Important limitation of the Mobius-ladder family

[Claim Level: Proved — elementary upper bound;
pending independent team review]

The current Mobius-ladder generator should not be treated
as an automatically expanding, increasing-treewidth family.

In fact, its underlying graph has treewidth at most five.

Proof:

Write the graph as 2k vertices, where k >= 2.

Define rung R_i = {i, i+k} for i = 0,...,k-1.

The matching edges lie inside individual rungs.

Cycle edges connect consecutive rungs, including the wraparound
connections between the last and first rung.

Construct path-decomposition bags:

B_i = R_0 union R_i union R_(i+1)

for i = 0,...,k-2.

Each bag contains at most six vertices.

Every vertex belongs to a bag.

Every matching edge is contained in a bag.

Every cycle edge between consecutive rungs is contained in
the corresponding bag.

The wraparound edges are contained in the final bag because
it contains both R_(k-1) and R_0.

Vertices in R_0 appear in every bag.
Vertices in other rungs appear in one or two consecutive bags.

Thus the running-intersection condition holds.

This is a valid path decomposition of width at most 5.

Consequently, the graph's treewidth is at most 5.

For k=2, the single bag contains all four vertices.

### 6.1 Consequence for the CNF primal graph

[Claim Level: Proved — elementary upper bound;
pending independent team review]

The primal graph of the corresponding Tseitin CNF is the
line graph of the underlying simple 3-regular graph.

Each primal vertex represents an original graph edge.
Two primal vertices are adjacent exactly when their original
edges share an endpoint.

Replace every original decomposition bag with the set of
all graph edges incident to its vertices.

Each replacement bag contains at most 6*3 = 18 edges.

Adjacent line-graph vertices share an original endpoint,
so they occur together in some replacement bag.

For each original edge uv, its line-graph vertex occurs in
the union of the bag intervals of u and v.

Those intervals intersect because uv belongs to an original bag.

Their union is therefore connected.

The replacement bags form a valid line-graph path decomposition.

The primal treewidth is consequently at most 17.

This is an upper bound, not a claim of exact treewidth.

A heuristic min-fill ordering may return a larger bound.

### 6.2 Research implication

Keep Mobius ladders as a useful bounded-width control family.

Add separately generated connected 3-regular graphs with
potentially larger width.

Do not label a sampled random regular graph an expander
without an appropriate mathematical guarantee or measurement.

A measured expansion proxy is not a proved expansion bound.

The comparison between bounded-width and broader graph families
is more valuable than assuming every Tseitin instance is hard.

---

## 7. Teammate assignments

### 7.1 Claude — algorithms and experiment infrastructure

Primary assignment:

Implement the frozen OM-C001-R2 experiment runner.

Suggested files:

- lab/om_lab/width_experiment.py
- lab/om_lab/harness.py
- lab/om_lab/solvers.py
- lab/tests/test_width_experiment.py

Responsibilities:

- Repair status and verification semantics.
- Implement deterministic budget-aware logging.
- Preserve the existing baseline branching policy.
- Implement training/test population construction.
- Run training and infrastructure smoke tests.
- Implement or integrate independent UNSAT proof verification.
- Supply the exact reproducible command for Lumi.

Acceptance:

- Every expected instance produces exactly one primary record.
- UNKNOWN is retained and never confused with UNSAT.
- Repeated deterministic runs reproduce branch counts.
- No confirmatory results are generated before the freeze.

Stretch work after the primary runner is frozen:

Implement a separate width-guided DPLL variant.

Do not replace the primary baseline with that variant.

### 7.2 Gemini — literature and mathematical context

Primary assignment:

Produce a focused literature map for graph width, Tseitin
contradictions, and restricted proof complexity.

Suggested file:

docs/phase3/WIDTH_TSEITIN_LITERATURE.md

Start with:

- Ben-Sasson and Wigderson's resolution width/size results.
- Treewidth-parameterized SAT and model-counting algorithms.
- Tseitin resolution lower bounds.
- Differences between regular, tree-like and unrestricted
  resolution.
- Gaussian elimination over GF(2).

For each theorem record:

- Exact proof system or computational model.
- Graph representation used.
- Quantifiers and parameter definitions.
- Upper versus lower bound.
- Assumptions.
- Primary-source citation.
- What the theorem does not establish.

Pay particular attention to whether known results already
subsume our proposed structural observations.

Acceptance:

An auditable theorem table with verified references and
explicit scope limitations.

Do not treat a known theorem reproduced by our team as a
newly discovered mathematical result.

### 7.3 Nova — structural feature discovery

Primary assignment:

Implement primal_min_fill_width and the frozen prediction
analysis in Section 3.

Suggested files:

- lab/om_lab/width_features.py
- lab/om_lab/analyze_width.py
- lab/tests/test_width_features.py

Responsibilities:

- Implement deterministic min-fill elimination.
- Return the width and ordering.
- Implement independent elimination-order replay.
- Implement M0 and M1 exactly.
- Implement paired stratified bootstrap evaluation.
- Produce per-cell plots and error summaries.
- Test degree-adjusted prediction as a secondary analysis.

Acceptance:

- All graph fixtures pass.
- No label leakage.
- No confirmatory feature selection.
- One machine-readable primary disposition.
- Every negative or inconclusive result retained.

Nova may continue exploratory pattern discovery on separate
instances, but those results must not modify the frozen
confirmatory test.

### 7.4 Dee — adversarial instances and counterexamples

Primary assignment:

Build the matched Tseitin structural counterexample suite.

Suggested files:

- lab/om_lab/matched_instances.py
- lab/tests/test_matched_instances.py
- docs/phase4/STRUCTURAL_COUNTEREXAMPLES.md

Responsibilities:

- Generate matched even-charge and odd-charge formulas.
- Verify equality of unsigned graph representations.
- Verify per-variable positive and negative occurrence counts.
- Independently validate all-zero satisfiability witnesses.
- Validate odd-charge contradictions by the parity argument.
- Generate connected simple 3-regular comparison graphs.
- Apply deterministic matched permutations.
- Attack the stability of width estimates and solver effort.

Include negative cases:

- Disconnected graphs.
- Incorrect incidence multiplicities.
- Malformed XOR encodings.
- Repeated edge identifiers.
- Invalid graph construction.
- Incorrect charge metadata.

For disconnected graphs, do not use even total charge as a
sufficient satisfiability criterion.

The parity condition must hold separately in every component.

Acceptance:

A reproducible suite that actively attempts to invalidate
our structural assumptions and formal specification.

### 7.5 Ace — theory and Lean formalization

Primary assignment:

Formalize Tseitin parity unsatisfiability and its connection
to the existing CNF semantics.

Suggested files:

- lean/Millennium/Tseitin.lean
- lean/Millennium.lean
- docs/phase3/TSEITIN_PROOF_SPEC.md

Use the existing Lean 4.24.0 and Mathlib v4.24.0 workspace.

Mathematical target A:

For finite vertex and edge types, assign each edge a value
in ZMod 2.

Represent each edge by two endpoints.

Define vertex parity as the sum of incident edge contributions,
counting both endpoint incidences.

Prove that the sum of all vertex parities is zero.

Mathematical target B:

If every vertex parity equals its assigned charge, then the
sum of all charges is zero.

Therefore, charges summing to one cannot be satisfied by any
edge assignment.

Mathematical target C:

Connect the four-clause XOR encoding to Millennium.evalCNF.

Define a function taking variable indices a,b,c and a
Boolean right-hand side.

For rhs=true, encode:

(a OR b OR c)
(a OR NOT b OR NOT c)
(NOT a OR b OR NOT c)
(NOT a OR NOT b OR c)

For rhs=false, encode:

(NOT a OR NOT b OR NOT c)
(NOT a OR b OR c)
(a OR NOT b OR c)
(a OR b OR NOT c)

Prove for every assignment that the resulting CNF evaluates
to true exactly when the three assigned Boolean values have
the requested XOR parity.

Proof method:

Case analysis on the three Boolean values and rhs.

This is a finite semantic equivalence, not an algorithmic
complexity theorem.

### Proposed Lean theorem interfaces

The following are specifications, not compiled Lean code.

vertexParity:

Inputs:

- Finite vertex type V.
- Finite edge type E.
- Endpoint maps u,v : E -> V.
- Assignment x : E -> ZMod 2.
- Vertex a : V.

Return:

Sum over edges e of:

(if u(e) = a then x(e) else 0)
+
(if v(e) = a then x(e) else 0)

Theorem sum_vertexParity_eq_zero:

Sum over all vertices a of vertexParity(u,v,x,a) = 0.

Proof strategy:

Exchange the finite vertex and edge sums.

For each edge, its first endpoint contributes x(e) once
and its second endpoint contributes x(e) once.

Thus each edge contributes x(e)+x(e)=0 in ZMod 2.

Theorem odd_charge_unsat:

Given charge : V -> ZMod 2 satisfying:

sum over V of charge = 1,

there does not exist x : E -> ZMod 2 such that:

for every a in V,
vertexParity(u,v,x,a) = charge(a).

Proof strategy:

Assume a satisfying edge assignment.
Sum its vertex equalities.
Apply sum_vertexParity_eq_zero.
Derive 0=1 in ZMod 2.

Theorem xor3CNF_correct:

For every assignment sigma and variable indices a,b,c,
evaluation of xor3CNF(a,b,c,rhs) equals the Boolean test
that their XOR parity equals rhs.

Final integration target:

Show that a correctly encoded finite 3-regular Tseitin
formula with odd total charge has no satisfying assignment
under Millennium.evalCNF.

Explicitly account for the relationship between abstract
edge identifiers and DIMACS variable indices.

Do not assume that a Python-generated CNF satisfies the Lean
construction merely because their names or metadata match.

Acceptance:

- Import Tseitin.lean from Millennium.lean.
- Clean lake build.
- No sorry or admitted proof.
- No custom axioms.
- Audit #print axioms for each exported theorem.
- Independently review the theorem statements.
- Validate fixed Python/Lean CNF fixtures for both rhs values.

Claim status:

The mathematical parity argument is established.
The implementation and Lean proof are not yet delivered.

No Lean-Verified label is authorized until the required
build and axiom audit actually succeed.

---

## 8. Lumi — coordination and verification

Lumi should own the confirmatory execution boundary.

Before the experiment:

1. Approve this preregistration.
2. Freeze the implementation commit.
3. Freeze generator, seed and dependency manifests.
4. Freeze the primary metric and acceptance criteria.
5. Verify the infrastructure regression suite.
6. Authorize confirmatory execution.

After the experiment:

1. Independently reproduce results.
2. Audit missing or invalid records.
3. Verify the certificate evidence.
4. Execute the frozen statistical analysis.
5. Publish the result without changing its disposition.
6. Preserve negative results.

Recommended artifacts:

- preregistration.md
- freeze.json
- seeds.json
- results.jsonl
- certificate_manifest.json
- primary_result.json
- secondary_results.json
- reproduction.md

Use SHA-256 hashes in freeze.json.

---

## 9. Phase 4 adversarial review

### 9.1 Statistical attacks

Nova's analysis must survive:

- Density-confounding audit.
- Train/test leakage audit.
- Feature-selection audit.
- Duplicate-record audit.
- Censoring and missingness audit.
- Per-cell heterogeneity analysis.
- Degree-adjusted comparison.
- Independent reproduction.

Explicitly check that the test outcome did not influence
the final feature, budget, model or threshold.

### 9.2 Solver attacks

Claude's implementation must survive:

- Empty and contradictory formulas.
- Invalid witnesses.
- Incorrect UNSAT certificates.
- Budget boundary cases.
- Variable relabeling.
- Clause reordering.
- Literal reordering.
- Repeated deterministic execution.
- Planted satisfiable instances.
- Known contradictory instances.

A DPLL search-effort observation is not automatically a
statement about CDCL, proof size or optimal algorithms.

### 9.3 Mathematical attacks

The theory result must survive:

- Empty graph cases.
- Invalid edge incidence.
- Self-loop and parallel-edge conventions.
- Disconnected graphs.
- Invalid variable mappings.
- Wrong XOR charge encodings.
- Hidden assumptions in graph decompositions.
- Confusion between the graph and its line graph.

For the restricted classifier result, verify that its input
really excludes sign and charge information.

If additional information is permitted, the indistinguishability
argument may no longer apply.

### 9.4 Complexity barrier audit

For the narrow mathematical results:

Relativization: N/A as a P vs NP obstruction.
The results do not separate relativized complexity classes.

Natural proofs: N/A.
We are not proving general Boolean circuit lower bounds.

Algebrization: N/A.
We are not making a complexity-class separation claim.

Representation and scope: REQUIRED.

Check finite graph encoding, variable identifiers,
feature computation costs, and proof-system assumptions.

Any later attempt to infer P != NP requires a separate
full barrier and complexity audit.

Passing the restricted audit cannot be inherited by an
unrestricted claim.

---

## 10. Phase 1 items to reject or downgrade

### 10.1 Reject UNSAT solver trust as independent verification

Current verified=True for a completed UNSAT solver return
does not constitute independently verified proof evidence.

Correct the terminology and infrastructure.

Preserve previous benchmarks, but describe their verification
status accurately.

### 10.2 Downgrade unrestricted structural hardness claims

The existing correlations are exploratory.

Do not claim co-occurrence degree or width causes hardness.

Do not infer general SAT complexity from finite solver data.

### 10.3 Downgrade Mobius ladders as generic hard instances

Their odd-charge formulas are mathematically contradictory.

That does not establish computational hardness for this
particular graph family.

Section 6 provides explicit constant-width upper bounds.

Keep them as controls rather than automatically labeling
them increasing-width hard instances.

### 10.4 Downgrade Impagliazzo's Five Worlds from theorem status

The alternative-techniques survey currently describes the
Five Worlds using a proved-taxonomy label.

These are conceptual scenarios organizing possible
relationships between complexity and cryptography.

Do not present the scenario classification as a proved
resolution of those relationships.

Use a literature-framework designation, with conjectural
relationships labeled separately.

### 10.5 Narrow the average-case reduction barrier

Do not infer that every approach to excluding Heuristica
requires non-black-box techniques.

The cited Bogdanov–Trevisan result concerns specified
nonadaptive worst-case-to-average-case reductions.

The stronger blanket conclusion exceeds that scope.

Retain the actual conditional theorem and its assumptions.

### 10.6 Repair the remaining Fagin citation

Use Ronald Fagin's author-maintained publication index and
the original paper rather than relying on an unverified
Semantic Scholar identifier.

Author index:

https://ronfagin.com/papers/

The bibliographic uncertainty does not require rejecting
Fagin's theorem itself.

### 10.7 Retain alternative frameworks without premature priority

Descriptive complexity, fine-grained complexity,
average-case complexity, and extended Frege are valuable
literature tracks.

None presently supplies a sufficiently concrete team plan
for an unrestricted separation.

Do not reject them as mathematical approaches.

Defer them as primary engineering priorities until we have
specific statements, deliverables and falsification methods.

---

## 11. Reference anchors

These references supplement the already verified Phase 1
literature map.

[1] Ben-Sasson and Wigderson.
Short Proofs are Narrow — Resolution Made Simple.
ECCC TR99-022.

https://eccc.weizmann.ac.il/report/1999/022/

Relevant to resolution width/size relationships and Tseitin
contradictions.

[2] Itsykson, Riazanov and Smirnov.
Tight Bounds for Tseitin Formulas.
SAT 2022.

https://doi.org/10.4230/LIPIcs.SAT.2022.6

Relevant to treewidth-dependent lower bounds for regular
resolution and specified OBDD refutation systems.

Do not generalize these results to all SAT algorithms.

[3] Samer and Szeider.
A Fixed-Parameter Algorithm for #SAT with Parameter
Incidence Treewidth.

https://arxiv.org/abs/cs/0610174

Relevant to structural parameterization and the distinction
between primal and incidence graph representations.

[4] Bogdanov and Trevisan.
On Worst-Case to Average-Case Reductions for NP Problems.

https://doi.org/10.1137/S0097539705446974

Authoritative archive:

https://eccc.weizmann.ac.il/report/2005/015/

Relevant to the scope of nonadaptive reduction barriers.

[5] Fagin.
Generalized First-Order Spectra and Polynomial-Time
Recognizable Sets.

Author-maintained publication index:

https://ronfagin.com/papers/

References [1] through [5] are established literature anchors.
Gemini should verify detailed theorem statements before
incorporating them into new technical proofs.

---

## 12. Round completion criteria

Discovery Round 01 is complete when:

- OM-C001-R2 receives PASS, FAIL or INCONCLUSIVE under
  the frozen protocol.
- The experiment is independently reproduced.
- All relevant negative results are published.
- The matched Tseitin structural suite is reproducible.
- The structural indistinguishability result is reviewed.
- The Mobius-ladder width bounds are independently reviewed.
- The parity theorem is formalized or its remaining Lean
  blockers are explicitly documented.
- The Phase 4 adversarial review is complete.

A negative empirical result is a valid completion outcome.

A Lean verification failure is not hidden by changing
the claim label.

There is no requirement to produce a novel complexity
separation to complete this round.

---

## 13. Handoff and limitations

This document was prepared against the requested dev base
a70f89c using repository source inspection and verified
literature records.

The Phase 1 experimental measurements are coordinator-reported;
Ace has not independently rerun those measurements here.

The proposed sample sizes, budget, statistical models,
effect threshold and task assignments are research-design
decisions requiring coordinator approval before freeze.

No new experiment was executed for this handoff.

No Lean compilation or machine verification was performed.

No remote branch, commit or PR was created.
The previous GitHub write-permission blocker remains relevant.

Deliver this document through a PR targeting dev.

Never merge to main without Stephon's explicit approval.

Free resources only. No credentials or secrets.

End of Discovery Round 01 specification.

Ace — Galactic AI Team
Operation Millennium
