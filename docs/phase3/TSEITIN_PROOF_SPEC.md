<!-- docs/phase3/TSEITIN_PROOF_SPEC.md -->

# Tseitin Parity and CNF Unsatisfiability

Operation Millennium — Discovery Round 01

Author: Ace — Galactic AI Team
Coordinator: Lumi
Research Director: Stephon
Base commit: dev 3901e30
Toolchain target: Lean 4.24.0
Mathlib target: v4.24.0
Status: Mathematical derivation and Lean implementation
submitted for independent verification.

No Lean-Verified claim is authorized until the submitted
implementation passes the required build and axiom audit.

This work reproduces an established parity argument.
It is not a novel mathematical discovery, a resolution
lower bound, or a solution to P vs NP.

---

## 1. Objective

Connect three layers of mathematical representation:

1. Finite graph endpoint incidence.
2. Parity equations over ZMod 2.
3. Boolean CNF semantics in Millennium.Sat.

The final target is an explicit theorem establishing that
a correctly encoded finite Tseitin CNF with odd total
charge has no satisfying Boolean assignment.

The relevant implementation is:

lean/Millennium/Tseitin.lean

It is imported by:

lean/Millennium.lean

The existing Sat.lean semantics remain unchanged.

---

## 2. Mathematical model

Let V be a finite type of vertices.

Let E be a finite type of edges.

Let

u, v : E -> V

specify the two endpoints of each edge.

Let

x : E -> ZMod 2

be an edge assignment.

Let

charge : V -> ZMod 2

be the requested vertex charges.

For each vertex w, define:

P(w) =
  sum over e in E of
    ([w = u(e)] * x(e) + [w = v(e)] * x(e))

The bracket notation denotes an indicator:

- 1 if the proposition holds.
- 0 otherwise.

The sum is evaluated in ZMod 2.

Both endpoint incidences are counted.

For an ordinary loopless edge, one contribution belongs
to each of its two endpoints.

For a self-loop, both contributions belong to the same
vertex.

Parallel edges remain distinguishable because they have
different identifiers in E.

Connectedness is not required for the odd-total-charge
contradiction.

---

## 3. Theorem A: Total vertex parity is zero

[Claim Level: Proved — established mathematical argument;
Lean implementation pending independent verification]

Lean theorem:

Millennium.sum_vertexParity_eq_zero

Statement:

For every finite endpoint system and edge assignment x,

sum over w in V of P(w) = 0.

### Proof

By the definition of vertex parity,

sum over w in V of P(w)

equals

sum over w in V of sum over e in E of

  ([w = u(e)] * x(e) + [w = v(e)] * x(e)).

All sums are finite, so interchange the order of summation.

For a fixed edge e, exactly one vertex equals u(e).
Exactly one vertex equals v(e).

Thus the total contribution of e is

x(e) + x(e) = 2*x(e).

Since the coefficient ring is ZMod 2,

2*x(e) = 0.

Every edge contributes zero.

Therefore the total vertex parity is zero.

QED.

### Lean implementation strategy

The implementation uses:

- Finset.sum_comm to exchange finite sums.
- Finset.sum_add_distrib to distribute summation.
- A private sum_at lemma to evaluate a single-point sum.
- Finset.sum_eq_zero to discharge the resulting sum.
- The equality (2 : ZMod 2) = 0.

This theorem does not depend on a particular graph family.

---

## 4. Theorem B: Odd total charge is contradictory

[Claim Level: Proved — established mathematical argument;
Lean implementation pending independent verification]

Lean theorem:

Millennium.odd_charge_unsat

Statement:

If

sum over w in V of charge(w) = 1,

there does not exist an edge assignment x satisfying

P(w) = charge(w)

for every vertex w.

### Proof

Assume a satisfying edge assignment exists.

Summing its vertex equations gives

sum over w of P(w) =
sum over w of charge(w).

Theorem A establishes that the left-hand side is zero.

The hypothesis establishes that the right-hand side is one.

Therefore 0 = 1 in ZMod 2, a contradiction.

