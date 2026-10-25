"""Озвучка по ролям: истории, диалоги недель, скороговорки. Эмоции реплик, фон сцены, музыка историй.

Запуск (обычно через generate_audio.bat):
    uv run python scripts/generate_story_audio.py --all                 # всё
    uv run python scripts/generate_story_audio.py --story 1
    uv run python scripts/generate_story_audio.py --week A1-1
    uv run python scripts/generate_story_audio.py --all --only twisters
    uv run python scripts/generate_story_audio.py --all --engine test   # без модели, для проверки

Что получается (static/audio/…):
    stories/sNN/, weeks/<уровень>-wNN/, twisters/tNNN/
        voice_very_slow.*, voice_slow.*, voice_natural.*   три темпа
        music_<темп>.*                                        музыка истории, тише под репликами
        manifest.json                                         голоса, тайминги, эмоции, громкость фона и музыки
Фон сцены — отдельный зацикленный файл static/audio/ambience/<scene>.*.
Эмоция реплики (content/manifests/voices.yaml, раздел emotions) меняет скорость, громкость и паузу после реплики.

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
# Целые файлы модели Kokoro v1.0: onnx ≈ 310 МБ, voices ≈ 27 МБ. Меньше — загрузка оборвалась.
MODEL_MIN_BYTES = 300_000_000
VOICES_MIN_BYTES = 27_000_000
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
        model, voices = models_dir / "kokoro-v1.0.onnx", models_dir / "voices-v1.0.bin"
        if not model.exists() or not voices.exists():
            sys.exit(f"Нет файлов модели в {models_dir}. Запустите generate_audio.bat — он их скачает.")
        for path, need in ((model, MODEL_MIN_BYTES), (voices, VOICES_MIN_BYTES)):
            size = path.stat().st_size
            if size < need:
                sys.exit(f"Файл {path.name} неполный: {size / 1e6:.0f} МБ из примерно {need / 1e6:.0f}+ МБ — загрузка оборвалась. "
                         f"Удалите {path} и запустите generate_audio.bat снова, он скачает файл заново.")
        try:
            from kokoro_onnx import Kokoro
        except ImportError:
            sys.exit("Нет пакета kokoro-onnx. Запустите generate_audio.bat — он всё установит.")
        try:
            self.tts = Kokoro(str(model), str(voices))
        except Exception as exc:  # повреждённый файл модели
            sys.exit(f"Не удалось открыть модель ({exc.__class__.__name__}). Файл {model.name} повреждён: "
                     f"удалите {model} и запустите generate_audio.bat снова.")
        self.available = set(self.tts.get_voices())

    def check_voice(self, voice: str) -> None:
        if voice not in self.available:
            sys.exit(f"Голоса {voice} нет в модели. Доступны: {', '.join(sorted(self.available))}")

    def synth(self, text: str, voice: str, speed: float, emotion: str = "neutral") -> np.ndarray:
        # Kokoro не управляет эмоцией напрямую: её уже учли скорость, громкость и пауза.
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

    def synth(self, text: str, voice: str, speed: float, emotion: str = "neutral") -> np.ndarray:
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


# ---------- музыка ----------

NOTE = {n: 440 * 2 ** ((i - 9) / 12) for i, n in enumerate("C C# D D# E F F# G G# A A# B".split())}


def _freq(name: str) -> float:
    """«A3», «C#4» → частота."""
    return NOTE[name[:-1]] * 2 ** (int(name[-1]) - 4)


def _tone(freq: float, seconds: float, decay: float | None, harmonics=(1.0, 0.35, 0.12)) -> np.ndarray:
    t = np.arange(int(seconds * SR)) / SR
    wave_ = sum(a * np.sin(2 * np.pi * freq * (k + 1) * t) for k, a in enumerate(harmonics))
    if decay:  # «пианино»: быстрая атака, затухание
        env = np.exp(-t / decay) * np.minimum(1, t / 0.01)
    else:  # «подушка»: мягкие нарастание и спад
        ramp = min(0.8, seconds / 3)
        env = np.minimum(1, np.minimum(t / ramp, (seconds - t) / ramp))
    return (wave_ * env).astype(np.float32)


