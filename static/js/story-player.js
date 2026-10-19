// Истории и стихи: открытые вопросы, охота за фразами, пропуски в стихотворении.
(() => {
  const csrf = () => (document.cookie.match(/(?:^|; )csrftoken=([^;]+)/) || [])[1] || "";
  const calm = !matchMedia("(prefers-reduced-motion: reduce)").matches && window.gsap;

  // Открытые вопросы: ответ-образец показываем только после попытки.
  document.querySelectorAll("[data-open-question]").forEach((box) => {
    const input = box.querySelector("input");
    const model = box.querySelector("[data-model-answer]");
    input.addEventListener("input", () => { model.hidden = true; });
    box.querySelector("[data-compare]").addEventListener("click", () => {
      if (!input.value.trim()) { input.focus(); input.placeholder = "сначала напишите свой вариант"; return; }
      model.hidden = false;
      if (calm) gsap.fromTo(model, { autoAlpha: 0, y: -4 }, { autoAlpha: 1, y: 0, duration: 0.25 });
    });
  });

  // Охота за фразами: подсветить фразу в тексте и показать её функцию.
  const text = document.querySelector("[data-story-text]");
  document.querySelectorAll("[data-hunt]").forEach((btn) => btn.addEventListener("click", () => {
    text?.querySelectorAll("mark").forEach((m) => m.replaceWith(...m.childNodes));
    text?.normalize();
    const phrase = btn.dataset.hunt.toLowerCase();
    for (const p of text?.querySelectorAll("p") || []) {
      const plain = p.textContent.toLowerCase();
      const at = plain.indexOf(phrase.replace(/[.!?]$/, ""));
      if (at >= 0) { highlight(p, at, at + phrase.replace(/[.!?]$/, "").length); p.scrollIntoView({ block: "center", behavior: calm ? "smooth" : "auto" }); break; }
    }
    document.querySelectorAll("[data-hunt]").forEach((other) => {
      other.setAttribute("aria-expanded", "false");
      if (other.nextElementSibling) other.nextElementSibling.hidden = true;
    });
    const fn = btn.nextElementSibling;
    fn.hidden = false;
    btn.setAttribute("aria-expanded", "true");
  }));

  function highlight(root, start, end) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let pos = 0; const parts = [];
    while (walker.nextNode()) {
      const node = walker.currentNode, len = node.length;
      const s = Math.max(start, pos), e = Math.min(end, pos + len);
      if (s < e) parts.push([node, s - pos, e - pos]);
      pos += len;
    }
    for (const [node, s, e] of parts) {
      const range = document.createRange();
      range.setStart(node, s); range.setEnd(node, e);
      const mark = document.createElement("mark");
      range.surroundContents(mark);
    }
  }

  // Пропуски в стихотворении: проверяет сервер.
  const gapsBox = document.querySelector("[data-poem]");
  if (gapsBox) {
    const revealBtn = document.querySelector("[data-gaps-reveal]");
    const checkBtn = document.querySelector("[data-gaps-check]");
    const status = document.querySelector("[data-gaps-status]");
    const inputs = [...gapsBox.querySelectorAll("[data-gap]")];
    let busy = false;
    const post = async (url, body) => {
      const response = await fetch(url, { method: "POST", headers: {
        "Content-Type": "application/json", "X-CSRFToken": decodeURIComponent(csrf()),
      }, body: JSON.stringify(body) });
      if (!response.ok) throw new Error("HTTP " + response.status);
      const result = await response.json();
      if (typeof result !== "object" || result === null) throw new Error("Bad response");
      return result;
    };
    async function runChecks(reveal) {
      if (busy) return;
      busy = true;
      checkBtn.disabled = true;
      revealBtn.disabled = true;
      status.textContent = reveal ? "Загружаем образцы…" : "Проверяем ответы…";
      let incorrect = 0;
      let firstInvalid = null;
      try {
        for (const input of inputs) {
          const mark = input.nextElementSibling;
          if (!reveal && !input.value.trim()) {
            mark.textContent = " — заполните пропуск";
            mark.dataset.state = "no";
            input.setAttribute("aria-invalid", "true");
            incorrect++;
            firstInvalid ||= input;
            continue;
          }
          if (reveal && input.getAttribute("aria-invalid") === "false") continue;
          const data = await post(input.dataset.url, reveal ? { reveal: true } : { answer: input.value });
          if (reveal) {
            if (typeof data.answer !== "string") throw new Error("Missing answer");
            input.value = data.answer;
            mark.textContent = " — образец показан";
            mark.dataset.state = "reveal";
            input.removeAttribute("aria-invalid");
          } else {
            if (typeof data.correct !== "boolean") throw new Error("Missing result");
            mark.textContent = data.correct ? " — верно" : " — попробуйте ещё раз";
            mark.dataset.state = data.correct ? "ok" : "no";
            input.setAttribute("aria-invalid", String(!data.correct));
            if (!data.correct) {
              incorrect++;
              firstInvalid ||= input;
            }
          }
        }
        status.textContent = reveal ? "Образцы показаны. Попробуйте объяснить, почему нужны эти слова."
          : incorrect ? "Осталось проверить или исправить пропусков: " + incorrect + "."
            : "Все заполненные пропуски совпали с образцами.";
        revealBtn.hidden = reveal || incorrect === 0;
        if (!reveal && firstInvalid) firstInvalid.focus();
      } catch (_) {
        status.textContent = "Сервер недоступен или ответ неполон. Ваш введённый текст сохранён на странице; проверьте соединение и повторите.";
      } finally {
        busy = false;
        checkBtn.disabled = false;
        revealBtn.disabled = false;
      }
    }
    checkBtn.addEventListener("click", () => runChecks(false));
    revealBtn.addEventListener("click", () => runChecks(true));
  }
})();
