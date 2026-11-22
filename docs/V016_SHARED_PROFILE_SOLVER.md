# V016 — shared fastener-driven XZ/YZ constraint solution

## Source of truth
Four fasteners live on the two X stations ±P_x/2 and two Z stations Z_mid ±P_z/2. All downstream surfaces depend on these stations, not on separate manually placed mounting holes. Each screw remains in an integral short ear with head support radius max(driver_d, head_d)/2 + wall + edge tolerance. Its longitudinal rear Ø7 tool corridor and front bearing floor are unchanged.

## Exterior rear spine
The 2020 saddle establishes the fixed rear root datum Y_s = clamp_width/2 - gusset_overlap. Three *dimensionless styling coefficients* derive the Y coordinates of lower rear root, maximum bulge and upper shoulder from vertical screw pitch: Y_i = Y_s + a_i P_z. The bulge Z is Z_mid + b P_z. The outer cap Z is Z_upper + tab_half_height. These replace the former fixed rear stations that could not scale with screw pitch.

## Inner curved opening
The two opening Z boundaries derive directly from the screw positions and ear envelopes. The exterior Y at each Z is interpolated from adjacent exterior control stations. Each inner lip lies forward of that exterior station by an explicit configurable minimum horizontal web offset. The rear Bézier nose is derived from the exterior lower spine at the screw-derived opening midpoint, minus the target rear structural-web offset. Cubic Bézier tangency is retained at each horizontal lip and at the shared nose.

## Verification
The fast nominal shape is deliberately preserved within rounding of the previous style ratios while moving to fully coupled controls. Tests require outer shoulder, bulge and lower root to react when screw pitch changes, and inner opening plus four M3 ear locations to remain constrained. Disallow negative webs, folded curves and impossible pitch. Existing CAD validity, clamp clearance, non-interference, rear-driver entry and connected-solid checks remain.

**Physical hardware boundary:** The Waveshare STEP reference identifies 114×59.1 mm hole pitch and Ø2 native holes; the candidate bracket is 78×45 mm M3 and remains explicitly unregistered. Do not declare a real hardware fit. The 120 mm source rail is never scaled or moved to reconcile mismatches.

Current generator: `src/build.py`; parameters: `config/mount_spec.json`; generated validation: `docs/validation.json`. Publish STEP/STL/PNG together after the GitHub CAD runner passes.
