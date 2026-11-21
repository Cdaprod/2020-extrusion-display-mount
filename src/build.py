#!/usr/bin/env python3
"""Parametric Neptune-2/2020 saddle-mounted touchscreen support V002.

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
            key = block(-length/2+15, -self.top_slot_key_width_mm/2,
                        self.bridge_bottom-self.top_slot_key_projection_mm,
                        length-30, self.top_slot_key_width_mm,
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

    def rib_outline(self):
        """Triangular right-angle support, referenced to the display and saddle.

        At 90 degrees the display is vertical above the rail centerline.  The
        rear leg slopes from the upper display support toward the long bottom
        foot, while the front rail-side leg remains tied into the carrier.
        The open triangle is internal to the rib, leaving no trapped material
        across the rear screwdriver corridors at the board mounting X stations.
        """
        y0,z0 = self.path_point(0,-2)
        y1,z1 = self.path_point(self.display_height_along_slope_mm+14,-2)
        foot_y=self.arm_rear_foot_y_mm
        foot_z=self.bridge_top-1
        top_y=self.arm_rear_top_y_mm
        # Keep the top node attached to the carrier plate's back surface.
        # The rear diagonal descends from that node to the foot endpoint.
        outer = [(self.arm_front_y_mm-13, foot_z),
                 (foot_y, foot_z),
                 (foot_y, foot_z+10),
                 (top_y+4,z1+3),
                 (y1,z1+3),
                 (y0,z0)]
        # Triangle corners are defined as relative support stations rather
        # than absolute display dimensions; the rib remains open at 90 deg.
        inner = [(self.arm_front_y_mm+15, foot_z+19),
                 (foot_y-13, foot_z+19),
                 (self.arm_front_y_mm+15, z1-18)]
        return outer,inner

    def arm(self, side):
        if side not in (-1,1):
            raise ValueError('side must be +/-1')
        outer, inner = self.rib_outline()
        # YZ sketch plane's normal is +X.
        arm = cq.Workplane('YZ').polyline(outer).close().extrude(self.arm_thickness_mm).val()
        tool = cq.Workplane('YZ').polyline(inner).close().extrude(self.arm_thickness_mm+2).val()
        arm = arm.cut(tool.translate((-1,0,0))).clean()
        if self.arm_outline_fillet_mm > 0:
            arm = cq.Workplane(obj=arm).edges('|X').fillet(self.arm_outline_fillet_mm).val().clean()
        center = side*self.arm_spacing_mm/2
        arm = arm.translate((center-self.arm_thickness_mm/2, 0, 0))
        return check_solid(('left' if side<0 else 'right')+'_arm',arm)

    def carrier(self):
        plane = self.plate_plane()
        w = self.display_width_mm
        h = self.display_height_along_slope_mm
        t = self.display_plate_thickness_mm
        # Face toward display is at plane normal zero; support projects rearward.
        plate = cq.Workplane(plane).center(0,h/2).rect(w,h).extrude(-t).val()
        # Two side access windows + central electronics service aperture.
        windows = [(0, h/2, self.display_central_window_width_mm,
                    self.display_central_window_length_mm),
                   (-62, h/2, self.display_side_window_width_mm,
                    self.display_side_window_length_mm),
                   (+62, h/2, self.display_side_window_width_mm,
                    self.display_side_window_length_mm)]
        for x,s,dx,ds in windows:
            cut = cq.Workplane(plane).center(x,s).rect(dx,ds).extrude(-t-1).val()
            plate = plate.cut(cut)
        # Stiffening strips on rear face: away from fastener stations.
        for s in (5, h-5):
            stiff = cq.Workplane(plane).center(0,s).rect(w-10, 7).extrude(-t-5).val()
            plate = plate.fuse(stiff)
        # All PCB mounting points are parametric and provisional.
        # Countersunk/counterbored from BACK: tools approach along +normal.
        for x in self.board_hole_x_mm:
            for s in self.board_hole_s_mm:
                boss = cq.Workplane(plane).center(x,s).circle(
                    self.display_standoff_diameter_mm/2).extrude(
                    self.display_standoff_height_mm).val()
                plate = plate.fuse(boss)
        plate = plate.clean()
        for x in self.board_hole_x_mm:
            for s in self.board_hole_s_mm:
                hole = (cq.Workplane(plane).center(x,s)
                        .circle(self.board_screw_clearance_d_mm/2)
                        .extrude(-t-1).val())
                # Cut through full boss toward screen too.
                forward = cq.Workplane(plane).center(x,s).circle(
                    self.board_screw_clearance_d_mm/2).extrude(
                    self.display_standoff_height_mm+1).val()
                counterbore = (cq.Workplane(plane).workplane(offset=-t-.005)
                               .center(x,s).circle(self.board_screw_head_access_d_mm/2)
                               .extrude(self.board_counterbore_depth_mm+.005).val())
                plate = plate.cut(hole).cut(forward).cut(counterbore)
        return check_solid('carrier',plate.clean())

    def integrated_support(self):
        # One rigid printable body: saddle + left/right triangular arms + carrier.
        # The display interface is integrated: service screws remain rear-accessible.
        clamp = self.upper_clamp()
        la,ra = self.arm(-1),self.arm(1)
        # Rear cross-tie at frame foot, leaving center open for PCB screwdriver access.
        tie_y=self.arm_rear_foot_y_mm-9
        cross = block(-self.arm_spacing_mm/2-self.arm_thickness_mm/2,
                      tie_y,self.bridge_top,
                      self.arm_spacing_mm+self.arm_thickness_mm,8,9)
        frame=union(clamp,la,ra,cross)
        carr=self.carrier()
        full=union(frame,carr)
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
                Y,Z=self.path_point(s,-self.display_plate_thickness_mm+0.3)
                base=(x,Y,Z)
                shaft=cyl(1.25,self.display_plate_thickness_mm+
                           self.display_standoff_height_mm+0.6,base,n)
                # Head is behind the carrier, so it's accessible from the cavity.
                Yh,Zh=self.path_point(s,-self.display_plate_thickness_mm-1.3)
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
        # Check all through-holes have a clear straight tool path to rear.
        # The first few mm of each ray are outside the carrier rear face.
        n=self.normal
        for x in self.board_hole_x_mm:
            for s in self.board_hole_s_mm:
                y,z=self.path_point(s,-self.display_plate_thickness_mm-2.5)
                rad=self.rear_access_tool_diameter_mm/2
                tool=cyl(rad,55,(x,y-55*n[0],z-55*n[1]),(0,n[0],n[1]))
                vol=tool.intersect(main).Volume()
                report[f'rear_tool_clearance_x{x:g}_s{s:g}_mm3']=round(vol,5)
                if vol>.03:
                    raise ValueError(f'Screwdriver blocked at x={x}, s={s}: {vol} mm3')
        report['status']='PASS: nominal geometry, zero body collisions, rear tools unobstructed'
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
    outer, inner = d.rib_outline()
    ax.add_patch(Polygon(outer,closed=True,facecolor='#475569',edgecolor='#1e293b',lw=1.8,zorder=3))
    ax.add_patch(Polygon(inner,closed=True,facecolor='#f8fafc',edgecolor='#1e293b',lw=1.5,zorder=3))
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
    ax.annotate('Two triangulated ribs, open inside',xy=(35,50),xytext=(68,45),
                fontsize=9,ha='left',color='#334155',
                arrowprops=dict(arrowstyle='->',color='#334155'))
    ax.axvline(0,color='#0f766e',ls='--',lw=1,zorder=0)
    ax.text(1,133,'CENTERED / Y = 0',fontsize=8,color='#0f766e')
    ax.axhline(0,color='#94a3b8',ls='--',lw=.6,zorder=0)
    ax.set_xlabel('Y (mm)   FRONT  ←                                      →  REAR',fontsize=11)
    ax.set_ylabel('Z height (mm)',fontsize=11)
    ax.set_xlim(-58,112);ax.set_ylim(-27,140)
    ax.set_aspect('equal');ax.grid(alpha=.17)
    ax.set_title('NEPTUNE 2  |  2020 EXTRUSION DISPLAY SUPPORT  |  V002 SIDE DATUM',
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
    export_step(assembly,out/'step'/'COMPLETE_2020_TOUCHSCREEN_ASSEMBLY_V002.step')
    # Printable only: main and keeper should never include reference rail or screen.
    printable=cq.Compound.makeCompound([parts['main'],parts['keeper']])
    export_step(printable,out/'step'/'PRINTABLE_PARTS_V002.step')
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
