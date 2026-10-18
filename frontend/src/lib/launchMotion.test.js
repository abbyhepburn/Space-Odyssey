import test from 'node:test';
import assert from 'node:assert/strict';
import {launchVibration} from './launchMotion.js';
test('engine vibration starts and stops at zero and never continues in idle flight',()=>{
 for(const age of [-1,0,5,8,NaN])assert.deepEqual(launchVibration(age),[0,0,0]);
});
test('launch vibration stays subtle and deterministic',()=>{
 for(let age=.01;age<5;age+=.01){
  const [x,y,z]=launchVibration(age);
  assert.ok(Math.abs(x)<=.004&&Math.abs(y)<=.012&&z===0);
 }
 assert.notDeepEqual(launchVibration(2),[0,0,0]);
});
