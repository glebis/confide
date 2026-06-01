#!/usr/bin/env bash
# One-command install for session-anonymizer's three layers. Idempotent.
# Each layer is OPTIONAL — the script skips missing layers at runtime and warns.
set -euo pipefail
cd "$(dirname "$0")"

echo "==> Layers 1 & 2: Natasha (Russian NER) + scrubadub + phonenumbers (deterministic regex)"
pip install -r requirements.txt

echo "==> Layer 3: Ollama model (medications / dates / contextual IDs)"
if command -v ollama >/dev/null 2>&1; then
  ollama pull qwen2.5:3b       # skill's verified default (no thinking overhead; qwen3:4b returns empty)
else
  echo "    Ollama not found — install from https://ollama.com, then: ollama pull qwen2.5:3b" >&2
fi

echo "==> Done. Verify: python3 scripts/anonymize.py --help"
echo "    Layers 1 & 2 are lightweight (tens of MB, instant); only the Ollama model needs real RAM."
echo "    Fast deterministic pass with no LLM: --layers natasha,regex"
