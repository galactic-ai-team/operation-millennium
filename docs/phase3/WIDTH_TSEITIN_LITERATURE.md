# Graph Width, Tseitin Contradictions, and Restricted Proof Complexity

> **Document:** `docs/phase3/WIDTH_TSEITIN_LITERATURE.md`  
> **Phase / Round:** Phase 3 — Discovery Round 01 (Phase 4 Gate C Repair — Revision 2, base `dev @ e7f87af`)  
> **Author:** Gemini — Galactic AI Team  
> **Review Status:** **REPAIR REVISION 2 SUBMITTED FOR INDEPENDENT RE-REVIEW** (addresses the remaining blocking findings `ACE-R11-11`, `ACE-R11-18`, `ACE-R11-19`, `ACE-R11-20`, and `ACE-R11-21` from `docs/phase4/reviews/REREVIEW_PR11_LIT_ACE.md`; `ACE-R11-22` and `ACE-R11-23` remain `OPEN` as recorded; per `docs/RULES.md`, Gemini does not self-approve this repair).  
> **Claim Labels (per `docs/RULES.md`):** `[Proved]`, `[Conjecture]`, `[Empirical Observation]`, `[Lean-Verified]`.

---

## 1. Scope, Notation, and Graph Representations

**Graph Scope Convention:** Unless expressly stated otherwise, all underlying graphs in this document are **finite simple undirected graphs**; results permitting multigraphs use their source-specific conventions. The expanded parity CNF encoding below assumes **distinct incident edge variables** (this scope also governs T10 and the Polynomial Calculus encodings in T18).

Let $G = (V, E)$ be a finite simple undirected graph with maximum degree $\Delta = \Delta(G)$, treewidth $\mathrm{tw}(G)$ (defined as maximum bag size minus $1$, adopting $\mathrm{tw}(\emptyset) = -1$ for the empty graph with no vertices), and branchwidth $\mathrm{bw}(G)$.

### 1.1 Balanced Edge Expansion

For a graph $G = (V, E)$ with $|V| \ge 2$, define the balanced edge expansion as

$$
e(G) = \min \left\{ |E(U, V \setminus U)| : U \subseteq V,\; \left\lceil \frac{|V|}{3} \right\rceil \le |U| \le \left\lfloor \frac{2|V|}{3} \right\rfloor \right\}.
$$

*(Edge-case guard: for $|V| \le 1$, the set of admissible cuts is empty, so $e(G)$ is not used; trivial graphs $|V| \le 1$ and no-edge parity systems are handled separately via direct empty-clause proofs where relevant.)*

### 1.2 Tseitin Formulas

Given a finite simple undirected graph $G = (V, E)$ and a charge function $f : V \to \{0, 1\}$, the **Tseitin formula** $\mathrm{Tseitin}(G, f)$ (also written $T(G, f)$) has one Boolean variable $x_e$ per edge $e \in E$ and, for each vertex $v \in V$ of degree $d(v)$, encodes the parity constraint

$$
\bigoplus_{e \ni v} x_e = f(v) \pmod 2.
$$

* If $d(v) \ge 1$, the standard expanded CNF encoding at $v$ consists of $2^{d(v)-1}$ clauses of width $d(v)$ over the $d(v)$ distinct incident edge variables, forbidding the $2^{d(v)-1}$ assignments with wrong parity.
* If $d(v) = 0$ (isolated vertex): $f(v) = 0$ contributes $0$ clauses (trivially satisfied), and $f(v) = 1$ contributes the single empty clause $\bot$ (immediately unsatisfiable). *(Do not evaluate $2^{d(v)-1}$ at $d(v) = 0$.)*

$\mathrm{Tseitin}(G, f)$ is unsatisfiable if and only if some connected component $C \subseteq V$ has odd total charge $\sum_{v \in C} f(v) \equiv 1 \pmod 2$ `[Proved]`.

### 1.3 Graph and Hypergraph Representations (Kept Strictly Distinct)

Width parameters depend strongly on which representation of a CNF $F$ is measured. Every theorem below pins its exact representation:

1. **Underlying Tseitin graph $G = (V, E)$:** Vertices are parity constraints; edges are Boolean variables.
2. **Primal (Gaifman) graph $G_P(F)$:** Vertices are Boolean variables $\mathrm{Var}(F)$; two distinct variables are adjacent iff they co-occur in at least one clause of $F$.
   * For the standard Tseitin CNF on a simple graph $G$, the variables co-occurring at vertex $v$ are precisely the edges incident to $v$, so $G_P(\mathrm{Tseitin}(G, f)) = L(G)$ (the **line graph** of $G$, whose vertices are $E$ and where two edges are adjacent iff they share an endpoint in $G$; when $E = \emptyset$, $L(G) = \emptyset$ with $\mathrm{tw}(\emptyset) = -1$) `[Proved]`.
   * For every simple graph $G$ of maximum degree $\Delta$ (with $E \neq \emptyset$),

     $$
     \mathrm{tw}(L(G)) \le \Delta(\mathrm{tw}(G) + 1) - 1
     $$

     `[Proved]` *(Proof: given a tree decomposition of $G$ of width $\mathrm{tw}(G)$, replace each vertex bag $B$ by the set of edges incident to vertices in $B$; each bag has size at most $\Delta(\mathrm{tw}(G)+1)$, adjacent line-graph vertices share an endpoint and co-occur in every bag containing that endpoint, and for each edge $e = \{u, v\}$ the subtrees of $u$ and $v$ intersect at a bag containing $\{u, v\}$, so their union is connected).*
