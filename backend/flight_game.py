"""Shared game authority for keyboard testing and physical remotes."""
import asyncio
import math
import os
import random
import logging
from gemini_runtime import cooldown_remaining, record_failure
from game_timing import (COUNTDOWN_SECONDS, WARNING_LEAD, RESPONSE_WINDOW, INPUT_GRACE, TRACK_SPEED, BODY_MODES, BODY_KINDS, encounter_times, timing_snapshot)
from flight_science_facts import SCIENCE_QUESTIONS
from targeting import crosshair_target
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

# Compact demo destinations. Units intentionally do not represent real solar distances.
DESTINATIONS=[('MARS',-110.,14.,-190.),('SATURN',0.,14.,-220.),('JUPITER',110.,14.,-200.),('NEPTUNE',200.,14.,-160.),('MERCURY',-205.,14.,-100.),('VENUS',-175.,14.,-165.),('URANUS',205.,14.,-40.),('EARTH',-55.,14.,-200.)]
MODEL_ALIASES={}
logger = logging.getLogger(__name__)
# Curated, stable NASA-backed facts. Gemini may theme games, never invent the science.
PLANET_FACTS={
 'MERCURY':{'fact':'Mercury has almost no atmosphere to trap heat, so the temperature swings dramatically between day and night.','why':'Watch the extreme landscape while you race across craters.','url':'https://science.nasa.gov/mercury/facts/'},
 'VENUS':{'fact':'Venus is the hottest planet in our solar system because its thick atmosphere traps heat.','why':'Find shelter from hostile surface conditions.','url':'https://science.nasa.gov/venus/venus-facts/'},
 'EARTH':{'fact':'Earth is the only planet in our solar system known to have liquid oceans on its surface.','why':'Protect habitats and collect samples as an explorer.','url':'https://science.nasa.gov/earth/facts/'},
 'MARS':{'fact':'The iron in Martian dust has oxidized, giving Mars its rusty red color.','why':'Study the mineral-rich ground and dodge dust storms.','url':'https://science.nasa.gov/mars/facts/'},
 'JUPITER':{'fact':'Jupiter’s Great Red Spot is a giant storm that has raged for centuries.','why':'Navigate dangerous debris in this giant planet’s orbital region.','url':'https://science.nasa.gov/jupiter/jupiter-facts/'},
 'SATURN':{'fact':'Saturn’s famous rings contain countless pieces of ice and rock.','why':'Leap and duck between icy obstacles in a fictional ring race.','url':'https://science.nasa.gov/saturn/facts/'},
 'URANUS':{'fact':'Uranus rotates almost on its side compared with other planets.','why':'Stay oriented while navigating a distant ice giant.','url':'https://science.nasa.gov/uranus/facts/'},
 'NEPTUNE':{'fact':'Neptune has some of the fastest winds measured in our solar system.','why':'Steer carefully through a fast-moving orbital challenge.','url':'https://science.nasa.gov/neptune/neptune-facts/'}
}
# Additional curated, stable NASA-sourced facts for revisiting a planet.
# Science comes from this checked catalogue, not Gemini output. Fact rotation
# is independent of game-family rotation and persists across in-game resets.
EXTRA_PLANET_FACTS={
 'MERCURY':[
  'Mercury travels around the Sun in just 88 Earth days.',
  'Some permanently shadowed polar craters on Mercury contain water ice.'],
 'VENUS':[
  'Venus rotates in the opposite direction to most of the planets.',
  'The clouds of Venus contain droplets of sulfuric acid.'],
 'EARTH':[
  'Earth has one natural moon.',
  'Earth’s magnetic field helps protect our planet from charged particles from the Sun.'],
 'MARS':[
  'Mars has two small moons, Phobos and Deimos.',
  'Olympus Mons on Mars is the largest known volcano in the solar system.'],
 'JUPITER':[
  'Jupiter is the largest planet in our solar system.',
  'Jupiter’s moon Europa has strong evidence of a salty ocean beneath its ice.'],
 'SATURN':[
  'Saturn’s moon Titan has lakes and seas of liquid methane and ethane.',
  'Saturn is a gas giant without a solid surface for astronauts to stand on.'],
 'URANUS':[
  'Methane in Uranus’s atmosphere contributes to its blue-green color.',
  'Uranus takes about 84 Earth years to complete one orbit of the Sun.'],
 'NEPTUNE':[
  'Neptune is the most distant planet from the Sun in our solar system.',
  'Neptune’s large moon Triton orbits in the opposite direction of Neptune’s rotation.']
}

def choose_planet_fact(planet,recent=()):
    facts=[PLANET_FACTS[planet]['fact']]+EXTRA_PLANET_FACTS[planet]
    pool=[fact for fact in facts if fact not in recent[-2:]] or facts
    return dict(fact=random.SystemRandom().choice(pool),url=PLANET_FACTS[planet]['url'])

# Surface adventures only appear on rocky planets; gas giants remain orbital.
ROCKY_PLANETS=('MERCURY','VENUS','EARTH','MARS')
SURFACE_MODES=('SURFACE_RUN','CRATER_LEAP','SAMPLE_HUNT','STORM_SHELTER')
CHALLENGE_STYLES=('STANDARD',)
# These layouts are real game-rule variants, not AI-only changes to the title.
STYLE_HELP={'STANDARD':'15 seconds. Score points by completing the mission objective.'}
MODE_LESSONS={
 'SURFACE_RUN':'Cross a fictional expedition training course to explore local terrain.',
 'CRATER_LEAP':'Navigate the rocky landscape using your body jump and upward remote flick.',
 'SAMPLE_HUNT':'Recover fictional scientific samples to investigate this planet.',
 'STORM_SHELTER':'Keep a fictional research shelter powered despite hazardous conditions.',
 'ASTEROID_DODGE':'Steer through a fictional orbiting rock field; real impacts are dangerous for spacecraft.',
 'RING_RACE':'Race above Saturn through a fictional track inspired by its rings of ice and rock.',
 'ORBIT_SLALOM':'Practice the precise steering that spacecraft navigation requires.',
 'METEOR_BREAK':'Clear fictional debris before it can hit your spacecraft.',
 'BEACON_RELAY':'Find and activate fictional orbital navigation beacons.',
 'RELAY_REPAIR':'Aim at fictional damaged orbiting relays, then shake to restore them.',
 'GRAVITY_SLING':'Gravity assists use planetary gravity to change spacecraft trajectories; fictional gates reward precise flick timing.',
 'SCIENCE_QUIZ':'Choose a correct answer from a pre-verified NASA-backed science question.'}

