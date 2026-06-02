# CONFIDE — The Three Locks for storing session data

In physical psychotherapy, paper records are kept **behind three locks** — e.g. the
office **entrance door**, a **cabinet**, and a **safe (or second cabinet)** inside it.
No single failure exposes a client. CONFIDE applies the same defense-in-depth to digital
**RED** (raw, identifiable) transcripts: three *independent* locks, so compromising one
does not reveal the data.

> This is a confidentiality posture, not legal advice or a compliance certificate.
> It complements `ISOLATION.md` (red/green, VM, network) — that's *how data flows*; this
> is *how data rests*.

## The three locks

| Physical | Digital (CONFIDE) | What it protects against |
|---|---|---|
| 🚪 **Entrance door** | **Lock 1 — Device.** FileVault full-disk encryption ON + strong login password + short auto-lock. | A lost/stolen/booted-from-USB machine. The disk is unreadable without the password. |
| 🗄️ **Cabinet** | **Lock 2 — Encrypted store.** RED lives in a *dedicated encrypted container* (an encrypted APFS volume or a password-protected disk image), **not** loose in Documents and **never** in an iCloud/Dropbox-synced folder. | Other apps, other users, and silent cloud sync of raw transcripts. |
| 🔒 **Safe** | **Lock 3 — Per-file + isolation.** Each RED file is **sops/age-encrypted at rest** (ciphertext on disk; the age key stored *separately*), and processing happens only inside a **no-network VM/container** that emits GREEN only. | Even "inside the cabinet": the files are individually sealed, the key isn't beside them, and the data can't phone home. |

Result: to read a real transcript an attacker needs the **device password** *and* the
**encrypted-store password** *and* the **age key** — three independent secrets, ideally
held in different places.

## Storage checklist

Run through this before any real session data touches the machine:

- [ ] **Lock 1 — Device**
  - [ ] FileVault enabled (`fdesetup status`)
  - [ ] Strong login password; screen auto-locks ≤5 min; no auto-login
  - [ ] Firmware/login password not reused elsewhere
- [ ] **Lock 2 — Encrypted store**
  - [ ] RED lives in a dedicated **encrypted** volume/image (e.g. `hdiutil create -encryption AES-256 …`, or an encrypted APFS volume) — its own password
  - [ ] RED folder is **excluded from iCloud / Dropbox / any cloud sync**
  - [ ] Backups of RED are encrypted (encrypted Time Machine / no plaintext offsite)
- [ ] **Lock 3 — Per-file + isolation**
  - [ ] RED files **sops/age-encrypted** at rest (`sops --encrypt`); plaintext only in tmpfs during processing
  - [ ] age key stored **separately** from the data (not in the same folder/backup); recovery copy in a password manager
  - [ ] Anonymization runs in a **no-network** container/VM (`ISOLATION.md` Layer 2/3)
  - [ ] Only **GREEN** (reviewed, redacted) output is ever copied out or sent to a model
- [ ] **Lifecycle**
  - [ ] GREEN verified (residual re-id risk checked) before any cloud use
  - [ ] Retention limit set; **secure deletion** of RED when no longer needed (`rm -P` / encrypted-volume destroy, not Trash)
  - [ ] Consent + scope recorded (only your own / consented sessions — see `ETHICS.md`)

## What CONFIDE provides for each lock

- **Lock 1:** OS-level (FileVault) — CONFIDE just requires it; the checklist verifies it.
- **Lock 2:** the dedicated RED folder + the green/red separation in `confide redact`.
- **Lock 3:** sops/age recipe + the sealed VM/container (`ISOLATION.md`), and the
  stats-only CLI so even *processing* a real session never emits PII.

**One sentence:** raw transcripts sit behind device encryption (door), an encrypted store
(cabinet), and per-file encryption + network isolation (safe) — and only the redacted
GREEN copy is ever allowed out.
