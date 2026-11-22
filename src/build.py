#!/usr/bin/env python3
"""Parametric Neptune-2/2020 saddle-mounted touchscreen support V013.

Input rail: unmodified user-supplied 2020-2O STEP, source axis +Z, slots +/-Y.
Assembly: original source (x,y,z) maps to (z,x,y): rail longitudinal +X,
T-slot faces +/-Z. Mechanical values not from the STEP are provisional.

This generator produces a real BREP model, not a render/AI concept.
Onshape imports STEP solids but cannot reconstruct this script's feature history.
Use mount_spec.json to modify geometry and regenerate STEP parts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

import cadquery as cq
from cadquery import exporters

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / 'config/mount_spec.json'
DEFAULT_RAIL = ROOT / 'reference/2020-2O_rail.step'


def block(x0, y0, z0, dx, dy, dz):
    return cq.Solid.makeBox(dx, dy, dz, cq.Vector(x0, y0, z0))


def cyl(radius, height, pos, direction=(0, 0, 1)):
    return cq.Solid.makeCylinder(radius, height, cq.Vector(*pos), cq.Vector(*direction))


def union(*parts):
    result = parts[0]
    for p in parts[1:]:
        result = result.fuse(p)
    return result.clean()


def check_solid(name, item):
    if not item.isValid() or len(item.Solids()) != 1:
        raise ValueError(f'{name}: expected one valid connected BREP solid; got {len(item.Solids())}')
    if item.Volume() <= 0:
        raise ValueError(f'{name}: non-positive volume')
    return item


@dataclass(frozen=True)
class Design:
    cfg: dict

    def __getattr__(self, key):
        if key in self.cfg:
            return self.cfg[key]
        raise AttributeError(key)

    @property
    def mounting_x_centers_mm(self):
        """Symmetric X stations. Mount rails move independently of support arms."""
        h=self.mount_hole_center_spacing_mm/2
        return (-h,h)

    @property
    def mounting_stations_s_mm(self):
        """Constrained vertical stations: S center and adjustable vertical pitch."""
        h=self.board_screw_vertical_pitch_mm/2
        return (self.board_screw_station_center_mm-h,
                self.board_screw_station_center_mm+h)

    @property
    def front_neck_width_mm(self):
        """Minimum X width of the narrowed, arm-integrated front mounting face."""
        return self.arm_thickness_mm-2*self.arm_front_rail_side_trim_mm

    @property
    def screw_support_radius_mm(self):
        """Minimum support radius around each complete rear driver corridor."""
        return self.board_driver_access_d_mm/2+self.min_screw_envelope_web_mm

    @property
    def rib_lower_spine_start_z(self):
        # Exterior rear diagonal begins at the saddle foot; no fixed opening
        # station may assume the foot remains at the V012 nominal height.
        return self.bridge_top-self.arm_saddle_intersection_mm

    @property
    def adaptive_profile(self):
        """YZ envelope strictly derived from actual vertical M3 stations."""
        lo,hi=self.mounting_stations_s_mm
        zl=self.path_point(lo)[1]; zh=self.path_point(hi)[1]
        r=self.screw_support_radius_mm
        # A screw envelope is preserved BEFORE any corner fillet.
        lower=zl+self.opening_lower_offset_from_screw_mm
        upper=zh-self.opening_upper_offset_from_screw_mm
        clearance=self.opening_transition_clearance_mm
        if lower<zl+r+clearance or upper>zh-r-clearance:
            raise ValueError('Opening intersects a required M3 support envelope')
        if upper-lower<2*self.arm_opening_corner_radius_mm+2:
            raise ValueError('M3 pitch too small for radiused front service aperture')
        rear_lower=max(self.arm_opening_rear_bottom_y_mm,
                       self.arm_front_y_mm+self.arm_opening_front_wall_mm+self.opening_rear_extra_y_mm)
        rear_upper=max(self.arm_front_y_mm+self.arm_opening_front_wall_mm+4,
                       min(self.arm_opening_rear_top_y_mm,rear_lower-2))
        outer_bulge_z=max(self.arm_outer_rear_bulge_z_mm,(lower+upper)/2+self.outer_rear_bulge_margin_mm)
        top=zh+self.upper_boss_cap_extra_mm
        # Side-wall rear distance at the roof must preserve a minimum ligament,
        # not merely avoid coincident boundary coordinates.
        outer_y_top=self.arm_outer_rear_shoulder_y_mm
        outer_y_bulge=self.arm_outer_rear_bulge_y_mm
        fraction=(upper-outer_bulge_z)/(top-outer_bulge_z)
        if not 0<=fraction<=1:
            raise ValueError('Outer shoulder does not span service aperture roof')
        exterior_y=outer_y_bulge+(outer_y_top-outer_y_bulge)*fraction
        if exterior_y-rear_upper < max(self.opening_rear_web_mm,
                                         self.v013_min_sloped_spine_web_mm):
            raise ValueError('Rear service aperture cuts into load-bearing sloped web')
        # At the lower obround end, the rear spine approaches the long outer
        # bulge. Constrain it against the actual outside YZ stations at that Z.
        outer_lower_z=self.rib_lower_spine_start_z
        bottom_fraction=(lower-outer_lower_z)/(outer_bulge_z-outer_lower_z)
        if not 0<=bottom_fraction<=1:
            raise ValueError('Rear opening bottom outside support spine span')
        exterior_lower=(self.arm_outer_lower_rear_y_mm+
                        (self.arm_outer_rear_bulge_y_mm-self.arm_outer_lower_rear_y_mm)*bottom_fraction)
        if exterior_lower-rear_lower < self.v013_min_sloped_spine_web_mm:
            raise ValueError('Rear opening bottom cuts into load-bearing diagonal web')
        return dict(bottom_z=lower,top_z=upper,rear_bottom_y=rear_lower,
                    rear_top_y=rear_upper,outer_bulge_z=outer_bulge_z,
                    screw_z=(zl,zh),support_radius=r,roof_web_z=zh-upper,
                    top_slope_rear_web_y=exterior_y-rear_upper,
                    lower_slope_rear_web_y=exterior_lower-rear_lower)

    def validate_mount_dimensions(self):
        """M3 centers are constrained inside the actual structural arms."""
        if abs(self.display_angle_deg-90)>1e-6: raise ValueError('Display face must be vertical')
        if self.mount_hole_center_spacing_mm<=0 or self.support_arm_center_spacing_mm<=0:
            raise ValueError('Invalid symmetric X spacing')
        offset=abs(self.mount_hole_center_spacing_mm-self.support_arm_center_spacing_mm)/2
        radial=(self.front_neck_width_mm-self.board_driver_access_d_mm)/2-offset
        if self.arm_front_rail_side_trim_mm<0 or self.front_neck_width_mm<=0:
            raise ValueError('V010 side trims remove the arm neck')
        if self.arm_front_rail_taper_depth_mm<=self.mount_pad_axial_thickness_mm:
            raise ValueError('V010 front draft must reach the rear structural web')
        if self.upper_boss_cap_extra_mm < self.board_driver_access_d_mm/2+self.min_screw_head_radial_wall_mm+1:
            raise ValueError('V010 upper curved tip too close to M3 access bore')
        if radial<self.min_screw_head_radial_wall_mm:
            raise ValueError('M3 driver passage exits the structural arm')
        if self.v013_rear_tool_overrun_mm<=0:
            raise ValueError('Rear tool overrun must extend beyond outer spine')
        if self.board_driver_access_d_mm<self.board_screw_head_access_d_mm:
            raise ValueError('Rear passage cannot admit M3 screw head')
        if self.board_screw_head_access_d_mm<self.board_screw_head_diameter_mm+self.head_pocket_diametral_clearance_mm:
            raise ValueError('M3 head has insufficient diametral clearance')
        if self.mount_pad_axial_thickness_mm-self.board_counterbore_depth_mm<self.min_screw_head_floor_mm:
            raise ValueError('M3 head bearing floor too thin')
        if self.board_counterbore_depth_mm<self.board_screw_head_height_mm:
            raise ValueError('M3 head pocket cannot accept screw head')
        if self.board_screw_clearance_d_mm>=self.board_screw_head_diameter_mm:
            raise ValueError('M3 bore exceeds head diameter')
        lo,hi=self.mounting_stations_s_mm
        if not (0<lo<hi<self.display_height_along_slope_mm):
            raise ValueError('Mount holes outside vertical arm region')
        profile=self.adaptive_profile
        for side in (-1,1):
            service=self.cfg['service_left' if side<0 else 'service_right']
            limit=service['throat_width_mm']/2+self.board_driver_access_d_mm/2+self.min_service_hole_gap_mm
            for st in (lo,hi):
                if abs(self.path_point(st)[1]-service['throat_center_z_mm'])<limit:
                    raise ValueError('Service notch clips screw bearing material')
        # Validate BOTH fastener axis envelopes and forward service throat
        # against the pitch-dependent side opening.
        zl,zh=profile['screw_z']
        for z in (zl,zh):
            for edge in (profile['bottom_z'],profile['top_z']):
                if abs(z-edge)<self.screw_support_radius_mm+self.opening_transition_clearance_mm:
                    raise ValueError('Service edge violates M3 material envelope')
        return radial

    @property
    def theta(self):
        return math.radians(self.display_angle_deg)

    @property
    def tangent(self):
        return (math.cos(self.theta), math.sin(self.theta))

    @property
    def normal(self):
        return (-math.sin(self.theta), math.cos(self.theta))

    @property
    def clamp_inner_half(self):
        return self.rail_nominal_size_mm / 2 + self.rail_clearance_mm

    @property
    def bridge_bottom(self):
        return self.clamp_inner_half

    @property
    def bridge_top(self):
        return self.clamp_inner_half + self.upper_clamp_bridge_thickness_mm

    def rail(self, path=DEFAULT_RAIL):
        imported = cq.importers.importStep(str(path))
        solids = imported.solids().vals()
        if len(solids) != 1:
            raise ValueError('Expected exactly one solid in user rail STEP')
        rail = solids[0]
        bb = rail.BoundingBox()
        if abs(bb.xlen - 20) > .05 or abs(bb.ylen - 20) > .05:
            raise ValueError(f'Unexpected actual rail STEP dimensions: {bb.xlen} x {bb.ylen}')
        if abs(bb.zlen - self.rail_reference_length_mm) > .05:
            raise ValueError('Reference STEP length differs from config; do not stretch a source STEP')
        # +Z -> +X, +X -> +Y, +Y -> +Z; a proper rigid rotation.
        return check_solid('rail', rail.rotate((0, 0, 0), (1, 1, 1), 120))

    def plate_plane(self):
        return cq.Plane(
            origin=(0, self.arm_front_y_mm, self.arm_front_z_mm),
            xDir=(1, 0, 0),
            normal=(0, self.normal[0], self.normal[1]),
        )

    def path_point(self, s, offset=0):
        """Side-section coordinate (Y,Z) at sloped station s; +offset toward screen."""
        return (self.arm_front_y_mm + s * self.tangent[0] + offset * self.normal[0],
                self.arm_front_z_mm + s * self.tangent[1] + offset * self.normal[1])

    def upper_clamp(self):
        length = self.upper_clamp_length_mm
        w = self.upper_clamp_width_mm
        top = block(-length/2, -w/2, self.bridge_bottom,
                    length, w, self.upper_clamp_bridge_thickness_mm)
        wall = w/2 - self.clamp_inner_half
        bottom = self.upper_clamp_sidewall_bottom_z_mm
        leg_height = self.bridge_top - bottom
        walls = [block(-length/2, sign*self.clamp_inner_half if sign > 0 else -w/2,
                       bottom, length, wall, leg_height) for sign in (-1, 1)]
        body = union(top, *walls)
        if self.top_slot_key_enabled:
            key = block(-self.top_slot_key_length_mm/2, -self.top_slot_key_width_mm/2,
                        self.bridge_bottom-self.top_slot_key_projection_mm,
                        self.top_slot_key_length_mm, self.top_slot_key_width_mm,
                        self.top_slot_key_projection_mm+.1)
            body = union(body, key)
        # Blind M4 heat-set pockets inserted from below; NO tapped-printed threads assumed.
        for x in self.clamp_screw_x_mm:
            for y in (-self.clamp_screw_y_abs_mm, self.clamp_screw_y_abs_mm):
                tool = cyl(self.clamp_insert_pocket_d_mm / 2,
                           self.clamp_insert_pocket_depth_mm + .01,
                           (x, y, bottom - .005))
                body = body.cut(tool)
        return check_solid('upper_saddle', body.clean())

    def keeper(self):
        length, width = self.upper_clamp_length_mm, self.upper_clamp_width_mm
        top = self.lower_keeper_top_z_mm
        t = self.lower_keeper_thickness_mm
        solid = block(-length/2, -width/2, top-t, length, width, t)
        for x in self.clamp_screw_x_mm:
            for y in (-self.clamp_screw_y_abs_mm, self.clamp_screw_y_abs_mm):
                tool = cyl(self.clamp_screw_clearance_d_mm/2, t+2,
                           (x,y,top-t-1))
                # Clear screw head to at least 8.0 mm in lower face.
                cb = cyl(4.0, 2.0, (x, y, top-t-.005))
                solid = solid.cut(tool).cut(cb)
        # Round only the four vertical outside corners; preserve the M4
        # bearing faces, counterbores and clamp datum planes exactly.
        if self.keeper_corner_fillet_mm>0:
            solid=cq.Workplane(obj=solid).edges('|Z').fillet(self.keeper_corner_fillet_mm).val()
        return check_solid('keeper', solid.clean())

    def rib_profile_stations(self):
        """V006: exterior YZ wire includes rear diagonal saddle-to-arm gusset."""
        z_foot=self.bridge_top-self.arm_saddle_intersection_mm
        # Keep a rounded, compact cap above the upper fastener rather than
        # V010's tall rectangular front tower. Derived from the M3 station.
        profile=self.adaptive_profile
        z_top=profile['screw_z'][1]+self.upper_boss_cap_extra_mm
        back=self.upper_clamp_width_mm/2-self.arm_gusset_saddle_overlap_mm
        root_z=self.upper_clamp_sidewall_bottom_z_mm+self.arm_gusset_bottom_relief_mm
        if not (0<self.arm_gusset_saddle_overlap_mm<self.upper_clamp_width_mm/2):
            raise ValueError("Invalid rear saddle overlap")
        if not (root_z<self.bridge_bottom-3 and self.arm_outer_lower_rear_y_mm>back+12):
            raise ValueError("Exterior rear gusset geometry invalid")
        return [
            (-self.upper_clamp_width_mm/2,z_foot),
            (back,z_foot),
            (back,root_z),
            (self.arm_outer_lower_rear_y_mm,z_foot),
            (self.arm_outer_rear_bulge_y_mm,profile['outer_bulge_z']),
            (self.arm_outer_rear_shoulder_y_mm,z_top),
            (self.arm_front_y_mm+self.arm_top_land_mm,z_top),
            (self.arm_front_y_mm+self.arm_top_land_mm,self.arm_front_z_mm),
            (-self.upper_clamp_width_mm/2,z_foot),
        ]

    def rib_profile_geometry(self):
        """Return connected analytic lines/arcs with mathematically G1 joins.

        Fillet tangent offsets are R*tan(turn/2). A circular arc is defined
        from the two tangent points and the angle-bisector midpoint. The
        geometric radius is therefore exact; no heuristic three-point arcs.
        """
        import math
        pts = self.rib_profile_stations()[:-1]
        radii = [self.arm_toe_radius_mm, 0, 0, self.arm_lower_rear_fillet_mm,
                 self.arm_rear_transition_fillet_mm,
                 self.arm_upper_shoulder_fillet_mm,
                 self.arm_front_top_fillet_mm,
                 self.arm_front_foot_fillet_mm]
        result=[]
        n=len(pts)
        for i,p in enumerate(pts):
            prev=pts[(i-1)%n]; nex=pts[(i+1)%n]
            v=(prev[0]-p[0],prev[1]-p[1])
            w=(nex[0]-p[0],nex[1]-p[1])
            lv=math.hypot(*v); lw=math.hypot(*w)
            if min(lv,lw)<1e-8:
                raise ValueError('Degenerate V004 rib station')
            u=(v[0]/lv,v[1]/lv); q=(w[0]/lw,w[1]/lw)
            angle=math.acos(max(-1,min(1,u[0]*q[0]+u[1]*q[1])))
            r=radii[i]
            if not r:
                result.append({'entry':p,'exit':p,'mid':None,'radius':0})
                continue
            d=r/math.tan(angle/2)
            if d>=min(lv,lw)*0.47:
                raise ValueError(f'V004 fillet radius at station {i} exceeds available tangent length')
            a=(p[0]+u[0]*d,p[1]+u[1]*d)
            b=(p[0]+q[0]*d,p[1]+q[1]*d)
            bis=(u[0]+q[0],u[1]+q[1])
            lb=math.hypot(*bis)
            center=(p[0]+bis[0]/lb*r/math.sin(angle/2),
                    p[1]+bis[1]/lb*r/math.sin(angle/2))
            va=(a[0]-center[0],a[1]-center[1])
            vb=(b[0]-center[0],b[1]-center[1])
            midv=(va[0]+vb[0],va[1]+vb[1])
            lm=math.hypot(*midv)
            mid=(center[0]+r*midv[0]/lm,center[1]+r*midv[1]/lm)
            result.append({'entry':a,'exit':b,'mid':mid,'radius':r,
                           'center':center,'incoming':u,'outgoing':q})
        return result

    def rib_workplane(self):
        sections=self.rib_profile_geometry()
        wire=cq.Workplane('YZ').moveTo(*sections[0]['exit'])
        for j in range(1,len(sections)+1):
            s=sections[j%len(sections)]
            wire=wire.lineTo(*s['entry'])
            if s['mid'] is not None:
                wire=wire.threePointArc(s['mid'],s['exit'])
        return wire.close()

    def arm_service_opening(self,side):
        """One open-front YZ cavity, not a fused capsule and polygon.

        The only two fillets visible in the remaining arm are the integral
        back corners of this cutter. The cutter's own front rounding is
        deliberately outside the real arm, avoiding a second slot, shoulder,
        and non-tangent internal lip. Both M3 tab endpoints depend on their
        fastener positions via adaptive_profile.
        """
        if side not in (-1,1):
            raise ValueError('side must be -1 or +1')
        p=self.adaptive_profile
        zlo,zhi=p['bottom_z'],p['top_z']
        entry=self.arm_front_y_mm-self.service_cutter_front_overshoot_mm
        radius=self.arm_opening_corner_radius_mm
        if entry>=self.arm_front_y_mm-2*radius:
            raise ValueError('Unified U cutter front rounding would touch a mounting tab')
        if p['rear_bottom_y']<=self.arm_front_y_mm+self.arm_opening_front_wall_mm:
            raise ValueError('U opening has insufficient rear screwdriver reach')
        # Four-sided opening footprint; precise G1 corner fillets are made
        # on its X-parallel edges. No second bore or capsule is added.
        cutter=(cq.Workplane('YZ')
                .polyline([(entry,zlo),(p['rear_bottom_y'],zlo),
                           (p['rear_top_y'],zhi),(entry,zhi)])
                .close().extrude(self.arm_thickness_mm+2)
                .edges('|X').fillet(radius)
                .val().translate((-1,0,0)))
        return check_solid('unified_front_u_cutter',cutter.clean())

    def trim_forward_arm_face(self, arm, side):
        """Lofted full-width gusset -> narrow M3 front neck transition.

        V010/V011 used an abrupt extruded XY wedge beginning at fixed Z,
        leaving hard root ledges at the two front gussets. This construction
        derives Z from the lowest M3 station and eases side material removal
        in five deterministic ruled sections. It does not notch the M3 seat.
        """
        trim=self.arm_front_rail_side_trim_mm
        if trim<=0:
            return arm
        half=self.arm_thickness_mm/2
        center=side*self.support_arm_center_spacing_mm/2
        ymin=self.arm_front_y_mm+self.arm_top_land_mm
        yend=ymin+self.arm_front_rail_taper_depth_mm
        z0=self.arm_front_z_mm+self.arm_front_neck_start_above_datum_mm
        h=self.front_neck_blend_height_mm
        z1=self.path_point(self.mounting_stations_s_mm[1])[1]+self.upper_boss_cap_extra_mm+2
        zl=self.adaptive_profile['screw_z'][0]
        if not (h>1 and z0+h<zl-self.board_driver_access_d_mm/2-1):
            raise ValueError('Front root blend must terminate below lower M3 passage')
        if z1<=z0+h:
            raise ValueError('Upper mounting region below neck blend')
        for sign in (-1,1):
            edge=center+sign*half
            outer=edge+sign
            wires=[]
            for fraction,z in ((0,z0),(.25,z0+.25*h),(.5,z0+.5*h),
                               (.75,z0+.75*h),(1,z0+h),(1,z1)):
                easing=3*fraction*fraction-2*fraction*fraction*fraction
                inset=edge-sign*max(.02,trim*easing)
                xy=[(outer,ymin-2),(inset,ymin-2),(inset,ymin),
                    (edge,yend),(outer,yend)]
                w=cq.Workplane('XY').polyline(xy).close().wire().val()
                wires.append(w.translate((0,0,z)))
            # Ruled loft is bounded by its control sections. An unconstrained
            # high-order loft can overshoot catastrophically for long arms.
            relief=cq.Solid.makeLoft(wires,ruled=True)
            if not relief.isValid():
                raise ValueError('Invalid blended front-neck relief')
            arm=arm.cut(relief)
        return check_solid('lofted_front_neck',arm.clean())

    def arm(self,side):
        """The sculpted arm itself carries M3 seats and rear driver passages.

        No separate rail/plate/pad is constructed. Four heads sit inside the
        arm thickness against a floor; only Ø3.4 passes through to the PCB.
        """
        if side not in (-1,1): raise ValueError('Invalid side')
        center=side*self.support_arm_center_spacing_mm/2
        mx=self.mounting_x_centers_mm[0 if side<0 else 1]
        arm=self.rib_workplane().extrude(self.arm_thickness_mm).val()
        arm=arm.cut(self.arm_service_opening(side)).clean()
        arm=arm.translate((center-self.arm_thickness_mm/2,0,0))
        arm=self.trim_forward_arm_face(arm,side)
        face_y=self.arm_front_y_mm+self.arm_top_land_mm
        floor=self.mount_pad_axial_thickness_mm-self.board_counterbore_depth_mm
        for station in self.mounting_stations_s_mm:
            z=self.path_point(station)[1]
            boss=cyl(self.display_standoff_diameter_mm/2,self.display_standoff_height_mm,
                     (mx,face_y,z),(0,-1,0))
            arm=arm.fuse(boss)
            bore=cyl(self.board_screw_clearance_d_mm/2,
                     floor+self.display_standoff_height_mm+2,
                     (mx,face_y-self.display_standoff_height_mm-1,z),(0,1,0))
            seat=cyl(self.board_screw_head_access_d_mm/2,self.board_counterbore_depth_mm+.02,
                     (mx,face_y+floor-.01,z),(0,1,0))
            # A true rear-entry tunnel is extended beyond the ACTUAL exterior,
            # not stopped at an arbitrary historical fixed tool length.
            rear_outer=arm.BoundingBox().ymax
            start_y=face_y+self.mount_pad_axial_thickness_mm
            length=max(self.board_driver_access_length_mm,
                       rear_outer-start_y+self.v013_rear_tool_overrun_mm)
            driver=cyl(self.board_driver_access_d_mm/2,length,
                       (mx,start_y,z),(0,1,0))
            arm=arm.cut(bore).cut(seat).cut(driver)
        return check_solid(('left' if side<0 else 'right')+'_integral_arm',arm.clean())

    def port_service_envelope(self,side):
        """Nominal side-specific open-front SD/USB corridor, not a PCB scan."""
        if side not in (-1,1): raise ValueError('Invalid service side')
        relief=self.cfg['sd_relief' if side<0 else 'usb_relief']
        x=side*self.support_arm_center_spacing_mm/2
        width=relief['inner_cut_width_mm']
        length=relief['length_mm']
        return block(x-width/2,-3,relief['station_mm']-length/2,width,25,length)

    def integrated_support(self):
        """One printable support: keyed clamp + TWO arm-integrated M3 mounts."""
        self.validate_mount_dimensions()
        clamp=self.upper_clamp()
        la,ra=self.arm(-1),self.arm(1)
        tie_y=self.arm_outer_lower_rear_y_mm-9
        cross=block(-self.support_arm_center_spacing_mm/2-self.arm_thickness_mm/2,
                    tie_y,self.bridge_top,
                    self.support_arm_center_spacing_mm+self.arm_thickness_mm,8,9)
        return check_solid('integrated_main_frame',union(clamp,la,ra,cross))

    def screen_reference(self):
        # ONLY nominal envelope, not the actual display geometry.
        plane=self.plate_plane()
        # Thin translucent-view reference in rendered views (separate STEP part).
        return cq.Workplane(plane).center(0,self.display_height_along_slope_mm/2).rect(
            self.display_width_mm,self.display_height_along_slope_mm
        ).extrude(self.nominal_display_reference_thickness_mm).translate((
            0,self.normal[0]*(self.display_standoff_height_mm+.75),
            self.normal[1]*(self.display_standoff_height_mm+.75))).val()

    def boardscrews(self):
        """M3 reference fasteners inside structural-arm counterbores."""
        result=[]
        seat_y=self.arm_front_y_mm+self.arm_top_land_mm+self.mount_pad_axial_thickness_mm-self.board_counterbore_depth_mm
        for x in self.mounting_x_centers_mm:
            for station in self.mounting_stations_s_mm:
                z=self.path_point(station)[1]
                shaft=cyl(self.board_screw_nominal_diameter_mm/2,self.board_screw_length_reference_mm,(x,seat_y,z),(0,-1,0))
                head=cyl(self.board_screw_head_diameter_mm/2,self.board_screw_head_height_mm,(x,seat_y,z),(0,1,0))
                result.append(union(shaft,head))
        return result

    def clampscrews(self):
        result=[]
        top=self.lower_keeper_top_z_mm
        for x in self.clamp_screw_x_mm:
            for y in (-self.clamp_screw_y_abs_mm,self.clamp_screw_y_abs_mm):
                shaft=cyl(2,14,(x,y,top-self.lower_keeper_thickness_mm+.5))
                head=cyl(3.8,1.8,(x,y,top-self.lower_keeper_thickness_mm-1.3))
                result.append(union(shaft,head))
        return result

    def validate(self,parts):
        rail=parts['rail']
        main=parts['main']
        keeper=parts['keeper']
        self.validate_mount_dimensions()
        report={
            'rail_bbox_mm': [rail.BoundingBox().xlen,rail.BoundingBox().ylen,rail.BoundingBox().zlen],
            'nominal_display_hole_centers_x_s_mm': [[x,s] for x in self.mounting_x_centers_mm for s in self.mounting_stations_s_mm],
            'clamp_fastener_centers_xy_mm': [[x,y] for x in self.clamp_screw_x_mm for y in (-self.clamp_screw_y_abs_mm,self.clamp_screw_y_abs_mm)],
            'parameters_provisional': True,
            'verification_scope': 'nominal CAD solids and reference clearances only; not physically fitted'
        }
        for key in ['rail','upper_saddle','keeper','left_arm','right_arm','main']:
            s=parts[key]
            check_solid(key,s)
            report[f'{key}_volume_mm3']=round(s.Volume(),2)
        # Solid-to-solid interference, not clearance envelope or actual surface fit.
        tests={'main_vs_rail': (main,rail), 'keeper_vs_rail': (keeper,rail),
               'main_vs_keeper':(main,keeper)}
        for name,(a,b) in tests.items():
            vol=a.intersect(b).Volume()
            report[name+'_overlap_mm3']=round(vol,5)
            if vol>0.01:
                raise ValueError(f'{name}: solid collision volume {vol:.4f} mm^3')
        # The saddle bearing plane is XY (Z-up normal); carrier is XZ at 90.
        # Their projected lower mounting datums coincide at Y=0.
        report['carrier_angle_to_saddle_deg']=self.display_angle_deg
        report['carrier_to_saddle_center_offset_y_mm']=self.arm_front_y_mm
        report['carrier_perpendicular_to_saddle']=abs(self.display_angle_deg-90.0)<.00001
        report['carrier_centered_over_saddle']=abs(self.arm_front_y_mm)<.00001
        if self.cfg.get('require_perpendicular_display', False) and abs(self.display_angle_deg-90.0)>.00001:
            raise ValueError('Display face must be perpendicular to saddle inside bearing plane')
        if self.cfg.get('require_display_centering', False) and abs(self.arm_front_y_mm)>.00001:
            raise ValueError('Display datum must be centered over saddle in Y')
        # The shallow mouth-entry key must be inside the source rail's actual
        # +Z T-slot void. It is an indexing feature, not the load-bearing fastener.
        # Probe real material in the lower rear region that was empty in V006.
        stations=self.rib_profile_stations()
        root=stations[2]
        sample=block(-self.support_arm_center_spacing_mm/2-self.arm_thickness_mm/2+1,
                     root[0]+8,self.bridge_bottom-1,2,2,2)
        vol=parts['left_arm'].intersect(sample).Volume()
        report['visible_rear_gusset_root_yz_mm']=[round(v,4) for v in root]
        report['visible_rear_gusset_sample_mm3']=round(vol,4)
        if root[1]>=self.bridge_bottom-3 or vol<1:
            raise ValueError('Exterior rear gusset missing from actual BREP')
        report['top_slot_key_enabled']=bool(self.top_slot_key_enabled)
        if self.top_slot_key_enabled:
            key=block(-self.top_slot_key_length_mm/2,
                      -self.top_slot_key_width_mm/2,
                      self.bridge_bottom-self.top_slot_key_projection_mm,
                      self.top_slot_key_length_mm,self.top_slot_key_width_mm,
                      self.top_slot_key_projection_mm)
            kv=key.intersect(rail).Volume()
            report['top_slot_key_rail_overlap_mm3']=round(kv,5)
            if kv>.01:
                raise ValueError(f'Top locating key hits rail: {kv} mm3')
        # Test uninterrupted access from rear through the integral arm to M3 head.
        face=self.arm_front_y_mm+self.arm_top_land_mm
        for x in self.mounting_x_centers_mm:
            for station in self.mounting_stations_s_mm:
                z=self.path_point(station)[1]
                tool=cyl(self.rear_access_tool_diameter_mm/2,self.board_driver_access_length_mm-.2,
                         (x,face+self.mount_pad_axial_thickness_mm+.1,z),(0,1,0))
                vol=tool.intersect(main).Volume()
                report[f'rear_tool_clearance_x{x:g}_s{station:g}_mm3']=round(vol,5)
                if vol>.03:
                    raise ValueError(f'Blocked rear driver at X={x}, S={station}: {vol} mm3')
        # Verify actual 3D service corridors remain free of bracket solids.
        for side,label in [(-1,'sd'),(1,'usb')]:
            branch=self.cfg['service_left' if side<0 else 'service_right']
            center=side*self.support_arm_center_spacing_mm/2
            profile=self.adaptive_profile
            width=branch['throat_width_mm']
            margin=self.service_throat_min_boundary_margin_mm
            throat_center=min(max(branch['throat_center_z_mm'],
                                  profile['bottom_z']+width/2+margin),
                              profile['top_z']-width/2-margin)
            # The V010 path enters from Y<0 at the display side, not from
            # the exterior rear slope. Check the actual front opening up to Y=23.
            probe=block(center-1,branch['throat_start_y_mm']+2,
                        throat_center-1,2,
                        self.arm_opening_front_wall_mm+8,2)
            if parts['left_arm' if side<0 else 'right_arm'].intersect(probe).Volume()>.01:
                raise ValueError(f'{label}: side-entry throat is blocked')
            corridor=self.port_service_envelope(side)
            overlap=main.intersect(corridor).Volume()
            report[f'{label}_service_envelope_overlap_mm3']=round(overlap,5)
            report[f'{label}_throat_width_mm']=branch['throat_width_mm']
            report[f'{label}_adaptive_throat_center_z_mm']=throat_center
            if overlap>.01:
                raise ValueError(f'{label} port/cable provisional service volume obstructed: {overlap}')
        report['mount_hole_center_spacing_mm']=self.mount_hole_center_spacing_mm
        report['support_arm_center_spacing_mm']=self.support_arm_center_spacing_mm
        report['integral_arm_mount_stations_s_mm']=list(self.mounting_stations_s_mm)
        report['m3_pocket_floor_wall_mm']=round(self.mount_pad_axial_thickness_mm-self.board_counterbore_depth_mm,4)
        report['m3_pocket_radial_wall_mm']=round(self.validate_mount_dimensions(),4)
        profile=self.adaptive_profile
        report['v012_unified_u_cutter']=True
        report['v012_neck_root_blend_height_mm']=self.front_neck_blend_height_mm
        report['v012_mount_tab_clearance_from_screw_z_mm']=[
            round(profile['bottom_z']-profile['screw_z'][0],4),
            round(profile['screw_z'][1]-profile['top_z'],4)]
        fixture=json.loads((ROOT/self.hardware_reference_manifest_path).read_text())
        measured=fixture['reference_mounts_xy_mm']
        xs=sorted(set(p[0] for p in measured));ys=sorted(set(p[1] for p in measured))
        if len(xs)!=2 or len(ys)!=2 or len(measured)!=4:
            raise ValueError('Waveshare STEP datum manifest must define four rectangle-corner centers')
        observed_x_pitch=round(xs[-1]-xs[0],4)
        observed_z_pitch=round(ys[-1]-ys[0],4)
        report['waveshare_step_mount_reference']={
            'source_sha256':fixture['source_sha256'],
            'source_bbox_mm':fixture['source_bbox_mm'],
            'native_centers_xy_mm':measured,
            'hole_diameter_mm':fixture['hole_diameter_mm'],
            'measured_x_pitch_mm':observed_x_pitch,
            'measured_y_pitch_mm':observed_z_pitch,
            'modeled_x_pitch_mm':self.mount_hole_center_spacing_mm,
            'modeled_z_pitch_mm':self.board_screw_vertical_pitch_mm,
            'x_pitch_mismatch_mm':round(self.mount_hole_center_spacing_mm-observed_x_pitch,4),
            'z_pitch_mismatch_mm':round(self.board_screw_vertical_pitch_mm-observed_z_pitch,4),
            'registered_to_bracket':False,
            'approved_to_print_for_hardware_fit':False}
        if self.hardware_reference_fit_required:
            raise ValueError('Waveshare STEP native hole datum is not registered to 2020 saddle; physical-fit mode cannot pass')
        report['v013_deeper_u_opening']={
            'lower_z_mm':profile['bottom_z'],
            'upper_z_mm':profile['top_z'],
            'rear_lower_y_mm':profile['rear_bottom_y'],
            'rear_upper_y_mm':profile['rear_top_y'],
            'corner_radius_mm':self.arm_opening_corner_radius_mm,
            'top_rear_spine_web_mm':round(profile['top_slope_rear_web_y'],4),
            'lower_rear_spine_web_mm':round(profile['lower_slope_rear_web_y'],4)}
        report['v013_rear_driver_tunnels']={
            'count':4,
            'diameter_mm':self.board_driver_access_d_mm,
            'minimum_exit_overrun_mm':self.v013_rear_tool_overrun_mm,
            'type':'enclosed round axial passages where surrounding solid exists',
            'bearing_floor_mm':round(self.mount_pad_axial_thickness_mm-self.board_counterbore_depth_mm,4)}
        report['v011_pitch_driven_support_profile']=profile
        report['v011_required_m3_support_radius_mm']=self.screw_support_radius_mm
        report['v011_min_screw_web_mm']=self.min_screw_envelope_web_mm
        report['v011_center_pitch_mm']=self.board_screw_vertical_pitch_mm
        report['v011_front_opening_bounds_z_mm']=[profile['bottom_z'],profile['top_z']]
        report['v010_front_neck_width_mm']=self.front_neck_width_mm
        report['v010_front_side_trim_mm']=self.arm_front_rail_side_trim_mm
        report['v010_front_draft_depth_mm']=self.arm_front_rail_taper_depth_mm
        report['v010_upper_tip_above_m3_mm']=self.upper_boss_cap_extra_mm
        report['v010_analytic_outer_corner_radii_mm']=[
            self.arm_toe_radius_mm, self.arm_front_top_fillet_mm,
            self.arm_front_foot_fillet_mm, self.arm_lower_rear_fillet_mm,
            self.arm_rear_transition_fillet_mm, self.arm_upper_shoulder_fillet_mm]
        report['v010_keeper_corner_fillet_mm']=self.keeper_corner_fillet_mm
        report['service_front_opening_yz_target_mm']=[0,20,60,80]
        report['detached_carrier_count']=0
        report['integral_arm_m3_holes']=4
        report['rear_sheet_removed']=True
        report['status']='PASS V013: enlarged U arm apertures, retained minimum spine web, four rear-exit M3 tool tunnels; Waveshare pad datum unregistered'
        return report


def export_step(shape,path):
    exporters.export(shape,str(path),exportType='STEP')


def export_stl(shape,path):
    exporters.export(shape,str(path),exportType='STL',tolerance=0.08,angularTolerance=0.15)


def waveshare_mount_datum_fixture(d):
    """Simplified standalone footprint from user STEP hole axes, not the PCB."""
    m=json.loads((ROOT/d.hardware_reference_manifest_path).read_text())
    bb=m['source_bbox_mm']
    shell=block(bb['xmin'],bb['ymin'],0,bb['xmax']-bb['xmin'],
                bb['ymax']-bb['ymin'],1.6)
    for x,y in m['reference_mounts_xy_mm']:
        shell=shell.cut(cyl(m['hole_diameter_mm']/2,3,(x,y,-.5)))
    return check_solid('waveshare_hole_pattern_fixture',shell.clean())


def render_waveshare_datum(d,output):
    """Auditable plot of native STEP-hole datum vs unregistered V013 proposal."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle
    m=json.loads((ROOT/d.hardware_reference_manifest_path).read_text())
    bb=m['source_bbox_mm']
    fig,ax=plt.subplots(figsize=(11,5.5),dpi=140)
    ax.add_patch(Rectangle((bb['xmin'],bb['ymin']),
                           bb['xmax']-bb['xmin'],bb['ymax']-bb['ymin'],
                           facecolor='#dbeafe',edgecolor='#334155',lw=2))
    for x,y in m['reference_mounts_xy_mm']:
        ax.add_patch(Circle((x,y),m['hole_diameter_mm']/2,
                            facecolor='#ffffff',edgecolor='#1d4ed8',lw=2))
        ax.plot(x,y,'o',color='#1d4ed8',markersize=5)
        ax.text(x+2,y+(3 if y>0 else -4),f'({x:g}, {y:g})',fontsize=8)
    ax.plot([],[],'o',color='#1d4ed8',label='Source STEP: four circled hole centers')
    ax.set_xlim(-112,112);ax.set_ylim(-47,47);ax.set_aspect('equal')
    ax.set_title('Waveshare 0820-1 STEP / extracted four-hole datum — V013',weight='bold')
    ax.set_xlabel('Native STEP X / mm');ax.set_ylabel('Native STEP Y / mm')
    ax.text(-103,-43,'Measured: X pitch 114, Y pitch 59.1 mm. Bracket config still 78 × 45; NOT FIT-CERTIFIED.',
            fontsize=9,color='#991b1b')
    ax.grid(alpha=.18);fig.tight_layout()
    outpath=output/'waveshare_mount_datums.png'
    fig.savefig(outpath,dpi=140);plt.close(fig)
    return str(outpath.relative_to(output.parent))


