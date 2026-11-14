"""Cloud Run entrypoint; preserves raw collector files, including failed cycles."""
import json, os, subprocess, sys, tempfile, hashlib
from datetime import datetime, timezone
from pathlib import Path

def upload_tree(root: Path, bucket_name: str, prefix: str, client=None):
    if client is None:
        from google.cloud import storage
        client = storage.Client()
    bucket = client.bucket(bucket_name)
    outcomes = []
    for path in sorted(root.rglob("*")):
        if not path.is_file(): continue
        relative = path.relative_to(root).as_posix()
        key = prefix.strip("/") + "/" + relative
        blob = bucket.blob(key)
        blob.metadata = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        blob.upload_from_filename(str(path), if_generation_match=0)
        outcomes.append(key)
    return outcomes

def main():
    bucket = os.getenv("WEATHER_ARCHIVE_BUCKET", "").strip()
    if not bucket: sys.exit("WEATHER_ARCHIVE_BUCKET is required")
    stations = Path(os.getenv("WEATHER_STATIONS", "data/stations_verified.csv"))
    if not stations.is_file(): sys.exit("Verified stations CSV missing: " + str(stations))
    cycle = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    prefix = "cycles/" + cycle
    selected = os.getenv("WEATHER_SOURCES", "observations").split(",")
    allow = {"observations":"--include-observations","harmonie":"--include-harmonie","ecmwf":"--include-ecmwf"}
    if not selected or any(x not in allow for x in selected) or len(selected)!=len(set(selected)):
        sys.exit("WEATHER_SOURCES must be comma-separated subset of observations,harmonie,ecmwf")
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp); archive = root/"archive"
        cmd = [sys.executable,"src/collect_cycle.py","--stations",str(stations),"--archive-root",str(archive)] + [allow[x] for x in selected]
        result = subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        (root/"execution.json").write_text(json.dumps({"cycle":cycle,"sources":selected,"returncode":result.returncode,"command":cmd,"stdout":result.stdout[-20000:],"stderr":result.stderr[-20000:]},indent=2),encoding="utf8")
        uploaded = upload_tree(root,bucket,prefix)
        print(json.dumps({"archive_bucket":bucket,"prefix":prefix,"uploaded_files":len(uploaded),"collection_returncode":result.returncode}))
        sys.exit(result.returncode)

if __name__=="__main__": main()
