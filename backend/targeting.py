"""One crosshair target for labels, keyboard, remote and selection actions."""
import json
import math
from pathlib import Path
DISCOVERIES=json.loads((Path(__file__).resolve().parent.parent/'shared/discoveries.json').read_text())
ANCHORS={'EARTH':(-55,14,-200),'EARTH_L2':(-55,14,-200),'JUPITER':(110,14,-200),'SATURN':(0,14,-220),'INNER_SOLAR_SYSTEM':(-205,14,-100)}
RADII={'EARTH':18,'JUPITER':19,'SATURN':15,'MERCURY':7}

def visible_discovery(item,ship):
    anchor=ANCHORS.get(item['zone'],item['position'] if item['zone']=='SOLAR_ORBIT' else None)
    return anchor is None or math.dist(anchor,ship)<(150 if item['zone']=='EARTH_L2' else 135)

def crosshair_target(ship,pilot,targets,travel):
    yaw=pilot['yaw'];pitch=pilot['pitch']
    ray=(math.sin(yaw)*math.cos(pitch),math.sin(pitch),-math.cos(yaw)*math.cos(pitch))
    hits=[]
    def intersect(pos,radius):
        v=[x-y for x,y in zip(pos,ship)];along=sum(x*y for x,y in zip(v,ray))
        perpendicular=sum(x*x for x in v)-along*along
        if along<=0 or perpendicular>radius*radius:return None
        return max(0,along-math.sqrt(max(0,radius*radius-perpendicular)))
    for t in targets:
        hit=intersect(t['position'],RADII.get(t['planet'],12))
        if hit is not None:
            hits.append((hit,dict(kind='planet',id=t['planet'],name=t['planet'].title(),selectable=t['distance']<165 and travel>20)))
    for d in DISCOVERIES:
        if not visible_discovery(d,ship):continue
        radius=64 if d['zone']=='DEEP_SKY' else 5 if d['kind']=='moon' else 7
        hit=intersect(d['position'],radius)
        if hit is not None:hits.append((hit,dict(kind='discovery',id=d['id'],name=d['name'],selectable=True)))
    return min(hits,key=lambda x:x[0])[1] if hits else None
