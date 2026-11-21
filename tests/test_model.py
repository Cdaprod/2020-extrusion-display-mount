"""Production-gating nominal CAD and provenance checks; no physical-fit claim."""
import json
import sys
import unittest
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
        cls.parts={'rail':cls.d.rail(DEFAULT_RAIL),
                   'upper_saddle':cls.d.upper_clamp(),
                   'keeper':cls.d.keeper(),
                   'left_arm':cls.d.arm(-1),
                   'right_arm':cls.d.arm(1),
                   'carrier':cls.d.carrier(),
                   'main':cls.d.integrated_support()}

    def test_source_rail_brep_preserved_exactly(self):
        original=cq.importers.importStep(str(DEFAULT_RAIL)).solids().val()
        rail=self.parts['rail']
        self.assertAlmostEqual(rail.Volume(),original.Volume(),places=5)
        b=rail.BoundingBox()
        self.assertAlmostEqual(b.xlen,120,places=4)
        self.assertAlmostEqual(b.ylen,20,places=4)
        self.assertAlmostEqual(b.zlen,20,places=4)

    def test_two_structural_arms_connected_in_integrated_main(self):
        p=self.parts['main']
        self.assertTrue(p.isValid())
        self.assertEqual(len(p.Solids()),1)
        self.assertGreater(self.parts['left_arm'].Volume(),1000)
        self.assertGreater(self.parts['right_arm'].Volume(),1000)

    def test_body_interference_and_tool_access(self):
        r=self.d.validate(self.parts)
        self.assertTrue(r['status'].startswith('PASS'))
        for name in ('main_vs_rail','keeper_vs_rail','main_vs_keeper'):
            self.assertEqual(r[name+'_overlap_mm3'],0)
        self.assertEqual(len([k for k in r if k.startswith('rear_tool_clearance_')]),4)

    def test_display_and_clamp_screw_patterns(self):
        self.assertEqual(len(self.d.boardscrews()),4)
        self.assertEqual(len(self.d.clampscrews()),4)
        self.assertAlmostEqual(self.cfg['board_hole_x_mm'][1]-self.cfg['board_hole_x_mm'][0],56)
        self.assertAlmostEqual(self.cfg['board_hole_s_mm'][1]-self.cfg['board_hole_s_mm'][0],31)

    def test_perpendicular_carrier_and_centered_saddle_datums(self):
        self.assertEqual(self.cfg['release'], 'V003')
        self.assertAlmostEqual(self.d.display_angle_deg,90.0,places=6)
        self.assertAlmostEqual(self.d.arm_front_y_mm,0.0,places=6)
        self.assertAlmostEqual(self.d.tangent[0],0.0,places=6)
        self.assertAlmostEqual(self.d.normal[1],0.0,places=6)
        railbb=self.parts['rail'].BoundingBox()
        screenbb=self.parts['carrier'].BoundingBox()
        self.assertAlmostEqual(railbb.xmin+railbb.xmax,0.0,places=4)
        self.assertAlmostEqual(screenbb.xmin+screenbb.xmax,0.0,places=4)
        y0,z0=self.d.path_point(0)
        self.assertAlmostEqual(y0,0.0,places=5)
        report=self.d.validate(self.parts)
        self.assertTrue(report['carrier_perpendicular_to_saddle'])
        self.assertTrue(report['carrier_centered_over_saddle'])

    def test_alignment_constraints_reject_wrong_geometry(self):
        wrong=dict(self.cfg);wrong['display_angle_deg']=46.0
        with self.assertRaisesRegex(ValueError,'perpendicular'):
            Design(wrong).validate(self.parts)
        wrong=dict(self.cfg);wrong['arm_front_y_mm']=-33.0
        with self.assertRaisesRegex(ValueError,'centered'):
            Design(wrong).validate(self.parts)

    def test_alignment_is_still_parametrically_editable(self):
        changed=dict(self.cfg)
        changed['require_perpendicular_display']=False
        changed['require_display_centering']=False
        changed['display_angle_deg']=85.0
        changed['arm_front_y_mm']=3.0
        self.assertTrue(Design(changed).carrier().isValid())

    def test_v003_key_is_inside_actual_rail_slot(self):
        self.assertTrue(self.d.top_slot_key_enabled)
        self.assertGreater(self.d.top_slot_key_projection_mm,0)
        report=self.d.validate(self.parts)
        self.assertEqual(report['top_slot_key_rail_overlap_mm3'],0)

    def test_v003_curved_arm_has_vertical_obround_and_real_arcs(self):
        self.assertGreater(self.parts['left_arm'].Volume(),1000)
        arcs=sum(e.geomType()=='CIRCLE' for e in self.parts['left_arm'].Edges())
        self.assertGreaterEqual(arcs,4)
        self.assertEqual(self.d.arm_service_slot_angle_deg,90)

    def test_changes_to_configuration_update_geometry(self):
        revised=dict(self.cfg)
        revised['display_angle_deg']=self.cfg['display_angle_deg']+2
        changed=Design(revised).carrier()
        self.assertNotAlmostEqual(changed.BoundingBox().ylen,self.parts['carrier'].BoundingBox().ylen,places=2)
        self.assertTrue(changed.isValid())

    def test_exported_files_reimport_as_valid_solids(self):
        for name in ('main','keeper','rail','carrier','left_arm','right_arm'):
            s=cq.importers.importStep(str(ROOT/'step'/f'{name}.step'))
            self.assertEqual(s.solids().size(),1)
            self.assertTrue(s.val().isValid())

    def test_actual_previews_embedded_in_readme(self):
        readme=(ROOT/'README.md').read_text()
        for name in ('assembly_isometric','main_frame_only','side_section',
                     'saddle_clamp','display_carrier','rear_screw_access',
                     'engineering_side_profile'):
            path=ROOT/'previews'/f'{name}.png'
            self.assertTrue(path.exists(),str(path))
            self.assertIn(f'previews/{name}.png',readme)


if __name__=='__main__':unittest.main()
