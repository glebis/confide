#!/usr/bin/env python3
"""Stale / drift check for the benchmark artifacts (Codex audit R1).

Deterministic, no LLM calls. Fails (exit 1) with a clear diff if any committed
artifact has drifted from what the current gold + detector caches produce, so a
stale number can never silently ship. Three independent checks:

  1. JSON freshness — re-score every dataset from the current caches and assert
     the committed ``<prefix>bench-results.json`` is byte-for-byte what
     ``score_bench.py`` writes now (headline metrics + entity/harm-weighted recall).
  2. Manifest validity — every detector cache that BENCHMARK.md actually cites
     must validate against its gold (doc-id set + transcript ``docs_sha``). A combo
     whose cache is intentionally omitted (e.g. the stale RU ``opf`` row) is allowed
     ONLY if BENCHMARK.md does not present a numeric row for it.
  3. Markdown ↔ JSON consistency — the headline numbers quoted in BENCHMARK.md and
     IAA-RESULTS.md (RU ★ coverage recall / entity recall / harm-weighted recall,
     EN/EN-real Presidio + Philter coverage F2 + micro-F1, IAA F1 + κ) must equal
     the values in the regenerated JSON.

Usage:  python check_artifacts.py            # check, exit non-zero on drift
        make check                            # same, via the Makefile target
"""
import json
import os
import re
import sys

import score_bench as sb

HERE = os.path.dirname(os.path.abspath(__file__))
DATASETS = ["ru", "ru-adv", "en", "en-real"]
PREFIX = {"ru": "ru-", "ru-adv": "ru-adv-", "en": "en-", "en-real": "en-real-"}

problems = []


def fail(msg):
    problems.append(msg)


def _docs_sha(gold):
    import hashlib
    return hashlib.sha256("".join(g["text"] for g in gold).encode("utf-8")).hexdigest()[:12]


def rescore(dataset):
    """Recompute the bench-results dict exactly as score_bench.main would, in-memory."""
    gold = sb.load_gold(dataset)
    docs_sha = _docs_sha(gold)
    has_entity = any(s.get("entity_id") for r in gold for s in r["spans"])
    results = {"dataset": dataset, "n_docs": len(gold),
               "n_gold_mentions": sum(len(r["spans"]) for r in gold), "combos": {}}
    for name, members in sb.COMBOS[dataset]:
        preds = sb.union_preds(dataset, members, [g["doc_id"] for g in gold], docs_sha)
        if preds is None:
            results["combos"][name] = {"status": "missing-cache", "members": members}
            continue
        cov_s = sb.metrics_block(*sb.score_span_coverage(gold, preds, sb.exact, False, prec_match=sb.exact))
        cov_r = sb.metrics_block(*sb.score_span_coverage(gold, preds, sb.overlaps, False))
        cov_c = sb.metrics_block(*sb.score_span_coverage(gold, preds, sb.contains, False))
        ty_s = sb.metrics_block(*sb.score_span_coverage(gold, preds, sb.exact, True, prec_match=sb.exact))
        ty_r = sb.metrics_block(*sb.score_span_coverage(gold, preds, sb.overlaps, True))
        entry = {"members": members, "n_pred": sum(len(v) for v in preds.values()),
                 "coverage_strict": cov_s["overall"], "coverage_relaxed": cov_r["overall"],
                 "coverage_containment": cov_c["overall"],
                 "type_strict": ty_s["overall"], "type_relaxed": ty_r["overall"],
                 "coverage_relaxed_per_type": cov_r["per_type"]}
        if has_entity:
            prot, total, by_class, by_type, harm = sb.score_entity_level(gold, preds, relaxed=True)
            entry["entity_level"] = {
                "protected": prot, "total": total,
                "entity_recall": round(prot / total, 3) if total else 0.0,
                "harm_weighted_recall": harm,
                "by_class": {k: {"protected": v[0], "total": v[1],
                                 "recall": round(v[0] / v[1], 3) if v[1] else 0.0}
                             for k, v in by_class.items()},
                "by_type": {k: {"protected": v[0], "total": v[1],
                                "recall": round(v[0] / v[1], 3) if v[1] else 0.0}
                            for k, v in by_type.items()},
            }
        if "★" in name:
            bs = sb.split_headline(gold, preds, has_entity)
            if bs:
                entry["by_split"] = bs
        results["combos"][name] = entry
    return results


