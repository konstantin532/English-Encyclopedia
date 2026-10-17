(function(){
'use strict';
const Text=window.EEAuthoringText;
function el(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;}
function button(text,fn,cls='ee-button'){const b=el('button',cls,text);b.type='button';b.addEventListener('click',fn);return b;}
function fieldLabel(text,input){const l=el('label','ee-label');const s=el('span','',text);l.append(s,input);return l;}
function marked(raw,config,onchange){let state=Text.decode(raw||'');const box=el('div','ee-marked'),input=el('textarea','ee-plain'),preview=el('div','ee-preview'),note=el('p','ee-status'),toolbar=el('div','ee-mark-tools');input.value=state.plain;input.rows=4;input.setAttribute('aria-label','Текст без технической разметки');input.placeholder='Пишите обычный текст…';preview.setAttribute('aria-label','Предпросмотр учебной разметки');note.setAttribute('aria-live','polite');note.textContent='Готовую разметку видно ниже. Чтобы изменить её, выделите слово в тексте и выберите его значение.';const tools=el('details','ee-tools-disclosure');tools.append(el('summary','','Разметка слов'));const category=el('select'),kind=el('select');category.setAttribute('aria-label','Часть речи');kind.setAttribute('aria-label','Значение слова');const lookup=new Map();config.categories.forEach((cat,i)=>{const o=el('option','',cat.name);o.value=i;category.append(o);cat.classes.forEach(c=>lookup.set(c.id,c));});function classes(){kind.replaceChildren();config.categories[Number(category.value)].classes.forEach(c=>{const o=el('option','',c.name);o.value=c.id;kind.append(o);});}category.addEventListener('change',classes);classes();function render(){preview.replaceChildren();let pos=0;for(const s of state.spans){preview.append(document.createTextNode(state.plain.slice(pos,s.start)));const c=lookup.get(s.tag);const word=el('span','ee-word',state.plain.slice(s.start,s.end));word.title=c?c.name:'Учебная разметка';if(c){word.style.color=c.color;word.style.textDecorationLine=c.line;word.style.textDecorationStyle=c.style;}function selectWord(){tools.open=true;const ci=config.categories.findIndex(cat=>cat.classes.some(item=>item.id===s.tag));if(ci>=0){category.value=ci;classes();kind.value=s.tag;}input.focus();input.setSelectionRange(s.start,s.end);}word.tabIndex=0;word.setAttribute('role','button');word.setAttribute('aria-label',state.plain.slice(s.start,s.end)+': '+(c?c.name:'разметка')+'. Изменить');word.addEventListener('click',selectWord);word.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();selectWord();}});preview.append(word);pos=s.end;}preview.append(document.createTextNode(state.plain.slice(pos)));if(!state.plain)preview.append(el('span','ee-placeholder','Здесь появится предпросмотр текста.'));}
function apply(tag){if(!Text.mark(state,input.selectionStart,input.selectionEnd,tag)){note.textContent='Сначала выделите слово или выражение в поле текста.';input.focus();return;}render();onchange(Text.encode(state));note.textContent=tag?'Разметка назначена.':'Разметка выделенного фрагмента убрана.';}
toolbar.append(category,kind,button('Назначить',()=>apply(kind.value)),button('Убрать разметку',()=>apply(null),'ee-button ee-secondary'));input.addEventListener('input',()=>{const lost=Text.edit(state,input.value);render();onchange(Text.encode(state));note.textContent=lost?'Текст изменён. Проверьте разметку изменённых слов: прежняя подсказка для них снята.':'Текст изменён. Новым словам разметка назначается вручную.';});tools.append(toolbar,note);box.append(input,tools,preview);render();return box;}
function choices(source,current){const result={...source};if(current&&!Object.hasOwn(result,current))result[current]=current+' (сохранённое значение)';return result;}
function records(host,source,ui,config){
  let value;
  try {value=JSON.parse(source.value||'[]');if(!Array.isArray(value)||value.some(r=>!r||typeof r!=='object'||Array.isArray(r)))throw Error();}
  catch(e){ui.append(el('p','errornote','Данные не удалось открыть в карточках. Сохранённый исходник не изменён. Обратитесь к разработчику.'));return;}
  const script=config.mode==='script', snapshot=source.value, initialCanonical=JSON.stringify(value);
  const schema=script?[
    {key:'speaker',label:'Кто говорит',kind:'roles',required:true},
    {key:'kind',label:'Тип реплики',kind:'kinds'},
    {key:'emotion',label:'Эмоция',kind:'emotions'},
    {key:'music',label:'Музыка',kind:'music'},
    {key:'text',label:'Текст реплики',kind:'marked',required:true},
    {key:'spoken',label:'Как произносится (если отличается)',kind:'marked'},
    {key:'ru',label:'Перевод на русский (необязательно)',kind:'text'}
  ]:config.fields;
  let active=0, removed=null;
  const list=el('div','ee-record-list'), status=el('p','ee-compose-status'), controls=el('div','ee-compose-controls');
  status.setAttribute('aria-live','polite');
  function message(dirty=false){status.textContent=(dirty&&JSON.stringify(value)!==initialCanonical?'Есть несохранённые изменения · ':'')+value.length+(script?' реплик':' карточек');}
  function sync(){source.value=JSON.stringify(value);source.dispatchEvent(new Event('change',{bubbles:true}));message(true);}
  const add=button(script?'+ Добавить реплику':'+ Добавить карточку',()=>{
    const row={};schema.filter(f=>f.required).forEach(f=>row[f.key]=f.key==='speaker'?(Object.keys(config.roles)[0]||'anna'):'');
    value.push(row);active=value.length-1;sync();draw();list.lastElementChild?.querySelector('textarea')?.focus();
  });
  const undo=button('Вернуть удалённую карточку',()=>{if(!removed)return;active=Math.min(removed.index,value.length);value.splice(active,0,removed.row);removed=null;undo.hidden=true;sync();draw();},'ee-button ee-secondary');
  undo.hidden=true;
  if(script){
    const quick=el('details','ee-quick-entry'),summary=el('summary','','Вставить историю обычным текстом'),paste=el('textarea','ee-bulk-text'),speaker=el('select');
    quick.open=!value.length;paste.rows=5;paste.placeholder='Напишите или вставьте историю. Разделяйте абзацы пустой строкой.';
    Object.entries(config.roles).forEach(([key,label])=>{const option=el('option','',label);option.value=key;speaker.append(option);});
    const feedback=el('p','ee-status');feedback.setAttribute('aria-live','polite');
    const importText=button('Добавить абзацы в историю',()=>{
      const lines=Text.paragraphsToLines(paste.value,speaker.value);
      if(!lines.length){feedback.textContent='Сначала напишите или вставьте текст.';paste.focus();return;}
      active=value.length;value.push(...lines);paste.value='';sync();draw();feedback.textContent='Добавлено реплик: '+lines.length+'. Существующие реплики сохранены. Проверьте персонажей и разметку перед публикацией.';
      list.children[active]?.querySelector('summary')?.focus();
    });
    quick.append(summary,el('p','ee-intro','Каждый абзац станет отдельной репликой рассказчика. Реплики добавятся в конец истории. Текст можно сохранить черновиком и разметить позже.'),fieldLabel('Кто рассказывает',speaker),fieldLabel('Текст истории',paste),importText,feedback);
    ui.append(quick);
  }
  function draw(){
    list.replaceChildren();
    value.forEach((row,index)=>{
      const card=el(script?'details':'section',script?'ee-record ee-scene':'ee-record');
      const title=el('strong','',script?'Реплика '+(index+1):'Карточка '+(index+1));
      let excerpt;
      if(script){
        card.open=index===active;
        const summary=el('summary','ee-scene-summary'),who=el('span','ee-scene-who',config.roles[row.speaker]||row.speaker||'Выберите персонажа');
        excerpt=el('span','ee-scene-excerpt',Text.decode(row.text||'').plain||'Напишите реплику…');
        summary.append(title,who,excerpt);card.append(summary);
        card.addEventListener('toggle',()=>{if(card.open){active=index;[...list.children].forEach(other=>{if(other!==card)other.open=false;});}});
      }else card.append(title);
      const fields=el('div','ee-record-fields'),metadata=el('details','ee-line-settings'),optional=el('details','ee-optional');
      metadata.append(el('summary','','Кто и как говорит'));
      const metaFields=el('div','ee-settings-grid');metadata.append(metaFields);
      optional.append(el('summary','','Произношение и перевод'));
      schema.forEach(f=>{
        const current=row[f.key]??'';
        const set=v=>{if(v===''&&!Object.hasOwn(row,f.key))return;row[f.key]=v;if(excerpt&&f.key==='text')excerpt.textContent=Text.decode(v).plain||'Напишите реплику…';sync();};
        let input;
        if(['roles','kinds','emotions','music'].includes(f.kind)){
          input=el('select');
          const sets={roles:config.roles,kinds:{speech:'Прямая речь',narration:'Рассказ'},emotions:config.emotions,music:config.music};
          const options=choices(sets[f.kind],current);
          if(!f.required&&!['kinds','emotions'].includes(f.kind)){const blank=el('option','',f.kind==='music'?'Без смены музыки':'Не задано');blank.value='';input.append(blank);}
          Object.entries(options).forEach(([key,label])=>{const option=el('option','',label);option.value=key;input.append(option);});
          input.value=current||(f.kind==='kinds'?'speech':f.kind==='emotions'?'neutral':'');
          input.addEventListener('change',()=>{if(!input.value&&!f.required){delete row[f.key];sync();}else set(input.value);if(script&&f.key==='speaker')card.querySelector('.ee-scene-who').textContent=config.roles[row.speaker]||row.speaker;});
        }else if(f.kind==='marked')input=marked(current,config,set);
        else{input=el('textarea','ee-record-text');input.rows=2;input.value=current;input.addEventListener('input',()=>set(input.value));}
        const wrap=el('div','ee-field ee-field-'+f.kind);
        if(f.kind==='marked')wrap.append(el('div','ee-field-title',f.label+(f.required?' *':'')),input);
        else wrap.append(fieldLabel(f.label+(f.required?' *':''),input));
        if(script&&['spoken','ru'].includes(f.key))optional.append(wrap);
        else if(script&&['speaker','kind','emotion','music'].includes(f.key))metaFields.append(wrap);
        else fields.append(wrap);
      });
      if(script)fields.append(metadata,optional);
      const actions=el('div','ee-record-actions');
      const up=button('Выше',()=>{[value[index-1],value[index]]=[value[index],value[index-1]];active=index-1;sync();draw();list.children[active]?.querySelector('summary')?.focus();});up.disabled=index===0;
      const down=button('Ниже',()=>{[value[index+1],value[index]]=[value[index],value[index+1]];active=index+1;sync();draw();list.children[active]?.querySelector('summary')?.focus();});down.disabled=index===value.length-1;
      const remove=button('Убрать',()=>{removed={index,row:value[index]};value.splice(index,1);undo.hidden=false;active=Math.max(0,index-1);sync();draw();undo.focus();},'ee-button ee-remove');
      actions.append(up,down,remove);fields.append(actions);card.append(fields);list.append(card);
    });
  }
  controls.append(add,undo);ui.append(status,list,controls);message();draw();
  const restore=button('Вернуть исходное содержимое поля',()=>{if(window.confirm('Вернуть содержимое этого поля к состоянию при открытии страницы?')){value=JSON.parse(snapshot);removed=null;undo.hidden=true;active=0;sync();draw();}},'ee-button ee-secondary');
  const footer=el('div','ee-editor-footer');footer.append(restore);ui.append(footer);
}
function poemEditor(host,source,ui,config){
  let value=JSON.parse(source.value||'{}');if(!value||typeof value.body!=='string'||!Array.isArray(value.pronunciation)||!Array.isArray(value.gaps))throw Error('Invalid poem');
  const initial=JSON.stringify(value),status=el('p','ee-compose-status'),notice=el('p','ee-status');status.setAttribute('aria-live','polite');notice.setAttribute('aria-live','polite');
  const details=el('details','ee-poem-notes'),list=el('div','ee-poem-lines');details.append(el('summary','','Произношение и пропуски по строкам'),el('p','ee-status','Необязательно. Откройте строку, чтобы добавить подсказки или выбрать слово для упражнения.'),list);
  function sync(){source.value=JSON.stringify(value);status.textContent=Text.poemLines(value.body).length+' строк · '+(JSON.stringify(value)===initial?'Содержимое сохранено':'Есть несохранённые изменения');}
  function draw(){list.replaceChildren();const lines=Text.poemLines(value.body);if(!lines.length){list.append(el('p','ee-empty','Сначала добавьте текст произведения. Строки появятся здесь автоматически.'));return;}
    lines.forEach((line,index)=>{const card=el('details','ee-poem-line');card.append(el('summary','','Строка '+(index+1)+' · '+line));const grid=el('div','ee-settings-grid');
      for(const [key,label,hint] of [['stress','Ударения и ритм','Например: GOOD MORning'],['ipa','Транскрипция IPA','Например: /ɡʊd ˈmɔːnɪŋ/'],['ru','Подсказка по-русски','Перевод или пояснение произношения']]){const input=el('input');input.type='text';input.value=value.pronunciation[index]?.[key]||'';input.placeholder=hint;input.addEventListener('input',()=>{while(value.pronunciation.length<=index)value.pronunciation.push({});if(input.value)value.pronunciation[index][key]=input.value;else delete value.pronunciation[index][key];sync();});grid.append(fieldLabel(label,input));}
      const select=el('select');select.setAttribute('aria-label','Слово для пропуска');const empty=el('option','','Без пропуска');empty.value='';select.append(empty);const gap=value.gaps.find(g=>g.line===index+1);const words=[...new Set(line.match(/[A-Za-z]+(?:['’][A-Za-z]+)*/g)||[])];if(gap&&!words.includes(gap.word))words.push(gap.word);for(const word of words){const option=el('option','',word);option.value=word;select.append(option);}select.value=gap?.word||'';
      select.addEventListener('change',()=>{const previous=value.gaps.find(g=>g.line===index+1);value.gaps=value.gaps.filter(g=>g.line!==index+1);if(select.value)value.gaps.push({...previous,line:index+1,word:select.value});value.gaps.sort((a,b)=>a.line-b.line);sync();});grid.append(fieldLabel('Слово для пропуска',select));card.append(grid);list.append(card);});
  }
  const editor=marked(value.body,config,body=>{const aligned=Text.reconcilePoem(Text.poemLines(value.body),Text.poemLines(body),value.pronunciation,value.gaps);value={...value,body,pronunciation:aligned.pronunciation,gaps:aligned.gaps};if(aligned.removed)notice.textContent='Для изменённых строк сняты старые подсказки и пропуски. Проверьте их перед публикацией.';sync();draw();});editor.querySelector('.ee-plain').rows=12;host.classList.add('ee-poem-editor');ui.append(el('p','ee-status','Введите стих или скороговорку обычным текстом. Сохраняйте переносы строк; пустая строка разделяет строфы.'),status,editor,notice,details);sync();draw();
}
function init(host){if(host.dataset.ready||host.closest('.empty-form'))return;const source=host.querySelector('.ee-source'),ui=host.querySelector('.ee-authoring-ui');if(!source||!ui||source.disabled)return;host.dataset.ready='true';try{const config=JSON.parse(host.dataset.config);if(config.mode==='marked')ui.append(marked(source.value,config,v=>{source.value=v;}));else if(config.mode==='poem')poemEditor(host,source,ui,config);else records(host,source,ui,config);}catch(e){ui.append(el('p','errornote','Редактор не загрузился. Исходные данные сохранены. Не меняйте это поле до исправления ошибки.'));}}
function scan(node){if(node.matches?.('.ee-authoring'))init(node);node.querySelectorAll?.('.ee-authoring').forEach(h=>{if(!h.closest('.empty-form'))init(h);});}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>scan(document));else scan(document);
document.addEventListener('formset:added',e=>scan(e.target));new MutationObserver(changes=>changes.forEach(c=>c.addedNodes.forEach(n=>{if(n.nodeType===1&&!n.closest('.ee-authoring-ui'))scan(n);}))).observe(document.documentElement,{childList:true,subtree:true});
})();