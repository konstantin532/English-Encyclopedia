import * as sass from 'sass';
import {readdir,readFile,writeFile,mkdir} from 'node:fs/promises';
import {fileURLToPath,pathToFileURL} from 'node:url';
import path from 'node:path';
const root=fileURLToPath(new URL('../',import.meta.url));
export async function buildStyles({outputDir=path.join(root,'static/css'),check=false}={}) {
 const source=path.join(root,'static/scss');
 const entries=(await readdir(source)).filter(n=>n.endsWith('.scss')&&!n.startsWith('_')).sort();
 const stale=[];
 if(!check) await mkdir(outputDir,{recursive:true});
 for(const entry of entries){
  const name=entry.replace(/\.scss$/,'.css');
  const result=sass.compile(path.join(source,entry),{style:'expanded',charset:false,sourceMap:false});
  const css='/* Generated from static/scss/'+entry+'; run pnpm build:css. Do not edit. */\n'+result.css+'\n';
  const target=path.join(outputDir,name);
  if(check){
   const current=await readFile(target,'utf8').catch(()=>null);
   if(current!==css){
    stale.push(name);
    if(name==='editorial-world.css' && current){
     let i=0;while(i<Math.min(current.length,css.length)&&current[i]===css[i])i++;
     console.log('VISUAL_CSS_DIFF offset='+i+' committed='+JSON.stringify(current.slice(Math.max(0,i-50),i+150))+' generated='+JSON.stringify(css.slice(Math.max(0,i-50),i+150)));
    }
   }
  }
  else await writeFile(target,css);
 }
 if(stale.length)throw Error('Stale CSS: '+stale.join(', ')+'. Run pnpm build:css.');
 return entries.length;
}
if(process.argv[1]&&pathToFileURL(path.resolve(process.argv[1])).href===import.meta.url){
 try{console.log('Stylesheets verified: '+await buildStyles({check:process.argv.includes('--check')}));}
 catch(error){console.error(error.message);process.exitCode=1;}
}
