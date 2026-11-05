"""Manual activity reviews: evidence and identity claims stay separate from source data."""
import json,re
from datetime import date,datetime
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

FIELDS=('description','tags','source_url','source_kind','source_date','review_date','source_excerpt','identity_basis','status')
def validate(value):
    if not isinstance(value,dict):raise ValueError('A review object is required')
    out={key:value.get(key,'') for key in FIELDS}
    for key in FIELDS:
        if key!='tags':
            if not isinstance(out[key],str):raise ValueError('Review fields must be text')
            out[key]=out[key].strip()
    if not 20<=len(out['description'])<=3000:raise ValueError('Business description must contain 20–3,000 characters')
    tags=out['tags']
    if not isinstance(tags,list) or not 1<=len(tags)<=20 or any(not isinstance(t,str) or not 1<=len(t.strip())<=80 for t in tags):raise ValueError('Add 1–20 activity tags, each up to 80 characters')
    out['tags']=list(dict.fromkeys(t.strip() for t in tags))
    url=urlsplit(out['source_url'])
    if len(out['source_url'])>2000 or url.scheme not in ('https','http') or not url.hostname or url.username or url.password:raise ValueError('Use a complete HTTP or HTTPS source link without credentials')
    if out['source_kind'] not in ('company_website','annual_report','filing','other'):raise ValueError('Choose a source type')
    if out['identity_basis'] not in ('cin_in_source','name_and_address','name_only'):raise ValueError('Choose how the company identity was checked')
    if out['status'] not in ('reviewed','needs_review'):raise ValueError('Choose a review status')
    if not 10<=len(out['source_excerpt'])<=3000:raise ValueError('Include a source excerpt of 10–3,000 characters')
    today=datetime.now(ZoneInfo('Asia/Kolkata')).date()
    for key in ('review_date','source_date'):
        if key=='source_date' and not out[key]:continue
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',out[key]):raise ValueError('Use a valid review/source date')
        try:parsed=date.fromisoformat(out[key])
        except ValueError:raise ValueError('Use a valid review/source date') from None
        if parsed>today:raise ValueError('Review/source dates cannot be in the future')
    if out['source_date'] and out['source_date']>out['review_date']:raise ValueError('Source date cannot be after the review date')
    return out

def history(db,cin):
    rows=db.execute('SELECT r.version,r.payload,r.saved_at,u.username AS reviewer FROM activity_reviews r JOIN users u ON u.id=r.reviewer_id WHERE cin=? ORDER BY version DESC LIMIT 20',(cin,)).fetchall()
    return [json.loads(row['payload'])|{'version':row['version'],'saved_at':row['saved_at'],'reviewer':row['reviewer']} for row in rows]
