import csv
import pytest
from werkzeug.security import generate_password_hash
from intelligence import create_app,business_activity
from intelligence.db import get_db,now
from intelligence.ingest import ingest
from intelligence.review_queue import query

A='U55101MH2010PTC000001';B='U72200MH2010PTC000002';C='U01111MH2010PTC000003';D='U55101MH2010PTC000004';E='U15511MH2010PTC000005';F='U55101MH2010PTC000006'
@pytest.fixture
def app(tmp_path,monkeypatch):
    monkeypatch.setattr(business_activity,'records',lambda:{A:{'description':'Synthetic company provides short-term hotel accommodation.','tags':['Hospitality'],'source_url':'https://example.test/company','observed_on':'2026-01-01','identity_status':'name_matched'}})
    app=create_app({'TESTING':True,'DATABASE':str(tmp_path/'queue.sqlite'),'SECRET_KEY':'queue-test'})
    with app.app_context():
        db=get_db();db.execute('INSERT INTO users(username,password_hash,role,created_at) VALUES(?,?,?,?)',('analyst',generate_password_hash('queue-test-password'),'analyst',now()));db.commit()
        p=tmp_path/'companies.csv'
        with p.open('w',newline='') as file:
            writer=csv.DictWriter(file,fieldnames=['cin','name','status','paid_up_capital']);writer.writeheader()
            for cin,status,capital in [(A,'Active',100),(B,'Active',1000),(C,'Active',500),(D,'Strike Off',99999),(E,'Active',99999),(F,'Active','')]:writer.writerow({'cin':cin,'name':'Synthetic '+cin[-1],'status':status,'paid_up_capital':capital})
        assert ingest(db,p,'companies','mca','2025-03-31')['inserted']==6
    return app

def test_queue_prioritizes_source_then_capital_without_treating_source_as_review(app):
    with app.app_context():
        first=query(get_db(),{});assert [r['cin'] for r in first['rows']]==[A,B,C,F]
        assert first['summary']=={'total':4,'checked':0,'pending':4,'source_described':1,'audit_flagged':0}
        assert [r['cin'] for r in query(get_db(),{'order':'capital'})['rows']]==[B,C,A,F]
        assert query(get_db(),{'per_page':'2','page':'99'})['page']==2
        with pytest.raises(ValueError):query(get_db(),{'mode':'verified'})

def test_latest_review_updates_pending_and_checked_but_preserves_queue_membership(app):
    client=app.test_client()
    assert client.get('/api/review-queue').status_code==401
    with client.session_transaction() as session:session.update(user_id=1,csrf='queue-csrf')
    value={'description':'Synthetic company supplies professional software services.','tags':['Software'],'source_url':'https://example.test/source','source_kind':'company_website','source_date':'2025-01-01','review_date':'2026-01-01','source_excerpt':'We supply professional software services.','identity_basis':'name_only','status':'reviewed','expected_version':0}
    assert client.post(f'/api/company/{B}/activity-reviews',json=value,headers={'X-CSRF-Token':'queue-csrf'}).status_code==201
    pending=client.get('/api/review-queue').json;assert pending['summary']['checked']==1 and pending['summary']['pending']==3
    assert B not in [r['cin'] for r in pending['rows']]
    checked=client.get('/api/review-queue?mode=checked').json;assert [r['cin'] for r in checked['rows']]==[B]
    value.update(status='needs_review',expected_version=1)
    assert client.post(f'/api/company/{B}/activity-reviews',json=value,headers={'X-CSRF-Token':'queue-csrf'}).status_code==201
    assert client.get('/api/review-queue').json['summary']['checked']==0


def test_rebuild_cleanup_removes_only_stale_generated_assets(tmp_path):
    from scripts.build_review_queue import cleanup
    stale=tmp_path/'page-0000-aaaaaaaaaaaa.json.gz';current=tmp_path/'manifest-bbbbbbbbbbbb.json.gz';other=tmp_path/'notes.json.gz'
    for p in (stale,current,other):p.write_bytes(b'test')
    cleanup(tmp_path,{current.name})
    assert not stale.exists() and current.exists() and other.exists()


def test_audit_flags_include_single_candidate_cases_without_correction_or_review(app,monkeypatch):
    from intelligence import review_flags
    sample={'cin':E,'reason':'Synthetic potential mismatch; primary evidence needed.','next_check':'Check the primary report.','status':'needs_primary_evidence'}
    monkeypatch.setattr(review_flags,'flags',lambda:{E:sample})
    with app.app_context():
        all_rows=query(get_db(),{'mode':'all'});assert all_rows['summary']['total']==5 and all_rows['summary']['audit_flagged']==1
        assert all_rows['summary']['checked']==0
        flagged=query(get_db(),{'reason':'audit_flags'});assert flagged['total']==1 and flagged['rows'][0]['cin']==E
        assert flagged['rows'][0]['registered_activity_status']=='reference_candidate'
        assert flagged['rows'][0]['activity_review_flag']['status']=='needs_primary_evidence'
        assert query(get_db(),{'reason':'multiple_candidates'})['total']==4
        assert get_db().execute('SELECT COUNT(*) FROM activity_reviews').fetchone()[0]==0


def test_shared_reviewed_flag_progress_uses_latest_manual_status(app,monkeypatch):
    from intelligence import review_flags
    monkeypatch.setattr(review_flags,'flags',lambda:{E:{'cin':E,'reason':'Synthetic potential mismatch','status':'needs_primary_evidence'}})
    client=app.test_client()
    with client.session_transaction() as session:session.update(user_id=1,csrf='queue-csrf')
    value={'description':'Synthetic company business description needs documentary review.','tags':['Synthetic'],'source_url':'https://example.test/source','source_kind':'other','source_date':'2025-01-01','review_date':'2026-01-01','source_excerpt':'Synthetic supporting source excerpt for a test review.','identity_basis':'name_only','status':'reviewed','expected_version':0}
    assert client.post(f'/api/company/{E}/activity-reviews',json=value,headers={'X-CSRF-Token':'queue-csrf'}).status_code==201
    assert client.get('/api/review-queue?reason=audit_flags').json['total']==0
    checked=client.get('/api/review-queue?reason=audit_flags&mode=checked').json
    assert checked['total']==1 and checked['rows'][0]['activity_review_flag']['status']=='needs_primary_evidence'
    assert checked['summary']['checked']==1
    assert client.get('/api/review-queue?reason=multiple_candidates').json['total']==4
