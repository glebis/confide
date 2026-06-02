# Privacy (top-k attack) & Utility (downstream task)

Default stack: **natasha+regex+ollama**. Attack budget: `qwen2.5:3b`, temp 0.4, 1 call/client, top-3 guesses/attribute, background knowledge = redacted transcript only. A frontier attacker is a strict upper bound on this local-model lower bound.

## Privacy — top-k inference attack on redacted text

| Client | top-1 hits | top-3 hits | of N | residual risk |
|---|--:|--:|--:|---|
| a | 0 | 0 | 5 | **MEDIUM** |
| b | 1 | 1 | 5 | **MEDIUM** |

Per-attribute (top-3 correct?):

| Client | profession | employer | city | age | medication |
|---|--:|--:|--:|--:|--:|
| a | · | · | · | · | · |
| b | · | · | · | ✓ | · |

## Quasi-identifier combination (k-anonymity-style singling-out) — ILLUSTRATIVE

> **ILLUSTRATIVE / methodological demonstration, not a re-identification probability.** Computed by the shared `kanon` estimator (identical to CONFIDE-Red). The personas are synthetic, so these counts show *how* a surviving quasi-identifier combination is assessed (GDPR Art-29 / k-anonymity; RU pop ≈ 146M), not a precise probability. The load-bearing signal is the **relative ranking** and the **sensitivity verdict**, not the point value.

_Naive product of per-quasi fractions assumes the quasi-identifiers are statistically independent. They are not (profession/city/age/medication correlate), so this OVERSTATES uniqueness — the real matching population is larger and the person is LESS singled out than the point estimate implies._

Direct identifiers can be perfectly masked and a person still singled out by the *combination* of surviving quasi-identifiers; an expected matching population below 1 would mean singling-out.

| Client | surviving quasi types | expected matches (illustrative) | singles out? | verdict robust to ±0.5x–2x priors? |
|---|---|--:|---|---|
| a | AGE, MEDICATION, PROFESSION | 50.1 | no | yes |
| b | AGE, LOCATION, MEDICATION, PROFESSION | 1.7 | no | **no (flips)** |

## Utility — downstream CBT-signal preservation (orig vs redacted)

Does the de-identified transcript still support the clinical analysis it exists for? We extract cognitive-distortion types from the original and the redacted text and measure the fraction of original signal preserved.

| Client | mean distortion-signal preserved |
|---|--:|
| a | 100% |
| b | 82% |

**Char-level non-PII preservation:** 99.5% of non-PII text survives redaction (the deterministic utility floor; complement of over-redaction). Computed from true per-doc character index sets — non-PII over-masking is `|MASKED \ PII|` (predicted-mask chars that are not gold-PII), so missed PII and false positives can no longer net out to a falsely perfect 100%.

_Privacy↑ and utility↑ are in tension: the same masking that lowers attacker success also risks erasing clinical signal. The default stack is tuned for recall (privacy); this table is the cost side._
