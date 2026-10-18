import test from 'node:test';
import assert from 'node:assert/strict';
import {ShoulderMotion} from './shoulderMotion.js';
test('shoulders jump and duck without a calibration screen',()=>{
 const m=new ShoulderMotion();m.update(.5,.2,0);
 assert.deepEqual(m.update(.35,.2,100),['JUMP']);
 m.update(.5,.2,1000);m.update(.5,.2,1100);
 m.update(.65,.2,1200);assert.deepEqual(m.update(.65,.2,1400),['DUCK_ON']);
 m.update(.5,.2,1500);assert.deepEqual(m.update(.5,.2,1600),['DUCK_OFF']);
 assert.deepEqual(m.update(.4,.2,1700),[]);
});
test('lost tracking releases duck and reacquisition starts fresh',()=>{
 const m=new ShoulderMotion();m.update(.5,.2,0);m.update(.7,.2,100);m.update(.7,.2,300);
 assert.deepEqual(m.lost(1000),['DUCK_OFF']);assert.deepEqual(m.update(.2,.2,1100),[]);
});
test('small shoulder jitter does not generate actions',()=>{
 const m=new ShoulderMotion();for(let i=0;i<60;i++)assert.deepEqual(m.update(.5+Math.sin(i)*.005,.2,i*40),[]);
});
