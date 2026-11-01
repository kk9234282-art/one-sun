"""Add separately attributed postal-area labels; never treat them as verified city boundaries."""
import base64,hashlib,io,json,tarfile,urllib.request,re
from collections import defaultdict
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from intelligence.locality import canonical
root=Path(__file__).resolve().parents[1]
url='https://registry.npmjs.org/india-pincode-search/-/india-pincode-search-1.0.2.tgz'
integrity='67p748UqQzvL1eMKmnyQdl8hAu76luhFfJEY9dz8KGka5Wqj3XNn6tdN1W6/SWJJu/i/cZ1Dw3yH8Yi7UPXlOg=='
path=root/'instance/build/city-reference/source.tgz'
if not path.exists():
 path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(urllib.request.urlopen(url,timeout=60).read())
body=path.read_bytes();assert base64.b64encode(hashlib.sha512(body).digest()).decode()==integrity
with tarfile.open(fileobj=io.BytesIO(body),mode='r:gz') as archive:data=archive.extractfile('package/db/pincode_db.json').read()
groups=defaultdict(set)
for row in json.loads(data):
 pin=str(row.get('pincode',''));state=canonical(row.get('state'));area=' '.join(str(row.get('village') or '').split()).title()
 if not re.search('[A-Za-z]',area) or len(area)>100 or not re.fullmatch('[1-9][0-9]{5}',pin) or not state or area.lower() in ('','na','n/a','none','null','unknown','not available','not applicable'):continue
 groups[(state,pin)].add(area)
target=root/'intelligence/static/pin-districts.json';reference=json.loads(target.read_text());areas=defaultdict(dict)
for (state,pin),labels in sorted(groups.items()):
 if len(labels)==1 and pin in reference['states'].get(state,{}):areas[state][pin]=next(iter(labels))
reference['areas']=dict(areas)
reference['area_source']={'name':'india-pincode-search','version':'1.0.2','author':'Mayank Jhawar','license':'ISC (package manifest; README states MIT)','url':url,'integrity':'sha512-'+integrity,'data_sha256':hashlib.sha256(data).hexdigest(),'reference_date':'Package published 2023-03-01; underlying postal record date unspecified.','notice':'Source village field is a representative PIN postal-area label, not a verified municipal city or exact company location. Conflicting labels and unresolved districts withheld.'}
target.write_text(json.dumps(reference,ensure_ascii=False,separators=(',',':')))
print('Postal area labels:',sum(map(len,areas.values())))
