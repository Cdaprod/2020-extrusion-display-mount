"""Independent CadQuery construction of the editable native FreeCAD mount.

Coordinates and features follow cad/freecad/display-mount-working.FCStd; the
legacy curved-profile generator remains available through build.py's default
mode. All output here is generated from these dimensions, not an imported STEP.
"""
from __future__ import annotations
import json
from pathlib import Path
import cadquery as cq
from cadquery import exporters

ROOT=Path(__file__).resolve().parent.parent

def box(x,y,z,dx,dy,dz):
    return cq.Solid.makeBox(dx,dy,dz,cq.Vector(x,y,z))

def cyl(radius,height,pos,axis=(0,0,1)):
    return cq.Solid.makeCylinder(radius,height,cq.Vector(*pos),cq.Vector(*axis))

def section(points,x0,thickness):
    return cq.Workplane('YZ').polyline(points).close().extrude(thickness).val().translate((x0,0,0))

def require_one(name,shape):
    if not shape.isValid() or len(shape.Solids())!=1 or shape.Volume()<=0:
        raise ValueError(f'{name} is not one valid connected solid')
    return shape

def geometry(cfg):
    """Build the main printable solid and the separate relieved keeper."""
    n=cfg['native_profile']; x_pitch=cfg['mount_hole_center_spacing_mm']; pitch=cfg['board_screw_vertical_pitch_mm']
    width=n['arm_width_mm']; half=cfg['board_mount_tab_height_mm']/2; z0=n['foot_base_z_mm']; eps=n['sketch_datum_rounding_mm']
    center=n['rail_center_y_mm']; channel=n['channel_width_mm']; key=n['slot_key_width_mm']; key_depth=n['slot_key_depth_mm']
    tab=n['tab_projection_mm']; access=n['tab_access_depth_mm']; upper=pitch/2
    min_web=n['minimum_web_mm']; reinforce=n['upper_root_reinforcement_mm']; inset=n['upper_taper_inset_mm']
    if x_pitch<=width or pitch<=2*half or key>=channel or min_web<=0:
        raise ValueError('Native screw pitch, tab height or channel dimensions invalid')
    if not 0<n['keeper_foot_clearance_mm']<channel/4:
        raise ValueError('Invalid keeper foot clearance')
    left=center-channel/2;right=center+channel/2;keyleft=center-key/2;keyright=center+key/2
    roof=z0+20; notch=roof-key_depth
    # Explicit sketch vertices: front tabs, outer web, 2020 channel and inner opening.
    pts=[(0,upper-half-eps),(0,upper+half-eps),
         (tab,upper+3.5+min_web+reinforce-eps),(48,upper+3.5+min_web+reinforce-eps),
         (68,28),(68,-35),(50,-76),(right,z0),(right,roof),
         (keyright,roof),(keyright,notch),(keyleft,notch),(keyleft,roof),(left,roof),(left,z0),
         (-13,z0),(-13,-68),(0,-56),(0,-upper-half-eps),(0,-upper+half-eps),
         (tab,-upper+half-eps),(tab,-upper-3.5-eps),(tab+access,-upper-3.5-eps),
         (55,-12),(55,upper-half-inset-eps),(tab+access,upper+3.5-eps),
         (tab,upper+3.5-eps),(tab,upper-half-eps)]
    arms=[]
    for side in (-1,1):
        x=side*x_pitch/2
        arm=section(pts,x-width/2,width)
        for z in (-upper,upper):
            # Native uses a 3 mm front bore and 5.5 mm rear access bore.
            drill=cyl(n['front_bore_diameter_mm']/2,n['front_bore_length_mm'],(x,0,z),(0,1,0)).fuse(cyl(n['rear_bore_diameter_mm']/2,n['rear_bore_length_mm'],(x,n['rear_bore_start_y_mm'],z),(0,1,0)))
            cone=cq.Solid.makeCone(n['front_bore_diameter_mm']/2,n['display_head_diameter_mm']/2,1,cq.Vector(x,n['display_bearing_thickness_mm'],z),cq.Vector(0,1,0))
            arm=arm.cut(drill.fuse(cone))
        arms.append(arm)
    margin=n['saddle_end_margin_mm']; span=x_pitch+width+2*margin; x0=-span/2
    sw=n['saddle_width_mm']; clearance=n['rail_side_clearance_mm']; rail_low=center-10-clearance;rail_high=center+10+clearance
    bottom=z0+1.5989;inside_roof=z0+20.2789;top=z0+20.35+n['saddle_bridge_thickness_mm']
    saddle_pts=[(center-sw/2,bottom),(rail_low,bottom),(rail_low,inside_roof),(rail_high,inside_roof),
                (rail_high,bottom),(center+sw/2,bottom),(center+sw/2,top),(center-sw/2,top)]
    saddle=section(saddle_pts,x0,span)
    hx=n['clamp_hole_x_mm'];hy=n['clamp_hole_y_offset_mm']
    for x in (-hx,hx):
        for y in (center-hy,center+hy):saddle=saddle.cut(cyl(n['insert_diameter_mm']/2,n['insert_depth_mm'],(x,y,bottom)))
    # Match the native rear cross member at the upper web.
    rear=box(-x_pitch/2-width/2,60,-5,x_pitch+width,8,10)
    main=require_one('native main',arms[0].fuse(arms[1],saddle,rear).clean())
    thick=n['keeper_thickness_mm']; top_z=z0-n['keeper_gap_mm']; keeper=box(x0,center-sw/2,top_z-thick,span,sw,thick)
    for x in (-hx,hx):
        for y in (center-hy,center+hy):
            keeper=keeper.cut(cyl(n['keeper_bolt_diameter_mm']/2,thick,(x,y,top_z-thick)))
            keeper=keeper.cut(cyl(n['keeper_head_diameter_mm']/2,n['keeper_head_depth_mm'],(x,y,top_z-thick)))
    edge=n['keeper_foot_clearance_mm'];depth=n['keeper_foot_relief_mm']
    for x in (-x_pitch/2-width/2-edge,x_pitch/2-width/2-edge):
        for y0,y1 in ((center-sw/2,left+edge),(right-edge,center+sw/2)):
            keeper=keeper.cut(box(x,y0,top_z-depth,width+2*edge,y1-y0,depth))
    keeper=require_one('native keeper',keeper.clean())
    if main.intersect(keeper).Volume()>1e-5:raise ValueError('Keeper intersects native mount')
    return main,keeper

