# V010 — tapered integral bosses and print-friendly curved edges

The red-marked oversized V009 screw-station tabs were not independent parts: they were the broad front faces of the structural arms. V010 narrows only the *forward portion* of each arm with symmetric XY wedge cuts. The forward profile is now 12 mm wide around the Ø7 rear access bore, retaining 2.5 mm minimum wall per side; over an 8.5 mm Y-depth it widens continuously back to the 16 mm diagonal structural arm. These are **drafted surfaces**, not detached tabs or perpendicular pads.

The upper front end is parametrically reduced to 9.5 mm above the upper M3 axis, rather than extending to the previous screen-envelope height. This value is constrained against the Ø7 driver corridor and radial wall minimum. Analytic G1 tangent radii now soften the upper/front cap (2 mm), lower/front root (2 mm), toe (1.5 mm) and the previously curved rear profile (5/6/7 mm). Keeper exterior vertical corners receive a 1 mm fillet; M4 hole seats and mating datums remain unchanged.

Critical preserved constraints: four integrated M3 stations, Ø3.4 through-bore, Ø6.4 head seat, Ø7 rear driver corridor, minimum 3 mm axial head-bearing floor, ≥2.5 mm radial wall at the new *minimum* boss width, SD/USB front opening, rear diagonal, 2020 key and removable M4 keeper.

All parameters are editable in `config/mount_spec.json`. CAD solid validity and tool access are tested, but these checks do not prove FDM fatigue strength, support-free printability, or hardware fit. Exclude mating surfaces and critical tool/screw holes from indiscriminate global chamfers/fillets.
