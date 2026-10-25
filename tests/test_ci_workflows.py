"""Workflow contract: scoped runs must not bypass existing check contexts."""
from pathlib import Path

import yaml
from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[1]


class ScopeWorkflowTests(SimpleTestCase):
    def workflow(self, name):
        return yaml.load((ROOT / '.github/workflows' / name).read_text(), Loader=yaml.BaseLoader)

    def test_existing_jobs_are_unconditionally_present(self):
        for filename, names in [('ci.yml', {'test', 'postgres'}),
                                ('quality-evolution.yml', {'coverage-and-fuzz', 'mutation-sentinels'})]:
            workflow = self.workflow(filename)
            self.assertEqual(set(workflow['jobs']), names)
            self.assertNotIn('paths', workflow['on'].get('pull_request') or {})
            self.assertNotIn('paths-ignore', workflow['on'].get('pull_request') or {})
            for job in workflow['jobs'].values():
                self.assertNotIn('if', job)

    def test_both_workflows_allow_manual_full_run(self):
        for filename in ['ci.yml', 'quality-evolution.yml']:
            self.assertIn('workflow_dispatch', self.workflow(filename)['on'])

    def test_selector_gets_event_and_explicit_pr_shas_without_shell_interpolation(self):
        for filename, job_names in [('ci.yml', ['test', 'postgres']),
                                    ('quality-evolution.yml', ['coverage-and-fuzz'])]:
            for name in job_names:
                steps = self.workflow(filename)['jobs'][name]['steps']
                checkout = next(s for s in steps if s.get('uses', '').startswith('actions/checkout@'))
                self.assertEqual(checkout['with']['fetch-depth'], '0')
                scope = next(s for s in steps if s.get('id') == 'scope')
                self.assertEqual(scope['env']['EVENT'], '${{ github.event_name }}')
                self.assertEqual(scope['env']['BASE_SHA'], '${{ github.event.pull_request.base.sha }}')
                self.assertEqual(scope['env']['HEAD_SHA'], '${{ github.event.pull_request.head.sha }}')
                self.assertIn('ci_scope.py plan', scope['run'])
                self.assertIn('set -o pipefail', scope['run'])
                self.assertNotIn('${{', scope['run'])

    def test_coverage_ratchet_only_uses_complete_suite(self):
        steps = self.workflow('quality-evolution.yml')['jobs']['coverage-and-fuzz']['steps']
        for name in ['Full test suite with branch coverage', 'Compare coverage and test count to baseline']:
            step = next(s for s in steps if s.get('name') == name)
            self.assertEqual(step['if'], "steps.scope.outputs.scope == 'full'")
        scoped = next(s for s in steps if s.get('name') == 'Scoped PR validation (not full coverage)')
        self.assertEqual(scoped['if'], "steps.scope.outputs.scope != 'full'")
        self.assertIn('ci_scope.py pytest', scoped['run'])
        self.assertNotIn('--cov', scoped['run'])

    def test_ci_preserves_scoped_suites_on_both_database_engines(self):
        for name in ['test', 'postgres']:
            steps = self.workflow('ci.yml')['jobs'][name]['steps']
            self.assertTrue(any('ci_scope.py pytest' in s.get('run', '') for s in steps))
        test = self.workflow('ci.yml')['jobs']['test']
        self.assertTrue(any('audit_course' in s.get('run', '') for s in test['steps']))
