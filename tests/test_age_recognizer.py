"""TDD for the RU spelled-out AGE recognizer (confide ru_age module).

AGE is one of the 0-deterministic-recall quasi types the benchmark surfaced.
Russian ages are spelled-out cardinals anchored to год/года/лет via a pronoun /
возраст cue or an "N лет + person" form. The trap is relative-time / duration
expressions ("пять лет назад", "двадцать лет вместе") which must NOT be ages.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                "skills", "session-anonymizer", "scripts"))
import ru_age


def _ages(text):
    return {text[s.start:s.end] for s in ru_age.find_ages(text)}


def test_cardinal_phrase_with_goda():
    assert "тридцать четыре" in _ages("Мне тридцать четыре года, а стою у окна")


def test_cardinal_phrase_with_let_and_person():
    assert "сорок пять" in _ages("смешно — сорок пять лет мужику, а он")


def test_vozrast_anchor():
    assert "двадцать девять" in _ages("Возраст — двадцать девять, то есть 29?")


def test_pronoun_predicate_age():
    assert "сорок один" in _ages("сейчас мне сорок один и всё то же")


def test_pronoun_short_predicate_age():
    # "Ему двенадцать." — number as predicate, followed by clause boundary.
    assert "двенадцать" in _ages("Ему двенадцать. Они в одном классе")


def test_bare_duration_is_not_an_age():
    assert _ages("Двадцать лет всё то же самое") == set()
    assert _ages("Отца нет семь лет уже") == set()


def test_pronoun_counting_a_noun_is_not_age():
    # "дал ей ОДИН проект" / "сто РАЗ" — the number counts a noun, not an age.
    assert _ages("просто дал ей один проект на неделю") == set()
    assert _ages("Артём мне сто раз говорил об этом") == set()


def test_relative_time_ago_is_not_age():
    assert _ages("это было пять лет назад, давно") == set()


def test_in_n_years_is_not_age():
    assert _ages("через три года всё изменится") == set()


def test_unrelated_number_words_not_matched():
    assert _ages("встретимся через тридцать минут у входа") == set()
