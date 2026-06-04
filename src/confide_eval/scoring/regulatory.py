#!/usr/bin/env python3
"""Regulatory / identifiability residual-risk metrics for CONFIDE-Bench.

Beyond detection (recall/F2), regulators care about *residual risk*. This module
assembles four families that map to named regulatory concepts, reusing existing
machinery rather than recomputing it:

  1. WP29 (Art-29 WP 05/2014) re-identification triad
       - singling out  -> residual quasi surface (confide_eval.scoring.kanon, a
         caveated population-fraction estimator; NOT corpus k-anonymity, N is tiny)
       - linkability    -> results/linkability-results.json (pairwise metric)
       - inference      -> results/reconstruction-results.json B_inference_attack
  2. HIPAA-inspired Safe-Harbor coverage (NOT legal certification)
  3. Residual-risk tier (ordinal RED/AMBER/GREEN; no scalar index)
  4. Worst-case leak (per-doc containment recall + leaked mentions / 10k chars)

Writes results/regulatory-results.json. Pure cores are unit-tested; see
tests/test_regulatory.py.
"""
import hashlib
import json
import os

from confide_eval import paths
from confide_eval.scoring import kanon
from confide_eval.scoring import score_bench as sb

RESULTS = os.fspath(paths.RESULTS)

# --- HIPAA Safe-Harbor mapping (illustrative; NOT a legal determination) ----
# Maps CONFIDE types onto the §164.514(b)(2) categories we can honestly assert.
HIPAA_MAP = {
    "PERSON": "A: names",
    "LOCATION": "B: geographic (< state)",
    "DATE": "C: dates",
    "PHONE": "D: phone",
    "FAX": "E: fax",
    "EMAIL": "F: email",
    "URL": "N: URLs",
    "IP": "O: IP address",
    "ID": "G-M: structured IDs (collapsed)",  # no id_subtype in gold -> cannot split
}
# AGE: only ages > 89 are HIPAA identifiers and the gold carries no age value,
# so we cannot assert this category -> N/A.
HIPAA_NA = {"AGE"}
# Clinical quasi-identifiers: outside HIPAA-18, reported as special-category risk.
HIPAA_SPECIAL = {"MEDICATION", "PROFESSION", "DIAGNOSIS"}


def hipaa_coverage(per_type):
    """HIPAA-inspired Safe-Harbor coverage from a per-type {TYPE:{support,fn}} map.

    A mapped category PASSES iff it has support and no leaked mentions (fn == 0).
    AGE is N/A; medication/profession are special-category (excluded from HIPAA).
    """
    categories, na, special, unmapped = {}, [], [], []
    applicable = passed = 0
    for typ, m in per_type.items():
        support = m.get("support", 0)
        if support <= 0:
            continue
        if typ in HIPAA_NA:
            na.append(typ)
            continue
        if typ in HIPAA_SPECIAL:
            special.append(typ)
            continue
        if typ not in HIPAA_MAP:
            unmapped.append(typ)
            continue
        fn = m.get("fn", 0)
        ok = fn == 0
        categories[typ] = {"hipaa": HIPAA_MAP[typ], "support": support, "fn": fn, "passed": ok}
        applicable += 1
        passed += 1 if ok else 0
    return {
        "categories": categories,
        "na": sorted(na),
        "special_category": sorted(special),
        "unmapped": sorted(unmapped),
        "applicable": applicable,
        "passed": passed,
        "removed_frac": (passed / applicable) if applicable else 0.0,
        "note": "HIPAA-inspired coverage, not legal certification. AGE is N/A "
                "(only ages>89 count, no value in gold); structured IDs collapsed.",
    }


def residual_risk_tier(direct_residual, special_residual, inference_rate, linkability_above_base):
    """Ordinal residual-risk tier (no scalar index).

    RED   = any direct identifier leaks (a re-identification key survives).
    AMBER = special-category residual, nonzero inference, or linkability > chance.
    GREEN = all residual-risk tests clear.
    """
    if direct_residual > 0:
        return "RED"
    if special_residual > 0 or inference_rate > 0 or linkability_above_base:
        return "AMBER"
    return "GREEN"


def percentile(values, p):
    """Linear-interpolated percentile; empty -> 0.0."""
    xs = sorted(values)
    if not xs:
        return 0.0
    if len(xs) == 1:
        return xs[0]
    k = (len(xs) - 1) * p / 100.0
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    if f == c:
        return xs[f]
    return xs[f] * (c - k) + xs[c] * (k - f)


