import itertools
from collections import defaultdict, deque

def make_tseitin_clauses(num_verts, edges, charges):
    """
    edges: list of (u, v) for edge index 0..m-1 (loopless multigraph)
    charges: dict v -> 0/1
    Returns dict v -> list of frozenset of literals (int: +(e+1) for x_e, -(e+1) for ~x_e)
    """
    inc = defaultdict(list)
    for idx, (u, v) in enumerate(edges):
        assert u != v, "Loop not allowed"
        inc[u].append(idx + 1)
        inc[v].append(idx + 1)
    clauses_by_v = {}
    for v in range(num_verts):
        vars_v = inc[v]
        d = len(vars_v)
        c = charges[v] % 2
        if d == 0:
            clauses_by_v[v] = [frozenset()] if c == 1 else []
        else:
            cls = []
            for bits in itertools.product([0, 1], repeat=d):
                if sum(bits) % 2 != c:
                    # forbid this assignment: literal is +var if bit==0, -var if bit==1
                    cl = frozenset(var if b == 0 else -var for var, b in zip(vars_v, bits))
                    cls.append(cl)
            clauses_by_v[v] = cls
    return clauses_by_v

def dp_regular_refutation(clauses, elim_order=None):
    """
    Weakening-free regular (ordered Davis-Putnam) resolution refutation of an UNSAT CNF.
    Returns list of nodes: (clause, rule, parents, pivot)
      rule in {'axiom', 'res'}
      parents: tuple of node indices
      pivot: int var (>0) or None
    """
    nodes = []
    clause_to_id = {}

    def add_node(cl, rule, parents, pivot):
        if cl in clause_to_id:
            return clause_to_id[cl]
        nid = len(nodes)
        nodes.append((cl, rule, parents, pivot))
        clause_to_id[cl] = nid
        return nid

    active = set()
    for cl in clauses:
        nid = add_node(cl, 'axiom', (), None)
        active.add(cl)
        if len(cl) == 0:
            return nodes, nid

    if elim_order is None:
        all_vars = sorted({abs(l) for cl in active for l in cl})
        elim_order = all_vars

    for var in elim_order:
        pos = [cl for cl in active if var in cl]
        neg = [cl for cl in active if -var in cl]
        rest = [cl for cl in active if var not in cl and -var not in cl]
        new_active = set(rest)
        for c1 in pos:
            for c2 in neg:
                res = (c1 - {var}) | (c2 - {-var})
                # check tautology
                if any(-l in res for l in res):
                    continue
                nid = add_node(res, 'res', (clause_to_id[c1], clause_to_id[c2]), var)
                new_active.add(res)
                if len(res) == 0:
                    return nodes, nid
        active = new_active
    raise RuntimeError("Formula was SAT or elimination failed")