MODES=('ASTEROID_DODGE','RING_RACE','ORBIT_SLALOM','METEOR_BREAK','BEACON_RELAY','RELAY_REPAIR','GRAVITY_SLING')+SURFACE_MODES
MOVES={'SURFACE_RUN':('JUMP','DUCK'),'CRATER_LEAP':('JUMP','FLICK'),'SAMPLE_HUNT':('TILT','PRESS'),'STORM_SHELTER':('DUCK','SHAKE'),'ASTEROID_DODGE':('STEER','SHAKE'),'RING_RACE':('JUMP','DUCK'),'ORBIT_SLALOM':('STEER',),'METEOR_BREAK':('SHAKE',),'BEACON_RELAY':('STEER','PRESS'),'RELAY_REPAIR':('TILT','SHAKE'),'GRAVITY_SLING':('STEER','FLICK'),'SCIENCE_QUIZ':('TILT','PRESS')}
SCIENCE_MODES=frozenset(('SCIENCE_QUIZ','SAMPLE_HUNT','STORM_SHELTER','RELAY_REPAIR','BEACON_RELAY'))
ACTION_MODES=frozenset(MODES)-SCIENCE_MODES

INSTRUCTIONS={'PRESS':'Press your remote button when a sample or beacon is near.','FLICK':'Flick your remote upward to clear the tall gaps.','TILT':'Tilt your remote left/right to move toward each sample.','STEER':'Move left or right to avoid the rocks.','JUMP':'Tilt your remote up to jump over the low barriers.','DUCK':'Push the joystick forward to duck under the high barriers.','SHAKE':'Shake your remote when the target is in range.'}

