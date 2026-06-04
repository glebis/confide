# Local LLM De-Identification Experiment

This experiment tests the user's challenge that CONFIDE should not assume Qwen is the only viable local LLM layer.
Before adding another local model, prompt/runtime variant, chunking strategy, or stack combo, use
`BENCHMARK-MODEL-STACK-CHECKLIST.md`.

## Model Decision

The model family is **Gemma**, not "Gamma."

As of 2026-06-04, Google has announced **Gemma 4 12B**. Google describes it as laptop-ready with **16 GB of VRAM or unified memory**, and Ollama exposes an MLX build as `gemma4:12b-mlx` with a **10.0 GB** model file and a 128K context window.

Local machine check:

- Installed RAM: 24 GB unified memory.
- Installed model: `gemma4:12b-mlx` at 10.0 GB.
- Remaining disk after pull and experiment caches: 13 GiB free on `/System/Volumes/Data`.

That is enough RAM to run the model locally, but disk is now tight. Do not pull more large variants until Ollama storage is cleaned up or moved.

Current comparison candidates:

- `qwen2.5:3b` - committed baseline.
- `qwen3:4b` - already installed locally, useful as a "pre-existing release" check, but previous project notes warn about thinking-mode/empty-output behavior.
- `gemma3:latest` / `gemma3:4b` - local Gemma 3 fallback. It runs, but non-chunked v1/v2 prompts produced no spans; chunking with the Claude hybrid improves recall while causing heavy over-redaction.
- `gemma4:12b-mlx` - latest local Gemma 4 candidate. It runs and handles synthetic de-id after disabling thinking. It is the strongest short-slice candidate so far, but whole-document inference timed out on long `ru-a-s01`.

Cloud availability is not the same as weight availability. The 2026-06-04 Hugging Face model search finds `google/gemma-4-12B-it`, but the Hugging Face Router chat model list currently exposes Gemma chat routes for `google/gemma-4-26B-A4B-it`, `google/gemma-4-31B-it`, `google/gemma-3-27b-it`, and `google/gemma-3n-E4B-it`, not Gemma 4 12B.

Smaller Gemma 4 options exist and are likely better local probes before spending cloud money:

- `gemma4:e2b-mlx` - 7.1 GB, 128K context, text.
- `gemma4:e4b-mlx` - 9.6 GB, 128K context, text.
- `gemma4:e2b` / `gemma4:e4b` - edge variants; useful if the runtime needs multimodal support.

For long therapy transcripts, the next local test should be `gemma4:e2b-mlx` or `gemma4:e4b-mlx`, not another whole-document `gemma4:12b-mlx` run.

Sources:
- Google Gemma 4 12B announcement: https://blog.google/innovation-and-ai/technology/developers-tools/introducing-gemma-4-12b/
- Ollama Gemma 4 tags: https://ollama.com/library/gemma4
- Google Gemma releases: https://ai.google.dev/gemma/docs/releases
- Ollama Gemma 3 tags: https://ollama.com/library/gemma3/tags
- Ollama Gemma 3n tags: https://ollama.com/library/gemma3n/tags
- Ollama Qwen3 tags: https://ollama.com/library/qwen3/tags
- Hugging Face Inference Providers router: https://huggingface.co/docs/inference-providers/main/en/index
- Hugging Face Inference Providers pricing: https://huggingface.co/docs/inference-providers/en/pricing

## Cloud Options

Use cloud only for synthetic benchmark text or for data explicitly approved for remote processing. The runner rejects non-local endpoints unless `--allow-remote` is passed.

Practical options:

- **Google Cloud Model Garden / Vertex AI / Gemini Enterprise Agent Platform** - strongest governance fit if this becomes a production cloud path. Google lists Gemma 4 deployment through Model Garden, Cloud Run, and GKE. In this environment, no Google Cloud project credentials are configured, so this is an endpoint-deployment path rather than an immediate chat API test.
- **Self-hosted GPU endpoint on Cloud Run or GKE** - best fit for the current code if served with vLLM, llama.cpp server, SGLang, or another OpenAI-compatible `/v1/chat/completions` API. Existing command shape:

