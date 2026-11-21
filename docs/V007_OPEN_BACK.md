# V007 — Open-backed display mounting rails and lateral service access

Source: user's photos of physical black triangular desktop stand and blue rear display PCB (November 2026); user-approved V006 sculpted envelope; cumulative [Issue #6](https://github.com/Cdaprod/2020-extrusion-display-mount/issues/6).

## V007 geometry

Two independent narrow mounting rails replace the former 176 × 80 mm backing plate. Each rail follows the **same X/S local datum** as its corresponding pair of provisional M2.5 mounting holes. Every hole, PCB standoff, through-bore, and screw-head counterbore is cut from the rail itself. Rails are 22 mm wide × 6 mm thick and merge with both structural side arms; their central/rear span is **empty**.

Left SD and right USB clearance cuts are parameterized independently. Each removes a window from the INNER edge of its respective rail while retaining at least 8 mm nominal outer spine. Clearance volumes are independent BREP solids checked against the complete printable main body. Their positions, dimensions and actual connector directions are **initial placeholders**, not inferred physical measurements.

Both support ribs retain V006 exterior arcs, gusseted saddle transition, and tangent continuity. Their enclosed trapezoidal cavity now connects to the exterior rear edge through an elongated horizontal rounded throat: left width 13 mm at Z=71 mm, right width 17 mm at Z=75 mm. Front structural ligament is at least 12 mm nominal. The cutter is a physically open CSG void, not a sketch-only illustration, and a rear entry probe confirms it reaches the service cavity.

## Fasteners and load path

- M2.5 candidates: four vertically paired holes recessed from the rear INSIDE face of the two rails, entering toward PCB bosses. Screw heads remain reachable from the open rear volume.
- M4 candidates: four screws clamp the existing lower keeper to the keyed upper saddle around the unchanged 2020 rail.
- Side-arm branches remain joined through their carrier-side ligament and saddle; no force-bearing snap tabs.
- PCB clearance, cable extraction and mechanical strength still need measured hardware fit and load validation.

## Manufacturing acceptance

One CadQuery main solid, one removable keeper, source STEP rail unmodified, 2 separate rail reference STEP solids, real side/rear previews, plus versioned V007 assembly and printable-parts STEP. The lightweight regression suite checks key topology, interference, access and output existence. A pass is only a nominal CAD condition, not a strength certification.

Adjust all values in `config/mount_spec.json`; source `src/build.py` remains authoritative.
