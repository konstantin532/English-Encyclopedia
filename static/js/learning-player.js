// Упражнения урока. Ответ проверяет сервер; правильный ответ не приходит
// в браузер, пока ученик не попробует сам или не попросит показать.
(() => {
  function csrf() {
    const m = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
  }

  async function post(url, body) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(String(res.status));
    return res.json();
  }

  document.querySelectorAll("[data-drill]").forEach((form) => {
    const kind = form.dataset.kind;
    const feedback = form.querySelector("[data-feedback]");
    const reveal = form.querySelector("[data-reveal]");
    const line = form.querySelector("[data-build-line]");
    let picked = "";
    let tries = 0;

    const say = (state, html) => {
      feedback.hidden = false;
      feedback.dataset.state = state;
      feedback.innerHTML = html;
      if (window.gsap && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
        gsap.fromTo(feedback, { autoAlpha: 0, y: -4 }, { autoAlpha: 1, y: 0, duration: 0.25 });
      }
    };
    const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

    form.querySelectorAll("[data-choice]").forEach((btn) => btn.addEventListener("click", () => {
      form.querySelectorAll("[data-choice]").forEach((b) => b.setAttribute("aria-pressed", "false"));
      btn.setAttribute("aria-pressed", "true");
      picked = btn.dataset.choice;
    }));

    form.querySelectorAll("[data-word]").forEach((btn) => btn.addEventListener("click", () => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "choice";
      chip.textContent = btn.dataset.word;
      chip.setAttribute("aria-label", `Убрать слово ${btn.dataset.word}`);
      chip.addEventListener("click", () => { chip.remove(); btn.hidden = false; });
      line.appendChild(chip);
      btn.hidden = true;
    }));
    form.querySelector("[data-build-reset]")?.addEventListener("click", () => {
      line.innerHTML = "";
      form.querySelectorAll("[data-word]").forEach((b) => (b.hidden = false));
    });

    const hintBtn = form.querySelector("[data-hint-btn]");
    hintBtn?.addEventListener("click", () => {
      const hint = form.querySelector(".drill-hint");
      hint.hidden = !hint.hidden;
      hintBtn.setAttribute("aria-expanded", String(!hint.hidden));
    });

    const answer = () => {
      if (kind === "choice") return picked;
      if (kind === "fill") return form.querySelector("input").value;
      return [...line.querySelectorAll("button")].map((b) => b.textContent).join(" ");
    };

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const value = answer().trim();
      if (!value) { say("no", kind === "choice" ? "Выберите один вариант." : kind === "fill" ? "Впишите слово." : "Соберите фразу из слов."); return; }
      let data;
      try { data = await post(form.dataset.url, { answer: value }); }
      catch (err) { say("no", "Не удалось проверить ответ: нет связи с сервером. Обновите страницу и попробуйте ещё раз."); return; }
      if (data.correct) {
        say("ok", `<strong>Верно.</strong> ${esc(data.explanation)}`);
        reveal.hidden = true;
      } else {
        tries += 1;
        say("no", tries === 1 ? "Пока не так. Попробуйте ещё раз или откройте подсказку." : "Снова не так. Можно открыть ответ с объяснением.");
        if (tries >= 2) reveal.hidden = false;
      }
    });

    reveal.addEventListener("click", async () => {
      let data;
      try { data = await post(form.dataset.url, { reveal: true }); }
      catch (err) { say("no", "Не удалось загрузить ответ. Обновите страницу."); return; }
      say("reveal", `Ответ: <strong lang="en">${esc(data.answer)}</strong>. ${esc(data.explanation)}`);
      reveal.hidden = true;
    });
  });
})();
