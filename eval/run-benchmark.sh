#!/usr/bin/env bash
# Reproducible benchmark entrypoint (container or host). Waits for the LLM,
# rebuilds gold, runs all detectors + scoring, and logs a provenance record.
set -euo pipefail

: "${LLM_BASE_URL:=http://llm:8080}"
: "${DETECTORS:=natasha,regex,ollama}"
: "${LLM_MODEL:=qwen2.5-3b-instruct}"

echo "==> waiting for LLM at ${LLM_BASE_URL} ..."
for _ in $(seq 1 120); do
  if curl -sf "${LLM_BASE_URL}/health" >/dev/null 2>&1 \
     || curl -sf "${LLM_BASE_URL}/v1/models" >/dev/null 2>&1 \
     || curl -sf "${LLM_BASE_URL}/api/tags" >/dev/null 2>&1; then
    echo "    LLM ready."; break
  fi
  sleep 3
done

echo "==> building gold"
python3 build_ru_dataset.py
python3 build_ru_adversarial.py

echo "==> running detectors (${DETECTORS}) on all datasets"
for ds in ru ru-adv en en-real; do
  python3 run_detectors.py --dataset "$ds" --detectors "$DETECTORS" --model "$LLM_MODEL"
done

echo "==> scoring (logs a run record to runs/)"
for ds in ru ru-adv en en-real; do
  python3 score_bench.py --dataset "$ds" --out-prefix "$ds-"
done

echo "==> generating benchmark report"
python3 make_benchmark.py

# copy headline artifacts to the host-mounted out/ if present
if [ -d out ]; then
  cp -f BENCHMARK.md *-bench-results.json runs/runs.jsonl out/ 2>/dev/null || true
fi
echo "==> DONE. See BENCHMARK.md and runs/runs.jsonl"
