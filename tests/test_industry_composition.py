"""Industry parents and exact CIN subcategories share directory filtering."""
import csv
from intelligence import create_app
from intelligence.db import get_db
from intelligence.ingest import ingest
from intelligence.analytics import directory,industry_composition


def test_subcategories_count_companies_once_and_respect_scope(tmp_path):
    app=create_app({'TESTING':True,'DATABASE':str(tmp_path/'test.sqlite'),'SECRET_KEY':'test'})
    path=tmp_path/'companies.csv'
    rows=[
        ['U01111MH2010PTC000001','First','Active','Manufacturing','Maharashtra',100000000],
        ['U01111GJ2010PTC000002','Second','Active','Manufacturing','Gujarat',100],
        ['U20110MH2010PTC000003','Third','Active','Manufacturing','Maharashtra',100],
        ['U01111MH2010PTC000004','Fourth','Active','Trading','Maharashtra',100],
        ['U01111MH2010PTC000005','Fifth','Strike Off','Manufacturing','Maharashtra',100],
    ]
    with path.open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['cin','name','status','industry','state','paid_up_capital']);writer.writerows(rows)
    with app.app_context():
        db=get_db();assert ingest(db,path,'companies','mca','2025-03-31')['inserted']==5
        filters={'industry':'Manufacturing','status':'Active'}
        result=industry_composition(db,filters)
        assert result['total']==directory(db,filters)['total']==3
        assert [(r['value'],r['count']) for r in result['rows']]==[('01111',2),('20110',1)]
        assert 'NIC 2004' in result['rows'][0]['label'] and 'NIC 2008' in result['rows'][0]['label']
        assert industry_composition(db,{**filters,'state':'Maharashtra'})['total']==2
        assert industry_composition(db,{**filters,'min_capital':'100000000'})['total']==1
        assert industry_composition(db,{**filters,'registered_activity_code':'01111'})['total']==2
        assert industry_composition(db,{**filters,'q':'Third'})['rows'][0]['value']=='20110'
        assert industry_composition(db,{**filters,'industry':'Absent'})=={'rows':[],'total':0}
        assert industry_composition(db,{'status':'Active'})=={'rows':[],'total':0}
