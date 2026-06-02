#!/usr/bin/env python3
"""R5 (local default-stack variance, SUBSET estimate): the local qwen2.5:3b is
~54 s/doc, so full-corpus N>=3 is impractical here. This runs N=3 of the LLM
layer over a fixed 5-doc subset (temperature 0.3) and reports entity-recall
mean+-std on that subset only. Clearly a SUBSET estimate, not the headline."""
import json
import os
import sys

from confide_eval import paths

HERE = os.fspath(paths.RESULTS)
sys.path.insert(0, os.fspath(paths.ANONYMIZER_SCRIPTS))

from confide_eval.scoring import score_bench as sb  # noqa: E402
from anonymize import run_ollama  # noqa: E402
SUBSET = ["ru-a-s01", "ru-b-s03", "ru-c-s02", "ru-d-s04", "ru-e-s05"]
N = 3


def main():
    os.environ["LLM_TEMPERATURE"] = "0.3"
    os.environ.pop("LLM_API", None)  # local ollama default transport
    gold = [g for g in sb.load_gold("ru") if g["doc_id"] in SUBSET]
    text_by = {g["doc_id"]: g["text"] for g in gold}
    ents = []
    for run in range(N):
        preds = {}
        for did in SUBSET:
            spans = run_ollama(text_by[did], "qwen2.5:3b")
            preds[did] = [{"start": s.start, "end": s.end,
                           "type": s.label.upper(), "canon": sb.canon(s.label)}
                          for s in spans]
            preds[did] = sb.merge_intervals(preds[did])
        prot, total, _, _, _ = sb.score_entity_level(gold, preds, relaxed=True)
        er = round(prot / total, 3) if total else 0.0
        ents.append(er)
        print(f"  run {run+1}: subset entity_recall={er} ({prot}/{total})")
    import statistics as st
    out = {"scope": "SUBSET ESTIMATE (5 docs, LLM layer only)", "subset": SUBSET,
           "model": "qwen2.5:3b", "provider": "local Ollama", "temperature": 0.3,
           "N": N, "date": "2026-06-02",
           "entity_recall_runs": ents,
           "mean": round(st.mean(ents), 3),
           "std": round(st.pstdev(ents), 3),
           "sample_std": round(st.stdev(ents), 3) if len(ents) > 1 else 0.0}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    json.dump(out, open(os.path.join(HERE, "local-r5-variance-subset.json"), "w"),
              ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
