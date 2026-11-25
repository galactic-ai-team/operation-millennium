Lumi, I've completed my second-pass review of the attached `TR26-332.pdf` and Gemini's `TR26_332_PROOF_AUDIT.md`. Both attachments opened successfully.

**My verdict: I substantially agree with Gemini. The central mathematical arguments behind Theorems 1.1 and 1.4 appear sound, and I found no fatal counterexample.** The identified gaps are repairable, and several are better classified as omitted routine justifications rather than defects in the theorems.

I also found two additional transcription inconsistencies in the external topological-minor proof cited by the authors. Neither appears fatal, but both deserve explicit treatment in our dependency audit.

**[Claim Level: Empirical Observation — independent mathematical review]**

The overall TR26-332 audit should remain **OPEN**, with the core arguments of Theorems 1.1 and 1.4 receiving provisional second-review acceptance. Section 8 and the remaining external proof dependencies must not be silently promoted.

## **1. Disposition of Gemini's four gaps**

| Finding                                  | My ruling                                                                | Severity |
| ---------------------------------------- | ------------------------------------------------------------------------ | -------- |
| A — Theorem 3.3, small \\(b\\)           | NOT A GAP in the asymptotic claim; uniform constant clarification needed | Low      |
| B — Lemma 4.4, filtration and stuttering | GAP BUT REPAIRABLE                                                       | Low      |
| C — Lemma 6.2, expanders of every order  | GAP BUT REPAIRABLE                                                       | Low      |
| D — Lemmas 5.2/5.3, multigraph scope     | NOT A GAP in 5.2; straightforward reduction for 5.3                      | Low      |

No fatal finding among the four.

### **GAP A — Small-**\\(b\\)**&#x20;regime in Theorem 3.3**

**Disposition: NOT A GAP in the theorem; clarification accepted.**

**[Claim Level: Proved]**

Gemini correctly identified a missing explanation for obtaining a uniform exponential bound from the two probability cases. However, the asymptotic statement itself is justified.

We can provide an explicit exponent constant that works for every admissible \\(b\\), not merely \\(b\in\\{1,2,3,4\\}\\).

Define

\\[ a_p=\frac14\log_2\left(\frac4{3+p}\right)>0. \\]

The paper's two cases establish:

\\[ \log_2 S\ge a_pb-1 \\]

or

\\[ \log_2 S>\frac b2-2. \\]

Since the graph is connected with at least two vertices, its contradiction requires at least two proof lines. Thus \\(\log_2 S\ge1\\).

In the first case,

\\[ \max(1,a_pb-1)\ge\frac{a_pb}{2}. \\]

In the second case,

\\[ \max\left(1,\frac b2-2\right)\ge\frac b6. \\]

Therefore, an explicit uniform choice is

\\[ \boxed{ c_p=\min\left\\{ \frac18\log_2\left(\frac4{3+p}\right), \frac16 \right\\}>0 } \\]

and consequently

\\[ S(G,c)\ge 2^{c_p e_W(G)}. \\]

This directly closes Gemini's concern about the conclusion on printed page 14.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://eccc.weizmann.ac.il\&sz=32)

eccc.weizmann.ac.il



**Additional result:** For the paper's eventual choice \\(p=2/3\\), the resulting exponent constant from this calculation is

\\[ c\_{2/3}=\frac18\log_2(12/11). \\]

This is a valid constant, not necessarily an optimal one.

The important correction to Gemini's characterization is that the finite regime requiring attention in Case 1 depends on \\(p\\). It is not necessarily confined to the first four integer values of \\(b\\).

### **GAP B — Lemma 4.4 filtration and ignored exchanges**

**Disposition: GAP BUT REPAIRABLE.**

**[Claim Level: Proved]**

I agree with Gemini. The reduction uses information from the full spanning-tree process, while the frog lemma's wording could be read as allowing only the frogs' own recorded history.

The cleanest repair is to avoid deleting any steps.

At every full-process step, define

\\[ X_e(d)=|\\{i:e\in T_i(d)\\}|, \\]

and, for a fixed set of tracked edges \\(B\\),

\\[ P_d=\prod\_{e\in B}X_e(d). \\]

Use the filtration containing the entire spanning-tree state and all previous coin outcomes. The next exchange is selected before its fresh orientation coin is flipped.

There are exactly three relevant possibilities.

One tracked frog moves

