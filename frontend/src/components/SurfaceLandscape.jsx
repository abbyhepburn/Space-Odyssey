import React,{useEffect,useMemo,useRef} from 'react';
import * as THREE from 'three';
import {useFrame} from '@react-three/fiber';

// Stylized first-person LOCAL SURFACE environments. These are not geological simulations.
// Gas giants deliberately have no surface mode: Saturn's ring track is orbital.
const palette={
 MERCURY:{ground:'#777873',stone:'#b0ada3',sky:'#080e1b',horizon:'#525462',haze:'#a4a09b',light:'#faf1dc',detail:'#484a4a'},
 VENUS:{ground:'#a16b39',stone:'#ce994e',sky:'#9c572d',horizon:'#e1a85b',haze:'#e2aa64',light:'#ffe2b2',detail:'#79502d'},
 EARTH:{ground:'#52765c',stone:'#87917c',sky:'#112e5d',horizon:'#81abce',haze:'#adcddf',light:'#f8f2dc',detail:'#364c38'},
 MARS:{ground:'#8b4236',stone:'#bf7050',sky:'#351e30',horizon:'#b36b53',haze:'#dc9672',light:'#ffceb0',detail:'#602e29'}
};
export const isSurfaceGame=(planet,mode)=>['MERCURY','VENUS','EARTH','MARS','SATURN'].includes(planet)&&['RING_RACE','SURFACE_RUN','CRATER_LEAP','SAMPLE_HUNT','STORM_SHELTER'].includes(mode);

function Ground({colors}){
 const texture=useMemo(()=>{const c=document.createElement('canvas');c.width=c.height=256;const x=c.getContext('2d');let seed=311;const rnd=()=>((seed=seed*16807%2147483647)/2147483647);x.fillStyle='#aaaaaa';x.fillRect(0,0,256,256);for(let i=0;i<12000;i++){const v=90+Math.floor(rnd()*110);x.fillStyle=`rgb(${v},${v},${v})`;x.fillRect(rnd()*256,rnd()*256,1+rnd()*2,1+rnd()*2)}const t=new THREE.CanvasTexture(c);t.wrapS=t.wrapT=THREE.RepeatWrapping;t.repeat.set(25,100);return t},[]);
 useEffect(()=>()=>texture.dispose(),[texture]);
 const geometry=useMemo(()=>{
  const g=new THREE.PlaneGeometry(220,1200,110,240);g.rotateX(-Math.PI/2);
  const a=g.attributes.position;
  for(let i=0;i<a.count;i++){
   const x=a.getX(i),z=a.getZ(i);
   const edges=Math.max(0,Math.abs(x)-5);
   const relief=Math.sin(x*.14+z*.026)*1.6+Math.cos(x*.08-z*.085)*1.2+Math.sin(z*.12+x*.08)*.55;
   a.setY(i,Math.min(12,edges*.09)*.4*relief);
  }
  g.computeVertexNormals();return g;
 },[]);
 useEffect(()=>()=>geometry.dispose(),[geometry]);
 return <mesh geometry={geometry} position={[0,-2.5,-380]} receiveShadow><meshStandardMaterial color={colors.ground} map={texture} bumpMap={texture} bumpScale={.12} roughness={1} side={THREE.DoubleSide}/></mesh>;
}
function Sky({colors}){
 const material=useMemo(()=>new THREE.ShaderMaterial({side:THREE.BackSide,depthWrite:false,uniforms:{zenith:{value:new THREE.Color(colors.sky)},horizon:{value:new THREE.Color(colors.horizon)}},vertexShader:'varying vec3 dir;void main(){dir=position;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',fragmentShader:'uniform vec3 zenith;uniform vec3 horizon;varying vec3 dir;void main(){float h=smoothstep(-.12,.64,normalize(dir).y);vec3 col=mix(horizon,zenith,h);gl_FragColor=vec4(col,1.0);}' }),[colors]);
 useEffect(()=>()=>material.dispose(),[material]);const group=useRef();useFrame(({camera})=>{if(group.current)group.current.position.copy(camera.position)});
 return <group ref={group}><mesh material={material}><sphereGeometry args={[650,32,20]}/></mesh><mesh position={[210,170,-440]}><sphereGeometry args={[23,24,18]}/><meshBasicMaterial color={colors.light} toneMapped={false}/></mesh></group>;
}
function RockScatter({colors,planet}){
 const mesh=useRef(); const positions=useMemo(()=>{
  let seed=137;const rand=()=>((seed=seed*16807%2147483647)/2147483647);
  return Array.from({length:230},()=>{let x=(rand()-.5)*105; if(Math.abs(x)<5)x+=Math.sign(x||1)*6;const z=-rand()*700;return [x,-2.1+rand()*.3,z,.5+rand()*2.5,rand()*6.28];});
 },[]);
 useEffect(()=>{if(!mesh.current)return;const d=new THREE.Object3D();positions.forEach(([x,y,z,s,r],i)=>{d.position.set(x,y,z);d.rotation.set(r*.1,r,r*.4);d.scale.set(s,s*.35,s*.7);d.updateMatrix();mesh.current.setMatrixAt(i,d.matrix)});mesh.current.instanceMatrix.needsUpdate=true},[positions]);
 return <instancedMesh ref={mesh} args={[undefined,undefined,positions.length]}><dodecahedronGeometry args={[1,0]}/><meshStandardMaterial color={planet==='EARTH'?colors.detail:colors.stone} roughness={1} /></instancedMesh>;
}
function Horizon({colors,planet}){return <group>{[-1,1].map((side)=><group key={side}>
 {Array.from({length:16},(_,i)=>{const x=side*(15+(i*13)%85);const z=-40-i*42;const h=planet==='MARS'?12+(i*7)%22:planet==='VENUS'?7+(i*11)%15:6+(i*7)%12;return <mesh key={i} position={[x,-2.5+h*.38,z]} rotation={[0,i*.68,.15]}><coneGeometry args={[6+(i*3)%11,h,18]}/><meshStandardMaterial color={i%3===0?colors.stone:colors.detail} roughness={1}/></mesh>})}
 </group>)}
 {planet==='EARTH'&&Array.from({length:40},(_,i)=><mesh key={i} position={[(i%2?-1:1)*(9+(i*7)%23),-1.7,-18-i*16]}><coneGeometry args={[.95,3+(i%4),6]}/><meshStandardMaterial color={i%2?'#304e34':'#3a633b'} /></mesh>)}
 </group>}
