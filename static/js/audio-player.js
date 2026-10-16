// Плеер реплик: голос по ролям + зацикленный фон сцены + музыка (третья дорожка, идёт синхронно с голосом).
// Подсветка звучащей реплики, переход по клику, режим «Сыграть роль», режимы слушания.
(() => {
  const box = document.querySelector("[data-story-player]");
  if (!box) return;
  const read = (id) => JSON.parse(document.getElementById(id)?.textContent || "[]");
  const tracks = { slow: { src: box.dataset.slow, timings: read("timings-slow") },
                   natural: { src: box.dataset.natural, timings: read("timings-natural") } };
  if (box.dataset.verySlow) tracks.very_slow = { src: box.dataset.verySlow, timings: read("timings-very_slow") };
  let mode = tracks.very_slow ? "very_slow" : "slow";
  const voice = new Audio(tracks[mode].src);
  voice.preservesPitch = true;
  voice.preload = "metadata";
  const amb = box.dataset.ambience ? new Audio(box.dataset.ambience) : null;
  if (amb) amb.loop = true;
  const levelGain = Math.pow(10, Number(box.dataset.ambienceDb || -24) / 20);
  const music = box.hasAttribute("data-music-slow") ? new Audio() : null;
  if (music) { music.preservesPitch = true; music.preload = "metadata"; }
  const musicVol = box.querySelector("[data-music-vol]");

  const playBtn = box.querySelector("[data-play]");
  const playLabel = box.querySelector("[data-play-label]");
  const timeEl = box.querySelector("[data-time]");
  const voiceVol = box.querySelector("[data-voice-vol]");
  const ambVol = box.querySelector("[data-amb-vol]");
  const roleMute = document.querySelector("[data-role-mute]");
  const lines = [...document.querySelectorAll("[data-line]")];
  let current = -1;
  const rateInput = box.querySelector("[data-rate]");
  const rateOut = box.querySelector("[data-rate-out]");
  const pauseLines = box.querySelector("[data-pause-lines]");
  let nextPending = false;
  let stopAt = null; // конец текущей реплики в режиме «пауза после реплики»
  try { const r = Number(localStorage.getItem("ee-audio-rate")); if (r >= 50 && r <= 125) rateInput.value = r; } catch (e) { /* нет хранилища */ }
  const applyRate = () => {
    voice.playbackRate = Number(rateInput.value) / 100;
    if (music) music.playbackRate = voice.playbackRate;
    rateOut.textContent = `${(voice.playbackRate).toFixed(2).replace(/0$/, "")}×`;
    try { localStorage.setItem("ee-audio-rate", rateInput.value); } catch (e) { /* нет хранилища */ }
  };
  rateInput.addEventListener("input", applyRate);
  applyRate();

  try { const m = localStorage.getItem("ee-music-volume"); if (musicVol && m !== null && m >= 0 && m <= 100) musicVol.value = m; } catch (e) { /* нет хранилища */ }
  const musicLevel = () => {
    if (!music || !musicVol) return 0;
    const db = Number(box.getAttribute(`data-music-db-${mode}`) || -26);
    return (Number(musicVol.value) / 100) * Math.pow(10, db / 20);
  };
  // Музыка всегда стоит там же, где голос: та же скорость и позиция.
  const syncMusic = (force) => {
    if (!music || !music.src) return;
    music.playbackRate = voice.playbackRate;
    music.volume = musicLevel();
    if (force || Math.abs(music.currentTime - voice.currentTime) > 0.25) {
      try { music.currentTime = voice.currentTime; } catch (e) { /* ещё не загружена */ }
    }
    if (!voice.paused && music.paused && musicLevel() > 0) music.play().catch(() => {});
    if ((voice.paused || musicLevel() === 0) && !music.paused) music.pause();
  };
  const loadMusic = () => {
    if (!music) return;
    const src = box.getAttribute(`data-music-${mode}`);
    if (!src) { music.pause(); music.removeAttribute("src"); return; }
    music.src = src;
    music.addEventListener("loadedmetadata", () => syncMusic(true), { once: true });
  };
  loadMusic();

  const fmt = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
  const durationEl = box.querySelector("[data-duration]");
  const updateProgress = () => {
    const duration = Number.isFinite(voice.duration) && voice.duration > 0 ? voice.duration : 0;
    const percentage = duration ? Math.max(0, Math.min(100, voice.currentTime / duration * 100)) : 0;
    box.style.setProperty("--audio-progress", percentage + "%");
    if (durationEl) durationEl.textContent = duration ? fmt(duration) : "—";
  };
  voice.addEventListener("loadedmetadata", updateProgress);
  voice.addEventListener("durationchange", updateProgress);
  voice.addEventListener("timeupdate", updateProgress);
  const ambLevel = () => (ambVol ? Number(ambVol.value) / 100 : 0) * levelGain;
  const voiceLevel = () => Number(voiceVol.value) / 100;

  function setPlaying(on) {
    playBtn.setAttribute("aria-pressed", String(on));
    playLabel.textContent = on ? "Пауза" : (nextPending ? "Дальше" : "Слушать");
    if (on) nextPending = false;
  }

  function highlight(t) {
    if (pauseLines?.checked && stopAt !== null && t >= stopAt) {
      nextPending = true; stopAt = null;
      voice.pause(); amb?.pause(); music?.pause();
    }
    const idx = tracks[mode].timings.findIndex((x) => t >= x.start && t <= x.end + 0.25);
    if (idx === current) return;
    lines[current]?.classList.remove("is-speaking");
    current = idx;
    const line = lines[idx];
    if (!line) { voice.volume = voiceLevel(); return; }
    line.classList.add("is-speaking");
    if (pauseLines?.checked) stopAt = tracks[mode].timings[idx].end + 0.15;
    const muted = roleMute && roleMute.value && line.dataset.speaker === roleMute.value;
    voice.volume = muted ? 0 : voiceLevel();
    line.classList.toggle("is-your-turn", Boolean(muted));
  }

  function switchMode(next) {
    const wasPlaying = !voice.paused;
    const ratio = voice.duration ? voice.currentTime / voice.duration : 0;
    mode = next;
    voice.src = tracks[mode].src;
    voice.addEventListener("loadedmetadata", () => {
      voice.currentTime = ratio * voice.duration;
      applyRate();
      loadMusic();
      if (wasPlaying) voice.play();
    }, { once: true });
    if (ambVol) { ambVol.value = mode === "natural" ? 100 : 0; if (amb) amb.volume = ambLevel(); }
    current = -2;
  }

  playBtn.addEventListener("click", async () => {
    if (voice.paused) {
      try { await voice.play(); } catch (e) { timeEl.textContent = "Не удалось воспроизвести звук"; return; }
      if (amb && ambLevel() > 0) { amb.volume = ambLevel(); amb.play().catch(() => {}); }
    } else { voice.pause(); amb?.pause(); }
  });
  voice.addEventListener("play", () => { setPlaying(true); syncMusic(true); });
  voice.addEventListener("pause", () => { setPlaying(false); music?.pause(); });
  voice.addEventListener("seeked", () => syncMusic(true));
  voice.addEventListener("ratechange", () => syncMusic(false));
  voice.addEventListener("ended", () => { setPlaying(false); amb?.pause(); music?.pause(); lines[current]?.classList.remove("is-speaking", "is-your-turn"); current = -1; });
  voice.addEventListener("timeupdate", () => { timeEl.textContent = fmt(voice.currentTime); highlight(voice.currentTime); syncMusic(false); });
  musicVol?.addEventListener("input", () => {
    try { localStorage.setItem("ee-music-volume", musicVol.value); } catch (e) { /* нет хранилища */ }
    syncMusic(false);
  });

  box.querySelectorAll("input[name=tempo]").forEach((r) => r.addEventListener("change", () => switchMode(r.value)));
  voiceVol.addEventListener("input", () => { voice.volume = voiceLevel(); });
  ambVol?.addEventListener("input", () => {
    if (!amb) return;
    amb.volume = ambLevel();
    if (!voice.paused && amb.paused && ambLevel() > 0) amb.play().catch(() => {});
  });
  roleMute?.addEventListener("change", () => { current = -2; highlight(voice.currentTime); });

  // Клик по реплике — слушать с её начала.
  lines.forEach((line) => {
    line.tabIndex = 0;
    const go = () => {
      const t = tracks[mode].timings[Number(line.dataset.line)];
      if (!t) return;
      voice.currentTime = Math.max(0, t.start - 0.05);
      if (voice.paused) playBtn.click();
    };
    line.addEventListener("click", (e) => { if (!e.target.closest("a")) go(); });
    line.addEventListener("keydown", (e) => { if (e.key === "Enter") go(); });
  });
})();

