"""Accessibility contracts shared by registration, teacher and learner forms."""
from html.parser import HTMLParser

from django import forms
from django.template.loader import render_to_string
from django.test import SimpleTestCase


class Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


class AtlasFieldTests(SimpleTestCase):
    def test_assistive_description_resolves_help_and_validation_error(self):
        class AnswerForm(forms.Form):
            answer = forms.CharField(label="Ответ", help_text="Напишите свой ответ.")

        for data in (None, {"answer": ""}):
            with self.subTest(bound=data is not None):
                form = AnswerForm(data)
                parser = Elements()
                parser.feed(render_to_string("components/field.html", {"field": form["answer"]}))
                ids = {attrs["id"] for _, attrs in parser.elements if "id" in attrs}
                control = next(attrs for tag, attrs in parser.elements if tag == "input")
                references = control["aria-describedby"].split()
                self.assertTrue(references)
                self.assertTrue(set(references) <= ids, "Screen reader references must resolve")
                self.assertIn("id_answer_helptext", references)
                if data is not None:
                    self.assertEqual(control["aria-invalid"], "true")
                    self.assertIn("id_answer_error", references)

    def test_field_without_help_does_not_create_an_empty_description(self):
        class AnswerForm(forms.Form):
            answer = forms.CharField(label="Ответ")

        parser = Elements()
        parser.feed(render_to_string("components/field.html", {"field": AnswerForm()["answer"]}))
        control = next(attrs for tag, attrs in parser.elements if tag == "input")
        self.assertNotIn("aria-describedby", control)
