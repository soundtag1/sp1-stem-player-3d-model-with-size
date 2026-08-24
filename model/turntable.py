"""Render a drag-to-rotate turntable sequence of the model."""

from __future__ import annotations

import math
import os
import sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import build_mesh
import render as RD

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, 'renders', 'turntable')


def main(frames=16, size=720, radius=150.0, elev_deg=32.0, ss=1):
    os.makedirs(OUT, exist_ok=True)
    tex = {k: np.asarray(Image.open(
        os.path.join(REPO, 'textures', f'sp1_{k}.png')).convert('RGB'),
        dtype=np.float32) / 255.0 for k in ('base', 'mr', 'normal')}
    m = build_mesh.build()
    el = math.radians(elev_deg)
    for i in range(frames):
        az = 2 * math.pi * i / frames
        eye = (radius * math.cos(el) * math.cos(az),
               radius * math.cos(el) * math.sin(az),
               radius * math.sin(el))
        img = RD.render(m['P'], m['N'], m['UV'], m['F'], tex,
                        size=(size, size), eye=eye, fov=25, ss=ss)
        img.save(os.path.join(OUT, f'{i:02d}.png'))
        print(f'frame {i+1}/{frames}', flush=True)


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 16
    main(frames=n)
