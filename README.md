```
  ____ ___  _   _ _____ ___ ____  _____
 / ___/ _ \| \ | |  ___|_ _|  _ \| ____|
| |  | | | |  \| | |_   | || | | |  _|
| |__| |_| | |\  |  _|  | || |_| | |___
 \____\___/|_| \_|_|   |___|____/|_____|
```

# CONFIDE

**Conf**idential **F**iltering of **I**dentifying **De**tails (Locked) — the CON·F·I·DE spelling.

> *"Confide in me."* — Kylie Minogue, *Confide in Me* (1994)

> "in the name of understanding a problem should be shared"

---

CONFIDE is a **local-first, privacy-first** toolkit and benchmark for de-identifying
**psychotherapy and coaching session transcripts** — and for measuring how well that
de-identification actually holds up against re-identification. Everything runs on your
own machine; raw client data never leaves it.

The premise: to *understand* a problem with AI, the transcript has to be shared with a
model — so first it must be made safe to share. CONFIDE both does that (the anonymizer)
and tells you, honestly, when it isn't enough (the benchmark + the attacks).

## The three parts

| Part | What it is | Where |
|---|---|---|
| **CONFIDE** | The layered, local de-identification stack: deterministic regex (emails/phones/IDs/dates) → Russian NER (Natasha) → optional OpenAI Privacy Filter → local LLM (Qwen via Ollama/llama.cpp) for medications, ages, professions, contextual IDs. | `skills/session-anonymizer/` |
| **CONFIDE-Bench** | A bilingual **RU + EN** psychotherapy-transcript de-identification **benchmark** — a layered-detector ablation scored the way the field does (recall-first / entity-level / direct vs quasi-identifier), plus a privacy–utility axis. To our knowledge the first therapy-*dialogue* de-id benchmark. | `eval/BENCHMARK.md` |
| **CONFIDE-Red** | The **red team**: LLM-based **re-identification / de-anonymization** attacks on the redacted output — single-session inference, longitudinal cross-session linkage, quasi-identifier singling-out — aligned with the GDPR Art-29 attack taxonomy (singling-out / linkability / inference) and the Staab et al. / RAT-Bench inference-attack literature. | `eval/*_attack.py`, `eval/privacy_utility_eval.py` |

CONFIDE *protects*; CONFIDE-Red *attacks* — measuring what survives so "we removed the
names" is never mistaken for "this is safe to send to the cloud."

## Headline findings

- **Some PII only an LLM catches** — medications, ages, professions, contextual dates are
  ~0% for regex + NER; only the local LLM layer recovers them.
- **Removing direct identifiers is necessary but not sufficient** — quasi-identifiers
  survive and an LLM attacker can still infer attributes, especially across multiple
  sessions of the same person.
- **Bigger isn't automatically better** — a one-line date regex recovered a heavy
  transformer's entire Russian advantage at ~500× the speed.

## Reproducibility & ethics

Pinned environment + Docker (`eval/Dockerfile`, `eval/requirements.lock`), an append-only
run registry (`eval/runs/`), and full docs: `eval/REPRODUCIBILITY.md`, `eval/ETHICS.md`,
`eval/DATASHEET.md`, `eval/EXPLAINER.md`.

> ⚠️ All transcripts in this repository are **synthetic** (fictional clients). Real client
> data never enters it and must not. CONFIDE-Red attacks run only against fabricated
> personas. Benchmark performance is **not** HIPAA or GDPR anonymisation certification.

CONFIDE grew out of the *Psychodemia · AI & Mental Health* masterclass (31 May 2026); the
original masterclass materials are in `README-masterclass.md`.
