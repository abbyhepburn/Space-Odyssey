import React from 'react';
// The server's launch clock drives ascent; browser refresh cannot skip ahead.
export default function LaunchCinematic({elapsed}){
 const t=Math.max(0,Math.min(1,(elapsed-1800)/8200)),ascent=t*t*(3-2*t);
 return <div className="rocket-departure" role="img" aria-label="The rocket floats upward from Earth into space" style={{'--ascent':ascent}}>
  <div className="departure-stars"/><div className="departure-atmosphere"/><div className="departure-earth"/>
  <div className="departure-rocket" style={{transform:`translate(-50%,-50%) translateY(${-ascent*42}vh) rotate(${-6+ascent*10}deg) scale(${1-ascent*.3})`}}>
   <svg viewBox="0 0 180 470" aria-hidden="true">
    <defs>
     <linearGradient id="hull"><stop stopColor="#657e93"/><stop offset=".45" stopColor="#f2f2e6"/><stop offset=".7" stopColor="#b5c9d4"/><stop offset="1" stopColor="#3e566a"/></linearGradient>
     <linearGradient id="exhaust" x2="0" y2="1"><stop stopColor="#fffef2"/><stop offset=".25" stopColor="#97e5ff"/><stop offset="1" stopColor="#527ffc" stopOpacity="0"/></linearGradient>
    </defs>
    <path d="M65 300Q42 327 28 385L66 366ZM115 300Q138 327 152 385L114 366Z" fill="#859dad" stroke="#d0e5e9"/>
    <path d="M65 176Q65 103 90 62Q115 103 115 176L115 355Q90 367 65 355Z" fill="url(#hull)" stroke="#c8dce4"/>
    <path d="M67 175H113M65 299H115" stroke="#27475c" strokeWidth="5"/>
    <circle cx="90" cy="193" r="13" fill="#0a263b" stroke="#7694a8" strokeWidth="4"/>
    <path d="M78 188Q90 178 99 188" fill="none" stroke="#9bdfea"/>
    <text x="90" y="253" fill="#233c50" fontSize="10" textAnchor="middle" letterSpacing="2" transform="rotate(-90 90 253)">ODYSSEY</text>
    <path d="M73 355H107L111 373H69Z" fill="#223343" stroke="#8299aa"/>
    <path className="rocket-exhaust" d="M74 374Q70 421 90 468Q110 421 106 374Z" fill="url(#exhaust)"/>
   </svg>
  </div>
  <div className="departure-readout"><span>EARTH DEPARTURE</span><strong>{elapsed<1800?'IGNITION':'ASCENDING INTO SPACE'}</strong><small>ODYSSEY · TWO PILOTS ABOARD</small></div>
 </div>;
}
