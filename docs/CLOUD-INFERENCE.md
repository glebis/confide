# CONFIDE — cloud inference options for the bigger-model experiments (R9/R5)

The local qwen2.5:3b **collapsed** on 32K-char RU docs (entity recall 0.157, 2 docs JSON-errored).
R9 needs a *bigger* model; a 48–64 GB Mini was one path, but **cloud inference APIs** run 70B–235B
open models fast and free the local machine. **Synthetic data only** — never send real/consented
transcripts to a cloud endpoint (same rule as the gpt-5 CONFIDE-Red run).

CONFIDE's LLM transport is already engine-agnostic: set `LLM_API=openai`, `LLM_BASE_URL=<provider
/v1>`, `LLM_MODEL=<id>`, and the right `*_API_KEY` — `anonymize.run_ollama` + `confide_red.py` post
to `/v1/chat/completions` unchanged.

## Providers (all OpenAI-compatible)

| Provider | Key in env? | Endpoint | Best RU-capable big models | Speed | Cost |
|---|---|---|---|---|---|
| **Cerebras** | ✅ `CEREBRAS_API_KEY` | `https://api.cerebras.ai/v1` | `qwen-3-235b-*`, `qwen-3-32b`, `llama-3.3-70b`, `llama-4-*`, `gpt-oss-120b` | **fastest** (wafer-scale) | free tier (rate-limited) |
| **Groq** | ✅ `GROQ_API_KEY` | `https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile`, `qwen-2.5-32b`/`qwen3-*`, `llama-4-scout/maverick`, `deepseek-r1-distill-llama-70b`, `gpt-oss-120b`, `kimi-k2` | very fast | free tier (rate-limited) |
| **Together.ai** | ❌ (no key) | `https://api.together.xyz/v1` | `Qwen2.5-72B-Instruct`, `Llama-3.3-70B`, `DeepSeek-V3`, `Qwen2.5-72B` | fast | pay-per-token |
| **z.ai (GLM)** | ❌ (no key) | `https://api.z.ai/api/paas/v4` | `glm-4.6`, `glm-4.5`, `glm-4-32b` (strong multilingual) | fast | pay-per-token |

## Recommendation for R9 (RU de-id, 3b → big head-to-head)

- **Cleanest comparison:** stay in the **Qwen family** (local was qwen2.5:3b) → a big Qwen scales
  the *same* model. Best available: **Cerebras `qwen-3-235b`** (or `qwen-3-32b` for a mid rung),
  or **Together `Qwen2.5-72B-Instruct`** if a key is added.
- **Strong multilingual alternatives:** `llama-3.3-70b` (Groq/Cerebras, good RU), `glm-4.6`
  (z.ai, excellent multilingual), `deepseek-v3` (Together).
- **Both present keys (Cerebras, Groq) are free-tier + fast** → no spend needed to run R9/R5.

**Plan:** run the RU LLM detector layer + CONFIDE-Red with **Cerebras qwen-3-235b** (primary) and
**Groq llama-3.3-70b** (cross-check), compare entity recall + ms/doc + JSON-error rate vs local
qwen2.5:3b. The same cloud model then powers **R5** (N≥5 variance) without grinding the laptop.

## Guardrails

- **Synthetic corpus only.** Real/consented sessions stay on the local stack (`THREE-LOCKS.md`).
- Pin the served model id + record it in the run registry (digests aren't exposed by these APIs;
  record the `id` string + date).
- Respect free-tier rate limits (batch/sleep between docs); fall back Cerebras→Groq→local on error.

## What actually ran (2026-06-02) — see `CLOUD-MODEL-RESULTS.md`

- **Model used: Groq `qwen/qwen3-32b`.** Cerebras' served catalogue on this tier
  was only `gpt-oss-120b` + `zai-glm-4.7` (no big Qwen); Groq had `qwen/qwen3-32b`
  (clean scale-up from `qwen2.5:3b`) + `llama-3.3-70b-versatile`.
- **Two transport gotchas, now handled in `anonymize.run_ollama`:**
  1. Both providers' Cloudflare front returns **HTTP 403 error 1010** to the
     default `urllib` User-Agent. A browser `User-Agent` header is required.
  2. `run_ollama` appends `/v1/chat/completions` itself, so set
     `LLM_BASE_URL=https://api.groq.com/openai` (**no** trailing `/v1`).
  Also added: `Authorization: Bearer $OPENAI_API_KEY`, and env overrides
  `LLM_TEMPERATURE` (R5 variance) / `LLM_MAX_TOKENS` (Qwen3 `<think>` budget).
- **Result:** R9 LLM-only entity recall 0.157 (3b) → **0.565** (qwen3-32b), full
  stack 0.676 → **0.815**; R5 LLM run-variance (N=5, temp 0.3) ±0.017–0.022.
