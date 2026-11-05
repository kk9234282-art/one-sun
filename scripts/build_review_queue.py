"""Build a small paged review queue from existing, checksum-checked data only."""
import gzip,hashlib,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from intelligence.registered_activity import dataset as cin_dataset
from intelligence.business_activity import records
ROOT=Path(__file__).resolve().parents[1]
SIZE=500
BUCKETS=128
def bucket(cin):
    value=2166136261
    for char in cin:value=((value^ord(char))*16777619)&0xffffffff
    return value%BUCKETS

def cleanup(folder,written):
    for path in folder.glob('*.json.gz'):
        if path.name not in written and re.fullmatch(r'(?:page-\d{4,}|members-\d{3,}|manifest)-[a-f0-9]{12}\.json\.gz',path.name):path.unlink()

def build():
    folder=ROOT/'deployment/national';out=ROOT/'deployment/review-queue';out.mkdir(exist_ok=True);catalog=json.loads((folder/'catalog.json').read_text());refs=cin_dataset();described=records();codes={code for code,row in refs['codes'].items() if row['status']=='multiple_candidates'};fields=catalog['index_fields'];dictionaries=catalog['dictionaries'];rows=[]
    for d in catalog['global_chunks']:
        body=(folder/d['path']).read_bytes()
        if hashlib.sha256(body).hexdigest()!=d['sha256']:raise ValueError('Company chunk checksum mismatch')
        values=json.loads(gzip.decompress(body))
        if len(values)!=d['rows']:raise ValueError('Company chunk row count mismatch')
        for values in values:
            cin=values[0]
            if cin[1:6] not in codes:continue
            row={key:dictionaries[key][value] if key in dictionaries else value for key,value in zip(fields,values)}
            if row['status']=='Active':rows.append([cin,row['name'],row['state'],row['industry'],row['paid_up_capital']])
    def capital(row):return (row[4] is None,-(row[4] or 0),row[0])
    rows.sort(key=lambda row:(row[0] not in described,)+capital(row));count=sum(row[0] in described for row in rows);priority={row[0]:i for i,row in enumerate(rows)};placements=[]
    for rank,row in enumerate(sorted(rows,key=capital)):
        if row[0] in described:placements.append({'rank':rank,'priority_index':priority[row[0]],'base_before':rank-len(placements)})
    assert len(rows)==refs['report']['active_company_counts']['multiple_candidates']
    written=set()
    def asset(prefix,value):
        body=gzip.compress(json.dumps(value,ensure_ascii=False,separators=(',',':')).encode(),mtime=0);sha=hashlib.sha256(body).hexdigest();name=prefix+'-'+sha[:12]+'.json.gz';(out/name).write_bytes(body);written.add(name)
        return {'path':'/review-queue/'+name,'rows':len(value),'sha256':sha,'bytes':len(body)}
    chunks=[asset(f'page-{i//SIZE:04d}',rows[i:i+SIZE]) for i in range(0,len(rows),SIZE)];membership=[[] for _ in range(BUCKETS)]
    for i,row in enumerate(rows):membership[bucket(row[0])].append([row[0],i])
    maps=[asset(f'members-{i:03d}',sorted(value)) for i,value in enumerate(membership)]
    metadata={'schema_version':1,'source_data_commit':catalog['data_commit'],'total':len(rows),'described':count,'chunk_size':SIZE,'bucket_count':BUCKETS,'chunks':chunks,'membership':maps,'capital_placements':placements};descriptor=asset('manifest',[metadata]);descriptor.update(schema_version=1,source_data_commit=catalog['data_commit'],total=len(rows));catalog['review_queue']=descriptor;(folder/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,separators=(',',':')))
    report={'total':len(rows),'with_source_description':count,'queue_chunks':len(chunks),'membership_chunks':len(maps),'manifest_bytes':descriptor['bytes'],'total_bytes':sum(d['bytes'] for d in chunks+maps)+descriptor['bytes'],'default_order':'Source description available first, then paid-up capital descending; unknown capital last; CIN tie-breaker','note':'Pending/checked progress comes from latest manual-review status, not from source-description availability.'};(folder/'review-queue-report.json').write_text(json.dumps(report,indent=2)+'\n');cleanup(out,written);print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':build()
