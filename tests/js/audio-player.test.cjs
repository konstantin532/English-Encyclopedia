const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const vm = require('node:vm');

function player() {
  const el = (extra = {}) => ({value:'100', textContent:'', checked:false, addEventListener(){}, setAttribute(){}, ...extra});
  const duration = el(), progress = new Map();
  const fields = {'[data-play]':el(), '[data-play-label]':el(), '[data-time]':el(), '[data-voice-vol]':el(), '[data-rate]':el(), '[data-rate-out]':el(), '[data-pause-lines]':el(), '[data-duration]':duration};
  const box = {dataset:{slow:'slow.mp3',natural:'natural.mp3'},style:{setProperty:(k,v)=>progress.set(k,v)},querySelector:k=>fields[k]||null,querySelectorAll:()=>[],hasAttribute:()=>false};
  const audios=[];
  class Audio {
    constructor(src){this.src=src;this.currentTime=0;this.duration=NaN;this.paused=true;this.listeners={};audios.push(this);}
    addEventListener(k,fn){(this.listeners[k]??=[]).push(fn);}
    emit(k){for(const fn of this.listeners[k]||[])fn();}
    pause(){this.paused=true;this.emit('pause');}
  }
  vm.runInNewContext(readFileSync(resolve(__dirname,'../../static/js/audio-player.js'),'utf8'),{
    document:{querySelector:s=>s==='[data-story-player]'?box:null,querySelectorAll:()=>[],getElementById:()=>null},Audio,
    localStorage:{getItem:()=>null,setItem(){}},Math,Number,String,Boolean,JSON
  });
  return {voice:audios[0],duration,progress};
}

test('waveform position and total time follow the actual audio clock',()=>{
  const p=player();p.voice.duration=20;p.voice.currentTime=10;p.voice.emit('loadedmetadata');p.voice.emit('timeupdate');
  assert.equal(p.duration.textContent,'0:20');assert.equal(p.progress.get('--audio-progress'),'50%');
});

test('unknown audio duration never creates invalid progress',()=>{
  for(const value of [NaN,Infinity,0]){const p=player();p.voice.duration=value;p.voice.currentTime=10;p.voice.emit('timeupdate');assert.equal(p.progress.get('--audio-progress'),'0%');}
});
