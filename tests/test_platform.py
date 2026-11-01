"""Synthetic fixtures only; never loaded into the application database."""
import csv
import io
import json
import sqlite3
import pytest
from werkzeug.security import generate_password_hash
from intelligence import create_app
from intelligence.db import get_db, now
from intelligence.ingest import ingest
from intelligence.analytics import directory, overview, research_score

CIN='U12345MH2010PTC000001'
CIN2='U12345KA2011PLC000002'


@pytest.fixture
def app(tmp_path):
    app=create_app({'TESTING':True,'DATABASE':str(tmp_path/'test.sqlite'),'SECRET_KEY':'test-only-secret'})
    with app.app_context():
        db=get_db()
        for username,role in [('admin','admin'),('reader','analyst')]:
            db.execute('INSERT INTO users(username,password_hash,role,created_at) VALUES(?,?,?,?)',
                       (username,generate_password_hash('test-password-only'),role,now()))
        db.commit()
    return app


@pytest.fixture
def client(app):
    c=app.test_client()
    with c.session_transaction() as s:
        s.update(user_id=1,csrf='test-csrf')
    return c


def load(db,tmp_path,kind,rows,source='mca',as_of='2025-03-31'):
    path=tmp_path/(kind+'.csv')
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for row in rows for k in row)))
        writer.writeheader();writer.writerows(rows)
    return ingest(db,path,kind,source,as_of)


def company(cin=CIN,**kwargs):
    return dict(cin=cin,name='Synthetic test entity '+cin[-1],status='Active',state='Maharashtra',
                industry='Testing',incorporated='2010-01-01',**{'class':'Private','listing_status':'unlisted'})|kwargs


def test_import_validation_duplicate_history(app,tmp_path):
    with app.app_context():
        db=get_db(); rows=[company(),company('invalid')]
        result=load(db,tmp_path,'companies',rows)
        assert (result['inserted'],result['rejected'],result['status'])==(1,1,'partial')
        assert load(db,tmp_path,'companies',rows)['duplicate']
        assert load(db,tmp_path,'companies',[company(name='Renamed synthetic fixture')],as_of='2025-04-01')['updated']==1
        assert db.execute('SELECT COUNT(*) FROM companies').fetchone()[0]==1
        assert db.execute('SELECT COUNT(*) FROM company_history').fetchone()[0]==2
        assert db.execute('SELECT name FROM historical_names').fetchone()[0].startswith('Synthetic')
        assert directory(db,{'q':'Synthetic'})['total']==1
        stale=load(db,tmp_path,'companies',[company(name='Older fixture')],as_of='2024-01-01')
        assert stale['rejected']==1


def test_financial_units_growth_revision_nulls(app,tmp_path):
    with app.app_context():
        db=get_db();load(db,tmp_path,'companies',[company()])
        statement={'cin':CIN,'financial_year':2024,'reporting_type':'standalone','unit':'INR crore',
                   'revenue':10,'net_profit':1,'assets':20,'liabilities':5,'source_url':'https://www.mca.gov.in/'}
        assert load(db,tmp_path,'financials',[statement,statement|{'financial_year':2025,'unit':'INR lakh','revenue':1200,'net_profit':150}])['inserted']==2
        row=directory(db,{})['rows'][0]
        assert row['revenue_inr']==120000000
        assert row['revenue_growth']==pytest.approx(20)
        assert row['profit_growth']==pytest.approx(50)
        revision=statement|{'financial_year':2025,'revenue':13}
        revision.pop('net_profit')
        load(db,tmp_path,'financials',[revision],as_of='2025-04-01')
        assert directory(db,{})['rows'][0]['profit_inr'] is None
        assert db.execute('SELECT COUNT(*) FROM financial_history').fetchone()[0]==1
        assert directory(db,{'fy':'2024'})['rows'][0]['revenue_inr']==100000000


def test_missing_financials_and_score(app,tmp_path):
    with app.app_context():
        load(get_db(),tmp_path,'companies',[company()])
        row=directory(get_db(),{})['rows'][0]
        assert row['revenue_inr'] is None
        assert directory(get_db(),{'min_revenue':'0'})['total']==0
        score=research_score(row)
        assert score['assessable_points']==15
        assert score['factors']['profitability']['points'] is None
        assert score['factors']['corporate_compliance']['points'] is None


