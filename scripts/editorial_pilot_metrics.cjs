const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const root = path.resolve(__dirname, '..');
const base = process.argv[2] || 'd88ff746480bb3692246db7df11469879a1180eb';
const git = process.env.EE_GIT || 'git';
const design = ['app','studio','cinematic-studio','motion-system','art-direction','art-light','editorial-world','living-atlas'];
const files = fs.readdirSync(path.join(root,'static/css')).filter(f=>f.endsWith('.css'));
function stats(names, before) {
 let lines=0,bytes=0; const hex=new Set(),radii=new Set();
 for(const name of names){
  const raw=before?execFileSync(git,['show',base+':static/css/'+name],{cwd:root,encoding:'utf8'}):fs.readFileSync(path.join(root,'static/css',name),'utf8');
  const text=raw.replace(/\r\n/g,'\n');
  lines+=text.split('\n').length-(text.endsWith('\n')?1:0);bytes+=Buffer.byteLength(text);
  const clean=text.replace(/\/\*[\s\S]*?\*\//g,'');
  for(const m of clean.matchAll(/#([\da-f]{8}|[\da-f]{6}|[\da-f]{4}|[\da-f]{3})\b/gi))hex.add(m[0].toLowerCase());
  for(const m of clean.matchAll(/border-radius\s*:\s*([^;}]+)/gi))radii.add(m[1].trim().replace(/\s+/g,' '));
 }
 return {files:names.length,lines,bytes,uniqueHex:hex.size,borderRadiusDeclarations:radii.size,radii:[...radii].sort()};
}
console.log(JSON.stringify({method:'Physical LF-normalized lines including comments. Hex literals and normalized border-radius values after stripping comments; variables remain distinct values.',base,all:{before:stats(files,true),after:stats(files,false)},designLayers:{before:stats(files.filter(f=>design.includes(f.slice(0,-4))),true),after:stats(files.filter(f=>design.includes(f.slice(0,-4))),false)}},null,2));
