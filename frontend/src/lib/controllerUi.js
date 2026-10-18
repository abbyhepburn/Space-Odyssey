const clamp=v=>Math.max(-1,Math.min(1,Number(v)||0));
// Both remotes can reach the entire screen. Use raw axes, never mission axes.
export function pointerPosition(raw=[]){
 return {x:50+clamp(raw[1])*49,y:50-clamp(raw[0])*49};
}
export function primarySelector({help,catalog,discovery,phase}){
 if(help)return '.help-layer .close';
 if(catalog)return '.planet-log .catalog-head button';
 if(discovery)return '.discovery-card .close';
 if(phase==='READY')return '.so-launch__primary';
 if(phase==='BRIEFING')return '.tutorial-start';
 if(phase==='RESULTS')return '.results-card .big-button';
 return null;
}
// Ignore counters present at connection/reconnection; never replay an old click.
export function pendingPresses(previous,current){
 if(!previous)return [];
 const presses=[];
 for(let i=0;i<2;i++){
  const delta=(current[i]||0)-(previous[i]||0);
  for(let n=0;n<Math.min(8,Math.max(0,delta));n++)presses.push(i);
 }
 return presses;
}
