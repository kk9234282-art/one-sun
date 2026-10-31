"""Archive and import a user-supplied company file with explicit coverage metadata."""
import argparse
import csv
import hashlib
import json
import shutil
import sys
from collections import Counter
from pathlib import Path
import sqlite3

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from intelligence import create_app
from intelligence.db import get_db
from intelligence.ingest import ingest, header, normalize
from intelligence.analytics import overview


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path',type=Path)
    parser.add_argument('--as-of',required=True)
    parser.add_argument('--title',required=True)
    parser.add_argument('--scope',required=True)
    parser.add_argument('--date-basis',required=True)
    args=parser.parse_args()
    app=create_app()
    root=Path(app.instance_path)
    archive=root/'datasets';reports=root/'reports';backups=root/'backups'
    for directory in (archive,reports,backups):directory.mkdir(exist_ok=True,mode=0o700)
    with args.path.open('rb') as original:
        digest=hashlib.file_digest(original,'sha256').hexdigest()
    preserved=archive/(digest+args.path.suffix.lower())
    if not preserved.exists():
        shutil.copyfile(args.path,preserved);preserved.chmod(0o600)
    with preserved.open('rb') as f:
        if hashlib.file_digest(f,'sha256').hexdigest()!=digest:
            raise ValueError('Archived source checksum does not match')
    with app.app_context():
        db=get_db()
        backup=backups/f'before-{digest[:16]}.sqlite'
        if not backup.exists():
            with sqlite3.connect(backup) as target:db.backup(target)
            backup.chmod(0o600)
        result=ingest(db,args.path,'companies','user_upload',args.as_of)
        if result['status']=='failed':
            print(json.dumps(result,indent=2));raise SystemExit(1)
        db.execute('INSERT OR IGNORE INTO import_annotations VALUES(?,?,?,?,?,?,?)',
                   (result['id'],args.title,args.scope,args.date_basis,
                    'User-supplied file; original publisher and publication date not independently verified.',
                    digest,str(preserved)))
        db.commit()
        rejected_path=reports/f"import-{result['id']}-rejected.csv"
        count=0;valid=0;ids=Counter();breakdowns={key:Counter() for key in ('state','industry','class','registered_class','status','listing_status')}
        with args.path.open(encoding='utf-8-sig',newline='') as source,rejected_path.open('w',encoding='utf-8',newline='') as out:
            reader=csv.DictReader(source)
            writer=csv.DictWriter(out,fieldnames=['source_line','validation_error']+reader.fieldnames);writer.writeheader()
            for line,row in enumerate(reader,2):
                try:
                    n=normalize({header(k):v for k,v in row.items()},'companies','user_upload')
                    valid+=1;ids[n['cin']]+=1
                    for key,counter in breakdowns.items():counter[n.get(key,'Unknown')]+=1
                except (ValueError,TypeError) as e:
                    writer.writerow({'source_line':line,'validation_error':str(e)}|row);count+=1
        rejected_path.chmod(0o600)
        summary={'title':args.title,'scope':args.scope,'date_basis':args.date_basis,
                 'original_filename':args.path.name,'sha256':digest,'import':result,
                 'valid_file_rows':valid,'rejected_file_rows':count,'unique_valid_cins':len(ids),
                 'duplicate_valid_cin_rows':sum(v-1 for v in ids.values()),
                 'file_distributions':{key:dict(v) for key,v in breakdowns.items()},
                 'database_summary_after_import':overview(db,{})['summary'],
                 'rejected_rows_file':str(rejected_path)}
        report=reports/f"import-{result['id']}-summary.json"
        report.write_text(json.dumps(summary,indent=2));report.chmod(0o600)
        print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
