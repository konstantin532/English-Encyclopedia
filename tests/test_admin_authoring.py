"""Regression checks for human-facing admin authoring and safe reloads."""
import copy
import json
from django.contrib import admin
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.forms.models import model_to_dict
from django.test import RequestFactory, TestCase, tag
from django.urls import reverse
from apps.lessons.models import Lesson
from apps.lessons.admin import ExerciseEditorForm, LessonEditorForm
from apps.poems.models import Poem
from apps.stories.models import Story
from apps.stories.admin import StoryEditorForm
from apps.core.admin_widgets import StringListField


def story_data(story):
    data = model_to_dict(story)
    data["new_units"] = [unit.pk for unit in story.new_units.all()]
    data["focus"] = list(story.focus)
    for name in ("script", "questions", "phrase_hunt", "audio"):
        data[name] = json.dumps(data[name], ensure_ascii=False)
    return data


class AuthoringTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(email="authoring-owner@example.com", password="test-only")

    def test_story_round_trip_preserves_script_metadata(self):
        story = Story.objects.get(number=1)
        form = StoryEditorForm(data=story_data(story), instance=story)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["script"], story.script)
        self.assertEqual(form.cleaned_data["questions"], story.questions)

    def test_bad_script_structure_and_unknown_role_are_rejected(self):
        story = Story.objects.get(number=1)
        for script in ({"text": "hello"}, ["broken"], [{"speaker": "unknown", "text": "Hello"}], [{"speaker": "anna", "text": "[S1]Anna"}]):
            data = story_data(story)
            data["script"] = json.dumps(script)
            form = StoryEditorForm(data=data, instance=story)
            self.assertFalse(form.is_valid())
            self.assertIn("script", form.errors)

    def test_new_plain_text_can_be_saved_as_draft(self):
        story = Story.objects.get(number=1)
        data = story_data(story)
        data["script"] = json.dumps([{"speaker": "anna", "text": "My new story."}])
        data["is_published"] = False
        form = StoryEditorForm(data=data, instance=story)
        self.assertTrue(form.is_valid(), form.errors)

    def test_save_rebuilds_body_and_clears_stale_audio(self):
        story = Story.objects.get(number=1)
        story.audio = {"old": "audio"}
        data = story_data(story)
        script = copy.deepcopy(story.script)
        script[0]["text"] += " New text."
        data["script"] = json.dumps(script)
        form = StoryEditorForm(data=data, instance=story)
        self.assertTrue(form.is_valid(), form.errors)
        obj = form.save(commit=False)
        request = RequestFactory().post("/admin/")
        request.user = self.user
        from unittest.mock import patch
        model_admin = admin.site._registry[Story]
        with patch.object(model_admin, "message_user"):
            model_admin.save_model(request, obj, form, True)
        obj.refresh_from_db()
        self.assertEqual(obj.body, "\n\n".join(row["text"] for row in script))
        self.assertEqual(obj.audio, {})
        self.assertNotIn("spoken", obj.script[0])

    def test_lines_replace_json_lists(self):
        field = StringListField(required=False)
        self.assertEqual(field.clean("one\ntwo\n\nthree"), ["one", "two", "three"])
        self.assertEqual(field.prepare_value(["one", "two"]), "one\ntwo")

    def test_admin_hides_audio_payload_and_renders_editor(self):
        self.client.force_login(self.user)
        story = Story.objects.get(number=1)
        response = self.client.get(reverse("admin:stories_story_change", args=[story.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "admin-authoring.js")
        self.assertNotIn("audio", response.context["adminform"].form.fields)
        self.assertContains(response, "Пишите историю, а не код.")
        lesson = self.client.get(reverse("admin:lessons_lesson_add"))
        self.assertEqual(lesson.status_code, 200)
        self.assertContains(lesson, "Семь разделов объяснения")
        self.assertContains(lesson, "admin-authoring.js")

    def test_malformed_record_list_has_human_error(self):
        field = LessonEditorForm.base_fields["contractions"]
        with self.assertRaisesMessage(Exception, "Сокращённая форма"):
            field.clean('[{"full":"I am"}]')


@tag("slow")
class PreserveAdminEditsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_superuser(email="reload-owner@example.com", password="test-only")

    def test_normal_startup_preserves_saved_story_and_lesson(self):
        story = Story.objects.get(number=1)
        lesson = Lesson.objects.first()
        story.title = "Редакторская история"
        story.script = [{"speaker": "anna", "text": "Admin saved text."}]
        story.body = "Admin saved text."
        story.audio = {}
        story.save()
        lesson.title = "Редакторский урок"
        lesson.save()
        layer = lesson.layers.first()
        layer.body = "Изменено редактором"
        layer.save()
        poem = Poem.objects.get(number=1)
        poem.title = "Редакторский стих"
        poem.body = "Admin poem text."
        poem.save()
        for obj in (story, lesson, poem):
            LogEntry.objects.create(user=self.user, content_type=ContentType.objects.get_for_model(obj), object_id=str(obj.pk), object_repr=str(obj), action_flag=CHANGE)
        call_command("load_content", preserve_admin_edits=True, verbosity=0)
        story.refresh_from_db()
        lesson.refresh_from_db()
        layer.refresh_from_db()
        self.assertEqual(story.title, "Редакторская история")
        self.assertEqual(story.body, "Admin saved text.")
        self.assertEqual(story.script, [{"speaker": "anna", "text": "Admin saved text."}])
        self.assertEqual(story.audio, {})
        self.assertEqual(lesson.title, "Редакторский урок")
        self.assertEqual(layer.body, "Изменено редактором")
        poem.refresh_from_db()
        self.assertEqual(poem.title, "Редакторский стих")
        self.assertEqual(poem.body, "Admin poem text.")
        # Explicit seed import still retains its documented authoritative behavior.
        call_command("load_content", verbosity=0)
        story.refresh_from_db()
        self.assertNotEqual(story.title, "Редакторская история")
        poem.refresh_from_db()
        self.assertNotEqual(poem.title, "Редакторский стих")
