<!-- docs/phase4/reviews/REVIEW_PR11_ACE.md -->

# Phase 4 — Independent Adversarial Review of PR #11

Reviewer: Ace — Galactic AI Team
Artifact author: Gemini
Coordinator: Lumi
Research Director: Stephon
Date: 2026-11-25

Reviewed commit:
0f550848808f53737c0466207ce745293405bc6f

Earlier assigned base:
7fd74bd

Reviewed artifact:
docs/phase3/WIDTH_TSEITIN_LITERATURE.md

Reviewed artifact Git blob:
4b57a6118c68035885a65f05f3d6e8725343d56b

Additional review:
docs/phase4/reviews/REVIEW_PR10_NOVA.md

Overall disposition: FAIL — corrections required.

Review coverage: COMPLETE for T1–T19 dispositions.
Resolution of findings: OPEN.
Gate C literature approval: NOT YET GRANTED.

No confirmatory test instances were executed or accessed.
No Lean build was executed for this assignment.
No new complexity separation is claimed.

---

## 1. Review methodology

Each theorem-table entry was inspected for:

- Mathematical statement.
- Proof-system definition.
- Graph representation.
- Parameter conventions.
- Quantifier accuracy.
- Input representation.
- Upper versus lower bound direction.
- Conditional versus unconditional status.
- Primary-source provenance.
- Whether its claimed consequences follow.

Where accessible, primary theorem statements were checked.

Where exact historical results or numerical bounds could
not be established from the accessible primary material,
the corresponding claim was left OPEN or replaced by a
narrower, independently supported statement.

Bibliographic verification is not theorem verification.

The four claim levels are used as follows:

- Proved: established mathematical result or explicit
  mathematical derivation.
- Empirical Observation: executed finite tests, source
  inspection, or coordinator/reviewer-reported evidence.
- Conjecture: unproved hypothesis or technical claim
  awaiting proof review.
- Lean-Verified: reserved for applicable machine-checked
  results satisfying the repository's proof rules.

Severity:

- HIGH: materially incorrect theorem, representation
  confusion, or unsupported research conclusion.
- MEDIUM: missing assumptions, inaccurate quantifiers,
  unverified strengthening, or incorrect parameterization.
- LOW: notation, documentation or citation precision.
- INFO: accepted result or useful clarification.

Disposition:

- PASS: statement accepted within explicitly stated scope.
- FAIL: current statement must be corrected.
- OPEN: insufficient evidence for approval.
- N/A: requirement does not apply, with justification.

A FAIL is a disposition on the reviewed statement.
It is not a claim that the entire cited paper is incorrect.

For every FAIL or OPEN finding below, Gemini may submit
a repair, but Ace or another independent reviewer must
approve the replacement.

---

## 2. Theorem-table disposition ledger

| ID | Row | Severity | Claim level of finding | Disposition |
|---|---|---|---|---|
| ACE-R11-01 | T1 | INFO | Proved | PASS |
| ACE-R11-02 | T2 | INFO | Proved | PASS |
| ACE-R11-03 | T3 | MEDIUM | Proved | FAIL |
| ACE-R11-04 | T4 | HIGH | Proved | FAIL |
| ACE-R11-05 | T5 | MEDIUM | Proved | FAIL |
| ACE-R11-06 | T6 | LOW | Proved | PASS |
| ACE-R11-07 | T7 | MEDIUM | Proved, conditional | FAIL |
| ACE-R11-08 | T8 | MEDIUM | Proved | FAIL |
| ACE-R11-09 | T9 | INFO | Proved | PASS |
| ACE-R11-10 | T10 | HIGH | Proved | FAIL |
| ACE-R11-11 | T11 | HIGH | Proved | FAIL |
| ACE-R11-12 | T12 | HIGH | Proved | FAIL |
| ACE-R11-13 | T13 | MEDIUM | Proved | FAIL |
| ACE-R11-14 | T14 | MEDIUM | Proved | FAIL |
| ACE-R11-15 | T15 | HIGH | Proved | FAIL |
| ACE-R11-16 | T16 | INFO | Proved | PASS |
| ACE-R11-17 | T17 | MEDIUM | Proved | FAIL |
| ACE-R11-18 | T18 | HIGH | Proved | FAIL |
| ACE-R11-19 | T19 | HIGH | Proved | FAIL |

Additional findings:

| ID | Target | Severity | Claim level | Disposition |
|---|---|---|---|---|
| ACE-R11-20 | Section 1 graph conventions | MEDIUM | Proved | FAIL |
| ACE-R11-21 | Section 4 subsumption audit | HIGH | Proved / Empirical Observation | FAIL |
| ACE-R11-22 | New November 2026 literature | HIGH | Empirical Observation / Conjecture | OPEN |
| ACE-R11-23 | Prior citation markers | LOW | Empirical Observation | OPEN |

Summary:

- PASS: 5 theorem-table rows.
- FAIL: 14 theorem-table rows.
- Every T1–T19 row received a disposition.
- Additional findings remain open until reviewed repairs.

These counts concern the current wording of the document,
not the number of false mathematical results in the
underlying literature.

Several FAIL rows contain valid core theorems but attach
incorrect assumptions, exact bounds, or consequences.

---

## 3. Individual theorem audit

### ACE-R11-01 — T1: Tree-like resolution size-width

Severity: INFO
Claim level: Proved — established literature
Disposition: PASS

Accepted statement:

For an unsatisfiable CNF F, let:

- w0 be the maximum initial clause width.
- W be minimum unrestricted resolution refutation width.
- ST be minimum tree-like resolution refutation size.

Then:

    ST >= 2^(W - w0).

Equivalently:

    W <= w0 + log2(ST).

Primary source:

Ben-Sasson and Wigderson,
Short Proofs Are Narrow — Resolution Made Simple.

Theorem 3.3 and Corollary 3.4.

https://people.inf.ethz.ch/emo/SatSem05/Papers/BensassonWidgerson01.pdf

Reproduction:

Read Section 3, matching the paper's definitions of
resolution, weakening, proof width and proof size.

Limit:

This is a lower bound on tree-like proof size.
It is not a universal lower bound on SAT-solving time.

Retain the theorem.

---

### ACE-R11-02 — T2: General resolution size-width

Severity: INFO
Claim level: Proved — established literature
Disposition: PASS, with explicit width convention

The source establishes:

    W <= w0 + O(sqrt(n * ln(S))).

Here n counts Boolean variables and S counts proof lines
under the paper's proof-size convention.

Consequently, when W >= w0:

    S >= exp(Omega((W - w0)^2 / n)).

For a convention allowing unused wide input clauses to
be omitted from a refutation, a universally safe form is:

    S >= exp(Omega(max(0, W-w0)^2 / n)).

Do not square a negative width gap.

Primary source:

Ben-Sasson and Wigderson.

Theorem 3.5 and Corollary 3.6.

https://people.inf.ethz.ch/emo/SatSem05/Papers/BensassonWidgerson01.pdf

Reproduction:

Rearrange Theorem 3.5 after taking the nonnegative
part of the width difference.

Limit:

The theorem does not provide an exponential size lower
bound when its width gap is only O(sqrt(n)).

This limitation belongs to this particular theorem.
It does not establish that stronger lower bounds are
unknown or impossible.

---

### ACE-R11-03 — T3: Optimality of the size-width tradeoff

Severity: MEDIUM
Claim level: Proved — established literature
Disposition: FAIL

The current table conflates GT_n and MGT_n.

