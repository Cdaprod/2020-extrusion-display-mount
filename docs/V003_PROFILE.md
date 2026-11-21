# V003 Freeform-derived profile and 2020 slot key

## Intent and provenance
The user's annotated Freeform screenshot (IMG_9089.png) supersedes the V002 straight triangular arm shown in IMG_9083.png and IMG_9084.png. These screenshots provide a *visual silhouette*, not calibrated dimensions. All parametric stations below are provisional.

## Datums
X runs along the aluminum extrusion; Y is front/rear; Z upward. The unchanged 120 mm user STEP rail is centered at Y=0. Its two opposing slots face +Z/-Z in the assembled coordinate frame. The display's upright carrier remains perpendicular to the horizontal saddle inside bearing plane, with lower datum centered at Y=0.

## Curve and clearance parameters
All parameters are in `config/mount_spec.json`: `arm_outer_rear_shoulder_y_mm`, `arm_outer_rear_shoulder_z_above_carrier_mm`, `arm_outer_rear_bulge_y_mm`, `arm_outer_rear_bulge_z_mm`, `arm_outer_lower_rear_y_mm`, `arm_front_toe_y_mm`, `arm_curve_radius_mm`, `arm_service_slot_center_y_mm`, `arm_service_slot_center_z_mm`, `arm_service_slot_length_mm`, `arm_service_slot_width_mm`, `arm_service_slot_angle_deg`. The actual arm is a closed CadQuery wire including explicit circular three-point arcs; the vertical service opening is a true obround BREP cut.

## Saddle indexing tongue
The top slot key is enabled in V003 and is built as a centered shallow mouth-entry rib: 5.6 mm wide, 75 mm long, 0.9 mm projection. A volume-intersection check uses the **actual imported user STEP rail** and rejects key collisions. This key is solely for locating and anti-twist; the four M4 candidate clamp screws and separate lower keeper retain the bracket. Verify physical clearance with a printed coupon; real rail is unmeasured.

## Acceptance and remaining uncertainty
Preserve all four M2.5 candidate display-board holes and their straight rear screwdriver corridors. Validate the two support arms, one-piece main, independent removable keeper, rail collision, and exported STEP/STL with tests. Physical PCB dimensions, clamp screw length, print orientation, load, printer-motion clearance and real extrusion-slot geometry still require measurement.
