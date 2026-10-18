import React,{useEffect,useRef,useState} from 'react';
export default function BrowserCamera({send}){
 const preview=useRef(),last=useRef(0),[status,setStatus]=useState('Separate preview stays on laptop');
 useEffect(()=>{
  const receive=e=>{if(e.origin!==location.origin||e.source!==preview.current||e.data?.type!=='odyssey-camera')return;const {player,action}=e.data;if(![0,1].includes(player)||!['JUMP','DUCK_ON','DUCK_OFF'].includes(action))return;last.current=Date.now();send(`VISION,P${player+1},${action}`);setStatus('Camera connected · shoulders tracked')};
  window.addEventListener('message',receive);
  const timer=setInterval(()=>{if(last.current&&Date.now()-last.current>1000){last.current=0;send('VISION,P1,DUCK_OFF');send('VISION,P2,DUCK_OFF');setStatus('No shoulders detected — check preview')}},500);
  return()=>{clearInterval(timer);window.removeEventListener('message',receive);preview.current?.close()};
 },[send]);
 function open(){if(preview.current&&!preview.current.closed){preview.current.focus();return}preview.current=window.open('/?camera=1','odyssey-motion-camera','popup,width=760,height=720');setStatus(preview.current?'Click Enable camera in the laptop preview':'Popup blocked — allow popups for this game')}
 return <aside className="camera-access"><button onClick={open}>Open motion camera ↗</button><small>{status}</small></aside>
}
