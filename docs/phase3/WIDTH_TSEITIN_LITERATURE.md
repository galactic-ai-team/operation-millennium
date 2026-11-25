# Graph Width, Tseitin Contradictions, and Restricted Proof Complexity

> **Document:** `docs/phase3/WIDTH_TSEITIN_LITERATURE.md`  
> **Phase / Round:** Phase 3 — Discovery Round 01 (Target branch: `dev`)  
> **Claim Labels (per `docs/RULES.md`):** `[Proved]`, `[Conjecture]`, `[Empirical Observation]`, `[Lean-Verified]`  
> **Citation Audit Convention:** Identifiers marked `[VERIFY]` require primary-record confirmation against Crossref / arXiv / ECCC before merging to `main`.

---

## 1. Scope & Notation

Let $G = (V, E)$ be a finite undirected graph with maximum degree $\Delta = \Delta(G)$, treewidth $\mathrm{tw}(G)$, branchwidth $\mathrm{bw}(G)$, and balanced edge expansion
$$e(G) = \min \left\{ |E(U, V \setminus U)| : \tfrac{|V|}{3} \le |U| \le \tfrac{2|V|}{3} \right\}.$$

Given a charge function $f : V \to \{0, 1\}$, the **Tseitin formula** $\mathrm{Tseitin}(G, f)$ has one Boolean variable $x_e$ per edge $e \in E$ and, for every vertex $v \in V$ of degree $d(v)$, the $2^{d(v)-1}$ clauses of width $d(v)$ encoding the parity constraint
$$\bigoplus_{e \ni v} x_e = f(v).$$
$\mathrm{Tseitin}(G, f)$ is unsatisfiable if and only if some connected component $C \subseteq V$ has odd total charge $\sum_{v \in C} f(v) \equiv 1 \pmod 2$ `[Proved]`.

### Graph Representations Used Across This Literature
Because width parameters depend critically on *which* graph is measured, every theorem below specifies one of four representations:

1. **Underlying Tseitin graph $G = (V, E)$:** Vertices are parity constraints; edges are Boolean variables.
2. **Primal (Gaifman) graph $G_P(F)$:** Vertices are variables $\mathrm{Var}(F)$; edges join variables co-occurring in at least one clause. For $\mathrm{Tseitin}(G, f)$ (with $d(v) \ge 2$), $G_P(\mathrm{Tseitin}(G, f)) = L(G)$, the **line graph** of $G$, satisfying $\Delta - 1 \le \mathrm{tw}(L(G)) \le \Delta(\mathrm{tw}(G) + 1) - 1$ `[Proved]`.
3. **Incidence graph $G_I(F)$:** Bipartite graph on $\mathrm{Var}(F) \cup \mathrm{Clauses}(F)$ with edges $\{x, C\}$ whenever $x$ or $\neg x$ occurs in $C$. Always satisfies $\mathrm{tw}(G_I(F)) \le \mathrm{tw}(G_P(F)) + 1$ `[Proved]`.
4. **Clause-variable hypergraph $H(F)$:** Vertices are clauses (or variables) and hyperedges encode incidence; used with branchwidth $\mathrm{bw}(H(F))$, where $\mathrm{bw} - 1 \le \mathrm{tw} \le \lfloor \frac{3}{2}\mathrm{bw} \rfloor - 1$ for $\mathrm{bw} \ge 2$ `[Proved]` (Robertson & Seymour, 1991).

For an unsatisfiable CNF $F$ on $n$ variables:
- $w(F)$ = maximum width (number of literals) of an initial clause in $F$.
- $w(F \vdash \bot)$ = minimum width of a general Resolution refutation of $F$.
- $S_T(F), S_R(F), S(F)$ = minimum number of clauses (size) of a **tree-like**, **regular**, and **general (DAG-like)** Resolution refutation of $F$, respectively.

---

## 2. Auditable Theorem Summary Table

