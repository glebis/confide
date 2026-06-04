#!/usr/bin/env python3
"""Score arbitrary local LLM detector caches outside the fixed benchmark COMBOS."""
import argparse
import hashlib
import json
import os

from confide_eval import paths
from confide_eval.scoring import score_bench as sb

CACHE = os.fspath(paths.CACHE)


def _docs_sha(rows: list[dict]) -> str:
    return hashlib.sha256("".join(r["text"] for r in rows).encode("utf-8")).hexdigest()[:12]


def _select_gold(dataset: str, doc_ids: str | None) -> tuple[list[dict], list[dict]]:
    if dataset == "en-real" and not sb.en_real_text_present():
        raise SystemExit(sb.EN_REAL_FETCH_HINT)
    full = sb.load_gold(dataset)
    if not doc_ids:
        return full, full
    wanted = [d.strip() for d in doc_ids.split(",") if d.strip()]
    by_id = {d["doc_id"]: d for d in full}
    missing = [d for d in wanted if d not in by_id]
    if missing:
        raise SystemExit(f"unknown doc_id(s): {', '.join(missing)}")
    return full, [by_id[d] for d in wanted]


def default_stack(dataset: str, detector: str) -> list[str]:
    if dataset.startswith("ru"):
        return ["natasha", "regex", detector]
    return ["opf", "regex", detector]


def _load_detector_selected(dataset: str, det: str, selected_ids: list[str],
                            selected_sha: str, full_sha: str) -> dict | None:
    path = os.path.join(CACHE, f"{dataset}.{det}.jsonl")
    if not os.path.exists(path):
        print(f"  WARNING {dataset}/{det}: missing cache")
        return None
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    by_doc = {r["doc_id"]: r["spans"] for r in rows}
    missing = [d for d in selected_ids if d not in by_doc]
    if missing:
        print(f"  WARNING {dataset}/{det}: cache lacks selected doc(s): {', '.join(missing)}")
        return None

    man_path = os.path.join(CACHE, f"{dataset}.{det}.manifest.json")
    if os.path.exists(man_path):
        man = json.load(open(man_path, encoding="utf-8"))
        if man.get("invalid_spans"):
            print(f"  WARNING {dataset}/{det}: manifest reports {man['invalid_spans']} invalid spans")
            return None
        man_ids = set(man.get("doc_ids", []))
        if man_ids and not set(selected_ids).issubset(man_ids):
            print(f"  WARNING {dataset}/{det}: manifest doc set does not cover selected docs")
            return None
        man_sha = man.get("docs_sha")
        if man_sha and man_sha not in {selected_sha, full_sha}:
            print(f"  WARNING {dataset}/{det}: manifest transcript hash differs from selected/full gold")
            return None
    else:
        print(f"  WARNING {dataset}/{det}: no manifest; using cache without provenance validation")

    return {did: by_doc[did] for did in selected_ids}


def union_selected(dataset: str, members: list[str], selected_gold: list[dict],
                   selected_sha: str, full_sha: str) -> dict | None:
    selected_ids = [g["doc_id"] for g in selected_gold]
    pred = {did: [] for did in selected_ids}
    for m in members:
        cache = _load_detector_selected(dataset, m, selected_ids, selected_sha, full_sha)
        if cache is None:
            return None
        for did in selected_ids:
            for span in cache[did]:
                sp = dict(span)
                sp["canon"] = sb.canon(sp["type"])
                pred[did].append(sp)
    return {did: sb.merge_intervals(spans) for did, spans in pred.items()}


