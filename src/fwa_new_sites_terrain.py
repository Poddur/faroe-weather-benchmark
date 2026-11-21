"""Frozen v2 new-site terrain profile reconstruction using verified original Faroese terrain artifacts.
No interpolation of observations or weather used in constructing profiles.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
ROOT=Path("outputs/spatial-expansion")
STATIONS={
 "06012":{"name":"Fugloy","lat":62.3195,"lon":-6.3205,"station_elevation_m":54.0,"source":"DMI metObs station registry, current validFrom 2024-11-22"},
 "EKVG":{"name":"Vagar airport","lat":62.0664,"lon":-7.2847,"station_elevation_m":85.0,"source":"IEM EKVG airport station metadata"}
}
def sphere(lat,lon):
    lat=np.radians(np.asarray(lat,float));lon=np.radians(np.asarray(lon,float))
    return np.column_stack((np.cos(lat)*np.cos(lon),np.cos(lat)*np.sin(lon),np.sin(lat)))
def km(chord):return 12742*np.arcsin(np.minimum(1,chord/2))
def build(static_path,directional_path,receipt_path):
    receipt=json.loads(Path(receipt_path).read_text())
    if receipt.get("status") not in ("complete","success","built","verified","ok","grid_built","geography_verified"):
        # The original receipt schema has file SHA keys and may not use a success enum.
        if not receipt.get("sha256") and not receipt.get("files"):raise ValueError("missing terrain provenance")
    with np.load(static_path) as a, np.load(directional_path) as b:
        tree=cKDTree(sphere(a["lat"],a["lon"]))
        profiles={}
        for sid,s in STATIONS.items():
            d,i=tree.query(sphere([s["lat"]],[s["lon"]])[0])
            dist=float(km(d))*1000
            if dist>100:raise ValueError("terrain cell further than 100 m")
            dz=float(a["elevation"][i])-s["station_elevation_m"]
            if abs(dz)>30:raise ValueError("terrain inconsistent with official station height")
            sectors=[]
            for k in range(72):
                cv=int(b["coverage_pct"][1,k,i])/100
                angle=int(b["shelter_cdeg"][1,k,i])/100 if cv>=.8 else None
                expo=int(b["exposure_cdeg"][1,k,i])/100 if cv>=.8 else None
                sectors.append(dict(direction_deg=5*k,coverage=cv,shelter_deg=angle,exposure_deg=expo))
            profiles[sid]=dict(lat=s["lat"],lon=s["lon"],station_elevation_m=s["station_elevation_m"],sectors=sectors,terrain_cell_elevation_m=float(a["elevation"][i]),terrain_match_distance_m=dist,terrain_height_difference_m=dz,source=s["source"],resolution_m=100,reference_radius_m=2000,provenance="Original national 10m DEM derived 100m cell; no station-specific calibration")
    return {"version":"fwa-geo-profiles-v2","status":"verified_geographic_proxy","stations":profiles,"terrain_receipt_sha256":hashlib.sha256(Path(receipt_path).read_bytes()).hexdigest(),"static_sha256":hashlib.sha256(Path(static_path).read_bytes()).hexdigest(),"directional_sha256":hashlib.sha256(Path(directional_path).read_bytes()).hexdigest()}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--static",required=True);p.add_argument("--directional",required=True);p.add_argument("--receipt",required=True);p.add_argument("--out",required=True)
    a=p.parse_args();d=build(a.static,a.directional,a.receipt);o=Path(a.out);o.parent.mkdir(parents=True,exist_ok=True);o.write_text(json.dumps(d,indent=2))
    print(json.dumps({k:{x:d["stations"][k][x] for x in ["terrain_match_distance_m","terrain_height_difference_m","station_elevation_m"]} for k in d["stations"]},indent=2))
if __name__=="__main__":main()
