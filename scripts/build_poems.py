"""Генератор стихов A1 (seed_poems): разметка из словаря курса, IPA из ipa_us со слабыми формами, строка ударений. Запуск: .venv/bin/python scripts/build_poems.py"""
import os, re, sys, yaml
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
import django; django.setup()
from apps.lexicon.models import LexicalUnit as L

TAG, IPA = {}, {}
for u in L.objects.select_related("semantic_class__category").exclude(unit_type="phrase"):
    tag = f"{u.semantic_class.category.code}{u.semantic_class.number}"
    for w in [u.lemma, *(u.forms or [])]:
        TAG.setdefault(w.lower(), tag)
    IPA.setdefault(u.lemma.lower(), u.ipa_us.strip("/"))
EXTRA = {"here": ("A3", "hɪr"), "good": ("J3", "ɡʊd"), "who": ("T9", "hu"), "what": ("T9", "wʌt"),
         "morning": ("S7", "ˈmɔrnɪŋ"), "day": ("S7", "deɪ"), "nice": ("J3", "naɪs"), "thank": ("O2", "θæŋk"),
         "again": ("A2", "əˈɡɛn"), "sorry": ("O2", "ˈsɑri"), "please": ("O8", "pliz"), "yes": ("O4", "jɛs"),
         "no": ("O4", "noʊ"), "one": ("N1", "wʌn"), "two": ("N1", "tu"), "three": ("N1", "θri"), "ten": ("N1", "tɛn"),
         "seven": ("N3", "ˈsɛvən"), "eight": ("N3", "eɪt"), "eleven": ("N3", "ɪˈlɛvən"), "happy": ("J4", "ˈhæpi"),
         "say": ("D5", "seɪ"), "says": ("D5", "sɛz"), "that": ("T2", "ðæt"), "this": ("T2", "ðɪs"), "family": ("S1", "ˈfæməli"),
         "tea": ("S3", "ti"), "coffee": ("S3", "ˈkɔfi"), "night": ("S7", "naɪt"), "photo": ("S2", "ˈfoʊt̬oʊ"),
         "hello": ("O1", "həˈloʊ"), "to": ("P2", "tu"), "and": ("C1", "ænd"), "the": ("T1", "ði"), "a": ("T1", "eɪ"), "an": ("T1", "æn"), "at": ("P3", "æt"), "for": ("P5", "fɔr"), "on": ("P1", "ɑn"), "in": ("P1", "ɪn"), "is": ("D1", "ɪz"), "are": ("D1", "ɑr"), "am": ("D1", "æm"), "do": ("D1", "du"), "does": ("D1", "dʌz"), "can": ("D7", "kæn"), "not": ("X1", "nɑt"), "my": ("T3", "maɪ"), "your": ("T3", "jʊr"), "our": ("T3", "ˈaʊɚ"), "he": ("T8", "hi"), "she": ("T8", "ʃi"), "where": ("A6", "wɛr"), "why": ("A6", "waɪ"), "meet": ("D2", "mit"), "i": ("T8", "aɪ"), "it": ("T8", "ɪt"), "you": ("T8", "ju")}
for w, (tg, ip) in EXTRA.items():
    TAG.setdefault(w, tg); IPA.setdefault(w, ip)
NAMES = {"anna": "ˈænə", "tom": "ˈtɑm", "mia": "ˈmiə", "box": "ˈbɑks", "rose": "ˈroʊz"}
TAGFIX = {"anna": "S1", "tom": "S1", "mia": "S1", "rose": "S1", "park": "S4", "street": "S4",
          "post": "S4", "office": "S4", "open": "J2", "says": "D5", "can": "D7", "do": "D1", "does": "D1",
          "have": "D1", "has": "D1", "is": "D1", "am": "D1", "are": "D1", "right": "A3", "thanks": "O2",
          "thank": "O2", "again": "A2", "sorry": "O2", "never": "A1", "hello": "O1", "yes": "O4", "please": "O8"}
WEAK = {"a": "ə", "an": "ən", "the": "ðə", "to": "tə", "and": "ən", "at": "ət", "for": "fɚ", "can": "kən",
        "is": "ɪz", "are": "ɚ", "am": "əm", "your": "jɚ", "her": "hɚ", "from": "frəm", "some": "səm", "does": "dəz",
        "do": "də", "or": "ɚ", "of": "əv", "you": "ju", "my": "maɪ", "it": "ɪt", "on": "ɑn", "in": "ɪn"}