def metrics_entry(dataset: str, name: str, members: list[str], full_gold: list[dict],
                  selected_gold: list[dict]) -> dict:
    selected_sha = _docs_sha(selected_gold)
    full_sha = _docs_sha(full_gold)
    preds = union_selected(dataset, members, selected_gold, selected_sha, full_sha)
    if preds is None:
        return {"status": "missing-cache", "members": members}

    has_entity = any(s.get("entity_id") for r in selected_gold for s in r["spans"])
    cov_r = sb.metrics_block(*sb.score_span_coverage(selected_gold, preds, sb.overlaps, False))
    cov_c = sb.metrics_block(*sb.score_span_coverage(selected_gold, preds, sb.contains, False))
    ty_r = sb.metrics_block(*sb.score_span_coverage(selected_gold, preds, sb.overlaps, True))
    out = {
        "members": members,
        "n_pred": sum(len(v) for v in preds.values()),
        "coverage_relaxed": cov_r["overall"],
        "coverage_containment": cov_c["overall"],
        "type_relaxed": ty_r["overall"],
        "coverage_relaxed_per_type": cov_r["per_type"],
    }
    if has_entity:
        prot, total, by_class, by_type, harm_recall = sb.score_entity_level(selected_gold, preds, relaxed=True)
        out["entity_level"] = {
            "protected": prot,
            "total": total,
            "entity_recall": round(prot / total, 3) if total else 0.0,
            "harm_weighted_recall": harm_recall,
            "by_class": {k: {"protected": v[0], "total": v[1],
                             "recall": round(v[0] / v[1], 3) if v[1] else 0.0}
                         for k, v in by_class.items()},
            "by_type": {k: {"protected": v[0], "total": v[1],
                            "recall": round(v[0] / v[1], 3) if v[1] else 0.0}
                        for k, v in by_type.items()},
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, choices=list(paths.GOLD))
    ap.add_argument("--detectors", required=True,
                    help="comma-separated custom detector names, e.g. local-gemma3-4b-p1")
    ap.add_argument("--doc-ids", help="score only a small sample")
    ap.add_argument("--mode", choices=["llm-only", "stack", "both"], default="both")
    ap.add_argument("--include-default-ollama", action="store_true",
                    help="also score the committed qwen2.5:3b detector cache")
    ap.add_argument("--out", help="output JSON path")
    args = ap.parse_args()

    full_gold, selected_gold = _select_gold(args.dataset, args.doc_ids)
    detectors = [d.strip() for d in args.detectors.split(",") if d.strip()]
    if args.include_default_ollama and "ollama" not in detectors:
        detectors.insert(0, "ollama")

    results = {
        "dataset": args.dataset,
        "doc_ids": [g["doc_id"] for g in selected_gold],
        "n_docs": len(selected_gold),
        "n_gold_mentions": sum(len(g["spans"]) for g in selected_gold),
        "comparisons": {},
    }
    for det in detectors:
        if args.mode in {"llm-only", "both"}:
            name = f"{det} :: llm-only"
            results["comparisons"][name] = metrics_entry(
                args.dataset, name, [det], full_gold, selected_gold
            )
        if args.mode in {"stack", "both"}:
            members = default_stack(args.dataset, det)
            name = f"{det} :: {'+'.join(members)}"
            results["comparisons"][name] = metrics_entry(
                args.dataset, name, members, full_gold, selected_gold
            )

    out_path = args.out or os.path.join(
        os.fspath(paths.RESULTS), f"local-llm-experiment-{args.dataset}.json"
    )
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n=== {args.dataset}: {len(selected_gold)} docs, "
          f"{results['n_gold_mentions']} gold mentions ===")
    print(f"{'candidate':48} {'maskCovR':>8} {'typeF2':>7} {'entR':>6} {'nPred':>6}")
    for name, e in results["comparisons"].items():
        if e.get("status") == "missing-cache":
            print(f"{name:48} missing cache")
            continue
        ent = e.get("entity_level", {}).get("entity_recall")
        ent_s = f"{ent:.3f}" if isinstance(ent, float) else "-"
        print(f"{name:48} {e['coverage_relaxed']['r']:>8.3f} "
              f"{e['type_relaxed']['f2']:>7.3f} {ent_s:>6} {e['n_pred']:>6}")
    print(f"\n[score] wrote {os.path.relpath(out_path)}")


if __name__ == "__main__":
    main()
