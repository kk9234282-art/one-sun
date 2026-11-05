import json
from datetime import date

LISTED = "EXISTS(SELECT 1 FROM securities s WHERE s.cin=c.cin AND s.status IN ('Listed','Active'))"
INACTIVE_STATUSES = ('Strike Off','Struck Off','Dormant','Dissolved','Under Liquidation','Inactive','Amalgamated',
                     'Converted To Llp','Dissolved (Liquidated)','Dormant Under Section 455',
                     'Dissolved Under Section 59(8)','Dissolved Under Section 54')
INACTIVE_SQL = ','.join("'"+value+"'" for value in INACTIVE_STATUSES)
BASE = f"""WITH ranked AS (
 SELECT f.*,ROW_NUMBER() OVER(PARTITION BY cin ORDER BY financial_year DESC) AS rn
 FROM financials f WHERE reporting_type=:reporting_type AND (:fy='' OR financial_year=CAST(:fy AS INTEGER))
), latest AS (SELECT *, CASE unit WHEN 'INR crore' THEN 10000000 WHEN 'INR lakh' THEN 100000 ELSE 1 END AS multiplier FROM ranked WHERE rn=1)
SELECT c.cin,c.name,c.class,c.category,c.status,c.incorporated,c.address,c.state,c.industry,c.nic,c.authorised_capital,c.paid_up_capital,c.listing_status,c.source_id,c.as_of,c.updated_at,c.import_id,c.roc,c.postal_code,c.subcategory,c.registered_class,c.district AS source_district,pin_district(c.postal_code,c.state) AS district,pin_area(c.postal_code,c.state) AS postal_city, pin_district(c.postal_code,c.state) AS city, CASE WHEN {LISTED} THEN 'listed' ELSE COALESCE(c.listing_status,'unknown') END AS effective_listing,
 f.financial_year, f.reporting_type, f.revenue*f.multiplier AS revenue_inr, f.net_profit*f.multiplier AS profit_inr,
 f.assets*f.multiplier AS assets_inr, f.liabilities*f.multiplier AS liabilities_inr,
 CASE WHEN p.revenue>0 THEN (f.revenue*f.multiplier/(p.revenue*CASE p.unit WHEN 'INR crore' THEN 10000000 WHEN 'INR lakh' THEN 100000 ELSE 1 END)-1)*100 END AS revenue_growth,
 CASE WHEN p.net_profit>0 THEN (f.net_profit*f.multiplier/(p.net_profit*CASE p.unit WHEN 'INR crore' THEN 10000000 WHEN 'INR lakh' THEN 100000 ELSE 1 END)-1)*100 END AS profit_growth,
 f.source_url AS financial_source, f.as_of AS financial_as_of
FROM companies c LEFT JOIN latest f ON c.cin=f.cin
LEFT JOIN financials p ON p.cin=f.cin AND p.financial_year=f.financial_year-1 AND p.reporting_type=f.reporting_type"""


