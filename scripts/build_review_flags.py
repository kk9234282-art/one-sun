"""Add a tiny sparse overlay; preserve every original queue page and membership file."""
import bisect,gzip,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from intelligence.business_activity import records
from intelligence.registered_activity import details
from intelligence.review_flags import flags
ROOT=Path(__file__).resolve().parents[1]
def main():
    folder=ROOT/'deployment/national';static=ROOT/'intelligence/static';catalog=json.loads((folder/'catalog.json').read_text());base_d=catalog['review_queue']
    def load(d):
        body=(ROOT/'deployment'/d['path'].lstrip('/')).read_bytes()
        if hashlib.sha256(body).hexdigest()!=d['sha256']:raise ValueError('Queue checksum mismatch')
        rows=json.loads(gzip.decompress(body))
        if len(rows)!=d['rows']:raise ValueError('Queue row count mismatch')
        return rows
    meta=load(base_d)[0];source=records();audit=flags();flag_rows=[]
    for cin,flag in sorted(audit.items()):
        entry=source[cin]
        if entry['master']['status']!='Active' or details(cin)['registered_activity_status']=='multiple_candidates':raise ValueError('Overlay expects Active cases outside the multiple-candidate base queue')
        if flag['source_sha256']!=entry['source_sha256'] or flag['source_url']!=entry['source_url']:raise ValueError('Flag source evidence changed; re-review required')
        m=entry['master'];flag_rows.append(dict(flag,queue_row=[cin,m['name'],m['state'],m['industry'],m['paid_up_capital']]))
    rows=[]
    for d in meta['chunks']:rows.extend(load(d))
    if len(rows)!=meta['total'] or any(row[0] in audit for row in rows):raise ValueError('Invalid queue overlay membership')
    def key(row):return (row[4] is None,-(row[4] or 0),row[0])
    remaining=[key(row) for row in rows[meta['described']:]]
    if remaining!=sorted(remaining):raise ValueError('Base capital order changed')
    positions={p['priority_index']:p for p in meta['capital_placements']};positive=[]
    for index,row in enumerate(rows[:meta['described']]):positive.append({'kind':'base','index':index,'base_before':positions[index]['base_before'],'key':key(row)})
    for flag in flag_rows:positive.append({'kind':'flag','cin':flag['cin'],'base_before':bisect.bisect_left(remaining,key(flag['queue_row'])),'key':key(flag['queue_row'])})
    positive.sort(key=lambda item:item['key']);sources=[{k:v for k,v in item.items() if k in ('kind','index','cin')} for item in positive];placements=[{'rank':item['base_before']+i,'priority_index':i,'base_before':item['base_before']} for i,item in enumerate(positive)]
    assert [s['index'] for s in sources if s['kind']=='base']==list(range(meta['described']))
    overlay={'base_total':meta['total'],'base_described':meta['described'],'base_manifest_sha256':base_d['sha256'],'added':len(flag_rows),'sources':sources,'capital_placements':placements}
    data=[{'schema_version':1,'source_data_commit':catalog['data_commit'],'flags':flag_rows,'queue_overlay':overlay,'notice':'Audit flags need fresh primary evidence. They do not confirm an error, select a NIC edition, or mark a company reviewed.'}];body=gzip.compress(json.dumps(data,ensure_ascii=False,separators=(',',':')).encode(),mtime=0);sha=hashlib.sha256(body).hexdigest();name='activity-review-flags-'+sha[:12]+'.json.gz';(static/name).write_bytes(body);d={'schema_version':1,'source_data_commit':catalog['data_commit'],'path':'/static/'+name,'rows':1,'bytes':len(body),'sha256':sha,'companies':len(flag_rows)};catalog['activity_review_flags']=d;(folder/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,separators=(',',':')))
    report={'base_multiple_candidate_companies':meta['total'],'audit_flagged_companies':len(flag_rows),'total_queue_companies':meta['total']+len(flag_rows),'source_described':meta['described']+len(flag_rows),'overlay_bytes':len(body),'base_queue_assets_rewritten':0,'primary_checks_completed':0};(folder/'activity-improvement-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
