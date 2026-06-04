#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 MODEL DETECTOR_PREFIX [DATASET] [DOC_IDS]" >&2
  echo "Example: $0 gemma3:4b local-gemma3-4b ru ru-a-s01,ru-b-s03" >&2
  exit 2
fi

MODEL="$1"
PREFIX="$2"
DATASET="${3:-ru}"
DOC_IDS="${4:-ru-a-s01,ru-b-s03}"
CHUNK_CHARS="${CHUNK_CHARS:-0}"
CHUNK_OVERLAP="${CHUNK_OVERLAP:-200}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PROMPT_DIR="$ROOT/experiments/local-llm-deid/prompts"
DETECTORS=()

for prompt in "$PROMPT_DIR"/pii_v[1-5]_*.txt; do
  stem="$(basename "$prompt" .txt)"
  suffix="${stem%%_*}"
  detector="${PREFIX}-${suffix}"
  DETECTORS+=("$detector")
  extra_args=()
  if [[ "$CHUNK_CHARS" != "0" ]]; then
    extra_args+=(--chunk-chars "$CHUNK_CHARS" --chunk-overlap "$CHUNK_OVERLAP")
  fi
  PYTHONPATH="$ROOT/src" python3 -m confide_eval.detectors.run_llm_detector \
    --dataset "$DATASET" \
    --doc-ids "$DOC_IDS" \
    --detector "$detector" \
    --model "$MODEL" \
    --prompt-file "$prompt" \
    "${extra_args[@]}"
done

joined="$(IFS=,; echo "${DETECTORS[*]}")"
PYTHONPATH="$ROOT/src" python3 -m confide_eval.scoring.score_llm_experiment \
  --dataset "$DATASET" \
  --doc-ids "$DOC_IDS" \
  --include-default-ollama \
  --detectors "$joined" \
  --out "$ROOT/results/local-llm-small-sample-${DATASET}.json"
