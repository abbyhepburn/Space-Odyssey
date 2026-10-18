"""Launch local game, optionally paired to spaceodyssey.work."""
import argparse
import getpass
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import webbrowser

ROOT=Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--serial',help='Pico USB port, e.g. /dev/cu.usbmodem123')
    parser.add_argument('--cloud',help='https://spaceodyssey.work or your Render URL')
    parser.add_argument('--camera',action='store_true',help='Enable optional laptop OpenCV tracking')
    parser.add_argument('--no-camera',action='store_true',help='Keep remote-only controls (default)')
    parser.add_argument('--port',type=int,default=8000)
    args=parser.parse_args()
    from dotenv import load_dotenv
    load_dotenv(ROOT/'backend'/'.env')
    env=os.environ.copy();env['VISION_ENABLED']='false';env['SPACE_ODYSSEY_HOSTED']='false'
    if args.serial:env.update(SIMULATE_PICO='false',SERIAL_PORT=args.serial)
    if args.cloud:
        env['SPACE_ODYSSEY_HOST_URL']=args.cloud
        env['SPACE_ODYSSEY_PAIRING_CODE']=getpass.getpass('Paste the pairing code shown in your online game: ').strip()
    endpoint=f'http://127.0.0.1:{args.port}'
    try:
        urllib.request.urlopen(endpoint+'/health',timeout=1)
    except Exception:pass
    else:raise SystemExit(f'Port {args.port} already has a game server. Stop it first or choose --port 8002.')
    if args.camera and not args.no_camera:
        subprocess.run([sys.executable,str(ROOT/'backend'/'download_pose_model.py')],check=True)
        env['VISION_ENABLED']='false'
    server=subprocess.Popen([sys.executable,'-m','uvicorn','main:app','--host','127.0.0.1','--port',str(args.port)],cwd=ROOT/'backend',env=env)
    try:
        for _ in range(60):
            if server.poll() is not None:raise RuntimeError('Backend did not start')
            try:urllib.request.urlopen(endpoint+'/health',timeout=.5);break
            except Exception:time.sleep(.2)
        else:raise RuntimeError('Backend startup timed out')
        if args.camera and not args.no_camera:
            request=urllib.request.Request(endpoint+'/api/vision/start',method='POST')
            try:urllib.request.urlopen(request,timeout=15).read()
            except Exception as exc:print('Camera could not open:',type(exc).__name__)
        if not args.cloud:webbrowser.open(endpoint)
        print('Keep this window open while the game runs. Move the game browser to the HDMI monitor if needed.')
        if args.cloud:print('Paired mode: keep the online game open. Refreshing the website creates a new pairing code.')
        server.wait()
    except KeyboardInterrupt:pass
    finally:
        server.terminate()
        try:server.wait(timeout=5)
        except subprocess.TimeoutExpired:server.kill();server.wait()

if __name__=='__main__':main()
