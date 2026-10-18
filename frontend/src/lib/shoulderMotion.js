// No calibration screen: first visible shoulders establish a neutral reference.
export class ShoulderMotion {
 constructor(){this.reset()}
 reset(){this.base=null;this.y=null;this.duck=false;this.lastJump=-Infinity;this.downAt=null;this.lastSeen=-Infinity}
 update(y,width,now){
  if(!Number.isFinite(y)||!Number.isFinite(width))return [];
  if(now-this.lastSeen>700)this.reset();this.lastSeen=now;
  const scale=Math.max(.10,Math.min(.4,width));
  this.y=this.y==null?y:this.y*.4+y*.6;
  if(this.base==null){this.base=this.y;return []}
  const delta=(this.y-this.base)/scale,events=[];
  if(delta>.38){this.downAt??=now;if(!this.duck&&now-this.downAt>120){this.duck=true;events.push('DUCK_ON')}}else this.downAt=null;
  if(this.duck&&delta<.14){this.duck=false;this.lastJump=now;events.push('DUCK_OFF')}
  if(!this.duck&&delta<-.28&&now-this.lastJump>850){events.push('JUMP');this.lastJump=now}
  if(Math.abs(delta)<.10)this.base=this.base*.99+this.y*.01;
  return events;
 }
 lost(now){if(now-this.lastSeen<600)return [];const held=this.duck;this.reset();return held?['DUCK_OFF']:[]}
}
