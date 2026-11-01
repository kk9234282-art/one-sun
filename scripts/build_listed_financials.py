"""Validate a real financial export and prepare its publishable static overlay.

No invented rows or network scraping. Run with an authorised source CSV.
"""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from intelligence.financial_data import build

def main():
    parser=argparse.ArgumentParser();parser.add_argument('csv',type=Path);args=parser.parse_args();root=Path(__file__).resolve().parents[1];catalog=json.loads((root/'deployment/national/catalog.json').read_text());listed_manifest=json.loads((root/'instance/build/listed-index/manifest.json').read_text());assert listed_manifest['source_data_commit']==catalog['data_commit']
    values=json.loads(gzip.decompress((root/'instance/build/listed-index'/listed_manifest['path']).read_bytes()));cin_column=catalog['full_fields'].index('cin');listed={row[cin_column] for row in values if row[catalog['full_fields'].index('status')]=='Active' and row[catalog['full_fields'].index('effective_listing')]=='listed'};rows,report=build(args.csv,listed)
    output=root/'instance/build/listed-financials';output.mkdir(parents=True,exist_ok=True);(output/'validation-report.json').write_text(json.dumps(report,indent=2))
    if report['rejected_rows']:raise SystemExit(f"{report['rejected_rows']} rows rejected. Review validation-report.json; no financial dataset was prepared.")
    if not rows:raise SystemExit('No valid real statements supplied; no dataset prepared.')
    body=gzip.compress(json.dumps(rows,separators=(',',':'),allow_nan=False).encode(),compresslevel=9,mtime=0);sha=hashlib.sha256(body).hexdigest();name='financials-'+sha[:12]+'.json.gz';(output/name).write_bytes(body)
    manifest={'schema_version':1,'path':name,'rows':len(rows),'sha256':sha,'bytes':len(body),'source_data_commit':catalog['data_commit'],'covered_companies':report['covered_companies'],'input_sha256':report['input_sha256'],'latest_publication_date':max(row['as_of'] for row in rows)};(output/'manifest.json').write_text(json.dumps(manifest,separators=(',',':')))
    print(json.dumps(manifest))
if __name__=='__main__':main()
