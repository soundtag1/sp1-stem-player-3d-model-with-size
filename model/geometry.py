"""
Geometry construction for the SP-1 stem player.

The body is built as three displaced surfaces that share their boundaries:

    front  - height field over (x, y), clipped to the inset outline
    back   - height field over (x, y)
    rim    - height field over (s, t): arclength around the outline and
             position along the front-fillet / side / back-fillet profile

Every pocket, slot, hole and key is a displacement of one of those surfaces,
so the model carries real geometry (and correct silhouettes) rather than
relying on the normal map alone.
"""

from __future__ import annotations

import math
import numpy as np

import spec as S


# ==========================================================================
# sampling helpers
# ==========================================================================

def axis(lo, hi, coarse, bands=()):
    """Sorted sample positions on [lo, hi].

    `bands` is a sequence of (start, end, step) triples that request denser
    sampling.  Feature boundaries are additionally doubled with a 0.02 mm
    offset so a pocket wall gets its own pair of grid lines - that keeps the
    edge crisp under smooth vertex normals while leaving a micro chamfer.
    """
    pts = list(np.arange(lo, hi + 1e-9, coarse))
    pts += [lo, hi]
    for a, b, step in bands:
        if a > b:
            a, b = b, a
        a = max(a, lo)
        b = min(b, hi)
        if b <= a:
            continue
        pts += list(np.arange(a, b + 1e-9, step))
        for edge in (a, b):
            pts += [edge - 0.02, edge, edge + 0.02]
    pts = [p for p in pts if lo - 1e-9 <= p <= hi + 1e-9]
    pts = np.array(sorted(pts))
    keep = np.concatenate([[True], np.diff(pts) > 1e-4])
    return pts[keep]


def band(centre, half, step, pad=0.35):
    return (centre - half - pad, centre + half + pad, step)


# ==========================================================================
# 2-D signed distance primitives (negative inside)
# ==========================================================================

def sd_circle(x, y, cx, cy, r):
    return np.hypot(x - cx, y - cy) - r


def sd_rrect(x, y, cx, cy, hx, hy, r):
    """Rounded rectangle; r may be 0."""
    r = min(r, hx, hy)
    dx = np.abs(x - cx) - (hx - r)
    dy = np.abs(y - cy) - (hy - r)
    outside = np.hypot(np.maximum(dx, 0.0), np.maximum(dy, 0.0))
    inside = np.minimum(np.maximum(dx, dy), 0.0)
    return outside + inside - r


def sd_stadium(x, y, x0, x1, cy, half_h):
    return sd_rrect(x, y, (x0 + x1) * 0.5, cy, (x1 - x0) * 0.5, half_h, half_h)


def disc_blend(x, y, cx, cy, r, edge=0.24):
    """Weight 1 in the middle of a disc, easing to 0 at its rim.

    A hard mask on a tensor grid turns a circular wall into a staircase, which
    smooth vertex normals then render as a fringe of bristles.  Easing the
    displacement over `edge` millimetres gives a shoulder instead.
    """
    rr = np.hypot(x - cx, y - cy)
    w = np.clip((r - rr) / edge, 0.0, 1.0)
    w = np.sin(w * (np.pi * 0.5))
    inner = np.clip(rr / max(r - edge, 1e-3), 0.0, 1.0)
    dome = np.sqrt(np.clip(1.0 - inner ** 2, 0.0, 1.0))
    return rr, w, dome


def sd_blend(sd, edge=0.16):
    """Weight 1 well inside a signed-distance shape, easing to 0 at its edge."""
    return np.sin(np.clip(-sd / edge, 0.0, 1.0) * (np.pi * 0.5))


# ==========================================================================
# material ids  (used to drive the texture atlas)
# ==========================================================================
M_ALU = 0        # anodised aluminium shell
M_POCKET = 1     # machined pocket floor
M_SLOT = 2       # dark slot / hole interior
M_KEY = 3        # plastic key cap
M_KNOB = 4       # slider knob
M_CHROME = 5     # steel channel inside a slider pocket
M_SEAM = 6       # parting line


# ==========================================================================
# front face
# ==========================================================================

