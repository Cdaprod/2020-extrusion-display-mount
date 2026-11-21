# V008 — front-access M3 rail design (parametric)

Source: the user's annotated V007 profile (Y approximately 0–20, Z 60–80) and physical display PCB photographs. This specification supersedes V007 rear-entry throat placement, without removing the support's exterior rear spine.

## Independent controlled dimensions

- `mount_rail_center_spacing_mm=56` — symmetric X center-to-center spacing of the **two vertical PCB mounting rails**; independently adjustable from support arm pitch.
- `support_arm_center_spacing_mm=78` — symmetric X center-to-center distance of the **two structural gusset arms**.
- `board_screw_station_center_mm=45.5` and `board_screw_vertical_pitch_mm=31` define the constrained pair of M3 fastener stations along Z on each rail (S = 30 and 61 mm from the display carrier datum).
- `mount_rail_lower_station_s_mm=15`, `mount_rail_upper_station_s_mm=74` trim the vertical rails to a 59 mm functional span without losing mounting screw stations.
- `arm_outer_rear_bulge_y_mm=58` and `arm_outer_lower_rear_y_mm=47` provisionally reduce superfluous rear material, preserving the saddle and the curved exterior support spine.
- The CAD rejects invalid spacing that leaves the rail disconnected from its adjacent structural arm. Both rails remain vertically constrained (90° to saddle bearing plane).

## M3 mounting hardware and printable walls

- M3 × 6–8 mm provisional screws (reference length 7 mm), 3.4 mm clearance bores.
- Recessed M3 head envelope: Ø5.6 mm × 2.9 mm; **parametric pocket Ø6.4 mm × 3.0 mm** in a **6.2 mm thick** rail.
- Floor between pocket and display face: 3.2 mm; minimum accepted floor is 3.0 mm.
- Side-wall ligament about the pocket: (20–6.4)/2 = 6.8 mm, minimum accepted 2.5 mm.
- All four bores, recesses and standoffs are cut from their corresponding rails and move automatically when rail pitch or hole pitch changes. Exact fastener head shape, thread engagement and PCB brass insert depths are unmeasured.

## Side-opening correction

V007 cut the outer/back diagonal at Y ≈ 50–60 mm. V008 instead cuts an **open front-access branch** at approximately Y 0–20 mm, Z 60–80 mm into the tapered inner cavity. It deliberately leaves the back tapered spine continuous. The branch is independently parameterized by side, while the SD-card and USB rail-side cutouts remain configurable.

## Acceptance

Generate actual CAD STEP, STL and preview PNG artifacts from source. Confirm main frame connectivity, original 2020 rail collision-free, 4 driver access corridors and 2 PCB/port service volumes. This is nominal mechanical CAD, not measured hardware fit or finite element strength validation.
