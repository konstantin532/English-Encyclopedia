import copy
import json
from django.contrib.auth import get_user_model
from django.forms.models import model_to_dict
from django.test import TestCase
from django.urls import reverse
from apps.poems.admin import PoemEditorForm
from apps.poems.models import Poem


class PoemAuthoringTests(TestCase):
    def setUp(self):
        self.poem = Poem.objects.get(number=1)
        self.payload = {"body": self.poem.body, "pronunciation": copy.deepcopy(self.poem.pronunciation), "gaps": copy.deepcopy(self.poem.gaps)}
        self.data = model_to_dict(self.poem)
        self.data["target_units"] = list(self.poem.target_units.values_list("pk", flat=True))
        self.data["phonetic_goals"] = "\n".join(self.poem.phonetic_goals)

    def form(self):
        self.data["workshop"] = json.dumps(self.payload)
        return PoemEditorForm(data=self.data, instance=self.poem)

    def test_unchanged_round_trip_preserves_text_notes_and_gaps(self):
        form = self.form()
        self.assertTrue(form.is_valid(), form.errors)
        saved = form.save()
        saved.refresh_from_db()
        self.assertEqual(saved.body, self.payload["body"])
        self.assertEqual(saved.pronunciation, self.payload["pronunciation"])
        self.assertEqual(saved.gaps, self.payload["gaps"])

    def test_plain_text_draft_keeps_stanzas(self):
        self.payload = {"body": "New poem\nSecond line\n\nNew stanza", "pronunciation": [], "gaps": []}
        self.data["is_published"] = False
        form = self.form()
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save(commit=False).body, self.payload["body"])

    def test_invalid_gaps_and_pronunciation_rejected(self):
        for gaps in ([{"line": 999, "word": "home"}], [{"line": 1, "word": "missingword"}], [{"line": True, "word": "Good"}], [{"line": 1, "word": "Good"}, {"line": 1, "word": "morning"}]):
            self.payload["gaps"] = gaps
            self.assertFalse(self.form().is_valid())
        self.payload["gaps"] = []
        self.payload["pronunciation"] = [{"ipa": 123}]
        self.assertFalse(self.form().is_valid())

    def test_broken_markup_and_empty_publication_rejected(self):
        self.payload = {"body": "[S1]Broken", "pronunciation": [], "gaps": []}
        self.assertFalse(self.form().is_valid())
        self.payload["body"] = ""
        self.data["is_published"] = True
        self.assertFalse(self.form().is_valid())

    def test_admin_add_and_change_use_workshop_without_raw_fields(self):
        user = get_user_model().objects.create_superuser(email="poem-editor@example.com", password="test-only")
        self.client.force_login(user)
        for url in (reverse("admin:poems_poem_add"), reverse("admin:poems_poem_change", args=[self.poem.pk])):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            fields = response.context["adminform"].form.fields
            self.assertIn("workshop", fields)
            self.assertTrue(all(key not in fields for key in ("body", "pronunciation", "gaps")))
            self.assertContains(response, "admin-authoring.js")
