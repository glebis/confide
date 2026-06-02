#!/usr/bin/env python3
"""Unit tests for the CONFIDE-Red linkability benchmark logic (B8 fix).

Exercises pairing + scoring on a TINY synthetic set with MOCKED verdicts — no
LLM call, no network. Asserts: (1) pair labels are correct (SAME iff same
client), (2) the DIFFERENT sample is the documented deterministic stride,
(3) accuracy / precision / recall / F1 / confusion matrix compute correctly, and
(4) ROC-AUC behaves on perfectly-separable and on chance score distributions.

Run: python3 eval/test_linkability.py   (exit 0 = pass)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import confide_red as cr


def test_pair_labels_and_count():
    # 3 clients × 2 sessions = 6 docs. C(6,2)=15 pairs: 3 SAME (one per client), 12 DIFFERENT.
    keys = [(c, s) for c in ("a", "b", "c") for s in range(2)]
    pairs, samp = cr.build_pairs(keys, diff_stride=1)  # stride 1 keeps every DIFFERENT pair
    same = [p for p in pairs if p[2] == "same"]
    diff = [p for p in pairs if p[2] == "diff"]
    assert len(same) == 3, f"expected 3 SAME pairs, got {len(same)}"
    assert len(diff) == 12, f"expected 12 DIFFERENT pairs, got {len(diff)}"
    # every SAME pair must share a client; every DIFFERENT pair must not
    for i, j, lab in same:
        assert keys[i][0] == keys[j][0]
    for i, j, lab in diff:
        assert keys[i][0] != keys[j][0]
    assert samp["total_diff"] == 12 and samp["dropped_diff"] == 0
    print("ok pair labels + count")


def test_diff_stride_is_deterministic():
    keys = [(c, s) for c in ("a", "b", "c", "d") for s in range(3)]  # 12 docs
    p1, s1 = cr.build_pairs(keys, diff_stride=5)
    p2, s2 = cr.build_pairs(keys, diff_stride=5)
    assert p1 == p2, "build_pairs must be deterministic (no RNG)"
    # stride strictly subsamples DIFFERENT, keeps ALL SAME
    n_same_total = sum(1 for i in range(len(keys)) for j in range(i + 1, len(keys))
                       if keys[i][0] == keys[j][0])
    n_same_kept = sum(1 for *_ , lab in p1 if lab == "same")
    assert n_same_kept == n_same_total, "all SAME pairs must be kept"
    assert s1["sampled_diff"] < s1["total_diff"], "stride 5 should drop DIFFERENT pairs"
    assert s1["dropped_diff"] == s1["total_diff"] - s1["sampled_diff"]
    print("ok deterministic stride")


def test_scoring_confusion_and_rates():
    # 4 SAME (3 correct, 1 missed), 4 DIFFERENT (1 false alarm, 3 correct)
    verdicts = [
        {"label": "same", "called_same": True, "confidence": 0.9},
        {"label": "same", "called_same": True, "confidence": 0.8},
        {"label": "same", "called_same": True, "confidence": 0.7},
        {"label": "same", "called_same": False, "confidence": 0.3},   # FN
        {"label": "diff", "called_same": True, "confidence": 0.6},     # FP
        {"label": "diff", "called_same": False, "confidence": 0.2},
        {"label": "diff", "called_same": False, "confidence": 0.1},
        {"label": "diff", "called_same": False, "confidence": 0.4},
    ]
    m = cr.score_linkability(verdicts)
    assert (m["tp"], m["fn"], m["fp"], m["tn"]) == (3, 1, 1, 3), m
    assert m["accuracy"] == 0.75, m["accuracy"]            # 6/8
    assert m["precision"] == 0.75, m["precision"]          # 3/(3+1)
    assert m["recall"] == 0.75, m["recall"]                # 3/(3+1)
    assert abs(m["f1"] - 0.75) < 1e-9, m["f1"]
    assert m["base_rate_same"] == 0.5 and m["majority_accuracy"] == 0.5
    print("ok scoring + confusion matrix")


def test_roc_auc():
    # Perfect separation: all SAME score above all DIFFERENT -> AUC 1.0
    perfect = ([True] * 3 + [False] * 3, [0.9, 0.8, 0.7, 0.3, 0.2, 0.1])
    assert cr.roc_auc(*perfect) == 1.0
    # Inverted -> AUC 0.0
    inv = ([True] * 3 + [False] * 3, [0.1, 0.2, 0.3, 0.7, 0.8, 0.9])
    assert cr.roc_auc(*inv) == 0.0
    # All-tied -> 0.5 (chance)
    tied = ([True, True, False, False], [0.5, 0.5, 0.5, 0.5])
    assert cr.roc_auc(*tied) == 0.5
    print("ok roc-auc")


def test_bootstrap_ci_shape():
    verdicts = [{"label": "same", "called_same": True, "confidence": 0.9}] * 5 + \
               [{"label": "diff", "called_same": False, "confidence": 0.1}] * 5
    ci = cr.bootstrap_link_ci(verdicts, iters=200)
    for k in ("accuracy", "roc_auc"):
        assert ci[k]["lo95"] <= ci[k]["mean"] <= ci[k]["hi95"], (k, ci[k])
    # perfectly separable -> accuracy and AUC pinned at 1.0
    assert ci["accuracy"]["mean"] == 1.0 and ci["roc_auc"]["mean"] == 1.0
    print("ok bootstrap ci shape")


if __name__ == "__main__":
    test_pair_labels_and_count()
    test_diff_stride_is_deterministic()
    test_scoring_confusion_and_rates()
    test_roc_auc()
    test_bootstrap_ci_shape()
    print("\nALL LINKABILITY TESTS PASSED")
