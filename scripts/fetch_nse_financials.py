"""Download public linked annual XBRL; match issuer-declared symbol/ISIN/CIN.

Inputs are NSE's public export CSVs and the cached BRSR identity report.
There are no guessed endpoints, credentials, name matches or challenge workarounds.
"""
import csv,hashlib,json,re,sys,threading,time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime
from pathlib import Path
import requests
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from intelligence.nse_financials import parse_annual,xml_root
from intelligence.financial_data import normalize
ROOT=Path(__file__).resolve().parents[1];FOLDER=ROOT/'instance/build/nse-financials';CACHE=FOLDER/'financial-xml';CACHE.mkdir(parents=True,exist_ok=True)

def stamp(text):
    for fmt in ('%d-%b-%Y %H:%M:%S','%d-%b-%Y'):
        try:return datetime.strptime(text,fmt)
        except ValueError:pass
    raise ValueError('Invalid exchange publication timestamp')

def main():
    catalog=json.loads((ROOT/'deployment/national/catalog.json').read_text());listed_meta=json.loads((ROOT/'instance/build/listed-index/manifest.json').read_text());import gzip
    listed_values=json.loads(gzip.decompress((ROOT/'instance/build/listed-index'/listed_meta['path']).read_bytes()));listed={row[catalog['full_fields'].index('cin')] for row in listed_values}
    identities=json.loads((FOLDER/'issuer-identities.json').read_text());pairs=defaultdict(list)
    for row in identities:
        if row.get('cin') in listed and re.fullmatch(r'[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}',row['cin']):pairs[(row['symbol'],row['isin'])].append(row)
    crosswalk={pair:rows[0] for pair,rows in pairs.items() if len({row['cin'] for row in rows})==1};symbols={pair[0] for pair in crosswalk};selected={};metadata_rejects=[]
    for market in ('equities','sme'):
        path=FOLDER/f'integrated-{market}-2026.csv'
        if not path.exists():continue
        for raw in csv.DictReader(path.open(encoding='utf-8-sig')):
            row={key.strip():value for key,value in raw.items()}
            if row.get('SYMBOL') not in symbols:continue
            if row.get('QUARTER END DATE','').upper()!='31-MAR-2026' and row.get('AUDITED / UNAUDITED')!='Audited':continue
            try:
                published=stamp(row['EXCHANGE DISSEMINATION TIME']);basis={'Standalone':'standalone','Consolidated':'consolidated'}[row['CONSOLIDATED / STANDALONE']];url=row['XBRL']
                if not url.startswith('https://nsearchives.nseindia.com/corporate/xbrl/'):raise ValueError('Unsupported filing link')
                item={'symbol':row['SYMBOL'],'basis':basis,'url':url,'published':published.date().isoformat(),'timestamp':published.isoformat(),'period_hint':row['QUARTER END DATE']}
                key=(item['symbol'],basis,item['period_hint'])
                if key not in selected or item['timestamp']>selected[key]['timestamp']:selected[key]=item
            except (ValueError,KeyError) as error:metadata_rejects.append({'symbol':row.get('SYMBOL'),'reason':str(error)})
    jobs=sorted(selected.values(),key=lambda row:(row['symbol'],row['basis'],row['timestamp']),reverse=True);stop=threading.Event()
    def fetch(item):
        path=CACHE/(hashlib.sha256(item['url'].encode()).hexdigest()+'.xml')
        try:
            if stop.is_set():raise ValueError('Stopped after access/rate denial')
            if path.exists():body=path.read_bytes()
            else:
                response=requests.get(item['url'],timeout=(10,35),verify='/etc/ssl/certs/ca-certificates.crt',allow_redirects=False)
                if response.status_code in (401,403,429):stop.set();raise ValueError('Access/rate denial HTTP '+str(response.status_code))
                response.raise_for_status();body=response.content;xml_root(body);path.write_bytes(body);time.sleep(0.15)
            rows=parse_annual(body,item,crosswalk)
            for row in rows:normalize(row,listed)
            return {'filing':item,'source_sha256':hashlib.sha256(body).hexdigest(),'records':rows}
        except Exception as error:return {'filing':item,'error':str(error)[:200]}
    print('Exact issuer pairs',len(crosswalk),'CINs',len({row['cin'] for row in crosswalk.values()}),'annual filing candidates',len(jobs),flush=True)
    results=[]
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures=[executor.submit(fetch,item) for item in jobs]
        for number,future in enumerate(as_completed(futures),1):
            results.append(future.result())
            if number%100==0:print('Annual filings processed',number,'/',len(jobs),'parsed',sum('records' in row for row in results),flush=True)
    (FOLDER/'financial-fetch-report.json').write_text(json.dumps({'source_page':'https://www.nseindia.com/companies-listing/corporate-integrated-filing','source_company_commit':catalog['data_commit'],'identity_pairs':len(crosswalk),'filings':results,'metadata_rejects':metadata_rejects,'access_stop':stop.is_set()},separators=(',',':')))
    chosen={};conflicts=[]
    for result in results:
        for row in result.get('records',[]):
            key=(row['cin'],row['financial_year'],row['reporting_type']);timestamp=result['filing']['timestamp'];previous=chosen.get(key)
            if previous and previous[0]==timestamp and previous[1]!=row:conflicts.append(key)
            if not previous or timestamp>previous[0]:chosen[key]=(timestamp,row)
    if conflicts:raise SystemExit('Conflicting same-time statement facts: '+str(conflicts[:5]))
    output=FOLDER/'annual-financials.csv';fields=['cin','financial_year','reporting_type','unit','period_end','period_months','revenue','revenue_metric','net_profit','assets','liabilities','expenses','ebitda','source_id','source_url','as_of']
    with output.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(row for _,row in sorted(chosen.values(),key=lambda value:(value[1]['cin'],value[1]['financial_year'],value[1]['reporting_type'])))
    print('Annual download complete',len(chosen),'statements;',len({row['cin'] for _,row in chosen.values()}),'companies; failures',sum('error' in row for row in results),'access_stop',stop.is_set(),flush=True)
if __name__=='__main__':main()