def check_proof(nodes, target_id, allowed_axioms):
    """
    Verify:
    1. Soundness of every reachable node (axiom in allowed_axioms, valid res, valid weak)
    2. Target clause is empty
    3. Global regularity along EVERY directed path in the reachable DAG
    4. Exact reachable DAG size and tree-unfolded size
    """
    # Collect reachable nodes
    reach = set()
    stack = [target_id]
    while stack:
        u = stack.pop()
        if u in reach:
            continue
        reach.add(u)
        _, _, parents, _ = nodes[u]
        for p in parents:
            stack.append(p)

    # Check soundness
    for u in reach:
        cl, rule, parents, pivot = nodes[u]
        if rule == 'axiom':
            assert cl in allowed_axioms, f"Invalid axiom {cl}"
        elif rule == 'weak':
            p_cl = nodes[parents[0]][0]
            assert p_cl.issubset(cl), f"Invalid weakening {p_cl} -> {cl}"
        elif rule == 'res':
            c1 = nodes[parents[0]][0]
            c2 = nodes[parents[1]][0]
            assert pivot > 0
            assert (pivot in c1 and -pivot in c2) or (-pivot in c1 and pivot in c2), \
                f"Invalid pivot {pivot} for {c1}, {c2}"
            if pivot in c1:
                expected = (c1 - {pivot}) | (c2 - {-pivot})
            else:
                expected = (c1 - {-pivot}) | (c2 - {pivot})
            assert cl == expected, f"Resolvent mismatch: {cl} != {expected}"
        else:
            raise ValueError(rule)

    assert nodes[target_id][0] == frozenset(), "Target is not empty clause"

    # Check regularity along EVERY path via memoized union of reachable pivot sets?
    # Wait: regularity requires NO pivot on any path from axiom to target is repeated.
    # Equivalently, for every node u and pivot p used at u, p does NOT occur at any strict ancestor of u!
    # Let's check exact ancestor pivot set (since DAG is small, exact union of all ancestor pivots;
    # wait: if a pivot appears in an ancestor of u, then there EXISTS a path from that ancestor to u
    # using pivot twice! So regularity <=> for every node u with pivot p, p not in ancestor_pivots(parents of u)!)
    anc_pivots = {}
    def get_anc_pivots(u):
        if u in anc_pivots:
            return anc_pivots[u]
        _, rule, parents, pivot = nodes[u]
        s = set()
        for p in parents:
            s |= get_anc_pivots(p)
        if rule == 'res':
            assert pivot not in s, f"REGULARITY VIOLATION: pivot {pivot} repeated at node {u}"
            s.add(pivot)
        anc_pivots[u] = s
        return s

    get_anc_pivots(target_id)

    # Compute tree-unfolded size
    tree_sz = {}
    def get_tree_sz(u):
        if u in tree_sz:
            return tree_sz[u]
        _, _, parents, _ = nodes[u]
        sz = 1 + sum(get_tree_sz(p) for p in parents)
        tree_sz[u] = sz
        return sz

    used_axioms = {nodes[u][0] for u in reach if nodes[u][1] == 'axiom'}
    return {
        'dag_size': len(reach),
        'used_axioms': len(used_axioms),
        'tree_size': get_tree_sz(target_id),
        'regular': True,
        'max_width': max(len(nodes[u][0]) for u in reach),
    }

def eliminate_weakening(nodes, target_id):
    """Proposition 2.9: eliminate weakening preserving regularity and not increasing size."""
    new_nodes = []
    old_to_new = {}

    def convert(u):
        if u in old_to_new:
            return old_to_new[u]
        cl, rule, parents, pivot = nodes[u]
        if rule == 'axiom':
            nid = len(new_nodes)
            new_nodes.append((cl, 'axiom', (), None))
        elif rule == 'weak':
            nid = convert(parents[0])
        elif rule == 'res':
            p1 = convert(parents[0])
            p2 = convert(parents[1])
            c1 = new_nodes[p1][0]
            c2 = new_nodes[p2][0]
            # Find which side had +pivot and -pivot originally
            orig_c1 = nodes[parents[0]][0]
            if pivot in orig_c1:
                l1, l2 = pivot, -pivot
            else:
                l1, l2 = -pivot, pivot
            if l1 not in c1:
                nid = p1
            elif l2 not in c2:
                nid = p2
            else:
                res = (c1 - {l1}) | (c2 - {l2})
                nid = len(new_nodes)
                new_nodes.append((res, 'res', (p1, p2), pivot))
        old_to_new[u] = nid
        return nid

    new_target = convert(target_id)
    return new_nodes, new_target

def find_bridges(num_verts, edges):
    """Tarjan bridge-finding supporting parallel edges."""
    adj = defaultdict(list)
    for idx, (u, v) in enumerate(edges):
        adj[u].append((v, idx))
        adj[v].append((u, idx))
    disc = [-1] * num_verts
    low = [0] * num_verts
    timer = [0]
    bridges = set()

    def dfs(u, pe):
        disc[u] = low[u] = timer[0]
        timer[0] += 1
        for v, eidx in adj[u]:
            if eidx == pe:
                continue
            if disc[v] == -1:
                dfs(v, eidx)
                low[u] = min(low[u], low[v])
                if low[v] > disc[u]:
                    bridges.add(eidx)
            else:
                low[u] = min(low[u], disc[v])

    for i in range(num_verts):
        if disc[i] == -1:
            dfs(i, -1)
    return bridges

