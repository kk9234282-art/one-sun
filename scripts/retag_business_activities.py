"""Refresh research tags only. Preserve all company, source and identity evidence fields."""
import gzip,hashlib,json,sys
from collections import Counter
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from intelligence.business_activity import tags_for,TAG_RULE_VERSION,TAG_POLICY
ROOT=Path(__file__).resolve().parents[1]
def main():
    static=ROOT/'intelligence/static';folder=ROOT/'deployment/national';manifest=static/'business-activity-manifest.json';d=json.loads(manifest.read_text());old=static/Path(d['path']).name;body=old.read_bytes()
    if hashlib.sha256(body).hexdigest()!=d['sha256']:raise ValueError('Business activity checksum mismatch')
    data=json.loads(gzip.decompress(body))[0];counts=Counter();changed=[]
    for row in data['records']:
        previous=row['tags'];current=tags_for(row['description'])
        if previous!=current:changed.append({'cin':row['cin'],'company_name':row['company_name'],'before':previous,'after':current})
        row['tags']=current;counts.update(current)
    data['report']['activity_tags']=dict(sorted(counts.items()));data['report']['tag_rule_version']=TAG_RULE_VERSION;data['report']['tag_policy']=TAG_POLICY
    body=gzip.compress(json.dumps([data],ensure_ascii=False,separators=(',',':')).encode(),mtime=0);sha=hashlib.sha256(body).hexdigest();name='business-activities-'+sha[:12]+'.json.gz';(static/name).write_bytes(body);d.update(path='/static/'+name,sha256=sha,bytes=len(body),tags=sorted(counts));manifest.write_text(json.dumps(d,indent=2)+'\n');catalog=json.loads((folder/'catalog.json').read_text());catalog['business_activities']=d;(folder/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,separators=(',',':')));(folder/'business-activity-report.json').write_text(json.dumps(data['report'],indent=2)+'\n')
    (ROOT/'work/activity-improvements').mkdir(parents=True,exist_ok=True)
    (ROOT/'work/activity-improvements/tag-changes.json').write_text(json.dumps(changed,ensure_ascii=False,indent=2))
    if old.name!=name:old.unlink()
    print('Records preserved:',len(data['records']),'changed tag sets:',len(changed),'available tags:',len(counts),'compressed bytes:',len(body),flush=True)
if __name__=='__main__':main()
