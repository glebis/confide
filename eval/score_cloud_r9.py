#!/usr/bin/env python3
"""R9 head-to-head: score the cloud LLM detector cache vs the local qwen2.5:3b
('ollama') cache, reusing score_bench's exact metric functions. Emits a small
JSON with entity recall, harm-weighted recall, per-type recall for the LLM-only
types, n_pred, and ms/doc, for: the LLM layer alone, and the full RU stack with
each LLM swapped in."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
import score_bench as sb

LLM_TYPES = ["MEDICATION", "AGE", "DATE", "PROFESSION", "ID", "PHONE", "EMAIL"]


def score_combo(gold, members, docs_sha):
    preds = sb.union_preds("ru", members, [g["doc_id"] for g in gold], docs_sha)
    if preds is None:
        return {"status": "missing-cache", "members": members}
    cov_r = sb.metrics_block(*sb.score_span_coverage(gold, preds, sb.overlaps, False))
    prot, total, by_class, by_type, harm = sb.score_entity_level(gold, preds, relaxed=True)
    pt = cov_r["per_type"]
    return {
        "members": members,
        "n_pred": sum(len(v) for v in preds.values()),
        "entity_recall": round(prot / total, 3) if total else 0.0,
        "harm_weighted_recall": harm,
        "protected": prot, "total": total,
        "per_type_recall": {t: {"support": pt[t]["support"], "c": pt[t]["c"], "r": pt[t]["r"]}
                            for t in LLM_TYPES if t in pt},
    }


def manifest_seconds(det):
    m = json.load(open(os.path.join(sb.CACHE, f"ru.{det}.manifest.json")))
    return m.get("seconds"), m.get("n_docs"), m.get("model")


def main():
    gold = sb.load_gold("ru")
    import hashlib
    docs_sha = hashlib.sha256("".join(g["text"] for g in gold).encode()).hexdigest()[:12]
    out = {"dataset": "ru", "n_docs": len(gold), "rows": {}}
    for label, members, det in [
        ("LLM-only: qwen2.5:3b (local)", ["ollama"], "ollama"),
        ("LLM-only: qwen3-32b (Groq cloud)", ["cloud-qwen3-32b"], "cloud-qwen3-32b"),
        ("stack: natasha+regex+qwen2.5:3b", ["natasha", "regex", "ollama"], "ollama"),
        ("stack: natasha+regex+qwen3-32b", ["natasha", "regex", "cloud-qwen3-32b"], "cloud-qwen3-32b"),
    ]:
        r = score_combo(gold, members, docs_sha)
        secs, ndocs, model = manifest_seconds(det)
        if secs and ndocs:
            r["ms_per_doc"] = round(secs / ndocs * 1000)
        r["model"] = model
        out["rows"][label] = r
    print(json.dumps(out, ensure_ascii=False, indent=2))
    json.dump(out, open(os.path.join(HERE, "cloud-r9-results.json"), "w"),
              ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
