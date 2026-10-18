import {useEffect,useRef} from 'react';
import {pointerPosition,primarySelector,pendingPresses,interactiveSelector,fallbackAction} from '../lib/controllerUi';

function hitTarget(game,ui,raw){
 const {x,y}=pointerPosition(raw);
 // Only the topmost element counts: do not find buttons behind a panel.
 const top=document.elementFromPoint(innerWidth*x/100,innerHeight*y/100);
 const target=top?.closest(interactiveSelector);
 const scope=ui.controllerPanel?'.controller-panel':ui.help?'.help-layer':ui.information?'.information-panel':ui.catalog?'.planet-log':ui.discovery?'.discovery-card':['TRAVEL','GENERATING','ARRIVAL'].includes(game.phase)?'.mission-loading':null;
 return target&&(!scope||target.closest(scope))?target:null;
}
const disabled=el=>el.disabled||el.getAttribute('aria-disabled')==='true';

export default function useControllerUi({game,ui,connected,send}){
 const previous=useRef(null),latest=useRef(null);
 latest.current={game,ui};
 const modal=Boolean(ui.help||ui.catalog||ui.discovery||ui.information||ui.controllerPanel);
 useEffect(()=>{
  if(!connected){previous.current=null;return}
  const refresh=()=>send(`UI,CONTEXT,${modal?'MODAL':'GAME'}`);
  refresh();const timer=setInterval(refresh,400);
  return()=>clearInterval(timer);
 },[connected,modal,send]);
 useEffect(()=>{
  const marked=[];
  if(connected)for(let i=0;i<2;i++){
   const row=game.controllers?.[i];
   if(!row?.fresh)continue;
   const target=hitTarget(game,ui,row.raw);
   if(target&&!disabled(target)){target.setAttribute('data-controller-hover','true');marked.push(target)}
  }
  return()=>marked.forEach(el=>el.removeAttribute('data-controller-hover'));
 },[game,ui,connected]);
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
   const raw=current.game.ui_pointer_positions?.[player]||current.game.controllers?.[player]?.raw;
   const target=hitTarget(current.game,current.ui,raw);
   const panelOpen=context.help||context.catalog||context.information||context.discovery||context.controllerPanel;
   if(!panelOpen&&target&&disabled(target))continue;
   const fallback=selector?document.querySelector(selector):null;
   // An open information/control panel is a toggle: the very next remote
   // press closes it, including when the pointer still rests over a control.
   const button=panelOpen?fallback:(target||fallback);
   if(button&&!disabled(button)){
    button.click();
    // One UI transition per snapshot, so simultaneous presses cannot click
    // through a closing panel. Gameplay below still handles both players.
    break;
   }
   const action=fallbackAction(context,player);
   if(action)send(action);
  }
 },[game.ui_presses,connected,send]);
}