```bash
OPENAI_API_KEY=... PYTHONPATH=src python3 -m confide_eval.detectors.run_llm_detector \
  --dataset ru \
  --detector cloud-gemma4-12b-hybrid \
  --model google/gemma-4-12B-it \
  --api openai \
  --base-url https://your-endpoint.example \
  --prompt-file experiments/local-llm-deid/prompts/pii_v6_claude_hybrid.txt \
  --allow-remote
```

- **Hugging Face Inference Providers Router** - the practical immediate cloud test path. It exposes an OpenAI-compatible `/v1/chat/completions` endpoint at `https://router.huggingface.co/v1` and supports suffixes like `:fastest`. The current `HF_TOKEN` worked for `google/gemma-4-26B-A4B-it:fastest`, but English synthetic expansion hit `402 Payment Required` after the free/credit allowance.
- **Hugging Face Inference Endpoints** - managed dedicated endpoint around Hugging Face-hosted Gemma weights. Requires Gemma access approval and `HF_TOKEN`; useful for more reliable hosted inference without operating GKE.
- **Hugging Face on Vertex AI** - good when we want Google Cloud billing/governance but Hugging Face model packaging and containers.
- **Groq** - configured locally and useful for a larger Qwen comparison (`qwen/qwen3-32b` is listed), but its model list does not currently expose Gemma with this account.
- **Ollama cloud tags** - quickest exploratory route where available, but treat as remote processing. Do not use raw private transcripts unless the account, region, retention, and legal terms are acceptable.

## Privacy Boundary

Claude review is prompt-only. Send Claude:

- the five prompt templates,
- the review rubric,
- aggregate metrics after local runs,
- anonymized failure summaries if needed.

Do not send raw transcript text to Claude. This applies even when the benchmark slice is synthetic, because the product norm is local-first de-identification.

## Five Prompt Iterations

Prompt files live in `experiments/local-llm-deid/prompts/`:

- `pii_v1_baseline.txt`
- `pii_v2_taxonomy_first.txt`
- `pii_v3_all_mentions.txt`
- `pii_v4_json_strict.txt`
- `pii_v5_ru_therapy.txt`

Claude reviewed these prompt templates through the relay without raw transcript text. Ranking:

1. `pii_v5_ru_therapy.txt`
2. `pii_v3_all_mentions.txt`
3. `pii_v2_taxonomy_first.txt`
4. `pii_v4_json_strict.txt`
5. `pii_v1_baseline.txt`

Claude's strongest recommendation was a v5+v3+v4 hybrid: keep v5's Russian therapy examples, add v3's "every distinct surface form" discipline, and add v4's `json.loads`-parseable response constraint. That hybrid is saved as:

- `pii_v6_claude_hybrid.txt`

Claude also suggested a `DIAGNOSIS` output type. This experiment intentionally does **not** add it, because the current benchmark gold taxonomy and scorer do not support `DIAGNOSIS`. Diagnoses can be considered in a future taxonomy expansion, not in this local-model comparison.

Each prompt uses `{text}` as the insertion point. The anonymizer also supports `LLM_PROMPT_FILE` and `LLM_PROMPT_TEMPLATE`, but the experiment runner passes prompt templates directly to avoid global environment bleed.

## Small-Sample Sweep

Use a fixed RU sample that covers different clients and sessions:

```bash
DOCS=ru-a-s01,ru-b-s03,ru-c-s02,ru-d-s04,ru-e-s05
```

Example cache run:

```bash
PYTHONPATH=src python3 -m confide_eval.detectors.run_llm_detector \
  --dataset ru \
  --doc-ids "$DOCS" \
  --detector local-gemma3-4b-p5 \
  --model gemma3:4b \
  --prompt-file experiments/local-llm-deid/prompts/pii_v5_ru_therapy.txt
```

