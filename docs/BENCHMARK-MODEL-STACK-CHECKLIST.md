# Checklist: Adding a New LLM Model or Stack Combo to CONFIDE-Bench

Use this checklist when adding any new LLM model, prompt/runtime variant, provider endpoint, chunking strategy, or detector-stack combination to the benchmark. The rule is simple: compare under a new detector name first, promote only with provenance, and never let a model experiment silently rewrite the published default.

## 1. Scope the Change

- [ ] State the research question before running anything: model swap, prompt comparison, runtime comparison, cloud scale-up, or new fixed stack combo.
- [ ] Name the candidate with a stable detector id, for example `local-gemma3-4b-chunk2k` or `cloud-qwen3-32b-r5`. Do not use names reserved by `RESERVED_DETECTORS` in `src/confide_eval/detectors/run_llm_detector.py`; it currently includes `ollama`, `natasha`, `regex`, `opf`, `presidio`, and `philter`.
- [ ] Choose the datasets up front: `ru`, `ru-adv`, `ru-real`, `en`, and/or `en-real`.
- [ ] Confirm the privacy boundary:
  - local models may run on committed synthetic/proxy benchmark data;
  - cloud/remote endpoints may run only on synthetic benchmark text or data explicitly approved for remote processing;
  - real or consented sessions stay local-only and stats-only;
  - do not send raw transcript text to Claude or any review assistant.
- [ ] Decide whether this is exploratory or publishable. Exploratory candidates use `score_llm_experiment.py`; publishable fixed combos require the promotion gates below.

## 2. Pin Provenance

- [ ] Record the exact model id. For Ollama, include the output of `ollama show <model> --modelfile` or an image/digest equivalent. For cloud APIs, record the served `id` string, provider, endpoint, and run date because provider digests are usually unavailable.
- [ ] Record runtime and transport: Ollama, local OpenAI-compatible server, llama.cpp, vLLM, Groq, Cerebras, Together, Vertex, etc.
- [ ] Record hardware when cost or latency is discussed: host, CPU/GPU/MPS, memory pressure, and notable disk constraints.
- [ ] Record prompt provenance: prompt file path, prompt version, `prompt_sha` from the manifest, and whether `{text}` is the insertion point.
- [ ] Record run-ledger provenance for publishable comparisons. `score_bench.py` appends to `caches/runs/runs.jsonl`; exploratory `score_llm_experiment.py` result JSON must either be promoted through that path or get an aggregate-only `run_registry.log_run(...)` entry. Never overwrite an existing run row.
- [ ] Check model/provider licence and terms. If a new provider, runtime, or model family becomes part of the documented stack, add it to `TOOLS.md`.

## 3. Prepare the Candidate

- [ ] Verify the model can answer a small non-sensitive prompt before running benchmark text.
- [ ] For local models, check RAM and disk before pulling large weights.
- [ ] For reasoning models, confirm whether thinking output must be disabled or token budget raised so JSON spans appear in `message.content`.
- [ ] Confirm the output taxonomy is limited to canonical benchmark types: `PERSON`, `LOCATION`, `ORG`, `PHONE`, `EMAIL`, `URL`, `ID`, `DATE`, `MEDICATION`, `AGE`, `PROFESSION`.
- [ ] If using chunking, pin `--chunk-chars` and `--chunk-overlap`; treat chunking as part of the detector identity.
- [ ] Use a fixed small sample before a full run. For RU local-LLM probes, the current sample is:

```bash
DOCS=ru-a-s01,ru-b-s03,ru-c-s02,ru-d-s04,ru-e-s05
```

## 4. Generate Caches Without Overwriting Defaults

Local candidate:

```bash
PYTHONPATH=src python3 -m confide_eval.detectors.run_llm_detector \
  --dataset ru \
  --doc-ids "$DOCS" \
  --detector local-my-model-p1 \
  --model my-model:tag \
  --prompt-file experiments/local-llm-deid/prompts/my_prompt.txt
```

Local OpenAI-compatible server:

```bash
PYTHONPATH=src python3 -m confide_eval.detectors.run_llm_detector \
  --dataset ru \
  --detector local-vllm-my-model \
  --model org/my-model \
  --api openai \
  --base-url http://localhost:8000 \
  --prompt-file experiments/local-llm-deid/prompts/my_prompt.txt
```

Remote synthetic-only candidate:

```bash
OPENAI_API_KEY=... PYTHONPATH=src python3 -m confide_eval.detectors.run_llm_detector \
  --dataset ru \
  --detector cloud-my-model \
  --model provider/my-model \
  --api openai \
  --base-url https://provider.example/openai \
  --prompt-file experiments/local-llm-deid/prompts/my_prompt.txt \
  --allow-remote
```

- [ ] Use `--resume` only to continue the same detector run after an interruption. Do not use `--resume` across independent variance replicates.
- [ ] Use `--sleep` for free-tier or rate-limited remote providers.
- [ ] Inspect the cache manifest after every run:
  - `invalid_spans` must be `0`;
  - `doc_ids` must match the intended document set;
  - `docs_sha` must match the selected or full input-text set expected by the scorer; it is a content hash over concatenated document text, not a doc-id hash;
  - `model`, `provider`, and `provider_base` must match the intended candidate;
  - `prompt_sha` must be non-null for publishable prompt-file runs;
  - `empty_docs` must be explained, not ignored;
  - `seconds` should be recorded if latency is discussed.

## 5. Score and Compare

Small-sample comparison:

