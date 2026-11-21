"""Recover durable FWA winter checkpoints without silently changing verified cases.

Archive snapshots are immutable release assets. GitHub Actions caches and
90-day artifacts are accelerators only, never the sole evidence store.
"""
import argparse, hashlib, json, shutil, tempfile, zipfile
from pathlib import Path

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def manifest_inventory(root):
    inventory={}
    for path in sorted(Path(root).glob("????????.json")):
        if not path.stem.isdigit():continue
        m=json.loads(path.read_text())
        if m.get("issue","")[:10].replace("-","") != path.stem:
            raise ValueError("Checkpoint date / manifest mismatch")
        paired=Path(root)/(path.stem+"_paired.csv")
        if m.get("paired_sha256"):
            if not paired.is_file() or sha(paired)!=m["paired_sha256"]:
                raise ValueError("Checkpoint paired hash mismatch: "+path.stem)
        if m.get("complete") and (m.get("paired_cases")!=18 or not m.get("paired_sha256")):
            raise ValueError("A complete checkpoint lacks 18 paired cases: "+path.stem)
        inventory[path.stem]=m
    return inventory

def restore(cache,archive):
    cache=Path(cache);cache.mkdir(parents=True,exist_ok=True)
    existing=manifest_inventory(cache)
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        with zipfile.ZipFile(archive) as z:
            if z.testzip() is not None:raise ValueError("Damaged archive")
            for item in z.infolist():
                p=Path(item.filename)
                if item.is_dir():continue
                if p.is_absolute() or ".." in p.parts or p.parts[0]!="winter-cache" or not p.name:
                    raise ValueError("Unexpected archive path: "+item.filename)
                destination=root.joinpath(*p.parts)
                destination.parent.mkdir(parents=True,exist_ok=True)
                with z.open(item) as src, destination.open("wb") as dst:
                    shutil.copyfileobj(src,dst)
        restored=root/"winter-cache"
        incoming=manifest_inventory(restored)
        for day in set(incoming).intersection(existing):
            a=existing[day];b=incoming[day]
            if a.get("complete") and b.get("complete") and a.get("paired_sha256")!=b.get("paired_sha256"):
                raise ValueError("Conflicting verified forecast day: "+day)
            if a.get("complete") and not b.get("complete"):
                raise ValueError("Durable release attempts to downgrade complete day: "+day)
        # The release is considered authoritative only for complete/missing
        # issue records. Never replace an already-verified complete day.
        recovered=[]
        for day,m in incoming.items():
            if existing.get(day,{}).get("complete"):continue
            old_attempts=existing.get(day,{}).get("attempts",-1)
            if day in existing and m.get("attempts",0)<old_attempts:continue
            for file in restored.glob(day+"*"):
                if not file.is_file():continue
                shutil.copy2(file,cache/file.name)
            recovered.append(day)
        for folder in ["om","directions"]:
            source=restored/folder
            if source.exists():
                for file in source.rglob("*"):
                    if not file.is_file():continue
                    dest=cache/file.relative_to(restored)
                    dest.parent.mkdir(parents=True,exist_ok=True)
                    if not dest.exists():shutil.copy2(file,dest)
        final=manifest_inventory(cache)
        if len(final)<len(existing):raise ValueError("Lost existing issue manifests")
    return {"prior_issue_days":len(existing),"durable_issue_days":len(incoming),
            "recovered_issue_days":recovered,"current_issue_days":len(final),
            "complete_issue_days":sum(bool(m.get("complete")) for m in final.values())}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--cache",default="winter-cache")
    p.add_argument("--archive",required=True)
    a=p.parse_args()
    print(json.dumps(restore(Path(a.cache),Path(a.archive)),indent=2))

if __name__=="__main__":main()
