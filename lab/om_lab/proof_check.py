"""Independent DRAT proof checker for UNSAT certificates (standard library only).

Why this module exists
----------------------
Section 4.1 of ``docs/phase3/DISCOVERY_ROUND_01.md`` (OM-C001-R2 integrity
gate) rejects ``verified=True`` on a completed UNSAT solver return as
evidence of unsatisfiability. A completed UNSAT claim may only be labelled
``UNSAT_PROOF_CHECKED`` after an *independent* checker has validated a proof
certificate for the original formula. This module is that checker.

Independence
------------
* It imports nothing from ``om_lab`` and nothing outside the Python standard
  library, so it shares no code with any solver whose claims it checks (the
  pure-Python DPLL baseline, or CaDiCaL / Glucose / Lingeling via PySAT).
* It reads only the original clauses and the proof text. Solver status,
  statistics and metadata are never consulted.

Proof format and acceptance rule
--------------------------------
Text DRAT, as defined for DRAT-trim (Wetzler, Heule & Hunt, "DRAT-trim:
Efficient Checking and Trimming Using Expressive Clausal Proofs", SAT 2014,
LNCS 8561, pp. 422-429, doi:10.1007/978-3-319-09284-3_31; format note:
Heule, "The DRAT format and DRAT-trim checker", arXiv:1610.06229):

* ``l1 ... lk 0`` adds the lemma ``(l1 v ... v lk)``;
* ``d l1 ... lk 0`` deletes one copy of that clause.

Every added lemma ``C`` must be

* AT/RUP: assigning every literal of ``C`` false and running unit
  propagation over the current clause database yields a conflict; or
* RAT on its *first* literal ``p``: for every clause ``D`` in the current
  database that contains ``-p``, the resolvent ``C v (D minus -p)`` is a
  tautology or AT.

The certificate is accepted only if the proof adds the empty clause and that
addition passes the check (lines after the empty clause are ignored), or if
the original formula already contains the empty clause.

Soundness argument (why acceptance implies the formula is UNSAT)
---------------------------------------------------------------
Let ``DB_0 = F`` and ``DB_t`` be the database this checker holds after ``t``
proof steps. Invariant: if ``F`` is satisfiable then ``DB_t`` is satisfiable.
An AT lemma is implied by ``DB_t``. A RAT lemma preserves satisfiability of
``DB_t`` (standard RAT property, checked here against the database this
checker actually holds). Applying a deletion can only preserve
satisfiability, and ignoring a deletion leaves ``DB_t`` unchanged. If the
empty clause passes its AT check, ``DB_t`` is unsatisfiable, hence so is ``F``.

Deletion convention (matches DRAT-trim's default behaviour)
-----------------------------------------------------------
Deletions of unit clauses, and of clauses that are currently a possible
reason under root-level unit propagation (exactly one true literal, all
others false), are ignored and counted. Deleting a clause that is not in the
database is ignored and counted. By the invariant above, ignoring a deletion
is always sound; it only prevents spurious rejection of proofs from solvers
that delete clauses still on their root-level trail. The cost is that a RAT
check may see extra clauses and reject a proof DRAT-trim would accept
(incompleteness, never unsoundness).

Claim levels
------------
* The DRAT soundness property is established literature (cited above); it is
  not re-proved here.
* "This implementation is correct" is **[Claim Level: Empirical
  Observation]**: it is tested (corrupted-certificate rejection, rejection of
  every certificate offered for satisfiable formulas, differential tests
  against an independent naive implementation and against DRAT-trim), not
  formally verified.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import operator
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
from typing import Iterable, Sequence

__all__ = [
    "CHECKER_NAME",
    "CHECKER_VERSION",
    "ProofCheckResult",
    "ProofParseError",
    "ProofStep",
    "check_drat",
    "checker_source_sha256",
    "dimacs_text",
    "parse_drat",
    "proof_sha256",
    "run_drat_trim",
]

CHECKER_NAME = "om_lab.proof_check"
CHECKER_VERSION = "1.0.0"
PROOF_FORMAT = "DRAT-text"

_INT_TOKEN = re.compile(r"^-?(0|[1-9][0-9]*)$")


class ProofParseError(ValueError):
    """Malformed proof text. A malformed certificate is never accepted."""


@dataclass(frozen=True)
class ProofStep:
    """One parsed proof line."""

    is_deletion: bool
    literals: tuple[int, ...]  # as written, possibly with duplicates
    line_no: int  # 1-based line number in the proof text


@dataclass(frozen=True)
class ProofCheckResult:
    """Outcome of checking one certificate against one formula."""

    valid: bool
    reason: str
    n_steps: int
    n_additions_checked: int
    n_rup: int
    n_rat: int
    n_deletions_applied: int
    n_deletions_ignored_reason: int
    n_deletions_ignored_missing: int
    empty_clause_line: int | None
    first_failed_line: int | None
    lines_after_empty_clause: int
    elapsed_s: float
    checker: str = CHECKER_NAME
    checker_version: str = CHECKER_VERSION

    def to_dict(self, include_timing: bool = False) -> dict:
        """JSON-ready dict. Timing is excluded by default because it is not
        deterministic and must not enter deterministic experiment records."""
        out = asdict(self)
        if not include_timing:
            out.pop("elapsed_s")
        return out


def checker_source_sha256() -> str:
    """SHA-256 of this checker's source file (checker identity for records)."""
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def proof_sha256(proof_lines: Iterable[str]) -> str:
    """SHA-256 of the proof text, one line per step, ``\\n``-terminated."""
    h = hashlib.sha256()
    for line in proof_lines:
        h.update(str(line).strip().encode("ascii"))
        h.update(b"\n")
    return h.hexdigest()


