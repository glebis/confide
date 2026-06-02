#!/usr/bin/env bash
# Reproducible benchmark entrypoint (container or host). Waits for the LLM,
# rebuilds gold, refreshes the detector caches used by the published tables,
# scores them, and logs a provenance record.
set -euo pipefail

: "${LLM_BASE_URL:=http://localhost:11434}"
: "${LLM_MODEL:=qwen2.5:3b}"

if [ -n "${DETECTORS:-}" ]; then
  : "${RU_DETECTORS:=$DETECTORS}"
  : "${RU_ADV_DETECTORS:=$DETECTORS}"
  : "${EN_DETECTORS:=$DETECTORS}"
  : "${EN_REAL_DETECTORS:=$DETECTORS}"
else
  : "${RU_DETECTORS:=natasha,regex,ollama}"
  : "${RU_ADV_DETECTORS:=natasha,regex,ollama}"
  : "${EN_DETECTORS:=opf,regex,ollama,presidio,philter}"
  : "${EN_REAL_DETECTORS:=opf,regex,ollama,presidio,philter}"
fi

echo "==> waiting for LLM at ${LLM_BASE_URL} ..."
for _ in $(seq 1 120); do
  if curl -sf "${LLM_BASE_URL}/health" >/dev/null 2>&1 \
     || curl -sf "${LLM_BASE_URL}/v1/models" >/dev/null 2>&1 \
     || curl -sf "${LLM_BASE_URL}/api/tags" >/dev/null 2>&1; then
    echo "    LLM ready."; break
  fi
  sleep 3
done

# The eval suite is the confide_eval package under src/; run modules via -m.
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}src"
PY="python3 -m confide_eval"

echo "==> building gold"
$PY.data.build_ru_dataset
$PY.data.build_ru_adversarial

echo "==> running detector caches"
$PY.detectors.run_detectors --dataset ru --detectors "$RU_DETECTORS" --model "$LLM_MODEL"
$PY.detectors.run_detectors --dataset ru-adv --detectors "$RU_ADV_DETECTORS" --model "$LLM_MODEL"
$PY.detectors.run_detectors --dataset en --detectors "$EN_DETECTORS" --model "$LLM_MODEL"
$PY.detectors.run_detectors --dataset en-real --detectors "$EN_REAL_DETECTORS" --model "$LLM_MODEL"

echo "==> scoring (logs a run record to caches/runs/)"
for ds in ru ru-adv en en-real; do
  $PY.scoring.score_bench --dataset "$ds" --out-prefix "$ds-"
done

echo "==> computing regulatory residual-risk metrics"
$PY.scoring.regulatory

echo "==> generating benchmark report"
$PY.report.make_benchmark

# copy headline artifacts to the host-mounted out/ if present
if [ -d out ]; then
  cp -f docs/BENCHMARK.md results/*-bench-results.json caches/runs/runs.jsonl out/ 2>/dev/null || true
fi
echo "==> DONE. See docs/BENCHMARK.md and caches/runs/runs.jsonl"