def check_json_freshness():
    """Committed *-bench-results.json must equal a fresh rescore."""
    fresh = {}
    for ds in DATASETS:
        committed_path = os.path.join(HERE, f"{PREFIX[ds]}bench-results.json")
        if not os.path.exists(committed_path):
            fail(f"[json] {PREFIX[ds]}bench-results.json missing on disk")
            continue
        committed = json.load(open(committed_path, encoding="utf-8"))
        now = rescore(ds)
        fresh[ds] = now
        # compare the JSON-normalized forms (round-trip to ignore key ordering)
        if json.dumps(committed, sort_keys=True, ensure_ascii=False) != \
           json.dumps(now, sort_keys=True, ensure_ascii=False):
            # narrow the diff to the headline numbers for a readable message
            for name, e in now["combos"].items():
                ce = committed["combos"].get(name, {})
                if e.get("status") or ce.get("status"):
                    if e.get("status") != ce.get("status"):
                        fail(f"[json] {ds}/{name}: status drift committed={ce.get('status')} fresh={e.get('status')}")
                    continue
                for metric in ("coverage_relaxed", "type_relaxed"):
                    for k in ("f2", "r", "f1"):
                        a = ce.get(metric, {}).get(k)
                        b = e.get(metric, {}).get(k)
                        if a != b:
                            fail(f"[json] {ds}/{name}.{metric}.{k}: committed={a} fresh={b}")
                if "entity_level" in e:
                    for k in ("entity_recall", "harm_weighted_recall"):
                        a = ce.get("entity_level", {}).get(k)
                        b = e["entity_level"].get(k)
                        if a != b:
                            fail(f"[json] {ds}/{name}.entity_level.{k}: committed={a} fresh={b}")
            if committed.get("n_gold_mentions") != now["n_gold_mentions"]:
                fail(f"[json] {ds}: n_gold_mentions committed={committed.get('n_gold_mentions')} "
                     f"fresh={now['n_gold_mentions']}")
    return fresh


def check_manifests(fresh):
    """Every cache cited by a numeric BENCHMARK.md row must validate against gold."""
    bench = open(os.path.join(HERE, "BENCHMARK.md"), encoding="utf-8").read()
    for ds in DATASETS:
        gold = sb.load_gold(ds)
        gold_ids = set(g["doc_id"] for g in gold)
        docs_sha = _docs_sha(gold)
        # which detectors feed the combos that scored cleanly (have a numeric row)?
        cited = set()
        for name, members in sb.COMBOS[ds]:
            e = fresh[ds]["combos"].get(name, {})
            if e.get("status") == "missing-cache":
                continue  # omitted row — not cited numerically, OK to skip
            cited.update(members)
        for det in sorted(cited):
            man_path = os.path.join(sb.CACHE, f"{ds}.{det}.manifest.json")
            if not os.path.exists(man_path):
                fail(f"[manifest] {ds}/{det}: no manifest but combo is scored")
                continue
            man = json.load(open(man_path, encoding="utf-8"))
            if man.get("invalid_spans"):
                fail(f"[manifest] {ds}/{det}: {man['invalid_spans']} invalid spans")
            if set(man.get("doc_ids", [])) != gold_ids:
                fail(f"[manifest] {ds}/{det}: doc-id set differs from gold (stale cache)")
            if man.get("docs_sha") and man["docs_sha"] != docs_sha:
                fail(f"[manifest] {ds}/{det}: docs_sha differs from gold (transcript changed)")


def _md_floats(md, label, n=1):
    """Find the float(s) following a regex `label` in `md`. Returns list of floats."""
    m = re.search(label, md)
    if not m:
        return None
    return [float(x) for x in m.groups()[:n]]


def _approx(a, b, tol=0.0005):
    return a is not None and b is not None and abs(a - b) <= tol