def compose(chords: list[list[str]], chord_seconds: float, arpeggio: int, piano_decay: float, seed: int,
            drone: str | None = None, pulse: float = 0.0) -> np.ndarray:
    """Петля: аккорды-подушка + перебор «пианино» + необязательный гул и пульс. Детерминирована зерном."""
    rng = np.random.default_rng(seed)
    total = int(len(chords) * chord_seconds * SR)
    out = np.zeros(total, np.float32)
    for c, chord in enumerate(chords):
        i0 = int(c * chord_seconds * SR)
        for note in chord:
            pad = _tone(_freq(note), chord_seconds, None, (1.0, 0.2)) * 0.18
            out[i0:i0 + len(pad)] += pad[: total - i0]
        step = chord_seconds / max(arpeggio, 1)
        for k in range(arpeggio):
            note = chord[int(rng.integers(len(chord)))]
            f = _freq(note) * 2
            ping = _tone(f, min(2.5, chord_seconds), piano_decay) * 0.25
            j = i0 + int(k * step * SR)
            out[j:j + len(ping)] += ping[: max(0, total - j)]
    if drone:
        out += _tone(_freq(drone), total / SR, None, (1.0, 0.5)) * 0.15
    if pulse:
        t = np.arange(total) / SR
        out *= (1 - 0.35 * (0.5 + 0.5 * np.sin(2 * np.pi * pulse * t))).astype(np.float32)
    fade = int(1.0 * SR)  # бесшовная петля
    out[:fade] = out[:fade] * np.linspace(0, 1, fade) + out[-fade:] * np.linspace(1, 0, fade)
    return rms_normalize(out[:-fade])


def _loop(fn):
    """Генератор настроения: петля, растянутая до нужной длины."""
    def make(seconds: float) -> np.ndarray:
        base = fn()
        reps = int(np.ceil(seconds * SR / len(base)))
        return np.tile(base, reps)[: int(seconds * SR)]
    return make


MUSIC = {
    "calm": _loop(lambda: compose([["C3", "E3", "G3"], ["A2", "C3", "E3"], ["F2", "A2", "C3"], ["G2", "B2", "D3"]], 4.0, 3, 1.4, 1)),
    "morning": _loop(lambda: compose([["G3", "B3", "D4"], ["E3", "G3", "B3"], ["C3", "E3", "G3"], ["D3", "F#3", "A3"]], 3.0, 6, 0.9, 2)),
    "mystery": _loop(lambda: compose([["A2", "C3", "E3"], ["A2", "C3", "D#3"], ["F2", "A2", "C3"], ["E2", "G#2", "B2"]], 5.0, 2, 2.0, 3, drone="A1")),
    "sad": _loop(lambda: compose([["D3", "F3", "A3"], ["A#2", "D3", "F3"], ["G2", "A#2", "D3"], ["A2", "C#3", "E3"]], 5.0, 2, 1.8, 4)),
    "happy": _loop(lambda: compose([["C4", "E4", "G4"], ["F3", "A3", "C4"], ["G3", "B3", "D4"], ["C4", "E4", "G4"]], 2.0, 8, 0.6, 5)),
    "tense": _loop(lambda: compose([["E2", "F2", "B2"], ["E2", "G2", "A#2"]], 4.0, 4, 0.5, 6, drone="E1", pulse=2.0)),
}


def music_track(script: list[dict], timings: list[dict], total_seconds: float) -> np.ndarray | None:
    """Музыка по настроениям реплик: настроение тянется до следующей смены, переход — кроссфейд 1 с."""
    changes = [(0.0 if i == 0 else timings[i]["start"], line["music"]) for i, line in enumerate(script) if "music" in line]
    if not any(mood != "none" for _, mood in changes):
        return None
    n = int(total_seconds * SR)
    out = np.zeros(n, np.float32)
    fade = int(1.0 * SR)
    for k, (start, mood) in enumerate(changes):
        if mood == "none":
            continue
        a = int(start * SR)
        b = int(changes[k + 1][0] * SR) if k + 1 < len(changes) else n
        env = np.zeros(n, np.float32)
        env[a:b] = 1
        if k > 0:  # плавное появление
            env[a:min(a + fade, b)] = np.linspace(0, 1, min(fade, b - a))
        if b < n:  # плавный уход в следующее настроение
            tail = min(fade, n - b)
            env[b:b + tail] = np.linspace(1, 0, tail)
        out += MUSIC[mood](total_seconds)[:n] * env
    return out


