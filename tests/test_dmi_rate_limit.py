import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
import collect_matched_forecasts as collector
import fetch_dmi_observations as observations

class Response:
    def __init__(self,status,wait=None):
        self.status_code=status
        self.headers={"Retry-After":str(wait)} if wait is not None else {}
    def raise_for_status(self):
        if self.status_code>=400:raise AssertionError("Should not raise before handling 429")

def test_harmonie_retries_429(monkeypatch):
    calls=[]
    responses=iter([Response(429,5),Response(200)])
    monkeypatch.setattr(collector.time,"sleep",lambda t:calls.append(t))
    monkeypatch.setattr(collector.requests,"get",lambda *args,**kwargs:next(responses))
    assert collector.dmi_request("https://example.org") .status_code==200
    assert any(wait>=5 for wait in calls)
def test_observation_retries_429(monkeypatch):
    calls=[]
    responses=iter([Response(429,8),Response(200)])
    monkeypatch.setattr(observations.time,"sleep",lambda t:calls.append(t))
    monkeypatch.setattr(observations.requests,"get",lambda *args,**kwargs:next(responses))
    assert observations.polite_get({"stationId":"06011"}).status_code==200
    assert 8 in calls
