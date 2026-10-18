import {useEffect,useRef,useCallback} from 'react';
export default function useBrowserCamera(send){
 const preview=useRef(null),last=useRef(0);
 useEffect(()=>{
  const release=()=>{for(const player of ['P1','P2'])send(`VISION,${player},DUCK_OFF`)};
  const receive=e=>{
   if(e.origin!==location.origin||e.source!==preview.current||e.data?.type!=='odyssey-camera')return;
   const {player,action}=e.data;
   if(![0,1].includes(player)||!['JUMP','DUCK_ON','DUCK_OFF'].includes(action))return;
   last.current=Date.now();send(`VISION,P${player+1},${action}`);
  };
  const timer=setInterval(()=>{if(last.current&&Date.now()-last.current>1000){last.current=0;release()}},400);
  window.addEventListener('message',receive);
  return()=>{clearInterval(timer);window.removeEventListener('message',receive);release();preview.current?.close()};
 },[send]);
 return useCallback(()=>{
  if(preview.current&&!preview.current.closed){preview.current.focus();return}
  preview.current=window.open('/?camera=1','odyssey-motion-camera','popup,width=760,height=720');
  return Boolean(preview.current);
 },[]);
}