def duck(music: np.ndarray, timings: list[dict], depth_db: float = -12.0,
         attack: float = 0.15, release: float = 0.4) -> np.ndarray:
    """Приглушение музыки под репликами: огибающая на 100 Гц с разной скоростью спада и возврата."""
    rate = 100
    n = int(np.ceil(len(music) / SR * rate)) + 1
    target = np.ones(n, np.float32)
    low = 10 ** (depth_db / 20)
    for t in timings:
        target[int(t["start"] * rate):int(np.ceil(t["end"] * rate))] = low
    k_down, k_up = 1 - np.exp(-1 / (attack * rate)), 1 - np.exp(-1 / (release * rate))
    env = np.empty(n, np.float32)
    cur = 1.0
    for i, goal in enumerate(target):
        cur += (goal - cur) * (k_down if goal < cur else k_up)
        env[i] = cur
    x = np.arange(len(music)) / SR * rate
    return (music * np.interp(x, np.arange(n), env)).astype(np.float32)


# ---------- сборка дорожки ----------

def build_track(engine, script, roles, factor: float, pause_mult: float = 1.0, emotions: dict | None = None,
                spoken: bool = False):
    """Голос по репликам. spoken=True — читать вариант «как говорят» (поле spoken), если он есть."""
    emotions = emotions or {}
    parts, timings, pos = [np.zeros(int(0.4 * SR), np.float32)], [], 0.4
    prev, prev_pause = None, 1.0
    for i, line in enumerate(script):
        role = roles[line["speaker"]]
        emotion = line.get("emotion", "neutral")
        emo = emotions.get(emotion, {})
        gap = 0.0 if prev is None else (0.6 if line["speaker"] != prev else 0.35) * pause_mult * prev_pause
        if gap:
            parts.append(np.zeros(int(gap * SR), np.float32))
            pos += len(parts[-1]) / SR
        text = (line.get("spoken") or line["text"]) if spoken else line["text"]
        speed = role.get("speed", 1.0) * emo.get("speed", 1.0) * factor
        audio = rms_normalize(engine.synth(plain(text), role["voice"], speed, emotion))
        if role.get("effect") == "old_radio":
            audio = rms_normalize(old_radio(audio))
        audio = (audio * 10 ** (emo.get("gain_db", 0) / 20)).astype(np.float32)
        timings.append({"line": i, "start": round(pos, 3), "end": round(pos + len(audio) / SR, 3), "emotion": emotion})
        parts.append(audio)
        pos += len(audio) / SR
        prev, prev_pause = line["speaker"], emo.get("pause", 1.0)
    parts.append(np.zeros(int(0.8 * SR), np.float32))
    return np.concatenate(parts), timings


def check_script(name: str, script: list[dict], roles: dict, voices: dict, engine) -> None:
    emotions, moods = voices.get("emotions", {}), voices.get("music_moods", {})
    for line in script:
        if line["speaker"] not in roles:
            sys.exit(f"{name}: роли {line['speaker']} нет в content/manifests/voices.yaml")
        if line.get("emotion", "neutral") not in emotions:
            sys.exit(f"{name}: неизвестная эмоция {line['emotion']}. Есть: {', '.join(emotions)}")
        if "music" in line and line["music"] not in moods:
            sys.exit(f"{name}: неизвестное настроение {line['music']}. Есть: {', '.join(moods)}")
        engine.check_voice(roles[line["speaker"]]["voice"])


def ambience_file(name: str, scene: str | None) -> str | None:
    if not scene:
        return None
    if scene not in AMBIENCE:
        sys.exit(f"{name}: неизвестный фон {scene}. Есть: {', '.join(AMBIENCE)}")
    amb_dir = OUT / "ambience"
    existing = list(amb_dir.glob(f"{scene}.*")) if amb_dir.exists() else []
    amb = existing[0] if existing else write_audio(AMBIENCE[scene](), amb_dir / scene)
    return amb.relative_to(ROOT / "static").as_posix()


def render(engine, name: str, script: list[dict], roles: dict, voices: dict, folder: Path, level: str | None,
           ambience: str | None = None, with_music: bool = False) -> dict:
    """Три темпа, тайминги, музыка (для историй) и manifest.json в папке folder."""
    check_script(name, script, roles, voices, engine)
    rendered = {}
    gain = voices.get("music_gain_db", {}).get(level, -24)
    for tempo, (factor, pause_mult) in TEMPOS.items():
        audio, timings = build_track(engine, script, roles, factor, pause_mult, voices.get("emotions", {}),
                                     spoken=tempo == "natural")
        entry = {"file": write_audio(audio, folder / f"voice_{tempo}").relative_to(ROOT / "static").as_posix(),
                 "timings": timings, "seconds": round(len(audio) / SR, 1)}
        music = music_track(script, timings, len(audio) / SR) if with_music else None
        if music is not None:
            entry["music"] = write_audio(duck(music, timings), folder / f"music_{tempo}").relative_to(ROOT / "static").as_posix()
            entry["music_gain_db"] = gain - (4 if tempo == "very_slow" else 0)
        rendered[tempo] = entry
    manifest = {
        "engine": engine.name,
        "model": f"kokoro-v{voices.get('model_version', '1.0')}" if engine.name == "kokoro" else "test-tone",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "verified": False,
        "voices": {k: v["voice"] for k, v in roles.items() if any(l["speaker"] == k for l in script)},
        **rendered,
        "ambience": ambience_file(name, ambience),
        "ambience_gain_db": voices.get("ambience_gain_db", {}).get(level, -24),
    }
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return rendered


