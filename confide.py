#!/usr/bin/env python3
"""confide — CLI for the CONFIDE de-identification toolkit.

Confidential Filtering of Identifying Details (Locked). One agent-facing entrypoint
over the pieces: the local anonymizer (CONFIDE), the benchmark (CONFIDE-Bench), and
the re-identification attacks (CONFIDE-Red).

PRIVACY CONTRACT (the reason the CLI exists in this shape):
  - `redact` / `stats` read RED (raw) text locally and write only GREEN (redacted)
    output + AGGREGATE manifests. stdout/JSON NEVER carry transcript text or PII
    values — safe to hand to a cloud agent.
  - Designed for agents: folder in, JSON out, green-only publication. The agent
    passes a RED folder and only ever reads the GREEN one.

Subcommands:
  confide redact <red> --out <green>    batch anonymize → GREEN .md + manifest.json
  confide stats  <folder>               local stats-only (counts/rates), no PII out
  confide verify <green>                residual re-id risk gate (pass/fail) [stub→bench]
  confide bench  [...]                  run CONFIDE-Bench (delegates to run-benchmark.sh)
  confide red    <folder> [...]         run CONFIDE-Red attacks (delegates to confide_eval.redteam)

Zero third-party deps (argparse + the session-anonymizer). The LLM layer is engine-
agnostic (LLM_API/LLM_BASE_URL → ollama or llama.cpp).
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ANON = os.path.join(HERE, "skills", "session-anonymizer", "scripts")
sys.path.insert(0, ANON)

ALLOWED_TYPES = {"PERSON", "LOCATION", "ADDRESS", "ORG", "PHONE", "EMAIL", "URL",
                 "ID", "DATE", "MEDICATION", "AGE", "PROFESSION", "UNKNOWN"}


def _safe_type(label):
    t = str(label).upper()
    return t if t in ALLOWED_TYPES else "OTHER"


def _merge(spans):
    ss = sorted(spans, key=lambda s: (s.start, -(s.end - s.start)))
    out = []
    for s in ss:
        if out and s.start < out[-1][1]:
            out[-1][1] = max(out[-1][1], s.end)
        else:
            out.append([s.start, s.end])
    return out


def _iter_md(path):
    if os.path.isfile(path):
        yield path
    else:
        for root, _d, files in os.walk(path):
            for fn in sorted(files):
                if fn.endswith(".md"):
                    yield os.path.join(root, fn)


def _detect(text, anonymize, layers, model):
    spans = []
    if "natasha" in layers:
        spans += anonymize.run_natasha(text)
    if "regex" in layers:
        spans += anonymize.run_regex(text)
    if "ollama" in layers or "llm" in layers:
        import contextlib
        import io
        with contextlib.redirect_stderr(io.StringIO()):
            spans += anonymize.run_ollama(text, model)
    return spans


def cmd_redact(args):
    """Batch anonymize RED → GREEN; emit a PII-free manifest."""
    import anonymize
    layers = args.layers.split(",")
    os.makedirs(args.out, exist_ok=True)
    manifest = {"red": os.path.abspath(args.input), "green": os.path.abspath(args.out),
                "layers": layers, "files": []}
    for i, p in enumerate(_iter_md(args.input)):
        try:
            text = open(p, encoding="utf-8").read()
            spans = _detect(text, anonymize, layers, args.model)
            iv = _merge(spans)
            # write GREEN (redacted) — the ONLY place PII-derived text goes, and it's
            # already redacted; placeholder = <TYPE> from the longest contributor.
            red_out, last = [], 0
            by_type = {}
            for s, e in iv:
                tp = _safe_type(max((sp for sp in spans if sp.start < e and s < sp.end),
                                    key=lambda sp: sp.end - sp.start, default=None).label
                                if any(sp.start < e and s < sp.end for sp in spans) else "OTHER")
                by_type[tp] = by_type.get(tp, 0) + 1
                red_out.append(text[last:s]); red_out.append(f"<{tp}>"); last = e
            red_out.append(text[last:])
            green_name = f"{os.path.splitext(os.path.basename(p))[0]}.green.md"
            open(os.path.join(args.out, green_name), "w", encoding="utf-8").write("".join(red_out))
            masked = sum(e - s for s, e in iv)
            manifest["files"].append({"doc": f"doc-{i:03d}", "green": green_name,
                                      "chars": len(text), "spans": len(spans),
                                      "by_type": by_type,
                                      "redaction_rate": round(masked / len(text), 4) if text else 0.0})
        except Exception as e:
            manifest["files"].append({"doc": f"doc-{i:03d}", "error": type(e).__name__})
    json.dump(manifest, open(os.path.join(args.out, "manifest.json"), "w"), ensure_ascii=False, indent=2)
    # stdout: aggregate only
    n = len(manifest["files"]); errs = sum(1 for f in manifest["files"] if "error" in f)
    print(json.dumps({"redacted": n - errs, "errors": errs,
                      "green": manifest["green"], "manifest": "manifest.json"}))


def cmd_stats(args):
    """Local stats-only: counts/rates per file, no GREEN written, no PII out."""
    import anonymize
    layers = args.layers.split(",")
    agg = {"files": 0, "total_chars": 0, "by_layer": {}, "by_type": {}, "masked": 0}
    for p in _iter_md(args.input):
        try:
            text = open(p, encoding="utf-8").read()
        except Exception:
            continue
        spans = _detect(text, anonymize, layers, args.model)
        for sp in spans:
            agg["by_type"][_safe_type(sp.label)] = agg["by_type"].get(_safe_type(sp.label), 0) + 1
        masked = sum(e - s for s, e in _merge(spans))
        agg["files"] += 1; agg["total_chars"] += len(text); agg["masked"] += masked
    agg["redaction_rate"] = round(agg["masked"] / agg["total_chars"], 4) if agg["total_chars"] else 0.0
    print(json.dumps(agg, ensure_ascii=False))


# Curated registry of PUBLIC, easily-downloadable de-id / PII datasets to extend the
# benchmark. `source`: hf (HuggingFace datasets), git (clone), url (file). See
# docs/DATASETS.md for the full annotated list + licenses/caveats.
DATASETS = {
    "ai4privacy-300k":   {"source": "hf", "id": "ai4privacy/pii-masking-300k",
                          "license": "CC-BY-4.0 (OpenPII core)", "langs": "en,fr,de,it,nl,es",
                          "note": "broad synthetic PII; already used for EN-real slice"},
    "ai4privacy-200k":   {"source": "hf", "id": "ai4privacy/pii-masking-200k",
                          "license": "varies", "langs": "en,fr,de,it", "note": "smaller synthetic PII"},
    "nemotron-pii":      {"source": "hf", "id": "nvidia/Nemotron-PII", "license": "CC-BY-4.0",
                          "langs": "en", "note": "synthetic, 50+ entity types — taxonomy reference"},
    "reddit-self-disclosure": {"source": "hf", "id": "douy/reddit-self-disclosure",
                          "license": "research-only", "langs": "en",
                          "note": "19 disclosed-experience categories — closest to therapy narrative"},
    "spy":               {"source": "hf", "id": "mks-logic/SPY", "license": "see card",
                          "langs": "en", "note": "synthetic medical+legal Q&A (semi-dialogue)"},
    "tab":               {"source": "git", "url": "https://github.com/NorskRegnesentral/text-anonymisation-benchmark",
                          "license": "MIT", "langs": "en", "note": "ECHR legal; direct/quasi/coref gold"},
    "jobstack":          {"source": "git", "url": "https://github.com/kris927b/JobStack",
                          "license": "open", "langs": "en", "note": "job postings; profession/org entities"},
    "open-legal-data-de":{"source": "hf", "id": "open-legal-data/german-court-decisions",
                          "license": "ODbL", "langs": "de", "note": "court-anonymized; quasi-id patterns"},
}


def cmd_datasets(args):
    if args.action == "list":
        print(json.dumps(DATASETS, ensure_ascii=False, indent=2))
        return
    # fetch
    d = DATASETS.get(args.name)
    if not d:
        print(json.dumps({"error": "unknown dataset", "available": list(DATASETS)})); sys.exit(1)
    out = args.out or os.path.join(HERE, "data", "external", args.name)
    os.makedirs(out, exist_ok=True)
    import subprocess
    if d["source"] == "hf":
        try:
            from datasets import load_dataset
        except ImportError:
            print(json.dumps({"error": "pip install datasets", "id": d["id"]})); sys.exit(1)
        ds = load_dataset(d["id"])
        ds.save_to_disk(out)
        print(json.dumps({"fetched": args.name, "id": d["id"], "out": out, "splits": list(ds)}))
    elif d["source"] == "git":
        subprocess.check_call(["git", "clone", "--depth", "1", d["url"], out])
        print(json.dumps({"fetched": args.name, "url": d["url"], "out": out}))
    elif d["source"] == "url":
        import urllib.request
        dest = os.path.join(out, os.path.basename(d["url"]))
        urllib.request.urlretrieve(d["url"], dest)
        print(json.dumps({"fetched": args.name, "out": dest}))


def _delegate_script(script, rest):
    """Run a top-level helper script (e.g. run-benchmark.sh) from the repo root."""
    import subprocess
    path = os.path.join(HERE, script)
    cmd = ["bash", path] if script.endswith(".sh") else [sys.executable, path]
    sys.exit(subprocess.call([*cmd, *rest], cwd=HERE))


def _delegate_module(module, rest):
    """Run a confide_eval package module (`python -m`) with src/ on PYTHONPATH."""
    import subprocess
    env = dict(os.environ)
    src = os.path.join(HERE, "src")
    env["PYTHONPATH"] = src + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    sys.exit(subprocess.call([sys.executable, "-m", module, *rest], cwd=HERE, env=env))


def cmd_bench(args):
    _delegate_script("run-benchmark.sh", args.rest)


def cmd_red(args):
    _delegate_module("confide_eval.redteam.confide_red", args.rest)


def main():
    ap = argparse.ArgumentParser(prog="confide", description="CONFIDE de-identification toolkit")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("redact", help="batch anonymize RED -> GREEN + manifest")
    r.add_argument("input"); r.add_argument("--out", required=True)
    r.add_argument("--layers", default="natasha,regex,ollama"); r.add_argument("--model", default="qwen2.5:3b")
    r.set_defaults(func=cmd_redact)

    s = sub.add_parser("stats", help="local stats-only (no PII emitted)")
    s.add_argument("input"); s.add_argument("--layers", default="natasha,regex,ollama")
    s.add_argument("--model", default="qwen2.5:3b"); s.set_defaults(func=cmd_stats)

    b = sub.add_parser("bench", help="run CONFIDE-Bench (run-benchmark.sh)")
    b.add_argument("rest", nargs=argparse.REMAINDER); b.set_defaults(func=cmd_bench)

    rd = sub.add_parser("red", help="run CONFIDE-Red attacks (confide_eval.redteam)")
    rd.add_argument("rest", nargs=argparse.REMAINDER); rd.set_defaults(func=cmd_red)

    ds = sub.add_parser("datasets", help="list / fetch public de-id datasets")
    ds.add_argument("action", choices=["list", "fetch"])
    ds.add_argument("name", nargs="?"); ds.add_argument("--out")
    ds.set_defaults(func=cmd_datasets)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
