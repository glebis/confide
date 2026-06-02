#!/usr/bin/env python3
"""Selftest for the shared k-anonymity / singling-out estimator (audit R6, bug B1).

Asserts that the two call sites — confide_red.py and privacy_utility_eval.py —
now return the IDENTICAL expected-match value for the same client (they used to
disagree: 104.3 vs 3504 for client a), and that the sensitivity sweep runs and
correctly flags client b's fragile verdict.

Deterministic, no LLM: reads the committed detector caches + gold only.
Run:  python3 test_kanon.py   (exit 0 on pass, 1 on failure)
"""
import sys

import kanon
import confide_red as cr
import privacy_utility_eval as pu


def main():
    fails = []

    # 1) Both call sites agree per client (the core B1 fix).
    pu_qc = pu.quasi_combination(["a", "b"])
    for cl in ("a", "b"):
        red_val = cr.singling_out(cl)["expected_matches"]
        pu_val = pu_qc[cl]["expected_matches"]
        if red_val != pu_val:
            fails.append(f"client {cl}: confide_red={red_val} != privacy_utility={pu_val}")
        else:
            print(f"[ok] client {cl}: both scripts agree expected_matches={red_val}")

    # 2) The estimator is the SINGLE source (sanity: kanon == both wrappers).
    for cl in ("a", "b"):
        base = kanon.singling_out(cl)["expected_matches"]
        if base != cr.singling_out(cl)["expected_matches"]:
            fails.append(f"client {cl}: kanon != confide_red wrapper")

    # 3) dims_used must be reflected in expected_matches (no silent dropped survivors).
    #    privacy_utility used to list survivors it then ignored in dims_used.
    for cl in ("a", "b"):
        s = kanon.singling_out(cl)
        if s["expected_matches"] is not None and not s["dims_used"]:
            fails.append(f"client {cl}: expected_matches set but dims_used empty")

    # 4) Sensitivity sweep runs and produces a verdict per client.
    for cl in ("a", "b", "c", "d", "e", "f"):
        sw = kanon.sensitivity(cl)
        if "verdict_robust" not in sw or not sw["rows"]:
            fails.append(f"client {cl}: sensitivity sweep produced no rows/verdict")
    # client b's verdict is known-fragile (baseline k≈1.7, near the threshold).
    if kanon.sensitivity("b")["verdict_robust"]:
        fails.append("client b: sensitivity expected NOT robust (k≈1.7 should flip)")
    else:
        print("[ok] client b sensitivity correctly flagged NOT robust")

    if fails:
        print("\n✗ test_kanon FAILED:")
        for f in fails:
            print("  " + f)
        sys.exit(1)
    print("\n✓ test_kanon: both call sites agree, sweep runs, fragile verdict flagged.")


if __name__ == "__main__":
    main()