def level_of(number: int) -> str:
    data = yaml.safe_load((CONTENT / "manifests" / "course_map.yaml").read_text(encoding="utf-8"))
    return next(s["level"] for s in data["stories"] if s["number"] == number)


def level_slug(code: str) -> str:
    return code.lower().replace("+", "-plus")


def _summary(title: str, n: int, rendered: dict, folder: Path) -> str:
    return (f"{title}: {n} реплик, " + ", ".join(f"{k} {v['seconds']} с" for k, v in rendered.items())
            + f" — {folder.relative_to(ROOT)}")


def generate(engine, path: Path, voices: dict) -> str:
    """История: голос, фон и музыка."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    script = data.get("script")
    if not script:
        return f"{path.name}: нет script, пропущено"
    number = data["number"]
    folder = OUT / "stories" / f"s{number:02d}"
    rendered = render(engine, path.name, script, voices["roles"], voices, folder, level_of(number),
                      data.get("ambience"), with_music=True)
    return _summary(f"История {number}", len(script), rendered, folder)


def generate_week(engine, path: Path, voices: dict) -> str:
    """Диалог недели: голос и фон, без музыки."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    script = data.get("script")
    if not script:
        return f"{path.name}: нет script, пропущено"
    folder = OUT / "weeks" / f"{level_slug(data['level'])}-w{data['week']:02d}"
    rendered = render(engine, path.name, script, voices["roles"], voices, folder, data["level"], data.get("ambience"))
    return _summary(f"Неделя {data['level']}-{data['week']}", len(script), rendered, folder)


def generate_twister(engine, twister: dict, voices: dict) -> str:
    """Скороговорка: один голос из пула extras, без фона и музыки."""
    roles = {"twister": {"voice": voices["extras"][0], "speed": 1.0}}
    script = [{"speaker": "twister", "text": twister["text"]}]
    folder = OUT / "twisters" / f"t{twister['number']:03d}"
    rendered = render(engine, f"скороговорка {twister['number']}", script, roles, voices, folder, None)
    return _summary(f"Скороговорка {twister['number']}", 1, rendered, folder)


def story_files():
    return sorted((CONTENT / "seed_stories").glob("s*.yaml"))


def week_files():
    return sorted((CONTENT / "seed_weeks").glob("*.yaml"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--story", type=int)
    ap.add_argument("--week", help="уровень-неделя, например A1-1")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--only", choices=["stories", "weeks", "twisters"])
    ap.add_argument("--engine", choices=["kokoro", "test"], default="kokoro")
    ap.add_argument("--models", type=Path, default=MODELS)
    args = ap.parse_args()
    if not args.all and args.story is None and args.week is None:
        ap.error("укажите --all, --story N или --week A1-1")
    voices = yaml.safe_load((CONTENT / "manifests" / "voices.yaml").read_text(encoding="utf-8"))
    engine = KokoroEngine(args.models) if args.engine == "kokoro" else TestEngine()
    want = lambda kind: args.only in (None, kind)
    stories = story_files() if args.all and want("stories") else (
        [p for p in story_files() if p.name.startswith(f"s{args.story:02d}")] if args.story is not None else [])
    weeks = []
    if args.week:
        lv, _, wk = args.week.partition("-")
        weeks = [p for p in week_files() if (d := yaml.safe_load(p.read_text(encoding="utf-8")))
                 and d["level"] == lv.upper() and d["week"] == int(wk)]
    elif args.all:
        weeks = week_files()
    if args.story is not None and not stories:
        sys.exit("Историй с таким номером нет.")
    if args.week and not weeks:
        sys.exit("Недели с таким номером нет.")
    for p in stories:
        print(generate(engine, p, voices))
    for p in weeks:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        if want("weeks"):
            print(generate_week(engine, p, voices))
        if want("twisters") and data.get("twister"):
            print(generate_twister(engine, data["twister"], voices))


if __name__ == "__main__":
    main()