def test_exchange_dedup_and_unknown_listing(app,tmp_path):
    with app.app_context():
        db=get_db();load(db,tmp_path,'companies',[company(listing_status=''),company(CIN2,listing_status='')])
        sec={'exchange':'NSE','symbol':'TEST1','name':'Synthetic test security','cin':CIN,'status':'Listed'}
        load(db,tmp_path,'securities',[sec,sec|{'symbol':'UNLINKED','cin':''}],source='nse')
        load(db,tmp_path,'securities',[sec|{'exchange':'BSE','symbol':'900001'}],source='bse')
        totals=overview(db,{})['summary']
        assert (totals['companies'],totals['listed'],totals['unknown_listing'],totals['securities'])==(2,1,1,3)
        assert totals['unlinked_securities']==1
        assert directory(db,{'listing':'unlisted'})['total']==0


def test_separate_registration_universes(app,tmp_path):
    with app.app_context():
        db=get_db();load(db,tmp_path,'companies',[company()])
        assert load(db,tmp_path,'llps',[{'llpin':'AAA-0001','name':'Synthetic LLP fixture'}])['inserted']==1
        assert load(db,tmp_path,'msmes',[{'registration_id':'UDYAM-MH-01-0000001','name':'Synthetic registration fixture'}],source='udyam')['inserted']==1
        counts=overview(db,{})['summary']
        assert (counts['companies'],counts['llps'],counts['msmes'])==(1,1,1)
        with pytest.raises(ValueError):
            load(db,tmp_path,'companies',[company()],source='msme_dashboard')


@pytest.mark.parametrize('args',[{'sort':'name; DROP TABLE companies'}, {'direction':'sideways'}, {'min_revenue':'nan'}, {'fy':'x'}, {'incorporated_from':'bad'}])
def test_invalid_filters(app,args):
    with app.app_context(),pytest.raises(ValueError):
        directory(get_db(),args)


def test_filters_pagination_and_exports(app,client,tmp_path):
    with app.app_context():
        db=get_db();load(db,tmp_path,'companies',[company(name='=test formula'),company(CIN2,state='Karnataka')])
    result=client.get('/api/companies?per_page=1&page=2').json
    assert len(result['rows'])==1 and result['total']==2
    assert client.get('/api/companies?state=Karnataka').json['total']==1
    csv_result=client.get('/api/export.csv?state=Maharashtra')
    assert "'=test formula" in csv_result.text
    from openpyxl import load_workbook
    xlsx=client.get('/api/export.xlsx')
    book=load_workbook(io.BytesIO(xlsx.data))
    assert book.active.max_row==3
    assert client.get('/api/company/'+CIN).json['company']['cin']==CIN
    assert client.get('/api/screen').json['total']==2


def test_auth_csrf_rbac(app,client):
    anonymous=app.test_client()
    assert anonymous.get('/api/companies').status_code==401
    assert anonymous.get('/').status_code==302
    assert client.post('/api/import').status_code==403
    with client.session_transaction() as s:s['user_id']=2
    assert client.post('/api/import',headers={'X-CSRF-Token':'test-csrf'}).status_code==403
    assert anonymous.get('/healthz').json['status']=='ok'
    assert "default-src 'self'" in client.get('/').headers['Content-Security-Policy']


def test_login_and_logout(app):
    c=app.test_client();assert c.get('/login').status_code==200
    with c.session_transaction() as s:token=s['csrf']
    assert c.post('/login',data={'username':'missing','password':'wrong','csrf_token':token}).status_code==200
    assert c.post('/login',data={'username':'admin','password':'test-password-only','csrf_token':token}).status_code==302
    assert c.get('/api/overview').status_code==200
    with c.session_transaction() as s:new_token=s['csrf']
    assert new_token!=token
    assert c.post('/logout',data={'csrf_token':new_token}).status_code==302
    assert c.get('/api/overview').status_code==401


def test_upload_and_headers(app,client):
    data={'source':'mca','kind':'companies','as_of':'2025-03-31',
          'file':(io.BytesIO(f'cin,name\n{CIN},Synthetic upload fixture\n'.encode()),'master.csv')}
    r=client.post('/api/import',data=data,headers={'X-CSRF-Token':'test-csrf'})
    assert r.status_code==200 and r.json['inserted']==1
    assert client.get('/api/sources').json['imports'][0]['status']=='completed'
    assert 'cin' in client.get('/api/template/companies').text
    assert client.get('/api/company/MISSING').status_code==404


def test_xlsx_import(app,tmp_path):
    from openpyxl import Workbook
    path=tmp_path/'master.xlsx';book=Workbook();sheet=book.active
    sheet.append(['CIN','COMPANY_NAME','DATE_OF_INCORPORATION']);sheet.append([CIN,'Synthetic Excel fixture','01/01/2010']);book.save(path)
    with app.app_context():
        assert ingest(get_db(),path,'companies','mca','2025-03-31')['inserted']==1


