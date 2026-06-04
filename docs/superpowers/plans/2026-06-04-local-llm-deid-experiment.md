# Local LLM De-Identification Experiment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compare Gemma/Gemma3n and Qwen local LLM detector variants across five prompt iterations, then promote the best candidates from a small RU sample to the wider CONFIDE benchmark.

**Architecture:** Keep the committed `ollama` baseline unchanged. Add a prompt-template hook to the anonymizer, write each local model+prompt pair to a separate detector cache, and score arbitrary candidates outside `score_bench.py`'s fixed publication combos.

**Tech Stack:** Python 3.11, Ollama local chat API, existing `anonymize.run_ollama`, CONFIDE gold JSONL, detector-cache manifests, `score_bench.py` metric helpers.

---

### Task 1: Prompt-Template Hook

**Files:**
- Modify: `skills/session-anonymizer/scripts/anonymize.py`
- Test: `tests/test_local_llm_experiment.py`

- [x] **Step 1: Add a default prompt template and renderer**

Add `_DEFAULT_PII_PROMPT_TEMPLATE`, `_load_llm_prompt_template()`, and `_render_llm_prompt()` so experiment prompts can be passed by function argument, `LLM_PROMPT_FILE`, or `LLM_PROMPT_TEMPLATE`.

- [x] **Step 2: Preserve current behavior**

Update `run_ollama(text, model="qwen2.5:3b", prompt_template=None)` so the verified default prompt is identical in effect unless a template is supplied.

- [x] **Step 3: Disable exposed thinking for Ollama reasoning models**

Add `think: false` to the Ollama `/api/chat` payload. Gemma 4 12B otherwise spends the generation budget in `message.thinking` and returns empty `message.content`.

- [x] **Step 4: Test JSON-brace safety and Ollama payload**

Run: `PYTHONPATH=src python3 -m pytest tests/test_local_llm_experiment.py -q`

Expected: prompt templates containing JSON examples render without requiring doubled braces.

### Task 2: Custom Local LLM Detector Runner

**Files:**
- Create: `src/confide_eval/detectors/run_llm_detector.py`

- [x] **Step 1: Add custom cache writer**

Create a runner with `--dataset`, `--detector`, `--model`, `--prompt-file`, `--doc-ids`, and `--limit-docs`. It writes `caches/detector-cache/<dataset>.<detector>.jsonl`.

- [x] **Step 2: Protect baseline caches**

Reject reserved detector names: `ollama`, `natasha`, `regex`, `opf`, `presidio`, and `philter`.

- [x] **Step 3: Keep local-first transport**

Default to Ollama and reject non-local endpoints unless `--allow-remote` is explicitly passed.

- [x] **Step 4: Add resumable long-run support**

Add `--resume` so existing completed cache rows are reused and only missing documents are processed. This is required for benchmark-wide long-RU chunked runs where a single pass can take more than an hour locally.

### Task 3: Arbitrary Candidate Scorer

**Files:**
- Create: `src/confide_eval/scoring/score_llm_experiment.py`

- [x] **Step 1: Score LLM-only candidates**

Score `[detector]` against the selected gold docs using the same span coverage, type-aware, and entity-level helpers as `score_bench.py`.

- [x] **Step 2: Score stack candidates**

For RU datasets score `natasha+regex+detector`; for EN datasets score `opf+regex+detector`.

- [x] **Step 3: Support small samples and full benchmark**

Accept `--doc-ids` for small samples and omit it for full dataset scoring. Validate manifests against either selected-doc or full-doc transcript hashes.

### Task 4: Five Prompt Iterations

**Files:**
- Create: `experiments/local-llm-deid/prompts/pii_v1_baseline.txt`
- Create: `experiments/local-llm-deid/prompts/pii_v2_taxonomy_first.txt`
- Create: `experiments/local-llm-deid/prompts/pii_v3_all_mentions.txt`
- Create: `experiments/local-llm-deid/prompts/pii_v4_json_strict.txt`
- Create: `experiments/local-llm-deid/prompts/pii_v5_ru_therapy.txt`

- [x] **Step 1: Write five prompt variants**

Cover baseline extraction, taxonomy-first recall, all-mentions discipline, JSON-strict exact substrings, and RU therapy-specific quasi-identifiers.

- [x] **Step 2: Claude review**

Sent only prompt text and the review rubric to Claude. No raw transcript text was sent. Claude ranked v5 > v3 > v2 > v4 > v1 and recommended a schema-compatible v5+v3+v4 hybrid.

### Task 5: Model Setup And Evaluation

**Files:**
- Modify: `docs/LOCAL-LLM-DEID-EXPERIMENT.md`

- [x] **Step 1: Pull the selected Gemma model**

Run: `ollama pull gemma3:4b` and `ollama pull gemma4:12b-mlx`.

Expected: Gemma 3 4B and Gemma 4 12B-MLX appear in `ollama list`.

Gemma 4 notes: `gemma4:12b-mlx` is installed at 10.0 GB. Local machine has 24 GB unified memory and 15 GiB free disk after the pull. It responds to `hello`, but whole-document `ru-a-s01` timed out at 180.1s with the current prompt.

- [ ] **Step 2: Run small-sample prompt sweep**

Run local caches for `qwen2.5:3b`, `qwen3:4b`, `gemma3:4b`, and selected Gemma4 variants over a fixed RU sample. Score all candidates with `score_llm_experiment.py`.

Current evidence: Gemma3 4B v1/v2 returned 0 spans on two RU docs. Gemma3 with the Claude hybrid plus chunking achieved high recall but severe over-redaction. Gemma4 12B-MLX needs `think:false`; it works on synthetic text but is too slow for whole-document local inference with the current prompt.

- [ ] **Step 3: Promote best candidates**

Run the best model+prompt detector caches on `ru`, `ru-adv`, `ru-real`, and `en` where the model is available, then score without `--doc-ids`.

Current propagation evidence:

- Done: full `ru-adv`, `ru-real`, and `en` for `gemma3:latest` + Claude hybrid.
- Done: full `ru-adv`, `ru-real`, and `en` for `gemma4:12b-mlx` + Claude hybrid.
- Done: synthetic cloud probe for Hugging Face Router `google/gemma-4-26B-A4B-it:fastest` on `ru-adv`; English synthetic started but is partial because 13/32 requests returned `402 Payment Required`.
- Done: full main `ru` long-transcript propagation for `gemma3:latest` + Claude hybrid with chunking (`chunk_chars=2000`, `chunk_overlap=250`).
- Result: Gemma4 beats the Qwen baseline on all completed full short slices; Gemma3 is faster and also beats Qwen on those slices.
- Result: long-RU Gemma3 chunked is high-recall but too noisy for promotion: stack recall 0.954 vs Qwen 0.875, but type-F2 0.362 vs Qwen 0.802 and 9,093 predictions.

- [ ] **Step 4: Verify**

Run: `PYTHONPATH=src python3 -m pytest tests/test_local_llm_experiment.py -q`

Expected: all tests pass.
