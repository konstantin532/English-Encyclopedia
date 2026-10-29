"""Week-one opening changes presentation while keeping the learning route intact."""
from html.parser import HTMLParser
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.curriculum.models import Week, WeekScene
from apps.curriculum.views import week_art
from apps.learning.models import WeekGoal
from tests.runner import ensure_content


class _Element:
    def __init__(self, tag, attrs=()):
        self.tag = tag
        self.attrs = dict(attrs)
        self.children = []

    def descendants(self):
        for child in self.children:
            if isinstance(child, _Element):
                yield child
                yield from child.descendants()

    @property
    def text(self):
        return "".join(child.text if isinstance(child, _Element) else child
                       for child in self.children)

    def find_all(self, tag=None, attrs=None):
        return [node for node in self.descendants()
                if (tag is None or node.tag == tag)
                and all(name in node.attrs and (value is None or node.attrs[name] == value)
                        for name, value in (attrs or {}).items())]


class _Page(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, markup):
        super().__init__(convert_charrefs=True)
        self.root = _Element("document")
        self.stack = [self.root]
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        node = _Element(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


class WeekOneCoverTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_content()
        cls.week = Week.objects.select_related("level").get(level__code="A1", number=1)
        cls.scene = WeekScene.objects.get(week=cls.week)

    def get_page(self, slug="a1", number=1):
        response = self.client.get(reverse("curriculum:week", args=[slug, number]))
        self.assertEqual(response.status_code, 200)
        return response, _Page(response.content.decode()).root

    def one(self, root, tag=None, attrs=None):
        found = root.find_all(tag, attrs)
        self.assertEqual(len(found), 1, (tag, attrs, len(found)))
        return found[0]

    def test_cover_opens_with_existing_art_then_one_title_and_one_scene_intro(self):
        _, page = self.get_page()
        cover = self.one(page, "header", {"data-week-one-chapter": None})
        image = self.one(cover, "img")
        title = self.one(page, "h1")
        self.assertIn(title, cover.find_all("h1"))
        self.assertEqual(image.attrs["src"], week_art("A1", 1)["large"])
        self.assertTrue(image.attrs.get("alt", "").strip())
        elements = list(cover.descendants())
        self.assertLess(elements.index(image), elements.index(title))
        self.assertEqual(title.text.strip(), self.week.situation_ru)
        intro = self.scene.story_beat["intro_ru"]
        self.assertEqual(cover.text.count(intro), 1)
        self.assertEqual(page.text.count(intro), 1)
        self.assertNotIn(intro, self.one(page, "section", {"id": "dialogue"}).text)
        self.one(cover, "a", {"href": reverse("curriculum:level", args=["a1"])})

    def test_chapter_opening_is_scoped_to_a1_week_one(self):
        for slug, number in (("a1", 2), ("a1", 3), ("a1-plus", 1)):
            with self.subTest(level=slug, week=number):
                _, page = self.get_page(slug, number)
                self.assertEqual(page.find_all(attrs={"data-week-one-chapter": None}), [])
                self.one(page, "h1")
                self.one(page, "section", {"id": "dialogue"})

    def test_guest_keeps_route_goal_form_and_working_audio_controls(self):
        audio = {
            "slow": {"file": "audio/week-one-slow.mp3", "timings": [{"start": 0, "end": 1}]},
            "natural": {"file": "audio/week-one-natural.mp3", "timings": [{"start": 0, "end": 1}]},
        }
        WeekScene.objects.filter(pk=self.scene.pk).update(audio=audio)
        response, page = self.get_page()
        blocks = ("goal", "dialogue", "lessons", "chunks", "role", "twister", "mission", "review")
        sections = [self.one(page, "section", {"id": name}) for name in blocks]
        order = list(page.descendants())
        self.assertEqual([order.index(section) for section in sections],
                         sorted(order.index(section) for section in sections))
        route = [node for node in page.find_all("aside")
                 if "week-route" in node.attrs.get("class", "").split()]
        self.assertEqual(len(route), 1)
        links = {link.attrs.get("href") for link in route[0].find_all("a")}
        self.assertTrue({"#" + name for name in blocks}.issubset(links))
        goal = self.one(page, "section", {"id": "goal"})
        form = self.one(goal, "form", {"data-guest-week-goal": None})
        self.assertEqual(form.attrs["method"].lower(), "post")
        self.assertEqual(form.attrs["action"], reverse("api:guest_week_goal", args=[self.week.pk]))
        self.assertEqual(form.attrs["data-guest-goal-key"], f"goal:{self.week.pk}")
        self.assertEqual({button.attrs.get("value") for button in form.find_all("button")},
                         {"done", "not_yet"})
        dialogue = self.one(page, "section", {"id": "dialogue"})
        transcript = self.one(dialogue, attrs={"data-script-lines": None})
        self.assertEqual(len(transcript.find_all(attrs={"data-line": None})), len(response.context["lines"]))
        self.one(dialogue, attrs={"data-listen-modes": None})
        player = self.one(dialogue, attrs={"data-story-player": None})
        self.assertTrue(player.attrs["data-slow"].endswith(audio["slow"]["file"]))
        self.assertTrue(player.attrs["data-natural"].endswith(audio["natural"]["file"]))
        self.one(player, "button", {"data-play": None})
        self.one(self.one(page, "section", {"id": "role"}), "select", {"data-role-mute": None})

    def test_signed_in_learner_keeps_personal_goal_post_and_single_cover(self):
        user = User.objects.create_user("week-cover@example.test", "strong-test-password-123")
        self.client.force_login(user)
        _, page = self.get_page()
        self.one(page, "header", {"data-week-one-chapter": None})
        self.assertEqual(page.find_all(attrs={"data-guest-week-goal": None}), [])
        url = reverse("learning:week_goal", args=[self.week.pk])
        form = self.one(self.one(page, "section", {"id": "goal"}), "form", {"action": url})
        self.assertEqual(form.attrs["method"].lower(), "post")
        self.one(form, "input", {"name": "csrfmiddlewaretoken"})
        response = self.client.post(url, {"status": "done"})
        self.assertRedirects(response, reverse("curriculum:week", args=["a1", 1]))
        self.assertEqual(WeekGoal.objects.get(user=user, week=self.week).status, "done")

    def test_missing_intro_or_art_keeps_a_readable_opening_without_broken_image(self):
        WeekScene.objects.filter(pk=self.scene.pk).update(story_beat={})
        with patch("apps.curriculum.views.week_art", return_value=None):
            _, page = self.get_page()
        cover = self.one(page, "header", {"data-week-one-chapter": None})
        self.assertEqual(self.one(page, "h1").text.strip(), self.week.situation_ru)
        self.assertEqual(cover.find_all(attrs={"id": "story-intro"}), [])
        for image in cover.find_all("img"):
            self.assertTrue(image.attrs.get("src", "").strip())
            self.assertNotIn(image.attrs["src"].lower(), {"none", "null", "undefined"})
        self.one(page, "section", {"id": "goal"})
        self.one(self.one(page, "section", {"id": "dialogue"}), attrs={"data-script-lines": None})
