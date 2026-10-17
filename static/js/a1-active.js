/* A1 scene studio 01–18. All responses and speech remain local to the browser. */
(function () {
  "use strict";

  function normalizeAnswer(value) {
    return String(value == null ? "" : value)
      .toLocaleLowerCase("en-US")
      .replace(/[‘’]/g, "'")
      .replace(/[.,!?;:]/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }
  function compareModelAnswer(value, expected, alternatives) {
    if (!normalizeAnswer(value)) return false;
    return [expected, ...(Array.isArray(alternatives) ? alternatives : [])]
      .some(function (candidate) { return normalizeAnswer(value) === normalizeAnswer(candidate); });
  }
  function getAmericanVoice(voices) {
    return (voices || []).find(function (voice) {
      return String(voice.lang || "").toLowerCase().replace("_", "-") === "en-us";
    }) || null;
  }
  function validTopic(topic) {
    return !!(topic && Number.isInteger(topic.n) && topic.n >= 1 && topic.n <= 18
      && Array.isArray(topic.dialogue) && topic.dialogue.length >= 2
      && Array.isArray(topic.options) && topic.options.length === 3
      && Number.isInteger(topic.correct) && topic.correct >= 0 && topic.correct < topic.options.length);
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { normalizeAnswer, compareModelAnswer, getAmericanVoice, validTopic };
  }
  if (typeof document === "undefined") return;
  const root = document.querySelector("[data-active-a1]");
  if (!root) return;
  let topic;
  try { topic = JSON.parse(document.getElementById("a1-active-topic-data").textContent); }
  catch (err) { return; }
  if (!validTopic(topic)) return;

  const by = function (selector) { return root.querySelector(selector); };
  const setText = function (selector, value) {
    const el = by(selector);
    if (el) el.textContent = value;
  };
  const status = by("[data-a1-audio-status]");
  const speakAvailable = typeof window !== "undefined" &&
    "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
  let playToken = 0;
  function stopAudio() {
    playToken += 1;
    if (speakAvailable) window.speechSynthesis.cancel();
  }
  function speakLines(lines) {
    stopAudio();
    if (!speakAvailable) {
      status.textContent = "На устройстве нет синтеза речи. Можно открыть английский текст.";
      return;
    }
    const voice = getAmericanVoice(window.speechSynthesis.getVoices());
    if (!voice) {
      status.textContent = "Не найден голос en-US. Можно читать английские реплики. Это не ошибка ответа.";
      return;
    }
    const token = playToken;
    let i = 0;
    const rate = Number(by("[data-a1-speed]").value) || 0.9;
    status.textContent = "Системный голос en-US. Для этой серии пока нет проверенной записи отдельных актёров.";
    function next() {
      if (token !== playToken) return;
      if (i >= lines.length) { status.textContent = "Прослушивание закончено."; return; }
      const u = new window.SpeechSynthesisUtterance(lines[i]);
      u.lang = "en-US";
      u.voice = voice;
      u.rate = rate;
      u.onend = function () { i += 1; next(); };
      u.onerror = function () {
        if (token === playToken) status.textContent = "Голос остановился. Откройте текст реплик.";
      };
      window.speechSynthesis.speak(u);
    }
    next();
  }
  const speakBtns = [
    by("[data-a1-play]"), by("[data-a1-play-model]"),
    ...root.querySelectorAll("[data-a1-play-line]")
  ];
  if (!speakAvailable) {
    speakBtns.forEach(function (btn) { btn.disabled = true; });
    status.textContent = "Системный синтез речи недоступен. Английский текст можно открыть вручную.";
  }
  by("[data-a1-play]").addEventListener("click", function () {
    speakLines(topic.dialogue.map(function (line) { return line[1]; }));
  });
  by("[data-a1-stop]").addEventListener("click", function () {
    stopAudio(); status.textContent = "Прослушивание остановлено.";
  });
  by("[data-a1-speed]").addEventListener("change", function () {
    stopAudio(); status.textContent = "Скорость изменена. Воспроизведите диалог заново.";
  });
  root.querySelectorAll("[data-a1-play-line]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const i = Number(btn.dataset.a1PlayLine);
      if (Number.isInteger(i) && i >= 0 && i < topic.dialogue.length)
        speakLines([topic.dialogue[i][1]]);
    });
  });
  const transcript = by("#active-a1-transcript");
  const toggle = by("[data-a1-reveal-transcript]");
  toggle.addEventListener("click", function () {
    transcript.hidden = !transcript.hidden;
    toggle.setAttribute("aria-expanded", String(!transcript.hidden));
    toggle.textContent = transcript.hidden ? "Показать текст диалога" : "Скрыть текст диалога";
  });

  const quiz = by("[data-a1-quiz]");
  quiz.addEventListener("submit", function (event) {
    event.preventDefault();
    const chosen = quiz.querySelector('input[name="quiz"]:checked');
    if (!chosen) return;
    const correct = Number(chosen.value) === topic.correct;
    const output = by("[data-a1-quiz-feedback]");
    output.dataset.state = correct ? "ok" : "retry";
    output.textContent = (correct ? "Верно! " : "Попробуйте ещё раз. ") +
      (correct ? topic.feedback : "Если нужно, прослушайте диалог и раскройте его текст.");
    output.hidden = false;
  });

  const production = by("[data-a1-production]");
  production.addEventListener("submit", function (event) {
    event.preventDefault();
    const submitted = by("[data-a1-production-answer]").value;
    if (!submitted.trim()) return;
    const match = compareModelAnswer(submitted, topic.answer, topic.alternatives);
    const feedback = by("[data-a1-production-feedback]");
    feedback.dataset.state = match ? "ok" : "review";
    feedback.textContent = match
      ? "Ваш текст совпал с одним из подготовленных примеров. Это проверка фразы, а не произношения."
      : "Ваш текст отличается от подготовленных вариантов. Это ещё не означает ошибку: сравните смысл, порядок слов и ситуацию.";
    feedback.hidden = false;
    setText("[data-a1-model-text]", topic.answer);
    setText("[data-a1-hint]", topic.hint);
    by("[data-a1-model]").hidden = false;
  });
  by("[data-a1-play-model]").addEventListener("click", function () {
    if (!by("[data-a1-model]").hidden) speakLines([topic.answer]);
  });

  const transfer = by("[data-a1-transfer]");
  transfer.addEventListener("submit", function (event) {
    event.preventDefault();
    if (!by("[data-a1-transfer-answer]").value.trim()) return;
    by("[data-a1-transfer-feedback]").hidden = false;
  });
  window.addEventListener("pagehide", stopAudio);
})();
