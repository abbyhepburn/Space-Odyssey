"""Planet-aware mission planning and a local authority for the unfinalized firmware.

This module never sends invented commands to the Pico. Hardware execution requires
an agreed mission protocol; the renderer labels local progress as simulation.
"""
import asyncio
import os
import time
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

PLANETS = ('MERCURY','VENUS','EARTH','MARS','JUPITER','SATURN','URANUS','NEPTUNE')
CONTROLS = ('JUMP','DUCK','SHAKE','COOP_SHAKE','UPWARD_FLICK')

class Objective(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    action: Literal['JUMP','DUCK','SHAKE','COOP_SHAKE','UPWARD_FLICK']
    instruction: str = Field(min_length=3,max_length=160)
    target: int = Field(ge=1,le=12)

class PlanetMission(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    planet: Literal['MERCURY','VENUS','EARTH','MARS','JUPITER','SATURN','URANUS','NEPTUNE']
    title: str = Field(min_length=3,max_length=70)
    briefing: str = Field(min_length=10,max_length=340)
    objectives: list[Objective] = Field(min_length=1,max_length=3)
    time_limit_s: int = Field(ge=30,le=180)

    def validate_context(self, planet, controls):
        if self.planet!=planet or any(o.action not in controls for o in self.objectives):
            raise ValueError('Mission does not match current planet or available controls')
        return self


def fallback(planet,controls):
    tasks=[Objective(action='SHAKE',instruction='Shake your remote to break apart approaching debris.',target=5),
           Objective(action='COOP_SHAKE',instruction='Both explorers shake within one second to break the large asteroid.',target=2),
           Objective(action='UPWARD_FLICK',instruction='Flick upward to release an orbital survey probe.',target=3)]
    tasks=[o for o in tasks if o.action in controls]
    if not tasks:
        tasks=[Objective(action=a,instruction='Jump over debris.' if a=='JUMP' else 'Duck beneath the debris.',target=3) for a in controls if a in ('JUMP','DUCK')]
    if not tasks: raise ValueError('No controls are currently available')
    return PlanetMission(planet=planet,title={'EARTH':'Beyond the blue horizon','SATURN':'Secrets of the rings','MARS':'Echoes of the red planet','JUPITER':'Eye of the great storm'}.get(planet,'The outer frontier'),
        briefing=f'Explore the orbital environment of {planet.title()}. Clear a safe path together, then deploy the survey equipment. This is a fictional expedition.', objectives=tasks[:3],time_limit_s=120)

async def create_mission(planet,controls):
    local=fallback(planet,controls)
    if not os.getenv('GEMINI_API_KEY'): return local,'LOCAL FALLBACK · API key not configured'
    try:
        from google import genai
        from google.genai import types
        async with genai.Client(api_key=os.environ['GEMINI_API_KEY'],http_options=types.HttpOptions(timeout=15000)).aio as client:
            response=await client.models.generate_content(model=os.getenv('GEMINI_MODEL','gemini-2.5-flash'),
                contents=f'''Generate a cooperative space exploration mission at {planet}. Available controls ONLY: {list(controls)}.
                JUMP and DUCK are camera detections; SHAKE hits small asteroids; COOP_SHAKE means both players hit a large asteroid within 1 second.
                UPWARD_FLICK is a gesture whose contextual purpose may be assigned by your instruction, such as deploying a probe.
                Use 1-3 sequential objectives. Targets 1-12, duration 30-180 seconds. Shared ship, two explorers.
                Ground the story in this planet's environment. Gas/ice giants have no walkable solid surface; use orbit, moons or fictional platforms.
                No joystick, steering, pinching, running, arbitrary new mechanics, code, or unsupported controls. Short clear instructions.''',
                config=types.GenerateContentConfig(response_mime_type='application/json',response_schema=PlanetMission))
            return PlanetMission.model_validate_json(response.text).validate_context(planet,controls),'GEMINI · Generated for this planet'
    except Exception:
        return local,'LOCAL FALLBACK · Gemini unavailable or response rejected'

class Exploration:
    def __init__(self, simulated=True):
        self.planet='SATURN'; self.controls=list(CONTROLS); self.simulated=simulated
        self.mission=None; self.source='Select a planet and generate an expedition'
        self.pending=False; self.error=''; self.epoch=0; self.progress=[]
        self.started=0; self.outcome='IDLE'; self.event=None; self.event_seq=0
        self.shakes={}; self.last_actions={}; self.duck=set(); self.task=None

    def snapshot(self):
        remaining=max(0,self.mission.time_limit_s-(time.monotonic()-self.started)) if self.started else 0
        if self.outcome=='ACTIVE' and remaining<=0: self.outcome='EXPIRED'
        return {'planet':self.planet,'controls':self.controls,'mission':self.mission.model_dump() if self.mission else None,
            'source':self.source,'pending':self.pending,'error':self.error,'progress':self.progress,
            'remaining':round(remaining,1),'outcome':self.outcome,'event':self.event,
            'authority':'LOCAL SIMULATOR' if self.simulated else 'PICO PROTOCOL NOT CONFIGURED'}

    def select(self,planet):
        if planet not in PLANETS: raise ValueError('Unknown planet')
        self.epoch+=1; self.planet=planet; self.mission=None; self.progress=[]; self.outcome='IDLE'
        self.started=0; self.error=''; self.shakes={}; self.duck=set()
        if self.task: self.task.cancel()
        self.pending=False

    async def generate(self):
        if self.pending or self.outcome=='ACTIVE': return
        self.pending=True; epoch=self.epoch
        try:
            mission,source=await create_mission(self.planet,self.controls)
            if self.epoch!=epoch: return
            mission.validate_context(self.planet,self.controls)
            self.mission=mission; self.source=source; self.progress=[0]*len(mission.objectives)
            self.outcome='READY' if self.simulated else 'AWAITING_FIRMWARE'
            self.started=0; self.shakes={}; self.last_actions={}; self.duck=set()
        except Exception as exc: self.error=str(exc)
        finally:
            if self.epoch==epoch: self.pending=False

    def command(self,command):
        p=command.split(',')
        if len(p)==2 and p[0]=='PLANET': self.select(p[1])
        elif command=='MISSION_GENERATE':
            if not self.pending and self.outcome!='ACTIVE': self.task=asyncio.create_task(self.generate())
        elif command=='MISSION_START':
            if self.mission and self.simulated and self.outcome=='READY': self.started=time.monotonic(); self.outcome='ACTIVE'
        elif len(p)==3 and p[0]=='ACTION': self.action(p[1],p[2])
        else: raise ValueError('Invalid exploration command')

    def action(self,player,action):
        if player not in ('P1','P2') or action not in (*CONTROLS,'DUCK_OFF'): raise ValueError('Unknown input')
        if not self.simulated: raise ValueError('Waiting for the finalized Pico mission protocol')
        if action=='COOP_SHAKE': raise ValueError('Cooperative actions require two separate player inputs')
        self.snapshot()  # Expire before processing a late input.
        if self.outcome!='ACTIVE': return
        now=time.monotonic(); key=(player,action)
        if action=='DUCK_OFF': self.duck.discard(player); return
        if action not in self.controls and not (action=='SHAKE' and 'COOP_SHAKE' in self.controls): return
        if now-self.last_actions.get(key,0)<.35: return
        self.last_actions[key]=now
        if action=='DUCK':
            if player in self.duck: return
            self.duck.add(player)
        idx=next((i for i,o in enumerate(self.mission.objectives) if self.progress[i]<o.target),None)
        if idx is None:return
        objective=self.mission.objectives[idx]; matched=action==objective.action
        if objective.action=='COOP_SHAKE' and action=='SHAKE':
            self.shakes[player]=now; other='P2' if player=='P1' else 'P1'
            matched=other in self.shakes and abs(now-self.shakes[other])<=1
            if matched:self.shakes={}
        self.event_seq+=1
        self.event={'id':self.event_seq,'action':action,'player':player,'matched':matched}
        if matched:
            self.progress[idx]+=1
            if self.progress[idx]>=objective.target:self.shakes={}
        if all(self.progress[i]>=o.target for i,o in enumerate(self.mission.objectives)): self.outcome='COMPLETE'
