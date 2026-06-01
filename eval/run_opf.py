#!/usr/bin/env python3
"""
Run the OpenAI Privacy Filter (openai/privacy-filter) over an eval JSONL and
write predicted spans to predictions.jsonl.

Route B from the task brief: load directly via the transformers pipeline,
no repository install / no `opf` CLI required.

    from transformers import pipeline
    nlp = pipeline("token-classification", "openai/privacy-filter",
                   aggregation_strategy="simple")

Model card: token-classification, ~1.5B params, Apache-2.0, English-first.
The 8 labels it emits:
    private_person, private_address, private_email, private_phone,
    private_url, private_date, account_number, secret

CPU notes (measured on this machine -- see eval/RESULTS.md):
  - First run downloads ~3 GB of weights to ~/.cache/huggingface.
  - Peak RSS for a 1.5B fp32 model on CPU is ~6-7 GB. If you are tight on RAM,
    keep other apps closed. torch_dtype is left at default (fp32) for CPU
    correctness; bf16/fp16 on CPU is slower and not worth it here.

Usage:
    python run_opf.py [--input ../sessions-en/pii-eval.jsonl]
                      [--output predictions.jsonl]
                      [--model openai/privacy-filter]
"""
import argparse
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def normalize_label(raw):
    """The pipeline returns entity_group like 'private_person'. Strip any
    BIES tag prefixes defensively and lowercase."""
    lab = raw
    if len(lab) > 2 and lab[1] == "-" and lab[0] in "BIES":
        lab = lab[2:]
    return lab.lower()


def clean_and_merge(text, raw_spans):
    """Post-process raw pipeline spans into clean entity spans.

    Two well-known artifacts of subword token-classification pipelines that we
    correct here (this is standard de-id post-processing, not score-gaming):
      1. Leading/trailing whitespace included in a span's char offsets ->
         trim the offsets to the non-space content.
      2. A single entity split into adjacent subword groups of the SAME type
         (e.g. 'Margaret Hall' + 'oran') -> merge spans that are adjacent or
         separated only by whitespace and share a type.
    Score is kept as the min score across merged pieces (conservative).
    """
    # punctuation we strip from the EDGES of a span (it is never PII itself).
    # Note: '.' / '@' / ':' / '/' are NOT stripped because they occur inside
    # emails, urls and times; we only strip them when trailing the whole span.
    LEAD_STRIP = " \t\n\r\"'([{"
    TRAIL_STRIP = " \t\n\r\"')]}.,;:!?"
    spans = []
    for s in raw_spans:
        st, en = s["start"], s["end"]
        while st < en and text[st] in LEAD_STRIP:
            st += 1
        while en > st and text[en - 1] in TRAIL_STRIP:
            en -= 1
        if en <= st:
            continue
        spans.append({"start": st, "end": en, "type": s["type"], "score": s["score"]})
    spans.sort(key=lambda x: x["start"])

    merged = []
    for s in spans:
        if merged and s["type"] == merged[-1]["type"]:
            gap = text[merged[-1]["end"]:s["start"]]
            if gap == "" or gap.isspace():  # adjacent or whitespace-separated
                merged[-1]["end"] = s["end"]
                merged[-1]["score"] = min(merged[-1]["score"], s["score"])
                continue
        merged.append(dict(s))

    for m in merged:
        m["value"] = text[m["start"]:m["end"]]
    return merged


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=os.path.join(HERE, "..", "sessions-en", "pii-eval.jsonl"))
    ap.add_argument("--output", default=os.path.join(HERE, "predictions.jsonl"))
    ap.add_argument("--model", default="openai/privacy-filter")
    args = ap.parse_args()

    from transformers import pipeline
    import torch

    device = -1  # CPU. Set to 0 for CUDA if available.
    if torch.cuda.is_available():
        device = 0

    t_load = time.time()
    nlp = pipeline(
        "token-classification",
        model=args.model,
        aggregation_strategy="first",  # 'first' merges subwords by the first token's
                                       # label; better than 'simple' for this model.
                                       # Residual splits/whitespace fixed in clean_and_merge.
        device=device,
    )
    load_s = time.time() - t_load
    print(f"[run] model loaded in {load_s:.1f}s on device={device}")

    rows = [json.loads(l) for l in open(args.input)]
    out = []
    t0 = time.time()
    for r in rows:
        text = r["text"]
        preds = nlp(text)
        raw = []
        for p in preds:
            raw.append({
                "start": int(p["start"]),
                "end": int(p["end"]),
                "type": normalize_label(p.get("entity_group", p.get("entity", ""))),
                "score": float(p.get("score", 0.0)),
            })
        spans = clean_and_merge(text, raw)
        out.append({"text": text, "spans": spans, "source": r.get("source")})
    infer_s = time.time() - t0

    with open(args.output, "w") as f:
        for row in out:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    n_pred = sum(len(o["spans"]) for o in out)
    print(f"[run] {len(rows)} snippets, {n_pred} predicted spans")
    print(f"[run] inference {infer_s:.1f}s total "
          f"({infer_s/max(len(rows),1)*1000:.0f} ms/snippet) on CPU")
    print(f"[run] wrote {args.output}")

    # stamp timing into a sidecar so RESULTS.md can cite real numbers
    with open(os.path.join(HERE, "run_meta.json"), "w") as f:
        json.dump({
            "model": args.model,
            "device": "cpu" if device == -1 else f"cuda:{device}",
            "n_snippets": len(rows),
            "n_pred_spans": n_pred,
            "load_seconds": round(load_s, 1),
            "inference_seconds": round(infer_s, 1),
            "ms_per_snippet": round(infer_s / max(len(rows), 1) * 1000, 0),
            "input": os.path.relpath(args.input, HERE),
        }, f, indent=2)


if __name__ == "__main__":
    main()