QED.

### Important scope limitation

The theorem proves that odd total charge is sufficient
for unsatisfiability.

It does not assert that even total charge is sufficient
for satisfiability on arbitrary disconnected graphs.

For disconnected graphs, parity consistency must hold
separately within every connected component.

The converse theorem for connected graphs is outside
this deliverable.

---

## 5. Exact incidence correspondence

Lean definition:

Millennium.TripleIncidenceMatches

Let

a, b, c : V -> E

specify three edge incidences for each vertex.

The required relationship is:

For every vertex w and edge e,

[w = u(e)] + [w = v(e)]
=
[e = a(w)] + [e = b(w)] + [e = c(w)].

This equality is evaluated in Nat.

It is not evaluated in ZMod 2.

### Design rationale

An equality modulo two can identify different incidence
multiplicities.

For example, multiplicities zero and two are equal
modulo two.

That equality would be too weak to certify that an edge
list faithfully represents a graph's incidences.

The exact Nat equality ensures that every endpoint
incidence is represented with its correct multiplicity.

For simple 3-regular graphs, the three listed edges
at every vertex are distinct.

The same interface can describe a graph with repeated
incidences, such as a self-loop, when multiplicities
are represented correctly.

This is a mathematical specification of incidence
correspondence, not an assumption that a Python graph
generator always satisfies it.

### Theorem: Vertex parity equals the triple sum

[Claim Level: Proved — elementary derivation supplied;
pending independent team review and Lean verification]

Lean theorem:

Millennium.vertexParity_eq_triple

Statement:

If TripleIncidenceMatches holds, then

P(w) = x(a(w)) + x(b(w)) + x(c(w))

for every vertex w.

### Proof

Fix w and e.

The exact incidence correspondence equates the number
of times e occurs among the graph's endpoint incidences
at w with the number of times it occurs in the specified
triple.

Map the natural-number equality into ZMod 2 and multiply
both sides by x(e).

Summing over all edges yields equality between the
endpoint-based vertex parity and the weighted triple
incidences.

Each of the three singleton sums evaluates to its
corresponding edge value.

The result is

P(w) = x(a(w)) + x(b(w)) + x(c(w)).

QED.

---

## 6. Boolean parity

Define bitValue by

bitValue(false) = 0
bitValue(true)  = 1

in ZMod 2.

Define

xor3Parity(p,q,r) = (p XOR q) XOR r.

In the implementation, Boolean XOR is represented by
Boolean inequality.

### Theorem: Boolean parity agrees with ZMod 2

[Claim Level: Proved — elementary truth-table identity;
Lean implementation pending independent verification]

Lean theorem:

Millennium.xor3Parity_bitValue

For all Boolean p, q and r,

bitValue(xor3Parity(p,q,r))
=
bitValue(p) + bitValue(q) + bitValue(r).

The proof consists of the eight Boolean input cases.

The related theorem

Millennium.xor3Parity_check_iff

establishes that testing whether the Boolean parity
equals a requested Boolean charge is equivalent to the
corresponding equality in ZMod 2.

Its proof consists of sixteen cases.

These are finite semantic identities, not empirical
generalizations from random examples.

The submitted Lean implementation uses kernel-oriented
decide proofs on these closed finite cases.

It does not use native_decide.

---

## 7. Theorem C: XOR-to-CNF correctness

[Claim Level: Proved — elementary truth-table identity;
Lean implementation pending independent verification]

Lean theorem:

Millennium.xor3CNF_correct

For variable indices a,b,c and Boolean rhs, define the
four-clause CNF xor3CNF(a,b,c,rhs).

For rhs=true:

(a OR b OR c)

(a OR NOT b OR NOT c)

(NOT a OR b OR NOT c)

(NOT a OR NOT b OR c)

For rhs=false:

(NOT a OR NOT b OR NOT c)

(NOT a OR b OR c)

(a OR NOT b OR c)

(a OR b OR NOT c)

For every Boolean assignment sigma,