def front_field(x, y):
    """Return (depth, material) for the front face.

    `depth` is measured into the body from the Z = +T/2 plane, so a negative
    value means the feature stands proud of the panel.
    """
    if S.MIRROR_X:
        x = -x
    d = np.zeros_like(x)
    m = np.full(x.shape, M_ALU, dtype=np.int32)

    # cap parting groove ----------------------------------------------------
    seam = np.abs(y - S.SEAM_Y) < S.SEAM_W * 0.5
    d = np.where(seam, S.SEAM_D, d)
    m = np.where(seam, M_SEAM, m)

    for cy in S.ROW_Y:
        # slider pocket -----------------------------------------------------
        sd = sd_stadium(x, y, S.SL_X0, S.SL_X1, cy, S.SL_H * 0.5)
        w = sd_blend(sd)
        d = d * (1.0 - w) + S.SL_DEPTH * w
        m = np.where(sd < -0.05, M_CHROME, m)

        # dark track inside the pocket --------------------------------------
        sd = sd_stadium(x, y, S.SL_TRACK_X0, S.SL_TRACK_X1, cy,
                        S.SL_TRACK_H * 0.5)
        w = sd_blend(sd, 0.12)
        d = d * (1.0 - w) + S.SL_TRACK_DEPTH * w
        m = np.where(sd < -0.04, M_SLOT, m)

        # knob: a post with a rounded shoulder, blended into the slot it sits in
        r = S.KNOB_D * 0.5
        rr, w, dome = disc_blend(x, y, S.KNOB_X, cy, r)
        top = -((S.KNOB_RISE - S.KNOB_CROWN) + S.KNOB_CROWN * dome)
        inside = rr < r
        d = np.where(inside, d * (1.0 - w) + top * w, d)
        m = np.where(rr < r - 0.10, M_KNOB, m)

        # indicator LED ------------------------------------------------------
        led = sd_circle(x, y, S.LED_X, cy, S.LED_D * 0.5) < 0
        d = np.where(led, S.LED_DEPTH, d)
        m = np.where(led, M_SLOT, m)

        # button: shallow pocket with a key cap standing in it ---------------
        bcx = (S.BT_X0 + S.BT_X1) * 0.5
        bhx = (S.BT_X1 - S.BT_X0) * 0.5
        sd = sd_rrect(x, y, bcx, cy, bhx + S.BT_GAP, S.BT_H * 0.5 + S.BT_GAP,
                      S.BT_R + S.BT_GAP)
        w = sd_blend(sd, 0.10)
        d = d * (1.0 - w) + S.BT_POCKET_DEPTH * w
        m = np.where(sd < -0.03, M_POCKET, m)

        sd = sd_rrect(x, y, bcx, cy, bhx, S.BT_H * 0.5, S.BT_R)
        w = sd_blend(sd, 0.10)
        d = d * (1.0 - w) + (-S.BT_KEY_RISE) * w
        m = np.where(sd < -0.03, M_KEY, m)

    # two blind holes on the cap -------------------------------------------
    for dx in S.CAP_DOT_X:
        hole = sd_circle(x, y, dx, S.CAP_DOT_Y, S.CAP_DOT_D * 0.5) < 0
        d = np.where(hole, S.CAP_DOT_DEPTH, d)
        m = np.where(hole, M_SLOT, m)

    return d, m


def back_field(x, y):
    if S.MIRROR_X:
        x = -x
    d = np.zeros_like(x)
    m = np.full(x.shape, M_ALU, dtype=np.int32)

    seam = np.abs(y - S.SEAM_Y) < S.SEAM_W * 0.5
    d = np.where(seam, S.SEAM_D, d)
    m = np.where(seam, M_SEAM, m)

    for (sx, sy) in S.SCREW_POS:
        counterbore = sd_circle(x, y, sx, sy, S.SCREW_D * 0.5) < 0
        d = np.where(counterbore, S.SCREW_DEPTH, d)
        m = np.where(counterbore, M_POCKET, m)
        head = sd_circle(x, y, sx, sy, S.SCREW_HEAD_D * 0.5) < 0
        d = np.where(head, S.SCREW_DEPTH - 0.12, d)
        m = np.where(head, M_CHROME, m)

    return d, m


# ==========================================================================
# rim  (the four side faces)
# ==========================================================================

