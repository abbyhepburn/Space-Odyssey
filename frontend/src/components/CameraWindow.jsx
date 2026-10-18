import React,{useEffect,useRef,useState} from 'react';
import {ShoulderMotion} from '../lib/shoulderMotion';
export default function CameraWindow(){
 const video=useRef(),cleanup=useRef(()=>{}),running=useRef(false);
 const [message,setMessage]=useState('Keep this window on your laptop. P1 stands on the left of the mirrored preview; P2 on the right.'),[labels,setLabels]=useState(['Not visible','Not visible']),[busy,setBusy]=useState(false);
 const send=(player,action)=>window.opener?.postMessage({type:'odyssey-camera',player,action},location.origin);
 const stop=()=>{cleanup.current();setBusy(false);setMessage('Camera stopped')};
 useEffect(()=>{const close=()=>cleanup.current();window.addEventListener('pagehide',close);return()=>{close();window.removeEventListener('pagehide',close)}},[]);
 async function start(){
  if(running.current)return;running.current=true;setBusy(true);let stream,pose,timer,alive=true;
  cleanup.current=()=>{alive=false;clearTimeout(timer);stream?.getTracks().forEach(t=>t.stop());pose?.close();running.current=false;for(let i=0;i<2;i++)send(i,'DUCK_OFF')};
  try{
   setMessage('Allow camera access. Loading shoulder tracking…');
   if(!navigator.mediaDevices?.getUserMedia)throw new DOMException('This browser cannot access the camera','NotSupportedError');
   stream=await navigator.mediaDevices.getUserMedia({video:{width:640,height:480},audio:false});
   if(!alive){stream.getTracks().forEach(t=>t.stop());return}
   video.current.srcObject=stream;await video.current.play();
   const url='https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.21/vision_bundle.mjs';
   const {FilesetResolver,PoseLandmarker}=await import(/* @vite-ignore */ url);
   const files=await FilesetResolver.forVisionTasks('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.21/wasm');
   pose=await PoseLandmarker.createFromOptions(files,{baseOptions:{modelAssetPath:'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task'},runningMode:'VIDEO',numPoses:2,minPoseDetectionConfidence:.5,minTrackingConfidence:.5});
   if(!alive){pose.close();return}
   const tracks=[new ShoulderMotion(),new ShoulderMotion()];let last=-1;
   setMessage('Tracking shoulders — jump up or duck down. Stay in your half of the preview. No calibration needed.');
   function tick(){
    if(!alive)return;
    try{
     const now=performance.now(),seen=[false,false],next=['Not visible','Not visible'];
     if(video.current.currentTime!==last){
      last=video.current.currentTime;
      const result=pose.detectForVideo(video.current,now);
      for(const points of result.landmarks){
       const a=points[11],b=points[12];if(Math.min(a.visibility??1,b.visibility??1)<.5)continue;
       const i=(a.x+b.x)/2>.5?0:1;if(seen[i])continue;seen[i]=true;
       const events=tracks[i].update((a.y+b.y)/2,Math.abs(a.x-b.x),now);
       for(const action of events)send(i,action);
       next[i]=tracks[i].duck?'DUCK':now-tracks[i].lastJump<500?'JUMP':'Shoulders tracked';
       send(i,tracks[i].duck?'DUCK_ON':'DUCK_OFF');
      }
      for(let i=0;i<2;i++)if(!seen[i])for(const action of tracks[i].lost(now))send(i,action);
      setLabels(next);
     }
     timer=setTimeout(tick,66);
    }catch(error){cleanup.current();setBusy(false);setMessage(`Tracking stopped: ${error.message}. Retry Enable camera.`)}
   }tick();
  }catch(error){cleanup.current();setBusy(false);setMessage(error.name==='NotSupportedError'||/not supported/i.test(error.message)?'This browser does not support the camera or pose runtime. Open spaceodyssey.work in regular Google Chrome on your laptop (outside the in-app browser), then choose Open motion camera. You can also use the Python camera launcher.':error.name==='NotAllowedError'?'Camera permission denied. Allow camera access for this site in your browser settings, then retry.':`Camera could not open (${error.name}): ${error.message}. Close other camera apps and retry.`)}
 }
 return <main className="camera-preview"><h1>Laptop motion camera</h1><p>{message}</p><button onClick={start} disabled={busy}>Enable camera</button><button onClick={stop}>Stop camera</button><video ref={video} muted playsInline/><div className="camera-players">{labels.map((s,i)=><span key={i}>P{i+1} · {s}</span>)}</div><p>Move only the game window to the HDMI display. Video stays on this laptop; only jump and duck events go to your game. USB joysticks still need the laptop launcher.</p></main>
}