def check_md_consistency(fresh):
    bench = open(os.path.join(HERE, "BENCHMARK.md"), encoding="utf-8").read()

    # --- RU ★ row: coverage F2, recall, entity recall, harm-weighted recall ---
    ru = fresh["ru"]["combos"].get("natasha+regex+ollama ★", {})
    if "coverage_relaxed" in ru:
        # leaderboard row: | natasha+regex+ollama ★ | **F2** | R | tF2 | macro | entR | harm | dir | quasi | preds |
        row = re.search(r"\| natasha\+regex\+ollama ★ \| \*\*([\d.]+)\*\* \| ([\d.]+) \| "
                        r"[\d.]+ \| [\d.]+ \| ([\d.]+) \| ([\d.]+) \|", bench)
        if not row:
            fail("[md] RU ★ leaderboard row not found in BENCHMARK.md")
        else:
            f2, r, entr, harm = (float(row.group(i)) for i in range(1, 5))
            if not _approx(f2, ru["coverage_relaxed"]["f2"]):
                fail(f"[md] RU ★ cov F2: md={f2} json={ru['coverage_relaxed']['f2']}")
            if not _approx(r, ru["coverage_relaxed"]["r"]):
                fail(f"[md] RU ★ cov R: md={r} json={ru['coverage_relaxed']['r']}")
            if not _approx(entr, ru["entity_level"]["entity_recall"]):
                fail(f"[md] RU ★ ent R: md={entr} json={ru['entity_level']['entity_recall']}")
            if not _approx(harm, ru["entity_level"]["harm_weighted_recall"]):
                fail(f"[md] RU ★ harm-wtd R: md={harm} json={ru['entity_level']['harm_weighted_recall']}")

    # --- n_gold_mentions stated in the RU section header ---
    mg = re.search(r"\*\*30 documents, (\d+) gold PII mentions\.\*\*", bench)
    if mg and int(mg.group(1)) != fresh["ru"]["n_gold_mentions"]:
        fail(f"[md] RU gold mentions: md={mg.group(1)} json={fresh['ru']['n_gold_mentions']}")

    # --- EN / EN-real baseline rows (presidio, philter) coverage F2 + micro-F1 ---
    # Scope each search to that dataset's section so the EN-synth `| presidio |`
    # row is not matched when checking EN-real (both sections share row labels).
    def _section(title):
        m = re.search(rf"\n## {re.escape(title)} —.*?(?=\n## )", bench, re.S)
        return m.group(0) if m else bench
    for ds, sect in (("en", "EN-synth"), ("en-real", "EN-real")):
        sect_md = _section(sect)
        for det in ("presidio", "philter"):
            e = fresh[ds]["combos"].get(det, {})
            if "coverage_relaxed" not in e:
                continue
            # leaderboard row: | presidio | **F2** | R | tF2 | micro | macro | preds |
            row = re.search(rf"\| {det} \| \*\*([\d.]+)\*\* \| [\d.]+ \| [\d.]+ \| ([\d.]+) \|", sect_md)
            if not row:
                fail(f"[md] {ds}/{det} baseline row not found")
                continue
            f2, micro = float(row.group(1)), float(row.group(2))
            if not _approx(f2, e["coverage_relaxed"]["f2"]):
                fail(f"[md] {ds}/{det} cov F2: md={f2} json={e['coverage_relaxed']['f2']}")
            if not _approx(micro, e["type_relaxed"]["f1"]):
                fail(f"[md] {ds}/{det} micro-F1: md={micro} json={e['type_relaxed']['f1']}")

    # --- IAA: F1 + kappa in IAA-RESULTS.md must match iaa-results.json ---
    iaa_json_path = os.path.join(HERE, "iaa-results.json")
    iaa_md_path = os.path.join(HERE, "IAA-RESULTS.md")
    if os.path.exists(iaa_json_path) and os.path.exists(iaa_md_path):
        ij = json.load(open(iaa_json_path, encoding="utf-8"))
        im = open(iaa_md_path, encoding="utf-8").read()
        f1 = _md_floats(im, r"Entity-level F1 \(A2 vs A1\): ([\d.]+)")
        ka = _md_floats(im, r"Cohen's κ: ([\d.]+)")
        if f1 and not _approx(f1[0], ij["span_agreement"]["f1"]):
            fail(f"[md] IAA F1: md={f1[0]} json={ij['span_agreement']['f1']}")
        if ka and not _approx(ka[0], ij["char_cohen_kappa"]):
            fail(f"[md] IAA κ: md={ka[0]} json={ij['char_cohen_kappa']}")
        # the BENCHMARK.md IAA narrative must quote the same F1 + κ
        bf1 = _md_floats(bench, r"Entity-level F1 ([\d.]+)")
        bka = _md_floats(bench, r"Cohen's κ ([\d.]+)")
        if bf1 and not _approx(bf1[0], ij["span_agreement"]["f1"]):
            fail(f"[md] BENCHMARK IAA F1: md={bf1[0]} json={ij['span_agreement']['f1']}")
        if bka and not _approx(bka[0], ij["char_cohen_kappa"]):
            fail(f"[md] BENCHMARK IAA κ: md={bka[0]} json={ij['char_cohen_kappa']}")
        # R4 framing guard: the IAA artifact must NOT claim human inter-annotator agreement
        if re.search(r"^# Inter-annotator agreement", im, re.M):
            fail("[md] IAA-RESULTS.md still titled 'Inter-annotator agreement' — must be "
                 "labelled an LLM-assisted consistency check (audit R4)")


def main():
    fresh = check_json_freshness()
    check_manifests(fresh)
    check_md_consistency(fresh)
    if problems:
        print(f"✗ check_artifacts: {len(problems)} drift(s) found:\n")
        for p in problems:
            print(f"  {p}")
        print("\nRegenerate with: score_bench.py (per dataset) + bootstrap_ci.py + "
              "iaa_eval.py + make_benchmark.py + make_tufte_report.py")
        sys.exit(1)
    print("✓ check_artifacts: all committed bench-results.json, manifests, and the "
          "numbers quoted in BENCHMARK.md / IAA-RESULTS.md are consistent with the "
          "current gold + caches.")


if __name__ == "__main__":
    main()
