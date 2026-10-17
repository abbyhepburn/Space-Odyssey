import React, { useEffect, useMemo, useRef, useState } from 'react';
import './SpaceOdysseyLaunch.css';

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
  { at: 0,       label: 'INITIALIZING FLIGHT SYSTEMS', detail: 'Crew telemetry established', progress: 14 },
  { at: 2500,    label: 'NAVIGATION ARRAY ONLINE', detail: 'Star charts synchronized', progress: 38 },
  { at: 5000,    label: 'REACTOR CORE STABILIZED', detail: 'Power distribution nominal', progress: 62 },
  { at: 7800,    label: 'THRUSTERS ARMED', detail: 'Flight controls responding', progress: 88 },
  { at: 10700,   label: 'CLEARANCE GRANTED', detail: 'Crew, you have the helm', progress: 100 },
];
const INTRO_MS = 12600;
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
  onOpenControls,
  onOpenDiscoveries,
  title = 'SPACE ODYSSEY',
}) {
  const [mode, setMode] = useState('menu'); // menu | intro
  const [elapsed, setElapsed] = useState(0);
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
    completedRef.current = false;
    setElapsed(0);
    setMode('intro');
  };

  useEffect(() => {
    if (mode !== 'intro') return;
    if (reducedMotion) {
      finish();
      return;
    }
    let frame;
    const startAt = performance.now();
    const tick = (now) => {
      const next = Math.min(INTRO_MS, now - startAt);
      setElapsed(next);
      if (next >= INTRO_MS) finish();
      else frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
    // onLaunchComplete is tracked by a ref so callback identity changes do not restart playback.
  }, [mode, reducedMotion]);

  useEffect(() => {
    function onKey(event) {
      if (mode === 'intro' && ['Escape', 'Enter', ' '].includes(event.key)) {
        event.preventDefault();
        finish();
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
  return (
    <section className={`so-launch so-launch--${mode}`} aria-label="Space Odyssey opening scene">
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
            <button type="button" className="so-launch__primary" onClick={start}>INITIATE LAUNCH <Icon name="arrow" /></button>
            <div className="so-launch__secondary-row">
              <button type="button" onClick={onOpenControls} disabled={!onOpenControls}>FLIGHT MANUAL</button>
              <button type="button" onClick={onOpenDiscoveries} disabled={!onOpenDiscoveries}>DISCOVERIES</button>
            </div>
          </div>
          <div className="so-launch__keyboard">TWO PILOTS · READY FOR LAUNCH</div>
        </main>
      ) : (
        <main className="so-launch__boot" aria-live="polite">
          <div className="so-launch__boot-index">A // INITIALIZATION SEQUENCE</div>
          <h2>{stage.label}</h2>
          <p>{stage.detail}</p>
          <div className="so-launch__progress" role="progressbar" aria-valuenow={stage.progress} aria-valuemin="0" aria-valuemax="100" aria-label="Cockpit initialization"><span style={{ width: `${stage.progress}%` }} /></div>
          <div className="so-launch__boot-bottom"><span>SEQUENCE {String(BOOT_STAGES.indexOf(stage) + 1).padStart(2,'0')} / 05</span><span>{stage.progress}%</span></div>
          <div className={`so-launch__hand ${elapsed > 5000 ? 'so-launch__hand--engage' : ''}`} aria-hidden="true"><div className="so-launch__sleeve" /><div className="so-launch__glove" /></div>
          <button className="so-launch__skip" type="button" onClick={finish}>SKIP INTRO ↗</button>
        </main>
      )}
      <footer className="so-launch__bottom"><span>EARTH ORBIT <b>◆</b> SOL 03</span><span>SPACE ODYSSEY // EXPEDITION PROGRAM</span><span>{isIntro ? 'AUTOMATED STARTUP' : 'CREW ACCESS ENABLED'}</span></footer>
    </section>
  );
}
