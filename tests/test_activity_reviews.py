import csv
import pytest
from werkzeug.security import generate_password_hash
from intelligence import create_app
from intelligence.db import get_db,now
from intelligence.ingest import ingest
from intelligence.activity_reviews import validate

CIN='U15511MH2010PTC000001'
REVIEW={'description':'Manufactures plywood sheets and decorative laminates.','tags':['Plywood','Laminates'],'source_url':'https://example.test/products','source_kind':'company_website','review_date':'2026-01-01','source_date':'2025-12-01','source_excerpt':'We manufacture plywood sheets and decorative laminates.','identity_basis':'name_and_address','status':'reviewed'}
@pytest.fixture
def review_app(tmp_path):
    app=create_app({'TESTING':True,'DATABASE':str(tmp_path/'reviews.sqlite'),'SECRET_KEY':'review-test'})
    with app.app_context():
        db=get_db();db.execute('INSERT INTO users(username,password_hash,role,created_at) VALUES(?,?,?,?)',('analyst',generate_password_hash('review-test-password'),'analyst',now()));db.commit()
        p=tmp_path/'company.csv'
        with p.open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=['cin','name','status']);writer.writeheader();writer.writerow({'cin':CIN,'name':'Synthetic review company','status':'Active'})
        assert ingest(db,p,'companies','mca','2025-03-31')['inserted']==1
    return app

def signed_in(app):
    client=app.test_client()
    with client.session_transaction() as session:session.update(user_id=1,csrf='review-csrf')
    return client

def test_reviews_keep_revision_history_and_leave_source_records_unchanged(review_app):
    client=signed_in(review_app);url=f'/api/company/{CIN}/activity-reviews';headers={'X-CSRF-Token':'review-csrf'}
    assert client.get(url).json['current'] is None
    page=client.get('/').get_data(as_text=True)
    assert 'id="review-list"' in page and '/static/research.js' in page and 'data-review-storage="server"' in page
    first=client.post(url,json=REVIEW|{'expected_version':0},headers=headers)
    assert first.status_code==201 and first.json['current']['version']==1
    edited=REVIEW|{'description':'Manufactures plywood sheets; laminates require further checking.','status':'needs_review'}
    second=client.post(url,json=edited|{'expected_version':1},headers=headers)
    assert second.status_code==201 and len(second.json['history'])==2
    assert second.json['history'][1]['description']==REVIEW['description']
    stale=client.post(url,json=REVIEW|{'expected_version':0},headers=headers)
    assert stale.status_code==409
    assert client.get(url).json['current']['description']==edited['description']
    assert client.get('/api/activity-reviews').json['rows'][0]['cin']==CIN
    assert client.get('/api/companies').json['rows'][0]['business_description'] is None
    with review_app.app_context():
        db=get_db();assert db.execute('SELECT COUNT(*) FROM activity_reviews').fetchone()[0]==2
        assert db.execute('SELECT name FROM companies WHERE cin=?',(CIN,)).fetchone()[0]=='Synthetic review company'

def test_reviews_require_authentication_csrf_and_known_company(review_app):
    assert review_app.test_client().get(f'/api/company/{CIN}/activity-reviews').status_code==401
    client=signed_in(review_app)
    assert client.post(f'/api/company/{CIN}/activity-reviews',json=REVIEW|{'expected_version':0}).status_code==403
    assert client.post('/api/company/U15511MH2010PTC999999/activity-reviews',json=REVIEW|{'expected_version':0},headers={'X-CSRF-Token':'review-csrf'}).status_code==404
    assert client.post(f'/api/company/{CIN}/activity-reviews',json=REVIEW|{'description':'x'*70000,'expected_version':0},headers={'X-CSRF-Token':'review-csrf'}).status_code==413

@pytest.mark.parametrize('changed',[{'source_url':'javascript:alert(1)'},{'source_url':'https://user:pass@example.test'},{'identity_basis':'verified'},{'review_date':'2099-01-01'},{'source_date':'2026-02-30'},{'tags':[]},{'source_excerpt':''}])
def test_invalid_evidence_is_rejected(changed):
    with pytest.raises(ValueError):validate(REVIEW|changed)
