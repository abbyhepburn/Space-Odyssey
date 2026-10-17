// Game authority accepts normalized [-1, 1] axes from either test keys or remotes.
// Navigation P1 AXIS X = signed forward/backward; Y = ship yaw/steering.
// Navigation P2 AXIS Y = roll correction; P2 never steers during flight.
// During minigames, both players' AXIS X is reserved for STEER/TILT challenges.
// This is the keyboard-only adapter; physical joystick readings can send the
// same FLIGHT,P1,AXIS,x,y / FLIGHT,P2,AXIS,x,y messages directly.
const horizontal = (keys, left, right) => Number(keys.has(right)) - Number(keys.has(left));
export function pilotAxes(keys, phase) {
  if (phase === 'MISSION' || phase === 'RESULTS') {
    return [horizontal(keys, 'a', 'd'), 0];
  }
  return [Number(keys.has('f')) - Number(keys.has('s')), horizontal(keys, 'a', 'd')];
}
export function helmAxes(keys, phase = 'NAVIGATION') {
  const joystick = horizontal(keys, 'arrowleft', 'arrowright');
  if (phase === 'MISSION' || phase === 'RESULTS') return [joystick, 0];
  // J/L are fallback test keys for the eventual P2 tilt sensor.
  // Left/right arrows are convenient alternative debug controls, not P2 yaw.
  return [0, Math.max(-1, Math.min(1, joystick + horizontal(keys, 'j', 'l')))];
}
export function thrustDown(keys, phase) {
  return phase === 'NAVIGATION' && keys.has('f');
}
