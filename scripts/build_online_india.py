"""Build verified, bounded-size compressed static indices from the released ZIP."""
import argparse
from collections import Counter,defaultdict
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import sys
import time
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from intelligence.ingest import header,normalize
from intelligence.analytics import INACTIVE_STATUSES

FULL_FIELDS=['cin','name','class','registered_class','category','subcategory','status','incorporated','address','state','registered_state','district','industry','nic','roc','postal_code','authorised_capital','paid_up_capital','effective_listing','source_id','as_of','source_file']
INDEX_FIELDS=['cin','name','class','registered_class','category','status','incorporated','state','industry','authorised_capital','paid_up_capital','effective_listing']
DICTIONARY_FIELDS=['class','registered_class','category','status','state','industry','effective_listing']
STATE_ALIASES={'Orissa':'Odisha','Pondicherry':'Puducherry','Jammu & Kashmir':'Jammu and Kashmir','Dadra & Nagar Haveli':'Dadra and Nagar Haveli and Daman and Diu','Daman And Diu':'Dadra and Nagar Haveli and Daman and Diu'}
EXPECTED_SHA='b6dfedff66c92f5eeff0caf5ea0b493c3cba00f6695413bd6a1c1b80fe0979dc'
SOURCE_URL='https://github.com/kk9234282-art/one-sun/releases/download/india-data-v1/company_master_data_2026-10-31.zip'
def compact(value):return json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False)
def bucket(cin):
    h=2166136261
    for byte in cin.encode('ascii'):h=((h^byte)*16777619)&0xffffffff
    return h%1024

class Stats:
    def __init__(self):
        self.summary=dict.fromkeys(['companies','active','inactive','other_status','private','public','listed','unlisted','unknown_listing','financial_coverage','llps','msmes','securities','unlinked_securities'],0)
        self.summary.update(oldest=None,newest=None)
        self.groups={key:Counter() for key in ['state','industry','class','status','effective_listing','trends','capital']}
    def add(self,row):
        s=self.summary;s['companies']+=1;s['active' if row['status']=='Active' else 'inactive' if row['status'] in INACTIVE_STATUSES else 'other_status']+=1
        if row['class']=='Private':s['private']+=1
        if row['class']=='Public':s['public']+=1
        s[row['effective_listing'] if row['effective_listing'] in ('listed','unlisted') else 'unknown_listing']+=1
        for key in ['state','industry','class','status','effective_listing']:self.groups[key][row[key] or 'Unknown']+=1
        if row['incorporated']:self.groups['trends'][row['incorporated'][:4]]+=1
        paid=row['paid_up_capital'];self.groups['capital']['Unknown' if paid is None else '< ₹1 crore' if paid<1e7 else '₹1–10 crore' if paid<1e8 else '≥ ₹10 crore']+=1
        date=row['as_of'];s['oldest']=min(s['oldest'] or date,date);s['newest']=max(s['newest'] or date,date)
    def output(self):return {'summary':self.summary,'groups':{key:[{'label':label,'count':count} for label,count in sorted(values.items(),key=(lambda pair:pair[0]) if key=='trends' else (lambda pair:(-pair[1],pair[0])))] for key,values in self.groups.items()}}

