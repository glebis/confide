#!/usr/bin/env python3
"""Run the LLM detector layer with a CLOUD OpenAI-compatible model and cache its
spans in the exact JSONL+manifest shape run_detectors.py uses, under a SEPARATE
detector name (so the committed ru.ollama.jsonl / qwen2.5:3b default is untouched).

Used for the R9 head-to-head (3b vs big model) and the R5 run-variance study.
SYNTHETIC corpus only — never point this at real/consented transcripts.

Transport: anonymize.run_ollama honours LLM_API=openai + LLM_BASE_URL + LLM_MODEL
and an Authorization: Bearer $OPENAI_API_KEY header. Set those in the env, e.g.:
  OPENAI_API_KEY=$GROQ_API_KEY LLM_API=openai \
  LLM_BASE_URL=https://api.groq.com/openai LLM_MODEL=qwen/qwen3-32b \
  python run_cloud_detector.py --dataset ru --detector cloud-qwen3-32b

NB: LLM_BASE_URL must NOT include a trailing /v1 — run_ollama appends
/v1/chat/completions itself.
"""
import argparse
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "skills", "session-anonymizer", "scripts"))
CACHE = os.path.join(HERE, "detector-cache")
DATASETS = {
    "ru":     os.path.join(HERE, "..", "sessions-ru", "pii-eval-ru.jsonl"),
    "ru-adv": os.path.join(HERE, "..", "sessions-ru", "pii-adversarial-ru.jsonl"),
    "en":     os.path.join(HERE, "..", "sessions-en", "pii-eval.jsonl"),
}


def to_dicts(spans):
    return [{"start": s.start, "end": s.end, "type": s.label.upper(), "source": s.source}
            for s in spans]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, choices=list(DATASETS))
    ap.add_argument("--detector", required=True,
                    help="cache name, e.g. cloud-qwen3-32b (NOT 'ollama')")
    ap.add_argument("--model", default=os.environ.get("LLM_MODEL", "qwen/qwen3-32b"))
    ap.add_argument("--sleep", type=float, default=0.0,
                    help="seconds to sleep between docs (free-tier rate limits)")
    args = ap.parse_args()
    os.makedirs(CACHE, exist_ok=True)
    if args.detector == "ollama":
        raise SystemExit("refusing to overwrite the committed 'ollama' cache")

    import anonymize
    docs = [json.loads(l) for l in open(DATASETS[args.dataset], encoding="utf-8")]
    for i, d in enumerate(docs):
        d.setdefault("doc_id", f"{args.dataset}-{i:03d}")

    anon_path = os.path.join(HERE, "..", "skills", "session-anonymizer", "scripts", "anonymize.py")
    code_sha = hashlib.sha256(open(anon_path, "rb").read()
                              + open(os.path.join(HERE, "run_cloud_detector.py"), "rb").read()
                              ).hexdigest()[:12]
    docs_sha = hashlib.sha256("".join(d["text"] for d in docs).encode("utf-8")).hexdigest()[:12]
    gold_ids = [d["doc_id"] for d in docs]

    out = os.path.join(CACHE, f"{args.dataset}.{args.detector}.jsonl")
    tmp = f"{out}.{os.getpid()}.tmp"
    t0 = time.time()
    n_spans = n_bad = n_empty = 0
    with open(tmp, "w", encoding="utf-8") as f:
        for d in docs:
            spans = to_dicts(anonymize.run_ollama(d["text"], args.model))
            if not spans:
                n_empty += 1
            for s in spans:
                if not (0 <= s["start"] < s["end"] <= len(d["text"])):
                    n_bad += 1
            n_spans += len(spans)
            f.write(json.dumps({"doc_id": d["doc_id"], "spans": spans},
                               ensure_ascii=False) + "\n")
            if args.sleep:
                time.sleep(args.sleep)
        f.flush(); os.fsync(f.fileno())
    with open(tmp, encoding="utf-8") as vf:
        for ln, line in enumerate(vf, 1):
            json.loads(line)
    os.replace(tmp, out)
    dt = time.time() - t0

    manifest = {"dataset": args.dataset, "detector": args.detector,
                "n_docs": len(docs), "n_spans": n_spans, "invalid_spans": n_bad,
                "empty_docs": n_empty, "doc_ids": gold_ids,
                "docs_sha": docs_sha, "code_sha": code_sha,
                "model": args.model, "provider_base": os.environ.get("LLM_BASE_URL"),
                "seconds": round(dt, 1)}
    man_out = os.path.join(CACHE, f"{args.dataset}.{args.detector}.manifest.json")
    man_tmp = f"{man_out}.{os.getpid()}.tmp"
    with open(man_tmp, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, ensure_ascii=False, indent=2)
        mf.flush(); os.fsync(mf.fileno())
    os.replace(man_tmp, man_out)
    print(f"[{args.dataset}/{args.detector}] {len(docs)} docs, {n_spans} spans, "
          f"{n_empty} empty, {dt:.1f}s ({dt/len(docs)*1000:.0f} ms/doc) -> {os.path.relpath(out)}")


if __name__ == "__main__":
    main()