def rim_field(x, y, z, nx, ny, flat):
    """Displacement of the side surface, evaluated on the nominal rim.

    `flat` is 1 on the straight part of the thickness profile and 0 on the
    two edge fillets, so features never bleed around the rounded edges.
    """
    if S.MIRROR_X:
        x = -x
        nx = -nx
    d = np.zeros_like(x)
    m = np.full(x.shape, M_ALU, dtype=np.int32)

    on_top = (ny > 0.7) & (y > S.SEAM_Y)          # +Y long edge
    on_bot = ny < -0.7                             # -Y long edge
    on_ports = nx > 0.7                            # +X short end (connectors)
    on_speaker = nx < -0.7                         # -X short end (speaker)
    live = flat > 0.5

    def put(mask, depth, mat):
        nonlocal d, m
        d = np.where(mask, depth, d)
        m = np.where(mask, mat, m)

    # ---- +Y edge: two keys, mic port, status LEDs -------------------------
    sel = on_top & live
    for kx in S.TOPKEY_X:
        pm = S.TOPKEY_POCKET_MARGIN
        pocket = sd_rrect(x, z, kx, 0.0, S.TOPKEY_LEN * 0.5 + pm,
                          S.TOPKEY_WID * 0.5 + pm, S.TOPKEY_R + pm) < 0
        put(sel & pocket, S.TOPKEY_POCKET_DEPTH, M_POCKET)
        key = sd_rrect(x, z, kx, 0.0, S.TOPKEY_LEN * 0.5,
                       S.TOPKEY_WID * 0.5, S.TOPKEY_R) < 0
        put(sel & key, -S.TOPKEY_RISE, M_KEY)

    put(sel & (sd_circle(x, z, S.MIC_X, 0.0, S.MIC_D * 0.5) < 0),
        S.MIC_DEPTH, M_SLOT)
    for lx in S.STATUS_LED_X:
        put(sel & (sd_circle(x, z, lx, 0.0, S.STATUS_LED_D * 0.5) < 0),
            S.STATUS_LED_DEPTH, M_SLOT)

    # ---- -Y edge: one key and a pinhole -----------------------------------
    sel = on_bot & live
    pm = S.BOTKEY_POCKET_MARGIN
    pocket = sd_rrect(x, z, S.BOTKEY_X, 0.0, S.BOTKEY_LEN * 0.5 + pm,
                      S.BOTKEY_WID * 0.5 + pm, S.BOTKEY_R + pm) < 0
    put(sel & pocket, S.BOTKEY_POCKET_DEPTH, M_POCKET)
    key = sd_rrect(x, z, S.BOTKEY_X, 0.0, S.BOTKEY_LEN * 0.5,
                   S.BOTKEY_WID * 0.5, S.BOTKEY_R) < 0
    put(sel & key, -S.BOTKEY_RISE, M_KEY)
    put(sel & (sd_circle(x, z, S.BOT_PINHOLE_X, 0.0,
                         S.BOT_PINHOLE_D * 0.5) < 0),
        S.BOT_PINHOLE_DEPTH, M_SLOT)

    # ---- +X end: two 3.5 mm jacks and USB-C -------------------------------
    sel = on_ports & live
    for jy in S.JACK_Y:
        rr, w, _ = disc_blend(y, z, jy, 0.0, S.JACK_D * 0.5, edge=0.18)
        bore = sel & (rr < S.JACK_D * 0.5)
        d = np.where(bore, d * (1.0 - w) + S.JACK_DEPTH * w, d)
        m = np.where(bore & (rr < S.JACK_D * 0.5 - 0.08), M_SLOT, m)
    put(sel & (sd_rrect(y, z, S.USBC_Y, 0.0, S.USBC_LEN * 0.5,
                        S.USBC_WID * 0.5, S.USBC_R) < 0),
        S.USBC_DEPTH, M_SLOT)

    # ---- -X end: speaker grille and two round keys ------------------------
    sel = on_speaker & live
    for gy in S.GRILLE_ROW_Y:
        for gz in S.GRILLE_COL_Z:
            put(sel & (sd_circle(y, z, gy, gz, S.GRILLE_D * 0.5) < 0),
                S.GRILLE_DEPTH, M_SLOT)
    for ky in S.ROUNDKEY_Y:
        rr, w, _ = disc_blend(y, z, ky, 0.0, S.ROUNDKEY_POCKET_D * 0.5, edge=0.16)
        ring = sel & (rr < S.ROUNDKEY_POCKET_D * 0.5)
        d = np.where(ring, d * (1.0 - w) + S.ROUNDKEY_POCKET_DEPTH * w, d)
        m = np.where(ring, M_POCKET, m)
        rr2, w2, _ = disc_blend(y, z, ky, 0.0, S.ROUNDKEY_D * 0.5, edge=0.16)
        cap = sel & (rr2 < S.ROUNDKEY_D * 0.5)
        d = np.where(cap, d * (1.0 - w2) + (-S.ROUNDKEY_RISE) * w2, d)
        m = np.where(cap & (rr2 < S.ROUNDKEY_D * 0.5 - 0.08), M_KEY, m)

    # ---- parting groove runs right round the shell ------------------------
    groove = live & (np.abs(y - S.SEAM_Y) < S.SEAM_W * 0.5) & ~on_top
    put(groove, S.SEAM_D, M_SEAM)

    return d, m