The bounded-initial-width construction in Bonet and
Galesi is the modified ordering formula MGT_n.

The original ordering formula has wide initial clauses.

The document also uses inconsistent meanings of n
between its summary and detailed theorem records.

Correct replacement:

There is a family of constant-width CNFs MGT_n with
O(n^2) Boolean variables, polynomial-size resolution
refutations, and minimum resolution width Omega(n).

Expressed in terms of the Boolean variable count N,
the corresponding lower bound is Omega(sqrt(N)).

Do not retain the specific O(n^3) proof-size bound for
the modified construction without separately checking
that bound in its intended parameterization.

Primary source:

Bonet and Galesi,
Optimality of Size-Width Tradeoffs for Resolution.

Theorems 3.2, 3.7 and 3.8.

https://www.cs.upc.edu/~bonet/revistas/computational_complexity.pdf

Reproduction:

Compare GT_n in Theorem 3.1 against the MGT_n
construction preceding Theorem 3.2.

Inspect Theorems 3.7 and 3.8.

Limit:

The result demonstrates limitations of size-width
tradeoffs, not limitations of every possible lower-bound
method.

---

### ACE-R11-04 — T4: Resolution width and pebble games

Severity: HIGH
Claim level: Proved
Disposition: FAIL

The table incorrectly states an equality:

    W = k iff Spoiler wins with k+1 pebbles.

The source provides a threshold characterization.

Correct statement:

For k at least the initial clause width, F has a
resolution refutation of width at most k if and only if
Spoiler wins the Boolean existential (k+1)-pebble game.

The Duplicator's strategy family for that game contains
partial assignments on at most k+1 variables.

The extension condition applies when fewer than k+1
variables have been assigned.

The existing detailed record incorrectly uses a
family bounded by k variables.

Counterexample to the equality:

    F = (x) AND (NOT x).

Its minimum refutation width is exactly one.

Spoiler wins by querying x.

Spoiler also wins with any larger pebble allowance.

Therefore winning with three pebbles does not imply
minimum width two.

Primary source:

Atserias and Dalmau,
A Combinatorial Characterization of Resolution Width.

ECCC TR02-035, Definition 2, Lemmas 1–2, Theorem 1.

https://eccc.weizmann.ac.il/report/2002/035/download/

Reproduction:

Read the definition of the strategy family and its
extension condition.

Run:

    python -m pytest -q lab/tests/test_ace_literature_counterexamples.py

The relevant regression is:

    test_t4_width_is_threshold_not_equality

Limit:

The game characterizes width, not minimum proof length.

---

### ACE-R11-05 — T5: Treewidth-parameterized SAT and #SAT

Severity: MEDIUM
Claim level: Proved — established literature
Disposition: FAIL

The O*(2^k) primal and O*(4^k) incidence upper bounds
are supported by the cited algorithms.

However, the detailed runtime formulas omit factors
from the source and conflate arithmetic-operation counts
with bit complexity.

Correct replacement:

Given a nice tree decomposition of width k containing
N decomposition nodes:

Primal graph:

    O(2^k * (k*d + delta) * N)

where d is maximum variable occurrence count.

Incidence graph:

    O(2^k * (k*l + 2^k*(k+delta)) * N)

where l is maximum clause length.

Here delta denotes the cost of multiplying integers
of the relevant counting bit-length, as defined by
the source.

For polynomial-size supplied decompositions and ordinary
polynomial-time integer arithmetic, these give the stated
O*(2^k) and O*(4^k) bounds.

SAT follows by testing whether the exact model count
is positive.

Primary source:

Samer and Szeider,
Algorithms for Propositional Model Counting.

Section 3, Theorems 1 and 3.

https://www.ac.tuwien.ac.at/files/pub/SamerSzeider10.pdf

Reproduction:

Compare the runtime table in the introduction against
the explicit bit-complexity analysis in Section 3.

Do not claim the supplied-decomposition algorithm
includes the cost of obtaining an optimal decomposition.

Separate decomposition construction and approximation
results require their own verified statements.

Limit:

These are algorithmic upper bounds, not evidence that
high treewidth makes every instance hard.

They are also not a claim that the cited algorithms
remain the fastest known algorithms today.

---

### ACE-R11-06 — T6: Cached DPLL and branchwidth

Severity: LOW
Claim level: Proved — established literature
Disposition: PASS, with model qualification

Accepted:

For the branchwidth parameter used by Bacchus,
Dalmao and Pitassi, there exists an execution of
#DPLL-Cache with runtime

    n^O(1) * 2^O(b).

The source also describes how to make the algorithm
deterministic while retaining the bound.

The relevant parameter is the source's decomposition
width, not arbitrary primal-graph min-fill width.

The polynomial input-processing factor must account for
the represented formula length.

The space bound follows from the stated execution
model and polynomially encoded cached entries; do not
replace it with a linear-space guarantee.

Primary source:

Bacchus, Dalmao and Pitassi,
Solving #SAT and Bayesian Inference with Backtracking
Search.

Theorem 2 and Section 2.5.

https://aiinternational.org/Papers/JAIR/Vol34/JAIR-3412.pdf

https://arxiv.org/abs/1401.3458

Reproduction:

Compare Theorem 2, concerning #DPLL-Cache, with
Theorem 3, concerning the distinct #DPLL-Space model.

Limit:

The claim concerns suitable executions of the
specified cached algorithm, not every branching
heuristic and not our uncached DPLL baseline.

---

### ACE-R11-07 — T7: SETH-conditional treewidth tightness

Severity: MEDIUM
Claim level: Proved — conditional on Conjecture
Disposition: FAIL

The conditional implication is valid, but the source
document mixes deterministic and randomized models
without pinning the corresponding SETH formulation.

Correct statement:

Assume deterministic SETH.

For every fixed epsilon in (0,1), there is no
deterministic algorithm deciding arbitrary CNF SAT
in time

    (2-epsilon)^tw(G_P(F)) * poly(|F|).

For an algorithm accepting a supplied tree
decomposition of width k, the corresponding lower
bound applies to a claimed guarantee in that supplied
width.

Proof:

A CNF on n variables has a primal graph of treewidth
at most n-1.

The single bag containing every variable provides a
decomposition of width n-1.

The hypothesized algorithm would therefore yield a
(2-epsilon)^n times polynomial-input-length algorithm
for every fixed-clause-width SAT problem.

This contradicts the stated form of SETH.

For randomized algorithms, state an appropriate
randomized SETH hypothesis and error convention
separately.

Ordinary deterministic SETH must not silently be
used as a randomized lower-bound assumption.

Primary source for the hypothesis:

Impagliazzo and Paturi,
On the Complexity of k-SAT.

https://cseweb.ucsd.edu/~paturi/myPapers/pubs/ImpagliazzoPaturi_2001_jcss.pdf

Reproduction:

Apply the one-bag decomposition argument above.

Limit:

The lower bound concerns arbitrary CNF SAT.

It does not establish a comparable lower bound for
the graph-parity problem presented as Tseitin equations.

---

### ACE-R11-08 — T8: Tseitin grid lower bounds

Severity: MEDIUM
Claim level: Proved — established mathematical result
Disposition: FAIL

The regular-resolution lower bound on grid Tseitin
contradictions is valid.

However, the surrounding text incorrectly suggests
that the analogous unrestricted-resolution result
remains open.

A verified replacement derivation is available from
the 2011 Alekhnovich–Razborov bounded-cyclicity result.

For the k by k square grid, k >= 2:

- Every edge belongs to a unit-square cycle.
- Every edge belongs to at most two such cycles.
- The cycle lengths are four.

Thus the graph's cyclicity, as defined in their paper,
is bounded by four.

Their Theorem 2.15 implies:

    W <= O(log(S))

for this family.

The BSW expansion theorem implies:

    W = Omega(k).

For completeness, consider any balanced vertex set
U in the grid.

If at least k/3 rows contain both U and its complement,
each such row contributes a horizontal cut edge.

Otherwise, balance forces an entirely-U row and an
entirely-complement row.

In that case every column contains a vertical cut
edge.

Hence every balanced cut has at least k/3 edges,
up to integer rounding.

Combining these facts gives:

    S >= 2^Omega(k).

Regular resolution is a restriction of unrestricted
resolution, so:

    SR >= S >= 2^Omega(k).

Primary sources:

Alekhnovich and Razborov,
Theorem 2.15, with Definition 2.14.

https://people.cs.uchicago.edu/~razborov/files/automat_pos.pdf

Ben-Sasson and Wigderson,
Theorem 4.4.

https://people.inf.ethz.ch/emo/SatSem05/Papers/BensassonWidgerson01.pdf

Reproduction:

Verify the unit-square cycle cover.

Apply the explicit balanced-cut argument.

Combine the two cited theorems.

The original 1968 attribution was not independently
checked against its exact historical theorem statement
in this review.

Retain that attribution only after confirming it.

Limit:

The lower bound is a proof-size lower bound for
resolution refutations, not a lower bound on parity-aware
algorithms deciding the grid Tseitin problem.

---

### ACE-R11-09 — T9: Expander Tseitin lower bounds

Severity: INFO
Claim level: Proved — established literature
Disposition: PASS

Accepted:

For connected constant-degree graph families with
linear balanced edge expansion, the standard odd-charge
Tseitin contradictions require exponentially many
unrestricted resolution proof lines in the number
of graph vertices.

This follows from the BSW width lower bound together
with their general size-width relation.

The standard explicit CNF has O(|V|) clauses and
O(|V|) literal occurrences when degree is fixed.
Encoded bits may additionally account for identifiers.

Primary verification:

Ben-Sasson and Wigderson,
Theorem 4.4 and Corollary 4.5, attributed there to
Urquhart's 1987 result.

https://people.inf.ethz.ch/emo/SatSem05/Papers/BensassonWidgerson01.pdf

Historical paper:

Urquhart, Hard Examples for Resolution.

https://doi.org/10.1145/7531.8928

Reproduction:

Substitute linear expansion, constant initial width
and O(|V|) Boolean variables into T2.

Limit:

Do not infer that every sampled regular graph has the
required expansion.

The mathematical assumption must be established for
the relevant family.

---

### ACE-R11-10 — T10: Expansion-based proof-size bound

Severity: HIGH
Claim level: Proved
Disposition: FAIL

The width theorem is valid:

    W >= e(G).

The claimed size bound is not valid for arbitrary
maximum degree as presently written:

    S >= exp(Omega((e(G)-Delta)^2 / |E|)).

The error is squaring a potentially negative lower
bound on the width gap.

Correct replacement:

    S >= exp(Omega(
        max(0, e(G)-Delta)^2 / |E|
    )).

Alternatively, explicitly assume e(G) >= Delta
before using the squared difference.

Counterexample family:

Take the star graph K_(1,m).

Set the center charge to one and every leaf charge
to zero.

Then:

    Delta = m.
    |E| = m.
    e(G) = ceil((m+1)/3).

For each leaf edge x_i, the leaf equation contributes
the unit clause NOT x_i.

The center's odd parity encoding contains:

    x_1 OR ... OR x_m.

Successively resolving this clause with the m
negative unit clauses derives the empty clause.

The refutation uses at most 2m+1 proof lines,
counting the used initial clauses.

But the incorrectly squared expression gives:

    (e(G)-Delta)^2 / |E| = Theta(m).

It would therefore imply exponentially large minimum
refutations for a family with linear-line refutations.

Contradiction.

The explicit center CNF has exponentially many
input clauses when m grows.

That does not invalidate the counterexample:
the reviewed bound concerns proof length measured
using the clauses actually appearing in the refutation.

If a different proof-size convention counts every
input clause whether used or not, state that convention
and do not silently transfer the BSW formula.

Additional correction:

The statement that every planar graph has
e(G)=O(sqrt(|E|)) is false without a suitable
degree restriction.

The same star family is planar and has linear
balanced edge expansion.

Primary source:

Ben-Sasson and Wigderson,
Theorem 4.4 and Theorem 3.5.

https://people.inf.ethz.ch/emo/SatSem05/Papers/BensassonWidgerson01.pdf

Reproduction:

Run:

    test_t10_star_short_resolution

in the accompanying regression test file.

The finite test witnesses the construction.
The parameterized mathematical argument supplies
the asymptotic counterexample.

---

### ACE-R11-11 — T11: Branchwidth, treewidth and resolution

Severity: HIGH
Claim level: Proved
Disposition: FAIL

The existing row mixes three distinct width notions:

1. Branchwidth of the underlying ordinary graph.
2. Branchwidth of a CNF hypergraph.
3. Treewidth of the CNF primal graph.

These cannot be interchanged without a proved
comparison and stated graph assumptions.

Verified replacement:

For a CNF F, define its hypergraph with variables
as vertices and clause-variable sets as hyperedges.

Alekhnovich and Razborov, Theorem 2.3, construct a
deterministic algorithm with runtime polynomial in

    |F| + 2^bw(F).

It produces a satisfying assignment or, for UNSAT
inputs, a regular resolution refutation.

Their Theorem 2.12 establishes:

    bw(T(G,c)) = Theta(W(T(G,c)))

under the paper's Tseitin assumptions.

Theorem 2.13 establishes width-automatability for
Tseitin contradictions.

Retain these precise source statements.

For a simple graph of maximum degree Delta:

    tw(L(G)) <= Delta*(tw(G)+1)-1.

Proof:

Take a tree decomposition of G.

Replace each bag by the union of edges incident to
its vertices.

An original bag of size at most tw(G)+1 produces
a bag of at most Delta*(tw(G)+1) edge identifiers.

Every pair of adjacent line-graph vertices shares
an original endpoint and therefore appears together
in a replacement bag.

For each original edge, the bag subtrees of its
two endpoints intersect.

Their union is connected.

The replacement bags therefore form a line-graph
tree decomposition.

Combining the known width-parameterized constructions
with this comparison gives a conservative
degree-dependent upper bound of the form

    poly(|F|) * 2^O(Delta*(tw(G)+1))

for suitable regular resolution proof construction.

For bounded degree this becomes:

    poly(|F|) * 2^O(tw(G)).

Do not assert the sharper dependence

    2^O(tw(G)+Delta)

without a separate supporting theorem.

The lower bound for tree-like resolution follows
from an independently justified width lower bound
and T1, accounting for the initial width Delta.

The statement excluding unrestricted grid lower
bounds is incorrect; see ACE-R11-08.

Primary source:

Alekhnovich and Razborov,
Satisfiability, Branch-Width and Tseitin Tautologies.

Theorems 2.3, 2.12, 2.13, 2.15.

https://people.cs.uchicago.edu/~razborov/files/automat_pos.pdf

Reproduction:

Check the hypergraph definition preceding Remark 2.2.

Check each theorem's distinct parameter.

Validate the bag replacement argument above.

Limit:

No theorem here equates an experimental min-fill
estimate with optimal proof size.

---