evalCNF(xor3CNF(a,b,c,rhs), sigma)

equals the Boolean test

xor3Parity(sigma(a), sigma(b), sigma(c)) == rhs.

### Complete truth table

| a | b | c | XOR parity | rhs=false CNF | rhs=true CNF |
|---|---|---|------------|---------------|--------------|
| 0 | 0 | 0 | 0 | 1 | 0 |
| 0 | 0 | 1 | 1 | 0 | 1 |
| 0 | 1 | 0 | 1 | 0 | 1 |
| 0 | 1 | 1 | 0 | 1 | 0 |
| 1 | 0 | 0 | 1 | 0 | 1 |
| 1 | 0 | 1 | 0 | 1 | 0 |
| 1 | 1 | 0 | 0 | 1 | 0 |
| 1 | 1 | 1 | 1 | 0 | 1 |

Each clause excludes precisely one of the four
incorrect-parity triples.

Their conjunction excludes all incorrect-parity triples
and accepts all correct-parity triples.

The table exhausts the finite Boolean domain.

The Lean theorem reasons about every Assignment,
not a selected collection of tested assignments.

No distinctness assumption on the three variable
indices is required for the semantic identity.

If indices coincide, the corresponding Boolean input
values coincide; the same identity continues to hold.

### Arithmetic corollary

Lean theorem:

Millennium.xor3CNF_correct_mod2

For every assignment sigma,

evalCNF(xor3CNF(a,b,c,rhs), sigma) = true

if and only if

bitValue(sigma(a)) +
bitValue(sigma(b)) +
bitValue(sigma(c))
=
bitValue(rhs).

This follows from XOR-to-CNF correctness and the
Boolean-to-ZMod-2 correspondence.

---

## 8. Composition of CNF constraints

### CNF concatenation

[Claim Level: Proved — elementary induction;
Lean implementation pending independent verification]

Lean theorem:

Millennium.evalCNF_append

For all CNFs phi and psi and every assignment sigma,

evalCNF(phi ++ psi, sigma)
=
evalCNF(phi, sigma) AND evalCNF(psi, sigma).

Proof:

Induct on phi.

For the empty CNF, its evaluation is true, which is
the identity for conjunction.

For a nonempty CNF, expand evalCNF at the first clause,
apply the induction hypothesis to the remaining clauses,
and use Boolean conjunction.

QED.

### Construction

Lean definition:

Millennium.tseitinCNF

The construction concatenates xor3CNF for every vertex
in a supplied finite list.

Inputs:

- Explicit edge-to-variable map idx.
- Three incidence maps a,b,c.
- Boolean vertex charges.
- Vertex list.

The final theorem separately requires that every vertex
occurs in the list.

The list may contain duplicates.

Duplicate vertex constraints do not invalidate
unsatisfiability soundness.

No assumption about the order of vertices is necessary
for the mathematical result.

### Local extraction theorem

[Claim Level: Proved — elementary induction;
Lean implementation pending independent verification]

Lean theorem:

Millennium.eval_tseitinCNF_local

If an assignment satisfies the concatenated Tseitin CNF,
then it satisfies the individual XOR encoding at every
vertex appearing in the construction list.

Proof:

Induct on the vertex list.

The empty list has no member, so the implication is
vacuous.

For a nonempty list, CNF concatenation correctness gives
satisfaction of both the head constraint and the
remaining concatenated constraints.

If the requested vertex is the head, use the first
conjunct.

Otherwise apply the induction hypothesis.

QED.

---

## 9. Final integration theorem

[Claim Level: Proved — mathematical derivation supplied;
pending independent team review and Lean verification]

Lean theorem:

Millennium.tseitinCNF_odd_unsat

### Assumptions

1. V is a finite vertex type.
2. E is a finite edge type.
3. u,v : E -> V specify endpoints.
4. idx : E -> Nat maps edges to CNF variable indices.
5. a,b,c : V -> E specify vertex incidence triples.
6. TripleIncidenceMatches holds.
7. Every vertex appears in the construction list.
8. The total Boolean charge, interpreted in ZMod 2,
   equals one.

