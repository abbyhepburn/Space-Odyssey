import React from 'react';
export default function ConnectionStatus({connected,status}){return <div className="connections"><span className={connected?'online':'offline'}>● {connected?'LIVE LINK':'RECONNECTING'}</span><span>{status.mode} · {status.usb&&status.state_fresh?'READY':'WAITING'}</span><span>{status.gemini}</span></div>}