FORMS = {"has": "ˈhæz", "cookies": "ˈkʊkiz", "tickets": "ˈtɪkɪts", "says": "ˈsɛz", "knows": "ˈnoʊz", "thanks": "ˈθæŋks",
         "reading": "ˈridɪŋ", "walking": "ˈwɔkɪŋ", "grandmother": "ˈɡrænˌmʌðɚ", "grandfather": "ˈɡrænˌfɑðɚ",
         "eleven": "ɪˈlɛvən", "seven": "ˈsɛvən", "post": "ˈpoʊst", "office": "ˈɔfɪs", "street": "ˈstrit", "park": "ˈpɑrk"}
FUNCTION = {"T", "P", "C"}
STRONG_END = {"do", "is", "can", "are", "am", "does"}

def tokens(line):
    return re.findall(r"[A-Za-z']+(?:\|[A-Z]\d+)?|[^A-Za-z'\s]+|\s+", line)

def build(line):
    marked, ipa, stress = [], [], []
    words = [t for t in tokens(line) if re.match(r"[A-Za-z]", t)]
    last = words[-1].split("|")[0].lower() if words else ""
    for t in tokens(line):
        if not re.match(r"[A-Za-z]", t):
            marked.append(t)
            if t.strip() in {",", "—", "?", "!", ".", ":"} or t.strip().endswith(("—", ",")):
                if "," in t or "—" in t:
                    ipa.append("|"); stress.append(" |" if "," in t else " —")
                else:
                    stress.append(t.strip())
            elif t.isspace():
                stress.append(" ")
            continue
        word, _, forced = t.partition("|")
        low = word.lower()
        is_name = low in NAMES and word[0].isupper() and (low != "box" or word == "Box")
        tag = forced or ("S1" if is_name else None) or (TAGFIX.get(low) if low not in NAMES else None) or TAG.get(low)
        if not tag:
            raise SystemExit(f"нет тега для «{word}» в строке: {line}")
        marked.append(f"[{tag}]{word}[/]")
        strong = tag[0] not in FUNCTION and not (tag in {"D1", "D7"} and low != last) or is_name or (low == last and tag != "T1" and low != "it") or low in {"cannot", "not"}
        if is_name: w_ipa = NAMES[low]
        elif low in FORMS: w_ipa = FORMS[low] if strong else FORMS[low].replace("ˈ", "").replace("ˌ", "")
        elif not strong and low in WEAK: w_ipa = WEAK[low]
        else:
            base = IPA.get(low) or IPA.get(low.rstrip("s"))
            if base is None: raise SystemExit(f"нет IPA для «{word}»")
            w_ipa = base if low in IPA else base + "z"
            if not strong: w_ipa = w_ipa.replace("ˈ", "").replace("ˌ", "")
            elif "ˈ" not in w_ipa: w_ipa = "ˈ" + w_ipa
        ipa.append(w_ipa)
        stress.append(word.upper() if strong else word.lower() if word not in {"I"} else "I")
    s = "".join(stress).replace("  ", " ").strip()
    s = re.sub(r"\s+([?!.:])", r"\1", s)
    s = re.sub(r"\s*[|—]\s*$", "", s)
    return "".join(marked), "/" + " ".join(x for x in ipa).replace(" | ", " | ").strip(" |") + "/", s

def poem(number, units, text, gaps):
    body, pron = [], []
    for raw in text.strip("\n").split("\n"):
        if not raw.strip():
            body.append(""); continue
        m, i, s = build(raw.strip())
        body.append(m); pron.append({"stress": s, "ipa": re.sub(r"\s*\|\s*", " | ", i)})
    return {"number": number, "target_units": units, "body": "\n".join(body) + "\n", "pronunciation": pron,
            "gaps": [{"line": l, "word": w} for l, w in gaps]}

def uid(*lemmas):
    out = []
    for lm in lemmas:
        u = L.objects.filter(lemma__iexact=lm).exclude(unit_type="phrase").order_by("uid").first()
        if not u: raise SystemExit(f"нет единицы {lm}")
        out.append(u.uid)
    return out