def dimacs_text(n_vars: int, clauses: Sequence[Sequence[int]]) -> str:
    """Canonical DIMACS text of a formula, preserving clause and literal order."""
    lines = [f"p cnf {int(n_vars)} {len(clauses)}"]
    lines.extend(" ".join(str(int(lit)) for lit in clause) + (" 0" if clause else "0") for clause in clauses)
    return "\n".join(lines) + "\n"


def parse_drat(proof_lines: Iterable[str | bytes]) -> list[ProofStep]:
    """Strictly parse text DRAT.

    Blank lines and comment lines (``c`` or ``c ...``) are skipped. Every
    other line must be ``[d] lit ... 0`` with base-10 integer tokens, the
    single terminating ``0`` last, and no other ``0``.
    """
    steps: list[ProofStep] = []
    for line_no, raw in enumerate(proof_lines, start=1):
        if isinstance(raw, (bytes, bytearray)):
            try:
                raw = raw.decode("ascii")
            except UnicodeDecodeError as exc:
                raise ProofParseError(f"line {line_no}: non-ASCII bytes") from exc
        if not isinstance(raw, str):
            raise ProofParseError(f"line {line_no}: expected text, got {type(raw).__name__}")
        text = raw.strip()
        if not text:
            continue
        tokens = text.split()
        if tokens[0] == "c":
            continue
        is_deletion = tokens[0] == "d"
        body = tokens[1:] if is_deletion else tokens
        if not body:
            raise ProofParseError(f"line {line_no}: deletion without literals or terminator")
        for tok in body:
            if not _INT_TOKEN.match(tok):
                raise ProofParseError(f"line {line_no}: invalid token {tok!r}")
        values = [int(tok) for tok in body]
        if values[-1] != 0:
            raise ProofParseError(f"line {line_no}: missing terminating 0")
        literals = tuple(values[:-1])
        if any(lit == 0 for lit in literals):
            raise ProofParseError(f"line {line_no}: literal 0 before end of line")
        steps.append(ProofStep(is_deletion=is_deletion, literals=literals, line_no=line_no))
    return steps


def _dedupe(literals: Iterable[int]) -> tuple[int, ...]:
    """Remove repeated literals, keeping first-occurrence order (pivot stays first)."""
    seen: set[int] = set()
    out: list[int] = []
    for lit in literals:
        if lit not in seen:
            seen.add(lit)
            out.append(lit)
    return tuple(out)


