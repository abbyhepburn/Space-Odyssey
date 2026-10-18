"""Read-only USB bench check. Close Serial Monitor/the bridge before running.

python backend/controller_check.py COM3 --seconds 30
This never flashes firmware or fabricates a passing motion result.
"""
import argparse
import json
import time
from collections import Counter
import serial
from serial.tools import list_ports
from control_inputs import remote_to_flight


def check(port,seconds=30):
    rows={p:{'states':0,'imu_packets':0,'imu_ok':False,'max_tilt':0.,
             'max_stick':0.,'actions':Counter()} for p in ('P1','P2')}
    other=0;invalid=0
    with serial.Serial(port,115200,timeout=.1) as usb:
        print(f'Listening on {port}. Center, tilt left/right, shake and click each remote.',flush=True)
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            raw=usb.read_until(b'\n',size=1025)
            if not raw:continue
            if not raw.endswith(b'\n'):
                # Drop the remainder rather than parsing a truncated packet.
                usb.read_until(b'\n',size=4096);invalid+=1;continue
            line=raw.decode('ascii',errors='replace').strip()
            if not line.startswith('REMOTE,'):
                other+=1;continue
            try:parts=remote_to_flight(line).split(',')
            except ValueError:invalid+=1;continue
            row=rows[parts[1]];action=parts[2]
            if action=='SENSORS':
                forward,steer,tilt=map(float,parts[3:]);row['states']+=1
                row['max_tilt']=max(row['max_tilt'],abs(tilt))
                row['max_stick']=max(row['max_stick'],abs(forward),abs(steer))
            elif action=='AXIS':
                row['states']+=1;row['max_stick']=max(row['max_stick'],*(abs(float(v)) for v in parts[3:]))
            elif action=='MPU':
                row['imu_packets']+=1;row['imu_ok']=parts[3] in ('1','1.0')
            else:
                row['actions'][action]+=1;print(line,flush=True)
    for row in rows.values():
        row['tilt_seen']=row['max_tilt']>=.1
        row['shake_seen']=row['actions']['SHAKE']>0
        row['button_seen']=row['actions']['SELECT']>0 or row['actions']['PRESS']>0
    result={'port':port,'players':rows,'other_lines':other,'invalid_lines':invalid,
            'passed':all(r['states'] and r['tilt_seen'] and r['shake_seen'] and r['button_seen'] for r in rows.values())}
    print(json.dumps(result,indent=2))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('port',nargs='?')
    parser.add_argument('--seconds',type=float,default=30)
    args=parser.parse_args()
    if not args.port:
        for p in list_ports.comports():print(f'{p.device}: {p.description}')
        raise SystemExit('Pass the exact Pico port shown by Arduino IDE Tools > Port.')
    if not 1<=args.seconds<=60:parser.error('--seconds must be between 1 and 60')
    try:result=check(args.port,args.seconds)
    except serial.SerialException as exc:raise SystemExit(f'Could not open Pico: {exc}. Close any other COM-port owner.')
    raise SystemExit(0 if result['passed'] else 1)


if __name__=='__main__':main()
