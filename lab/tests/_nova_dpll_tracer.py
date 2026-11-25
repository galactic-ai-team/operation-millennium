"""Separately written tiny DPLL reference tracer (Nova, Phase 4 attack on PR #10).

Implements the DISCOVERY_ROUND_01 Section 3.6 search semantics from the
text, in a deliberately different structure from ``om_lab.solvers.solve_dpll``:

* unit propagation assigns ONE unit at a time and re-simplifies after
  each assignment (``solve_dpll`` assigns a whole batch of units per
  pass); the set of forced assignments is the same either way, so the
  propagation count must agree -- that agreement is itself a test;
* branch variable: the first remaining variable of the first shortest
  clause (``min`` with key ``len``, first minimum wins);
* branch values tried True, then False;
* ``decisions`` counts each attempted branch value;
* the budget is checked at recursive entry, BEFORE any unit propagation
  or completion test, exactly as the frozen convention specifies: a run
  that would finish with exactly B decisions is UNKNOWN with D == B;
* ``propagations`` counts each distinct unit assignment.

No imports from ``om_lab``. Pure standard library. This is a test
oracle, not production code: it is slow on purpose and must never be
used to run the experiment.

[Claim Level: Empirical Observation] for every count it produces.
"""

from __future__ import annotations

import time


class _BudgetExceeded(Exception):
    """Internal signal: decision or wall-clock budget exhausted."""


def trace_dpll(n_vars, clauses, max_decisions=None, max_seconds=None):
    """Reference DPLL. Returns a dict with status, decisions,
    propagations, model (complete, unassigned variables default True),
    timed_out and stop_reason.

    ``status`` is "SAT", "UNSAT" or "UNKNOWN". A completed UNSAT return
    is unverified by construction: this tracer emits no certificate.
    """
    t0 = time.perf_counter()
    deadline = None if max_seconds is None else t0 + max_seconds
    stats = {"decisions": 0, "propagations": 0}
    norm = [[int(lit) for lit in clause] for clause in clauses]

    def simplify(cls, assign):
        """Apply the assignment; return the reduced clause list, or
        None if some clause is falsified (conflict), or [] if satisfied."""
        out = []
        for clause in cls:
            satisfied = False
            reduced = []
            for lit in clause:
                var = abs(lit)
                if var in assign:
                    if (lit > 0) == assign[var]:
                        satisfied = True
                        break
                else:
                    reduced.append(lit)
            if satisfied:
                continue
            if not reduced:
                return None
            out.append(reduced)
        return out

    def search(cls, assign):
        # Budget check at recursive entry, before any other work.
        if max_decisions is not None and stats["decisions"] >= max_decisions:
            raise _BudgetExceeded("decision")
        if deadline is not None and time.perf_counter() > deadline:
            raise _BudgetExceeded("time")
        # Unit propagation, one unit at a time with re-simplification.
        while True:
            cls = simplify(cls, assign)
            if cls is None:
                return None
            if not cls:
                return assign
            units = [c[0] for c in cls if len(c) == 1]
            if not units:
                break
            lit = units[0]
            var = abs(lit)
            if var in assign:
                # simplify() would have removed a satisfied unit clause
                # and returned None for a falsified one, so this is
                # unreachable for well-formed input; treat it as a
                # conflict rather than looping forever.
                return None
            assign[var] = lit > 0
            stats["propagations"] += 1
        # Branch on the first remaining variable of the first shortest clause.
        shortest = min(cls, key=len)
        var = abs(shortest[0])
        for value in (True, False):
            stats["decisions"] += 1
            nxt = dict(assign)
            nxt[var] = value
            result = search(cls, nxt)
            if result is not None:
                return result
        return None

    try:
        solution = search(norm, {})
    except _BudgetExceeded as exc:
        stop = (
            "decision_budget"
            if str(exc) == "decision"
            or (max_decisions is not None and stats["decisions"] >= max_decisions)
            else "time_budget"
        )
        return {
            "status": "UNKNOWN",
            "decisions": stats["decisions"],
            "propagations": stats["propagations"],
            "model": None,
            "timed_out": True,
            "stop_reason": stop,
        }
    if solution is None:
        return {
            "status": "UNSAT",
            "decisions": stats["decisions"],
            "propagations": stats["propagations"],
            "model": None,
            "timed_out": False,
            "stop_reason": None,
        }
    model = [v if solution.get(v, True) else -v for v in range(1, n_vars + 1)]
    return {
        "status": "SAT",
        "decisions": stats["decisions"],
        "propagations": stats["propagations"],
        "model": model,
        "timed_out": False,
        "stop_reason": None,
    }
