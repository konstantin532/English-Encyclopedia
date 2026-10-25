"""Rendered contextual noun/adverb labels; primary directional UID remains stable."""
from html.parser import HTMLParser
from django.test import TestCase
from django.urls import reverse
from apps.lexicon.models import LexicalUnit
from tests.runner import ensure_content

class SideLabels(HTMLParser):
    def __init__(self, layers_only=False):
        super().__init__(); self.span=None; self.layer=None; self.rows=[]; self.layers_only=layers_only
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag=='section' and attrs.get('id','').startswith('layer-'):
            self.layer=attrs['id']
        if tag=='span':self.span=attrs
    def handle_data(self,data):
        if (self.span and self.span.get('data-cat') and data.strip() in ('right','left')
                and (self.layer or not self.layers_only)):
            self.rows.append((data.strip(),self.span.get('data-cat'),self.span.get('data-cls'),self.span.get('data-label','')))
    def handle_endtag(self,tag):
        if tag=='span':self.span=None
        if tag=='section':self.layer=None

class A1SideContextTests(TestCase):
    @classmethod
    def setUpTestData(cls):ensure_content()
    def test_location_heads_are_nouns_but_turn_left_keeps_directional_adverb(self):
        for slug in ('a1-where-is-prepositions','a1-directions-turn-left'):
            with self.subTest(lesson=slug):
                page=self.client.get(reverse('lessons:detail',args=[slug]));self.assertEqual(page.status_code,200)
                parser=SideLabels(layers_only=True);parser.feed(page.content.decode())
                right=[r for r in parser.rows if r[0]=='right'];self.assertTrue(right)
                self.assertTrue(all(r[1:3]==('S','4') for r in right),right)
            if slug=='a1-directions-turn-left':
                left=[r for r in parser.rows if r[0]=='left'];self.assertTrue(left)
                self.assertTrue(all(r[1:3]==('A','3') for r in left),left)
    def test_dictionary_examples_show_side_nouns_without_reassigning_directional_uid(self):
        for uid,word in (('LX-00169','right'),('LX-00344','left')):
            with self.subTest(entry=uid):
                page=self.client.get(reverse('lexicon:detail',args=[uid]));self.assertEqual(page.status_code,200)
                parser=SideLabels();parser.feed(page.content.decode())
                matching=[r for r in parser.rows if r[0]==word and r[1:3]==('S','4')]
                self.assertTrue(matching,parser.rows)
        for uid in ('LX-00168','LX-00169'):
            with self.subTest(primary_directional_uid=uid):
                self.assertEqual(LexicalUnit.objects.get(uid=uid).semantic_class.class_id,'A3')