def query(args):
    params = {'reporting_type': args.get('reporting_type','standalone'), 'fy': args.get('fy','')}
    if params['reporting_type'] not in ('standalone','consolidated'):
        raise ValueError('Invalid reporting type')
    if params['fy'] and not str(params['fy']).isdigit():
        raise ValueError('Financial year must be an integer')
    conditions = []
    for field in ('state','industry','class','status','district','nic','city','roc','postal_code','postal_city'):
        if args.get(field):
            conditions.append(f'lower({field})=lower(:{field})' if field in ('city','district','postal_city') else f'{field}=:{field}')
            params[field] = args[field]
    for field in ('city','district','postal_city'):
        if str(args.get(field,'')).strip().lower()=='(not identified)':
            conditions.remove(f'lower({field})=lower(:{field})');conditions.append(f'{field} IS NULL')
    if args.get('activity_evidence') and args['activity_evidence'] not in ('source_described','cin_checked','name_matched','needs_research'):
        raise ValueError('Invalid business activity evidence filter')
    if args.get('registered_activity_code'):
        code=args['registered_activity_code']
        if len(code)!=5 or not code.isascii() or not code.isdigit():raise ValueError('Registered activity code must contain five digits')
        params['registered_activity_code']=code;conditions.append('substr(cin,2,5)=:registered_activity_code')
    if any(args.get(key) for key in ('activity_tag','activity_evidence','activity_q')):
        for key in ('activity_tag','activity_evidence','activity_q'):params[key]=args.get(key,'').strip()
        conditions.append('activity_matches(cin,:activity_tag,:activity_evidence,:activity_q)=1')
    if args.get('q'):
        params['q'] = '%' + args['q'].replace('\\','\\\\').replace('%','\\%').replace('_','\\_') + '%'
        conditions.append("(name LIKE :q ESCAPE '\\' OR cin LIKE :q ESCAPE '\\' OR cin IN (SELECT cin FROM historical_names WHERE name LIKE :q ESCAPE '\\'))")
    if args.get('listing'):
        if args['listing'] not in ('listed','unlisted','unknown'):
            raise ValueError('Invalid listing filter')
        params['listing'] = args['listing']
        conditions.append('effective_listing=:listing')
    for field in ('incorporated','as_of'):
        for suffix, op in (('from','>='),('to','<=')):
            key = field+'_'+suffix
            if args.get(key):
                params[key] = date.fromisoformat(args[key]).isoformat()
                conditions.append(f'{field}{op}:{key}')
    for key, expression in {'min_revenue':'revenue_inr', 'min_profit':'profit_inr','min_revenue_growth':'revenue_growth',
                            'min_profit_growth':'profit_growth','min_capital':'paid_up_capital'}.items():
        if args.get(key) is not None and args.get(key) != '':
            import math
            params[key] = float(args[key])
            if not math.isfinite(params[key]):
                raise ValueError('Filter must be finite')
            conditions.append(f'{expression}>=:{key}')
    band=args.get('capital_band','')
    if band:
        capital_conditions={
            'under_1cr':'paid_up_capital IS NOT NULL AND paid_up_capital<10000000',
            '1_to_10cr':'paid_up_capital>=10000000 AND paid_up_capital<100000000',
            '10cr_plus':'paid_up_capital>=100000000',
            'unknown':'paid_up_capital IS NULL',
        }
        if band not in capital_conditions:
            raise ValueError('Invalid paid-up capital range')
        conditions.append('('+capital_conditions[band]+')')
    if args.get('positive_profit') == '1':
        conditions.append('profit_inr>0')
    if args.get('min_age'):
        age = int(args['min_age'])
        if age < 0:
            raise ValueError('Age must be nonnegative')
        params['min_age'] = age
        conditions.append("(julianday('now')-julianday(incorporated))/365.2425>=:min_age")
    sql = 'SELECT * FROM (' + BASE + ') universe'
    if conditions:
        sql += ' WHERE ' + ' AND '.join(conditions)
    return sql, params


def directory(db, args, export=False):
    sql, params = query(args)
    sort = args.get('sort','name')
    if sort not in ('name','cin','incorporated','paid_up_capital','revenue_inr','profit_inr','revenue_growth','as_of'):
        raise ValueError('Invalid sort column')
    direction = args.get('direction','asc').lower()
    if direction not in ('asc','desc'):
        raise ValueError('Invalid sort direction')
    count = db.execute('SELECT COUNT(*) FROM ('+sql+')', params).fetchone()[0]
    sql += f' ORDER BY {sort} {direction} NULLS LAST,cin'
    if export:
        return db.execute(sql, params), count
    page = max(1,int(args.get('page',1)))
    per_page = min(100,max(1,int(args.get('per_page',25))))
    params.update(limit=per_page,offset=(page-1)*per_page)
    from .business_activity import enrich
    rows = [enrich(dict(r)) for r in db.execute(sql+' LIMIT :limit OFFSET :offset',params)]
    return {'rows': rows, 'total': count,'page': page,'per_page':per_page}


