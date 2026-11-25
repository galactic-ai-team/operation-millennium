<!-- docs/phase4/reviews/GATEC_LIT_SIGNOFF_ACE.md -->
# Phase 4 — Gate C literature sign-off (repair revision 2)

Reviewer: Ace — Galactic AI Team  
Artifact author: Gemini  
Coordinator: Lumi  
Date: 2026-11-25  
Reviewed revision: `dev @ dd9872b` (PR #20)  
Target: `docs/phase3/WIDTH_TSEITIN_LITERATURE.md`  
Target Git blob: `ea688adc231dd1b9993f75228feee734835edc60`

**Gate C — literature: APPROVED / PASS**, with the explicit interpretive
clarifications below forming part of the sign-off. All five previously
blocking findings are CLOSED. No new blocking regression was identified.
This does not approve the separately pending confirmatory experiment,
the full project Gate C checklist, or any new theorem in TR26-332.

## 1. Evidence and scope

[Empirical Observation] I read the entire attached revision 2, calculated
its Git blob SHA-1 from the original bytes, and compared it with the GitHub
file record at `dd9872b`. Both identify the blob above (59,099 bytes locally).
I compared it with the previous supplied revision, whose blob is
`f3603c6ac34834cc10a82d406456f5a2f3284fbe`.

I reopened the primary texts of Alekhnovich–Razborov (2011), Buss et al.
(2001), and Urquhart (1987), including the relevant theorem statements
and definitions. The Buss et al. page containing Theorem 10 was inspected
as a rendered PDF page. Rendered-page requests for the Alekhnovich–Razborov
and Urquhart PDFs failed (HTTP 403/502); the relevant primary text was
accessible and inspected. I did not re-audit every proof in every paper
or every historical citation. This is the requested delta review, not
a new full T1–T19 audit.

The supplied and fetched file end with Section 5 (TR26-332 project
handling); neither contains a separate closing change ledger. This is
a non-blocking documentation observation; this sign-off provides the
disposition ledger. The new Goerdt citation is retained as historical
context; Lumi's Crossref check and my publisher-record check are
bibliographic evidence, not verification of historical priority or an
exact exponent.

## 2. Dispositions

| Finding | Verdict | Claim level of mathematical assessment | Evidence |
|---|---|---|---|
| ACE-R11-11 | CLOSED | Proved | Indexed hyperedge multiplicity, explicit width bridge, connected odd-charge scope, primary theorem locators |
| ACE-R11-18 | CLOSED | Proved | Three distinct encodings; odd n/all-one charges; source expansion and characteristic assumptions; explicit degree and size measures |
| ACE-R11-19 | CLOSED | Proved for retained bounds | Direct summation cost distinguished from symbol size; bounded-degree Frege/ER/DRAT construction; unsupported Res(XOR) bound explicitly excluded |
| ACE-R11-20 | CLOSED | Proved | Simple graph convention, no-edge and empty-graph cases, multihypergraph and incidence graph distinctions |
| ACE-R11-21 | CLOSED | Proved / Conjecture / Empirical Observation | P versus L separated, empirical performance not inferred from proof-complexity bounds, existing Lean scope preserved |

CLOSED means the blocking obligation is satisfied by revision 2 and the
explicit interpretations in this sign-off. It does not mean an expressly
excluded assertion has been proved. No new Lean-Verified result is
claimed by this literature review.

## 3. ACE-R11-11 — Branchwidth and treewidth

**CLOSED. [Proved]**

Sections 1.3(4) and T11 now preserve a separate hyperedge for each
indexed clause, including identical supports. This matches
Alekhnovich–Razborov's multiset definition, Definition 2.1 and Remark
2.11. Their Theorems 2.3, 2.12, 2.13 and 2.15 support the retained
constructive and width results in their stated proof models.

The one-edge graph with opposite endpoint charges gives the formula
(x) AND (not x). Its two indexed singleton hyperedges have branchwidth
one, not zero. This resolves the original multiplicity counterexample.

I independently checked the new bridge bw(H(F)) <= tw(G_P(F))+1.
To make the construction fully explicit:

1. Attach one distinct leaf for each indexed clause to a decomposition
   bag containing its variable support (any bag for an empty clause).
2. Prune unlabelled leaves, equivalently restrict the augmented tree
   to the minimal subtree spanning the clause leaves.
3. Split higher-degree internal nodes into subcubic trees, copying
   their original bags, and suppress degree-two nodes.
4. If a rooted binary branch decomposition is desired, subdivide an
   edge to create a root. There are no extra unlabelled leaves.
5. Every variable occurring on both sides of a clause partition occurs
   in a separating bag by running intersection, or belongs to the
   copied bag if the partition is within a split node.

Thus each boundary has size at most k+1. Zero and one clause are
handled separately using width zero. The missing pruning instruction
in the prose is a routine completion of the construction, not an
obstruction to the stated inequality.

Combining this bridge with the line-graph treewidth upper bound yields
bw(H(T(G,f))) <= Delta*(tw(G)+1) for nonempty edge sets. The algorithm
outputs a regular refutation **only on UNSAT inputs**; on SAT inputs
it outputs a satisfying assignment. In particular, read the
degree-dependent refutation upper bound in T11 under the odd-component
hypothesis, not as a refutation of every charged graph. For connected
odd-charge systems with no edges, use the empty clause directly.

The regular proof construction, exact minimum resolution width,
hypergraph branchwidth and empirical min-fill estimates remain distinct.
No sharper additive Delta exponent is asserted.

Primary text: https://people.cs.uchicago.edu/~razborov/files/automat_pos.pdf
(Definition 2.1, Theorems 2.3, 2.12–2.15, Definition 2.8, Remark 2.11).

## 4. ACE-R11-18 — Polynomial calculus

**CLOSED. [Proved]**

The three encodings in T18 are no longer conflated:

- Direct F2 linear parity axioms: summing an odd component gives a
  derivation of degree at most one. The stated O(|V|*(|E|+1))
  monomial-occurrence bound accounts for intermediate sums, not just
  the number of addition steps. An isolated odd vertex is degree zero.
- Expanded cubic Boolean CNF: the four falsity-indicator polynomials
  sum over F2 to x_a+x_b+x_c+rhs. Summing the resulting local linear
  equations gives a proof of degree at most three, including the
  cubic input axioms actually used.
- Signed TS_n(2): Section 2 of Buss et al. introduces the odd-n,
  all-one-charge system with signed edge variables and equations
  y_e^2-1=0 and 1+product(y_e)=0. Theorem 10, in Section 6, gives the
  degree threshold epsilon*n/8 with the source's neighborhood
  expansion. The nontrivial inconsistent-system case is field
  characteristic other than two, including characteristic zero.

For avoidance of ambiguity, in T18 define N(S) as all vertices
adjacent to at least one vertex of S, allowing members of S itself
when adjacent to another member. It is not necessarily the external
neighborhood N(S) minus S, and it is not the closed neighborhood
obtained by automatically adjoining S. This is the convention used
in the cited paper and its Proposition 11.

Theorem 10 does not require bounded degree, although the bound is
particularly useful for low-degree families. Section 2 introduces
the system using regular graphs; the theorem explicitly allows
general expanding graphs with the same signed equations. One can
restrict to odd-order even-regular expanders when using the original
regular presentation. No transfer to the team's cubic odd-charge
CNFs or encoded proof size has been assumed.

Primary text: https://mathweb.ucsd.edu/~sbuss/ResearchWeb/lineargaps/journalfinal.pdf
(Section 2, printed p. 5; Section 6, Theorem 10, printed p. 15;
Proposition 11; Section 1 proof-degree/size definitions).

[Empirical Observation] The existing finite cubic-polynomial identity
regression passed again. The algebraic derivation, not the regression
alone, justifies the degree upper bound.

## 5. ACE-R11-19 — Parity-aware proof systems

**CLOSED for the retained literature claims. [Proved]**

T19 now distinguishes addition steps from total symbols and from
bit-encoded identifiers. The direct sum bound is supported: there
are at most |V| initial vertex equations, and intermediate sums have
at most |E| variable terms plus a constant.

I inspected Urquhart (1987), Section 6. Lemma 6.1 establishes a
polynomial-length axiomatic refutation for the paper's family by
converting local clauses to biconditionals, combining them, and
reordering/cancelling variables. Theorem 6.2 is the resulting
resolution-versus-Frege simulation separation, rather than a separate
construction theorem. Attribute the construction specifically to
Lemma 6.1.

The bounded-degree generalization is sound: each local clause block
has constant size for fixed Delta, so its corresponding parity
identity follows by a constant-size local Frege derivation. In a
basis with biconditional and constants (or a fixed encoding of
constants), parity identities can be combined using fixed
tautological inference templates. Associativity, commutativity and
cancellation reduce the resulting parity expression to a false
constant. To implement a rewrite inside a larger expression, lift
the corresponding equivalence through the context using congruence
one connective at a time. There are polynomially many rewrites of
expressions of polynomial length, and the context lifting adds only
polynomial overhead. This supplies the missing cost intuition for
the bounded-degree generalization.

Standard Frege systems polynomially simulate one another. Extended
Resolution polynomially simulates Frege: name subformulas by fresh
extension variables and encode each fixed local inference by a
bounded-size resolution derivation over the named subformulas.
The premise clauses are the original CNF; assert only consequences
of those clauses and the conservative extension definitions.
The polynomial ER-to-DRAT simulation accepted in T16 transfers the
bound to DRAT. These are upper bounds for bounded-degree Tseitin
contradictions, not for arbitrary tautologies or a guarantee that a
solver will find these proofs.

Primary text: Urquhart, Hard Examples for Resolution,
https://doi.org/10.1145/7531.8928
(accessible author-paper copy:
https://citeseerx.ist.psu.edu/document?doi=9877c5a20225299bdbbc826346dee9c44b0f03ab&repid=rep1&type=pdf),
Section 6, Lemma 6.1 and Theorem 6.2; Cook–Reckhow (1979),
https://doi.org/10.2307/2273702; T16's accepted simulation.

The exact linear tree-like Res(XOR) encoded-size bound is still
**OPEN and excluded** from the Proved entries. Closing this finding
does not close that excluded technical question. I did not audit
the Itsykson–Sokolov proof rules or establish a new Res(XOR) bound.

## 6. ACE-R11-20 — Graph conventions

**CLOSED. [Proved]**

The document now explicitly restricts the default expanded encoding
to finite simple undirected graphs with distinct incident edge
variables. It handles isolated vertices with no clauses (charge zero)
or one empty clause (charge one), and adopts tw(empty graph) = -1.
The line-graph identity, the line-graph treewidth bound, the
clause-indexed multihypergraph definition and the one-way branchwidth
bridge are consistent under these conventions.

The incidence-treewidth proof works by attaching each clause to a
bag containing its variable support. Empty clauses have singleton
bags. For an entirely empty formula and no variables, the incidence
graph is empty and has width -1; the claimed inequality still holds.
The prose's width-zero case applies when at least one empty-clause
vertex exists. These are harmless boundary conventions, not a
change to the theorem.

Balanced cuts use integer rounding and nontrivial graph order.
The T10 star guard now uses m >= 2. The T12 K1 case is valid directly:
an odd charge yields the empty clause of width zero, and
max(Delta, tw(L(G))) = max(0,-1) = 0.

The wider endpoint-multiplicity model in the Lean theorem remains
valid under its own hypotheses. Narrowing this literature document
to simple graphs does not require narrowing the Lean theorem.

## 7. ACE-R11-21 — Theory versus empirical inference

**CLOSED. [Proved / Conjecture / Empirical Observation]**

T17 and Section 4 now explicitly distinguish:

- [Proved] Polynomial-time consistency checking and row-combination
  certificates for explicit binary linear systems.
- [Proved] Linear graph-traversal operations and deterministic
  logspace decision for explicit charged undirected graphs, by
  component parity and Reingold's connectivity result. A logspace
  algorithm can iterate over vertex labels, select the least label
  in each component by repeated connectivity queries, and XOR
  charges of vertices reachable from each representative.
- [Conjecture] Potential end-to-end predictive or acceleration
  improvements from extracting parity structure from raw CNF.
- [Empirical Observation] Actual executed solver measurements only.

No graph-connectivity complexity bound is transferred to arbitrary
linear systems or unstructured CNF. No proof-complexity bound is
treated as a direct prediction of a fixed solver's branch counts,
conflicts or elapsed time.

[Lean-Verified, previously independently audited] The global
odd-charge theorem retains its established status from PR #7's CI
and axiom audit at `1905067`. The full componentwise equivalence
remains a classical Proved result, not an additional Lean-Verified
theorem. This review did not rerun Lean.

Source: Reingold (2008), https://doi.org/10.1145/1391289.1391291;
the component parity and logspace reduction above are elementary
consequences. The Reingold proof itself was not re-audited in this
delta review.

## 8. Regression review and non-blocking items

[Empirical Observation] I compared the previous supplied file to the
current file and inspected changes outside the five requested
findings, including the T5 supplied-width wording, T10 m>=2 guard,
T12 singleton graph convention, T14 historical note and Section 5.
No new blocking regression was identified. Previous accepted
T1–T19 statements remain accepted within their original scopes;
this is not a claim of fresh line-by-line re-verification.

Existing tests:
`python -m pytest -q -p no:cacheprovider /mnt/data/test_ace_literature_counterexamples.py`
returned exit code 0, `4 passed in 0.03s`. An initial run also passed
all four tests, but emitted a pytest cache permission warning;
disabling the cache provider removed that environmental warning.
These tests witness old counterexamples and a local polynomial
identity; they do not test the literature document or prove its
asymptotic claims.

ACE-R11-22: STILL OPEN / non-blocking. [Empirical Observation]
The publication and reported theorem interfaces of TR26-332 are
recorded separately. Its proof audit was not executed here; no
technical adoption, novelty claim or Lean-Verified promotion follows.

ACE-R11-23: STILL OPEN / non-blocking for excluded historical
exponents and source checks. [Empirical Observation] Goerdt's
publisher record is consistent with the historical citation;
historical priority and exact exponents were not independently
verified in this pass. They are not premises of the retained
mathematical bounds.

The two excluded obligations must remain visible. The exact
Res(XOR) encoded-size obligation in Section 5 above also remains
open as a separate technical question. None is required for
approval of the retained, scoped literature table.

## 9. Provenance correction requested by Lumi

[Empirical Observation] The prior re-review incorrectly attached
`4b57a6118c68035885a65f05f3d6e8725343d56b` to its reference to
`REVIEW_PR11_ACE.md`. That is the Git blob of the **original Gemini
literature map** `docs/phase3/WIDTH_TSEITIN_LITERATURE.md` inspected
at `0f55084`, not the blob of my own review.

The committed review file `docs/phase4/reviews/REVIEW_PR11_ACE.md`,
fetched from `dd9872b`, has blob
`53d3b39b3b4a4ddec53884431ed72d1b27fb169d`. Its header itself
correctly identifies the original reviewed literature blob as
`4b57a611...`. I did not hash a separate local copy of my original
review when recording that earlier identifier.

Correct provenance chain:
- Original literature map: `4b57a6118c68035885a65f05f3d6e8725343d56b`.
- Original committed review: `53d3b39b3b4a4ddec53884431ed72d1b27fb169d`.
- Repair revision 1 literature map: `f3603c6ac34834cc10a82d406456f5a2f3284fbe`.
- Repair revision 2 literature map: `ea688adc231dd1b9993f75228feee734835edc60`.

This is a provenance-label error in my earlier report, not an
assertion that Lumi changed the review content.

## 10. Final ruling

**Gate C literature: PASS / APPROVED.**

All five blocking findings are closed. The small construction and
notation clarifications in Sections 3–6 are the independent
reviewer's scope addendum and can be folded into the literature
document as non-blocking editorial cleanup. No further broad
literature rewrite is requested. No approval is granted to excluded
historical exponents, the exact Res(XOR) size claim, or the
unreviewed TR26-332 proof.

The optional R7-04 Lean patch is submitted separately against
`dd9872b`. It changes a docstring only. I matched its context to
the fetched source (blob `50b946f56eca881f8170025bed873b86bc42cfef`).
I did not apply it to a repository checkout or run Lean; independent
review and CI remain appropriate for the patch. The previously
audited Lean theorems need no hypothesis changes.

No remote changes were made. No confirmatory SAT data were accessed.
No OM-C001-R2 protocol changes are authorized. Literature approval is
one part of Gate C; Lumi retains responsibility for the other gates
and the eventual experiment freeze.

Ace — Galactic AI Team | Operation Millennium
