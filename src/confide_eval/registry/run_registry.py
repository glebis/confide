#!/usr/bin/env python3
"""Append-only run registry for benchmark provenance (lm-eval-harness style).

Each scoring/eval run appends ONE JSON line to eval/runs/runs.jsonl capturing the
provenance needed to reproduce or compare it: UTC timestamp, git commit, code hash,
dataset version (docs_sha), model versions, host, and the headline metrics. This is
the de-facto benchmark standard (EleutherAI lm-eval results.json, HELM run dirs); a
SQLite/leaderboard DB is only worth adding once runs proliferate.

PRIVACY: `metrics` and `extra` must be AGGREGATES ONLY — never transcript text or PII
values. Real-session runs pass privacy="real-local-statsonly"; the registry is then an
audit trail that we ran on real data without leaking it.
"""
import datetime
import hashlib
import json
import os
import platform
import subprocess
import sys

from confide_eval import paths

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS_DIR = os.fspath(paths.RUNS)
RUNS_JSONL = os.path.join(RUNS_DIR, "runs.jsonl")


def _sha(path, n=12):
    try:
        return hashlib.sha256(open(path, "rb").read()).hexdigest()[:n]
    except OSError:
        return None


def _git(*args):
    try:
        return subprocess.check_output(["git", *args], cwd=os.fspath(paths.ROOT),
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


def _model_versions():
    v = {"python": sys.version.split()[0]}
    try:
        import torch  # noqa
        v["torch"] = torch.__version__
    except Exception:
        pass
    try:
        import transformers  # noqa
        v["transformers"] = transformers.__version__
    except Exception:
        pass
    return v


def log_run(kind, dataset, metrics, *, model=None, privacy="synthetic", extra=None):
    """Append one run record. `metrics`/`extra` MUST be aggregates (no PII).

    kind     — e.g. "score_bench", "real_session_eval", "iaa", "privacy_utility".
    dataset  — dataset id / name.
    metrics  — dict of headline numbers (recall, F2, etc.) — aggregates only.
    model    — model id (e.g. qwen2.5:3b) if relevant.
    privacy  — "synthetic" | "real-local-statsonly" (audit flag).
    """
    os.makedirs(RUNS_DIR, exist_ok=True)
    anon = os.path.join(os.fspath(paths.ANONYMIZER_SCRIPTS), "anonymize.py")
    rec = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "kind": kind,
        "dataset": dataset,
        "privacy": privacy,
        "git_commit": _git("rev-parse", "--short", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain")),
        "code_sha": _sha(anon),
        "runner_sha": _sha(os.path.join(os.path.dirname(HERE), "detectors", "run_detectors.py")),
        "model": model,
        "versions": _model_versions(),
        "host": {"platform": platform.platform(), "machine": platform.machine()},
        "metrics": metrics,
    }
    if extra:
        rec["extra"] = extra
    # 1) append-only index (one line per run) — quick history/leaderboard
    with open(RUNS_JSONL, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    # 2) per-run JSON file (lm-evaluation-harness / HELM convention) — committed,
    #    self-contained provenance + results for that exact run.
    safe_ts = rec["ts"].replace(":", "").replace("-", "").replace("+0000", "Z")
    fname = f"{safe_ts}-{kind}-{str(dataset).replace('/', '_')}.json"
    with open(os.path.join(RUNS_DIR, fname), "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)
    rec["_file"] = fname
    return rec


def summary():
    """Print a compact history table from runs.jsonl."""
    if not os.path.exists(RUNS_JSONL):
        print("no runs logged yet"); return
    rows = [json.loads(l) for l in open(RUNS_JSONL, encoding="utf-8")]
    print(f"{'ts':20} {'kind':18} {'dataset':10} {'commit':9} {'privacy':22} headline")
    for r in rows:
        head = r.get("metrics", {})
        h = head.get("recall") or head.get("coverage_recall") or head.get("overall_redaction_rate") or ""
        print(f"{r['ts']:20} {r['kind']:18} {str(r['dataset']):10} {str(r.get('git_commit')):9} "
              f"{r['privacy']:22} {h}")


if __name__ == "__main__":
    summary()