// Режимы слушания работают и без аудио: без текста → с текстом → с цветной разметкой.
(() => {
  const script = document.querySelector("[data-script-lines]");
  if (!script) return;
  document.querySelectorAll("input[name=listen]").forEach((r) => r.addEventListener("change", () => {
    script.classList.toggle("listen-hidden", r.value === "hidden");
    script.classList.toggle("listen-text", r.value === "text");
  }));
})();

// Выбор варианта речи сохраняется и работает до появления озвучки.
(() => {
  const script = document.querySelector("[data-script-lines]");
  const choices = [...document.querySelectorAll("input[name=speech]")];
  if (!script || !choices.length) return;
  const apply = (mode) => {
    script.classList.toggle("speech-spoken", mode === "spoken");
    choices.forEach((choice) => { choice.checked = choice.value === mode; });
  };
  let mode = "written";
  try { if (localStorage.getItem("ee-speech-mode") === "spoken") mode = "spoken"; } catch (e) { /* нет хранилища */ }
  apply(mode);
  choices.forEach((choice) => choice.addEventListener("change", () => {
    apply(choice.value);
    try { localStorage.setItem("ee-speech-mode", choice.value); } catch (e) { /* нет хранилища */ }
  }));
})();

// Скороговорка: три подготовленные записи без изменения высоты голоса.
(() => {
  const box = document.querySelector("[data-twister-player]");
  if (!box) return;
  const audio = box.querySelector("audio");
  const buttons = [...box.querySelectorAll("[data-twister-src]")];
  buttons.forEach((button) => button.addEventListener("click", () => {
    const playing = !audio.paused;
    audio.src = button.dataset.twisterSrc;
    buttons.forEach((item) => item.setAttribute("aria-pressed", String(item === button)));
    if (playing) audio.play().catch(() => {});
  }));
})();
