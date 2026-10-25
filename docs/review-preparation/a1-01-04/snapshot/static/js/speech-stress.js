/* Visual prominence task from editor-written poem stress guidance.
 * NOT an audio-perception or acoustic pronunciation test.
 */
(function (global) {
  "use strict";
  const TOKEN = /[A-Za-z]+(?:['’][A-Za-z]+)*/g;
  function tokens(text) {
    return typeof text === "string" ? (text.match(TOKEN) || []) : [];
  }
  function annotatedStress(plain, marked) {
    const words = tokens(plain), model = tokens(marked);
    if (!words.length || words.length !== model.length ||
        words.some((w,i) => w.toLowerCase().replace("’","'") !== model[i].toLowerCase().replace("’","'")))
      return null;
    // "I" is always capitalized in AmE; do not mistake spelling for emphasis.
    const stressed = model.map(w => w.length > 1 && w === w.toUpperCase() && /[A-Z]/.test(w));
    return {words, stressed};
  }
  function compare(selected, stressed) {
    if (!Array.isArray(selected) || selected.length !== stressed.length) return null;
    let correct = 0;
    for (let i=0;i<stressed.length;i++) if (Boolean(selected[i])===stressed[i]) correct++;
    return {correct,total:stressed.length,allCorrect:correct===stressed.length};
  }
  function init(root) {
    const list = [...root.querySelectorAll("[data-stress-entry]")];
    const one = selector=>root.querySelector(selector);
    const choices=one("[data-stress-choices]");
    const position=one("[data-stress-position]");
    const answer=one("[data-stress-answer]");
    const feedback=one("[data-stress-feedback]");
    const check=one("[data-stress-check]");
    const reveal=one("[data-stress-reveal]");
    const next=one("[data-stress-next]");
    let index = 0, selected = [], last = null;
    function show() {
      let found = null;
      for (let step=0;step<list.length;step++) {
        const candidate=(index+step)%list.length;
        const row=annotatedStress(list[candidate].dataset.stressPlain, list[candidate].dataset.stressModel);
        if(row) { index=candidate; found=row; break; }
      }
      if(!found) {
        choices.textContent="Для этого стихотворения ещё не заполнена корректная разметка ударений.";
        check.disabled=true;reveal.disabled=true;next.disabled=true;return;
      }
      last=found;
      selected=last.words.map(()=>false);
      choices.replaceChildren();
      last.words.forEach((word,i)=>{
        const btn=document.createElement("button");
        btn.type="button";
        btn.className="speech-stress-word";
        btn.textContent=word;
        btn.setAttribute("aria-pressed","false");
        btn.addEventListener("click",()=>{
          selected[i]=!selected[i];
          btn.setAttribute("aria-pressed",String(selected[i]));
          feedback.textContent="Выберите ударные слова и нажмите «Сверить ударения».";
          answer.hidden=true;
        });
        choices.append(btn);
      });
      position.textContent="Строка "+(index+1)+" из "+list.length;
      answer.textContent=list[index].dataset.stressModel;
      answer.hidden=true;
      feedback.textContent="Где здесь смысловое ударение? Выберите слова, которые произносятся заметнее.";
    }
    check.addEventListener("click",()=>{
      const result=compare(selected,last.stressed);
      if(!result) return;
      answer.hidden=false;
      feedback.textContent=result.allCorrect
        ?"Ваш выбор совпал с разметкой этой строки. Произнесите её с выделенными словами."
        :"Совпало "+result.correct+" из "+result.total+" позиций. Сравните ударения и попробуйте прочитать заново.";
    });
    reveal.addEventListener("click",()=>{
      answer.hidden=false;
      feedback.textContent="Разметка показана. Произнесите строку с выделением ударных слов, затем переходите дальше.";
    });
    next.addEventListener("click",()=>{index=(index+1)%list.length;show();});
    show();
  }
  if(typeof module!=="undefined"&&module.exports) module.exports={tokens,annotatedStress,compare};
  if(typeof document!=="undefined"){
    const boot=()=>document.querySelectorAll("[data-stress-lab]").forEach(init);
    if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot,{once:true});
    else boot();
  }
})(typeof window!=="undefined"?window:globalThis);