```bash
PYTHONPATH=src python3 -m confide_eval.scoring.score_llm_experiment \
  --dataset ru \
  --doc-ids "$DOCS" \
  --include-default-ollama \
  --detectors local-my-model-p1 \
  --out results/local-llm-my-model-small-ru.json
```

Full-dataset comparison:

First regenerate the candidate cache without `--doc-ids`; otherwise the full scorer will see a small-sample cache that lacks most documents.

```bash
PYTHONPATH=src python3 -m confide_eval.detectors.run_llm_detector \
  --dataset ru \
  --detector local-my-model-p1 \
  --model my-model:tag \
  --prompt-file experiments/local-llm-deid/prompts/my_prompt.txt
```

```bash
PYTHONPATH=src python3 -m confide_eval.scoring.score_llm_experiment \
  --dataset ru \
  --include-default-ollama \
  --detectors local-my-model-p1 \
  --out results/local-llm-my-model-full-ru.json
```

- [ ] Rank candidates by entity-level recall, harm-weighted recall, coverage containment recall, type-aware F2, then failure counts (`empty_docs`, `invalid_spans`), with precision as an over-redaction guardrail.
- [ ] For LLM-dependent publishable metrics, run at least `N>=3` independent detector caches and report mean +/- std. Use distinct detector ids such as `local-my-model-r1`, `local-my-model-r2`, and `local-my-model-r3`; do not overwrite the same cache or use `--resume` between replicates. Use `N>=5` when making a variance claim comparable to R5.
- [ ] Record the sampling configuration that makes replicates comparable, for example `LLM_TEMPERATURE`, token budget, prompt file, chunking, endpoint, and model id.
- [ ] Keep dev/test discipline: inspect prompts and thresholds on dev; use test only for reporting generalisation.
- [ ] Do not call a candidate a new default just because it beats a point estimate. Compare against bootstrap CIs and the preregistered minimum-detectable-difference caveat.

## 6. Promotion Gates

Use these gates only after the exploratory comparison is worth publishing.

- [ ] If adding a fixed ablation combo, update `COMBOS` in `src/confide_eval/scoring/score_bench.py`.
- [ ] If changing a star default, treat it as a preregistration amendment and update `PREREGISTRATION.md`; do not bury it as a routine result refresh.
- [ ] Regenerate affected detector caches under their stable detector names.
- [ ] Regenerate affected score artifacts:

```bash
PYTHONPATH=src python3 -m confide_eval.scoring.score_bench --dataset ru --out-prefix ru-
PYTHONPATH=src python3 -m confide_eval.scoring.bootstrap_ci --dataset ru --iters 2000
PYTHONPATH=src python3 -m confide_eval.report.make_benchmark
PYTHONPATH=src python3 -m confide_eval.report.make_tufte_report
```

- [ ] Repeat the commands for every affected dataset. `en-real` requires `python -m confide_eval.data.fetch_ai4privacy` locally and should be skipped rather than faked when source text is absent.
- [ ] Run `make check` before committing any benchmark-result update.
- [ ] If code changed, run the focused tests for detector/scoring behaviour and then the repository's normal test target.

## 7. Documentation Updates

- [ ] Update the experiment note (`LOCAL-LLM-DEID-EXPERIMENT.md` or `CLOUD-MODEL-RESULTS.md`) with model id, date, command, scope, metrics, caveats, and recommendation.
- [ ] Update `REPRODUCIBILITY.md` if the re-run policy, provenance fields, variance policy, or cost policy changed.
- [ ] Update `REPORTING.md` if the headline/omission logic changes.
- [ ] Update `PREREGISTRATION.md` for any fixed combo/default change.
- [ ] Update `BENCHMARK.md` only through `make_benchmark.py` when generated benchmark text changes.
- [ ] Update `TOOLS.md` when a new provider, model family, runtime, or external baseline becomes part of the documented workflow.
- [ ] Update `README.md` and `CONFIDE-README.md` if the public docs map, quickstart, or default-stack language changes.
- [ ] If a new result file is committed, ensure it is linked from the relevant result or experiment document.

## 8. Claude Validation Gate

- [ ] Send Claude only the checklist, commands, prompt templates, review rubric, and aggregate metrics. Do not send raw transcript text.
- [ ] Ask Claude to review for missing provenance, privacy, reproducibility, promotion, and documentation gates.
- [ ] Resolve every blocking issue or record why it is out of scope.
- [ ] Record the validation summary below.

Validation summary: Claude Code reviewed this checklist on 2026-06-04 using documentation and runner/scorer excerpts only, with no raw transcript data. Valid findings were incorporated: explicit `runs.jsonl` provenance, independent replicate detector ids, full-cache regeneration before full scoring, clearer `docs_sha` wording, reserved-name source-of-truth wording, and stricter manifest inspection. One reported blocker was rejected after checking `run_llm_detector.py`: the manifest does include `prompt_sha`. Follow-up Claude validation accepted the patched checklist with no remaining blockers.

## 9. Done Criteria

- [ ] Candidate has a separate cache name and manifest; default caches were not overwritten.
- [ ] Metrics are reproducible from committed or locally reconstructable inputs.
- [ ] LLM variance has been measured for publishable LLM-dependent claims.
- [ ] Privacy boundary is explicit, especially for cloud/remote runs.
- [ ] Promotion/default changes are preregistered or explicitly labelled as amendments.
- [ ] All related docs link back to this checklist.
- [ ] Claude validation has been completed and recorded.
