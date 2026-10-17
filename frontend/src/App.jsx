import React,{useEffect,useRef,useState} from 'react';
import useGameSocket from './hooks/useGameSocket';
import CockpitGame,{discoveries} from './components/CockpitGame';
import MovementDemo,{keyLabels} from './components/MovementDemo';
import SpaceOdysseyLaunch from './components/SpaceOdysseyLaunch';
import {pilotAxes,helmAxes} from './lib/flightControls';
import {aimedDiscovery} from './lib/discoveryTargeting';
const angle=d=>Math.atan2(Math.sin(d),Math.cos(d));
const player={x:0,y:0,yaw:0,pitch:.065,distance:0,health:100,score:0,jump:0,flick:0,duck:false,samples:0,chargers:0};
const initial={phase:'READY',age:0,roll:0,speed:0,ship:[0,0,0],health:100,team_score:0,players:[{...player},{...player}],targets:[],locked:[null,null],obstacles:[],event:'READY'};
function Hold({children,down,up,...props}){
  // Pointer capture supports a continuous hold, including touchscreens. Every
  // exit path releases the control; the server also expires stale axes.
  return <button type="button" {...props}
    onPointerDown={e=>{if(e.button!==0&&e.pointerType==='mouse')return;e.currentTarget.setPointerCapture(e.pointerId);down()}}
    onPointerUp={up} onPointerCancel={up} onLostPointerCapture={up} onBlur={up}
    onKeyDown={e=>{if((e.key===' '||e.key==='Enter')&&!e.repeat){e.preventDefault();e.stopPropagation();down()}}}
    onKeyUp={e=>{if(e.key===' '||e.key==='Enter'){e.preventDefault();e.stopPropagation();up()}}}
    />;
}
export default function App(){const {flight,connected,send}=useGameSocket();const g=(flight && Array.isArray(flight.players) && flight.players.length >= 2 && flight.players.every(p=>p && typeof p === 'object') && Array.isArray(flight.targets) && Array.isArray(flight.obstacles) && Array.isArray(flight.locked) && Array.isArray(flight.ship)) ? flight : initial;const keys=useRef(new Set());const [help,setHelp]=useState(false);const [thrustHeld,setThrustHeld]=useState(false);const [catalog,setCatalog]=useState(false);const [discovery,setDiscovery]=useState(null);const [hoveredDiscovery,setHoveredDiscovery]=useState(null);const [fullError,setFullError]=useState('');const [aspect,setAspect]=useState(innerWidth/innerHeight);const race=['MISSION','RESULTS'].includes(g.phase)&&['RING_RACE','SURFACE_RUN','CRATER_LEAP','SAMPLE_HUNT','STORM_SHELTER'].includes(g.mission?.game_type);const split=['MISSION','RESULTS'].includes(g.phase);const active=g.phase==='MISSION';const flying=['LAUNCH','NAVIGATION','TRAVEL'].includes(g.phase);const moves=g.mission?.movements||[];const debugControls=new URLSearchParams(window.location.search).get('debugControls')==='1';
const phaseRef=useRef(g.phase);phaseRef.current=g.phase;
const aimed= g.phase==='NAVIGATION' ? (hoveredDiscovery||aimedDiscovery(g.ship,g.players[0],discoveries)) : null;
const aimedRef=useRef(null);aimedRef.current=aimed;
useEffect(()=>{if(g.phase!=='NAVIGATION'){setDiscovery(null);setCatalog(false);setHoveredDiscovery(null)}},[g.phase]);
useEffect(()=>{const resize=()=>setAspect(innerWidth/innerHeight);window.addEventListener('resize',resize);return()=>window.removeEventListener('resize',resize)},[]);
useEffect(()=>{
  const down=e=>{
    if(/INPUT|TEXTAREA|SELECT/.test(e.target?.tagName||'')||e.target?.isContentEditable||e.ctrlKey||e.metaKey||e.altKey)return;
    const k=e.code==='KeyF'?'f':e.key.toLowerCase();
    if([' ','arrowleft','arrowright','arrowup','arrowdown'].includes(k))e.preventDefault();
    if(phaseRef.current==='READY')return;
    keys.current.add(k);
    if(k==='f')setThrustHeld(true);
    if(e.repeat)return;
    const actions={' ':['P1','JUMP'],c:['P1','DUCK_ON'],q:['P1','SHAKE'],r:['P1','UPWARD_FLICK'],p:['P2','UPWARD_FLICK'],i:['P2','JUMP'],k:['P2','DUCK_ON'],u:['P2','SHAKE'],enter:['P1','SELECT'],e:['P1','SELECT'],o:['P2','SELECT']};
    if((k==='e'||k==='enter')&&phaseRef.current==='NAVIGATION'&&aimedRef.current){setDiscovery(aimedRef.current);setCatalog(false)}
    else if(actions[k])send(`FLIGHT,${actions[k].join(',')}`);
    if(k==='h')setHelp(v=>!v);
  };
  const up=e=>{
    const k=e.code==='KeyF'?'f':e.key.toLowerCase();keys.current.delete(k);
    if(k==='f')setThrustHeld(false);
    if(k==='c')send('FLIGHT,P1,DUCK_OFF');
    if(k==='k')send('FLIGHT,P2,DUCK_OFF');
  };
  const clear=()=>{
    keys.current.clear();setThrustHeld(false);
    for(const p of ['P1','P2']){
      send(`FLIGHT,${p},AXIS,0,0`);send(`FLIGHT,${p},DUCK_OFF`);
    }
  };
  // The same normalized analog axes can be sent by the future hardware bridge:
  // FLIGHT,P1,AXIS,<forward/backward>,<left/right turn>.
  // FLIGHT,P2,AXIS,0,<left/right roll correction>.
  // F/S emulate P1 forward/backward; A/D P1 steering; J/L P2 leveling.
  // Refresh both players' axes to keep the 400-ms server dead-man timer alive.
  const timer=setInterval(()=>{
    const k=keys.current;
    const [p1x,p1y]=pilotAxes(k,phaseRef.current);
    const [p2x,p2y]=helmAxes(k,phaseRef.current);
    send(`FLIGHT,P1,AXIS,${p1x},${p1y}`);
    send(`FLIGHT,P2,AXIS,${p2x},${p2y}`);
  },50);
  const hidden=()=>{if(document.hidden)clear()};
  // Capture before a focused menu/button can consume key events.
  window.addEventListener('keydown',down,true);window.addEventListener('keyup',up,true);
  window.addEventListener('blur',clear);document.addEventListener('visibilitychange',hidden);
  return()=>{clearInterval(timer);window.removeEventListener('keydown',down,true);window.removeEventListener('keyup',up,true);window.removeEventListener('blur',clear);document.removeEventListener('visibilitychange',hidden);clear()};
},[send]);
useEffect(()=>{if(!connected){keys.current.clear();setThrustHeld(false)}},[connected]);
const full=async()=>{try{await document.documentElement.requestFullscreen()}catch{setFullError('Use your browser’s fullscreen command.')}};const hold=(k,label)=> <Hold
  className={k==='f'&&thrustHeld?'thrust-pressed':undefined}
  aria-label={k==='f'?'Hold to thrust forward':label}
  aria-pressed={k==='f'?thrustHeld:undefined}
  down={()=>{keys.current.add(k);if(k==='f')setThrustHeld(true)}}
  up={()=>{keys.current.delete(k);if(k==='f')setThrustHeld(false)}}
>{label}</Hold>;
const nearest=g.targets.length?g.targets.reduce((a,b)=>Math.abs(angle(a.yaw-g.players[0].yaw))<Math.abs(angle(b.yaw-g.players[0].yaw))?a:b):null;
const keyFor=(move,p)=>keyLabels[move]?.[p]||'';
const ground=['SURFACE_RUN','CRATER_LEAP','SAMPLE_HUNT','STORM_SHELTER'].includes(g.mission?.game_type);
const scienceMode=['SCIENCE_QUIZ','SAMPLE_HUNT','STORM_SHELTER','RELAY_REPAIR','BEACON_RELAY'].includes(g.mission?.game_type);
const quizMode=g.mission?.game_type==='SCIENCE_QUIZ';
const modeSync={SURFACE_RUN:'JUMP',CRATER_LEAP:'FLICK',SAMPLE_HUNT:'PRESS',STORM_SHELTER:'SHAKE',RING_RACE:'JUMP',BEACON_RELAY:'PRESS',ASTEROID_DODGE:'SHAKE',METEOR_BREAK:'SHAKE',RELAY_REPAIR:'SHAKE',GRAVITY_SLING:'FLICK'}[g.mission?.game_type];
const syncText={JUMP:'jump together',FLICK:'flick up together',PRESS:'press together',DUCK:'duck together',SHAKE:'shake together'}[modeSync];
const remoteControls={STEER:'Move each joystick left / right',TILT:'Tilt each remote left / right',JUMP:'Jump in front of the camera',DUCK:'Duck in front of the camera',PRESS:'Press your joystick button',SHAKE:'Shake your remote',FLICK:'Flick your remote upward'};
const sendAction=(p,m)=>send(`FLIGHT,${p},${m==='FLICK'?'UPWARD_FLICK':m}`);

if(g.phase==='READY')return <><SpaceOdysseyLaunch
  onLaunchComplete={()=>{setHelp(false);setCatalog(false);send('FLIGHT,LAUNCH')}}
  onOpenControls={()=>setHelp(true)} onOpenDiscoveries={()=>setCatalog(true)} />
  {!connected&&<div className="connection-banner">Waiting for Python backend on port 8000…</div>}
  {help&&<div className="help-layer"><section className="help-card"><button className="close" onClick={()=>setHelp(false)}>×</button><h2>Flight controls</h2><p><b>Player 1 · Pilot:</b> Push joystick forward or pull backward to fly. Move it left/right to turn. Press the joystick button to select a destination.</p><p><b>Player 2 · Stabilizer:</b> Tilt your remote left/right to keep the spacecraft upright.</p><p><b>Planet challenges:</b> Both players use their remotes to tilt, shake, flick upward and press the joystick button. Jumping and ducking will be detected by the laptop camera.</p><button className="big-button" onClick={()=>setHelp(false)}>Back to launch</button></section></div>}
  {catalog&&<aside className="catalog-panel"><div className="catalog-head"><strong>SPACE ENCYCLOPEDIA</strong><button onClick={()=>setCatalog(false)}>×</button></div><p>Choose a real space object to explore.</p><div className="catalog-items">{discoveries.map(d=><button key={d.name} onClick={()=>setDiscovery(d)}><span>{d.name}</span><small>{d.category} · {d.zone==='DEEP_SKY'?'Deep sky':d.zone==='EARTH_L2'?'Sun–Earth L2':d.zone==='SOLAR_ORBIT'?'Solar orbit':d.zone.replaceAll('_',' ')}</small></button>)}</div>{discovery&&<div className="preflight-discovery"><b>{discovery.name}</b><p><strong>LOCATION:</strong> {discovery.location}</p><p>{discovery.fact}</p><a target="_blank" rel="noreferrer" href={discovery.url}>Learn more ↗</a></div>}</aside>}
</>;

return <main className={`game revised ${race?'race-mode':''}`}><div className={`game-views ${split?'split':''}`}>{(split?[0,1]:[0]).map(i=><div className="view" key={i}><CockpitGame game={g} index={i} onDiscover={setDiscovery} onHover={setHoveredDiscovery}/>{split&&<span className={`player-badge player-${i+1}`}>PLAYER {i+1}</span>}</div>)}</div><div className="glass-noise"/>{g.damage_flash>0&&<div className="impact-flash"/>}
<header className="simple-header"><strong>◈ ODYSSEY</strong><div className="header-score player-scoreboard"><span>P1 <b>{g.players[0]?.score||0}</b></span><span>P2 <b>{g.players[1]?.score||0}</b></span></div><div><button onClick={()=>setHelp(true)}>Controls</button><button onClick={full} aria-label="Fullscreen">⛶</button><button disabled={!connected} onClick={()=>send('FLIGHT,RESET')} aria-label="Restart demo">↻</button></div></header>
{!connected&&<div className="connection-banner">Connecting to the game…</div>}
{g.phase==='READY'&&<section className="start-card"><span className="section-label">TWO PLAYERS · ONE GALAXY · HEAD TO HEAD</span><h1>Let’s leave Earth.</h1><div className="crew-lessons"><div><MovementDemo action="THRUST"/><b>PLAYER 1 · PILOT</b><p>Joystick ↑/↓ · Forward / reverse<br/>Joystick ←/→ · Turn<br/>Joystick button · Select</p></div><div><MovementDemo action="TILT"/><b>PLAYER 2 · HELM</b><p>Tilt remote left / right<br/>Keep the ship level</p></div></div><button className="big-button" disabled={!connected||!flight} onClick={()=>send('FLIGHT,LAUNCH')}>Launch</button><small>Computer simulation available until the remotes are connected</small></section>}
{g.phase==='LAUNCH'&&<div className="travel-title"><span>EARTH DEPARTURE</span><h1>Lift off.</h1><progress max="5" value={g.age}/></div>}
{g.phase==='NAVIGATION'&&<><button className="catalog-open" onClick={()=>setCatalog(v=>!v)}>✦ DISCOVERIES · {discoveries.length} OBJECTS</button><div className="nav-aim"><span>＋</span><b>{aimed?.name||g.locked[0]||nearest?.planet}</b><small>{aimed?'INSPECT SPACE OBJECT':g.locked[0]?'IN RANGE':'MOVE CLOSER TO SELECT'}</small></div><div className={`nav-status ${Math.abs(g.throttle_input??0)>0?'thrust-engaged':''}`}>
  <span>{g.thrust_blocked?'PROXIMITY SAFETY · TURN AWAY':(g.throttle_input??0)>0?'FORWARD THRUST':(g.throttle_input??0)<0?'REVERSE THRUST':Math.abs(g.speed)>.2?'BRAKING · JOYSTICK CENTERED':'P1 · MOVE JOYSTICK TO FLY'}</span>
  <strong data-testid="flight-speed">{Math.round(g.speed)}<small> demo units/s</small></strong>
  <div className={`thrust-meter ${(g.throttle_input??0)<0?'reverse':''}`}><i style={{width:`${Math.round(Math.abs(g.throttle_input??g.thrust_input??0)*100)}%`}}/></div>
  <small className="thrust-guide">P1 · Push / pull to move · Left / right to turn</small>
</div><div className="attitude-gauge"><span>P2 · TILT REMOTE TO LEVEL</span><div><i style={{transform:`rotate(${-(g.roll||0)*180/Math.PI}deg)`}}/><b>− ◇ −</b></div></div><div className="destination-tags" style={{transform:`rotate(${(g.roll||0)*180/Math.PI}deg)`}}>{g.targets.map(t=>{const d=angle(t.yaw-g.players[0].yaw);return Math.abs(d)<.85&&<span key={t.planet} style={{left:`${50+Math.tan(d)*100/(2*Math.tan(Math.PI/5)*aspect)}%`,top:`${50-Math.tan(t.pitch-g.players[0].pitch)*100/(2*Math.tan(Math.PI/5))}%`}}>{t.planet}</span>})}</div><div className="nav-prompt">{aimed?<button className="big-button" onClick={()=>{setDiscovery(aimed);setCatalog(false)}}>Inspect {aimed.name} <span className="remote-tag">P1 · PRESS BUTTON</span></button>:<button className="big-button" disabled={!g.locked[0]} onClick={()=>send('FLIGHT,P1,SELECT')}>Visit {g.locked[0]||'planet'} <span className="remote-tag">P1 · PRESS BUTTON</span></button>}</div></>}
{['TRAVEL','GENERATING'].includes(g.phase)&&<div className="travel-title"><span>{g.planet}</span><h1>{g.phase==='TRAVEL'?'On our way.':'A new adventure.'}</h1><div className="loading-orbit"/><p>{g.mission?'Mission received':'Gemini is creating your game…'}</p></div>}
{g.phase==='BRIEFING'&&g.mission&&<section className="game-briefing"><div className="brief-title"><span>{g.planet} · {scienceMode?'SCIENCE CHALLENGE':'ACTION CHALLENGE'} · {String(g.source||'').startsWith('GEMINI')?'GEMINI CREATED':'LOCAL'}</span><h1>{g.mission.name}</h1><p>{g.mission.briefing}</p><div className="planet-lesson"><span>✦ DID YOU KNOW?</span><p>{g.education?.fact||'Explore this world to learn what makes it unique.'}</p>{g.education?.why&&<small>{g.education.why}</small>}{g.education?.url&&<a href={g.education.url} target="_blank" rel="noreferrer">NASA planet facts ↗</a>}</div></div><div className="lesson-layout"><div className="lesson-preview"><div className="lesson-demo-row">{moves.map(m=><MovementDemo key={m.control} action={m.control}/>)}</div><span className="watch-label">WATCH THE MOVES · THEN RACE EACH OTHER</span></div><div className="lesson-controls"><h2>How to play</h2>{moves.map(m=><div className="control-lesson" key={m.control}><strong>{m.control==='STEER'?'Move left / right':m.control==='JUMP'?'Jump':m.control==='DUCK'?'Duck':m.control==='PRESS'?'Click joystick':m.control==='FLICK'?'Flick remote upward':m.control==='TILT'?'Tilt remote left / right':'Shake'}</strong><p>{m.instruction}</p><div className="remote-action-label">{remoteControls[m.control]}</div></div>)}{g.mission.sync_boost&&<div className="sync-lesson"><span>✦ Sync for bonus</span></div>}</div></div><div className="brief-actions"><button onClick={()=>send('FLIGHT,REGENERATE')}>Try a different game ↻</button>{['MERCURY','VENUS','EARTH','MARS'].includes(g.planet)&&<button onClick={()=>send('FLIGHT,SURFACE_GAME')}>Play a ground game ↻</button>}<button className="big-button" onClick={()=>send('FLIGHT,P1,SELECT')}>Start 15-second challenge</button></div><small className="source-note">{g.source}</small></section>}
{active&&<>{ground&&<div className="surface-location"><strong>⬡ {g.planet} SURFACE</strong><span>{g.mission.game_type==='SAMPLE_HUNT'?'SCIENTIFIC RECOVERY':g.mission.game_type==='STORM_SHELTER'?'STORM SURVIVAL':g.mission.game_type==='CRATER_LEAP'?'CRATER EXPEDITION':'OUTPOST COURSE'}</span></div>}<div className="mission-top"><span>{scienceMode?'✦ SCIENCE · ':'⚡ CHALLENGE · '}{g.mission.name}</span><b>{Math.max(0,Math.ceil(g.mission.time_limit_s-g.age))}s</b><div className="team-health"><i style={{width:`${g.players[0]?.health||0}%`}}/><i style={{width:`${g.players[1]?.health||0}%`}}/></div></div><div className="game-feedback" key={g.event_id}>{g.event}</div>{g.boost>0&&<div className="boost-effect"><b>{g.sync_effect||'SYNC! ✦ BOTH SCORE'}</b></div>}{ground&&<div className="surface-objectives">{g.players.map((p,i)=><div key={i}><strong>PLAYER {i+1} · {p.score||0} PTS</strong><span>{g.mission.game_type==='SAMPLE_HUNT'?`SAMPLES ${p.samples||0}/3`:g.mission.game_type==='STORM_SHELTER'?`POWER ${p.chargers||0}/2`:g.mission.game_type==='CRATER_LEAP'?'JUMP + FLICK':'JUMP + DUCK'}</span></div>)}</div>}{quizMode&&<div className="science-quiz-overlay">{[0,1].map(i=><section key={i} className={`science-quiz-player p${i+1}`}><div className="quiz-overline">PLAYER {i+1} · PLANET SCIENCE · {g.planet}</div>{g.quiz ? <><h2>{g.quiz.question}</h2><div className="quiz-answers">{g.quiz.choices.map((text,j)=><div key={j} className={`quiz-answer ${g.players[i]?.selection===j?'selected':''} ${g.quiz.answered?.[i]?'answered':''}`}><b>{'ABC'[j]}</b><span>{text}</span></div>)}</div><div className="quiz-foot">{g.quiz.answered?.[i]?'ANSWER LOCKED IN · WAIT FOR THE NEXT QUESTION':'Tilt left / center / right to choose · Press joystick button to answer'}</div></> : <><h2>Preparing next discovery...</h2><p>Watch for the next question</p></>}</section>)}</div>}{!race&&!quizMode&&[0,1].map(i=><div key={i} className="target-circle" style={{left:`${25+i*50}%`}}>＋<span>{g.mission.game_type==='ORBIT_SLALOM'?'DODGE':g.mission.game_type==='BEACON_RELAY'?'COLLECT':g.mission.game_type==='RELAY_REPAIR'?'REPAIR':g.mission.game_type==='GRAVITY_SLING'?'FLICK UP':'HIT'}</span></div>)}<div className="mission-motion-hints">{moves.map(m=><div key={m.control}><MovementDemo action={m.control} small/><span>{remoteControls[m.control]}</span></div>)}{g.mission.sync_boost&&<div className="mission-sync-hint">✦ Sync for bonus</div>}</div>
{debugControls&&<div className="simple-actions debug-actions">{moves.map(m=><div key={m.control}><MovementDemo action={m.control} small/><div>{['STEER','TILT'].includes(m.control)?<><span>P1</span>{hold('a','A ←')}{hold('d','D →')}<span>P2</span>{hold('arrowleft','←')}{hold('arrowright','→')}</>:['P1','P2'].map((p,i)=><React.Fragment key={p}><span>{p}</span>{m.control==='DUCK'?<Hold down={()=>sendAction(p,'DUCK_ON')} up={()=>sendAction(p,'DUCK_OFF')}>{keyFor(m.control,i)}</Hold>:<button onClick={()=>sendAction(p,m.control)}>{keyFor(m.control,i)}</button>}</React.Fragment>)}</div></div>)}{g.mission.sync_boost&&<div className="sync-action"><b>✦ Sync for bonus</b><span>{g.boost_cooldown>0?`Ready in ${Math.ceil(g.boost_cooldown)}s`:syncText}</span><div>{['P1','P2'].map((p,i)=><button key={p} onClick={()=>sendAction(p,modeSync)}>{p} · {keyFor(modeSync,i)}</button>)}</div></div>}</div>}</>}
{debugControls&&flying&&<div className="flight-buttons"><div><span>P1 · PILOT · TEST INPUTS</span>{hold('f','F · Forward')}{hold('s','S · Backward')}{hold('a','A · Turn left')}{hold('d','D · Turn right')}</div><div><span>P2 · LEVEL · TEST INPUTS</span>{hold('j','J · Roll left')}{hold('l','L · Roll right')}</div></div>}{g.phase==='RESULTS'&&<section className="results-card"><span>15-SECOND CHALLENGE · {g.planet}</span><h1>{g.winner==='P1'?'Player 1 wins!':g.winner==='P2'?'Player 2 wins!':'It’s a tie!'}</h1><div className="versus-result"><div><span>PLAYER 1</span><strong>{g.players[0]?.score||0}</strong><small>POINTS</small></div><b>VS</b><div><span>PLAYER 2</span><strong>{g.players[1]?.score||0}</strong><small>POINTS</small></div></div><div><button onClick={()=>send('FLIGHT,REGENERATE')}>New game here ↻</button>{['MERCURY','VENUS','EARTH','MARS'].includes(g.planet)&&<button onClick={()=>send('FLIGHT,SURFACE_GAME')}>Ground game ↻</button>}<button className="big-button" onClick={()=>send('FLIGHT,EXPLORE')}>Keep exploring ↗</button></div></section>}
{catalog&&g.phase==='NAVIGATION'&&<aside className="catalog-panel"><div className="catalog-head"><strong>SPACE ENCYCLOPEDIA</strong><button onClick={()=>setCatalog(false)} aria-label="Close discoveries">×</button></div><p>Select a real object to learn about space.</p><div className="catalog-items">{discoveries.map(d=><button key={d.name} onClick={()=>{setDiscovery(d);setCatalog(false)}}><span>{d.name}</span><small>{d.category} · {d.zone==='DEEP_SKY'?'Deep sky':d.zone==='EARTH_L2'?'Sun–Earth L2':d.zone==='SOLAR_ORBIT'?'Solar orbit':d.zone.replaceAll('_',' ')}</small></button>)}</div><small>Schematic positions: correct planetary neighborhoods; not-to-scale or real-time.</small></aside>}{discovery&&g.phase==='NAVIGATION'&&<aside className="discovery-card"><button className="close" onClick={()=>setDiscovery(null)} aria-label="Close discovery">×</button><span>SPACE DISCOVERY · {discovery.category?.toUpperCase()}</span><h2>{discovery.name}</h2><div className="discovery-location"><strong>LOCATION / ORBIT</strong><p>{discovery.location}</p></div><p>{discovery.fact}</p>{discovery.details?.length>0&&<ul>{discovery.details.map((fact,i)=><li key={i}>{fact}</li>)}</ul>}<a href={discovery.url} target="_blank" rel="noreferrer">Learn more ↗</a><small>Schematic map — shows correct parent body or sky region, not live satellite locations or actual distances.</small></aside>}{help&&<div className="help-layer"><section className="help-card"><button className="close" onClick={()=>setHelp(false)} aria-label="Close controls">×</button><h1>Remote controls</h1><div className="crew-lessons"><div><MovementDemo action="THRUST"/><h2>Player 1 · Pilot</h2><p>Joystick forward / backward · Fly and reverse<br/>Joystick left / right · Turn<br/>Joystick button · Select destination</p></div><div><MovementDemo action="TILT"/><h2>Player 2 · Stabilizer</h2><p>Tilt remote left / right to counter ship roll and keep the spacecraft level.</p></div></div><p>During minigames, both players use the indicated remote movements: tilt, shake, button press or upward flick. Jump and duck in view of the laptop camera. ✦ Sync for bonus when the mission allows it.</p><small>{fullError||'Gemini is loaded on the backend. Your key is never sent to the browser.'}</small><button className="big-button" onClick={()=>setHelp(false)}>Back to game</button></section></div>}
</main>}
