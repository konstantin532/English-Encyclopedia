/* A1 scene studio 01–28. All responses and speech remain local to the browser. */
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
  function retrievalLine(topic) {
    if (!topic || !Array.isArray(topic.dialogue) || !topic.dialogue.length) return null;
    const index = (topic.n - 1) % topic.dialogue.length;
    const line = topic.dialogue[index];
    return Array.isArray(line) && line.length >= 3
      && typeof line[1] === "string" && typeof line[2] === "string" ? line : null;
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

  function validMissions(topic) {
    return !!(topic && Array.isArray(topic.missions) && topic.missions.length === 6
      && topic.missions.every(function (mission, index) {
        return mission.id === index + 1
          && ["title", "scene", "prompt", "example", "coach"].every(function (field) {
            return typeof mission[field] === "string" && !!mission[field].trim();
          });
      })
      && Array.isArray(topic.twists) && topic.twists.length === 2
      && topic.twists.every(function (twist) {
        return ["scene", "example"].every(function (key) {
          return typeof twist[key] === "string" && !!twist[key].trim();
        });
      }));
  }
  function scenarioVariant(topic, index, twistNumber) {
    if (!validMissions(topic) || !Number.isInteger(index) || index < 0 || index >= 6) return null;
    const base = topic.missions[index];
    if (index !== 5 || !twistNumber) return base;
    if (!Number.isInteger(twistNumber) || twistNumber < 1 || twistNumber > 2) return null;
    return {
      ...base,
      scene: topic.twists[twistNumber - 1].scene,
      prompt: "Используйте конструкцию этого урока и дайте свой ответ на неожиданное условие.",
      example: topic.twists[twistNumber - 1].example,
      coach: "Это другой поворот истории. Подходящих ответов может быть несколько — сравните свою фразу с примером.",
    };
  }

  function getAmericanVoice(voices) {
    return (voices || []).find(function (voice) {
      return String(voice.lang || "").toLowerCase().replace("_", "-") === "en-us";
    }) || null;
  }
  function validTopic(topic) {
    return !!(topic && Number.isInteger(topic.n) && topic.n >= 1 && topic.n <= 28
      && Array.isArray(topic.dialogue) && topic.dialogue.length >= 2
      && Array.isArray(topic.options) && topic.options.length === 3
      && Number.isInteger(topic.correct) && topic.correct >= 0 && topic.correct < topic.options.length);
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { normalizeAnswer, compareModelAnswer, getAmericanVoice, validTopic, validMissions, scenarioVariant, retrievalLine, builderTokens, builderPhrase, builderCorrect };
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
  // Two new retrieval modes use a dialogue already authored for this lesson:
  // listening/transcription and meaning-to-English production. No answer is
  // persisted or marked as a formal pronunciation/listening certificate.
  const retrieval = retrievalLine(topic);
  if (retrieval) {
    const dictation = by("[data-a1-dictation]");
    const backtranslation = by("[data-a1-backtranslation]");
    const play = by("[data-a1-dictation-play]");
    const audioNote = by("[data-a1-dictation-availability]");
    const firstAnswer = by("[data-a1-dictation-input]");
    const secondAnswer = by("[data-a1-backtranslation-input]");
    const firstFeedback = by("[data-a1-dictation-feedback]");
    const secondFeedback = by("[data-a1-backtranslation-feedback]");
    const firstModel = by("[data-a1-dictation-model]");
    const secondModel = by("[data-a1-backtranslation-model]");
    by("[data-a1-backtranslation-prompt]").textContent = retrieval[2];
    if (!speakAvailable) {
      play.disabled = true;
      audioNote.textContent = "Системной озвучки нет: прослушивание недоступно. Второе задание можно выполнить по тексту.";
    }
    play.addEventListener("click", function () { speakLines([retrieval[1]]); });
    firstAnswer.addEventListener("input", function () {
      firstFeedback.hidden = true;
      firstModel.hidden = true;
    });
    secondAnswer.addEventListener("input", function () {
      secondFeedback.hidden = true;
      secondModel.hidden = true;
    });
    dictation.addEventListener("submit", function (event) {
      event.preventDefault();
      if (!firstAnswer.value.trim()) return;
      const match = compareModelAnswer(firstAnswer.value, retrieval[1], topic.retrieval_alternatives);
      firstFeedback.textContent = match
        ? "Запись совпала с текстом реплики. Это не оценка распознавания речи или произношения."
        : "Запись отличается от образца. Переслушайте фразу и сравните слова; отличия пунктуации могут быть допустимы.";
      firstFeedback.dataset.state = match ? "ok" : "retry";
      firstFeedback.hidden = false;
      firstModel.textContent = "Один образец: " + retrieval[1];
      firstModel.hidden = false;
    });
    backtranslation.addEventListener("submit", function (event) {
      event.preventDefault();
      if (!secondAnswer.value.trim()) return;
      secondFeedback.textContent = compareModelAnswer(secondAnswer.value, retrieval[1], topic.retrieval_alternatives)
        ? "Ваш ответ совпал с образцом."
        : "Вариант отличается от образца, но может быть естественным и правильным. Сравните смысл и грамматику.";
      secondFeedback.hidden = false;
      secondModel.textContent = "Один возможный вариант: " + retrieval[1];
      secondModel.hidden = false;
    });
  }

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
    by("[data-a1-repair]").hidden = false;
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

  // Error repair: only reveal the explanation after a correct prepared answer
  // or an explicit request after at least two unsuccessful attempts.
  let repairAttempts = 0;
  const repair = by("[data-a1-repair-form]");
  const repairFeedback = by("[data-a1-repair-feedback]");
  const repairReveal = by("[data-a1-repair-reveal]");
  const repairExplanation = by("[data-a1-repair-explanation]");
  repair.addEventListener("submit", function (event) {
    event.preventDefault();
    const value = by("[data-a1-repair-answer]").value.trim();
    if (!value) return;
    repairAttempts += 1;
    const correct = compareModelAnswer(value, topic.repair.correct, topic.repair.alternatives);
    repairFeedback.dataset.state = correct ? "ok" : "retry";
    repairFeedback.textContent = correct
      ? "Верно! Вы нашли ожидаемое исправление. Прочитайте, почему оно работает."
      : repairAttempts === 1
        ? "Пока не совпадает с образцом. Подсказка: " + topic.repair.hint
        : "Пока не совпадает. Попробуйте снова или откройте объяснение.";
    repairFeedback.hidden = false;
    if (correct) {
      repairExplanation.hidden = false;
      repairReveal.hidden = true;
    } else if (repairAttempts >= 2) {
      repairReveal.hidden = false;
    }
  });
  repairReveal.addEventListener("click", function () {
    repairExplanation.hidden = false;
    repairReveal.hidden = true;
  });

  const transfer = by("[data-a1-transfer]");
  transfer.addEventListener("submit", function (event) {
    event.preventDefault();
    if (!by("[data-a1-transfer-answer]").value.trim()) return;
    by("[data-a1-transfer-feedback]").hidden = false;
  });
  // Six additional original story missions per lesson. Open-ended text is
  // NEVER auto-graded: show a model only after an independent written attempt.
  // No backend requests or persistence.
  if (validMissions(topic)) {
    const missionForm = by("[data-a1-mission-form]");
    const answer = by("[data-a1-mission-answer]");
    const result = by("[data-a1-mission-result]");
    const hint = by("[data-a1-mission-hint-text]");
    const prev = by("[data-a1-mission-prev]");
    const next = by("[data-a1-mission-next]");
    const twistButton = by("[data-a1-mission-twist]");
    const twistControls = by("[data-a1-mission-twist-controls]");
    const tabs = [...root.querySelectorAll("[data-a1-mission-index]")];
    const drafts = new Map();
    const completed = new Set();
    const submitted = new Set();
    const selectedMission = Number(by("[data-a1-missions]").dataset.startMission || 1);
    let current = Number.isInteger(selectedMission) && selectedMission >= 1 && selectedMission <= 6
      ? selectedMission - 1 : 0;
    let twist = 0;

    function key() { return String(current) + ":" + String(twist); }
    function activeMission() { return scenarioVariant(topic, current, twist); }
    function saveDraft() { drafts.set(key(), answer.value); }
    function updateMissionProgress() {
      by("[data-a1-mission-progress]").textContent =
        "Ситуация " + (current + 1) + " из 6 · Попробовано: " + completed.size + " из 6";
      tabs.forEach(function (tab, index) {
        if (index === current) tab.setAttribute("aria-current", "step");
        else tab.removeAttribute("aria-current");
        tab.dataset.done = String(completed.has(index));
      });
    }
    function renderMission() {
      const mission = activeMission();
      by("[data-a1-mission-type]").textContent = "ИСТОРИЯ " + (current + 1) + " / 6";
      by("[data-a1-mission-title]").textContent = mission.title;
      by("[data-a1-mission-scene]").textContent = mission.scene;
      by("[data-a1-mission-prompt]").textContent = mission.prompt;
      answer.value = drafts.get(key()) || "";
      hint.textContent = mission.coach;
      hint.hidden = true;
      result.hidden = !submitted.has(key());
      by("[data-a1-mission-example]").textContent = mission.example;
      by("[data-a1-mission-coach]").textContent = mission.coach;
      twistControls.hidden = current !== 5;
      twistButton.textContent = twist
        ? "🎲 Другое условие (" + twist + " из 2)" : "🎲 Неожиданный поворот";
      by("[data-a1-mission-twist-note]").textContent = twist
        ? "Условие изменилось. Не копируйте ответ из предыдущей истории." :
          "Дополнительная импровизация: два заранее подготовленных неожиданных поворота.";
      prev.disabled = current === 0;
      next.disabled = current === 5;
      updateMissionProgress();
    }
    function switchMission(index) {
      if (!Number.isInteger(index) || index < 0 || index > 5) return;
      saveDraft();
      current = index;
      twist = 0;
      renderMission();
      window.EnglishMotion?.enter(by(".active-a1-mission-card"), "scene");
    }
    tabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        switchMission(Number(tab.dataset.a1MissionIndex));
      });
    });
    prev.addEventListener("click", function () { switchMission(current - 1); });
    next.addEventListener("click", function () { switchMission(current + 1); });
    twistButton.addEventListener("click", function () {
      saveDraft();
      twist = (twist + 1) % 3;  // base → surprise 1 → surprise 2 → base
      renderMission();
      window.EnglishMotion?.enter(by(".active-a1-mission-card"), "scene");
      answer.focus();
    });
    by("[data-a1-mission-hint]").addEventListener("click", function () {
      hint.hidden = !hint.hidden;
    });
    missionForm.addEventListener("submit", function (event) {
      event.preventDefault();
      if (!answer.value.trim()) return;
      saveDraft();
      submitted.add(key());
      completed.add(current);
      result.hidden = false;
      updateMissionProgress();
    });
    by("[data-a1-mission-speak]").addEventListener("click", function () {
      if (!submitted.has(key())) return;
      speakLines([activeMission().example]);
    });
    renderMission();
  }

  window.addEventListener("pagehide", stopAudio);
})();
