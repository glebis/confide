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

## Quasi-identifier combination (k-anonymity-style singling-out)

Direct identifiers can be perfectly masked and a person still singled out by the *combination* of surviving quasi-identifiers. Using declared, illustrative RU population fractions (pop ≈ 146M; **method demo, not census**), the surviving combination multiplies down to an expected number of matching people; below 1 means singling-out.

| Client | surviving quasi types | expected matches | singles out? |
|---|---|--:|---|
| a | MEDICATION, PROFESSION | 3504.0 | no |
| b | AGE, DATE, LOCATION, MEDICATION, PROFESSION | 8342.86 | no |

## Utility — downstream CBT-signal preservation (orig vs redacted)

Does the de-identified transcript still support the clinical analysis it exists for? We extract cognitive-distortion types from the original and the redacted text and measure the fraction of original signal preserved.

| Client | mean distortion-signal preserved |
|---|--:|
| a | 100% |
| b | 82% |

**Char-level non-PII preservation:** 100.0% of non-PII text survives redaction (the deterministic utility floor; complement of over-redaction).

_Privacy↑ and utility↑ are in tension: the same masking that lowers attacker success also risks erasing clinical signal. The default stack is tuned for recall (privacy); this table is the cost side._
