# Недели вокруг ситуаций — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** У каждой недели A1 появляются ситуация, озвученный диалог с эмоциями, скороговорка и цель «Я смогу…»; у историй — музыка, приглушённая под голос; у реплик — вариант «как говорят американцы», в уроках — блок «Как сокращают»; недели 1–2 наполнены полностью.

**Architecture:** План недель и нормы живут в реестре и манифестах (`registry.py`, `voices.yaml`, `weeks_plan.yaml`), контент недели — в `content/seed_weeks/*.yaml`. Загрузчик кладёт всё в новые модели `WeekScene` и `TongueTwister`; проверки — в новом модуле `apps/publishing/audit_weeks.py`. Генератор озвучки собирает диалоги, скороговорки и музыку тем же конвейером, что истории; плеер выносится в общий шаблон и получает третью дорожку.

**Tech Stack:** Django 5.2, Python 3.13, numpy, Kokoro (kokoro-onnx), ванильный JS, YAML-контент.

**Spec:** `docs/specs/2026-10-14-situation-weeks.md` — читать вместе с планом.

## Global Constraints

- Реестры `apps/taxonomy/registry.py` и `apps/curriculum/registry.py` — источник истины; новые словари добавлять можно, смысл занятых ID не менять.
- Новая лексика — только YAML-пакетами в `content/seed_lexicon/` с новыми `LX-xxxxx`, `cefr: unverified`, `verification_status: pending`.
- Сокращения размечаются раздельно: `[T8]I[/][D1]'m[/]`, `[D1]is[/][X1]n't[/]`.
- Эмоции: `neutral, happy, surprised, sad, tired, angry, worried, whisper, excited`; без поля — `neutral`.
- Настроения музыки: `none, calm, morning, mystery, sad, happy, tense`.
- Приглушение музыки под репликой −12 дБ, нарастание 150 мс, спад 400 мс; на темпе «очень медленно» музыка ещё −4 дБ.
- `music_gain_db`: A1 −26, A1+ −25, A2 −24, A2+ −23, B1 −22, B1+ −21, B2 −20, B2+ −19.
- Длина диалога A1: 6–10 реплик, 40–90 слов.
- Скороговорка: номер = порядковый номер недели в курсе 1–150; серии по уровням — таблица раздела 8 спецификации.
- `localStorage`-ключ громкости музыки: `ee-music-volume`; все обращения в `try/catch`.
- Тексты интерфейса — на простом русском.
- Слияния, запрещённые в `spoken` на A1–A2: `gonna, wanna, gotta, gimme, lemme, kinda, sorta, whatcha, dunno, y'all`; ключ режима речи — `ee-speech-mode`.
- Перед завершением: `load_content`, `audit_course` без ошибок, `manage.py test tests` зелёный, страницы проверены в браузере (компьютер и телефон 390 px).

## Review Focus

1. История или диалог, где `music` стоит только у первой реплики, а у истории настроение `none` целиком: музыка тянется до следующей смены; при `none` ключа `music` в манифесте нет, плеер работает без третьей дорожки (тест в Task 5 и Task 6).
2. Неизвестная эмоция или настроение в YAML: генератор останавливается с понятным сообщением по-русски, а не с `KeyError` (тест в Task 5); `audit_course` даёт ошибку (тест в Task 4).
3. Смена темпа и перемотка при играющей музыке: музыка переключается на файл нового темпа и встаёт на ту же позицию, что голос (ручная проверка в браузере, Task 6, шаг проверки).
4. Гость нажимает «Получилось»: не 500, а переход на вход; на странице для гостя — подсказка зарегистрироваться (тест в Task 8).
5. Неделя из плана без сцены (недели 3–14): страница недели отвечает 200 с пометкой «готовится», уровень показывает её в списке (тест в Task 8).

---

### Task 1: Реестр и манифесты

**Files:**
- Modify: `apps/curriculum/registry.py`
- Modify: `content/manifests/voices.yaml`
- Create: `content/manifests/weeks_plan.yaml`
- Test: `tests/test_registry.py`

