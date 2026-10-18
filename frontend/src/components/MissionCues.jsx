import React from 'react';
const actions={HURDLE:'JUMP',PIT:'JUMP',GATE:'DUCK',STORM:'DUCK',RIDGE:'FLICK UP',SAMPLE:'COLLECT',GENERATOR:'SHAKE',BEACON:'PRESS',PORTAL:'ALIGN + FLICK',SLALOM:'ALIGN',ROCK:'DODGE'};
export default function MissionCues({game}) {
 if(game.mission?.game_type==='SCIENCE_QUIZ')return null;
 const lead=game.timing?.warning_lead_s??1.8;
 return <div className="lane-cues">{game.players.map((p,i)=>{
   const next=game.obstacles.find(o=>!o.passed[i]&&!o.destroyed_by?.[i]&&o.event_at-game.age<=lead&&o.event_at-game.age>=-.2);
   const remaining=next?next.event_at-game.age:0;
   const action=next?.kind==='SAMPLE'&&!next.research?'SKIP DECOY':next?.kind==='ROCK'&&game.mission.game_type==='METEOR_BREAK'?'SHAKE':actions[next?.kind];
   return <section key={i} className={`lane-cue player-${i+1} ${next?'visible':''}`}>
     {p.feedback_until>game.age?<div className="lane-feedback">{p.feedback}</div>:next?<><small>PLAYER {i+1} · {remaining>.8?'GET READY':'NOW'}</small><strong>{action}</strong><progress max={lead} value={Math.max(0,lead-remaining)}/><span>{remaining>0?`${remaining.toFixed(1)}s`:'NOW'}</span></>:<small>Watch the horizon</small>}
   </section>
 })}</div>
}
