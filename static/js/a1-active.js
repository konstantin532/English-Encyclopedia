/* A1 scene studio 01–18. All responses and speech remain local to the browser. */
(function () {
  "use strict";

  function normalizeAnswer(value) {
    return String(value == null ? "" : value)
      .toLocaleLowerCase("en-US")
      .replace(/['‘’"“”„«»]/g, "")
      .replace(/[.,!?;:]/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }
  function compareModelAnswer(value, expected, alternatives) {
    if (!normalizeAnswer(value)) return false;
    return [expected, ...(Array.isArray(alternatives) ? alternatives : [])]
      .some(function (candidate) { return normalizeAnswer(value) === normalizeAnswer(candidate); });
  }
  function builderTokens(answer) {
    const source = String(answer || "").trim();
    if (/^[A-Z](?:-[A-Z])+$/.test(source)) return source.split("-");
    return source ? source.split(/\s+/) : [];
  }
  function builderPhrase(tokens, selected) {
    const letterMode = tokens.length > 1 && tokens.every(function (t) { return /^[A-Z]$/.test(t); });
    return selected.map(function (i) { return tokens[i]; }).join(letterMode ? "-" : " ");
  }
  function builderCorrect(tokens, selected) {
    return tokens.length > 1 && selected.length === tokens.length
      && new Set(selected).size === selected.length
      && selected.every(function (id, i) {
        return Number.isInteger(id) && id >= 0 && id < tokens.length
          && tokens[id] === tokens[i];
      });
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
    module.exports = { normalizeAnswer, compareModelAnswer, getAmericanVoice, validTopic, builderTokens, builderPhrase, builderCorrect };
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
  let pendingVoice = null;
  function cancelPendingVoice() {
    if (!pendingVoice) return;
    window.speechSynthesis.removeEventListener("voiceschanged", pendingVoice.handler);
    window.clearTimeout(pendingVoice.timer);
    pendingVoice = null;
  }
  function stopAudio() {
    playToken += 1;
    if (speakAvailable) {
      cancelPendingVoice();
      window.speechSynthesis.cancel();
    }
  }
  function speakLines(lines) {
    stopAudio();
    if (!speakAvailable) {
      status.textContent = "На устройстве нет синтеза речи. Можно открыть английский текст.";
      return;
    }
    const token = playToken;
    const rate = Number(by("[data-a1-speed]").value) || 0.9;
    function startSpeaking(voice) {
      if (token !== playToken) return;
      let i = 0;
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
    const voice = getAmericanVoice(window.speechSynthesis.getVoices());
    if (voice) { startSpeaking(voice); return; }
    // Chrome / Android may initially return no voices while their list loads.
    status.textContent = "Загружаем доступные голоса en-US…";
    const handler = function () {
      if (token !== playToken) return;
      const ready = getAmericanVoice(window.speechSynthesis.getVoices());
      if (!ready) return;
      cancelPendingVoice();
      startSpeaking(ready);
    };
    window.speechSynthesis.addEventListener("voiceschanged", handler);
    const timer = window.setTimeout(function () {
      if (token !== playToken) return;
      cancelPendingVoice();
      status.textContent = "Голос en-US не найден. Можно читать текст реплик или повторить попытку позже.";
    }, 2500);
    pendingVoice = { handler, timer };
    handler(); // Handle a voice that appeared during listener registration.
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
    by("[data-a1-builder]").hidden = false;
  });
  by("[data-a1-play-model]").addEventListener("click", function () {
    if (!by("[data-a1-model]").hidden) speakLines([topic.answer]);
  });

  // A second, optional retrieval step appears only after the independent
  // production attempt. Duplicate words are tracked by index, not by spelling.
  const words = builderTokens(topic.answer);
  const puzzle = [...words].map(function (_, index) { return words.length - index - 1; });
  const selectedWords = [];
  const pool = by("[data-a1-builder-pool]");
  const undo = by("[data-a1-builder-undo]");
  const builderFeedback = by("[data-a1-builder-feedback]");
  function renderBuilder() {
    pool.replaceChildren();
    puzzle.forEach(function (idx) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "active-a1-btn active-a1-builder-word";
      button.textContent = words[idx];
      button.disabled = selectedWords.includes(idx);
      button.setAttribute("aria-label", "Добавить " + words[idx]);
      button.addEventListener("click", function () {
        selectedWords.push(idx);
        builderFeedback.hidden = true;
        renderBuilder();
      });
      pool.appendChild(button);
    });
    setText("[data-a1-builder-selected]", selectedWords.length
      ? builderPhrase(words, selectedWords) : "—");
    undo.disabled = selectedWords.length === 0;
  }
  undo.addEventListener("click", function () {
    if (selectedWords.length) selectedWords.pop();
    builderFeedback.hidden = true;
    renderBuilder();
  });
  by("[data-a1-builder-reset]").addEventListener("click", function () {
    selectedWords.length = 0;
    builderFeedback.hidden = true;
    renderBuilder();
  });
  by("[data-a1-builder-check]").addEventListener("click", function () {
    const complete = selectedWords.length === words.length;
    const correct = builderCorrect(words, selectedWords);
    builderFeedback.dataset.state = correct ? "ok" : "retry";
    builderFeedback.textContent = !complete
      ? "Выберите все элементы. Порядок пока не проверялся."
      : correct
        ? "Верно! Все слова стоят в нужном порядке. Теперь примените модель в новой ситуации."
        : "Порядок пока не совпадает с образцом. Попробуйте начать заново или отменить последнее слово.";
    builderFeedback.hidden = false;
  });
  renderBuilder();

  const transfer = by("[data-a1-transfer]");
  transfer.addEventListener("submit", function (event) {
    event.preventDefault();
    if (!by("[data-a1-transfer-answer]").value.trim()) return;
    by("[data-a1-transfer-feedback]").hidden = false;
  });
  window.addEventListener("pagehide", stopAudio);
})();
