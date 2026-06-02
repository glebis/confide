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
  presidio — Microsoft Presidio AnalyzerEngine (spaCy en_core_web_sm + Presidio's
             pattern/checksum recognizers). Established off-the-shelf EN baseline.
             ENGLISH only (run on en / en-real); spaCy-dependent RU support is weak.
  philter  — Philter (philter-lite, UCSF clinical de-id, HIPAA Safe-Harbor rule
             set). High-recall PHI scrubber; most spans come back as type OTHER
             (Philter redacts broadly rather than typing precisely). EN only.

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

from confide_eval import paths

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.fspath(paths.ANONYMIZER_SCRIPTS))

CACHE = os.fspath(paths.CACHE)
DATASETS = {k: os.fspath(v) for k, v in paths.GOLD.items()}

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


# --- Microsoft Presidio (established EN baseline), lazily loaded once -----------
_PRESIDIO = None
# Presidio entity types we keep + their RAW label fed to score_bench's CANON map.
# (CANON in score_bench.py maps these to the benchmark's canonical types.)
_PRESIDIO_KEEP = {
    "PERSON": "PERSON",
    "LOCATION": "LOCATION",
    "GPE": "LOCATION",            # spaCy geo-political entity surfaced by Presidio
    "NRP": "LOCATION",            # nationality/religion/political — quasi-identifier; closest canon
    "PHONE_NUMBER": "PHONE",
    "EMAIL_ADDRESS": "EMAIL",
    "URL": "URL",
    "DATE_TIME": "DATE",
    "US_SSN": "ID", "US_ITIN": "ID", "US_PASSPORT": "ID", "US_DRIVER_LICENSE": "ID",
    "US_BANK_NUMBER": "ID", "IBAN_CODE": "ID", "CREDIT_CARD": "ID",
    "CRYPTO": "ID", "IP_ADDRESS": "ID", "MEDICAL_LICENSE": "ID",
    "ORGANIZATION": "ORG", "ORG": "ORG",
    "AGE": "AGE",
}
# Drop low-confidence context-only guesses (spaCy URL fragments off emails, weak
# phone matches). Presidio's own default for a "real" hit is ~0.4+; we keep the
# structured-recognizer hits (SSN/email score high) and name/location NER (0.85).
_PRESIDIO_MIN_SCORE = 0.45


def _presidio_engine():
    global _PRESIDIO
    if _PRESIDIO is None:
        from presidio_analyzer import AnalyzerEngine
        from presidio_analyzer.nlp_engine import NlpEngineProvider
        prov = NlpEngineProvider(nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
        })
        _PRESIDIO = AnalyzerEngine(nlp_engine=prov.create_engine())
        print("[presidio] spaCy model=en_core_web_sm")
    return _PRESIDIO


def run_presidio(text):
    """Returns list of {start,end,type,source} from Presidio's AnalyzerEngine.
    Mapped Presidio entity types -> the benchmark's raw labels (see _PRESIDIO_KEEP).
    Drops hits below _PRESIDIO_MIN_SCORE and any type we don't map."""
    eng = _presidio_engine()
    results = eng.analyze(text=text, language="en")
    spans = []
    for r in results:
        if r.score < _PRESIDIO_MIN_SCORE:
            continue
        raw = _PRESIDIO_KEEP.get(r.entity_type)
        if raw is None:
            continue
        s, t = int(r.start), int(r.end)
        # trim edge whitespace/punctuation, same convention as the OPF path
        while s < t and text[s] in " \t\n.,;:!?\"'()[]":
            s += 1
        while t > s and text[t - 1] in " \t\n.,;:!?\"'()[]":
            t -= 1
        if t > s:
            spans.append({"start": s, "end": t, "type": raw, "source": "presidio"})
    return spans


# --- Philter (philter-lite, UCSF clinical de-id), lazily loaded once -----------
_PHILTER_PATS = None


