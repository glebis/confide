#!/usr/bin/env python3
"""Score the layered-detector ablation against gold, every researched way.

Reads gold (a *-eval*.jsonl with per-doc `spans`) and the per-detector caches
written by run_detectors.py, composes each ablation combo by SPAN-UNION, and
reports, per combo:

  Methodologies (all standards-aligned, see eval/BENCHMARK.md for citations):
   1. Span-coverage (type-agnostic): did we redact the PII span at all?
      precision/recall/F1/F2, STRICT (exact) and RELAXED (overlap>=1 char).
      This is the privacy-first "did we catch it" view (Presidio-research).
   2. Type-aware: same, but a predicted span must also map to the gold span's
      canonical type. Micro-F1 (primary) + macro-F1 over types (i2b2/n2c2).
   3. Entity-level recall (TAB): an entity is "protected" only if ALL of its
      gold mentions are covered by some prediction. Headline privacy metric.
   4. Direct vs quasi-identifier recall split (TAB).
   5. Per-category recall table (which layer catches what) — surfaces the
      LLM-required types (medication/age/date/profession).

F2 (recall-weighted) is the headline: a missed entity is leaked PII; a false
positive is mere over-redaction. See eval/README.md for the rationale.

Usage:
  python score_bench.py --dataset ru   --out-prefix ru-
  python score_bench.py --dataset en   --out-prefix en-
  python score_bench.py --dataset en-real --out-prefix en-real-
"""
import argparse
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "detector-cache")
GOLD = {
    "ru":      os.path.join(HERE, "..", "sessions-ru", "pii-eval-ru.jsonl"),
    "ru-adv":  os.path.join(HERE, "..", "sessions-ru", "pii-adversarial-ru.jsonl"),
    "en":      os.path.join(HERE, "..", "sessions-en", "pii-eval.jsonl"),
    "en-real": os.path.join(HERE, "..", "sessions-en", "pii-eval-ai4privacy.jsonl"),
}

# Ablation combos per dataset. Each base detector's spans are cached once; a
# combo is the UNION of its members' spans. (natasha is RU-only; opf is the
# English name/address detector — Natasha's English counterpart.)
COMBOS = {
    "ru": [
        ("regex",                  ["regex"]),
        ("natasha",                ["natasha"]),
        ("ollama",                 ["ollama"]),
        ("natasha+regex",          ["natasha", "regex"]),
        ("natasha+ollama",         ["natasha", "ollama"]),
        ("regex+ollama",           ["regex", "ollama"]),
        ("natasha+regex+ollama ★", ["natasha", "regex", "ollama"]),
        ("opf+natasha+regex+ollama", ["opf", "natasha", "regex", "ollama"]),
    ],
    "en": [
        ("regex",                 ["regex"]),
        ("opf",                   ["opf"]),
        ("ollama",                ["ollama"]),
        ("opf+regex",             ["opf", "regex"]),
        ("opf+ollama",            ["opf", "ollama"]),
        ("regex+ollama",          ["regex", "ollama"]),
        ("opf+regex+ollama ★",    ["opf", "regex", "ollama"]),
        ("natasha+regex+ollama",  ["natasha", "regex", "ollama"]),
    ],
}
COMBOS["en-real"] = COMBOS["en"]
COMBOS["ru-adv"] = [
    ("regex",                  ["regex"]),
    ("natasha",                ["natasha"]),
    ("ollama",                 ["ollama"]),
    ("natasha+regex",          ["natasha", "regex"]),
    ("natasha+regex+ollama ★", ["natasha", "regex", "ollama"]),
]

# Map every detector's raw label -> canonical type (for the type-aware view).
CANON = {
    # natasha / pipeline
    "PERSON": "PERSON", "LOCATION": "LOCATION", "ADDRESS": "LOCATION", "ORG": "ORG",
    "PHONE": "PHONE", "EMAIL": "EMAIL", "URL": "URL", "ID": "ID", "DATE": "DATE",
    "MEDICATION": "MEDICATION", "AGE": "AGE", "PROFESSION": "PROFESSION",
    # OPF private_* labels
    "PRIVATE_PERSON": "PERSON", "PRIVATE_ADDRESS": "LOCATION", "PRIVATE_EMAIL": "EMAIL",
    "PRIVATE_PHONE": "PHONE", "PRIVATE_URL": "URL", "PRIVATE_DATE": "DATE",
    "ACCOUNT_NUMBER": "ID", "SECRET": "ID",
    # ai4privacy gold native labels seen in the EN-real slice get canon'd in load_gold
}