class Movement(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    control: Literal['STEER','TILT','JUMP','DUCK','SHAKE','PRESS','FLICK']
    instruction: str=Field(min_length=4,max_length=85)
class GameMission(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    planet: Literal['MERCURY','VENUS','EARTH','MARS','JUPITER','SATURN','URANUS','NEPTUNE']
    game_type: Literal['ASTEROID_DODGE','RING_RACE','ORBIT_SLALOM','METEOR_BREAK','BEACON_RELAY','RELAY_REPAIR','GRAVITY_SLING','SCIENCE_QUIZ','SURFACE_RUN','CRATER_LEAP','SAMPLE_HUNT','STORM_SHELTER']
    name: str=Field(min_length=3,max_length=48)
    briefing: str=Field(min_length=5,max_length=120)
    challenge_style: Literal['STANDARD']
    movements: list[Movement]=Field(min_length=1,max_length=2)
    obstacle_count: int=Field(ge=4,le=10)
    time_limit_s: int=Field(ge=15,le=15)
    sync_boost: bool=True
    # AI can choose one implemented, gameplay-visible encounter pattern.
    event_pattern: Literal['SCATTERED','ALTERNATING','CENTER_OUT']='SCATTERED'

    def validate_planet(self,planet,expected_mode=None,expected_style=None,allowed_modes=None):
        if self.planet!=planet:raise ValueError('Wrong planet')
        if self.game_type=='RING_RACE' and planet!='SATURN':raise ValueError('Ring game requires Saturn')
        if self.game_type in SURFACE_MODES and planet not in ROCKY_PLANETS:raise ValueError('Surface adventure requires rocky planet')
        if expected_mode and self.game_type!=expected_mode:raise ValueError('Game type not selected for this round')
        if allowed_modes is not None and self.game_type not in allowed_modes:raise ValueError('Mode not allowed for this round')
        if expected_style and self.challenge_style!=expected_style:raise ValueError('Challenge layout not selected for this round')
        if [m.control for m in self.movements]!=list(MOVES[self.game_type]):raise ValueError('Unsupported movement set')
        if self.game_type=='SCIENCE_QUIZ' and self.obstacle_count!=5:raise ValueError('Science quiz must have five questions')
        if self.game_type in BODY_MODES and self.obstacle_count!=4:raise ValueError('Body games require four spaced encounters')
        return self


class MissionConcept(BaseModel):
    """Gemini selects a real implemented game family and its creative framing.

    All controls, scoring rules, scientific answers, game duration and arena
    are assigned by the backend; model output cannot inject code or new input.
    """
    model_config=ConfigDict(extra='forbid',strict=True)
    game_type: str=Field(min_length=4,max_length=30)
    name: str=Field(min_length=3,max_length=48)
    briefing: str=Field(min_length=8,max_length=120)
    event_pattern: Literal['SCATTERED','ALTERNATING','CENTER_OUT']


def choose_mode(planet,recent=(),global_recent=()):
    """Rotate game families across planets, while respecting physical setting and the last two local games."""
    available=[m for m in MODES if (m!='RING_RACE' or planet=='SATURN') and (m not in SURFACE_MODES or planet in ROCKY_PLANETS)]
    possible=[m for m in available if m not in recent[-2:]] or available
    # Prefer families unseen in the last four rounds on ANY planet. Even when
    # the player switches planets every round, the catalogue doesn't loop.
    fresh=[m for m in possible if m not in global_recent[-4:]]
    pool=fresh or [m for m in possible if m!=global_recent[-1]] or possible
    # A shuffle-bag approach: pick the least played family, randomizing ties.
    lowest=min(global_recent[-15:].count(m) for m in pool)
    least_used=[m for m in pool if global_recent[-15:].count(m)==lowest]
    return random.SystemRandom().choice(least_used)



def eligible_gemini_modes(planet, recent=(), global_recent=(), forced_mode=None):
    """Return a safe AI choice set; alternate arcade/science where possible.

    The model picks the *actual mechanics family* from this list, and Python
    subsequently validates the entire structured mission before running it.
    """
    if planet not in PLANET_FACTS:raise ValueError('Unknown planet')
    available=[m for m in MODES if (m!='RING_RACE' or planet=='SATURN')
               and (m not in SURFACE_MODES or planet in ROCKY_PLANETS)]
    if forced_mode:
        if forced_mode not in available:raise ValueError('Invalid forced game')
        return [forced_mode]
    # Alternating educational and arcade rounds prevents three consecutive
    # obstacle races even when Gemini chooses the family each time.
    last=global_recent[-1] if global_recent else None
    requested=ACTION_MODES if last in SCIENCE_MODES else SCIENCE_MODES
    fresh=[m for m in available if m not in recent[-2:] and m not in global_recent[-4:]]
    pool=[m for m in fresh if m in requested] or fresh or [m for m in available if m not in recent[-2:]]
    return pool or available

# Allowed modes are different, implemented game loops (not just new titles).
MODE_RULES={
    'SCIENCE_QUIZ':'Live fact challenge: tilt joystick/remote among A, B, C and PRESS to answer five verified NASA questions. The backend chooses the correct answers.',
    'SAMPLE_HUNT':'First-person rocky surface research: TILT to reach 3 samples and PRESS to collect them.',
    'STORM_SHELTER':'Push the joystick forward to duck beneath a dust front; shake to restart field generators.',
    'RELAY_REPAIR':'Orbital engineering: TILT to align with damaged relay hardware, SHAKE to repair.',
    'BEACON_RELAY':'Orbital signal chase: STEER toward separate beacons, PRESS to activate.',
    'SURFACE_RUN':'First-person rocky terrain hurdles: jump low obstacles, duck high obstacles.',
    'CRATER_LEAP':'First-person crater crossing: tilt your remote up to jump over pits; flick upward at ledges.',
    'ASTEROID_DODGE':'Space rock survival: STEER to evade; SHAKE to break oncoming debris.',
    'RING_RACE':'Saturn orbital ring course: JUMP and DUCK past icy obstacles (not on Saturn surface).',
    'ORBIT_SLALOM':'Fast orbital steering contest: STEER to avoid moving barriers.',
    'METEOR_BREAK':'Reaction contest: SHAKE to smash approaching debris.',
    'GRAVITY_SLING':'Orbital gravity training: STEER through rings and FLICK at each gate.'
}
def choose_style(recent_styles=()):
    return 'STANDARD'  # Removed Precision/Final Rush gameplay and UI.

def local_mission(planet,mode=None,style='STANDARD',recent_names=()):
    mode=mode or ('RING_RACE' if planet=='SATURN' else 'ASTEROID_DODGE')
    rng=random.SystemRandom()
    titles={'SURFACE_RUN':['Outpost Dash','Horizon Hurdles','Terrain Sprint'],
            'CRATER_LEAP':['Crater Crossing','Lava Fissure Leap','Gravity Gaps'],
            'SAMPLE_HUNT':['Geologist Quest','Rare Mineral Recovery','Science Sample Hunt'],
            'STORM_SHELTER':['Storm Shield Rescue','Outpost Power-Up','Dustfront Defense'],
            'BEACON_RELAY':['Signal Sweep','Beacon Rescue','Starlight Collectors'],
            'RELAY_REPAIR':['Relay Rescue','Orbital Repair Crew','Signal Salvage'],
            'GRAVITY_SLING':['Gravity Gate Dash','Slingshot Sprint','Orbital Boost Race'],
            'SCIENCE_QUIZ':['Research Lab Faceoff','Planet Science Challenge','Astronomy Showdown'],
            'RING_RACE':['Icefall Run','Ring Relay','Frostline Dash'],
            'ASTEROID_DODGE':['Debris Dash','Orbit Breakers','Asteroid Alley'],
            'ORBIT_SLALOM':['Starlight Slalom','Drift Corridor','Orbital Weave'],
            'METEOR_BREAK':['Meteor Pop','Rock Rescue','Impact Patrol']}
    name_choices=[f'{planet.title()} {t}' for t in titles[mode]]
    eligible=[t for t in name_choices if t not in recent_names[-8:]] or name_choices
    name=rng.choice(eligible)
    briefings={'SURFACE_RUN':'Race over the planet terrain: jump low hazards, duck under high ones.',
            'CRATER_LEAP':'Jump over craters and flick upward to clear steep ridges.',
            'SAMPLE_HUNT':'Collect striped research samples. Leave unmarked rocks behind.',
            'STORM_SHELTER':'Duck beneath hazard fronts and shake to charge generators.',
            'BEACON_RELAY':'Steer toward beacons and press to activate them.',
            'RELAY_REPAIR':'Tilt to align with damaged orbital relays; shake to restore their signals.',
            'GRAVITY_SLING':'Steer toward each gravity gate and flick upward while crossing to score.',
            'SCIENCE_QUIZ':'Tilt left / center / right to select a scientific answer; press to submit.',
            'RING_RACE':'Race over Saturn’s fictional icy track: jump low and duck high.',
            'ASTEROID_DODGE':'Steer to avoid rocks or shake to break them.',
            'ORBIT_SLALOM':'Steer through the center of each navigation gate.',
            'METEOR_BREAK':'Shake to clear incoming rocks before impact.'}
    return GameMission(planet=planet,game_type=mode,name=name,briefing=briefings[mode],
                       movements=[Movement(control=c,instruction=('Steer through the illuminated gate centers.' if mode=='ORBIT_SLALOM' else 'Tilt toward striped research samples; avoid plain decoys.' if mode=='SAMPLE_HUNT' and c=='TILT' else 'Press to collect a striped sample when it is near.' if mode=='SAMPLE_HUNT' and c=='PRESS' else 'Tilt to select answer A, B, or C.' if mode=='SCIENCE_QUIZ' and c=='TILT' else 'Press your button to submit your answer.' if mode=='SCIENCE_QUIZ' and c=='PRESS' else INSTRUCTIONS[c])) for c in MOVES[mode]],
                       obstacle_count=4 if mode in BODY_MODES else 5 if mode in ('SCIENCE_QUIZ','SAMPLE_HUNT','BEACON_RELAY','RELAY_REPAIR','GRAVITY_SLING') else 7,time_limit_s=15,
                       challenge_style=style,sync_boost=mode in ('RELAY_REPAIR','BEACON_RELAY'))

async def generate_game(planet,recent=(),recent_names=(),global_recent=(),style_history=(),lesson=None,forced_mode=None):
    """Gemini creates the mission concept AND selects its implemented mechanics.

    The server owns controls, scoring, challenge duration, curated science and
    planet restrictions. This means AI-generated missions are *playable* with
    both physical remotes and can be previewed with the keyboard.
    """
    allowed=eligible_gemini_modes(planet,recent,global_recent,forced_mode)
    lesson=lesson or choose_planet_fact(planet)

    def fallback():
        # Rotate the same science/arcade category even if Gemini is offline.
        # Choosing by recent usage avoids repeatedly cycling through one family.
        tally={mode:global_recent[-20:].count(mode) for mode in allowed}
        selected=forced_mode or random.SystemRandom().choice(
            [m for m in allowed if tally[m]==min(tally.values())])
        return local_mission(planet,selected,'STANDARD',recent_names)

    if not os.getenv('GEMINI_API_KEY'):
        return fallback(),'LOCAL · NO API KEY'
    if cooldown_remaining()>0:
        return fallback(),'LOCAL · GEMINI RATE LIMITED (COOLDOWN)'
    try:
        from google import genai
        from google.genai import types
        specifications='\n'.join(f'- {m}: {MODE_RULES[m]} Controls: {", ".join(MOVES[m])}.' for m in allowed)
        prompt=f"""Create ONE lively, original 15-second head-to-head SPACE ODYSSEY challenge for the planet {planet}.
        Two players compete individually, with one remote each. Tilt up to jump and push the joystick forward to duck.
        You CHOOSE THE PLAYABLE GAME FAMILY from ONLY these implemented modes:
        {specifications}
        Select game_type EXACTLY from: {allowed}.
        Mix actual hands-on educational challenges with fast arcade contests across rounds. Make the chosen
        objective meaningful: science modes collect samples, restore research relays or answer real questions;
        arcade modes reward successful movement, not empty button pressing. The real mechanics shown above
        cannot be changed. Player 1 and Player 2 must have the same fair objective.
        Remote controls are joystick steering, physical tilt up for jump, forward joystick for duck, button press, shake and upward flick. Never ask for extra input devices, voice, mouse, hovering, lasers or new controls.
        Curated NASA fact for the educational briefing (you may quote this fact, no invented claims):
        {lesson['fact']}
        Use the real fact as story inspiration where it fits. Do not pretend fictional missions are historical
        NASA operations. Rocky surface research is for Mercury, Venus, Earth, Mars only.
        Saturn, Jupiter, Uranus and Neptune have no solid ground on which this game could be played.
        Never create quizzes or multiple-choice questions. Teach science through physical action and exploration.
        Give a fresh memorable name and a punchy, actionable briefing under 120 characters.
        Choose an encounter pattern: SCATTERED, ALTERNATING, or CENTER_OUT.
        Recent game types: {list(global_recent[-5:])}; recent titles: {list(recent_names[-8:])}.
        Return just the four JSON fields from the supplied schema."""
        async with genai.Client(api_key=os.environ['GEMINI_API_KEY'],http_options=types.HttpOptions(timeout=18000)).aio as client:
            async def request(model):
                return await client.models.generate_content(
                    model=model,contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type='application/json',
                           response_json_schema=MissionConcept.model_json_schema(),temperature=.85))
            # Use a currently documented stable Flash model by default.
            # Older .env configurations may still name a retired model.
            configured=os.getenv('GEMINI_MODEL','gemini-3.8-flash')
            current=MODEL_ALIASES.get(configured,configured)
            try:
                response=await request(current)
            except Exception as exc:
                if getattr(exc,'code',None) not in (404,410) or current=='gemini-3.8-flash':
                    raise
                current='gemini-3.8-flash'
                response=await request(current)
                MODEL_ALIASES[configured]=current
        concept=MissionConcept.model_validate_json(response.text)
        if concept.game_type not in allowed:
            raise ValueError('Gemini chose an ineligible game family')
        if concept.name.casefold() in (n.casefold() for n in recent_names[-8:]):
            raise ValueError('Gemini repeated a recent title')
        # Convert the concept to server-owned controls, obstacles and 15-second rules.
        mission=local_mission(planet,concept.game_type,'STANDARD',recent_names)
        mission.name=concept.name
        mission.briefing=concept.briefing
        mission.event_pattern=concept.event_pattern
        mission.validate_planet(planet,expected_mode=forced_mode,allowed_modes=allowed)
        return mission,'GEMINI · LIVE CHALLENGE'
    except Exception as exc:
        # Never expose credentials, request payloads or provider error text.
        record_failure(exc)
        code=getattr(exc,'code',None)
        if isinstance(exc, (ImportError, ModuleNotFoundError)):
            reason='SDK NOT INSTALLED'
        elif isinstance(exc, ValueError):
            reason='RESPONSE REJECTED'
        elif isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
            reason='TIMED OUT'
        else:
            reason={400:'INVALID REQUEST',401:'INVALID API KEY',403:'ACCESS DENIED',
                    404:'MODEL UNAVAILABLE',410:'MODEL RETIRED',
                    429:'RATE LIMITED'}.get(code,'REQUEST FAILED')
        logger.warning('Flight Gemini fallback: %s (exception=%s, http_code=%s)',
                       reason,type(exc).__name__,code)
        return fallback(),f'LOCAL · GEMINI {reason}'

class FlightGame:
    def __init__(self,simulated=True):
        self.controller_signs=[[(-1. if os.getenv(f'P{i}_{axis}_SIGN','1')=='-1' else 1.) for axis in ('FORWARD','STEER','TILT')] for i in (1,2)];self.simulated=simulated;self.task=None;self.generation=0;self.history={};self.global_history=[];self.style_history=[];self.fact_history={};self.names={};self.reset()
    def reset(self):
        if self.task:self.task.cancel()
        self.generation+=1;self.phase='READY';self.age=0.;self.world_time=0.;self.planet=None;self.mission=None;self.source='';self.education=None
        self.planet_results={};self.visited=[];self.mpu=[None,None]
        self.players=[dict(x=0.,y=0.,yaw=0.,pitch=0.,distance=0.,health=100,score=0,jump=0.,flick=0.,duck=False,samples=0,chargers=0,selection=1) for _ in range(2)]
        # Separate sources: the browser sends neutral keyboard axes every 50 ms.
        # A live physical remote must never be overwritten by those idle packets.
        self.axes=[[0.,0.],[0.,0.]];self.input_at=[-10.,-10.]
        self.remote_axes=[[0.,0.],[0.,0.]];self.remote_input_at=[-10.,-10.];self.remote_tilt=[None,None]
        self.remote_raw=[[0.,0.,None],[0.,0.,None]];self.remote_packets=[0,0];self.remote_events=[None,None]
        # Per-action debounce and matched-action sync are independent of transport.
        # Keyboard, webcam and two eventual ESP32 remotes all use these same events.
        self.last_actions=[{},{}];self.sync_timestamps={};self.last_sync=-10.
        self.duck_sources=[set(),set()];self.jump_at=[-100.,-100.];self.flick_at=[-100.,-100.];self.total_scores=[0,0]
        self.ship=[-15.,14.,-120.];self.roll=0.;self.speed=0.;self.thrust_blocked=False;self.travel=0.;self.team_score=0;self.health=100;self.boost=0.;self.boost_cooldown=0.;self.sync_effect=''
        self.inspected=None;self.transfer_from=[0.,0.,0.];self.obstacles=[];self.winner='NONE';self.event='READY';self.event_id=0;self.damage_flash=0.
    def emit(self,text):self.event=text;self.event_id+=1
    def transition(self,phase):self.phase=phase;self.age=0.
    def targets(self):
        result=[]
        for name,x,y,z in DESTINATIONS:
            dx,dy,dz=x-self.ship[0],y-self.ship[1],z-self.ship[2]
            result.append(dict(planet=name,position=[x,y,z],yaw=math.atan2(dx,-dz),pitch=math.atan2(dy,math.hypot(dx,dz)),distance=round(math.sqrt(dx*dx+dy*dy+dz*dz),1)))
        return result
    def selection(self):
        return crosshair_target(self.ship,self.players[0],self.targets(),self.travel)
    def target(self,i=0):
        t=self.selection()
        return t['id'] if t and t['kind']=='planet' and t['selectable'] else None
    async def generate(self,planet,version,forced_mode=None):
        lesson=choose_planet_fact(planet,self.fact_history.get(planet,[]))
        m,source=await generate_game(planet,self.history.get(planet,[]),self.names.get(planet,[]),self.global_history,self.style_history,lesson,forced_mode=forced_mode)
        if version!=self.generation:return
        self.mission=m;self.source=source;self.education=lesson
        self.fact_history.setdefault(planet,[]).append(lesson['fact'])
        self.fact_history[planet]=self.fact_history[planet][-8:]
        self.history.setdefault(planet,[]).append(m.game_type);self.names.setdefault(planet,[]).append(m.name)
        self.global_history=(self.global_history+[m.game_type])[-20:]
        self.style_history=(self.style_history+[m.challenge_style])[-8:]
        self.history[planet]=self.history[planet][-8:];self.names[planet]=self.names[planet][-8:]
    def active_axes(self):
        # Prefer physical controller readings while their data is fresh.
        # If disconnected, both devices safely decay to neutral after 0.4 s;
        # keyboard control remains available for testing/fallback.
        result=[]
        for i in range(2):
            if self.world_time-self.remote_input_at[i]<.4:
                remote=self.remote_axes[i]
                # Hardware packet convention: X is P1 forward/reverse, Y is
                # left/right stick or P2 roll/tilt. Mission movement is lateral;
                # route that same real horizontal sensor reading to the mission
                # lane axis, without changing flight/navigation behavior.
                if self.phase in ('COUNTDOWN','MISSION','RESULTS'):
                    lateral=self.remote_tilt[i] if self.remote_tilt[i] is not None and 'TILT' in MOVES[self.mission.game_type] else remote[1]
                    result.append([lateral,0.])
                else:
                    result.append([0.,self.remote_tilt[i]] if i==1 and self.remote_tilt[i] is not None else remote)
            elif self.world_time-self.input_at[i]<.4:
                result.append(self.axes[i])
            else:
                result.append([0.,0.])
        return result

    def command(self,line,source='keyboard'):
        parts=line.split(',')
        if parts[0]!='FLIGHT':raise ValueError('Invalid flight command')
        if source not in ('keyboard','remote','vision'):raise ValueError('Invalid input source')
        if line=='FLIGHT,RESET':self.reset();return
        if line=='FLIGHT,EXPLORE':
            if self.phase in ('RESULTS','BRIEFING','MISSION','COUNTDOWN','GENERATING','TRAVEL','ARRIVAL'):
                if self.task:self.task.cancel()
                self.generation+=1
                dest=next((t for t in DESTINATIONS if t[0]==self.planet),None)
                if dest:self.ship=[dest[1],dest[2],dest[3]+65]
                for p in self.players:p['yaw']=math.pi;p['pitch']=0.
                self.duck_sources=[set(),set()];self.roll=0.
                self.mission=None;self.speed=0.;self.axes=[[0.,0.],[0.,0.]];self.input_at=[-10.,-10.]
                self.remote_axes=[[0.,0.],[0.,0.]];self.remote_input_at=[-10.,-10.];self.remote_tilt=[None,None]
                self.transition('NAVIGATION')
            return
        if line=='FLIGHT,LAUNCH':
            if self.phase=='READY':self.transition('BOOT');self.emit('PREPARING FLIGHT')
            return
        if line=='FLIGHT,SURFACE_GAME':
            if self.phase in ('BRIEFING','RESULTS') and self.planet:
                if self.task and not self.task.done():return
                seen=self.history.get(self.planet,[])
                # Giant planets get an orbital course, never an imaginary surface.
                choices=(('SURFACE_RUN','CRATER_LEAP','STORM_SHELTER','SAMPLE_HUNT')
                         if self.planet in ROCKY_PLANETS else
                         ('RING_RACE',) if self.planet=='SATURN' else
                         ('ORBIT_SLALOM','GRAVITY_SLING','RELAY_REPAIR'))
                last=next((m for m in reversed(seen) if m in choices),None)
                mode=choices[(choices.index(last)+1)%len(choices)] if last else choices[0]
                self.mission=None;self.transition('GENERATING')
                self.task=asyncio.create_task(self.generate(self.planet,self.generation,mode))
            return
        if line=='FLIGHT,REGENERATE':
            if self.phase in ('BRIEFING','RESULTS'):
                if self.task and not self.task.done():return
                self.mission=None;self.transition('GENERATING');self.task=asyncio.create_task(self.generate(self.planet,self.generation))
            return
        if len(parts)<3 or parts[1] not in ('P1','P2'):raise ValueError('Invalid player')
        i=int(parts[1][1])-1;p=self.players[i];action=parts[2]
        if source=='remote' and action not in ('SENSORS','AXIS','MPU'):
            self.remote_events[i]={'action':action,'at':self.world_time}
        if action=='MPU' and source=='remote':
            if len(parts)!=10:raise ValueError('Invalid MPU packet')
            values=list(map(float,parts[3:]))
            if not all(math.isfinite(v) and abs(v)<=2000 for v in values) or values[0] not in (0,1):raise ValueError('Invalid MPU values')
            self.mpu[i]={'ok':bool(values[0]),'accel':values[1:4],'gyro':values[4:7],'at':self.world_time}
            return
        if action=='DISCONNECTED' and source=='remote':
            self.remote_input_at[i]=-100.;self.remote_axes[i]=[0.,0.];self.remote_tilt[i]=None;self.duck_sources[i].discard('remote');p['duck']=bool(self.duck_sources[i]);return
        if action=='SENSORS' and source=='remote' and len(parts)==6:
            throttle,steer,tilt=map(float,parts[3:])
            if not all(math.isfinite(v) and -1<=v<=1 for v in (throttle,steer,tilt)):raise ValueError('Invalid sensor state')
            self.remote_raw[i]=[throttle,steer,tilt];self.remote_packets[i]+=1
            signs=self.controller_signs[i];forward=throttle*signs[0];self.remote_axes[i]=[forward,steer*signs[1]];self.remote_tilt[i]=tilt*signs[2];self.remote_input_at[i]=self.world_time
            # During missions the forward stick is a held duck control. Keep
            # hysteresis so small center noise does not flicker DUCK on/off.
            if self.phase=='MISSION' and (forward>=.35 or ('remote' in self.duck_sources[i] and forward>.20)):
                self.duck_sources[i].add('remote')
            else:self.duck_sources[i].discard('remote')
            p['duck']=bool(self.duck_sources[i]);return
        if action=='AXIS' and len(parts)==5:
            x,y=map(float,parts[3:])
            if not all(math.isfinite(v) and -1<=v<=1 for v in (x,y)):raise ValueError('Axes must be normalized')
            if source=='remote':
                self.remote_raw[i]=[x,y,None];self.remote_packets[i]+=1
                self.remote_axes[i]=[x*self.controller_signs[i][0],y*self.controller_signs[i][1]];self.remote_tilt[i]=None;self.remote_input_at[i]=self.world_time
            else:
                self.axes[i]=[x,y];self.input_at[i]=self.world_time
            return
        if len(parts)!=3:raise ValueError('Invalid action')
        if action=='SELECT':
            if self.phase=='MISSION':action='PRESS'
        if action=='SELECT':
            if i!=0:return
            if self.phase=='READY':self.command('FLIGHT,LAUNCH')
            elif self.phase=='NAVIGATION':
                selected=self.selection()
                if selected and selected['kind']=='discovery':
                    self.inspected=selected['id'];self.emit('INSPECT '+selected['name']);return
                planet=self.target()
                if planet:
                    self.planet=planet;self.transfer_from=list(self.ship);self.transition('TRAVEL');self.emit(f'{planet} LOCKED')
                    self.task=asyncio.create_task(self.generate(planet,self.generation))
                else:self.emit('P1 · STEER TOWARD A PLANET AND MOVE FORWARD')
            elif self.phase=='BRIEFING' and self.mission:self.transition('COUNTDOWN');self.emit('GET READY')
            elif self.phase=='RESULTS':self.command('FLIGHT,EXPLORE')
            return
        if action not in ('JUMP','DUCK_ON','DUCK_OFF','SHAKE','PRESS','UPWARD_FLICK'):raise ValueError('Unsupported action')
        if action=='DUCK_OFF':
            self.duck_sources[i].discard(source)
            p['duck']=bool(self.duck_sources[i])
            return
        if action=='DUCK_ON':
            self.duck_sources[i].add(source)
            p['duck']=bool(self.duck_sources[i])
            return
        if self.phase!='MISSION' or self.age>=self.mission.time_limit_s:return
        moves=MOVES[self.mission.game_type]
        # Ignore auto-repeat / IMU jitter. DUCK_ON is an edge, not an every-frame event.
        if action=='DUCK_ON' and p['duck']:return
        if action=='JUMP' and ('JUMP' not in moves or p['jump']>0):return
        if action=='UPWARD_FLICK' and ('FLICK' not in moves or p['flick']>0):return
        now=self.world_time
        if now-self.last_actions[i].get(action,-100)<.23:return
        self.last_actions[i][action]=now
        if action=='JUMP':p['jump']=RESPONSE_WINDOW;self.jump_at[i]=self.age
        elif action=='UPWARD_FLICK':
            p['flick']=RESPONSE_WINDOW;self.flick_at[i]=self.age
            self.emit(f'P{i+1} · BOOST LEAP!')
        elif action=='DUCK_ON':p['duck']=True
        elif action=='PRESS' and self.mission.game_type=='SCIENCE_QUIZ':
            # Each question is a separate timed decision, not a forward-moving obstacle.
            current=next((o for o in self.obstacles if o['kind']=='QUESTION' and o['event_at']<=self.age<o['event_at']+2.3 and not o['passed'][i]),None)
            if current:
                current['passed'][i]=True
                choice=p['selection']
                if choice==current['answer']:
                    p['score']+=25;self.emit(f'P{i+1} · CORRECT! +25')
                else:self.emit(f'P{i+1} · LEARN: {current["explanation"]}')
            return
        elif action in ('SHAKE','PRESS') and action in moves:
            nearby=[o for o in self.obstacles if not o['destroyed_by'][i] and not o['passed'][i]
                    and -INPUT_GRACE<=o['event_at']-self.age<=1.0 and abs(o['x']-p['x'])<2.2
                    and (o['kind'] in ('SAMPLE','GENERATOR') if self.mission.game_type in ('SAMPLE_HUNT','STORM_SHELTER','RELAY_REPAIR') else True)]
            if nearby:
                picked=min(nearby,key=lambda o:o['z']);picked['destroyed_by'][i]=True
                if picked['kind']=='SAMPLE' and not picked.get('research',True):
                    p['score']=max(0,p['score']-5);p['feedback']='DECOY −5';p['feedback_until']=self.age+1.2;self.emit(f'P{i+1} · UNMARKED ROCK −5');return
                if picked['kind']=='SAMPLE':p['samples']+=1;self.emit(f'P{i+1} SAMPLE {p["samples"]}/{3}')
                elif picked['kind']=='GENERATOR':p['chargers']+=1;self.emit(f'P{i+1} POWER {p["chargers"]}/2')
                else:self.emit(f'P{i+1} · +25')
                p['score']+=self._points(25,picked['event_at'])
                p['feedback']='COLLECTED +25' if picked['kind']=='SAMPLE' else 'REPAIRED +25' if self.mission.game_type=='RELAY_REPAIR' else 'ACTIVATED +25'
                p['feedback_until']=self.age+1.2
        # Optional sync uses only a natural primary movement for this mission;
        # it is never a random extra shake or a replacement for the objective.
        sync_action={
            'SURFACE_RUN':'JUMP','CRATER_LEAP':'UPWARD_FLICK',
            'SAMPLE_HUNT':'PRESS','STORM_SHELTER':'SHAKE',
            'RING_RACE':'JUMP','BEACON_RELAY':'PRESS',
            'ASTEROID_DODGE':'SHAKE','METEOR_BREAK':'SHAKE','RELAY_REPAIR':'SHAKE','GRAVITY_SLING':'UPWARD_FLICK'
        }.get(self.mission.game_type)
        if self.mission.sync_boost and action==sync_action:
            stamps=self.sync_timestamps.setdefault(action,[-100.,-100.])
            stamps[i]=now
            if self.boost_cooldown<=0 and abs(stamps[0]-stamps[1])<=.8:
                self.boost=1.0;self.boost_cooldown=5.
                for explorer in self.players:explorer['score']+=8
                self.team_score=sum(explorer['score'] for explorer in self.players)
                stamps[:]=[-100.,-100.]
                self.last_sync=now
                context={'SAMPLE_HUNT':'CO-SCAN · BOTH +8', 'BEACON_RELAY':'LINKED SIGNAL · BOTH +8',
                         'STORM_SHELTER':'DUAL SHELTER · BOTH +8', 'CRATER_LEAP':'BRIDGE BURST · BOTH +8',
                         'SURFACE_RUN':'TANDEM LEAP · BOTH +8','RING_RACE':'RING RHYTHM · BOTH +8',
                         'RELAY_REPAIR':'DUAL RELAY RESTORED · BOTH +8',
                         'GRAVITY_SLING':'TWIN GRAVITY BOOST · BOTH +8'}
                self.sync_effect=context.get(self.mission.game_type,'DUAL SHIELD · BOTH +8')
                self.emit(self.sync_effect)
    def _points(self,base,event_at):
        return base

    def start_mission(self):
        self.transition('MISSION');self.last_actions=[{},{}];self.sync_timestamps={};self.last_sync=-10.;self.health=100;self.boost=0;self.boost_cooldown=0;self.team_score=0;self.sync_effect=''
        self.jump_at=[-100.,-100.];self.flick_at=[-100.,-100.]
        for i,p in enumerate(self.players):p.update(x=0.,y=0.,distance=0.,health=100,score=0,jump=0.,flick=0.,duck=bool(self.duck_sources[i]),samples=0,chargers=0,selection=1,streak=0,feedback='',feedback_until=0.)
        rng=random.Random(self.mission.name+str(self.generation));self.obstacles=[]
        if self.mission.game_type=='SCIENCE_QUIZ':
            # Five true science prompts: the final prompt appears near second 13
            # and remains playable through second 15. Every fact is pre-verified.
            questions=SCIENCE_QUESTIONS[self.planet][:]
            rng.shuffle(questions)
            for n,q in enumerate(questions[:5]):
                choices=list(q['choices']);rng.shuffle(choices)
                self.obstacles.append(dict(id=n,kind='QUESTION',event_at=[.5,3.7,6.9,10.1,13.2][n],
                                           question=q['question'],choices=choices,answer=choices.index(q['correct']),
                                           explanation=q['explanation'],x=0.,y=0.,z=0.,
                                           destroyed=False,destroyed_by=[False,False],passed=[False,False]))
            self.emit('SCIENCE LAB · CHOOSE THE CORRECT ANSWER!')
            return
        for n,encounter_at in enumerate(encounter_times(self.mission.game_type,self.mission.obstacle_count)):
            mode=self.mission.game_type
            kind=({'SURFACE_RUN':('HURDLE','GATE'),'RING_RACE':('HURDLE','GATE'),
                   'CRATER_LEAP':('PIT','RIDGE'),'SAMPLE_HUNT':('SAMPLE',),
                   'STORM_SHELTER':('GENERATOR','STORM'),'RELAY_REPAIR':('GENERATOR',),'GRAVITY_SLING':('PORTAL',),'ORBIT_SLALOM':('SLALOM',)}.get(mode,('BEACON',) if mode=='BEACON_RELAY' else ('ROCK',)))[n % (2 if mode in ('SURFACE_RUN','RING_RACE','STORM_SHELTER','CRATER_LEAP') else 1)]
            mobile=mode in ('SAMPLE_HUNT','BEACON_RELAY','ORBIT_SLALOM','ASTEROID_DODGE','RELAY_REPAIR','GRAVITY_SLING')
            if mobile:
                x=(rng.choice([-2.7,0.,2.7]) if self.mission.event_pattern=='SCATTERED' else
                   (-2.7 if n%2==0 else 2.7) if self.mission.event_pattern=='ALTERNATING' else
                   (0.,-2.7,2.7)[n%3])
            else:x=0.
            self.obstacles.append(dict(id=n,x=x,y=0.,z=TRACK_SPEED*encounter_at,event_at=encounter_at,
                                       cue_at=max(0.,encounter_at-WARNING_LEAD), avoided=[False,False], research=(n%2==0 if mode=='SAMPLE_HUNT' else True),
                                       kind=kind,destroyed=False,destroyed_by=[False,False],passed=[False,False]))
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
        axes=self.active_axes()
        if self.phase=='BOOT' and self.age>=10:self.transition('LAUNCH')
        if self.phase=='LAUNCH':
            t=min(1.,self.age/5);ease=t*t*(3-2*t)
            self.ship[1]=14.+10.*ease;self.ship[2]=-120.-15.*ease
            if self.age>=5:self.transition('NAVIGATION');self.emit('P1 · FORWARD / BACK / TURN · P2 · LEVEL THE SHIP')
        if self.phase=='COUNTDOWN' and self.age>=COUNTDOWN_SECONDS:self.start_mission()
        if self.phase=='NAVIGATION':
            self.thrust_blocked=False
            pilot=self.players[0]
            # Navigation: P1 owns both joystick axes (forward/backward, yaw).
            # P2's dedicated roll/level correction never changes heading.
            pilot['yaw']=(pilot['yaw']+axes[0][1]*dt*.65+math.pi)%(2*math.pi)-math.pi
            # Signed throttle: forward and reverse are equally controllable.
            # Releasing the joystick brakes toward zero instead of coasting forever.
            throttle=axes[0][0];desired=throttle*34.
            response=4.5 if throttle else 9.0
            self.speed+=(desired-self.speed)*min(1.,dt*response)
            if throttle==0 and abs(self.speed)<.05:self.speed=0.
            before={t['planet']:math.dist(self.ship,t['position']) for t in self.targets()}
            step=self.speed*dt
            self.ship[0]+=math.sin(pilot['yaw'])*step
            self.ship[2]-=math.cos(pilot['yaw'])*step
            # Don't allow the ship to move further into a planet's safety zone.
            # Backing away from a nearby planet must still be possible.
            # Earth starts close to the cockpit and below its flight plane.
            # The old 42-unit invisible safety sphere included our spawn point
            # and falsely blocked forward thrust. Keep a clearance zone without
            # treating a safe departing ship as a collision.
            if any(math.dist(self.ship,t['position'])<30
                   and math.dist(self.ship,t['position']) < before[t['planet']] - 1e-6 for t in self.targets()):
                self.ship[0]-=math.sin(pilot['yaw'])*step
                self.ship[2]+=math.cos(pilot['yaw'])*step
                self.speed=0.;self.thrust_blocked=True
            else:
                self.travel+=abs(step)
            self.players[1]['yaw']=pilot['yaw']
        if self.phase in ('LAUNCH','NAVIGATION','TRAVEL'):
            self.roll=max(-.32,min(.32,self.roll+dt*(.065*math.sin(self.world_time*1.1)+.02-axes[1][1]*.5)))
        if self.phase=='TRAVEL':
            dest=next(t for t in DESTINATIONS if t[0]==self.planet);t=min(1,self.age/4);smooth=t*t*(3-2*t)
            end=[dest[1],dest[2],dest[3]+55]
            self.ship=[a+(b-a)*smooth for a,b in zip(self.transfer_from,end)]
            yaw=self.players[0]['yaw'];self.players[0]['yaw']=yaw*(1-min(1,dt*2));self.players[1]['yaw']=self.players[0]['yaw']
            if self.age>=4 and self.mission:self.transition('ARRIVAL');self.emit('PREPARING LANDING')
        if self.phase=='GENERATING' and self.mission:self.transition('ARRIVAL')
        if self.phase=='ARRIVAL' and self.age>=2:
            if self.planet not in self.visited:self.visited.append(self.planet)
            self.transition('BRIEFING');self.emit('MISSION READY')
        if self.phase!='MISSION':return
        mode=self.mission.game_type;race=mode in ('RING_RACE','SURFACE_RUN','CRATER_LEAP','SAMPLE_HUNT','STORM_SHELTER')
        for i,p in enumerate(self.players):
            if mode=='SCIENCE_QUIZ':
                p['selection']=0 if axes[i][0]<-.45 else 2 if axes[i][0]>.45 else 1
            elif 'STEER' in MOVES[mode] or 'TILT' in MOVES[mode]:p['x']=max(-4.,min(4.,p['x']+axes[i][0]*dt*5))
            p['jump']=max(0.,p['jump']-dt);p['flick']=max(0.,p['flick']-dt)
            if mode!='SCIENCE_QUIZ':p['distance']=min(self.age,self.mission.time_limit_s)*TRACK_SPEED
            for o in self.obstacles:
                if mode=='SCIENCE_QUIZ':
                    if o['event_at']+2.3<=self.age:o['passed'][i]=True
                    continue
                if o['passed'][i] or o['destroyed_by'][i]:continue
                if o['kind'] in BODY_KINDS:
                    # Capture success at contact; permit a late camera edge within
                    # the grace interval. Resolve once, identically for both lanes.
                    if self.age>=o['event_at']:
                        jump_ok=o['event_at']-RESPONSE_WINDOW <= self.jump_at[i] <= o['event_at']+INPUT_GRACE
                        flick_ok=o['event_at']-RESPONSE_WINDOW <= self.flick_at[i] <= o['event_at']+INPUT_GRACE
                        ok=jump_ok if o['kind'] in ('HURDLE','PIT') else flick_ok if o['kind']=='RIDGE' else p['duck']
                        o['avoided'][i]=o['avoided'][i] or ok
                if self.age<o['event_at']+INPUT_GRACE:continue
                o['passed'][i]=True
                if o['kind'] in ('BEACON','SAMPLE'):continue
                if o['kind']=='SLALOM':
                    aligned=abs(o['x']-p['x'])<1.65
                    p['score']+=15 if aligned else 0
                    p['feedback']='GATE +15' if aligned else 'MISSED GATE';p['feedback_until']=self.age+1.2
                    continue
                if o['kind']=='PORTAL':
                    if p['flick']>0 and abs(o['x']-p['x'])<1.8:
                        points=self._points(15,o['event_at']);p['score']+=points
                        self.emit(f'P{i+1} · GRAVITY BOOST +{points}!')
                    elif self.boost<=0:
                        p['health']=max(0,p['health']-8);self.emit(f'P{i+1} · LINE UP AND FLICK!')
                    continue
                if o['kind']=='GENERATOR':
                    if not o['destroyed_by'][i] and self.boost<=0:
                        p['health']=max(0,p['health']-5);self.damage_flash=.2;self.emit(f'P{i+1} · CHARGE THE GENERATOR!')
                    continue
                hit=not o['avoided'][i] if o['kind'] in BODY_KINDS else abs(o['x']-p['x'])<1.5
                p['feedback']='MISSED' if hit and self.boost<=0 else 'CLEARED +10'
                p['feedback_until']=self.age+1.2
                if hit and self.boost<=0:
                    p['streak']=0;p['health']=max(0,p['health']-8);self.damage_flash=.35;self.emit(f'P{i+1} · '+('FLICK UP!' if o['kind']=='RIDGE' else 'JUMP THE GAP!' if o['kind']=='PIT' else 'JUMP!' if o['kind']=='HURDLE' else 'TAKE COVER!' if o['kind']=='STORM' else 'DUCK!' if o['kind']=='GATE' else 'WATCH THE ROCKS!'))
                else:
                    points=self._points(10,o['event_at'])
                    p['streak']=p.get('streak',0)+1
                    bonus=min(15,(p['streak']-1)*3);points+=bonus
                    p['score']+=points;p['feedback']=f"{p['streak']} IN A ROW +{points}";self.emit(f'P{i+1} · +{points}!')
        self.team_score=sum(p['score'] for p in self.players)  # backwards-compatible total only
        self.health=min(p['health'] for p in self.players)
        if self.age>=self.mission.time_limit_s:
            if mode=='SCIENCE_QUIZ':
                for o in self.obstacles:
                    for i in range(2):o['passed'][i]=True  # End the final answer window on time.
            scores=[p['score'] for p in self.players]
            self.winner='P1' if scores[0]>scores[1] else 'P2' if scores[1]>scores[0] else 'TIE'
            self.total_scores=[total+p['score'] for total,p in zip(self.total_scores,self.players)]
            if self.planet not in self.planet_results:
                self.planet_results[self.planet]={'scores':list(scores),'winner':self.winner}
            self.transition('RESULTS')
            self.emit('PLAYER 1 WINS!' if self.winner=='P1' else 'PLAYER 2 WINS!' if self.winner=='P2' else 'IT’S A TIE!')
    def controller_snapshot(self):
        active=self.active_axes()
        rows=[]
        for i in range(2):
            age=max(0.,self.world_time-self.remote_input_at[i]);fresh=age<.4
            event=self.remote_events[i]
            rows.append(dict(player=f'P{i+1}',raw=self.remote_raw[i],axes=self.remote_axes[i],tilt=self.remote_tilt[i],effective=active[i],fresh=fresh,age_ms=round(age*1000) if self.remote_packets[i] else None,packets=self.remote_packets[i],source='REMOTE' if fresh else 'KEYBOARD' if self.world_time-self.input_at[i]<.4 else 'NONE',last_action=event['action'] if event else None,action_age_ms=round((self.world_time-event['at'])*1000) if event else None,signs=self.controller_signs[i],mpu=self.mpu[i]))
        return rows

    def snapshot(self):
        education=dict(self.education or PLANET_FACTS.get(self.planet) or {})
        if self.mission:
            education['why']=MODE_LESSONS[self.mission.game_type]
        thrust=self.active_axes()[0][0] if self.phase=='NAVIGATION' else 0.
        quiz=next(({'id':o['id'],'question':o['question'],'choices':o['choices'],'explanation':o['explanation'],'answered':list(o['passed'])} for o in self.obstacles if o['kind']=='QUESTION' and o['event_at']<=self.age<o['event_at']+2.3),None) if self.mission and self.mission.game_type=='SCIENCE_QUIZ' else None
        return dict(planet_results=self.planet_results,visited=self.visited,expedition_wins=[sum(r['winner']==p for r in self.planet_results.values()) for p in ('P1','P2')],expedition_complete=len(self.planet_results)==len(DESTINATIONS),jump_scale=min(1.25,1.+max(0.,{'JUPITER':2.53,'SATURN':1.065,'NEPTUNE':1.14}.get(self.planet,1.)-1.)*.15),controllers=self.controller_snapshot(),selection=self.selection() if self.phase=='NAVIGATION' else None,inspected=self.inspected,timing=timing_snapshot(),total_scores=self.total_scores,quiz=quiz,thrust_input=max(0.,thrust),reverse_input=max(0.,-thrust),throttle_input=thrust,thrust_blocked=self.thrust_blocked,ship=self.ship,team_score=self.team_score,health=self.health,boost=self.boost,boost_cooldown=self.boost_cooldown,damage_flash=self.damage_flash,roll=round(self.roll,4),speed=round(self.speed,1),travel=round(self.travel,2),phase=self.phase,age=round(self.age,2),planet=self.planet,players=self.players,targets=self.targets(),locked=[self.target(),self.target()],mission=self.mission.model_dump() if self.mission else None,source=self.source,obstacles=[{k:v for k,v in o.items() if k!='answer'} for o in self.obstacles],winner=self.winner,event=self.event,event_id=self.event_id,sync_ready=self.boost_cooldown<=0,sync_window_s=.8,education=education or None,sync_effect=self.sync_effect,authority='SIMULATOR / KEYBOARD' if self.simulated else 'PICO / COMPUTER')
