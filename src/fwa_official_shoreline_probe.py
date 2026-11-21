"""Probe authoritative Faroese shoreline geometry and project five site distances.
No forecast predictions, calibration or station outcomes used.
"""
import json,hashlib,zipfile,io,datetime
from pathlib import Path
import requests
OUT=Path("outputs/shoreline")
URL="https://cdn.foroyakort.fo/geodata/vector/lendiskort/FGDB/lendiskort_fgdb.zip"
STATIONS={"06009":(61.3957,-6.6818),"06011":(62.0231,-6.7647),"06012":(62.3195,-6.3205),"06014":(62.2995,-7.074),"EKVG":(62.0664,-7.2847)}
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    rec={"status":"started","source_url":URL,"attribution":"Data from the Faroese Environment Agency, Umhvørvisstovan: Lendiskort / Strandalinja","access":"https://www.foroyakort.fo/um-foeroyakort/terms-and-conditions-in-english"}
    try:
        resp=requests.get(URL,timeout=120)
        rec.update(http=resp.status_code)
        resp.raise_for_status()
        if len(resp.content)>75_000_000:raise ValueError("unexpected large map download")
        rec["source_sha256"]=hashlib.sha256(resp.content).hexdigest()
        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            entries=z.infolist()
            if len(entries)>10000 or sum(i.file_size for i in entries)>450_000_000:raise ValueError("unreasonable map contents")
            base=(OUT/"data").resolve();base.mkdir(exist_ok=True)
            for i in entries:
                target=(base/i.filename).resolve()
                if not str(target).startswith(str(base)+"/"):raise ValueError("unsafe archive path")
                z.extract(i,base)
        import pyogrio
        gdbs=list((OUT/"data").rglob("*.gdb"))
        if len(gdbs)!=1:raise ValueError("Expected exactly one FGDB directory: "+str(gdbs[:6]))
        layers=pyogrio.list_layers(str(gdbs[0]))
        rec["layers"]=[{"name":x[0],"geometry":str(x[1])} for x in layers]
        names=[str(x[0]) for x in layers if "strand" in str(x[0]).lower()]
        if len(names)!=1:raise ValueError("No unique Strandalinja in official map; do not infer shoreline from other layers")
        from shapely.geometry import Point
        from shapely.ops import transform,unary_union
        from pyproj import Transformer
        frame=pyogrio.read_dataframe(str(gdbs[0]),layer=names[0])
        if frame.crs is None or frame.empty:raise ValueError("No shoreline CRS/geometries")
        meter="EPSG:5316"
        coast=frame.to_crs(meter)
        if coast.geom_type.isin(["LineString","MultiLineString"]).mean()<.9:raise ValueError("Not a shoreline line dataset")
        union=unary_union(coast.geometry.values)
        # Preserve the exact projected shoreline geometry as a reusable national asset.
        # WKB retains the original Umhvørvisstovan geometry; record EPSG separately.
        geo_path=OUT/"shoreline_epsg5316.wkb"
        geo_path.write_bytes(union.wkb)
        rec["shoreline_wkb_sha256"]=hashlib.sha256(geo_path.read_bytes()).hexdigest()
        rec["shoreline_wkb_bytes"]=geo_path.stat().st_size
        rec["shoreline_wkb_crs"]=meter
        project=Transformer.from_crs("EPSG:4326",meter,always_xy=True)
        rec["site_distances_m"]={}
        for station,(lat,lon) in STATIONS.items():
            x,y=project.transform(lon,lat)
            dist=float(Point(x,y).distance(union))
            if not 0<=dist<=15000:raise ValueError("implausible shore distance "+station+":"+str(dist))
            rec["site_distances_m"][station]=dist
        rec.update(status="verified_shoreline",feature_count=len(frame),crs=str(frame.crs))
    except Exception as e:
        rec.update(status="unavailable",error=str(e)[:600])
    finally:(OUT/"status.json").write_text(json.dumps(rec,indent=2))
    print(json.dumps({k:v for k,v in rec.items() if k!="layers"},indent=2))
if __name__=="__main__":main()