def canon(t):
    return CANON.get(t.upper(), t.upper())


def overlaps(a, b):
    return a["start"] < b["end"] and b["start"] < a["end"]


def contains(a, b, frac=0.8):
    """`a` (prediction) covers >= frac of `b` (gold) characters. The privacy
    question — is most of the identifier actually masked — instead of crediting a
    1-char touch as 'caught' (Codex audit: relaxed >=1-char is too forgiving)."""
    inter = max(0, min(a["end"], b["end"]) - max(a["start"], b["start"]))
    glen = b["end"] - b["start"]
    return glen > 0 and inter / glen >= frac


def exact(a, b):
    return a["start"] == b["start"] and a["end"] == b["end"]


def prf(c, fp, fn):
    p = c / (c + fp) if (c + fp) else 0.0
    r = c / (c + fn) if (c + fn) else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    f2 = 5 * p * r / (4 * p + r) if (4 * p + r) else 0.0
    return p, r, f1, f2


def load_gold(dataset):
    rows = [json.loads(l) for l in open(GOLD[dataset], encoding="utf-8")]
    for i, r in enumerate(rows):
        r.setdefault("doc_id", f"{dataset}-{i:03d}")
        for s in r["spans"]:
            s["canon"] = canon(s["type"])
    return rows


_WARNED = set()


def load_detector(dataset, det, gold_ids=None, docs_sha=None):
    path = os.path.join(CACHE, f"{dataset}.{det}.jsonl")
    if not os.path.exists(path):
        return None
    by_doc = {}
    for l in open(path, encoding="utf-8"):
        r = json.loads(l)
        by_doc[r["doc_id"]] = r["spans"]
    # validate against the manifest instead of trusting file existence (Codex audit)
    man_path = os.path.join(CACHE, f"{dataset}.{det}.manifest.json")
    if os.path.exists(man_path):
        man = json.load(open(man_path, encoding="utf-8"))
        if man.get("invalid_spans") and (dataset,det,"inv") not in _WARNED:
            _WARNED.add((dataset,det,"inv"))
            print(f"  ⚠ {dataset}/{det}: manifest reports {man['invalid_spans']} invalid spans")
        if gold_ids is not None and set(man.get("doc_ids", [])) != set(gold_ids) and (dataset,det,"stale") not in _WARNED:
            _WARNED.add((dataset,det,"stale"))
            print(f"  ⚠ {dataset}/{det}: cache doc set differs from gold — STALE cache, re-run detectors")
        if docs_sha is not None and man.get("docs_sha") and man["docs_sha"] != docs_sha and (dataset,det,"text") not in _WARNED:
            _WARNED.add((dataset,det,"text"))
            print(f"  ⚠ {dataset}/{det}: transcript text changed since cache was built — re-run detectors")
    elif (dataset,det,"nomani") not in _WARNED:
        _WARNED.add((dataset,det,"nomani"))
        print(f"  ⚠ {dataset}/{det}: no manifest — cannot validate")
    return by_doc


def merge_intervals(spans):
    """Interval-merge overlapping spans into the deployed redaction mask, exactly
    as anonymize.py does before redacting (this is the artifact actually written
    to the anonymized file). Overlapping spans collapse to one; the merged span's
    canonical type is that of its longest contributor (ties -> earliest), so the
    type-aware view scores the label that would survive redaction. Without this,
    overlapping detections from different layers double-count as false positives
    and distort precision / F2 / over-redaction (per the Codex design audit)."""
    if not spans:
        return []
    ss = sorted(spans, key=lambda s: (s["start"], -(s["end"] - s["start"])))
    merged = [dict(ss[0])]
    for s in ss[1:]:
        prev = merged[-1]
        if s["start"] < prev["end"]:  # overlap -> extend, keep longest contributor's type
            if (s["end"] - s["start"]) > (prev["end"] - prev["start"]):
                prev["type"], prev["canon"] = s["type"], s.get("canon", canon(s["type"]))
            prev["end"] = max(prev["end"], s["end"])
        else:
            merged.append(dict(s))
    return merged


