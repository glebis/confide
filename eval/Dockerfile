# PsychoPII benchmark runner — reproducible env (see REPRODUCIBILITY.md §6).
# The local LLM runs in a sibling service (llama.cpp, primary) via the
# OpenAI-compatible endpoint; this image holds the detectors + scorer.
FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl build-essential git && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY eval/requirements.lock eval/requirements.lock
RUN pip install --no-cache-dir -r eval/requirements.lock

COPY skills/ skills/
COPY sessions-ru/ sessions-ru/
COPY sessions-en/ sessions-en/
COPY eval/ eval/

WORKDIR /app/eval
# llama.cpp (primary) via OpenAI-compatible endpoint; override for ollama.
ENV LLM_API=openai LLM_BASE_URL=http://llm:8080 DETECTORS=natasha,regex,ollama
ENTRYPOINT ["bash", "run-benchmark.sh"]
