#!/usr/bin/env python3
"""Run one local LLM detector variant and cache it under a custom detector name.

This is the local-model counterpart to run_cloud_detector.py. It is intended for
Gemma/Qwen prompt experiments where each model+prompt pair gets its own cache,
leaving the committed ``<dataset>.ollama.jsonl`` qwen2.5:3b baseline untouched.
"""
import argparse
import hashlib
import json
import os
import sys
import time
from urllib.parse import urlparse

from confide_eval import paths

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.fspath(paths.ANONYMIZER_SCRIPTS))

CACHE = os.fspath(paths.CACHE)
DATASETS = {k: os.fspath(v) for k, v in paths.GOLD.items()}
RESERVED_DETECTORS = {"ollama", "natasha", "regex", "opf", "presidio", "philter"}


def _is_local_base(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in {"localhost", "127.0.0.1", "::1", ""}


def _load_docs(dataset: str) -> list[dict]:
    src = DATASETS[dataset]
    if dataset == "en-real":
        if not paths.en_real_text_present():
            raise SystemExit(
                "en-real source text not present; run "
                "`python -m confide_eval.data.fetch_ai4privacy` first."
            )
        src = os.fspath(paths.en_real_gold())
    docs = [json.loads(l) for l in open(src, encoding="utf-8")]
    for i, d in enumerate(docs):
        d.setdefault("doc_id", f"{dataset}-{i:03d}")
    return docs


def _select_docs(docs: list[dict], doc_ids: str | None, limit_docs: int | None) -> list[dict]:
    selected = docs
    if doc_ids:
        wanted = [d.strip() for d in doc_ids.split(",") if d.strip()]
        by_id = {d["doc_id"]: d for d in docs}
        missing = [d for d in wanted if d not in by_id]
        if missing:
            raise SystemExit(f"unknown doc_id(s): {', '.join(missing)}")
        selected = [by_id[d] for d in wanted]
    if limit_docs is not None:
        selected = selected[:limit_docs]
    if not selected:
        raise SystemExit("no documents selected")
    return selected


def _prompt_template(path: str | None) -> str | None:
    if not path:
        return None
    with open(path, encoding="utf-8") as f:
        return f.read()


def _to_dicts(spans):
    return [{"start": s.start, "end": s.end, "type": s.label.upper(), "source": s.source}
            for s in spans]


def _read_cache_rows(path: str) -> dict[str, dict]:
    rows = {}
    if not os.path.exists(path):
        return rows
    with open(path, encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                raise SystemExit(f"corrupt cache line {ln} in {path}: {e}") from e
            doc_id = row.get("doc_id")
            if not doc_id:
                raise SystemExit(f"cache line {ln} in {path} has no doc_id")
            rows[doc_id] = row
    return rows


def _write_cache_checkpoint(path: str, docs: list[dict], rows: dict[str, dict]) -> None:
    tmp = f"{path}.{os.getpid()}.checkpoint.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for d in docs:
            row = rows.get(d["doc_id"])
            if row is None:
                continue
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True, choices=list(DATASETS))
    ap.add_argument("--detector", required=True,
                    help="custom cache name, e.g. local-gemma3-4b-p1")
    ap.add_argument("--model", required=True, help="local model id, e.g. gemma3:4b")
    ap.add_argument("--prompt-file", help="prompt template file; use {text} for insertion")
    ap.add_argument("--doc-ids", help="comma-separated doc IDs for a small sample")
    ap.add_argument("--limit-docs", type=int, help="first N docs after any doc-id filtering")
    ap.add_argument("--api", choices=["ollama", "openai"], default="ollama",
                    help="transport: Ollama /api/chat or a local OpenAI-compatible server")
    ap.add_argument("--base-url", help="local server base URL; defaults to Ollama host")
    ap.add_argument("--allow-remote", action="store_true",
                    help="allow non-localhost base URLs; off by default for privacy")
    ap.add_argument("--sleep", type=float, default=0.0,
                    help="seconds to sleep between docs")
    ap.add_argument("--chunk-chars", type=int, default=0,
                    help="split each document into boundary-aware chunks of this size; 0 disables")
    ap.add_argument("--chunk-overlap", type=int, default=200,
                    help="character overlap when --chunk-chars is enabled")
    ap.add_argument("--resume", action="store_true",
                    help="reuse completed rows from an existing cache and process only missing docs")
    args = ap.parse_args()

    if args.detector in RESERVED_DETECTORS:
        raise SystemExit(f"refusing reserved detector name {args.detector!r}")

    base = args.base_url or os.environ.get(
        "LLM_BASE_URL", os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    )
    if not args.allow_remote and not _is_local_base(base):
        raise SystemExit(
            f"refusing non-local model endpoint {base!r}; pass --allow-remote only for synthetic data"
        )
    os.environ["LLM_API"] = args.api
    if args.base_url:
        os.environ["LLM_BASE_URL"] = args.base_url

    prompt = _prompt_template(args.prompt_file)
    docs = _select_docs(_load_docs(args.dataset), args.doc_ids, args.limit_docs)
    os.makedirs(CACHE, exist_ok=True)

    import anonymize

    anon_path = os.path.join(os.fspath(paths.ANONYMIZER_SCRIPTS), "anonymize.py")
    prompt_bytes = (prompt or "").encode("utf-8")
    code_sha = hashlib.sha256(
        open(anon_path, "rb").read()
        + open(os.path.join(HERE, "run_llm_detector.py"), "rb").read()
        + prompt_bytes
    ).hexdigest()[:12]
    docs_sha = hashlib.sha256("".join(d["text"] for d in docs).encode("utf-8")).hexdigest()[:12]
    doc_ids = [d["doc_id"] for d in docs]

    out = os.path.join(CACHE, f"{args.dataset}.{args.detector}.jsonl")
    existing = _read_cache_rows(out) if args.resume else {}
    t0 = time.time()
    rows: dict[str, dict] = {
        d["doc_id"]: existing[d["doc_id"]]
        for d in docs
        if d["doc_id"] in existing
    }
    processed_any = False
    for d in docs:
        cached = rows.get(d["doc_id"])
        if cached is not None:
            continue
        if args.chunk_chars:
            raw_spans = anonymize.run_ollama_chunked(
                d["text"],
                args.model,
                prompt_template=prompt,
                chunk_chars=args.chunk_chars,
                overlap=args.chunk_overlap,
            )
        else:
            raw_spans = anonymize.run_ollama(d["text"], args.model, prompt_template=prompt)
        spans = _to_dicts(raw_spans)
        rows[d["doc_id"]] = {"doc_id": d["doc_id"], "spans": spans}
        processed_any = True
        _write_cache_checkpoint(out, docs, rows)
        if args.sleep:
            time.sleep(args.sleep)

    if rows and not os.path.exists(out):
        _write_cache_checkpoint(out, docs, rows)

    n_spans = n_bad = n_empty = n_resumed = 0
    for d in docs:
        row = rows.get(d["doc_id"])
        if row is None:
            raise SystemExit(
                f"[{args.dataset}/{args.detector}] internal error: missing row for {d['doc_id']}"
            )
        spans = row.get("spans", [])
        if d["doc_id"] in existing:
            n_resumed += 1
        if not spans:
            n_empty += 1
        for s in spans:
            if not (0 <= s["start"] < s["end"] <= len(d["text"])):
                n_bad += 1
        n_spans += len(spans)

    if processed_any or rows:
        with open(out, encoding="utf-8") as vf:
            for ln, line in enumerate(vf, 1):
                try:
                    json.loads(line)
                except json.JSONDecodeError as e:
                    raise SystemExit(
                        f"[{args.dataset}/{args.detector}] corrupt cache line {ln}: {e}"
                    ) from e

    dt = time.time() - t0
    manifest = {
        "dataset": args.dataset,
        "detector": args.detector,
        "n_docs": len(docs),
        "n_spans": n_spans,
        "invalid_spans": n_bad,
        "empty_docs": n_empty,
        "doc_ids": doc_ids,
        "docs_sha": docs_sha,
        "code_sha": code_sha,
        "model": args.model,
        "provider": args.api,
        "provider_base": base,
        "prompt_file": args.prompt_file,
        "prompt_sha": hashlib.sha256(prompt_bytes).hexdigest()[:12] if prompt is not None else None,
        "chunk_chars": args.chunk_chars,
        "chunk_overlap": args.chunk_overlap if args.chunk_chars else 0,
        "resumed_docs": n_resumed,
        "seconds": round(dt, 1),
    }
    man_out = os.path.join(CACHE, f"{args.dataset}.{args.detector}.manifest.json")
    man_tmp = f"{man_out}.{os.getpid()}.tmp"
    with open(man_tmp, "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, ensure_ascii=False, indent=2)
        mf.flush()
        os.fsync(mf.fileno())
    os.replace(man_tmp, man_out)

    flag = f"  WARNING {n_bad} invalid spans" if n_bad else ""
    resume_note = f", {n_resumed} resumed" if n_resumed else ""
    print(f"[{args.dataset}/{args.detector}] {len(docs)} docs, {n_spans} spans, "
          f"{n_empty} empty{resume_note}, {dt:.1f}s ({dt/len(docs)*1000:.0f} ms/doc) -> "
          f"{os.path.relpath(out)}{flag}")


if __name__ == "__main__":
    main()
