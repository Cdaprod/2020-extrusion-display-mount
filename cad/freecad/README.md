# Preserved FreeCAD source

`display-mount-original.FCStd` is the editable checkpoint imported from the user's saved `display-mount.FCStd`. `original-brackets.step` and `original-side.png` show the checkpoint's two separate bracket solids; they are references, not a completed printable mount.

The Assembly contains a Body whose active tip is `Pocket001`: the YZ Sketch (28 elements, fully constrained) drives Pad; MultiTransform mirrors it; XY Sketch drives Pocket; Binder supplies Pocket001. The unused TabOpeningSketch and TabOpeningPocket remain in the tree, but are not the active tip. MountingParams supplies 114 mm X pitch, 59.1 mm Z pitch, 10 mm face width, 15 mm tab height, 10 mm pad depth, 4 mm datum offset, 12 mm tab projection, 13 mm access depth, 5 mm nominal web, 2 mm upper taper inset and 6 mm upper root reinforcement.

At import, Pocket001 contains two valid disconnected solids with combined bounds X −62…62, Y −13…68, Z −88.2789…44.05 mm. It does not yet include the connecting saddle or keeper.

![Preserved bracket side view](original-side.png)
