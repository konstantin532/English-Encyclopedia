/* Adaptive oral recall. Stores only self-ratings/due dates; microphone data NEVER uploaded. */
(function (global) {
  "use strict";
  const MS_DAY = 86400000, DAYS = [0, 1, 3, 7, 14];
  const RATINGS = ["again", "hard", "good"];
  function nextState(previous, rating, now) {
    if (!RATINGS.includes(rating)) throw new TypeError("Unknown oral self-rating");
    const stage = previous && Number.isInteger(previous.stage) ? previous.stage : 0;
    const nextStage = rating === "again" ? 0 : rating === "hard" ? Math.max(0, stage - 1) : Math.min(4, stage + 1);
    const delay = rating === "again" ? 0 : rating === "hard" ? 1 : DAYS[nextStage];
    return { stage: nextStage, rating, attempts: (previous?.attempts || 0) + 1,
      next_review_at: new Date(now + delay * MS_DAY).toISOString(), due: delay === 0 };
  }
  function nextDue(items, count, current, now) {
    for (let step = 1; step <= count; step++) {
      const index = (current + step) % count;
      const p = items[index];
      if (!p || Date.parse(p.next_review_at) <= now) return index;
    }
    return null;
  }
  function init(root) {
    const panel = root.querySelector("[data-speech-review]");
    if (!panel) return;
    const entries = root.querySelectorAll("[data-speech-entry]");
    const count = entries.length, grades = root.querySelector("[data-speech-grades]");
    const report = root.querySelector("[data-speech-review-status]");
    const next = root.querySelector("[data-speech-next-review]");
    const endpoint = root.dataset.speechEndpoint;
    const key = root.dataset.speechKey;
    const signedIn = root.dataset.speechPersist === "true";
    const records = Array(count).fill(null);
    // A GET started on page load can finish AFTER a successful rating POST.
    // Never let that older snapshot overwrite a newly saved response.
    const locallySaved = new Set();
    let busy = false, loadFailed = false;
    function current() { return Math.max(0, Math.min(count - 1, Number(root.dataset.speechIndex || 0))); }
    function show() {
      if (!count) { panel.hidden = true; return; }
      const phase = root.dataset.speechMode;
      grades.hidden = phase !== "recall" && phase !== "transfer";
      const i = current(), p = records[i], now = Date.now();
      const dueCount = records.filter(x => x && Date.parse(x.next_review_at) <= now).length;
      const remaining = records.filter(x => !x).length;
      const status = p ? (
        Date.parse(p.next_review_at) <= now
          ? "Фрагмент назначен к повторению сейчас."
          : "Следующее повторение: " + new Date(p.next_review_at).toLocaleDateString("ru-RU") + "."
      ) : "Новый фрагмент: ещё нет самооценки.";
      report.textContent = status + " Новых: " + remaining + ". Пора повторить: " + dueCount + ". " +
        (signedIn ? (loadFailed ? "Сохранение сейчас недоступно." : "Самооценка сохраняется в аккаунте.") :
          "Без входа отметки существуют только пока открыта страница.");
      next.disabled = nextDue(records, count, i, now) === null;
    }
    root.querySelectorAll("[data-speech-grade]").forEach(btn => btn.addEventListener("click", async () => {
      if (busy || !["recall", "transfer"].includes(root.dataset.speechMode)) return;
      const rating = btn.dataset.speechGrade, index = current();
      if (!RATINGS.includes(rating)) return;
      busy = true;
      root.querySelectorAll("[data-speech-grade]").forEach(x => x.disabled = true);
      try {
        if (signedIn) {
          const csrf = (document.cookie.match(/(?:^|; )csrftoken=([^;]+)/) || [])[1] || "";
          const res = await global.fetch(endpoint, {
            method: "POST", credentials: "same-origin",
            headers: { "Content-Type": "application/json", "X-CSRFToken": decodeURIComponent(csrf) },
            body: JSON.stringify({key, index, rating})
          });
          if (!res.ok) throw new Error("Unable to save oral review");
          const data = await res.json();
          records[index] = data;
          locallySaved.add(index);
          loadFailed = false;
        } else {
          records[index] = nextState(records[index], rating, Date.now());
        }
        show();
      } catch (_) {
        loadFailed = true;
        report.textContent = "Не удалось сохранить самооценку. Проверьте подключение или войдите заново. Отметка не засчитана.";
      } finally {
        busy = false;
        root.querySelectorAll("[data-speech-grade]").forEach(x => x.disabled = false);
      }
    }));
    next.addEventListener("click", () => {
      const target = nextDue(records, count, current(), Date.now());
      if (target !== null && typeof root.dispatchEvent === "function" && typeof global.CustomEvent === "function")
        root.dispatchEvent(new global.CustomEvent("speech:jump", {detail: {index: target}}));
      show();
    });
    if (typeof root.addEventListener === "function") root.addEventListener("speech:changed", show);
    if (signedIn && endpoint && key && typeof global.fetch === "function") {
      global.fetch(endpoint + "?key=" + encodeURIComponent(key), {credentials: "same-origin"})
        .then(res => { if (!res.ok) throw new Error("Unable to load"); return res.json(); })
        .then(data => {
          if (!Array.isArray(data.items)) throw new Error("Invalid review data");
          data.items.forEach(p => {
            if (Number.isInteger(p.index) && p.index >= 0 && p.index < count && !locallySaved.has(p.index))
              records[p.index] = p;
          });
          show();
        }).catch(() => { if (!locallySaved.size) loadFailed = true; show(); });
    }
    show();
  }
  if (typeof module !== "undefined" && module.exports) module.exports = {nextState, nextDue};
  if (typeof document !== "undefined") {
    const boot = () => document.querySelectorAll("[data-speech-studio]").forEach(init);
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot, {once: true});
    else boot();
  }
})(typeof window !== "undefined" ? window : globalThis);
