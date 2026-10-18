import React,{useState} from 'react';
export default function CameraStart({status}){
 const [message,setMessage]=useState(''),[busy,setBusy]=useState(false);
 const start=async()=>{setBusy(true);try{const response=await fetch('/api/vision/start',{method:'POST'});const data=await response.json();setMessage(data.detail||'Camera starting');}catch{setMessage('Camera service unavailable. Start the local Python backend.')}finally{setBusy(false)}};
 if(status?.mode==='HOSTED')return <div className="camera-start"><span>Pair USB remotes: run the laptop launcher with --cloud and enter this code when prompted. Open motion camera for browser tracking.<br/><code className="pairing-code">{status.pairing_code}</code><br/>{status.vision}</span></div>;
 return <div className="camera-start"><button onClick={start} disabled={busy}>{busy?'Opening camera…':'Open laptop camera'}</button><span>{message||status?.vision||'Camera not connected'}</span></div>;
}
