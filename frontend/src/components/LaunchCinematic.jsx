import React from 'react';
const smooth=(t,a,b)=>{const x=Math.max(0,Math.min(1,(t-a)/(b-a)));return x*x*(3-2*x)};
export default function LaunchCinematic({elapsed}){
 const t=elapsed/1000;
 const reach=smooth(t,.5,2.5)*(1-smooth(t,4,6));
 const burn=smooth(t,5,8),power=smooth(t,2.4,3.5);
 return <div className="launch-cinematic orbital-cinematic" aria-label="First-person astronaut powers the spacecraft above Earth's curved horizon, then begins an orbital departure">
  <div className="orbital-stage" style={{transform:`translate(-50%,-50%) translate(${Math.sin(t*42)*burn*1.3}px,${Math.cos(t*31)*burn*1.1}px)`}}>
   <img className="orbital-backdrop" src="/art/orbital-cockpit.png" alt=""/>
   <div className="orbital-window"><img src="/art/orbital-cockpit.png" alt="" style={{transform:`translateY(${burn*3}%) scale(${1-burn*.025})`}}/></div>
   <div className="orbital-power-shadow" style={{opacity:.65*(1-power)}}/>
   {[24,49,68].map((left,i)=><div key={left} className="orbital-screen-light" style={{left:`${left}%`,opacity:smooth(t,2.5+i*.3,3+i*.3)*.25}}/>)}
   <div className="orbital-ignition" style={{opacity:power}}/>
   <img className="orbital-glove" src="/art/astronaut-glove.png" alt="Astronaut's gloved hand reaching for the ignition switch" style={{transform:`translate(${(1-reach)*38}%,${(1-reach)*85}%) rotate(${(1-reach)*12}deg)`,opacity:smooth(t,.1,.7)}}/>
   <div className="orbital-engine-light" style={{opacity:burn*.3}}/>
  </div>
  <div className="orbital-vignette"/>
 </div>;
}
