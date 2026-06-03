# Security & Responsible Disclosure

CONFIDE is a privacy tool for vulnerable people's data, so "security" here means two
things at once:

1. **Classic software security** — a bug in the code, dependencies, or container.
2. **Privacy / de-identification failures** — a way the anonymizer leaks PII it should
   have removed, or a re-identification technique that recovers a person from redacted
   output. For this project, a de-id leak *is* a security vulnerability.

We take both seriously and we'd rather hear about a problem privately than read about it
in a public issue.

## Report privately — please do not open a public issue

Use **GitHub's private vulnerability reporting** for this repository:
**Security → Report a vulnerability** (Security Advisories) at
<https://github.com/glebis/confide/security/advisories/new>.

If that is unavailable, email the maintainer: **glebis@gmail.com** with `CONFIDE
SECURITY` in the subject. PGP available on request.

### What to include

- What you found and why it matters (code bug, de-id leak, or re-id technique).
- A **minimal reproduction on synthetic data** — the command, the synthetic input (or a
  pointer to a corpus document), expected vs actual, and your environment (OS, Python,
  model versions). The detector manifests (`caches/detector-cache/*.manifest.json`)
  carry code/data SHAs that help us reproduce.

### What to **never** include in any report, issue, or PR

- **Real personal data.** No real transcripts, names, phones, emails, IDs, or any PII —
  reproduce on synthetic data instead (see `CONTRIBUTING.md` §"Ground rules").
- **A re-identification recipe against real people.** If your finding is an attack
  technique, describe it against the *fabricated personas* in this repo, not a real
  individual. We headline recall (a miss is a leak) precisely so attacks can be discussed
  as measurements, not as instructions. See `docs/ETHICS.md` on dual-use.

## Our commitment

- We aim to **acknowledge within 7 days** and give an initial assessment within 30 days.
  This is a volunteer / citizen-science project, not a funded lab — timelines are
  best-effort, and we'll tell you honestly where things stand.
- We will **fix before we publicize.** For a de-id leak that affects users in the field,
  we will ship a fix (or a documented mitigation) before describing the leak in detail.
- We will **credit you** for the report unless you prefer to stay anonymous
  (see `CONTRIBUTORS.md`).
- We practice **coordinated disclosure** in the spirit of NIST SP 800-216: triage →
  fix/mitigate → disclose, with a reasonable embargo so people relying on CONFIDE in real
  clinical settings are not left exposed.

## Scope

In scope: the anonymizer (`skills/session-anonymizer/`), the evaluation/red-team code
(`src/confide_eval/`), the CLI (`confide.py`), the benchmark gold and tooling, the Docker
image, and dependencies as shipped.

Out of scope: third-party model providers (OpenAI, Ollama models, etc.) — report those to
the provider; vulnerabilities that require committing real PII to reproduce (don't — find
a synthetic repro or describe it abstractly in a private report).

> Reminder: passing CONFIDE-Bench is **not** a HIPAA / GDPR / 152-ФЗ anonymization
> certificate. Even "green" output needs human review before any cloud use. See
> `DISCLAIMER.md`.
