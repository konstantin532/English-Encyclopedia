"""Загружает учебный контент из content/ в базу. Идемпотентно: обновляет по ID."""
import json
from pathlib import Path

import yaml
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.curriculum.models import Level, TongueTwister, Week, WeekScene
from apps.drills.models import Exercise
from apps.lessons.models import Lesson, LessonLayer
from apps.lexicon.models import LexicalUnit
from apps.poems.models import Poem
from apps.stories.models import Story
from apps.taxonomy.markup import find_issues
from apps.taxonomy.models import PartOfSpeech, SemanticClass

UNIT_FIELDS = [
    "lemma", "meaning", "unit_type", "grammar_features", "forms", "cefr", "ipa_us", "ipa_ru", "stress_note", "translation_ru",
    "frequency_source", "verification_status", "verification_note", "collocations", "chunks",
    "grammar_dependencies", "example_en", "example_ru", "pattern", "substitutions", "situation",
    "typical_error", "usage_note",
]


class Command(BaseCommand):
    help = "Загрузить лексику, уроки и упражнения из каталога content/"

    def handle(self, *args, **opts):
        root = Path(settings.CONTENT_DIR)
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

    def _check_markup(self, where: str, *texts: str):
        for text in texts:
            issues = find_issues(text or "")
            if issues:
                raise CommandError(f"{where}: " + "; ".join(f"{i.token} — {i.problem}" for i in issues))

    def load_units(self, path: Path) -> int:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        level = Level.objects.get(code=data["level"])
        week = Week.objects.filter(level=level, number=data.get("week")).first()
        count = 0
        for item in data["units"]:
            code, num = item["class"][0], int(item["class"][1:])
            pos = PartOfSpeech.objects.get(code=code)
            cls = SemanticClass.objects.get(category=pos, number=num)
            self._check_markup(f"{path.name}:{item['uid']}", item.get("example_en", ""))
            defaults = {f: item[f] for f in UNIT_FIELDS if f in item}
            LexicalUnit.objects.update_or_create(
                uid=item["uid"],
                defaults=dict(defaults, part_of_speech=pos, semantic_class=cls, internal_level=level, week=week),
            )
            count += 1
        return count

    def load_lesson(self, path: Path) -> int:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        level = Level.objects.get(code=data["level"])
        lesson, _ = Lesson.objects.update_or_create(
            slug=data["slug"],
            defaults=dict(
                level=level, week=Week.objects.filter(level=level, number=data.get("week")).first(),
                order=data.get("order", 1), title=data["title"], summary=data["summary"],
                focus=PartOfSpeech.objects.filter(code=data.get("focus")).first(), minutes=data.get("minutes", 40),
                sound_notes=data.get("sound_notes", []),
            ),
        )
        lesson.units.set(LexicalUnit.objects.filter(uid__in=data.get("units", [])))
        missing = set(data.get("units", [])) - set(lesson.units.values_list("uid", flat=True))
        if missing:
            raise CommandError(f"{path.name}: незарегистрированные единицы {sorted(missing)}")
        lesson.layers.exclude(number__in=[l["number"] for l in data["layers"]]).delete()
        for layer in data["layers"]:
            self._check_markup(f"{path.name}: слой {layer['number']}", layer["body"])
            LessonLayer.objects.update_or_create(lesson=lesson, number=layer["number"], defaults={"body": layer["body"]})
        lesson.exercises.exclude(order__in=[e["order"] for e in data.get("exercises", [])]).delete()
        for ex in data.get("exercises", []):
            self._check_markup(f"{path.name}: упражнение {ex['order']}", ex.get("prompt_en", ""))
            obj, _ = Exercise.objects.update_or_create(
                lesson=lesson, order=ex["order"],
                defaults={k: ex.get(k, Exercise._meta.get_field(k).get_default()) for k in
                          ["kind", "stage", "prompt_ru", "prompt_en", "options", "answer", "accepted", "hint_ru", "explanation_ru"]},
            )
            obj.units.set(LexicalUnit.objects.filter(uid__in=ex.get("units", [])))
        return 1

    def _week(self, level, number):
        return Week.objects.filter(level=level, number=number).first()

    def load_course_map(self, path: Path) -> None:
        if not path.exists():
            return
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for item in data.get("stories", []):
            level = Level.objects.get(code=item["level"])
            Story.objects.update_or_create(number=item["number"], defaults=dict(
                level=level, week=self._week(level, item["week"]), title=item["title"],
                hook_ru=item["hook_ru"], focus=item["focus"]))
        for item in data.get("poems", []):
            level = Level.objects.get(code=item["level"])
            Poem.objects.update_or_create(number=item["number"], defaults=dict(
                level=level, week=self._week(level, item["week"]), title=item["title"],
                rhyme_scheme=item["rhyme_scheme"], theme_ru=item["theme_ru"], phonetic_goals=item["phonetic_goals"]))

    def load_story(self, path: Path) -> int:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        story = Story.objects.get(number=data["number"])
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
                self._check_markup(f"{path.name}: реплика", line["text"])
            story.body = "\n\n".join(line["text"] for line in story.script)
        manifest = Path(settings.BASE_DIR) / "static" / "audio" / "stories" / f"s{story.number:02d}" / "manifest.json"
        story.audio = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else {}
        story.is_published = True
        story.save()
        story.new_units.set(LexicalUnit.objects.filter(uid__in=data.get("new_units", [])))
        return 1

    def _voice_roles(self) -> dict:
        path = Path(settings.CONTENT_DIR) / "manifests" / "voices.yaml"
        return yaml.safe_load(path.read_text(encoding="utf-8"))["roles"] if path.exists() else {}

    def load_poem(self, path: Path) -> int:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        poem = Poem.objects.get(number=data["number"])
        self._check_markup(path.name, data["body"])
        poem.body, poem.pronunciation, poem.gaps = data["body"], data.get("pronunciation", []), data.get("gaps", [])
        poem.is_published = True
        poem.save()
        poem.target_units.set(LexicalUnit.objects.filter(uid__in=data.get("target_units", [])))
        return 1

    def _audio_manifest(self, *parts: str) -> dict:
        path = Path(settings.BASE_DIR) / "static" / "audio" / Path(*parts) / "manifest.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def load_weeks_plan(self, path: Path) -> int:
        if not path.exists():
            return 0
        weeks = yaml.safe_load(path.read_text(encoding="utf-8")).get("weeks", [])
        for item in weeks:
            week = Week.objects.get(level__code=item["level"], number=item["week"])
            week.situation_ru, week.sphere = item["situation_ru"], item["sphere"]
            week.grammar_ru, week.grammar_markers = item.get("grammar_ru", ""), item.get("grammar_markers", [])
            week.save()
        return len(weeks)

    def load_week(self, path: Path) -> int:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        week = Week.objects.select_related("level").get(level__code=data["level"], number=data["week"])
        roles = self._voice_roles()
        for line in data.get("script", []):
            if line["speaker"] not in roles:
                raise CommandError(f"{path.name}: роли {line['speaker']} нет в content/manifests/voices.yaml")
            self._check_markup(f"{path.name}: реплика", line["text"], line.get("spoken", ""))
        folder = f"{week.level.slug}-w{week.number:02d}"
        scene, _ = WeekScene.objects.update_or_create(week=week, defaults=dict(
            can_do_ru=data["can_do_ru"], mission_ru=data["mission_ru"], script=data.get("script", []),
            ambience=data.get("ambience", ""), audio=self._audio_manifest("weeks", folder)))
        scene.chunks.set(LexicalUnit.objects.filter(uid__in=data.get("chunks", [])))
        missing = set(data.get("chunks", [])) - set(scene.chunks.values_list("uid", flat=True))
        if missing:
            raise CommandError(f"{path.name}: незарегистрированные готовые фразы {sorted(missing)}")
        tw = data.get("twister")
        if tw:
            self._check_markup(f"{path.name}: скороговорка", tw["text"])
            TongueTwister.objects.filter(number=tw["number"]).exclude(week=week).delete()
            TongueTwister.objects.update_or_create(week=week, defaults=dict(
                number=tw["number"], series=tw["series"], text=tw["text"], ipa=tw.get("ipa", ""), ru=tw.get("ru", ""),
                focus_sounds=tw.get("focus_sounds", []), full_form=tw.get("full_form", ""), source=tw["source"],
                source_note=tw.get("source_note", ""), audio=self._audio_manifest("twisters", f"t{tw['number']:03d}")))
        else:
            TongueTwister.objects.filter(week=week).delete()
        return 1
