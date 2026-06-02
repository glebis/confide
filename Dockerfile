# CONFIDE benchmark runner — reproducible env (see REPRODUCIBILITY.md §6).
# The local LLM runs in a sibling service (llama.cpp, primary) via the
# OpenAI-compatible endpoint; this image holds the detectors + scorer.
FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl build-essential git && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.lock requirements.lock
RUN pip install --no-cache-dir -r requirements.lock

COPY skills/ skills/
COPY data/ data/
COPY caches/ caches/
COPY results/ results/
COPY docs/ docs/
COPY src/ src/
COPY pyproject.toml Makefile run-benchmark.sh ./

# Install the eval package so `python -m confide_eval.*` resolves anywhere.
RUN pip install --no-cache-dir -e .
RUN python -m spacy download en_core_web_sm \
    && python -c "import nltk; nltk.download('averaged_perceptron_tagger_eng')"

# llama.cpp (primary) via OpenAI-compatible endpoint; override for ollama.
ENV LLM_API=openai LLM_BASE_URL=http://llm:8080 \
    RU_DETECTORS=natasha,regex,ollama \
    RU_ADV_DETECTORS=natasha,regex,ollama \
    EN_DETECTORS=opf,regex,ollama,presidio,philter \
    EN_REAL_DETECTORS=opf,regex,ollama,presidio,philter
WORKDIR /app
ENTRYPOINT ["bash", "run-benchmark.sh"]