Or run the five original prompt iterations for one model:

```bash
experiments/local-llm-deid/run_prompt_sweep.sh gemma3:4b local-gemma3-4b ru "$DOCS"
```

Initial Gemma3 4B probe on `ru-a-s01,ru-b-s03`:

| Candidate | LLM-only mask recall | LLM-only entity recall | Empty docs | Seconds |
| --- | ---: | ---: | ---: | ---: |
| `local-gemma3-4b-p1` | 0.000 | 0.000 | 2/2 | 135.7 |
| `local-gemma3-4b-p2` | 0.000 | 0.000 | 2/2 | 139.5 |
| committed `ollama` / `qwen2.5:3b` | 0.267 | 0.286 | from existing cache | cached |

This is evidence against promoting Gemma3 4B with the early prompts.

Gemma3 with `pii_v6_claude_hybrid.txt`:

| Candidate | Scope | LLM-only mask recall | LLM-only entity recall | Stack mask recall | Stack entity recall | nPred |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `gemma3:latest` non-chunked | `ru-a-s01` | 0.311 | 0.278 | 0.844 | 0.778 | 42 LLM / 71 stack |
| `gemma3:latest` non-chunked, JSON parser fixed | `ru-a-s01,ru-b-s03` | 0.186 | 0.179 | 0.872 | 0.786 | 43 LLM / 115 stack |
| `gemma3:latest` chunked, 2K/250 overlap | `ru-a-s01,ru-b-s03` | 0.802 | 0.643 | 0.977 | 0.929 | 666 LLM / 692 stack |

Chunking clearly fixes local-LLM recall/reliability on long transcripts, but the current Gemma3 chunked output over-redacts heavily. It is useful as a high-recall candidate, not as a clean production default.

Gemma4 12B-MLX probe:

| Check | Result |
| --- | --- |
| Pull | `gemma4:12b-mlx` installed, 10.0 GB |
| CLI hello | Works, 11.25s |
| API hello | Works, 3.35s |
| Synthetic de-id before `think:false` | Response spent token budget in `message.thinking`; `message.content` was empty |
| Synthetic de-id after `think:false` | 5 correct spans in 9.1s |
| Whole-document `ru-a-s01` | Timed out at 180.1s, 0 LLM spans |
| Whole-document score | LLM-only 0.000 mask recall / 0.000 entity recall; stack 0.800 mask recall / 0.722 entity recall from deterministic layers |
| Chunked `ru-a-s01`, 2K/250 overlap | Stopped after several minutes without a completed document write |

The code now sends `think:false` to Ollama for local `/api/chat` calls. That is required for Gemma4 12B and should be harmless for non-reasoning models.

Current local recommendation:

1. Keep `qwen2.5:3b` as the committed baseline.
2. Use `gemma4:12b-mlx` as the best-quality short-document local candidate where latency is acceptable.
3. Keep `gemma3:latest` chunked as a high-recall/noisy long-transcript comparison.
4. Do not run full long-RU `gemma4:12b-mlx` locally with the current prompt; use a smaller Gemma4 MLX variant or a cloud/GPU endpoint.
5. If testing Gemma4 locally again on long transcripts, pull `gemma4:e2b-mlx` first because it has the smallest MLX footprint.

Example score:

```bash
PYTHONPATH=src python3 -m confide_eval.scoring.score_llm_experiment \
  --dataset ru \
  --doc-ids "$DOCS" \
  --include-default-ollama \
  --detectors local-gemma3-4b-p1,local-gemma3-4b-p2,local-gemma3-4b-p3,local-gemma3-4b-p4,local-gemma3-4b-p5 \
  --out results/local-llm-small-sample-ru.json
```

Rank candidates by:

1. entity-level recall,
2. harm-weighted recall,
3. coverage containment recall,
4. type-aware F2,
5. empty-doc count and invalid-span count.

Precision is secondary for this layer because false positives are over-redaction, while false negatives are leaked identifiers.

