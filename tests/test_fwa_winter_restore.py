"""Regression tests for durable recovery of frozen FWA validation cases."""
import io, json, sys, zipfile
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from fwa_winter_restore import restore,sha,manifest_inventory

def snapshot(tmp_path,days,tag="archive"):
    source=tmp_path/("origin-"+tag)/"winter-cache"
    source.mkdir(parents=True)
    for day,complete,content in days:
        (source/(day+"_paired.csv")).write_text(content)
        m={"issue":day[:4]+"-"+day[4:6]+"-"+day[6:8]+" 00:00:00+00:00",
           "complete":complete,"paired_cases":18 if complete else 0,
           "paired_sha256":sha(source/(day+"_paired.csv")) if complete else None,
           "attempts":1}
        (source/(day+".json")).write_text(json.dumps(m))
    dest=tmp_path/(tag+".zip")
    with zipfile.ZipFile(dest,"w") as z:
        for p in source.rglob("*"):
            if p.is_file():z.write(p,p.relative_to(source.parent))
    return dest

def test_restores_missing_days_without_losing_existing(tmp_path):
    cache=tmp_path/"current";cache.mkdir()
    a=snapshot(tmp_path,[("20261121",True,"old")],tag="old")
    b=snapshot(tmp_path,[("20261121",True,"old"),("20261122",True,"new")],tag="new")
    assert restore(cache,a)["current_issue_days"]==1
    r=restore(cache,b)
    assert r["recovered_issue_days"]==["20261122"]
    assert r["current_issue_days"]==2
    assert (cache/"20261121_paired.csv").read_text()=="old"

def test_conflicting_complete_days_fail_closed(tmp_path):
    cache=tmp_path/"current";cache.mkdir()
    a=snapshot(tmp_path,[("20261121",True,"old")],tag="old")
    b=snapshot(tmp_path,[("20261121",True,"different")],tag="new")
    restore(cache,a)
    with pytest.raises(ValueError,match="Conflicting verified"):
        restore(cache,b)
    assert (cache/"20261121_paired.csv").read_text()=="old"

def test_no_downgrade_or_corruption(tmp_path):
    cache=tmp_path/"current";cache.mkdir()
    a=snapshot(tmp_path,[("20261121",True,"old")],tag="old")
    b=snapshot(tmp_path,[("20261121",False,"new")],tag="new")
    restore(cache,a)
    with pytest.raises(ValueError,match="downgrade"):
        restore(cache,b)
    (cache/"20261121_paired.csv").write_text("tampered")
    with pytest.raises(ValueError,match="hash mismatch"):
        restore(cache,a)

def test_rejects_archive_path_escape(tmp_path):
    a=tmp_path/"danger.zip"
    with zipfile.ZipFile(a,"w") as z:
        z.writestr("../escapes.txt","bad")
    with pytest.raises(ValueError,match="Unexpected archive path"):
        restore(tmp_path/"current",a)