def bridge_tree_regular_proof(num_verts, edges, charges, root_comp_vert=None):
    """
    Implements Section 8.2's exact bridge-tree regular proof construction
    for a connected graph G with odd total charge.
    """
    assert sum(charges.values()) % 2 == 1
    bridges = find_bridges(num_verts, edges)

    # Components after deleting bridges
    adj_nb = defaultdict(list)
    for idx, (u, v) in enumerate(edges):
        if idx not in bridges:
            adj_nb[u].append((v, idx))
            adj_nb[v].append((u, idx))
    comp_of = [-1] * num_verts
    comps = []
    for i in range(num_verts):
        if comp_of[i] == -1:
            cid = len(comps)
            verts = []
            q = deque([i])
            comp_of[i] = cid
            while q:
                u = q.popleft()
                verts.append(u)
                for v, _ in adj_nb[u]:
                    if comp_of[v] == -1:
                        comp_of[v] = cid
                        q.append(v)
            comps.append(verts)

    # Build bridge tree
    bt_adj = defaultdict(list)
    for bidx in bridges:
        u, v = edges[bidx]
        cu, cv = comp_of[u], comp_of[v]
        assert cu != cv
        bt_adj[cu].append((cv, bidx, u, v))
        bt_adj[cv].append((cu, bidx, v, u))

    root_cid = 0 if root_comp_vert is None else comp_of[root_comp_vert]
    # BFS from root to orient tree
    parent_info = {root_cid: None}  # cid -> (parent_cid, bidx, u_in_cid, w_in_parent)
    children_info = defaultdict(list)
    order = []
    q = deque([root_cid])
    while q:
        c = q.popleft()
        order.append(c)
        for nxt, bidx, u_in_c, w_in_nxt in bt_adj[c]:
            if nxt not in parent_info:
                parent_info[nxt] = (c, bidx, w_in_nxt, u_in_c) # (parent, bidx, my_vert, parent_vert)
                children_info[c].append((nxt, bidx, u_in_c, w_in_nxt))
                q.append(nxt)

    # Global DAG
    global_nodes = []
    global_clause_id = {}
    def add_gnode(cl, rule, parents, pivot):
        # Do NOT merge across different derivations blindly; wait—merging identical clauses
        # could create a cycle if not careful, so only reuse unit clauses / identical already-created nodes!
        if cl in global_clause_id:
            return global_clause_id[cl]
        nid = len(global_nodes)
        global_nodes.append((cl, rule, parents, pivot))
        global_clause_id[cl] = nid
        return nid

    # Track child bridges incident to each vertex v
    # child_bridges_at[v] = list of (bidx, beta_b, lit_b, unit_node_id)
    child_bridges_at = defaultdict(list)
    res_charges = dict(charges)

    # Process bottom-up (reverse BFS order)
    for cid in reversed(order):
        verts = comps[cid]
        vset = set(verts)
        # Internal edges of component cid
        int_edges = [idx for idx, (u, v) in enumerate(edges) if idx not in bridges and u in vset and v in vset]
        # Map vertex -> internal edge vars
        int_inc = defaultdict(list)
        for idx in int_edges:
            u, v = edges[idx]
            int_inc[u].append(idx + 1)
            int_inc[v].append(idx + 1)

        pinfo = parent_info[cid]
        if pinfo is not None:
            parent_cid, pbidx, u_in_c, w_in_p = pinfo
            # beta_b = sum of residual charges in cid
            beta_b = sum(res_charges[v] for v in verts) % 2
            bvar = pbidx + 1
            lit_b = bvar if beta_b == 1 else -bvar  # asserts x_b = beta_b
            # Assign x_b = 1 - beta_b -> flip charge of u_in_c by (1 - beta_b)
            local_charges = {v: res_charges[v] for v in verts}
            local_charges[u_in_c] = (local_charges[u_in_c] + (1 - beta_b)) % 2
            assert sum(local_charges.values()) % 2 == 1
        else:
            pbidx = None
            u_in_c = None
            lit_b = None
            local_charges = {v: res_charges[v] for v in verts}
            assert sum(local_charges.values()) % 2 == 1

        # Build local CNF for component cid (clauses tagged by vertex)
        local_clauses = []
        local_cl_to_v = {}
        for v in verts:
            vars_v = int_inc[v]
            d = len(vars_v)
            c = local_charges[v] % 2
            if d == 0:
                if c == 1:
                    cl = frozenset()
                    local_clauses.append(cl)
                    local_cl_to_v[cl] = v
            else:
                for bits in itertools.product([0, 1], repeat=d):
                    if sum(bits) % 2 != c:
                        cl = frozenset(var if b == 0 else -var for var, b in zip(vars_v, bits))
                        local_clauses.append(cl)
                        local_cl_to_v[cl] = v

        # Get local regular refutation (weakening-free via DP)
        loc_nodes, loc_target = dp_regular_refutation(local_clauses)

        # Find reachable nodes in loc_nodes
        loc_reach = []
        seen = set()
        def dfs_loc(u):
            if u in seen:
                return
            seen.add(u)
            for p in loc_nodes[u][2]:
                dfs_loc(p)
            loc_reach.append(u)
        dfs_loc(loc_target)

        # Lift and embed into global_nodes
        loc_to_glob = {}
        for u in loc_reach:
            cl, rule, parents, pivot = loc_nodes[u]
            lifted_cl = cl if lit_b is None else (cl | {lit_b})
            if rule == 'axiom':
                v = local_cl_to_v[cl]
                # Derive base clause from original axiom at v by resolving child bridges
                # Base clause before weakening:
                #   if v == u_in_c (endpoint of parent bridge): lifted_cl = cl | {lit_b}
                #   else: cl
                base_cl = lifted_cl if (lit_b is not None and v == u_in_c) else cl
                cbridges = child_bridges_at[v]
                orig_cl = base_cl | frozenset(-lb for (_, _, lb, _) in cbridges)
                cur_id = add_gnode(orig_cl, 'axiom', (), None)
                cur_cl = orig_cl
                for (cbidx, _, clb, cunit_id) in cbridges:
                    nxt_cl = cur_cl - {-clb}
                    cur_id = add_gnode(nxt_cl, 'res', (cur_id, cunit_id), cbidx + 1)
                    cur_cl = nxt_cl
                assert cur_cl == base_cl
                if cur_cl != lifted_cl:
                    # weakening step at v != u_in_c
                    cur_id = add_gnode(lifted_cl, 'weak', (cur_id,), None)
                loc_to_glob[u] = cur_id
            else:
                gp1 = loc_to_glob[parents[0]]
                gp2 = loc_to_glob[parents[1]]
                loc_to_glob[u] = add_gnode(lifted_cl, 'res', (gp1, gp2), pivot)

        out_id = loc_to_glob[loc_target]
        if pinfo is not None:
            assert global_nodes[out_id][0] == frozenset({lit_b})
            # Record for parent
            child_bridges_at[w_in_p].append((pbidx, beta_b, lit_b, out_id))
            res_charges[w_in_p] = (res_charges[w_in_p] + beta_b) % 2
        else:
            final_target = out_id

    return global_nodes, final_target, bridges, comps

