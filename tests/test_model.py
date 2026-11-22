"""V013: M3 mounting holes are integral to the actual sculpted arms."""
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
                   'keeper':cls.d.keeper(),'left_arm':cls.d.arm(-1),
                   'right_arm':cls.d.arm(1),'main':cls.d.integrated_support()}

    def test_integrated_vertical_mount_pitches(self):
        d=self.d
        self.assertEqual(self.cfg['release'],'V013')
        self.assertFalse(hasattr(d,'carrier'))
        self.assertFalse(hasattr(d,'carrier_rails'))
        self.assertEqual(d.mounting_x_centers_mm,(-39,39))
        self.assertEqual(d.mounting_stations_s_mm,(20,65))
        self.assertAlmostEqual(d.tangent[0],0,places=7)
        self.assertGreaterEqual(d.validate_mount_dimensions(),d.min_screw_head_radial_wall_mm)
        alt=dict(self.cfg);alt['mount_hole_center_spacing_mm']=76
        self.assertNotEqual(Design(alt).mounting_x_centers_mm,d.mounting_x_centers_mm)
        self.assertEqual(Design(alt).support_arm_center_spacing_mm,d.support_arm_center_spacing_mm)

    def test_screw_access_and_bearing_wall_limits(self):
        d=self.d
        self.assertEqual(len(d.boardscrews()),4)
        self.assertTrue(self.parts['main'].isValid())
        self.assertEqual(len(self.parts['main'].Solids()),1)
        self.assertEqual(d.board_screw_clearance_d_mm,3.4)
        self.assertGreaterEqual(d.mount_pad_axial_thickness_mm-d.board_counterbore_depth_mm,d.min_screw_head_floor_mm)
        for key,value in [('board_counterbore_depth_mm',5),
                          ('board_driver_access_d_mm',13),
                          ('mount_hole_center_spacing_mm',65),
                          ('board_screw_vertical_pitch_mm',31)]:
            bad=dict(self.cfg);bad[key]=value
            with self.assertRaises(ValueError): Design(bad).validate_mount_dimensions()

    def test_front_side_openings_and_integral_ribs(self):
        for side in (-1,1):
            arm=self.d.arm(side)
            opening=self.d.arm_service_opening(side)
            self.assertEqual(len(arm.Solids()),1)
            self.assertLess(opening.BoundingBox().ymin,0)
            self.assertGreater(arm.Volume(),3000)

    def test_rail_fit_and_four_rear_driver_envelopes(self):
        result=self.d.validate(self.parts)
        self.assertTrue(result['status'].startswith('PASS'))
        self.assertEqual(result['detached_carrier_count'],0)
        self.assertEqual(result['integral_arm_m3_holes'],4)
        for key in ('main_vs_rail_overlap_mm3','main_vs_keeper_overlap_mm3',
                    'keeper_vs_rail_overlap_mm3','sd_service_envelope_overlap_mm3',
                    'usb_service_envelope_overlap_mm3'):
            self.assertLess(result[key],.01)
        self.assertEqual(sum(k.startswith('rear_tool_clearance_') for k in result),4)

    def test_v013_boss_trimming_is_constrained(self):
        d=self.d
        self.assertAlmostEqual(d.front_neck_width_mm,12.0)
        self.assertAlmostEqual(d.validate_mount_dimensions(),2.5)
        self.assertLess(d.path_point(d.mounting_stations_s_mm[1])[1]+d.upper_boss_cap_extra_mm,
                        d.arm_front_z_mm+d.display_height_along_slope_mm+16)
        self.assertGreater(d.keeper_corner_fillet_mm,0)
        self.assertTrue(all(v['radius']>0 for v in
                        (d.rib_profile_geometry()[0],d.rib_profile_geometry()[6],
                         d.rib_profile_geometry()[7])))
        for key,value in [('arm_front_rail_side_trim_mm',3.0),
                          ('upper_boss_cap_extra_mm',3.0),
                          ('arm_front_rail_taper_depth_mm',5.0)]:
            bad=dict(self.cfg);bad[key]=value
            with self.assertRaises(ValueError):Design(bad).validate_mount_dimensions()

    def test_screw_pitch_drives_both_opening_edges_and_rear_profile(self):
        d=self.d
        p=d.adaptive_profile
        self.assertEqual(self.cfg['release'],'V013')
        self.assertGreaterEqual(p['bottom_z']-p['screw_z'][0],
                                d.screw_support_radius_mm+d.opening_transition_clearance_mm)
        self.assertGreaterEqual(p['screw_z'][1]-p['top_z'],
                                d.screw_support_radius_mm+d.opening_transition_clearance_mm)
        self.assertGreater(p['top_z']-p['bottom_z'],2*d.arm_opening_corner_radius_mm)
        alt=dict(self.cfg);alt['board_screw_station_center_mm']=45.0
        q=Design(alt).adaptive_profile
        self.assertNotEqual((p['bottom_z'],p['top_z']),(q['bottom_z'],q['top_z']))
        alt2=dict(self.cfg);alt2['board_screw_vertical_pitch_mm']=49
        q2=Design(alt2).adaptive_profile
        self.assertNotEqual(p['bottom_z'],q2['bottom_z'])
        self.assertNotEqual(p['top_z'],q2['top_z'])
        invalid=dict(self.cfg);invalid['board_screw_vertical_pitch_mm']=31
        with self.assertRaises(ValueError): Design(invalid).validate_mount_dimensions()

    def test_both_curved_arms_remain_connected_and_have_throat_clearance(self):
        for side in (-1,1):
            arm=self.d.arm(side)
            self.assertTrue(arm.isValid())
            self.assertEqual(len(arm.Solids()),1)
        p=self.d.adaptive_profile
        self.assertGreater(p['roof_web_z'],self.d.screw_support_radius_mm)
        self.assertGreaterEqual(p['outer_bulge_z'],self.d.arm_outer_rear_bulge_z_mm)
        self.assertGreaterEqual(p['top_slope_rear_web_y'],self.d.opening_rear_web_mm)

    def test_v013_unified_front_service_cutter_is_one_solid(self):
        for side in (-1,1):
            cut=self.d.arm_service_opening(side)
            self.assertEqual(len(cut.Solids()),1)
            self.assertLess(cut.BoundingBox().ymin,self.d.arm_front_y_mm)
            self.assertGreater(cut.BoundingBox().ymax,29)
            self.assertLess(self.parts['left_arm' if side==-1 else 'right_arm'].Volume(),
                            self.d.rib_workplane().extrude(self.d.arm_thickness_mm).val().Volume())
        self.assertTrue(self.d.unified_front_u_opening)

    def test_v013_source_step_hole_centers_are_kept_separate_from_nominal_mount(self):
        fixture=self.d.validate(self.parts)['waveshare_step_mount_reference']
        self.assertEqual(fixture['measured_x_pitch_mm'],114)
        self.assertEqual(fixture['measured_y_pitch_mm'],59.1)
        self.assertAlmostEqual(fixture['x_pitch_mismatch_mm'],-36)
        self.assertAlmostEqual(fixture['z_pitch_mismatch_mm'],-14.1)
        self.assertFalse(fixture['registered_to_bracket'])
        self.assertTrue(__import__('pathlib').Path(ROOT/'reference/waveshare_0820_1_mounting_datums.json').exists())

    def test_v013_smooth_root_blend_stays_clear_of_lowest_m3(self):
        self.assertGreater(self.d.front_neck_blend_height_mm,0)
        p=self.d.adaptive_profile
        self.assertLess(self.d.arm_front_z_mm+self.d.arm_front_neck_start_above_datum_mm+
                        self.d.front_neck_blend_height_mm,p['screw_z'][0]-self.d.board_driver_access_d_mm/2)
        self.assertTrue(self.d.arm(-1).isValid())

    def test_v013_slimmer_arm_opening_without_removing_screw_web(self):
        p=self.d.adaptive_profile
        self.assertAlmostEqual(p['bottom_z'],63.0)
        self.assertAlmostEqual(p['top_z'],88.0)
        self.assertAlmostEqual(p['rear_bottom_y'],45.0)
        self.assertAlmostEqual(p['rear_top_y'],36.0)
        self.assertGreaterEqual(p['top_slope_rear_web_y'],self.d.v013_min_sloped_spine_web_mm)
        self.assertGreaterEqual(p['lower_slope_rear_web_y'],self.d.v013_min_sloped_spine_web_mm)
        for z,aperture in zip(p['screw_z'],(p['bottom_z'],p['top_z'])):
            clearance=abs(z-aperture)-self.d.board_driver_access_d_mm/2
            self.assertGreaterEqual(clearance,self.d.min_screw_envelope_web_mm+
                                    self.d.opening_transition_clearance_mm)
        bad=dict(self.cfg)
        bad['arm_opening_rear_bottom_y_mm']=54
        with self.assertRaises(ValueError): Design(bad).validate_mount_dimensions()

    def test_v013_four_rear_exit_tool_tunnels_are_unobstructed(self):
        d=self.d
        for side in (-1,1):
            arm=self.parts['left_arm' if side<0 else 'right_arm']
            x=d.mounting_x_centers_mm[0 if side<0 else 1]
            for st in d.mounting_stations_s_mm:
                z=d.path_point(st)[1]
                y0=d.arm_front_y_mm+d.arm_top_land_mm+d.mount_pad_axial_thickness_mm
                far=max(d.board_driver_access_length_mm,
                        arm.BoundingBox().ymax-y0+d.v013_rear_tool_overrun_mm)
                probe=cq.Solid.makeCylinder(d.board_driver_access_d_mm/2,far,
                                            cq.Vector(x,y0,z),cq.Vector(0,1,0))
                self.assertLess(arm.intersect(probe).Volume(),0.02)
                self.assertGreater(y0+far,arm.BoundingBox().ymax+d.v013_rear_tool_overrun_mm-0.001)

    def test_v013_manufacturing_and_preview_outputs(self):
        for name in ('main.step','left_arm.step','right_arm.step',
                     'COMPLETE_2020_TOUCHSCREEN_ASSEMBLY_V013.step',
                     'PRINTABLE_PARTS_V013.step','M3_DISPLAY_SCREWS_REFERENCE.step',
                     'WAVESHARE_0820_DATUM_FIXTURE.step'):
            self.assertTrue((ROOT/'step'/name).exists(),name)
        self.assertTrue((ROOT/'stl/main.stl').exists())
        self.assertFalse((ROOT/'step/carrier.step').exists())
        self.assertFalse((ROOT/'stl/carrier.stl').exists())
        for name in ('main_frame_only','rear_screw_access',
                     'integrated_display_mount','engineering_side_profile','waveshare_mount_datums'):
            self.assertTrue((ROOT/'previews'/f'{name}.png').exists())
            self.assertIn(f'previews/{name}.png',(ROOT/'README.md').read_text())
if __name__=='__main__': unittest.main()
