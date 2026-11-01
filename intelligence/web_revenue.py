"""Unverified, name-matched web revenue leads; never financial statements."""
import math,re
from datetime import date
from decimal import Decimal
from intelligence.screener_financials import Tables


def extract(html,*,cin,company_name,source_company_name,symbol,source_url,observed_on):
    from urllib.parse import parse_qs,urlsplit
    parser=Tables();parser.feed(html)
    symbols={parse_qs(urlsplit(link).query).get('symbol',[''])[0].upper() for link in parser.links if urlsplit(link).hostname=='www.nseindia.com'}
    if symbol.upper() not in symbols:raise ValueError('Source page symbol mismatch')
    section=parser.sections.get('profit-loss')
    if not section:raise ValueError('No annual profit/loss section')
    text=' '.join(section['text'][:40])
    if 'Figures in Rs. Crores' not in text:raise ValueError('Unrecognized source currency/scale')
    headers=next((row for row in section['rows'] if any(cell['date'] for cell in row)),[])
    columns=[(cell['date'],i) for i,cell in enumerate(headers) if cell['date'] and re.fullmatch(r'\d{4}-\d{2}-\d{2}',cell['date']) and date.fromisoformat(cell['date'])<=date.fromisoformat(observed_on)]
    if not columns:raise ValueError('No non-future dated annual column; TTM excluded')
    period,column=max(columns)
    revenue=None;label=None
    for row in section['rows']:
        if not row:continue
        label=row[0]['text'].replace('+','').strip()
        if label not in ('Sales','Revenue') or len(row)<=column:continue
        number=row[column]['text'].replace(',','').replace('−','-').strip()
        if not re.fullmatch(r'-?\d+(?:\.\d+)?',number):continue
        revenue=float(Decimal(number)*10000000)
        if not math.isfinite(revenue):raise ValueError('Non-finite source amount')
        break
    if revenue is None:raise ValueError('No usable revenue figure')
    basis='standalone' if re.search(r'\bStandalone\s+Figures',text) else 'consolidated' if re.search(r'\bConsolidated\s+Figures',text) else 'unspecified'
    return dict(cin=cin,company_name=company_name,source_company_name=source_company_name,revenue_inr=revenue,source_label=label,period_end=period,reporting_basis=basis,source_url=source_url,observed_on=observed_on,verification_status='unverified',match_basis='unique normalized legal name and source NSE symbol; master CIN not confirmed',confidence='low',precision='Displayed INR crore values may be rounded',notice='Research lead only. The source may describe a different entity or reporting scope. Excluded from verified financials, revenue filters, growth and scores.')


def unique_leads(rows):
    """Collapse identical share-class pages; exclude conflicting CIN-level leads."""
    groups={}
    for row in rows:groups.setdefault(row['cin'],[]).append(row)
    result=[];conflicts=[]
    for cin,records in groups.items():
        measurements={(r['revenue_inr'],r['period_end'],r['reporting_basis']) for r in records}
        if len(measurements)!=1:conflicts.append(cin);continue
        chosen=dict(min(records,key=lambda r:r['source_url']))
        chosen['alternate_source_urls']=sorted({r['source_url'] for r in records if r['source_url']!=chosen['source_url']})
        result.append(chosen)
    return result,conflicts
