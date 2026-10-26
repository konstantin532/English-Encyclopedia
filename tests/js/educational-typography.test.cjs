const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const source=path.resolve(__dirname,'../../static/scss/educational-reading.scss');
test('educational reading has three scoped palettes without changing marker semantics',()=>{
  assert.ok(fs.existsSync(source),'missing educational reading entrypoint');
  const css=fs.readFileSync(source,'utf8');
  for(const value of ['#FAFAF7','#26332F','#194B3B','#D8DED8','#F7F5EF','#E7ECE6','#B99A68','#F5F4F0','#202B30','#284B63','#E9EEF0','#D3DBDE']) assert.ok(css.toLowerCase().includes(value.toLowerCase()),value);
  assert.match(css,/\[data-educational-reading\]/);
  assert.doesNotMatch(css,/(?:^|\n)\s*(?:body|html|:root|\.studio-sidebar|\.mk)(?:\s|[{:])/);
  assert.match(css,/var\(--font-ipa\)/);
});
