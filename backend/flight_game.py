"""Computer-only game authority: flight, cooperative missions, and Gemini planning."""
import asyncio
import math
import os
import random
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

# Compact demo destinations. Units intentionally do not represent real solar distances.
DESTINATIONS=[('MARS',-110.,14.,-190.),('SATURN',0.,14.,-220.),('JUPITER',110.,14.,-200.),('NEPTUNE',200.,14.,-160.),('MERCURY',-205.,14.,-100.),('VENUS',-175.,14.,-165.),('URANUS',205.,14.,-40.),('EARTH',0.,-36.,-12.)]
MODEL_ALIASES={}
MODES=('ASTEROID_DODGE','RING_RACE','ORBIT_SLALOM','METEOR_BREAK','BEACON_RELAY','SURFACE_RUN')
MOVES={'SURFACE_RUN':('JUMP','DUCK'),'ASTEROID_DODGE':('STEER','SHAKE'),'RING_RACE':('JUMP','DUCK'),'ORBIT_SLALOM':('STEER',),'METEOR_BREAK':('SHAKE',),'BEACON_RELAY':('STEER','PRESS')}
INSTRUCTIONS={'PRESS':'Click your joystick button to collect a beacon in your sights.','STEER':'Move left or right to avoid the rocks.','JUMP':'Jump over the low barriers.','DUCK':'Duck under the high barriers.','SHAKE':'Shake to break rocks inside the target circle.'}

