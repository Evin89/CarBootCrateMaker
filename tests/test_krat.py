# Geometrietest voor Kofferbakkrat.FCMacro. Draaien met:
#   "C:Program FilesFreeCAD 1.1binreecadcmd.exe" tests	est_krat.py
import json, os, sys, itertools
import xml.dom.minidom
import FreeCAD as App
HERE = os.path.dirname(os.path.abspath(sys.argv[-1] if sys.argv[-1].endswith(".py") else __file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "uitvoer")
MAC = os.path.join(ROOT, "Kofferbakkrat.FCMacro")
ns = {"KRAT_TEST": True, "__name__": "krattest"}
exec(compile(open(MAC, encoding="utf-8").read(), MAC, "exec"), ns)
fails = []
def check(cond, msg):
    print(("OK   " if cond else "FAIL ") + msg)
    if not cond: fails.append(msg)

for (L, W, H, t, fw, hd) in [(600,400,300,9,30,False),(437,283,211,8.8,27,False),(320,400,250,9,30,True),(1000,150,120,12,40,True)]:
    s = json.loads(json.dumps(ns["DEFAULTS"])); s["t"]=t; s["finger"]=fw
    doc = App.newDocument("T")
    part, panels, rep = ns["build_crate"](doc, {"name":"K","L":L,"W":W,"H":H,"handles":hd}, s)
    doc.recompute()
    objs = [o for o in part.Group]
    shapes = [o.Shape.transformGeometry(o.Placement.toMatrix()) if False else o.Shape.copy() for o in objs]
    for o, sh in zip(objs, shapes):
        sh.Placement = o.getGlobalPlacement()
    check(all(sh.isValid() and len(sh.Solids)==1 for sh in shapes), f"{L}x{W}x{H} t={t}: 5 geldige massieve panelen")
    ov = 0.0
    for a, b in itertools.combinations(shapes, 2):
        ov = max(ov, a.common(b).Volume)
    check(ov < 1e-3, f"{L}x{W}x{H}: geen overlap tussen panelen (max {ov:.4f} mm3)")
    tot = sum(sh.Volume for sh in shapes)
    shell = L*W*H - (L-2*t)*(W-2*t)*(H-t)
    if not hd:
        check(abs(tot-shell) < 1e-2, f"{L}x{W}x{H}: panelen vullen de wand exact ({tot:.1f} vs {shell:.1f} mm3)")
    else:
        check(tot < shell and shell - tot < 2*110*32*t+1, f"{L}x{W}x{H}: met handgrepen alleen het greepgat minder")
    fused = shapes[0].fuse(shapes[1:])
    bb = fused.BoundBox
    check(abs(bb.XMin)<1e-6 and abs(bb.YMin)<1e-6 and abs(bb.ZMin)<1e-6 and abs(bb.XMax-L)<1e-6 and abs(bb.YMax-W)<1e-6 and abs(bb.ZMax-H)<1e-6,
          f"{L}x{W}x{H}: buitenmaat klopt ({bb.XLength:.2f} x {bb.YLength:.2f} x {bb.ZLength:.2f})")
    App.closeDocument(doc.Name)

# SVG laser en CNC
data = json.load(open(os.path.join(ROOT, "kofferbakkratten-gegevens.json"), encoding="utf-8"))
for machine in ("laser","cnc"):
    s = ns["merge_settings"](ns["DEFAULTS"], data["settings"]); s["machine"]=machine
    doc = App.newDocument("B")
    built, notes = ns["build_from_backup"](doc, data, s, flat=False)
    doc.recompute()
    check(len(built)==1 and any(o.Label=="Decoupeerzaag" for o in doc.Objects), f"{machine}: back-up opgebouwd met gereedschap; meldingen: {notes}")
    files, over = ns["write_svgs"](built, s, os.path.join(OUT, "svg-"+machine))
    for f in files: xml.dom.minidom.parse(f)
    check(len(files)>=1 and not over, f"{machine}: {len(files)} SVG-plaat(en) geldig XML")
    App.closeDocument(doc.Name)
    doc = App.newDocument("F")
    built, notes = ns["build_from_backup"](doc, data, s, flat=True)
    doc.recompute()
    check(sum(1 for o in doc.Objects if o.Name.startswith("Paneel")) == 5, f"{machine}: platte weergave heeft 5 panelen")
    App.closeDocument(doc.Name)

# kerf: laser-contour is 0.1 mm groter rondom
s = json.loads(json.dumps(ns["DEFAULTS"]))
p = ns["crate_panels"](600,400,300,9,30,False)[4]
g = ns["panel_cut_geom"](p, s)
check(abs(g["w"]-600.2)<1e-9 and abs(g["h"]-400.2)<1e-9, "kerfcompensatie 0,2 mm geeft bodem 600,2 x 400,2")
s["machine"]="cnc"; g = ns["panel_cut_geom"](p, s)
check(g["d"].count("A") > 0, f"CNC: {g['d'].count('A')} dogbones in de bodem")
print("KLAAR", "fouten:", len(fails))