| ID | Topic / Theorem | Proof System / Model | Graph Representation | Bound Type & Formula | Claim Level | Primary Citation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **T1** | BSW Tree-like Size–Width | Tree-like Resolution | Arbitrary CNF (no graph) | **Lower:** $S_T(F) \ge 2^{w(F \vdash \bot) - w(F)}$ | `[Proved]` | Ben-Sasson & Wigderson (2001) |
| **T2** | BSW General Size–Width | General (DAG) Resolution | Arbitrary CNF (no graph) | **Lower:** $S(F) = \exp\!\left(\Omega\!\left(\frac{(w(F \vdash \bot) - w(F))^2}{n}\right)\right)$ | `[Proved]` | Ben-Sasson & Wigderson (2001) |
| **T3** | Optimality of BSW Tradeoff | General Resolution | Ordering principle $GT_n$ (tournament) | **Upper / Lower:** $S(GT_n) = O(n^3)$ yet $w(GT_n \vdash \bot) = \Omega(\sqrt{n})$ | `[Proved]` | Bonet & Galesi (2001) |
| **T4** | Width–Pebble Game Equivalence | General Resolution (width) | Incidence / relational structure | **Exact:** $w(F \vdash \bot) = k \iff$ Spoiler wins existential $(k+1)$-pebble game | `[Proved]` | Atserias & Dalmau (2008) |
| **T5** | Treewidth SAT / #SAT (Primal & Incidence) | Deterministic RAM (DP on tree decomp.) | $G_P(F)$ and $G_I(F)$ | **Upper:** $O^*(2^{\mathrm{tw}(G_P)})$ and $O^*(4^{\mathrm{tw}(G_I)})$ | `[Proved]` | Samer & Szeider (2010) |
| **T6** | #SAT via DPLL + Caching | DPLL with component/formula caching | $G_P(F)$ / $H(F)$ branchwidth | **Upper:** $n^{O(1)} \cdot 2^{O(\mathrm{bw}(F))}$ | `[Proved]` | Bacchus, Dalmao, & Pitassi (2009) |
| **T7** | SETH Tightness for Primal Treewidth SAT | Deterministic/Randomized RAM | $G_P(F)$ | **Conditional Lower:** No $(2-\varepsilon)^{\mathrm{tw}(G_P)}\mathrm{poly}(|F|)$ SAT algorithm under SETH | `[Proved]` (conditional on `[Conjecture]` SETH) | Impagliazzo–Paturi (2001); Lokshtanov–Marx–Saurabh (2018) |
| **T8** | Tseitin Regular Resolution Lower Bound | Regular Resolution | Underlying graph $G$ (2D grids / general) | **Lower:** $S_R(\mathrm{Tseitin}(G_{k \times k}, f)) = 2^{\Omega(k)}$ | `[Proved]` | Tseitin (1968) |
| **T9** | Tseitin General Resolution on Expanders | General Resolution | Underlying $d$-regular expander $G$ | **Lower:** $S(\mathrm{Tseitin}(G, f)) = 2^{\Omega(|V|)}$ | `[Proved]` | Urquhart (1987) |
| **T10** | BSW Tseitin Width & Size via Expansion | General Resolution | Underlying graph $G$ of max degree $\Delta$ | **Lower:** $w \ge e(G)$; $S = \exp\!\left(\Omega\!\left(\frac{(e(G)-\Delta)^2}{|E|}\right)\right)$ | `[Proved]` | Ben-Sasson & Wigderson (2001) |
| **T11** | Branchwidth / Treewidth & Tseitin Resolution | General & Tree-like Resolution | Underlying $G$ / hypergraph $H(F)$ | **Upper:** $S \le 2^{O(\mathrm{bw})} \mathrm{poly}(|F|)$; **Lower:** $w = \Omega(\mathrm{tw}(G))$, $S_T = 2^{\Omega(\mathrm{tw}(G))}$ (const. $\Delta$) | `[Proved]` | Alekhnovich & Razborov (2002 / 2011) |
| **T12** | Tseitin Width Characterized by Treewidth | General Resolution (width) | Underlying graph $G$ | **Tight (up to $\Delta$):** $\mathrm{tw}(G) \le w(\mathrm{Tseitin}(G,f) \vdash \bot) \le \mathrm{tw}(G) + \Delta$ (via cops-and-robber) `[VERIFY exact additive term]` | `[Proved]` | Galesi, Talebanfard, & Torán (2019 / 2020) |
| **T13** | Tree-like vs. Regular Resolution Separation | Tree-like vs. Regular Resolution | Pebbling DAGs $G$ | **Upper (Reg):** $O(n)$; **Lower (Tree):** $\exp(\Omega(n/\log n))$ | `[Proved]` | Bonet et al. (2000); Ben-Sasson–Impagliazzo–Wigderson (2004) |
| **T14** | Regular vs. General Resolution Separation | Regular vs. General Resolution | Modified ordering / pebbling CNFs | **Upper (Gen):** $\mathrm{poly}(n)$; **Lower (Reg):** $2^{\Omega(n/\log n)}$ (or $2^{\Omega(n^\varepsilon)}$) | `[Proved]` | Goerdt (1993); Alekhnovich et al. (2007); Urquhart (2011) |
| **T15** | CDCL / DRUP vs. General Resolution | CDCL (with restarts) / DRUP | Arbitrary CNF | **Polynomial Equivalence:** Idealized CDCL $\equiv_p$ General Resolution | `[Proved]` | Pipatsrisawat & Darwiche (2011); Atserias–Fichte–Thurley (2011) |
| **T16** | DRAT vs. Extended Resolution | DRAT / Extended Resolution (ER) | Arbitrary CNF | **Polynomial Equivalence:** DRAT $\equiv_p$ Extended Resolution | `[Proved]` | Kiesl, Rebola-Pardo, & Heule (2018) |
| **T17** | Gaussian Elimination & Component Parity | RAM / $\oplus\mathrm{L}$ / $\mathrm{L}$ | Incidence matrix $A \in \mathbb{F}_2^{|V|\times|E|}$ / graph $G$ | **Upper:** $O(|V|^3)$ (Gauss) and $O(|V|+|E|)$ (component parity) | `[Proved]` | Folklore / Reingold (2008) for $\mathrm{L}$ |
| **T18** | Polynomial Calculus over $\mathbb{F}_2$ vs. $\mathbb{F}_p$ ($p \neq 2$) | Polynomial Calculus (PC) | Underlying graph $G$ | **Upper ($\mathbb{F}_2$):** deg $1$, size $O(|V|+|E|)$; **Lower ($\text{char}\neq 2$):** deg $\Omega(|V|)$ on expanders | `[Proved]` | Clegg–Edmonds–Impagliazzo (1996); Grigoriev (1998); Buss et al. (2001) |
| **T19** | $\mathrm{Res}(\oplus)$ and Extended Resolution on Tseitin | $\mathrm{Res}(\oplus)$; Extended Resolution; Frege | Underlying graph $G$ | **Upper:** $O(|V|+|E|)$ in $\mathrm{Res}(\oplus)$; $\mathrm{poly}(|V|, 2^\Delta)$ in ER and Frege | `[Proved]` | Itsykson & Sokolov (2020); Cook & Reckhow (1979) |

---

## 3. Detailed Theorem Records

### 3.1 Ben-Sasson & Wigderson Resolution Width/Size Results

#### **T1 & T2 — Size–Width Tradeoffs for Tree-like and General Resolution `[Proved]`**
* **Exact proof system:** Tree-like Resolution (T1) and Unrestricted DAG-like Resolution (T2).
* **Graph representation:** None (applies to any unsatisfiable CNF formula $F$).
* **Quantifiers & parameters:** For every unsatisfiable CNF $F$ over $n$ Boolean variables with initial clause width $w(F)$, minimum general Resolution refutation width $w(F \vdash \bot)$, tree-like refutation size $S_T(F)$, and general refutation size $S(F)$:
  - **(T1, Tree-like):** $S_T(F) \ge 2^{w(F \vdash \bot) - w(F)}$.
  - **(T2, General):** $S(F) = \exp\!\left(\Omega\!\left(\frac{(w(F \vdash \bot) - w(F))^2}{n}\right)\right)$.