class _ClauseDB:
    """Multiset clause database with occurrence lists and unit propagation."""

    def __init__(self) -> None:
        self.clauses: dict[int, tuple[int, ...]] = {}
        self.occ: dict[int, set[int]] = {}
        self.units: dict[int, int] = {}
        self.empty: set[int] = set()
        self._by_key: dict[tuple[int, ...], list[int]] = {}
        self._next_id = 0

    def add(self, lits: tuple[int, ...]) -> int:
        cid = self._next_id
        self._next_id += 1
        self.clauses[cid] = lits
        self._by_key.setdefault(tuple(sorted(lits)), []).append(cid)
        if not lits:
            self.empty.add(cid)
        elif len(lits) == 1:
            self.units[cid] = lits[0]
        for lit in lits:
            self.occ.setdefault(lit, set()).add(cid)
        return cid

    def find(self, lits: tuple[int, ...]) -> int | None:
        ids = self._by_key.get(tuple(sorted(lits)))
        return ids[-1] if ids else None

    def remove(self, cid: int) -> None:
        lits = self.clauses.pop(cid)
        key = tuple(sorted(lits))
        ids = self._by_key[key]
        ids.remove(cid)
        if not ids:
            del self._by_key[key]
        self.empty.discard(cid)
        self.units.pop(cid, None)
        for lit in lits:
            bucket = self.occ[lit]
            bucket.discard(cid)
            if not bucket:
                del self.occ[lit]

    def propagate(self, assumptions: Iterable[int]) -> tuple[bool, dict[int, bool]]:
        """Unit propagation from all unit clauses plus ``assumptions``.

        Returns ``(conflict, assignment)``. Whether a conflict is reached does
        not depend on processing order (unit propagation is confluent), so
        the verdict is deterministic.
        """
        if self.empty:
            return True, {}
        val: dict[int, bool] = {}
        trail: list[int] = []

        def set_true(lit: int) -> bool:
            var = lit if lit > 0 else -lit
            want = lit > 0
            cur = val.get(var)
            if cur is None:
                val[var] = want
                trail.append(lit)
                return True
            return cur == want

        for lit in self.units.values():
            if not set_true(lit):
                return True, val
        for lit in assumptions:
            if not set_true(lit):
                return True, val

        clauses = self.clauses
        occ = self.occ
        head = 0
        while head < len(trail):
            lit = trail[head]
            head += 1
            falsified_in = occ.get(-lit)
            if not falsified_in:
                continue
            for cid in falsified_in:
                open_lit = 0
                n_open = 0
                satisfied = False
                for other in clauses[cid]:
                    value = val.get(other if other > 0 else -other)
                    if value is None:
                        n_open += 1
                        open_lit = other
                        if n_open > 1:
                            break
                    elif value == (other > 0):
                        satisfied = True
                        break
                if satisfied or n_open > 1:
                    continue
                if n_open == 0:
                    return True, val
                set_true(open_lit)
        return False, val


def _is_possible_reason(lits: tuple[int, ...], val: dict[int, bool]) -> bool:
    """Exactly one literal true and all others false under ``val``."""
    n_true = 0
    for lit in lits:
        value = val.get(lit if lit > 0 else -lit)
        if value is None:
            return False
        if value == (lit > 0):
            n_true += 1
            if n_true > 1:
                return False
    return n_true == 1


def _has_rat(db: _ClauseDB, lemma: tuple[int, ...]) -> bool:
    """RAT check on the lemma's first literal against the current database."""
    pivot = lemma[0]
    for cid in sorted(db.occ.get(-pivot, ())):
        resolvent = set(lemma)
        resolvent.update(lit for lit in db.clauses[cid] if lit != -pivot)
        if any(-lit in resolvent for lit in resolvent):
            continue  # tautological resolvent
        conflict, _ = db.propagate(-lit for lit in resolvent)
        if not conflict:
            return False
    return True