def render_views(parts, output):
    """Actual model-derived geometry via CadQuery tessellation + VTK rasterizer."""
    try:
        import vtk
    except ImportError:
        print('VTK missing; skipping preview generation (CAD exports unaffected)')
        return []

    def actor_for(s,color,opacity=1.0):
        vertices, faces=s.tessellate(0.18,0.25)
        points=vtk.vtkPoints()
        for v in vertices: points.InsertNextPoint(v.x,v.y,v.z)
        polys=vtk.vtkCellArray()
        for f in faces:
            tri=vtk.vtkTriangle()
            for i,idx in enumerate(f): tri.GetPointIds().SetId(i,idx)
            polys.InsertNextCell(tri)
        data=vtk.vtkPolyData();data.SetPoints(points);data.SetPolys(polys)
        normals=vtk.vtkPolyDataNormals()
        normals.SetInputData(data);normals.ConsistencyOn();normals.AutoOrientNormalsOn();normals.Update()
        mapper=vtk.vtkPolyDataMapper(); mapper.SetInputConnection(normals.GetOutputPort())
        a=vtk.vtkActor();a.SetMapper(mapper)
        a.GetProperty().SetColor(*color);a.GetProperty().SetOpacity(opacity)
        a.GetProperty().SetAmbient(.30);a.GetProperty().SetDiffuse(.69)
        a.GetProperty().SetSpecular(.16);a.GetProperty().SetSpecularPower(20)
        a.GetProperty().EdgeVisibilityOff()
        return a

    palette={'rail':(.64,.67,.70),'main':(.39,.44,.51),'keeper':(.90,.44,.14),
             'screen':(.05,.45,.61),'m4':(.86,.88,.91),'m25':(.95,.77,.23),
             'upper_saddle':(.35,.38,.43),
             'left_arm':(.90,.44,.14),'right_arm':(.90,.44,.14)}
    scenes={
      'assembly_isometric': [('rail',1.0),('main',1.0),('keeper',1.0),('screen',0.42),('m4',1.0),('m25',1.0)],
      'main_frame_only': [('main',1.0)],
      'side_section': [('rail',.3),('main',1.0),('keeper',1.0),('screen',0.4)],
      'saddle_clamp': [('rail',.35),('upper_saddle',1.0),('keeper',1.0)],
      'integrated_display_mount': [('main',1.0),('m25',1.0)],
      'rear_screw_access': [('rail',.35),('main',1.0),('keeper',1.0),('m4',1.0),('m25',1.0)],
      'rear_tool_tunnels_oblique': [('main',1.0),('m25',.32)],
    }
    saved=[]
    for name,entities in scenes.items():
        renderer=vtk.vtkRenderer()
        renderer.SetBackground(1,1,1)
        for key,opacity in entities:
            shapes=parts['clamp_screws'] if key=='m4' else parts['board_screws'] if key=='m25' else [parts[key]]
            for shape in shapes:
                renderer.AddActor(actor_for(shape,palette[key],opacity))
        window=vtk.vtkRenderWindow();window.SetOffScreenRendering(1)
        window.AddRenderer(renderer);window.SetSize(1500,1100)
        renderer.ResetCamera()
        camera=renderer.GetActiveCamera();camera.ParallelProjectionOn()
        if name=='rear_screw_access':
            camera.SetPosition(0,205,-102);camera.SetFocalPoint(0,8,50)
        elif name=='rear_tool_tunnels_oblique':
            camera.SetPosition(185,240,155);camera.SetFocalPoint(0,34,75)
        elif name=='side_section':
            camera.SetPosition(450,-260,160);camera.SetFocalPoint(0,9,48)
            # view mostly along +X side, slightly perspective for paired arms
        elif name=='integrated_display_mount':
            camera.SetPosition(220,-180,230);camera.SetFocalPoint(0,0,70)
        elif name=='saddle_clamp':
            camera.SetPosition(160,-180,110);camera.SetFocalPoint(0,0,0)
        else:
            camera.SetPosition(210,-245,180);camera.SetFocalPoint(0,10,47)
        camera.SetViewUp(0,0,1)
        renderer.ResetCamera()
        camera.SetParallelScale(camera.GetParallelScale()*1.02)
        window.Render()
        filt=vtk.vtkWindowToImageFilter();filt.SetInput(window);filt.SetInputBufferTypeToRGB();filt.ReadFrontBufferOff();filt.Update()
        dest=output/f'{name}.png'
        writer=vtk.vtkPNGWriter();writer.SetFileName(str(dest));writer.SetInputConnection(filt.GetOutputPort());writer.Write()
        saved.append(str(dest.relative_to(output.parent)))
        window.Finalize()
    return saved



