"""V016: M3 mounting holes are integral to the actual sculpted arms."""
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
        self.assertEqual(self.cfg['release'],'V016')
        self.assertFalse(hasattr(d,'carrier'))
        self.assertFalse(hasattr(d,'carrier_rails'))
        self.assertEqual(d.mounting_x_centers_mm,(-39,39))
        self.assertEqual(d.mounting_stations_s_mm,(20,65))
        self.assertAlmostEqual(d.tangent[0],0,places=7)
        self.assertGreaterEqual(d.validate_mount_dimensions(),d.min_screw_head_radial_wall_mm)
        alt=dict(self.cfg);alt['mount_hole_center_spacing_mm']=90
        self.assertNotEqual(Design(alt).mounting_x_centers_mm,d.mounting_x_centers_mm)
        self.assertNotEqual(Design(alt).effective_arm_pitch_mm,d.effective_arm_pitch_mm)
        self.assertNotEqual(Design(alt).effective_saddle_length_mm,d.effective_saddle_length_mm)

    def test_screw_access_and_bearing_wall_limits(self):
        d=self.d
        self.assertEqual(len(d.boardscrews()),4)
        self.assertTrue(self.parts['main'].isValid())
        self.assertEqual(len(self.parts['main'].Solids()),1)
        self.assertEqual(d.board_screw_clearance_d_mm,3.4)
        self.assertGreaterEqual(d.mount_pad_axial_thickness_mm-d.board_counterbore_depth_mm,d.min_screw_head_floor_mm)
        for key,value in [('board_counterbore_depth_mm',5),
                          ('board_driver_access_d_mm',13),
                          ('mount_hole_center_spacing_mm',0),
                          ('board_screw_vertical_pitch_mm',18)]:
            bad=dict(self.cfg);bad[key]=value
            with self.assertRaises(ValueError): Design(bad).validate_mount_dimensions()

    def test_front_side_openings_and_integral_ribs(self):
        for side in (-1,1):
            arm=self.d.arm(side)
            opening=self.d.arm_service_opening(side)
            self.assertEqual(len(arm.Solids()),1)
            self.assertLess(opening.BoundingBox().ymin,0)
            self.assertGreater(arm.Volume(),2500)

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

    def test_v015_boss_trimming_is_constrained(self):
        d=self.d
        self.assertAlmostEqual(d.front_neck_width_mm,12.0)
        self.assertAlmostEqual(d.validate_mount_dimensions(),2.5)
        self.assertLess(d.path_point(d.mounting_stations_s_mm[1])[1]+d.compact_tab_half_height_mm,
                        d.arm_front_z_mm+d.display_height_along_slope_mm+16)
        self.assertGreater(d.keeper_corner_fillet_mm,0)
        self.assertTrue(all(v['radius']>0 for v in
                        (d.rib_profile_geometry()[0],d.rib_profile_geometry()[6],
                         d.rib_profile_geometry()[7])))
        for key,value in [('arm_front_rail_side_trim_mm',3.0),
                          ('v014_min_tab_wall_mm',-2.0),
                          ('arm_front_rail_taper_depth_mm',5.0)]:
            bad=dict(self.cfg);bad[key]=value
            with self.assertRaises(ValueError):Design(bad).validate_mount_dimensions()

    def test_screw_pitch_drives_both_opening_edges_and_rear_profile(self):
        d=self.d
        p=d.adaptive_profile
        self.assertEqual(self.cfg['release'],'V016')
        self.assertGreaterEqual(p['bottom_z']-p['screw_z'][0],
                                d.compact_tab_half_height_mm)
        self.assertGreaterEqual(p['screw_z'][1]-p['top_z'],
                                d.compact_tab_half_height_mm)
        self.assertGreater(p['top_z']-p['bottom_z'],2*d.arm_opening_corner_radius_mm)
        alt=dict(self.cfg);alt['board_screw_station_center_mm']=45.0
        q=Design(alt).adaptive_profile
        self.assertNotEqual((p['bottom_z'],p['top_z']),(q['bottom_z'],q['top_z']))
        alt2=dict(self.cfg);alt2['board_screw_vertical_pitch_mm']=43
        q2=Design(alt2).adaptive_profile
        self.assertNotEqual(p['bottom_z'],q2['bottom_z'])
        self.assertNotEqual(p['top_z'],q2['top_z'])
        invalid=dict(self.cfg);invalid['board_screw_vertical_pitch_mm']=18
        with self.assertRaises(ValueError): Design(invalid).validate_mount_dimensions()

    def test_both_curved_arms_remain_connected_and_have_throat_clearance(self):
        for side in (-1,1):
            arm=self.d.arm(side)
            self.assertTrue(arm.isValid())
            self.assertEqual(len(arm.Solids()),1)
        p=self.d.adaptive_profile
        self.assertGreaterEqual(p['roof_web_z'],self.d.compact_tab_half_height_mm)
        self.assertGreaterEqual(p['outer_bulge_z'],self.d.arm_outer_rear_bulge_z_mm)
        self.assertGreaterEqual(p['top_slope_rear_web_y'],self.d.opening_rear_web_mm)

    def test_v015_nested_curvature_and_fastener_driven_control_points(self):
        p=self.d.v015_inner_profile
        es=self.d.v015_inner_boundary_edges()
        self.assertEqual(len(es),5)
        self.assertEqual(es[1].geomType(),'BEZIER')
        self.assertEqual(es[2].geomType(),'BEZIER')
        self.assertLess((es[1].endPoint()-es[2].startPoint()).Length,0.00001)
        self.assertAlmostEqual(p['web_at_nose_mm'],9)
        self.assertGreater(p['nose_y'],p['rear_bottom_y'])
        shifted=dict(self.cfg)
        shifted['board_screw_station_center_mm']+=2
        q=Design(shifted).v015_inner_profile
        self.assertNotEqual(q['middle_z'],p['middle_z'])
        self.assertNotEqual(q['nose_y'],p['nose_y'])

    def test_v015_unified_front_service_cutter_is_one_solid(self):
        for side in (-1,1):
            cut=self.d.arm_service_opening(side)
            self.assertEqual(len(cut.Solids()),1)
            self.assertLess(cut.BoundingBox().ymin,self.d.arm_front_y_mm)
            self.assertGreater(cut.BoundingBox().ymax,29)
            self.assertLess(self.parts['left_arm' if side==-1 else 'right_arm'].Volume(),
                            self.d.rib_workplane().extrude(self.d.arm_thickness_mm).val().Volume())
        self.assertTrue(self.d.unified_front_u_opening)

    def test_v015_source_step_hole_centers_are_kept_separate_from_nominal_mount(self):
        fixture=self.d.validate(self.parts)['waveshare_step_mount_reference']
        self.assertEqual(fixture['measured_x_pitch_mm'],114)
        self.assertEqual(fixture['measured_y_pitch_mm'],59.1)
        self.assertAlmostEqual(fixture['x_pitch_mismatch_mm'],-36)
        self.assertAlmostEqual(fixture['z_pitch_mismatch_mm'],-14.1)
        self.assertFalse(fixture['registered_to_bracket'])
        self.assertTrue(__import__('pathlib').Path(ROOT/'reference/waveshare_0820_1_mounting_datums.json').exists())

    def test_v015_smooth_root_blend_stays_clear_of_lowest_m3(self):
        self.assertGreater(self.d.front_neck_blend_height_mm,0)
        p=self.d.adaptive_profile
        self.assertLess(self.d.arm_front_z_mm+self.d.arm_front_neck_start_above_datum_mm+
                        self.d.front_neck_blend_height_mm,p['screw_z'][0]-self.d.board_driver_access_d_mm/2)
        self.assertTrue(self.d.arm(-1).isValid())

    def test_v015_slimmer_arm_opening_without_removing_screw_web(self):
        p=self.d.adaptive_profile
        self.assertAlmostEqual(p['bottom_z'],59.5)
        self.assertAlmostEqual(p['top_z'],91.5)
        self.assertAlmostEqual(p['rear_bottom_y'],45.05,places=1)
        self.assertAlmostEqual(p['rear_top_y'],35.89,places=1)
        self.assertGreaterEqual(p['top_slope_rear_web_y'],self.d.v014_min_sloped_spine_web_mm)
        self.assertGreaterEqual(p['lower_slope_rear_web_y'],self.d.v014_min_sloped_spine_web_mm)
        for z,aperture in zip(p['screw_z'],(p['bottom_z'],p['top_z'])):
            clearance=abs(z-aperture)-self.d.board_driver_access_d_mm/2
            self.assertGreaterEqual(clearance,self.d.v014_min_tab_wall_mm+
                                    self.d.v014_tab_edge_allowance_mm)
        bad=dict(self.cfg)
        bad['v016_inner_lip_y_web_mm']=5
        with self.assertRaises(ValueError): Design(bad).validate_mount_dimensions()

    def test_v015_four_rear_exit_tool_tunnels_are_unobstructed(self):
        d=self.d
        for side in (-1,1):
            arm=self.parts['left_arm' if side<0 else 'right_arm']
            x=d.mounting_x_centers_mm[0 if side<0 else 1]
            for st in d.mounting_stations_s_mm:
                z=d.path_point(st)[1]
                y0=d.arm_front_y_mm+d.arm_top_land_mm+d.mount_pad_axial_thickness_mm
                far=max(d.board_driver_access_length_mm,
                        arm.BoundingBox().ymax-y0+d.v014_rear_tool_overrun_mm)
                probe=cq.Solid.makeCylinder(d.board_driver_access_d_mm/2,far,
                                            cq.Vector(x,y0,z),cq.Vector(0,1,0))
                self.assertLess(arm.intersect(probe).Volume(),0.02)
                self.assertGreater(y0+far,arm.BoundingBox().ymax+d.v014_rear_tool_overrun_mm-0.001)

    def test_v015_mount_pitch_drives_real_saddle_and_arm_positions(self):
        d=self.d
        self.assertEqual(d.effective_arm_pitch_mm,d.mount_hole_center_spacing_mm)
        self.assertEqual(d.effective_saddle_length_mm,108)
        alt=dict(self.cfg)
        alt['mount_hole_center_spacing_mm']=90
        changed=Design(alt)
        self.assertEqual(changed.mounting_x_centers_mm,(-45,45))
        self.assertEqual(changed.effective_arm_pitch_mm,90)
        self.assertEqual(changed.effective_saddle_length_mm,120)
        self.assertAlmostEqual(changed.compact_tab_half_height_mm,6.5)
        self.assertEqual(changed.rib_profile_stations()[5][1],
                         changed.adaptive_profile['screw_z'][1]+changed.compact_tab_half_height_mm)
        self.assertEqual(changed.adaptive_profile['bottom_z'],
                         changed.adaptive_profile['screw_z'][0]+changed.compact_tab_half_height_mm)

    def test_v015_four_compact_ears_and_screw_rear_paths(self):
        p=self.d.adaptive_profile
        self.assertAlmostEqual(p['bottom_z'],59.5)
        self.assertAlmostEqual(p['top_z'],91.5)
        self.assertAlmostEqual(2*self.d.compact_tab_half_height_mm,13)
        self.assertLess(self.d.lower_tab_root_relief().BoundingBox().zmax,
                        p['screw_z'][0]-self.d.compact_tab_half_height_mm)
        self.assertLessEqual(p['screw_z'][1]+self.d.compact_tab_half_height_mm,105)
        self.assertTrue(self.parts['main'].isValid())
        self.assertEqual(self.d.validate(self.parts)['v014_compact_tabs']['count'],4)

    def test_v016_shared_profile_solution_moves_with_fastener_datums(self):
        d=self.d
        p=d.v016_profile_solution
        self.assertEqual(len(p['fasteners_x']),2)
        self.assertEqual(len(p['fasteners_z']),2)
        self.assertAlmostEqual(p['outer']['bulge_y'],58,places=5)
        self.assertAlmostEqual(p['outer']['lower_y'],47,places=5)
        self.assertAlmostEqual(p['outer']['shoulder_y'],16,places=5)
        self.assertAlmostEqual(p['outer']['bulge_z'],85.5,places=5)
        self.assertGreaterEqual(d.v016_minimum_curved_spine_distance_mm(),
                                d.v016_outer_inner_min_euclidean_web_mm)
        self.assertAlmostEqual(p['opening']['bottom_z'],59.5)
        self.assertAlmostEqual(p['opening']['top_z'],91.5)
        # Both contours and the printable saddle now depend on one fastener
        # pitch datum instead of independently fixed YZ profile coordinates.
        for offset in (-1,1):
            altered=dict(self.cfg)
            altered['board_screw_vertical_pitch_mm']+=offset
            changed=Design(altered).v016_profile_solution
            self.assertNotEqual(changed['outer']['bulge_y'],p['outer']['bulge_y'])
            self.assertNotEqual(changed['outer']['bulge_z'],p['outer']['bulge_z'])
            self.assertNotEqual(changed['opening']['bottom_z'],p['opening']['bottom_z'])
            self.assertNotEqual(changed['curves']['nose_y'],p['curves']['nose_y'])
        altered=dict(self.cfg)
        altered['mount_hole_center_spacing_mm']=90
        changed=Design(altered).v016_profile_solution
        self.assertEqual(changed['fasteners_x'],[-45,45])
        self.assertEqual(changed['saddle_length'],120)

    def test_v016_rejects_unphysical_profile_offset(self):
        for field,value in [('v016_inner_lip_y_web_mm',6),
                            ('v016_outer_bulge_y_from_saddle_pitch_ratio',.3),
                            ('v016_bulge_z_above_screw_mid_pitch_ratio',1)]:
            altered=dict(self.cfg);altered[field]=value
            with self.assertRaises(ValueError):
                Design(altered).validate_mount_dimensions()

    def test_v016_manufacturing_and_preview_outputs(self):
        for name in ('main.step','left_arm.step','right_arm.step',
                     'COMPLETE_2020_TOUCHSCREEN_ASSEMBLY_V016.step',
                     'PRINTABLE_PARTS_V016.step','M3_DISPLAY_SCREWS_REFERENCE.step',
                     'WAVESHARE_0820_DATUM_FIXTURE.step'):
            self.assertTrue((ROOT/'step'/name).exists(),name)
        self.assertTrue((ROOT/'stl/main.stl').exists())
        self.assertFalse((ROOT/'step/carrier.step').exists())
        self.assertFalse((ROOT/'stl/carrier.stl').exists())
        for name in ('main_frame_only','rear_screw_access',
                     'integrated_display_mount','engineering_side_profile','waveshare_mount_datums','rear_tool_tunnels_oblique'):
            self.assertTrue((ROOT/'previews'/f'{name}.png').exists())
            self.assertIn(f'previews/{name}.png',(ROOT/'README.md').read_text())
if __name__=='__main__': unittest.main()
