<!-- Deep-research brief via ChatGPT Deep Research (~11 min, 55 citations, 520 searches),
     2026-06-04, for CONFIDE. Inline citation tokens stripped; verify sources before relying. -->

# CONFIDE Research Brief

## Executive synthesis

For **CONFIDE**, the strongest evidence points to a clear architecture choice: use a **hybrid, local-first pipeline** rather than a single off-the-shelf de-identification tool. In the surveyed landscape, open and commercial systems cluster into three families: **pattern/rule engines** for structured identifiers, **NER pipelines** for names/locations/organizations, and **LLM or encoder-based systems** for broader contextual masking. The most reusable general framework is **Microsoft Presidio** because it is explicitly designed to combine recognizers, swap NLP backends, add new languages, and integrate external models. By contrast, **Philter** is highly specialized for **English clinical notes** and is built around English POS tagging, English-oriented regex/safe lists, and a Stanford NER setup, making it a poor primary choice for Russian. 

The most important gap is also the one CONFIDE is targeting. The survey surfaced **Russian conversational PII benchmarks** such as **Jay Guard NER Benchmark** and **PII-Bench (ru)**, and it surfaced **clinical de-identification benchmarks** such as **n2c2/i2b2** and **MEDDOCAN**, and **re-identification-risk benchmarks** such as **RAT-Bench** and **SPIA**. But I did **not** find an open benchmark or toolkit that simultaneously covers **Russian + psychotherapy/coaching conversation + explicit re-identification evaluation**. That absence is not trivial: therapy transcripts are unusually rich in **indirect identifiers**, and recent work on LLM privacy shows that simple masking can still leave enough context for attribute inference or subject-level identification. 

The practical recommendation is therefore: make **Presidio the orchestration layer**, put **Russian-native recognizers and regexes** behind it, and add a **local LLM or encoder rewrite layer** only after deterministic masking has already removed obvious identifiers. Use **Philter only as an English clinical baseline** if you want a comparison point on English medical-style notes; do not make it core to the Russian stack. For benchmarking, combine **span-level detection**, **subject/attribute-inference red-teaming**, and **domain-specific utility checks**. 

## Tools for de-identification and anonymization

The table below focuses on tools that are most relevant to a **local-first transcript de-id stack** and to the **Russian + English** problem. “Maturity” is deliberately qualitative and based on the evidence available in the consulted documentation, repositories, releases, and product docs.

