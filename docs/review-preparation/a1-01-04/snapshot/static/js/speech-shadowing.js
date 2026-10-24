/* Listen–pause–speak–compare with existing course audio. No fake speech scoring or ASR. */
(function (global) {
  "use strict";

  function chooseSource(mode, natural, slow) {
    if (mode === "slow") return slow || natural || "";
    if (mode === "natural") return natural || slow || "";
    return "";
  }

  function init(root) {
    const player = root.querySelector("[data-speech-reference-player]");
    if (!player) return; // Course has no available audio. The text-only trainer remains usable.
    const status = player.querySelector("[data-reference-status]");
    const natural = player.dataset.referenceNatural || "";
    const slow = player.dataset.referenceSlow || "";
    if (!natural && !slow) return;
    const verified = player.dataset.referenceVerified === "true";
    const buttons = [...player.querySelectorAll("[data-reference-play]")];
    const stop = player.querySelector("[data-reference-stop]");
    const NativeAudio = global.Audio;
    if (typeof NativeAudio !== "function") {
      buttons.forEach(button => { button.disabled = true; });
      stop.disabled = true;
      status.textContent = "Браузер не поддерживает аудио. Продолжайте тренировку по тексту.";
      return;
    }
    const audio = new NativeAudio();
    audio.preload = "metadata";
    audio.preservesPitch = true;
    let closed = false;
    let busy = false;
    function setBusy(on) {
      busy = on;
      buttons.forEach(button => button.setAttribute("aria-pressed", String(on && button.dataset.referencePlay === audio.datasetMode)));
    }
    function stopPlaying() {
      audio.pause();
      try { audio.currentTime = 0; } catch (_) { /* source may not have metadata */ }
      setBusy(false);
    }
    async function play(mode) {
      if (closed) return;
      const url = chooseSource(mode, natural, slow);
      if (!url) {
        status.textContent = "Аудиофайл недоступен. Продолжайте тренироваться по тексту.";
        return;
      }
      stopPlaying();
      const alternate = root.closest(".twister-trainer")?.querySelector("[data-twister-player] audio");
      if (alternate && typeof alternate.pause === "function") alternate.pause();
      audio.datasetMode = mode;
      audio.src = url;
      audio.playbackRate = 1; // Use separately generated natural/slow tracks; avoid pitch-distorting time stretch.
      setBusy(true);
      status.textContent = verified
        ? "Слушайте проверенный образец. После окончания записи произнесите фразу самостоятельно."
        : "Слушайте предварительную синтезированную запись. Её произношение не подтверждено экспертом.";
      try {
        await audio.play();
      } catch (_) {
        setBusy(false);
        status.textContent = "Не удалось включить звук. Проверьте аудиофайл или продолжайте без него.";
      }
    }
    audio.addEventListener("ended", () => {
      setBusy(false);
      status.textContent = "Теперь ваша очередь: произнесите скороговорку вслух без подсказки. При желании послушайте ещё раз.";
    });
    audio.addEventListener("error", () => {
      setBusy(false);
      status.textContent = "Файл не загрузился. Продолжайте речевую тренировку без аудио.";
    });
    buttons.forEach(button => button.addEventListener("click", () => play(button.dataset.referencePlay)));
    stop.addEventListener("click", () => {
      stopPlaying();
      status.textContent = "Остановлено. Вы можете произнести фразу самостоятельно.";
    });
    if (typeof document !== "undefined") document.addEventListener("visibilitychange", () => {
      if (document.hidden) stopPlaying();
    });
    global.addEventListener("pagehide", () => {
      closed = true;
      stopPlaying();
      audio.removeAttribute("src");
      if (typeof audio.load === "function") audio.load();
    });
  }

  if (typeof module !== "undefined" && module.exports) module.exports = {chooseSource};
  if (typeof document !== "undefined") {
    const boot = () => document.querySelectorAll("[data-speech-reference]").forEach(init);
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot, {once: true});
    else boot();
  }
})(typeof window !== "undefined" ? window : globalThis);