## Full-Benchmark Propagation

After the small sample, promote the best one or two detector names to the full datasets.
Promotion to a published fixed combo or ★ default requires the gates in
`BENCHMARK-MODEL-STACK-CHECKLIST.md`; otherwise keep the candidate as an exploratory
`score_llm_experiment.py` comparison.

Example full RU run:

```bash
PYTHONPATH=src python3 -m confide_eval.detectors.run_llm_detector \
  --dataset ru \
  --detector local-gemma3-4b-best \
  --model gemma3:4b \
  --prompt-file experiments/local-llm-deid/prompts/pii_v5_ru_therapy.txt

PYTHONPATH=src python3 -m confide_eval.scoring.score_llm_experiment \
  --dataset ru \
  --include-default-ollama \
  --detectors local-gemma3-4b-best \
  --out results/local-llm-full-ru.json
```

The runner now supports `--resume`, so long detector-cache generation can reuse already completed rows after interruption instead of restarting from scratch.

Completed full short-slice propagation:

| Dataset | Candidate stack | maskCovR | typeF2 | entR | nPred | Runtime |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `ru` | Qwen baseline: `natasha+regex+ollama` | 0.875 | 0.802 | 0.726 | 1392 | cached |
| `ru` | `natasha+regex+gemma3-chunk2k` | 0.954 | 0.362 | 0.850 | 9093 | 6195.7s |
| `ru-adv` | Qwen baseline: `natasha+regex+ollama` | 0.950 | 0.887 | 0.950 | 30 | cached |
| `ru-adv` | `natasha+regex+gemma3` | 1.000 | 0.917 | 1.000 | 32 | 21.7s |
| `ru-adv` | `natasha+regex+gemma4-12b-mlx` | 1.000 | 0.948 | 1.000 | 28 | 58.0s |
| `ru-adv` | `natasha+regex+gemma4-26b-a4b-hf-cloud` | 1.000 | 0.943 | 1.000 | 26 | 17.3s |
| `ru-real` | Qwen baseline: `natasha+regex+ollama` | 0.792 | 0.614 | 0.792 | 180 | cached |
| `ru-real` | `natasha+regex+gemma3` | 0.961 | 0.730 | 0.961 | 201 | 79.8s |
| `ru-real` | `natasha+regex+gemma4-12b-mlx` | 1.000 | 0.820 | 1.000 | 172 | 336.8s |
| `en` | Qwen baseline: `opf+regex+ollama` | 0.978 | 0.870 | - | 66 | cached |
| `en` | `opf+regex+gemma3` | 1.000 | 0.904 | - | 62 | 30.7s |
| `en` | `opf+regex+gemma4-12b-mlx` | 1.000 | 0.955 | - | 54 | 191.0s |
| `en` | `opf+regex+gemma4-26b-a4b-hf-cloud` | 0.935 | 0.914 | - | 48 | 22.0s partial |

Interpretation:

- Gemma4 12B-MLX is the best-quality candidate on the completed full short slices: equal or better recall than Gemma3, better type-F2, and fewer predictions.
- Hugging Face cloud Gemma4 26B-A4B is close to local Gemma4 on `ru-adv` and much faster wall-clock, but the English run is not reliable evidence because 13 of 32 requests returned `402 Payment Required`.
- Gemma3 is much faster locally and still beats the Qwen baseline on these slices.
- Main long-RU full propagation confirms the tradeoff: Gemma3 chunked improves stack recall from 0.875 to 0.954 and entity recall from 0.726 to 0.850, but over-redacts badly: type-F2 falls from 0.802 to 0.362 with 9,093 predictions. Do not promote this as a default.
- The next long-RU step should be a smaller Gemma4 MLX variant, a stricter prompt/post-filter for Gemma3 chunking, or a cloud/GPU Gemma4 run on synthetic text only.

`en-real` requires fetching ai4privacy source text first and should stay local-only unless remote processing is explicitly approved.
