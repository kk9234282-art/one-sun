"""Bulk apply CIN reference candidates to every published company; no company web searches."""
import gzip,hashlib,json,sys
from collections import Counter,defaultdict
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from intelligence.registered_activity import candidates,reference
from scripts.build_online_india import Stats
ROOT=Path(__file__).resolve().parents[1]
def main():
    folder=ROOT/'deployment/national';static=ROOT/'intelligence/static';catalog=json.loads((folder/'catalog.json').read_text());fields=catalog['index_fields'];dictionaries=catalog['dictionaries'];all_stats=defaultdict(Stats);active_stats=defaultdict(Stats);code_chunks=defaultdict(set);processed=0
    for descriptor in catalog['global_chunks']:
        body=(folder/descriptor['path']).read_bytes()
        if hashlib.sha256(body).hexdigest()!=descriptor['sha256']:raise ValueError('Company chunk checksum mismatch')
        values=json.loads(gzip.decompress(body))
        if len(values)!=descriptor['rows']:raise ValueError('Company chunk row count mismatch')
        for values in values:
            row={key:dictionaries[key][value] if key in dictionaries else value for key,value in zip(fields,values)};code=row['cin'][1:6];row['as_of']=catalog['as_of']
            if row['cin'] in catalog.get('date_quality',{}):row['incorporated']=None
            all_stats[code].add(row);code_chunks[code].add(descriptor['path'])
            if row['status']=='Active':active_stats[code].add(row)
            processed+=1
        if processed%500000==0:print('Processed',processed,flush=True)
    rows={};total=Counter();active=Counter()
    for code,stats in sorted(all_stats.items()):
        choices=candidates(code);status='multiple_candidates' if len(choices)>1 else 'reference_candidate' if choices else 'unmapped';full=stats.output();current=active_stats[code].output()
        total[status]+=full['summary']['companies'];active[status]+=current['summary']['companies']
        rows[code]={'candidates':choices,'status':status,'label':' / '.join(c['description'].split(' [',1)[0] for c in choices),'stats':full,'active_stats':current,'chunks':sorted(code_chunks[code])}
    assert sum(total.values())==catalog['record_count'];assert sum(active.values())==catalog['stats']['summary']['active']
    report={'schema_version':1,'source_data_commit':catalog['data_commit'],'companies_processed':processed,'active_companies':sum(active.values()),'unique_cin_codes':len(rows),'all_company_counts':dict(total),'active_company_counts':dict(active),'registered_activity_candidates':sum(total.values())-total['unmapped'],'active_registered_activity_candidates':sum(active.values())-active['unmapped'],'note':'Registration-code reference candidates, not verified current business. NIC edition is not declared by the company master. Both 2004 and 2008 candidates are retained; shorter matches are explicitly labelled broad. Other historical editions may remain unresolved. No company-name inference or per-company internet research.'}
    data=[{'schema_version':1,'source_data_commit':catalog['data_commit'],'sources':reference()['sources'],'codes':rows,'report':report}];body=gzip.compress(json.dumps(data,ensure_ascii=False,separators=(',',':')).encode(),mtime=0);sha=hashlib.sha256(body).hexdigest();name='cin-activities-'+sha[:12]+'.json.gz';(static/name).write_bytes(body)
    d={'schema_version':1,'source_data_commit':catalog['data_commit'],'path':'/static/'+name,'rows':1,'sha256':sha,'bytes':len(body),'companies':processed};(static/'cin-activity-manifest.json').write_text(json.dumps(d,indent=2)+'\n');catalog['cin_activities']=d;(folder/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,separators=(',',':')));(folder/'cin-activity-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));print('Asset bytes:',len(body),flush=True)
if __name__=='__main__':main()
