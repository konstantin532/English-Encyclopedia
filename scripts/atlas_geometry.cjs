// Only authored reading height may change; shell and column geometry stay invariant.
function geometryDelta(screen,selector,before,after){
  let keys=['x','y','width','height'];
  if(screen==='chapter'&&selector==='.story-script')keys=['x','width'];
  else if(screen==='chapter'&&selector==='.studio-lesson-card')keys=['x','width','height'];
  return Math.max(...keys.map(key=>Math.abs(before[key]-after[key])));
}
module.exports={geometryDelta};
