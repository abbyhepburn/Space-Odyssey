// Uses the same yaw/pitch conventions as the live flight camera.
const wrap = angle => Math.atan2(Math.sin(angle),Math.cos(angle));
export function aimedDiscovery(ship, pilot, discoveries) {
  if (!ship || !pilot) return null;
  let best = null;
  let bestError = Infinity;
  for (const item of discoveries) {
    const [dx,dy,dz]=item.position.map((n,i)=>n-ship[i]);
    const horizontal=Math.hypot(dx,dz);
    if(horizontal<1 || Math.hypot(horizontal,dy)<5) continue;
    const yaw=Math.atan2(dx,-dz);
    const pitch=Math.atan2(dy,horizontal);
    const error=Math.hypot(wrap(yaw-(pilot.yaw||0)),pitch-(pilot.pitch||0));
    // Enlarged selection cone for accessibility. Distant objects remain
    // selectable via the encyclopedia even if outside this view.
    const cone=item.zone==='DEEP_SKY'?0.105:0.14;
    if(error<cone && error<bestError){best=item;bestError=error;}
  }
  return best;
}