def check_drat(
    clauses: Sequence[Sequence[int]],
    proof_lines: Iterable[str | bytes],
) -> ProofCheckResult:
    """Check a text-DRAT refutation of ``clauses``.

    Returns a :class:`ProofCheckResult`; ``valid`` is True only when the
    certificate establishes that ``clauses`` is unsatisfiable. A malformed or
    insufficient certificate yields ``valid=False`` with a reason; it never
    raises for bad proof text. A malformed *formula* (literal 0 or a
    non-integer literal) raises :class:`ValueError`, because that is a caller
    bug rather than a certificate property.
    """
    t0 = time.perf_counter()
    counters = {
        "n_steps": 0,
        "n_additions_checked": 0,
        "n_rup": 0,
        "n_rat": 0,
        "n_deletions_applied": 0,
        "n_deletions_ignored_reason": 0,
        "n_deletions_ignored_missing": 0,
    }

    def result(valid: bool, reason: str, *, empty_line: int | None = None,
               failed_line: int | None = None, after_empty: int = 0) -> ProofCheckResult:
        return ProofCheckResult(
            valid=valid,
            reason=reason,
            empty_clause_line=empty_line,
            first_failed_line=failed_line,
            lines_after_empty_clause=after_empty,
            elapsed_s=time.perf_counter() - t0,
            **counters,
        )

    db = _ClauseDB()
    formula_has_empty_clause = False
    for clause in clauses:
        lits = []
        for lit in clause:
            if isinstance(lit, bool):
                raise ValueError(f"invalid literal {lit!r} in formula")
            value = operator.index(lit)  # rejects floats and strings
            if value == 0:
                raise ValueError("literal 0 in formula")
            lits.append(value)
        deduped = _dedupe(lits)
        if not deduped:
            formula_has_empty_clause = True
        db.add(deduped)

    try:
        steps = parse_drat(proof_lines)
    except ProofParseError as exc:
        return result(False, f"malformed certificate: {exc}")
    counters["n_steps"] = len(steps)

    if formula_has_empty_clause:
        return result(True, "formula contains the empty clause (trivially UNSAT; proof not needed)")

    for position, step in enumerate(steps):
        lemma = _dedupe(step.literals)
        if step.is_deletion:
            cid = db.find(lemma)
            if cid is None:
                counters["n_deletions_ignored_missing"] += 1
                continue
            if len(lemma) <= 1:
                counters["n_deletions_ignored_reason"] += 1
                continue
            root_conflict, root_val = db.propagate(())
            if root_conflict or _is_possible_reason(lemma, root_val):
                counters["n_deletions_ignored_reason"] += 1
                continue
            db.remove(cid)
            counters["n_deletions_applied"] += 1
            continue

        counters["n_additions_checked"] += 1
        conflict, _ = db.propagate(-lit for lit in lemma)
        if conflict:
            counters["n_rup"] += 1
        elif lemma and _has_rat(db, lemma):
            counters["n_rat"] += 1
        else:
            kind = "empty clause" if not lemma else "lemma"
            return result(
                False,
                f"line {step.line_no}: {kind} is neither AT (RUP) nor RAT on its first literal",
                failed_line=step.line_no,
            )
        if not lemma:
            return result(
                True,
                "empty clause derived",
                empty_line=step.line_no,
                after_empty=len(steps) - position - 1,
            )
        db.add(lemma)

    return result(False, "certificate does not derive the empty clause")


def run_drat_trim(
    binary: str | os.PathLike,
    n_vars: int,
    clauses: Sequence[Sequence[int]],
    proof_lines: Iterable[str],
    timeout_s: float = 120.0,
) -> dict:
    """Optional external cross-check with the DRAT-trim binary (MIT licence).

    DRAT-trim is not a dependency of this package; pass the path of a locally
    built binary (``https://github.com/marijnheule/drat-trim``). Returns
    ``{"checker": "drat-trim", "verdict": "VERIFIED" | "NOT VERIFIED" |
    "ERROR", "detail": ...}``. Only ``VERIFIED`` counts as acceptance.
    """
    with tempfile.TemporaryDirectory(prefix="om_drat_") as tmp:
        cnf_path = Path(tmp) / "formula.cnf"
        proof_path = Path(tmp) / "proof.drat"
        cnf_path.write_text(dimacs_text(n_vars, clauses), encoding="ascii")
        proof_path.write_text("".join(f"{str(line).strip()}\n" for line in proof_lines), encoding="ascii")
        try:
            proc = subprocess.run(
                [str(binary), str(cnf_path), str(proof_path), "-w"],
                capture_output=True,
                text=True,
                timeout=timeout_s,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"checker": "drat-trim", "verdict": "ERROR", "detail": f"{type(exc).__name__}: {exc}"}
    status_lines = [line for line in proc.stdout.splitlines() if line.startswith("s ")]
    if "s VERIFIED" in status_lines:
        verdict = "VERIFIED"
    elif status_lines:
        verdict = "NOT VERIFIED"
    else:
        verdict = "ERROR"
    return {"checker": "drat-trim", "verdict": verdict, "detail": status_lines[-1] if status_lines else proc.stdout[-200:]}