def union_preds(dataset, members, gold_ids=None, docs_sha=None):
    """Union the cached spans of `members` per doc, then interval-merge to the
    deployed redaction mask. Returns {doc_id: [spans]} or None if a cache is
    missing."""
    caches = {}
    for m in members:
        c = load_detector(dataset, m, gold_ids, docs_sha)
        if c is None:
            return None
        caches[m] = c
    out = {}
    docs = set().union(*[set(c) for c in caches.values()])
    for d in docs:
        merged = []
        for m in members:
            for sp in caches[m].get(d, []):
                merged.append(dict(sp, canon=canon(sp["type"])))
        out[d] = merge_intervals(merged)
    return out


def score_span_coverage(gold_rows, preds, match, type_aware, prec_match=None):
    """Mask-coverage scoring against the merged redaction mask (not greedy 1:1).

    `match(pred, gold)` is the RECALL criterion: `exact`, `overlaps` (relaxed,
    >=1 char), or `contains` (>=80% of the gold span covered — the stricter,
    privacy-meaningful headline). `prec_match` is the PRECISION criterion; it
    defaults to `overlaps` because `contains` is asymmetric — a huge predicted
    span trivially contains small gold spans and would fake perfect precision
    (Codex audit #3). Precision asks only "did this masked region touch any PII".

    RECALL side: each gold span is *caught* if some predicted span matches it
    (same canonical type too, if type_aware).
    PRECISION side: each predicted span is a *hit* if it overlaps >=1 gold span,
    else over-redaction (fp).

    Returns per-canon-type counts: c (gold caught), fn (gold missed),
    pred_hit, fp. recall uses c/(c+fn); precision uses pred_hit/(pred_hit+fp)."""
    if prec_match is None:
        prec_match = overlaps
    per = {}

    def slot(t):
        return per.setdefault(t, {"c": 0, "fn": 0, "pred_hit": 0, "fp": 0})

    for g in gold_rows:
        gold = g["spans"]
        pr = preds.get(g["doc_id"], [])
        # recall: each gold independently
        for gg in gold:
            hit = any((not type_aware or gg["canon"] == p["canon"]) and match(p, gg) for p in pr)
            slot(gg["canon"])["c" if hit else "fn"] += 1
        # precision: each predicted span independently (uses prec_match = overlap)
        for p in pr:
            pc = p.get("canon", canon(p["type"]))
            hit = any((not type_aware or pc == gg["canon"]) and prec_match(p, gg) for gg in gold)
            slot(pc)["pred_hit" if hit else "fp"] += 1

    tot = {"c": 0, "fn": 0, "pred_hit": 0, "fp": 0}
    for t in per:
        for k in tot:
            tot[k] += per[t][k]
    return per, tot


# Harm weights for therapy de-id (see HARM-TAXONOMY.md). Harm != linkability:
# an email is a strong linker but low *content*-harm and rare in therapy speech;
# medication implies a diagnosis (high stigma). Qualitative levels -> coarse weights
# for an OPTIONAL harm-weighted recall reported alongside plain recall.
HARM_LEVEL = {  # canonical type -> level
    "MEDICATION": "high", "PERSON": "high",
    "LOCATION": "medium", "PROFESSION": "medium", "ORG": "medium",
    "AGE": "medium", "DATE": "medium",
    "EMAIL": "low", "PHONE": "low", "URL": "low", "HANDLE": "low",
    "ID": "low", "SNILS": "low", "INN": "low", "PASSPORT": "low",
}
HARM_WEIGHT = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def _harm_w(canon):
    return HARM_WEIGHT.get(HARM_LEVEL.get(canon, "medium"), 2)


