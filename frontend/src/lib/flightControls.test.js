import test from 'node:test';
import assert from 'node:assert/strict';
import {pilotAxes, helmAxes, thrustDown} from './flightControls.js';

test('P1 joystick F forward, S backward, releasing to neutral', () => {
  assert.deepEqual(pilotAxes(new Set(['f']), 'NAVIGATION'), [1,0]);
  assert.deepEqual(pilotAxes(new Set(['s']), 'NAVIGATION'), [-1,0]);
  assert.deepEqual(pilotAxes(new Set(['f','s']), 'NAVIGATION'), [0,0]);
  assert.deepEqual(pilotAxes(new Set(), 'NAVIGATION'), [0,0]);
  assert(thrustDown(new Set(['f']), 'NAVIGATION'));
});
test('P1 steers in both directions while moving forward or reverse', () => {
  assert.deepEqual(pilotAxes(new Set(['f','a']), 'NAVIGATION'), [1,-1]);
  assert.deepEqual(pilotAxes(new Set(['s','d']), 'NAVIGATION'), [-1,1]);
  assert.deepEqual(pilotAxes(new Set(['a']), 'NAVIGATION'), [0,-1]);
});
test('P2 only corrects roll while navigating, never steers', () => {
  assert.deepEqual(helmAxes(new Set(['arrowright']), 'NAVIGATION'), [0,1]);
  assert.deepEqual(helmAxes(new Set(['arrowleft']), 'NAVIGATION'), [0,-1]);
  assert.deepEqual(helmAxes(new Set(['j']), 'NAVIGATION'), [0,-1]);
  assert.deepEqual(helmAxes(new Set(['l']), 'NAVIGATION'), [0,1]);
  assert.deepEqual(helmAxes(new Set(['arrowright','l']), 'NAVIGATION'), [0,1]);
});
test('minigames still give both players independent steering and tilt axes', () => {
  assert.deepEqual(pilotAxes(new Set(['f','s','a']), 'MISSION'), [-1,0]);
  assert.deepEqual(helmAxes(new Set(['arrowright']), 'MISSION'), [1,0]);
  assert.deepEqual(helmAxes(new Set(['arrowleft']), 'MISSION'), [-1,0]);
});
test('F remains active after other keyboard actions', () => {
  const pressed = new Set(['arrowleft']);
  pressed.add('f');
  pressed.delete('arrowleft');
  assert.deepEqual(pilotAxes(pressed,'NAVIGATION'), [1,0]);
  pressed.add('a');
  assert.deepEqual(pilotAxes(pressed,'NAVIGATION'), [1,-1]);
  pressed.delete('a');
  pressed.add('s');
  assert.deepEqual(pilotAxes(pressed,'NAVIGATION'), [0,0]);
  pressed.delete('s');
  assert.deepEqual(pilotAxes(pressed,'NAVIGATION'), [1,0]);
});

test('W and arrow-up move forward; S and arrow-down reverse, no vertical movement', () => {
  for (const k of ['w', 'arrowup']) {
    assert.deepEqual(pilotAxes(new Set([k]), 'NAVIGATION'), [1, 0]);
  }
  for (const k of ['s', 'arrowdown']) {
    assert.deepEqual(pilotAxes(new Set([k]), 'NAVIGATION'), [-1, 0]);
  }
  assert.deepEqual(pilotAxes(new Set(['w','arrowdown']), 'NAVIGATION'), [0, 0]);
  assert(thrustDown(new Set(['arrowup']), 'NAVIGATION'));
});
