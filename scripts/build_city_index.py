"""Build small locality-ID sidecars aligned with immutable national state indices."""
from collections import Counter
import gzip,hashlib,json,sqlite3,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from intelligence.locality import derive

root=Path('deployment/cities');root.mkdir(parents=True,exist_ok=True)
country=json.loads(Path('deployment/national/catalog.json').read_text())
manifest={'schema_version':1,'source_data_commit':country['data_commit'],'policy':'Literal city/locality labels extracted from a consistent registered-address tail, with matching state and source PIN. Not independently verified cities or geocoding. Spelling variants are retained; ambiguous addresses are Not identified.','states':{},'matched':0,'unknown':0}
with sqlite3.connect('instance/india-online.sqlite') as db:
    for number,(state,definition) in enumerate(country['states'].items()):
        labels=[None];ids={None:0};counts=Counter();chunks={};batch=[];cins=[];chunk_number=0
        def flush():
            global chunk_number
            descriptor=definition['chunks'][chunk_number];assert len(batch)==descriptor['rows']
            body=gzip.compress(json.dumps(batch,separators=(',',':')).encode(),compresslevel=9,mtime=0);digest=hashlib.sha256(body).hexdigest()
            path=f'maps/{number:02d}/{chunk_number:04d}-{digest[:12]}.json.gz';target=root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body)
            chunks[descriptor['path']]={'path':path,'rows':len(batch),'sha256':digest,'bytes':len(body),'cin_order_sha256':hashlib.sha256('\n'.join(cins).encode()).hexdigest()}
            batch.clear();cins.clear();chunk_number+=1
        for (payload,) in db.execute('SELECT payload FROM records WHERE state=? ORDER BY name COLLATE NOCASE,cin',(state,)):
            row=json.loads(payload);city=derive(row.get('address'),row.get('state'),row.get('postal_code'))
            if city not in ids:ids[city]=len(labels);labels.append(city)
            value=ids[city];counts[value]+=1;batch.append(value);cins.append(row['cin'])
            if len(batch)==10000:flush()
        if batch:flush()
        assert chunk_number==len(definition['chunks'])
        state_data={'state':state,'labels':labels,'counts':[counts[i] for i in range(len(labels))],'chunks':chunks,'source_data_commit':country['data_commit'],'policy':manifest['policy']}
        body=json.dumps(state_data,ensure_ascii=False,separators=(',',':')).encode();digest=hashlib.sha256(body).hexdigest();path=f'states/{number:02d}-{digest[:12]}.json';target=root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body)
        total=sum(counts.values());matched=total-counts[0]
        manifest['states'][state]={'path':path,'sha256':digest,'bytes':len(body),'total':total,'matched':matched,'unknown':counts[0],'labels':len(labels)-1}
        manifest['matched']+=matched;manifest['unknown']+=counts[0]
        print(state,':',matched,'address localities,',counts[0],'unidentified;',len(labels)-1,'labels',flush=True)
assert manifest['matched']+manifest['unknown']==country['record_count']
(root/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
print('City sidecars bytes',sum(path.stat().st_size for path in root.rglob('*') if path.is_file()),flush=True)