def _philter_filters():
    global _PHILTER_PATS
    if _PHILTER_PATS is None:
        import philter_lite
        cfg = os.path.join(os.path.dirname(philter_lite.__file__),
                           "configs", "philter_delta.toml")
        _PHILTER_PATS = philter_lite.load_filters(cfg)
        print(f"[philter] loaded {len(_PHILTER_PATS)} filters from philter_delta.toml")
    return _PHILTER_PATS


# Philter phi_type -> benchmark raw label. Philter is a HIPAA Safe-Harbor scrubber
# that emits most detections as "OTHER" (it redacts broadly rather than typing
# precisely), so coverage recall is its strength and type-aware its weakness.
_PHILTER_MAP = {
    "DATE": "DATE", "Email": "EMAIL", "Name": "PERSON", "Age": "AGE",
    "Patient_Social_Security_Number": "ID",
    "Provider_Address_or_Location": "LOCATION",
    "OTHER": "OTHER",   # canon'd to itself; counts for coverage, not type-aware
}


def run_philter(text):
    """Returns list of {start,end,type,source} from Philter's detect_phi.
    Philter is a high-recall scrubber; most spans are type OTHER."""
    import philter_lite
    pats = _philter_filters()
    _inc, _exc, dt = philter_lite.detect_phi(text, pats)
    spans = []
    for e in dt.phi:
        s, t = int(e.start), int(e.stop)
        raw = _PHILTER_MAP.get(e.phi_type, "OTHER")
        while s < t and text[s] in " \t\n.,;:!?\"'()[]":
            s += 1
        while t > s and text[t - 1] in " \t\n.,;:!?\"'()[]":
            t -= 1
        if t > s:
            spans.append({"start": s, "end": t, "type": raw, "source": "philter"})
    return spans


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
        "presidio": run_presidio,
        "philter":  run_philter,
    }

    # code version = hash of anonymize.py (regex/natasha/ollama) + run_detectors.py
    # (OPF route lives here) so an OPF logic change also invalidates caches.
    anon_path = os.path.join(os.fspath(paths.ANONYMIZER_SCRIPTS), "anonymize.py")
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
        tmp_out = f"{out}.{os.getpid()}.tmp"
        t0 = time.time()
        n_spans = n_bad = 0
        with open(tmp_out, "w", encoding="utf-8") as f:
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
            f.flush()
            os.fsync(f.fileno())
        # Validate the just-written JSONL before replacing a usable cache. This
        # catches partial/corrupt writes from disk pressure or concurrent runs.
        with open(tmp_out, encoding="utf-8") as vf:
            for line_no, line in enumerate(vf, 1):
                try:
                    json.loads(line)
                except json.JSONDecodeError as e:
                    raise SystemExit(f"[{args.dataset}/{det}] corrupt cache line "
                                     f"{line_no}: {e}") from e
        os.replace(tmp_out, out)
        dt = time.time() - t0
        # manifest: lets score_bench validate instead of trusting file existence
        manifest = {"dataset": args.dataset, "detector": det, "n_docs": len(docs),
                    "n_spans": n_spans, "invalid_spans": n_bad, "doc_ids": gold_doc_ids,
                    "docs_sha": docs_sha, "code_sha": code_sha,
                    "model": args.model if det == "ollama" else None,
                    "seconds": round(dt, 1)}
        man_out = os.path.join(CACHE, f"{args.dataset}.{det}.manifest.json")
        man_tmp = f"{man_out}.{os.getpid()}.tmp"
        with open(man_tmp, "w", encoding="utf-8") as mf:
            json.dump(manifest, mf, ensure_ascii=False, indent=2)
            mf.flush()
            os.fsync(mf.fileno())
        os.replace(man_tmp, man_out)
        flag = f"  ⚠ {n_bad} INVALID spans" if n_bad else ""
        print(f"[{args.dataset}/{det}] {len(docs)} docs, {n_spans} spans, "
              f"{dt:.1f}s ({dt/len(docs)*1000:.0f} ms/doc) -> {os.path.relpath(out)}{flag}")


if __name__ == "__main__":
    main()
