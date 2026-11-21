# Codex engineering instructions

- `reference/2020-2O_rail.step` is the canonical uploaded extrusion reference. Do not remodel or modify it, except by applying a rigid assembly transform.
- All dimensional changes must be expressed as modifications to `config/mount_spec.json` or genuinely dependent constructions in `src/build.py`. Never fudge geometry to make renders look right.
- Preserve four M2.5 candidate PCB mount locations (their actual dimensions remain provisional), four accessible rear driver paths, four M4 candidate clamp fastener channels and the split jaw until new measured data or explicit design instruction changes them.
- Do not fuse reference rail/screen/fasteners into the printable main or lower keeper.
- Always regenerate STEP/STL and geometry-derived PNG previews and embed the actual preview images in README with valid relative Markdown paths.
- Any new user measurements supersede provisional values, but record provenance and retain the original measurements. Do not call unmeasured hardware a physical fit.
- Run `python -m unittest discover -s tests -v` and rebuild with `xvfb-run -a python src/build.py`. A commit that changes geometry must update delivered outputs and `docs/validation.json`.
- Make the arm outlines dimensionally coherent, maintain printer clearance and hardware serviceability, use metal fasteners/inserts rather than force-carrying plastic snaps.
- Complete substantive tasks with deliverables and verify the outputs. When performing repository work, merge accepted verified changes to `main` unless explicitly told otherwise.

- V002 design invariants: saddle interior bearing plane normal is +Z, display carrier plane must be at 90° to that plane, and the carrier lower/front datum must share Y=0 with the saddle/rail center. Preserve the two triangular support arms, M4 clamp screw paths, and M2.5 board tool access while rebuilding. The V001 46° tilt is superseded, not a target.

- V003 Freeform silhouette acceptance: two full sculpted arms with radiused upper rear shoulder, swept angled back, radiused lower/rear transitions, front toe, and tall vertical rounded obround opening. The centered top saddle has an enabled shallow key entering the actual rail STEP's +Z T-slot, validated by zero volume overlap. Do not revert to V002's hard triangular cutout. The 90° display/saddle and Y=0 alignment, lower M4 keeper, four M2.5 board mounts and unobstructed rear access must remain.

- V004 user-directed profile: front support foot must terminate at upper saddle's FRONT face datum, never project as a rounded nose. Keep shortened rear taper and exact G1 line/arc tangency at upper shoulder, rear transition and lower rear foot. Validate analytically with radius-dot-tangent checks; preserve V003's functional rail/key/display fastener constraints.

- V006: a lower rear gusset must be part of the *actual external YZ wire* and visually apparent in the generated side profile, not an interior wedge. Keep a BREP solid-volume test outside the rear saddle face below bridge height.

- V007: replace old full-width carrier plane with two independent rail solids fused to structural arms. Fastener bores, rear head counterbores and standoffs must originate in their own rail. No central back sheet. The two support openings must CUT THROUGH the rear exterior (side-specific U/Y service branches), not enclosed obrounds. Preserve side saddle root, key and split M4 keeper. SD/USB reliefs are independent; keep a nominal >=8 mm rail ligament and >=12 mm arm front ligament. User requests one coordinated release, minimum essential tests and real previews.
