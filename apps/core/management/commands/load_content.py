"""Загружает учебный контент из content/ в базу. Идемпотентно: обновляет по ID."""
import json
import re
from pathlib import Path

import yaml
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction

from apps.curriculum.models import Level, TongueTwister, Week, WeekScene
from apps.drills.models import Exercise, PracticeItem
from apps.lessons.models import Lesson, LessonLayer
from apps.lexicon.models import LexicalUnit
from apps.poems.models import Poem
from apps.stories.models import Story
from apps.taxonomy.markup import find_issues
from scripts.audio_readiness import validate_manifest
from apps.taxonomy.models import PartOfSpeech, SemanticClass

UNIT_FIELDS = [
    "lemma", "meaning", "unit_type", "grammar_features", "forms", "cefr", "ipa_us", "ipa_ru", "stress_note", "translation_ru",
    "frequency_source", "verification_status", "verification_note", "collocations", "chunks",
    "grammar_dependencies", "example_en", "example_ru", "pattern", "substitutions", "situation",
    "typical_error", "usage_note",
]

# Русская рамка истории недели (план пилота, «Файлы и контракты»).
STORY_BEAT_KEYS = {"intro_ru", "outcome_ru", "next_hook_ru"}


def read_seed(path: Path) -> dict:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise CommandError(f"{path.name}: неверный YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise CommandError(f"{path.name}: ожидается словарь YAML")
    return data


def require_fields(where: str, data: dict, fields: dict) -> None:
    for key, kind in fields.items():
        if type(data.get(key)) is not kind:
            raise CommandError(f"{where}: отсутствует или неверно задано поле {key}")


def records(where: str, key: str, value, required: dict) -> list[dict]:
    if not isinstance(value, list):
        raise CommandError(f"{where}: {key} должен быть списком")
    for i, record in enumerate(value, 1):
        if not isinstance(record, dict):
            raise CommandError(f"{where}: {key}, элемент {i} должен быть словарём")
        require_fields(f"{where}: {key}, элемент {i}", record, required)
    return value


def string_list(where: str, key: str, value) -> None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise CommandError(f"{where}: {key} должен быть списком строк")


class Command(BaseCommand):
    help = "Загрузить лексику, уроки и упражнения из каталога content/"

    def add_arguments(self, parser):
        parser.add_argument("--preserve-admin-edits", action="store_true", help="Не перезаписывать истории и уроки, сохранённые через админку")
        parser.add_argument("--allow-progress-loss", action="store_true",
                            help="Разрешить удалить упражнения, у которых есть ответы учеников (история ответов пропадёт)")

    def _preserve_admin(self, obj):
        return obj is not None and (obj._meta.app_label, obj._meta.model_name, str(obj.pk)) in getattr(self, "admin_edited", set())

    def handle(self, *args, **opts):
        root = Path(settings.CONTENT_DIR)
        self.seen_units = {}
        self.allow_progress_loss = bool(opts.get("allow_progress_loss"))
        self.admin_edited = set()
        if opts.get("preserve_admin_edits"):
            from django.contrib.admin.models import LogEntry, ADDITION, CHANGE
            self.admin_edited = set(LogEntry.objects.filter(
                content_type__app_label__in=("stories", "lessons", "poems"),
                action_flag__in=(ADDITION, CHANGE),
            ).values_list("content_type__app_label", "content_type__model", "object_id"))
        with transaction.atomic():
            n_units = sum(self.load_units(p) for p in sorted((root / "seed_lexicon").glob("*.yaml")))
            self.load_weeks_plan(root / "manifests" / "weeks_plan.yaml")
            n_lessons = sum(self.load_lesson(p) for p in sorted((root / "seed_lessons").glob("*.yaml")))
            self.load_course_map(root / "manifests" / "course_map.yaml")
            n_stories = sum(self.load_story(p) for p in sorted((root / "seed_stories").glob("*.yaml")))
            n_poems = sum(self.load_poem(p) for p in sorted((root / "seed_poems").glob("*.yaml")))
            n_weeks = sum(self.load_week(p) for p in sorted((root / "seed_weeks").glob("*.yaml")))
        self.stdout.write(self.style.SUCCESS(
            f"Единиц: {n_units}, уроков: {n_lessons}, историй с текстом: {n_stories}, стихов с текстом: {n_poems}, "
            f"недель с диалогом: {n_weeks}"))

    def _guard_learner_data(self, where: str, exercises) -> None:
        """Удаление упражнения каскадом стирает ответы и повторения учеников. Без явного флага — стоп."""
        if self.allow_progress_loss:
            return
        from apps.learning.models import ExerciseAttempt, MistakeReview

        used = sorted({*ExerciseAttempt.objects.filter(exercise__in=exercises).values_list("exercise__order", flat=True),
                       *MistakeReview.objects.filter(exercise__in=exercises).values_list("exercise__order", flat=True)})
        if used:
            raise CommandError(
                f"{where}: упражнения {', '.join(map(str, used))} убраны из файла, но у них есть ответы учеников. "
                "Удаление сотрёт их историю. Верните упражнения или запустите load_content --allow-progress-loss, "
                "если потеря истории осознанная. Номер (order) упражнения нельзя переиспользовать для другого задания.")

    def _check_markup(self, where: str, *texts: str):
        for text in texts:
            if not isinstance(text, str):
                raise CommandError(f"{where}: текст должен быть строкой")
            issues = find_issues(text)
            if issues:
                raise CommandError(f"{where}: " + "; ".join(f"{i.token} — {i.problem}" for i in issues))

    def _set_units(self, relation, ids, where: str) -> None:
        if not isinstance(ids, list) or not all(isinstance(uid, str) for uid in ids):
            raise CommandError(f"{where}: ожидается список ID учебных единиц")
        units = list(LexicalUnit.objects.filter(uid__in=ids))
        missing = set(ids) - {unit.uid for unit in units}
        if missing:
            raise CommandError(f"{where}: незарегистрированные единицы {sorted(missing)}")
        relation.set(units)

    def load_units(self, path: Path) -> int:
        data = read_seed(path)
        require_fields(path.name, data, {"level": str, "units": list})
        records(path.name, "units", data["units"], {"uid": str, "class": str, "lemma": str})
        level = Level.objects.get(code=data["level"])
        week = self._week(level, data.get("week"), path.name)
        count = 0
        for item in data["units"]:
            if item["uid"] in self.seen_units:
                raise CommandError(f"{path.name}: повторный ID {item['uid']} (уже в {self.seen_units[item['uid']]})")
            self.seen_units[item["uid"]] = path.name
            if not re.fullmatch(r"[A-Z][1-9]\d?", item["class"]):
                raise CommandError(f"{path.name}: неверный класс {item['class']}")
            code, num = item["class"][0], int(item["class"][1:])
            try:
                pos = PartOfSpeech.objects.get(code=code)
                cls = SemanticClass.objects.get(category=pos, number=num)
            except ObjectDoesNotExist as exc:
                raise CommandError(f"{path.name}: класса {item['class']} нет в реестре") from exc
            self._check_markup(f"{path.name}:{item['uid']}", item.get("example_en", ""))
            defaults = {f: item[f] for f in UNIT_FIELDS if f in item}
            LexicalUnit.objects.update_or_create(
                uid=item["uid"],
                defaults=dict(defaults, part_of_speech=pos, semantic_class=cls, internal_level=level, week=week),
            )
            count += 1
        return count

    def load_lesson(self, path: Path) -> int:
        data = read_seed(path)
        require_fields(path.name, data, {"level": str, "slug": str, "title": str, "summary": str, "layers": list})
        records(path.name, "layers", data["layers"], {"number": int, "body": str})
        for exercise in records(path.name, "exercises", data.get("exercises", []), {"order": int, "answer": str}):
            for key in ("options", "accepted"):
                string_list(path.name, key, exercise.get(key, []))
            for key in ("prompt_ru", "prompt_en", "hint_ru", "explanation_ru"):
                if key in exercise and not isinstance(exercise[key], str):
                    raise CommandError(f"{path.name}: {key} должен быть строкой")
        orders = {e["order"] for e in data.get("exercises", [])}
        for item in records(path.name, "practice", data.get("practice", []),
                            {"order": int, "prompt_ru": str, "answer": str, "explanation_ru": str, "review_of": int}):
            string_list(path.name, "accepted", item.get("accepted", []))
            if item.get("kind", "translate") != "translate":
                raise CommandError(f"{path.name}: перевод {item['order']}: неизвестный вид {item.get('kind')}")
            if item["review_of"] not in orders:
                raise CommandError(f"{path.name}: перевод {item['order']}: нет основного задания {item['review_of']}")
            if "hint_ru" in item and not isinstance(item["hint_ru"], str):
                raise CommandError(f"{path.name}: hint_ru должен быть строкой")
        for key, required in (("sound_notes", {"text": str}), ("contractions", {"full": str, "short": str})):
            for item in records(path.name, key, data.get(key, []), required):
                for field in ("text", "full", "short", "ipa", "ru", "note_ru"):
                    if field in item and not isinstance(item[field], str):
                        raise CommandError(f"{path.name}: {key}.{field} должен быть строкой")
                self._check_markup(f"{path.name}: {key}", *(item[k] for k in required))
        level = Level.objects.get(code=data["level"])
        if self._preserve_admin(Lesson.objects.filter(slug=data["slug"]).first()):
            return 1
        lesson, _ = Lesson.objects.update_or_create(
            slug=data["slug"],
            defaults=dict(
                level=level, week=self._week(level, data.get("week"), path.name),
                order=data.get("order", 1), title=data["title"], summary=data["summary"],
                focus=PartOfSpeech.objects.filter(code=data.get("focus")).first(), minutes=data.get("minutes", 40),
                sound_notes=data.get("sound_notes", []), contractions=data.get("contractions", []),
            ),
        )
        self._set_units(lesson.units, data.get("units", []), path.name)
        lesson.layers.exclude(number__in=[l["number"] for l in data["layers"]]).delete()
        for layer in data["layers"]:
            self._check_markup(f"{path.name}: слой {layer['number']}", layer["body"])
            LessonLayer.objects.update_or_create(lesson=lesson, number=layer["number"], defaults={"body": layer["body"]})
        stale = lesson.exercises.exclude(order__in=[e["order"] for e in data.get("exercises", [])])
        self._guard_learner_data(path.name, stale)
        stale.delete()
        for ex in data.get("exercises", []):
            self._check_markup(f"{path.name}: упражнение {ex['order']}", ex.get("prompt_en", ""))
            obj, _ = Exercise.objects.update_or_create(
                lesson=lesson, order=ex["order"],
                defaults={k: ex.get(k, Exercise._meta.get_field(k).get_default()) for k in
                          ["kind", "stage", "prompt_ru", "prompt_en", "options", "answer", "accepted", "hint_ru", "explanation_ru"]},
            )
            self._set_units(obj.units, ex.get("units", []), f"{path.name}: упражнение {ex['order']}")
        practice = data.get("practice", [])
        lesson.practice_items.exclude(order__in=[p["order"] for p in practice]).delete()
        for item in practice:
            obj, _ = PracticeItem.objects.update_or_create(
                lesson=lesson, order=item["order"],
                defaults={"kind": item.get("kind", "translate"), "prompt_ru": item["prompt_ru"],
                          "answer": item["answer"], "accepted": item.get("accepted", []),
                          "hint_ru": item.get("hint_ru", ""), "explanation_ru": item["explanation_ru"],
                          "review_of": item["review_of"]},
            )
            self._set_units(obj.units, item.get("units", []), f"{path.name}: перевод {item['order']}")
        return 1

    def _week(self, level, number, where="контент"):
        if number is None:
            return None
        if type(number) is not int:
            raise CommandError(f"{where}: номер недели должен быть целым числом")
        week = Week.objects.filter(level=level, number=number).first()
        if week is None:
            raise CommandError(f"{where}: недели {level.code}-{number} нет в программе")
        return week

    def load_course_map(self, path: Path) -> None:
        if not path.exists():
            return
        data = read_seed(path)
        for item in data.get("stories", []):
            if self._preserve_admin(Story.objects.filter(number=item["number"]).first()):
                continue
            level = Level.objects.get(code=item["level"])
            Story.objects.update_or_create(number=item["number"], defaults=dict(
                level=level, week=self._week(level, item["week"], path.name), title=item["title"],
                hook_ru=item["hook_ru"], focus=item["focus"]))
        for item in data.get("poems", []):
            if self._preserve_admin(Poem.objects.filter(number=item["number"]).first()):
                continue
            level = Level.objects.get(code=item["level"])
            Poem.objects.update_or_create(number=item["number"], defaults=dict(
                level=level, week=self._week(level, item["week"], path.name), title=item["title"],
                rhyme_scheme=item["rhyme_scheme"], theme_ru=item["theme_ru"], phonetic_goals=item["phonetic_goals"]))

    def load_story(self, path: Path) -> int:
        data = read_seed(path)
        require_fields(path.name, data, {"number": int})
        records(path.name, "script", data.get("script", []), {"speaker": str, "text": str})
        story = Story.objects.get(number=data["number"])
        if self._preserve_admin(story):
            return 1
        if "body" in data:
            self._check_markup(path.name, data["body"])
        for f in ["characters", "grammar_ru", "prediction_ru", "visual_cues", "body", "questions",
                  "phrase_hunt", "retell_words", "retell_steps", "creative_ru", "script", "ambience"]:
            setattr(story, f, data.get(f, getattr(story, f)))
        if story.script:
            roles = self._voice_roles()
            for line in story.script:
                if line["speaker"] not in roles:
                    raise CommandError(f"{path.name}: роли {line['speaker']} нет в content/manifests/voices.yaml")
                self._check_markup(f"{path.name}: реплика", line["text"], line.get("spoken", ""))
            story.body = "\n\n".join(line["text"] for line in story.script)
        story.audio = self._audio_manifest("stories", f"s{story.number:02d}")
        story.is_published = True
        story.save()
        self._set_units(story.new_units, data.get("new_units", []), path.name)
        return 1

    def _voice_roles(self) -> dict:
        path = Path(settings.CONTENT_DIR) / "manifests" / "voices.yaml"
        return yaml.safe_load(path.read_text(encoding="utf-8"))["roles"] if path.exists() else {}

    def load_poem(self, path: Path) -> int:
        data = read_seed(path)
        require_fields(path.name, data, {"number": int, "body": str})
        lines = [ln for ln in data["body"].strip().splitlines() if ln.strip()]  # пустые строки — границы строф
        for gap in records(path.name, "gaps", data.get("gaps", []), {"line": int, "word": str}):
            if not 1 <= gap["line"] <= len(lines) or not gap["word"].strip():
                raise CommandError(f"{path.name}: пропуск должен содержать слово и номер существующей строки")
        for note in records(path.name, "pronunciation", data.get("pronunciation", []), {}):
            for key in ("stress", "ipa", "ru"):
                if key in note and not isinstance(note[key], str):
                    raise CommandError(f"{path.name}: pronunciation.{key} должен быть строкой")
        poem = Poem.objects.get(number=data["number"])
        if self._preserve_admin(poem):
            return 1
        self._check_markup(path.name, data["body"])
        poem.body, poem.pronunciation, poem.gaps = data["body"], data.get("pronunciation", []), data.get("gaps", [])
        poem.is_published = True
        poem.save()
        self._set_units(poem.target_units, data.get("target_units", []), path.name)
        return 1

    def _audio_manifest(self, *parts: str) -> dict:
        path = Path(settings.BASE_DIR) / "static" / "audio" / Path(*parts) / "manifest.json"
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            data = None
        if not isinstance(data, dict):
            # Озвучка необязательна: повреждённый манифест не должен останавливать загрузку курса.
            self.stdout.write(f"Пропущен повреждённый manifest.json: {path.parent.name}. Запустите generate_audio.bat.")
            return {}
        problem = validate_manifest(data, Path(settings.BASE_DIR) / "static")
        if problem:
            self.stdout.write(f"Пропущен аудиокомплект {path.parent.name}: {problem}.")
            return {}
        return data

    def load_weeks_plan(self, path: Path) -> int:
        if not path.exists():
            return 0
        weeks = read_seed(path).get("weeks", [])
        for item in weeks:
            week = Week.objects.get(level__code=item["level"], number=item["week"])
            week.situation_ru, week.sphere = item["situation_ru"], item["sphere"]
            week.grammar_ru, week.grammar_markers = item.get("grammar_ru", ""), item.get("grammar_markers", [])
            week.save()
        return len(weeks)

    def load_week(self, path: Path) -> int:
        data = read_seed(path)
        require_fields(path.name, data, {"level": str, "week": int, "can_do_ru": str, "mission_ru": str})
        records(path.name, "script", data.get("script", []), {"speaker": str, "text": str})
        week = Week.objects.select_related("level").get(level__code=data["level"], number=data["week"])
        roles = self._voice_roles()
        for line in data.get("script", []):
            if line["speaker"] not in roles:
                raise CommandError(f"{path.name}: роли {line['speaker']} нет в content/manifests/voices.yaml")
            self._check_markup(f"{path.name}: реплика", line["text"], line.get("spoken", ""))
        beat = data.get("story_beat", {})
        if not isinstance(beat, dict) or set(beat) - STORY_BEAT_KEYS or not all(isinstance(v, str) for v in beat.values()):
            raise CommandError(f"{path.name}: story_beat — словарь строк с ключами {', '.join(sorted(STORY_BEAT_KEYS))}")
        folder = f"{week.level.slug}-w{week.number:02d}"
        scene, _ = WeekScene.objects.update_or_create(week=week, defaults=dict(story_beat=beat,
            can_do_ru=data["can_do_ru"], mission_ru=data["mission_ru"], script=data.get("script", []),
            ambience=data.get("ambience", ""), audio=self._audio_manifest("weeks", folder)))
        self._set_units(scene.chunks, data.get("chunks", []), path.name)
        tw = data.get("twister")
        if tw is not None:
            if not isinstance(tw, dict):
                raise CommandError(f"{path.name}: twister должен быть словарём")
            require_fields(path.name, tw, {"number": int, "series": str, "text": str, "source": str})
            if tw["number"] != week.global_number:
                raise CommandError(f"{path.name}: номер скороговорки должен быть {week.global_number}")
            self._check_markup(f"{path.name}: скороговорка", tw["text"])
            warmup = tw.get("warmup", [])
            if not isinstance(warmup, list) or not all(isinstance(x, str) for x in warmup):
                raise CommandError(f"{path.name}: warmup скороговорки — список строк")
            for i, line in enumerate(warmup, 1):
                self._check_markup(f"{path.name}: разминка, шаг {i}", line)
            TongueTwister.objects.update_or_create(week=week, defaults=dict(
                goal_ru=tw.get("goal_ru", ""), tip_ru=tw.get("tip_ru", ""), warmup=warmup,
                target_line=tw.get("target_line", ""), own_ru=tw.get("own_ru", ""),
                number=tw["number"], series=tw["series"], text=tw["text"], ipa=tw.get("ipa", ""), ru=tw.get("ru", ""),
                focus_sounds=tw.get("focus_sounds", []), full_form=tw.get("full_form", ""), source=tw["source"],
                source_note=tw.get("source_note", ""), audio=self._audio_manifest("twisters", f"t{tw['number']:03d}")))
        else:
            TongueTwister.objects.filter(week=week).delete()
        return 1
