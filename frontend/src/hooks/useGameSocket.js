import {useCallback,useEffect,useRef,useState} from 'react';
import {initialState} from '../lib/protocol';
export default function useGameSocket(){
 const [data,setData]=useState({state:initialState,status:{mode:'CONNECTING'},mission:null}),[connected,setConnected]=useState(false);const socket=useRef(null);
 useEffect(()=>{let cancelled=false,timer,attempt=0;function connect(){if(cancelled)return;const ws=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/ws/game`);socket.current=ws;ws.onopen=()=>{attempt=0;setConnected(true)};ws.onmessage=e=>{try{const d=JSON.parse(e.data);if(d.type==='snapshot')setData(d)}catch{}};ws.onclose=()=>{setConnected(false);if(!cancelled)timer=setTimeout(connect,Math.min(5000,500*2**attempt++))};ws.onerror=()=>ws.close()}connect();return()=>{cancelled=true;clearTimeout(timer);socket.current?.close()}},[]);
 const send=useCallback(command=>{if(socket.current?.readyState===WebSocket.OPEN)socket.current.send(JSON.stringify({command}))},[]);return {...data,connected,send};
}