3. **Incidence graph $G_I(F)$:** Bipartite graph on $\mathrm{Var}(F) \cup \mathrm{Clauses}(F)$ with an edge $\{x, C\}$ whenever $x$ or $\neg x$ occurs in $C$.
   * Always satisfies $\mathrm{tw}(G_I(F)) \le \mathrm{tw}(G_P(F)) + 1$ `[Proved]` *(Proof: for $\mathrm{Var}(F) \neq \emptyset$, every non-empty clause's variables form a clique in $G_P(F)$ and therefore lie inside some bag $B_C$ of an optimal tree decomposition of $G_P(F)$; attach a new leaf bag $B_C \cup \{C\}$ adjacent to $B_C$, and attach each empty-clause singleton bag $\{C\}$ to an existing bag of the decomposition; if $\mathrm{Var}(F) = \emptyset$, form a tree of singleton bags $\{C\}$ for the empty clauses, giving width $0 = \mathrm{tw}(\emptyset) + 1$. Maximum bag size increases by at most $1$).*
4. **CNF Clause-Indexed Multihypergraph $H(F)$ (Alekhnovich–Razborov convention):**
   * $H(F)$ has **one indexed hyperedge per clause**, supported on its variable set. Different clauses with identical support are retained as separate hyperedges; use the multihypergraph convention of Alekhnovich–Razborov (2011), Remark 2.11. Clause positions remain distinct if the represented input contains duplicate clauses, unless a specified preprocessing step changes the input and the parameter is recomputed.
   * **Why Multiplicity Must Not Be Collapsed — Two-Vertex / One-Edge Counterexample `[Proved]`:** Let $G$ be the simple graph with two vertices and one edge $e$ (variable $x$), with vertex charges $0$ and $1$. Its expanded Tseitin CNF is $F = (\neg x) \land (x)$, which has minimum Resolution width $W = 1$. The clause-indexed multihypergraph $H(F)$ has two distinct hyperedges both supported on $\{x\}$; the cut separating them has boundary $\{x\}$ and width $1$. Collapsing identical-support hyperedges into a single hyperedge would yield branchwidth $0$ under the single-hyperedge convention (and likewise collapses the four distinct local clauses of a cubic vertex into one hyperedge even though their literal polarities differ).
   * **Hypergraph-to-Primal-Treewidth Bridge `[Proved]`:** For any CNF $F$ (with $\mathrm{tw}(\emptyset) = -1$),

     $$
     \mathrm{bw}(H(F)) \le \mathrm{tw}(G_P(F)) + 1.
     $$

     *(Proof: if $F$ has at most $1$ clause, $\mathrm{bw}(H(F)) = 0 \le \mathrm{tw}(G_P(F)) + 1$. Otherwise, start from an optimal tree decomposition $(T, \{B_t\})$ of $G_P(F)$ of width $k = \mathrm{tw}(G_P(F))$—or a single empty bag if $\mathrm{Var}(F) = \emptyset$. Every non-empty clause's variable support is a clique in $G_P(F)$ and lies in some bag $B_t$; attach one distinct leaf per indexed clause hyperedge to a bag containing its support, or to any bag for an empty clause. Expand internal vertices of degree $> 3$ into subcubic trees copying their bags, and suppress degree-$2$ nodes. For any edge of the resulting branch-decomposition tree, every variable occurring in clauses on both sides must lie in the bag $B_t$ of an endpoint of that edge by the running-intersection property, so every cut has boundary size at most $|B_t| \le k + 1$.)*
   * **Critical Robertson–Seymour Warning `[Proved]`:** Do **not** apply the ordinary-graph inequality $\mathrm{bw}(G) - 1 \le \mathrm{tw}(G) \le \lfloor \frac{3}{2}\mathrm{bw}(G) \rfloor - 1$ directly in the reverse direction to arbitrary clause hypergraphs $H(F)$ and primal graphs $G_P(F)$. *Counterexample:* a hypergraph consisting of a single hyperedge on $n$ vertices has $\mathrm{bw} = 0$ under a single-hyperedge branch decomposition, whereas its primal graph is $K_n$ with $\mathrm{tw}(K_n) = n - 1$.

### 1.4 Resolution Complexity Measures

For an unsatisfiable CNF $F$ on $n$ variables:

* $w_0 = w(F)$: maximum width (number of literals) of an initial clause in $F$.
* $W = w(F \vdash \bot)$: minimum width (maximum number of literals in any clause of the refutation) of an unrestricted Resolution refutation of $F$.
* $S_T(F)$, $S_R(F)$, $S(F)$: minimum number of clauses (proof lines, counting used clauses under the cited source's convention) in a **tree-like**, **regular**, and **unrestricted (general DAG-like)** Resolution refutation of $F$, respectively.

---

## 2. Auditable Theorem Summary Table

Every `[Proved]` entry below is backed either by a checked primary theorem locator (recorded in the table and Section 3) or by an explicit elementary derivation written out in Sections 1 and 3. Unverified historical exponents, the unverified `Res(XOR)` total-symbol-size locator (`ACE-R11-19`), and the November 2026 preprint audit (`ACE-R11-22`) remain explicitly `OPEN` and outside the `[Proved]` entries.

| ID | Topic / Theorem | Proof System / Model | Representation | Bound Type & Verified Statement | Claim Level | Primary Source & Locator |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **T1** | BSW Tree-like Size–Width | Tree-like Resolution | Arbitrary CNF | **Lower:** $S_T(F) \ge 2^{W - w_0}$ (equiv. $W \le w_0 + \log_2 S_T(F)$) | `[Proved]` | Ben-Sasson & Wigderson (2001), Thm. 3.3, Cor. 3.4 |
| **T2** | BSW General Size–Width | Unrestricted Resolution | Arbitrary CNF ($n \ge 1$) | **Lower:** $W \le w_0 + O(\sqrt{n \ln S(F)})$; safely $S(F) \ge \exp(\Omega(\max(0, W - w_0)^2 / n))$ | `[Proved]` | Ben-Sasson & Wigderson (2001), Thm. 3.5, Cor. 3.6 |
| **T3** | Optimality of BSW Tradeoff | Unrestricted Resolution | Modified ordering CNF $MGT_n$ | **Upper / Lower:** Constant-width $MGT_n$ on $N = \Theta(n^2)$ vars has $\mathrm{poly}(n)$-size refutation and $W = \Omega(n) = \Omega(\sqrt{N})$ | `[Proved]` | Bonet & Galesi (2001), Thms. 3.2, 3.7, 3.8 |
| **T4** | Width–Pebble Game Equivalence | Unrestricted Resolution (width) | CNF / partial assignments | **Threshold Exact:** For $k \ge w_0$, $W \le k \iff$ Spoiler wins Boolean existential $(k+1)$-pebble game (Duplicator family size $\le k+1$) | `[Proved]` | Atserias & Dalmau (2008 / ECCC TR02-035), Def. 2, Lem. 1–2, Thm. 1 |
| **T5** | Treewidth SAT & #SAT DP | Deterministic RAM (supplied nice tree decomp., $N$ nodes) | $G_P(F)$ and $G_I(F)$ | **Upper:** Primal $O(2^k(kd+\delta)N)$; Incidence $O(2^k(k\ell + 2^k(k+\delta))N)$ (hence $O^*(2^k)$ and $O^*(4^k)$) | `[Proved]` | Samer & Szeider (2010), Sec. 3, Thms. 1 & 3 |
| **T6** | #SAT via `#DPLL-Cache` | `#DPLL-Cache` (deterministic / suitable order) | Decomposition branchwidth $b$ | **Upper:** $n^{O(1)} \cdot 2^{O(b)}$ (accounting for formula length and cached entries) | `[Proved]` | Bacchus, Dalmao, & Pitassi (2009), Thm. 2, Sec. 2.5 |
| **T7** | SETH Tightness for Primal Treewidth | Deterministic RAM (or Randomized under rSETH) | $G_P(F)$ | **Conditional Lower:** Under det. SETH, no $(2-\varepsilon)^{\mathrm{tw}(G_P(F))}\mathrm{poly}(\lvert F \rvert)$ det. SAT algorithm | `[Proved]` (conditional on `[Conjecture]` SETH) | Impagliazzo & Paturi (2001); Lokshtanov, Marx, & Saurabh (2018) |
| **T8** | Tseitin Grid Resolution Lower Bound | Unrestricted & Regular Resolution | $k \times k$ grid $G_{k \times k}$ ($k \ge 2$) | **Lower:** $S_R \ge S(\mathrm{Tseitin}(G_{k\times k}, f)) \ge 2^{\Omega(k)}$ (via cyclicity $\le 4$ + balanced cut $\ge \Omega(k)$) | `[Proved]` | Alekhnovich & Razborov (2011), Def. 2.14, Thm. 2.15 + BSW (2001), Thm. 4.4 |
| **T9** | Tseitin General Resolution on Expanders | Unrestricted Resolution | Constant-degree expander $G$ | **Lower:** $S(\mathrm{Tseitin}(G, f)) = 2^{\Omega(\lvert V \rvert)}$ | `[Proved]` | Urquhart (1987); BSW (2001), Thm. 4.4, Cor. 4.5 |
| **T10** | BSW Tseitin Width & Size via Expansion | Unrestricted Resolution | Connected simple $G$ ($\lvert V \rvert \ge 2$, max deg $\Delta$) | **Lower:** $W \ge e(G)$; $S \ge \exp(\Omega(\max(0, e(G) - \Delta)^2 / \lvert E \rvert))$ | `[Proved]` | Ben-Sasson & Wigderson (2001), Thms. 4.4 & 3.5 |
| **T11** | Branchwidth, Treewidth & Tseitin Resolution | Regular & Unrestricted Resolution | Clause-indexed multihypergraph $H(F)$ / connected odd-charge $G$ / $L(G)$ | **Upper (all CNF):** $\mathrm{poly}(\lvert F \rvert + 2^{\mathrm{bw}(H(F))})$ Regular Res (width $O(\mathrm{bw}(H(F)))$); bridge gives $\mathrm{poly}(\lvert F \rvert)\cdot 2^{O(\Delta(\mathrm{tw}(G)+1))}$. **Tseitin (conn., odd):** $\mathrm{bw}(H(T(G,f))) = \Theta(W)$ | `[Proved]` | Alekhnovich & Razborov (2011), Def. 2.8, Rem. 2.11, Thms. 2.3, 2.12, 2.13, 2.15 + Sec. 1.3 bridge |
| **T12** | Exact Tseitin Resolution Width | Unrestricted Resolution (width) | Connected simple $G$ and $L(G)$ | **Exact:** $W(T(G, f)) = \max(\Delta(G), \mathrm{tw}(L(G)))$ (with $\mathrm{tw}(\emptyset) = -1$ for $K_1$) | `[Proved]` | Galesi, Talebanfard, & Torán (ECCC TR18-170), Cor. 8 (p. 12), Cor. 16 (p. 15) |
| **T13** | Tree-like vs. Regular / General Resolution | Tree-like vs. Regular (A); Tree-like vs. General (B) | $MGT_n$ (A); pebbling CNFs (B) | **(A):** Reg $\mathrm{poly}(n)$ vs. Tree $2^{\Omega(n)}$; **(B):** Gen $O(n)$ vs. Tree $\exp(\Omega(n/\log n))$ | `[Proved]` | (A) Bonet & Galesi (2001), Thms. 3.2, 4.1–4.2; (B) BIW (2004), Thm. 1 |
| **T14** | Regular vs. Unrestricted Resolution | Regular vs. Unrestricted Resolution | Modified ordering CNF $GT'_{n,\rho}$ | **Upper (Gen):** $O(n^3)$; **Lower (Reg):** $> 2^{n/200}$ lines ($n$ = ordering elements, $\Theta(n^2)$ vars) | `[Proved]` | Alekhnovich, Johannsen, Pitassi, & Urquhart (2007), Def. 3.3, Cor. 3.4, Thm. 3.10 |
| **T15** | CDCL (CLR) & DRUP vs. General Resolution | Idealized CLR / DRUP vs. Unrestricted Resolution | Arbitrary CNF | **Simulation:** CLR with asserting learning + restarts $\equiv_p$ General Res; DRUP $\equiv_p$ General Res | `[Proved]` | Pipatsrisawat & Darwiche (2011), Thms. 1–2, Cor. 1; Kiesl et al. (2018), Thm. 2, Sec. 4.4 |
| **T16** | DRAT vs. Extended Resolution | DRAT vs. Extended Resolution (ER) | Arbitrary CNF (with extension vars) | **Simulation:** DRAT $\equiv_p$ ER | `[Proved]` | Kiesl, Rebola-Pardo, & Heule (2018), Sec. 4 (esp. Sec. 4.5) |
| **T17** | Algebraic Solving & Graph Connectivity | RAM ($\mathrm{P}$) / Deterministic Logspace ($\mathrm{L}$) | (A) Linear sys.; (B) Charged graph; (C) Raw CNF | **(A):** poly-time ($\mathrm{P}$) Gauss + cert; **(B):** $O(\lvert V \rvert + \lvert E \rvert)$ & $\mathrm{L}$ graph parity; **(C):** requires extraction | `[Proved]` | Component parity + spanning tree; Reingold (2008 / ECCC TR04-094) |
| **T18** | Polynomial Calculus & Field Encodings | Polynomial Calculus (PC) | (1) Linear $\mathbb{F}_2$; (2) Cubic CNF $\mathbb{F}_2$; (3) Signed $TS_n(2)$ (odd $n$, charge $1$, $\mathrm{char}\neq 2$) | **(1):** deg $\le 1$, $O(\lvert V \rvert)$ steps, $O(\lvert V \rvert(\lvert E \rvert + 1))$ monomials; **(2):** deg $\le 3$; **(3):** no deg $d < \varepsilon n/8$ for $\lvert N(S) \rvert \ge (1+\varepsilon)\lvert S \rvert$ ($\lvert S \rvert \le n/2$) | `[Proved]` | Clegg et al. (1996); Buss, Grigoriev, Impagliazzo, & Pitassi (2001), Sec. 2, Thm. 10 (p. 15) |
| **T19** | Direct Parity Sums, Frege & Extended Resolution | Direct $\mathbb{F}_2$ sums; Frege; ER / DRAT *(Res($\oplus$) exact size: `OPEN`)* | Direct equations vs. bounded-deg CNF | Direct sum: $O(\lvert V \rvert)$ steps, $O(\lvert V \rvert(\lvert E \rvert + 1))$ unit-cost symbols; Frege / ER / DRAT: $\mathrm{poly}(\lvert V \rvert)$ for bounded $\Delta$ | `[Proved]` *(exact `Res(XOR)` symbol size excluded / `OPEN`)* | Urquhart (1987), Sec. 6, Lem. 6.1, Thm. 6.2 + bounded-deg derivation; Cook & Reckhow (1979); Kiesl et al. (2018) |

---

## 3. Detailed Theorem Records

### 3.1 Ben-Sasson & Wigderson Resolution Width/Size Results

#### **T1 — Tree-like Resolution Size–Width Lower Bound `[Proved]`**

* **Exact proof system:** Tree-like Resolution (with standard weakening/size conventions of the source).
* **Representation:** Arbitrary unsatisfiable CNF $F$ on $n$ variables.
* **Quantifiers & parameters:** For every unsatisfiable CNF $F$ with maximum initial clause width $w_0$, minimum unrestricted Resolution refutation width $W = w(F \vdash \bot)$, and minimum tree-like Resolution refutation size $S_T(F)$:

  $$
  S_T(F) \ge 2^{W - w_0} \qquad \text{(equivalently, } W \le w_0 + \log_2 S_T(F)\text{)}.
  $$

* **Bound direction:** Lower bound on tree-like proof size in terms of refutation width.
* **Assumptions:** $F$ is an unsatisfiable CNF.
* **Primary source:** Eli Ben-Sasson and Avi Wigderson, "Short Proofs Are Narrow—Resolution Made Simple," *Journal of the ACM (JACM)*, Vol. 48, No. 2, pp. 149–169, 2001. DOI: `10.1145/375827.375835`. **Locator:** Theorem 3.3 and Corollary 3.4.
* **What it does NOT establish:** Not a universal lower bound on SAT-solving time or DAG-like Resolution size; does not apply to proof systems stronger than Resolution.

#### **T2 — General (Unrestricted) Resolution Size–Width Tradeoff `[Proved]`**

* **Exact proof system:** Unrestricted (DAG-like) Resolution.
* **Representation:** Arbitrary unsatisfiable CNF $F$ on $n$ Boolean variables.
* **Quantifiers & parameters:** Under the source's proof-size convention ($S(F)$ = number of lines in a shortest refutation):

  $$
  W \le w_0 + O\!\left(\sqrt{n \ln S(F)}\right).
  $$

  Rearranging safely without squaring a negative gap (relevant whenever unused wide input clauses can be omitted from a refutation):

  $$
  S(F) \ge \exp\!\left(\Omega\!\left(\frac{\max(0, W - w_0)^2}{n}\right)\right).
  $$

* **Bound direction:** Lower bound on unrestricted Resolution proof size in terms of width gap.
* **Assumptions:** $F$ is an unsatisfiable CNF on $n$ variables ($n \ge 1$).
* **Primary source:** Ben-Sasson and Wigderson (2001), DOI: `10.1145/375827.375835`. **Locator:** Theorem 3.5 and Corollary 3.6.
* **What it does NOT establish:** Yields only a trivial $O(1)$ size lower bound whenever $\max(0, W - w_0) = O(\sqrt{n})$. This limitation belongs to T2 alone and does *not* imply that stronger lower bounds are unknown or impossible for width-$\Theta(\sqrt{n})$ formulas (see T8).

#### **T3 — Optimality of the BSW Size–Width Tradeoff (`MGT_n`) `[Proved]`**

* **Exact proof system:** Unrestricted Resolution.
* **Representation:** Modified Graph Ordering Principle CNF $MGT_n$ (bounded initial clause width, distinct from the wide-clause original ordering formula $GT_n$).
* **Quantifiers & parameters:** For ordering size $n$, $MGT_n$ is a family of constant-width unsatisfiable CNFs on $N = \Theta(n^2)$ Boolean variables that admits polynomial-size Resolution refutations while requiring minimum Resolution refutation width $W(MGT_n \vdash \bot) = \Omega(n) = \Omega(\sqrt{N})$.
* **Bound direction:** Simultaneous polynomial size upper bound and $\Omega(\sqrt{N})$ width lower bound.
* **Assumptions:** Constant-width modified ordering encoding $MGT_n$.
* **Primary source:** Maria Luisa Bonet and Nicola Galesi, "Optimality of Size-Width Tradeoffs for Resolution," *Computational Complexity*, Vol. 10, No. 4, pp. 261–276, 2001. DOI: `10.1007/s000370100000`. **Locator:** Theorems 3.2, 3.7, and 3.8 (comparing against $GT_n$ in Theorem 3.1).
* **What it does NOT establish:** Demonstrates the tightness of size–width tradeoffs as a proof-lower-bound technique, not a limitation on non-width lower-bound methods.

#### **T4 — Threshold Pebble-Game Characterization of Resolution Width `[Proved]`**

* **Exact proof system:** Unrestricted Resolution (refutation width).
* **Representation:** Unsatisfiable CNF $F$ via families of partial truth assignments.
* **Quantifiers & parameters:** For every unsatisfiable CNF $F$ and every integer $k \ge w_0$:

  $$
  W(F \vdash \bot) \le k \iff \text{Spoiler wins the Boolean existential } (k+1)\text{-pebble game on } F.
  $$

  Equivalently, $W(F \vdash \bot) > k$ iff Duplicator has a non-empty winning strategy family $\mathcal{H}$ of partial truth assignments each assigning **at most $k+1$ variables**, falsifying no clause of $F$, closed under sub-assignments (restrictions), and satisfying the extension property: for every $\alpha \in \mathcal{H}$ with $|\mathrm{dom}(\alpha)| < k+1$ and every variable $x$, there exists $\beta \in \mathcal{H}$ extending $\alpha$ with $x \in \mathrm{dom}(\beta)$.
* **Bound direction:** Exact **threshold** characterization (note: **not** an equality $W = k$; e.g., $F = (x) \land (\neg x)$ has $W = 1$, yet Spoiler wins with every pebble allowance $k+1 \ge 2$).
* **Assumptions:** $F$ is an unsatisfiable CNF and $k \ge w_0$.
* **Primary source:** Albert Atserias and Víctor Dalmau, "A Combinatorial Characterization of Resolution Width," *Journal of Computer and System Sciences (JCSS)*, Vol. 74, No. 3, pp. 323–334, 2008. DOI: `10.1016/j.jcss.2007.06.025`; ECCC Report `TR02-035` (`https://eccc.weizmann.ac.il/report/2002/035/`). **Locator:** ECCC `TR02-035`, Definition 2, Lemmas 1–2, and Theorem 1.
* **What it does NOT establish:** Characterizes minimum Resolution width, not minimum proof length or CDCL solver effort.

---

### 3.2 Treewidth-Parameterized SAT and Model-Counting (#SAT) Algorithms

#### **T5 — Fixed-Parameter Tractable #SAT and SAT via Primal and Incidence Treewidth `[Proved]`**

* **Exact computational model:** Deterministic RAM running dynamic programming over a **supplied** nice tree decomposition.
* **Representation:** Primal graph $G_P(F)$ and incidence graph $G_I(F)$.
* **Quantifiers & parameters:** Given a CNF $F$ and a supplied nice tree decomposition of width $k$ having $N$ decomposition nodes, let $d$ be the maximum number of clauses in which any variable occurs, $\ell$ be the maximum clause length, and $\delta$ be the bit-complexity cost of multiplying integers of the relevant model-count bit-length (as defined in the source):
  * **Primal decomposition width $k$ (in particular $k = \mathrm{tw}(G_P(F))$ for an optimal decomposition):** #SAT (and hence SAT, by testing whether the count is $> 0$) is solved in time

    $$
    O\!\left(2^k \cdot (k d + \delta) \cdot N\right).
    $$

  * **Incidence decomposition width $k$ (in particular $k = \mathrm{tw}(G_I(F))$ for an optimal decomposition):** #SAT (and SAT) is solved in time

    $$
    O\!\left(2^k \cdot \left(k \ell + 2^k(k + \delta)\right) \cdot N\right).
    $$

    For polynomial-size supplied decompositions and polynomial-time integer arithmetic, these yield $O^*(2^k)$ and $O^*(4^k)$ respectively.
* **Bound direction:** Algorithmic upper bounds.
* **Assumptions:** A width-$k$ nice tree decomposition is supplied as input (the cost of computing an optimal or approximate tree decomposition is separate and requires its own cited theorems).
* **Primary source:** Marko Samer and Stefan Szeider, "Algorithms for Propositional Model Counting," *Journal of Discrete Algorithms*, Vol. 8, No. 1, pp. 50–64, 2010. DOI: `10.1016/j.jda.2009.06.002`. **Locator:** Section 3, Theorems 1 and 3.
* **What it does NOT establish:** Does not imply high treewidth forces algorithmic hardness on structured subclasses like Tseitin; does not claim $O^*(4^k)$ remains the fastest known incidence-treewidth #SAT algorithm; does not imply heuristic CDCL solvers achieve $O^*(2^{\mathrm{tw}})$.

#### **T6 — #SAT via `#DPLL-Cache` and Decomposition Branchwidth `[Proved]`**

* **Exact computational model:** `#DPLL-Cache` (backtracking DPLL with component/formula caching, distinct from the `#DPLL-Space` model of Theorem 3).
* **Representation:** Source-defined decomposition branchwidth $b$ of the formula (not an arbitrary primal-graph min-fill width).
* **Quantifiers & parameters:** There exists an execution of `#DPLL-Cache` (which can be made deterministic given the decomposition order) running in time $n^{O(1)} \cdot 2^{O(b)}$ (with polynomial input-processing factor accounting for formula length, and space bounded accordingly by polynomially encoded cached entries).
* **Bound direction:** Algorithmic upper bound.
* **Assumptions:** Execution follows a suitable variable ordering derived from a width-$b$ decomposition, with caching enabled.
* **Primary source:** Fahiem Bacchus, Shannon Dalmao, and Toniann Pitassi, "Solving #SAT and Bayesian Inference with Backtracking Search," *Journal of Artificial Intelligence Research (JAIR)*, Vol. 34, pp. 391–442, 2009. DOI: `10.1613/jair.2648`; arXiv:`1401.3458`. **Locator:** Theorem 2 and Section 2.5.
* **What it does NOT establish:** Does not apply to uncached DPLL baselines or arbitrary branching heuristics, and does not provide a linear-space guarantee.

#### **T7 — SETH-Conditional Optimality of $2^{\mathrm{tw}(G_P(F))}$ for General CNF SAT `[Proved conditional on Conjecture]`**

* **Exact computational model:** Deterministic RAM (under deterministic SETH). *(For randomized algorithms, an explicit randomized SETH hypothesis and error convention must be stated separately; deterministic SETH does not silently imply randomized lower bounds.)*
* **Representation:** Primal graph $G_P(F)$ (or supplied width-$k$ tree decomposition of $G_P(F)$).
* **Quantifiers & parameters:** Assume **deterministic SETH** `[Conjecture]` (for $s_k = \inf\{\delta : k\text{-SAT is deterministically decidable in } O(2^{\delta n})\}$, $\lim_{k \to \infty} s_k = 1$). Then for every fixed $\varepsilon \in (0, 1)$, there is no deterministic algorithm deciding arbitrary CNF SAT in time $(2 - \varepsilon)^{\mathrm{tw}(G_P(F))} \cdot \mathrm{poly}(|F|)$ (nor in time $(2 - \varepsilon)^k \cdot \mathrm{poly}(|F|)$ given a supplied decomposition of width $k$).
  * *Direct proof:* Every $n$-variable CNF has $\mathrm{tw}(G_P(F)) \le n - 1$ (witnessed by the single bag containing all $n$ variables), so such an algorithm would solve $k$-SAT in $(2 - \varepsilon)^n \cdot \mathrm{poly}(|F|)$ time for every fixed $k$, contradicting deterministic SETH.
* **Bound direction:** Conditional algorithmic lower bound.
* **Assumptions:** Deterministic SETH holds; input ranges over arbitrary CNF formulas.
* **Primary sources:**
  * Russell Impagliazzo and Ramamohan Paturi, "On the Complexity of $k$-SAT," *JCSS*, Vol. 62, No. 2, pp. 367–375, 2001. DOI: `10.1006/jcss.2000.1727`.
  * Daniel Lokshtanov, Dániel Marx, and Saket Saurabh, "Known Algorithms on Graphs of Bounded Treewidth are Probably Optimal," *ACM Transactions on Algorithms (TALG)*, Vol. 14, No. 2, Article 13, 2018. DOI: `10.1145/3170442`.
* **What it does NOT establish:** Unconditional lower bounds; and does **not** apply to Tseitin formulas, which are a polynomial-time solvable subclass of CNF regardless of primal treewidth.

---

### 3.3 Tseitin Resolution Lower Bounds & Graph Width Characterizations

#### **T8 — Exponential Resolution Lower Bound for Tseitin on 2D Square Grids `[Proved]`**

* **Exact proof system:** Unrestricted (DAG-like) Resolution, and consequently Regular Resolution ($S_R \ge S$).
* **Representation:** Underlying $k \times k$ square grid graph $G_{k \times k}$ ($|V| = k^2$, $\Delta \le 4$, $k \ge 2$).
* **Quantifiers & parameters:** For every $k \ge 2$ and every odd-charge function $f : V(G_{k \times k}) \to \{0, 1\}$:

  $$
  S_R(\mathrm{Tseitin}(G_{k \times k}, f)) \ge S(\mathrm{Tseitin}(G_{k \times k}, f)) \ge 2^{\Omega(k)}.
  $$

* **Verified derivation:**
  1. *Bounded cyclicity:* In $G_{k \times k}$ ($k \ge 2$), every edge lies on a unit-square $4$-cycle and belongs to at most $2$ such cycles, so the graph's cyclicity (Alekhnovich & Razborov 2011, Definition 2.14) is bounded by $4$. By Theorem 2.15, $W(\mathrm{Tseitin}(G_{k \times k}, f) \vdash \bot) \le O(\log S(\mathrm{Tseitin}(G_{k \times k}, f)))$.
  2. *Balanced cut lower bound:* For any $U \subseteq V(G_{k \times k})$ with $\lceil k^2/3 \rceil \le |U| \le \lfloor 2k^2/3 \rfloor$, if at least $k/3$ rows intersect both $U$ and $V \setminus U$, each contributes at least $1$ horizontal cut edge; otherwise, balance forces at least one all-$U$ row and one all-$(V \setminus U)$ row, so every one of the $k$ columns contributes at least $1$ vertical cut edge. Hence $e(G_{k \times k}) \ge \Omega(k)$, so $W \ge \Omega(k)$ by BSW Theorem 4.4.
  3. Combining (1) and (2) gives $S(\mathrm{Tseitin}(G_{k \times k}, f)) \ge 2^{\Omega(k)}$ (and therefore also $S_R \ge 2^{\Omega(k)}$).
* **Bound direction:** Exponential lower bound in $k = \sqrt{|V|}$ for **unrestricted** and regular Resolution.
* **Primary sources:**
  * Michael Alekhnovich and Alexander A. Razborov, "Satisfiability, Branch-width and Tseitin Tautologies," *Computational Complexity*, Vol. 20, No. 4, pp. 649–678, 2011. DOI: `10.1007/s00037-011-0033-1`. **Locator:** Definition 2.14 and Theorem 2.15.
  * Ben-Sasson and Wigderson (2001), DOI: `10.1145/375827.375835`. **Locator:** Theorem 4.4.
  * *Historical note (`OPEN` for exact original wording):* G. S. Tseitin (1968, 1983 reprint DOI: `10.1007/978-3-642-81955-1_28`) introduced these contradictions and established early regular Resolution lower bounds; the exact 1968 theorem wording was not independently inspected in the original text during Phase 4, so the verified derivation above is the primary basis for T8.
* **What it does NOT establish:** Proof-size lower bound for Resolution only; does not bound parity-aware algorithms or proof systems such as PC($\mathbb{F}_2$), Frege, or Extended Resolution.

#### **T9 — Exponential General Resolution Lower Bound on Constant-Degree Expanders `[Proved]`**

* **Exact proof system:** Unrestricted Resolution.
* **Representation:** Connected constant-degree simple graph families $\{G_m\}$ ($\Delta(G_m) = O(1)$) with linear balanced edge expansion $e(G_m) = \Omega(|V(G_m)|)$.
* **Quantifiers & parameters:** For such families and every odd-charge function $f$, $S(\mathrm{Tseitin}(G_m, f)) = 2^{\Omega(|V(G_m)|)}$ (with $O(|V|)$ clauses and $O(|V|)$ literal occurrences for fixed degree).
* **Bound direction:** Exponential lower bound on unrestricted Resolution proof lines.
* **Assumptions:** Connectedness, odd total charge, constant maximum degree, and proved linear balanced edge expansion.
* **Primary sources:**
  * Alasdair Urquhart, "Hard Examples for Resolution," *JACM*, Vol. 34, No. 1, pp. 209–219, 1987. DOI: `10.1145/7531.8928`.
  * Ben-Sasson and Wigderson (2001), DOI: `10.1145/375827.375835`. **Locator:** Theorem 4.4 and Corollary 4.5.
* **What it does NOT establish:** Does not imply every sampled regular graph satisfies the expansion hypothesis (expansion must be verified for the family), nor does it apply beyond Resolution.

#### **T10 — BSW Tseitin Width and Size Lower Bounds via Balanced Edge Expansion `[Proved]`**

* **Exact proof system:** Unrestricted Resolution.
* **Representation:** Connected simple undirected graph $G = (V, E)$ with $|V| \ge 2$, $|E| \ge 1$, maximum degree $\Delta$, and balanced edge expansion $e(G)$.
* **Quantifiers & parameters:** For every odd-charge function $f$:
  1. $W(\mathrm{Tseitin}(G, f) \vdash \bot) \ge e(G)$.
  2. Combining with T2 ($n = |E|$, $w_0 = \Delta$, proof length counting clauses appearing in the refutation):

     $$
     S(\mathrm{Tseitin}(G, f)) \ge \exp\!\left(\Omega\!\left(\frac{\max(0, e(G) - \Delta)^2}{|E|}\right)\right).
     $$

* **Critical Counterexample Guard (`[Proved]`):** The $\max(0, \cdot)$ clamp (or explicit hypothesis $e(G) \ge \Delta$) is mandatory. On the **star graph** $K_{1,m}$ ($m \ge 2$, center charge $1$, leaf charges $0$), $\Delta = m$, $|E| = m$, and $e(K_{1,m}) = \lceil (m+1)/3 \rceil < m$. Squaring $e(G) - \Delta$ without clamping falsely predicts $2^{\Omega(m)}$ lines, whereas resolving the center clause $(x_1 \lor \dots \lor x_m)$ with the $m$ negative leaf unit clauses refutes $\mathrm{Tseitin}(K_{1,m}, f)$ in at most $2m + 1$ proof lines. Likewise, $K_{1,m}$ is **planar** with linear edge expansion, refuting any claim that $e(G) = O(\sqrt{|E|})$ holds for arbitrary planar graphs without a bounded-degree hypothesis.
* **Primary source:** Ben-Sasson and Wigderson (2001), DOI: `10.1145/375827.375835`. **Locator:** Theorem 4.4 and Theorem 3.5.
* **What it does NOT establish:** Non-trivial size lower bounds whenever $e(G) - \Delta = O(\sqrt{|E|})$ (e.g., bounded-degree planar graphs); if a non-standard size convention counts all unused input clauses, T2's formula does not transfer directly without restatement.

#### **T11 — Branchwidth, Treewidth, and Resolution on Tseitin Formulas `[Proved]`**

* **Exact proof system:** Regular Resolution (constructive upper bound) and Unrestricted / Tree-like Resolution (width and tree-like lower bounds).
* **Representation:** Strictly distinguishes (1) the **clause-indexed multihypergraph** $H(F)$ retaining repeated identical-support clause hyperedges (Section 1.3(4); Alekhnovich–Razborov, Remark 2.11), (2) underlying graph treewidth $\mathrm{tw}(G)$, and (3) primal/line-graph treewidth $\mathrm{tw}(L(G))$.
* **Quantifiers & parameters:**
  * **General CNF Constructive Upper Bound (Theorem 2.3 — applies to all CNFs $F$):** There is a deterministic algorithm running in time $\mathrm{poly}(|F| + 2^{\mathrm{bw}(H(F))})$ that outputs either a satisfying assignment or a **regular Resolution** refutation of width $O(\mathrm{bw}(H(F)))$.
  * **Tseitin Width–Branchwidth Equivalence (Theorem 2.12 — restricted to connected odd-charge graphs, Definition 2.8):** For connected simple graphs $G$ with odd total charge $f$, $\mathrm{bw}(H(T(G, f))) = \Theta(W(T(G, f) \vdash \bot))$.
  * **Tseitin Width-Automatability (Theorem 2.13 — connected odd-charge graphs, Definition 2.8):** Tseitin contradictions on connected odd-charge graphs are width-automatable in the sense of the source.
  * **Bounded Cyclicity (Theorem 2.15):** For bounded-cyclicity graphs, $W \le O(\log S)$ (yielding T8 on 2D grids).
  * **Explicit Conservative Treewidth Upper-Bound Bridge (`[Proved]`):** Combining the multihypergraph-to-primal-treewidth bridge $\mathrm{bw}(H(F)) \le \mathrm{tw}(G_P(F)) + 1$ (Section 1.3(4)) with $\mathrm{tw}(L(G)) \le \Delta(\mathrm{tw}(G) + 1) - 1$ (Section 1.3(2)) yields $\mathrm{bw}(H(T(G, f))) \le \Delta(\mathrm{tw}(G) + 1)$ for every simple graph $G$ of maximum degree $\Delta$ (with $E \neq \emptyset$; for $E = \emptyset$, odd-charge Tseitin contains the empty clause directly). Applying Theorem 2.3 produces a regular Resolution refutation (and runtime) of size $\mathrm{poly}(|F| + 2^{\Delta(\mathrm{tw}(G)+1)}) = \mathrm{poly}(|F|) \cdot 2^{O(\Delta(\mathrm{tw}(G)+1))}$ (hence $\mathrm{poly}(|F|) \cdot 2^{O(\mathrm{tw}(G))}$ for bounded degree $\Delta = O(1)$).
  * **Tree-like Lower Bound:** Follows by substituting an independently established width lower bound (e.g., T10 or T12) into T1, accounting for initial width $\Delta$.
* **Primary source:** Michael Alekhnovich and Alexander A. Razborov, "Satisfiability, Branch-width and Tseitin Tautologies," *Computational Complexity*, Vol. 20, No. 4, pp. 649–678, 2011 (preliminary: *FOCS 2002*). DOI: `10.1007/s00037-011-0033-1`. **Locator:** Definition 2.8, Remark 2.11, and Theorems 2.3, 2.12, 2.13, and 2.15.
* **What it does NOT establish:** Does not equate heuristic min-fill elimination width with exact multihypergraph branchwidth or optimal proof size; Theorems 2.12–2.13 do not apply to arbitrary satisfiable or disconnected parity systems outside Definition 2.8.

#### **T12 — Exact Characterization of Tseitin Resolution Width via Line-Graph Treewidth `[Proved]`**

* **Exact proof system:** Unrestricted Resolution (minimum refutation width).
* **Representation:** Underlying finite connected simple graph $G = (V, E)$ and its **line graph** $L(G)$.
* **Quantifiers & parameters:** For every finite connected simple graph $G$ and every odd-charge marking $c : V \to \{0, 1\}$, under the source's refutation-width convention and standard treewidth ($\max\text{ bag size} - 1$, with $\mathrm{tw}(\emptyset) = -1$ for the trivial edgeless graph $K_1$ whose Tseitin formula is $\{\bot\}$ of width $0$):

  $$
  W(T(G, c) \vdash \bot) = \max\!\left(\Delta(G),\; \mathrm{tw}(L(G))\right).
  $$

  * *Derivation from source corollaries:* Corollary 8 (printed p. 12) establishes $W(T(G, c) \vdash \bot) = \max(\Delta(G), \mathrm{ec}(G) - 1)$ via the edge cops-and-robber number $\mathrm{ec}(G)$; Corollary 16 (printed p. 15) establishes $\mathrm{ec}(G) = \mathrm{tw}(L(G)) + 1$.
  * *Cubic specialization:* For a connected simple $3$-regular graph $G$, $G_P(T(G, c)) = L(G)$, so $W(T(G, c) \vdash \bot) = \max(3, \mathrm{tw}(G_P(T(G, c))))$.
* **Refuted Prior Claim (`[Proved]`):** The earlier draft's upper bound $\mathrm{tw}(G) + \Delta$ is **false**. Counterexample: $G = K_8$ has $\mathrm{tw}(K_8) = 7$ and $\Delta(K_8) = 7$ ($\mathrm{tw} + \Delta = 14$), whereas every balanced cut has side sizes $3, 4,$ or $5$, giving $e(K_8) = \min(15, 16, 15) = 15 > 14$, so $W(T(K_8, c) \vdash \bot) \ge 15$ by BSW Theorem 4.4.
* **Primary source:** Nicola Galesi, Navid Talebanfard, and Jacobo Torán, "Cops-Robber Games and the Resolution of Tseitin Formulas," ECCC Report `TR18-170`, 2018 (`https://eccc.weizmann.ac.il/report/2018/170/`; conference version: *SAT 2018*, LNCS 10929, pp. 311–326, DOI: `10.1007/978-3-319-94144-8_19`; journal version: *ACM Transactions on Computation Theory*, Vol. 12, No. 2, Article 9, pp. 9:1–9:22, 2020, DOI: `10.1145/3378667`). **Locator (mathematical basis):** ECCC `TR18-170`, Corollary 8 (p. 12) and Corollary 16 (p. 15).
* **What it does NOT establish:** Characterizes minimum Resolution *width*, not DPLL branch counts, runtime, or arbitrary SAT complexity; a heuristic min-fill elimination width on $G_P(T(G,c))$ is only an upper bound on $\mathrm{tw}(L(G))$ unless independently proved optimal.

---

### 3.4 Resolution Fragment Separations and Practical SAT Solver Models

#### **T13 — Exponential Separations Involving Tree-like Resolution `[Proved]`**

Two distinct separations are recorded separately without conflating their upper-bound proof systems:

* **Part A — Tree-like vs. Regular Resolution:** The modified ordering formulas $MGT_n$ admit **polynomial-size Regular Resolution** refutations while requiring **Tree-like Resolution** size $2^{\Omega(n)}$.
  * *Primary source:* Bonet and Galesi (2001), DOI: `10.1007/s000370100000`. **Locator:** Theorems 3.2, 4.1, and 4.2.
* **Part B — Tree-like vs. Unrestricted (General) Resolution:** There exists an explicit family of unsatisfiable pebbling-based CNFs of size $O(n)$ having **linear-size Unrestricted Resolution** refutations ($S = O(n)$) while requiring **Tree-like Resolution** size $S_T = \exp(\Omega(n / \log n))$.
  * *Primary source:* Eli Ben-Sasson, Russell Impagliazzo, and Avi Wigderson, "Near Optimal Separation of Tree-Like and General Resolution," *Combinatorica*, Vol. 24, No. 4, pp. 585–603, 2004. DOI: `10.1007/s00493-004-0036-5`. **Locator:** Theorem 1.
* **What it does NOT establish:** These are proof-system separations on specialized ordering/pebbling families, not automatically separations on unmodified Tseitin contradictions.

#### **T14 — Exponential Separation of Regular vs. Unrestricted Resolution `[Proved]`**

* **Exact proof systems:** Regular Resolution vs. Unrestricted Resolution.
* **Representation:** Modified ordering formulas $GT'_{n,\rho}$, parameterized by $n$ = number of ordering elements, having $\Theta(n^2)$ Boolean variables and $O(n^3)$ clauses.
* **Quantifiers & parameters:**
  * For every appropriate $\rho$, Unrestricted Resolution refutes $GT'_{n,\rho}$ in size $O(n^3)$.
  * For sufficiently large $n$, there exists $\rho$ such that every Regular Resolution refutation of $GT'_{n,\rho}$ requires more than $2^{n/200}$ proof lines.
* **Primary source:** Michael Alekhnovich, Jan Johannsen, Toniann Pitassi, and Alasdair Urquhart, "An Exponential Separation between Regular and General Resolution," *Theory of Computing*, Vol. 3, Article 5, pp. 81–102, 2007. DOI: `10.4086/toc.2007.v003a005`. **Locator:** Definition 3.3, Corollary 3.4, and Theorem 3.10.
* **Historical note (`OPEN` for exact exponents):** Andreas Goerdt ("Regular Resolution Versus Unrestricted Resolution," *SIAM J. Comput.*, Vol. 22, No. 4, pp. 661–683, 1993, DOI: `10.1137/0222044`) established the first super-polynomial separation, and Alasdair Urquhart ("A Near-Optimal Separation of Regular and General Resolution," *SIAM J. Comput.*, Vol. 40, No. 1, pp. 107–121, 2011, DOI: `10.1137/090772897`) established a near-optimal separation; their exact numerical exponents are omitted from the approved bound above pending direct primary-text locator checks.
* **What it does NOT establish:** Does not establish a super-polynomial gap between Regular and Unrestricted Resolution on standard Tseitin contradictions (cf. Section 5 on newly reported 2026 results).

#### **T15 — Operational Simulation Models for CDCL (CLR) and DRUP `[Proved]`**

* **Part A — Clause Learning with Restarts (CLR) vs. Unrestricted Resolution:** In Pipatsrisawat and Darwiche's CLR model equipped with an asserting clause-learning scheme, suitable extended branching sequences, and restarts, CLR polynomially simulates Unrestricted Resolution (and vice versa).
  * *Primary source:* Knot Pipatsrisawat and Adnan Darwiche, "On the Power of Clause-Learning SAT Solvers as Resolution Engines," *Artificial Intelligence*, Vol. 175, No. 2, pp. 512–525, 2011. DOI: `10.1016/j.artint.2010.10.002`. **Locator:** Theorems 1 and 2, Corollary 1.
* **Part B — DRUP vs. Unrestricted Resolution:** Every valid non-tautological Reverse Unit Propagation (RUP) clause addition converts into a Resolution derivation of a subclause (with polynomial overhead by recording unit-propagation reasons, followed by subsumption/weakening elimination); tautological steps can be discarded, and clause deletion introduces no new logical consequences. Conversely, every ordinary Resolution inference is a RUP addition. Hence DRUP $\equiv_p$ Unrestricted Resolution.
  * *Primary source:* Benjamin Kiesl, Adrián Rebola-Pardo, and Marijn J. H. Heule, "Extended Resolution Simulates DRAT," *IJCAR 2018*, LNCS 10900, pp. 516–531, 2018. DOI: `10.1007/978-3-319-94205-6_34`. **Locator:** Theorem 2 and Section 4.4.
* **What it does NOT establish (Critical Experimental Guard):**
  * Existence of a polynomial simulation under idealized branching/restarts does **not** guarantee that a deterministic CDCL heuristic (such as VSIDS) finds short proofs when they exist.
  * **Wall-clock runtime and conflict counts are NOT automatically upper bounds on minimum Resolution proof size.** Only a concrete, independently verified Resolution proof (or a verified DRUP proof after accounting for RUP-to-Resolution translation overhead) witnesses an upper bound under its actual size measure.
  * A DRAT proof utilizing RAT steps cannot be treated as a pure Resolution proof.

#### **T16 — Equivalence of DRAT and Extended Resolution `[Proved]`**

* **Exact proof systems:** DRAT (Deletion Resolution Asymmetric Tautology) and Extended Resolution (ER), under their standard definitions permitting fresh extension variables.
* **Quantifiers & parameters:** DRAT and ER polynomially simulate each other.
  * *DRAT $\to$ ER:* Explicitly constructed and analyzed in Kiesl, Rebola-Pardo, and Heule (2018), Section 4 (especially Section 4.5).
  * *ER $\to$ DRAT:* Introducing a fresh extension variable $y \leftrightarrow (a \land b)$ via the three clauses $(\neg y \lor a)$, $(\neg y \lor b)$, and $(y \lor \neg a \lor \neg b)$ is valid in DRAT (the first two are RAT on $\neg y$ because $y$ is fresh; the third is RAT on $y$ since its resolvents with the first two are tautologies), and ordinary Resolution inferences are RUP additions.
* **Primary source:** Kiesl, Rebola-Pardo, and Heule (2018), DOI: `10.1007/978-3-319-94205-6_34`. **Locator:** Section 4, especially Section 4.5.
* **What it does NOT establish:** An accepted DRAT certificate does not certify membership in ordinary Resolution, nor does this theorem certify the correctness of a specific software DRAT checker.

---

### 3.5 Algebraic Solving, Polynomial Calculus, and Stronger Proof Systems

#### **T17 — Algebraic Solving & Component Parity Across Three Distinct Input Models `[Proved]`**

The complexity of deciding Tseitin consistency depends strictly on the input representation:

* **Model A — Explicit arbitrary binary linear system ($Ax = f$ over $\mathbb{F}_2$):** Ordinary Gaussian elimination decides consistency in **polynomial time ($\mathrm{P}$)**; when inconsistent, tracking row operations yields a polynomial-bit refutation certificate $y$ satisfying $y^T A = 0$ and $y^T f = 1$. *(This does not place arbitrary binary linear-system consistency in deterministic logspace $\mathrm{L}$.)*
* **Model B — Explicit charged undirected graph $(G, f)$:** Consistent iff every connected component has even total charge (`[Proved]`: necessity by summing equations over a component; sufficiency by setting non-tree edges to $0$ and solving a spanning tree bottom-up from leaves to root).
  * Given an adjacency-list representation, component traversal decides consistency in $O(|V| + |E|)$ graph operations.
  * In **deterministic logspace ($\mathrm{L}$)**, Reingold's undirected connectivity algorithm enumerates vertices, identifies component representatives via undirected reachability, and accumulates each component's charge parity using logarithmic counters.
  * *Primary source:* Omer Reingold, "Undirected Connectivity in Log-Space," *JACM*, Vol. 55, No. 4, Article 17, 2008. DOI: `10.1145/1391289.1391291`; ECCC Report `TR04-094` (`https://eccc.weizmann.ac.il/eccc-reports/2004/TR04-094/`).
* **Model C — Raw CNF without supplied parity metadata:** Parity equations must first be extracted and certified against the input clauses. The time cost and completeness of extraction are separate algorithmic obligations; privileged generator metadata must never be reported as end-to-end general CNF runtime.
* **What it does NOT establish:** Efficient $\mathbb{F}_2$-linear solving yields no general SAT algorithm.

#### **T18 — Polynomial Calculus: Encoding Dependence and Field Characteristic `[Proved]`**

Three distinct polynomial encodings (all scoped to finite simple undirected graphs under Section 1) must be separated:

* **Encoding 1 — Direct linear parity axioms over $\mathbb{F}_2$:** Given axioms $\sum_{e \ni v} x_e - f(v) = 0$ directly, summing the equations of an odd-charged component derives $0 = 1$ in **degree at most $1$** (degree $0$ for an isolated odd vertex whose axiom is $0 = 1$) using $O(|V|)$ addition steps. Because intermediate sums can contain up to $|E|$ edge variables plus a constant term, sequential summation has total monomial-occurrence count $O(|V| \cdot (|E| + 1))$ (note: monomial count is distinct from encoded bit size).
* **Encoding 2 — Standard expanded strict cubic CNF encoded as polynomials over $\mathbb{F}_2$:** Translating each $3$-clause to the product of its falsity indicators produces initial polynomials of **degree $3$**. Over $\mathbb{F}_2$, summing the four degree-$3$ clause polynomials for a cubic vertex recovers its linear parity polynomial (confirmed algebraically for both charges $0$ and $1$). Summing the recovered linear polynomials across an odd component gives a **degree-at-most-$3$** Polynomial Calculus refutation — **not** degree $1$, because the degree-$3$ initial clause polynomials appear in the derivation.
* **Encoding 3 — Odd-characteristic signed formulation $TS_n(2)$:** Buss, Grigoriev, Impagliazzo, and Pitassi (Section 2) define $TS_n(2)$ on a connected simple graph with an **odd number $n$ of vertices** and **all vertex charges equal to $1$** (e.g., bounded even-degree $r$-regular graphs for odd $n$), using signed edge variables $y_e$ subject to $y_e^2 - 1 = 0$ and multiplicative vertex axioms $\prod_{e \ni v} y_e + 1 = 0$.
  * **Expansion hypothesis & lower bound (Theorem 10, p. 15):** Suppose the underlying graph satisfies vertex-neighborhood expansion with parameter $\varepsilon > 0$: for every $S \subseteq V$ with $|S| \le n/2$, $|N(S)| \ge (1 + \varepsilon)|S|$ *(distinct from balanced edge expansion $e(G)$)*. Over any field with $\mathrm{char}(\mathbb{F}) \neq 2$, there is **no Polynomial Calculus refutation of $TS_n(2)$ of degree $d < \varepsilon n / 8$**.
  * **Characteristic-2 degeneracy:** In $\mathrm{char}(\mathbb{F}) = 2$, $1 = -1$ makes the signed system $TS_n(2)$ satisfiable (e.g., $y_e = 1$), so Encoding 1 and Encoding 3 are not literally the same polynomial input.
  * **Transfer obligation:** Transferring Theorem 10's bound to arbitrary odd charge markings, to balanced edge expansion $e(G)$, to the team's expanded cubic Boolean CNF encoding, or to monomial-size lower bounds requires separate justified reductions and size–degree theorems.
* **Primary sources:**
  * Matthew Clegg, Jeffery Edmonds, and Russell Impagliazzo, "Using the Groebner Basis Algorithm to Find Proofs of Unsatisfiability," *Proceedings of the 28th Annual ACM Symposium on Theory of Computing (STOC '96)*, pp. 174–183, 1996. DOI: `10.1145/237814.237860`.
  * Sam Buss, Dima Grigoriev, Russell Impagliazzo, and Toniann Pitassi, "Linear Gaps between Degrees for the Polynomial Calculus Modulo Distinct Primes," *JCSS*, Vol. 62, No. 2, pp. 267–289, 2001. DOI: `10.1006/jcss.2000.1726`. **Locator:** Section 2 and Theorem 10 (p. 15).
* **What it does NOT establish:** Does not prove lower bounds for PC over $\mathbb{F}_2$ on Tseitin, and does not automatically transfer signed-encoding degree lower bounds to Boolean CNF polynomial encodings without explicit translation bounds.

#### **T19 — Direct Parity Sums, Frege, Extended Resolution, and `OPEN` $\mathrm{Res}(\oplus)$ `[Proved / OPEN locator]`**

* **Direct linear equations (parity axioms supplied) `[Proved]`:** Summing the vertex parity equations over an odd-charged component derives $0 = 1$ in $O(|V|)$ addition steps and $O(|V| \cdot (|E| + 1))$ symbols under unit-cost variable names (bit-encoded variable identifiers may add logarithmic factors; an isolated odd vertex is already contradictory and requires no large construction).
* **Frege, Extended Resolution, and DRAT on bounded-degree Tseitin CNF `[Proved]`:**
  * *Primary construction:* Urquhart (1987), Section 6, Lemma 6.1 and Theorem 6.2 (pp. 217–218) explicitly construct polynomial-size axiomatic proofs for the graph family treated there.
  * *Bounded-degree extension:* For any finite simple graph of fixed maximum degree $\Delta$ with an odd-charged component (handling isolated odd vertices directly via the empty clause), convert each vertex's expanded CNF block into its local parity identity using constant-size local reasoning in a Frege basis containing the biconditional; chain the parity identities across the odd component; and apply associativity and commutativity to bring duplicate edge occurrences together and cancel pairs, deriving a contradiction. For bounded $\Delta$, both the number of swaps and the intermediate formula sizes are polynomial in $|V|$. Because standard Frege systems polynomially simulate one another (Cook & Reckhow 1979), this yields polynomial-size proofs in any standard Frege system; Extended Resolution simulates these steps via extension definitions (or iterative XOR definitions directly), and T16 transfers the polynomial upper bound to DRAT.
  * *Primary sources:*
    * Alasdair Urquhart, "Hard Examples for Resolution," *JACM*, Vol. 34, No. 1, pp. 209–219, 1987. DOI: `10.1145/7531.8928`. **Locator:** Section 6, Lemma 6.1 and Theorem 6.2 (pp. 217–218).
    * Stephen A. Cook and Robert A. Reckhow, "The Relative Efficiency of Propositional Proof Systems," *The Journal of Symbolic Logic*, Vol. 44, No. 1, pp. 36–50, 1979. DOI: `10.2307/2273702`.
    * Kiesl, Rebola-Pardo, and Heule (2018), DOI: `10.1007/978-3-319-94205-6_34`.
* **$\mathrm{Res}(\oplus)$ — Status `OPEN` (excluded from `[Proved]` bounds):** Dmitry Itsykson and Dmitry Sokolov introduced Resolution over linear equations modulo $2$ ("Resolution over Linear Equations Modulo Two," *Annals of Pure and Applied Logic*, Vol. 171, No. 1, 102722, 2020, DOI: `10.1016/j.apal.2019.102722`). Earlier drafts asserted an exact linear $O(|V|+|E|)$ tree-like $\mathrm{Res}(\oplus)$ proof size; that unverified total-symbol-size bound remains **removed / `OPEN`** pending direct primary-text verification of the proof-rule conventions, CNF-to-linear-equation local derivation cost, and total encoded symbol count (distinct from line/step count).
* **What it does NOT establish:** Polynomial-size proofs for bounded-degree Tseitin formulas do not imply polynomial boundedness of Frege, ER, DRAT, or $\mathrm{Res}(\oplus)$ on general tautologies.

---

## 4. Scope & Distinction Audit: Known Theory vs. Operation Millennium Experiments

Mathematical proof-complexity theorems and empirical SAT-solver measurements answer **different questions** and must not be conflated as "subsumed" by one another. Untested predictive or performance hypotheses are labeled `[Conjecture]`; `[Empirical Observation]` is reserved strictly for actually executed measurements.

| Project Topic / Hypothesis | Mathematical Status | Empirical / Experimental Distinction | Honest Classification |
| :--- | :--- | :--- | :--- |
| **Componentwise parity iff consistency** | Known `[Proved]` theorem (T17 Model B). | `lean/Millennium/Tseitin.lean` formalizes **global odd-charge unsatisfiability** (`[Lean-Verified]` at `dev @ 1905067`), distinct from the full componentwise `iff` theorem on disconnected graphs. | Componentwise `iff`: `[Proved]`. Global UNSAT Lean theorem: `[Lean-Verified]`. |
| **Graph / line-graph treewidth vs. minimum Resolution width** | Exact characterization $W = \max(\Delta(G), \mathrm{tw}(L(G)))$ is `[Proved]` (T12). | Whether a fast heuristic width estimator (such as deterministic min-fill elimination width) strongly predicts practical solver decisions or runtimes is an untested/separately tested empirical question. | Width characterization: `[Proved]`. Untested predictor hypothesis: `[Conjecture]` (executed runs only: `[Empirical Observation]`). |
| **Low-width vs. high-width CDCL / DPLL solver behavior on matched cubic Tseitin suites** | Proof-complexity bounds (T8–T12, T15) constrain minimum proof size/width under idealized proof systems. | Actual solver behavior depends on branching heuristic, clause learning, restarts, preprocessing, and encoding; proof-complexity bounds do **not** theorem-level subsume concrete solver dynamics. | Untested scaling hypothesis: `[Conjecture]`; executed solver measurements: `[Empirical Observation]` (never a proof-complexity lower bound). |
| **Primal treewidth $\mathrm{tw}(G_P)$ vs. underlying treewidth $\mathrm{tw}(G)$ as solver predictors** | $\mathrm{tw}(L(G)) \le \Delta(\mathrm{tw}(G)+1)-1$ and T12 relate exact widths (`[Proved]`). | Graph-theoretic inequalities do not prove which feature yields higher empirical predictive accuracy for a specific solver and branch budget. | Untested feature-comparison hypothesis: `[Conjecture]`; measured results: `[Empirical Observation]`. |
| **XOR / Gaussian extraction acceleration on raw CNF inputs** | Explicit arbitrary $\mathbb{F}_2$ linear systems are decidable in **polynomial time ($\mathrm{P}$)**; explicit charged undirected graph parity consistency is in **deterministic logspace ($\mathrm{L}$)** by connectivity and parity accumulation (T17 Models A & B; `[Proved]`). | End-to-end extraction from raw CNF without metadata (T17 Model C), certification overhead, and practical speedup on mixed/structured CNF populations are separate algorithmic and empirical properties. | Algebraic/graph upper bounds: `[Proved]`. Untested end-to-end CNF speedup: `[Conjecture]` (executed benchmarks only: `[Empirical Observation]`). |
| **Comparing practical certified proof size against theoretical upper bounds** | Existential/constructive upper bounds (T11, T15, T16) exist for specific proof formats. | Benchmarking concrete DRUP vs. DRAT proof sizes against width bounds is valid empirical measurement only when proof formats and size conventions are kept strictly separate. | Upper bounds: `[Proved]`; executed proof-trace benchmarks: `[Empirical Observation]`. |
| **Unrestricted Resolution on 2D grids** | **Not open:** $S \ge 2^{\Omega(k)}$ is `[Proved]` via bounded cyclicity (T8). | Small-scale grid runs measure concrete solver scaling; they do not probe an open lower-bound boundary. | Theory: `[Proved]` (T8); executed runs: `[Empirical Observation]`. |

### Project Scope Statement

No result currently established by Operation Millennium on Tseitin formulas resolves $\mathrm{P}$ vs. $\mathrm{NP}$. Tseitin contradictions remain a rigorous testbed for separating semantic satisfiability, restricted proof-system complexity, graph-width parameters, certified proof formats (DRUP vs. DRAT), and certified algebraic extraction from raw CNF.

---

## 5. Newly Reported Literature (November 2026 — `ACE-R11-22`, Technical Audit `OPEN`)

> **Claim Status:** `Empirical Observation` (publication record and reported theorem statements inspected on ECCC); **`OPEN`** for independent team technical proof audit (Sections 5–8 have **not** been audited line-by-line by Operation Millennium; per `docs/RULES.md`, these results are **not** adopted as team-audited `Proved` or `Lean-Verified` theorems yet).

* **Preprint:** Dmitry Itsykson and Petr Smirnov, "Resolution Is Automatable on Tseitin Formulas," ECCC Report `TR26-332` (paper dated November 21, 2026; ECCC publication record November 22, 2026; `https://eccc.weizmann.ac.il/report/2026/332/`).
* **Reported Results (as stated by the authors in Section 1.2, p. 4):**
  1. **Theorem 1.1 / Corollary 5.4:** For connected $G$ with odd charge, $S(T(G, c)) \ge 2^{\Omega(\mathrm{tw}(G))}$.
  2. **Theorem 1.2 / Theorem 6.1:** For connected $G$ with odd charge, $S(T(G, c)) + |T(G, c)| \ge 2^{\Omega(\mathrm{tw}(L(G)))}$.
  3. **Corollary 1.3 / Corollary 8.1:** For $2$-edge-connected graphs (connected, $|V| \ge 2$, bridgeless) with odd charge, $S(T(G, c)) \ge 2^{\Omega(\mathrm{tw}(L(G)))}$.
  4. **Theorem 1.4 / Theorem 7.1:** Both regular and unrestricted Resolution are reported to be automatable on Tseitin contradictions, producing regular refutations in time polynomial in the encoded input length $\ell(F)$ and minimum unrestricted refutation length $S(F)$.
  5. **Theorem 1.5 / Theorem 8.2:** There exists an absolute constant $C$ such that $S(F) \le S_R(F) \le S(F)^C$ for every Tseitin contradiction $F$.
* **Project Handling:**
  * Do not mischaracterize these as conjectures of the authors (they report proved theorems) and do not treat them as an Operation Millennium discovery.
  * Do not infer automatability of general Resolution on arbitrary CNFs from automatability on Tseitin formulas.
  * Keep technical adoption **`OPEN`** pending a dedicated proof audit (`docs/phase5/TR26_332_PROOF_AUDIT.md`).