# Prototype SP-1 Stem Player — measured dimensions

Model marking: `YZY0020SP01Y4KNGK17` · `contains FCC-ID WAP3027`
"designed and engineered by kanye west and teenage engineering"

Every dimension here was derived from the photographs in [`photos/`](photos/).
No manufacturer drawing was used — nothing authoritative is published for this
prototype — so each number states how it was obtained and how much to trust it.

## Headline dimensions

| Axis | Value | Confidence |
|---|---|---|
| Long axis (X) | **64.0 mm** | ±0.8 mm |
| Short axis (Y) | **47.0 mm** | ±0.7 mm |
| Thickness (Z) | **9.4 mm** | ±0.4 mm |
| Corner radius | 2.6 mm | ±0.3 mm |
| Front/back edge fillet | 0.9 mm | ±0.2 mm |

## How the size was established

The tape-measure photographs alone were not conclusive — the same short axis
read **46.0 mm** in one shot and **48.3 mm** in another, because a tape lying
across a curved bedspread is not a straight edge and the labels are printed
slightly off their ticks. So the tape was used only to fix the *absolute
scale*, and the *proportions* came from photogrammetry:

1. **Perspective rectification.** The main front panel was isolated as a
   connected bright/desaturated blob; its four edges were fitted with RANSAC
   lines and intersected to give four corners. A homography then mapped that
   quadrilateral onto a flat canvas, removing the camera's perspective. The
   same was done for the back plate and, later, for each of the four edges.

2. **Recovering the true aspect ratio.** A homography from four corners is
   exact, but leaves the horizontal:vertical scale ratio free. The four
   indicator LEDs are circular holes, so their measured second moments pin it
   down: σx/σy came out at **0.795 ± 0.010** across all four dots, giving a
   main-panel aspect of **1.677**.

3. **Scale from the tape.** Averaging the three usable tape readings
   (4.60, 4.68, 4.83 cm for the short axis) gives 47.0 mm, which the 1.677
   panel aspect and the measured cap-to-panel ratio turn into 64.0 mm long.

4. **The consistency check that closed it.** With those numbers the four
   slider rows land 5.67 mm from the top of the main panel and 5.71 mm from
   the bottom — symmetric to within 0.04 mm, which is what a designer would
   have drawn. Independent slider-pitch estimates from two different
   photographs (9.03 mm and 9.24 mm) bracket the rectified value of 8.93 mm.

The thickness came from the two edge-on tape shots (9.65 mm) and from the
port-face length:width ratio (9.13 mm); 9.4 mm splits them.

### What the straight-on edge shots corrected

A later set of four photographs, each shot perpendicular to one edge, was
rectified the same way and revised several numbers that the earlier angled
shots had got wrong:

- The **slider knobs stand 1.55 mm proud** of the front face, not the ~0.3 mm
  a flat-on photograph suggests. Seen edge-on they are clearly little posts.
- The **−Y long edge has its own key and pinhole** — it is not blank.
- The three **connectors are not evenly spaced**. The earlier estimate of a
  uniform 13.4 mm pitch was an artefact of a foreshortened view; the real
  spacings are 13.2 mm and 9.6 mm.
- The **status LEDs sit at a 2.37 mm pitch** and what looked like a second
  pinhole is simply the fourth, unlit LED.
- The **speaker grille pitch is 2.00 mm** and the round keys are Ø 5.05 mm.

## Orientation

`+X` → speaker end · `+Y` → cap / top-edge keys · `+Z` → out of the front face

The model is the **mirror image** of the way the reference photographs were
laid out, confirmed against the physical unit. Rather than negating every X
constant, `spec.MIRROR_X` applies the flip once — where the fields are
evaluated and where the photographs are sampled. Set it to `False` to get the
un-mirrored arrangement back.

## Layout (millimetres, origin at the body centre)

Positions below are given in the spec's own pre-mirror coordinates, which is
how they appear in `model/spec.py`.

### Front face
| Feature | Value |
|---|---|
| Cap strip height (from +Y edge) | 8.87, parting line at Y = +14.63 |
| Control rows (Y) | +8.96, +0.03, −8.90, −17.83 (pitch 8.93) |
| Slider pocket | X −6.40 … +6.50, 2.70 tall, 0.42 deep |
| Slider slot | 11.70 × 1.50, 0.95 deep |
| Slider knob | Ø 2.45, parked at X = −4.95, **1.55 proud** |
| Indicator LED | Ø 0.80 at X = +12.70 |
| Buttons | X +17.18 … +23.73 (6.55 × 2.70), 0.10 proud in a 0.46 pocket |
| Red index triangle | 2.05 × 2.20 at (−20.29, +18.80) |
| Cap blind holes | Ø 0.92 at X = +19.73 and +21.30 |

### +Y long edge
| Feature | Value |
|---|---|
| Two keys | 11.20 (X) × 5.60 (Z), 1.72 proud, centres X = −20.40 and +20.95 |
| Status LEDs | 4 × Ø 0.55 at X = −3.80, −1.43, +0.94, +3.31 |
| Microphone pinhole | Ø 0.85 at X = +6.50 |

### −Y long edge
| Feature | Value |
|---|---|
| One key | 10.30 × 5.20, 1.45 proud, centre X = −20.80 |
| Pinhole | Ø 0.85 at X = −7.00 |

### Connector end
| Feature | Value |
|---|---|
| 3.5 mm jacks | Ø 3.90 at Y = +8.80 and −0.80 |
| USB-C | 9.10 × 3.20 at Y = −14.00 |

### Speaker end
| Feature | Value |
|---|---|
| Grille | 2 columns × 5 rows of Ø 0.85 holes, 2.00 row pitch, 1.45 column pitch |
| Round keys | 2 × Ø 5.05 at Y = −8.80 and −15.90 |

### Back plate
| Feature | Value |
|---|---|
| Screws | Ø 3.00 counterbores at (−29.00, +11.73) and (+29.00, −21.00) |
| Etching | lifted directly from the rectified photograph |

## Known uncertainties

- **The cap.** Whether the +Y strip is a removable cap, a battery door or
  simply a second extrusion is not determinable from the photographs. It is
  modelled as a flush piece with a 0.16 mm parting groove running right round
  the shell. The front panel puts its height at 8.87 mm; the rectified
  connector-end shot says 8.0 mm. The larger figure is used.
- **The two keys on the +Y edge** stand 1.72 mm proud, measured from their
  silhouette in the straight-on front photograph. That is a lot of travel for
  a key, so it may include a pocket rim the silhouette cannot separate.
- **Internal depths** (how far the jack barrels actually go) are modelled to
  plausible values, not measured — the photographs cannot see inside.
- **Which way round the long edges run.** Both long-edge photographs are
  symmetrical enough that nothing in them fixes which end is which; the
  assignment follows the connector end.