def render(main,keeper,path,side=False):
    import vtk
    renderer=vtk.vtkRenderer();renderer.SetBackground(1,1,1)
    for shape,color in [(main,(.37,.42,.48)),(keeper,(.80,.44,.20))]:
        vertices,faces=shape.tessellate(.18,.25);points=vtk.vtkPoints();cells=vtk.vtkCellArray()
        for v in vertices:points.InsertNextPoint(v.x,v.y,v.z)
        for face in faces:
            tri=vtk.vtkTriangle()
            for i,idx in enumerate(face):tri.GetPointIds().SetId(i,idx)
            cells.InsertNextCell(tri)
        data=vtk.vtkPolyData();data.SetPoints(points);data.SetPolys(cells)
        normal=vtk.vtkPolyDataNormals();normal.SetInputData(data);normal.ConsistencyOn();normal.AutoOrientNormalsOn();normal.Update()
        mapper=vtk.vtkPolyDataMapper();mapper.SetInputConnection(normal.GetOutputPort());actor=vtk.vtkActor();actor.SetMapper(mapper);actor.GetProperty().SetColor(*color);renderer.AddActor(actor)
    window=vtk.vtkRenderWindow();window.SetOffScreenRendering(1);window.AddRenderer(renderer);window.SetSize(1500,1100)
    camera=renderer.GetActiveCamera();camera.ParallelProjectionOn();camera.SetViewUp(0,0,1);camera.SetFocalPoint(0,20,-25)
    camera.SetPosition((400,20,-25) if side else (210,-245,180));renderer.ResetCamera();window.Render()
    image=vtk.vtkWindowToImageFilter();image.SetInput(window);image.SetInputBufferTypeToRGB();image.ReadFrontBufferOff();image.Update()
    writer=vtk.vtkPNGWriter();writer.SetFileName(str(path));writer.SetInputConnection(image.GetOutputPort());writer.Write();window.Finalize()

def build_native(config_path,out,with_previews=True):
    cfg=json.loads(Path(config_path).read_text());out=Path(out).resolve()
    for name in ('step','stl','previews','docs'):(out/name).mkdir(parents=True,exist_ok=True)
    main,keeper=geometry(cfg)
    for name,shape in [('mount',main),('keeper',keeper)]:
        exporters.export(shape,str(out/'step'/f'NATIVE_EQUIVALENT_{name.upper()}.step'))
        exporters.export(shape,str(out/'stl'/f'native_equivalent_{name}.stl'),tolerance=.1,angularTolerance=.3)
    if with_previews:
        render(main,keeper,out/'previews'/'native_equivalent_isometric.png')
        render(main,keeper,out/'previews'/'native_equivalent_side.png',side=True)
    report={'status':'PASS: native-equivalent CadQuery solids','main_volume_mm3':main.Volume(),'keeper_volume_mm3':keeper.Volume(),
            'main_solids':len(main.Solids()),'keeper_solids':len(keeper.Solids()),'keeper_overlap_mm3':main.intersect(keeper).Volume(),
            'screw_pitch_x_mm':cfg['mount_hole_center_spacing_mm'],'screw_pitch_z_mm':cfg['board_screw_vertical_pitch_mm'],
            'channel_width_mm':cfg['native_profile']['channel_width_mm'],'key_width_mm':cfg['native_profile']['slot_key_width_mm']}
    (out/'docs'/'native_equivalent_validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('NATIVE EQUIVALENT BUILD PASS',report)
    return main,keeper
