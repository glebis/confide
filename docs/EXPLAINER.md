# What CONFIDE-Bench Measures — in Plain Language

A graded explainer (ELI5 → ELI14) plus ready-to-paste blurbs for science blogs,
magazines, and psychology outlets. Everything below describes a benchmark built on
**fictional, synthetic** therapy sessions — no real patients.

---

## ELI5 (≈age 5)

Imagine you draw a picture of your day and want to show it to a robot helper, but
first you cover up your name and your phone number with stickers so the robot can't
tell it's *you*. This project is a **sticker-checking game**: it tests how good
different robots are at finding all the things that should get a sticker — and
whether they accidentally cover up the important parts of the story too.

## ELI8 (≈age 8)

When someone talks to a therapist, they say private things — their name, their town,
their doctor, what medicine they take. If a computer is going to help read those
notes, it first has to **hide the private bits** (this is called "anonymizing"). But
hiding is tricky:

- Easy stuff: a phone number or an email always *looks* like a phone number or email,
  so a simple rule can catch it.
- Hard stuff: "I'm the only puppet-maker in my small town" has **no** name in it — but
  it could still tell people exactly who you are.

CONFIDE-Bench is a **scorecard** that checks how many private bits a computer catches, how
many it misses, and whether it accidentally erases the parts a therapist still needs.

## ELI11 (≈age 11)

De-identification means removing the clues that reveal *who* someone is. There are two
kinds of clues:

1. **Direct identifiers** — a name, phone, email, ID number. One of these alone points
   to you.
2. **Quasi-identifiers** — your age, your job, your city, your employer. Each one is
   shared by lots of people, but **stack three or four together** and only one person
   matches.

CONFIDE-Bench tests a "team" of computer tools working together: a rule-checker for
patterns (phones, emails), a name-finder for Russian, an AI model, and a small local
language model (an LLM) for the trickier clues. The scorecard answers three questions:

- **Did we catch the private stuff?** (we count misses — a miss is a leak)
- **Did we erase too much?** (covering up real therapy content is its own cost)
- **Could someone still guess who it is** from what's left? (we let an AI try)

It works in **both Russian and English** — important because almost all such tests
exist only for English, and mostly for hospital notes, not therapy conversations.

## ELI14 (≈age 14)

CONFIDE-Bench is a **benchmark** — a standardized test — for *de-identifying psychotherapy
transcripts* in Russian and English. It measures a layered system where each "layer"
catches different things, and it scores them the way privacy researchers do:

- **Recall is king.** Missing a piece of private information is a privacy breach;
  over-covering a non-private word only hurts readability. So the headline metric
  weights *catching everything* more than *being tidy*.
- **All mentions, not just the first.** If your name appears five times and the tool
  masks four, you still leak. An identity counts as "protected" only if *every* mention
  is hidden.
- **Direct vs. quasi.** The benchmark separately tracks the obvious identifiers and the
  combine-to-reveal ones, because the quasi-identifiers are where de-identification
  quietly fails.

**Three findings worth knowing:**

1. **Some private things only an LLM can catch.** A rule can spot a phone number, and a
   name-finder can spot "Marina." But a *medication name*, a *spoken-aloud age*, or a
   *job title* needs a model that understands meaning. In our current RU test those
   types stay near-zero for the rule-and-name-finder layers; the LLM improves them but
   still does not solve them.
2. **Small deterministic fixes still matter.** Numeric dates and structured IDs are
   better handled by deterministic rules than by a heavy model: they are faster,
   reproducible, and easy to audit. Bigger is not automatically better.
3. **Removing names is necessary but not sufficient.** Even after the best scrub, about
   a quarter to a third of the *quasi*-identifiers survive, and a small AI "attacker"
   can sometimes still infer details (a medication, a profession) from what's left.
   Meanwhile ~90%+ of the clinical signal (the cognitive patterns a therapist would
   analyze) is preserved — so you *can* anonymize and still do the analysis, but you
   should measure the leftover risk, not assume it's gone.

**Honest caveats** (the boring-but-important part): the data is synthetic and small, so
treat the exact numbers as directional; the gold-standard labels were checked against a
second independent annotator (substantial agreement, but not yet a full double pass);
and passing this test is **not** legal anonymization under HIPAA or GDPR.

---

## Ready-to-paste blurbs

**One-liner (tweet/abstract):**
> CONFIDE-Bench is the first public Russian+English benchmark for scrubbing private details
> from *therapy* conversations — measuring not just whether names get removed, but
> whether someone could still be re-identified, and whether the therapeutic meaning
> survives. Synthetic data; recall-first; the quasi-identifiers are where it gets hard.

**Magazine paragraph (general science):**
> Before an AI can help summarize a therapy session, the private details have to be
> stripped out. That sounds simple — delete the names and phone numbers — but the real
> danger hides in combinations: your age, job, city and employer can single you out even
> with every name gone. CONFIDE-Bench is a new open benchmark that tests how well a stack of
> tools (pattern rules, a name-finder, and a local AI model) does exactly this on
> *fictional* therapy transcripts in Russian and English. Its sharpest lesson: removing
> the obvious identifiers is the easy 80%; the leftover "quasi-identifiers" are what let
> a curious model still guess who you are — so privacy has to be *measured*, not assumed.

**Psychology-outlet framing:**
> Therapists increasingly want to use AI to review sessions, supervise, or spot patterns
> — but session transcripts are among the most sensitive text that exists. CONFIDE-Bench
> asks a practical question: can you de-identify a therapy transcript *and still keep
> what matters clinically*? On synthetic sessions it finds that good anonymization
> preserves ~90% of the cognitive-distortion signal a clinician would analyze, while
> still leaving real re-identification risk from indirect details (a rare profession, a
> small city, a medication). The takeaway for practice: "we removed the names" is not
> the same as "this is safe to send to the cloud" — the residual risk is checkable, and
> should be checked.

**Methods-blog one-paragraph:**
> CONFIDE-Bench evaluates a layered, *local-first* de-identification stack (regex +
> Russian NER + the OpenAI Privacy Filter + a local qwen LLM, composed by span-union)
> with the metrics de-id research expects: recall-weighted F2, entity-level all-mention
> recall (TAB), direct/quasi split, a top-k re-identification attack, k-anonymity-style
> combination risk, and a downstream clinical-utility check (Tau-Eval style). Gold is
> checked against an independent GPT-5 seed annotation (Cohen's κ ≈ 0.79; not human IAA). It is a focused,
> reproducible teaching/research benchmark — explicitly not a compliance certification.
