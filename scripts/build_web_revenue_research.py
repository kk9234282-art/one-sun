"""Build a high-capital research queue and real cached name-only revenue leads.

No network search is claimed. Only already collected public tables supply
amounts; generated search links are pending research, never source evidence.
"""
import csv,gzip,hashlib,io,json,sys,re
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from intelligence.company_names import candidate_key
from intelligence.web_revenue import extract,unique_leads
ROOT=Path(__file__).resolve().parents[1]

def main():
    folder=ROOT/'deployment/national';catalog=json.loads((folder/'catalog.json').read_text());fields=catalog['index_fields'];dictionaries=catalog['dictionaries'];targets={}
    for descriptor in catalog['global_chunks']:
        body=(folder/descriptor['path']).read_bytes()
        if hashlib.sha256(body).hexdigest()!=descriptor['sha256']:raise ValueError('Company source checksum mismatch')
        for values in json.loads(gzip.decompress(body)):
            if dictionaries['status'][values[fields.index('status')]]!='Active':continue
            capital=values[fields.index('paid_up_capital')]
            if capital is None or capital<100000000:continue
            row={key:dictionaries[key][value] if key in dictionaries else value for key,value in zip(fields,values)};targets[row['cin']]=row
    active=json.loads(gzip.decompress((ROOT/'deployment'/catalog['active_summary']['path'].lstrip('/')).read_bytes()))[0]
    if len(targets)!=active['facets']['capital_band']['10cr_plus']['summary']['companies']:raise ValueError('High-capital counts do not reconcile')
    financial=catalog['financials'];body=(ROOT/'instance/build/listed-financials'/financial['path'].rsplit('/',1)[-1]).read_bytes();assert hashlib.sha256(body).hexdigest()==financial['sha256'];statements=json.loads(gzip.decompress(body));verified={r['cin'] for r in statements}
    latest={}
    for statement in statements:
        previous=latest.get(statement['cin'])
        if previous is None or (statement['reporting_type']=='standalone',statement['period_end'],statement['as_of'])>(previous['reporting_type']=='standalone',previous['period_end'],previous['as_of']):latest[statement['cin']]=statement
    names={}
    for row in targets.values():names.setdefault(candidate_key(row['name']),[]).append(row)
    cache=ROOT/'instance/build/screener-financials';url='https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv';exchange=list(csv.DictReader(io.StringIO((cache/(hashlib.sha256(url.encode()).hexdigest()+'.body')).read_text(encoding='utf-8-sig'))));leads=[];examined=0;rejected=0
    for issuer in exchange:
        matches=names.get(candidate_key(issuer['NAME OF COMPANY']),[])
        if len(matches)!=1 or matches[0]['cin'] in verified:continue
        row=matches[0];source='https://www.screener.in/company/'+issuer['SYMBOL']+'/';page=cache/(hashlib.sha256(source.encode()).hexdigest()+'.body')
        if not page.exists():continue
        examined+=1
        try:
            lead=extract(page.read_text(),cin=row['cin'],company_name=row['name'],source_company_name=issuer['NAME OF COMPANY'],symbol=issuer['SYMBOL'],source_url=source,observed_on=datetime.fromtimestamp(page.stat().st_mtime,ZoneInfo('Asia/Kolkata')).date().isoformat());lead['source_sha256']=hashlib.sha256(page.read_bytes()).hexdigest();leads.append(lead)
        except ValueError:rejected+=1
    source_rows=len(leads);leads,conflicts=unique_leads(leads)
    by_cin={r['cin']:r for r in leads};queue=[]
    for cin,row in sorted(targets.items(),key=lambda pair:pair[1]['name']):
        lead=by_cin.get(cin,{});statement=latest.get(cin,{})
        revenue=statement.get('revenue');revenue=None if revenue is None else revenue*{'INR':1,'INR lakh':100000,'INR crore':10000000}[statement['unit']]
        queue.append(dict(cin=cin,company_name=row['name'],master_status=row['status'],state=row['state'],listing=row['effective_listing'],paid_up_capital_inr=row['paid_up_capital'],research_status='Verified statement imported' if cin in verified else 'Unverified web revenue lead' if lead else 'Not researched',verified_revenue_inr=revenue,verified_period_end=statement.get('period_end'),verified_reporting_basis=statement.get('reporting_type'),verified_source_url=statement.get('source_url'),web_revenue_inr=lead.get('revenue_inr'),web_period_end=lead.get('period_end'),web_reporting_basis=lead.get('reporting_basis'),web_source_url=lead.get('source_url'),web_observed_on=lead.get('observed_on'),web_confidence=lead.get('confidence'),name_revenue_search_url='https://www.google.com/search?q='+quote_plus('"'+row['name']+'" revenue turnover annual report')))
    def write_csv(name,rows):
        stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows({key:("'"+value if isinstance(value,str) and re.match(r'^\s*[=+@-]',value) else value) for key,value in row.items()} for row in rows);(folder/name).write_bytes(stream.getvalue().encode('utf-8-sig'))
    write_csv('high-capital-revenue-research.csv',queue)
    if leads:write_csv('unverified-web-revenue.csv',leads)
    body=gzip.compress(json.dumps(leads,separators=(',',':'),allow_nan=False).encode(),mtime=0);sha=hashlib.sha256(body).hexdigest();name='web-revenue-'+sha[:12]+'.json.gz';(folder/name).write_bytes(body)
    report=dict(schema_version=1,source_data_commit=catalog['data_commit'],target_companies=len(targets),capital_scope='Active, paid-up capital >= INR 100000000',verified_statement_companies=sum(cin in verified for cin in targets),unverified_web_leads=len(leads),cached_pages_examined=examined,cached_pages_rejected=rejected,duplicate_source_pages=source_rows-len({r['cin'] for r in leads})-len(conflicts),conflicting_company_matches=len(conflicts),pending_research_companies=len(targets)-sum(cin in verified for cin in targets)-len(leads),method='Unique normalized legal-name candidate from NSE equity list; source page symbol checked. Master CIN NOT verified. Only existing cached public annual tables were read; no general web search performed. Search links are research suggestions, not evidence.',rows=len(leads),path='/national/'+name,sha256=sha,bytes=len(body),queue_csv_path='/national/high-capital-revenue-research.csv',leads_csv_path='/national/unverified-web-revenue.csv')
    (folder/'web-revenue-research-report.json').write_text(json.dumps(report,indent=2)+'\n');catalog['web_revenue_research']=report;(folder/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,separators=(',',':')));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