* **Upper vs. lower bound:** Lower bounds on proof size in terms of refutation width (equivalently, upper bounds on width in terms of size: $w(F \vdash \bot) \le w(F) + \log_2 S_T(F)$ and $w(F \vdash \bot) \le w(F) + O(\sqrt{n \ln S(F)})$).
* **Assumptions:** $F$ is an unsatisfiable CNF on $n$ variables.
* **Primary-source citation:** Eli Ben-Sasson and Avi Wigderson, "Short Proofs Are Narrow—Resolution Made Simple," *Journal of the ACM (JACM)*, Vol. 48, No. 2, pp. 149–169, 2001 (preliminary: *STOC 1999*, pp. 517–526). DOI: `10.1145/375827.375835` `[VERIFY]`; ECCC TR99-022 `[VERIFY]`.
* **What it does NOT establish:**
  - **The $\sqrt{n}$ barrier:** Whenever $w(F \vdash \bot) = O(\sqrt{n})$, T2 yields only a **trivial $O(1)$ lower bound** on general Resolution size. In particular, T2 alone fails to prove super-polynomial general Resolution lower bounds for Tseitin formulas on 2D grids (where $n = \Theta(k^2)$ and width is $\Theta(k) = \Theta(\sqrt{n})$).
  - Does not imply that small width guarantees polynomial size (width $w$ only guarantees $S(F) \le O((2n)^w)$).
  - Does not apply to proof systems stronger than Resolution (e.g., $\mathrm{Res}(\oplus)$, Polynomial Calculus, Cutting Planes, Extended Resolution, DRAT).

#### **T3 — Optimality of the BSW Size–Width Tradeoff `[Proved]`**
* **Exact proof system:** General Resolution.
* **Graph representation:** Complete directed graph / ordering axioms $GT_n$ (on $\binom{n}{2}$ variables encoding a strict linear order on $n$ elements without a minimal element).
* **Quantifiers & parameters:** For all $n \ge 3$, $N = \Theta(n^2)$ variables; $S(GT_n) = O(n^3)$ while $w(GT_n \vdash \bot) = \Omega(n) = \Omega(\sqrt{N})$.
* **Upper vs. lower bound:** Simultaneous polynomial size upper bound and $\Omega(\sqrt{N})$ width lower bound.
* **Assumptions:** Standard 3-CNF / bounded-width encoding of $GT_n$.
* **Primary-source citation:** Maria Luisa Bonet and Nicola Galesi, "Optimality of Size-Width Tradeoffs for Resolution," *Computational Complexity*, Vol. 10, No. 4, pp. 261–276, 2001 (preliminary: *FOCS 1999*, pp. 422–431). DOI: `10.1007/s000370100000` `[VERIFY]`.
* **What it does NOT establish:** Does not rule out super-polynomial lower bounds for specific formulas of width $\Theta(\sqrt{N})$ (such as Tseitin on grids) via *non-width* techniques; it only proves that width alone cannot force super-polynomial size at the $\Theta(\sqrt{N})$ threshold.

#### **T4 — Combinatorial Characterization of Resolution Width `[Proved]`**
* **Exact proof system:** General Resolution (refutation width).
* **Graph representation:** Relational / incidence structure of CNF $F$.
* **Quantifiers & parameters:** For every unsatisfiable CNF $F$ and integer $k \ge w(F)$, $w(F \vdash \bot) \le k$ if and only if Duplicator has no winning strategy in the existential $(k+1)$-pebble game on $F$ (equivalently, no non-empty family $\mathcal{H}$ of partial truth assignments of size $\le k$ closed under restrictions and single-variable extensions that falsify no clause of $F$).
* **Upper vs. lower bound:** Exact characterization (both upper and lower bound on width).
* **Assumptions:** None beyond $F$ being an unsatisfiable CNF.
* **Primary-source citation:** Albert Atserias and Víctor Dalmau, "A Combinatorial Characterization of Resolution Width," *Journal of Computer and System Sciences (JCSS)*, Vol. 74, No. 3, pp. 323–334, 2008 (preliminary: *CCC 2003*, pp. 239–245). DOI: `10.1016/j.jcss.2007.06.025` `[VERIFY]`.
* **What it does NOT establish:** Characterizes refutation *width*, not refutation *size* or CDCL runtime.

---

### 3.2 Treewidth-Parameterized SAT and Model-Counting (#SAT) Algorithms

#### **T5 — Fixed-Parameter Tractable SAT and #SAT via Primal and Incidence Treewidth `[Proved]`**
* **Exact computational model:** Deterministic RAM executing dynamic programming over a nice tree decomposition.
* **Graph representation:** Primal graph $G_P(F)$ and incidence graph $G_I(F)$.
* **Quantifiers & parameters:** For any CNF $F$ with $n$ variables, $m$ clauses, and total length $|F|$:
  - Given a tree decomposition of $G_P(F)$ of width $k = \mathrm{tw}(G_P(F))$, both SAT and #SAT are solved in time $O(2^k \cdot k \cdot (n + m))$ (i.e., $O^*(2^k)$).
  - Given a tree decomposition of $G_I(F)$ of width $k = \mathrm{tw}(G_I(F))$, both SAT and #SAT are solved in time $O(4^k \cdot k \cdot |F|)$ (i.e., $O^*(4^k)$).
* **Upper vs. lower bound:** Algorithmic upper bounds.
* **Assumptions:** A width-$k$ tree decomposition is provided (or precomputed; computing exact $\mathrm{tw}$ is NP-hard, though FPT in $k$ via Bodlaender 1996 in $2^{O(k^3)} n$ time, or constant-factor approximated in $2^{O(k)} n$ time).
* **Primary-source citation:** Marko Samer and Stefan Szeider, "Algorithms for Propositional Model Counting," *Journal of Discrete Algorithms*, Vol. 8, No. 1, pp. 50–64, 2010. DOI: `10.1016/j.jda.2009.06.002` `[VERIFY]`. (See also Stefan Szeider, "On Fixed-Parameter Tractable Parameterizations of SAT," *SAT 2003*, LNCS 2919, pp. 188–202, DOI: `10.1007/978-3-540-24605-3_15` `[VERIFY]`.)
* **What it does NOT establish:**
  - Does not give polynomial-time algorithms when $\mathrm{tw} = \omega(\log |F|)$.
  - Does not imply that generic CDCL solvers automatically achieve $O^*(2^{\mathrm{tw}})$ time (CDCL heuristics do not compute tree decompositions).
  - Does not imply that high treewidth forces *algorithmic* hardness for special CNF subclasses such as Tseitin (which is in $\mathrm{P}$ via Gaussian elimination).

