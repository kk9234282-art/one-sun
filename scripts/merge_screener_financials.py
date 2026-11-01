"""Merge verified additions into the existing immutable financial overlay."""
import csv,gzip,hashlib,json,sys
from collections import Counter
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from intelligence.financial_data import normalize
from intelligence.screener_financials import parse_annual
ROOT=Path(__file__).resolve().parents[1]

def main():
    catalog=json.loads((ROOT/'deployment/national/catalog.json').read_text());cache=ROOT/'instance/build/screener-financials';report=json.loads((cache/'fetch-report.json').read_text())
    if report['source_data_commit']!=catalog['data_commit'] or report['processed']!=report['candidates']:raise ValueError('Fetch must finish against the current company snapshot')
    records=[];reparse_errors=[]
    for result in report['results']:
        if not result.get('records'):continue
        first=result['records'][0];page=cache/(hashlib.sha256(first['source_url'].encode()).hexdigest()+'.body');html=page.read_bytes()
        if hashlib.sha256(html).hexdigest()!=result['page_sha256']:raise ValueError('Cached table checksum mismatch')
        try:records.extend(parse_annual(html.decode('utf-8'),cin=result['cin'],symbol=result['symbol'],year=max(r['financial_year'] for r in result['records']),published=first['as_of'],source_url=first['source_url'],identity_url=first['identity_source_url'],retrieved=first['source_retrieved_on']))
        except ValueError as error:reparse_errors.append({'symbol':result['symbol'],'error':str(error)})
    for row in records:row['source_precision']='Public INR crore table; displayed amounts may be rounded'
    descriptor=catalog['financials'];path=ROOT/'instance/build/listed-financials'/descriptor['path'].rsplit('/',1)[-1];body=path.read_bytes();assert hashlib.sha256(body).hexdigest()==descriptor['sha256'];previous=json.loads(gzip.decompress(body));covered={row['cin'] for row in previous}
    listed=catalog['listed_index'];values=json.loads(gzip.decompress((ROOT/'instance/build/listed-index'/listed['path'].rsplit('/',1)[-1]).read_bytes()));fields=catalog['full_fields'];active={row[fields.index('cin')] for row in values if row[fields.index('status')]=='Active' and row[fields.index('effective_listing')]=='listed'}
    if any(row['cin'] in covered for row in records):raise ValueError('Gap-fill must not replace existing company statements')
    added=[normalize(row,active) for row in records];keys=[(row['cin'],row['financial_year'],row['reporting_type']) for row in previous+added];assert len(keys)==len(set(keys))
    output=cache/'combined-annual-financials.csv';names=list(dict.fromkeys(key for row in previous+added for key in row))
    with output.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=names);writer.writeheader();writer.writerows(previous+added)
    def reason(error):
        if 'pdftotext' in error:return 'Unreadable annual-report PDF'
        if error.startswith('404 Client Error:'):return 'Public company page unavailable (HTTP 404)'
        return error
    summary={'source':'screener','scope':'Active listed companies without imported statements','candidates':report['candidates'],'completed_jobs':report['processed'],'attempted_companies':sum(not r.get('error','').startswith('Stopped after') for r in report['results']),'deferred_after_rate_or_access_stop':sum(r.get('error','').startswith('Stopped after') for r in report['results']),'new_companies':len({row['cin'] for row in added}),'new_annual_statements':len(added),'access_stop':report['access_stop'],'final_revalidation_exceptions':reparse_errors,'exceptions':dict(Counter(reason(result['error']) for result in report['results'] if 'error' in result)),'method':'Exact NSE legal-name matches discover candidates only. The target CIN must appear in the NSE-linked annual PDF, and the NSE symbol must match the public Screener company page. Explicit annual standalone tables only; TTM and ambiguous bases are excluded. Crore values are converted to INR; displayed precision is retained. as_of is the matching NSE annual-report dissemination date; table retrieval is stored separately. Only gaps are filled; existing NSE statements are preserved.'}
    (ROOT/'deployment/national/screener-source-report.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2));print('Combined CSV:',output)
if __name__=='__main__':main()
