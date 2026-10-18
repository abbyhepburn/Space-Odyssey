import test from 'node:test';
import assert from 'node:assert/strict';
import {pointerPosition,primarySelector,pendingPresses} from './controllerUi.js';
test('each controller reaches full viewport and malformed input stays bounded',()=>{
 assert.deepEqual(pointerPosition([0,0]),{x:50,y:50});
 assert.deepEqual(pointerPosition([1,-1]),{x:1,y:1});
 assert.deepEqual(pointerPosition([-1,1]),{x:99,y:99});
 assert.deepEqual(pointerPosition([NaN,Infinity]),{x:99,y:50});
});
test('information and help close before launch, tutorial or winner actions',()=>{
 assert.equal(primarySelector({help:true,phase:'RESULTS'}),'.help-layer .close');
 assert.equal(primarySelector({discovery:{},phase:'NAVIGATION'}),'.discovery-card .close');
 assert.equal(primarySelector({catalog:true}),'.planet-log .catalog-head button');
 assert.equal(primarySelector({phase:'RESULTS'}),'.results-card .big-button');
 assert.equal(primarySelector({phase:'BRIEFING'}),'.tutorial-start');
 assert.equal(primarySelector({phase:'MISSION'}),null);
});
test('snapshot counters catch presses from both players without replay on reconnect',()=>{
 assert.deepEqual(pendingPresses(null,[5,10]),[]);
 assert.deepEqual(pendingPresses([5,10],[6,11]),[0,1]);
 assert.deepEqual(pendingPresses([6,11],[6,11]),[]);
 assert.deepEqual(pendingPresses([6,11],[0,0]),[]);
});