# ==========================================================================
# outline of the body in XY
# ==========================================================================

class Outline:
    """Rounded rectangle, offset inward by `inset`, parameterised by arclength."""

    def __init__(self, L, W, r, inset=0.0):
        self.A = L * 0.5 - inset
        self.B = W * 0.5 - inset
        self.r = max(r - inset, 0.05)
        self.ax = self.A - self.r
        self.by = self.B - self.r
        self.seg_len = [2 * self.ax, 0.5 * math.pi * self.r,
                        2 * self.by, 0.5 * math.pi * self.r,
                        2 * self.ax, 0.5 * math.pi * self.r,
                        2 * self.by, 0.5 * math.pi * self.r]
        self.cum = np.concatenate([[0.0], np.cumsum(self.seg_len)])
        self.total = self.cum[-1]

    def point(self, s):
        """Vectorised: arclength -> (x, y, nx, ny)."""
        s = np.mod(s, self.total)
        x = np.zeros_like(s); y = np.zeros_like(s)
        nx = np.zeros_like(s); ny = np.zeros_like(s)
        c, r, ax, by, A, B = self.cum, self.r, self.ax, self.by, self.A, self.B

        def arc(mask, u, cx, cy, a0):
            ang = a0 + u / r
            x[mask] = cx + r * np.cos(ang); y[mask] = cy + r * np.sin(ang)
            nx[mask] = np.cos(ang); ny[mask] = np.sin(ang)

        k = (s >= c[0]) & (s < c[1])                       # bottom edge, -Y
        x[k] = -ax + (s[k] - c[0]); y[k] = -B; nx[k] = 0; ny[k] = -1
        k = (s >= c[1]) & (s < c[2])                       # bottom-right arc
        arc(k, s[k] - c[1], ax, -by, -0.5 * math.pi)
        k = (s >= c[2]) & (s < c[3])                       # right edge, +X
        x[k] = A; y[k] = -by + (s[k] - c[2]); nx[k] = 1; ny[k] = 0
        k = (s >= c[3]) & (s < c[4])                       # top-right arc
        arc(k, s[k] - c[3], ax, by, 0.0)
        k = (s >= c[4]) & (s < c[5])                       # top edge, +Y
        x[k] = ax - (s[k] - c[4]); y[k] = B; nx[k] = 0; ny[k] = 1
        k = (s >= c[5]) & (s < c[6])                       # top-left arc
        arc(k, s[k] - c[5], -ax, by, 0.5 * math.pi)
        k = (s >= c[6]) & (s < c[7])                       # left edge, -X
        x[k] = -A; y[k] = by - (s[k] - c[6]); nx[k] = -1; ny[k] = 0
        k = (s >= c[7])                                    # bottom-left arc
        arc(k, s[k] - c[7], -ax, -by, math.pi)
        return x, y, nx, ny

    def project(self, x, y):
        """Snap points that fall outside the outline back onto it."""
        sx = np.sign(x); sy = np.sign(y)
        dx = np.abs(x) - self.ax
        dy = np.abs(y) - self.by
        corner = (dx > 0) & (dy > 0)
        px, py = x.copy(), y.copy()
        # flat regions
        px = np.where(~corner, np.clip(x, -self.A, self.A), px)
        py = np.where(~corner, np.clip(y, -self.B, self.B), py)
        # corner regions
        cx = sx * self.ax; cy = sy * self.by
        vx = x - cx; vy = y - cy
        ln = np.maximum(np.hypot(vx, vy), 1e-9)
        scale = np.minimum(1.0, self.r / ln)
        px = np.where(corner, cx + vx * scale, px)
        py = np.where(corner, cy + vy * scale, py)
        return px, py