def worst_case_leak(per_doc):
    """Worst-case residual leak across docs.

    per_doc: [{doc_id, leaked, gold, chars}] where `leaked` is leaked *mentions*
    (gold spans not masked under containment). Reports min/p10/mean recall, totals,
    leaked mentions per 10k characters, and the worst doc.
    """
    if not per_doc:
        return {"min_recall": 1.0, "p10_recall": 1.0, "mean_recall": 1.0,
                "total_leaked": 0, "total_gold": 0, "total_chars": 0,
                "leaked_per_10k_chars": 0.0, "worst_doc": None, "n_docs": 0}
    recalls = []
    for d in per_doc:
        g = d["gold"]
        recalls.append((g - d["leaked"]) / g if g else 1.0)
    total_leaked = sum(d["leaked"] for d in per_doc)
    total_gold = sum(d["gold"] for d in per_doc)
    total_chars = sum(d["chars"] for d in per_doc)
    worst = min(per_doc, key=lambda d: ((d["gold"] - d["leaked"]) / d["gold"] if d["gold"] else 1.0,
                                        -d["leaked"]))
    return {
        "min_recall": round(min(recalls), 4),
        "p10_recall": round(percentile(recalls, 10), 4),
        "mean_recall": round(sum(recalls) / len(recalls), 4),
        "total_leaked": total_leaked,
        "total_gold": total_gold,
        "total_chars": total_chars,
        "leaked_per_10k_chars": round(total_leaked / (total_chars / 10000.0), 3) if total_chars else 0.0,
        "worst_doc": worst["doc_id"],
        "n_docs": len(per_doc),
    }


def is_spelled_out_digit(type_, text):
    """A structured identifier written out in words (no digits) — out of scope
    for the regex layer by design (e.g. a phone/policy number dictated aloud)."""
    return type_ in {"PHONE", "ID"} and not any(ch.isdigit() for ch in text)


def split_direct_residual(leaked_entities):
    """Split unprotected direct entities into in-scope vs out-of-scope.

    leaked_entities: [{entity_id, leaked:[{type,text}]}]. An entity is OUT-of-scope
    only if EVERY one of its leaked mentions is a spelled-out digit string; one
    in-scope leak makes the whole entity in-scope. The tier is driven by in-scope.
    """
    in_ids, oos_ids = [], []
    for e in leaked_entities:
        ms = e.get("leaked", [])
        if ms and all(is_spelled_out_digit(m["type"], m["text"]) for m in ms):
            oos_ids.append(e["entity_id"])
        else:
            in_ids.append(e["entity_id"])
    return {"in_scope": len(in_ids), "out_of_scope": len(oos_ids),
            "in_scope_ids": in_ids, "out_of_scope_ids": oos_ids}


def inference_summary(recon):
    """Aggregate the B_inference_attack block into recovered/tested + per-client rate."""
    by = recon.get("B_inference_attack", {})
    rec = tot = 0
    by_client = {}
    for cl, v in by.items():
        if not isinstance(v, dict):
            continue
        nr, nt = v.get("n_recovered", 0), v.get("n_tested", 0)
        rec += nr
        tot += nt
        by_client[cl] = round(nr / nt, 4) if nt else 0.0
    return {"n_recovered": rec, "n_tested": tot,
            "rate": round(rec / tot, 4) if tot else 0.0, "by_client": by_client}


