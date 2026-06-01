---
name: session-anonymizer
description: Three-layer PII anonymization for session transcripts (therapy, coaching, consulting, mentoring). Runs Natasha (Russian NER), a deterministic regex layer (scrubadub + libphonenumber), and a local LLM (Ollama) in sequence for maximum coverage. Fully local by default. This skill should be used when anonymizing session transcripts, notes, or any text containing client PII before AI analysis. Triggers on "anonymize", "redact PII", "anonymize session", "protect client data", "strip personal data", "anonymize transcript".
---

# Therapy Anonymizer

Three-layer PII detection and anonymization for therapy session transcripts. Supports Russian and English. Fully local by default — no data leaves the machine.

## Architecture

Three detection layers run in sequence, each catching what others miss:

| Layer | Tool | Catches | Size | Speed |
|-------|------|---------|------|-------|
| 1 | Natasha | Russian names, locations, organizations | 27 MB | instant |
| 2 | Regex (scrubadub + libphonenumber) | Emails, URLs, phones, structured IDs (policy/account/card) | ~10 MB | instant |
| 3 | Ollama LLM | Medications, dates, contextual IDs | 2.5-7 GB | ~10s |

Spans from all layers are merged, overlaps resolved, and a unified redacted output is produced.

## Prerequisites

One command installs all three layers (idempotent):

```bash
./setup.sh
```

Manual equivalent:

```bash
pip install -r requirements.txt                 # Layers 1 & 2: Natasha, scrubadub, phonenumbers
ollama pull qwen2.5:3b                           # Layer 3: local LLM (verified default model)
```

Each layer is optional — the script gracefully skips unavailable layers and warns. Layers 1 and 2
are lightweight (tens of MB, instant); only Layer 3 (the Ollama model) needs real RAM, so there is
no memory contention. `--layers natasha,regex` gives a fast, fully deterministic pass with no LLM.

## Usage

### Single file

```bash
python3 scripts/anonymize.py session.txt
```

### Stdin pipe

```bash
cat session.txt | python3 scripts/anonymize.py
```

### Batch processing

```bash
python3 scripts/anonymize.py --batch ~/sessions/ -o ~/sessions_clean/
```

### JSON report

```bash
python3 scripts/anonymize.py session.txt --json
```

### Pseudonyms instead of tags

```bash
python3 scripts/anonymize.py session.txt --pseudonyms
```

### Select layers / model

```bash
# Fast — Natasha only
python3 scripts/anonymize.py session.txt --layers natasha

# Fast deterministic pass — names + emails/phones/IDs, no LLM
python3 scripts/anonymize.py session.txt --layers natasha,regex

# LLM only — maximum coverage
python3 scripts/anonymize.py session.txt --layers ollama --model qwen2.5:3b
```

### Encrypt output (AES-256)

```bash
python3 scripts/anonymize.py session.txt -o clean.txt --encrypt "password"
```

## Invoking from an agent (Claude Code / Codex)

Run from the installed skill folder (`~/.claude/skills/session-anonymizer` or
`~/.agents/skills/session-anonymizer`), or use the absolute path to `scripts/anonymize.py`.
To anonymize text already in context, pipe it through the script:

```bash
echo '<text>' | python3 scripts/anonymize.py --json
```

For files, pass the path directly. Always recommend manual review after automated anonymization.

## Limitations

- Contextual identifiers ("the only red-haired architect in Kostroma") are NOT detected by any automated tool
- Layer 2 is deterministic: it catches emails, URLs, phones (region RU), and grouped numeric IDs — but NOT spelled-out digits ("семь-семь-два-два"); those fall to Layer 3 / manual review
- Medications detected only by Layer 3 (requires Ollama)
- Does not assess re-identification risk from combinations of non-PII fields

## Guardrails

- NEVER send raw transcripts to cloud services
- Cloud verification only on already-anonymized text
- Always recommend manual review for therapy data
- Never log original PII values

## Learnings

### 2026-05-31
- **OPF replaced by a deterministic regex layer.** OpenAI Privacy Filter was the wrong tool for Layer 2: a 2.8 GB transformer running *per-line* inference on CPU (~2s/line → 338s and still unfinished on a 10 KB transcript), and with `--json-indent 0` it emitted multiple concatenated JSON objects that broke the single `json.loads` in `run_opf`, silently returning zero entities. Layer 2's targets (emails, URLs, phones, structured IDs) are format-bound, so the replacement is deterministic: scrubadub detectors for email/URL, Google libphonenumber (`PhoneNumberMatcher(text, "RU")`) for phones, and a regex for grouped numeric IDs. Full 3-layer run dropped from "never finishes" to ~16s; Layer 2 itself is instant (the ~2.5s seen is one-time scrubadub import). `opf` remains a deprecated `--layers` alias mapping to `regex`.
- **No more memory contention.** Layers 1 and 2 are tens of MB, so the old "OPF + Ollama can't coexist on 16 GB" workaround (unloading the model after Ollama) was removed.

### 2026-05-05
- **Qwen2.5:3b is the right default model** — no thinking overhead, 2s response, 8/8 with medication prompt. Qwen3 4B returns empty content via Ollama chat API on longer prompts due to thinking mode.
- **Memory contention on 16 GB**: OPF (2.8 GB) + Ollama model cannot coexist. Run `--layers natasha,ollama` for max coverage or `--layers natasha,opf` for deterministic-only. All 3 layers need 32 GB.
- **Medication prompt is critical**: "Include MEDICATIONS with dosages as PII (they narrow identity)" is what takes any LLM from 7/8 to 8/8. No dedicated PII tool catches medications.
- **OPF `redact` subcommand required**: `opf` alone doesn't work, must use `opf redact --device cpu --format json`.
- **Russian morphology breaks text matching**: LLM returns "Москва" but text has "Москве" (prepositional case). Stem matching fallback needed.
- **Ollama API**: use `/api/chat` not `/api/generate`. The generate endpoint returns empty for Qwen2.5 on complex prompts.
