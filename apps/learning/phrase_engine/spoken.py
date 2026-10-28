"""Живая форма фразы для показа ученику: обычные американские сокращения.

Генератор строит фразу в полной форме (I am, do not), и проверка ответа сравнивает
именно её. Ученику же образец и карточки показываются так, как говорят в жизни:
I'm, don't, isn't, there's. Проверка (phrase_checker.normalize) раскрывает
сокращения, поэтому ответ засчитывается в любой из двух форм.

Сокращаются только формы из phrase_checker.CONTRACTIONS. В конце фразы
(Yes, I am.) и перед местоимением (Where is it?) сокращения нет: так не говорят.
"""
from __future__ import annotations

import re

# не + глагол → n't (am not не сокращается: I'm not — см. ниже)
NEGATIVE = {
    "is": "isn't", "are": "aren't", "was": "wasn't", "were": "weren't",
    "do": "don't", "does": "doesn't", "did": "didn't",
    "will": "won't", "must": "mustn't",
}
# местоимение + be / will
SUBJECT_BE = {
    ("i", "am"): "I'm", ("you", "are"): "you're", ("we", "are"): "we're", ("they", "are"): "they're",
    ("he", "is"): "he's", ("she", "is"): "she's", ("it", "is"): "it's", ("that", "is"): "that's",
    ("there", "is"): "there's",
}
SUBJECT_WILL = {"i": "I'll", "you": "you'll", "he": "he'll", "she": "she'll",
                "we": "we'll", "they": "they'll", "it": "it'll"}
WH_IS = {"what": "what's", "where": "where's", "who": "who's"}
PRONOUNS = {"i", "you", "he", "she", "it", "we", "they"}

_TOKEN = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?|[^A-Za-z\s]+|\s+")


def _match_case(src: str, out: str) -> str:
    if out.startswith("I'") or out == "I":
        return out
    return out[:1].upper() + out[1:] if src[:1].isupper() else out


def spoken(text: str) -> str:
    """Полная форма → живая форма с сокращениями. Пробелы и пунктуация сохраняются."""
    parts = _TOKEN.findall(text or "")
    words = [i for i, p in enumerate(parts) if p[:1].isalpha()]

    def low(k):
        return parts[words[k]].lower() if 0 <= k < len(words) else None

    def followed_by_word(k):
        """После слова k идёт ещё слово той же фразы (а не конец фразы)."""
        if k + 1 >= len(words):
            return False
        between = "".join(parts[words[k] + 1:words[k + 1]])
        return between.strip() == ""

    out = {}      # индекс слова → новое написание ("" — слово убрано)
    k = 0
    while k < len(words):
        a, b = low(k), low(k + 1)
        joined = followed_by_word(k)
        if a == "cannot":
            out[k] = _match_case(parts[words[k]], "can't")
        elif joined and b == "not" and a in NEGATIVE:
            out[k] = _match_case(parts[words[k]], NEGATIVE[a])
            out[k + 1] = ""
            k += 1
        elif joined and (a, b) in SUBJECT_BE and followed_by_word(k + 1) and (b == "am" or low(k + 2) != "not"):
            # I am not → I'm not; he is not → he isn't (это сделает правило для «is not» на следующем слове)
            out[k] = _match_case(parts[words[k]], SUBJECT_BE[(a, b)])
            out[k + 1] = ""
            k += 1
        elif joined and a in SUBJECT_WILL and b == "will" and followed_by_word(k + 1) and low(k + 2) != "not":
            out[k] = _match_case(parts[words[k]], SUBJECT_WILL[a])
            out[k + 1] = ""
            k += 1
        elif joined and a in WH_IS and b == "is" and followed_by_word(k + 1) and low(k + 2) not in PRONOUNS:
            out[k] = _match_case(parts[words[k]], WH_IS[a])
            out[k + 1] = ""
            k += 1
        k += 1

    result = []
    for i, p in enumerate(parts):
        if p[:1].isalpha():
            k = words.index(i)
            if k in out:
                if out[k] == "":
                    # убираем слово вместе с пробелом перед ним
                    if result and result[-1].isspace():
                        result.pop()
                    continue
                result.append(out[k])
                continue
        result.append(p)
    return "".join(result)
