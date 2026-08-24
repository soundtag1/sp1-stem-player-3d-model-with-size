"""
Texture atlas generation: base colour, metallic/roughness and normal maps.

The atlas is painted by evaluating the same signed-distance fields that drive
the geometry, so every pocket edge, hole and key cap lines up with the mesh
exactly.  Fine detail that is too small to be worth meshing - the bead blast
of the anodised shell, the laser etching on the back plate, the knurl on the
slider knobs, machining rings in the pocket floors - is carried in the normal
map instead.
"""

from __future__ import annotations

import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import spec as S
import geometry as G
import build_mesh as B

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
FONT = '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'

PPM_ATLAS = B.FRONT_RECT[2] / S.L        # ~31.75 texels per millimetre


# --------------------------------------------------------------------------
# noise helpers
# --------------------------------------------------------------------------

def value_noise(shape, cell, seed=0):
    """Smooth value noise by bilinear upsampling of a coarse random grid."""
    rng = np.random.default_rng(seed)
    h = max(2, int(shape[0] / cell)); w = max(2, int(shape[1] / cell))
    small = rng.random((h, w)).astype(np.float32)
    img = Image.fromarray((small * 255).astype(np.uint8)).resize(
        (shape[1], shape[0]), Image.BICUBIC)
    return np.asarray(img, dtype=np.float32) / 255.0


def fbm(shape, cells=(64, 26, 11, 5), seed=0):
    out = np.zeros(shape, dtype=np.float32)
    amp = 1.0; tot = 0.0
    for i, c in enumerate(cells):
        out += amp * value_noise(shape, c, seed + i * 17)
        tot += amp; amp *= 0.5
    return out / tot


# --------------------------------------------------------------------------
# per-region field evaluation
# --------------------------------------------------------------------------

def _region_grid(rect):
    x, y, w, h = rect
    px = np.arange(w) + 0.5
    py = np.arange(h) + 0.5
    U, V = np.meshgrid(px / w, py / h)
    return U, V, (slice(y, y + h), slice(x, x + w))


def evaluate_fields():
    """Return dicts of material id / depth arrays for each atlas region."""
    out = {}

    # ---- front -----------------------------------------------------------
    U, V, sl = _region_grid(B.FRONT_RECT)
    X = S.X0 + U * S.L
    Y = S.Y1 - V * S.W
    d, m = G.front_field(X, Y)
    out['front'] = dict(slice=sl, mat=m, depth=d, A=X, Bc=Y)

    # ---- back ------------------------------------------------------------
    U, V, sl = _region_grid(B.BACK_RECT)
    X = S.X1 - U * S.L
    Y = S.Y1 - V * S.W
    d, m = G.back_field(X, Y)
    out['back'] = dict(slice=sl, mat=m, depth=d, A=X, Bc=Y)

    # ---- rim -------------------------------------------------------------
    U, V, sl = _region_grid(B.RIM_RECT)
    outline = G.Outline(S.L, S.W, S.R_CORNER, inset=0.0)
    n, z, pn, pz, flat, arclen = G.rim_profile()
    s = U * outline.total
    al = V * arclen[-1]
    nn = np.interp(al, arclen, n)
    zz = np.interp(al, arclen, z)
    fl = np.interp(al, arclen, flat)
    ox, oy, onx, ony = outline.point(s.ravel())
    ox = ox.reshape(s.shape); oy = oy.reshape(s.shape)
    onx = onx.reshape(s.shape); ony = ony.reshape(s.shape)
    x0 = ox + onx * nn; y0 = oy + ony * nn
    d, m = G.rim_field(x0, y0, zz, onx, ony, fl)
    out['rim'] = dict(slice=sl, mat=m, depth=d, A=x0, Bc=y0, Z=zz,
                      nx=onx, ny=ony)
    return out


# --------------------------------------------------------------------------
# material lookup tables
# --------------------------------------------------------------------------
#                        base rgb            rough  metal
MATERIALS = {
    G.M_ALU:    (S.COL_ALU,        0.42, 0.88),
    G.M_POCKET: (S.COL_ALU_DARK,   0.52, 0.85),
    G.M_SLOT:   (S.COL_SLOT,       0.72, 0.05),
    G.M_KEY:    (S.COL_PLASTIC,    0.34, 0.02),
    G.M_KNOB:   (S.COL_PLASTIC,    0.30, 0.02),
    G.M_CHROME: (S.COL_CHROME,     0.24, 0.95),
    G.M_SEAM:   ((150, 149, 145),  0.58, 0.80),
}


