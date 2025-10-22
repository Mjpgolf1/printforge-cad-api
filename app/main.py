from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
# NEW: Import CORS middleware
from fastapi.middleware.cors import CORSMiddleware
import cadquery as cq
from cadquery import exporters
import io, math
from typing import List, Dict

app = FastAPI(title="CAD Microservice", version="0.1")

# NEW: Add CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

def _export_stl(shape) -> bytes:
    buf = io.BytesIO()
    exporters.export(shape, buf, exporters.ExportTypes.STL)
    return buf.getvalue()

def _block(L, W, H, centered=True):
    return cq.Workplane("XY").box(L, W, H, centered=centered)

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/v1/basic-tray")
def basic_tray(payload: Dict):
    try:
        inner = payload["inner"]
        wall = float(payload.get("wall_mm", 2))
        floor = float(payload.get("floor_mm", 2))
        L = float(inner["length_mm"])
        W = float(inner["width_mm"])
        H = float(inner["height_mm"])
        outer_box = _block(L + 2*wall, W + 2*wall, H + floor)
        inner_cut = _block(L, W, H).translate((0, 0, floor / 2.0))
        shape = outer_box.cut(inner_cut)
        return Response(_export_stl(shape), media_type="model/stl")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/v1/inset-box")
def inset_box(payload: Dict):
    try:
        outer = payload["outer"]; inner = payload["inner"]
        tol = float(payload.get("tolerance_mm", 1.5))
        oL,oW,oH = float(outer["length_mm"]), float(outer["width_mm"]), float(outer["height_mm"])
        iL,iW,iH = float(inner["length_mm"])+tol, float(inner["width_mm"])+tol, float(inner["height_mm"])
        shell = _block(oL, oW, oH)
        cut = _block(iL, iW, iH)
        shape = shell.cut(cut)
        return Response(_export_stl(shape), media_type="model/stl")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/v1/gridfinity-bin")
def gridfinity_bin(payload: Dict):
    try:
        U, D, H = int(payload["width_u"]), int(payload["depth_u"]), float(payload["height_mm"])
        wall = float(payload.get("wall_mm", 2)); floor = float(payload.get("floor_mm", 2))
        GRID = 42.0
        L = U * GRID; W = D * GRID;
        outer = _block(L, W, H)
        inner = _block(L - 2*wall, W - 2*wall, H - floor).translate((0,0, floor/2))
        shape = outer.cut(inner)
        return Response(_export_stl(shape), media_type="model/stl")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

def _area_ccw(pts):
    area = 0.0
    for i,(x1,y1) in enumerate(pts):
        x2,y2 = pts[(i+1)%len(pts)]
        area += x1*y2 - x2*y1
    return area/2.0

@app.post("/v1/contour-inset")
def contour_inset(payload: Dict):
    try:
        outer = payload["outer"]
        pts = payload["points"]
        tol = float(payload.get("tolerance_mm", 1.5))
        floor = float(payload.get("floor_mm", 2))
        oL,oW,oH = float(outer["length_mm"]), float(outer["width_mm"]), float(outer["height_mm"])
        tool_h = float(payload.get("tool_h_mm", oH))

        if _area_ccw(pts) < 0: pts.reverse()
        
        # Add tolerance by scaling around centroid (approximate offset)
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        
        scaled_pts = []
        max_r = 0
        for x,y in pts:
            max_r = max(max_r, math.hypot(x-cx, y-cy))
        
        scale_factor = (max_r + tol) / max_r if max_r > 0 else 1.0

        for x,y in pts:
            scaled_pts.append(((x-cx)*scale_factor + cx, (y-cy)*scale_factor + cy))
        
        polygon = cq.Workplane("XY").polyline(scaled_pts).close()
        cutout = polygon.extrude(tool_h)
        base = _block(oL, oW, oH)
        shape = base.cut(cutout.translate((0,0,-oH/2 + tool_h/2 + floor)))
        
        return Response(_export_stl(shape), media_type="model/stl")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
