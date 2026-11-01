"""Build a small, exact listed-company query index from the existing release."""
import gzip,hashlib,json,sqlite3,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
root=Path(__file__).resolve().parents[1];catalog_path=root/'deployment/national/catalog.json';catalog=json.loads(catalog_path.read_text());listing_index=catalog['index_fields'].index('effective_listing');listed_id=catalog['dictionaries']['effective_listing'].index('listed');cins=[]
for descriptor in catalog['global_chunks']:
    rows=json.loads(gzip.decompress((root/'deployment/national'/descriptor['path']).read_bytes()))
    cins.extend(row[0] for row in rows if row[listing_index]==listed_id)
assert len(cins)==len(set(cins))==catalog['stats']['summary']['listed']
values=[];below=0
with sqlite3.connect(root/'instance/india-online.sqlite') as db:
    for cin in cins:
        row=json.loads(db.execute('SELECT payload FROM records WHERE cin=?',(cin,)).fetchone()[0]);assert row['effective_listing']=='listed';values.append([row.get(field) for field in catalog['full_fields']])
        if row['paid_up_capital'] is not None and row['paid_up_capital']<10000000:below+=1
body=gzip.compress(json.dumps(values,ensure_ascii=False,separators=(',',':')).encode(),compresslevel=9,mtime=0);digest=hashlib.sha256(body).hexdigest();folder=root/'instance/build/listed-index';folder.mkdir(parents=True,exist_ok=True);filename='listed-'+digest[:12]+'.json.gz';(folder/filename).write_bytes(body)
manifest={'path':filename,'sha256':digest,'rows':len(values),'bytes':len(body),'source_data_commit':catalog['data_commit'],'full_fields':catalog['full_fields'],'listed_below_1cr':below}
(folder/'manifest.json').write_text(json.dumps(manifest,separators=(',',':')))
print(json.dumps(manifest))