def score_entity_level(gold_rows, preds, relaxed=True):
    """TAB-style: an entity (entity_id) is protected only if ALL its mentions
    are covered by >=1 prediction. Returns (protected, total, by_class, by_type,
    harm_weighted_recall). Requires gold spans to carry entity_id + identifier_class."""
    match = overlaps if relaxed else exact
    ents = {}  # entity_id -> {"mentions":[g...], "class":, "type":}
    for g in gold_rows:
        pr = preds.get(g["doc_id"], [])
        for s in g["spans"]:
            eid = s.get("entity_id")
            if eid is None:
                eid = f"{g['doc_id']}:{s['start']}"  # EN: treat each mention as its own entity
            e = ents.setdefault(eid, {"covered": True, "n": 0,
                                      "class": s.get("identifier_class", "direct"),
                                      "type": s["canon"]})
            e["n"] += 1
            if not any(match(s, p) for p in pr):
                e["covered"] = False
    total = len(ents)
    protected = sum(1 for e in ents.values() if e["covered"])
    by_class = {}
    by_type = {}
    for e in ents.values():
        bc = by_class.setdefault(e["class"], [0, 0])
        bc[0] += int(e["covered"]); bc[1] += 1
        bt = by_type.setdefault(e["type"], [0, 0])
        bt[0] += int(e["covered"]); bt[1] += 1
    # harm-weighted recall: each entity weighted by its type's clinical severity
    wnum = sum(_harm_w(e["type"]) * int(e["covered"]) for e in ents.values())
    wden = sum(_harm_w(e["type"]) for e in ents.values())
    harm_recall = round(wnum / wden, 3) if wden else 0.0
    return protected, total, by_class, by_type, harm_recall


def _prf2(c, fn, pred_hit, fp):
    """recall from gold coverage, precision from predicted-span hits (decoupled)."""
    r = c / (c + fn) if (c + fn) else 0.0
    p = pred_hit / (pred_hit + fp) if (pred_hit + fp) else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    f2 = 5 * p * r / (4 * p + r) if (4 * p + r) else 0.0
    return p, r, f1, f2