### Conclusion

There does not exist a Boolean assignment sigma such that

evalCNF(tseitinCNF(idx,a,b,c,charge,vertices), sigma)
=
true.

### Proof

Assume a satisfying Boolean assignment sigma exists.

Define an edge assignment x by

x(e) = bitValue(sigma(idx(e))).

Fix any vertex w.

The coverage assumption ensures that w appears in the
construction list.

The local extraction theorem establishes satisfaction
of its four-clause XOR encoding.

The arithmetic XOR-to-CNF theorem consequently gives

x(a(w)) + x(b(w)) + x(c(w))
=
bitValue(charge(w)).

The incidence correspondence theorem gives

P(w) = x(a(w)) + x(b(w)) + x(c(w)).

Therefore

P(w) = bitValue(charge(w)).

Because w was arbitrary, x satisfies all vertex
parity equations.

But the total charge is one.

The odd-charge unsatisfiability theorem excludes the
existence of such an edge assignment.

This is a contradiction.

QED.

### Result scope

This is a semantic unsatisfiability theorem for a
specified mathematical construction.

It does not prove a lower bound on:

- Resolution proof size.
- Resolution proof width.
- DPLL search effort.
- CDCL search effort.
- General SAT-solving time.
- Boolean circuit size.

It does not establish P != NP.

---

## 10. Edge identifiers and DIMACS correspondence

The Lean SAT semantics use natural-number variable
indices and total Boolean assignments.

The Python laboratory uses signed, one-indexed DIMACS
literal lists.

The map

idx : E -> Nat

is explicit in the integration theorem.

For faithful correspondence with the Python generator,
a graph-to-DIMACS adapter should establish:

1. Every edge has exactly one identifier.
2. Every identifier is positive.
3. Distinct edges receive distinct identifiers.
4. Every identifier is within the declared variable range.
5. Every required vertex incidence is represented.
6. Each vertex's charge is encoded with the intended sign
   pattern.
7. The actual CNF matches the constructed encoding.

### Why injectivity is not assumed in the final theorem

The final theorem is one-directional.

It establishes that no CNF assignment can satisfy the
odd-charge construction.

Even if different abstract edges receive the same CNF
variable index, any hypothetical satisfying assignment
still induces an abstract edge assignment by composition
with idx.

That induced assignment is ruled out by the parity
contradiction.

Therefore injectivity is unnecessary for this particular
unsatisfiability theorem.

However, injectivity is important for faithful
representation and for a future satisfiability
completeness theorem.

The stronger DIMACS requirements must not be silently
dropped when claiming generator equivalence.

---

## 11. Python/Lean fixture comparison

The source of _xor3_clauses in

lab/om_lab/hard_instances.py

was inspected at dev 3901e30.

The following fixed fixtures reproduce the observed
Python clause order.

### Odd local charge

Python invocation:

_xor3_clauses(1, 2, 3, 1)

Expected result:

[
  [1, 2, 3],
  [1, -2, -3],
  [-1, 2, -3],
  [-1, -2, 3]
]

Corresponding Lean theorem:

Millennium.xor3CNF_dimacs_true

### Even local charge

Python invocation:

_xor3_clauses(1, 2, 3, 0)

Expected result:

[
  [-1, -2, -3],
  [-1, 2, 3],
  [1, -2, 3],
  [1, 2, -3]
]

Corresponding Lean theorem:

Millennium.xor3CNF_dimacs_false

### Local validation performed

[Claim Level: Empirical Observation]

Ace executed a standalone Python check using a
transcription of the repository's _xor3_clauses
implementation.

Observed results:

- Two expected-clause-list comparisons passed.
- Sixteen Boolean truth-table checks passed.
- No mismatch was observed.

This check did not import or execute the repository's
actual Python module.

It did not compile Lean.

The checked code was a local transcription.

The Lean fixture declarations are submitted for CI
verification and must not be described as already passed.

### Independent reproduction code

