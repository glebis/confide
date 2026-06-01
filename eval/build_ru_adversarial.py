#!/usr/bin/env python3
"""Build a Russian ADVERSARIAL robustness probe for the de-id stack.

Short therapy-style snippets, each planting PII in a *hard* form the main eval
under-covers (drawn from the JayGuard / PII-Bench RU observations in the research):
patronymics, Latin transliteration, diminutives, messenger handles, Russian
structured IDs (SNILS/INN/passport), abbreviated addresses, and code-switching.

Gold is exact: each planted PII string is located by substring search (snippets are
hand-authored, so offsets are unambiguous). Output mirrors the main dataset schema
so run_detectors.py / score_bench.py work unchanged.

Output: ../sessions-ru/pii-adversarial-ru.jsonl
Each entity carries `adversarial` = the robustness dimension it probes.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "sessions-ru", "pii-adversarial-ru.jsonl")

# (text, [(pii_substring, CANON_type, identifier_class, dimension)])
SNIPPETS = [
    ("К: Меня по отчеству зовут — Сергей Анатольевич, как отца.",
     [("Сергей Анатольевич", "PERSON", "direct", "patronymic")]),
    ("К: Коллеги в чате пишут меня латиницей, Sergey Volkov, мне неприятно.",
     [("Sergey Volkov", "PERSON", "direct", "transliteration")]),
    ("К: Мама зовёт меня Серёжа, а на работе — Сергей Анатольевич.",
     [("Серёжа", "PERSON", "direct", "diminutive"),
      ("Сергей Анатольевич", "PERSON", "direct", "patronymic")]),
    ("К: Жена — Светка, для всех Светлана Игоревна.",
     [("Светка", "PERSON", "direct", "diminutive"),
      ("Светлана Игоревна", "PERSON", "direct", "patronymic")]),
    ("К: Он скинул мне в телеге, @seryoga_real, я даже отвечать не стал.",
     [("@seryoga_real", "URL", "direct", "telegram_handle")]),
    ("К: Она написала в ВК, vk.com/id4815162, и я понял, что это конец.",
     [("vk.com/id4815162", "URL", "direct", "vk_handle")]),
    ("К: Дал ему свой t.me/marina_v, теперь жалею.",
     [("t.me/marina_v", "URL", "direct", "telegram_link")]),
    ("К: В поликлинике попросили СНИЛС — 112-233-445 95, я растерялся.",
     [("112-233-445 95", "ID", "direct", "snils")]),
    ("К: ИП оформил, ИНН теперь 503012345678, и сразу тревога.",
     [("503012345678", "ID", "direct", "inn")]),
    ("К: Паспорт 4509 123456 я при ней назвал вслух, до сих пор стыдно.",
     [("4509 123456", "ID", "direct", "passport")]),
    ("К: Живу на ул. Тверская, д. 12, кв. 47 — рядом с её домом.",
     [("ул. Тверская, д. 12, кв. 47", "LOCATION", "direct", "address_abbrev")]),
    ("К: Переехали в г. Кострому, мкр. Заволжский, и стало только хуже.",
     [("Кострому", "LOCATION", "quasi", "city_inflected"),
      ("Заволжский", "LOCATION", "quasi", "district")]),
    ("К: Брат, Alexey, живёт in Moscow, работает в Сбере — мы с ним не разговариваем.",
     [("Alexey", "PERSON", "direct", "codeswitch_name"),
      ("Moscow", "LOCATION", "quasi", "codeswitch_city")]),
    ("К: Написал бывшей на почту marina.volkova@yandex.ru, ответа нет.",
     [("marina.volkova@yandex.ru", "EMAIL", "direct", "email")]),
    ("К: Звонил с другого номера, 8 (916) 555-21-43, она не взяла.",
     [("8 (916) 555-21-43", "PHONE", "direct", "phone_formatting")]),
    ("К: Тимлид, Пал Палыч, опять при всех — я будто снова маленький.",
     [("Пал Палыч", "PERSON", "direct", "colloquial_patronymic")]),
]


def main():
    rows = []
    for i, (text, items) in enumerate(SNIPPETS):
        spans = []
        for sub, typ, cls, dim in items:
            idx = text.index(sub)
            spans.append({"start": idx, "end": idx + len(sub), "type": typ,
                          "value": sub, "identifier_class": cls,
                          "entity_id": f"adv-{i}-{dim}", "adversarial": dim,
                          "llm_required": False})
        rows.append({"doc_id": f"ru-adv-{i:02d}", "lang": "ru", "client": "adv",
                     "session": i, "split": "adversarial", "text": text, "spans": spans})

    with open(OUT, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    by_dim = {}
    for r in rows:
        for s in r["spans"]:
            by_dim[s["adversarial"]] = by_dim.get(s["adversarial"], 0) + 1
    print(f"[adv] wrote {len(rows)} snippets, {sum(len(r['spans']) for r in rows)} gold spans -> {os.path.relpath(OUT)}")
    print(f"[adv] dimensions: {dict(sorted(by_dim.items()))}")


if __name__ == "__main__":
    main()
