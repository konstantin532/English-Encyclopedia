#!/usr/bin/env python3
"""Conservative, fail-closed PR test selection; no shell evaluation or path globs.

Only existing prose and the reviewed A1 supplemental JSON are eligible. Unknown
paths, source drift, ambiguous git history and non-PR events use the full suite.
The five exclusions do not consume active_a1 data, directly or transitively.
All other tests (including new/unclassified tests) remain selected.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DOC_PATHS = frozenset({
    'README.md', 'CLAUDE.md', 'docs/CONTEXT.md', 'docs/lesson-review.md',
    'docs/operations/TAILSCALE_PRIVATE.md',
})
ACTIVE_PATHS = frozenset('content/active_a1/' + name for name in (
    'error_repairs_01_18.json', 'error_repairs_19_20.json',
    'error_repairs_21_22.json', 'error_repairs_23_24.json',
    'error_repairs_25_26.json', 'error_repairs_27_28.json',
    'scenarios_01_06.json', 'scenarios_07_12.json', 'scenarios_13_18.json',
    'scenarios_19_20.json', 'scenarios_21_22.json', 'scenarios_23_24.json',
    'scenarios_25_26.json', 'scenarios_27_28.json',
    'topics_01_08.json', 'topics_09_13.json', 'topics_14_18.json',
    'topics_19_20.json', 'topics_21_22.json', 'topics_23_24.json',
    'topics_25_26.json', 'topics_27_28.json',
))
# Reviewed on main 2a35c04. A mismatch disables selection, not the full suite.
# Refresh only after re-checking every exclusion's transitive dependencies.
REVIEWED_FINGERPRINT = 'ff513a1e206ff3de724bed2b0d915d5dcd724fa3fec874521f68250e09df3a75'
FINGERPRINT_EXCLUDES = frozenset({
    'scripts/ci_scope.py',  # self contains the fingerprint; changes route full by path
})
EXCLUDED_CLASSES = (
    'tests/test_adversarial_loader.py::InvalidSeedTests',
    'tests/test_audit_weeks.py::WeekAuditTests',
    'tests/test_adversarial_content.py::AuditSurfaceTests',
    'tests/test_story_pilot.py::StoryBeatTests',
    'tests/test_no_duplicate_words.py::DuplicateWordTests',
)
DOC_TESTS = ('tests/test_docs.py', 'tests/test_tailscale_private.py',
             'tests/test_ci_scope.py', 'tests/test_ci_workflows.py')
SHA = re.compile(r'[0-9a-f]{40}')


def git_bytes(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args],
                                   stderr=subprocess.PIPE, timeout=30)


def dependency_fingerprint(root):
    """Hash all tracked files except explicitly reviewed variable prose/A1 JSON.

    Unlike a filename rule, this invalidates the reviewed dependency boundary
    when a future source change makes a previously unrelated test read A1 JSON.
    Reads working bytes too, so local edits cannot retain an old fingerprint.
    """
    paths = git_bytes(root, 'ls-files', '-z').decode('utf-8').split('\0')
    digest = hashlib.sha256()
    for name in sorted(paths):
        if not name or name in FINGERPRINT_EXCLUDES | DOC_PATHS | ACTIVE_PATHS:
            continue
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('Dependency is missing or not a regular file')
        digest.update(name.encode('utf-8') + b'\0')
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def classify_diff(raw):
    """Only modifications of individually reviewed existing files are eligible."""
    try:
        fields = raw.decode('utf-8').split('\0')
    except UnicodeDecodeError:
        return 'full'
    if not raw or fields[-1] != '' or len(fields[:-1]) % 2:
        return 'full'
    active = False
    for status, name in zip(fields[0:-1:2], fields[1:-1:2]):
        if status != 'M':
            return 'full'
        if name in ACTIVE_PATHS:
            active = True
        elif name not in DOC_PATHS:
            return 'full'
    return 'active-a1' if active else 'docs'


def plan(root, event, base, head, expected_fingerprint=REVIEWED_FINGERPRINT):
    def full(reason):
        return {'scope': 'full', 'reason': reason}
    if event != 'pull_request':
        return full('Only pull_request events are eligible for scoped checks')
    if not SHA.fullmatch(base or '') or not SHA.fullmatch(head or ''):
        return full('Missing or invalid immutable base/head SHA')
    try:
        # Rev verification prevents absent shallow-history objects being trusted.
        for ref in (base, head):
            if git_bytes(root, 'rev-parse', '--verify', ref + '^{commit}').decode().strip() != ref:
                return full('Base/head is not an exact commit')
        checkout = git_bytes(root, 'rev-parse', 'HEAD').decode().strip()
        if checkout != head:
            parents = git_bytes(root, 'rev-list', '--parents', '-n', '1', 'HEAD').decode().split()
            if parents != [checkout, base, head]:
                return full('Checkout is neither PR head nor the expected test merge')
        if git_bytes(root, 'diff', '--name-only', 'HEAD', '--').strip():
            return full('Tracked checkout has local changes')
        bases = git_bytes(root, 'merge-base', '--all', base, head).decode().split()
        if len(bases) != 1 or not SHA.fullmatch(bases[0]):
            return full('Merge base is missing or ambiguous')
        raw = git_bytes(root, 'diff', '--no-renames', '--name-status', '-z', bases[0], head, '--')
        scope = classify_diff(raw)
        if scope == 'full':
            return full('Empty diff or changes outside reviewed existing prose/A1 JSON')
        if dependency_fingerprint(root) != expected_fingerprint:
            return full('Reviewed dependency fingerprint changed; full coverage required')
        return {'scope': scope, 'reason': 'Reviewed existing files only; dependency fingerprint matches'}
    except (OSError, ValueError, UnicodeError, subprocess.SubprocessError):
        return full('Cannot establish safe scope from git history and dependencies')


def pytest_command(scope, arguments):
    command = [sys.executable, '-m', 'pytest', *arguments]
    if scope == 'docs':
        command.extend(DOC_TESTS)
    elif scope == 'active-a1':
        command.extend('--deselect=' + node for node in EXCLUDED_CLASSES)
    elif scope != 'full':
        raise ValueError('Unknown CI scope')
    return command


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    planner = commands.add_parser('plan')
    planner.add_argument('--event', default='')
    planner.add_argument('--base', default='')
    planner.add_argument('--head', default='')
    runner = commands.add_parser('pytest')
    runner.add_argument('--scope', choices=('full', 'docs', 'active-a1'), required=True)
    runner.add_argument('arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.command == 'plan':
        result = plan(ROOT, args.event, args.base, args.head)
        print(json.dumps(result))
        if output := os.environ.get('GITHUB_OUTPUT'):
            with open(output, 'a', encoding='utf-8') as stream:
                # Values are internal constants; no filenames/user-controlled text.
                stream.write(f"scope={result['scope']}\nreason={result['reason']}\n")
        return 0
    forwarded = args.arguments[1:] if args.arguments[:1] == ['--'] else args.arguments
    return subprocess.call(pytest_command(args.scope, forwarded), cwd=ROOT)


if __name__ == '__main__':
    raise SystemExit(main())
