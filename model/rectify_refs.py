"""
Perspective-rectify the reference photographs into true-scale orthographic
views, which the texture stage then samples.

Front and back come from the flat-on panel shots; the four side faces come
from the straight-on edge shots.  Output goes to reference/ at 40 px/mm.
"""

from __future__ import annotations

import math
import os
import sys
import numpy as np
from PIL import Image
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec as S

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHOTOS = os.path.join(REPO, 'photos')
REFS = os.path.join(REPO, 'reference')
PPM = 40.0


# --------------------------------------------------------------------------
def blob(fn, seed, sat_max=0.10, v_min=140, ds=4):
    im0 = Image.open(os.path.join(PHOTOS, fn)).convert('RGB')
    W0, H0 = im0.size
    im = np.asarray(im0.resize((W0 // ds, H0 // ds), Image.LANCZOS), dtype=np.float32)
    v = im.max(2)
    s = (v - im.min(2)) / (v + 1e-6)
    m = (v > v_min) & (s < sat_max)
    H, W = m.shape
    sx, sy = seed[0] // ds, seed[1] // ds
    if not m[sy, sx]:
        raise SystemExit(f'{fn}: seed not on the device (v={v[sy,sx]:.0f} s={s[sy,sx]:.2f})')
    seen = np.zeros_like(m)
    q = deque([(sy, sx)])
    seen[sy, sx] = True
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and m[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                q.append((ny, nx))
    return seen, ds, im0


def ransac_line(pts, iters=4000, tol=1.6, seed=0):
    rng = np.random.default_rng(seed)
    n = len(pts)
    best = (0, None)
    for _ in range(iters):
        i, j = rng.integers(0, n, 2)
        if i == j:
            continue
        p, q = pts[i], pts[j]
        d = q - p
        L = math.hypot(*d)
        if L < 8:
            continue
        nx, ny = -d[1] / L, d[0] / L
        r = np.abs((pts - p) @ np.array([nx, ny]))
        k = int((r < tol).sum())
        if k > best[0]:
            best = (k, (p, q))
    p, q = best[1]
    d = q - p
    L = math.hypot(*d)
    nx, ny = -d[1] / L, d[0] / L
    inl = pts[np.abs((pts - p) @ np.array([nx, ny])) < tol]
    c = inl.mean(0)
    _, _, vt = np.linalg.svd(inl - c)
    return c, vt[0]


def intersect(l1, l2):
    (c1, d1), (c2, d2) = l1, l2
    t = np.linalg.solve(np.array([d1, -d2]).T, c2 - c1)
    return c1 + t[0] * d1


def homography(src, dst):
    A = []
    for (x, y), (u, v) in zip(src, dst):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u])
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y, -v])
    _, _, vt = np.linalg.svd(np.array(A))
    H = vt[-1].reshape(3, 3)
    return H / H[2, 2]


def warp(im0, H, W, Hh):
    src = np.asarray(im0, dtype=np.float32)
    ys, xs = np.mgrid[0:Hh, 0:W]
    P = np.stack([xs.ravel(), ys.ravel(), np.ones(xs.size)])
    Q = np.linalg.inv(H) @ P
    Q /= Q[2]
    xq = np.clip(Q[0], 0, src.shape[1] - 1)
    yq = np.clip(Q[1], 0, src.shape[0] - 1)
    x0 = xq.astype(int); y0 = yq.astype(int)
    x1 = np.minimum(x0 + 1, src.shape[1] - 1)
    y1 = np.minimum(y0 + 1, src.shape[0] - 1)
    fx = (xq - x0)[:, None]; fy = (yq - y0)[:, None]
    out = (src[y0, x0] * (1 - fx) * (1 - fy) + src[y0, x1] * fx * (1 - fy) +
           src[y1, x0] * (1 - fx) * fy + src[y1, x1] * fx * fy)
    return Image.fromarray(out.reshape(Hh, W, 3).astype(np.uint8))


