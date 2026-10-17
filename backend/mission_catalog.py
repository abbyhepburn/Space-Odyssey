"""Shared approved firmware capabilities; AI cannot extend this catalog."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
BOUNDS = {'SATURN_SPRINT':(4,20,15,60), 'SATURN_JUMP':(1,5,20,90), 'SATURN_DUCK':(1,5,20,90)}

class Mission(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    planet: Literal['SATURN'] = 'SATURN'
    mission_id: Literal['SATURN_SPRINT','SATURN_JUMP','SATURN_DUCK']
    title: str = Field(min_length=1,max_length=70)
    story: str = Field(min_length=1,max_length=240)
    target: int
    time_limit_s: int
    visual_theme: Literal['ice','amber','aurora'] = 'ice'

    def compatible(self, phase, capabilities):
        lo, hi, tlo, thi = BOUNDS[self.mission_id]
        if phase != 'RACE': raise ValueError('Missions require RACE')
        if not (lo <= self.target <= hi and tlo <= self.time_limit_s <= thi):
            raise ValueError('Mission outside tested bounds')
        ability = self.mission_id.split('_')[1].lower()
        if ability != 'sprint' and not capabilities.get(ability): raise ValueError('Ability unavailable')
        return self


def fallback(capabilities, index=0):
    choices = ['SATURN_SPRINT'] + [f'SATURN_{a.upper()}' for a in ('jump','duck') if capabilities.get(a)]
    mid = choices[index % len(choices)]
    action = mid.split('_')[1].lower()
    return Mission(mission_id=mid, title={'sprint':'Chase the ringlight','jump':'Clear the ice ridges','duck':'Under the satellites'}[action],
        story={'sprint':'Pump your arms to collect 12 thruster charges.', 'jump':'Jump three times to clear the ice ridges.', 'duck':'Duck and stand three times beneath the satellite gates.'}[action],
        target=12 if action=='sprint' else 3, time_limit_s=30 if action=='sprint' else 40)
