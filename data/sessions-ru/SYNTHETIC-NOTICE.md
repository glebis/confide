# ⚠️ SYNTHETIC DATA — read this

**Every transcript in this directory is AI-generated and fictional.** The clients
(Марина, Игорь, Алина, Роман, Вера, Тимур …), their names, contact details, employers,
diagnoses, medications, and life events are **invented for benchmarking de-identification**.

- **Not real people.** No real patient, client, or session is represented here.
- **Not clinical records** and **not therapeutic advice.**
- All personally-identifying values are fabricated so they can be used as a public test set
  for PII detection without exposing anyone.

Real or consented session data is **never** committed to this repository — it is processed
only locally and stats-only (see `docs/ETHICS.md`, `docs/THREE-LOCKS.md`, root `DISCLAIMER.md`).

The `ANSWER-KEY.md` in each client folder lists the planted PII (the gold standard); the
machine-readable gold is `pii-eval-ru.jsonl`.