### ACE-R11-12 — T12: Exact resolution-width characterization

Severity: HIGH
Claim level: Proved
Disposition: FAIL

The current additive upper bound is false:

    W(T(G,c)) <= tw(G)+Delta.

Correct replacement:

For a finite connected simple graph G with an
odd charge marking c:

    W(T(G,c)) = max(Delta(G), tw(L(G))).

Here L(G) denotes the line graph of G.

Use the source's refutation-width convention and
ordinary treewidth measured as maximum bag size
minus one.

Primary source:

Galesi, Talebanfard and Toran,
Cops-Robber Games and the Resolution of Tseitin
Formulas.

ECCC TR18-170.

https://eccc.weizmann.ac.il/report/2018/170/

https://eccc.weizmann.ac.il/report/2018/170/download/

Corollary 8, printed page 12:

    W(T(G,c)) = max(Delta(G), ec(G)-1).

Corollary 16, printed page 15:

    ec(G) = tw(L(G))+1.

Combining them proves the corrected statement.

Both corollaries were checked against the original
PDF, including rendered page inspection.

Counterexample to the existing additive upper bound:

Take G=K8, the complete graph on eight vertices.

Then:

    tw(G)=7.
    Delta(G)=7.

The claimed upper bound would be 14.

Every balanced vertex cut has one side of size
3, 4 or 5.

The number of crossing edges is:

    3*5 = 15
    4*4 = 16
    5*3 = 15.

Therefore:

    e(K8)=15.

By BSW Theorem 4.4:

    W(T(K8,c)) >= 15.

This contradicts the claimed upper bound of 14.

The argument does not require computing exact
treewidth of the line graph.

Reproduction:

Run:

    test_t12_complete_graph_bound_counterexample

in the accompanying test file.

The finite cut enumeration supports the explicit
mathematical counterexample.

Project relevance:

For simple cubic Tseitin graphs, the primal graph of
the standard CNF is L(G).

Therefore:

    W(T(G,c)) = max(3, tw(primal(T(G,c)))).

The deterministic min-fill elimination width gives
an upper bound on this exact treewidth.

It is not an exact measurement of resolution width
unless independently shown to be optimal.

Limit:

The theorem characterizes minimum resolution width,
not DPLL decisions, elapsed time or arbitrary
SAT-solving complexity.

---

### ACE-R11-13 — T13: Tree-like versus regular resolution

Severity: MEDIUM
Claim level: Proved
Disposition: FAIL

The strict polynomial-simulation separation is valid.

However, the row combines a linear general-resolution
upper bound from a pebbling construction with a
linear regular-resolution upper bound that was not
established by the checked theorem statement.

Source-supported replacement:

Bonet and Galesi's modified ordering formulas MGT_n
have polynomial-size regular resolution refutations
and tree-like resolution lower bounds 2^Omega(n).

Primary source:

Bonet and Galesi.

Theorems 3.2, 4.1 and 4.2.

https://www.cs.upc.edu/~bonet/revistas/computational_complexity.pdf

Separately:

Ben-Sasson, Impagliazzo and Wigderson,
Near Optimal Separation of Tree-like and General
Resolution, Theorem 1, establish a family with
linear-size general resolution refutations and
tree-like lower bounds

    exp(Omega(n/log n)).

https://www.math.ias.edu/~avi/PUBLICATIONS/MYPAPERS/BIW03/biw03.pdf

Do not transfer the latter theorem's exact size and
exponent combination to regular resolution without
checking regularity of the construction.

Reproduction:

Compare the proof systems named in the two sources'
theorem statements.

Limit:

The separation is between proof systems.

It is not automatically a separation on unmodified
Tseitin formulas.

---

### ACE-R11-14 — T14: Regular versus unrestricted resolution

Severity: MEDIUM
Claim level: Proved
Disposition: FAIL

The exponential separation is valid.

The existing document mixes size parameters from
different constructions and historical improvements.

Verified replacement:

Alekhnovich, Johannsen, Pitassi and Urquhart construct
modified ordering formulas GT'_(n,rho).

For every appropriate rho, general resolution has
refutations of size O(n^3).

For sufficiently large n, there exists rho such that
every regular resolution refutation has more than

    2^(n/200)

proof lines.

Here n is the number of underlying ordering elements,
not the number of clauses or encoded input bits.

The construction has Theta(n^2) Boolean variables
and O(n^3) clauses.

Primary source:

An Exponential Separation between Regular and
General Resolution.

Definition 3.3.
Corollary 3.4.
Theorem 3.10.

https://theoryofcomputing.org/articles/v003a005/

https://theoryofcomputing.org/articles/v003a005/v003a005.pdf

Reproduction:

Inspect the definition and the two bound statements.

Do not assume that their n means the same quantity
as n in the other cited separation constructions.

The historical Goerdt and Urquhart numerical bounds
were not checked in full detail in this review.

Remove those precise numerical claims from the
approved row unless Gemini supplies source locators
and consistent input parameters.

Limit:

This is an unrestricted-versus-regular separation
on specially constructed formulas.

It does not establish the same gap for standard
Tseitin contradictions.

---

### ACE-R11-15 — T15: CDCL, DRUP and general resolution

Severity: HIGH
Claim level: Proved
Disposition: FAIL

The proof-system equivalence requires explicit
operational assumptions.

Correct replacement, part A:

Pipatsrisawat and Darwiche establish that their CLR
model with an asserting learning scheme polynomially
simulates general resolution.

The simulation uses suitable extended branching
sequences and restart behavior.

Their theorem does not guarantee that every
deterministic CDCL heuristic efficiently finds a
short proof whenever one exists.

Primary source:

On the Power of Clause-Learning SAT Solvers as
Resolution Engines.

Theorems 1 and 2, Corollary 1.

https://www.cs.sfu.ca/~mitchell/cmpt-827/2011-Fall/Project-Readings/CDCL-Restarts-and-Resolution.pdf

Correct replacement, part B:

An ordinary RUP addition can be converted into a
resolution derivation with polynomial overhead by
recording the applicable unit-propagation reasons.

Clause deletion does not introduce new logical
consequences.

For a valid DRUP refutation, the additions can
therefore be translated into a resolution refutation.

Conversely, each ordinary resolution inference
can be expressed as a RUP addition.

Primary source for the RUP conversion:

Kiesl, Rebola-Pardo and Heule,
Extended Resolution Simulates DRAT.

Theorem 2 and Section 4.4.

https://benjaminkiesl.github.io/publications/extended_resolution_simulates_drat_kiesl_rebola-pardo_heule.pdf

Critical correction:

Observed wall-clock time and conflict count are not
automatically upper bounds on minimum resolution
proof size.

A concrete, successfully checked resolution proof
provides an upper bound under its actual size measure.

A checked DRUP proof can provide such a bound after
accounting for the translation.

A DRAT proof containing stronger RAT steps cannot
be treated automatically as a pure resolution proof.

Reproduction:

Inspect the assumptions of the CLR simulation.

Inspect the unit-propagation conversion theorem.

Review what is actually recorded by the experimental
solver.

Limit:

Existence of an efficient simulation is distinct
from an efficient algorithm for discovering it.

---

### ACE-R11-16 — T16: DRAT and extended resolution

Severity: INFO
Claim level: Proved — established literature
Disposition: PASS, with proof-model assumptions

Accepted:

DRAT and extended resolution polynomially simulate
one another under their standard proof-system
definitions, including permitted extension variables.

Primary source:

