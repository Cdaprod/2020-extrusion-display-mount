# V014 — fastener-driven compact mounting ears

## User design intent
Two separate, minimal vertical mounting ears per support arm, each only tall enough to support the head/pocket; open material between ears; preserved integral structural rear spine and rear screw-driver tunnel. No front full-height mounting rail and no extra detached carrier plate. The user-confirmed V014 change requires screw positions to determine bracket height AND overall bracket X span.

## Dependency graph
```text
mount_hole_center_spacing_mm -> mounting_x_centers -> support_arm_centers -> crossbeam span -> saddle length
board_screw_station_center_mm + board_screw_vertical_pitch_mm -> lower/upper screw Z
max(driver_D, head_pocket_D), min_tab_wall, edge_allowance -> tab_half_height
lower screw Z + tab_half_height -> U cavity bottom
upper screw Z - tab_half_height -> U cavity top
upper screw Z + tab_half_height -> outer rear shoulder and top of arm
lower screw Z - tab_half_height -> lower tab sculpt relief
```

For V014 nominal: screws X±39; stations S20 and S65 give Z53, Z98. Compact tab half-height 6.5 mm, nominal upper cap Z104.5; central opening from Z59.5 to Z91.5. Radiused rear U walls and existing 8 mm rear slope web requirement remain. Nominal saddle X length 108 mm derives from max(108, 78 + 16 mm arm thickness + 2×7 mm side margin). On changing mounting pitch to 90, arm axes become ±45 and saddle length 120; no separate carrier rail, screw positions are still coplanar and coaxial with rear access.

## Fastener interface
Use four head seats Ø6.4 × 3 mm deep, four M3 clearance holes Ø3.4, and four coaxial Ø7 rear driver channels that break out beyond arm back. Preserve minimum 3 mm axial bearing floor, 2.5 mm radial web and the M4 clamp / key geometry unchanged. Do not let driver tunnel turn into a full-bore hole through the PCB-facing mounting head seat.

## Validation and hardware provenance
The reference 2020 STEP length remains 120 mm and the physical Waveshare mounting STEP is **114 × 59.1 mm, Ø2**, not the existing provisional **78 × 45 mm M3**. The generator may resize the saddle when parametric pitch changes; this does not certify hardware fit. Regenerate complete assembly, printable STEP/STL, side and isometric PNGs, updated docs/validation.json; run the small engineering test suite before merge to main.
