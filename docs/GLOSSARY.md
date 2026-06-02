# CONFIDE Glossary · Глоссарий

Bilingual EN↔RU glossary of the de-identification, NLP, and data-protection
terms used across CONFIDE (annotation tool, codebook, benchmark, reports).
It is the canonical reference for terminology — the Russian UI of
`tools/annotator.html` uses the same terms.

Двуязычный глоссарий терминов деидентификации, NLP и защиты персональных данных,
используемых в CONFIDE (инструмент разметки, кодбук, бенчмарк, отчёты).
Это нормативный справочник по терминологии — русскоязычный интерфейс
`tools/annotator.html` использует те же термины.

> Convention / Соглашение: canonical schema tokens (`PERSON`, `direct`,
> `quasi`, `entity_id`, `person_role`, harm levels, …) stay in English in
> both languages; only the human-readable display text is translated.
> Канонические токены схемы остаются на английском в обоих языках —
> переводится только отображаемый текст.

---

## Core privacy / data-protection terms · Базовые понятия защиты данных

### PII — Personally Identifiable Information
**RU:** персональные данные (ПДн); персонально идентифицируемая информация

- **EN:** Any information that can identify a specific living person, either on
  its own (a full name, phone number, passport number) or in combination with
  other data (a city + profession + age). In Russian law the operative term is
  **«персональные данные (ПДн)»** as defined by **152-ФЗ**.
- **RU:** Любые сведения, позволяющие установить личность конкретного
  физического лица — самостоятельно (ФИО, номер телефона, паспорт) или в
  сочетании с другими данными (город + профессия + возраст). В российском
  праве используется термин **«персональные данные (ПДн)»** (152-ФЗ);
  английское *PII* ему примерно соответствует. **Не путать** с
  «идентифицирующей» — правильно: персонально *идентифицируемая* информация.
- **Примеры / Examples:** имя «Алина», телефон +7 916…, email, адрес,
  дата рождения, диагноз в сочетании с местом работы.

### De-identification — Деидентификация / обезличивание
- **EN:** The overall process of removing or transforming PII from a document
  so the person can no longer be readily identified.
- **RU:** Процесс удаления или преобразования персональных данных таким
  образом, чтобы личность человека нельзя было без труда установить. В
  юридическом и нормативном контексте РФ предпочтителен термин
  **«обезличивание»** (152-ФЗ); «деидентификация» — технический калькированный
  термин, принятый в профессиональной среде NLP и информационной безопасности.

### Anonymization — Анонимизация
- **EN:** De-identification strong enough that re-identification is no longer
  reasonably possible (irreversible). The high bar of GDPR Recital 26.
- **RU:** Обезличивание, при котором повторная идентификация практически
  исключена и **необратима**. Высокий стандарт GDPR (рец. 26). Принципиально
  отличается от юридического «обезличивания» по 152-ФЗ степенью
  необратимости — в GDPR анонимизированные данные перестают быть
  персональными.

### Pseudonymization — Псевдонимизация
- **EN:** Replacing identifiers with pseudonyms/codes; reversible if you hold
  the key. Reduces risk but data is still "personal" under GDPR.
- **RU:** Замена идентификаторов псевдонимами/кодами; **обратима** при наличии
  ключа. Снижает риск, но данные остаются персональными (GDPR, ст. 4).

### Redaction / Masking — Сокрытие / маскирование данных
- **EN:** The concrete edit that hides a span — deleting it, blacking it out,
  or replacing it with a tag like `[PERSON]`. Masking = replacing with a
  placeholder of the same type.
- **RU:** Конкретная операция, скрывающая фрагмент: удаление, «вымарывание»
  или замена меткой вида `[PERSON]`. **Маскирование** — замена заменителем
  (плейсхолдером) того же типа. *(Важно: не «редактирование» — это
  ложный друг переводчика; «редактировать» по-русски означает
  литературную правку текста.)*

### Re-identification — Повторная идентификация / реидентификация
- **EN:** Recovering the person's identity from supposedly de-identified data,
  e.g. by combining quasi-identifiers or linking to an external dataset.
- **RU:** Восстановление личности из якобы обезличенных данных — например,
  через сочетание квазиидентификаторов или сопоставление с внешним набором
  данных.

---

## Identifier types · Типы идентификаторов

### Direct identifier — Прямой идентификатор (`direct`)
- **EN:** Identifies a person on its own: full name, phone, email, passport/ID.
- **RU:** Идентифицирует человека сам по себе: ФИО, телефон, email, паспорт/ID.

### Quasi-identifier — Квазиидентификатор (`quasi`)
- **EN:** Does not identify alone, but can in combination (city, age,
  profession, dates). The main driver of re-identification risk.
- **RU:** Сам по себе не идентифицирует, но идентифицирует **в сочетании**
  (город, возраст, профессия, даты). Главный источник риска повторной
  идентификации.

### Confidential / sensitive attribute — Конфиденциальный (чувствительный) атрибут
- **EN:** A sensitive fact about the person (diagnosis, sexual orientation,
  religion) that must be protected even when not itself an identifier. Maps to
  GDPR Art. 9 "special categories".
- **RU:** Чувствительный факт о человеке (диагноз, сексуальная ориентация,
  вероисповедание), подлежащий защите даже в тех случаях, когда сам по себе
  не является идентификатором. Соответствует понятию «специальные категории
  персональных данных» (GDPR ст. 9, 152-ФЗ).

### GDPR special category / 152-ФЗ — Специальные категории персональных данных
- **EN:** Health, sex life, religion, ethnicity, biometrics, etc. — extra-protected
  categories under GDPR Art. 9 and 152-ФЗ. Therapy transcripts are full of them.
