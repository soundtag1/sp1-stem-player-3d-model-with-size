# Prototype SP-1 Stem Player — 3D model

A dimensionally accurate, textured 3D model of the Teenage Engineering ×
Kanye West **Prototype SP-1 Stem Player** (`YZY0020SP01Y4KNGK17`,
FCC-ID `WAP3027`), reconstructed photogrammetrically from photographs of the
physical unit.

**64.0 × 47.0 × 9.4 mm.** See [DIMENSIONS.md](DIMENSIONS.md) for every
measurement and how it was derived.

## What's here

| Path | Contents |
|---|---|
| `dist/sp1_stem_player.glb` | glTF 2.0 binary, metres, 2K PBR textures embedded |
| `dist/sp1_stem_player_photo.glb` | same mesh, textures taken straight off the photographs |
| `dist/sp1_stem_player.obj` + `.mtl` | Wavefront, millimetres |
| `dist/sp1_stem_player.stl` | binary STL, millimetres — for printing |
| `textures/` | 4K base colour, metallic-roughness and normal maps |
| `textures/photo/` | the as-shot variant of the same three maps |
| `renders/` | preview renders |
| `photos/` | the source photographs |
| `reference/` | perspective-rectified orthographic views used as texture sources |
| `model/` | the generator — everything above is reproducible from it |

## Rebuilding

```bash
pip install pillow numpy
python3 model/rectify_refs.py           # photos -> rectified orthographic views
python3 model/build_all.py              # textures, meshes, exports, renders
python3 model/build_all.py --no-render  # skip the slow preview renders
```

`model/spec.py` holds every dimension as a named constant. Change a number
there and the mesh, the textures and the renders all follow — the texture
atlas is painted by evaluating the same signed-distance fields that displace
the geometry, so pocket edges, holes and key caps stay registered to the mesh
exactly.

## How the model is built

The body is three displaced surfaces that share their boundaries:

- **front** — a height field over (x, y), clipped to the inset outline
- **back** — a height field over (x, y)
- **rim** — a height field over (arclength, thickness-profile position),
  which is how the four side faces get their jacks, grille, keys and USB-C
  cut-out without any boolean operations

Sampling is adaptive: roughly 2 mm across blank areas, down to 0.07 mm across
feature boundaries, with each boundary doubled at ±0.02 mm so pocket walls
stay crisp under smooth vertex normals while keeping a micro-chamfer.
Result: ~290 k triangles with real silhouettes on every pocket and hole.

## Textures

Base colour comes from the **photographs themselves**. All six faces —
front, back and the four edges — were perspective-rectified to true
orthographic scale, de-lit by dividing out a heavily blurred copy of
themselves, masked to the device outline with bedding and fingers filled in
from neighbouring device pixels, and resampled into the atlas. So the
aluminium tone, the scuffs along the bottom edge and the complete laser
etching on the back — the TE logo, the FCC text, the CE mark, the charge and
battery icons — are the real article rather than a redrawing.

Procedural detail fills in only what a photograph cannot give: bead-blast
micro-relief, machining rings in the pocket floors, and the knurl on the
slider knobs. The normal map carries only detail that is *not* in the mesh,
so nothing is double counted.

Two variants ship:

- **default** — de-lit albedo. Lighting comes from your renderer, which is
  what you want for a model that has to sit in a scene.
- **photo** (`textures/photo/`, `dist/sp1_stem_player_photo.glb`) — the
  rectified photographs as-is, highlights and shadows baked in. Closer to the
  snapshot, less flexible under new lighting.

## Caveats

This is a reconstruction from photographs of a prototype, not a manufacturer
CAD file. Overall dimensions are good to roughly ±0.8 mm and the internal
depths are plausible rather than measured. `DIMENSIONS.md` lists the known
uncertainties, including the orientation flip recorded in `spec.MIRROR_X`.
