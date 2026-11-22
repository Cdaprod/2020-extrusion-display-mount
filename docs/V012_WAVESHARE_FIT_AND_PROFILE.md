# V012 — sculpted U aperture, root blend and Waveshare STEP hardware datum

## Implemented geometry
1. A single filleted quadrilateral cutter opens each structural arm toward the screen (negative Y). This replaces the old union of the main cavity and a second rounded `slot2D()` throat, removing internal stair-steps and secondary bulges. The cutter begins 18 mm in front of the arm so its own front corner fillets never introduce a contour on the load-bearing tabs.
2. The lower and upper M3-support termini derive from `adaptive_profile`, with nominal Z=64 and Z=86, while nominal fastener Z=53 and 98. The critical access radius is Ø7/2+4=7.5 mm plus configurable margin.
3. The 16-to-12-mm front-neck transition uses a ruled multi-station loft along Z with parameter `front_neck_blend_height_mm=8`. The vertical station is strictly below the lower M3 driver corridor. This removes the visually sharp extruded trim termination at the front gusset root; no global fillets are permitted on the saddle/rail bearing or screw seats.
4. Preserve two integral arms, the open back, M3 pocket floor and tool access, 2020 T-slot index key, and separate M4 keeper. The nominal backside geometry is unchanged.

## Actual native CAD-hole evidence
The uploaded `0820-1.stp` contains one valid solid, bounding box X[-104,+104], Y[-34.9,+34.9], Z[-3.67,+12.33] mm. Four user-marked cylindrical holes were extracted with exact center axes in native STEP coordinates:
- (-68.9, -29.9), (-68.9,+29.2), (+45.1,-29.9), (+45.1,+29.2) mm;
- Ø2.0 cylinders, coaxial Ø5.5 boss cylinders; 114.0 mm along STEP X, 59.1 mm along STEP Y; rectangular pattern midpoint (-11.9,-0.35).
- Original STEP SHA256: `c501cd74045d34d4b53eab16fc685bbd9e5ccb5f2d6d479fd9ca9fecf300a367`.

This is an **extracted mechanical reference**, not yet a physical mating design: the bracket proposal is 78 × 45 mm, and its 120 mm 2020 rail/reference clamp cannot simply span 114 mm bosses with nominal 16 mm arms and margin without resolving overhang and support. The original uploaded 1.1 MB Waveshare STEP is not reconstructed or falsely represented as the simplified rectangular four-hole fixture. Keep the full original STEP as source material for physical design registration.

The user has indicated M3×6–8 candidate screws, but the source model contains Ø2.0 through-cylinders. Fastener hardware and standoff threads must be verified before drilling or manufacturing. Geometry tests must never certify actual board fit until these discrepancies are resolved.

## Verification scope
Run the existing engineering regression suite, inspect the final CAD-derived V012 main-frame and side-profile previews, and verify generated STEP/STL and matching JSON report are committed together. Check 3D collisions against the reference 2020 STEP and modeled SD/USB access corridors. Do not claim FEA or actual print-strength certification.