**Interfaces:**
- Produces:
  - `SPHERES: dict[str, str]` — 12 кодов раздела 3 спецификации → русское название.
  - `DIALOGUE_LINES: dict[str, tuple[int, int]] = {"A1": (6, 10)}`, `DIALOGUE_WORDS = {"A1": (40, 90)}`.
  - `TWISTER_SERIES: dict[str, str]` — `A1: sounds`, `A1+/A2: contractions`, `A2+/B1: connected`, `B1+/B2/B2+: fast`.
  - `global_week(level_code: str, week: int) -> int` — сумма недель предыдущих уровней + `week`.
  - `voices.yaml`: `emotions: {code: {name_ru, speed, gain_db, pause}}` (значения — таблица раздела 6), `music_moods: {code: name_ru}`, `music_gain_db: {level: dB}`.
  - `weeks_plan.yaml`: `weeks: [{level, week, situation_ru, sphere, grammar_ru, grammar_markers: [..]}]` — 14 строк A1 из раздела 5 спецификации.

- [ ] **Step 1: Тесты**

```python
def test_spheres_and_norms(self):
    from apps.curriculum.registry import SPHERES, DIALOGUE_LINES, TWISTER_SERIES, global_week, LEVELS
    self.assertEqual(len(SPHERES), 12)
    self.assertEqual(DIALOGUE_LINES["A1"], (6, 10))
    self.assertEqual(set(TWISTER_SERIES), {lv.code for lv in LEVELS})
    self.assertEqual(global_week("A1", 1), 1)
    self.assertEqual(global_week("A1+", 1), 15)
    self.assertEqual(global_week("B2+", 22), 150)

def test_voices_manifest_lists(self):
    v = yaml.safe_load((CONTENT / "manifests/voices.yaml").read_text(encoding="utf-8"))
    self.assertEqual(set(v["emotions"]), {"neutral","happy","surprised","sad","tired","angry","worried","whisper","excited"})
    self.assertEqual(v["emotions"]["whisper"], {"name_ru": "шёпотом", "speed": 0.92, "gain_db": -8, "pause": 1.2})
    self.assertEqual(set(v["music_moods"]), {"none","calm","morning","mystery","sad","happy","tense"})
    self.assertEqual(v["music_gain_db"]["A1"], -26)
    self.assertEqual(v["music_gain_db"]["B2+"], -19)

def test_weeks_plan_a1(self):
    plan = yaml.safe_load((CONTENT / "manifests/weeks_plan.yaml").read_text(encoding="utf-8"))["weeks"]
    a1 = [w for w in plan if w["level"] == "A1"]
    self.assertEqual([w["week"] for w in a1], list(range(1, 15)))
    self.assertEqual({w["sphere"] for w in a1}, set(SPHERES))
    self.assertEqual(a1[0]["grammar_markers"], ["D1"])
    self.assertEqual(a1[13]["grammar_markers"], [])
```

- [ ] **Step 2:** `.venv/bin/python manage.py test tests.test_registry` — FAIL (нет имён).
- [ ] **Step 3:** Добавить словари и `global_week` в `registry.py`, разделы в `voices.yaml`, создать `weeks_plan.yaml` (коды маркеров — столбец раздела 5).
- [ ] **Step 4:** Тот же запуск — PASS.
- [ ] **Step 5:** Commit `Реестр: сферы, нормы диалогов, серии скороговорок; эмоции и музыка в voices.yaml; план 14 недель A1`.

---

### Task 2: Модели и миграции

**Files:**
- Modify: `apps/curriculum/models.py`, `apps/learning/models.py`
- Create: миграции `apps/curriculum/migrations/000N_week_scene.py`, `apps/learning/migrations/000N_weekgoal.py` (через `makemigrations`)
- Test: `tests/test_weeks.py` (новый)

**Interfaces:**
- Produces:
  - `Week`: `sphere = CharField(16, blank, choices=SPHERES.items())`, `situation_ru = CharField(160, blank)`, `grammar_ru = CharField(200, blank)`, `grammar_markers = JSONField(default=list, blank)`; свойство `global_number -> int` через `global_week`.
  - `WeekScene(week=OneToOneField(Week, related_name="scene", CASCADE), can_do_ru: CharField(240), mission_ru: CharField(300), script: JSONField(list), chunks: M2M(LexicalUnit, blank, related_name="week_scenes"), ambience: CharField(40, blank), audio: JSONField(dict, blank))`.
  - `TongueTwister(number=PositiveSmallIntegerField(unique), week=OneToOneField(Week, related_name="twister", CASCADE), series: CharField(16, choices sounds/contractions/connected/fast), text: CharField(300), ipa: CharField(300, blank), ru: CharField(300, blank), focus_sounds: JSONField(list), full_form: CharField(300, blank), source: CharField(8, choices original/folk), source_note: CharField(200, blank), audio: JSONField(dict, blank))`.
  - `WeekGoal(user FK, week FK(Week, related_name="goals"), status: CharField(8, choices done «Получилось» / not_yet «Ещё нет»), updated_at auto_now)`, `UniqueConstraint(user, week)`.

