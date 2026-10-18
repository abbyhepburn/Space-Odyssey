import React from 'react';
import MovementDemo from './MovementDemo';
const labels={JUMP:'Jump',DUCK:'Duck',FLICK:'Flick upward',SHAKE:'Shake',STEER:'Move joystick',TILT:'Tilt remote',PRESS:'Press joystick'};
export default function ChallengeTutorial({game:g,status,send}){
 const art=g.planet==='SATURN'?'saturn-expedition.jpg':g.planet==='EARTH'?'earth-orbit.jpg':['MARS','VENUS','MERCURY'].includes(g.planet)?'orange-frontier.jpg':'asteroid-nebula.jpg';
 return <section className="challenge-tutorial" style={{'--mission-art':`url('/art/${art}')`}}>
  <header><span>{g.planet} · 15 SECONDS · PLAYER VS PLAYER</span><h1>{g.mission.name}</h1><p>{g.mission.briefing}</p></header>
  <div className="tutorial-moves">{g.mission.movements.map(m=><article key={m.control}><MovementDemo action={m.control}/><div><h2>{labels[m.control]}</h2><p>{m.instruction}</p><small>Both players · Your own remote</small></div></article>)}</div>
  <aside className="tutorial-fact"><b>DISCOVER {g.planet}</b><p>{g.education?.fact}</p></aside>
  <p className="tutorial-tip">Jump or duck in front of the laptop camera. You can also tilt the remote up to jump or push the joystick forward to duck. Watch your lane and collect points.</p>
  <footer><div><button onClick={()=>send('FLIGHT,REGENERATE')}>Different game ↻</button><button onClick={()=>send('FLIGHT,SURFACE_GAME')}>{['MERCURY','VENUS','EARTH','MARS'].includes(g.planet)?'Play ground game':g.planet==='SATURN'?'Play ring course':'Play orbital game'}</button><button onClick={()=>send('FLIGHT,EXPLORE')}>Leave planet ↗</button></div><button className="tutorial-start" onClick={()=>send('FLIGHT,P1,SELECT')}>START CHALLENGE <small>P1 · PRESS JOYSTICK</small></button></footer>
  <small className="tutorial-source">{g.source}</small>
 </section>;
}