#### **T6 — #SAT via Backtracking Search (DPLL) with Formula/Component Caching `[Proved]`**
* **Exact computational model:** DPLL backtracking search augmented with component / formula caching.
* **Graph representation:** Hypergraph $H(F)$ / primal graph $G_P(F)$ via branchwidth $\mathrm{bw}(F)$.
* **Quantifiers & parameters:** For any CNF $F$ on $n$ variables with branchwidth $b = \mathrm{bw}(F)$, #SAT (and SAT) can be solved in time $n^{O(1)} \cdot 2^{O(b)}$ (and space $n^{O(1)} \cdot 2^{O(b)}$).
* **Upper vs. lower bound:** Algorithmic upper bound.
* **Assumptions:** Variable branching order is guided by an appropriate branch decomposition of width $O(b)$.
* **Primary-source citation:** Fahiem Bacchus, Shannon Dalmao, and Toniann Pitassi, "Solving #SAT and Bayesian Inference with Backtracking Search," *Journal of Artificial Intelligence Research (JAIR)*, Vol. 34, pp. 391–442, 2009 (preliminary: *FOCS 2003*, pp. 340–351). DOI: `10.1613/jair.2648` `[VERIFY]`.
* **What it does NOT establish:** Does not apply without caching (plain DPLL without caching / clause learning corresponds to tree-like Resolution and cannot exploit shared subproblems without re-solving); does not remove the exponential dependence on branchwidth.

#### **T7 — SETH-Conditional Optimality of $2^{\mathrm{tw}}$ for General SAT `[Proved conditional on Conjecture]`**
* **Exact computational model:** Deterministic or randomized RAM.
* **Graph representation:** Primal graph $G_P(F)$.
* **Quantifiers & parameters:** Assuming the Strong Exponential Time Hypothesis (SETH) `[Conjecture]`, there is no $\varepsilon > 0$ such that SAT on CNFs $F$ of primal treewidth $k = \mathrm{tw}(G_P(F))$ can be solved in time $(2 - \varepsilon)^k \cdot \mathrm{poly}(|F|)$ (note: directly implied by $\mathrm{tw}(G_P(F)) \le n$ for arbitrary $n$-variable $k$-CNFs; extended to numerous bounded-treewidth graph problems by Lokshtanov–Marx–Saurabh).
* **Upper vs. lower bound:** Conditional algorithmic lower bound.
* **Assumptions:** SETH holds ($\lim_{k \to \infty} s_k = 1$ for $k$-SAT).
* **Primary-source citations:**
  - Russell Impagliazzo and Ramamohan Paturi, "On the Complexity of $k$-SAT," *JCSS*, Vol. 62, No. 2, pp. 367–375, 2001. DOI: `10.1006/jcss.2000.1727` `[VERIFY]`.
  - Daniel Lokshtanov, Dániel Marx, and Saket Saurabh, "Known Algorithms on Graphs of Bounded Treewidth are Probably Optimal," *ACM Transactions on Algorithms (TALG)*, Vol. 14, No. 2, Article 13, 2018 (preliminary: *SODA 2011*, pp. 777–789). DOI: `10.1145/3170442` `[VERIFY]`.
* **What it does NOT establish:** Unconditional lower bounds; and **critically, does NOT apply to Tseitin formulas** (which are restricted $\mathbb{F}_2$-linear CNFs solvable in polynomial time regardless of treewidth).

---

### 3.3 Tseitin Resolution Lower Bounds & Graph Width Characterizations

#### **T8 — Tseitin's Original Regular Resolution Lower Bound `[Proved]`**
* **Exact proof system:** Regular Resolution (no variable is resolved upon twice along any path in the refutation DAG).
* **Graph representation:** Underlying undirected graph $G = (V, E)$, specifically $k \times k$ 2D grid graphs (and general graphs via edge-cut / expansion parameters).
* **Quantifiers & parameters:** For the $k \times k$ grid $G_{k \times k}$ ($|V| = k^2$, $\Delta = 4$) and any odd-charge function $f$, $S_R(\mathrm{Tseitin}(G_{k \times k}, f)) = 2^{\Omega(k)} = 2^{\Omega(\sqrt{|V|})}$.
* **Upper vs. lower bound:** Lower bound on Regular Resolution size.
* **Assumptions:** Regularity restriction on the refutation; connected graph with odd total charge.
* **Primary-source citation:** G. S. Tseitin, "On the complexity of derivation in propositional calculus," *Studies in Constructive Mathematics and Mathematical Logic, Part II*, Seminars in Mathematics, V. A. Steklov Mathematical Institute, Leningrad, Vol. 8, pp. 115–125, 1968 (English translation: Consultants Bureau, 1970; reprinted in *Automation of Reasoning*, Vol. 2, Springer, 1983, pp. 466–483). DOI (1983 reprint): `10.1007/978-3-642-81955-1_28` `[VERIFY]`.
* **What it does NOT establish:** Does **not** apply to unrestricted (non-regular) general Resolution, nor to CDCL with arbitrary restarts/clause learning, nor to DRAT / Extended Resolution / $\mathrm{Res}(\oplus)$.

#### **T9 — Urquhart's Exponential General Resolution Lower Bound on Expanders `[Proved]`**
* **Exact proof system:** Unrestricted (general DAG-like) Resolution.
* **Graph representation:** Underlying constant-degree $d$-regular expander graph $G = (V, E)$.
* **Quantifiers & parameters:** There exists an infinite family of bounded-degree expander graphs $\{G_m\}$ (with $|V(G_m)| \to \infty$ and $\Delta(G_m) = O(1)$) and a constant $c > 1$ such that for every odd-charge function $f$, $S(\mathrm{Tseitin}(G_m, f)) \ge c^{|V(G_m)|}$.
* **Upper vs. lower bound:** Exponential lower bound on general Resolution size.
* **Assumptions:** $G_m$ has constant maximum degree (keeping formula size $O(|V|)$) and linear edge expansion.
* **Primary-source citation:** Alasdair Urquhart, "Hard Examples for Resolution," *Journal of the ACM (JACM)*, Vol. 34, No. 1, pp. 209–219, 1987. DOI: `10.1145/7531.8928` `[VERIFY]`.
* **What it does NOT establish:** Does not characterize Resolution size on sparse *non-expander* graphs (such as planar graphs or 2D grids); does not hold in proof systems capable of parity reasoning.

