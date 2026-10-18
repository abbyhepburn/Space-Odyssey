import React from 'react';
import CameraStart from './CameraStart';
import {pointerPosition} from '../lib/controllerUi';
const number=v=>Number(v||0).toFixed(2);
export default function ControllerOverlay({game,status,connected}){
 const rows=game.controllers||[{},{}];
 return <>{rows.map((r,i)=>{const [forward=0,steer=0]=r.raw||[];return <div key={i} className={`screen-stick p${i+1} ${r.fresh?"":"offline"}`} style={{left:`${pointerPosition(r.raw).x}%`,top:`${pointerPosition(r.raw).y}%`}}><b>⌖</b><span>P{i+1}{r.fresh?"":" · connect USB"}</span></div>})}<aside className="controller-hud" aria-label="Live controller cursors">
  <div className="cursor-row">{rows.map((r,i)=>{const [forward=0,steer=0]=r.raw||[];return <div className={`cursor-player ${r.fresh?'live':''}`} key={i}><div className="joystick-pad" aria-label={`Player ${i+1} joystick X ${number(steer)}, Y ${number(forward)}`}><i style={{left:`${50+steer*38}%`,top:`${50-forward*38}%`}}/></div><span><b>P{i+1}</b><small>{r.fresh?'LIVE':r.packets?'STALE':'NO DATA'}</small></span></div>})}</div>
  <details className="mpu-data"><summary>MPU sensor data</summary>{rows.map((r,i)=><section key={i}><b>P{i+1} · {r.mpu?(r.mpu.fresh?(r.mpu.ok?'IMU responding':'IMU READ FAILED'):'STALE'):'Awaiting telemetry firmware'}</b><p>Accel m/s²: {r.mpu?.accel?.map(number).join(' / ')||'—'}</p><p>Gyro rad/s: {r.mpu?.gyro?.map(number).join(' / ')||'—'}</p><p>Last action: {r.last_action||'—'}</p></section>)}</details>
  <details><summary>Controller setup</summary><div className="controller-details">
   <p>Game {connected?'connected':'offline'} · {status?.mode==='SIMULATOR'?'Simulated USB':status?.usb?'USB connected':'USB disconnected'} · {game.phase}</p>
   <div className="controller-cards">{rows.map((r,i)=><section className="controller-card" key={i}><b>P{i+1}</b><p>X {number(r.raw?.[1])} · Y {number(r.raw?.[0])}</p><p>Tilt {r.raw?.[2]==null?'—':number(r.raw[2])}</p><p>{r.age_ms==null?'No packets':`${r.age_ms} ms · #${r.packets}`}</p><p>Using {r.source||'NONE'}</p><p>Game {r.effective?.map(number).join(', ')||'0, 0'}</p><p className="controller-action">{r.action_age_ms<1500?r.last_action:'—'}</p><small>{game.phase==='NAVIGATION'?(i===0?'Stick ↑: forward · ↓: reverse':'Tilt: ship roll'):game.mission?.movements?.map(m=>m.control).join(' + ')||'P1 button: select'}</small></section>)}</div>
   <p>During missions, tilt up to jump and push forward to duck. Cursors show raw stick readings; stale input stops after 400 ms.</p>
   <CameraStart status={status}/>
  </div></details>
 </aside></>;
}