def corners(fn, seed, ang=20, **kw):
    seen, ds, im0 = blob(fn, seed, **kw)
    ys, xs = np.nonzero(seen)
    pts = np.stack([xs, ys], 1).astype(np.float64)
    best = None
    for deg in np.arange(-ang, ang, 0.1):
        t = math.radians(deg)
        R = np.array([[math.cos(t), -math.sin(t)], [math.sin(t), math.cos(t)]])
        p = pts @ R.T
        a = np.ptp(p[:, 0]) * np.ptp(p[:, 1])
        if best is None or a < best[0]:
            best = (a, deg)
    t = math.radians(best[1])
    R = np.array([[math.cos(t), -math.sin(t)], [math.sin(t), math.cos(t)]])
    pr = pts @ R.T
    lines = []
    for axis, which in ((1, 'min'), (1, 'max'), (0, 'min'), (0, 'max')):
        keyi = 1 - axis
        key = np.round(pr[:, keyi]).astype(int)
        prof = {}
        for k, val, orig in zip(key, pr[:, axis], pts):
            if k not in prof:
                prof[k] = (val, orig)
            elif (which == 'min' and val < prof[k][0]) or (which == 'max' and val > prof[k][0]):
                prof[k] = (val, orig)
        P = np.array([v[1] for v in prof.values()])
        lines.append(ransac_line(P))
    top, bot, left, right = lines
    c = [intersect(top, left), intersect(top, right),
         intersect(bot, right), intersect(bot, left)]
    return [p * ds for p in c], im0


def rectify(fn, seed, w_mm, h_mm, out, rot=0, flip_h=False, flip_v=False, **kw):
    c, im0 = corners(fn, seed, **kw)
    Wp, Hp = int(round(w_mm * PPM)), int(round(h_mm * PPM))
    # order the corners so the long side of the target maps to the long side
    e_top = np.linalg.norm(np.array(c[1]) - np.array(c[0]))
    e_right = np.linalg.norm(np.array(c[2]) - np.array(c[1]))
    if (e_top < e_right) != (Wp < Hp):
        c = [c[1], c[2], c[3], c[0]]          # rotate the correspondence by 90 deg
    H = homography(c, [(0, 0), (Wp, 0), (Wp, Hp), (0, Hp)])
    img = warp(im0, H, Wp, Hp)
    if rot:
        img = img.rotate(rot, expand=True)
    if flip_h:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    if flip_v:
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
    img.save(os.path.join(REFS, out))
    print(f'{out:26s} {img.size}  from {fn}')
    return img


# The device is never exactly edge-on, so the silhouette of an edge shot is
# the face plus a sliver of the front or back.  Rectify the whole silhouette
# to its own apparent height, then FACE_BAND says which part of that is the
# real 9.4 mm face.
EDGES = [
    # file,                    seed,          long_mm, output
    ('edge-top-long.jpg',      (2150, 1500), S.L, 'rect_edge_top.png'),
    ('edge-bottom-long.jpg',   (2026, 1411), S.L, 'rect_edge_bottom.png'),
    ('edge-connector-end.jpg', (2100, 1700), S.W, 'rect_edge_ports.png'),
    ('edge-speaker-end.jpg',   (2097, 1411), S.W, 'rect_edge_speaker.png'),
]

EDGE_KW = dict(sat_max=0.17, v_min=155)


def rectify_edge(fn, seed, long_mm, out):
    c, im0 = corners(fn, seed, **EDGE_KW)
    e = [np.linalg.norm(np.array(c[(i + 1) % 4]) - np.array(c[i])) for i in range(4)]
    long_px = (e[0] + e[2]) / 2
    short_px = (e[1] + e[3]) / 2
    if long_px < short_px:
        long_px, short_px = short_px, long_px
        c = [c[1], c[2], c[3], c[0]]
    apparent_mm = long_mm * short_px / long_px
    Wp, Hp = int(round(long_mm * PPM)), int(round(apparent_mm * PPM))
    H = homography(c, [(0, 0), (Wp, 0), (Wp, Hp), (0, Hp)])
    img = warp(im0, H, Wp, Hp)
    img.save(os.path.join(REFS, out))
    print(f'{out:26s} {img.size}  apparent depth {apparent_mm:5.2f} mm  from {fn}')
    return img


if __name__ == '__main__':
    os.makedirs(REFS, exist_ok=True)
    for fn, seed, long_mm, out in EDGES:
        rectify_edge(fn, seed, long_mm, out)
