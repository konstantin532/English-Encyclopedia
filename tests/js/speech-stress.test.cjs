const {test} = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const mod = require("../../static/js/speech-stress.js");
const source = fs.readFileSync(path.join(__dirname,"../../static/js/speech-stress.js"),"utf8");

test("word stress exercise follows editorial prominence, not spelling capitalization", () => {
  assert.deepEqual(mod.annotatedStress("I have my coffee", "I have my COFFEE").stressed, [false,false,false,true]);
  assert.deepEqual(mod.annotatedStress("Good morning, day!", "GOOD MORNING | DAY!").stressed, [true,true,true]);
  assert.deepEqual(mod.annotatedStress("Do you like it?", "do you LIKE it?").stressed, [false,false,true,false]);
  assert.deepEqual(mod.annotatedStress("a big big box", "a BIG | BIG BOX").stressed,[false,true,true,true]);
  assert.equal(mod.annotatedStress("wrong text","SOME OTHER WORDS"),null);
  assert.equal(mod.annotatedStress("No words in this","MORE WORDS"),null);
  assert.deepEqual(mod.compare([false,false,false,true],[false,false,false,true]),{correct:4,total:4,allCorrect:true});
});

test("all seven A1 poems have exactly aligned original stress models", () => {
  const files = [
    "p01_my_new_home.yaml","p02_who_is_she.yaml","p03_what_time_is_it.yaml",
    "p04_one_for_you.yaml","p05_read_walk_play.yaml","p06_who_knows.yaml",
    "p07_bus_to_park_street.yaml"
  ];
  let checked=0;
  for(const file of files) {
    const s=fs.readFileSync(path.join(__dirname,"../../content/seed_poems",file),"utf8");
    const body=s.slice(s.indexOf("body: |")+7,s.indexOf("pronunciation:"))
      .split("\n").filter(line=>line.startsWith("  ")&&line.trim())
      .map(line=>line.trim().replace(/\[[A-Z]\d+(?:-[^\]]+)?\]/g,"").replace(/\[\/\]/g,""));
    const stress=[...s.matchAll(/^- stress: (.*)$/gm)].map(match=>match[1]);
    assert.equal(body.length,stress.length,file);
    for(let i=0;i<body.length;i++) {
      assert.ok(mod.annotatedStress(body[i],stress[i]),file+" line "+(i+1)+": "+body[i]+" / "+stress[i]);
      checked++;
    }
  }
  // Every line of every poem is checked; poems have at least 12 lines each.
  assert.ok(checked>=files.length*12, "checked "+checked);
});

test("only text is evaluated, not a fabricated audio speech rating", () => {
  assert.doesNotMatch(source,/getUserMedia|SpeechRecognition|AudioContext|fetch\s*\(/);
  assert.match(source,/разметкой этой строки/);
});

test("tap on words predicts stress; check reveals editorial model; next resets", () => {
  class Node {
    constructor() {this.listeners={};this.dataset={};this.attrs={};this.children=[];this.hidden=false;this.textContent="";}
    addEventListener(type,fn) {this.listeners[type]=fn;}
    dispatch(type) {return this.listeners[type]();}
    setAttribute(key,value) {this.attrs[key]=value;}
    replaceChildren() {this.children=[];}
    append(...nodes) {this.children.push(...nodes);}
  }
  const nodes=new Map(), one=s=>{if(!nodes.has(s))nodes.set(s,new Node());return nodes.get(s);};
  const rows=[
    {dataset:{stressPlain:"I have my coffee",stressModel:"I have my COFFEE"}},
    {dataset:{stressPlain:"Good morning, day!",stressModel:"GOOD MORNING | DAY!"}}
  ];
  const root={querySelector:one,querySelectorAll:selector=>selector==="[data-stress-entry]"?rows:[]};
  const doc={readyState:"complete",querySelectorAll:()=>[root],createElement:()=>new Node()};
  vm.runInNewContext(source,{window:{},document:doc,module:{exports:{}}});
  const words=one("[data-stress-choices]");
  assert.equal(words.children.length,4);
  assert.equal(one("[data-stress-answer]").hidden,true);
  words.children[3].dispatch("click");
  assert.equal(words.children[3].attrs["aria-pressed"],"true");
  one("[data-stress-check]").dispatch("click");
  assert.match(one("[data-stress-feedback]").textContent,/совпал с разметкой/);
  assert.equal(one("[data-stress-answer]").textContent,"I have my COFFEE");
  one("[data-stress-next]").dispatch("click");
  assert.equal(words.children.length,3);
  assert.match(one("[data-stress-position]").textContent,/Строка 2/);
  assert.equal(one("[data-stress-answer]").hidden,true);
});