| Tool | Languages and RU relevance | Approach | Clinical or therapy fit | License / deployment / maturity | Notes for CONFIDE |
|---|---|---|---|---|---|
| **Microsoft Presidio** | Default config is English; docs explicitly support adding new languages by configuring another NLP engine plus language-specific recognizers. Russian is feasible through custom spaCy/Stanza/transformers/GLiNER backends and Russian recognizers. | Hybrid: regex, deny lists, rule-based recognizers, context enhancement, NER backends, external recognizers, anonymizer operators. | General-purpose, but it also ships medical/clinical entities via `MedicalNERRecognizer` and supports Azure/AHDS clinical integrations. Not therapy-specific. | Open-source project with active docs, samples, and March 2026 releases; local Python/Docker deployment is first-class. Exact repo license was not re-verified in the consulted pages. | Best **framework** choice, especially if you want one bilingual pipeline with pluggable recognizers. |
| **Philter** | English-centered by design; no Russian support is documented, and code/config strongly suggest English assumptions. | Rule-heavy clinical de-id: regex filters, POS-based logic, whitelist/safelist patterns, optional Stanford NER. | Yes—specifically free-text **clinical notes** and i2b2-style workflows. Not therapy-conversation specific. | Open-source package with PyPI packaging and modest but real community footprint; exact license was not re-verified in the consulted sources. | Useful as an **English clinical baseline**, not as the backbone of a Russian system. |
| **MIST** | MITRE describes it as a machine-learning de-identification toolkit for tailoring to document types; the consulted source does not document multilingual or Russian support. | ML-based de-identification toolkit. | Yes—medical/medico-legal de-id. | Open-source, legacy-but-important clinical toolkit. | Good historical baseline for clinical de-id research; not obviously a strong Russian-fit. |
| **scrubadub** | Supports localization and some region-specific detectors, but bundled capabilities are mostly English/US/GB/CA oriented; Russian is not a documented strong point. | Detector-based scrubbing with regex and optional extras such as spaCy and Stanford detectors. | No clinical specialization. | Apache-2.0; mature lightweight OSS library with 12 releases, latest in Sept 2023. | Good lightweight baseline for structured/global PII, but not enough for Russian therapy transcripts alone. |
| **DataFog** | Local regex-first screening with optional spaCy and GLiNER; docs mention explicit locale handling such as German structured PII. No Russian specialization is documented in the consulted README. | Regex core plus optional NER/GLiNER/OCR/Spark. | No clinical specialization. | MIT; emerging lightweight SDK oriented toward LLM guardrails and local screening. | Attractive for a fast structured-PII prefilter, but you would still need Russian NER/custom recognizers. |
| **John Snow Labs Spark NLP Healthcare DeIdentification** | Product demo explicitly shows de-identification for English, Spanish, French, Italian, Portuguese, Romanian, and German; Russian is not listed. | Clinical NLP pipeline with PHI-aware de-identification and surrogate replacement. | Yes—strong clinical focus. | Commercial/proprietary healthcare stack. | Strong if you needed multilingual **clinical** de-id in supported European languages, but it does not solve Russian. |
| **AWS Comprehend PII / Comprehend Medical** | General PII detection is documented for **English and Spanish**; Comprehend Medical is described for clinical text but the consulted AWS pages do not advertise Russian support. | Managed ML APIs for PII and PHI extraction/redaction. | Medical product is clinical; not therapy-specific. | Proprietary cloud service. | Not a fit for a strict local-first Russian stack. |
| **Google Sensitive Data Protection** | Strong de-identification product, but the consulted docs do not publish a clean natural-language coverage matrix for Russian transcript PII. | Discovery, classification, and de-identification with built-in infoTypes and templates. | General-purpose, not therapy-specific. | Proprietary cloud service. | Operationally mature, but not ideal for local-first psychotherapy transcripts. |
| **Limina / Private AI** | Docs state **49+ / 50+ languages**, with **52-language marketing claims**, code-switching support, and container/on-prem deployment; Russian is included in the supported-language docs. | Context-aware entity detection and de-identification over text, files, images, and audio; can redact, mask, or replace with synthetic values. | Covers PII, PHI, and PCI, but not specifically therapy. | Commercial container-based engine deployable in your environment. | The strongest commercial **local/on-prem multilingual** option in this survey. |
| **Jay Guard** | Russian-language product docs describe PII finding/masking for LLM traffic, including names, email, phone numbers, IPs, and custom filtering. | Gateway/guardrail with configurable filtering and reversible replacement before cloud LLM calls. | Not clinical-specific; oriented to prompt protection and operational controls. | Commercial/proprietary. | Relevant as a Russian guardrail product reference, especially for LLM ingress/egress. |

Two observations matter most for CONFIDE. First, in open source, the **toolkit with the best extensibility story is Presidio**, not because it is the best Russian detector out of the box, but because it is the cleanest **host framework** for combining regexes, NER backends, and anonymization operators. Second, most **clinical de-id tools are still English-first or Western-European-language-first**, while the few **Russian** assets are mostly either **general conversational NER benchmarks** or **guardrail products**, not full therapy-grade de-identification systems. 

## Benchmarks, datasets, and privacy-attack frameworks

A strong CONFIDE benchmark should distinguish between **detection quality** and **residual re-identification risk**. The survey suggests that most older benchmarks emphasize span detection, while the most useful recent work is moving toward **attacker-centric evaluation**.

### Core de-identification and PII benchmarks

