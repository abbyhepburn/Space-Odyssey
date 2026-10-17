"""Deterministic mock Pico. Only this authority mutates simulator game state."""
from protocol import State, command_line
from mission_catalog import BOUNDS

class Simulator:
    def __init__(self):
        self.capabilities = {'jump':True,'duck':True}
        self.reset()

    def reset(self):
        self.state=State(); self.stage_ms=0; self.mission_start=0; self.mission=None
        self.jump_until=[0,0]; self.completed=set(); self.last_run=[-1000,-1000]

    def command(self, line):
        command_line(line)
        p=line.split(','); s=self.state; out=[]
        if p[0]=='RESET': self.reset()
        elif p[0]=='SKIP_CUTSCENE' and s.phase=='CUTSCENE': self._phase('COUNTDOWN')
        elif p[0]=='CAPABILITIES': self.capabilities=dict(zip(('jump','duck'),(x=='1' for x in p[1:])))
        elif p[0]=='SET_MISSION':
            mid,target,limit=p[1],int(p[2]),int(p[3]); ability=mid.split('_')[1].lower()
            reason = 'WRONG_PHASE' if s.phase!='RACE' else 'BUSY' if self.mission else 'NOT_READY' if ability!='sprint' and not self.capabilities[ability] else None
            if reason: return [f'MISSION_REJECTED,{mid},{reason}']
            self.mission=(mid,target,limit); self.mission_start=s.elapsed_ms; self.completed=set()
            s.mission_id=mid; s.progress1=s.progress2=0
            out.append(f'MISSION_ACCEPTED,{mid}')
        elif p[0]=='INPUT' and s.phase=='RACE':
            player,action=p[1:]; i=int(player[1])-1; n=i+1
            pose=getattr(s,f'p{n}_pose'); valid=False
            if action=='RUN' and s.elapsed_ms-self.last_run[i]>=120:
                self.last_run[i]=s.elapsed_ms
                distance=getattr(s,f'p{n}_distance')+10
                setattr(s,f'p{n}_distance',distance)
                # Alternating fixed gates every 100m: same coordinates as the renderer.
                if distance % 100 == 0:
                    required='JUMP' if (distance//100)%2 else 'DUCK'
                    cleared=pose==required
                    setattr(s,f'score{n}',max(0,getattr(s,f'score{n}')+(5 if cleared else -5)))
                    out.append(f'EVENT,{"OBSTACLE_CLEARED" if cleared else "COLLISION"},{player},{required}')
                setattr(s,f'score{n}',getattr(s,f'score{n}')+1); valid=True
            elif action=='JUMP' and pose=='NORMAL':
                setattr(s,f'p{n}_pose','JUMP'); self.jump_until[i]=s.elapsed_ms+650; valid=True
            elif action=='DUCK_ON' and pose=='NORMAL': setattr(s,f'p{n}_pose','DUCK'); valid=True
            elif action=='DUCK_OFF' and pose=='DUCK': setattr(s,f'p{n}_pose','NORMAL')
            if valid and self.mission:
                mid,target,_=self.mission
                if action=={'SATURN_SPRINT':'RUN','SATURN_JUMP':'JUMP','SATURN_DUCK':'DUCK_ON'}[mid] and player not in self.completed:
                    progress=min(target,getattr(s,f'progress{n}')+1); setattr(s,f'progress{n}',progress)
                    if progress==target:
                        self.completed.add(player); setattr(s,f'score{n}',getattr(s,f'score{n}')+30)
                        out.append(f'MISSION_COMPLETED,{mid},{player}')
            if any(getattr(s,f'p{j}_distance')>=1000 for j in (1,2)): self.finish()
        return out+[self.state.line()]

    def _phase(self, phase):
        self.state.phase=phase; self.state.planet='SATURN'; self.stage_ms=0
        if phase=='RACE': self.state.elapsed_ms=0

    def finish(self):
        s=self.state; self._phase('RESULTS')
        a=(s.p1_distance,s.score1); b=(s.p2_distance,s.score2)
        s.winner='P1' if a>b else 'P2' if b>a else 'TIE'
        self.mission=None; s.mission_id='NONE'

    def tick(self, ms=50):
        s=self.state; self.stage_ms+=ms; out=[]
        if s.phase=='CUTSCENE':
            s.elapsed_ms=self.stage_ms
            if self.stage_ms>=9000: self._phase('COUNTDOWN'); s.elapsed_ms=0
        elif s.phase=='COUNTDOWN':
            s.elapsed_ms=self.stage_ms
            if self.stage_ms>=3000: self._phase('RACE')
        elif s.phase=='RACE':
            s.elapsed_ms+=ms
            for i in range(2):
                if getattr(s,f'p{i+1}_pose')=='JUMP' and s.elapsed_ms>=self.jump_until[i]: setattr(s,f'p{i+1}_pose','NORMAL')
            if self.mission and (len(self.completed)==2 or s.elapsed_ms-self.mission_start>=self.mission[2]*1000):
                out.append(f'EVENT,MISSION_ENDED,NONE,{self.mission[0]}'); self.mission=None; s.mission_id='NONE'
            if s.elapsed_ms>=120000: self.finish()
        return out+[s.line()]
