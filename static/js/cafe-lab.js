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

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { buildSentence, buildTranslation, chooseAmericanVoice, isCorrectListenAnswer, DIALOGUE };
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
  const canSpeak = typeof window !== "undefined" && "speechSynthesis" in window &&
    "SpeechSynthesisUtterance" in window;
  const dialogueBtn = by("[data-speak-dialogue]");
  const builtBtn = by("[data-speak-built]");
  if (!canSpeak) {
    dialogueBtn.disabled = true;
    builtBtn.disabled = true;
    text(audioStatus, "Озвучка недоступна в этом браузере. Вы можете открыть английские реплики.");
  }
  function speak(lines) {
    if (!canSpeak) return;
    const voice = chooseAmericanVoice(window.speechSynthesis.getVoices());
    if (!voice) {
      text(audioStatus, "Системный голос en-US не найден. Это не ошибка урока: откройте текст реплик.");
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new window.SpeechSynthesisUtterance(lines);
    utterance.lang = VOICES_LANG;
    utterance.voice = voice;
    utterance.rate = 0.88;
    utterance.onstart = function () { text(audioStatus, "Звучит синтез речи en-US (один голос для всего диалога)."); };
    utterance.onend = function () { text(audioStatus, "Воспроизведение закончено."); };
    utterance.onerror = function () { text(audioStatus, "Не удалось озвучить. Откройте текст реплик."); };
    window.speechSynthesis.speak(utterance);
  }
  dialogueBtn.addEventListener("click", function () { speak(DIALOGUE.join(" … ")); });
  builtBtn.addEventListener("click", function () { speak(output.textContent); });

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
      if (canSpeak) window.speechSynthesis.cancel();
    });
  }
})();