| Benchmark / dataset | Domain | Languages | Covers Russian | Covers clinical or therapy conversation | Why it matters |
|---|---|---|---|---|---|
| **TAB — Text Anonymization Benchmark** | European Court of Human Rights cases | English | No | No | Includes semantic categories, masking decisions, confidential attributes, and co-reference; useful for anonymization beyond simple NER. |
| **n2c2 / i2b2 2014 de-id** | Longitudinal clinical narratives | English | No | Clinical yes; therapy conversation no | Still the canonical open clinical de-id benchmark family. |
| **MEDDOCAN** | Clinical case reports / medical document anonymization | Spanish | No | Clinical yes; therapy no | Strong non-English clinical de-id benchmark; useful pattern reference for multilingual clinical annotation design. |
| **AI4Privacy PII-Masking 200k / 2M European** | Synthetic broad-domain PII | Multilingual; 2M European release advertises 32 locales and 98 entity types | Likely not Russian in the 32-locale European set as described; no Russian focus | No | Useful for training/evaluating broad multilingual PII masking, especially synthetic data generation. |
| **Jay Guard NER Benchmark** | Conversational text, work chats, customer support, spoken transcripts | Russian | Yes | Not clinical/therapy | Captures noisy Russian conversational PII detection, but mainly for person, geopolitics, and street addresses. |
| **PII-Bench (ru)** | Synthetic realistic Russian deployment scenarios across 9 domains | Russian | Yes | Not clinical/therapy | Especially valuable because it is **span-level** and designed to evaluate **whole pipelines**, including Presidio-like systems and regexes, not just BIO-tagging models. |
| **PIIBench** | Unified multi-source PII corpus across ten datasets | Multi-source / multilingual mix | Not Russian-focused in the published abstract | Mixed, but not therapy-specific | Important 2026 benchmark because it demonstrates how badly systems degrade out of distribution; the abstract reports all published systems below 0.14 F1 on the unified corpus. |

Two recent Russian resources deserve special attention. **Jay Guard NER Benchmark** gives you genuine **Russian conversational noise**, which is useful for chats, support logs, and transcript-like language, but it covers only a narrow slice of entity types. **PII-Bench (ru)** is broader and, importantly, is built for **end-to-end evaluation** of recognizers and regexes via exact spans rather than only token-tagging metrics; it includes identifiers such as **name, phone, email, address, bank card, CVC, INN, KPP, OGRN, OGRNIP, SNILS, passport number, and token/API key**. That makes it immediately useful for benchmarking a Russian de-id pipeline’s “obvious identifier” layer. 

### Re-identification and privacy-attack evaluation

| Framework / paper | What it evaluates | Relevance to CONFIDE |
|---|---|---|
| **Staab et al., Violating Privacy via Inference with LLMs** | Whether LLMs can infer personal attributes from text even without direct memorization; finds common protections such as text anonymization and model alignment insufficient in many settings. | Essential conceptual basis for CONFIDE’s red-team: direct masking alone is not enough. |
| **Anonymeter** | Attack-based privacy risk for **synthetic tabular data**, including singling out, linkability, and inference. | Not text-native, but useful for threat-model vocabulary and for structured metadata associated with transcripts. |
| **Text Re-Identification / TRIR** | Automated re-identification attacks on anonymized documents to quantify disclosure risk. | Very relevant model for document-level re-id risk evaluation after de-identification. |
| **RAT-Bench** | A 2026 benchmark for text anonymization based on **re-identification risk**, using direct and indirect identifiers, multiple domains and languages, and an LLM-based attacker. | One of the closest public precedents to the kind of red-team CONFIDE should implement. |
| **SPIA — Subject-level PII Inference Assessment** | Shifts evaluation from spans to **people/subjects** and asks whether personal information remains inferable; shows that >90% span masking can still leave low subject-level protection. | Extremely relevant to therapy transcripts, where identity leaks through relationships and narrative context rather than only direct spans. |
| **Membership inference on de-identified clinical notes** | 2024 study reports that de-identification of real clinical notes did not protect against membership inference attacks. | Direct warning that “PHI removed” does not imply safe downstream model training or release. |

The key lesson from the re-identification literature is that **span recall is necessary but not sufficient**. A system can score highly on direct identifier masking while still leaving enough contextual residue for **attribute inference**, **subject identification**, or **membership inference**. For psychotherapy and coaching data, that risk is amplified because sessions often contain unusual combinations of **family structure, occupation, migration history, diagnoses, rare events, locations, and timelines**. Recent mental-health privacy work explicitly flags therapy transcripts and recordings as containing PII and sensitive attributes that can be inferred from text and audiovisual traces. 

## Russian-specific tooling and the main gap

The Russian NLP stack is usable, but it is **not enough on its own** for psychotherapy de-identification.

