# External session sources (links & licenses only — data NOT in this repo)

Real/realistic therapy, counseling and coaching session data used to *calibrate* the
RU side of CONFIDE-Bench. **None of the actual transcripts live in this repository.**
They are staged locally outside the repo (`~/ai_projects/confide-data/external-sessions/`,
gitignored by being outside the tree) because of license and consent constraints. This
file records only where each source came from, its license, and its consent status, so
the provenance is reproducible without redistributing sensitive content.

> Staged corpus snapshot: **3,647 sessions / 53,511 turns / ~7.2 M chars**, normalized
> to a speaker-turn JSONL schema and deduped by content hash. 3,640 EN, **7 real RU**.

## English — open datasets

| Source | Link | License | Modality | Kind |
|---|---|---|---|---|
| AnnoMI (133 MI convos, expert-annotated) | https://github.com/uccollab/AnnoMI · https://huggingface.co/datasets/to-be/annomi-motivational-interviewing-therapy-conversations | OpenRAIL | Motivational interviewing | demo-transcribed |
| Counsel-Chat (Amod mirror) | https://huggingface.co/datasets/Amod/mental_health_counseling_conversations | "other" (public posts) | Counselor Q&A | real (public forum) |
| ESConv | https://huggingface.co/datasets/thu-coai/esconv | **CC-BY-NC-4.0 (non-commercial)** | Emotional support | role-play (crowdworkers) |
| ZahrizhalAli MH conversational | https://huggingface.co/datasets/ZahrizhalAli/mental_health_conversational_dataset | MIT | MH chat | synthetic |

## English — published reference transcripts (local research use)

| Source | Link | License / consent | Modality | Kind |
|---|---|---|---|---|
| Rogers–Gloria (1965) | Brodley transcript PDF (anamartinspsicoterapiaacp.files.wordpress.com) | "research/teaching, may not be sold"; film © Psychological Films 1965 | Person-centered | real (published film) |
| Beck Institute — Abe S2 / S10 | beckinstitute.org/.../BB3-Session-2 / -10-Annotated-Transcript.pdf | **© Beck Institute — local research use only, do not redistribute** | CBT | role-play (composite client) |

## Russian — consented public demo sessions (auto-captions, local only)

ASR auto-captions pulled with `yt-dlp` (no audio/video stored, no whisper). One line per
video. Consent is "public demo" — **verify the on-page statement before any reuse**.
~319,638 chars (~493 min) across CBT/REBT/person-centered/gestalt/ICF-coaching.

| YouTube id | Modality | Uploader | ~min |
|---|---|---|---|
| Q6C2FvcwyYU | REBT/CBT | PsychoPadve | 65 |
| -aKA9s2mmmE | CBT | PsychoPadve | 41 |
| yOILw3AZNHI | person-centered | AURUM | 46 |
| _kWWCw6agXg | gestalt | Лев Черняев | 47 |
| 272AhSkQCfE | ICF coaching | SLAcademy | 37 |
| pplJR5WCvEQ | ICF coaching | Erickson International | 119 |
| kPsIB0XIoCY | ICF coaching | Erickson Kharkov | 138 |

Unavailable at fetch time (private/removed): `qXZt04FoWgg`, `5eQP8le_Js4`, `5EdnR4CcjY8`, `xp_yZ9c3YPU`.

Real-client podcast noted but **not ingested** (audio, sensitive): libo/libo
«Хорошо, что вы это сказали» — consented real sessions (podcast.ru/1500763929).

## Ethics & licensing summary

- **Do not commit any of this transcript content to a public repo.** ESConv is
  non-commercial; Beck/Rogers are copyrighted; RU captions are YouTube-ToS with
  unverified per-video consent.
- Use is **local calibration only** — informing RU PII patterns (names, ages,
  professions, medications) and stress-testing the anonymizer against real text. The
  shipped RU benchmark gold remains fully synthetic.
