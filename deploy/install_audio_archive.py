"""Install optional external A1 audio at BUILD time, not during web requests.

Only a pinned HTTPS ZIP with static/audio/* contents is accepted.
A real TTS file is NOT evidence of manual pronunciation review.
"""
import hashlib
import os
import re
import shutil
import stat
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DOWNLOAD_LIMIT = 800_000_000
UNPACK_LIMIT = 1_500_000_000
FILE_LIMIT = 150_000_000


def safe_unpack(archive: Path, root: Path):
    output = (root / "static").resolve()
    total = 0
    found = 0
    with zipfile.ZipFile(archive) as package:
        records = package.infolist()
        if len(records) > 500:
            raise ValueError("Архив содержит слишком много файлов")
        for info in records:
            name = info.filename
            bits = Path(name)
            parts = bits.parts
            if (not parts or parts[:2] != ("static", "audio") or bits.is_absolute()
                    or any(x in ("", ".", "..") for x in parts) or "\\" in name):
                raise ValueError(f"Недопустимый путь в архиве: {name}")
            if stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError(f"Символическая ссылка в архиве: {name}")
            if info.is_dir():
                continue
            if info.file_size > FILE_LIMIT:
                raise ValueError("Слишком большой аудиофайл")
            total += info.file_size
            if total > UNPACK_LIMIT:
                raise ValueError("Слишком большой аудиоархив")
            target = (root / bits).resolve()
            if not target.is_relative_to(output):
                raise ValueError(f"Путь вышел за пределы static: {name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with package.open(info) as source, target.open("wb") as sink:
                shutil.copyfileobj(source, sink, length=1024 * 1024)
            found += 1
    if not found:
        raise ValueError("Пустой аудиоархив")
    return found


def install(root=ROOT, environ=None):
    env = os.environ if environ is None else environ
    url, wanted = env.get("A1_AUDIO_ARCHIVE_URL", ""), env.get("A1_AUDIO_ARCHIVE_SHA256", "")
    if not url and not wanted:
        print("A1 audio archive not configured; text-only deploy.")
        return False
    if not url or not re.fullmatch(r"[a-fA-F0-9]{64}", wanted):
        raise ValueError("Нужны оба параметра: A1_AUDIO_ARCHIVE_URL и полный SHA256")
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Архив можно скачать только по HTTPS без данных авторизации в URL")
    with tempfile.TemporaryDirectory() as temporary:
        zipped = Path(temporary) / "a1-audio.zip"
        digest = hashlib.sha256()
        received = 0
        request = urllib.request.Request(url, headers={"User-Agent": "EnglishEncyclopedia-Audio"})
        with urllib.request.urlopen(request, timeout=60) as response, zipped.open("wb") as file:
            while block := response.read(1024 * 1024):
                received += len(block)
                if received > DOWNLOAD_LIMIT:
                    raise ValueError("Архив превышает предел загрузки")
                digest.update(block)
                file.write(block)
        if digest.hexdigest() != wanted.lower():
            raise ValueError("SHA256 аудиоархива не совпадает")
        count = safe_unpack(zipped, root)
    # Publishing with a broken/incomplete audio archive would expose empty players.
    from scripts.audio_readiness import check_audio
    report = check_audio(root)
    if report["missing"] or report["invalid"]:
        raise ValueError("Аудиокомплект неполон или содержит тестовые/невалидные файлы")
    print(f"Installed {count} files; {report['files_present']} real Kokoro bundles. "
          f"Need human listening review: {len(report['unreviewed'])}.")
    return True


if __name__ == "__main__":
    try:
        install()
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        raise SystemExit(f"Cannot install A1 audio: {exc}")