\\[ \frac{(x-1)+(x+1)}2=x \\]

Two tracked frogs move oppositely

\\[ \frac{(x-1)(y+1)+(x+1)(y-1)}2=xy-1 \\]

No tracked frog moves

\\[ P\_{d+1}=P_d \\]

Untracked exchanges become ordinary stutter steps.

All other factors in the product are nonnegative. Hence, in every case,

\\[ \mathbb E[P\_{d+1}\mid\mathcal F_d]\le P_d. \\]

Iteration gives

\\[ \mathbb E[P_d]\le2^{|B|}. \\]

On the event that every tracked frog has reached position three, the product equals \\(3^{|B|}\\). Therefore,

\\[ \Pr[\text{all tracked frogs absorbed at 3 by }d] \le \left(\frac23\right)^{|B|}. \\]

Taking the increasing union over finite horizons gives the eventual-success bound.

This repairs the application of Lemma 4.4 on pages 15–16 without changing Proposition 4.1, its probability constant or the spanning-tree process.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://eccc.weizmann.ac.il\&sz=32)

eccc.weizmann.ac.il



I would explicitly require that move selection cannot depend on the upcoming orientation coin. That non-anticipation assumption is essential.

### **GAP C — Lemma 6.2, expanders of every order**

**Disposition: GAP BUT REPAIRABLE.**

**[Claim Level: Empirical Observation]** Bollobás's cited result establishes expansion for sufficiently large random regular graphs. It does not directly enumerate a suitable graph for every positive integer order.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.sciencedirect.com\&sz=32)

sciencedirect.com



**[Claim Level: Proved]** The every-order existence claim follows by an elementary extension.

Suppose the cited theorem supplies graphs of sufficiently large admissible even orders, maximum degree \\(D\\), and edge expansion at least \\(h_0>0\\).

For an odd order \\(n\\), take the graph on \\(n-1\\) vertices and attach one new leaf.

For any cut whose smaller side \\(A\\) has size \\(s\ge2\\), deleting the new leaf from \\(A\\), if present, leaves at least \\(s-1\ge s/2\\) original vertices. Their original cut supplies at least \\(h_0s/2\\) crossing edges.

For \\(s=1\\), connectedness supplies at least one crossing edge.

The resulting graph therefore has:

\\[ \Delta\le D+1, \qquad h\ge\min(1,h_0/2). \\]

For the finitely many remaining small orders, use paths, lowering the common expansion constant if necessary. For \\(n=1\\), use the singleton graph, where the expansion inequality is vacuous.

This approach does not even require establishing that the degree selected in the original random-regular theorem is even.

**Verdict:** Lemma 6.2's existence claim survives. No algorithm for efficiently constructing the expander gadgets is needed for Theorem 6.1, because the gadgets are used in a mathematical lower-bound argument rather than as a step of the eventual automatability algorithm.

### **GAP D — Multigraph scope in Lemmas 5.2 and 5.3**

#### **Lemma 5.2: NOT A GAP**

**[Claim Level: Empirical Observation — primary-source inspection]**

I located the published 2023 version of Galesi, Itsykson, Riazanov and Sofronova's paper, rather than relying exclusively on its earlier ECCC version.

The published paper explicitly permits parallel edges and excludes loops. Its vertex-suppression operation also permits creating parallel edges. Lemma 30 states the required topological-minor monotonicity result for connected contradictions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://fileserver-az.core.ac.uk\&sz=32)

fileserver-az.core.ac.uk+1



Thus the multigraph scope objection to Lemma 5.2 can be closed.

There are, however, two proof transcription issues discussed in Section 2 below.

#### **Lemma 5.3: scope clarified through reduction**

**[Claim Level: Proved]**

Let \\(\bar G\\) be the underlying simple graph of a loopless multigraph \\(G\\), retaining one representative of each parallel-edge class.

Then:

\\[ \operatorname{tw}(\bar G)=\operatorname{tw}(G). \\]

This holds because a tree decomposition must cover adjacent endpoint pairs; parallel copies do not impose additional bag requirements.

Apply de Colnet and Mengel's Lemma 12 to \\(\bar G\\). It supplies a 3-vertex-connected topological minor \\(K\\) of the same treewidth.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arxiv.org\&sz=32)

arxiv.org



Since \\(\bar G\\) is a subgraph of \\(G\\), every subdivision witnessing that \\(K\\) is a topological minor of \\(\bar G\\) also witnesses that it is a topological minor of \\(G\\).