| Russian-oriented asset | What it offers | Limitation for CONFIDE |
|---|---|---|
| **Natasha** | Production-minded Russian NLP toolkit covering tokenization, segmentation, morphology, syntax, NER, and fact extraction; CPU-friendly. | Natasha explicitly warns that models are optimized for **news articles** and quality may be lower in other domains. |
| **Slovnet** | Compact Russian NER/morphology/syntax models; Russian NER model is small and fast on CPU. | Trained on **news** and standard PER/LOC/ORG labeling; not a PII-specific or therapy-specific system. |
| **spaCy `ru_core_news_lg`** | Mature Russian pipeline with NER, vectors, and self-reported NER F-score 0.953; sources include Nerus/Navec. | General Russian NER; no PII ontology, no therapy tuning. |
| **Stanza Russian** | Russian NER support is documented; the NER table reports Russian WikiNER F1 of 92.9. | Good general NER, but still not therapy-specific or PII-specific. |
| **DeepPavlov Russian NER** | Offers multiple Russian models, including conversational ones such as `ner_rus_convers_distilrubert_2L` and `ner_rus_convers_distilrubert_6L`, with reported F1 92.9 and 96.7 on Collection-rus. | This is closer to transcript/chat language than news, but still mostly generic NER rather than full de-id coverage. |
| **Jay Guard NER Benchmark** | Russian conversational anonymization benchmark from chats, customer support, and spoken transcripts. | Limited entity scope; not clinical/therapy. |
| **PII-Bench (ru)** | Broader Russian PII benchmark with IDs, contact info, government/business identifiers, and chat/dialog domains. | Not medical or therapy-specific; synthetic and evaluation-only. |
| **Jay Guard product** | Russian-oriented masking/filtering gateway for LLM traffic. | Operationally useful, but not a full therapy transcript benchmark/toolkit. |

The best open Russian building blocks today are therefore a **mix**: use **DeepPavlov conversational NER** or a Russian transformer/GLiNER model for **person/location/organization-like mentions**, use **Natasha/Slovnet/spaCy/Stanza** as lightweight alternatives or ensemble members, and use **custom regex recognizers** for Russian structured identifiers such as **passport numbers, SNILS, INN, OGRN, OGRNIP, KPP, phone formats, card numbers, CVCs, emails, and URLs**. PII-Bench (ru) is especially useful because its entity inventory already overlaps heavily with the Russian structured-ID layer you would need in production. 

The most important gap remains unchanged after the survey: I found **Russian conversational PII** resources and **clinical de-id** resources and **re-id-risk** resources, but no open resource that combines **all three** of the following in one benchmark or toolkit: **Russian language, psychotherapy/coaching conversation, and explicit residual re-identification measurement**. The nearest therapy-adjacent public dataset I found is **MentalChat16K**, which combines synthetic counseling data with **anonymized English transcripts** from behavioral-health interventions; it is useful as evidence that mental-health dialogue datasets exist, but it does not solve Russian de-id evaluation. 

## Microsoft Presidio in depth

Presidio’s architecture is well aligned with CONFIDE’s requirements because it separates **analysis** from **anonymization**. The **Analyzer** runs multiple recognizers—regex-based, rule-based, deny-list, context-enhanced, or model-backed—and returns scored spans. The **Anonymizer** then applies operators such as masking or replacement to the detected spans. Presidio’s own docs emphasize that the analyzer can combine predefined recognizers with custom recognizers and external models, and that its NLP layer is replaceable. 

Presidio also has unusually strong **language extensibility**. Its multi-language documentation states that the default configuration is English, but that supporting another language requires two things: **an NLP engine for that language** and **recognizers adapted or created for that language**. The docs are explicit that regexes are mostly language-agnostic, while **context words are not**, so recognizers need language-specific context terms to get good scores. The docs also show how to register multiple language models in one configuration and how to map model labels to Presidio entity names via `model_to_presidio_entity_mapping`. 

That means **yes, Presidio can realistically run on Russian**, but not “magically” and not at high quality without customization. The practical routes are:

1. **spaCy or Stanza as the NLP engine**. Presidio’s NlpEngine can load arbitrary spaCy/Stanza models per language; by direct extension of the documented configuration pattern, a Russian model such as `ru_core_news_lg` or a Russian Stanza model can be attached as the `ru` backend. spaCy’s Russian model is a full NER pipeline sourced from Nerus/Navec, and Stanza documents an official Russian NER model. 

