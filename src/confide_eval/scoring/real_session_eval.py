#!/usr/bin/env python3
"""LOCAL, STATS-ONLY evaluation of the anonymization stack over REAL own-sessions.

PRIVACY CONTRACT (the whole reason this script exists):
  - Runs entirely on the local machine (Natasha + regex + Ollama; no cloud).
  - Reads real transcript text ONLY inside this process.
  - Emits ONLY aggregate statistics — span COUNTS by type/layer, character
    redaction rate, doc length. It NEVER prints, logs, or writes any transcript
    substring, any detected PII value, or any span text. The output is safe to
    surface to a cloud agent; the raw PII never leaves the machine.

This measures detector BEHAVIOR on real therapy dialogue (there is no gold, so no
recall-vs-truth): how much each layer fires, how much gets masked, and a coarse
"residual" proxy. Input: a file listing absolute paths, one per line.

Usage:
  python real_session_eval.py --list /tmp/own-sessions.txt --out real-eval-stats.json
"""
import argparse
import contextlib
import io
import json
import os
import sys

from confide_eval import paths

HERE = os.fspath(paths.RESULTS)
sys.path.insert(0, os.fspath(paths.ANONYMIZER_SCRIPTS))

# PRIVACY: only these canonical labels may ever appear in output. Any other label
# (e.g. a stray value the local LLM puts in its `type` field) is bucketed as
# "OTHER" so a PII string can never escape via a type label (Codex leak audit).
ALLOWED_TYPES = {"PERSON", "LOCATION", "ADDRESS", "ORG", "PHONE", "EMAIL", "URL",
                 "ID", "DATE", "MEDICATION", "AGE", "PROFESSION", "UNKNOWN"}


def safe_type(label):
    t = str(label).upper()
    return t if t in ALLOWED_TYPES else "OTHER"


def merge_intervals(spans):
    if not spans:
        return []
    ss = sorted(spans, key=lambda s: (s.start, -(s.end - s.start)))
    out = [[ss[0].start, ss[0].end]]
    for s in ss[1:]:
        if s.start < out[-1][1]:
            out[-1][1] = max(out[-1][1], s.end)
        else:
            out.append([s.start, s.end])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", required=True, help="file with absolute paths, one per line")
    ap.add_argument("--out", default=os.path.join(HERE, "real-eval-stats.json"))
    ap.add_argument("--model", default="qwen2.5:3b")
    args = ap.parse_args()

    import anonymize
    paths = [l.strip() for l in open(args.list, encoding="utf-8") if l.strip()]

    per_file = []
    agg = {"n_files": 0, "total_chars": 0,
           "spans_by_layer": {"natasha": 0, "regex": 0, "ollama": 0},
           "spans_by_type": {}, "masked_chars": 0}

    for idx, p in enumerate(paths):
        # Exception-safe: never let a traceback echo the path/filename or content.
        # On any failure, record only the index + the exception CLASS name.
        try:
            with open(p, encoding="utf-8") as f:
                text = f.read()
            n = len(text)
            # suppress any stderr from the detectors (e.g. run_ollama prints str(e))
            # so a library/server message can't surface transcript-derived content.
            with contextlib.redirect_stderr(io.StringIO()):
                layers = {
                    "natasha": anonymize.run_natasha(text),
                    "regex": anonymize.run_regex(text),
                    "ollama": anonymize.run_ollama(text, args.model),
                }
        except Exception as e:
            per_file.append({"doc": f"own-{idx:02d}", "error": type(e).__name__})
            continue
        # counts only — never the values; labels passed through safe_type()
        by_type = {}
        all_spans = []
        for lname, spans in layers.items():
            agg["spans_by_layer"][lname] += len(spans)
            all_spans.extend(spans)
            for s in spans:
                t = safe_type(s.label)
                by_type[t] = by_type.get(t, 0) + 1
                agg["spans_by_type"][t] = agg["spans_by_type"].get(t, 0) + 1
        merged = merge_intervals(all_spans)
        masked = sum(e - s for s, e in merged)
        # file id = basename WITHOUT extension hashed-ish length only? keep basename
        # (a filename is not session content; but to be conservative, store index only)
        per_file.append({
            "doc": f"own-{len(per_file):02d}",
            "chars": n,
            "spans_natasha": len(layers["natasha"]),
            "spans_regex": len(layers["regex"]),
            "spans_ollama": len(layers["ollama"]),
            "spans_by_type": by_type,
            "masked_chars": masked,
            "redaction_rate": round(masked / n, 4) if n else 0.0,
        })
        agg["n_files"] += 1
        agg["total_chars"] += n
        agg["masked_chars"] += masked
        # flushed progress (counts only, no PII) so the run is observable
        print(f"[real-eval] {idx + 1}/{len(paths)} chars={n} "
              f"spans={len(layers['natasha'])+len(layers['regex'])+len(layers['ollama'])} "
              f"red={per_file[-1]['redaction_rate']:.1%}", flush=True)

    agg["overall_redaction_rate"] = round(agg["masked_chars"] / agg["total_chars"], 4) if agg["total_chars"] else 0.0
    result = {"privacy": "stats-only; no transcript text or PII values emitted",
              "aggregate": agg, "per_file": per_file}
    json.dump(result, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # audit-trail run log (aggregates only; privacy flag marks real-local processing)
    try:
        from confide_eval.registry import run_registry
        run_registry.log_run("real_session_eval", "own-sessions",
                             {"n_files": agg["n_files"],
                              "overall_redaction_rate": agg["overall_redaction_rate"],
                              "spans_by_layer": agg["spans_by_layer"]},
                             model=args.model, privacy="real-local-statsonly")
    except Exception:
        pass

    # console: COUNTS ONLY
    a = agg
    print(f"[real-eval] files={a['n_files']} total_chars={a['total_chars']}")
    print(f"[real-eval] spans by layer: {a['spans_by_layer']}")
    print(f"[real-eval] spans by type: {dict(sorted(a['spans_by_type'].items()))}")
    print(f"[real-eval] overall redaction rate: {a['overall_redaction_rate']:.2%}")
    # print only the basename (an --out path could contain personal info)
    print(f"[real-eval] wrote {os.path.basename(args.out)} (stats only; no text/PII)")


if __name__ == "__main__":
    main()
