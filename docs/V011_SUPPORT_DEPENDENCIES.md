# V011 — Screw-station-driven side profile

The failure shown in the annotated V010 image is a dependency error: four M3 axes moved parametrically but the front-open U cavity retained fixed `arm_opening_bottom_z_mm=44` and `arm_opening_top_z_mm=96`. An X-direction radial wall of 2.5 mm does not prove an adequate YZ support web.

V011 derives the side profile from the M3 vertical midpoint and pitch:

- `z_lower=arm_front_z_mm+(board_screw_station_center_mm-board_screw_vertical_pitch_mm/2)`
- `z_upper=arm_front_z_mm+(board_screw_station_center_mm+board_screw_vertical_pitch_mm/2)`
- `r_required=board_driver_access_d_mm/2+min_screw_envelope_web_mm`
- `opening_bottom=z_lower+opening_lower_offset_from_screw_mm`
- `opening_top=z_upper-opening_upper_offset_from_screw_mm`
- `z_bulge=max(arm_outer_rear_bulge_z_mm,(opening_bottom+opening_top)/2+outer_rear_bulge_margin_mm)`

Nominal `r_required=3.5+4=7.5 mm`. Each opening edge must clear its fastener center by at least `r_required+opening_transition_clearance_mm=9.5 mm`. The opening has a parametric corner radius and an independent rear-web spacing bound. The source rail and split M4 keeper are not changed.

New dependencies are part of `src/build.py` rather than manual fixed positions in the preview. Tests exercise vertical midpoint, vertical pitch and rejection of infeasible configurations. They cannot replace inspection of the *actual* printed-load geometry or physical fit.

The STEP/STL and images are to be regenerated from this source and committed with matching `docs/validation.json` before release.
