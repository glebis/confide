#!/usr/bin/env python3
"""R5 run-variance: score N qwen3-32b runs (temperature 0.3) and report mean±std
of entity recall + harm-weighted recall, for the LLM layer alone and the full RU
stack (natasha+regex+LLM). Reuses score_bench's exact metric functions."""
import json
import os
import statistics as st

import score_bench as sb

HERE = os.path.dirname(os.path.abspath(__file__))
N = 5
VAR = [f"cloud-qwen3-32b-var{i}" for i in range(1, N + 1)]


def ent_harm(gold, members, docs_sha):
    preds = sb.union_preds("ru", members, [g["doc_id"] for g in gold], docs_sha)
    prot, total, _, _, harm = sb.score_entity_level(gold, preds, relaxed=True)
    return round(prot / total, 3) if total else 0.0, harm


def summarize(vals):
    return {"mean": round(st.mean(vals), 3),
            "std": round(st.pstdev(vals), 3),
            "sample_std": round(st.stdev(vals), 3) if len(vals) > 1 else 0.0,
            "min": min(vals), "max": max(vals), "runs": vals}


def main():
    gold = sb.load_gold("ru")
    import hashlib
    docs_sha = hashlib.sha256("".join(g["text"] for g in gold).encode()).hexdigest()[:12]
    rows = {}
    for label, base_members in [
        ("LLM-only (qwen3-32b)", []),
        ("stack: natasha+regex+qwen3-32b", ["natasha", "regex"]),
    ]:
        ents, harms = [], []
        for v in VAR:
            e, h = ent_harm(gold, base_members + [v], docs_sha)
            ents.append(e); harms.append(h)
        rows[label] = {"entity_recall": summarize(ents),
                       "harm_weighted_recall": summarize(harms)}
    out = {"dataset": "ru", "n_docs": len(gold), "N": N,
           "model": "qwen/qwen3-32b", "provider": "Groq",
           "provider_base": "https://api.groq.com/openai",
           "temperature": 0.3, "date": "2026-06-02", "rows": rows}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    json.dump(out, open(os.path.join(HERE, "cloud-r5-variance.json"), "w"),
              ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