- **RU:** Сведения о состоянии здоровья, сексуальной жизни, вероисповедании,
  национальности, биометрические данные и др. — категории, пользующиеся
  усиленной защитой по GDPR (ст. 9) и 152-ФЗ (ст. 10). Транскрипты
  психотерапевтических сессий практически целиком состоят из таких данных.

---

## Annotation / NLP terms · Термины разметки и NLP

### Named entity (recognition / NER) — Именованная сущность (распознавание именованных сущностей)
- **EN:** A real-world object referred to by name (person, place, organization,
  date…). NER is the task of automatically finding and typing them.
- **RU:** Объект реального мира, названный по имени (человек, место,
  организация, дата…). **NER** — задача их автоматического поиска и
  определения типа.

### Span — Фрагмент (спан)
- **EN:** A contiguous stretch of text (character offset `start`–`end`) marked
  as one annotation. In CONFIDE every PII mention is a span.
- **RU:** Непрерывный участок текста (смещения символов `start`–`end`),
  отмеченный как одна единица разметки. В интерфейсе используется
  **«фрагмент»**; в NLP-среде также говорят **«спан»**. В CONFIDE каждое
  упоминание ПДн — это фрагмент.

### Annotation — Разметка
- **EN:** Labeling text spans with categories (here: PII type, identifier
  class, harm, role, entity id). An *annotator* is a person doing this.
- **RU:** Присвоение фрагментам текста категориальных меток (здесь: тип ПДн,
  класс идентификатора, степень вреда, роль лица, entity id). Человек,
  выполняющий разметку, — **аннотатор** (также: разметчик).

### Person role — Роль лица (`person_role`)
- **EN:** Whose identity a span reveals: client, partner, relative, friend,
  clinician, third party, institution.
- **RU:** Чью личность раскрывает фрагмент: клиент, партнёр, родственник, друг,
  терапевт / специалист, третье лицо, организация / учреждение.

### Entity id — `entity_id`
- **EN:** A stable label tying together all mentions of the *same* real person
  or thing, so co-reference is preserved (same person → same id).
- **RU:** Устойчивая метка, связывающая все упоминания **одного и того же**
  человека или объекта (один человек → один id); сохраняет кореференцию.

### Gold standard — Эталонная разметка (золотой стандарт)
- **EN:** The reference annotation, adjudicated by experts, against which models
  and annotators are scored.
- **RU:** Разметка, согласованная экспертами и принятая в качестве эталона,
  относительно которого оцениваются модели и аннотаторы. Калькированный термин
  «золотой стандарт» широко используется и считается допустимым.

### Inter-annotator agreement (IAA) — Межаннотаторное согласие
- **EN:** How much independent annotators agree, beyond chance. Measures label
  quality and codebook clarity.
- **RU:** Степень совпадения оценок независимых аннотаторов за вычетом
  случайного совпадения. Характеризует качество разметки и чёткость кодбука.
  Используемые синонимы: «межэкспертная согласованность»,
  «межразметчиковое согласие».

### Cohen's / Fleiss' kappa — Каппа Коэна / каппа Флейса
- **EN:** Chance-corrected agreement statistics. **Cohen's κ** for two
  annotators, **Fleiss' κ** for three or more.
- **RU:** Статистики согласия с поправкой на случайность. **Каппа Коэна** —
  для двух разметчиков, **каппа Флейса** — для трёх и более.

---

## Re-identification risk (GDPR Art-29 / WP216) · Риски повторной идентификации

### Singling-out — Выделение индивида
- **EN:** Being able to isolate one individual (or their record) within a
  dataset, even without a name.
- **RU:** Возможность выделить одного человека (или его запись) в наборе данных,
  даже без имени.

### Linkability — Связываемость
- **EN:** Being able to link two records about the same person across datasets.
- **RU:** Возможность связать две записи об одном человеке между разными
  наборами данных (связываемость записей).

### Inference (attack) — Атака на основе вывода атрибутов (инференс)
- **EN:** Deducing a sensitive attribute about a person with significant
  probability from other data.
- **RU:** Восстановление чувствительного атрибута человека с высокой
  вероятностью на основе косвенных данных. В отечественной литературе по
  защите данных также встречается как «вывод атрибутов» или «атака
  инференса».

---

## Evaluation metrics · Метрики оценки

### Entity-level recall — Полнота на уровне сущностей
- **EN:** Of all PII *entities* in the gold standard, the fraction the system
  caught. Entity-level (not character/token-level) is what matters for leakage.
- **RU:** Доля сущностей — носителей ПДн — из эталонной разметки, которые
  система обнаружила. Именно уровень сущностей (а не символов или токенов)
  имеет значение для оценки риска утечки данных. При оценке отдельных
  упоминаний используется «полнота на уровне упоминаний».

### Harm-weighted recall — Полнота, взвешенная по степени вреда
- **EN:** Recall where each missed entity is weighted by its harm level, so
  missing a `critical` identifier costs more than missing a `low` one.
- **RU:** Полнота, при вычислении которой каждая пропущенная сущность
  взвешивается по степени вреда: пропуск идентификатора уровня `critical`
  обходится значительно дороже, чем пропуск `low`.

---

## Harm levels · Степени вреда

`critical` — критический · `high` — высокий · `medium` — средний · `low` — низкий

The harm level encodes how damaging a leak of this span would be to the person.
Степень вреда отражает потенциальный ущерб субъекту персональных данных в случае утечки данного фрагмента.