- [ ] **Step 1: Тест**

```python
class WeekModelTests(TestCase):
    def test_scene_twister_goal(self):
        week = Week.objects.get(level__code="A1", number=1)
        scene = WeekScene.objects.create(week=week, can_do_ru="Я смогу…", mission_ru="…", script=[])
        TongueTwister.objects.create(number=1, week=week, series="sounds", text="[T2]This[/]", source="original")
        user = User.objects.create_user("u@example.com", "u@example.com", "pw-123456")
        WeekGoal.objects.create(user=user, week=week, status="done")
        self.assertEqual(week.scene, scene)
        self.assertEqual(week.twister.number, 1)
        self.assertEqual(Week.objects.get(level__code="A1+", number=1).global_number, 15)
        with self.assertRaises(IntegrityError):
            WeekGoal.objects.create(user=user, week=week, status="not_yet")
```

- [ ] **Step 2:** `manage.py test tests.test_weeks` — FAIL.
- [ ] **Step 3:** Поля и модели, `makemigrations curriculum learning`. RLS-хук `post_migrate` новые таблицы подхватит сам — проверить, что ничего добавлять не нужно.
- [ ] **Step 4:** `manage.py test tests` — PASS целиком.
- [ ] **Step 5:** Commit `Модели: сцена недели, скороговорка, цель недели`.

---

### Task 3: Загрузчик недель и скороговорок

**Files:**
- Modify: `apps/core/management/commands/load_content.py`
- Create: `apps/stories/script.py` (общие функции реплик)
- Modify: `apps/stories/views.py` (брать `voice_roles` из `script.py`)
- Test: `tests/test_weeks.py`

**Interfaces:**
- Consumes: модели Task 2, `weeks_plan.yaml` Task 1.
- Produces:
  - `apps/stories/script.py`: `voices_manifest() -> dict` (весь `voices.yaml`, пустой dict если файла нет); `voice_roles() -> dict`; `build_lines(script: list[dict]) -> tuple[list[dict], list[dict]]` — строки `{"i", "speaker", "kind", "text", "ru", "name", "emotion", "emotion_ru"}` (`emotion_ru` пусто для `neutral`) и список говорящих `{"id", "name"}` в порядке появления.
  - `Command.load_weeks_plan(path) -> int`, `Command.load_week(path) -> int`.
  - Папки озвучки: недели `static/audio/weeks/<level.slug>-wNN/manifest.json`, скороговорки `static/audio/twisters/tNNN/manifest.json`.
- Порядок в `handle`: лексика → **план недель** → уроки → карта → истории → стихи → **недели** (`content/seed_weeks/*.yaml`).
- `load_week`: по `level`+`week` находит `Week`; `update_or_create` сцены; `chunks` по uid, незарегистрированные — `CommandError` как у уроков; каждая реплика: `speaker` из ролей (иначе `CommandError`), разметка через `_check_markup`; `twister` → `TongueTwister.update_or_create(week=…)`; манифесты читаются в `audio`, если файлов нет — `{}`.

- [ ] **Step 1: Тесты** — во временной копии `content/` (`shutil.copytree` в `tempfile.mkdtemp()`, `override_settings(CONTENT_DIR=…)`) пишем `seed_weeks/a1_w01.yaml` с 6 репликами Anna/Tom и скороговоркой.

```python
def test_plan_fills_weeks(self):
    call_command("load_content", verbosity=0)
    w = Week.objects.get(level__code="A1", number=8)
    self.assertEqual((w.sphere, w.grammar_markers), ("city", ["P1", "A6"]))

def test_week_file_loads_idempotently(self):
    with self.content_with_week(SAMPLE_WEEK):
        call_command("load_content", verbosity=0); call_command("load_content", verbosity=0)
    scene = WeekScene.objects.get(week__level__code="A1", week__number=1)
    self.assertEqual(len(scene.script), 6)
    self.assertEqual(TongueTwister.objects.get(number=1).week, scene.week)
    self.assertEqual(WeekScene.objects.count(), 1)

def test_unknown_speaker_rejected(self):
    with self.content_with_week(SAMPLE_WEEK.replace("speaker: tom", "speaker: nobody", 1)):
        with self.assertRaisesMessage(CommandError, "nobody"):
            call_command("load_content", verbosity=0)

def test_build_lines_emotion_label(self):
    lines, speakers = build_lines([{"speaker": "tom", "text": "Hi", "emotion": "surprised"}, {"speaker": "anna", "text": "Hi"}])
    self.assertEqual((lines[0]["name"], lines[0]["emotion_ru"], lines[1]["emotion_ru"]), ("Том", "удивлённо", ""))
    self.assertEqual([s["id"] for s in speakers], ["tom", "anna"])
```

- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** Реализация по Interfaces; `story_detail` переводится на `build_lines` без изменения вывода (старые тесты историй должны пройти).
- [ ] **Step 4:** `manage.py test tests` — PASS.
- [ ] **Step 5:** Commit `Загрузчик: план недель, сцены недель и скороговорки`.

---

### Task 4: Проверки недель, скороговорок и реплик

**Files:**
- Create: `apps/publishing/audit_weeks.py`
- Modify: `apps/publishing/audit.py` (вызов `audit_weeks(r)` в конце `run_audit` до подсчёта незнакомых слов)
- Modify: `content/seed_stories/s01_not_my_box.yaml` (у первой реплики `music: morning`, чтобы существующий тест «аудит без ошибок» остался зелёным)
- Test: `tests/test_audit_weeks.py`

**Interfaces:**
- Consumes: `vocab_until`, `is_known`, `text_tokens`, `strip_markup` из `audit.py`; реестры Task 1; модели Task 2.
- Produces: `audit_weeks(r: AuditReport) -> None`, внутри — `audit_script(r, where, script, roles, emotions, moods, music_required: bool)`, `marker_count(script, code) -> int`, `lesson_examples(lesson) -> set[str]`, `normalize_line(text) -> str`.
- Правила — таблица раздела 9 спецификации, дословно, с её делением на ошибки и предупреждения. Уточнения:
  - `normalize_line`: `strip_markup`, убрать `“ ” " '` по краям слов-кавычек, схлопнуть пробелы, `casefold`.
  - Пример урока — строка слоя, начинающаяся с `> `; английская часть — до ` — `.
  - Маркер: одна буква (`D`) совпадает с любым классом категории, `D1` — только с классом; код проверяется по `CATEGORIES` реестра.
  - Сферы: считаются по `Week.sphere` уровня; «план полный», когда сфера заполнена у всех `level.weeks` недель.
  - Номер скороговорки должен равняться `week.global_number` — ошибка.

- [ ] **Step 1: Тесты** — после `load_content` создаём сцену недели 1 прямо в БД и портим по одному правилу:

```python
def test_valid_scene_passes(self): ...            # сцена из 6 реплик be, всё известно → нет ошибок с «Неделя A1-1»
def test_unknown_word_in_dialogue(self): ...      # слово "elephant" → ошибка «незнакомые слова: elephant»
def test_grammar_marker_missing(self): ...        # диалог без D1 → ошибка «маркер D1 встречается 0 раз, нужно 2»
def test_marker_not_in_registry(self): ...        # week.grammar_markers=["Z9"] → ошибка «Z9 нет в реестре»
def test_lesson_without_dialogue_example(self): ... # урок недели без такой строки → ошибка с slug урока
def test_bad_emotion_and_speaker(self): ...       # emotion "furious", speaker "nobody" → две ошибки
def test_dialogue_length_a1(self): ...            # 5 реплик → ошибка «реплик 5, норма 6–10»
def test_story_first_line_needs_music(self): ...  # убрать music у s01 → ошибка «История 1: у первой реплики нет music»
def test_spheres_warning_until_plan_complete(self): ... # стереть sphere у недели 14 → предупреждение со списком «travel»
def test_twister_rules(self): ...                 # series fast на A1; folk без source_note; number=2 на неделе 1 → три ошибки
def test_missing_twister_is_warning(self): ...
```

Каждый тест проверяет конкретную подстроку сообщения в `run_audit().errors` или `.warnings`.

- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** Реализовать `audit_weeks.py`, добавить `music: morning` в историю 1.
- [ ] **Step 4:** `manage.py test tests` — PASS; `manage.py audit_course` — без ошибок (до Task 9 сцен нет, предупреждений о сценах тоже нет).
- [ ] **Step 5:** Commit `Проверки курса: недели, скороговорки, эмоции и музыка реплик`.

---

### Task 5: Озвучка — эмоции, музыка, диалоги недель, скороговорки