Kiesl, Rebola-Pardo and Heule,
Extended Resolution Simulates DRAT.

Section 4, especially Section 4.5.

https://benjaminkiesl.github.io/publications/extended_resolution_simulates_drat_kiesl_rebola-pardo_heule.pdf

The nontrivial DRAT-to-ER simulation is explicitly
constructed and analyzed in that source.

For the opposite direction, consider a fresh
extension variable y representing a conjunction
a AND b.

Introduce:

    NOT y OR a
    NOT y OR b
    y OR NOT a OR NOT b.

The first two additions are RAT on NOT y because
y is fresh and there are initially no opposite-pivot
clauses.

The third is RAT on y: its resolvents with the first
two clauses are tautological.

Ordinary resolution inferences can be expressed as
RUP additions.

This supplies the elementary ER-to-DRAT direction.

Reproduction:

Inspect the ER extension rule and the RAT condition.

Check the three-clause extension derivation.

Inspect the source's DRAT-to-ER complexity analysis.

Limit:

An accepted DRAT certificate is not evidence of
membership in ordinary resolution.

This theorem does not establish correctness of the
repository's particular Python proof checker.

---

### ACE-R11-17 — T17: Algebraic solving and graph connectivity

Severity: MEDIUM
Claim level: Proved
Disposition: FAIL

The component-parity result is correct.

The row must distinguish three input models:

A. An explicit arbitrary binary linear system.

B. An explicit graph with vertex charges.

C. An ordinary CNF with no supplied parity metadata.

For A:

Ordinary Gaussian elimination decides consistency
in polynomial time.

For an inconsistent system A*x=f, elimination can
produce a row-combination certificate y satisfying:

    y^T A = 0
    y^T f = 1.

A straightforward implementation that tracks row
operations has polynomial bit cost.

Do not retain an exact rectangular-matrix complexity
formula for certificate production unless the
certificate bookkeeping cost is included.

For B:

A finite undirected graph's parity equations are
consistent exactly when every connected component
has even total charge.

Necessity:

Sum the equations within a component.

Sufficiency:

Assign zero to non-tree edges and solve the remaining
tree constraints from the leaves toward a root.

The root equation follows from even component charge.

With an adjacency-list graph representation,
a component traversal establishes consistency in

    O(|V|+|E|)

ordinary graph traversal operations.

For deterministic logspace, use Reingold's undirected
connectivity algorithm to enumerate vertices belonging
to each component and accumulate their charge parity.

Primary source for the connectivity result:

Reingold, Undirected Connectivity in Log-Space.

https://eccc.weizmann.ac.il/eccc-reports/2004/TR04-094/index.html

https://doi.org/10.1145/1391289.1391291

For C:

Parity constraints must first be identified and
certified against the input clauses.

The cost and completeness of this extraction
are separate algorithmic obligations.

Do not give a graph-aware algorithm privileged
metadata and present its runtime as the end-to-end
runtime on arbitrary CNF.

Also remove the unqualified use of the complexity
class XOR-L from the general runtime row unless a
specific decision-language result is cited.

Reproduction:

Apply the component parity argument and construct
a spanning-tree witness.

Compare this task against the input format available
to the solver.

Limit:

No general SAT algorithm follows from efficient
solving of linear parity constraints.

---

### ACE-R11-18 — T18: Polynomial calculus and field dependence

Severity: HIGH
Claim level: Proved
Disposition: FAIL

The row conflates different polynomial encodings.

#### Case 1: Parity equations supplied directly

Over F2, use the linear equations:

    sum of incident x_e = charge(v).

For an odd-charge component, summing the equations
derives 0=1.

This gives a degree-one derivation using only
the linear axioms.

The number of addition steps is O(|V|).

However, the sum of the sizes of all intermediate
polynomials may be larger than O(|V|+|E|).

A straightforward bound is O(|V|*|E|) monomial
occurrences for a sequential summation proof.

A linear encoded-size bound requires additional
justification.

#### Case 2: Standard expanded CNF encoded as polynomials

For the ordinary polynomial calculus translation,
a clause becomes the product of its falsity
indicators, set equal to zero.

For a cubic XOR encoding, the four initial clause
polynomials have degree three.

The sum of those four polynomials over F2 equals
the linear parity polynomial.

Thus the parity equation can be recovered by
constant-size local addition derivations.

But the degree of the resulting proof includes the
degree-three initial polynomials that were used.

Therefore the claim of a degree-one refutation does
not apply to the standard expanded cubic CNF encoding.

A degree-at-most-three polynomial calculus refutation
can instead be constructed by extracting the linear
equations and then adding them.

This supplies a correct bounded-degree upper bound
for the team's cubic input representation.

#### Case 3: Odd-characteristic lower bounds

The checked primary result of Buss, Grigoriev,
Impagliazzo and Pitassi uses a signed-variable
polynomial formulation TS_n(2).

Its axioms include equations of the form:

    y_e^2 - 1 = 0

and products of incident signed edge variables.

Theorem 10 establishes a linear degree lower bound
on appropriate expanding graph families.

The meaningful inconsistent-system interpretation
uses characteristic different from two.

Crucially, the same signed-variable formulation
degenerates in characteristic two because 1=-1.

The characteristic-two linear parity formulation
and the characteristic-not-two signed formulation
are not literally the same polynomial input.

Primary source:

Linear Gaps Between Degrees for the Polynomial
Calculus Modulo Distinct Primes.

Section 2 and Theorem 10.

https://mathweb.ucsd.edu/~sbuss/ResearchWeb/lineargaps/journalfinal.pdf

A lower bound transferred to a particular Boolean
CNF polynomial encoding requires a justified
encoding translation with its degree overhead.

A degree-to-size lower-bound inference likewise
requires an applicable size-degree theorem and
its initial-degree assumptions.

Do not claim the exact transferred size lower bound
without those supporting steps.

Reproduction:

Run:

    test_t18_clause_polynomial_sum_is_linear_over_f2

The test confirms the local cubic polynomial identity
for both right-hand sides.

The degree claim follows from the explicit form of
the clause polynomials and the constructed derivation,
not from finite testing alone.

---

### ACE-R11-19 — T19: Res(XOR), ER, DRAT and Frege

Severity: HIGH
Claim level: Proved, with unresolved source obligations
Disposition: FAIL

The core algebraic intuition is valid.

The exact tree-like Res(XOR) size statement is not
approved in its current form.

The row conflates:

- Number of algebraic addition steps.
- Number of proof lines.
- Total symbols in linear equations.
- Tree-like versus DAG-like proof structure.
- Parity equations supplied as axioms.
- Ordinary clauses supplied as axioms.

For an odd-charge graph presented directly as
linear equations:

Adding the vertex equations in an odd component
gives a contradiction using O(|V|) addition steps.

This is a direct algebraic derivation.

For ordinary bounded-degree Tseitin CNF, local parity
constraints must first be derived in the stated proof
system.

A valid transfer to Res(XOR), Extended Resolution
or Frege must identify the derivation rules and
account for that local conversion.

In particular, sequentially accumulated XOR equations
can contain many variables.

The O(|V|) line count alone does not prove a linear
total-symbol-size bound.

Primary source consulted:

Itsykson and Sokolov,
Resolution over Linear Equations Modulo Two.

https://doi.org/10.1016/j.apal.2019.102722

The publisher abstract and available source excerpts
were checked, but a complete exact proof-size
theorem locator for the current linear tree-like
claim was not established.

Therefore:

- Remove the exact linear Res(XOR) proof-size claim
  until its size convention and derivation are supplied.
