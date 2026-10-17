import test from 'node:test';
import assert from 'node:assert/strict';
import {discoveries,SCENE_ANCHORS} from './discoveries.js';
import {aimedDiscovery} from './discoveryTargeting.js';
const distance=(a,b)=>Math.hypot(...a.map((x,i)=>x-b[i]));
test('every discovery has a source and location description',()=>{
  for(const d of discoveries){assert(d.location?.length>20,d.name);assert(d.url?.startsWith('https://'),d.name)}
});
test('Earth satellites are near the EARTH scene anchor and not Jupiter',()=>{
  for(const d of discoveries.filter(d=>['EARTH','EARTH_L2'].includes(d.zone))){
    assert(distance(d.position,SCENE_ANCHORS.EARTH)<150,d.name);
    assert(distance(d.position,SCENE_ANCHORS.EARTH)<distance(d.position,SCENE_ANCHORS.JUPITER),d.name);
  }
});
test('Jupiter and Saturn moons remain close to their host planets',()=>{
 for(const body of ['JUPITER','SATURN']) for(const d of discoveries.filter(d=>d.zone===body))assert(distance(d.position,SCENE_ANCHORS[body])<65,d.name)
});
test('distant nebulae and galaxies are beyond the playable solar system',()=>{
 for(const d of discoveries.filter(d=>d.zone==='DEEP_SKY'))assert(distance(d.position,[0,0,0])>1300,d.name)
});
test('center-aim picks the discovery and cannot target a different direction',()=>{
 const p=discoveries.find(d=>d.id==='hubble');const [x,y,z]=p.position;
 const pilot={yaw:Math.atan2(x,-z),pitch:Math.atan2(y,Math.hypot(x,z))};
 assert.equal(aimedDiscovery([0,0,0],pilot,[p])?.id,'hubble');
 assert.equal(aimedDiscovery([0,0,0],{yaw:2,pitch:0},[p]),null)
});