def render_engineering_side_profile(d, output):
    """Exact dimension-driven side layout of generated model (Y horizontal, Z vertical)."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from matplotlib.patches import Polygon, Rectangle, Circle
    except ImportError:
        return None
    fig,ax=plt.subplots(figsize=(13,9),dpi=165)
    fig.patch.set_facecolor('#ffffff')
    ax.set_facecolor('#f8fafc')
    # The rotated rail's YZ section is the original supplied STEP bounding box.
    ax.add_patch(Rectangle((-10,-10),20,20,facecolor='#b0bac6',
                            edgecolor='#334155',linewidth=1.8,zorder=4))
    ax.text(0,0,'2020\nRAIL',ha='center',va='center',fontsize=10,weight='bold',color='#334155',zorder=7)
    # Project the actual curved parametric wire into the engineering drawing.
    # Trace edges in connectivity order; do not connect unordered BREP edges.
    def curve_points(wire):
        """Sample connected BREP edges using their actual parametric direction.

        OCCT Face.outerWire().Edges() may expose reversed topological edge
        orientation: Edge.startPoint() can disagree with positionAt(0).
        Connecting sample arrays without checking the parametric endpoints
        draws false diagonals across the profile. Use positionAt(0/1) for
        BOTH connectivity and sampling orientation.
        """
        edges=list(wire.Edges())
        if not edges:
            raise ValueError('Empty source BREP boundary')
        ring=[]
        first=edges.pop(0)
        count=max(3,int(first.Length()/0.3))
        ring.extend((first.positionAt(i/count).y,first.positionAt(i/count).z)
                    for i in range(count))
        last=first.positionAt(1)
        while edges:
            best=None
            for index,e in enumerate(edges):
                for reversed_param,t in ((False,0),(True,1)):
                    dist=(e.positionAt(t)-last).Length
                    if best is None or dist<best[0]:
                        best=(dist,index,reversed_param)
            dist,index,reversed_param=best
            if dist>0.01:
                raise ValueError(f'Disconnected source wire: {dist:.4f} mm gap')
            e=edges.pop(index)
            count=max(3,int(e.Length()/0.3))
            for n in range(count):
                point=e.positionAt(1-n/count if reversed_param else n/count)
                ring.append((point.y,point.z))
            last=e.positionAt(0 if reversed_param else 1)
        return ring
    support_pts=curve_points(d.rib_workplane().wire().val())
    ax.add_patch(Polygon(support_pts,closed=True,facecolor='#475569',edgecolor='#1e293b',lw=1.8,zorder=3))
    # Draw ACTUAL planar section of cut arm (including open rear throat).
    # V006 drew a now-nonexistent enclosed aperture on the outside polygon.
    arm_section=d.arm(-1)
    yz_faces=[f for f in arm_section.Faces() if abs(f.normalAt().x)>.999]
    if not yz_faces:
        raise ValueError('No planar support side found for section drawing')
    boundary=max(yz_faces,key=lambda f:f.Area()).outerWire()
    ax.patches[-1].remove()
    ax.add_patch(Polygon(curve_points(boundary),closed=True,
                         facecolor='#475569',edgecolor='#1e293b',
                         lw=1.8,zorder=3))
    clamp_y = d.upper_clamp_width_mm/2
    inside = d.clamp_inner_half
    ax.add_patch(Rectangle((-clamp_y,d.bridge_bottom),d.upper_clamp_width_mm,
                            d.upper_clamp_bridge_thickness_mm,facecolor='#334155',edgecolor='#1e293b',zorder=5))
    for left in (-clamp_y,inside):
        ax.add_patch(Rectangle((left,d.upper_clamp_sidewall_bottom_z_mm),clamp_y-inside,
                               d.bridge_top-d.upper_clamp_sidewall_bottom_z_mm,
                               facecolor='#334155',edgecolor='#1e293b',zorder=5))
    ax.add_patch(Rectangle((-clamp_y,d.lower_keeper_top_z_mm-d.lower_keeper_thickness_mm),
                            d.upper_clamp_width_mm,d.lower_keeper_thickness_mm,
                            facecolor='#d97706',edgecolor='#9a3412',zorder=5))
    if d.top_slot_key_enabled:
        ax.add_patch(Rectangle((-d.top_slot_key_width_mm/2,d.bridge_bottom-d.top_slot_key_projection_mm),
                               d.top_slot_key_width_mm,d.top_slot_key_projection_mm,
                               facecolor='#0f766e',edgecolor='#065f46',zorder=8))
    p0 = d.path_point(0)
    p1 = d.path_point(d.display_height_along_slope_mm)
    p2 = d.path_point(d.display_height_along_slope_mm,-d.display_plate_thickness_mm)
    p3 = d.path_point(0,-d.display_plate_thickness_mm)
    ax.add_patch(Polygon([p0,p1,p2,p3],closed=True,facecolor='#38bdf8',
                         alpha=.9,edgecolor='#0369a1',lw=1.5,zorder=8))
    for station in d.mounting_stations_s_mm:
        ys,zs=d.path_point(station,d.display_standoff_height_mm)
        ax.plot(ys,zs,'o',markersize=7,color='#eab308',mec='#713f12',zorder=9)
        ax.annotate('M3 candidate\nS = '+str(station), (ys,zs),
                    xytext=(-103,6 if station==d.mounting_stations_s_mm[0] else 12),
                    textcoords='offset points',fontsize=8,color='#854d0e',
                    arrowprops=dict(arrowstyle='-',color='#a16207',lw=.7))
    ax.annotate('Structural arms / M3 integral mounts\n'+str(d.display_angle_deg)+'° to saddle bearing face',
                xy=p1,xytext=(-51,122),fontsize=10,weight='bold',color='#0369a1',
                arrowprops=dict(arrowstyle='->',lw=1.3,color='#0369a1'))
    ax.annotate('Removable M4 keeper',xy=(0,d.lower_keeper_top_z_mm-3),
                xytext=(31,-23),fontsize=9,color='#9a3412',
                arrowprops=dict(arrowstyle='->',color='#9a3412'))
    ax.annotate('Two front-open U service cutouts',xy=(35,50),xytext=(68,45),
                fontsize=9,ha='left',color='#334155',
                arrowprops=dict(arrowstyle='->',color='#334155'))
    ax.axvline(0,color='#0f766e',ls='--',lw=1,zorder=0)
    ax.text(1,133,'CENTERED / Y = 0',fontsize=8,color='#0f766e')
    ax.axhline(0,color='#94a3b8',ls='--',lw=.6,zorder=0)
    ax.set_xlabel('Y (mm)   FRONT  ←                                      →  REAR',fontsize=11)
    ax.set_ylabel('Z height (mm)',fontsize=11)
    ax.set_xlim(-58,112);ax.set_ylim(-27,140)
    ax.set_aspect('equal');ax.grid(alpha=.17)
    ax.set_title('NEPTUNE 2  |  2020 EXTRUSION DISPLAY SUPPORT  |  V013 FASTENER-DRIVEN SIDE DATUM',
                 fontsize=13,weight='bold',pad=18)
    fig.text(.12,.045,'Derived from source geometry + provisional config; not measured display hardware.',
             fontsize=9,color='#64748b')
    fig.tight_layout(rect=(.02,.06,.98,.97))
    dest=output/'engineering_side_profile.png'
    fig.savefig(dest,dpi=165,bbox_inches='tight');plt.close(fig)
    return str(dest.relative_to(output.parent))

def build(config_path=DEFAULT_CONFIG,out=ROOT,rail_path=DEFAULT_RAIL,with_previews=True):
    with open(config_path,encoding='utf-8') as f: cfg=json.load(f)
    d=Design(cfg)
    out=Path(out).resolve()
    for sub in ['step','stl','previews','docs']:(out/sub).mkdir(parents=True,exist_ok=True)
    parts={'rail':d.rail(rail_path),'upper_saddle':d.upper_clamp(),
           'keeper':d.keeper(),'left_arm':d.arm(-1),'right_arm':d.arm(1),
           'main':d.integrated_support(),
           'screen':d.screen_reference(),
           'board_screws':d.boardscrews(), 'clamp_screws':d.clampscrews()}
    report=d.validate(parts)
    for name in ['rail','upper_saddle','keeper','left_arm','right_arm','main','screen']:
        export_step(parts[name],out/'step'/f'{name}.step')
        if name not in ('rail','screen'):
            export_stl(parts[name],out/'stl'/f'{name}.stl')
    # Source-STEP-derived four-hole fixture (not a manufactured PCB).
    export_step(waveshare_mount_datum_fixture(d),
                out/'step'/'WAVESHARE_0820_DATUM_FIXTURE.step')
    # Explicit fastener reference solids (not printable).
    export_step(cq.Compound.makeCompound(parts['board_screws']),
                out/'step'/'M3_DISPLAY_SCREWS_REFERENCE.step')
    export_step(cq.Compound.makeCompound(parts['clamp_screws']),
                out/'step'/'M4_CLAMP_SCREWS_REFERENCE.step')
    # Assembly compound preserves separate rail, main, keeper, screen and hardware.
    assembly=cq.Compound.makeCompound([parts[k] for k in ['rail','main','keeper','screen']]
                                      +parts['board_screws']+parts['clamp_screws'])
    export_step(assembly,out/'step'/'COMPLETE_2020_TOUCHSCREEN_ASSEMBLY_V013.step')
    # Printable only: main and keeper should never include reference rail or screen.
    printable=cq.Compound.makeCompound([parts['main'],parts['keeper']])
    export_step(printable,out/'step'/'PRINTABLE_PARTS_V013.step')
    report['rail_reference_sha256']=hashlib.sha256(Path(rail_path).read_bytes()).hexdigest()
    report['design_config']=cfg
    (out/'docs'/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    previews=render_views(parts,out/'previews') if with_previews else []
    if with_previews:
        datum=render_engineering_side_profile(d,out/'previews')
        if datum: previews.append(datum)
        previews.append(render_waveshare_datum(d,out/'previews'))
    print('BUILD PASS',report['status'])
    print('volumes', {k:round(parts[k].Volume()) for k in ['main','keeper','rail']})
    print('previews',previews)
    return parts,report


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--config',type=Path,default=DEFAULT_CONFIG)
    p.add_argument('--rail',type=Path,default=DEFAULT_RAIL)
    p.add_argument('--out',type=Path,default=ROOT)
    p.add_argument('--no-previews',action='store_true')
    args=p.parse_args()
    build(args.config,args.out,args.rail,not args.no_previews)

if __name__=='__main__':main()
