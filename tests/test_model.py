"""Focused V007 nominal CAD validation; physical PCB/ports remain unmeasured."""
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

    def test_actual_reference_rail_unchanged(self):
        original=cq.importers.importStep(str(DEFAULT_RAIL)).solids().val()
        self.assertAlmostEqual(original.Volume(),self.parts['rail'].Volume(),places=4)

    def test_two_open_back_rails_and_screw_pockets(self):
        self.assertEqual(self.cfg['release'],'V007')
        self.assertEqual(len(self.parts['carrier'].Solids()),2)
        self.assertEqual(len(self.d.boardscrews()),4)
        self.assertEqual(len(self.d.clampscrews()),4)
        self.assertEqual(len(self.parts['main'].Solids()),1)
        self.assertTrue(self.parts['main'].isValid())

    def test_asymmetric_open_side_access_and_kept_supports(self):
        self.assertNotEqual(self.cfg['service_left']['throat_width_mm'],
                            self.cfg['service_right']['throat_width_mm'])
        for sign in (-1,1):
            arm=self.d.arm(sign)
            self.assertEqual(len(arm.Solids()),1)
            self.assertGreater(arm.Volume(),2000)
            self.assertGreater(self.d.arm_service_opening(sign).BoundingBox().ymax,80)

    def test_ports_rail_key_keeper_and_driver_paths_nominal(self):
        report=self.d.validate(self.parts)
        self.assertTrue(report['status'].startswith('PASS'))
        self.assertTrue(report['rear_sheet_removed'])
        self.assertEqual(report['carrier_rail_count'],2)
        for name in ('main_vs_rail','main_vs_keeper','keeper_vs_rail',
                     'sd_service_envelope','usb_service_envelope'):
            self.assertLess(report[name+'_overlap_mm3'],.01)
        self.assertEqual(len([k for k in report if k.startswith('rear_tool_clearance_')]),4)

    def test_exported_manufacturing_files_and_previews(self):
        for name in ('main','keeper','rail','left_arm','right_arm'):
            part=cq.importers.importStep(str(ROOT/'step'/f'{name}.step'))
            self.assertEqual(part.solids().size(),1)
        carrier=cq.importers.importStep(str(ROOT/'step/carrier.step'))
        self.assertEqual(carrier.solids().size(),2)
        for filename in ('COMPLETE_2020_TOUCHSCREEN_ASSEMBLY_V007.step',
                         'PRINTABLE_PARTS_V007.step'):
            self.assertTrue((ROOT/'step'/filename).exists())
        for name in ('assembly_isometric','main_frame_only','side_section',
                     'saddle_clamp','display_carrier','rear_screw_access',
                     'engineering_side_profile'):
            self.assertTrue((ROOT/'previews'/f'{name}.png').exists())
            self.assertIn(f'previews/{name}.png',(ROOT/'README.md').read_text())

if __name__=='__main__':unittest.main()