**Files:**
- Modify: `scripts/generate_story_audio.py`
- Test: `tests/test_audio_generator.py` (модуль грузится через `importlib.util.spec_from_file_location`)

**Interfaces:**
- Consumes: `voices.yaml` Task 1, формат файлов недели Task 3.
- Produces (в скрипте):
  - `Engine.synth(text: str, voice: str, speed: float, emotion: str = "neutral") -> np.ndarray` у `KokoroEngine` и `TestEngine`; Kokoro эмоцию не использует (её уже учла скорость), будущий движок — может.
  - `build_track(engine, script, roles, factor, pause_mult, emotions) -> tuple[np.ndarray, list[dict]]`: скорость = роль × эмоция × темп; после `rms_normalize` громкость × `10**(gain_db/20)`; пауза перед следующей репликой × `pause` эмоции предыдущей; в тайминге новое поле `emotion`.
  - `MUSIC: dict[str, Callable[[float], np.ndarray]]` — `calm, morning, mystery, sad, happy, tense`; каждый генератор детерминирован (`default_rng` с фиксированным зерном), бесшовно зацикливается, `rms_normalize` до −20 дБ.
  - `music_track(script, timings, total_seconds) -> np.ndarray | None`: настроение тянется от реплики с `music` до следующей, переход — кроссфейд 1 с; `none` — тишина; если во всём сценарии нет настроения кроме `none` — `None`.
  - `duck(music, timings, depth_db=-12, attack=0.15, release=0.4) -> np.ndarray` — огибающая на 100 Гц, несимметричное сглаживание, интерполяция до SR.
  - Манифест истории: у каждого темпа ключ `music` (путь к `<tempo>.music.mp3`) и `music_gain_db` (уровень; для `very_slow` ещё −4); при `None` ключей нет.
  - `generate_week(engine, path, voices) -> str` → `static/audio/weeks/<slug>-wNN/` (манифест как у истории: темпы, `ambience`, без музыки).
  - `generate_twister(engine, twister: dict, voices) -> str` → `static/audio/twisters/tNNN/`, голос `voices["extras"][0]`, без фона и музыки.
  - CLI: `--all` (истории, недели, скороговорки — как вызывает `generate_audio.bat`), `--story N`, `--week A1-1`, `--only {stories,weeks,twisters}`.
  - Неизвестная эмоция или настроение → `sys.exit("<файл>: неизвестная эмоция …. Есть: …")`.

- [ ] **Step 1: Тесты** (с `TestEngine`, во временной папке `OUT`):

```python
def test_emotion_changes_speed_and_lands_in_timings(self):
    script = [{"speaker": "tom", "text": "I am Tom here", "emotion": "sad"},
              {"speaker": "tom", "text": "I am Tom here"}]
    _, t = gen.build_track(gen.TestEngine(), script, ROLES, 1.0, 1.0, EMOTIONS)
    self.assertEqual([x["emotion"] for x in t], ["sad", "neutral"])
    self.assertGreater(t[0]["end"] - t[0]["start"], t[1]["end"] - t[1]["start"])

def test_music_ducks_under_lines(self):
    music = np.ones(gen.SR * 6, np.float32)
    out = gen.duck(music, [{"start": 2.0, "end": 4.0}])
    self.assertLess(abs(out[int(3.0 * gen.SR)]), 10 ** (-11 / 20))
    self.assertGreater(abs(out[int(5.5 * gen.SR)]), 0.9)

def test_music_none_gives_no_track(self):
    self.assertIsNone(gen.music_track([{"speaker": "anna", "text": "Hi", "music": "none"}], [{"start": 0, "end": 1}], 2.0))

def test_story_manifest_has_music_per_tempo(self):  # history with music: morning → very_slow.music_gain_db == level - 4
def test_unknown_emotion_exits_with_message(self):  # SystemExit, текст содержит «неизвестная эмоция»
def test_week_and_twister_folders(self):            # generate_week / generate_twister создают manifest.json в нужных папках
```

- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** Реализация по Interfaces. Генераторы музыки — простые аккорды (сумма синусов с огибающей) и «пианино» (затухающие ноты) на numpy, разные лады и темпы для настроений; без scipy.
- [ ] **Step 4:** `manage.py test tests` — PASS; затем `.venv/bin/python scripts/generate_story_audio.py --all --engine test` — без ошибок, для истории 1 есть `*.music.mp3` (или `.wav`); удалить сгенерированные тестовые файлы из `static/audio/` (папка в `.gitignore`).
- [ ] **Step 5:** Commit `Озвучка: эмоции, музыка с приглушением, диалоги недель и скороговорки`.

