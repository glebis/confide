# Cloud big-model results — R9 (scale-up) + R5 (run-variance)

**Provider / model:** Groq, `qwen/qwen3-32b` (served id), OpenAI-compatible
endpoint `https://api.groq.com/openai/v1`. Run date **2026-06-02**.
**Corpus:** the 30 synthetic RU sessions (`sessions-ru/pii-eval-ru.jsonl`,
~32 K chars/doc). **Synthetic data only** — no real/consented transcript ever
touched a cloud endpoint (`THREE-LOCKS.md`).

These APIs do not expose model digests, so the served `id` string + date are the
pinned provenance (recorded in the run registry, `privacy="synthetic-cloud"`).

## Why qwen3-32b, and why Groq

The local default LLM layer is `qwen2.5:3b` (Ollama). It **collapsed** on the
long RU transcripts: LLM-only entity recall **0.157**, and the layer is *unstable*
across runs (see R5 local subset below). R9 asks whether a bigger model in the
same family recovers the LLM-only types (MEDICATION / AGE / DATE / PROFESSION).

Connectivity probe (this host): both `CEREBRAS_API_KEY` and `GROQ_API_KEY` are
present and both providers are **reachable** — but only after adding a browser
`User-Agent` header (their Cloudflare front returns HTTP 403 *error 1010* to the
default `urllib` UA). Cerebras' served catalogue here was only `gpt-oss-120b` and
`zai-glm-4.7` (no big Qwen). Groq exposes **`qwen/qwen3-32b`** — the clean
scale-up from `qwen2.5:3b` — plus `llama-3.3-70b-versatile`. Picked
`qwen/qwen3-32b` to keep the comparison within the Qwen family.

Transport fixes required in `anonymize.run_ollama` (engine-agnostic layer):
add the `Authorization: Bearer $OPENAI_API_KEY` header, a browser `User-Agent`,
and env overrides `LLM_TEMPERATURE` / `LLM_MAX_TOKENS` (Qwen3 spends output
budget on a `<think>` block before the JSON; the cloud run uses 4096 tokens).
NB: `LLM_BASE_URL` must **not** include a trailing `/v1` — the layer appends
`/v1/chat/completions` itself (so `…/openai`, not `…/openai/v1`).

## R9 — head-to-head (30 RU docs)

Entity-level recall (an entity is protected only if **all** its mentions are
covered) and harm-weighted recall, type-agnostic relaxed matching. `ms/doc` is
wall-clock from the detector manifest (local Ollama vs Groq cloud).

| Configuration | entity recall | harm-wtd recall | n_pred spans | ms/doc |
|---|---|---|---|---|
| LLM-only — `qwen2.5:3b` (local) | 0.157 | 0.091 | 360 | 53 973 |
| LLM-only — `qwen3-32b` (Groq) | **0.565** | **0.481** | 1005 | **10 210** |
| Stack `natasha+regex+qwen2.5:3b` (current default) | 0.676 | 0.632 | 1484 | — |
| Stack `natasha+regex+qwen3-32b` | **0.815** | **0.788** | 1605 | — |

**LLM-only-type recall** (these types are only reachable by the LLM layer —
Natasha/regex cannot produce them). This is where the 3b collapsed:

| Type | support | 3b recall | qwen3-32b recall |
|---|---|---|---|
| MEDICATION | 48 | 0.042 | **0.729** |
| AGE | 24 | 0.250 | **0.958** |
| DATE | 23 | 0.043 | **0.913** |
| PROFESSION | 47 | 0.043 | **0.596** |
| ID | 6 | 0.500 | 0.667 |
| PHONE | 6 | 0.833 | 0.833 |
| EMAIL | 8 | 0.875 | 0.875 |

**Takeaways.** The big model recovers exactly the LLM-only types the 3b missed
on long docs: MEDICATION 0.042→0.729, AGE 0.25→0.958, DATE 0.043→0.913,
PROFESSION 0.043→0.596. LLM-only entity recall **0.157→0.565** (3.6×) and the
full stack **0.676→0.815** (+0.139 absolute, +0.156 harm-weighted). It is also
**5× faster** here (cloud: 10.2 s/doc vs 54 s/doc local) and emitted **0
JSON-errored docs** over 30 (the 3b had 2 JSON failures on 32 K-char docs).

## R5 — LLM run-variance (N = 5, temperature 0.3, qwen3-32b)

Five independent runs, identical except sampling. Std is the **sample** std
(n−1); population std is ~equal at this N. Empty docs from transient read
timeouts were re-queried so the variance reflects sampling, not network noise.

| Configuration | entity recall (mean ± std) | harm-wtd recall (mean ± std) | runs (entR) |
|---|---|---|---|
| LLM-only `qwen3-32b` | **0.526 ± 0.022** | 0.434 ± 0.022 | 0.537, 0.537, 0.519, 0.491, 0.546 |
| Stack `natasha+regex+qwen3-32b` | **0.796 ± 0.017** | 0.765 ± 0.021 | 0.815, 0.796, 0.806, 0.769, 0.796 |

Run-to-run variance is small (±0.017–0.022 entity recall) — the gains above are
not a lucky sample.

### R5 (local default stack) — SUBSET estimate

Full-corpus N≥3 with the local `qwen2.5:3b` is impractical here (~54 s/doc). On a
fixed **5-doc subset**, N=3, temperature 0.3, the local LLM layer's entity recall
was **0.132 ± 0.081** (runs: 0.047, 0.140, 0.209). Beyond being low, the 3b is
**unstable** — it collapses inconsistently on long docs, ~4× the relative
variance of qwen3-32b. *(Subset estimate, LLM layer only — not the headline.)*

## Recommendation

The cloud big-model gain is **decisive** on the LLM-only types and substantial on
the full-stack headline (entR +0.14, harm-wtd +0.16), with lower run-variance and
faster turnaround. **Recommend** documenting `qwen3-32b` (or an equivalent ≥32B
model) as the LLM layer for serious de-identification of long RU transcripts.

**The committed default stays `qwen2.5:3b`** (fully local, no data egress — the
`THREE-LOCKS` privacy guarantee), and was **not** silently swapped. Cloud
inference is opt-in and **synthetic-corpus only**; real/consented sessions must
stay on the local stack. The win is recorded as evidence for the bigger-model
upgrade path, not as a change to the privacy-preserving default.

## Reproduce

```sh
# R9 cache (separate name — never overwrites ru.ollama.jsonl):
OPENAI_API_KEY=$GROQ_API_KEY LLM_API=openai \
  LLM_BASE_URL=https://api.groq.com/openai LLM_MODEL=qwen/qwen3-32b \
  LLM_MAX_TOKENS=4096 LLM_TEMPERATURE=0 \
  python eval/run_cloud_detector.py --dataset ru --detector cloud-qwen3-32b --sleep 0.5
python eval/score_cloud_r9.py        # -> eval/cloud-r9-results.json

# R5 variance (N=5, temp 0.3):
for i in 1 2 3 4 5; do OPENAI_API_KEY=$GROQ_API_KEY LLM_API=openai \
  LLM_BASE_URL=https://api.groq.com/openai LLM_MODEL=qwen/qwen3-32b \
  LLM_MAX_TOKENS=4096 LLM_TEMPERATURE=0.3 \
  python eval/run_cloud_detector.py --dataset ru --detector cloud-qwen3-32b-var$i; done
python eval/score_cloud_r5.py        # -> eval/cloud-r5-variance.json
python eval/score_local_r5_subset.py # -> eval/local-r5-variance-subset.json (local 3b subset)
```