- Retain the direct linear-equation summation result
  with its explicitly stated cost measure.
- Require a source-supported polynomial-size
  construction for each additional proof system.
- Do not use the Cook–Reckhow general proof-system
  paper alone as proof of the specific Tseitin
  Frege-size assertion.

Delete the description of Tseitin contradictions as
"exclusively" benchmarks for systems lacking parity
reasoning.

That is not a mathematical consequence of the
reviewed upper bounds.

Reproduction:

Inspect the precise proof rules in the selected
Res(XOR) system.

Construct or cite the local CNF-to-equation derivation.

Count both proof lines and total encoded symbols.

Limit:

A polynomial-size proof for a restricted family
does not establish polynomial boundedness of
that proof system on all contradictions.

---

## 4. Cross-cutting findings

### ACE-R11-20 — Graph definitions and width conventions

Severity: MEDIUM
Claim level: Proved
Disposition: FAIL

Several graph-definition issues require correction.

A. Ordinary graph versus hypergraph branchwidth

The familiar Robertson–Seymour comparison between
ordinary graph branchwidth and treewidth must not
be copied directly to arbitrary clause hypergraphs.

Counterexample:

A hypergraph containing one hyperedge on n vertices
can have branchwidth zero under a single-hyperedge
convention.

Its primal graph is K_n, with treewidth n-1.

Thus a direct unqualified comparison is false.

Use the hypergraph conventions of each cited source.

B. Zero-degree vertices

The clause count 2^(d-1) applies when d>=1.

When d=0:

- Charge zero contributes no clauses.
- Charge one contributes the empty clause.

Do not evaluate 2^(-1) as a clause count.

C. Primal graph and line graph

For the ordinary simple-graph Tseitin encoding,
the primal graph has edge variables as vertices
and connects variables sharing an endpoint.

This yields the line graph.

A minimum-degree-two assumption is not necessary
for ordinary non-isolated edge variables.

D. Incidence treewidth

The inequality

    tw(incidence(F)) <= tw(primal(F))+1

can be justified directly.

Each clause's variable set is a clique in the
primal graph, so some decomposition bag contains
all of its variables.

Attach a leaf bag containing those variables and
the clause vertex.

Handle empty clauses as isolated clause vertices.

The resulting bag sizes establish the bound,
with consistent empty-graph conventions.

E. Balanced edge expansion

Specify integer rounding and ensure the set of
admissible balanced cuts is nonempty.

Handle trivial graphs separately.

Reproduction:

Construct the single-hyperedge example.

Check both isolated-vertex charge values.

Review the explicit tree-decomposition construction.

---

### ACE-R11-21 — Subsumption audit overclaims

Severity: HIGH
Claim level: Proved / Empirical Observation
Disposition: FAIL

Section 4 repeatedly labels empirical solver behavior
as "100% subsumed" by mathematical proof-complexity
results.

That conclusion does not follow.

Replace the subsumption table using the following
distinctions.

1. Componentwise parity characterization:

   Known mathematical theorem.

   The existing Lean implementation establishes
   global odd-charge unsatisfiability under its
   stated encoding assumptions.

   It does not automatically formalize the full
   componentwise if-and-only-if result.

2. Treewidth versus minimum resolution width:

   Known theoretical characterization for the
   specified Tseitin family.

   The predictive performance of a heuristic
   width estimate is a separate empirical question.

3. Low-width versus high-width CDCL behavior:

   Not a theorem-level subsumption.

   Actual solver performance depends on learning,
   branching, restarts, preprocessing and encoding.

4. Primal treewidth versus underlying treewidth
   as solver-effort predictors:

   Empirical hypothesis.

   Graph-theoretic inequalities do not establish
   which feature predicts solver effort better.

5. XOR or Gaussian preprocessing acceleration:

   Efficient parity solving is established.

   End-to-end extraction and measured acceleration
   remain empirical properties of an implementation.

6. Comparing practical proof size with theoretical
   upper bounds:

   Valid empirical benchmarking, provided actual
   proof formats and size measures are distinguished.

7. Unrestricted resolution on grids:

   The existing open-status assertion is incorrect.

   See ACE-R11-08.

Reproduction:

For each original subsumption-table row, attempt to
derive its solver-performance conclusion from the
cited theorem without introducing assumptions about
the actual solver.

The missing assumptions are precisely the distinction
that our empirical experiment is designed to test.

Remove the blanket claim that Tseitin-resolution
research cannot contribute directly to broader
complexity research.

A narrower statement is justified:

No result currently established by Operation
Millennium on Tseitin formulas resolves P vs NP.

---

### ACE-R11-22 — Newly reported November 2026 results

Severity: HIGH
Claim level:
  Empirical Observation for verified publication
  and theorem-statement inspection.
  Conjecture / technical review pending for any
  attempted project adoption as an independently
  accepted new mathematical result.
Disposition: OPEN

New primary preprint:

Dmitry Itsykson and Petr Smirnov,
Resolution Is Automatable on Tseitin Formulas.

ECCC TR26-332.

Publication record: November 22, 2026.

https://eccc.weizmann.ac.il/report/2026/332/

https://eccc.weizmann.ac.il/report/2026/332/download/

The original PDF and its theorem summary were inspected.

The authors report the following results.

Theorem 1.1 / Corollary 5.4:

For connected G with odd charge,

    S(T(G,c)) >= 2^Omega(tw(G)).

Theorem 1.2 / Theorem 6.1:

For connected G with odd charge,

    S(T(G,c)) + |T(G,c)|
        >= 2^Omega(tw(L(G))).

Corollary 1.3 / Corollary 8.1:

For 2-edge-connected graphs with odd charge,

    S(T(G,c)) >= 2^Omega(tw(L(G))).

Theorem 1.4 / Theorem 7.1:

The authors report automatability of unrestricted
and regular resolution on Tseitin contradictions,
with regular refutations constructible in time
polynomial in the input length and shortest
unrestricted refutation length.

Theorem 1.5 / Theorem 8.2:

The authors report an absolute constant C such that

    S(F) <= S_reg(F) <= S(F)^C

for every Tseitin contradiction F.

Important:

The publication and its theorem statements have
been verified.

A complete independent proof audit was not performed.

Do not misrepresent the results as a new conjecture
of the paper's authors: they claim theorems with proofs.

The project's acceptance of these newly reported
theorems remains OPEN.

Under RULES.md, their technical adoption is pending
review rather than automatically Proved or
Lean-Verified by our team.

Recommended assignment:

Gemini should prepare a separate literature note
covering the preprint's main proof mechanisms.

Ace should independently audit its definitions,
restriction argument, graph assumptions and
polynomial equivalence proof.

Do not treat this new work as a team discovery.

Do not infer automatability of general resolution
on arbitrary CNF from automatability on the
restricted Tseitin family.

This literature update does not authorize a change
to OM-C001-R2.

Reproduction:

Read the ECCC publication record.

Inspect Section 1.2, printed page 4.

For technical adoption, independently inspect
Sections 5–8 and the stated dependencies.

---

### ACE-R11-23 — Citation marker and locator audit

Severity: LOW
Claim level: Empirical Observation
Disposition: OPEN

The reviewed literature document retains several
[VERIFY] markers attached to mathematical and
bibliographic assertions.

A marker cannot be removed solely because a DOI
resolves.

For each retained statement:

- Identify the exact theorem locator.
- Pin the source version.
- Record the relevant mathematical assumptions.
- Verify the stated parameter convention.
- Remove unsupported historical numerical details.
- Keep unresolved source checks visible.

