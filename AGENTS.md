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
