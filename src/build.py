#!/usr/bin/env python3
"""Parametric Neptune-2/2020 saddle-mounted touchscreen support V007.

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
        return check_solid('keeper', solid.clean())

    def rib_profile_stations(self):
        """V006: exterior YZ wire includes rear diagonal saddle-to-arm gusset."""
        z_foot=self.bridge_top-self.arm_saddle_intersection_mm
        z_top=self.arm_front_z_mm+self.display_height_along_slope_mm+self.arm_outer_rear_shoulder_z_above_carrier_mm
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
            (self.arm_outer_rear_bulge_y_mm,self.arm_outer_rear_bulge_z_mm),
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
        radii = [0, 0, 0, self.arm_lower_rear_fillet_mm,
                 self.arm_rear_transition_fillet_mm,
                 self.arm_upper_shoulder_fillet_mm, 0, 0]
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
        """Real rear-open U/Y branch in each arm, using side-specific parameters.

        Keep the tapered front service cavity but extend a rounded horizontal
        throat through the rear exterior. The surviving front ligament remains
        attached to the upright mounting rail; two branches meet at that root.
        """
        if side not in (-1,1):
            raise ValueError("Arm side must be -1 or +1")
        zlo=self.arm_opening_bottom_z_mm
        zhi=self.arm_opening_top_z_mm
        front=self.arm_front_y_mm+self.arm_opening_front_wall_mm
        rearlo=self.arm_opening_rear_bottom_y_mm
        rearhi=self.arm_opening_rear_top_y_mm
        cavity=(cq.Workplane('YZ')
                .polyline([(front,zlo),(rearlo,zlo),(rearhi,zhi),(front,zhi)])
                .close().extrude(self.arm_thickness_mm+2)
                .edges('|X').fillet(self.arm_opening_corner_radius_mm)
                .val().translate((-1,0,0)))
        branch=self.cfg['service_left' if side<0 else 'service_right']
        center=branch['throat_center_z_mm']
        width=branch['throat_width_mm']
        end=branch['throat_end_y_mm']
        if width<=0 or width>zhi-zlo-2*self.arm_opening_corner_radius_mm:
            raise ValueError('Invalid service branch throat width')
        if front-self.arm_front_y_mm<self.min_arm_front_ligament_mm:
            raise ValueError('Arm service aperture leaves insufficient front ligament')
        if end<=self.arm_outer_rear_bulge_y_mm+width:
            raise ValueError('Service entry does not clear rear arm exterior')
        # A horizontal rounded cutter runs from INSIDE cavity to far beyond
        # rear perimeter; it is deliberately open to the actual arm exterior.
        throat=(cq.Workplane('YZ').center((25+end)/2,center)
                .slot2D(end-25+width,width,angle=0)
                .extrude(self.arm_thickness_mm+2).val().translate((-1,0,0)))
        return cavity.fuse(throat).clean()

    def arm(self,side):
        if side not in (-1,1):
            raise ValueError('side must be +/-1')
        arm=self.rib_workplane().extrude(self.arm_thickness_mm).val()
        arm=arm.cut(self.arm_service_opening(side)).clean()
        center=side*self.arm_spacing_mm/2
        arm=arm.translate((center-self.arm_thickness_mm/2,0,0))
        return check_solid(('left' if side<0 else 'right')+'_arm',arm)

    def port_service_envelope(self,side):
        """Nominal SD/USB insertion corridor. Real hardware is not measured."""
        width=self.mount_rail_width_mm
        center=self.board_hole_x_mm[0 if side<0 else -1]
        relief=self.cfg['sd_relief' if side<0 else 'usb_relief']
        inner=center-side*width/2
        # 0.5 mm margin inside the actual rail cut, including x tolerance.
        x0=min(inner,inner+side*relief['inner_cut_width_mm'])+.5
        x1=max(inner,inner+side*relief['inner_cut_width_mm'])-.5
        z0=self.arm_front_z_mm+relief['station_mm']-relief['length_mm']/2+.5
        return block(x0,-3,z0,x1-x0,16,relief['length_mm']-1)

    def carrier_rails(self):
        """Two independent integral mounting rails, no rear sheet.

        Each rail carries a vertical PCB-hole pair and its OWN counterbores.
        The standoffs are attached to that same rail. Each side has a separate
        replaceable relief parameter set for SD/USB service.
        """
        plane=self.plate_plane()
        width=self.mount_rail_width_mm
        h=self.display_height_along_slope_mm
        t=self.mount_rail_thickness_mm
        rails=[]
        for x in self.board_hole_x_mm:
            side=-1 if x<0 else 1
            rail=cq.Workplane(plane).center(x,h/2).rect(width,h).extrude(-t).val()
            relief=self.cfg['sd_relief' if side<0 else 'usb_relief']
            if relief['enabled']:
                ligament=width-relief['inner_cut_width_mm']-relief['overhang_mm']/2
                if ligament<self.min_mount_rail_ligament_mm:
                    raise ValueError('Port relief removes too much load-bearing rail width')
                inner=x-side*width/2
                cut_center=inner+side*relief['inner_cut_width_mm']/2
                service=(cq.Workplane(plane)
                         .center(cut_center,relief['station_mm'])
                         .rect(relief['inner_cut_width_mm']+relief['overhang_mm'],
                               relief['length_mm'])
                         .extrude(-t-1).val())
                rail=rail.cut(service)
            for station in self.board_hole_s_mm:
                boss=(cq.Workplane(plane).center(x,station)
                      .circle(self.display_standoff_diameter_mm/2)
                      .extrude(self.display_standoff_height_mm).val())
                rail=rail.fuse(boss)
            rail=rail.clean()
            for station in self.board_hole_s_mm:
                bore=(cq.Workplane(plane).center(x,station)
                      .circle(self.board_screw_clearance_d_mm/2)
                      .extrude(-t-1).val())
                forward=(cq.Workplane(plane).center(x,station)
                         .circle(self.board_screw_clearance_d_mm/2)
                         .extrude(self.display_standoff_height_mm+1).val())
                cb=(cq.Workplane(plane).workplane(offset=-t-.005)
                    .center(x,station)
                    .circle(self.board_screw_head_access_d_mm/2)
                    .extrude(self.board_counterbore_depth_mm+.005).val())
                rail=rail.cut(bore).cut(forward).cut(cb)
            rails.append(check_solid(
                ('left' if side<0 else 'right')+'_mount_rail',rail.clean()))
        return rails

    def carrier(self):
        """Reference compound: exactly two rails, physically fused into main."""
        return cq.Compound.makeCompound(self.carrier_rails())

    def integrated_support(self):
        # One rigid printable body: saddle + left/right triangular arms + carrier.
        # The display interface is integrated: service screws remain rear-accessible.
        clamp = self.upper_clamp()
        la,ra = self.arm(-1),self.arm(1)
        # Rear cross-tie at frame foot, leaving center open for PCB screwdriver access.
        tie_y=self.arm_outer_lower_rear_y_mm-9
        cross = block(-self.arm_spacing_mm/2-self.arm_thickness_mm/2,
                      tie_y,self.bridge_top,
                      self.arm_spacing_mm+self.arm_thickness_mm,8,9)
        frame=union(clamp,la,ra,cross)
        carr=self.carrier()
        full=union(frame,*self.carrier_rails())
        return check_solid('integrated_main_frame',full)

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
        plane = self.plate_plane()
        n=(0,self.normal[0],self.normal[1])
        result=[]
        for x in self.board_hole_x_mm:
            for s in self.board_hole_s_mm:
                Y,Z=self.path_point(s,-self.mount_rail_thickness_mm+0.3)
                base=(x,Y,Z)
                shaft=cyl(1.25,self.mount_rail_thickness_mm+
                           self.display_standoff_height_mm+0.6,base,n)
                # Head is behind the carrier, so it's accessible from the cavity.
                Yh,Zh=self.path_point(s,-self.mount_rail_thickness_mm-1.3)
                head=cyl(2.5,1.6,(x,Yh,Zh),n)
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
        report={
            'rail_bbox_mm': [rail.BoundingBox().xlen,rail.BoundingBox().ylen,rail.BoundingBox().zlen],
            'nominal_display_hole_centers_x_s_mm': [[x,s] for x in self.board_hole_x_mm for s in self.board_hole_s_mm],
            'clamp_fastener_centers_xy_mm': [[x,y] for x in self.clamp_screw_x_mm for y in (-self.clamp_screw_y_abs_mm,self.clamp_screw_y_abs_mm)],
            'parameters_provisional': True,
            'verification_scope': 'nominal CAD solids and reference clearances only; not physically fitted'
        }
        for key in ['rail','upper_saddle','keeper','left_arm','right_arm','carrier','main']:
            s=parts[key]
            if key=='carrier':
                if len(s.Solids())!=2 or any(not body.isValid() for body in s.Solids()):
                    raise ValueError('Carrier must be two separate valid mounting rails')
            else:
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
        sample=block(-self.arm_spacing_mm/2-self.arm_thickness_mm/2+1,
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
        # Check all through-holes have a clear straight tool path to rear.
        # The first few mm of each ray are outside the carrier rear face.
        n=self.normal
        for x in self.board_hole_x_mm:
            for s in self.board_hole_s_mm:
                y,z=self.path_point(s,-self.mount_rail_thickness_mm-2.5)
                rad=self.rear_access_tool_diameter_mm/2
                tool=cyl(rad,55,(x,y-55*n[0],z-55*n[1]),(0,n[0],n[1]))
                vol=tool.intersect(main).Volume()
                report[f'rear_tool_clearance_x{x:g}_s{s:g}_mm3']=round(vol,5)
                if vol>.03:
                    raise ValueError(f'Screwdriver blocked at x={x}, s={s}: {vol} mm3')
        # Verify actual 3D service corridors remain free of bracket solids.
        for side,label in [(-1,'sd'),(1,'usb')]:
            branch=self.cfg['service_left' if side<0 else 'service_right']
            center=side*self.arm_spacing_mm/2
            probe=block(center-1, self.arm_opening_front_wall_mm+4,
                        branch['throat_center_z_mm']-1,2,65,2)
            if parts['left_arm' if side<0 else 'right_arm'].intersect(probe).Volume()>.01:
                raise ValueError(f'{label}: side-entry throat is blocked')
            corridor=self.port_service_envelope(side)
            overlap=main.intersect(corridor).Volume()
            report[f'{label}_service_envelope_overlap_mm3']=round(overlap,5)
            report[f'{label}_throat_width_mm']=branch['throat_width_mm']
            if overlap>.01:
                raise ValueError(f'{label} port/cable provisional service volume obstructed: {overlap}')
        report['carrier_rail_count']=len(parts['carrier'].Solids())
        report['rear_sheet_removed']=True
        report['status']='PASS: two open mounting rails, rear service branches, zero solid overlaps'
        return report


def export_step(shape,path):
    exporters.export(shape,str(path),exportType='STEP')


def export_stl(shape,path):
    exporters.export(shape,str(path),exportType='STL',tolerance=0.08,angularTolerance=0.15)


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
             'carrier':(.18,.45,.67),'upper_saddle':(.35,.38,.43),
             'left_arm':(.90,.44,.14),'right_arm':(.90,.44,.14)}
    scenes={
      'assembly_isometric': [('rail',1.0),('main',1.0),('keeper',1.0),('screen',0.42),('m4',1.0),('m25',1.0)],
      'main_frame_only': [('main',1.0)],
      'side_section': [('rail',.3),('main',1.0),('keeper',1.0),('screen',0.4)],
      'saddle_clamp': [('rail',.35),('upper_saddle',1.0),('keeper',1.0)],
      'display_carrier': [('carrier',1.0),('m25',1.0)],
      'rear_screw_access': [('rail',.35),('main',1.0),('keeper',1.0),('m4',1.0),('m25',1.0)],
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
        elif name=='side_section':
            camera.SetPosition(450,-260,160);camera.SetFocalPoint(0,9,48)
            # view mostly along +X side, slightly perspective for paired arms
        elif name=='display_carrier':
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
    for station in d.board_hole_s_mm:
        ys,zs=d.path_point(station,d.display_standoff_height_mm)
        ax.plot(ys,zs,'o',markersize=7,color='#eab308',mec='#713f12',zorder=9)
        ax.annotate('M2.5 candidate\nS = '+str(station), (ys,zs),
                    xytext=(-103,6 if station==d.board_hole_s_mm[0] else 12),
                    textcoords='offset points',fontsize=8,color='#854d0e',
                    arrowprops=dict(arrowstyle='-',color='#a16207',lw=.7))
    ax.annotate('Display carrier + 2 arms\n'+str(d.display_angle_deg)+'° to saddle bearing face',
                xy=p1,xytext=(-51,122),fontsize=10,weight='bold',color='#0369a1',
                arrowprops=dict(arrowstyle='->',lw=1.3,color='#0369a1'))
    ax.annotate('Removable M4 keeper',xy=(0,d.lower_keeper_top_z_mm-3),
                xytext=(31,-23),fontsize=9,color='#9a3412',
                arrowprops=dict(arrowstyle='->',color='#9a3412'))
    ax.annotate('Two rear-open U/Y service branches',xy=(35,50),xytext=(68,45),
                fontsize=9,ha='left',color='#334155',
                arrowprops=dict(arrowstyle='->',color='#334155'))
    ax.axvline(0,color='#0f766e',ls='--',lw=1,zorder=0)
    ax.text(1,133,'CENTERED / Y = 0',fontsize=8,color='#0f766e')
    ax.axhline(0,color='#94a3b8',ls='--',lw=.6,zorder=0)
    ax.set_xlabel('Y (mm)   FRONT  ←                                      →  REAR',fontsize=11)
    ax.set_ylabel('Z height (mm)',fontsize=11)
    ax.set_xlim(-58,112);ax.set_ylim(-27,140)
    ax.set_aspect('equal');ax.grid(alpha=.17)
    ax.set_title('NEPTUNE 2  |  2020 EXTRUSION DISPLAY SUPPORT  |  V007 SIDE DATUM',
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
           'carrier':d.carrier(),'main':d.integrated_support(),
           'screen':d.screen_reference(),
           'board_screws':d.boardscrews(), 'clamp_screws':d.clampscrews()}
    report=d.validate(parts)
    for name in ['rail','upper_saddle','keeper','left_arm','right_arm','carrier','main','screen']:
        export_step(parts[name],out/'step'/f'{name}.step')
        if name not in ('rail','screen'):
            export_stl(parts[name],out/'stl'/f'{name}.stl')
    # Explicit fastener reference solids (not printable).
    export_step(cq.Compound.makeCompound(parts['board_screws']),
                out/'step'/'M2_5_DISPLAY_SCREWS_REFERENCE.step')
    export_step(cq.Compound.makeCompound(parts['clamp_screws']),
                out/'step'/'M4_CLAMP_SCREWS_REFERENCE.step')
    # Assembly compound preserves separate rail, main, keeper, screen and hardware.
    assembly=cq.Compound.makeCompound([parts[k] for k in ['rail','main','keeper','screen']]
                                      +parts['board_screws']+parts['clamp_screws'])
    export_step(assembly,out/'step'/'COMPLETE_2020_TOUCHSCREEN_ASSEMBLY_V007.step')
    # Printable only: main and keeper should never include reference rail or screen.
    printable=cq.Compound.makeCompound([parts['main'],parts['keeper']])
    export_step(printable,out/'step'/'PRINTABLE_PARTS_V007.step')
    report['rail_reference_sha256']=hashlib.sha256(Path(rail_path).read_bytes()).hexdigest()
    report['design_config']=cfg
    (out/'docs'/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    previews=render_views(parts,out/'previews') if with_previews else []
    if with_previews:
        datum=render_engineering_side_profile(d,out/'previews')
        if datum: previews.append(datum)
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
