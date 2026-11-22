# V013 — Expanded U openings, rear screwdriver exits, structural envelope

## Scope
V012 main frame was a connected single solid with a front-open U in each arm, but the opening was undersized relative to the support envelope visible in the user markup. V013 removes additional YZ material while retaining four front screw seats and a continuous gusset-to-saddle load path. The user selected enclosed rear tool bores where enough material exists.

## Dimensions and constraints (nominal, mm)
| Feature | V012 | V013 |
|---|---:|---:|
| Lower cut Z | 64 | 63 |
| Upper cut Z | 86 | 88 |
| Lower rear U Y | 40 | 45 |
| Upper rear U Y | 30 | 36 |
| Internal cutter fillet R | 5 | 6 |
| Minimum rear web at aperture ends | 8 (roof only) | 8 (upper + lower) |
| Screw stations Z | 53 / 98 | 53 / 98 |
| Driver channel | Ø7 | Ø7, positive-Y through-exterior exit |
| M3 head seat | Ø6.4 | Ø6.4 (unchanged) |
| Nominal axial head floor | 3.2 | 3.2 |

The Y-direction wall web is a **nominal profile bound**, not a 3D FEA stress/safety-factor conclusion. Fillet support and minimum radial material should be physically printed and checked. In the side profile at the lower opening end, the exterior bound is linearly interpolated between the outer lower-rear point and bulge; at the upper opening, the exterior is interpolated between rear bulge and upper shoulder. Reject impossible dimensions. Screw pitches/positions continue to parameterize both cut ends. Both arms are reflected across X and must remain connected, watertight and interfere with neither the reference 2020 rail nor the removable keeper.

Each screwdriver passage begins behind the 3.2 mm screw-bearing floor and is cut longitudinally through positive Y for at least `max(configured_length, rear-most arm Y - start + 5 mm)`. The cutter must remove no screw-head bearing floor. The finished arm is probed with a Ø7 cylinder at each fastener height, and no rear obstruction is allowed.

## Retained fit caveat
The selected mounting pads in the supplied Waveshare `0820-1.stp` have native X pitch 114 mm, Y pitch 59.1 mm and Ø2 mm holes. This provisional V013 support still uses 78×45 mm M3 positions. `reference/waveshare_0820_1_mounting_datums.json` is an independently measured fixture only. Do not claim compatibility until bracket coordinate transform and mounting redesign are verified.

## Production gate
Generate and commit `step/main.step`, `stl/main.stl`, `step/COMPLETE_2020_TOUCHSCREEN_ASSEMBLY_V013.step`, `step/PRINTABLE_PARTS_V013.step`, geometry-derived `previews/*.png`, and `docs/validation.json`. Tests and generated STEP/STL timestamps must agree with this version. DO NOT merge an ungenerated or failed revision.
