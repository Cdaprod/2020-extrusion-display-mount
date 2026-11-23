"""Native FreeCAD / independently generated CadQuery dimensional checks."""
import json,sys,unittest
from pathlib import Path
import cadquery as cq
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'src'))
from native_equivalent import geometry,cyl

class NativeEquivalentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=json.loads((ROOT/'config/mount_spec.json').read_text())
        cls.main,cls.keeper=geometry(cls.cfg)

    def test_nominal_matches_saved_native_brep(self):
        for generated,path in ((self.main,'mount-working.step'),(self.keeper,'keeper-working.step')):
            saved=cq.importers.importStep(str(ROOT/'cad/freecad'/path)).solids().vals()[0]
            # STEP and CadQuery use slightly different shape tolerances.
            self.assertLess(abs(generated.Volume()-saved.Volume()),0.02)
            self.assertLess(generated.cut(saved).Volume(),0.02)
            self.assertLess(saved.cut(generated).Volume(),0.02)

    def test_centered_key_and_separate_keeper(self):
        n=self.cfg['native_profile'];half=n['channel_width_mm']/2;key=n['slot_key_width_mm']/2
        self.assertAlmostEqual(half-key,7.175)
        self.assertTrue(self.main.isValid());self.assertEqual(len(self.main.Solids()),1)
        self.assertTrue(self.keeper.isValid());self.assertEqual(len(self.keeper.Solids()),1)
        self.assertLess(self.main.intersect(self.keeper).Volume(),1e-6)
        for x in (-38,38):
            for y in (-5.4,25.4):
                probe=cyl(1.2,14.8,(x,y,n['foot_base_z_mm']-n['keeper_gap_mm']-n['keeper_thickness_mm']-.001))
                self.assertLess(self.main.intersect(probe).Volume()+self.keeper.intersect(probe).Volume(),1e-5)

    def test_m3_seats_and_clamp_fasteners(self):
        # Probe the rear countersink at two depths: it narrows toward the
        # display, leaving the 3 mm axial bearing pad intact.
        x,z=57,29.55
        self.assertLess(self.main.intersect(cyl(.05,.08,(x+2.25,3.85,z),(0,1,0))).Volume(),1e-7)
        self.assertGreater(self.main.intersect(cyl(.05,.08,(x+2.25,3.05,z),(0,1,0))).Volume(),1e-5)
        n=self.cfg['native_profile']; top=n['foot_base_z_mm']-n['keeper_gap_mm']; bottom=top-n['keeper_thickness_mm']
        self.assertLess(self.keeper.intersect(cyl(2.9,2.9,(38,-5.4,bottom))).Volume(),1e-6)
        self.assertGreater(self.keeper.intersect(cyl(.1,.2,(40.5,-5.4,bottom+3.1))).Volume(),1e-5)

    def test_pitch_variants_keep_screw_access_and_one_solid(self):
        for pitch in (53,59.1,65):
            cfg=dict(self.cfg);cfg['board_screw_vertical_pitch_mm']=pitch
            main,keeper=geometry(cfg)
            self.assertTrue(main.isValid(),pitch);self.assertEqual(len(main.Solids()),1,pitch)
            self.assertTrue(keeper.isValid(),pitch);self.assertEqual(len(keeper.Solids()),1,pitch)
            for x in (-57,57):
                for z in (-pitch/2,pitch/2):
                    probe=cyl(3,12.8,(x,12.1,z),(0,1,0))
                    self.assertLess(main.intersect(probe).Volume(),1e-5,(pitch,x,z))

if __name__=='__main__':unittest.main()
