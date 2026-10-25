"""Rendered contrasts: turn right (adverb), right door (adjective), on the right (noun)."""
from html.parser import HTMLParser
from django.test import TestCase
from django.urls import reverse
from apps.poems.models import Poem
from tests.runner import ensure_content


class SharedSideFunctionTests(TestCase):
    @classmethod
    def setUpTestData(cls):ensure_content()

    def labels(self,response):
        self.assertEqual(response.status_code,200)
        class Parser(HTMLParser):
            def __init__(self):super().__init__();self.current=None;self.rows=[]
            def handle_starttag(self,tag,attrs):
                if tag=='span':self.current=dict(attrs)
            def handle_endtag(self,tag):
                if tag=='span':self.current=None
            def handle_data(self,text):
                if self.current and self.current.get('data-cat')and text.strip():
                    self.rows.append((text.strip().casefold(),self.current['data-cat'],self.current.get('data-label','')))
        p=Parser();p.feed(response.content.decode());return p.rows

    def sides(self,rows):
        return [rows[i+2]for i in range(len(rows)-2)
                if rows[i][0]=='on'and rows[i+1][0]in('the','your')and rows[i+2][0]in('right','left')]

    def test_week_distinguishes_side_nouns_direction_adverbs_and_correct_door_adjective(self):
        rows=self.labels(self.client.get(reverse('curriculum:week',args=['a1',8])))
        sides=self.sides(rows);self.assertGreaterEqual(len(sides),4)
        for side,category,label in sides:
            with self.subTest(side=side,label=label):
                self.assertEqual(category,'S');self.assertTrue(label.endswith('Места и город'),label)
        commands=[rows[i+1]for i in range(len(rows)-1)if rows[i][0]=='turn'and rows[i+1][0]in('right','left')]
        self.assertTrue(commands)
        self.assertTrue(all(cat=='A'and label.endswith('Место')for _,cat,label in commands),commands)
        right_door=[rows[i]for i in range(len(rows)-1)if rows[i][0]=='right'and rows[i+1][0]=='door']
        self.assertTrue(right_door)
        self.assertTrue(all(cat=='J'and label.endswith('Оценка')for _,cat,label in right_door),right_door)

    def test_poem_side_noun_contrasts_with_turn_adverbs_and_keeps_original_gap_solutions(self):
        response=self.client.get(reverse('stories:poem',args=[4]));rows=self.labels(response)
        sides=self.sides(rows);self.assertTrue(sides)
        self.assertTrue(all(cat=='S'and label.endswith('Места и город')for _,cat,label in sides),sides)
        directions=[rows[i+1]for i in range(len(rows)-1)if rows[i][0]=='turn'and rows[i+1][0]in('right','left')]
        self.assertTrue(directions);self.assertTrue(all(cat=='A'for _,cat,_ in directions),directions)
        poem=Poem.objects.get(number=4)
        self.assertEqual([(g['line'],g['word'])for g in poem.gaps],[(4,'me'),(6,'left'),(12,'right'),(15,'Whose'),(20,'key')])
        self.assertEqual(sum(r['gap']is not None for r in response.context['gapped']),5)