# ----------------------------------------------------------- orchestration
def _load(name):
    p = os.path.join(RESULTS, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def _star_combo(res):
    for n, e in res["combos"].items():
        if "★" in n and isinstance(e, dict) and "coverage_relaxed_per_type" in e:
            return n, e
    return None, None


def _per_doc_leak(dataset, members):
    """Recompute per-doc leaked mentions under containment via score_bench helpers."""
    gold = sb.load_gold(dataset)
    docs_sha = hashlib.sha256("".join(g["text"] for g in gold).encode("utf-8")).hexdigest()[:12]
    preds = sb.union_preds(dataset, members, [g["doc_id"] for g in gold], docs_sha)
    if preds is None:
        return []
    per_doc = []
    for g in gold:
        pr = preds.get(g["doc_id"], [])
        leaked = sum(0 if any(sb.contains(p, s) for p in pr) else 1 for s in g["spans"])
        per_doc.append({"doc_id": g["doc_id"], "leaked": leaked,
                        "gold": len(g["spans"]), "chars": len(g["text"])})
    return per_doc


def _direct_leak_entities(dataset, members):
    """Unprotected DIRECT entities (grouped by entity_id across docs) with the
    specific mentions that leaked — for the in-scope/out-of-scope split."""
    gold = sb.load_gold(dataset)
    docs_sha = hashlib.sha256("".join(g["text"] for g in gold).encode("utf-8")).hexdigest()[:12]
    preds = sb.union_preds(dataset, members, [g["doc_id"] for g in gold], docs_sha)
    if preds is None:
        return []
    ents = {}
    for g in gold:
        pr = preds.get(g["doc_id"], [])
        for s in g["spans"]:
            if s.get("identifier_class") != "direct":
                continue
            eid = s.get("entity_id") or f'{g["doc_id"]}:{s["start"]}'
            e = ents.setdefault(eid, {"entity_id": eid, "leaked": []})
            if not any(sb.overlaps(s, p) for p in pr):  # not even 1 char masked
                e["leaked"].append({"type": s["type"], "text": g["text"][s["start"]:s["end"]]})
    return [e for e in ents.values() if e["leaked"]]


def compute(dataset):
    if dataset == "en-real" and not paths.en_real_text_present():
        # EN-real source text is fetch-required (ai4privacy license; not
        # redistributed). The per-doc/per-entity leak recompute needs the text;
        # without the local gitignored JSONL we cannot recompute it, so skip.
        print("[regulatory] en-real source text not present — run "
              "`python -m confide_eval.data.fetch_ai4privacy` to include it. Skipping.")
        raise FileNotFoundError("en-real source text not fetched")
    res = _load(f"{dataset}-bench-results.json")
    if not res:
        raise FileNotFoundError(f"{dataset}-bench-results.json")
    name, combo = _star_combo(res)
    hip = hipaa_coverage(combo.get("coverage_relaxed_per_type", {}))

    el = combo.get("entity_level", {})
    med = el.get("by_type", {}).get("MEDICATION", {})
    special_residual = med.get("total", 0) - med.get("protected", 0)

    # Recompute direct leaks per entity and split in-scope vs out-of-scope
    # (spelled-out digit IDs are out of scope for the regex layer by design).
    members = combo.get("members", [])
    direct_leaks = _direct_leak_entities(dataset, members)
    dsplit = split_direct_residual(direct_leaks)
    direct_in_scope = dsplit["in_scope"]

    recon = _load("reconstruction-results.json")
    inf = inference_summary(recon) if recon else {"n_recovered": 0, "n_tested": 0, "rate": 0.0, "by_client": {}}

    link = _load("linkability-results.json")
    link_metrics = (link or {}).get("metrics", {})
    roc = link_metrics.get("roc_auc", 0.0)
    link_above_base = roc > 0.5

    singling = []
    if dataset == "ru":
        try:
            surv = kanon.surviving_quasi()
            for cl in sorted(surv):
                singling.append(kanon.singling_out(cl, surv[cl]))
        except Exception:  # caches absent in a fresh checkout
            singling = []

    worst = worst_case_leak(_per_doc_leak(dataset, members))
    # In-scope direct residual drives the tier; out-of-scope (spelled-out) is reported alongside.
    tier = residual_risk_tier(direct_in_scope, special_residual, inf["rate"], link_above_base)

    return {
        "dataset": dataset,
        "combo": name,
        "wp29": {
            "singling_out": {"clients": singling, "caveat": kanon.independence_caveat()},
            "linkability": {"roc_auc": roc, "recall": link_metrics.get("recall"),
                            "f1": link_metrics.get("f1"), "above_chance": link_above_base},
            "inference": inf,
        },
        "hipaa": hip,
        "tier": {
            "tier": tier,
            "direct_residual": direct_in_scope,            # in-scope drives the tier
            "direct_residual_out_of_scope": dsplit["out_of_scope"],
            "out_of_scope_ids": dsplit["out_of_scope_ids"],
            "in_scope_ids": dsplit["in_scope_ids"],
            "special_residual": special_residual,
            "inference_rate": inf["rate"],
            "linkability_above_base": link_above_base,
        },
        "worst_case": worst,
    }


def main():
    out = {"datasets": {}}
    for ds in ("ru", "en", "en-real"):
        try:
            out["datasets"][ds] = compute(ds)
        except FileNotFoundError:
            continue
    path = os.path.join(RESULTS, "regulatory-results.json")
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[regulatory] wrote {os.path.relpath(path)} "
          f"({len(out['datasets'])} datasets)")


if __name__ == "__main__":
    main()
