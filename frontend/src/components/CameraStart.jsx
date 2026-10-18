import React,{useState} from 'react';
export default function CameraStart({status}){
 const [message,setMessage]=useState(''),[busy,setBusy]=useState(false);
 const start=async()=>{setBusy(true);try{const response=await fetch('/api/vision/start',{method:'POST'});const data=await response.json();if(!response.ok)throw new Error(data.detail||'Camera could not start');setMessage(data.detail||'Camera starting');}catch(error){setMessage(error.message||'Camera service unavailable. Start the local Python backend.')}finally{setBusy(false)}};
 return <div className="camera-start">{status?.mode==='HOSTED'?<span>Pair USB remotes: run the laptop launcher with --cloud and enter this code.<br/><code className="pairing-code">{status.pairing_code}</code></span>:<button onClick={start} disabled={busy}>{busy?'Opening camera…':'Start OpenCV on laptop'}</button>}<span>{message||status?.vision||'Camera not connected'}</span></div>;
}
