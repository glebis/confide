# Reproducibility, Re-run Policy & Cost — CONFIDE-Bench

How to keep the benchmark **comparable over time** as tools, models, and data change.
Follows the living-benchmark norms of HELM and EleutherAI lm-evaluation-harness, and
the LLM-nondeterminism literature (temperature 0 ≠ deterministic).

## 1. Versioning

- **Benchmark version = gold version × scorer version.** Results are comparable ONLY
  within a version. Bump the version when the gold (`pii-eval-*.jsonl`) or `score_bench.py`
  changes. (Current: gold **v2** = post-IAA adjudication.)
- Every detector cache carries a manifest (`code_sha`, `docs_sha`, `doc_ids`, model,
  seconds); `score_bench` warns when a cache is stale vs the current code/data.
- Every run is appended to `runs/runs.jsonl` (`run_registry.py`): UTC timestamp, git
  commit, code/runner sha, model + library versions, host, headline metrics. This is
  the audit trail and the comparison substrate.

## 2. When to re-run

| Trigger | Action |
|---|---|
| A detector's `code_sha` or model version changes | Re-run THAT detector's cache, then rescore. Manifest flags the staleness automatically. |
| Gold changes (e.g. v2→v3 adjudication) | Re-run scoring; bump benchmark version. `docs_sha` flags transcript-text changes. |
| **New / swapped LLM** (qwen→other, version bump, cloud model) | Run as a **NEW `runs.jsonl` row** — compare, never overwrite. |
| Dependency bump (`transformers`, `torch`, `ollama`, `natasha`) | Periodic **drift check** (≈quarterly): re-run, diff against the last registry row. |
| Publishing a number | Re-run the LLM-dependent layers **N≥3** and report **mean ± std** (see §3). |

## 3. LLM nondeterminism (important)

**Temperature 0 does NOT guarantee identical outputs** for local/quantized models — batch
size, reduction-kernel order, quantization, and GPU/CPU architecture all perturb the
forward pass. We observed this directly: the qwen CBT-utility metric drifted **0.92 → 0.82**
across reruns of the *same* config.

Policy: for any **qwen/ollama-dependent metric** (per-category recall, utility,
reconstruction attack), run **N≥3** and report **mean ± std**, not a single value. Pin the
exact ollama model digest (`ollama show qwen2.5:3b --modelfile` / image digest) in the run
record. Caution (from the literature): hardware nondeterminism can *inflate* apparent
variance — keep the machine fixed when measuring it.

Deterministic layers (regex, Natasha) are reproducible and need a single run.

## 4. Inference cost

- Logged per detector: wall-clock `seconds`, ms/doc. Extend with **device** (CPU/MPS/GPU),
  **peak RAM**, **token count** (LLM), and **$/1k tokens** (cloud).
- Headline cost metrics: **recall-per-second** and **recall-per-dollar** (bang-for-buck).
  Report OPF latency only from a cache regenerated for the current corpus and host.
- Cost is **hardware-dependent**: absolute numbers are comparable only on the same machine.
  Report cost **relative to the regex layer** for machine-independent comparison.

## 5. Dedicated machine?

- **Quality metrics (recall / F2 / entity-recall):** ~machine-independent — **any machine is
  fine** (only LLM nondeterminism varies; mitigate with §3).
- **Cost / latency metrics:** use a **fixed reference machine** for comparable absolute
  numbers, and for the slow OPF / GPU runs. Record the host in the registry either way.

## 6. Containerization (reproducible "everyone runs the same versions")

Pin the **entire** stack so a third party reproduces a run:
- Python + libs via a locked `requirements.lock` (exact versions of natasha, scrubadub,
  phonenumbers, transformers, torch, torchvision).
- The **ollama model digest** (not just the tag `qwen2.5:3b`).
- The OPF model revision (`openai/privacy-filter` commit) for the transformers route.

A `Dockerfile`/`Containerfile` is the portable default; lightweight declarative
alternatives (Nix / devbox / Pixi / mise / Apptainer / devcontainer) achieve the same and
are friendlier to "install the latest of everything." The container goes in the run record
(image digest) so results are tied to an exact environment.

## 7. Privacy note for real-session runs

Real-session runs are logged with `privacy: "real-local-statsonly"` and **aggregates only**
(no transcript text, no PII). The registry is then an *audit trail* proving a real-data run
happened locally without leaking — never a content store.

## 8. Stale / drift check (`make check`)

`check_artifacts.py` is a deterministic guard (no LLM calls) that fails the build when any
committed artifact has drifted from what the current gold + detector caches produce, so a
stale number can never silently ship (Codex audit R1). Run it after any regeneration and in
CI:

```
make check          # or: python check_artifacts.py
```

It enforces three invariants:
1. **JSON freshness** — each committed `*-bench-results.json` equals a fresh in-memory
   rescore from the current caches (headline coverage/type metrics + entity & harm-weighted
   recall).
2. **Manifest validity** — every detector cache cited by a *numeric* BENCHMARK.md row
   validates against its gold (doc-id set + transcript `docs_sha`). A combo whose cache is
   intentionally omitted (e.g. the stale RU `opf` row) is allowed only because BENCHMARK.md
   presents no numeric row for it.
3. **Markdown ↔ JSON consistency** — the numbers quoted in BENCHMARK.md and IAA-RESULTS.md
   (RU ★ coverage/entity/harm-weighted recall, EN/EN-real Presidio + Philter coverage-F2 +
   micro-F1, IAA F1 + κ) equal the regenerated JSON, and IAA-RESULTS.md is labelled an
   **LLM-assisted consistency check**, not human inter-annotator agreement (audit R4).

Full regeneration order (the checker prints this on failure):
`score_bench.py` (per dataset) → `bootstrap_ci.py` (per dataset) → `iaa_eval.py` →
`make_benchmark.py` → `make_tufte_report.py` → `check_artifacts.py`.

### Continuous verification (CI)

`make check` is **enforced in CI**: the GitHub Actions workflow
`.github/workflows/check-artifacts.yml` runs it on every `push` and `pull_request`,
and the build **fails on artifact drift**. The job is deterministic, LLM-free, and
network-free — it runs only stdlib Python (3.11) against the committed gold and
detector caches (the JSONL is in the repo); it does **not** install or require
Ollama / OPF / Presidio / torch / transformers, and needs no network. The pre-existing
`⚠` warnings about the stale RU `opf` cache and legacy `opf` manifests are non-fatal
and do not fail CI.

**Contributors: run `make check` (from `eval/`) before committing.** If it exits
non-zero, regenerate the artifacts in the order above and re-run until it passes —
otherwise CI will reject the change.
