// Deterministic, launch-only engine vibration. The zero-ended envelope prevents
// a camera jump at ignition or handover to idle navigation. No rotation is added.
export function launchVibration(age,duration=5){
 if(!Number.isFinite(age)||age<=0||age>=duration)return [0,0,0];
 const t=age/duration,envelope=Math.sin(Math.PI*t)**2*(1-.45*t);
 return [Math.sin(age*67)*.004*envelope,
         (Math.sin(age*79)*.009+Math.sin(age*43)*.003)*envelope,0];
}
