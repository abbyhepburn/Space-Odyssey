import {useEffect,useRef} from 'react';
import {pointerPosition,primarySelector,pendingPresses} from '../lib/controllerUi';

export default function useControllerUi({game,ui,connected,send}){
 const previous=useRef(null),latest=useRef(null);
 latest.current={game,ui};
 const modal=Boolean(ui.help||ui.catalog||ui.discovery);
 useEffect(()=>{
  if(!connected){previous.current=null;return}
  const refresh=()=>send(`UI,CONTEXT,${modal?'MODAL':'GAME'}`);
  refresh();const timer=setInterval(refresh,400);
  return()=>clearInterval(timer);
 },[connected,modal,send]);
 useEffect(()=>{
  if(!connected){previous.current=null;return}
  const counters=game.ui_presses||[0,0];
  const presses=pendingPresses(previous.current,counters);
  previous.current=counters;
  // Local overlays take priority, so their close button cannot click through.
  for(const player of presses){
   const current=latest.current;
   const context={...current.ui,phase:current.game.phase};
   const selector=primarySelector(context);
   const scope=current.ui.help?'.help-layer':current.ui.catalog?'.planet-log':current.ui.discovery?'.discovery-card':null;
   const {x,y}=pointerPosition(current.game.controllers?.[player]?.raw);
   const target=document.elementsFromPoint(innerWidth*x/100,innerHeight*y/100)
    .map(el=>el.closest('button,summary,a')).find(el=>el&&!el.disabled&&(!scope||el.closest(scope)));
   const fallback=selector?document.querySelector(selector):null;
   const button=target||fallback;
   if(button&&!button.disabled)button.click();
   else if(!scope&&!['BOOT','LAUNCH','TRAVEL','GENERATING','ARRIVAL','COUNTDOWN'].includes(current.game.phase))send('FLIGHT,P1,SELECT');
   // At most one UI transition per snapshot: a second player cannot click
   // through a panel that the first player's simultaneous press just closed.
   break;
  }
 },[game.ui_presses,connected,send]);
}
