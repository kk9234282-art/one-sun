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


@pytest.mark.parametrize('text,expected',[
    ('Manufactures decorative laminates and plywood.','Wood and plywood products'),
    ('Produces eggs and manufactures egg products.','Poultry and egg products'),
    ('Processes shrimps from aquaculture and produces shrimp feeds.','Aquaculture and seafood'),
    ('Manufactures shrimp feeds.','Animal feed'),
    ('Provides crop nutrition, crop protection and soil health management products.','Agricultural inputs and seeds'),
    ('The company is in the grain seed selling business.','Agricultural inputs and seeds'),
    ('The company offers premium western wear brands.','Textiles and apparel'),
    ('Manufactures LED lights and undertakes electrical projects.','Electrical equipment'),
    ('Manufactures bags, backpacks and fashion accessories.','Fashion accessories and bags'),
    ('Operates as an investment company.','Investment and holding companies'),
    ('Manufactures automotive lubricants and rubber process oils.','Lubricants and petroleum products'),
])
def test_explicit_product_and_service_gaps_are_covered(text,expected):
    assert expected in activity.tags_for(text)


def test_material_customer_and_name_context_does_not_invent_manufacture():
    tags=activity.tags_for('Harrisons Malayalam Ltd is engaged in plantations of tea and rubber.')
    assert 'Agriculture and farming' in tags
    assert 'Non-alcoholic beverages' not in tags and 'Plastics and rubber' not in tags
    tags=activity.tags_for('GP Petroleums Ltd manufactures Automotive Lubricants and Rubber Process Oils and trades base oil.')
    assert 'Lubricants and petroleum products' in tags
    assert 'Automobiles and components' not in tags and 'Plastics and rubber' not in tags
    assert 'Wood and plywood products' not in activity.tags_for('Wood Products Limited provides software development services.')
    assert 'Wood and plywood products' not in activity.tags_for('Manufactures resins for the plywood industry.')
    assert 'Fashion accessories and bags' not in activity.tags_for('Manufactures industrial woven bags.')
    assert 'Automobiles and components' in activity.tags_for('Makes piston rings and differential gears for automotive engines.')
    tags=activity.tags_for('Operates rubber plantations and manufactures rubber tyres.')
    assert 'Plastics and rubber' in tags and 'Agriculture and farming' in tags


def test_unspecified_alcohol_does_not_become_confirmed_alcoholic_beverages():
    tags=activity.tags_for('IFB Agro Ltd manufactures Alcohol and Marine products.')
    assert 'Alcohol products (type unspecified)' in tags and 'Aquaculture and seafood' in tags
    assert 'Alcoholic beverages' not in tags
    assert 'Alcohol products (type unspecified)' not in activity.tags_for('Manufactures industrial alcohol and ethanol.')