def ingest(archive,db,report_path):
    if db.execute("SELECT value FROM meta WHERE key='complete'").fetchone():return
    total=accepted=rejected=0;files=[];start=time.time()
    exceptions=report_path/'exceptions.csv';exceptions.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as z,exceptions.open('w',encoding='utf-8',newline='') as error_file:
        errors=csv.writer(error_file,lineterminator='\n');errors.writerow(['source_file','source_record','reason','original_record_json'])
        for member in z.infolist():
            if not member.filename.lower().endswith('.csv'):continue
            file_count=file_valid=file_rejected=0;batch=[]
            with z.open(member) as raw,io.TextIOWrapper(raw,encoding='utf-8-sig',newline='') as source:
                reader=csv.DictReader(source);names=[header(value) for value in reader.fieldnames]
                if len(names)!=len(set(names)) or not {'cin','name'}<=set(names):raise ValueError('Unsupported company CSV headers: '+member.filename)
                for record,original in enumerate(reader,2):
                    total+=1;file_count+=1
                    try:
                        if None in original:raise ValueError('Extra CSV columns')
                        row=normalize({header(key):value for key,value in original.items()},'companies','user_upload')
                        row['registered_state']=original.get('Company State')
                        row['state']=STATE_ALIASES.get(row.get('state'),row.get('state'))
                        row['effective_listing']=row.pop('listing_status',None) or 'unknown'
                        row.update(source_id='user_upload',as_of='2026-10-31',source_file=member.filename)
                        row={key:row.get(key) for key in FULL_FIELDS}
                        batch.append((row['cin'],row['name'],row['state'],row['industry'],compact(row),bucket(row['cin'])))
                        accepted+=1;file_valid+=1
                    except (ValueError,TypeError,OverflowError) as error:
                        rejected+=1;file_rejected+=1;errors.writerow([member.filename,record,str(error),compact(original)])
                    if len(batch)>=5000:
                        db.executemany('INSERT INTO records VALUES(?,?,?,?,?,?) ON CONFLICT(cin) DO UPDATE SET name=excluded.name,state=excluded.state,industry=excluded.industry,payload=excluded.payload,bucket=excluded.bucket',batch);db.commit();batch=[]
                    if total%250000==0:print(f'Validated {total:,} source rows ({time.time()-start:.1f}s)',flush=True)
            if batch:db.executemany('INSERT INTO records VALUES(?,?,?,?,?,?) ON CONFLICT(cin) DO UPDATE SET name=excluded.name,state=excluded.state,industry=excluded.industry,payload=excluded.payload,bucket=excluded.bucket',batch);db.commit()
            files.append({'name':member.filename,'source_rows':file_count,'valid_rows':file_valid,'rejected_rows':file_rejected,'zip_crc32':f'{member.CRC:08x}'})
    unique=db.execute('SELECT COUNT(*) FROM records').fetchone()[0]
    report={'source_url':SOURCE_URL,'source_sha256':EXPECTED_SHA,'source_rows':total,'valid_rows':accepted,'rejected_rows':rejected,'unique_companies':unique,'duplicate_valid_rows':accepted-unique,'files':files,'state_aliases':STATE_ALIASES,'notice':'User-supplied public release; source publication date and national completeness not independently verified. 2026-10-31 is the filename date label. Structurally valid identifiers are not proof of official registration.'}
    db.executemany('INSERT OR REPLACE INTO meta VALUES(?,?)',[('report',compact(report)),('complete','1')]);db.commit()
    print('Creating cache indices…',flush=True);db.executescript('CREATE INDEX IF NOT EXISTS records_name ON records(name COLLATE NOCASE,cin);CREATE INDEX IF NOT EXISTS records_state_name ON records(state,name COLLATE NOCASE,cin);CREATE INDEX IF NOT EXISTS records_bucket ON records(bucket,cin);')
    (report_path/'source-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--archive',default='instance/datasets/india-data-v1.zip');parser.add_argument('--cache',default='instance/india-online.sqlite');parser.add_argument('--output',default='deployment/national');args=parser.parse_args()
    archive=Path(args.archive)
    with archive.open('rb') as source:assert hashlib.file_digest(source,'sha256').hexdigest()==EXPECTED_SHA,'Release archive SHA-256 mismatch'
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(args.cache);db.row_factory=sqlite3.Row;db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=NORMAL')
    db.executescript('CREATE TABLE IF NOT EXISTS records(cin TEXT PRIMARY KEY,name TEXT NOT NULL,state TEXT,industry TEXT,payload TEXT NOT NULL,bucket INTEGER NOT NULL);CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);')
    ingest(archive,db,output)
    db.executescript('CREATE INDEX IF NOT EXISTS records_name ON records(name COLLATE NOCASE,cin);CREATE INDEX IF NOT EXISTS records_state_name ON records(state,name COLLATE NOCASE,cin);CREATE INDEX IF NOT EXISTS records_bucket ON records(bucket,cin);')
    report=json.loads(db.execute("SELECT value FROM meta WHERE key='report'").fetchone()[0])
    dictionaries={key:[None] for key in DICTIONARY_FIELDS};global_stats=Stats();states=defaultdict(Stats);industries=defaultdict(Stats);sets={key:set() for key in DICTIONARY_FIELDS};start=time.time()
    for n,record in enumerate(db.execute('SELECT payload FROM records'),1):
        row=json.loads(record[0]);global_stats.add(row);states[row['state'] or 'Unknown'].add(row);industries[row['industry'] or 'Unknown'].add(row)
        for key in sets:
            if row[key] is not None:sets[key].add(row[key])
        if n%500000==0:print(f'Aggregated {n:,} unique companies ({time.time()-start:.1f}s)',flush=True)
    for key in dictionaries:dictionaries[key].extend(sorted(sets[key]))
    ids={key:{value:i for i,value in enumerate(values)} for key,values in dictionaries.items()}
    def index_row(row):return [ids[key][row[key]] if key in ids else row[key] for key in INDEX_FIELDS]
    def write_gzip(relative,rows):
        body=compact(rows).encode('utf-8');compressed=gzip.compress(body,compresslevel=6,mtime=0);sha=hashlib.sha256(compressed).hexdigest();path=Path(relative);name=str(path.with_name(path.stem+'-'+sha[:12]+path.suffix+'.gz'))
        target=output/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(compressed)
        return {'path':name,'rows':len(rows),'bytes':len(compressed),'sha256':sha}
    def index_chunks(query,params,prefix):
        chunks=[];batch=[]
        for record in db.execute(query,params):
            batch.append(index_row(json.loads(record[0])))
            if len(batch)==10000:chunks.append(write_gzip(f'{prefix}/{len(chunks):04d}.json',batch));batch=[]
        if batch:chunks.append(write_gzip(f'{prefix}/{len(chunks):04d}.json',batch))
        return chunks
    catalog={'schema_version':2,'publication_mode':'authorised-public-dataset','record_count':report['unique_companies'],'as_of':'2026-10-31','index_fields':INDEX_FIELDS,'full_fields':FULL_FIELDS,'dictionaries':dictionaries,'source':report,'stats':global_stats.output(),'states':{},'industries':{label:stats.output() for label,stats in industries.items()},'profile_buckets':{},'datasets':[{'title':'All-India company master — user-supplied release','scope':f"{report['unique_companies']:,} unique structurally valid company CINs from {report['source_rows']:,} source rows. These are imported records, not a certified national census.",'date_basis':'2026-10-31 is the release filename date label; official publication date not independently verified.','provenance':f"Source: GitHub release india-data-v1. {report['rejected_rows']} rejected rows are preserved separately; {report['duplicate_valid_rows']} duplicate valid rows were reconciled. Company classes, source states and listing labels come from the supplied files."}]}
    print('Writing national name index…',flush=True)
    catalog['global_chunks']=index_chunks('SELECT payload FROM records ORDER BY name COLLATE NOCASE,cin',(),'index/all')
    for state,stats in sorted(states.items()):
        state_id=ids['state'].get(state,0);print('Writing state index:',state,flush=True)
        chunks=index_chunks('SELECT payload FROM records WHERE state IS ? ORDER BY name COLLATE NOCASE,cin',(None if state=='Unknown' else state,),f'index/states/{state_id}')
        catalog['states'][state]={'stats':stats.output(),'chunks':chunks}
    print('Writing bounded profile buckets…',flush=True)
    for bucket_id in range(1024):
        rows=[]
        for record in db.execute('SELECT payload FROM records WHERE bucket=? ORDER BY cin',(bucket_id,)):
            decoded=json.loads(record[0]);rows.append([decoded.get(key) for key in FULL_FIELDS])
        if rows:catalog['profile_buckets'][str(bucket_id)]=write_gzip(f'profiles/{bucket_id:04d}.json',rows)
    (output/'catalog.json').write_text(compact(catalog),encoding='utf-8')
    total_bytes=sum(path.stat().st_size for path in output.rglob('*') if path.is_file());assert total_bytes<750*1024*1024,'Static dataset exceeds the chosen free-deployment size budget; do not publish blindly'
    print(compact({'record_count':catalog['record_count'],'states':len(catalog['states']),'compressed_static_bytes':total_bytes,'rejected':report['rejected_rows'],'duplicates':report['duplicate_valid_rows']}),flush=True)
    db.close()

if __name__=='__main__':main()
