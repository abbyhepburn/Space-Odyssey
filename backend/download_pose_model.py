"""One-time official Google MediaPipe Pose Landmarker Lite model download."""
from pathlib import Path
from urllib.request import urlopen
import os

MODEL_URL = (
    'https://storage.googleapis.com/mediapipe-models/pose_landmarker/'
    'pose_landmarker_lite/float16/1/pose_landmarker_lite.task'
)
MODEL_PATH = Path(__file__).parent / 'models' / 'pose_landmarker_lite.task'


def ensure_model():
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    if MODEL_PATH.exists() and MODEL_PATH.stat().st_size > 100_000:
        print(f'Pose model already present: {MODEL_PATH}')
        return MODEL_PATH
    partial = MODEL_PATH.with_suffix('.download')
    print(f'Downloading official MediaPipe model to {MODEL_PATH} ...')
    try:
        with urlopen(MODEL_URL, timeout=40) as source, partial.open('wb') as out:
            while chunk := source.read(128 * 1024):
                out.write(chunk)
        if partial.stat().st_size < 100_000:
            raise RuntimeError('Download too small; not a valid model file')
        os.replace(partial, MODEL_PATH)
    finally:
        partial.unlink(missing_ok=True)
    print(f'Saved model: {MODEL_PATH} ({MODEL_PATH.stat().st_size:,} bytes)')
    return MODEL_PATH


if __name__ == '__main__':
    ensure_model()
