/* Speech coach: four phases, no speech scoring, no cloud, no saved recordings. */
(function (global) {
  "use strict";
  const MODES = ["see", "echo", "recall", "transfer"];
  const INSTRUCTIONS = {
    poem: {
      see: "Прочитайте строку, поймите смысл и найдите ударение.",
      echo: "Произнесите чётко, с естественными паузами, затем повторите.",
      recall: "Произнесите строку по памяти, не заглядывая в образец.",
      transfer: "Замените одно знакомое слово и произнесите новую фразу."
    },
    twister: {
      see: "Поймите смысл и найдите трудный звук.",
      echo: "Произнесите медленно. Точность важнее скорости.",
      recall: "Воспроизведите строку без пропусков по памяти.",
      transfer: "Примените трудный звук в обычной реплике диалога."
    },
    lesson: {
      see: "Прочитайте пример и поймите, почему он подходит к ситуации.",
      echo: "Произнесите ответ вслух. Не ускоряйтесь в ущерб ясности.",
      recall: "Ответьте на вопрос ситуации без видимого образца.",
      transfer: "Ответьте самостоятельно другими известными словами — без готовой фразы."
    }
  };
  const clampIndex = (i, n) => n ? Math.max(0, Math.min(i, n - 1)) : 0;
  function tempoFromTaps(taps) {
    if (!Array.isArray(taps) || taps.length < 2) return null;
    const recent = taps.slice(-8), differences = [];
    for (let i = 1; i < recent.length; i++) {
      const delta = recent[i] - recent[i - 1];
      if (Number.isFinite(delta) && delta >= 300 && delta <= 1800) differences.push(delta);
    }
    if (!differences.length) return null;
    return Math.round(60000 / (differences.reduce((a, b) => a + b, 0) / differences.length));
  }
  function init(root) {
    const one = selector => root.querySelector(selector);
    const entries = [...root.querySelectorAll("[data-speech-entry]")];
    if (!entries.length) { const controls = one("[data-speech-controls]"); if (controls) controls.hidden = true; return; }
    const kind = ["twister", "lesson"].includes(root.dataset.speechKind) ? root.dataset.speechKind : "poem";
    const task = one("[data-speech-task]");
    const current = one("[data-speech-current]");
    const stress = one("[data-speech-stress]");
    const progress = one("[data-speech-position]");
    const instruction = one("[data-speech-instruction]");
    const prev = one("[data-speech-prev]");
    const next = one("[data-speech-next]");
    const reveal = one("[data-speech-reveal]");
    const done = one("[data-speech-done]");
    const status = one("[data-speech-status]");
    const checked = new Set();
    let index = 0, mode = "see", visible = true, taps = [];
    // Повторение открывает нужный фрагмент по безопасному числовому параметру URL.
    const requested = (global.location && String(global.location.search || "").match(/[?&]speech=(\d{1,3})(?:&|$)/));
    if (requested) { index = clampIndex(Number(requested[1]), entries.length); mode = "recall"; visible = false; }
    function paint() {
      index = clampIndex(index, entries.length);
      root.dataset.speechIndex = String(index);
      root.dataset.speechMode = mode;
      const promptSource = entries[index].querySelector("[data-speech-task-source]");
      if (task) { task.textContent = promptSource ? promptSource.textContent.trim() : ""; task.hidden = !task.textContent; }
      const source = entries[index].querySelector("[data-speech-source]");
      const accent = entries[index].querySelector("[data-speech-accent]");
      const hidden = (mode === "recall" || mode === "transfer") && !visible;
      current.replaceChildren();
      if (hidden) {
        const prompt = document.createElement("span");
        prompt.lang = "ru";
        prompt.textContent = mode === "recall" ? "Сначала произнесите по памяти." : "Придумайте свою реплику, не читая образец.";
        current.append(prompt);
      } else if (source) current.append(...[...source.childNodes].map(n => n.cloneNode(true)));
      stress.textContent = !hidden && accent ? accent.textContent.trim() : "";
      stress.hidden = hidden || !stress.textContent;
      progress.textContent = "Фрагмент " + (index + 1) + " из " + entries.length;
      instruction.textContent = INSTRUCTIONS[kind][mode];
      prev.disabled = index === 0; next.disabled = index === entries.length - 1;
      reveal.hidden = !hidden;
      done.textContent = checked.has(index) ? "Отменить отметку" : "Мне удалось произнести";
      status.textContent = "Отмечено " + checked.size + " из " + entries.length + ".";
      root.querySelectorAll("[data-speech-mode]").forEach(btn => btn.setAttribute("aria-pressed", String(btn.dataset.speechMode === mode)));
      if (typeof root.dispatchEvent === "function" && typeof global.CustomEvent === "function")
        root.dispatchEvent(new global.CustomEvent("speech:changed"));
    }
    root.querySelectorAll("[data-speech-mode]").forEach(btn => btn.addEventListener("click", () => {
      if (!MODES.includes(btn.dataset.speechMode)) return;
      mode = btn.dataset.speechMode;
      visible = mode === "see" || mode === "echo";
      paint();
      global.EnglishMotion?.enter(current, "component");
    }));
    prev.addEventListener("click", () => { index--; visible = mode === "see" || mode === "echo"; paint(); global.EnglishMotion?.enter(current, "component"); });
    next.addEventListener("click", () => { index++; visible = mode === "see" || mode === "echo"; paint(); global.EnglishMotion?.enter(current, "component"); });
    reveal.addEventListener("click", () => { visible = true; paint(); });
    done.addEventListener("click", () => { if (checked.has(index)) checked.delete(index); else checked.add(index); paint(); });
    const tempo = one("[data-speech-tempo]");
    one("[data-speech-tap]")?.addEventListener("click", () => {
      const now = Date.now();
      if (taps.length && now - taps[taps.length - 1] > 2300) taps = [];
      taps.push(now); if (taps.length > 8) taps.shift();
      const bpm = tempoFromTaps(taps);
      tempo.textContent = bpm ? "Примерно " + bpm + " ударов в минуту — только темп нажатий." : "Продолжайте отмечать удары ритма.";
    });
    one("[data-speech-reset-beat]")?.addEventListener("click", () => { taps = []; tempo.textContent = "Ритм сброшен."; });
    if (typeof root.addEventListener === "function") root.addEventListener("speech:jump", event => {
      if (!event.detail || !Number.isInteger(event.detail.index)) return;
      index = clampIndex(event.detail.index, entries.length);
      mode = "recall"; visible = false; paint();
    });
    paint();
  }
  function initRecorder(root) {
    const one = selector => root.querySelector(selector);
    const record = one("[data-speech-record]");
    if (!record) return;
    const stop = one("[data-speech-stop]");
    const remove = one("[data-speech-delete]");
    const playback = one("[data-speech-playback]");
    const report = one("[data-speech-record-status]");
    let media = null, stream = null, audioUrl = null, chunks = [];
    let starting = false, captureEpoch = 0;
    function forget() {
      playback.pause(); playback.removeAttribute("src"); playback.load();
      playback.hidden = true; remove.hidden = true;
      if (audioUrl) URL.revokeObjectURL(audioUrl);
      audioUrl = null;
    }
    function release() {
      if (stream) stream.getTracks().forEach(track => track.stop());
      stream = null; stop.hidden = true; record.hidden = false;
    }
    if (!global.navigator || !global.navigator.mediaDevices || !global.navigator.mediaDevices.getUserMedia || typeof global.MediaRecorder !== "function") {
      record.disabled = true;
      report.textContent = "Запись в этом браузере недоступна.";
    } else {
      record.addEventListener("click", async () => {
        if (starting || (media && media.state === "recording")) return;
        // Late events from an older recording must not affect the next one.
        const epoch = ++captureEpoch;
        starting = true;
        forget(); chunks = []; record.disabled = true;
        try {
          const input = await global.navigator.mediaDevices.getUserMedia({ audio: true, video: false });
          if (epoch !== captureEpoch) { input.getTracks().forEach(track => track.stop()); return; }
          stream = input;
          media = new global.MediaRecorder(stream);
          media.addEventListener("dataavailable", event => { if (epoch === captureEpoch && event.data && event.data.size) chunks.push(event.data); });
          media.addEventListener("stop", () => {
            if (epoch !== captureEpoch) return;
            release(); record.disabled = false;
            if (chunks.length) {
              const blob = new Blob(chunks, { type: media.mimeType || "audio/webm" });
              audioUrl = URL.createObjectURL(blob);
              playback.src = audioUrl; playback.hidden = false; remove.hidden = false;
              report.textContent = "Запись готова: послушайте и при желании удалите.";
            } else report.textContent = "Запись пуста. Можно попробовать ещё раз.";
            chunks = [];
          }, { once: true });
          media.addEventListener("error", () => { if (epoch !== captureEpoch) return; release(); record.disabled = false; report.textContent = "Запись прервана."; }, { once: true });
          media.start(); record.hidden = true; stop.hidden = false;
          report.textContent = "Идёт запись только в памяти страницы.";
        } catch (_) {
          if (epoch !== captureEpoch) return;
          release(); record.disabled = false;
          report.textContent = "Нет разрешения на микрофон или запись недоступна.";
        } finally {
          if (epoch === captureEpoch) { starting = false; record.disabled = false; }
        }
      });
      stop.addEventListener("click", () => { if (media && media.state === "recording") media.stop(); else release(); });
      remove.addEventListener("click", () => { forget(); report.textContent = "Запись удалена."; });
      global.addEventListener("pagehide", () => {
        captureEpoch++; starting = false; record.disabled = false;
        if (media && media.state === "recording") media.stop();
        release(); forget(); chunks = [];
      });
    }
  }
  if (typeof module !== "undefined" && module.exports) module.exports = { MODES, INSTRUCTIONS, clampIndex, tempoFromTaps };
  if (typeof document !== "undefined") {
    const boot = () => {
      document.querySelectorAll("[data-speech-studio]").forEach(init);
      document.querySelectorAll("[data-speech-recorder]").forEach(initRecorder);
    };
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot, { once: true });
    else boot();
  }
})(typeof window !== "undefined" ? window : globalThis);
