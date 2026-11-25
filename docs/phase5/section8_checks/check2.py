import itertools

def line_graph(edges):
    m = len(edges)
    adj = [set() for _ in range(m)]
    for i in range(m):
        for j in range(i + 1, m):
            if set(edges[i]) & set(edges[j]):
                adj[i].add(j)
                adj[j].add(i)
    return adj

def exact_treewidth(adj):
    """Exact treewidth via minimum elimination width over all permutations (for |V| <= 10)."""
    n = len(adj)
    if n == 0:
        return -1
    # DP over subsets: tw(G) = min over elimination orders of max clique-1
    # Memoized bitmask DP: min width to eliminate remaining set S (where edges added among neighbors of eliminated)
    # Easier: for n <= 10, standard subset DP using Q-sets (Bodlaender et al.):
    # For small n <= 8, just do bitmask DP on eliminated set S:
    # Actually let's compute neighbors in filled graph: two vertices u,v in V\S are adjacent in filled(G, S)
    # iff u-v in G or there is a path from u to v with all internal vertices in S.
    # Then when eliminating v next (v in V\S), its degree in filled(G, S) is |N_{filled(G, S)}(v) \cap (V\S)|!
    # Wait: that depends ONLY on S (not the order within S)! That's the classic O(2^n n^2) exact treewidth DP!
    full = (1 << n) - 1
    adj_mask = [0] * n
    for i in range(n):
        for j in adj[i]:
            adj_mask[i] |= (1 << j)

    # Precompute for each S and each v not in S, the set of vertices in V\S reachable from v via S
    from functools import lru_cache
    @lru_cache(maxsize=None)
    def filled_deg(S, v):
        # BFS inside S starting from neighbors of v
        vis = 0
        q = adj_mask[v] & S
        vis |= q
        # Also direct neighbors outside S
        out_nbrs = adj_mask[v] & (~S) & (~(1 << v)) & full
        while q:
            lsb = q & -q
            u = lsb.bit_length() - 1
            q ^= lsb
            out_nbrs |= adj_mask[u] & (~S) & (~(1 << v)) & full
            nxt = adj_mask[u] & S & (~vis)
            vis |= nxt
            q |= nxt
        return out_nbrs.bit_count()

    dp = [10**9] * (1 << n)
    dp[full] = 0
    for S in range(full - 1, -1, -1):
        best = 10**9
        rem = full ^ S
        tmp = rem
        while tmp:
            lsb = tmp & -tmp
            v = lsb.bit_length() - 1
            tmp ^= lsb
            d = filled_deg(S, v)
            val = max(d, dp[S | lsb])
            if val < best:
                best = val
        dp[S] = best
    return dp[0]

graphs = {
    "B2": [(0,1),(0,1)],
    "B3": [(0,1),(0,1),(0,1)],
    "K3": [(0,1),(1,2),(2,0)],
    "K4": [(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)],
    "K5": [(i,j) for i in range(5) for j in range(i+1,5)],
}
for name, es in graphs.items():
    lg = line_graph(es)
    tw = exact_treewidth(lg)
    print(f"{name}: |V|={max(max(e) for e in es)+1}, |E|={len(es)}, |V(L)|={len(lg)}, exact tw(L({name})) = {tw}")

# Also test Fixture 5: K_{1,3} (unsat) U K_4 (sat) U K_5 (unsat)
# Compute exact Tseitin clause counts and DP refutation sizes for K_{1,3} and K_5
k13_edges = [(0,1),(0,2),(0,3)]
k13_charges = {0:1, 1:0, 2:0, 3:0}
k13_cls = [cl for cls in make_tseitin_clauses(4, k13_edges, k13_charges).values() for cl in cls]
n13, t13 = dp_regular_refutation(k13_cls)
r13 = check_proof(n13, t13, set(k13_cls))

k5_edges = graphs["K5"]
k5_charges = {0:1, 1:0, 2:0, 3:0, 4:0}
k5_cls = [cl for cls in make_tseitin_clauses(5, k5_edges, k5_charges).values() for cl in cls]
n5, t5 = dp_regular_refutation(k5_cls)
r5 = check_proof(n5, t5, set(k5_cls))

k4_edges = graphs["K4"]
k4_charges = {0:0, 1:0, 2:0, 3:0}
k4_cls = [cl for cls in make_tseitin_clauses(4, k4_edges, k4_charges).values() for cl in cls]

print(f"F5 comp1 K1,3 (UNSAT): |T|={len(k13_cls)}, DP regular DAG={r13['dag_size']}, used_ax={r13['used_axioms']}")
print(f"F5 comp2 K4   (SAT):   |T|={len(k4_cls)}")
print(f"F5 comp3 K5   (UNSAT): |T|={len(k5_cls)}, DP regular DAG={r5['dag_size']}, used_ax={r5['used_axioms']}, Cor 8.1 forced axioms at deg-4 v >= 2^(4-1)=8")
print(f"F5 total: n=13, |E|=19, |T(G,c)|={len(k13_cls)+len(k4_cls)+len(k5_cls)}")


