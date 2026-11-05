import pytest
from intelligence import business_activity as activity

HTML='''<a href="https://www.nseindia.com/get-quotes/equity?symbol=EXAMPLE">NSE</a><div class="about sub"><p>The company manufactures beer and alcoholic beverages.<sup><a href="https://example.test/annual.pdf">[1]</a></sup></p></div><p>Unrelated software text.</p>'''

def test_description_is_scoped_and_identity_checked():
    text=activity.extract_description(HTML,'EXAMPLE')
    assert text=='The company manufactures beer and alcoholic beverages.'
    assert activity.tags_for(text)==['Alcoholic beverages']
    with pytest.raises(ValueError,match='symbol'):activity.extract_description(HTML,'OTHER')
    with pytest.raises(ValueError,match='description'):activity.extract_description(HTML.replace('class="about sub"','class="other"'),'EXAMPLE')

def test_tags_use_description_not_company_name():
    assert 'Alcoholic beverages' not in activity.tags_for('Manufactures denatured spirits and ethanol.')
    assert 'Chemicals' in activity.tags_for('Manufactures denatured spirits and ethanol.')
    assert 'Agriculture and farming' in activity.tags_for('The company manufactures seeds and fertilizers.')
    assert 'Alcoholic beverages' not in activity.tags_for('The company develops agricultural software.')
    assert 'Software and IT services' in activity.tags_for('The company develops agricultural software.')

def test_evidence_filters_do_not_promote_name_matches(monkeypatch):
    monkeypatch.setattr(activity,'records',lambda:{'A':{'description':'The company produces beer.','tags':['Alcoholic beverages'],'identity_status':'name_matched'}})
    assert activity.matches('A','Alcoholic beverages','source_described','beer')
    assert not activity.matches('A','','cin_checked','')
    assert activity.matches('A','','name_matched','')
    assert activity.matches('B','','needs_research','')
    assert not activity.matches('B','Alcoholic beverages','needs_research','')


def test_unknown_activity_is_unfilled_and_code_is_not_translated(monkeypatch):
    monkeypatch.setattr(activity,'records',lambda:{})
    row=activity.enrich({'cin':'U55101MH2022PTC389051'})
    assert row['registered_activity_code']=='55101'
    assert row['business_description'] is None
    assert row['activity_evidence']=='needs_research'


def test_flask_directory_and_totals_share_activity_evidence(tmp_path,monkeypatch):
    import csv
    from intelligence import create_app
    from intelligence.db import get_db
    from intelligence.ingest import ingest
    from intelligence.analytics import directory,overview
    cin='U15511MH2010PTC000001';other='U01111MH2010PTC000002'
    source={'description':'Manufactures alcoholic beverages.','tags':['Alcoholic beverages'],'identity_status':'name_matched','source_url':'https://www.screener.in/company/SYNTHETIC/','observed_on':'2026-11-01'}
    monkeypatch.setattr(activity,'records',lambda:{cin:source})
    app=create_app({'TESTING':True,'DATABASE':str(tmp_path/'test.sqlite'),'SECRET_KEY':'test'})
    path=tmp_path/'companies.csv'
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['cin','name','status']);writer.writeheader();writer.writerows([{'cin':cin,'name':'Synthetic beverages','status':'Active'},{'cin':other,'name':'Synthetic agriculture','status':'Active'}])
    with app.app_context():
        db=get_db();assert ingest(db,path,'companies','mca','2025-03-31')['inserted']==2
        filters={'activity_tag':'Alcoholic beverages','activity_evidence':'name_matched'}
        found=directory(db,filters);assert found['total']==1;assert found['rows'][0]['activity_evidence']=='name_matched'
        assert overview(db,filters)['summary']['companies']==1
        assert directory(db,{'activity_evidence':'cin_checked'})['total']==0
        assert directory(db,{'activity_evidence':'needs_research'})['total']==1
        assert directory(db,{'registered_activity_code':'15511'})['total']==1
        assert directory(db,{'registered_activity_q':'liquor'})['total']==1
        assert directory(db,{'registered_activity_status':'unmapped'})['total']==0
        assert directory(db,{'registered_activity_status':'multiple_candidates'})['total']==1
        with pytest.raises(ValueError):directory(db,{'registered_activity_code':'155'})
