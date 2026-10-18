import React from 'react';
const smooth=(t,a,b)=>{const x=Math.max(0,Math.min(1,(t-a)/(b-a)));return x*x*(3-2*x)};
export default function LaunchCinematic({elapsed}){
 const t=elapsed/1000;
 const burn=smooth(t,5,8),power=smooth(t,2.4,3.5);
 const switchCue=smooth(t,1.4,2.1)*(1-smooth(t,3.3,4.1));
 return <div className="launch-cinematic orbital-cinematic" aria-label="A crew member checks the launch control from inside the cockpit">
  <div className="orbital-stage" style={{transform:`translate(-50%,-50%) translate(0,${-burn*.35}%)`}}>
   <img className="orbital-backdrop" src="/art/orbital-cockpit.png" alt=""/>
   <div className="orbital-power-shadow" style={{opacity:.65*(1-power)}}/>
   <div className={`orbital-switch-cue ${switchCue>.01?'orbital-switch-cue--active':''}`} style={{'--cue-opacity':switchCue}} aria-hidden="true"><i/><span>LAUNCH CONTROL</span></div>
   <div className="orbital-engine-light" style={{opacity:burn*.16}}/>
  </div>
  <div className="orbital-vignette"/>
 </div>;
}
