import React, { useEffect, useMemo, useRef, useState } from 'react';
import './SpaceOdysseyLaunch.css';
import LaunchCinematic from './LaunchCinematic';

/**
 * Self-contained cinematic opening for Space Odyssey.
 *
 * Drop into an existing React/Vite frontend as:
 *   <SpaceOdysseyLaunch onLaunchComplete={() => setScreen('flight')} />
 *
 * The component never changes your flight/game state and never calls the backend.
 * It only manages an introductory menu + skippable cockpit boot animation.
 */
const BOOT_STAGES = [
  {at:0,label:'Crew check',detail:'Two pilots aboard. Take a moment to get settled.'},
  {at:2500,label:'Cockpit power',detail:'Displays are coming on. Earth is in view.'},
  {at:4500,label:'Navigation check',detail:'The ship is ready for its first destination.'},
  {at:6000,label:'Leaving orbit',detail:'Your flight begins here.'},
  {at:8500,label:'Take the controls',detail:'Choose a planet and see what you find.'},
];
const CHECKLIST = ['Crew on board','Cockpit powered','Navigation ready'];
const INTRO_MS = 10000;
const STAR_COUNT = 140;

function seededNoise(seed) {
  let n = seed >>> 0;
  return () => {
    n = (Math.imul(n, 1664525) + 1013904223) >>> 0;
    return n / 4294967296;
  };
}

function createStars() {
  const next = seededNoise(217);
  return Array.from({ length: STAR_COUNT }, (_, i) => ({
    id: i,
    left: `${next() * 100}%`,
    top: `${next() * 100}%`,
    size: `${0.7 + next() * 2.4}px`,
    opacity: 0.28 + next() * 0.7,
    duration: `${2.4 + next() * 5}s`,
    delay: `${-next() * 6}s`,
  }));
}

function Icon({ name }) {
  if (name === 'arrow') return <span aria-hidden="true">↗</span>;
  if (name === 'play') return <span aria-hidden="true">▶</span>;
  return null;
}