def test_field_level_provenance(app,tmp_path):
    with app.app_context():
        db=get_db();load(db,tmp_path,'companies',[company()])
        load(db,tmp_path,'companies',[{'cin':CIN,'name':'Synthetic updated name'}],source='data_gov',as_of='2025-04-01')
        fields={r['field']:r['source_id'] for r in db.execute('SELECT * FROM field_sources WHERE kind=?',('companies',))}
        assert fields['name']=='data_gov' and fields['state']=='mca'


def test_source_failure_does_not_invent_records(app,monkeypatch,tmp_path):
    from intelligence import sources
    import requests
    monkeypatch.setattr(requests.Session,'get',lambda *a,**k: (_ for _ in ()).throw(requests.ConnectionError('sensitive query')))
    status,message=sources.probe('nse')
    assert status=='unavailable' and 'sensitive' not in message
    with pytest.raises(sources.SourceError):sources.download_data_gov(tmp_path/'empty.csv')


def test_uploaded_export_mapping_and_rollback(app,tmp_path):
    columns={'CIN':CIN,'Company Name':'Synthetic agricultural fixture','Company Registration Date':'2010-01-01',
             'Company State':'Maharashtra','Company Industrial Classification':'Agriculture and Allied Activities',
             'Company Class':'One Person Company','Company ROC':'ROC Mumbai','Company Address':'Test address',
             'Pin Code':'400001','Company Sub Category':'Non-government company','Listing Status':'Unlisted'}
    with app.app_context():
        db=get_db();result=load(db,tmp_path,'companies',[columns],source='user_upload')
        assert result['inserted']==1
        row=directory(db,{})['rows'][0]
        assert row['industry']=='Agriculture and Allied Activities' and row['nic'] is None
        assert row['state']=='Maharashtra' and row['incorporated']=='2010-01-01'
        assert row['class']=='Private' and row['registered_class']=='One Person Company'
        assert row['roc']=='ROC Mumbai' and row['postal_code']=='400001' and row['address']=='Test address'
        # An invalid file structure after a valid row must roll back that earlier row.
        path=tmp_path/'malformed.csv';path.write_text(f'cin,name\n{CIN2},Synthetic rollback fixture\ninvalid,row,extra\n')
        failed=ingest(db,path,'companies','user_upload','2025-03-31')
        assert failed['status']=='failed' and failed['inserted']==0
        assert db.execute('SELECT COUNT(*) FROM companies WHERE cin=?',(CIN2,)).fetchone()[0]==0


def test_uploaded_terminal_statuses_and_coverage(app,tmp_path):
    with app.app_context():
        db=get_db();load(db,tmp_path,'companies',[company(status='Converted to LLP'),company(CIN2,status='Under CIRP')],source='user_upload')
        result=overview(db,{})
        assert result['summary']['inactive']==1 and result['summary']['other_status']==1
        assert result['summary']['llps']==0
        assert result['datasets']==[]
        import_id=db.execute('SELECT id FROM imports').fetchone()[0]
        db.execute('INSERT INTO import_annotations VALUES(?,?,?,?,?,?,?)',
                   (import_id,'Test subset','Partial state/industry coverage','User filename date','Not independently verified','test-checksum','test-archive'))
        db.commit()
        assert overview(db,{})['datasets'][0]['scope']=='Partial state/industry coverage'


@pytest.mark.parametrize('code',['PLN','GAT','UTC','PTL','NIL','SFC'])
def test_structurally_valid_three_letter_cin_types(code):
    from intelligence.ingest import normalize
    row=normalize({'cin':f'U12345MH2010{code}000001','name':'Synthetic CIN-type fixture','class':'Public'},'companies','user_upload')
    assert row['cin']==f'U12345MH2010{code}000001'
    assert row['class']=='Public'  # Class comes from the field, never guessed from the CIN.


@pytest.mark.parametrize('incorporated',['1111-11-11','9076-08-29'])
def test_implausible_source_date_is_not_age_evidence(incorporated):
    score=research_score({'incorporated':incorporated,'as_of':'2026-10-31'})
    assert score['factors']['business_history']['points'] is None
    assert score['assessable_points']==0


def test_city_options_filters_and_totals(app,client,tmp_path):
    with app.app_context():
        db=get_db()
        load(db,tmp_path,'companies',[
            company(address='123 Mumbai Road,Pune,Pune,Maharashtra,411001-India',postal_code='411001'),
            company(CIN2,address='Unstructured address',postal_code='400001')])
        assert directory(db,{'state':'Maharashtra','city':'pune'})['total']==1
        assert directory(db,{'state':'Maharashtra','city':'(Not identified)'})['total']==1
        assert overview(db,{'state':'Maharashtra','city':'Pune'})['summary']['companies']==1
    options=client.get('/api/options?state=Maharashtra').get_json()
    assert options['city']==['Pune'] and options['city_unknown']==1
