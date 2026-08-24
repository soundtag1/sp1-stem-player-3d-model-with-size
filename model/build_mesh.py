"""Assemble the SP-1 mesh from the height fields in geometry.py."""

from __future__ import annotations

import numpy as np

import spec as S
import geometry as G

# --------------------------------------------------------------------------
# texture atlas layout  (pixels in a 4096 x 2048 sheet)
# --------------------------------------------------------------------------
ATLAS_W, ATLAS_H = 4096, 2048
FRONT_RECT = (8, 8, 2032, 1492)      # x, y, w, h
BACK_RECT = (2056, 8, 2032, 1492)
RIM_RECT = (8, 1516, 4080, 202)


def _uv(rect, u, v):
    """Map unit coordinates into an atlas rectangle, returning glTF UVs."""
    x, y, w, h = rect
    return np.stack([(x + u * w) / ATLAS_W, (y + v * h) / ATLAS_H], axis=-1)


# --------------------------------------------------------------------------
# sampling plans
# --------------------------------------------------------------------------

def front_axes():
    xs = G.axis(S.X0 + S.R_EDGE, S.X1 - S.R_EDGE, 1.9, bands=[
        (S.SL_X0 - 0.4, S.SL_X1 + 0.4, 0.18),
        (S.KNOB_X - 1.5, S.KNOB_X + 1.5, 0.11),
        (S.LED_X - 0.7, S.LED_X + 0.7, 0.09),
        (S.BT_X0 - 0.5, S.BT_X1 + 0.5, 0.18),
        (min(S.CAP_DOT_X) - 0.8, max(S.CAP_DOT_X) + 0.8, 0.10),
        (S.X0 + S.R_EDGE, S.X0 + S.R_EDGE + 3.2, 0.22),
        (S.X1 - S.R_EDGE - 3.2, S.X1 - S.R_EDGE, 0.22),
    ])
    ybands = [
        (S.SEAM_Y - 0.35, S.SEAM_Y + 0.35, 0.06),
        (S.CAP_DOT_Y - 0.8, S.CAP_DOT_Y + 0.8, 0.09),
        (S.Y0 + S.R_EDGE, S.Y0 + S.R_EDGE + 3.2, 0.22),
        (S.Y1 - S.R_EDGE - 3.2, S.Y1 - S.R_EDGE, 0.22),
    ]
    for cy in S.ROW_Y:
        ybands.append((cy - 1.75, cy + 1.75, 0.14))
    ys = G.axis(S.Y0 + S.R_EDGE, S.Y1 - S.R_EDGE, 1.9, bands=ybands)
    return xs, ys


def back_axes():
    xb, yb = [], []
    for (sx, sy) in S.SCREW_POS:
        xb.append((sx - 1.9, sx + 1.9, 0.13))
        yb.append((sy - 1.9, sy + 1.9, 0.13))
    xb += [(S.X0 + S.R_EDGE, S.X0 + S.R_EDGE + 3.2, 0.22),
           (S.X1 - S.R_EDGE - 3.2, S.X1 - S.R_EDGE, 0.22)]
    yb += [(S.SEAM_Y - 0.35, S.SEAM_Y + 0.35, 0.06),
           (S.Y0 + S.R_EDGE, S.Y0 + S.R_EDGE + 3.2, 0.22),
           (S.Y1 - S.R_EDGE - 3.2, S.Y1 - S.R_EDGE, 0.22)]
    xs = G.axis(S.X0 + S.R_EDGE, S.X1 - S.R_EDGE, 2.4, bands=xb)
    ys = G.axis(S.Y0 + S.R_EDGE, S.Y1 - S.R_EDGE, 2.4, bands=yb)
    return xs, ys


