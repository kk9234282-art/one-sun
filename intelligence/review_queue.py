"""Authenticated application queue, scoped to its own companies and saved reviews."""
from .business_activity import enrich

def query(db,args):
    from .review_flags import flags
    flagged=tuple(flags());placeholders=','.join('?' for _ in flagged) or 'NULL'
    mode=args.get('mode','pending');order=args.get('order','priority');reason=args.get('reason','all')
    if mode not in ('pending','checked','all') or order not in ('priority','capital') or reason not in ('all','audit_flags','multiple_candidates'):raise ValueError('Invalid review queue mode or sort')
    size=min(50,max(1,int(args.get('per_page',20))));page=max(1,int(args.get('page',1)))
    base=f"""SELECT c.cin,c.name,c.state,c.industry,c.paid_up_capital,c.status,
        activity_matches(c.cin,'','source_described','') AS described,
        CASE WHEN c.cin IN ({placeholders}) THEN 1 ELSE 0 END AS audit_flagged,
        CASE WHEN json_extract(r.payload,'$.status')='reviewed' THEN 1 ELSE 0 END AS queue_checked
        FROM companies c LEFT JOIN activity_reviews r ON r.cin=c.cin AND r.version=(SELECT MAX(x.version) FROM activity_reviews x WHERE x.cin=c.cin)
        WHERE c.status='Active' AND (registered_activity_matches(c.cin,'','multiple_candidates')=1 OR c.cin IN ({placeholders}))"""
    params=flagged+flagged
    counts=db.execute('SELECT COUNT(*) AS total,COALESCE(SUM(queue_checked),0) AS checked,COALESCE(SUM(described),0) AS source_described,COALESCE(SUM(audit_flagged),0) AS audit_flagged,COALESCE(SUM(CASE WHEN audit_flagged=1 THEN queue_checked ELSE 0 END),0) AS flagged_checked FROM ('+base+')',params).fetchone();summary=dict(counts);flagged_checked=summary.pop('flagged_checked');summary['pending']=summary['total']-summary['checked']
    predicates=[]
    if mode!='all':predicates.append('queue_checked='+('1' if mode=='checked' else '0'))
    if reason!='all':predicates.append('audit_flagged='+('1' if reason=='audit_flags' else '0'))
    suffix=' WHERE '+' AND '.join(predicates) if predicates else ''
    cohort_total=summary['audit_flagged'] if reason=='audit_flags' else summary['total']-summary['audit_flagged'] if reason=='multiple_candidates' else summary['total'];cohort_checked=flagged_checked if reason=='audit_flags' else summary['checked']-flagged_checked if reason=='multiple_candidates' else summary['checked'];total=cohort_checked if mode=='checked' else cohort_total-cohort_checked if mode=='pending' else cohort_total;page=min(page,max(1,(total+size-1)//size));sort=('described DESC,' if order=='priority' else '')+'paid_up_capital DESC NULLS LAST,cin'
    rows=[enrich(dict(row)) for row in db.execute('SELECT * FROM ('+base+')'+suffix+' ORDER BY '+sort+' LIMIT ? OFFSET ?',params+(size,(page-1)*size))]
    return {'rows':rows,'summary':summary,'page':page,'per_page':size,'total':total,'scope':'shared'}