#### **T10 — BSW Width and Size Lower Bounds for Tseitin via Edge Expansion `[Proved]`**
* **Exact proof system:** General Resolution (width and size).
* **Graph representation:** Underlying connected undirected graph $G = (V, E)$ of maximum degree $\Delta$ and balanced edge expansion $e(G)$.
* **Quantifiers & parameters:** For every connected graph $G$ and every odd-charge function $f$:
  - $w(\mathrm{Tseitin}(G, f) \vdash \bot) \ge e(G)$.
  - Combining with T2 (with $n = |E| \le \frac{\Delta}{2}|V|$ and $w(\mathrm{Tseitin}(G, f)) = \Delta$):
    $$S(\mathrm{Tseitin}(G, f)) = \exp\!\left(\Omega\!\left(\frac{(e(G) - \Delta)^2}{|E|}\right)\right).$$
* **Upper vs. lower bound:** Lower bounds on width and general Resolution size.
* **Assumptions:** Connected $G$, odd total charge.
* **Primary-source citation:** Eli Ben-Sasson and Avi Wigderson, *JACM* 48(2):149–169, 2001. DOI: `10.1145/375827.375835` `[VERIFY]`.
* **What it does NOT establish:** Whenever $e(G) = O(\sqrt{|E|})$ (e.g., all planar graphs by the Lipton–Tarjan separator theorem, including 2D grids), the size bound degenerates to $\exp(O(1)) = O(1)$ (trivial).

#### **T11 — Branchwidth / Treewidth Upper and Lower Bounds for Tseitin Resolution `[Proved]`**
* **Exact proof system:** General Resolution (upper bound on size, lower bound on width) and Tree-like Resolution (lower bound on size).
* **Graph representation:** Underlying graph $G$ and clause-variable incidence hypergraph $H(F)$ with branchwidth $\mathrm{bw}$.
* **Quantifiers & parameters:**
  - **Upper bound (General Resolution & SAT):** Any unsatisfiable CNF $F$ whose incidence hypergraph has branchwidth $b$ admits a general Resolution refutation of size $2^{O(b)} \cdot \mathrm{poly}(|F|)$ (for $\mathrm{Tseitin}(G, f)$ on a graph $G$ of max degree $\Delta$, size $2^{O(\mathrm{tw}(G) + \Delta)} \cdot \mathrm{poly}(|V|)$ `[VERIFY exact dependence on Delta]`).
  - **Lower bound (Width & Tree-like Size):** For $\mathrm{Tseitin}(G, f)$ on any connected graph $G$ with odd charge, $w(\mathrm{Tseitin}(G, f) \vdash \bot) \ge \Omega(\mathrm{bw}(G)) = \Omega(\mathrm{tw}(G))$; hence for bounded degree $\Delta = O(1)$, tree-like Resolution requires $S_T(\mathrm{Tseitin}(G, f)) = 2^{\Omega(\mathrm{tw}(G))}$.
* **Upper vs. lower bound:** Both upper bound (general Resolution) and lower bound (width and tree-like size).
* **Assumptions:** Odd total charge on a connected component; bounded degree $\Delta = O(1)$ for clean $\mathrm{tw}(G)$ vs. $w(F)$ separation in tree-like lower bound.
* **Primary-source citation:** Michael Alekhnovich and Alexander A. Razborov, "Satisfiability, Branch-width and Tseitin Tautologies," *Computational Complexity*, Vol. 20, No. 4, pp. 649–678, 2011 (preliminary: *FOCS 2002*, pp. 593–603). DOI: `10.1007/s00037-011-0011-7` `[VERIFY]`.
* **What it does NOT establish:** Does **not** prove a $2^{\Omega(\mathrm{tw}(G))}$ lower bound for **unrestricted (general)** Resolution when $\mathrm{tw}(G) = O(\sqrt{|E|})$ (such as 2D grids).

#### **T12 — Tight Characterization of Tseitin Resolution Width via Treewidth & Cops-and-Robber `[Proved]`**
* **Exact proof system:** General Resolution (refutation width).
* **Graph representation:** Underlying connected graph $G = (V, E)$ of max degree $\Delta$ and treewidth $\mathrm{tw}(G)$.
* **Quantifiers & parameters:** For every connected graph $G$ and odd-charge function $f$, $w(\mathrm{Tseitin}(G, f) \vdash \bot)$ is characterized via a cops-and-robber game on $G$, yielding $\mathrm{tw}(G) \le w(\mathrm{Tseitin}(G, f) \vdash \bot) \le \mathrm{tw}(G) + \Delta$ (up to small additive/constant factors depending on whether width counts literals vs. variables) `[VERIFY exact constant/additive term in TOCL version]`.
* **Upper vs. lower bound:** Matching upper and lower bounds on refutation width (tight for constant-degree graphs).
* **Assumptions:** Connected graph $G$, odd total charge.
* **Primary-source citation:** Nicola Galesi, Navid Talebanfard, and Jacobo Torán, "Cops-Robber Games and the Resolution of Tseitin Formulas," *SAT 2019*, LNCS 11628, pp. 311–326, 2019 (journal version: *ACM Transactions on Computational Logic (TOCL)*, 2020 `[VERIFY]`). DOI (SAT 2019): `10.1007/978-3-030-24258-9_22` `[VERIFY]`; ECCC TR18-174 `[VERIFY]`.
* **What it does NOT establish:** Does not resolve general Resolution *size* when $\mathrm{tw}(G) = \Theta(\sqrt{|E|})$ (e.g., 2D grids). Note also that for **regular** Resolution on arbitrary constant-degree graphs, Itsykson, Riazanov, Sagunov, & Smirnov (*SAT 2020* / *MFCS 2020* `[VERIFY exact venue, DOI, and log factor]`) established near-tight $2^{\Omega(\mathrm{tw}(G) / \log |V|)}$ size lower bounds `[VERIFY]`, whereas the analogous lower bound for *unrestricted* Resolution on grids remains open `[Conjecture / VERIFY current status]`.