def rim_s_samples(outline):
    """Arclength samples: coarse everywhere, dense across every side feature."""
    c = outline.cum
    ax, by = outline.ax, outline.by

    def s_top(x):      # +Y edge, x decreasing with s
        return c[4] + (ax - x)

    def s_ports(y):    # +X edge, y increasing with s
        return c[2] + (y + by)

    def s_speaker(y):  # -X edge, y decreasing with s
        return c[6] + (by - y)

    bands = []
    for kx in S.TOPKEY_X:
        half = S.TOPKEY_LEN * 0.5 + S.TOPKEY_POCKET_MARGIN + 0.4
        bands.append((s_top(kx + half), s_top(kx - half), 0.22))
    for hx, hw in ((S.MIC_X, S.MIC_D), (S.AUX_HOLE_X, S.AUX_HOLE_D)):
        bands.append((s_top(hx + hw), s_top(hx - hw), 0.08))
    for lx in S.STATUS_LED_X:
        bands.append((s_top(lx + 0.6), s_top(lx - 0.6), 0.07))
    for jy in S.JACK_Y:
        bands.append((s_ports(jy + S.JACK_D * 0.6), s_ports(jy - S.JACK_D * 0.6), 0.11))
    bands.append((s_ports(S.USBC_Y + S.USBC_LEN * 0.6),
                  s_ports(S.USBC_Y - S.USBC_LEN * 0.6), 0.14))
    for gy in S.GRILLE_ROW_Y:
        bands.append((s_speaker(gy - S.GRILLE_D), s_speaker(gy + S.GRILLE_D), 0.07))
    for ky in S.ROUNDKEY_Y:
        r = S.ROUNDKEY_POCKET_D * 0.6
        bands.append((s_speaker(ky - r), s_speaker(ky + r), 0.14))
    # parting groove crosses the two short ends
    bands.append((s_ports(S.SEAM_Y + 0.4), s_ports(S.SEAM_Y - 0.4), 0.06))
    bands.append((s_speaker(S.SEAM_Y - 0.4), s_speaker(S.SEAM_Y + 0.4), 0.06))
    # keep the rounded corners smooth
    for i in (1, 3, 5, 7):
        bands.append((c[i], c[i + 1], 0.16))

    fixed = []
    for a, b, st in bands:
        lo, hi = (a, b) if a < b else (b, a)
        fixed.append((lo, hi, st))
    return G.axis(0.0, outline.total, 1.6, bands=fixed)


# --------------------------------------------------------------------------
# surface builders
# --------------------------------------------------------------------------

def build_front(mesh, outline_in):
    xs, ys = front_axes()
    X, Y = np.meshgrid(xs, ys)
    PX, PY = outline_in.project(X, Y)
    d, mat = G.front_field(PX, PY)
    Z = S.Z1 - d
    P = np.stack([PX, PY, Z], axis=-1)
    u = (PX - S.X0) / S.L
    v = (S.Y1 - PY) / S.W
    mesh.add_grid(P, _uv(FRONT_RECT, u, v), mat, flip=False)
    return P.shape


def build_back(mesh, outline_in):
    xs, ys = back_axes()
    X, Y = np.meshgrid(xs, ys)
    PX, PY = outline_in.project(X, Y)
    d, mat = G.back_field(PX, PY)
    Z = S.Z0 + d
    P = np.stack([PX, PY, Z], axis=-1)
    u = (S.X1 - PX) / S.L          # mirrored: the back is seen from -Z
    v = (S.Y1 - PY) / S.W
    mesh.add_grid(P, _uv(BACK_RECT, u, v), mat, flip=True)
    return P.shape


def build_rim(mesh, outline):
    ss = rim_s_samples(outline)
    n, z, pn, pz, flat, arclen = G.rim_profile()
    Sg, Tg = np.meshgrid(ss, np.arange(len(n)), indexing='ij')

    ox, oy, onx, ony = outline.point(Sg.astype(float).ravel())
    ox = ox.reshape(Sg.shape); oy = oy.reshape(Sg.shape)
    onx = onx.reshape(Sg.shape); ony = ony.reshape(Sg.shape)

    nn = n[Tg]; zz = z[Tg]
    pnn = pn[Tg]; pzz = pz[Tg]; fl = flat[Tg]

    x0 = ox + onx * nn
    y0 = oy + ony * nn
    z0 = zz
    nx = onx * pnn
    ny = ony * pnn
    nz = pzz

    d, mat = G.rim_field(x0, y0, z0, onx, ony, fl)
    P = np.stack([x0 - d * nx, y0 - d * ny, z0 - d * nz], axis=-1)

    u = Sg / outline.total
    v = arclen[Tg] / arclen[-1]
    mesh.add_grid(P, _uv(RIM_RECT, u, v), mat, flip=False)
    return P.shape


def build():
    outline = G.Outline(S.L, S.W, S.R_CORNER, inset=0.0)
    outline_in = G.Outline(S.L, S.W, S.R_CORNER, inset=S.R_EDGE)
    mesh = G.Mesh()
    fs = build_front(mesh, outline_in)
    bs = build_back(mesh, outline_in)
    rs = build_rim(mesh, outline)
    P, N, UV, MAT, F = mesh.finish()

    return dict(P=P, N=N, UV=UV, MAT=MAT, F=F,
                shapes=dict(front=fs, back=bs, rim=rs), outline=outline)


if __name__ == '__main__':
    m = build()
    P, F = m['P'], m['F']
    print('front grid', m['shapes']['front'])
    print('back  grid', m['shapes']['back'])
    print('rim   grid', m['shapes']['rim'])
    print(f"vertices {len(P):,}   triangles {len(F):,}")
    print('bbox min', np.round(P.min(0), 3), 'max', np.round(P.max(0), 3))
    print('size    ', np.round(P.max(0) - P.min(0), 3), 'mm')