# --------------------------------------------------------------------------
# back plate etching, lifted from the rectified photograph
# --------------------------------------------------------------------------

def back_etch_mask(shape):
    """Binary-ish mask of the laser etched marks on the back plate.

    Falls back to a drawn approximation if the rectified reference is absent.
    """
    ref = os.path.join(REPO, 'reference', 'rect_back.png')
    H, W = shape
    mask = np.zeros(shape, dtype=np.float32)
    if not os.path.exists(ref):
        return mask

    src = Image.open(ref).convert('L')
    a = np.asarray(src, dtype=np.float32)
    ppm = 40.0                       # the reference is rendered at 40 px/mm
    # the main back plate occupies these rows/cols of the reference
    y0 = int(2.40 * ppm); y1 = int(40.50 * ppm)
    plate = a[y0:y1, :]
    # local background = heavily blurred copy, so glare is divided out
    bg = np.asarray(Image.fromarray(plate.astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(28)), dtype=np.float32)
    rel = plate / np.maximum(bg, 1.0)
    etch = np.clip((0.86 - rel) / 0.16, 0.0, 1.0)

    # place it into the back region: v spans SEAM_Y..Y0
    v0 = (S.Y1 - S.SEAM_Y) / S.W
    rows = int(round(v0 * H))
    tgt_h = H - rows
    im = Image.fromarray((etch * 255).astype(np.uint8)).resize((W, tgt_h), Image.LANCZOS)
    mask[rows:, :] = np.asarray(im, dtype=np.float32) / 255.0
    # keep only confident marks
    mask = np.clip((mask - 0.30) / 0.55, 0.0, 1.0)
    return mask


# --------------------------------------------------------------------------
# photographic albedo
# --------------------------------------------------------------------------
# The rectified references are true-scale orthographic views at 40 px/mm.
# These constants say where the device sits inside each of them, in mm.
REF_PPM = 40.0
REF_FRONT = dict(file='rect_front.png',
                 x_of_left=0.0, x_span=64.5,      # device -X edge -> +X edge
                 y_of_top=3.05, y_span=47.41)     # device +Y edge -> -Y edge
REF_BACK = dict(file='rect_back.png',
                x_of_left=0.0, x_span=64.5,
                y_of_top=2.40, y_span=38.10,      # only the plate below the seam
                y_top_is_seam=True)


def _bilinear(a, x, y):
    H, W = a.shape[:2]
    x = np.clip(x, 0, W - 1.001); y = np.clip(y, 0, H - 1.001)
    x0 = x.astype(np.int32); y0 = y.astype(np.int32)
    x1 = x0 + 1; y1 = y0 + 1
    fx = (x - x0)[..., None]; fy = (y - y0)[..., None]
    return (a[y0, x0] * (1 - fx) * (1 - fy) + a[y0, x1] * fx * (1 - fy) +
            a[y1, x0] * (1 - fx) * fy + a[y1, x1] * fx * fy)


