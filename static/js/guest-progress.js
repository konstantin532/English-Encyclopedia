/* Week-one results stay in this browser until an authenticated import succeeds. */
(function(global){
  'use strict';
  const KEY='ee-guest-week-one-v1', MAX=64;
  const document=global.document;
  function notify(text){const el=document?.querySelector('[data-guest-progress-status]');if(el)el.textContent=text;}
  function valid(item){return item && typeof item.key==='string' && /^(exercise|practice|goal):[1-9]\d*$/.test(item.key) && typeof item.token==='string' && item.token.length<=4096;}
  function read(){
    try{const value=JSON.parse(global.localStorage.getItem(KEY)||'[]');return Array.isArray(value)?value.filter(valid).slice(-MAX):[];}
    catch(_){return [];}
  }
  function write(items){
    try{global.localStorage.setItem(KEY,JSON.stringify(items));return true;}
    catch(_){notify('Браузер не смог сохранить результаты.');return false;}
  }
  function remember(item){
    if(!valid(item))return false;
    const items=read(), previous=items.find(x=>x.key===item.key);
    // A completed exercise remains completed; a weekly goal is the learner's latest choice.
    if(previous?.complete && !item.complete && !item.key.startsWith('goal:'))return true;
    return write([...items.filter(x=>x.key!==item.key),item].slice(-MAX));
  }
  function csrf(){return decodeURIComponent((document.cookie.match(/(?:^|; )csrftoken=([^;]+)/)||[])[1]||'');}
  async function importPending(){
    const url=document?.body?.dataset.guestProgressImportUrl;
    const pending=read();
    if(!url||!pending.length)return;
    try{
      const response=await global.fetch(url,{method:'POST',credentials:'same-origin',
        headers:{'Content-Type':'application/json','X-CSRFToken':csrf()},
        body:JSON.stringify({receipts:pending.map(x=>x.token)})});
      if(!response.ok)throw new Error('Import failed');
      const data=await response.json();
      if(!Array.isArray(data.acknowledged))throw new Error('Invalid acknowledgement');
      const sent=new Set(pending.map(x=>x.token));
      const acknowledged=new Set(data.acknowledged.filter(x=>typeof x==='string'&&sent.has(x)));
      if(!write(read().filter(x=>!acknowledged.has(x.token))))return;
      if(data.imported>0){
        notify('Результаты первой недели сохранены в аккаунте.');
        if(global.location?.pathname==='/learning/')global.location.reload();
      }
    }catch(_){notify('Результаты остались в этом браузере. Перенос можно повторить при следующем открытии страницы.');}
  }
  function wireGoal(form){
    const report=form.querySelector('[data-guest-goal-status]');
    const buttons=[...form.querySelectorAll('button[name="status"]')];
    const show=choice=>{
      if(!['done','not_yet'].includes(choice))return;
      buttons.forEach(b=>{const selected=b.value===choice;b.classList.toggle('btn-primary',selected);b.classList.toggle('btn-quiet',!selected);b.setAttribute('aria-pressed',String(selected));});
      report.textContent='Ваша отметка: '+(choice==='done'?'Получилось.':'Ещё нет.');
    };
    show(read().find(x=>x.key===form.dataset.guestGoalKey)?.choice);
    buttons.forEach(b=>b.disabled=false);
    let busy=false;
    form.addEventListener('submit',async event=>{
      event.preventDefault();
      const choice=event.submitter?.value;
      if(busy||!['done','not_yet'].includes(choice))return;
      busy=true;buttons.forEach(b=>b.disabled=true);
      try{
        const response=await global.fetch(form.action,{method:'POST',credentials:'same-origin',
          headers:{'Content-Type':'application/x-www-form-urlencoded','X-CSRFToken':csrf()},body:'status='+choice});
        if(!response.ok)throw new Error('Goal failed');
        const result=await response.json();
        if(!remember(result.guest_receipt))throw new Error('Goal not saved');
        show(result.status);
      }catch(_){report.textContent='Не удалось сохранить отметку. Попробуйте ещё раз.';}
      finally{busy=false;buttons.forEach(b=>b.disabled=false);}
    });
  }
  const api={remember,read,importPending};
  global.GuestProgress=api;
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  if(document){
    const boot=()=>{document.querySelectorAll('[data-guest-week-goal]').forEach(wireGoal);importPending();};
    if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
  }
})(typeof window!=='undefined'?window:globalThis);
