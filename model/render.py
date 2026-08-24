"""A small software rasteriser, used to produce preview renders of the model.

Deliberately dependency free (numpy + Pillow only) so previews can be
regenerated anywhere the generator runs.
"""

from __future__ import annotations

import numpy as np
from PIL import Image


def look_at(eye, target, up=(0, 0, 1)):
    eye = np.asarray(eye, float); target = np.asarray(target, float)
    f = target - eye; f /= np.linalg.norm(f)
    u = np.asarray(up, float)
    r = np.cross(f, u); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    M = np.eye(4)
    M[0, :3] = r; M[1, :3] = u; M[2, :3] = -f
    M[:3, 3] = -M[:3, :3] @ eye
    return M


def perspective(fov_deg, aspect, near=1.0, far=5000.0):
    t = 1.0 / np.tan(np.radians(fov_deg) * 0.5)
    M = np.zeros((4, 4))
    M[0, 0] = t / aspect; M[1, 1] = t
    M[2, 2] = (far + near) / (near - far); M[2, 3] = 2 * far * near / (near - far)
    M[3, 2] = -1.0
    return M


def sample(tex, u, v):
    """Bilinear texture lookup; tex is float32 HxWxC in [0,1]."""
    H, W = tex.shape[:2]
    x = np.clip(u * W - 0.5, 0, W - 1.001)
    y = np.clip(v * H - 0.5, 0, H - 1.001)
    x0 = x.astype(np.int32); y0 = y.astype(np.int32)
    x1 = x0 + 1; y1 = y0 + 1
    fx = (x - x0)[..., None]; fy = (y - y0)[..., None]
    return (tex[y0, x0] * (1 - fx) * (1 - fy) + tex[y0, x1] * fx * (1 - fy) +
            tex[y1, x0] * (1 - fx) * fy + tex[y1, x1] * fx * fy)


LIGHTS = [
    # direction (towards the light), colour, intensity
    (np.array([-0.45, 0.55, 0.72]), np.array([1.00, 0.98, 0.95]), 1.00),
    (np.array([0.70, 0.20, 0.45]), np.array([0.72, 0.80, 0.95]), 0.55),
    (np.array([0.10, -0.85, 0.30]), np.array([1.00, 0.92, 0.85]), 0.38),
]


