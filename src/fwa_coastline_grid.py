"""Deterministic 100m coastal-distance layer from verified official Umhvørvisstovan Strandalinja WKB.
Requires local national terrain grid/static artifacts; does not fetch/reconstruct private files.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from rasterio.features import rasterize
from rasterio.transform import Affine
from scipy.ndimage import distance_transform_edt
from shapely import from_wkb
REQUIRED_WKB_SHA="cdc3d9645cf4844921a370924dfd28c1005e7aee7ddff0a6cfb26394331b1460"
def build(grid,static,shoreline,out):
    wkb=Path(shoreline).read_bytes()
    if hashlib.sha256(wkb).hexdigest()!=REQUIRED_WKB_SHA:raise ValueError("official coast WKB checksum mismatch")
    coast_geom=from_wkb(wkb)
    if coast_geom.is_empty or not coast_geom.is_valid:raise ValueError("invalid shoreline geometry")
    with np.load(grid) as d:
        shape=d["elevation"].shape;affine=Affine(*d["transform"])
        if abs(affine.a-100)>.01 or abs(affine.e+100)>.01:raise ValueError("not 100m EPSG5316 grid")
    with np.load(static) as d:
        row=d["row"].copy();col=d["col"].copy()
    if len(row)!=146067 or np.any(row>=shape[0]) or np.any(col>=shape[1]):raise ValueError("terrain identity mismatch")
    raster=rasterize([(coast_geom,1)],out_shape=shape,transform=affine,dtype="uint8",all_touched=True,fill=0)
    if raster.sum()<500:raise ValueError("shoreline almost empty")
    dist_full=distance_transform_edt(raster==0,sampling=(100,100)).astype("float32")
    dist=dist_full[row,col]
    if len(dist)!=146067 or not np.isfinite(dist).all():raise ValueError("coverage incomplete")
    output=Path(out);output.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(output,row=row,col=col,distance_to_official_shoreline_m=dist)
    receipt=dict(status="built",cells=len(dist),coastline_pixels=int(raster.sum()),within_500m=int((dist<=500).sum()),within_1000m=int((dist<=1000).sum()),shoreline_wkb_sha256=REQUIRED_WKB_SHA,output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),crs="EPSG:5316",resolution_m=100,source="Data from the Faroese Environment Agency, Umhvørvisstovan: Lendiskort / Strandalinja",license="https://www.foroyakort.fo/um-foeroyakort/terms-and-conditions-in-english",limitations="100m raster approximation, likely +-100m. Never substitute it for measured site exposure, roughness or terrain flow.")
    output.with_suffix(".json").write_text(json.dumps(receipt,indent=2))
    return receipt
def main():
    p=argparse.ArgumentParser()
    for x in ("grid","static","shoreline","output"):p.add_argument("--"+x,required=True)
    a=p.parse_args();print(json.dumps(build(a.grid,a.static,a.shoreline,a.output),indent=2))
if __name__=="__main__":main()
