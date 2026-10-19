const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const os=require('node:os');
const path=require('node:path');

test('stylesheet build detects and repairs stale deployed CSS',async()=>{
 const {buildStyles}=await import('../../scripts/build_styles.mjs');
 const outputDir=await fs.mkdtemp(path.join(os.tmpdir(),'ee-styles-'));
 try{
   await buildStyles({outputDir});
   await buildStyles({outputDir,check:true});
   await fs.appendFile(path.join(outputDir,'foundation.css'),'/* accidental edit */');
   await assert.rejects(buildStyles({outputDir,check:true}),/foundation.css/);
   await buildStyles({outputDir});
   await buildStyles({outputDir,check:true});
 }finally{await fs.rm(outputDir,{recursive:true,force:true});}
});
