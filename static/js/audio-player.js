// Плеер истории: голос по ролям + отдельный зацикленный фон сцены.
// Подсветка звучащей реплики, переход по клику, режим «Сыграть роль».
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

  const playBtn = box.querySelector("[data-play]");
  const playLabel = box.querySelector("[data-play-label]");
  const timeEl = box.querySelector("[data-time]");
  const voiceVol = box.querySelector("[data-voice-vol]");
  const ambVol = box.querySelector("[data-amb-vol]");
  const roleMute = box.querySelector("[data-role-mute]");
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
    rateOut.textContent = `${(voice.playbackRate).toFixed(2).replace(/0$/, "")}×`;
    try { localStorage.setItem("ee-audio-rate", rateInput.value); } catch (e) { /* нет хранилища */ }
  };
  rateInput.addEventListener("input", applyRate);
  applyRate();

  const fmt = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
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
      voice.pause(); amb?.pause();
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
  voice.addEventListener("play", () => setPlaying(true));
  voice.addEventListener("pause", () => setPlaying(false));
  voice.addEventListener("ended", () => { setPlaying(false); amb?.pause(); lines[current]?.classList.remove("is-speaking", "is-your-turn"); current = -1; });
  voice.addEventListener("timeupdate", () => { timeEl.textContent = fmt(voice.currentTime); highlight(voice.currentTime); });

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