class Movement(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    control: Literal['STEER','JUMP','DUCK','SHAKE','PRESS']
    instruction: str=Field(min_length=4,max_length=85)
class GameMission(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    planet: Literal['MERCURY','VENUS','EARTH','MARS','JUPITER','SATURN','URANUS','NEPTUNE']
    game_type: Literal['ASTEROID_DODGE','RING_RACE','ORBIT_SLALOM','METEOR_BREAK','BEACON_RELAY','SURFACE_RUN']
    name: str=Field(min_length=3,max_length=48)
    briefing: str=Field(min_length=5,max_length=120)
    movements: list[Movement]=Field(min_length=1,max_length=2)
    obstacle_count: int=Field(ge=6,le=10)
    time_limit_s: int=Field(ge=20,le=20)
    sync_boost: bool=True

    def validate_planet(self,planet,expected_mode=None):
        if self.planet!=planet:raise ValueError('Wrong planet')
        if self.game_type=='RING_RACE' and planet!='SATURN':raise ValueError('Ring game requires Saturn')
        if expected_mode and self.game_type!=expected_mode:raise ValueError('Game type not selected for this round')
        if [m.control for m in self.movements]!=list(MOVES[self.game_type]):raise ValueError('Unsupported movement set')
        return self

def choose_mode(planet,recent=()):
    available=[m for m in MODES if m!='RING_RACE' or planet=='SATURN']
    eligible=[m for m in available if m not in recent[-2:]]
    return random.SystemRandom().choice(eligible or [m for m in available if not recent or m!=recent[-1]])

def local_mission(planet,mode=None):
    mode=mode or ('RING_RACE' if planet=='SATURN' else 'ASTEROID_DODGE')
    rng=random.SystemRandom()
    titles={'SURFACE_RUN':['Horizon Hurdles','Cosmic Sprint','Crater Dash'],'BEACON_RELAY':['Signal Sweep','Beacon Rescue','Starlight Collectors'],'RING_RACE':['Icefall Run','Ring Relay','Frostline Dash'],'ASTEROID_DODGE':['Debris Dash','Orbit Breakers','Asteroid Alley'],'ORBIT_SLALOM':['Starlight Slalom','Drift Corridor','Orbital Weave'],'METEOR_BREAK':['Meteor Pop','Rock Rescue','Impact Patrol']}
    return GameMission(planet=planet,game_type=mode,name=rng.choice(titles[mode]),briefing={'SURFACE_RUN':'Both explorers jump low hurdles and duck high gates.','BEACON_RELAY':'Both pilots steer toward beacons and click to collect them.','RING_RACE':'Clear the ring track together. Jump low. Duck high.','ASTEROID_DODGE':'Dodge or break the asteroids. Bring your crew through safely.','ORBIT_SLALOM':'Weave through the debris. Keep your shared ship intact.','METEOR_BREAK':'Break the incoming rocks before they reach your ship.'}[mode],movements=[Movement(control=c,instruction=INSTRUCTIONS[c]) for c in MOVES[mode]],obstacle_count=rng.randint(6,9),time_limit_s=20,sync_boost=True)

async def generate_game(planet,recent=(),recent_names=()):
    mode=choose_mode(planet,recent)
    if not os.getenv('GEMINI_API_KEY'):return local_mission(planet,mode),'LOCAL · NO API KEY'
    try:
        from google import genai
        from google.genai import types
        async with genai.Client(api_key=os.environ['GEMINI_API_KEY'],http_options=types.HttpOptions(timeout=18000)).aio as client:
            async def request(model):
                return await client.models.generate_content(model=model,
                contents=f'''Create a fresh, easy two-player cooperative game at {planet}.
                This round's implemented game_type MUST be {mode}. Exactly these movements in order: {MOVES[mode]}.
                Each player has a joystick with a built-in PRESS button, tilt, remote SHAKE, and camera JUMP/DUCK. STEER means each player moves their own joystick left/right. PRESS means click their own joystick button. Both players MUST perform every listed primary movement in their own view; neither player only provides sync.
                Game rules: SURFACE_RUN = both players JUMP low hurdles and DUCK overhead gates along a planet-themed course, using fictional orbital platforms at gas giants; BEACON_RELAY = each pilot steers toward beacons and uses PRESS within 38 units to collect; ASTEROID_DODGE = two independent pilot lanes, dodge left/right or break rocks; RING_RACE = two players automatically run together on a constructed Saturn track, JUMP low hurdles and DUCK overhead gates, shared score; ORBIT_SLALOM = both pilots independently avoid their lane rocks with STEER only; METEOR_BREAK = automatically approach centered rocks and SHAKE them apart. SHAKE hits when rocks are within 38 units.
                Optional sync_boost is both players shaking within 1 second, giving a brief shield and speed boost. It is a bonus, not a required third movement.
                All games cooperate for one TEAM score. No individual winner. Describe 1-2 moves only with very short instructions. Name under 48 chars, briefing under 120 chars. 6-10 obstacles, time limit exactly 20 seconds.
                Be creative with planet-specific name and theme while preserving mechanics. Do not repeat recent names: {list(recent_names[-5:])}. Previous game types: {list(recent[-3:])}. Gas giants are orbital environments or fictional platforms. Return JSON only.''',
                config=types.GenerateContentConfig(response_mime_type='application/json',response_json_schema=GameMission.model_json_schema(),temperature=1.0))
            used_current=False
            try:
                configured=os.getenv('GEMINI_MODEL','gemini-flash-latest')
                response=await request(MODEL_ALIASES.get(configured,configured))
                used_current=configured in MODEL_ALIASES
            except Exception as exc:
                if getattr(exc,'code',None) not in (404,410):raise
                response=await request('gemini-flash-latest');used_current=True
                MODEL_ALIASES[os.getenv('GEMINI_MODEL','gemini-flash-latest')]='gemini-flash-latest'
            m=GameMission.model_validate_json(response.text).validate_planet(planet,mode)
            if m.name in recent_names[-3:]:raise ValueError('Repeated title')
            return m,('GEMINI · LIVE MISSION / CURRENT FLASH' if used_current else 'GEMINI · LIVE MISSION')
    except Exception as exc:
        # Keep keys and raw provider messages out of UI/logs.
        reason='RESPONSE REJECTED' if isinstance(exc,ValueError) else {429:'RATE LIMITED',403:'ACCESS DENIED',404:'MODEL UNAVAILABLE'}.get(getattr(exc,'code',None),'REQUEST FAILED')
        return local_mission(planet,mode),f'LOCAL · GEMINI {reason}'

class FlightGame:
    def __init__(self,simulated=True):
        self.simulated=simulated;self.task=None;self.generation=0;self.history={};self.names={};self.reset()
    def reset(self):
        if self.task:self.task.cancel()
        self.generation+=1;self.phase='READY';self.age=0.;self.world_time=0.;self.planet=None;self.mission=None;self.source=''
        self.players=[dict(x=0.,y=0.,yaw=0.,pitch=.065,distance=0.,health=100,jump=0.,duck=False) for _ in range(2)]
        self.axes=[[0.,0.],[0.,0.]];self.input_at=[-10.,-10.];self.shakes=[-10.,-10.];self.last_shake=[-10.,-10.]
        self.ship=[0.,0.,0.];self.roll=0.;self.speed=0.;self.travel=0.;self.team_score=0;self.health=100;self.boost=0.;self.boost_cooldown=0.
        self.transfer_from=[0.,0.,0.];self.obstacles=[];self.winner='NONE';self.event='READY';self.event_id=0;self.damage_flash=0.
    def emit(self,text):self.event=text;self.event_id+=1
    def transition(self,phase):self.phase=phase;self.age=0.
    def targets(self):
        result=[]
        for name,x,y,z in DESTINATIONS:
            dx,dy,dz=x-self.ship[0],y-self.ship[1],z-self.ship[2]
            result.append(dict(planet=name,position=[x,y,z],yaw=math.atan2(dx,-dz),pitch=math.atan2(dy,math.hypot(dx,dz)),distance=round(math.sqrt(dx*dx+dy*dy+dz*dz),1)))
        return result
    def target(self,i=0):
        p=self.players[0];angle=lambda t:abs(math.atan2(math.sin(t['yaw']-p['yaw']),math.cos(t['yaw']-p['yaw'])))
        t=min(self.targets(),key=lambda t:angle(t)**2+(t['pitch']-p['pitch'])**2)
        return t['planet'] if angle(t)<.18 and abs(t['pitch']-p['pitch'])<.4 and t['distance']<165 and self.travel>20 else None
    async def generate(self,planet,version):
        m,source=await generate_game(planet,self.history.get(planet,[]),self.names.get(planet,[]))
        if version!=self.generation:return
        self.mission=m;self.source=source
        self.history.setdefault(planet,[]).append(m.game_type);self.names.setdefault(planet,[]).append(m.name)
        self.history[planet]=self.history[planet][-8:];self.names[planet]=self.names[planet][-8:]
    def command(self,line):
        parts=line.split(',')
        if parts[0]!='FLIGHT':raise ValueError('Invalid flight command')
        if not self.simulated:raise ValueError('Computer demo mode required')
        if line=='FLIGHT,RESET':self.reset();return
        if line=='FLIGHT,EXPLORE':
            if self.phase=='RESULTS':
                self.mission=None;self.speed=0.;self.axes=[[0.,0.],[0.,0.]];self.transition('NAVIGATION')
            return
        if line=='FLIGHT,LAUNCH':
            if self.phase=='READY':self.transition('LAUNCH');self.emit('LEAVING EARTH')
            return
        if line=='FLIGHT,REGENERATE':
            if self.phase in ('BRIEFING','RESULTS'):
                if self.task and not self.task.done():return
                self.mission=None;self.transition('GENERATING');self.task=asyncio.create_task(self.generate(self.planet,self.generation))
            return
        if len(parts)<3 or parts[1] not in ('P1','P2'):raise ValueError('Invalid player')
        i=int(parts[1][1])-1;p=self.players[i];action=parts[2]
        if action=='AXIS' and len(parts)==5:
            x,y=map(float,parts[3:])
            if not all(math.isfinite(v) and -1<=v<=1 for v in (x,y)):raise ValueError('Axes must be normalized')
            self.axes[i]=[x,y];self.input_at[i]=self.world_time;return
        if len(parts)!=3:raise ValueError('Invalid action')
        if action=='SELECT':
            if self.phase=='MISSION':action='PRESS'
        if action=='SELECT':
            if i!=0:return
            if self.phase=='READY':self.command('FLIGHT,LAUNCH')
            elif self.phase=='NAVIGATION':
                planet=self.target()
                if planet:
                    self.planet=planet;self.transfer_from=list(self.ship);self.transition('TRAVEL');self.emit(f'{planet} LOCKED')
                    self.task=asyncio.create_task(self.generate(planet,self.generation))
                else:self.emit('P1 F · THRUST / P2 ← → · TURN')
            elif self.phase=='BRIEFING' and self.mission:self.start_mission()
            elif self.phase=='RESULTS':self.reset()
            return
        if action not in ('JUMP','DUCK_ON','DUCK_OFF','SHAKE','PRESS','UPWARD_FLICK'):raise ValueError('Unsupported action')
        if action=='DUCK_OFF':p['duck']=False;return
        if self.phase!='MISSION':return
        moves=MOVES[self.mission.game_type]
        if action=='JUMP' and 'JUMP' in moves and p['jump']<=0:p['jump']=.85
        elif action=='DUCK_ON' and 'DUCK' in moves:p['duck']=True
        elif action in ('SHAKE','PRESS') and self.world_time-self.last_shake[i]>.25:
            self.last_shake[i]=self.world_time
            if action=='SHAKE':self.shakes[i]=self.world_time
            if action=='SHAKE' and self.mission.sync_boost and self.boost_cooldown<=0 and min(self.shakes)>0 and abs(self.shakes[0]-self.shakes[1])<=1:
                self.boost=1.6;self.boost_cooldown=5.;self.shakes=[-10.,-10.];self.team_score+=20;self.emit('TOGETHER! +20 · SHIELD BOOST')
            if action in moves:
                nearby=[o for o in self.obstacles if not o['destroyed_by'][i] and not o['passed'][i] and 0<o['z']-p['distance']<38 and abs(o['x']-p['x'])<2.2]
                if nearby:
                    min(nearby,key=lambda o:o['z'])['destroyed_by'][i]=True;self.team_score+=25;self.emit(f'P{i+1} · +25')
    def start_mission(self):
        self.transition('MISSION');self.shakes=[-10.,-10.];self.health=100;self.boost=0;self.boost_cooldown=0;self.team_score=0
        for p in self.players:p.update(x=0.,y=0.,distance=0.,health=100,jump=0.,duck=False)
        rng=random.Random(self.mission.name+str(self.generation));self.obstacles=[]
        for n in range(self.mission.obstacle_count):
            race=self.mission.game_type in ('RING_RACE','SURFACE_RUN');kind=('HURDLE','GATE')[n%2] if race else ('BEACON' if self.mission.game_type=='BEACON_RELAY' else 'ROCK')
            x=0. if race or self.mission.game_type=='METEOR_BREAK' else rng.choice([-2.7,0.,2.7])
            self.obstacles.append(dict(id=n,x=x,y=0.,z=30.+n*18,kind=kind,destroyed=False,destroyed_by=[False,False],passed=[False,False]))
        self.emit('LET’S GO!')
    def tick(self,dt):
        remaining=min(max(dt,0.),.25)
        while remaining>1e-8:
            step=min(1/60,remaining);self._step(step);remaining-=step
    def _step(self,dt):
        self.world_time+=dt
        if self.phase not in ('READY','RESULTS','BRIEFING'):self.age+=dt
        self.damage_flash=max(0.,self.damage_flash-dt)
        self.boost=max(0.,self.boost-dt);self.boost_cooldown=max(0.,self.boost_cooldown-dt)
        axes=[self.axes[i] if self.world_time-self.input_at[i]<.4 else [0.,0.] for i in range(2)]
        if self.phase=='LAUNCH':
            self.ship[1]=self.age*2;self.ship[2]=-self.age*3
            if self.age>=5:self.transition('NAVIGATION');self.emit('P1 F · THRUST / P2 ← → · TURN')
        if self.phase=='NAVIGATION':
            pilot=self.players[0];pilot['yaw']=(pilot['yaw']+axes[1][0]*dt*.65+math.pi)%(2*math.pi)-math.pi
            self.ship[1]+=axes[0][1]*dt*18
            desired=max(0.,axes[0][0])*34
            self.speed+=(desired-self.speed)*min(1,dt*2.5)
            # Actual translation through world space: all planets, stars and dust parallax.
            step=self.speed*dt;self.ship[0]+=math.sin(pilot['yaw'])*step;self.ship[2]-=math.cos(pilot['yaw'])*step;self.travel+=step
            if any(t['distance']<(42 if t['planet']=='EARTH' else 30) for t in self.targets()):
                self.ship[0]-=math.sin(pilot['yaw'])*step;self.ship[2]+=math.cos(pilot['yaw'])*step;self.speed=0.
            self.players[1]['yaw']=pilot['yaw']
        if self.phase in ('LAUNCH','NAVIGATION','TRAVEL'):
            self.roll=max(-.32,min(.32,self.roll+dt*(.065*math.sin(self.world_time*1.1)+.02-axes[1][1]*.5)))
        if self.phase=='TRAVEL':
            dest=next(t for t in DESTINATIONS if t[0]==self.planet);t=min(1,self.age/4);smooth=t*t*(3-2*t)
            end=[dest[1],dest[2]-3,dest[3]+55]
            self.ship=[a+(b-a)*smooth for a,b in zip(self.transfer_from,end)]
            yaw=self.players[0]['yaw'];self.players[0]['yaw']=yaw*(1-min(1,dt*2));self.players[1]['yaw']=self.players[0]['yaw']
            if self.age>=4 and self.mission:self.transition('BRIEFING');self.emit('MISSION READY')
        if self.phase=='GENERATING' and self.mission:self.transition('BRIEFING')
        if self.phase!='MISSION':return
        mode=self.mission.game_type;race=mode in ('RING_RACE','SURFACE_RUN')
        for i,p in enumerate(self.players):
            if 'STEER' in MOVES[mode]:p['x']=max(-4.,min(4.,p['x']+axes[i][0]*dt*5))
            p['jump']=max(0.,p['jump']-dt)
            p['distance']+=dt*(19 if self.boost>0 else 12)
            for o in self.obstacles:
                if o['passed'][i] or o['destroyed_by'][i] or o['z']>p['distance']+6:continue
                o['passed'][i]=True
                if o['kind']=='BEACON':continue
                hit=(p['jump']<=0 if o['kind']=='HURDLE' else not p['duck'] if o['kind']=='GATE' else abs(o['x']-p['x'])<1.5)
                if hit and self.boost<=0:
                    self.health=max(0,self.health-8);self.damage_flash=.35;self.emit('JUMP!' if o['kind']=='HURDLE' else 'DUCK!' if o['kind']=='GATE' else 'WATCH THE ROCKS!')
                else:self.team_score+=10;self.emit('CLEAR! +10')
        for p in self.players:p['health']=self.health
        finish=30+(self.mission.obstacle_count-1)*18
        if self.health<=0 or self.age>=self.mission.time_limit_s:
            success=self.players[0]['distance']>=finish and self.health>0
            self.winner='TEAM' if success else 'NONE'
            if success:self.team_score+=100
            self.transition('RESULTS');self.emit('TEAM MISSION COMPLETE! +100' if success else 'TRY AGAIN, CREW')
    def snapshot(self):
        return dict(ship=self.ship,team_score=self.team_score,health=self.health,boost=self.boost,boost_cooldown=self.boost_cooldown,damage_flash=self.damage_flash,roll=round(self.roll,4),speed=round(self.speed,1),travel=round(self.travel,2),phase=self.phase,age=round(self.age,2),planet=self.planet,players=self.players,targets=self.targets(),locked=[self.target(),self.target()],mission=self.mission.model_dump() if self.mission else None,source=self.source,obstacles=self.obstacles,winner=self.winner,event=self.event,event_id=self.event_id,authority='COMPUTER DEMO')
