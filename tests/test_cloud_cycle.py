import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from cloud_cycle import upload_tree

class FakeBlob:
    def __init__(self,key):self.key=key;self.metadata={};self.uploads=[]
    def upload_from_filename(self,p,if_generation_match=None):
        assert if_generation_match==0
        self.uploads.append(Path(p).read_bytes())
class FakeBucket:
    def __init__(self):self.blobs={}
    def blob(self,key):
        self.blobs[key]=FakeBlob(key);return self.blobs[key]
class FakeClient:
    def __init__(self):self.b=FakeBucket()
    def bucket(self,name):assert name=="archive-bucket";return self.b
def test_upload_includes_raw_and_manifest(tmp_path):
    (tmp_path/"archive").mkdir()
    (tmp_path/"archive"/"raw.json").write_text('{"foo":1}')
    (tmp_path/"execution.json").write_text('{"ok":false}')
    fake=FakeClient()
    result=upload_tree(tmp_path,"archive-bucket","cycles/run123",fake)
    assert len(result)==2
    assert all(k.startswith("cycles/run123/") for k in result)
    assert all(len(blob.metadata["sha256"])==64 for blob in fake.b.blobs.values())