# ==========================================================================
# thickness profile of the rim
# ==========================================================================

def rim_profile(step_flat=0.18, step_fillet=0.12):
    """Polyline through the (n, z) cross-section of the side wall.

    Returns arrays (n, z, pn, pz, flat, arclen) where (pn, pz) is the outward
    surface normal in the cross-section plane.
    """
    R = S.R_EDGE
    n_list, z_list, pn, pz, fl = [], [], [], [], []

    k = max(3, int(round((0.5 * math.pi * R) / step_fillet)))
    for i in range(k + 1):                      # front fillet, 90deg -> 0deg
        a = 0.5 * math.pi * (1.0 - i / k)
        n_list.append(-R + R * math.cos(a)); z_list.append(S.Z1 - R + R * math.sin(a))
        pn.append(math.cos(a)); pz.append(math.sin(a)); fl.append(0.0)

    zt, zb = S.Z1 - R, S.Z0 + R
    k = max(2, int(round((zt - zb) / step_flat)))
    for i in range(1, k):                       # straight side
        z = zt + (zb - zt) * i / k
        n_list.append(0.0); z_list.append(z)
        pn.append(1.0); pz.append(0.0); fl.append(1.0)

    k = max(3, int(round((0.5 * math.pi * R) / step_fillet)))
    for i in range(k + 1):                      # back fillet, 0deg -> -90deg
        a = -0.5 * math.pi * (i / k)
        n_list.append(-R + R * math.cos(a)); z_list.append(S.Z0 + R + R * math.sin(a))
        pn.append(math.cos(a)); pz.append(math.sin(a)); fl.append(0.0)

    n = np.array(n_list); z = np.array(z_list)
    seg = np.hypot(np.diff(n), np.diff(z))
    arclen = np.concatenate([[0.0], np.cumsum(seg)])
    return n, z, np.array(pn), np.array(pz), np.array(fl), arclen


# ==========================================================================
# mesh assembly
# ==========================================================================

class Mesh:
    def __init__(self):
        self.P = []      # positions
        self.UV = []
        self.MAT = []
        self.F = []
        self.nvert = 0

    def add_grid(self, P, UV, MAT, flip=False):
        """P, UV, MAT are (rows, cols, k) arrays; emit a quad grid."""
        rows, cols = P.shape[0], P.shape[1]
        base = self.nvert
        self.nvert += rows * cols
        self.P.append(P.reshape(-1, 3))
        self.UV.append(UV.reshape(-1, 2))
        self.MAT.append(MAT.reshape(-1))
        idx = base_index(base, rows, cols, flip)
        self.F.append(idx)

    def finish(self):
        P = np.concatenate([np.asarray(p, dtype=np.float64) for p in self.P])
        UV = np.concatenate([np.asarray(u, dtype=np.float64) for u in self.UV])
        MAT = np.concatenate([np.asarray(m, dtype=np.int32) for m in self.MAT])
        F = np.concatenate(self.F)
        # drop degenerate triangles created by corner projection
        a, b, c = P[F[:, 0]], P[F[:, 1]], P[F[:, 2]]
        area = np.linalg.norm(np.cross(b - a, c - a), axis=1)
        F = F[area > 1e-9]
        N = vertex_normals(P, F)
        return P, N, UV, MAT, F


_offsets = {}


def base_index(base, rows, cols, flip):
    key = (rows, cols, flip)
    if key not in _offsets:
        i = np.arange(rows - 1)[:, None] * cols + np.arange(cols - 1)[None, :]
        i = i.reshape(-1)
        a = i; b = i + 1; c = i + cols; d = i + cols + 1
        if flip:
            tri = np.concatenate([np.stack([a, c, b], 1), np.stack([b, c, d], 1)])
        else:
            tri = np.concatenate([np.stack([a, b, c], 1), np.stack([b, d, c], 1)])
        _offsets[key] = tri
    return _offsets[key] + base


def vertex_normals(P, F):
    N = np.zeros_like(P)
    a, b, c = P[F[:, 0]], P[F[:, 1]], P[F[:, 2]]
    fn = np.cross(b - a, c - a)          # area weighted
    for k in range(3):
        np.add.at(N, F[:, k], fn)
    ln = np.linalg.norm(N, axis=1, keepdims=True)
    return N / np.maximum(ln, 1e-12)
