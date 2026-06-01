#!/usr/bin/env python3
"""Run each PII detector ONCE per dataset and cache its spans.

The session-anonymizer layers are independent and combined by span-union, so we
never need to run a "combination" — we run each base detector once, cache its
per-document spans, and let score_bench.py compose any ablation combo by union.
That makes the full ablation cheap even with OPF/qwen in the mix.

Detectors:
  natasha  — Russian NER (names/locations/orgs)           [via anonymize.py]
  regex    — emails/URLs/phones/IDs (scrubadub+phonenumbers+regex) [anonymize.py]
  ollama   — local qwen LLM (medications/dates/ages/...)   [via anonymize.py]
  opf      — OpenAI Privacy Filter via the transformers token-classification
             pipeline (Route B — the fast, correct path, NOT the opf CLI).

Output: detector-cache/<dataset>.<detector>.jsonl, one row per input doc:
  {"doc_id": "...", "spans": [{"start","end","type","source"}]}
`type` is the detector's raw label, UPPERCASED; score_bench.py maps to canon.

Usage:
  python run_detectors.py --dataset ru   --detectors natasha,regex,ollama,opf
  python run_detectors.py --dataset en   --detectors opf,regex,ollama
  python run_detectors.py --dataset en-real --detectors opf,regex,ollama
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
    "ru":      os.path.join(HERE, "..", "sessions-ru", "pii-eval-ru.jsonl"),
    "ru-adv":  os.path.join(HERE, "..", "sessions-ru", "pii-adversarial-ru.jsonl"),
    "en":      os.path.join(HERE, "..", "sessions-en", "pii-eval.jsonl"),
    "en-real": os.path.join(HERE, "..", "sessions-en", "pii-eval-ai4privacy.jsonl"),
}

# --- OPF via transformers pipeline (Route B), lazily loaded once ---------------
_OPF_PIPE = None


def _opf_pipe():
    global _OPF_PIPE
    if _OPF_PIPE is None:
        import torch
        from transformers import pipeline
        # Apple-Silicon MPS is ~10-20x faster than CPU for this 1.5B NER model.
        device = "mps" if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available() else "cpu"
        _OPF_PIPE = pipeline("token-classification", "openai/privacy-filter",
                             aggregation_strategy="simple", device=device)
        print(f"[opf] device={device}")
    return _OPF_PIPE


def _opf_raw_chunked(text, window=1200, overlap=150):
    """Run the OPF pipeline over char windows (the NER model truncates long
    inputs to its max sequence length, which would silently drop all PII past
    the first chunk on a full transcript). Offsets are mapped back to absolute
    positions; windows overlap so entities on a boundary aren't split."""
    pipe = _opf_pipe()
    if len(text) <= window:
        return pipe(text)
    out = []
    pos = 0
    while pos < len(text):
        chunk = text[pos:pos + window]
        for e in pipe(chunk):
            e = dict(e)
            e["start"] = int(e["start"]) + pos
            e["end"] = int(e["end"]) + pos
            out.append(e)
        pos += window - overlap
    return out


def run_opf_transformers(text):
    """Returns list of {start,end,type,source} from the OPF NER pipeline,
    with the two standard post-cleanups (trim edge punctuation, merge adjacent
    same-type subword fragments) documented in eval/README.md. Long docs are
    processed in overlapping char windows (see _opf_raw_chunked)."""
    raw = _opf_raw_chunked(text)
    spans = []
    for e in raw:
        lab = (e.get("entity_group") or e.get("entity") or "").lower()
        lab = lab.split("-")[-1] if "-" in lab else lab
        s, t = int(e["start"]), int(e["end"])
        # trim leading/trailing whitespace + edge punctuation (never PII)
        while s < t and text[s] in " \t\n.,;:!?\"'()[]":
            s += 1
        while t > s and text[t - 1] in " \t\n.,;:!?\"'()[]":
            t -= 1
        if t > s:
            spans.append({"start": s, "end": t, "type": lab.upper(), "source": "opf"})
    # merge adjacent same-type fragments separated only by whitespace
    spans.sort(key=lambda x: x["start"])
    merged = []
    for sp in spans:
        if merged and sp["type"] == merged[-1]["type"] and \
           text[merged[-1]["end"]:sp["start"]].strip() == "":
            merged[-1]["end"] = sp["end"]
        else:
            merged.append(sp)
    return merged