2. **Transformers or GLiNER as external recognizers**. Presidio documents both a transformers-based NLP engine and the ability to run transformers, Flair, SpanMarker, GLiNER, or remote services as additional recognizers. That is particularly important for Russian because it lets you wrap a stronger Russian or multilingual PII model without forking Presidio itself. 

3. **Custom regex/pattern recognizers for Russian IDs**. Presidio’s supported-entities page shows that many of its strongest built-in recognizers are pattern/checksum/context based. But the same page does **not** list Russian-specific identifiers such as **SNILS, INN, OGRN, OGRNIP, KPP, or Russian passport formats**. So for Russian, Presidio would contribute its recognizer framework and detection pipeline, but you would need to add Russian-specific recognizers yourself. 

In practice, that means Presidio’s **most reliable immediate value on Russian** is the **structured identifier layer**: email, URL, IP, MAC, card-like strings, phone numbers, dates, and custom Russian government/business IDs expressed with regexes, checksums, and localized context words. Its value for **names, locations, and organizations** depends on the plugged-in Russian NER model. That can be quite good on ordinary named entities, but there are two quality caveats. First, several mainstream Russian models in the open ecosystem are trained on **news corpora** rather than psychotherapy dialogue. Natasha explicitly warns about cross-domain degradation, and Slovnet states its compact NER is trained on news with standard PER/LOC/ORG labels. Second, general NER models do not directly solve therapist-specific or coaching-specific identity leakage such as **nicknames, kinship relations, rare biography fragments, occupational identifiers, or indirect location narratives**. 

Presidio’s **medical/clinical support** is real but should not be over-interpreted for Russian. The supported-entities page documents a `MedicalNERRecognizer` backed by the default Hugging Face model `blaze999/Medical-NER`, with clinical entities such as disease/disorder, medication, procedure, event, and biological attribute. But the consulted documentation does **not** document Russian clinical coverage for that recognizer. For CONFIDE, that means Presidio’s clinical extension is useful as an English clinical component or as an architecture example, not as evidence of a ready-made Russian psychotherapy model. 

My assessment is therefore straightforward: **Presidio should play a central role in CONFIDE**, but as an **orchestrator and recognizer framework**, not as the source of Russian therapy intelligence by itself. Its strengths are **modularity, local deployment, mixed recognizers, per-language configuration, and anonymization operators**. Its weakness on your problem is that **Russian therapy-specific semantics and indirect identifiers are outside its default envelope**. 

## Philter in depth

Philter is much more specialized. Its README describes it as a **command-line clinical text de-identification** tool for plain-text notes, with default workflows built around **i2b2 notes and annotations** and evaluation against that format. In other words, Philter is not a generic multilingual PII framework: it is a **clinical-note de-id system** with strong assumptions about the target corpus and workflow. 

The code-level evidence shows that Philter is **English-oriented by design**. The implementation imports **NLTK**, **WordNetLemmatizer**, and **StanfordNERTagger**, and its POS functions call `nltk.pos_tag(...)`, which is the classic English POS tagging path in NLTK. Its preprocessing functions use Latin-centric regexes such as `[^a-zA-Z0-9]`, and multiple parts of the code strip tokens with `re.sub(r"[^a-zA-Z0-9]+", "",...)`. The Stanford NER wiring also references an English classifier path. 

The configuration reinforces the same conclusion. The default `philter_delta.json` is filled with large numbers of **English clinical safe-pattern files** and domain-specific rules—for example entries titled **“hearing safe,” “HENT safe,” “medical safe,” “md safe,” “ordering md safe,” “ROS safe,”** and many address/hospital regexes. That is useful in English clinical notes because it protects high-frequency clinical phrases from being over-masked, but it is exactly the sort of rule inventory that does **not** transfer well to Russian psychotherapy transcripts. 

Could Philter contribute anything to Russian? Only in a limited sense. Conceptually, it offers a design pattern for a **rule-heavy, precision-focused clinical baseline**. In principle, one could replace its tokenization assumptions, POS tagging, NER backend, regex sets, “safe” dictionaries, and evaluation corpus, but by the time you have done that, you have effectively built a new system. In practical engineering terms, **Philter should be treated as English-only for this use case**. If you want it in CONFIDE at all, the right role is as a **baseline comparator on English medical-style notes**, not as a production component for Russian or bilingual therapy transcripts. 

