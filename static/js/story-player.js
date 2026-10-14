// Истории и стихи: открытые вопросы, охота за фразами, пропуски в стихотворении.
(() => {
  const csrf = () => (document.cookie.match(/(?:^|; )csrftoken=([^;]+)/) || [])[1] || "";
  const calm = !matchMedia("(prefers-reduced-motion: reduce)").matches && window.gsap;

  // Открытые вопросы: ответ-образец показываем только после попытки.
  document.querySelectorAll("[data-open-question]").forEach((box) => {
    const input = box.querySelector("input");
    const model = box.querySelector("[data-model-answer]");
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
    const post = (url, body) => fetch(url, { method: "POST", headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() }, body: JSON.stringify(body) }).then((r) => r.json());
    document.querySelector("[data-gaps-check]").addEventListener("click", async () => {
      let allRight = true;
      for (const input of gapsBox.querySelectorAll("[data-gap]")) {
        const mark = input.nextElementSibling;
        if (!input.value.trim()) { mark.textContent = " ?"; allRight = false; continue; }
        const data = await post(input.dataset.url, { answer: input.value });
        mark.textContent = data.correct ? " ✓" : " ✗";
        mark.dataset.state = data.correct ? "ok" : "no";
        input.setAttribute("aria-invalid", String(!data.correct));
        if (!data.correct) allRight = false;
      }
      revealBtn.hidden = allRight;
    });
    revealBtn.addEventListener("click", async () => {
      for (const input of gapsBox.querySelectorAll("[data-gap]")) {
        const data = await post(input.dataset.url, { reveal: true });
        if (input.getAttribute("aria-invalid") !== "false") { input.value = data.answer; input.nextElementSibling.textContent = " ←"; }
      }
      revealBtn.hidden = true;
    });
  }
})();
