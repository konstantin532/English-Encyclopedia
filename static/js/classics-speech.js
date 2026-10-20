// «Классика»: озвучка голосом браузера (американский английский). Без голоса — понятное сообщение.
(() => {
  const synth = window.speechSynthesis;
  const note = document.querySelector("[data-voice-note]");
  const blocks = [...document.querySelectorAll("[data-speak-text]")];
  if (!synth || typeof window.SpeechSynthesisUtterance !== "function") {
    if (note) note.textContent = "Ваш браузер не умеет читать текст вслух. Откройте страницу в Chrome или Safari.";
    blocks.forEach((b) => b.querySelectorAll("button").forEach((btn) => { btn.disabled = true; }));
    return;
  }
  const pickVoice = () => {
    const voices = synth.getVoices();
    return voices.find((v) => v.lang === "en-US" && /natural|google|samantha|aria|jenny/i.test(v.name))
      || voices.find((v) => v.lang === "en-US") || voices.find((v) => /^en/i.test(v.lang)) || null;
  };
  blocks.forEach((block) => block.querySelectorAll("[data-speak-rate]").forEach((btn) => {
    btn.addEventListener("click", () => {
      synth.cancel();
      const u = new SpeechSynthesisUtterance(block.dataset.speakText);
      u.lang = "en-US";
      u.rate = Number(btn.dataset.speakRate) || 1;
      const voice = pickVoice();
      if (voice) u.voice = voice;
      btn.setAttribute("aria-pressed", "true");
      u.onend = u.onerror = () => btn.setAttribute("aria-pressed", "false");
      synth.speak(u);
    });
  }));
})();
