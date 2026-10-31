"""The desktop must not silently show another checkout or an old port owner."""
from contextlib import contextmanager, nullcontext
from io import StringIO
from pathlib import Path
import socket
import subprocess
import tempfile
from unittest import TestCase
from unittest.mock import Mock, patch

from scripts import local_start


class LocalServerTests(TestCase):
    def test_busy_port_does_not_start_or_open_a_browser(self):
        with socket.socket() as occupied:
            occupied.bind(('127.0.0.1', 0))
            occupied.listen()
            with patch.object(local_start.subprocess, 'Popen') as launch, patch.object(local_start.webbrowser, 'open') as browser:
                with self.assertRaisesRegex(RuntimeError, 'уже занят'):
                    local_start.serve(port=occupied.getsockname()[1])
                launch.assert_not_called()
                browser.assert_not_called()

    def test_dead_new_process_does_not_accept_old_health_response(self):
        process = Mock()
        process.poll.return_value = 1
        with patch.object(local_start, 'urlopen') as request:
            with self.assertRaisesRegex(RuntimeError, 'завершился'):
                local_start.wait_ready(process, 8000)
            request.assert_not_called()

    def test_healthy_response_from_another_owner_is_rejected(self):
        process = Mock()
        process.poll.return_value = None
        response = Mock(status=200)
        response.__enter__ = Mock(return_value=StringIO('{"status":"ok"}'))
        response.__exit__ = Mock(return_value=False)
        response.__enter__.return_value.status = 200
        with patch.object(local_start, 'urlopen', return_value=response), patch.object(local_start, 'owns_listener', return_value=False), patch.object(local_start.time, 'monotonic', side_effect=[0, 0, 0, 0, 1, 2]):
            with self.assertRaisesRegex(RuntimeError, 'вовремя'):
                local_start.wait_ready(process, 8000, timeout=1)

    def test_failed_readiness_cleans_own_process_and_never_opens_browser(self):
        process = Mock()
        with patch.object(local_start, 'ensure_free_port'), patch.object(local_start, 'record_server'), patch.object(local_start, 'clear_server_record'), patch.object(local_start.subprocess, 'Popen', return_value=process), patch.object(local_start, 'wait_ready', side_effect=RuntimeError('not ready')), patch.object(local_start, 'stop_owned') as stop, patch.object(local_start.webbrowser, 'open') as browser:
            with self.assertRaises(RuntimeError):
                local_start.serve()
            stop.assert_called_once_with(process)
            browser.assert_not_called()

    def test_browser_opens_only_after_new_server_is_confirmed(self):
        process = Mock()
        process.wait.return_value = 0
        events = []
        with patch.object(local_start, 'ensure_free_port'), patch.object(local_start, 'record_server'), patch.object(local_start, 'clear_server_record'), patch.object(local_start.subprocess, 'Popen', return_value=process), patch.object(local_start, 'wait_ready', side_effect=lambda *a: events.append('ready')), patch.object(local_start, 'stop_owned'), patch.object(local_start.webbrowser, 'open', side_effect=lambda *a: events.append('browser')):
            self.assertEqual(local_start.serve(), 0)
        self.assertEqual(events, ['ready', 'browser'])


class LocalUpdateTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.producer, self.remote, self.checkout = [self.root / name for name in ('producer', 'remote.git', 'checkout')]
        self.run_git('init', '--bare', str(self.remote))
        self.run_git('init', '-b', 'main', str(self.producer))
        self.run_git('-C', str(self.producer), 'config', 'user.name', 'Fixture')
        self.run_git('-C', str(self.producer), 'config', 'user.email', 'fixture@example.test')
        (self.producer / 'version.txt').write_text('old')
        self.run_git('-C', str(self.producer), 'add', 'version.txt')
        self.run_git('-C', str(self.producer), 'commit', '-m', 'base')
        self.run_git('-C', str(self.producer), 'remote', 'add', 'origin', str(self.remote))
        self.run_git('-C', str(self.producer), 'push', 'origin', 'main')
        self.run_git('clone', '-b', 'main', str(self.remote), str(self.checkout))
        self.run_git('-C', str(self.checkout), 'switch', '-c', 'completed-feature')
        self.run_git('-C', str(self.checkout), 'config', 'branch.completed-feature.remote', 'origin')
        self.run_git('-C', str(self.checkout), 'config', 'branch.completed-feature.merge', 'refs/heads/deleted-feature')
        (self.producer / 'version.txt').write_text('new')
        self.run_git('-C', str(self.producer), 'commit', '-am', 'merged update')
        self.run_git('-C', str(self.producer), 'push', 'origin', 'main')

    def run_git(self, *args):
        return subprocess.run([local_start.git_binary(), *args], check=True, capture_output=True, timeout=15)

    def test_deleted_feature_upstream_still_updates_from_merged_main(self):
        (self.checkout / 'private-untracked.txt').write_text('keep')
        self.assertEqual(local_start.sync_checkout(self.checkout), 'updated')
        self.assertEqual((self.checkout / 'version.txt').read_text(), 'new')
        self.assertEqual((self.checkout / 'private-untracked.txt').read_text(), 'keep')

    def test_uncommitted_work_is_preserved(self):
        (self.checkout / 'version.txt').write_text('local editing')
        self.assertEqual(local_start.sync_checkout(self.checkout), 'development')
        self.assertEqual((self.checkout / 'version.txt').read_text(), 'local editing')

    def test_fetch_failure_does_not_silently_launch_stale_code(self):
        self.run_git('-C', str(self.checkout), 'remote', 'set-url', 'origin', str(self.root / 'missing'))
        with self.assertRaises(subprocess.CalledProcessError):
            local_start.sync_checkout(self.checkout)