The following script should be run against the installed
repository package, rather than the transcription:

    from itertools import product
    from om_lab.hard_instances import _xor3_clauses

    fixtures = {
        0: [
            [-1, -2, -3],
            [-1, 2, 3],
            [1, -2, 3],
            [1, 2, -3],
        ],
        1: [
            [1, 2, 3],
            [1, -2, -3],
            [-1, 2, -3],
            [-1, -2, 3],
        ],
    }

    for rhs in (0, 1):
        clauses = _xor3_clauses(1, 2, 3, rhs)
        assert clauses == fixtures[rhs]

        for values in product((False, True), repeat=3):
            assignment = dict(enumerate(values, start=1))

            result = all(
                any(
                    assignment[abs(lit)] == (lit > 0)
                    for lit in clause
                )
                for clause in clauses
            )

            p, q, r = values
            expected = (p ^ q ^ r) == bool(rhs)

            assert result == expected

    print("Both fixtures and all 16 cases passed")

Passing this script confirms the local encoder fixtures.

It does not certify every output of
generate_tseitin_3sat.

The Lean fixture conversion helper is not a validated
DIMACS serializer.

---

## 12. Recommended adversarial review

### Graph structure

Attempt to violate the final theorem's assumptions
using the following cases:

- Empty vertex type.
- Empty edge type.
- Disconnected graphs.
- Self-loops.
- Parallel edges.
- Repeated incidence identifiers.
- Missing endpoint incidences.
- Incorrect incidence triples.
- Incorrect vertex coverage.

Expected mathematical behavior:

Odd total charge remains contradictory whenever the
stated assumptions hold.

Malformed representations may fail the assumptions.

They should not be accepted as counterexamples to the
conditional theorem without establishing those
assumptions.

### Vertex coverage

Dropping vertex coverage would be unsound.

For example, an empty construction list produces the
empty CNF.

The empty CNF is satisfied by every assignment.

It cannot encode an arbitrary contradictory nonempty
parity system.

The final theorem therefore explicitly requires
coverage of every vertex.

### Incidence correspondence

Dropping exact incidence correspondence would allow
unrelated triples to be substituted for graph
incidences.

That would disconnect the CNF from the parity argument.

The final theorem requires the correspondence rather
than treating it as an undocumented invariant.

### Variable indexing

Test positive, distinct indices in the intended Python
adapter.

Test repeated indices separately.

Repeated indices may preserve the one-way
unsatisfiability theorem while violating faithful
graph representation.

### Charge consistency

Test:

- All-zero charges.
- Exactly one nonzero charge.
- Exactly two nonzero charges.
- Odd total charge in a disconnected graph.
- Even total charge distributed across components
  with individually odd charges.

The final two cases distinguish global odd-charge
soundness from a stronger componentwise characterization.

---

## 13. Complexity and barrier audit

### Relativization

N/A as a P vs NP barrier for this result.

No complexity-class separation is claimed.

### Natural proofs

N/A.

No general Boolean circuit lower bound is claimed.

### Algebrization

N/A.

No class inclusion or separation is claimed.

### Representation audit

Required and addressed through:

- Explicit finite vertex and edge types.
- Explicit endpoint maps.
- Exact natural-number incidence counts.
- Explicit edge-to-variable map.
- Explicit vertex-list coverage.
- Existing CNF semantics.

Remaining representation work:

- Verified DIMACS parsing.
- Compact finite assignment certificates.
- Python-to-Lean instance correspondence.
- Proof-producing validation of generated graph data.
- Computational cost model.

The current result concerns semantics only.

Neither an abstract Assignment nor the existence of
these theorems establishes polynomial verification cost.

---

## 14. Lean build and axiom acceptance gate

From the repository root:

    cd lean
    lake build

The target workspace specifies:

Lean 4.24.0

Mathlib v4.24.0

The submitted source imports Mathlib broadly to avoid
unnecessary uncertainty over minimal module imports.
This can be narrowed later after successful CI.

All exported theorems have explicit #print axioms
commands in Tseitin.lean.

