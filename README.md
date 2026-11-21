# Neptune 2 · Parametric 2020 Extrusion Display Mount · V009

**Current design: one integral structural display mount + one removable M4 keeper.** The curved side arms are the vertical PCB mounting rails. There is no intervening carrier, rear display sheet, or transverse screw-tab attachment. All four M3 mounting holes and their rear driver corridors are machined parametrically into the **main structural arm BREP**.

The 20 × 20 × 120 mm two-face-slotted reference extrusion is the original unmodified `reference/2020-2O_rail.step`, rigidly positioned along X. The saddle index key enters its existing upper slot. The main frame is centered on the rail and holds the screen upright at 90° to the saddle's inside horizontal bearing face.

> **Provisional engineering model:** display, PCB hole coordinates, M3 head type/length, SD slot and USB connector clearance are not physically measured. Do not treat a nominal BREP collision pass as real-world fit or strength approval.

## Geometry-derived previews

Every image below is rendered from the generated CAD geometry and committed to the repository with the STEP/STL files.

**Complete assembly** — translucent blue rectangle is a provisional display bounding reference, not a printable plate.

![V009 complete assembly and 2020 extrusion](previews/assembly_isometric.png)

**One-piece structural frame** — both arm faces carry their own M3 screw mounting interfaces.

![V009 one-piece integrated main frame](previews/main_frame_only.png)

**Integral M3 mounting and driver access** — these are arm features, not separate rail parts.

![V009 integral display mounting interface](previews/integrated_display_mount.png)

![V009 rear M3 driver access and M4 keeper](previews/rear_screw_access.png)

**Engineering side profile**, including open front service access and preserved rear slope.

![V009 orthographic side datum](previews/engineering_side_profile.png)

**Assembly side angle and lower 2020 clamp.**

![V009 side section](previews/side_section.png)

![V009 saddle and removable keeper](previews/saddle_clamp.png)

## Single-piece mounting architecture

The two 16 mm-thick sculpted arms themselves comprise the entire rear PCB mounting structure. Their center spacing and the mounting-hole X spacing are independent config variables, but any relative offset must preserve the minimum material around all driver passages.

Each M3 station contains a centered Ø3.4 mm forward through-bore, an internal Ø6.4 mm head seat, and an axial Ø7 mm driver/head passage that continues toward the rear. The forward screw-head bearing floor remains 3.2 mm thick by default (3.0 mm minimum); the radial wall is validated against the complete arm thickness. No rectangular PCB backing plane, separate mounting carrier, rail step, or outboard screw tabs are manufactured.

The side-facing access cutout is parameterized separately for SD and USB service. Its open throat remains approximately Y=0–20 mm and Z=60–80 mm, with an uninterrupted diagonal back rib. To keep both M3 seats out of that open service throat, their temporary vertical coordinates are now S=20 and S=65 mm. **These screw locations are construction candidates, not measurements of your PCB.**

| Config key | Default | Purpose |
|---|---:|---|
| `support_arm_center_spacing_mm` | 78 mm | Symmetric arm X pitch |
| `arm_thickness_mm` | 16 mm | Integrated structural arm width |
| `mount_hole_center_spacing_mm` | 78 mm | M3 hole X pitch; constrained to arm material |
| `board_screw_station_center_mm` | 42.5 mm | Vertical fastener midpoint, S datum |
| `board_screw_vertical_pitch_mm` | 45 mm | Two M3 Z stations per arm |
| `board_screw_clearance_d_mm` | 3.4 mm | M3 through-hole |
| `board_screw_head_access_d_mm` | 6.4 mm | Internal head seat diameter |
| `board_driver_access_d_mm` | 7.0 mm | Continuous rear insertion corridor |
| `mount_pad_axial_thickness_mm` | 6.2 mm | Front seat plus head depth |
| `board_counterbore_depth_mm` | 3.0 mm | M3 head seat axial depth |
| `min_screw_head_floor_mm` | 3.0 mm | Required front bearing floor |
| `min_screw_head_radial_wall_mm` | 2.5 mm | Required side arm material |
| `display_angle_deg` | 90° | Mount upright relative to 2020 saddle |

The right-handed coordinate system is X along extrusion/screen width, Y front-to-back, Z upward. `S` is vertical distance upward from the support front datum at Z=33 mm. The side holes and the arm outer profile are symmetric about X=0; both service branches remain separately configurable.

## Manufacturing and Onshape files

| Item | STEP | STL | Role |
|---|---|---|---|
| **Integrated main frame** | [main.step](step/main.step) | [main.stl](stl/main.stl) | One 3D-printable structural body with four integral M3 pockets |
| **Removable lower keeper** | [keeper.step](step/keeper.step) | [keeper.stl](stl/keeper.stl) | Second printable body, with M4 clamp channels |
| Full V009 reference assembly | [assembly](step/COMPLETE_2020_TOUCHSCREEN_ASSEMBLY_V009.step) | — | Main + keeper + source rail + screen envelope + screw references |
| Printable two-body assembly | [main + keeper](step/PRINTABLE_PARTS_V009.step) | — | Only actual intended printed parts |
| Arm diagnostics | [left](step/left_arm.step) · [right](step/right_arm.step) | — | Subsolids already included in main; **do not print separately** |
| 2020 STEP reference | [rail](step/rail.step) | — | Real supplied section, rigidly oriented |
| Display M3 screw references | [M3 screws](step/M3_DISPLAY_SCREWS_REFERENCE.step) | — | Provisional hardware visualization |

Onshape: import the V009 full assembly STEP with **Y-axis up unchecked** (+Z is up). It provides independent editable solids, but parametric feature history remains in [src/build.py](src/build.py) and [config/mount_spec.json](config/mount_spec.json), not in Onshape's imported STEP feature tree.

## Regeneration

`/src/build.py`

```bash
python -m pip install -r requirements.txt
xvfb-run -a python src/build.py
python -m unittest discover -s tests -v
```

Changes to CAD geometry must commit updated STEP/STL, all rendered previews and [docs/validation.json](docs/validation.json). [V009 integral-arm design contract](docs/V009_INTEGRAL_ARMS.md) distinguishes the screen-facing bore, head-seat shoulder and rear insertion corridor.

**Measure before printing:** actual PCB hole X/Z pitch and thread type, M3 head profile and effective engagement, display/port extents, printer top rail slots and clearances, nozzle/bed motion envelope, torque, load direction and printed-layer strength.
