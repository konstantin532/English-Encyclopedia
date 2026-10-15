"""Скачать целые файлы Kokoro; недокачанный файл не считается готовой моделью."""
import argparse
import hashlib
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
BASE_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
# Размеры: API выпуска model-files-v1.0. SHA256 модели также опубликован в
# https://github.com/nordwestt/kokoro-wyoming/blob/master/Dockerfile
# и https://huggingface.co/fastrtc/kokoro-onnx/blob/main/kokoro-v1.0.onnx
# SHA256 voices сверен с существующим полным архивом (28 214 398 байт).
ASSETS = {
    "kokoro-v1.0.onnx": (325532387, "7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5"),
    "voices-v1.0.bin": (28214398, "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d"),
}


def matches(path: Path, size: int, digest: str) -> bool:
    if not path.is_file() or path.stat().st_size != size:
        return False
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest() == digest


def ensure_asset(path: Path, url: str, size: int, digest: str) -> None:
    if matches(path, size, digest):
        print(f"Проверен: {path.name} (размер и SHA256).", flush=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Скачиваю заново: {path.name}, {size / 1_000_000:.1f} МБ…", flush=True)
    partial = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".part", delete=False) as output:
            partial = Path(output.name)
            request = Request(url, headers={"User-Agent": "English-Encyclopedia-audio"})
            with urlopen(request, timeout=60) as response:
                total, last_report = 0, 0
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > size:
                        raise ValueError(f"{path.name}: размер скачанного файла превышает ожидаемый.")
                    output.write(chunk)
                    if total - last_report >= 25_000_000:
                        print(f"  {total / 1_000_000:.0f} / {size / 1_000_000:.0f} МБ", flush=True)
                        last_report = total
        if not matches(partial, size, digest):
            raise ValueError(f"{path.name}: файл скачан не полностью или не совпадает SHA256. Повторите запуск.")
        partial.replace(path)
        print(f"Готово: {path.name} (размер и SHA256 совпали).", flush=True)
    finally:
        if partial is not None:
            partial.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", type=Path, default=ROOT / "models/kokoro")
    args = parser.parse_args()
    try:
        for name, (size, digest) in ASSETS.items():
            ensure_asset(args.models / name, BASE_URL + name, size, digest)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Не удалось подготовить модель: {error}\nПроверьте связь и снова запустите generate_audio.bat.\n")


if __name__ == "__main__":
    main()
