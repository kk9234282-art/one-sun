"""CIN registration-code candidates, explicitly separate from verified operations."""
import gzip,hashlib,json,re
from functools import lru_cache
from pathlib import Path
REFERENCE=Path(__file__).parent/'data/cin-activity-reference.json'
@lru_cache(maxsize=1)
def reference():return json.loads(REFERENCE.read_text())

def candidates(code):
    if not re.fullmatch(r'\d{5}',code):return []
    result=[]
    for edition,rows in reference()['references'].items():
        match=code if code in rows else None
        # Zero-padded historical codes can preserve a class or group, not a subclass.
        if not match and code.endswith('0') and code[:4] in rows:match=code[:4]
        if not match and code.endswith('00') and code[:3] in rows:match=code[:3]
        if match:result.append({'edition':edition,'reference_code':match,'level':len(match),'description':rows[match]})
    return result

def details(cin):
    code=cin[1:6] if re.fullmatch(r'[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}',cin or '') else None
    meanings=candidates(code) if code else []
    state='multiple_candidates' if len(meanings)>1 else 'reference_candidate' if meanings else 'unmapped'
    text=' | '.join('NIC '+r['edition']+': '+r['description']+(' (broad '+str(r['level'])+'-digit match)' if r['level']<5 else '') for r in meanings)
    return {'registered_activity_code':code,'registered_activity':text or 'Code meaning unresolved','registered_activity_candidates':meanings,'registered_activity_status':state}

def matches(cin,query,status):
    info=details(cin)
    return int((not status or info['registered_activity_status']==status) and (not query or query.casefold() in info['registered_activity'].casefold()))

@lru_cache(maxsize=1)
def dataset():
    root=Path(__file__).parent/'static';m=json.loads((root/'cin-activity-manifest.json').read_text());body=(root/Path(m['path']).name).read_bytes()
    if hashlib.sha256(body).hexdigest()!=m['sha256']:raise ValueError('CIN activity checksum mismatch')
    return json.loads(gzip.decompress(body))[0]

def options():
    return [{'value':code,'label':code+' · '+(row['label'][:180] if row['candidates'] else 'Code meaning unresolved')} for code,row in dataset()['codes'].items() if row['active_stats']['summary']['companies']]
