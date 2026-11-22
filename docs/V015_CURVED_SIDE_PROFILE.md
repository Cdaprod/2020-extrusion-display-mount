# V015 Curved Profile and Fastener Station Contract

The red marks on the source user's sketch represent the existing M3 screw-center locations, not extra fasteners.

## Source of truth and derived geometry
- Horizontal screw pitch drives ±X arm centers and overall saddle length.
- Vertical center/pitch drives lower/upper M3 ear positions, upper cap, service opening boundaries, midpoint and inner curve control points.
- Each short upper/lower mounting ear continues to provide one M3 head seat and tool tunnel; the open middle section has no continuous carrier strip.
- The U recess is assembled from straight horizontal tab lips, two **cubic Bézier spans** connected at an identical nose point with matching vertical tangents, and an off-body opening edge at the front. It has G1 tangency where the horizontal lips meet the cubic paths and at the common rear nose.
- Inner rear nose Y is calculated by linear interpolation of the exterior lower sloped spine at the opening's screw-derived Z midpoint, then offset inward (frontwards) by `v015_rear_spine_web_mm` (9 mm nominal). Sufficient shape bulge and a minimum sampled analytic spine web are required or generation fails; the profile is not allowed to arbitrarily delete structural material.
- No additional holes or tubes shall be introduced. M3 screw-driver rear exits, axial bearing floors, M4 bottom keeper, and source STEP remain unchanged.

## Generated CAD and validation
The generator produces two printable BREP parts (`main`, `keeper`), auxiliary references, and current V015 assembly STEP and STL plus geometry-derived PNGs and `docs/validation.json`. The only printed parts are the main bracket and keeper. The original Waveshare 114 × 59.1 mm Ø2 mounting datum is still a separate construction fixture; the 78 × 45 mm M3 candidate is not approved for direct fit. Physical loads and PETG/PLA print strength remain unverified.

## Side profile constraints
Keep tab supports >= Ø7 rear tool radius + 2.5 mm printable radial wall + 0.5 mm edge allowance. Maintain >=3 mm head-seat axial bearing floor; respect ≥7.5 mm interpolated rear web, with 9 mm target at the inner curve's rearmost reference station. Recompute bounds for every screw pattern change. Failure should produce an error rather than silently relaxing thickness.
