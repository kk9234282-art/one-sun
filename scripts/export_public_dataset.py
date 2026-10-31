"""Publish the authorised current company records; exclude accounts and private state."""
import csv
import hashlib
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from flask import g,render_template
from intelligence import create_app
from intelligence.db import get_db
from intelligence.analytics import directory,overview
from intelligence.sources import SOURCES


def main():
    root=Path(__file__).resolve().parents[1]
    target=root/'deployment';data_path=target/'data'
    data_path.mkdir(parents=True,exist_ok=True)
    app=create_app()
    with app.app_context():
        db=get_db();cursor,count=directory(db,{},export=True)
        # Explicit allowlist: never export users, password hashes, sessions or local paths.
        fields=['cin','name','class','registered_class','category','subcategory','status','incorporated',
                'address','state','district','industry','nic','roc','postal_code','authorised_capital',
                'paid_up_capital','effective_listing','source_id','as_of']
        rows=[[row[field] for field in fields] for row in cursor]
        stats=overview(db,{})
        datasets=[{key:d[key] for key in ('title','scope','date_basis','provenance','as_of','inserted','updated','rejected')}
                  for d in stats['datasets']]
        manifest={'schema_version':1,'publication_mode':'authorised-public-dataset','record_count':count,
                  'scope':datasets,'financial_records':db.execute('SELECT COUNT(*) FROM financials').fetchone()[0],
                  'notice':'User authorised publication of all uploaded company data. Original publisher and source date not independently verified.'}
        if manifest['financial_records']:
            raise ValueError('Financial export requires a separate reviewed schema; do not silently omit statements')
        source_ids={row[fields.index('source_id')] for row in rows}
        sources=[{'id':source,'name':SOURCES[source]['name'],'url':SOURCES[source]['url'],
                  'mode':SOURCES[source]['mode'],'status':'uploaded','checked_at':None,
                  'message':'Published from the user-supplied dataset; not independently certified.',
                  'note':SOURCES[source]['note']} for source in sorted(source_ids)]
        payload={'manifest':manifest,'fields':fields,'rows':rows,'sources':sources,'datasets':datasets}
        content=json.dumps(payload,ensure_ascii=False,separators=(',',':'),allow_nan=False)
        (data_path/'companies.json').write_text(content,encoding='utf-8')
        manifest['data_sha256']=hashlib.sha256(content.encode()).hexdigest()
        (data_path/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        # Original nonstandard CIN rows remain separate from the searchable valid records.
        rejection_source=root/'instance/reports/import-1-rejected.csv'
        if rejection_source.exists():
            (data_path/'cin-exceptions.csv').write_text(rejection_source.read_text(encoding='utf-8'),encoding='utf-8')
    with app.test_request_context('/'):
        g.user={'username':'Public dataset','role':'analyst'}
        output=render_template('index.html',sources=SOURCES,public_snapshot=True)
        (target/'index.html').write_text(output,encoding='utf-8')
    print(f'Exported {count:,} current companies, {len(content.encode()):,} JSON bytes. No database or account tables exported.')


if __name__=='__main__':main()
