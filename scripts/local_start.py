"""Windows start.bat support: explicit main updates and an owned, ready server."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.request import urlopen
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
IS_WINDOWS = os.name == 'nt'


def git_binary():
    installed = Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Git/cmd/git.exe'
    return str(installed) if IS_WINDOWS and installed.is_file() else shutil.which('git')


def git(root, *args, check=True):
    return subprocess.run(
        [git_binary(), '-c', f'safe.directory={root.as_posix()}', '-C', str(root), *args],
        text=True, encoding='utf-8', capture_output=True, check=check, timeout=45,
    )


def sync_checkout(root=ROOT):
    if not (root / '.git').exists() or not git_binary():
        print('Запуск локальной копии без Git. Автоматического обновления нет.')
        return 'local'
    # No implicit upstream: completed PR branches may already be deleted remotely.
    git(root, 'fetch', 'origin', 'main')
    dirty = git(root, 'status', '--porcelain', '--untracked-files=no').stdout.strip()
    ancestor = git(root, 'merge-base', '--is-ancestor', 'HEAD', 'origin/main', check=False)
    if ancestor.returncode not in (0, 1):
        ancestor.check_returncode()
    if not dirty and ancestor.returncode == 0:
        git(root, 'merge', '--ff-only', 'origin/main')
        mode = 'updated'
        print('Загружена уже слитая автором версия main.')
    else:
        mode = 'development'
        print('Рабочая ветка с локальными изменениями. Автообновление пропущено; правки сохранены.')
    branch = git(root, 'branch', '--show-current').stdout.strip() or 'detached HEAD'
    version = git(root, 'rev-parse', '--short', 'HEAD').stdout.strip()
    print(f'Папка: {root}\nВетка: {branch}\nВерсия: {version}')
    return mode


def ensure_free_port(port):
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1', port)) == 0:
            raise RuntimeError(f'Порт {port} уже занят. Завершите предыдущий локальный сервер. Другой сайт не будет открыт.')


def state_path(root, port):
    key = hashlib.sha256(str(root.resolve()).casefold().encode()).hexdigest()[:16]
    folder = Path(os.environ.get('LOCALAPPDATA', Path.home() / '.local/share')) / 'EnglishEncyclopedia/run'
    return folder / f'{key}-{port}.json'


def process_stamp(pid):
    if not IS_WINDOWS or int(pid) <= 0:
        return None
    command = f'(Get-Process -Id {int(pid)} -ErrorAction SilentlyContinue).StartTime.ToUniversalTime().Ticks'
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
                            capture_output=True, text=True, timeout=5)
    return result.stdout.strip() if result.returncode == 0 else None


def record_server(root, process, port):
    if not IS_WINDOWS:
        return
    stamp = process_stamp(process.pid)
    if not stamp:
        raise RuntimeError('Не удалось записать владельца локального сервера.')
    path = state_path(root, port)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.with_suffix('.tmp').write_text(json.dumps({'root': str(root.resolve()), 'port': port,
                                                  'pid': process.pid, 'stamp': stamp}), encoding='utf-8')
    path.with_suffix('.tmp').replace(path)


def clear_server_record(root, process, port):
    path = state_path(root, port)
    if path.exists() and json.loads(path.read_text(encoding='utf-8')).get('pid') == process.pid:
        path.unlink()


@contextmanager
def pin_process(pid):
    """Keep the verified Windows process object alive so its PID cannot be reused.

    https://learn.microsoft.com/windows/win32/api/processthreadsapi/ns-processthreadsapi-process_information
    """
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        yield
    finally:
        kernel.CloseHandle(handle)


def restart_managed_server(root, port):
    try:
        ensure_free_port(port)
        return
    except RuntimeError:
        pass
    path = state_path(root, port)
    if not IS_WINDOWS or not path.exists():
        raise RuntimeError(f'Порт {port} занят неизвестным сервером. Он не будет остановлен или открыт.')
    data = json.loads(path.read_text(encoding='utf-8'))
    pid = int(data['pid'])
    from types import SimpleNamespace
    if (str(data.get('root', '')).casefold() != str(root.resolve()).casefold()
            or data.get('port') != port or not data.get('stamp') or pid <= 0):
        raise RuntimeError(f'Запись владельца порта {port} не соответствует проекту.')
    # Pin before checking identity; hold through taskkill to prevent PID reuse.
    with pin_process(pid):
        owned = (process_stamp(pid) == data['stamp']
                 and owns_listener(SimpleNamespace(pid=pid), port, 15))
        if not owned:
            raise RuntimeError(f'Владелец порта {port} изменился. Чужой процесс не остановлен.')
        subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'], check=True, capture_output=True, timeout=10)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            ensure_free_port(port)
            print('Предыдущий собственный сервер остановлен для обновления.')
            return
        except RuntimeError:
            time.sleep(.1)
    raise RuntimeError('Предыдущий сервер ещё освобождает порт. Запустите снова.')


def owns_listener(process, port, timeout):
    if not IS_WINDOWS:
        return process.poll() is None
    # Follow the runserver autoreloader/venv child back to our Popen handle.
    command = (
        f'$owner=(Get-NetTCPConnection -State Listen -LocalPort {port} -ErrorAction SilentlyContinue '
        '| Select-Object -First 1 -ExpandProperty OwningProcess); '
        'for($i=0;$i -lt 12 -and $owner;$i++){'
        f'if($owner -eq {process.pid}){{exit 0}}; '
        '$owner=(Get-CimInstance Win32_Process -Filter "ProcessId=$owner").ParentProcessId}; exit 1'
    )
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
                            capture_output=True, timeout=timeout)
    return result.returncode == 0


def wait_ready(process, port, timeout=45):
    deadline = time.monotonic() + timeout
    url = f'http://127.0.0.1:{port}/healthz/'
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError('Новый сервер завершился до запуска. Браузер не открыт.')
        try:
            remaining = max(.01, deadline - time.monotonic())
            with urlopen(url, timeout=min(1, remaining)) as response:
                healthy = response.status == 200 and json.load(response).get('status') == 'ok'
            remaining = max(.01, deadline - time.monotonic())
            if healthy and owns_listener(process, port, min(12, remaining)) and process.poll() is None:
                return
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass
        time.sleep(min(.1, max(0, deadline - time.monotonic())))
    raise RuntimeError('Сервер не подтвердил готовность вовремя. Браузер не открыт.')


def stop_owned(process):
    if process.poll() is not None:
        return
    if IS_WINDOWS:
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True, timeout=10)
    else:
        process.terminate()
    process.wait(timeout=10)


def serve(root=ROOT, port=8000, *, smoke=False, no_browser=False):
    ensure_free_port(port)
    command = [sys.executable, 'manage.py', 'runserver', f'127.0.0.1:{port}']
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if IS_WINDOWS else 0
    process = subprocess.Popen(command, cwd=root, creationflags=flags)
    try:
        wait_ready(process, port)
        record_server(root, process, port)
        print(f'Готовность нового сервера подтверждена: http://127.0.0.1:{port}', flush=True)
        if smoke:
            return 0
        if not no_browser:
            webbrowser.open(f'http://127.0.0.1:{port}')
        return process.wait()
    finally:
        stop_owned(process)
        clear_server_record(root, process, port)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('sync', 'serve'))
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--smoke-test', action='store_true')
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args(argv)
    try:
        if not 1 <= args.port <= 65535:
            raise ValueError('Неверный порт')
        if args.action == 'sync':
            restart_managed_server(ROOT, args.port)
            sync_checkout()
            return 0
        return serve(port=args.port, smoke=args.smoke_test, no_browser=args.no_browser)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f'Запуск остановлен: {error}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