function DistantOutpost({colors,mode}){
 if(mode==='CRATER_LEAP')return null;
 return <group position={[12,-1.4,-95]}><mesh position={[0,2.4,0]}><cylinderGeometry args={[5.5,5.5,4.8,12]}/><meshStandardMaterial color={'#a4a7a4'} metalness={.35} roughness={.65}/></mesh><mesh position={[0,5.1,0]}><sphereGeometry args={[5.5,20,10,0,Math.PI*2,0,Math.PI/2]}/><meshStandardMaterial color={'#c9c5b9'} metalness={.35}/></mesh><mesh position={[0,1,3.8]}><boxGeometry args={[2.2,3,.4]}/><meshStandardMaterial color={'#263844'} emissive={'#293b40'} emissiveIntensity={.3}/></mesh>{[-1,1].map(x=><mesh key={x} position={[x*10,6,0]} rotation={[0,0,x*.3]}><boxGeometry args={[12,.15,6]}/><meshStandardMaterial color={'#273e59'} metalness={.6}/></mesh>)}</group>;
}
export default function SurfaceLandscape({planet='MARS',mode='SURFACE_RUN'}){
 const colors=planet==='SATURN'?{...palette.MERCURY,ground:'#bbc8d6',stone:'#dce7f2',haze:'#5a6982',sky:'#070e1b',horizon:'#233451'}:palette[planet]||palette.MARS;
 return <>
  <color attach="background" args={[colors.sky]}/><fog attach="fog" args={[colors.haze,planet==='VENUS'?32:120,planet==='VENUS'?135:planet==='MARS'?205:280]}/>
  <ambientLight intensity={planet==='MERCURY'?.8:1.2} color={colors.light}/><hemisphereLight args={[colors.horizon,colors.detail,1.3]}/><directionalLight position={[45,60,-120]} intensity={2.1} color={colors.light}/>
  <Sky colors={colors}/><Ground colors={colors}/><RockScatter colors={colors} planet={planet}/><Horizon colors={colors} planet={planet}/><DistantOutpost colors={colors} mode={mode}/>
 </>;
}