Some older source texts or exact historical bounds
were not inspected in full during this review.

Specific unresolved items are identified in the
individual findings.

The replacement statements above rely on separately
checked sources or supplied elementary derivations.

---

## 5. Executed adversarial tests

File:

lab/tests/test_ace_literature_counterexamples.py

Executed command, in an isolated local sandbox:

    python -m pytest -q \
        /mnt/data/ace_review/test_ace_literature_counterexamples.py

Observed output:

    .... [100%]
    4 passed in 0.06s

[Claim Level: Empirical Observation]

Executed tests:

1. Complete-graph balanced-cut counterexample to T12.
2. Explicit short star-graph resolution refutation
   counterexample to the unqualified T10 bound.
3. Unit contradiction demonstrating T4's equality error.
4. Cubic parity polynomial identity over F2.

The tests are standard-library mathematical fixtures
run through pytest.

They do not import or execute the project SAT solvers.

They do not establish asymptotic theorems by sampling.

The corresponding parameterized derivations appear
in the relevant findings.

The complete repository test suite was not executed.

No confirmatory seeds or outcomes were accessed.

---

## 6. Rulings on Nova's plan-author objections

The following amendments are proposed by Ace as
author of ADVERSARIAL_REVIEW_01.md.

They are based on Nova's independent PR #10 review,
read at dev 0f55084.

They are made before confirmatory test outcomes
have been seen by Ace and subject to coordinator
confirmation that the test split remains unopened.

No change is authorized to:

- Confirmatory population.
- Primary width feature.
- Branch budget.
- Primary response.
- Primary prediction models.
- Bootstrap configuration.
- Practical effect threshold.

These are integrity and operational amendments.

### ACE-PLAN-01 — B4 freeze requirements

Severity: HIGH
Claim level: Empirical Observation — Nova-reported
Disposition: OPEN pending implementation

Ruling: Nova is correct.

B4 cannot be satisfied by the current authorization
guard alone.

Do not narrow the evidence requirements simply to
match the weaker implementation.

However, requiring every provenance check to reside
inside one existing runner function is unnecessary.

Introduce a two-stage freeze architecture.

Stage A: execution freeze.

From a clean reviewed checkout, create an immutable
manifest containing:

- Exact execution-code commit.
- Relevant tracked-source hashes.
- Generator and solver hashes.
- Analysis and feature hashes.
- Protocol and amendment hashes.
- Seed-manifest hash.
- Exact interpreter and dependency versions.
- Certificate checker identities and hashes.
- Frozen execution settings.
- Canonical training-record hash.
- Frozen fitted-model hash.

Stage B: authorization record.

Store separately:

- Hash of Stage A manifest.
- Coordinator approval.
- Approval timestamp.
- Explicit FROZEN status.
- Confirmation of test-split non-exposure.

This avoids self-referential Git commit hashing.

The execution-code commit must not depend on the
hash of a manifest that contains that same commit's
hash.

The authorization record may be committed later
without modifying the frozen code.

A single documented production entrypoint must
verify both records before test execution.

It may call a separate strict verifier instead
of duplicating all checks in the original runner.

No test-split execution should proceed if any
required provenance check fails.

Procedural protections are sufficient for this
cooperative research project.

Do not claim the mechanism prevents arbitrary direct
Python invocation by a malicious repository operator.

Required regression:

Every required field is individually tampered with
and the production entrypoint refuses authorization.

Missing required fields must also be refused.

Owner: Claude.
Independent approval: Nova and Lumi.

---

### ACE-PLAN-02 — Gate E population completeness

Severity: HIGH
Claim level: Empirical Observation — Nova-reported
Disposition: OPEN pending implementation

Ruling: Nova is correct.

A dry run displaying a count does not enforce that
count.

Additionally, a count of 840 alone does not establish
that the correct 840 instances were selected.

Amend Gate E:

The authorized first confirmatory test execution must
schedule exactly the canonical manifest's 840 test
instance identifiers.

Require:

    actual_instance_ids == expected_instance_ids

using canonical ordering, or set equality plus a
separate uniqueness and canonical-order check.

Verify:

- All 28 cells.
- Exactly 30 test instances per cell.
- No training indices.
- No duplicates.
- No unexpected instances.
- Correct seeds and clause counts.

Apply the same completeness requirement to the
1960-instance training population.

The initial confirmatory test run must reject
subset flags.

Diagnostic or infrastructure recovery subsets require
an explicitly marked recovery mode and must retain
the original attempted-run records.

Partial output is never labeled complete.

A recovery subset cannot become a new independent
confirmatory sample.

Required regression:

- Authorized full dry run: accepted.
- Authorized one-index dry run: rejected.
- Wrong 840-instance population: rejected.
- Duplicate identifiers preserving total count:
  rejected.
- Partial combine: clearly marked incomplete.

Owner: Claude.
Independent approval: Nova.

---

### ACE-PLAN-03 — B5.1 raw-record validation

Severity: HIGH
Claim level: Empirical Observation — Nova-reported
Disposition: OPEN pending implementation

Ruling: Nova is correct.

This is a scientific-integrity blocker.

A numerical analysis function must not be able to
issue the project's official confirmatory PASS merely
because its caller supplies population="confirmatory".

Implement strict validation before records_to_rows
or other lossy conversion.

The production confirmatory analysis entrypoint must:

1. Load the authorized freeze.
2. Verify the locked training and test artifacts.
3. Load the canonical expected instance manifest.
4. Validate raw record types without permissive
   bool(), int() or float() coercions.
5. Verify every record's identity.
6. Verify formula regeneration hashes.
7. Verify features and response recomputation.
8. Verify statuses and certificate evidence.
9. Reject missing, duplicate or unexpected records.
10. Pass only validated rows to the statistical core.

The statistical core may still be callable on
synthetic or pilot rows for unit testing.

Such calls must never produce the official
confirmatory disposition.

Use separate functions or a distinct validated
population object for the production path.

Do not trust a bare verified=True field.

Required regression:

Nova's fabricated-population attack must no longer
receive an official PASS.

Also test:

- String-valued booleans.
- String-valued decision counts.
- Incorrect formula hashes.
- Swapped seeds.
- Wrong budget.
- Invalid certificate references.
- Mixed population rows.
- ERROR rows.
- Missing expected cells.

A legitimate integrity failure yields INCONCLUSIVE,
or a documented validation rejection that is
translated into the official INCONCLUSIVE disposition.

The failure must remain in the research record.

Owner: Nova, with Claude supplying runner schema
and validation interfaces.

Independent approval: Dee and Lumi.

---

### ACE-PLAN-04 — Reproduction and propagation counts

Severity: MEDIUM
Claim level: Empirical Observation — Nova-reported
Disposition: OPEN until amendment adopted

Ruling: Nova is correct, with an important distinction.

Our primary response depends on the DPLL
branch-attempt count.

It does not depend on the propagation counter.

Different valid unit-propagation schedules can
produce different numbers of recorded assignments
before discovering a contradiction.

The plan should not require every independently
implemented DPLL tracer to reproduce an
implementation-specific propagation count.

Amend the reproduction gate into two cases.

Case A: identical frozen implementation.

Repeat execution of the exact same frozen DPLL code
on the exact same formula and configuration.

Require agreement on:

- Completed or incomplete status.
- Branch-attempt count.
- Budget-exhaustion classification.
- Capped logarithmic response.

Because the implementation is intended to be
deterministic, unexplained propagation-count
differences should also be investigated.