def metrics_block(per, tot):
    out = {"per_type": {}, "overall": {}}
    for t in sorted(per):
        d = per[t]
        p, r, f1, f2 = _prf2(d["c"], d["fn"], d["pred_hit"], d["fp"])
        out["per_type"][t] = {"support": d["c"] + d["fn"], "c": d["c"], "fp": d["fp"], "fn": d["fn"],
                              "p": round(p, 3), "r": round(r, 3), "f1": round(f1, 3), "f2": round(f2, 3)}
    p, r, f1, f2 = _prf2(tot["c"], tot["fn"], tot["pred_hit"], tot["fp"])
    types = [t for t in out["per_type"] if out["per_type"][t]["support"] > 0]
    macro_f1 = sum(out["per_type"][t]["f1"] for t in types) / len(types) if types else 0.0
    macro_r = sum(out["per_type"][t]["r"] for t in types) / len(types) if types else 0.0
    out["overall"] = {"support": tot["c"] + tot["fn"], "c": tot["c"], "fp": tot["fp"], "fn": tot["fn"],
                      "p": round(p, 3), "r": round(r, 3), "f1": round(f1, 3), "f2": round(f2, 3),
                      "macro_f1": round(macro_f1, 3), "macro_r": round(macro_r, 3)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, choices=list(GOLD))
    ap.add_argument("--out-prefix", default="")
    args = ap.parse_args()

    gold = load_gold(args.dataset)
    import hashlib as _hl
    _docs_sha = _hl.sha256(''.join(g['text'] for g in gold).encode('utf-8')).hexdigest()[:12]
    has_entity = any(s.get("entity_id") for r in gold for s in r["spans"])
    results = {"dataset": args.dataset,
               "n_docs": len(gold),
               "n_gold_mentions": sum(len(r["spans"]) for r in gold),
               "combos": {}}

    for name, members in COMBOS[args.dataset]:
        preds = union_preds(args.dataset, members, [g['doc_id'] for g in gold], _docs_sha)
        if preds is None:
            results["combos"][name] = {"status": "missing-cache", "members": members}
            continue
        # 1. span coverage (type-agnostic): strict (exact), relaxed (>=1 char),
        #    containment (>=80% of identifier masked — stricter headline)
        cov_s = metrics_block(*score_span_coverage(gold, preds, exact, False, prec_match=exact))
        cov_r = metrics_block(*score_span_coverage(gold, preds, overlaps, False))
        cov_c = metrics_block(*score_span_coverage(gold, preds, contains, False))  # prec=overlap
        # 2. type-aware, strict + relaxed (micro + macro)
        ty_s = metrics_block(*score_span_coverage(gold, preds, exact, True, prec_match=exact))
        ty_r = metrics_block(*score_span_coverage(gold, preds, overlaps, True))
        entry = {
            "members": members,
            "n_pred": sum(len(v) for v in preds.values()),
            "coverage_strict": cov_s["overall"], "coverage_relaxed": cov_r["overall"],
            "coverage_containment": cov_c["overall"],
            "type_strict": ty_s["overall"], "type_relaxed": ty_r["overall"],
            "coverage_relaxed_per_type": cov_r["per_type"],
        }
        # 3-4. entity-level (TAB) — only where gold has entity_id (RU)
        if has_entity:
            prot, total, by_class, by_type, harm_recall = score_entity_level(gold, preds, relaxed=True)
            entry["entity_level"] = {
                "protected": prot, "total": total,
                "entity_recall": round(prot / total, 3) if total else 0.0,
                "harm_weighted_recall": harm_recall,
                "by_class": {k: {"protected": v[0], "total": v[1],
                                 "recall": round(v[0] / v[1], 3) if v[1] else 0.0}
                             for k, v in by_class.items()},
                "by_type": {k: {"protected": v[0], "total": v[1],
                                "recall": round(v[0] / v[1], 3) if v[1] else 0.0}
                            for k, v in by_type.items()},
            }
        results["combos"][name] = entry

    out_json = os.path.join(HERE, f"{args.out_prefix}bench-results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    # provenance log: one committed run record (lm-eval-harness style) per scoring
    try:
        import run_registry
        star = next((e for n, e in results["combos"].items()
                     if "★" in n and isinstance(e, dict) and "coverage_relaxed" in e), None)
        headline = {"n_docs": results["n_docs"], "n_gold": results["n_gold_mentions"]}
        if star:
            headline["default_coverage_recall"] = star["coverage_relaxed"]["r"]
            headline["default_coverage_f2"] = star["coverage_relaxed"]["f2"]
            if "entity_level" in star:
                headline["default_entity_recall"] = star["entity_level"]["entity_recall"]
                headline["default_harm_weighted_recall"] = star["entity_level"].get("harm_weighted_recall")
        run_registry.log_run("score_bench", args.dataset, headline,
                             extra={"combos": {n: e.get("coverage_relaxed")
                                               for n, e in results["combos"].items()
                                               if isinstance(e, dict) and "coverage_relaxed" in e}})
    except Exception:
        pass
    # console summary
    print(f"\n=== {args.dataset}: {results['n_docs']} docs, {results['n_gold_mentions']} gold mentions ===")
    hdr = f"{'combo':28} {'covF2(rel)':>10} {'covR':>6} {'typeF2':>7} {'macroF1':>8}"
    if has_entity:
        hdr += f" {'entR':>6} {'directR':>8} {'quasiR':>7}"
    print(hdr)
    for name, e in results["combos"].items():
        if e.get("status") == "missing-cache":
            print(f"{name:28} (missing cache: {'+'.join(e['members'])})"); continue
        line = (f"{name:28} {e['coverage_relaxed']['f2']:>10.3f} {e['coverage_relaxed']['r']:>6.3f} "
                f"{e['type_relaxed']['f2']:>7.3f} {e['type_relaxed']['macro_f1']:>8.3f}")
        if has_entity and "entity_level" in e:
            el = e["entity_level"]
            d = el["by_class"].get("direct", {}).get("recall", 0.0)
            q = el["by_class"].get("quasi", {}).get("recall", 0.0)
            line += f" {el['entity_recall']:>6.3f} {d:>8.3f} {q:>7.3f}"
        print(line)
    print(f"\n[score] wrote {os.path.relpath(out_json)}")


if __name__ == "__main__":
    main()
