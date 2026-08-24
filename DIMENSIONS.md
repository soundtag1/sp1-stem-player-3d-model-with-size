# Prototype SP-1 Stem Player — measured dimensions

Model marking: `YZY0020SP01Y4KNGK17` · `contains FCC-ID WAP3027`
"designed and engineered by kanye west and teenage engineering"

Every dimension here was derived from the photographs in [`photos/`](photos/).
No manufacturer drawing was used — nothing authoritative is published for this
prototype — so each number below states how it was obtained and how much to
trust it.

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
   same was done for the back plate.

2. **Recovering the true aspect ratio.** A homography from four corners is
   exact, but leaves the horizontal:vertical scale ratio free. The four
   indicator LEDs are circular holes, so their measured second moments pin it
   down: σx/σy came out at **0.795 ± 0.010** across all four dots, giving a
   main-panel aspect of **1.677**.

3. **Scale from the tape.** Averaging the three usable tape readings
   (4.60, 4.68, 4.83 cm for the short axis) gives 47.0 mm, which the 1.677
   panel aspect and the measured cap-to-panel ratio turn into 64.0 mm long.

4. **The consistency check that closed it.** With those numbers the four
   slider rows land at 5.67 mm from the top of the main panel and 5.71 mm
   from the bottom — symmetric to within 0.04 mm, which is what a designer
   would have drawn. Independent slider-pitch estimates from two different
   photographs (9.03 mm and 9.24 mm) bracket the rectified value of 8.93 mm.

The thickness came from the two edge-on tape shots (9.65 mm) and from the
port-face length:width ratio (9.13 mm); 9.4 mm splits them.

## Layout (millimetres, origin at the body centre)

`+X` → connector end · `+Y` → cap / top-edge keys · `+Z` → out of the front face

### Front face
| Feature | Value |
|---|---|
| Cap strip height (from +Y edge) | 8.87, parting line at Y = +14.63 |
| Control rows (Y) | +8.96, +0.03, −8.90, −17.83 (pitch 8.93) |
| Slider pocket | X −6.40 … +6.50, 2.70 tall, 0.42 deep |
| Slider slot | 11.70 × 1.50, 0.95 deep |
| Slider knob | Ø 2.45, parked at X = −4.95, 0.34 proud |
| Indicator LED | Ø 0.80 at X = +12.70 |
| Buttons | X +17.18 … +23.73 (6.55 × 2.70), 0.10 proud in a 0.46 pocket |
| Red index triangle | 2.05 × 2.20 at (−20.29, +18.80) |
| Cap blind holes | Ø 0.92 at X = +19.73 and +21.30 |

### +Y long edge
| Feature | Value |
|---|---|
| Two keys | 10.90 (X) × 5.60 (Z), **1.72 proud**, centres X = ±20.09 |
| Microphone pinhole | Ø 0.90 at X = −5.20 |
| Second pinhole | Ø 0.55 at X = −2.10 |
| Status LEDs | 4 × Ø 0.70 at X = 0.20, 2.00, 3.80, 5.60 |

### +X end — connectors
| Feature | Value |
|---|---|
| 3.5 mm jacks | Ø 4.20 at Y = +13.40 and 0.00 |
| USB-C | 8.90 × 3.20 at Y = −13.40 |

The three connectors are evenly spaced at a 13.4 mm pitch — measured
independently as 13.36 and 13.52 mm, which is the clearest sign the
rectification is sound.

### −X end — speaker and round keys
| Feature | Value |
|---|---|
| Grille | 2 columns × 5 rows of Ø 0.85 holes, 2.12 row pitch, 1.45 column pitch |
| Round keys | 2 × Ø 4.90 at Y = −7.53 and −16.91 |

### Back plate
| Feature | Value |
|---|---|
| Screws | Ø 3.00 counterbores at (−29.00, +11.73) and (+29.00, −21.00) |
| Etching | lifted directly from the rectified photograph (see below) |

## Known uncertainties

- **Handedness.** Which short end carries the connectors was corrected on
  feedback from the owner; the back-plate etching orientation follows the
  rectified photograph, and the screw positions were then matched to it.
- **The cap.** Whether the +Y strip is a removable cap, a battery door or
  simply a second extrusion is not determinable from the photographs. It is
  modelled as a flush piece with a 0.16 mm parting groove running right round
  the shell.
- **The two keys on the +Y edge** stand 1.72 mm proud, measured from their
  silhouette in the straight-on front photograph. That is a lot of travel for
  a key, so it may include a pocket rim that the silhouette cannot separate.
- **Internal depths** (how deep the jack barrels actually go) are modelled to
  plausible values, not measured — the photographs cannot see inside.