export default function SpaceOdysseyLaunch({
  onLaunchComplete,
  phase = 'READY',
  serverAge = 0,
  onOpenControls,
  onOpenDiscoveries,
  disabled = false,
  title = 'SPACE ODYSSEY',
}) {
  const mode=phase==='BOOT'?'intro':'menu'; // menu | intro
  const elapsed=serverAge*1000;
  const [audio, setAudio] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const stage = useMemo(() => [...BOOT_STAGES].reverse().find(s => elapsed >= s.at) || BOOT_STAGES[0], [elapsed]);
  const stars = useMemo(createStars, []);
  const onCompleteRef = useRef(onLaunchComplete);
  const completedRef = useRef(false);
  onCompleteRef.current = onLaunchComplete;

  useEffect(() => {
    if (typeof window !== 'undefined' && window.matchMedia) {
      setReducedMotion(window.matchMedia('(prefers-reduced-motion: reduce)').matches);
    }
  }, []);

  const finish = () => {
    if (completedRef.current) return;
    completedRef.current = true;
    onCompleteRef.current?.();
  };

  const start = () => {
    if(disabled)return;
    onLaunchComplete?.();
  };

  useEffect(() => {
    function onKey(event) {
      if (mode === 'intro' && ['Escape', 'Enter', ' '].includes(event.key)) {
        event.preventDefault();
        return;
      } else if (mode === 'menu' && event.key === 'Enter' && event.target?.tagName !== 'BUTTON') {
        event.preventDefault();
        start();
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [mode]);

  const isIntro = mode === 'intro';
  const bootActive = isIntro && elapsed > 500;
  const earthVisible = !isIntro || elapsed > 3800;
  const activeCheck = elapsed < 2500 ? 0 : elapsed < 4500 ? 1 : 2;
  const progress = Math.min(100, Math.round(elapsed / INTRO_MS * 100));
  return (
    <section className={`so-launch so-launch--${mode}`} aria-label="Space Odyssey opening scene">
      {isIntro&&<LaunchCinematic elapsed={elapsed}/>}
      <div className="so-launch__dust" aria-hidden="true" />
      <div className="so-launch__nebula" aria-hidden="true" />
      <div className="so-launch__stars" aria-hidden="true">
        {stars.map(s => <i key={s.id} className="so-launch__star" style={{ left:s.left, top:s.top, width:s.size, height:s.size, opacity:s.opacity, animationDuration:s.duration, animationDelay:s.delay }} />)}
      </div>
      <div className={`so-launch__earth ${earthVisible ? '' : 'so-launch__earth--dark'}`} aria-hidden="true"><span /></div>
      <div className="so-launch__horizon" aria-hidden="true" />
      <div className={`so-launch__cockpit ${bootActive ? 'so-launch__cockpit--active' : ''}`} aria-hidden="true">
        <div className="so-launch__strut so-launch__strut--left" />
        <div className="so-launch__strut so-launch__strut--right" />
        <div className="so-launch__beam" />
        <div className="so-launch__dashboard">
          <div className="so-launch__dash-side">
            <span className="so-launch__dash-label">NAV / ORBIT</span>
            <div className="so-launch__radar"><span /><i /><b /></div>
          </div>
          <div className="so-launch__console">
            <div className="so-launch__console-top"><span>FLIGHT DIRECTOR</span><span className="so-launch__signal">{bootActive ? '● ONLINE' : '○ STANDBY'}</span></div>
            <div className="so-launch__console-bars"><i /><i /><i /><i /><i /><i /><i /><i /><i /></div>
            <div className="so-launch__console-bottom"><span>OXYGEN <b>99.8%</b></span><span>REACTOR <b>{bootActive ? 'NOMINAL' : 'OFFLINE'}</b></span></div>
          </div>
          <div className="so-launch__dash-side so-launch__dash-side--right"><span className="so-launch__dash-label">FLIGHT STATUS</span><div className="so-launch__levels"><i/><i/><i/><i/><i/></div><small>EARTH ORBIT / 004</small></div>
        </div>
      </div>
      <div className="so-launch__glare" aria-hidden="true" />
      <div className="so-launch__grain" aria-hidden="true" />
      <header className="so-launch__top">
        <div className="so-launch__brand"><span className="so-launch__brandmark">◈</span><span>ODYSSEY <b>EXPLORATION DIVISION</b></span></div>
        <span className="so-launch__mission-number">FLIGHT NO. AO–001 <em>◆</em> SOL SYSTEM</span>
      </header>
      {!isIntro ? (
        <main className="so-launch__hero">
          <div className="so-launch__eyebrow"><i/> MISSION CONTROL // AWAITING CREW</div>
          <h1>{title.split(' ').map((word, i) => <span key={`${word}-${i}`}>{word}</span>)}</h1>
          <p className="so-launch__tagline">Two explorers. One spacecraft.<br />An entire universe to discover.</p>
          <div className="so-launch__menu">
            <button type="button" className="so-launch__primary" onClick={start} disabled={disabled}>{disabled?'CONNECTING TO SHIP':'INITIATE LAUNCH'} <Icon name="arrow" /></button>
            <div className="so-launch__secondary-row">
              <button type="button" onClick={onOpenControls} disabled={!onOpenControls}>FLIGHT MANUAL</button>
              <button type="button" onClick={onOpenDiscoveries} disabled={!onOpenDiscoveries}>PLANET LOG</button>
            </div>
          </div>
          <div className="so-launch__keyboard">TWO PILOTS · READY FOR LAUNCH</div>
        </main>
      ) : (
        <main className="so-launch__boot" aria-live="polite">
          <div className="so-launch__boot-index">CREWED FLIGHT <span>·</span> EARTH ORBIT</div>
          <h2>{stage.label}</h2>
          <p>{stage.detail}</p>
          <ol className="launch-checklist" aria-label="Launch checklist">
            {CHECKLIST.map((item,index)=><li key={item} className={index<activeCheck?'is-complete':index===activeCheck?'is-current':''}>
              <span className="launch-checklist__mark" aria-hidden="true">{index<activeCheck?'✓':String(index+1).padStart(2,'0')}</span>
              <span>{item}</span>
              <b>{index<activeCheck?'READY':index===activeCheck?'CHECKING':'STANDBY'}</b>
            </li>)}
          </ol>
          <div className="launch-progress" role="progressbar" aria-label="Launch sequence" aria-valuemin="0" aria-valuemax="100" aria-valuenow={progress}><span style={{width:`${progress}%`}}/></div>
          <div className="launch-progress__caption"><span>LAUNCH SEQUENCE</span><span>{progress}%</span></div>
          <span className="so-launch__skip">Preparing flight · please wait</span>
        </main>
      )}
      <footer className="so-launch__bottom"><span>EARTH ORBIT <b>◆</b> {isIntro?'CREWED FLIGHT':'SOL 03'}</span><span>{isIntro?'PRE-FLIGHT CHECKLIST':'SPACE ODYSSEY // EXPEDITION PROGRAM'}</span><span>{isIntro?'SYSTEMS CHECK IN PROGRESS':'CREW ACCESS ENABLED'}</span></footer>
    </section>
  );
}
