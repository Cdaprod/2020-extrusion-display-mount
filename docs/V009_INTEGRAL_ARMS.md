# V009 correction — M3 display mounts are built INTO the two structural arms

## Source of change

The V009 screenshot showed rectangular carrier rails with extra sideward screw pads. Those parts were fused to the printable main BREP but retained the wrong geometry and manufacturing architecture. This correction eliminates the separate carrier-rail solids entirely, not merely their export labels.

## Parametric design

- The two actual load-bearing profile arms are each 16 mm wide in X, centered at X=±39 mm and fused with the keyed 2020 saddle and rear cross tie.
- Four M3 holes are machined directly through the arm front: the two mounting X stations are independently adjustable but constrained within the arm web, retaining at least 2.5 mm material beside each rear-driver passage.
- Provisional vertical mounting stations S=20 and S=65 mm keep the M3 bearing rings away from the cutout at Z≈60–80. Real PCB measurements supersede those coordinates.
- The Ø3.4 mm forward bore crosses the remaining 3.2 mm front floor and integral display standoff.
- The Ø6.4 mm head seat is 3.0 mm axially deep; a Ø7 mm access corridor runs rearward from that seat beyond the back of the structural arm. An M3 head can enter from the rear and clamp against the retained annular floor.
- The front side U access slots remain independently configured for SD/USB service, but are prohibited from intersecting the head-bearing region. The outer diagonal spine is continuous.
- No intermediate display carrier, additional back plate, lateral screw-tab pads or separately printable interface rails.

## Deliverables

Two intended printed parts: `main.step`/`main.stl` and `keeper.step`/`keeper.stl`. Full assembly STEP also contains the unchanged 2020 source rail and provisional screen/screw references. Legacy `carrier.step`, `carrier.stl` and `display_carrier.png` are removed.

Each GitHub CI build must regenerate actual STEP/STL/PNG files, run focused nominal BREP tests and commit all artifacts to the feature branch before merging.

This is CAD validation only, not verified physical PCB or thermal/fatigue fit.