---

### 3.4 Differences Between Tree-like, Regular, and Unrestricted Resolution (and SAT Solvers)

The three Resolution fragments form a strict polynomial-simulation hierarchy:
$$\text{Tree-like Resolution} \;\subsetneq_p\; \text{Regular Resolution} \;\subsetneq_p\; \text{General (DAG-like) Resolution} \;\subsetneq_p\; \text{Extended Resolution}.$$

#### **T13 — Exponential Separation of Tree-like vs. Regular Resolution `[Proved]`**
* **Exact proof systems:** Tree-like Resolution vs. Regular Resolution.
* **Graph representation:** Bounded-in-degree DAGs $G$ with high black pebbling number, encoded as pebbling contradictions $\mathrm{Peb}_G$ (and lifted/substituted variants).
* **Quantifiers & parameters:** There exist infinite families of unsatisfiable bounded-width CNFs $\{F_n\}$ of size $O(n)$ with $S_R(F_n) = O(n)$ (and hence $S(F_n) = O(n)$), while $S_T(F_n) = \exp(\Omega(n / \log n))$.
* **Upper vs. lower bound:** Linear upper bound in Regular Resolution; near-exponential lower bound in Tree-like Resolution.
* **Assumptions:** Explicit high-pebbling-number DAG families (e.g., Paul–Tarjan–Celoni graphs).
* **Primary-source citations:**
  - Maria Luisa Bonet, Juan Luis Esteban, Nicola Galesi, and Jan Johannsen, "On the Relative Complexity of Resolution Refinements and Cutting Planes Proof Systems," *SIAM Journal on Computing*, Vol. 30, No. 5, pp. 1462–1484, 2000. DOI: `10.1137/S0097539799352474` `[VERIFY]`.
  - Eli Ben-Sasson, Russell Impagliazzo, and Avi Wigderson, "Near Optimal Separation of Tree-Like and General Resolution," *Combinatorica*, Vol. 24, No. 4, pp. 585–603, 2004. DOI: `10.1007/s00493-004-0036-5` `[VERIFY]`; ECCC TR00-005 `[VERIFY]`.
* **What it does NOT establish:** Does not separate Regular from General Resolution, and does not show a super-polynomial gap between Tree-like and Regular Resolution *specifically on Tseitin formulas*.