class ManagedRestartTests(TestCase):
    def test_unknown_listener_is_never_stopped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(local_start, 'ensure_free_port', side_effect=RuntimeError('busy')), patch.object(local_start, 'state_path', return_value=root / 'absent.json'), patch.object(local_start.subprocess, 'run') as run:
                with self.assertRaises(RuntimeError):
                    local_start.restart_managed_server(root, 8000)
                run.assert_not_called()

    def test_reused_pid_is_not_stopped(self):
        import json
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / 'server.json'
            state.write_text(json.dumps({'root': str(root.resolve()), 'port': 8000, 'pid': 123, 'stamp': 'old'}))
            with patch.object(local_start, 'IS_WINDOWS', True), patch.object(local_start, 'pin_process', return_value=nullcontext()), patch.object(local_start, 'ensure_free_port', side_effect=RuntimeError('busy')), patch.object(local_start, 'state_path', return_value=state), patch.object(local_start, 'process_stamp', return_value='new'), patch.object(local_start.subprocess, 'run') as run:
                with self.assertRaises(RuntimeError):
                    local_start.restart_managed_server(root, 8000)
                run.assert_not_called()

    def test_only_matching_project_and_own_process_tree_is_restarted(self):
        import json
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / 'server.json'
            state.write_text(json.dumps({'root': str(root.resolve()), 'port': 8000, 'pid': 123, 'stamp': 'same'}))
            with patch.object(local_start, 'IS_WINDOWS', True), patch.object(local_start, 'pin_process', return_value=nullcontext()), patch.object(local_start, 'ensure_free_port', side_effect=[RuntimeError('busy'), None]), patch.object(local_start, 'state_path', return_value=state), patch.object(local_start, 'process_stamp', return_value='same'), patch.object(local_start, 'owns_listener', return_value=True), patch.object(local_start.subprocess, 'run') as run:
                local_start.restart_managed_server(root, 8000)
                self.assertEqual(run.call_args.args[0], ['taskkill', '/PID', '123', '/T', '/F'])


class MissingOwnerIdentityTests(TestCase):
    def test_missing_creation_stamp_never_authorizes_a_stop(self):
        import json
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / 'server.json'
            state.write_text(json.dumps({'root': str(root.resolve()), 'port': 8000, 'pid': 123}))
            with patch.object(local_start, 'IS_WINDOWS', True), patch.object(local_start, 'pin_process', return_value=nullcontext()), patch.object(local_start, 'ensure_free_port', side_effect=RuntimeError('busy')), patch.object(local_start, 'state_path', return_value=state), patch.object(local_start, 'process_stamp', return_value=None), patch.object(local_start, 'owns_listener', return_value=True), patch.object(local_start.subprocess, 'run') as run:
                with self.assertRaises(RuntimeError):
                    local_start.restart_managed_server(root, 8000)
                run.assert_not_called()


class ProcessPinTests(TestCase):
    def test_owner_is_pinned_before_identity_check_until_stop_finishes(self):
        import json
        events = []
        @contextmanager
        def pin(pid):
            events.append('pinned')
            try:
                yield
            finally:
                events.append('released')
        def stamp(pid):
            self.assertEqual(events, ['pinned'])
            return 'same'
        def stop(*args, **kwargs):
            self.assertEqual(events, ['pinned'])
            events.append('stopped')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / 'server.json'
            state.write_text(json.dumps({'root': str(root.resolve()), 'port': 8000, 'pid': 123, 'stamp': 'same'}))
            with patch.object(local_start, 'IS_WINDOWS', True), patch.object(local_start, 'ensure_free_port', side_effect=[RuntimeError('busy'), None]), patch.object(local_start, 'state_path', return_value=state), patch.object(local_start, 'pin_process', side_effect=pin), patch.object(local_start, 'process_stamp', side_effect=stamp), patch.object(local_start, 'owns_listener', return_value=True), patch.object(local_start.subprocess, 'run', side_effect=stop):
                local_start.restart_managed_server(root, 8000)
            self.assertEqual(events, ['pinned', 'stopped', 'released'])
