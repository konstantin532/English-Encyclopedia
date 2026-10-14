"""Озвучка историй по ролям + фон сцены.

Запуск (обычно через generate_audio.bat):
    uv run python scripts/generate_story_audio.py --all
    uv run python scripts/generate_story_audio.py --story 1
    uv run python scripts/generate_story_audio.py --story 1 --engine test   # без модели, для проверки

Что получается для истории N (static/audio/stories/sNN/):
    voice_very_slow.*  очень медленно, длинные паузы — для тех, кто впервые слышит английский
    voice_slow.*       медленно (фон по умолчанию выключен)
    voice_natural.*    обычный темп «как в жизни»
    manifest.json    голоса, тайминги реплик для подсветки, громкость фона, статус проверки
Фон сцены — отдельный зацикленный файл static/audio/ambience/<scene>.*: громкость голоса
и фона ученик регулирует отдельно.

Голоса синтезированы: verified=false, пока произношение не прослушал человек.
"""
import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
OUT = ROOT / "static" / "audio"
MODELS = ROOT / "models" / "kokoro"
SR = 24000
TOKEN = re.compile(r"\[[SDJANTPXCOF]\d{1,2}(?:-#[0-9a-fA-F]{6})?\](.+?)\[/\]", re.S)
# Темпы: (коэффициент скорости голоса, множитель пауз между репликами)
TEMPOS = {"very_slow": (0.7, 2.0), "slow": (0.85, 1.3), "natural": (1.0, 1.0)}


def plain(text: str) -> str:
    text = TOKEN.sub(lambda m: m.group(1), text)
    return re.sub(r"[“”\"]", "", text).strip()


# ---------- движки синтеза ----------

class KokoroEngine:
    name = "kokoro"

    def __init__(self, models_dir: Path):
        try:
            from kokoro_onnx import Kokoro
        except ImportError:
            sys.exit("Нет пакета kokoro-onnx. Запустите generate_audio.bat — он всё установит.")
        model, voices = models_dir / "kokoro-v1.0.onnx", models_dir / "voices-v1.0.bin"
        if not model.exists() or not voices.exists():
            sys.exit(f"Нет файлов модели в {models_dir}. Запустите generate_audio.bat — он их скачает.")
        self.tts = Kokoro(str(model), str(voices))
        self.available = set(self.tts.get_voices())

    def check_voice(self, voice: str) -> None:
        if voice not in self.available:
            sys.exit(f"Голоса {voice} нет в модели. Доступны: {', '.join(sorted(self.available))}")

    def synth(self, text: str, voice: str, speed: float) -> np.ndarray:
        samples, rate = self.tts.create(text, voice=voice, speed=speed, lang="en-us")
        samples = np.asarray(samples, dtype=np.float32)
        if rate != SR:  # простая передискретизация на случай другой частоты модели
            x = np.linspace(0, len(samples) - 1, int(len(samples) * SR / rate))
            samples = np.interp(x, np.arange(len(samples)), samples).astype(np.float32)
        return samples


class TestEngine:
    """Без модели: тон вместо речи, длина пропорциональна тексту. Только для проверки конвейера."""

    name = "test"

    def check_voice(self, voice: str) -> None:
        pass

    def synth(self, text: str, voice: str, speed: float) -> np.ndarray:
        dur = max(0.4, 0.065 * len(text) / speed)
        t = np.arange(int(dur * SR)) / SR
        pitch = 180 + (sum(map(ord, voice)) % 120)
        return (0.3 * np.sin(2 * np.pi * pitch * t) * np.hanning(len(t))).astype(np.float32)


# ---------- обработка звука ----------

def rms_normalize(x: np.ndarray, target_db: float = -20.0) -> np.ndarray:
    rms = np.sqrt(np.mean(x ** 2)) or 1e-9
    y = x * (10 ** (target_db / 20) / rms)
    peak = np.max(np.abs(y)) or 1
    return (y / peak * 0.95 if peak > 0.95 else y).astype(np.float32)


def one_pole(x: np.ndarray, cutoff: float) -> np.ndarray:
    """Простой фильтр нижних частот без scipy."""
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def old_radio(x: np.ndarray) -> np.ndarray:
    """Эффект старой записи: узкая полоса частот и лёгкое шипение."""
    band = one_pole(x, 3400) - one_pole(x, 300)
    hiss = np.random.default_rng(7).normal(0, 0.004, len(x)).astype(np.float32)
    return (np.tanh(band * 2.2) * 0.6 + hiss).astype(np.float32)


def ambience_morning_home(seconds: float = 30.0) -> np.ndarray:
    """Временный синтетический фон «утро в доме»: тихий гул комнаты, далёкий город, редкие птицы.

    Заглушка до лицензированных записей (см. content/source_registry.yaml).
    """
    rng = np.random.default_rng(42)
    n = int(seconds * SR)
    brown = np.cumsum(rng.normal(0, 1, n)).astype(np.float32)
    brown -= one_pole(brown, 2)  # убираем дрейф
    room = one_pole(brown, 400) * 0.02
    city = one_pole(rng.normal(0, 1, n).astype(np.float32), 180) * 0.6
    out = room + city
    for start in rng.uniform(1, seconds - 2, 9):  # короткие «чирики» 3–5 кГц
        dur = rng.uniform(0.08, 0.18)
        t = np.arange(int(dur * SR)) / SR
        f = np.linspace(rng.uniform(3000, 4200), rng.uniform(4200, 5200), len(t))
        chirp = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.hanning(len(t)) * 0.08
        i = int(start * SR)
        out[i:i + len(chirp)] += chirp.astype(np.float32)
    fade = int(2 * SR)  # бесшовная петля: конец перетекает в начало
    out[:fade] = out[:fade] * np.linspace(0, 1, fade) + out[-fade:] * np.linspace(1, 0, fade)
    return rms_normalize(out[:-fade])


