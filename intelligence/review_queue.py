"""Authenticated application queue, scoped to its own companies and saved reviews."""
from .business_activity import enrich

def query(db,args):
    mode=args.get('mode','pending');order=args.get('order','priority')
    if mode not in ('pending','checked','all') or order not in ('priority','capital'):raise ValueError('Invalid review queue mode or sort')
    size=min(50,max(1,int(args.get('per_page',20))));page=max(1,int(args.get('page',1)))
    base="""SELECT c.cin,c.name,c.state,c.industry,c.paid_up_capital,c.status,
        activity_matches(c.cin,'','source_described','') AS described,
        CASE WHEN json_extract(r.payload,'$.status')='reviewed' THEN 1 ELSE 0 END AS queue_checked
        FROM companies c LEFT JOIN activity_reviews r ON r.cin=c.cin AND r.version=(SELECT MAX(x.version) FROM activity_reviews x WHERE x.cin=c.cin)
        WHERE c.status='Active' AND registered_activity_matches(c.cin,'','multiple_candidates')=1"""
    counts=db.execute('SELECT COUNT(*) AS total,COALESCE(SUM(queue_checked),0) AS checked,COALESCE(SUM(described),0) AS source_described FROM ('+base+')').fetchone();summary=dict(counts);summary['pending']=summary['total']-summary['checked']
    suffix=" WHERE queue_checked=0" if mode=='pending' else " WHERE queue_checked=1" if mode=='checked' else ''
    total=summary[mode] if mode in ('pending','checked') else summary['total'];page=min(page,max(1,(total+size-1)//size));sort=('described DESC,' if order=='priority' else '')+'paid_up_capital DESC NULLS LAST,cin'
    rows=[enrich(dict(row)) for row in db.execute('SELECT * FROM ('+base+')'+suffix+' ORDER BY '+sort+' LIMIT ? OFFSET ?',(size,(page-1)*size))]
    return {'rows':rows,'summary':summary,'page':page,'per_page':size,'total':total,'scope':'shared'}
