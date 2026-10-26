const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const code=fs.readFileSync(require('node:path').resolve(__dirname,'../../static/js/studio-reader.js'),'utf8');
function fixture(scoped=true) {
  const style=()=>({values:{},setProperty(k,v){this.values[k]=v;}});
  const root={style:style()}, other={style:style()}, practice={style:style()}, translate={style:style()};
  const reader={style:style(),closest(){return scoped?root:null;}};
  const button=()=>({disabled:false,addEventListener(type,fn){this.click=fn;}});
  const smaller=button(),larger=button(),output={textContent:''};
  const elements={'[data-lesson-reader]':reader,'[data-lesson-practice]':practice,'[data-lesson-translate]':translate,'[data-reader-smaller]':smaller,'[data-reader-larger]':larger,'[data-reader-size]':output};
  const context={document:{querySelector:s=>elements[s]||null},getComputedStyle:()=>({fontSize:'19px'}),localStorage:{getItem:()=>null,setItem(){}}};
  vm.runInNewContext(code,context);
  return {root,other,reader,practice,translate,smaller,larger,output};
}
test('reader shares scale with its educational surface, including sibling translation',()=>{
  const f=fixture();
  for(let i=0;i<5;i++)f.larger.click();
  assert.equal(f.reader.style.fontSize,'24px');
  assert.equal(f.root.style.values['--reader-scale'],String(24/19));
  assert.equal(f.practice.style.values['--reader-scale'],String(24/19));
  assert.equal(f.other.style.values['--reader-scale'],undefined);
  assert.equal(f.larger.disabled,true);
  for(let i=0;i<9;i++)f.smaller.click();
  assert.equal(f.output.textContent,'15');
  assert.equal(f.smaller.disabled,true);
  assert.equal(f.root.style.values['--reader-scale'],String(15/19));
});
test('legacy reader without educational root keeps its existing practice scale',()=>{
  const f=fixture(false);f.larger.click();
  assert.equal(f.practice.style.values['--reader-scale'],String(20/19));
  assert.equal(f.reader.style.fontSize,'20px');
});
