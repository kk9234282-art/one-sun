"""Enrich from cached public descriptions with explicit entity-match evidence. No network."""
import csv,gzip,hashlib,json,sqlite3,sys
from collections import Counter
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from intelligence.business_activity import extract_description,tags_for
ROOT=Path(__file__).resolve().parents[1]
def main():
    folder=ROOT/'deployment/national';static=ROOT/'intelligence/static';cache=ROOT/'instance/build/screener-financials';catalog=json.loads((folder/'catalog.json').read_text());db=sqlite3.connect('file:'+str(ROOT/'instance/india-online.sqlite')+'?mode=ro',uri=True)
    candidates={};rejected=[]
    for name in ['fetch-report.json','name-variants-fetch-report.json']:
        for result in json.loads((cache/name).read_text()).get('results',[]):
            identity=result.get('identity',{});cin=result.get('cin');records=result.get('records',[])
            if cin not in identity.get('cins',[]) or not records:continue
            source=records[0]['source_url'];candidates[cin]={'source_url':source,'symbol':result['symbol'],'identity_status':'cin_checked','identity_source_url':identity['source_url'],'expected_sha256':result.get('page_sha256')}
    lead_desc=catalog['web_revenue_research'];leads=json.loads(gzip.decompress((ROOT/'deployment'/lead_desc['path'].lstrip('/')).read_bytes()))
    for lead in leads:
        source=lead['source_url']
        if 'www.screener.in/company/' not in source:continue
        candidates.setdefault(lead['cin'],{'source_url':source,'symbol':source.split('/company/')[1].split('/')[0],'identity_status':'name_matched','identity_source_url':None,'expected_sha256':lead['source_sha256']})
    output=[]
    for cin,job in sorted(candidates.items()):
        p=cache/(hashlib.sha256(job['source_url'].encode()).hexdigest()+'.body')
        try:
            body=p.read_bytes();sha=hashlib.sha256(body).hexdigest()
            if not job['expected_sha256'] or sha!=job['expected_sha256']:raise ValueError('Page checksum missing or changed')
            master=db.execute('SELECT payload FROM records WHERE cin=?',(cin,)).fetchone()
            if not master:raise ValueError('Company missing from master')
            master=json.loads(master[0])
            if master['status']!='Active':continue
            description=extract_description(body.decode('utf-8'),job['symbol'])
            output.append(dict(cin=cin,company_name=master['name'],description=description,tags=tags_for(description),source_url=job['source_url'],source_sha256=sha,identity_status=job['identity_status'],identity_source_url=job['identity_source_url'],observed_on=datetime.fromtimestamp(p.stat().st_mtime,ZoneInfo('Asia/Kolkata')).date().isoformat(),master=master))
        except (OSError,ValueError) as error:rejected.append({'cin':cin,'reason':str(error)})
    evidence=Counter(r['identity_status'] for r in output);tags=Counter(t for r in output for t in r['tags']);covered={r['cin'] for r in output}
    # Existing high-capital queue makes the next 1,000-company pilot practical and bounded.
    queue=list(csv.DictReader((folder/'high-capital-revenue-research.csv').open(encoding='utf-8-sig')));pending=[r for r in queue if r['cin'] not in covered];pending.sort(key=lambda r:(-float(r.get('paid_up_capital_inr') or r.get('paid_up_capital') or 0),r['cin']));pilot=pending[:1000]
    internal=ROOT/'instance/reports';internal.mkdir(exist_ok=True)
    (internal/'business-activity-next-1000.json').write_text(json.dumps([{'cin':r['cin'],'company_name':r['company_name'],'status':'Needs source research; no search performed'} for r in pilot],indent=2))
    report={'schema_version':1,'source_data_commit':catalog['data_commit'],'master_records':catalog['record_count'],'active_companies':catalog['stats']['summary']['active'],'broad_categories':len(catalog['industries']),'source_description_candidates':len(candidates),'source_described_companies':len(output),'cin_checked':evidence['cin_checked'],'name_matched':evidence['name_matched'],'active_needing_research':catalog['stats']['summary']['active']-len(output),'activity_tags':dict(sorted(tags.items())),'next_pilot_companies':len(pilot),'method':'Extracted public About text from previously cached issuer pages; original page SHA-256 and NSE symbol checked. CIN-checked matches also retain previously checked annual-report identity evidence. Name-only matches remain low-confidence leads. No new web search performed.','code_policy':'CIN positions 2–6 preserved as registered activity code. Code system/version is not supplied; no automatic NIC-2008 or other version mapping. Registered industry remains separate from source-described operations.','description_policy':'Descriptions report what the cached source said as of retrieval, not independently verified current operations. Tags are keyword-based research aids from description text, never company-name guesses.','rejected':rejected}
    payload=[{'schema_version':1,'source_data_commit':catalog['data_commit'],'records':output,'report':report}];body=gzip.compress(json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode(),mtime=0);sha=hashlib.sha256(body).hexdigest();name='business-activities-'+sha[:12]+'.json.gz';(static/name).write_bytes(body)
    descriptor={'schema_version':1,'source_data_commit':catalog['data_commit'],'path':'/static/'+name,'rows':1,'bytes':len(body),'sha256':sha,'companies':len(output),'tags':sorted(tags)}
    (static/'business-activity-manifest.json').write_text(json.dumps(descriptor,indent=2)+'\n');(folder/'business-activity-report.json').write_text(json.dumps(report,indent=2)+'\n');catalog['business_activities']=descriptor;(folder/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,separators=(',',':')))
    print(json.dumps({k:v for k,v in report.items() if k not in ('rejected','activity_tags')},indent=2));print('Tags:',len(tags),'asset bytes:',len(body),'rejected:',len(rejected),flush=True)
if __name__=='__main__':main()
