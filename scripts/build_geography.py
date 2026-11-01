"""Add reconciled geographic counts and PIN sidecars for the default national list."""
from collections import Counter,defaultdict
import gzip,hashlib,json,sqlite3,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from intelligence.locality import derive,area,reference
root=Path('deployment/cities');catalog=json.loads(Path('deployment/national/catalog.json').read_text());manifest=json.loads((root/'manifest.json').read_text())
def groups(counts):return [{'label':label,'count':count} for label,count in sorted(counts.items(),key=lambda pair:(-pair[1],pair[0]))]
def write(path,body):
 digest=hashlib.sha256(body).hexdigest();path=path.format(digest=digest[:12]);target=root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body)
 return {'path':path,'sha256':digest,'bytes':len(body)}
manifest['area_reference']=reference()['area_source'];reuse='--reuse-global' in sys.argv and bool(manifest.get('global_chunks'));
if not reuse:manifest['global_chunks']={}
for number,(state,descriptor) in enumerate(manifest['states'].items()):
 data=json.loads((root/descriptor['path']).read_text());districts=Counter();areas=Counter();by_district=defaultdict(Counter)
 for mapping in data['chunks'].values():
  for _,_,pin in json.loads(gzip.decompress((root/mapping['path']).read_bytes())):
   district=derive(pin,state) or 'Not identified';label=area(pin,state) or 'Not identified';districts[district]+=1;areas[label]+=1;by_district[district][label]+=1
 data['geography']={'district':groups(districts),'postal_city':groups(areas)};data['areas_by_district']={district:groups(counts) for district,counts in sorted(by_district.items())}
 assert sum(districts.values())==descriptor['total']
 body=json.dumps(data,ensure_ascii=False,separators=(',',':')).encode();manifest['states'][state]={**descriptor,**write(f'states/{number:02d}-{{digest}}.json',body)}
 print(state,'geographic counts ready',flush=True)
if not reuse:
 with sqlite3.connect('instance/india-online.sqlite') as db:
  cursor=db.execute("SELECT cin,json_extract(payload,'$.postal_code') FROM records ORDER BY name COLLATE NOCASE,cin")
  for number,descriptor in enumerate(catalog['global_chunks']):
   rows=cursor.fetchmany(descriptor['rows']);assert len(rows)==descriptor['rows']
   body=gzip.compress(json.dumps([pin for _,pin in rows],separators=(',',':')).encode(),compresslevel=9,mtime=0)
   result=write(f'global/{number:04d}-{{digest}}.json.gz',body);result.update(rows=len(rows),cin_order_sha256=hashlib.sha256('\n'.join(cin for cin,_ in rows).encode()).hexdigest());manifest['global_chunks'][descriptor['path']]=result
  assert not cursor.fetchone()
(root/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,separators=(',',':')))
print('Global PIN sidecars and geographic metadata complete',flush=True)