#### **T14 — Exponential Separation of Regular vs. General Resolution `[Proved]`**
* **Exact proof systems:** Regular Resolution vs. General (unrestricted) Resolution.
* **Graph representation:** Modified Graph Ordering Principle ($GT'_n$) / stone-pebbling CNFs with auxiliary variables preventing regular reuse.
* **Quantifiers & parameters:** There exist infinite families of unsatisfiable CNFs $\{F_n\}$ of size $O(n)$ with $S(F_n) = O(n)$ (polynomial in Alekhnovich et al.; linear in Urquhart 2011), while $S_R(F_n) = 2^{\Omega(\sqrt{n})}$ (Alekhnovich et al.) and $S_R(F_n) = 2^{\Omega(n / \log n)}$ (Urquhart 2011).
* **Upper vs. lower bound:** Polynomial/linear upper bound in General Resolution; exponential lower bound in Regular Resolution.
* **Assumptions:** Carefully constructed ordering/pebbling gadgets (not standard Tseitin formulas).
* **Primary-source citations:**
  - Andreas Goerdt, "Regular Resolution versus Unrestricted Resolution," *SIAM Journal on Computing*, Vol. 22, No. 4, pp. 661–683, 1993 (first super-polynomial separation, $n^{\Omega(\log n)}$). DOI: `10.1137/0222044` `[VERIFY]`.
  - Michael Alekhnovich, Jan Johannsen, Toniann Pitassi, and Alasdair Urquhart, "An Exponential Separation between Regular and General Resolution," *Theory of Computing*, Vol. 3, Article 5, pp. 81–102, 2007 (preliminary: *STOC 2002*, pp. 448–456). DOI: `10.4086/toc.2007.v003a005` `[VERIFY]`.
  - Alasdair Urquhart, "A Near-Optimal Separation of Regular and General Resolution," *SIAM Journal on Computing*, Vol. 40, No. 1, pp. 107–121, 2011. DOI: `10.1137/080744234` `[VERIFY]`.
* **What it does NOT establish:** Does **not** establish whether General Resolution beats Regular Resolution on **Tseitin formulas over 2D grids** (where Regular Resolution requires $2^{\Omega(\sqrt{|V|})}$ by T8, while General Resolution lower bounds remain open).

#### **T15 & T16 — Exact Proof-System Correspondences for Practical SAT Solvers & DRAT `[Proved]`**
* **Exact proof systems / models:**
  - **(T15):** Idealized CDCL (clause learning + restarts + nondeterministic branching) and DRUP proofs vs. **General Resolution**.
  - **(T16):** DRAT (Deletion Resolution Asymmetric Tautology) proofs vs. **Extended Resolution (ER)**.
* **Graph representation:** Arbitrary CNF.
* **Quantifiers & parameters:**
  - **(T15):** General Resolution and idealized CDCL (with restarts) polynomially simulate each other. Every DRUP proof translates in polynomial time to a General Resolution refutation.
  - **(T16):** DRAT and Extended Resolution polynomially simulate each other.
* **Upper vs. lower bound:** Bidirectional polynomial simulations.
* **Assumptions:** T15 assumes nondeterministic branching/restarts (practical deterministic heuristics such as VSIDS can perform exponentially worse than optimal General Resolution on specific formulas); T16 assumes RAT (Resolution Asymmetric Tautology) steps are permitted.
* **Primary-source citations:**
  - Knot Pipatsrisawat and Adnan Darwiche, "On the Power of Clause-Learning SAT Solvers as Resolution Engines," *Artificial Intelligence*, Vol. 175, No. 2, pp. 512–525, 2011. DOI: `10.1016/j.artint.2010.10.002` `[VERIFY]`.
  - Albert Atserias, Johannes Klaus Fichte, and Marc Thurley, "Clause-Learning Algorithms with Many Restarts and Bounded-Width Resolution," *JAIR*, Vol. 40, pp. 353–373, 2011. DOI: `10.1613/jair.3152` `[VERIFY]`.
  - Benjamin Kiesl, Adrián Rebola-Pardo, and Marijn J. H. Heule, "Extended Resolution Simulates DRAT," *IJCAR 2018*, LNCS 10900, pp. 516–531, 2018. DOI: `10.1007/978-3-319-94205-6_34` `[VERIFY]`.
* **What it does NOT establish:**
  - A **DRAT** certificate does **not** certify that a proof lies in General Resolution (if RAT steps are used, the proof may inhabit Extended Resolution, where Tseitin has polynomial-size proofs!).
  - Empirical CDCL solve time / conflict count is only a *heuristic upper bound* on General Resolution size—never a proof of a lower bound.

---

### 3.5 Gaussian Elimination over $\mathbb{F}_2$ and Parity-Aware Proof Systems

#### **T17 — Polynomial / Linear-Time Decidability of Tseitin via $\mathbb{F}_2$-Linear Algebra `[Proved]`**
* **Exact computational model:** Deterministic RAM (and deterministic logspace $\mathrm{L}$ / $\oplus\mathrm{L}$).
* **Graph representation:** Vertex-edge incidence matrix $A \in \mathbb{F}_2^{|V| \times |E|}$ and charge vector $f \in \mathbb{F}_2^{|V|}$; equivalently, the underlying undirected graph $G = (V, E)$.
* **Quantifiers & parameters:**
  - **General $\mathbb{F}_2$ linear systems ($Ax = f$):** Gaussian elimination decides consistency and finds a refutation vector $y \in \mathbb{F}_2^{|V|}$ ($y^T A = 0$, $y^T f = 1$) in $O(|V| \cdot |E| \cdot \min(|V|, |E|))$ bit operations ($O(|V|^3)$ for bounded-degree graphs, or $O(|V|^\omega)$ via fast matrix multiplication).
  - **Tseitin specifically:** Since each column of $A$ has weight $2$, summing rows over any connected component $C \subseteq V$ yields $0 \pmod 2$. Hence $\mathrm{Tseitin}(G, f)$ is unsatisfiable iff some component $C$ has $\sum_{v \in C} f(v) \equiv 1 \pmod 2$, decidable in **linear time $O(|V| + |E|)$** (BFS/DFS) and in deterministic logspace $\mathrm{L}$ (via undirected connectivity).
* **Upper vs. lower bound:** Algorithmic upper bounds.
* **Assumptions:** Instance is presented as (or parsed back into) $\mathbb{F}_2$-linear equations / Tseitin parity constraints.
* **Primary-source citations:** Classical linear algebra (folklore); for deterministic logspace connectivity $\mathrm{SL} = \mathrm{L}$: Omer Reingold, "Undirected Connectivity in Log-Space," *Journal of the ACM (JACM)*, Vol. 55, No. 4, Article 17, 2008 (preliminary: *STOC 2005*, pp. 376–385). DOI: `10.1145/1391289.1391291` `[VERIFY]`.
* **What it does NOT establish:** Does not yield a general SAT algorithm (general 3-SAT cannot be reduced to $\mathbb{F}_2$-linear systems unless $\mathrm{P} = \mathrm{NP}$).

#### **T18 — Polynomial Calculus over $\mathbb{F}_2$ vs. Characteristic $\neq 2$ `[Proved]`**
* **Exact proof system:** Polynomial Calculus (PC) over a field $\mathbb{F}$.
* **Graph representation:** Underlying graph $G = (V, E)$ (variables $x_e$, Boolean axioms $x_e^2 - x_e = 0$, parity polynomials).
* **Quantifiers & parameters:**
  - **Over $\mathbb{F}_2$ (Upper bound):** Every unsatisfiable $\mathrm{Tseitin}(G, f)$ has a **degree-$1$**, **size-$O(|V| + |E|)$** PC refutation (summing all vertex equations in an odd-charged component yields $0 = 1$).
  - **Over $\mathbb{F}$ with $\mathrm{char}(\mathbb{F}) \neq 2$ (Lower bound):** For constant-degree expander graphs $G$, PC (and Nullstellensatz) requires **degree $\Omega(|V|)$** (and exponential monomial size under PC size–degree relations) to refute $\mathrm{Tseitin}(G, f)$.
* **Upper vs. lower bound:** Sharp contrast: trivial linear upper bound in $\mathrm{char} = 2$ vs. linear degree lower bound in $\mathrm{char} \neq 2$.
* **Assumptions:** For the lower bound, $G$ is a bounded-degree expander and $\mathrm{char}(\mathbb{F}) \neq 2$.
* **Primary-source citations:**
  - Matthew Clegg, Jeffery Edmonds, and Russell Impagliazzo, "Using the Groebner Basis Algorithm to Find Proofs of Unsatisfiability," *STOC 1996*, pp. 174–183, 1996. DOI: `10.1145/237814.237860` `[VERIFY]`.
  - Dima Grigoriev, "Tseitin's Tautologies and Lower Bounds for Nullstellensatz Proofs," *FOCS 1998*, pp. 648–652, 1998. DOI: `10.1109/SFCS.1998.743515` `[VERIFY]`.
  - Sam Buss, Dima Grigoriev, Russell Impagliazzo, and Toniann Pitassi, "Linear Gaps between Degrees for the Polynomial Calculus Modulo Distinct Primes," *JCSS*, Vol. 62, No. 2, pp. 267–289, 2001. DOI: `10.1006/jcss.2000.1726` `[VERIFY]`.
* **What it does NOT establish:** PC over $\mathbb{F}_2$ is still far from $\mathrm{NP} = \mathrm{coNP}$ (e.g., Pigeonhole Principle and $\mathrm{MOD}_3$ counting principles remain hard for PC over $\mathbb{F}_2$).

#### **T19 — $\mathrm{Res}(\oplus)$, Extended Resolution, and Frege Upper Bounds on Tseitin `[Proved]`**
* **Exact proof systems:** $\mathrm{Res}(\oplus)$ (Resolution over linear clauses modulo $2$), Extended Resolution ($\mathrm{ER}$), and Frege.
* **Graph representation:** Underlying graph $G = (V, E)$.
* **Quantifiers & parameters:**
  - **$\mathrm{Res}(\oplus)$:** Every unsatisfiable $\mathrm{Tseitin}(G, f)$ has a **tree-like $\mathrm{Res}(\oplus)$ refutation of size $O(|V| + |E|)$** (directly adding linear equations mod $2$).
  - **Extended Resolution ($\mathrm{ER}$) / DRAT / Frege:** Every unsatisfiable $\mathrm{Tseitin}(G, f)$ of bounded degree $\Delta = O(1)$ admits a **polynomial-size** refutation (by introducing extension variables simulating Gaussian elimination / iterative XOR folding in $\mathrm{ER}$, or balanced XOR formula trees in Frege).
* **Upper vs. lower bound:** Polynomial / linear proof-size upper bounds.
* **Assumptions:** Bounded degree $\Delta = O(1)$ so the CNF encoding itself has polynomial size $\sum_{v \in V} 2^{d(v)-1}$.
* **Primary-source citations:**
  - Dmitry Itsykson and Dmitry Sokolov, "Resolution over Linear Equations Modulo Two," *Annals of Pure and Applied Logic*, Vol. 171, No. 1, 102722, 2020 (preliminary: *SAT 2014*, LNCS 8561, pp. 180–196). DOI: `10.1016/j.apal.2019.102722` `[VERIFY]`.
  - Stephen A. Cook and Robert A. Reckhow, "The Relative Efficiency of Propositional Proof Systems," *The Journal of Symbolic Logic*, Vol. 44, No. 1, pp. 36–50, 1979. DOI: `10.2307/2273702` `[VERIFY]`.
* **What it does NOT establish:** Does not make $\mathrm{Res}(\oplus)$ or $\mathrm{ER}$ polynomially bounded on all tautologies; rather, it establishes that **Tseitin contradictions cannot separate Frege, $\mathrm{ER}$, DRAT, or $\mathrm{Res}(\oplus)$ from polynomial size**—Tseitin is exclusively a lower-bound benchmark for weak systems lacking $\mathbb{F}_2$-linear reasoning (Resolution, $\mathrm{AC}^0$-Frege, PC($\mathbb{F}_p, p\neq 2$)).

---

## 4. Subsumption Audit: Do Known Results Subsume Discovery Round 01 Observations?

This section evaluates each structural observation likely to arise from the `dev @ d115ced` pipeline (`Tseitin.lean`, matched Tseitin suite, Nova's width features, Claude's SAT/DRAT runner) against T1–T19.

| Potential Team Observation | Subsumed by Known Theory? | Exact Subsuming Results | Honest Classification |
| :--- | :--- | :--- | :--- |
| "Unsatisfiability of $\mathrm{Tseitin}(G, f)$ depends only on odd component charge." | **Yes (100% subsumed)** | Tseitin (1968), T17 | Known `[Proved]` theorem (valid as `[Lean-Verified]` formalization in `Tseitin.lean`, not a new discovery). |
| "Higher treewidth $\mathrm{tw}(G)$ or edge expansion $e(G)$ correlates with larger Resolution width and harder SAT instances on matched Tseitin graphs." | **Yes (100% subsumed)** | T1, T2, T9, T10, T11, T12 | `[Empirical Observation]` reproducing known `[Proved]` theory. |
| "Low-treewidth Tseitin graphs solve fast while expander graphs of the same $(|V|, |E|, \Delta)$ blow up in CDCL." | **Yes (100% subsumed)** | T9, T10 (lower bound on expanders) + T11 (upper bound $2^{O(\mathrm{tw})}$) + T15 (CDCL $\sim$ General Res) | `[Empirical Observation]` consistent with existing bounds. |
| "Primal treewidth $\mathrm{tw}(G_P)$ tracks solver difficulty better than $\mathrm{tw}(G)$ when degrees vary." | **Yes (subsumed)** | Section 1 ($\mathrm{tw}(L(G)) \in [\Delta-1, \Delta(\mathrm{tw}+1)-1]$) + T5, T11, T12 | Expected consequence of line-graph degree blowup and initial clause width $w(F) = \Delta$. |
| "Solver solves Tseitin instances rapidly regardless of treewidth when XOR/Gaussian or BVA/RAT inprocessing is enabled." | **Yes (100% subsumed)** | T16 (DRAT $\equiv_p$ ER), T17 (Gauss), T19 (ER/$\mathrm{Res}(\oplus)$ poly-size) | `[Empirical Observation]` confirming the proof system left Resolution. |
| "Quantifying how far practical CDCL heuristics (VSIDS/restarts) deviate from optimal $2^{O(\mathrm{tw}(G))}$ Resolution size on matched graphs." | **Partially novel (empirical systems measurement)** | T11 (existential upper bound) vs. T15 (nondeterministic CDCL) | Valid `[Empirical Observation]` on solver heuristics—**never** a proof-complexity lower bound. |
| "Behavior of pure DRUP (general Resolution) proof size on intermediate-width graphs (e.g., 2D grids where $\mathrm{tw} = \Theta(\sqrt{|V|})$ and BSW T2 is vacuous)." | **Open boundary in theory (empirical exploration only)** | T2 fails at $\sqrt{n}$; T8 covers only *Regular* Res; general Res on grids remains open `[VERIFY]` | Small-scale runs remain `[Empirical Observation]` only; cannot prove a lower bound, though discovering an unexpectedly short *pure DRUP* refutation on grids would merit theoretical inspection. |

### Bottom-Line Scope Limitation for Operation Millennium
Because Tseitin formulas are decidable in linear time $O(|V| + |E|)$ (T17) and admit polynomial-size proofs in $\mathrm{Res}(\oplus)$, PC($\mathbb{F}_2$), Frege, and Extended Resolution / DRAT (T18, T19), **no result on Tseitin formulas in Resolution can advance $\mathrm{P}$ vs. $\mathrm{NP}$ directly**. Its value in Phase 3 is strictly as a calibrated testbed for understanding proof-complexity barriers (width vs. size, regular vs. general Resolution, and why algebraic structure breaks Resolution-based solvers).

