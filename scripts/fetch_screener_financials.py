"""Fill Active listed gaps using public Screener annual tables and NSE report CINs.

Legal names discover candidates only. Every imported issuer requires the exact
CIN in its NSE annual-report PDF and the same NSE symbol on Screener. Stop on
access/rate denials, respect robots.txt, cache evidence, and never use TTM.
"""
import argparse,csv,gzip,hashlib,json,re,subprocess,sys,tempfile,threading,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import date,datetime
from pathlib import Path
from urllib.parse import quote,urlsplit
from urllib.robotparser import RobotFileParser
import requests
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from intelligence.screener_financials import parse_annual,Tables
from intelligence.financial_data import normalize
ROOT=Path(__file__).resolve().parents[1];CACHE=ROOT/'instance/build/screener-financials';CACHE.mkdir(parents=True,exist_ok=True)
STOP=threading.Event();GATE=threading.Lock();LAST={}

def fetch(url,*,pdf=False):
    global LAST
    key=hashlib.sha256(url.encode()).hexdigest();path=CACHE/(key+('.identity.json' if pdf else '.body'))
    if path.exists():return json.loads(path.read_text()) if pdf else path.read_bytes()
    if STOP.is_set():raise ValueError('Stopped after access/rate denial')
    if urlsplit(url).hostname not in ('www.nseindia.com','nsearchives.nseindia.com','www.screener.in','raw.githubusercontent.com'):raise ValueError('Unexpected source domain')
    with GATE:
        host=urlsplit(url).hostname;interval=2.0 if host=='www.screener.in' else .5
        delay=interval-(time.monotonic()-LAST.get(host,0))
        if delay>0:time.sleep(delay)
        LAST[host]=time.monotonic()
    with requests.get(url,timeout=(10,55),stream=True,allow_redirects=False,verify='/etc/ssl/certs/ca-certificates.crt') as response:
        if response.status_code in (401,403,429):STOP.set();raise ValueError('Access/rate denial HTTP '+str(response.status_code)+' from '+urlsplit(url).hostname)
        response.raise_for_status()
        if response.status_code!=200:raise ValueError('Unexpected redirect/status')
        chunks=[];size=0
        for part in response.iter_content(256*1024):
            size+=len(part)
            if size>(45 if pdf else 5)*1024*1024:raise ValueError('Source exceeds safe size limit')
            chunks.append(part)
        body=b''.join(chunks)
    if not pdf:path.write_bytes(body);return body
    if not body.startswith(b'%PDF-'):raise ValueError('Expected annual report PDF')
    with tempfile.TemporaryDirectory(dir='/tmp') as temp:
        report=Path(temp)/'annual.pdf';report.write_bytes(body)
        text=subprocess.check_output(['pdftotext','-f','1','-l','20',str(report),'-'],timeout=30,stderr=subprocess.DEVNULL).decode(errors='replace')
    result={'source_url':url,'sha256':hashlib.sha256(body).hexdigest(),'cins':sorted(set(re.findall(r'\b[LU]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\b',text.upper())))}
    path.write_text(json.dumps(result));return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--limit',type=int);args=ap.parse_args();catalog=json.loads((ROOT/'deployment/national/catalog.json').read_text());fields=catalog['full_fields']
    descriptor=catalog['listed_index'];body=(ROOT/'instance/build/listed-index'/descriptor['path'].rsplit('/',1)[-1]).read_bytes();assert hashlib.sha256(body).hexdigest()==descriptor['sha256']
    companies=[dict(zip(fields,row)) for row in json.loads(gzip.decompress(body))];active={row['cin']:row for row in companies if row['status']=='Active' and row['effective_listing']=='listed'}
    descriptor=catalog['financials'];folder=ROOT/'instance/build/listed-financials';folder.mkdir(parents=True,exist_ok=True);path=folder/descriptor['path'].rsplit('/',1)[-1]
    if not path.exists():path.write_bytes(fetch(descriptor['path']))
    old=json.loads(gzip.decompress(path.read_bytes()));assert hashlib.sha256(path.read_bytes()).hexdigest()==descriptor['sha256'];covered={row['cin'] for row in old}
    names={}
    for row in active.values():names.setdefault(row['name'].upper(),[]).append(row['cin'])
    exchange=list(csv.DictReader(fetch('https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv').decode('utf-8-sig').splitlines()))
    jobs=[]
    for row in exchange:
        candidates=names.get(row['NAME OF COMPANY'].upper(),[])
        if len(candidates)==1 and candidates[0] not in covered:jobs.append((row['SYMBOL'],candidates[0]))
    if args.limit:jobs=jobs[:args.limit]
    robots=RobotFileParser();robots.parse(fetch('https://www.screener.in/robots.txt').decode().splitlines())
    saved={}
    checkpoint=CACHE/'fetch-report.json'
    if checkpoint.exists():
        prior=json.loads(checkpoint.read_text())
        if prior['source_data_commit']==catalog['data_commit']:saved={(r['symbol'],r['cin']):r for r in prior['results'] if not r.get('error','').startswith(('Stopped after','Access/rate denial'))}
    def process(job):
        if job in saved:return saved[job]
        symbol,cin=job;result={'symbol':symbol,'cin':cin}
        try:
            source='https://www.screener.in/company/'+quote(symbol,safe='')+'/'
            if not robots.can_fetch('*',source):raise ValueError('Source robots disallows company page')
            html=fetch(source).decode('utf-8');preview=Tables();preview.feed(html)
            heading=' '.join(preview.sections.get('profit-loss',{}).get('text',[])[:40])
            if not re.search(r'\bStandalone\s+Figures in Rs\. Crores',heading,re.I):raise ValueError('Annual reporting basis or crore unit is not explicit')
            url='https://www.nseindia.com/api/annual-reports?index=equities&symbol='+quote(symbol,safe='');reports=json.loads(fetch(url)).get('data',[])
            reports=[r for r in reports if r.get('broadcast_dttm') not in ('-',None) and r.get('fileName','').startswith('https://nsearchives.nseindia.com/annual_reports/') and r['fileName'].lower().endswith('.pdf')]
            if not reports:raise ValueError('No public dated NSE annual PDF')
            valid=[]
            for r in reports:
                try:stamp=datetime.strptime(r['broadcast_dttm'],'%d-%b-%Y %H:%M:%S').date()
                except ValueError:continue
                if stamp<=date.today():valid.append((int(r['toYr']),stamp,r))
            if not valid:raise ValueError('No non-future dated annual report')
            year,published,report=max(valid,key=lambda item:(item[0],item[1]))
            identity=fetch(report['fileName'],pdf=True)
            if cin not in identity['cins']:raise ValueError('Master CIN absent from first 20 report pages')
            source='https://www.screener.in/company/'+quote(symbol,safe='')+'/'
            if not robots.can_fetch('*',source):raise ValueError('Source robots disallows company page')
            html=fetch(source).decode('utf-8');rows=parse_annual(html,cin=cin,symbol=symbol,year=year,published=published.isoformat(),source_url=source,identity_url=report['fileName'],retrieved=date.today().isoformat())
            for row in rows:normalize(row,set(active))
            result.update(records=rows,identity=identity,page_sha256=hashlib.sha256(html.encode()).hexdigest())
        except Exception as error:result['error']=str(error)[:250]
        return result
    results=[];print('Uncovered exact-name NSE candidates requiring CIN verification:',len(jobs),flush=True)
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures=[pool.submit(process,job) for job in jobs]
        for n,future in enumerate(as_completed(futures),1):
            results.append(future.result())
            if n%10==0 or n==len(jobs):
                (CACHE/'fetch-report.json').write_text(json.dumps({'source_data_commit':catalog['data_commit'],'candidates':len(jobs),'processed':n,'access_stop':STOP.is_set(),'results':results},separators=(',',':')))
                print('Processed',n,'/',len(jobs),'new companies',sum('records' in r for r in results),'access_stop',STOP.is_set(),flush=True)
    rows=[r for item in results for r in item.get('records',[])];(CACHE/'new-statements.json').write_text(json.dumps(rows,separators=(',',':')))
    print('New companies',len({r['cin'] for r in rows}),'annual rows',len(rows),flush=True)
if __name__=='__main__':main()
