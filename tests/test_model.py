"""V008 targeted tests for front-opening and independent M3 mounting rail parameters."""
import json,sys,unittest
from pathlib import Path
import cadquery as cq
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'src'))
from build import Design,DEFAULT_RAIL
class ModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=json.loads((ROOT/'config/mount_spec.json').read_text())
        cls.d=Design(cls.cfg)
        cls.parts={'rail':cls.d.rail(DEFAULT_RAIL),'upper_saddle':cls.d.upper_clamp(),
                   'keeper':cls.d.keeper(),'left_arm':cls.d.arm(-1),'right_arm':cls.d.arm(1),
                   'carrier':cls.d.carrier(),'main':cls.d.integrated_support()}

    def test_independent_centered_vertical_rail_and_arm_pitch(self):
        d=self.d
        self.assertEqual(self.cfg['release'],'V008')
        self.assertNotEqual(d.mount_rail_center_spacing_mm,d.support_arm_center_spacing_mm)
        self.assertEqual(d.mounting_x_centers_mm,(-28,28))
        self.assertEqual(d.mounting_stations_s_mm,(30,61))
        self.assertAlmostEqual(d.tangent[0],0,places=7)
        self.assertGreater(d.validate_mount_dimensions(),d.min_rail_arm_overlap_mm)
        changed=dict(self.cfg);changed['mount_rail_center_spacing_mm']=54
        self.assertNotEqual(Design(changed).mounting_x_centers_mm,d.mounting_x_centers_mm)
        self.assertEqual(Design(changed).support_arm_center_spacing_mm,d.support_arm_center_spacing_mm)

    def test_m3_head_pocket_through_bore_and_wall_limits(self):
        d=self.d
        self.assertEqual(len(self.parts['carrier'].Solids()),2)
        self.assertEqual(len(d.boardscrews()),4)
        self.assertEqual(d.board_screw_clearance_d_mm,3.4)
        self.assertGreaterEqual(d.mount_rail_thickness_mm-d.board_counterbore_depth_mm,d.min_screw_head_floor_mm)
        self.assertGreaterEqual((d.mount_rail_width_mm-d.board_screw_head_access_d_mm)/2,d.min_screw_head_radial_wall_mm)
        for param,value in [('board_counterbore_depth_mm',5),('board_screw_head_access_d_mm',18)]:
            wrong=dict(self.cfg);wrong[param]=value
            with self.assertRaises(ValueError):Design(wrong).validate_mount_dimensions()

    def test_front_opened_support_keeps_rear_spine(self):
        for side in (-1,1):
            arm=self.d.arm(side)
            opening=self.d.arm_service_opening(side)
            self.assertEqual(len(arm.Solids()),1)
            self.assertLess(opening.BoundingBox().ymin,0)
            self.assertLess(opening.BoundingBox().ymax,55)
            self.assertGreater(arm.Volume(),2000)

    def test_nominal_fit_and_fastener_access(self):
        r=self.d.validate(self.parts)
        self.assertTrue(r['status'].startswith('PASS'))
        self.assertEqual(r['carrier_rail_count'],2)
        for key in ('main_vs_rail_overlap_mm3','main_vs_keeper_overlap_mm3','keeper_vs_rail_overlap_mm3',
                    'sd_service_envelope_overlap_mm3','usb_service_envelope_overlap_mm3'):
            self.assertLess(r[key],.01)
        self.assertEqual(len([k for k in r if k.startswith('rear_tool_clearance_')]),4)

    def test_v008_exports_are_committed(self):
        for name in ('COMPLETE_2020_TOUCHSCREEN_ASSEMBLY_V008.step','PRINTABLE_PARTS_V008.step',
                     'M3_DISPLAY_SCREWS_REFERENCE.step'):
            self.assertTrue((ROOT/'step'/name).exists())
        for name in ('main.step','carrier.step'):
            self.assertTrue((ROOT/'step'/name).exists())
        for name in ('main.stl','keeper.stl'):
            self.assertTrue((ROOT/'stl'/name).exists())
        for name in ('engineering_side_profile.png','main_frame_only.png','rear_screw_access.png'):
            self.assertTrue((ROOT/'previews'/name).exists())
            self.assertIn(f'previews/{name}',(ROOT/'README.md').read_text())
if __name__=='__main__':unittest.main()
