# Section 8 fixture checks: Lumi reproduction (2026-11-25)

check1.py and check2.py are Gemini's code blocks, extracted verbatim from its reply. check2.py reuses check1.py's definitions; Gemini ran them in one session.

Lumi ran them on CPython 3.13 (om_venv): python check1.py, and python check1.py+check2.py concatenated. Both outputs match check1_claimed_output.txt and check2_claimed_output.txt (diff -w), apart from trailing blank lines.

Claim level: Empirical Observation (small fixtures F1-F5 only). The checks test Gemini's own Tseitin/DP-regular-DAG model of Section 8. They are not a proof of Thm 8.2.
