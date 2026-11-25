from om_lab.generators import generate_random_3sat
from om_lab.solvers import solve_dpll, solve_pysat, verify_cnf_assignment


def test_verify_cnf_assignment():
    clauses = [[1, 2], [-1, 3]]
    assert verify_cnf_assignment(clauses, [1, -2, 3])
    assert not verify_cnf_assignment(clauses, [1, -2, -3])
    assert not verify_cnf_assignment(clauses, None)


def test_dpll_and_pysat_edge_cases():
    # Empty CNF is SAT
    for fn in (solve_dpll, solve_pysat):
        res = fn(2, [])
        assert res.satisfiable
        assert res.verified

    # Empty clause is UNSAT
    for fn in (solve_dpll, solve_pysat):
        res = fn(2, [[1], []])
        assert not res.satisfiable
        assert res.verified

    # Simple UNSAT: (x1) & (-x1)
    for fn in (solve_dpll, solve_pysat):
        res = fn(1, [[1], [-1]])
        assert not res.satisfiable
        assert res.verified


def test_dpll_matches_pysat_on_random_3sat():
    for seed in range(25):
        inst = generate_random_3sat(n_vars=16, n_clauses=68, seed=seed)
        r_pysat = solve_pysat(inst.n_vars, inst.clauses)
        r_dpll = solve_dpll(inst.n_vars, inst.clauses)
        assert r_pysat.verified
        assert r_dpll.verified
        assert r_pysat.satisfiable == r_dpll.satisfiable
