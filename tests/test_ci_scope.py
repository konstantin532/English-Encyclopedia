"""Fail-closed CI routing; temporary real git repositories, never course data."""
import importlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

from django.test import SimpleTestCase


class ScopeTests(SimpleTestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('scripts.ci_scope'), 'CI scope selector must exist')
        self.scope = importlib.import_module('scripts.ci_scope')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git('init', '-q')
        self.git('config', 'user.name', 'Scope Test')
        self.git('config', 'user.email', 'scope@example.invalid')
        for name, value in {
            'README.md': 'docs',
            'apps/core/example.py': 'source',
            'templates/base.html': 'template',
            'tests/test_example.py': 'test',
            'content/active_a1/topics_01_08.json': '[]',
            'content/seed_weeks/a1_w01.yaml': 'level: A1',
            'docs/pilots/a1-four-weeks/assessment.yaml': 'runtime: fixture',
        }.items():
            self.write(name, value)
        self.base = self.commit()
        self.fingerprint = self.scope.dependency_fingerprint(self.root)

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], stderr=subprocess.PIPE).decode().strip()

    def write(self, name, value):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(value, encoding='utf-8')

    def commit(self):
        self.git('add', '.')
        self.git('commit', '-qm', 'fixture')
        return self.git('rev-parse', 'HEAD')

    def plan(self, head=None, base=None, event='pull_request'):
        return self.scope.plan(self.root, event, self.base if base is None else base,
                               head or self.git('rev-parse', 'HEAD'), self.fingerprint)

    def test_existing_prose_edit_gets_docs_checks(self):
        self.write('README.md', 'edited docs')
        self.assertEqual(self.plan(self.commit())['scope'], 'docs')

    def test_existing_active_json_keeps_affected_tests(self):
        self.write('content/active_a1/topics_01_08.json', '[{"changed":true}]')
        self.assertEqual(self.plan(self.commit())['scope'], 'active-a1')
        args = self.scope.pytest_command('active-a1', ['-q'])
        self.assertEqual(args[:3], [sys.executable, '-m', 'pytest'])
        self.assertEqual(sum(a.startswith('--deselect=') for a in args), 5)
        self.assertFalse(any('SpokenTests' in a or 'ContentTests' in a for a in args))

    def test_mixed_docs_and_active_runs_active_checks(self):
        self.write('README.md', 'new docs')
        self.write('content/active_a1/topics_01_08.json', '[1]')
        self.assertEqual(self.plan(self.commit())['scope'], 'active-a1')

    def test_code_seed_runtime_docs_and_unknown_paths_use_full(self):
        for path in ('apps/core/example.py', 'content/seed_weeks/a1_w01.yaml',
                     'docs/pilots/a1-four-weeks/assessment.yaml', 'docs/new-guide.md', 'unknown.txt'):
            with self.subTest(path=path):
                self.git('reset', '--hard', self.base)
                self.write(path, 'changed')
                self.assertEqual(self.plan(self.commit())['scope'], 'full')

    def test_added_deleted_renamed_and_symlink_files_use_full(self):
        self.write('content/active_a1/new.json', '[]')
        self.assertEqual(self.plan(self.commit())['scope'], 'full')
        self.git('reset', '--hard', self.base)
        (self.root / 'README.md').unlink()
        self.assertEqual(self.plan(self.commit())['scope'], 'full')
        self.git('reset', '--hard', self.base)
        self.git('mv', 'README.md', 'CLAUDE.md')
        self.assertEqual(self.plan(self.commit())['scope'], 'full')
        # Windows may require an elevated token to create a symlink. The raw
        # type-change diff is also covered platform-independently below.
        if os.name != 'nt':
            self.git('reset', '--hard', self.base)
            (self.root / 'README.md').unlink()
            (self.root / 'README.md').symlink_to('apps/core/example.py')
            self.assertEqual(self.plan(self.commit())['scope'], 'full')

    def test_non_pr_empty_and_bad_refs_use_full(self):
        for event in ('push', 'schedule', 'workflow_dispatch', 'merge_group', 'pull_request_target', ''):
            self.assertEqual(self.plan(event=event)['scope'], 'full')
        self.assertEqual(self.plan()['scope'], 'full')
        for ref in ('', '--help', 'main', '0' * 40, 'a' * 39, 'a' * 40 + '\nscope=docs'):
            self.assertEqual(self.plan(base=ref)['scope'], 'full')

    def test_uncommitted_dependency_and_later_dependency_drift_use_full(self):
        self.write('README.md', 'changed')
        head = self.commit()
        self.write('apps/core/example.py', 'uncommitted')
        self.assertEqual(self.plan(head)['scope'], 'full')
        newbase = self.commit()
        self.write('README.md', 'another edit')
        self.assertEqual(self.plan(self.commit(), base=newbase)['scope'], 'full')

    def test_incompatible_checkout_uses_full(self):
        self.write('README.md', 'changed')
        head = self.commit()
        self.git('checkout', '--detach', self.base)
        self.assertEqual(self.plan(head)['scope'], 'full')

    def test_unavailable_git_and_ambiguous_merge_base_use_full(self):
        self.write('README.md', 'changed')
        head = self.commit()
        real = self.scope.git_bytes
        def multiple(root, *args):
            if args[:2] == ('merge-base', '--all'):
                return (self.base + '\n' + head + '\n').encode()
            return real(root, *args)
        with patch.object(self.scope, 'git_bytes', side_effect=multiple):
            self.assertEqual(self.plan(head)['scope'], 'full')
        with patch.object(self.scope, 'git_bytes', side_effect=OSError('git unavailable')):
            self.assertEqual(self.plan(head)['scope'], 'full')

    def test_merge_base_diff_covers_old_feature_commits_and_accepts_merge_checkout(self):
        original_branch = self.git('branch', '--show-current')
        self.git('checkout', '-qb', 'feature')
        self.write('content/active_a1/topics_01_08.json', '[1]')
        head = self.commit()
        self.git('checkout', original_branch)
        self.write('CLAUDE.md', 'base-side new doc')
        base = self.commit()
        self.git('merge', '--no-ff', '-qm', 'merge checkout', 'feature')
        self.assertEqual(self.plan(head, base)['scope'], 'active-a1')

    def test_diff_parser_is_nul_delimited_and_rejects_unsafe_status(self):
        self.assertEqual(self.scope.classify_diff(b'M\0README.md\0'), 'docs')
        for raw in (b'M\0README.md\nscope=docs\0', b'R100\0README.md\0CLAUDE.md\0',
                    b'M\0README.md', b'\xff\0README.md\0', b'T\0README.md\0'):
            self.assertEqual(self.scope.classify_diff(raw), 'full')

    def test_runner_preserves_full_args_and_rejects_unknown_scope(self):
        self.assertEqual(self.scope.pytest_command('full', ['-q', '-rfE']),
                         [sys.executable, '-m', 'pytest', '-q', '-rfE'])
        with self.assertRaises(ValueError):
            self.scope.pytest_command('docs; touch /tmp/injected', [])
        docs = self.scope.pytest_command('docs', ['-q'])
        self.assertIn('tests/test_ci_scope.py', docs)
        self.assertIn('tests/test_docs.py', docs)
        self.assertIn('tests/test_tailscale_private.py', docs)
        self.assertIn('tests/test_ci_workflows.py', docs)

    def test_cli_plan_writes_safe_output(self):
        output = self.root / 'github-output'
        with patch.dict(os.environ, {'GITHUB_OUTPUT': str(output)}):
            self.assertEqual(self.scope.main(['plan', '--event', 'push']), 0)
        self.assertIn('scope=full\n', output.read_text())

    def test_new_tracked_dependency_invalidates_review(self):
        self.write('apps/core/new_dependency.py', 'new dependency')
        self.git('add', '.')
        self.assertNotEqual(self.scope.dependency_fingerprint(self.root), self.fingerprint)

    def test_root_hooks_and_new_support_modules_invalidate_review(self):
        for path in ('conftest.py', 'pytest.ini', 'setup.cfg', 'support/helper.py'):
            with self.subTest(path=path):
                self.git('reset', '--hard', self.base)
                self.write(path, 'new shared dependency')
                self.git('add', '.')
                self.assertNotEqual(self.scope.dependency_fingerprint(self.root), self.fingerprint)

    def test_new_base_root_hook_forces_subsequent_active_pr_full(self):
        self.write('conftest.py', 'import pytest\n# New global test hook\n')
        base = self.commit()
        self.write('content/active_a1/topics_01_08.json', '[1]')
        self.assertEqual(self.plan(self.commit(), base=base)['scope'], 'full')

    def test_selector_contract_files_are_also_dependency_guarded(self):
        self.write('tests/test_ci_scope.py', '# a new test hook')
        self.git('add', '.')
        self.assertNotEqual(self.scope.dependency_fingerprint(self.root), self.fingerprint)
