# V004 tangent-continuous compact side profile

Source: user annotated screenshots IMG_9092(1).jpeg (red defects, green intended edge) and IMG_9095.png (preferred compact silhouette). Earlier V003 reference is retained as historical source.

## Exact geometry

The YZ arm's front toe terminates at `Y=-upper_clamp_width_mm/2` and `Z=bridge_top-arm_saddle_intersection_mm`. It is fused into the saddle top and cannot form a free nose. The rear foot is shortened to `arm_outer_lower_rear_y_mm` and its rising taper is controlled by the rear bulge station. Top shoulder, rear transition and lower rear foot use exact analytic circular fillets calculated from adjacent line direction vectors. Tangent distances are `R/tan(theta/2)`; circle center is found on the normalized angle bisector. Each arc's radius vector is orthogonal to its incoming and outgoing segment at the contact points, guaranteeing G1 continuity.

The front inclined foot and vertical carrier interface retain the intentionally defined structural intersection, not a decorative nose. A vertical obround access opening remains.

## Unchanged interfaces

2020 reference STEP, centered upper saddle, slot-indexing key, four M4 lower keeper screws, 90-degree upright display and four M2.5 provisional board fasteners with rear access.

## Limitations

Dimensions are estimated from sketches. Tangency is mathematically tested; physical fit and actual mechanical loads remain unverified.