## Recommended architecture for CONFIDE

The highest-confidence recommendation is a **four-layer bilingual stack**.

### Detection layer

Use **Presidio as the top-level analysis and anonymization framework**. For **Russian structured PII**, implement custom Presidio recognizers for **passport, SNILS, INN, OGRN, OGRNIP, KPP, bank-card/CVC patterns, Russian phone formats, email, URLs, IPs, and dates**, and localize all context words. Benchmark this layer first against **PII-Bench (ru)** because that dataset already contains a close match to many of those entity types and is explicitly designed for evaluating whole pipelines and regex-based systems. 

For **Russian names/locations/organization-like mentions**, plug in a stronger Russian backend behind Presidio. If you want lightweight classical NLP, start with **spaCy `ru_core_news_lg`**, **Stanza Russian**, or **Natasha/Slovnet**; if you want transcript-like language, **DeepPavlov’s conversational Russian NER models** are the most obviously relevant open option among the surveyed sources. Because therapy transcripts contain nicknames, partial names, and colloquial speech, I would treat generic NER as a **high-recall candidate generator** rather than a final authority. 

For **English**, Presidio can run closer to its intended path. If you want a clinical English baseline, compare **Presidio + English clinical recognizers** to **Philter** on English note-style text. That gives you a good reference point for how much purely rule-heavy clinical engineering buys you over a flexible hybrid framework. 

### Contextual rewrite layer

Add a **local LLM or encoder-based rewrite pass only after first-pass masking**. The recent privacy literature is clear that direct de-identification alone may not prevent **attribute inference** or **subject-level inference**. Therefore the second pass should focus on **indirect identifiers**: rare occupations, unique migration histories, unusual family constellations, small-town references, institution names, specific event chains, and other biography-like cues that ordinary NER misses. The rewrite layer should not see raw obvious identifiers if you can avoid it; it should see already-sanitized text and be tasked with **meaning-preserving paraphrase or surrogate replacement**. 

### Benchmark layer

CONFIDE’s benchmark should combine three axes:

| Axis | Suggested source or model |
|---|---|
| **Direct-identifier detection** | PII-Bench (ru), Jay Guard NER Benchmark, n2c2/i2b2, MEDDOCAN, AI4Privacy synthetic corpora. |
| **Residual inference / re-identification risk** | RAT-Bench-style attackers, SPIA-style subject-level inference, TRI/TRIR-style document re-identification, Staab-style attribute inference prompts. |
| **Utility preservation** | Task-specific measures for summarization quality, session-structure retention, speaker-role preservation, and clinically relevant semantics. The motivation comes from the privacy/utility trade-off literature and from therapy-domain concerns in mental-health AI. |

### Product decision on Presidio and Philter

For a **Russian therapy de-id stack**, the clearest division of labor is:

- **Presidio**: yes, as the **core runtime** and evaluation harness for text spans, recognizer composition, operator-based anonymization, multilingual routing, and local deployment. 
- **Philter**: no, as a Russian core component; yes only as an **English clinical baseline** or inspiration for precision-oriented safelists in English medical notes. 

That architecture is, in my view, the most practical and rigorous path to a **local-first, bilingual, therapy-aware de-identification benchmark and toolkit**.

## Open questions and limitations

A few points remain genuinely incomplete in the public record I reviewed. Exact license metadata for some open-source tools, especially **Presidio** and **Philter**, was not clearly exposed in the consulted documentation pages, so I have avoided guessing. Some commercial products, especially cloud APIs, also do not expose a single transparent table for **Russian natural-language coverage** in the consulted docs, so I have reported only what the documentation clearly states. 

The evidence base is also uneven across domains. Canonical clinical de-id datasets such as **i2b2/n2c2** and **MEDDOCAN** remain important, but they are not recent and they are not psychotherapy-conversation datasets. The more recent benchmarks that emphasize **re-identification risk**—especially **RAT-Bench** and **SPIA**—are closer to what CONFIDE needs conceptually, but they are not Russian therapy resources either. That is exactly why the core niche for CONFIDE appears to be real rather than incremental. 