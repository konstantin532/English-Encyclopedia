/* Изолированная лаборатория A1. Без отправки голоса/свободных ответов на сервер.
   Общие функции доступны Node.js для модульной проверки. */
(function () {
  "use strict";

  const NUMBER = { 1: "one", 2: "two", 3: "three" };
  const RU_NUMBER = { 1: "один", 2: "два", 3: "три" };
  const VOICES_LANG = "en-US";
  const DIALOGUE = [
    "Good morning, Tom! What would you like?",
    "I'd like one tea and one coffee, please.",
    "Two coffees?",
    "No, sorry. One tea and one coffee, please.",
    "One tea and one coffee. Here you are.",
    "Thank you!"
  ];

  function buildSentence(quantity, drink, style) {
    const n = Number(quantity);
    if (!NUMBER[n] || !["tea", "coffee"].includes(drink) || !["like", "can"].includes(style)) {
      throw new Error("Unknown sentence selection");
    }
    const item = NUMBER[n] + " " + drink + (n > 1 ? "s" : "");
    return style === "like" ? "I'd like " + item + ", please." : "Can I have " + item + ", please?";
  }
  function buildTranslation(quantity, drink) {
    const n = Number(quantity);
    const name = drink === "tea" ? (n === 1 ? "чай" : "чая") : "кофе";
    return "Мне " + RU_NUMBER[n] + " " + name + ", пожалуйста.";
  }
  function chooseAmericanVoice(voices) {
    return (voices || []).find(function (voice) {
      return String(voice.lang || "").toLowerCase().replace("_", "-") === "en-us";
    }) || null;
  }
  function isCorrectListenAnswer(value) { return value === "b"; }

  function selectAudioTrack(manifest, tempo) {
    if (!manifest || manifest.engine !== "kokoro" || !manifest.tracks) return null;
    const track = manifest.tracks[tempo];
    return track && typeof track.url === "string" && Array.isArray(track.timings) &&
      track.timings.length === DIALOGUE.length ? track : null;
  }
  function activeDialogueLine(timings, seconds) {
    if (!Array.isArray(timings) || !Number.isFinite(seconds)) return -1;
    return timings.findIndex(function (timing) { return seconds >= timing.start && seconds < timing.end; });
  }


  if (typeof module !== "undefined" && module.exports) {
    module.exports = { buildSentence, buildTranslation, chooseAmericanVoice, isCorrectListenAnswer, selectAudioTrack, activeDialogueLine, DIALOGUE };
  }
  if (typeof document === "undefined") return;
  const root = document.querySelector("[data-cafe-lab]");
  if (!root) return;

  const by = function (selector) { return root.querySelector(selector); };
  const text = function (el, value) { if (el) el.textContent = value; };
  const reveal = function (el) { if (el) el.hidden = false; };

  const transcript = by("#cafe-transcript");
  const toggle = by("[data-show-transcript]");
  toggle.addEventListener("click", function () {
    transcript.hidden = !transcript.hidden;
    const open = !transcript.hidden;
    toggle.setAttribute("aria-expanded", String(open));
    toggle.textContent = open ? "Скрыть реплики" : "Показать реплики";
  });

  const explanations = {
    i: "I — личное местоимение: говорящий называет себя («я»).",
    would: "'d здесь означает would: вспомогательный модальный глагол в мягкой просьбе. Сравните полное I would like.",
    like: "Like в I'd like помогает вежливо назвать желаемое. Само по себе like также значит «нравиться».",
    one: "One — числительное «один». Два напитка: two teas / two coffees, когда имеется в виду количество порций.",
    tea: "Tea обычно неисчисляемое название напитка. В заказе one tea — одна порция чая.",
    coffee: "Coffee как напиток может быть неисчисляемым, а в кафе two coffees значит две порции.",
    please: "Please смягчает просьбу. Контекст и тон важнее механического правила «всегда только так»."
  };
  const wordPanel = by("[data-word-explanation]");
  root.querySelectorAll("[data-explain]").forEach(function (btn) {
    btn.addEventListener("click", function () { text(wordPanel, explanations[btn.dataset.explain]); });
  });

  const qty = by("[data-quantity]");
  const drink = by("[data-drink]");
  const style = by("[data-style]");
  const output = by("[data-built-sentence]");
  function refresh() {
    text(output, buildSentence(qty.value, drink.value, style.value));
    text(by("[data-built-translation]"), buildTranslation(qty.value, drink.value));
  }
  [qty, drink, style].forEach(function (el) { el.addEventListener("change", refresh); });
  refresh();

  const audioStatus = by("[data-audio-status]");
  const playBtn = by("[data-speak-dialogue]");
  const stopDialogueBtn = by("[data-stop-dialogue]");
  const builtBtn = by("[data-speak-built]");
  const tempoSelect = by("[data-audio-tempo]");
  const audio = by("[data-dialogue-audio]");
  const lineEls = [...root.querySelectorAll("[data-dialogue-line]")];
  const canSpeak = typeof window !== "undefined" && "speechSynthesis" in window &&
    "SpeechSynthesisUtterance" in window;

  let audioManifest = null;
  try { audioManifest = JSON.parse(document.getElementById("cafe-audio-manifest")?.textContent || "null"); }
  catch (error) { audioManifest = null; }
  let currentTrack = null;
  let singleLineEnd = null;
  let speechActive = false;
  let speechPaused = false;
  let operation = 0;

  function markLine(index) {
    lineEls.forEach(function (line, i) {
      if (i === index) line.setAttribute("data-current-line", "true");
      else line.removeAttribute("data-current-line");
    });
  }
  function togglePlay(playing) {
    playBtn.setAttribute("aria-pressed", String(playing));
    playBtn.textContent = playing ? "Ⅱ Пауза" : "▶ Слушать диалог";
  }
  function stopAll() {
    operation += 1;
    if (canSpeak) window.speechSynthesis.cancel();
    audio.pause();
    currentTrack = null;
    singleLineEnd = null;
    speechActive = false;
    speechPaused = false;
    markLine(-1);
    togglePlay(false);
  }

  function browserVoice() {
    if (!canSpeak) return null;
    return chooseAmericanVoice(window.speechSynthesis.getVoices());
  }
  function browserSpeak(lines, startLine) {
    stopAll();
    const voice = browserVoice();
    if (!voice) {
      text(audioStatus, "На устройстве нет доступного голоса en-US. Прочитайте текст диалога.");
      return;
    }
    const token = operation;
    const rate = { very_slow: 0.65, slow: 0.8, natural: 1.0 }[tempoSelect.value] || 1.0;
    let index = 0;
    speechActive = true;
    function next() {
      if (token !== operation) return;
      if (index >= lines.length) {
        speechActive = false; markLine(-1); togglePlay(false);
        text(audioStatus, "Озвучивание завершено.");
        return;
      }
      if (startLine === -2) markLine(-1);
      else if (startLine >= 0) markLine(startLine + index);
      else markLine(index);
      const u = new window.SpeechSynthesisUtterance(lines[index]);
      u.lang = VOICES_LANG;
      u.voice = voice;
      u.rate = rate;
      u.onend = function () { index += 1; next(); };
      u.onerror = function () {
        if (token !== operation) return;
        speechActive = false; markLine(-1); togglePlay(false);
        text(audioStatus, "Системный синтез речи остановился. Реплики доступны текстом.");
      };
      window.speechSynthesis.speak(u);
    }
    text(audioStatus, startLine === -2
      ? "Озвучивание вашей фразы синтезированным голосом en-US."
      : "Системный синтез en-US: один голос для Мии и Тома, не оригинальная запись.");
    togglePlay(true);
    next();
  }
  function playGenerated(track, onlyLine) {
    stopAll();
    const token = operation;
    currentTrack = track;
    singleLineEnd = onlyLine >= 0 ? track.timings[onlyLine].end : null;
    if (audio.getAttribute("src") !== track.url) {
      audio.src = track.url;
      audio.load();
    }
    try { audio.currentTime = onlyLine >= 0 ? track.timings[onlyLine].start : 0; }
    catch (error) { /* seek available once metadata loads */ }
    text(audioStatus, "Kokoro: синтезированные голоса Мии и Тома. Проверка произношения редактором ещё впереди.");
    togglePlay(true);
    const promise = audio.play();
    if (promise && typeof promise.catch === "function") promise.catch(function () {
      if (token !== operation) return;
      text(audioStatus, "Запись недоступна. Пробуем системный голос en-US.");
      browserSpeak(onlyLine >= 0 ? [DIALOGUE[onlyLine]] : DIALOGUE, onlyLine);
    });
  }
  function playSelected(onlyLine) {
    const track = selectAudioTrack(audioManifest, tempoSelect.value);
    if (track) playGenerated(track, onlyLine);
    else browserSpeak(onlyLine >= 0 ? [DIALOGUE[onlyLine]] : DIALOGUE, onlyLine);
  }

  const hasRecorded = !!selectAudioTrack(audioManifest, "natural");
  if (!canSpeak) builtBtn.disabled = true;
  if (!hasRecorded && !canSpeak) {
    playBtn.disabled = true;
    root.querySelectorAll("[data-replay-line]").forEach(function (b) { b.disabled = true; });
    text(audioStatus, "Аудио пока недоступно. Английские реплики можно прочитать после раскрытия текста.");
  } else {
    text(audioStatus, hasRecorded
      ? "Доступны три темпа Kokoro: отдельные голоса Мии и Тома."
      : "Готовой записи пока нет. Доступен системный синтез en-US, если голос установлен.");
  }

  playBtn.addEventListener("click", function () {
    if (speechActive) {
      if (!speechPaused) { window.speechSynthesis.pause(); speechPaused = true; togglePlay(false); }
      else { window.speechSynthesis.resume(); speechPaused = false; togglePlay(true); }
      return;
    }
    if (currentTrack && !audio.paused) {
      audio.pause(); togglePlay(false); return;
    }
    if (currentTrack && audio.paused && audio.currentTime > 0 && !singleLineEnd) {
      togglePlay(true);
      const p = audio.play();
      if (p && typeof p.catch === "function") p.catch(function () { playSelected(-1); });
      return;
    }
    playSelected(-1);
  });
  stopDialogueBtn.addEventListener("click", function () { stopAll(); text(audioStatus, "Воспроизведение остановлено."); });
  tempoSelect.addEventListener("change", function () {
    stopAll();
    text(audioStatus, "Темп изменён. Нажмите «Слушать диалог».");
  });
  root.querySelectorAll("[data-replay-line]").forEach(function (button) {
    button.addEventListener("click", function () {
      const index = Number(button.dataset.replayLine);
      if (!Number.isInteger(index) || index < 0 || index >= DIALOGUE.length) return;
      playSelected(index);
    });
  });
  audio.addEventListener("timeupdate", function () {
    if (!currentTrack) return;
    markLine(activeDialogueLine(currentTrack.timings, audio.currentTime));
    if (singleLineEnd !== null && audio.currentTime >= singleLineEnd) {
      stopAll();
      text(audioStatus, "Реплика прослушана.");
    }
  });
  audio.addEventListener("ended", function () {
    stopAll(); text(audioStatus, "Воспроизведение завершено.");
  });
  audio.addEventListener("error", function () {
    if (!currentTrack) return;
    const index = singleLineEnd === null ? -1 : activeDialogueLine(currentTrack.timings, audio.currentTime);
    browserSpeak(index >= 0 ? [DIALOGUE[index]] : DIALOGUE, index);
  });
  builtBtn.addEventListener("click", function () {
    browserSpeak([output.textContent], -2);
  });

  const quiz = by("[data-listen-check]");
  quiz.addEventListener("submit", function (event) {
    event.preventDefault();
    const checked = quiz.querySelector('input[name="answer"]:checked');
    if (!checked) return;
    const correct = isCorrectListenAnswer(checked.value);
    const feedback = by("[data-check-feedback]");
    feedback.dataset.state = correct ? "ok" : "retry";
    text(feedback, correct
      ? "Верно! Two coffees? — «Два кофе?». Но Том просил один чай и один кофе."
      : "Мия перепутала заказ: вместо чая и кофе она услышала два кофе. Попробуйте ещё раз.");
    reveal(feedback);
  });

  const free = by("[data-free-answer]");
  free.addEventListener("submit", function (event) {
    event.preventDefault();
    if (!by("#cafe-free-text").value.trim()) return;
    reveal(by("[data-free-feedback]"));
  });
  const transfer = by("[data-transfer-answer]");
  transfer.addEventListener("submit", function (event) {
    event.preventDefault();
    if (!by("#cafe-transfer-text").value.trim()) return;
    reveal(by("[data-transfer-feedback]"));
  });

  // Микрофон по нажатию, без upload. Текущий Blob живёт только в памяти вкладки.
  const startBtn = by("[data-record-start]");
  const stopBtn = by("[data-record-stop]");
  const recStatus = by("[data-record-status]");
  const playback = by("[data-record-playback]");
  let recorder = null;
  let mediaStream = null;
  let playbackUrl = null;
  let recording = false;

  function stopTracks() {
    if (mediaStream) { mediaStream.getTracks().forEach(function (track) { track.stop(); }); mediaStream = null; }
  }
  function resetRecordingControls() { recording = false; startBtn.disabled = false; stopBtn.disabled = true; }
  function cleanupPlayback() {
    if (playbackUrl) { URL.revokeObjectURL(playbackUrl); playbackUrl = null; }
    playback.removeAttribute("src");
    playback.hidden = true;
  }
  if (typeof window === "undefined" || !window.MediaRecorder || !navigator.mediaDevices ||
      !navigator.mediaDevices.getUserMedia) {
    startBtn.disabled = true;
    text(recStatus, "Запись голоса недоступна: нужен совместимый браузер и HTTPS либо localhost.");
  } else {
    startBtn.addEventListener("click", async function () {
      if (recording) return;
      startBtn.disabled = true;
      text(recStatus, "Запрашиваем доступ к микрофону…");
      try {
        mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const chunks = [];
        recorder = new window.MediaRecorder(mediaStream);
        recorder.ondataavailable = function (e) { if (e.data && e.data.size) chunks.push(e.data); };
        recorder.onstop = function () {
          stopTracks();
          resetRecordingControls();
          if (!chunks.length) { text(recStatus, "Запись пуста. Попробуйте снова."); return; }
          cleanupPlayback();
          const blob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
          playbackUrl = URL.createObjectURL(blob);
          playback.src = playbackUrl;
          playback.hidden = false;
          text(recStatus, "Запись доступна только здесь. Прослушайте её ниже.");
        };
        recorder.onerror = function () {
          stopTracks();
          resetRecordingControls();
          text(recStatus, "Не удалось записать звук.");
        };
        recorder.start();
        recording = true;
        stopBtn.disabled = false;
        text(recStatus, "Запись идёт. Произнесите ответ и нажмите «Завершить».");
      } catch (err) {
        stopTracks();
        resetRecordingControls();
        text(recStatus, "Доступ к микрофону не получен. Письменная практика доступна без записи.");
      }
    });
    stopBtn.addEventListener("click", function () {
      if (recorder && recorder.state === "recording") {
        stopBtn.disabled = true;
        recorder.stop();
      }
    });
    window.addEventListener("pagehide", function () {
      if (recorder && recorder.state === "recording") recorder.stop();
      stopTracks();
      cleanupPlayback();
      stopAll();
    });
  }
})();
