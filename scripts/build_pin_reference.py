"""Reduce a pinned MIT-licensed postal dataset to unambiguous state/PIN districts.

Only JSON is read; no third-party package code is installed or executed.
"""
import base64,gzip,hashlib,io,json,re,tarfile,urllib.request
from collections import defaultdict
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from intelligence.locality import canonical

URL='https://registry.npmjs.org/india-pincode/-/india-pincode-2.5.9.tgz'
INTEGRITY='6d9zSwJvxLTSFlJs2ges1tAozW4oZVDgiFwWDUfJeOqHf1N1154J1K/I4LyWSnIxawWRPv8U2RX4NIo4rBDKNQ=='
root=Path(__file__).resolve().parents[1];archive=root/'instance/build/pin-package/source.tgz'
if not archive.exists():
    archive.parent.mkdir(parents=True,exist_ok=True)
    archive.write_bytes(urllib.request.urlopen(URL,timeout=60).read())
body=archive.read_bytes()
assert base64.b64encode(hashlib.sha512(body).digest()).decode()==INTEGRITY,'Postal source integrity mismatch'
with tarfile.open(fileobj=io.BytesIO(body),mode='r:gz') as source:
    data=gzip.decompress(source.extractfile('package/data/pincodes.json.gz').read())
rows=json.loads(data);groups=defaultdict(set)
for row in rows:
    state=canonical(row['s']);district=' '.join(row['i'].split()).title();pin=str(row['p'])
    if state in ('','na') or district.lower() in ('','na','n/a','unknown') or not re.fullmatch('[1-9][0-9]{5}',pin):continue
    groups[(state,pin)].add(district)
states=defaultdict(dict);ambiguous=0
for (state,pin),labels in sorted(groups.items()):
    if len(labels)==1:states[state][pin]=next(iter(labels))
    else:ambiguous+=1
result={'schema_version':1,'source':{'name':'india-pincode','version':'2.5.9','author':'Deepak Kumar','license':'MIT','url':URL,'integrity':'sha512-'+INTEGRITY,'data_sha256':hashlib.sha256(data).hexdigest(),'reference_date':'Package published 2026-03-16; underlying postal record date is not specified.','notice':'Third-party postal reference. District labels are not municipal city boundaries. Ambiguous state/PIN pairs are withheld.'},'ambiguous_pairs':ambiguous,'states':dict(states)}
target=root/'intelligence/static/pin-districts.json';target.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')))
print(json.dumps({'states':len(states),'pairs':sum(map(len,states.values())),'ambiguous_pairs':ambiguous,'bytes':target.stat().st_size}))