def to_dicts(spans):
    """anonymize.py Span dataclass -> {start,end,type,source}."""
    return [{"start": s.start, "end": s.end, "type": s.label.upper(), "source": s.source}
            for s in spans]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, choices=list(DATASETS))
    ap.add_argument("--detectors", default="natasha,regex,ollama,opf")
    ap.add_argument("--model", default="qwen2.5:3b")
    args = ap.parse_args()
    os.makedirs(CACHE, exist_ok=True)

    docs = [json.loads(l) for l in open(DATASETS[args.dataset], encoding="utf-8")]
    # normalize id field (en datasets may lack doc_id)
    for i, d in enumerate(docs):
        d.setdefault("doc_id", f"{args.dataset}-{i:03d}")

    import anonymize
    runners = {
        "natasha": lambda t: to_dicts(anonymize.run_natasha(t)),
        "regex":   lambda t: to_dicts(anonymize.run_regex(t)),
        "ollama":  lambda t: to_dicts(anonymize.run_ollama(t, args.model)),
        "opf":     run_opf_transformers,
    }

    # code version = hash of anonymize.py (regex/natasha/ollama) + run_detectors.py
    # (OPF route lives here) so an OPF logic change also invalidates caches.
    anon_path = os.path.join(HERE, "..", "skills", "session-anonymizer", "scripts", "anonymize.py")
    code_sha = hashlib.sha256(open(anon_path, "rb").read()
                              + open(os.path.join(HERE, "run_detectors.py"), "rb").read()
                              ).hexdigest()[:12]
    gold_doc_ids = [d["doc_id"] for d in docs]
    # hash the actual document texts so edits under the same doc_ids are detected
    docs_sha = hashlib.sha256("".join(d["text"] for d in docs).encode("utf-8")).hexdigest()[:12]

    for det in args.detectors.split(","):
        det = det.strip()
        if det not in runners:
            print(f"  ! unknown detector {det!r}, skipping"); continue
        out = os.path.join(CACHE, f"{args.dataset}.{det}.jsonl")
        t0 = time.time()
        n_spans = n_bad = 0
        with open(out, "w", encoding="utf-8") as f:
            for d in docs:
                spans = runners[det](d["text"])
                # validate: every span offset must lie within the doc and the slice
                # must be non-empty (catches offset bugs at write time)
                for s in spans:
                    if not (0 <= s["start"] < s["end"] <= len(d["text"])):
                        n_bad += 1
                n_spans += len(spans)
                f.write(json.dumps({"doc_id": d["doc_id"], "spans": spans},
                                   ensure_ascii=False) + "\n")
        dt = time.time() - t0
        # manifest: lets score_bench validate instead of trusting file existence
        manifest = {"dataset": args.dataset, "detector": det, "n_docs": len(docs),
                    "n_spans": n_spans, "invalid_spans": n_bad, "doc_ids": gold_doc_ids,
                    "docs_sha": docs_sha, "code_sha": code_sha,
                    "model": args.model if det == "ollama" else None,
                    "seconds": round(dt, 1)}
        json.dump(manifest, open(os.path.join(CACHE, f"{args.dataset}.{det}.manifest.json"), "w"),
                  ensure_ascii=False, indent=2)
        flag = f"  ⚠ {n_bad} INVALID spans" if n_bad else ""
        print(f"[{args.dataset}/{det}] {len(docs)} docs, {n_spans} spans, "
              f"{dt:.1f}s ({dt/len(docs)*1000:.0f} ms/doc) -> {os.path.relpath(out)}{flag}")


if __name__ == "__main__":
    main()