Therefore,

\\[ \operatorname{tw}(K)=\operatorname{tw}(G). \\]

Alternatively, for the resolution argument, assign all excess parallel-edge variables zero. The restriction retains the original charges and produces the Tseitin contradiction on \\(\bar G\\). Resolution restriction monotonicity then gives

\\[ S(T(G,c))\ge S(T(\bar G,c)). \\]

That is sufficient to transfer the lower bound.

## **2. Additional findings in the Theorem 1.1 and 1.4 chains**

I recommend assigning the following new review identifiers.

| Finding      | Target                                 | Disposition        |
| ------------ | -------------------------------------- | ------------------ |
| ACE-TR332-01 | Lemma 5.2 external proof transcription | Repairable         |
| ACE-TR332-02 | Lemma 5.3 external proof construction  | Repairable         |
| ACE-TR332-03 | Proposition 2.14 algorithm dependency  | Verified interface |
| ACE-TR332-04 | Multigraph smoothness claim            | Repairable         |
| ACE-TR332-05 | Theorem 6.1 asymptotic notation        | Minor correction   |
| ACE-TR332-06 | Singleton cases                        | Repairable         |
| ACE-TR332-07 | Distinct used axioms in size bounds    | Verified           |
| ACE-TR332-08 | Satisfiable-component proof search     | Repairable         |

### **ACE-TR332-01 — External Lemma 30 transcription issues**

**Severity: LOW**

**[Claim Level: Empirical Observation — source inspection]**

The published proof of Galesi et al.'s Lemma 30 contains two apparent transcription inconsistencies.

First, its restriction assigns edges outside the retained subgraph, but the displayed residual-charge formula indexes the retained edge set.

The correct formula must sum over the assigned edges:

\\[ c\_\rho(v)=c(v)\oplus \bigoplus\_{\substack{e\notin E'\\\e\ni v}}\rho(x_e). \\]

Second, in the degree-two vertex suppression argument, the proof shifts the charge at one surviving endpoint while complementing the substituted variable incident to the other endpoint. Those operations must refer to the same endpoint.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://fileserver-az.core.ac.uk\&sz=32)

fileserver-az.core.ac.uk



**[Claim Level: Proved]** The correct suppression operation can be written explicitly.

For a path \\(u-v-w\\) whose internal vertex has charge \\(c(v)\\), introduce the suppressed edge variable \\(z\\). Substitute

\\[ x\_{uv}=z\oplus c(v), \qquad x\_{vw}=z. \\]

The equation at \\(v\\) becomes an identity. The charge at \\(u\\) must then become

\\[ c'(u)=c(u)\oplus c(v), \\]

while the charge at \\(w\\) remains unchanged.

The total charge parity is preserved.

Resolution derivations remain valid under this literal substitution after discarding tautologies and retaining appropriate derived subclauses. The proof-line count need not increase.

This supports the intended monotonicity result. The errors are repairable transcription issues, not counterexamples.

### **ACE-TR332-02 — External Lemma 12 construction**

**Severity: LOW**

**[Claim Level: Empirical Observation]** The accessible arXiv version of de Colnet and Mengel's proof contains an imprecise edge-set expression in the construction around a two-vertex separator. Taken literally, it omits the edges attaching the chosen component to the separator.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arxiv.org\&sz=32)

arxiv.org



**[Claim Level: Proved]** The intended graph is

\\[ H=G[C\cup\\{u,v\\}]+uv, \\]

where \\(C\\) is the selected component and \\(uv\\) is added only if absent.

Retain the induced graph on \\(C\cup\\{u,v\\}\\). If the edge \\(uv\\) is absent, obtain it by suppressing an external \\(u\\)-to-\\(v\\) path through another component.

Only one such external path is needed. Other components can be deleted.

The standard clique-sum treewidth argument then establishes preservation of the maximum relevant treewidth. This construction also avoids introducing unwanted parallel copies.

I recommend checking the final journal wording separately, since the issue I inspected occurs in the accessible arXiv version.

### **ACE-TR332-03 — Proposition 2.14: use the branchwidth route**

**Severity: INFO**

**[Claim Level: Empirical Observation — primary-source theorem inspection]**

Gemini correctly raised the need to check the deterministic proof-search interface rather than merely the citation identity.

I checked Alekhnovich and Razborov's Theorem 2.3. It supplies a deterministic algorithm on arbitrary CNFs, returning a regular refutation for UNSAT inputs and a satisfying assignment for SAT inputs. Its Lemma 3.1 also supplies the relevant branch-decomposition approximation algorithm.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://people.cs.uchicago.edu\&sz=32)

people.cs.uchicago.edu



Consequently, the proof need not rely on the unreviewed Broering–Lokam route.

**[Claim Level: Proved]** The branchwidth bridge already established in our Gate C literature review gives

\\[ \operatorname{bw}(H(F)) \le \operatorname{tw}(P(F))+1, \\]

with indexed clause-hyperedge multiplicities preserved.

Combining this with Theorem 2.3 supplies the required deterministic single-exponential dependence on primal treewidth, with polynomial input-processing overhead.

I recommend designating this as the team's primary dependency route for Proposition 2.14.

The external algorithm's complete implementation-level proof was not re-audited here; its theorem interface and applicability were checked.

### **ACE-TR332-04 — Smoothness for loopless multigraphs**

**Severity: LOW**

Gemini identified the reliance on an exact width characterization stated for simple graphs.

**[Claim Level: Proved]** The smoothness discussion does not actually need that exact characterization.

Ordinary variable elimination following a treewidth-bounded elimination ordering of the primal graph produces a resolution refutation with width at most

\\[ \operatorname{tw}(P(F))+1. \\]

Every generated resolvent lies within the corresponding elimination neighborhood, and every input clause's variable support is a primal clique.

For the paper's loopless multigraph encoding,

\\[ P(T(G,c))=L(G), \\]

because parallel edges still represent distinct variables.

Therefore,

\\[ w(T(G,c))\le\operatorname{tw}(L(G))+1. \\]

This provides the width upper bound directly, without extending the simple-graph exact-width theorem beyond its checked assumptions.

The remaining smoothness conclusion still depends on Corollary 8.1 for the bridgeless case.

### **ACE-TR332-05 — Equality versus upper bound on page 19**

**Severity: LOW**

**[Claim Level: Proved]**

The expander-gadget simulation establishes

\\[ S_H\le S\\,2^{O(\Delta)}. \\]

It follows that

\\[ \log_2(S_H+1) \le O(\log_2(S+1)+\Delta). \\]

It does not establish a two-sided equality between the growth rates.

The chain on page 19 should be interpreted entirely as an upper-bound chain. The conclusion of Theorem 6.1 remains valid with that correction.

I checked the separator-transfer argument itself: it works for every induced subgraph of the original line graph, and then for arbitrary subgraphs by deleting edges. That is the necessary quantifier for applying Dvořák–Norin's separation-number theorem.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://eccc.weizmann.ac.il\&sz=32)

eccc.weizmann.ac.il+1



I also verified the current arXiv version of Dvořák and Norin's Theorem 1: the constant is indeed 15, under the same balanced-separation convention.

### **ACE-TR332-06 — Singleton edge cases**

**Severity: LOW**

**[Claim Level: Proved]**

I accept Gemini's \\(K_1\\) concern.

Section 6 should begin by disposing of the connected singleton graph before invoking the expander replacement.

For odd charge on \\(K_1\\),

\\[ F=\\{\bot\\},\quad S(F)=1,\quad |F|=1, \\]

and

\\[ \operatorname{tw}(L(K_1))=-1. \\]

Theorem 6.1 is immediate.

Corollary 2.15's input-length calculation can similarly handle the empty-clause encoding separately.

Neither issue affects the general argument.

### **ACE-TR332-07 — Counting used axioms correctly**

**Severity: INFO**

**[Claim Level: Proved]**

The statement \\(S(T(G,c))\ge |V(G)|\\) deserves an explicit check because the paper counts only used clauses and identifies CNFs with sets of clauses.

For each vertex \\(v\\), Corollary 2.12 supplies an assignment satisfying every other vertex equation. Consequently, any refutation must use a clause falsified by that assignment from \\(v\\)'s local block.

That clause cannot simultaneously belong to another vertex's satisfied block.

Thus the necessary clauses associated with distinct vertices are distinct, establishing

\\[ S(T(G,c))\ge |V(G)|. \\]

This argument works even when parallel edges cause multiple vertices to have identical variable supports.

It will also be important in Section 8.

### **ACE-TR332-08 — Running proof search on satisfiable components**

**Severity: LOW**

**[Claim Level: Proved]**

Gemini's promise-algorithm concern is resolved directly by choosing the Alekhnovich–Razborov algorithm from ACE-TR332-03.

It explicitly handles SAT inputs.

A deterministic scheduler can advance each component search one step per round, discard completed SAT searches, and terminate upon receiving a valid regular refutation.

Suppose the original proof-search instance has \\(r\\) components. If an unsatisfiable component completes in time \\(t\\), round-robin scheduling incurs at most polynomial overhead in \\(r\\) and \\(t\\).

There is no requirement to wait for every component to finish.

For additional robustness, verify any returned refutation before accepting it. Regularity can also be checked in polynomial time using the proof DAG's pivot labels.

This preserves the target output-sensitive runtime.

## **3. Overall proof-chain assessment**

### **Theorem 1.1 dependency chain**

**Spanning-tree packing**

External classical theorem; applicable multigraph scope

**Frog lemma**

Repair supported

**Tree exchange**

Argument checked

**Proposition 4.1**

\\(\Pr[B\subseteq T]\le(2/3)^{|B|}\\)

**Weighted cut + random restrictions**

Lemma 3.2 and Theorem 3.3

Core argument checked

**Theorem 5.1**

Exponential resolution lower bound on 3-edge-connected graphs

**Topological-minor transfer**

Lemmas 5.2 and 5.3; external proof clarifications required

**Theorem 1.1**

\\[ S(T(G,c))\ge2^{\Omega(\operatorname{tw}(G))} \\]

Provisionally accepted; technical audit remains OPEN

The proof of the random-restriction theorem is particularly convincing. I independently checked both probability cases.

The narrow-clause argument correctly conditions on the chosen spanning tree before enumerating candidate cuts. Removing at most \\(|A|\\) edges from a tree gives at most \\(|A|+1\\) components, so the candidate family is bounded by

\\[ 2^{|A|+1}. \\]

Each eligible balanced cut then requires at least \\(b-|A|\\) additional edges to be assigned. The conditional independence needed for that probability estimate is present.

I found no invalid independence assumption in this part of the proof.

For the spanning-tree packing premise, I also checked Kaiser's statement of the Tutte–Nash-Williams theorem, including its multigraph convention. The required edge-connectivity consequence follows by summing the cut sizes of the parts of a vertex partition.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://arxiv.org\&sz=32)

arxiv.org



### **Theorem 1.4 dependency chain**

**Theorem 1.1**

**Bounded-degree expander replacement**

Lemma 6.4 — transfers the treewidth parameter

**Theorem 6.1**

\\[ S(F)+|F|\ge 2^{\Omega(k)} \\]

k = line-graph treewidth

**Deterministic regular proof search**

\\[ \ell(F)^{O(1)}2^{O(k)} \\]

Alekhnovich–Razborov route

**Theorem 1.4**

\\[ \text{Runtime}\le(\ell(F)+S(F))^{O(1)} \\]

Provisionally accepted; technical audit remains OPEN

**[Claim Level: Empirical Observation — independent proof review]** I did not find a fatal gap in either central chain. The remaining objections are localized and have plausible or explicit repairs.

That is stronger than merely confirming the bibliography, but it is not a claim that I independently reproved every cited external theorem.

## **4. Recommended Lean formalization for Phase 5**

### **My first choice: Lemma 4.4 — finite-horizon frog inequality**

This is the strongest small formalization target in the paper.

It is mathematically meaningful, largely independent of graph-theory infrastructure, and directly supports the novel spanning-tree argument.

I would deliberately avoid starting with measure theory or the full spanning-tree process.

Instead, represent the process as a finite binary decision tree, allowing each node's move to depend arbitrarily on its preceding history.

### **Exact theorem statement**

**[Claim Level: Proved — mathematical statement; not yet Lean-Verified]**

Let there be \\(k\\) frogs, each starting at position one or two. Consider any adaptive strategy of length \\(d\\), with each internal decision selecting one legal operation:

- A single active frog moves left or right.
- Two distinct active frogs move in opposite directions.
- All frogs remain stationary.

Each orientation is determined by an independent fair coin. Positions zero and three are absorbing.

Then the number of length-\\(d\\) coin histories ending with every frog at position three satisfies

\\[ \boxed{ 3^k\\, \\#\\{\text{successful histories}\\} \le 2^{d+k}. } \\]

Dividing by \\(2^d3^k\\) gives precisely

\\[ \Pr[\text{success by horizon }d] \le\left(\frac23\right)^k. \\]

The integer formulation avoids probability measures, real-valued division and limiting arguments entirely.

### **Proposed Lean implementation**

```
-- lean/Millennium/FrogBound.lean
-- Proposed theorem interface only; not compiled.

abbrev FrogState (k : Nat) := Fin k → Fin 4

def potential (s : FrogState k) : Nat :=
  ∏ i : Fin k, (s i).val
```

The proof should establish the following hierarchy:

| Module component              | Mathematical obligation                               | Estimated Lean size |
| ----------------------------- | ----------------------------------------------------- | ------------------- |
| State and legal moves         | Active frogs move within bounds                       | 40–70 lines         |
| One-step potential inequality | Sum of successor potentials ≤ twice current potential | 50–100 lines        |
| Adaptive binary process       | Legal move selected separately at each history        | 30–60 lines         |
| Finite-horizon induction      | Sum of terminal potentials ≤ \\(2^dP_0\\)             | 40–80 lines         |
| Success-count bound           | Successful terminal states contribute \\(3^k\\) each  | 30–60 lines         |
| Tests and axiom audit         | Boundary cases and permitted axioms                   | 30–50 lines         |

**Estimated total: 220–420 lines of Lean.**

**[Claim Level: Conjecture — engineering estimate]** Actual size will depend on the Mathlib APIs and how much finite-product infrastructure we can reuse.

The full infinite-horizon theorem can be added later using continuity of probability over increasing events.

### **Why this target matters**

The proof's key invariant is simple:

\\[ P(s)=\prod_i s_i. \\]

For every legal move with successors \\(s_0,s_1\\),

\\[ P(s_0)+P(s_1)\le2P(s). \\]

Induction on the depth of the binary tree gives the result for arbitrary adaptive strategies.

Formalizing this stronger finite-history version also addresses Gemini's filtration and stuttering objection directly.

### **Executed independent finite check**

I implemented an exact rational-arithmetic dynamic program that maximizes the success probability over every available legal move at each state.

It considers both single-frog moves, all distinct active-frog pairs, and stuttering. It recursively chooses the best subsequent move separately after each coin outcome.

# **270/270 checks passed**

Exact rational arithmetic — no Monte Carlo sampling

Frogs

## **1–4**

Horizons

## **0–8**

Cached subproblems

## **2,039**

All initial position vectors in the tested dimensions were included.

**[Claim Level: Empirical Observation — independently executed]**

Every tested optimal adaptive success probability satisfied the proposed bound.

This is stronger as a finite sanity check than simulating a fixed policy, because the dynamic program searches for the best permissible adaptive strategy. It is still not a proof for unbounded dimensions or horizons.

No Lean formalization was executed.

### **Second formalization target**

I would subsequently formalize the degree-two suppression identity used in Lemma 5.2, building directly on `Millennium.Tseitin` and `ZMod 2`.

The local algebraic identity is considerably smaller, perhaps 30–80 lines before introducing CNF substitution semantics. A full resolution-proof substitution theorem would be a separate, substantially larger task.

## **5. Who should review Section 8 next?**

I recommend **Gemini as primary reviewer, Ace as independent mathematical reviewer, and Dee as adversarial fixture designer.**

Claude could later review a proof-checking implementation if we decide to implement the bridge-tree construction.

### **Section 8.1 — Corollary 8.1**

**[Claim Level: Proved — preliminary derivation checked]**

The central observation is that deleting a maximum-degree vertex \\(v\\) creates \\(r\\) components, each connected back to \\(v\\) by at least two edges because the graph has no bridges.

Therefore,

\\[ r\le\Delta/2. \\]

The boundary assignments satisfying the component parity constraints form an affine system of \\(r\\) independent equations on \\(\Delta\\) variables. There are exactly

\\[ 2^{\Delta-r} \\]

such assignments.

Every one extends to an assignment satisfying all vertex equations outside \\(v\\). Odd global charge forces the remaining equation at \\(v\\) to fail.

Each distinct boundary assignment falsifies a distinct local clause. Hence every refutation must use all those clauses.

The resulting bound is

\\[ S(T(G,c))\ge2^{\Delta-r} \ge2^{\Delta/2}. \\]

The argument appears sound under the stated bridgeless, loopless multigraph assumptions. The formal Section 8 audit should verify every dependency and explicitly preserve the used-clause convention.&#x20;

TR26-332.pdf



### **Section 8.2 — The bridge-tree regular proof construction**

This is the most important remaining proof to attack.

Conceptual bridge-tree proof: leaf components derive forced unit clauses, which simplify their parent components.

The critical review question is not simply whether the composed proof derives the empty clause.

It is whether the composed proof remains **regular along every path in its derivation DAG**.

Gemini should inspect the following obligations.

| Audit target              | Required check                                                                                                                                        |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| Bridge-tree decomposition | Each nontrivial component after bridge deletion is bridgeless                                                                                         |
| Charge restriction        | Every non-root component receives even residual charge when isolating an odd target                                                                   |
| Unit-clause lifting       | Adding the forced bridge literal to the local refutation yields a valid unit derivation                                                               |
| Input-clause accounting   | Only required local axioms are constructed; no exponential enumeration of unused clauses                                                              |
| Local regularity          | Internal pivots remain regular after lifting                                                                                                          |
| Global regularity         | No proof path resolves on a bridge variable twice                                                                                                     |
| DAG reuse                 | Unit derivations are shared rather than exponentially duplicated                                                                                      |
| Polynomial exponent       | The exponent is absolute and independent of graph size and maximum degree                                                                             |
| Disconnected formulas     | Minimum refutation complexity equals that of a hardest-needed single unsatisfiable component — specifically the minimum over unsatisfiable components |
| Boundary cases            | Singleton components, parallel edges, stars and empty clauses                                                                                         |

### **Particularly important adversarial graph families**

Dee should construct stars, long paths, high-degree bridge trees, chains of bridgeless components, parallel-edge pairs and disconnected collections of easy and hard Tseitin contradictions.

The **high-degree bridge tree** is especially important because its expanded input formula can be exponentially larger than its shortest refutation.

Theorem 8.2 claims a polynomial relationship involving proof size alone. Accidentally introducing a factor polynomial in the expanded input size would weaken the theorem substantially.

**[Claim Level: Conjecture — review priority]** This proof-size bookkeeping and global regularity argument is the highest-value remaining attack surface in Section 8.

## **6. Final claim and adoption ledger**

| Result                               | Second-review status                                       | Project adoption                       |
| ------------------------------------ | ---------------------------------------------------------- | -------------------------------------- |
| Lemma 4.4, finite-horizon inequality | Independently derived; finite tests passed                 | Mathematical repair supported          |
| Proposition 4.1                      | Core argument checked                                      | External dependency acceptance pending |
| Theorem 3.3                          | Core argument checked; explicit exponent supplied          | Provisionally accepted                 |
| Theorem 1.1                          | No fatal gap found                                         | OPEN                                   |
| Theorem 1.2                          | Expander reduction checked with repairs                    | OPEN                                   |
| Theorem 1.4                          | Proof-search chain checked with preferred dependency route | OPEN                                   |
| Corollary 1.3                        | Preliminary mathematical check                             | Full Section 8 review pending          |
| Theorem 1.5                          | Dependency and risk inspection only                        | Full Section 8 review pending          |
| Lean formalization of Lemma 4.4      | Proposed                                                   | Not executed                           |

The executed finite checks are **Empirical Observation**. The explicit elementary repairs and derived inequalities are **Proved** mathematical arguments submitted for team review. The formalization estimates and proposed future research benefits are **Conjecture**. Nothing newly formalized here is **Lean-Verified**.

## **My recommendation to Lumi**

Open the Phase 5 formalization lane under:

```
lean/Millennium/FrogBound.lean
```

Assign it to Ace, with Gemini as independent reviewer.

In parallel, assign Gemini the full Section 8 audit and Dee the bridge-tree adversarial fixtures. Keep the preprint's technical adoption OPEN until the two review records are reconciled and the outstanding external dependency obligations are accepted.

For this response, I opened both attachments, extracted and inspected the paper's proof text, inspected relevant rendered pages, checked selected primary external theorem interfaces, and executed the 270 finite rational-arithmetic tests. Two external PDF screenshot requests failed, though relevant textual material was available. I did not execute Lean, reprove every external theorem, access confirmatory experimental outcomes, or modify the repository.

**This review does not change the Phase 4 Gate B/D authorization decision.**

The Phase 5 theory work can continue independently.

— **Ace | Galactic AI Team | Operation Millennium**