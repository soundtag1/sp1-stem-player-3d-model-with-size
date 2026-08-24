"""One-shot build: textures, meshes, exports and preview renders.

    python3 model/build_all.py            # everything
    python3 model/build_all.py --no-render # skip the (slow) preview renders
"""

from __future__ import annotations

import os
import sys
import time
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import spec as S
import build_mesh
import textures as TX
import exporters as EX
import render as RD

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(REPO, 'dist')
TEXDIR = os.path.join(REPO, 'textures')
RENDERS = os.path.join(REPO, 'renders')

VIEWS = {
    'hero':      dict(eye=(102, -86, 76), fov=27),
    'front':     dict(eye=(0, -6, 152), fov=25),
    'back':      dict(eye=(0, -6, -152), fov=25),
    'top_edge':  dict(eye=(36, 116, 50), fov=26),
    'ports_end': dict(eye=(140, -46, 34), fov=25),
    'speaker_end': dict(eye=(-140, -46, 34), fov=25),
}


def main(do_render=True):
    t0 = time.time()
    os.makedirs(DIST, exist_ok=True)
    os.makedirs(TEXDIR, exist_ok=True)

    print('[1/4] texture atlas')
    maps = TX.build_atlas()
    for k, v in maps.items():
        v.save(os.path.join(TEXDIR, f'sp1_{k}.png'), optimize=True)

    print('[2/4] mesh')
    m = build_mesh.build()
    P, N, UV, F = m['P'], m['N'], m['UV'], m['F']
    size = P.max(0) - P.min(0)
    print(f'      {len(P):,} vertices / {len(F):,} triangles')
    print(f'      bounding box {size[0]:.2f} x {size[1]:.2f} x {size[2]:.2f} mm')

    print('[3/4] exports')
    # The GLB embeds a 2K texture set: across a 64 mm body that is still about
    # 62 um per texel, and it keeps the file openable in a browser.  The 4K
    # masters live in textures/ and are what the OBJ material points at.
    import io
    embed = {}
    for k, v in maps.items():
        buf = io.BytesIO()
        v.resize((v.width // 2, v.height // 2), Image.LANCZOS).save(
            buf, format='PNG', optimize=True)
        embed[k] = buf.getvalue()
    n = EX.write_glb(os.path.join(DIST, 'sp1_stem_player.glb'), P, N, UV, F, embed)
    print(f'      dist/sp1_stem_player.glb   {n/1e6:.2f} MB  (metres, 2K PBR textures)')

    EX.write_obj(os.path.join(DIST, 'sp1_stem_player.obj'), P, N, UV, F)
    print(f'      dist/sp1_stem_player.obj   '
          f'{os.path.getsize(os.path.join(DIST, "sp1_stem_player.obj"))/1e6:.2f} MB  (millimetres)')
    EX.write_stl(os.path.join(DIST, 'sp1_stem_player.stl'), P, F)
    print(f'      dist/sp1_stem_player.stl   '
          f'{os.path.getsize(os.path.join(DIST, "sp1_stem_player.stl"))/1e6:.2f} MB  (millimetres)')

    if do_render:
        print('[4/4] preview renders')
        os.makedirs(RENDERS, exist_ok=True)
        tex = {k: np.asarray(v.convert('RGB'), dtype=np.float32) / 255.0
               for k, v in maps.items()}
        for name, v in VIEWS.items():
            img = RD.render(P, N, UV, F, tex, size=(1280, 960), ss=1, **v)
            img.save(os.path.join(RENDERS, f'{name}.png'))
            print(f'      renders/{name}.png')
    else:
        print('[4/4] renders skipped')

    print(f'done in {time.time()-t0:.0f}s')


if __name__ == '__main__':
    main(do_render='--no-render' not in sys.argv)
