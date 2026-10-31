import csv
import pytest
from intelligence import sources


class Response:
    def __init__(self,data=None,content=b'',status=200):
        self.data=data;self.content=content;self.status_code=status
    def json(self):return self.data
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def raise_for_status(self):
        if self.status_code>=400:
            import requests
            raise requests.HTTPError('test HTTP failure')
    def iter_content(self,size):yield self.content


class Session:
    def __init__(self,responses):self.responses=iter(responses);self.calls=[]
    def get(self,url,**kwargs):
        self.calls.append((url,kwargs));return next(self.responses)
    def __enter__(self):return self
    def __exit__(self,*args):pass


def test_nse_download_schema(monkeypatch,tmp_path):
    fake=Session([Response(content=b'SYMBOL,NAME OF COMPANY,ISIN NUMBER\nTEST,Synthetic connector fixture,INE000000001\n')])
    monkeypatch.setattr(sources,'session',lambda:fake)
    target=tmp_path/'nse.csv'
    sources.download_nse(target)
    assert target.read_text().startswith('SYMBOL,')
    assert fake.calls[0][1]['allow_redirects'] is False
    monkeypatch.setattr(sources,'session',lambda:Session([Response(content=b'<html>challenge</html>')]))
    with pytest.raises(sources.SourceError,match='expected NSE CSV'):
        sources.download_nse(target)


def test_ogd_pagination_and_redacted_errors(monkeypatch,tmp_path):
    monkeypatch.setenv('DATA_GOV_RESOURCE_ID','test-resource')
    monkeypatch.setenv('DATA_GOV_API_KEY','test-only-not-a-real-key')
    page=[{'cin':str(i),'name':'Synthetic connector fixture'} for i in range(1000)]
    fake=Session([Response({'records':page,'total':1001}),Response({'records':[{'cin':'last','name':'Synthetic final fixture'}],'total':1001})])
    monkeypatch.setattr(sources,'session',lambda:fake)
    path=tmp_path/'ogd.csv'
    _,offset=sources.download_data_gov(path)
    assert offset==1001
    assert [c[1]['params']['offset'] for c in fake.calls]==[0,1000]
    with path.open() as f:assert len(list(csv.DictReader(f)))==1001
    monkeypatch.setattr(sources,'session',lambda:Session([Response(status=403)]))
    with pytest.raises(sources.SourceError) as error:
        sources.download_data_gov(path)
    assert 'test-only-not-a-real-key' not in str(error.value)


def test_ogd_budget_and_terminal_page(monkeypatch,tmp_path):
    monkeypatch.setenv('DATA_GOV_RESOURCE_ID','test-resource');monkeypatch.setenv('DATA_GOV_API_KEY','test-key')
    rows=[{'cin':str(i)} for i in range(1000)]
    monkeypatch.setattr(sources,'session',lambda:Session([Response({'records':rows})]))
    with pytest.raises(sources.SourceError,match='Page budget'):
        sources.download_data_gov(tmp_path/'budget.csv',max_pages=1)
    monkeypatch.setattr(sources,'session',lambda:Session([Response({'records':rows,'total':1000})]))
    _,offset=sources.download_data_gov(tmp_path/'complete.csv',max_pages=1)
    assert offset==1000
