# Reconstruction & Re-identification — what survives anonymization

Default stack under test: **natasha+regex+ollama** (the RU benchmark default).
Method follows the re-identification / inference-attack literature (Staab et al.; RAT-Bench; Tau-Eval privacy–utility).

## A. Quasi-identifier survival (the re-identification surface)

An entity *survives* if **any** of its mentions is left unmasked. Direct identifiers (name/phone/email) are well masked; the danger is the quasi-identifiers that, combined, still single out a person.

| Client | Quasi-entities | Survived | Survival rate | Surviving types |
|---|--:|--:|--:|---|
| a | 11 | 3 | **27%** | MEDICATION, PROFESSION |
| b | 15 | 5 | **33%** | AGE, DATE, LOCATION, MEDICATION, PROFESSION |

## B. LLM inference attack on the *redacted* text

A local qwen model, given only the anonymized transcript (`<TAGS>` in place of PII), is asked to infer the client's attributes from remaining context.
Recovered = attribute correctly reconstructed despite redaction.

| Client | Recovered / tested | Reconstructed attributes |
|---|--:|---|
| a | 2/5 | profession, medication |
| b | 0/5 | — |

_Even a 3B local model reconstructs identity-narrowing attributes from context alone; a frontier model would recover more (the literature reports state-of-the-art tools prevent re-identification only ~27–29% of the time). Redaction of direct identifiers is necessary but not sufficient._

## C. Utility cost (over-redaction)

Under the default stack, **39 of 193** redacted spans (**20%**) were not gold PII — the readability price paid for recall. In de-id this is the cheap error (over-redaction costs readability; a miss leaks PII).

Those false-positive spans are short, so the **character-level** over-redaction is far smaller: only **0.47%** of non-PII characters are over-masked (**99.5%** non-PII char preservation, computed from true per-doc index sets as `|MASKED \ PII| / (doc_len − |PII|)` — see `privacy-utility-RESULTS.md`). The span-rate (20%) and char-rate (0.47%) are complementary views of the same over-redaction, not a contradiction: many small spurious masks, little total text lost.