P = {
1: ("p01_my_new_home", uid("home", "phone", "coffee", "house", "room", "new", "like", "box", "cat"), """
Good morning, day!
Good morning, home!
I have my coffee,
I have my phone.

My house is big,
my room is new.
Do you like it?
Yes, I do!

Tom has a box,
a big, big box.
Is it my box?
No|O4, it is not!

It is a cat!
Is it my cat?
Yes, it is!
I like that!
""", [(4, "phone"), (6, "new"), (9, "box"), (14, "cat"), (16, "that")]),
2: ("p02_who_is_she", uid("photo", "sister", "brother", "mother", "father", "grandmother", "grandfather", "tea", "cookie"), """
Here is a photo.
Who is she?
She is my sister.
She is three!

And who is he?
Is he ten?
He is my brother.
Sorry? Again?

This is my mother,
this is my father,
my grandmother,
my grandfather!

Your family is nice!
Coffee or tea?
Tea, please! And cookies —
one, two, three!
""", [(3, "sister"), (6, "ten"), (8, "Again"), (11, "grandmother"), (16, "three")]),
3: ("p03_what_time_is_it", uid("get", "breakfast", "drink", "eleven", "work", "every", "cafe", "time", "go"), """
I get up at seven,
I have breakfast at ten,
I drink coffee at eleven —
and coffee again!

Do you work every day?
Yes, I do!
I work at the cafe.
And you? And you?

What time is it?
Is it ten?
Coffee time!
Coffee again!

I go home at seven,
I have my phone,
my book, my coffee —
I am home!
""", [(1, "seven"), (2, "breakfast"), (5, "every"), (11, "time"), (16, "home")]),
4: ("p04_one_for_you", uid("key", "old", "for", "me", "turn", "left", "right", "straight", "near", "mailbox"), """
Here is a key,
an old, old key.
Is it for you?
Is it for me?

Turn left, turn right,
at night, at night.
Go straight, go straight,
at eight, at eight.

Where is the key shop?
It is near the bank.
Go straight and turn left.
Thank you! Thanks!

It is our mailbox,
our mailbox key.
One|N1 for you
and one|N1 for me!
""", [(2, "old"), (4, "me"), (6, "night"), (10, "near"), (16, "me")]),
5: ("p05_read_walk_play", uid("always", "read", "saturday", "walk", "park", "sunday", "never", "guitar", "play", "weekend"), """
I always read
on|P3 Saturdays.
I like reading —
it is my day!

I walk in the park
on|P3 Sundays.
I like walking —
my walking day!

And you, Tom? Do you walk?
Never! Never! No|O4!
I play the guitar,
and Box says hello!

Saturday, Sunday —
read, walk and play!
Every weekend
is a happy day!
""", [(1, "always"), (5, "park"), (10, "Never"), (11, "guitar"), (14, "play")]),
6: ("p06_who_knows", uid("letter", "white", "address", "word", "know", "mailbox", "cannot", "sleep", "night"), """
There is a letter,
it is white.
There is no|T4 address.
Is it right?

There is one|N1 word,
one|N1 word: Rose.
Who is Rose?
Who knows? Who knows?

The post office
does not know.
The old mailbox?
No|O4, no|O4, no|O4!

I cannot sleep,
it is night.
I have the letter,
white, white, white.
""", [(2, "white"), (3, "address"), (8, "knows"), (13, "sleep"), (16, "white")]),
7: ("p07_bus_to_park_street", uid("ticket", "bus", "three", "last", "stop", "shop", "open", "why", "know", "where"), """
Two tickets, please —
one|N1 for me,
one|N1 for you,
and the bus at three!

Does this bus go
to Park Street?
Who is on Park Street?
Who can I meet?

Here is the last stop,
the old photo shop.
Is it open? No|O4.
Stop|D2, stop|D2, stop|D2.

Why? Why? Why?
I do not know.
Rose, Rose, Rose —
where do you go?
""", [(1, "tickets"), (4, "three"), (9, "stop"), (11, "open"), (14, "know")]),
}
root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "content", "seed_poems") + os.sep
for f in os.listdir(root):
    if f.endswith(".yaml"): os.remove(root + f)
class Lit(str): pass
yaml.add_representer(Lit, lambda d, v: d.represent_scalar("tag:yaml.org,2002:str", v, style="|"), Dumper=yaml.SafeDumper)
for n, (name, units, text, gaps) in P.items():
    data = poem(n, units, text, gaps); data["body"] = Lit(data["body"])
    with open(root + name + ".yaml", "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, allow_unicode=True, sort_keys=False, width=1000)
print("ok")