---

### Task 6: Общий плеер — музыка, эмоции, три режима слушания

**Files:**
- Create: `templates/components/script_player.html` (плеер + реплики, вынесенные из `templates/stories/detail.html`)
- Modify: `templates/stories/detail.html` (include компонента), `apps/stories/views.py`
- Modify: `static/js/audio-player.js`, `static/css/studio.css`
- Test: `tests/test_content_and_learning.py` (истории), ручная проверка в браузере

**Interfaces:**
- Consumes: `build_lines` Task 3, манифест Task 5.
- Produces: компонент `{% include "components/script_player.html" with audio=audio lines=lines speakers=speakers listen_modes=True %}`.
  - Атрибуты: `data-music-very_slow|slow|natural` (пути), `data-music-db-<tempo>`; регулятор `data-music-vol` (0–100, по умолчанию 100, из `ee-music-volume`).
  - Реплика: `<span class="speaker">Том<span class="emotion"> · удивлённо</span></span>`, перевод `<span class="line-ru" lang="ru">` (если есть `ru`).
  - Режимы при `listen_modes`: радиокнопки `name="listen"` — `hidden` «Без текста», `text` «С текстом», `marked` «С разметкой» (по умолчанию). Класс на контейнере реплик: `listen-hidden` прячет `.line-text` и `.line-ru` (имена героев видны), `listen-text` гасит маркеры у `.mk`.
- JS: третья дорожка `music` (`new Audio`), всегда `playbackRate` и `currentTime` как у голоса: на `play/pause/seeked/ratechange`, при смене темпа меняется `src` на файл нового темпа и выставляется время голоса после `loadedmetadata`; громкость = слайдер × `10**(db/20)`; без `data-music-*` код музыки не запускается.

- [ ] **Step 1: Тесты страницы истории** (после `load_content`, в манифест истории 1 в БД подставлен словарь с `music`):

```python
def test_story_page_has_music_and_emotions(self):
    story = Story.objects.get(number=1)
    story.audio = FAKE_MANIFEST_WITH_MUSIC; story.script[2]["emotion"] = "surprised"; story.save()
    html = self.client.get(reverse("stories:detail", args=[1])).content.decode()
    self.assertIn('data-music-slow="/static/audio/stories/s01/slow.music.mp3"', html)
    self.assertIn("data-music-vol", html)
    self.assertIn('<span class="emotion"> · удивлённо</span>', html)

def test_story_page_without_music_has_no_slider(self): ...
```

- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** Вынести компонент, дописать JS и CSS (режим `listen-hidden` на телефоне не ломает высоту строк).
- [ ] **Step 4:** `manage.py test tests` — PASS. Браузер (Playwright из `/opt/node22/lib/node_modules/playwright`, сервер `runserver`, манифест с музыкой из `--engine test`): играет, музыка тише в репликах; смена темпа и клик по реплике — музыка на той же позиции, что голос; «Сыграть роль» работает; 390 px без горизонтальной прокрутки.
- [ ] **Step 5:** Commit `Плеер: музыка третьей дорожкой, подпись эмоции, режимы слушания`.

---

### Task 7: Живая речь — «Как написано / Как говорят» и «Как сокращают»

**Files:**
- Modify: `apps/lessons/models.py` (+ миграция), `apps/core/management/commands/load_content.py`
- Modify: `apps/stories/script.py` (`build_lines` отдаёт `spoken`), `templates/components/script_player.html`, `static/js/audio-player.js`, `static/css/studio.css`
- Create: `templates/components/contractions.html`; Modify: `templates/lessons/detail.html`
- Modify: `scripts/generate_story_audio.py`, `apps/publishing/audit_weeks.py`
- Test: `tests/test_spoken.py`

**Interfaces:**
- Consumes: `build_lines` Task 3, `build_track` Task 5, компонент Task 6, `audit_script` Task 4.
- Produces:
  - `Lesson.contractions = JSONField(default=list, blank=True)` — `[{full, short, ipa, note_ru}]`; загрузчик читает ключ `contractions` урока.
  - `build_lines`: в каждой строке `spoken` (пусто, если поля нет).
  - Компонент: переключатель `name="speech"` — `written` «Как написано» (по умолчанию), `spoken` «Как говорят»; у строки с `spoken` два блока: `.line-written` и `.line-spoken` + `.line-full` «полностью: …»; класс `speech-spoken` на контейнере переключает видимость; выбор в `localStorage` `ee-speech-mode`.
  - Генератор: в `build_track` текст реплики = `line.get("spoken") or line["text"]` только для темпа `natural`; для остальных — `text`. Признак передаётся параметром `spoken: bool`.
  - `audit_script` получает правила таблицы раздела 8a спецификации; новая `audit_lesson_contractions(r)`.
  - Компонент `contractions.html`: таблица «Полностью → Как говорят → Транскрипция (IPA и `|ru_tr`) → Заметка», заголовок «Как сокращают», `id="contractions"`, ставится после блока «Как это звучит».

