# Preserved FreeCAD source

**Current:** `display-mount-working.FCStd` and `../../previews/native_equivalent_side.png`. `original-side.png` is an archived earlier state and should not be used to judge the current key alignment. The working model retains the current 15 mm rear-access pocket. The horizontal sketch placement now follows the screw pitch through a spreadsheet expression.

`display-mount-original.FCStd` is the editable checkpoint imported from the user's saved `display-mount.FCStd`. `original-brackets.step` and `original-side.png` show the checkpoint's two separate bracket solids; they are references, not a completed printable mount.

The Assembly contains a Body whose active tip is `Pocket001`: the YZ Sketch (28 elements, fully constrained) drives Pad; MultiTransform mirrors it; XY Sketch drives Pocket; Binder supplies Pocket001. The unused TabOpeningSketch and TabOpeningPocket remain in the tree, but are not the active tip. MountingParams supplies 114 mm X pitch, 59.1 mm Z pitch, 10 mm face width, 15 mm tab height, 10 mm pad depth, 4 mm datum offset, 12 mm tab projection, 13 mm access depth, 5 mm nominal web, 2 mm upper taper inset and 6 mm upper root reinforcement.

At import, Pocket001 contains two valid disconnected solids with combined bounds X −62…62, Y −13…68, Z −88.2789…44.05 mm. It does not yet include the connecting saddle or keeper.

![Preserved bracket side view](original-side.png)

## Connected working model

`display-mount-working.FCStd` preserves the original bracket Body and adds editable saddle and rear cross-member features, insert pockets, a separate keeper and a final `MountPrintable` fusion. The cross member follows the upper rear web and is flush with the outside arm faces. The original 6 mm notch key conflicted with the supplied rail STEP; the working model narrows it to 5.8 mm about the rail center. The original file remains unchanged.

The keeper is 138 × 42 × 6 mm, spans the saddle, and has four 3.4 mm clearance holes with 6 mm diameter, 3 mm deep underside counterbores aligned to 2.5 mm printed-thread M3 pilot pockets. These provisional dimensions require a fit test with the actual screws and print material. The Contoured bracket-foot clearance pocket follows the two bracket-foot positions, with 0.30 mm edge clearance and a 1.70 mm effective relief depth (1.30 mm parameter plus 0.40 mm). The keeper is initially 0.45 mm below the reference rail. Four 2.4 mm pilot-path probes were unobstructed; translations of 0.44 mm and 0.46 mm bracketed rail contact without intersecting the mount. The clearance, relief depth and initial gap are editable in MountingParams. These geometric checks do not establish actual clamping force or hardware fit.

At 53, 59.1 and 65 mm vertical pitch the native fused mount and separate keeper were valid single solids; modeled rail and keeper overlap were zero. The nominal main bounds are 138 × 81 × 132.33 mm, within the configured Neptune 2 base profile's 235 × 235 × 250 mm build volume. This is a bounding-box check only. The upper cross member and arm interiors may require supports depending on orientation; no slicer analysis has been performed.

The default Python generator retains a different curved arm profile and coordinate system. The `--native-equivalent` build mode independently reproduces the current native model; see the repository README and `previews/native_equivalent_side.png`. Its lower root-relief and front-neck blend previously rejected 65 mm pitch. The generator now shortens those transitions as the lower screw descends and locates its cross member at the upper rear web. Its full validation passed at 53, 59.1 and 65 mm; its round bosses, 16 mm arms and curved opening remain different from the native 10 mm arms and angular opening. STEP and STL files marked `working` are CAD review exports; the keeper remains a separate part.

![Connected working mount](mount-working-isometric.png)

## Centered bracket channel

The native YZ sketch uses `BracketChannelWidth = 20.15 mm`, centered on `RailCenterY = 10 mm`. The 5.8 mm slot key is centered on that datum, leaving 7.175 mm on each side of the bracket channel. The saddle's separate channel remains 20.70 mm wide and centered on the same datum, giving 7.45 mm on each side of the key. Coincidence plus horizontal and vertical constraints replace duplicate ordinate dimensions. The main `MountPrintable` fusion remains one solid; `RemovableKeeper` remains a separate body and export. Native recomputes at 53, 59.1 and 65 mm pitch remained valid, and the reference rail and keeper had zero overlap at nominal pitch.

## Separate component references — joints pending

The working document exposes linked, individually selectable right bracket, left bracket, saddle and upper crossbar under `Separate component references - joints pending`. These are parametric selections of the existing fused design in their assembly positions; the original main fusion and separate keeper are preserved. They are valid individual solids at 104, 114 and 124 mm horizontal pitch and 53, 59.1 and 65 mm vertical pitch.

These selections are not yet a bolt-together design: at nominal pitch each bracket overlaps the saddle by about 6330.67 mm³ and the upper crossbar by 800 mm³. The requested 1–2 mm locating sockets, underside fasteners and anti-rotation features still need to be designed and checked against the extrusion channel and existing keeper screws. Do not print these reference solids as an assembled kit.

## Modular assembly with locating joints

`Modular assembly (prototype joints)` contains separate left and right brackets, a saddle with the original fused lower foot and key geometry, and an upper crossbar. `Modular joint dimensions` provides a 1.5 mm locating depth and 0.2 mm lateral clearance. Each bracket has an 8 mm long keyed tongue and a 2.5 mm M3 pilot at its saddle joint; the saddle has corresponding 3.4 mm clearance bores and 6 mm × 3 mm underside counterbores. Install these two saddle-to-bracket screws before fitting the separate keeper: the keeper covers their heads.

The 8 × 10 mm rectangular crossbar engages each bracket socket by 1.5 mm, with a 0.2 mm socket clearance, side entry clearance holes and recessed heads and 2.5 mm pilots in the bar. Its length is `ScrewPitchX - TabWidth + 2 * SocketDepth`: 107 mm at 114 mm pitch. Each component was a valid single solid with zero pairwise interference at X pitches 104, 114 and 124 mm and Z pitches 53, 59.1 and 65 mm. Fused and modular designs are separate alternatives in the same document.

Dimensions are prototype values. Screw lengths, actual plastic-thread engagement, clearance, clamping and resistance to loads and rotation require physical fit and load testing; no certification is implied. The earlier `Separate component references` group remains as reference geometry and is not the assembled modular design.