def _delight(rgb, big=260, small=3):
    """Divide out the illumination gradient, leaving a flat albedo."""
    im = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8))
    lowf = np.asarray(im.filter(ImageFilter.GaussianBlur(big)),
                      dtype=np.float32) / 255.0
    flat = rgb / np.maximum(lowf, 0.02)
    med = np.median(flat.reshape(-1, 3), axis=0)
    flat = flat / np.maximum(med, 1e-3)
    # high frequency component - real scratches, blast texture, dust
    sm = np.asarray(Image.fromarray(
        (np.clip(flat / flat.max(), 0, 1) * 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(small)), dtype=np.float32) / 255.0
    hf = (flat / flat.max()) - sm
    return flat, hf.mean(axis=2)


def photo_layer(cfg, rect, mirror_x=False, seam_anchor=False):
    """Resample a rectified photograph into an atlas rectangle.

    Returns (albedo, highfreq, coverage) at the atlas region resolution.
    """
    path = os.path.join(REPO, 'reference', cfg['file'])
    x, y, w, h = rect
    if not os.path.exists(path):
        return None, None, None

    src = np.asarray(Image.open(path).convert('RGB'), dtype=np.float32) / 255.0
    flat, hf = _delight(src)

    # Where in the reference is the device itself?  Anything else is bedding,
    # fingers or shadow and must not leak into the albedo.
    v = src.max(axis=2)
    sat = (v - src.min(axis=2)) / np.maximum(v, 1e-6)
    dev = ((v > 0.42) & (sat < 0.17)).astype(np.float32)
    dev_img = Image.fromarray((dev * 255).astype(np.uint8))
    dev_img = dev_img.filter(ImageFilter.MinFilter(9))       # erode the border
    dev_img = dev_img.filter(ImageFilter.GaussianBlur(4))
    devm = np.asarray(dev_img, dtype=np.float32) / 255.0

    U, V = np.meshgrid((np.arange(w) + 0.5) / w, (np.arange(h) + 0.5) / h)
    # device coordinates for every texel of this atlas region
    dx = (S.X1 - U * S.L) if mirror_x else (S.X0 + U * S.L)
    dy = S.Y1 - V * S.W

    u_mm = (dx - S.X0) / S.L * cfg['x_span']
    if seam_anchor:
        v_mm = cfg['y_of_top'] + (S.SEAM_Y - dy) / (S.SEAM_Y - S.Y0) * cfg['y_span']
    else:
        v_mm = cfg['y_of_top'] + (S.Y1 - dy) / S.W * cfg['y_span']

    px = u_mm * REF_PPM
    py = v_mm * REF_PPM
    H, W = src.shape[:2]
    cover = ((px >= 0) & (px < W - 1) & (py >= 0) & (py < H - 1)).astype(np.float32)
    cover *= _bilinear(devm[..., None], px, py)[..., 0]
    albedo = _bilinear(flat, px, py)
    high = _bilinear(hf[..., None], px, py)[..., 0]
    return albedo, high, cover


def draw_cap_triangle(draw, rect, colour):
    """Red index triangle on the cap, pointing towards -X."""
    x, y, w, h = rect

    def to_px(mx, my):
        return (x + (mx - S.X0) / S.L * w, y + (S.Y1 - my) / S.W * h)

    cx, cy = S.TRI_CX, S.TRI_CY
    hw, hh = S.TRI_W * 0.5, S.TRI_H * 0.5
    pts = [to_px(cx - hw, cy), to_px(cx + hw, cy + hh), to_px(cx + hw, cy - hh)]
    draw.polygon(pts, fill=colour)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def build_atlas(verbose=True):
    W, H = B.ATLAS_W, B.ATLAS_H
    base = np.zeros((H, W, 3), dtype=np.float32)
    rough = np.full((H, W), 0.5, dtype=np.float32)
    metal = np.full((H, W), 0.0, dtype=np.float32)
    height = np.zeros((H, W), dtype=np.float32)   # micro relief, millimetres

    fields = evaluate_fields()
    if verbose:
        print('  painting material regions')
    for name, f in fields.items():
        sl = f['slice']; m = f['mat']
        b = np.zeros(m.shape + (3,), dtype=np.float32)
        r = np.zeros(m.shape, dtype=np.float32)
        mt = np.zeros(m.shape, dtype=np.float32)
        for mid, (rgb, rg, mtl) in MATERIALS.items():
            sel = m == mid
            b[sel] = np.array(rgb, dtype=np.float32) / 255.0
            r[sel] = rg
            mt[sel] = mtl
        base[sl] = b
        rough[sl] = r
        metal[sl] = mt

    # ---- photographic albedo for the two big faces ------------------------
    # How much of the real photograph to trust per material.  Slot interiors
    # keep the procedural black because the photo bakes in their shadowing.
    PHOTO_W = {G.M_ALU: 0.92, G.M_SEAM: 0.80, G.M_POCKET: 0.70,
               G.M_KEY: 0.75, G.M_KNOB: 0.70, G.M_CHROME: 0.62, G.M_SLOT: 0.30}
    if verbose:
        print('  photographic albedo (rectified references)')
    for name, cfg, rect, mirror, anchor in (
            ('front', REF_FRONT, B.FRONT_RECT, False, False),
            ('back', REF_BACK, B.BACK_RECT, True, True)):
        alb, high, cover = photo_layer(cfg, rect, mirror_x=mirror,
                                       seam_anchor=anchor)
        if alb is None:
            continue
        f = fields[name]
        sl = f['slice']; m = f['mat']
        wgt = np.zeros(m.shape, dtype=np.float32)
        for mid, wv in PHOTO_W.items():
            wgt[m == mid] = wv
        wgt *= cover
        tint = base[sl]
        # keep the procedural hue, take the photograph's value and detail
        mixed = np.clip(alb, 0.0, 1.6) * tint / np.maximum(
            np.median(alb.reshape(-1, 3), axis=0)[None, None, :], 1e-3)
        base[sl] = tint * (1.0 - wgt[..., None]) + mixed * wgt[..., None]
        # real scratches and blast texture into the bump + roughness
        alu_here = (m == G.M_ALU) | (m == G.M_SEAM)
        hh = height[sl]
        hh[alu_here] += np.clip(high, -0.25, 0.25)[alu_here] * 0.055
        height[sl] = hh
        rr = rough[sl]
        rr[alu_here] -= np.clip(high, -0.25, 0.25)[alu_here] * 0.35
        rough[sl] = rr
        if verbose:
            print(f'    {name}: {100*cover.mean():.0f}% covered by reference')

    # ---- bead blasted anodising ------------------------------------------
    if verbose:
        print('  bead blast + machining detail')
    grain = fbm((H, W), cells=(3, 2), seed=7)
    fine = value_noise((H, W), 1.6, seed=23)
    micro = (grain - 0.5) * 0.016 + (fine - 0.5) * 0.012
    alu = (metal > 0.5)
    base[alu] *= (1.0 + micro[alu] * 1.6)[..., None]
    rough += micro * 0.9
    height += (fine - 0.5) * 0.0022 + (grain - 0.5) * 0.0018

    # ---- machining rings in pocket floors --------------------------------
    for name, f in fields.items():
        sl = f['slice']; m = f['mat']
        pocket = (m == G.M_POCKET)
        if not pocket.any():
            continue
        A, Bc = f['A'], f['Bc']
        rings = np.sin((A * 9.0 + Bc * 3.0)) * 0.5 + 0.5
        h = height[sl]
        h[pocket] += (rings[pocket] - 0.5) * 0.004
        height[sl] = h
        rr = rough[sl]
        rr[pocket] += (rings[pocket] - 0.5) * 0.03
        rough[sl] = rr

    # ---- knurl on the slider knobs ---------------------------------------
    f = fields['front']
    sl = f['slice']
    knob = f['mat'] == G.M_KNOB
    if knob.any():
        A, Bc = f['A'], f['Bc']
        ribs = np.sin(np.arctan2(Bc, A - S.KNOB_X) * 26.0) * 0.5 + 0.5
        h = height[sl]
        h[knob] += (ribs[knob] - 0.5) * 0.005
        height[sl] = h

    # ---- laser etching on the back ---------------------------------------
    if verbose:
        print('  back plate etching')
    bx, by, bw, bh = B.BACK_RECT
    etch = back_etch_mask((bh, bw))
    if etch.max() > 0:
        reg = base[by:by + bh, bx:bx + bw]
        col = np.array(S.COL_ETCH, dtype=np.float32) / 255.0
        reg *= (1.0 - etch[..., None])
        reg += col[None, None, :] * etch[..., None]
        base[by:by + bh, bx:bx + bw] = reg
        rough[by:by + bh, bx:bx + bw] += etch * 0.30
        height[by:by + bh, bx:bx + bw] -= etch * 0.045     # engraved

    # ---- red index triangle ----------------------------------------------
    img = Image.fromarray((np.clip(base, 0, 1) * 255).astype(np.uint8))
    draw_cap_triangle(ImageDraw.Draw(img), B.FRONT_RECT, S.COL_RED)
    base = np.asarray(img, dtype=np.float32) / 255.0

    # ---- gentle used-unit patina -----------------------------------------
    scuff = value_noise((H, W), 90, seed=99)
    swirl = np.clip((value_noise((H, W), 6, seed=131) - 0.62) * 6.0, 0, 1)
    rough += swirl * 0.03 * (scuff > 0.55)
    height -= swirl * 0.001

    # ---- assemble the normal map -----------------------------------------
    if verbose:
        print('  differentiating height -> normal map')
    texel_mm = 1.0 / PPM_ATLAS
    gy, gx = np.gradient(height, texel_mm)
    strength = 1.0
    nz = np.ones_like(gx)
    nx = -gx * strength
    ny = gy * strength
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    normal = np.stack([nx / ln, ny / ln, nz / ln], axis=-1) * 0.5 + 0.5

    rough = np.clip(rough, 0.04, 0.98)
    metal = np.clip(metal, 0.0, 1.0)
    mr = np.stack([np.zeros_like(rough), rough, metal], axis=-1)

    to_img = lambda a: Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    return dict(base=to_img(base), mr=to_img(mr), normal=to_img(normal))


if __name__ == '__main__':
    maps = build_atlas()
    out = os.path.join(REPO, 'textures')
    os.makedirs(out, exist_ok=True)
    for k, v in maps.items():
        p = os.path.join(out, f'sp1_{k}.png')
        v.save(p, optimize=True)
        print(f'{p}  {v.size}  {os.path.getsize(p)/1e6:.2f} MB')
