# CONFIDE-Red — floor-vs-ceiling re-identification risk

**Floor** = weak local attacker, `qwen2.5:3b` via Ollama.
**Ceiling** = strong cloud attacker, `gpt-5` via the OpenAI-compatible
`/v1/chat/completions` endpoint (`LLM_API=openai`, key from `OPENAI_API_KEY`).

**Synthetic data only.** Every persona/attribute (clients a–f) is fabricated, so
sending the redacted text to a cloud model is acceptable here. This would **never**
be done on real sessions.

**Controlled comparison.** The *defense* (the CONFIDE redactor: Natasha NER +
regex + local `qwen2.5:3b` Ollama LLM layer) is held **identical** across both
runs — only the *attacker* model changes. The redactor is pinned to local Ollama
inside `redact()` regardless of which engine the attacker uses, so the numbers
below isolate attacker strength.

**Caveat.** Even the gpt-5 ceiling is still a **lower bound** on a determined,
resourced adversary: no external knowledge bases, no cross-corpus linkage, no
human analyst, single-shot prompts, top-3 scoring against a known truth dict. A
real attacker with auxiliary data would do better.

## 1. Inference attack — top-3 attribute recovery (of 5 attributes/client)

Best-of-3-prompt-strategies recovery per client:

| Client | floor (qwen3b) | ceiling (gpt-5) | of | Δ |
|---|--:|--:|--:|--:|
| a | 2 | 2 | 5 | 0 |
| b | 2 | 4 | 5 | +2 |
| c | 1 | 5 | 5 | +4 |
| d | 3 | 4 | 5 | +1 |
| e | 0 | 4 | 5 | +4 |
| f | 1 | 4 | 5 | +3 |
| **Σ** | **9 / 30** | **23 / 30** | | **+14** |

The stronger attacker recovered **2.6×** as many redacted attributes overall
(30% → 77%). Client e went from 0/5 (floor whiffed completely) to 4/5. No client
got *worse*. gpt-5 fully reconstructed client c (5/5).

### Per-prompt-strategy breakdown (direct / reason / investigator)

| Client | floor d/r/i | ceiling d/r/i |
|---|---|---|
| a | 2 / 1 / 0 | 2 / 2 / 0 |
| b | 1 / 1 / 2 | 3 / 3 / 4 |
| c | 1 / 0 / 1 | 4 / 4 / 5 |
| d | 0 / 3 / 0 | 4 / 4 / 4 |
| e | 0 / 0 / 0 | 4 / 2 / 4 |
| f | 1 / 1 / 1 | 4 / 4 / 4 |

The floor model is erratic across framings (e.g. client d: only the "reason"
prompt scored). gpt-5 is consistently high across all three framings — the
anonymizer's residual leakage is robustly exploitable, not a prompt artifact.

## 2. Singling-out — ILLUSTRATIVE

> **ILLUSTRATIVE / methodological demonstration, not a re-identification probability.**
Computed by the shared `kanon` estimator (entity-aware survivor detection over the
gold + detector caches, one sourced prior table) — **independent of the attacker
model** (no LLM in this attack), so identical in both runs. Personas are synthetic;
this shows *how* singling-out is assessed, not a precise probability. The naive
product assumes independent quasi-identifiers and therefore OVERSTATES uniqueness.

| Client | singled out? | expected matches (illustrative) | verdict robust to ±0.5x–2x priors? |
|---|---|--:|---|
| a | no | 50.1 | yes |
| b | no | 1.7 | **no (flips)** |
| c | no | 33.4 | yes |
| d | no | 62.6 | yes |
| e | no | 5256.0 | yes |
| f | no | 83.4 | yes |

No client is singled out under the unified estimate. The **relative ranking** is
the signal: client b (k≈1.7) is by far the most exposed — its surviving
age+location+medication+profession combination sits right at the k=1 threshold and
its "not singled out" verdict **flips** if the priors are tightened 2x, so it is not
robust. This is attacker-independent: a property of what survived redaction, not of
who reads it.

## 3. Linkability — can the attacker tell two sessions are the same person?

| | same-pair → "same"? | diff-pair → "same"? | linkable? |
|---|---|---|---|
| floor (qwen3b) | False | False | **No** |
| ceiling (gpt-5) | True | False | **YES** |

The floor model failed to recognize that two sessions from client a were the same
person. gpt-5 correctly judged the same-client pair as the same person **and** the
cross-client pair as different — so it achieves **linkability** that the weak
attacker missed entirely.

## Bottom line

Going from a weak 3b local model to a frontier cloud model flips two of the three
attacks toward the attacker:

- **Inference:** 9/30 → 23/30 attributes recovered (+14, 2.6×).
- **Linkability:** not-linkable → **linkable**.
- **Singling-out (illustrative):** unchanged across attackers — 0/6 clients singled out, but client b (k≈1.7) is the most exposed and its verdict is *not* robust to a 2x prior tightening.

The synthetic corpus's residual re-identification risk after CONFIDE redaction is
**substantially higher than the 3b floor suggests**. The gap between floor and
ceiling is the danger zone: a defender who only red-teams with a small local model
will badly underestimate what a capable adversary recovers. And the ceiling itself
is still conservative.