def render(P, N, UV, F, textures, size=(1600, 1200), eye=(120, -95, 85),
           target=(0, 0, 0), fov=26.0, ss=2, bg=(0.117, 0.121, 0.129)):
    """Rasterise the mesh.  `textures` is a dict with base/rough/normal maps."""
    W, H = size[0] * ss, size[1] * ss
    view = look_at(eye, target)
    proj = perspective(fov, W / H)
    mvp = proj @ view

    hom = np.concatenate([P, np.ones((len(P), 1))], axis=1)
    clip = hom @ mvp.T
    w = np.maximum(clip[:, 3:4], 1e-6)
    ndc = clip[:, :3] / w
    sx = (ndc[:, 0] * 0.5 + 0.5) * W
    sy = (1.0 - (ndc[:, 1] * 0.5 + 0.5)) * H
    sz = ndc[:, 2]
    invw = (1.0 / w[:, 0])

    a, b, c = F[:, 0], F[:, 1], F[:, 2]
    ax, ay = sx[a], sy[a]; bx, by = sx[b], sy[b]; cx, cy = sx[c], sy[c]
    area = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    front = area < -1e-9                      # keep counter-clockwise facing
    keep = front & (sz[a] > -1) & (sz[a] < 1)
    idx = np.nonzero(keep)[0]
    order = np.argsort(np.minimum(np.minimum(sz[a], sz[b]), sz[c])[idx])
    idx = idx[order]

    zbuf = np.full((H, W), np.inf, dtype=np.float32)
    gnrm = np.zeros((H, W, 3), dtype=np.float32)
    guv = np.zeros((H, W, 2), dtype=np.float32)
    gmask = np.zeros((H, W), dtype=bool)

    xi = np.array([ax, bx, cx]); yi = np.array([ay, by, cy])
    for t in idx:
        i0, i1, i2 = a[t], b[t], c[t]
        x0, y0 = sx[i0], sy[i0]; x1, y1 = sx[i1], sy[i1]; x2, y2 = sx[i2], sy[i2]
        lo_x = int(max(0, np.floor(min(x0, x1, x2))))
        hi_x = int(min(W - 1, np.ceil(max(x0, x1, x2))))
        lo_y = int(max(0, np.floor(min(y0, y1, y2))))
        hi_y = int(min(H - 1, np.ceil(max(y0, y1, y2))))
        if hi_x < lo_x or hi_y < lo_y:
            continue
        px = np.arange(lo_x, hi_x + 1) + 0.5
        py = np.arange(lo_y, hi_y + 1) + 0.5
        PX, PY = np.meshgrid(px, py)
        d = area[t]
        w0 = ((x1 - PX) * (y2 - PY) - (y1 - PY) * (x2 - PX)) / d
        w1 = ((x2 - PX) * (y0 - PY) - (y2 - PY) * (x0 - PX)) / d
        w2 = 1.0 - w0 - w1
        m = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not m.any():
            continue
        zz = w0 * sz[i0] + w1 * sz[i1] + w2 * sz[i2]
        sub = zbuf[lo_y:hi_y + 1, lo_x:hi_x + 1]
        m &= zz < sub
        if not m.any():
            continue
        pw = w0 * invw[i0] + w1 * invw[i1] + w2 * invw[i2]
        n0 = (w0 * invw[i0])[..., None] * N[i0] + (w1 * invw[i1])[..., None] * N[i1] \
            + (w2 * invw[i2])[..., None] * N[i2]
        u0 = (w0 * invw[i0])[..., None] * UV[i0] + (w1 * invw[i1])[..., None] * UV[i1] \
            + (w2 * invw[i2])[..., None] * UV[i2]
        n0 = n0 / pw[..., None]
        u0 = u0 / pw[..., None]
        sub[m] = zz[m]
        gnrm[lo_y:hi_y + 1, lo_x:hi_x + 1][m] = n0[m]
        guv[lo_y:hi_y + 1, lo_x:hi_x + 1][m] = u0[m]
        gmask[lo_y:hi_y + 1, lo_x:hi_x + 1][m] = True

    # ---- deferred shading -------------------------------------------------
    nrm = gnrm / np.maximum(np.linalg.norm(gnrm, axis=2, keepdims=True), 1e-9)
    base = np.zeros((H, W, 3), dtype=np.float32)
    rough = np.full((H, W), 0.4, dtype=np.float32)
    metal = np.full((H, W), 0.9, dtype=np.float32)

    if textures:
        u = guv[..., 0]; v = guv[..., 1]
        base = sample(textures['base'], u, v)[..., :3]
        mr = sample(textures['mr'], u, v)
        rough = mr[..., 1]; metal = mr[..., 2]
        nt = sample(textures['normal'], u, v)[..., :3] * 2.0 - 1.0
        # perturb around the geometric normal using a screen-stable basis
        up = np.array([0.0, 0.0, 1.0])
        tang = np.cross(np.broadcast_to(up, nrm.shape), nrm)
        ln = np.linalg.norm(tang, axis=2, keepdims=True)
        tang = np.where(ln > 1e-4, tang / np.maximum(ln, 1e-9),
                        np.array([1.0, 0.0, 0.0]))
        bit = np.cross(nrm, tang)
        nrm = (tang * nt[..., 0:1] + bit * nt[..., 1:2] + nrm * nt[..., 2:3])
        nrm /= np.maximum(np.linalg.norm(nrm, axis=2, keepdims=True), 1e-9)
    else:
        base[:] = np.array([0.87, 0.865, 0.845])

    eye_v = np.asarray(eye, float) - np.asarray(target, float)
    V = eye_v / np.linalg.norm(eye_v)

    col = np.zeros((H, W, 3), dtype=np.float32)
    diffuse_col = base * (1.0 - metal[..., None] * 0.82)
    spec_col = base * metal[..., None] + 0.045 * (1.0 - metal[..., None])
    shin = np.clip(2.0 / np.maximum(rough, 0.03) ** 2, 4.0, 900.0)

    for Ldir, Lcol, Li in LIGHTS:
        Ld = Ldir / np.linalg.norm(Ldir)
        ndl = np.clip(nrm @ Ld, 0, 1)
        Hv = Ld + V; Hv = Hv / np.linalg.norm(Hv)
        ndh = np.clip(nrm @ Hv, 0, 1)
        col += diffuse_col * (ndl * Li)[..., None] * Lcol
        col += spec_col * (np.power(ndh, shin) * ndl * Li * 0.9)[..., None] * Lcol

    ndv = np.clip(np.abs(nrm @ V), 0, 1)
    fres = np.power(1.0 - ndv, 4.0)[..., None]
    col += base * fres * 0.13
    col += diffuse_col * 0.13                    # ambient

    col = col / (1.0 + col * 0.55)               # soft tone map
    col = np.power(np.clip(col, 0, 1), 1 / 2.2)
    out = np.where(gmask[..., None], col, np.array(bg, dtype=np.float32))
    img = Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))
    if ss > 1:
        img = img.resize(size, Image.LANCZOS)
    return img
