"""Idempotently add the small camera router to YOUR existing backend/main.py.

Run at the Space-Odyssey project root, after copying the backend camera files.
Always backs up main.py before editing it. Does not touch frontend or .env.
"""
from pathlib import Path
import shutil
import sys

root = Path(__file__).resolve().parent
main = root / 'backend' / 'main.py'
if not main.is_file():
    sys.exit(f'Cannot find {main}. Copy this script to your Space-Odyssey project root.')
source = main.read_text(encoding='utf-8')
if 'app.include_router(vision_router)' in source:
    print('Camera integration is already installed. Nothing changed.')
    sys.exit(0)
if 'app=FastAPI(' not in source and 'app = FastAPI(' not in source:
    sys.exit('Could not identify FastAPI app. Your backend may be a different version; no edits made.')
backup = main.with_name('main.py.before-camera.bak')
if not backup.exists():
    shutil.copy2(main, backup)

import_line = 'from vision_route import router as vision_router, expire_camera\n'
if import_line not in source:
    source = import_line + source

# Include router immediately following app initialization (same module, no app logic replacement).
lines = source.splitlines(keepends=True)
for i, line in enumerate(lines):
    if line.lstrip().startswith(('app=FastAPI(', 'app = FastAPI(')):
        lines.insert(i+1, 'app.include_router(vision_router)\n')
        break
else:
    sys.exit('Unable to locate FastAPI app initialization; no edits made.')
source = ''.join(lines)
# Keep physical Pico capabilities accurate when the standalone camera disconnects.
needle = '            self.flight.tick(now-last)\n'
if needle in source and 'expire_camera(self,now)' not in source:
    source = source.replace(needle, needle + '            expire_camera(self,now)\n', 1)
else:
    if 'expire_camera(self,now)' not in source:
        print('Note: heartbeat timeout hook not installed; backend loop structure differs.')
compile(source, str(main), 'exec')
main.write_text(source, encoding='utf-8')
print('Camera router installed in backend/main.py.')
print(f'Original backed up at {backup}')
print('Backend still uses existing INPUT event processing; frontend unchanged.')