- [ ] **Step 1: Тесты**

```python
def test_spoken_variant_on_story_page(self):
    story = Story.objects.get(number=1)
    story.script[3]["spoken"] = "“[O4]No[/], [T8]it[/][D1]'s[/] [X1]not[/] [T3]my[/] [S2]box[/].”"; story.save()
    html = self.client.get(reverse("stories:detail", args=[1])).content.decode()
    self.assertIn('name="speech"', html); self.assertIn('class="line-spoken"', html); self.assertIn("полностью:", html)

def test_natural_tempo_reads_spoken(self):  # TestEngine: длительность natural-реплики считается по spoken (короче), slow — по text
def test_audit_spoken_rules(self):           # spoken == text → ошибка; "gonna" на A1 → ошибка; незнакомое слово в spoken → ошибка
def test_contraction_without_spoken_warns(self):  # реплика недели 1 с "it is" без spoken → предупреждение
def test_lesson_contractions_block(self):    # урок с contractions → id="contractions", "I'm", русская транскрипция; short без апострофа → ошибка аудита
```

- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** Реализация по Interfaces.
- [ ] **Step 4:** `manage.py test tests` — PASS; браузер: переключатель на истории 1, выбор сохраняется после перезагрузки, на 390 px строка «полностью» переносится без прокрутки.
- [ ] **Step 5:** Commit `Живая речь: «как говорят» у реплик, озвучка «как в жизни» по ней, блок «Как сокращают»`.

---

### Task 8: Страницы недели и уровня, цель «Я смогу…»

**Files:**
- Modify: `apps/curriculum/views.py`, `apps/curriculum/urls.py`, `templates/curriculum/level.html`
- Create: `templates/curriculum/week.html`
- Modify: `apps/learning/views.py`, `apps/learning/urls.py`
- Modify: `templates/core/home.html` и `templates/curriculum/level.html` — карточка урока ссылается на неделю
- Test: `tests/test_weeks.py`

**Interfaces:**
- Consumes: модели Task 2, компонент Task 6, `build_lines` Task 3.
- Produces:
  - URL `curriculum:week` — `levels/<slug>/weeks/<int:number>/`, `week_detail(request, slug, number)`.
  - URL `learning:week_goal` — `learning/weeks/<int:week_id>/goal/`, `week_goal(request, week_id)`: только POST, `login_required`, `status ∈ {done, not_yet}` иначе 400, `update_or_create`, redirect на неделю.
  - Неделя: блоки раздела 4 спецификации по порядку (`id`: `goal`, `dialogue`, `lessons`, `chunks`, `role`, `twister`, `mission`); без сцены — шапка с ситуацией из плана и «Неделя готовится».
  - Уровень: список недель «N · ситуация · сфера» со ссылкой, у недели без сцены — пометка «готовится».
  - Блок скороговорки: текст с разметкой (`|annotate`), IPA и русская транскрипция (`|ru_tr`), обычный `<audio controls>` и три кнопки темпа из `twister.audio`; без аудио — подсказка «озвучка появится после generate_audio.bat».

- [ ] **Step 1: Тесты**

```python
def test_week_without_scene_is_200(self):
    r = self.client.get(reverse("curriculum:week", args=["a1", 5]))
    self.assertContains(r, "Магазин у дома"); self.assertContains(r, "готовится")

def test_week_with_scene_shows_blocks(self):  # сцена из Task 4-фикстуры → id goal, dialogue, twister, mission в нужном порядке
def test_level_lists_weeks(self):             # /levels/a1/ содержит ссылки на 14 недель
def test_guest_goal_redirects_to_login(self):
    r = self.client.post(reverse("learning:week_goal", args=[week.pk]), {"status": "done"})
    self.assertEqual(r.status_code, 302); self.assertIn("login", r["Location"])
def test_learner_goal_saved_and_bad_status_400(self): ...
def test_guest_sees_register_hint(self): ...
```

- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** Реализация; CSRF-токен в форме цели.
- [ ] **Step 4:** `manage.py test tests` — PASS; браузер: неделя 5 и уровень A1 на компьютере и 390 px.
- [ ] **Step 5:** Commit `Страница недели, список недель уровня, цель «Я смогу…»`.

---

### Task 9: Контент недель 1 и 2

**Files:**
- Create: `content/seed_lexicon/a1_w01_phrases.yaml`, `content/seed_lexicon/a1_w02_phrases.yaml` (готовые фразы, тип `phrase`, ID с `LX-00042`)
- Create: `content/seed_weeks/a1_w01.yaml`, `content/seed_weeks/a1_w02.yaml`
- Modify: уроки `content/seed_lessons/a1_w01_l01_nouns.yaml`, `a1_w01_l02_be.yaml`, `a1_w02_l03_determiners.yaml`, `a1_w02_l04_have_like_can.yaml` — по одному примеру `>` из диалога своей недели
- Modify: `content/seed_stories/s01_not_my_box.yaml` — эмоции у реплик, настроения сцен
- Modify: `content/manifests/voices.yaml` — эпизодический герой, если он нужен в неделе 2
- Modify: `tests/test_content_and_learning.py` — новые количества единиц

**Требования к контенту** (проверяются `audit_course`, кроме помеченных):
- Неделя 1 «Знакомство с соседом»: Anna знакомится с Tom у двери нового дома; маркер D1 ≥ 2; цель и задание из спецификации (раздел 10).
- Неделя 2 «Мой новый дом»: Anna показывает Tom и Mia дом; маркеры T1, T2, T3 ≥ 2 каждый; сюжет ведёт к истории 1 «Not My Box» (не проверяется).
- В каждом диалоге 6–10 реплик, 40–90 слов, хотя бы 3 разные эмоции; у каждой реплики `ru`.
- Готовые фразы: 5–8 на неделю; их слова либо уже известны, либо входят в саму фразу-единицу.
- Скороговорки 1 и 2: серия `sounds`, `source: original`, только известные слова, 3–8 слов; `focus_sounds`: неделя 1 — `dh`, неделя 2 — `h` или `ae`.
- История 1: `music` у первой реплики `morning`, у реплики с котом — `happy`; эмоции у реплик речи героев.
- `spoken` у каждой реплики недель 1–2 и истории 1, где возможно сокращение (предупреждений раздела 8a нет).
- Блок `contractions` в уроках 2–4: урок 2 (be) — `I am → I'm`, `you are → you're`, `it is → it's`, `is not → isn't`, `are not → aren't`; уроки 3–4 — `that is → that's`, `do not → don't`, `can not → can't` (в те уроки, где эти слова изучаются), у каждой пары `ipa` и `note_ru`.

- [ ] **Step 1:** Обновить ожидаемые количества в `test_packages_loaded` и `test_loader_is_idempotent` (41 + новые фразы) — тест FAIL.
- [ ] **Step 2:** Написать пакеты фраз, недели, правки уроков и истории.
- [ ] **Step 3:** `load_content`, `audit_course` — 0 ошибок, нет предупреждений о неделях 1–2; `manage.py test tests` — PASS.
- [ ] **Step 4:** `generate_story_audio.py --all --engine test` — проходит; браузер: неделя 1 и 2, история 1 (режимы слушания, подписи эмоций, «Сыграть роль»).
- [ ] **Step 5:** Commit `Контент: недели 1–2 A1 — диалоги, готовые фразы, скороговорки; эмоции и музыка истории 1`.

---

### Task 10: Документация и финальная проверка

**Files:**
- Modify: `README.md` (раздел «Озвучка»: музыка, недели, скороговорки; генерация `generate_audio.bat`), `CLAUDE.md` (правила для недель: файлы `seed_weeks`, проверки), `docs/CONTEXT.md` (термины: сцена недели, сфера, скороговорка, цель недели)

- [ ] **Step 1:** Обновить три документа.
- [ ] **Step 2:** Полный прогон: `manage.py test tests`, `load_content`, `audit_course`, браузер — главная, уровень A1, недели 1, 2, 5, история 1 (компьютер и 390 px).
- [ ] **Step 3:** Commit `Документация: недели вокруг ситуаций` и `git push origin HEAD:main`.
- [ ] **Step 4:** Сообщить автору: запустить `start.bat` (подтянет изменения), затем `generate_audio.bat` и послушать неделю 1 и историю 1.
