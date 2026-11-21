# V002 alignment correction — Neptune 2 2020 display mount

The user-supplied annotated V001 side datum showed the desired *carrier-to-saddle* relationship, not merely a camera-view rotation.

## Reference datums (mm)

- `X`: across the display and along the rail. The imported 120 mm long STEP rail remains symmetric about X=0.
- `Y`: front/rear. The rail center, saddle inner bearing centroid, and **front/lower display carrier datum** share Y=0.
- `Z`: vertical. The two opposed rail slots face +Z/-Z in the assembled reference, and the saddle's inner bearing surface is horizontal (normal +Z).
- The display carrier is an XZ plane: its in-plane uphill tangent is `(0,+1)` in the YZ side plane. Its normal is `(0,-1,0)`.
- **Perpendicularity:** display carrier versus horizontal saddle bearing plane = **90°**. This is the user-requested target; not a measured original tabletop-stand angle.
- The bottom carrier station is Z=33 mm (provisional), centered at Y=0. The real screen envelope, PCB holes and height remain placeholders.

## Preservation, validation, and fit scope

The corrected main frame consists of **two open triangular side supports + one upright perforated carrier + the 2020 upper split saddle**, fused into a single connected body. A lower keeper is independently removable. Its four M4 candidate screw bores and the carrier's four M2.5 candidate PCB screw passages are retained. Driver-path checks are run from the rear. Exact reference STEP bytes remain in `reference/2020-2O_rail.step`.

Rebuild with `xvfb-run -a python src/build.py`, then `python -m unittest discover -s tests -v`. `previews/engineering_side_profile.png` and all STEP/STL files derive from this source.

CAD validity does **not** establish real fit to the Neptune 2 upper extrusion, wall strength, screw engagement, PCB hardware compatibility, thermal performance, or motion-envelope safety. Do not install without measurements and physical testing.

V001 exports are retained as historical artifacts; use the **V002** full-assembly and printable-part filenames for the corrected geometry.