Audit targets:

- Millennium.sum_vertexParity_eq_zero
- Millennium.odd_charge_unsat
- Millennium.vertexParity_eq_triple
- Millennium.xor3Parity_bitValue
- Millennium.xor3Parity_check_iff
- Millennium.xor3CNF_correct
- Millennium.xor3CNF_correct_mod2
- Millennium.evalCNF_append
- Millennium.eval_tseitinCNF_local
- Millennium.tseitinCNF_odd_unsat
- Millennium.xor3CNF_dimacs_true
- Millennium.xor3CNF_dimacs_false

Acceptance requires:

1. The complete workspace builds successfully.
2. Every theorem elaborates and is kernel-checked.
3. No admitted proof placeholders.
4. No custom axioms.
5. No sorryAx dependency.
6. No Lean.ofReduceBool dependency introduced through
   native_decide.
7. Axiom dependencies satisfy docs/RULES.md.
8. Independent review confirms that the statements
   express the intended mathematical claims.
9. Both Python fixture comparisons pass against the
   actual repository implementation.

Permitted standard axioms under the repository rules:

- propext
- Classical.choice
- Quot.sound

A theorem using fewer axioms or no axioms is acceptable.

Record the actual axiom output, rather than asserting
in advance which subset will appear.

The use of ordinary decide on finite closed cases is
intended to permit kernel reduction without introducing
native_decide assumptions.

### Claim promotion

Before a successful build:

Mathematical argument: Proved in the stated sense,
with independent team review pending where required.

Lean implementation: unverified proof submission.

After a successful independent build and axiom audit:

Eligible for Lean-Verified promotion under RULES.md.

A failed build does not make the underlying mathematical
argument false.

However, it does mean the submitted formalization has
not met its acceptance criterion.

Retain build failures and subsequent fixes in the
research record.

---

## 15. Theoretical interpretation

[Claim Level: Proved — direct scope distinction]

Odd-charge Tseitin unsatisfiability is a statement about
the inconsistency of a system of parity equations.

It does not establish that proving the inconsistency
is difficult in every proof system or computational
representation.

A parity contradiction is directly visible by adding
the equations modulo two.

A SAT solver operating on the expanded CNF may not
immediately exploit that algebraic structure.

Whether it does so efficiently is a separate empirical
or proof-complexity question.

### Proposed follow-up

[Claim Level: Conjecture — untested]

For some structured Tseitin instance populations,
explicit extraction and elimination of parity equations
may substantially reduce measured solver effort
relative to a specified clause-based DPLL baseline.

This must be evaluated under a separate protocol.

The complete algorithm must include the cost of
detecting or extracting parity equations.

Do not give the algebraic method access to privileged
generator metadata while describing the comparison as
an equal-input general SAT-solving experiment.

The known odd-charge theorem alone does not establish
that the proposed comparative performance hypothesis
is true.

---

## 16. Explicit limitations and handoff

The submitted deliverable contains:

- Finite vertex-parity semantics.
- Total-parity theorem.
- Odd-charge contradiction theorem.
- Exact incidence correspondence.
- Boolean parity identities.
- Four-clause XOR encoding.
- CNF concatenation theorem.
- Local constraint extraction theorem.
- Final odd-charge Tseitin CNF unsatisfiability theorem.
- Fixed signed-integer fixtures.
- Axiom-audit commands.
- Mathematical proof specification.

Repository sources were inspected at dev 3901e30.

The Python fixture transcription was checked locally.

Lean and Lake were unavailable in Ace's execution
environment.

Therefore:

- No Lean compilation is claimed.
- No successful CI run is claimed.
- No actual axiom output is claimed.
- No full Python generator formalization is claimed.
- No new complexity separation is claimed.

No repository branch or commit was created.

The coordinator should submit these three files on a
branch based on dev and perform the independent build.

Never merge into main without Stephon's explicit
approval.

Free resources only.

No credentials or secrets are included.

Ace — Galactic AI Team
Operation Millennium
Discovery Round 01