They are an implementation-reproduction diagnostic.

Case B: independently implemented reference tracer.

Require the relevant correctness and branch-count
agreement under the same specified branching and
budget semantics.

Do not require identical propagation counters unless
the reference tracer deliberately reproduces the same
unit-propagation scheduling and counting convention.

For the frozen implementation, document:

A propagation is counted when a previously unassigned
variable receives a value through that implementation's
unit-assignment process.

Document the actual batch order and conflict
termination behavior from the frozen source.

Do not change the solver's unit-propagation algorithm
merely to make a secondary diagnostic agree.

A discrepancy confined to independent propagation
counting does not invalidate the primary estimand.

A discrepancy affecting status, branch counts,
budget exhaustion or the response remains blocking.

Secondary propagation findings require their own
implementation-specific interpretation.

Nova's reported byte-identical training reproduction
is valuable evidence.

It is not silently substituted for the coordinator's
remaining independent reproduction and freeze approval.

Owner: Claude documents measurement semantics.
Independent approval: Nova and Lumi.

---

## 7. Additional rulings arising from Nova's review

### ACE-PLAN-05 — Retained certificate verification

Severity: HIGH
Claim level: Empirical Observation — Nova-reported
Disposition: OPEN pending implementation

Regenerating a new valid certificate does not verify
the original retained certificate file.

The official audit must:

- Read the exact retained CNF.
- Read the exact retained proof.
- Verify their hashes.
- Verify their manifest association.
- Check the proof against that CNF.

Regeneration is an additional reproducibility check.

Two independently generated valid proofs need not
have byte-identical contents.

A substituted or corrupted retained proof must be
detected even if the solver can regenerate another
valid proof.

Require regression coverage for retained-file
substitution and proof-to-formula mismatches.

Owner: Claude.
Independent approval: Nova.

### ACE-PLAN-06 — Procedural versus adversarial authorization

Severity: MEDIUM
Claim level: Empirical Observation — Nova-reported
Disposition: OPEN pending documentation and tests

The runner's authorization boundary protects the
registered experiment workflow.

It is not a sandbox preventing all direct Python
calls by a researcher.

Nevertheless, test-only fault injection should be
rejected for confirmatory instances wherever the
production execution path can invoke it.

Do not expose a second official execution path
that bypasses the frozen configuration.

Direct lower-level test functions must not issue
official confirmatory authorization or official
statistical dispositions.

Owner: Claude.
Independent approval: Nova.

---

## 8. Confirmatory experiment ruling

Phase 4 adversarial review: GO.

Final experiment freeze: NO-GO pending closure
of execution-integrity blockers.

Confirmatory test execution: NO-GO.

The literature corrections do not require changing
the experimental hypothesis.

The new ECCC preprint does not require changing
the primary model.

Retain:

    B = 10000
    I10 threshold = 0.05
    1960 training instances
    840 test instances
    original seed manifest
    original primary width feature
    original statistical procedure

Before authorizing:

1. Adopt the pre-test amendments above.
2. Correct the runner and analysis integrity blockers.
3. Independently approve the repaired code.
4. Confirm the held-out population remains unopened.
5. Reproduce and validate training at the final
   execution-code commit.
6. Freeze the complete provenance bundle.
7. Check exact test-population identity.
8. Authorize through Lumi's controlled entrypoint.

Lumi alone initiates the initial confirmatory run.

No original artifact author is the sole approver
of their own repair.

---

## 9. Gate A–C disposition

### Gate A: Independent review coverage

Ace's independent review of Gemini's PR #11:
COMPLETE.

This review identifies the exact attacked commit
and the reviewed literature blob.

This does not establish that every other teammate's
review has been approved.

### Gate B: Finding disposition

Unique identifiers: COMPLETE.

Severity and claim-level classification: COMPLETE.

Reproduction instructions: COMPLETE for this review.

Mathematical counterexamples: PROVIDED.

Executed regression checks: 4/4 passed locally.

Review of fixes: OPEN.

The author must not independently close their own
findings without review.

### Gate C: Mathematical integrity

T12 correction: mathematically supported;
repository repair and review remain OPEN.

T1–T19 initial audit: COMPLETE.

Acceptance of all retained Proved entries: OPEN.

Remaining historical citation verification: OPEN
where specified above.

Current literature-table disposition: FAIL.

The existing known-result Lean formalization is not
invalidated by these literature corrections.

No new Lean-Verified claim is made here.

---

## 10. Required Gemini repair checklist

[ ] T3 uses MGT_n and consistent size parameters.
[ ] T4 uses threshold width and k+1 pebble semantics.
[ ] T5 restores the source's decomposition and cost factors.
[ ] T7 distinguishes deterministic and randomized SETH.
[ ] T8 removes the incorrect unrestricted-grid open claim.
[ ] T10 uses the nonnegative width gap.
[ ] T10 removes the unrestricted planar expansion claim.
[ ] T11 distinguishes graph and hypergraph parameters.
[ ] T11 removes the unsupported additive degree exponent.
[ ] T12 uses exact line-graph width characterization.
[ ] T13 separates the two cited proof-system results.
[ ] T14 retains source-supported bounds with consistent n.
[ ] T15 pins the simulation and certificate models.
[ ] T17 separates graph, linear-system and CNF input models.
[ ] T18 distinguishes polynomial encodings and proof sizes.
[ ] T19 removes unsupported exact linear-size claims.
[ ] Section 1 graph conventions are repaired.
[ ] Section 4 theorem/experiment distinctions are corrected.
[ ] Newly reported literature is recorded separately.
[ ] Unsupported exact historical claims remain OPEN or
    are removed.
[ ] All retained theorem statements have source locators.
[ ] Independent reviewer approves every correction.

---

## 11. Research recommendation

Do not abandon Tseitin experiments.

They remain useful for studying the difference between:

- Mathematical satisfiability.
- Restricted proof-system complexity.
- Graph-width parameters.
- Practical search behavior.
- Recognition of algebraic structure.
- Certificate construction and verification.

The new literature makes it more important to verify
novelty before claiming a theoretical discovery.

Round 02 should prioritize certified CNF-to-parity
extraction rather than reproducing a known asymptotic
Tseitin resolution lower bound and labeling it novel.

[Claim Level: Conjecture]

A certified extraction and elimination pipeline may
provide substantial practical improvements on specified
mixed and structured CNF populations.

This hypothesis requires a separate preregistration.

It must include extraction cost, verification cost,
negative examples and ordinary-CNF input semantics.

No general polynomial-time SAT-solving claim follows.

---

## 12. Handoff and limitations

Reviewed repository commit:

0f550848808f53737c0466207ce745293405bc6f

No remote changes were made.

The four mathematical regression tests were executed
in an isolated local sandbox.

No complete repository test suite was run.

No Lean build was run.

Primary-source theorem statements were inspected where
accessible.

Some PDF screenshot requests failed, although relevant
text was available.

The exact historical Tseitin attribution, selected
historical separation exponents, some original
citation markers and the precise T19 linear-size
claim were not independently resolved.

These limitations are explicitly recorded rather
than treated as successful verification.

The November 2026 preprint was verified as an
existing publication with the reported theorem
statements. Its complete proofs were not audited.

No confirmatory data was accessed.

All proposed experiment amendments preserve the
original primary scientific protocol.

Submit this review and its regression tests against
dev.

Never merge to main without Stephon's explicit
approval.

Free resources only.
No credentials or secrets.

Ace — Galactic AI Team
Operation Millennium
