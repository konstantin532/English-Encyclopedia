"""Сверка CEFR учебных единиц с официальным списком «The Oxford 3000 by CEFR level (American English)».

Сам список в проект не входит (это материал Oxford University Press). Скачайте PDF
с oxfordlearnersdictionaries.com и превратите в текст, например: pdftotext файл.pdf oxford3000.txt

Запуск:
    uv run python scripts/check_cefr_oxford3000.py oxford3000.txt          # отчёт
    uv run python scripts/check_cefr_oxford3000.py oxford3000.txt --write  # вписать уровни в YAML

Скрипт сверяет пару «слово + часть речи». Oxford даёт уровень для слова в целом,
поэтому подтверждение записывается как partial: значение отдельно не проверяется.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEVELS = ("A1", "A2", "B1", "B2")
POS_START = r"(n\.|v\.|adj\.|adv\.|prep\.|pron\.|det\.|conj\.|exclam\.|number|modal|auxiliary|indefinite|definite|linking|ordinal)"
# Учебная категория → обозначения части речи в списке Oxford
CATEGORY_POS = {
    "S": ["n."], "D": ["v.", "modal v.", "auxiliary v."], "J": ["adj."], "A": ["adv."], "N": ["number"],
    "T": ["det.", "pron.", "article", "det./pron."], "P": ["prep."], "X": ["adv.", "prep."],
    "C": ["conj."], "O": ["exclam."], "F": ["adv.", "exclam."],
}


def parse_list(path: Path) -> dict[str, list[tuple[str, str]]]:
    index: dict[str, list[tuple[str, str]]] = {}
    level = None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line in LEVELS:
            level = line
            continue
        if not level or not line or line.startswith("©"):
            continue
        head = re.split(rf"\s+(?={POS_START})", line)[0]
        word = re.sub(r"\d", "", head).split(" (")[0].split(",")[0].strip().lower()
        index.setdefault(word, []).append((level, line))
    return index

def matches_category(entry: str, category: str) -> bool:
    """Only distinct POS abbreviations, not 'n.' buried in 'pron.' etc."""
    terms = CATEGORY_POS.get(category, [])
    return any(re.search(r"(?<![A-Za-z])" + re.escape(term) + r"(?![A-Za-z])", entry, re.I)
               for term in terms)


def unambiguous_hit(hits, category: str):
    possible = [hit for hit in hits if matches_category(hit[1], category)]
    return possible[0] if len({hit[0] for hit in possible}) == 1 and possible else None


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    index = parse_list(Path(sys.argv[1]))
    write = "--write" in sys.argv
    unit_re = re.compile(r"  - uid: (LX-\d{5})\n(.*?)(?=\n  - uid: |\Z)", re.S)
    problems = 0
    for path in sorted((ROOT / "content" / "seed_lexicon").glob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        new_text = text
        for m in unit_re.finditer(text):
            uid, body = m.group(1), m.group(2)
            lemma = re.search(r"lemma: \"?([^\"\n]+)\"?", body).group(1).strip().lower()
            code = re.search(r"class: ([A-Z])", body).group(1)
            hits = index.get(lemma, [])
            match = unambiguous_hit(hits, code)
            if not match:
                problems += 1
                print(f"{uid} {lemma}: нет в Oxford 3000 для этой части речи ({hits or 'слова нет'})")
                continue
            level, entry = match
            print(f"{uid} {lemma}: {level} — «{entry}»")
            if write:
                note = f"Oxford 3000 (American English): {entry} — {level}. Уровень дан для слова, значение отдельно не сверялось"
                new_body = re.sub(r"cefr: \S+", f"cefr: {level}", body, count=1)
                new_body = re.sub(r"verification_note: .*", lambda _: "verification_note: " + json.dumps(note, ensure_ascii=False), new_body, count=1)
                if "verification_status:" in new_body:
                    new_body = re.sub(r"verification_status: \S+", "verification_status: partial", new_body, count=1)
                else:
                    new_body = new_body.replace(f"cefr: {level}", f"cefr: {level}\n    verification_status: partial", 1)
                new_text = new_text.replace(body, new_body, 1)
        if write and new_text != text:
            path.write_text(new_text, encoding="utf-8")
    print(f"\nНе найдено: {problems}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