# Define all 5 fixtures
fixtures = []

# Fixture 1: Star K_{1,5} rooted at leaf 5
f1_n = 6
f1_edges = [(0, i) for i in range(1, 6)]
f1_charges = {0: 1, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
fixtures.append(("F1_star_K1_5_root_leaf", f1_n, f1_edges, f1_charges, 5))

# Fixture 2: Chain of three B_2 dipoles with shared attachment vertex 2 on middle dipole
f2_n = 6
f2_edges = [(0, 1), (0, 1), (2, 3), (2, 3), (4, 5), (4, 5), (1, 2), (2, 4)]
f2_charges = {0: 1, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
fixtures.append(("F2_dipole_chain_3_shared_v", f2_n, f2_edges, f2_charges, 4))

# Fixture 3: K_3 with 6 pendant leaves attached to vertex 0 (mixed charges), rooted at K_3 AND rooted at leaf 8
f3_n = 9
f3_edges = [(0, 1), (1, 2), (2, 0)] + [(0, i) for i in range(3, 9)]
f3_charges = {0: 0, 1: 1, 2: 0, 3: 1, 4: 1, 5: 0, 6: 0, 7: 0, 8: 0}
fixtures.append(("F3a_k3_6leaves_root_K3", f3_n, f3_edges, f3_charges, 0))
fixtures.append(("F3b_k3_6leaves_root_leaf", f3_n, f3_edges, f3_charges, 8))

# Fixture 4: Branching bridge tree: K_4 root + K_3 + B_3 + (singleton -> B_2)
f4_n = 12
f4_edges = (
    [(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)] +  # K_4
    [(4,5),(5,6),(6,4)] +                    # K_3
    [(7,8),(7,8),(7,8)] +                    # B_3
    [(10,11),(10,11)] +                      # B_2
    [(0,4),(1,7),(2,9),(9,10)]               # 4 bridges
)
f4_charges = {i: 0 for i in range(12)}
f4_charges[5] = 1; f4_charges[8] = 1; f4_charges[11] = 1
fixtures.append(("F4_branching_K4_K3_B3_sing_B2", f4_n, f4_edges, f4_charges, 0))

# Also test longer dipole chain (m=8) to show DAG vs Tree blowup!
m_chain = 8
f2_long_n = 2 * m_chain
f2_long_edges = []
for i in range(m_chain):
    f2_long_edges.append((2*i, 2*i+1))
    f2_long_edges.append((2*i, 2*i+1))
for i in range(m_chain - 1):
    f2_long_edges.append((2*i+1, 2*(i+1)))
f2_long_charges = {i: (1 if i == 0 else 0) for i in range(f2_long_n)}
fixtures.append(("F2_long_dipole_chain_8", f2_long_n, f2_long_edges, f2_long_charges, 2*m_chain-1))

for name, n, edges, charges, root_v in fixtures:
    clauses_by_v = make_tseitin_clauses(n, edges, charges)
    all_axioms = {cl for cls in clauses_by_v.values() for cl in cls}
    total_clauses = sum(len(cls) for cls in clauses_by_v.values())
    nodes, target, bridges, comps = bridge_tree_regular_proof(n, edges, charges, root_v)
    res_with_w = check_proof(nodes, target, all_axioms)
    nodes_nw, target_nw = eliminate_weakening(nodes, target)
    res_no_w = check_proof(nodes_nw, target_nw, all_axioms)
    print(f"=== {name} ===")
    print(f"  n={n}, |E|={len(edges)}, |bridges|={len(bridges)}, |X|={len(comps)}, |T(G,c)|={total_clauses}")
    print(f"  With weakening:    DAG={res_with_w['dag_size']}, used_ax={res_with_w['used_axioms']}, tree={res_with_w['tree_size']}, width={res_with_w['max_width']}, regular={res_with_w['regular']}")
    print(f"  Without weakening: DAG={res_no_w['dag_size']}, used_ax={res_no_w['used_axioms']}, tree={res_no_w['tree_size']}, width={res_no_w['max_width']}, regular={res_no_w['regular']}")