def overview(db,args):
    sql, params = query(args)
    groups = {}
    for field in ('state','industry','class','effective_listing','status','district','postal_city'):
        groups[field] = [dict(r) for r in db.execute(f'SELECT COALESCE({field},\'Unknown\') AS label,COUNT(*) AS count FROM ({sql}) GROUP BY {field} ORDER BY count DESC,label',params)]
    groups['trends'] = [dict(r) for r in db.execute(f"SELECT substr(incorporated,1,4) AS label,COUNT(*) AS count FROM ({sql}) WHERE incorporated IS NOT NULL GROUP BY label ORDER BY label",params)]
    groups['capital'] = [dict(r) for r in db.execute(f"""SELECT CASE WHEN paid_up_capital IS NULL THEN 'Unknown' WHEN paid_up_capital<10000000 THEN '< ₹1 crore' WHEN paid_up_capital<100000000 THEN '₹1–10 crore' ELSE '≥ ₹10 crore' END AS label,COUNT(*) AS count FROM ({sql}) GROUP BY label""",params)]
    summary = dict(db.execute(f"""SELECT COUNT(*) AS companies,
      SUM(CASE WHEN status='Active' THEN 1 ELSE 0 END) AS active,
      SUM(CASE WHEN status IN ({INACTIVE_SQL}) THEN 1 ELSE 0 END) AS inactive,
      SUM(CASE WHEN status IS NULL OR (status!='Active' AND status NOT IN ({INACTIVE_SQL})) THEN 1 ELSE 0 END) AS other_status,
      SUM(CASE WHEN class='Private' THEN 1 ELSE 0 END) AS private,
      SUM(CASE WHEN class='Public' THEN 1 ELSE 0 END) AS public,
      SUM(CASE WHEN effective_listing='listed' THEN 1 ELSE 0 END) AS listed,
      SUM(CASE WHEN effective_listing='unlisted' THEN 1 ELSE 0 END) AS unlisted,
      SUM(CASE WHEN effective_listing='unknown' THEN 1 ELSE 0 END) AS unknown_listing,
      SUM(CASE WHEN revenue_inr IS NOT NULL THEN 1 ELSE 0 END) AS financial_coverage,
      MIN(as_of) AS oldest,MAX(as_of) AS newest FROM ({sql})""",params).fetchone())
    for key in ('active','inactive','other_status','private','public','listed','unlisted','unknown_listing','financial_coverage'):
        summary[key] = summary[key] or 0
    # These independent universes are deliberately not added to companies.
    summary['llps'] = db.execute('SELECT COUNT(*) FROM llps').fetchone()[0]
    summary['msmes'] = db.execute('SELECT COUNT(*) FROM msmes').fetchone()[0]
    summary['securities'] = db.execute('SELECT COUNT(*) FROM securities').fetchone()[0]
    summary['unlinked_securities'] = db.execute('SELECT COUNT(*) FROM securities WHERE cin IS NULL').fetchone()[0]
    datasets = [dict(r) for r in db.execute('SELECT a.*,i.as_of,i.inserted,i.updated,i.rejected,i.status FROM import_annotations a JOIN imports i ON i.id=a.import_id ORDER BY i.id DESC')]
    return {'summary':summary,'groups':groups,'datasets':datasets}


DEFAULT_WEIGHTS = {'revenue_growth':25,'profitability':20,'financial_stability':20,'business_history':15,'corporate_compliance':10,'industry_prospects':10}


def research_score(row, weights=None):
    weights = weights or DEFAULT_WEIGHTS
    if set(weights) != set(DEFAULT_WEIGHTS) or any(not isinstance(v,(int,float)) or v<0 or v>100 for v in weights.values()) or sum(weights.values()) != 100:
        raise ValueError('Score weights must contain the six factors and total 100')
    factors = {}
    growth = row.get('revenue_growth')
    factors['revenue_growth'] = None if growth is None else max(0,min(1,growth/25))
    revenue, profit = row.get('revenue_inr'), row.get('profit_inr')
    factors['profitability'] = None if revenue is None or revenue<=0 or profit is None else max(0,min(1,profit/revenue/0.15))
    assets, liabilities = row.get('assets_inr'), row.get('liabilities_inr')
    factors['financial_stability'] = None if assets is None or assets<=0 or liabilities is None else max(0,min(1,1-liabilities/assets))
    incorporated = row.get('incorporated')
    if incorporated == '1111-11-11' or (incorporated and incorporated > (row.get('as_of') or date.today().isoformat())):
        incorporated = None
    factors['business_history'] = None if not incorporated else max(0,min(1,(date.today()-date.fromisoformat(incorporated)).days/365.2425/10))
    # Master status and sector labels are insufficient evidence of compliance or prospects.
    factors['corporate_compliance'] = None
    factors['industry_prospects'] = None
    detail = {k:{'points':None if v is None else round(v*weights[k],2),'maximum':weights[k]} for k,v in factors.items()}
    covered = sum(weights[k] for k,v in factors.items() if v is not None)
    return {'observed_points':round(sum(v['points'] or 0 for v in detail.values()),2),
            'assessable_points':covered,'maximum':100,'factors':detail,
            'notice':'Partial research indicator, not an official SEBI IPO eligibility test or investment recommendation. Missing evidence is unscored; points are not normalized to 100.'}
