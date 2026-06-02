#!/usr/bin/env python3
"""Bootstrap 95% confidence intervals on the headline metrics.

Small N means point estimates are uncertain — each miss moves recall
several points. This resamples DOCUMENTS with replacement (the standard
nonparametric bootstrap) and recomputes coverage recall + TAB entity recall for
the default ★ combo, reporting mean and a 2.5–97.5 percentile interval. Honesty,
not theater: it shows how wide the uncertainty actually is.

Entity-level CI weighting (Codex audit R2 #6): entities are grouped by entity_id,
but the bootstrap resamples DOCS. So a doc drawn k times must contribute its
entities k times, not collapse to one. `entity_recall_weighted` namespaces each
sampled doc instance (draw#-prefixed entity_ids) so entity weight tracks the
doc-level resample. Without this the entity CI was mis-estimated.

Usage: python bootstrap_ci.py --dataset ru --iters 2000
"""
import argparse
import json
import os
import random

from confide_eval import paths
from confide_eval.scoring import score_bench as sb

HERE = os.fspath(paths.RESULTS)


def star_combo(dataset):
    for name, members in sb.COMBOS[dataset]:
        if "★" in name:
            return name, members
    return sb.COMBOS[dataset][-1]


def coverage_recall(gold_rows, preds):
    per, tot = sb.score_span_coverage(gold_rows, preds, sb.overlaps, False)
    c, fn = tot["c"], tot["fn"]
    return c / (c + fn) if (c + fn) else 0.0


def entity_recall(gold_rows, preds):
    prot, total, _, _, _ = sb.score_entity_level(gold_rows, preds, relaxed=True)
    return prot / total if total else 0.0


def entity_recall_weighted(sampled_rows, preds):
    """Entity-level recall on a DOC-level bootstrap resample, with correct entity
    weighting (Codex audit R2 #6).

    The bug: `score_entity_level` groups mentions by global `entity_id`. On a
    bootstrap that resamples DOCS with replacement, an entity is normally tied to
    a single doc, but the grouping collapses every draw of that doc into one
    entity — so a doc drawn 3× contributes its entities only ONCE, and the
    entity-level CI is mis-weighted relative to the doc-level resample.

    Fix: namespace each sampled doc instance so its entities are counted each time
    the doc is drawn. We give every (draw#, doc) a fresh copy whose entity_ids are
    suffixed with the draw index, so a doc appearing k times contributes k
    independent entity groups. An entity's mentions stay grouped WITHIN one draw
    (so the all-mentions-masked TAB rule still holds per occurrence), but its
    weight now scales with how often its doc was sampled — matching the doc-level
    resample the bootstrap actually performs."""
    expanded = []
    for i, g in enumerate(sampled_rows):
        gg = dict(g)
        spans = []
        for s in g["spans"]:
            s2 = dict(s)
            eid = s2.get("entity_id")
            if eid is not None:
                s2["entity_id"] = f"{i}:{eid}"  # unique per draw occurrence
            spans.append(s2)
        gg["spans"] = spans
        gg["doc_id"] = f"{i}:{g['doc_id']}"  # so preds lookup still resolves below
        expanded.append(gg)
    # preds is keyed by ORIGINAL doc_id; remap so each draw instance finds its preds
    pred_map = {}
    for i, g in enumerate(sampled_rows):
        pred_map[f"{i}:{g['doc_id']}"] = preds.get(g["doc_id"], [])
    prot, total, _, _, _ = sb.score_entity_level(expanded, pred_map, relaxed=True)
    return prot / total if total else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="ru", choices=list(sb.GOLD))
    ap.add_argument("--iters", type=int, default=2000)
    args = ap.parse_args()
    # deterministic resampling (the bootstrap itself is reproducible; the underlying
    # detector caches are fixed, so this CI is stable run-to-run)
    rng = random.Random(20260601)

    if args.dataset == "en-real" and not sb.en_real_text_present():
        print("en-real source text not present — run "
              "`python -m confide_eval.data.fetch_ai4privacy` to fetch it "
              "(ai4privacy license; not redistributed). Skipping en-real CI.")
        return
    gold = sb.load_gold(args.dataset)
    name, members = star_combo(args.dataset)
    docs_sha = __import__("hashlib").sha256("".join(g["text"] for g in gold).encode()).hexdigest()[:12]
    preds = sb.union_preds(args.dataset, members, [g["doc_id"] for g in gold], docs_sha)
    if preds is None:
        print(f"[ci] {args.dataset}: cache missing for {name}"); return
    has_ent = any(s.get("entity_id") for r in gold for s in r["spans"])

    n = len(gold)
    cov, ent = [], []
    for _ in range(args.iters):
        sample = [gold[rng.randrange(n)] for _ in range(n)]
        cov.append(coverage_recall(sample, preds))
        if has_ent:
            ent.append(entity_recall_weighted(sample, preds))

    def ci(xs):
        xs = sorted(xs)
        lo = xs[int(0.025 * len(xs))]; hi = xs[int(0.975 * len(xs)) - 1]
        mean = sum(xs) / len(xs)
        return round(mean, 3), round(lo, 3), round(hi, 3)

    out = {"dataset": args.dataset, "combo": name, "n_docs": n, "iters": args.iters,
           "coverage_recall": dict(zip(("mean", "lo95", "hi95"), ci(cov)))}
    if has_ent:
        out["entity_recall"] = dict(zip(("mean", "lo95", "hi95"), ci(ent)))
    json.dump(out, open(os.path.join(HERE, f"{args.dataset}-bootstrap-ci.json"), "w"), indent=2)
    cr = out["coverage_recall"]
    line = f"[ci] {args.dataset} {name}: coverage recall {cr['mean']:.3f} (95% CI {cr['lo95']:.3f}–{cr['hi95']:.3f}, n={n})"
    if has_ent:
        er = out["entity_recall"]
        line += f" | entity recall {er['mean']:.3f} (CI {er['lo95']:.3f}–{er['hi95']:.3f})"
    print(line)


if __name__ == "__main__":
    main()
