# Source and provenance

- `reference/2020-2O_rail.step` is the **user-uploaded** file, copied byte-for-byte; `step/rail.step` is a rigidly oriented copy for the assembly.
- Original rail coordinates: **section X/Y ±10 mm**, **length along Z from -60 to +60 mm**, two opposite slot faces. Imported solid volume about **33082.04 mm³**.
- Assembly coordinate transform: cycle axes `(X,Y,Z)_source -> (Y,Z,X)_assembly` (120-degree right-handed rotation about axis (1,1,1)).
- Original display support and mounting location are inferred from user's photographs and two corrected hand sketches. No scale or caliper values were supplied for the actual stand or LCD.
- Inclined carrier is **recreated geometrically**, not a photo scan. Relative standoff and mount-hole positions are *candidate parameters*, not measurements.
- Generated outputs from `src/build.py` are BREP-derived. Previews are rendered from tessellated BREP, not from image generation.