AMBIENCE = {"morning_home": ambience_morning_home}


def write_audio(samples: np.ndarray, path_no_ext: Path) -> Path:
    """MP3 через ffmpeg или soundfile, иначе WAV."""
    path_no_ext.parent.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(samples, -1, 1) * 32767).astype("<i2")
    if shutil.which("ffmpeg"):
        out = path_no_ext.with_suffix(".mp3")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(SR), "-ac", "1",
                        "-i", "-", "-codec:a", "libmp3lame", "-b:a", "64k", str(out)], input=pcm.tobytes(), check=True)
        return out
    try:
        import soundfile as sf

        out = path_no_ext.with_suffix(".mp3")
        sf.write(str(out), samples, SR, format="MP3")
        return out
    except Exception:
        out = path_no_ext.with_suffix(".wav")
        with wave.open(str(out), "wb") as w:
            w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR)
            w.writeframes(pcm.tobytes())
        return out


# ---------- сборка истории ----------

def build_track(engine, script, roles, factor: float, pause_mult: float = 1.0):
    parts, timings, pos = [], [], 0.4
    parts.append(np.zeros(int(0.4 * SR), np.float32))
    prev = None
    for i, line in enumerate(script):
        role = roles[line["speaker"]]
        gap = 0.0 if prev is None else (0.6 if line["speaker"] != prev else 0.35) * pause_mult
        if gap:
            parts.append(np.zeros(int(gap * SR), np.float32))
            pos += len(parts[-1]) / SR
        audio = engine.synth(plain(line["text"]), role["voice"], role.get("speed", 1.0) * factor)
        audio = rms_normalize(audio)
        if role.get("effect") == "old_radio":
            audio = rms_normalize(old_radio(audio))
        timings.append({"line": i, "start": round(pos, 3), "end": round(pos + len(audio) / SR, 3)})
        parts.append(audio)
        pos += len(audio) / SR
        prev = line["speaker"]
    parts.append(np.zeros(int(0.8 * SR), np.float32))
    return np.concatenate(parts), timings


def story_files():
    return sorted((CONTENT / "seed_stories").glob("s*.yaml"))


def level_of(number: int) -> str:
    data = yaml.safe_load((CONTENT / "manifests" / "course_map.yaml").read_text(encoding="utf-8"))
    return next(s["level"] for s in data["stories"] if s["number"] == number)


def generate(engine, path: Path, voices: dict) -> str:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    script = data.get("script")
    if not script:
        return f"{path.name}: нет script, пропущено"
    roles = voices["roles"]
    for line in script:
        if line["speaker"] not in roles:
            sys.exit(f"{path.name}: роли {line['speaker']} нет в content/manifests/voices.yaml")
        engine.check_voice(roles[line["speaker"]]["voice"])
    number = data["number"]
    folder = OUT / "stories" / f"s{number:02d}"
    rendered = {}
    for tempo, (factor, pause_mult) in TEMPOS.items():
        audio, timings = build_track(engine, script, roles, factor, pause_mult)
        rendered[tempo] = {"file": write_audio(audio, folder / f"voice_{tempo}").relative_to(ROOT / "static").as_posix(),
                           "timings": timings, "seconds": round(len(audio) / SR, 1)}
    scene = data.get("ambience")
    amb_rel = None
    if scene:
        if scene not in AMBIENCE:
            sys.exit(f"{path.name}: неизвестный фон {scene}. Есть: {', '.join(AMBIENCE)}")
        amb_dir = OUT / "ambience"
        existing = list(amb_dir.glob(f"{scene}.*")) if amb_dir.exists() else []
        amb = existing[0] if existing else write_audio(AMBIENCE[scene](), amb_dir / scene)
        amb_rel = amb.relative_to(ROOT / "static").as_posix()
    manifest = {
        "engine": engine.name,
        "model": f"kokoro-v{voices.get('model_version', '1.0')}" if engine.name == "kokoro" else "test-tone",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "verified": False,
        "voices": {k: v["voice"] for k, v in roles.items() if any(l["speaker"] == k for l in script)},
        **rendered,
        "ambience": amb_rel,
        "ambience_gain_db": voices.get("ambience_gain_db", {}).get(level_of(number), -24),
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return (f"История {number}: {len(script)} реплик, " + ", ".join(f"{k} {v['seconds']} с" for k, v in rendered.items())
            + f" — {folder.relative_to(ROOT)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--story", type=int)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--engine", choices=["kokoro", "test"], default="kokoro")
    ap.add_argument("--models", type=Path, default=MODELS)
    args = ap.parse_args()
    if not args.all and args.story is None:
        ap.error("укажите --story N или --all")
    voices = yaml.safe_load((CONTENT / "manifests" / "voices.yaml").read_text(encoding="utf-8"))
    engine = KokoroEngine(args.models) if args.engine == "kokoro" else TestEngine()
    files = story_files() if args.all else [p for p in story_files() if p.name.startswith(f"s{args.story:02d}")]
    if not files:
        sys.exit("Историй с таким номером нет.")
    for p in files:
        print(generate(engine, p, voices))


if __name__ == "__main__":
    main()
