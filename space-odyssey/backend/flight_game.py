"""Authoritative local stand-in for the planned Pico firmware.
All flight, collision, mission and score state lives here, never in React.
The FLIGHT commands are a draft simulator API, not the old Pico wire protocol.
"""
import asyncio
import math
import os
import random
import time
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

DESTINATIONS=[('MARS',-.55,.08),('SATURN',0.,.08),('JUPITER',.55,.08),('NEPTUNE',.95,.08)]
CONTROLS=['STEER','JUMP','DUCK','SHAKE','COOP_SHAKE','UPWARD_FLICK','SELECT']
class Movement(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    control: Literal['STEER','JUMP','DUCK','SHAKE','COOP_SHAKE','UPWARD_FLICK']
    instruction: str=Field(min_length=4,max_length=150)
class GameMission(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    planet: Literal['MARS','SATURN','JUPITER','NEPTUNE']
    game_type: Literal['ASTEROID_DODGE','RING_RACE']
    name: str=Field(min_length=3,max_length=70)
    briefing: str=Field(min_length=10,max_length=260)
    movements: list[Movement]=Field(min_length=1,max_length=6)
    obstacle_count: int=Field(ge=5,le=12)
    time_limit_s: int=Field(ge=45,le=60)

    def validate_planet(self,planet):
        if self.planet!=planet: raise ValueError('Wrong planet')
        if self.game_type=='RING_RACE' and planet!='SATURN':raise ValueError('Ring race is only implemented at Saturn')
        required={'STEER','JUMP'} if self.game_type=='RING_RACE' else {'STEER','SHAKE','COOP_SHAKE'}
        if not required.issubset({m.control for m in self.movements}):raise ValueError('Missing required movement instructions')
        return self

def local_mission(planet):
    race=planet=='SATURN'
    return GameMission(planet=planet,game_type='RING_RACE' if race else 'ASTEROID_DODGE',
        name='Ringrunners: Icefall Circuit' if race else f'{planet.title()}: Asteroid Escape',
        briefing='Race your partner along a constructed track above the rings. Steer past ice blocks and jump the glowing hurdles. First across wins 100 points.' if race else 'Pilot through the orbital debris field together. Dodge rocks, shake to break small asteroids, and synchronize both shakes to clear the large ones.',
        movements=([Movement(control='STEER',instruction='Tilt or move the joystick left and right to change lanes.'),Movement(control='JUMP',instruction='Jump as a glowing hurdle reaches you. Your webcam detects the jump.'),Movement(control='DUCK',instruction='Duck when an overhead gate reaches you.'),Movement(control='UPWARD_FLICK',instruction='Flick upward for a short speed boost; it recharges in 3 seconds.')] if race else [Movement(control='STEER',instruction='Tilt or use the joystick to move around approaching asteroids.'),Movement(control='SHAKE',instruction='Shake to hit the nearest small asteroid when it is inside the targeting zone.'),Movement(control='COOP_SHAKE',instruction='Both players shake within one second to hit a large asteroid in range.'),Movement(control='UPWARD_FLICK',instruction='Flick upward to briefly boost through clear space; recharge takes 3 seconds.')]),obstacle_count=8,time_limit_s=60)

async def generate_game(planet):
    if not os.getenv('GEMINI_API_KEY'):return local_mission(planet),'LOCAL MISSION · GEMINI KEY NOT SET'
    try:
        from google import genai
        from google.genai import types
        async with genai.Client(api_key=os.environ['GEMINI_API_KEY'],http_options=types.HttpOptions(timeout=15000)).aio as client:
            result=await client.models.generate_content(model=os.getenv('GEMINI_MODEL','gemini-2.5-flash'),
                contents=f'''Generate one randomized two-player first-person game mission at {planet}. Controls available: {CONTROLS}.
                Choose an IMPLEMENTED game_type: ASTEROID_DODGE (any planet, orbital spacecraft flying), or RING_RACE (Saturn only, fictional built track above rings).
                Include a vivid short game name, clear briefing and movements. ASTEROID_DODGE MUST explain STEER, SHAKE and COOP_SHAKE. RING_RACE MUST explain STEER and JUMP, and should explain DUCK.
                Mechanics: joystick/tilt steers; camera jump clears low hurdles; duck clears overhead gates; shake destroys a small asteroid within 32 units; both shakes within 1 second destroy a large asteroid; upward flick gives a 1-second boost with 3-second cooldown.
                Obstacles 5-12; time 45-60 seconds. Do not invent any other mechanic, gesture or goal. Race winner earns 100 points; asteroid escape is cooperative. No landable surface on gas giants; use orbit. Vary name, story, obstacle count and timing.''',
                config=types.GenerateContentConfig(response_mime_type='application/json',response_schema=GameMission))
            mission=GameMission.model_validate_json(result.text).validate_planet(planet)
            return mission,'GEMINI · PLANET + CONTROL-AWARE MISSION'
    except Exception:return local_mission(planet),'LOCAL MISSION · GEMINI UNAVAILABLE / INVALID RESPONSE'

class FlightGame:
    def __init__(self,simulated=True):
        self.simulated=simulated;self.task=None;self.generation=0;self.reset()
    def reset(self):
        if self.task:self.task.cancel()
        self.generation+=1;self.phase='READY';self.age=0.;self.world_time=0.;self.planet=None;self.mission=None;self.source='';self.error=''
        self.players=[dict(x=0.,y=0.,yaw=0.,pitch=.08,distance=0.,health=100,score=0,jump=0.,duck=False,boost=0.,cooldown=0.) for _ in range(2)]
        self.axes=[[0.,0.],[0.,0.]];self.input_at=[-10.,-10.];self.shakes=[-10.,-10.];self.last_shake=[-10.,-10.]
        self.roll=0.;self.speed=0.;self.travel=0.
        self.obstacles=[];self.winner='NONE';self.event='AWAITING LAUNCH';self.event_id=0
    def emit(self,text):self.event=text;self.event_id+=1
    def transition(self,phase):self.phase=phase;self.age=0.
    def targets(self):
        return [dict(planet=p,yaw=yaw,pitch=pitch) for p,yaw,pitch in DESTINATIONS]
    def target(self,i):
        p=self.players[0];target=min(DESTINATIONS,key=lambda d:math.hypot(d[1]-p['yaw'],d[2]-p['pitch']))
        return target[0] if math.hypot(target[1]-p['yaw'],target[2]-p['pitch'])<.17 else None
    async def generate(self,planet,version):
        mission,source=await generate_game(planet)
        if version!=self.generation:return
        self.mission=mission;self.source=source
    def command(self,line):
        parts=line.split(',')
        if parts[0]!='FLIGHT':raise ValueError('Invalid flight command')
        if not self.simulated:raise ValueError('Flight is a local preview until the Pico firmware protocol is finalized')
        if len(parts)==2 and parts[1]=='RESET':self.reset();return
        if len(parts)==2 and parts[1]=='LAUNCH':
            if self.phase=='READY':self.transition('LAUNCH');self.emit('ASCENT CONFIRMED — LEAVING EARTH')
            return
        if len(parts)<3 or parts[1] not in ('P1','P2'):raise ValueError('Invalid player')
        i=int(parts[1][1])-1;p=self.players[i];action=parts[2]
        if action=='AXIS' and len(parts)==5:
            x,y=map(float,parts[3:])
            if not all(math.isfinite(v) and -1<=v<=1 for v in (x,y)):raise ValueError('Axes must be finite and normalized')
            self.axes[i]=[x,y];self.input_at[i]=self.world_time;return
        if len(parts)!=3:raise ValueError('Invalid action')
        if action=='SELECT':
            if self.phase=='READY':
                self.command('FLIGHT,LAUNCH');return
            if self.phase=='NAVIGATION':
                if i!=0:return
                planet=self.target(i)
                if planet:
                    self.planet=planet;self.transition('TRAVEL');self.emit(f'{planet} LOCKED — GENERATING MISSION')
                    self.task=asyncio.create_task(self.generate(planet,self.generation))
                else:self.emit('ALIGN A PLANET WITH YOUR CROSSHAIR')
            elif self.phase=='BRIEFING' and self.mission:
                self.start_mission()
            elif self.phase=='RESULTS':self.reset()
            return
        if action not in ('JUMP','DUCK_ON','DUCK_OFF','SHAKE','UPWARD_FLICK'):raise ValueError('Unsupported action')
        if action=='DUCK_OFF':p['duck']=False;return
        if self.phase!='MISSION':return
        if action=='JUMP' and p['jump']<=0:p['jump']=.9
        elif action=='DUCK_ON':p['duck']=True
        elif action=='UPWARD_FLICK' and p['cooldown']<=0:p['boost']=1.;p['cooldown']=3.;self.emit(f'P{i+1} BOOST')
        elif action=='SHAKE' and self.world_time-self.last_shake[i]>.3:
            self.last_shake[i]=self.world_time;self.shakes[i]=self.world_time
            nearby=[o for o in self.obstacles if o['kind'] in ('ROCK','LARGE') and not o['destroyed'] and 0<o['z']-p['distance']<32 and abs(o['x']-p['x'])<2.4 and abs(o['y']-p['y'])<2.4]
            if nearby:
                o=min(nearby,key=lambda o:o['z'])
                if o['kind']=='LARGE':
                    if abs(self.shakes[0]-self.shakes[1])<=1 and min(self.shakes)>0:
                        o['destroyed']=True;self.shakes=[-10.,-10.]
                        for player in self.players:player['score']+=25
                        self.emit('SYNCHRONIZED HIT — LARGE ASTEROID CLEARED')
                    else:self.emit('LARGE ASTEROID — BOTH PLAYERS SHAKE TOGETHER')
                else:o['destroyed']=True;p['score']+=10;self.emit(f'P{i+1} ASTEROID CLEARED')
    def start_mission(self):
        self.transition('MISSION');self.shakes=[-10.,-10.]
        for p in self.players:p.update(x=0.,y=0.,distance=0.,health=100,jump=0.,duck=False,boost=0.,cooldown=0.)
        rng=random.Random(f'{self.planet}-{self.mission.name}-{self.generation}')
        self.obstacles=[]
        for n in range(self.mission.obstacle_count):
            race=self.mission.game_type=='RING_RACE'
            kind=('HURDLE','GATE','ROCK')[n%3] if race else ('LARGE' if n%3==2 else 'ROCK')
            self.obstacles.append(dict(id=n,x=0. if kind in ('HURDLE','GATE','LARGE') else rng.choice([-2.5,0.,2.5]),y=0. if race or kind=='LARGE' else rng.choice([-1.,0.,1.]),z=70.+n*55,kind=kind,destroyed=False,passed=[False,False]))
        self.emit('MISSION ACTIVE — FOLLOW YOUR MOVEMENT INSTRUCTIONS')
    def tick(self,dt):
        # Bound catch-up and subdivide physics so camera/serial lag cannot skip collisions.
        remaining=min(max(dt,0.),.25)
        while remaining>1e-8:
            step=min(1/60,remaining);self._step(step);remaining-=step
    def _step(self,dt):
        self.world_time+=dt
        if self.phase not in ('READY','RESULTS','BRIEFING'):self.age+=dt
        if self.phase=='LAUNCH' and self.age>=5:self.transition('NAVIGATION');self.emit('STEER TOWARD A PLANET — PRESS SELECT TO LOCK DESTINATION')
        if self.phase=='TRAVEL' and self.age>=4 and self.mission:self.transition('BRIEFING');self.emit('ARRIVED — REVIEW MISSION INSTRUCTIONS')
        flying=self.phase in ('LAUNCH','NAVIGATION','TRAVEL') or (self.phase=='MISSION' and self.mission.game_type=='ASTEROID_DODGE')
        if flying:
            tilt=self.axes[1][0] if self.world_time-self.input_at[1]<.4 else 0.
            self.roll=max(-.48,min(.48,self.roll+dt*(.08*math.sin(self.world_time*1.1)+.035-tilt*.5)))
        for i,p in enumerate(self.players):
            ax,ay=self.axes[i] if self.world_time-self.input_at[i]<.4 else (0.,0.)
            if self.phase in ('LAUNCH','NAVIGATION'):
                if i==0:
                    p['yaw']=max(-1.2,min(1.2,p['yaw']+ax*dt*.45))
                    self.speed=max(0.,6+ay*10);self.travel+=self.speed*dt
                else:
                    p['yaw']=self.players[0]['yaw'];p['pitch']=self.players[0]['pitch']
            elif self.phase=='MISSION':
                if self.mission.game_type=='ASTEROID_DODGE' and i==1:
                    p['x']=self.players[0]['x'];p['y']=self.players[0]['y']
                else:
                    p['x']=max(-4.,min(4.,p['x']+ax*dt*5));p['y']=max(-2.5,min(2.5,p['y']+ay*dt*4))
                p['jump']=max(0.,p['jump']-dt);p['boost']=max(0.,p['boost']-dt);p['cooldown']=max(0.,p['cooldown']-dt)
                if p['health']<=0:continue
                p['distance']+=dt*(20 if p['boost']>0 else 13)
                for o in self.obstacles:
                    if o['passed'][i] or o['destroyed'] or o['z']>p['distance']:continue
                    o['passed'][i]=True
                    aligned=abs(o['x']-p['x'])<1.5 and (self.mission.game_type=='RING_RACE' or abs(o['y']-p['y'])<1.7)
                    collision=(p['jump']<=0 if o['kind']=='HURDLE' else not p['duck'] if o['kind']=='GATE' else aligned)
                    if collision:
                        p['health']=max(0,p['health']-20);p['score']=max(0,p['score']-5);self.emit(f'P{i+1} IMPACT — '+('JUMP THE HURDLE' if o['kind']=='HURDLE' else 'DUCK UNDER THE GATE' if o['kind']=='GATE' else 'STEER OR SHAKE TO CLEAR ASTEROIDS'))
                    else:p['score']+=10
        if self.phase=='MISSION':
            finish=70+self.mission.obstacle_count*55
            reached=[i for i,p in enumerate(self.players) if p['distance']>=finish and p['health']>0]
            timed=self.age>=self.mission.time_limit_s
            if reached or timed or all(p['health']<=0 for p in self.players):
                if self.mission.game_type=='RING_RACE':
                    values=[(p['health']>0,p['distance'],p['score']) for p in self.players]
                    self.winner='TIE' if values[0]==values[1] else 'P1' if values[0]>values[1] else 'P2'
                    if not reached:self.winner='NONE'
                    for i,p in enumerate(self.players):
                        if self.winner==f'P{i+1}':p['score']+=100
                else:
                    self.winner='TEAM' if reached and all(p['health']>0 for p in self.players) else 'NONE'
                    if self.winner=='TEAM':
                        for p in self.players:p['score']+=100
                self.transition('RESULTS');self.emit('EXPEDITION COMPLETE' if self.winner!='NONE' else 'MISSION FAILED — RETRY FROM EARTH')
    def snapshot(self):
        return dict(roll=round(self.roll,4),speed=round(self.speed,1),travel=round(self.travel,2),phase=self.phase,age=round(self.age,2),planet=self.planet,players=self.players,targets=self.targets(),locked=[self.target(i) for i in range(2)],mission=self.mission.model_dump() if self.mission else None,source=self.source,obstacles=self.obstacles,winner=self.winner,event=self.event,event_id=self.event_id,authority='LOCAL PICO SIMULATOR' if self.simulated else 'PICO FLIGHT PROTOCOL PENDING')
