"""Checkpoint public profile research; stop on any access/rate/human challenge."""
import argparse,csv,gzip,hashlib,json,re,sys,time,threading
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
from zoneinfo import ZoneInfo
import requests
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from intelligence.tofler_revenue import extract
ROOT=Path(__file__).resolve().parents[1];CACHE=ROOT/'instance/build/tofler-revenue';CACHE.mkdir(parents=True,exist_ok=True);STOP=threading.Event();LOCK=threading.Lock();last=0

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--offline',action='store_true');ap.add_argument('--retry-deferred',action='store_true');args=ap.parse_args()
    session=requests.Session();robots_url='https://www.tofler.in/robots.txt';robots_path=CACHE/'robots.txt'
    if args.offline:rules=robots_path.read_text() if robots_path.exists() else 'User-agent: *\nDisallow: /'
    else:
        r=session.get(robots_url,timeout=25,verify='/etc/ssl/certs/ca-certificates.crt');r.raise_for_status();rules=r.text;robots_path.write_text(rules)
    robots=RobotFileParser();robots.parse(rules.splitlines())
    queue=list(csv.DictReader((ROOT/'deployment/national/high-capital-revenue-research.csv').open(encoding='utf-8-sig')));pending=[r for r in queue if r['research_status']=='Not researched'];observed=datetime.now(ZoneInfo('Asia/Kolkata')).date().isoformat()
    def run(row):
        global last
        cin=row['cin'];saved=CACHE/(cin+'.json')
        if saved.exists():
            cached=json.loads(saved.read_text())
            if cached.get('reason') in ('HTTP 502','HTTP 503','HTTP 504'):cached.update(status='deferred',reason='Provider service unavailable; research incomplete')
            if args.offline or not args.retry_deferred or cached.get('status')!='deferred':return cached
        result={'cin':cin,'company_name':row['company_name']};slug=re.sub(r'[^a-z0-9]+','-',row['company_name'].lower()).strip('-');url=f'https://www.tofler.in/{slug}/company/{cin}';result['source_url']=url
        if args.offline or STOP.is_set():return result|{'status':'deferred','reason':'Stopped after provider access/rate denial'}
        if not robots.can_fetch('*',url):return result|{'status':'excluded','reason':'Robots disallows profile'}
        try:
            with LOCK:
                delay=.5-(time.monotonic()-last)
                if delay>0:time.sleep(delay)
                last=time.monotonic()
            if args.offline or STOP.is_set():return result|{'status':'deferred','reason':'Stopped after provider access/rate denial'}
            response=requests.get(url,timeout=(10,35),verify='/etc/ssl/certs/ca-certificates.crt',allow_redirects=False)
            if response.status_code in (401,403,429,502,503,504):STOP.set();raise ValueError('Provider access/rate/service barrier HTTP '+str(response.status_code))
            if response.status_code in (301,302,307,308):
                location=response.headers.get('Location','');result.update(status='unavailable',reason='Canonical redirect needs review',redirect=location)
            elif response.status_code!=200:result.update(status='unavailable',reason='HTTP '+str(response.status_code))
            elif re.search(r'captcha|verify you are human|just a moment|challenge-platform',response.text,re.I):STOP.set();raise ValueError('Provider human/challenge verification required')
            else:
                result['sha256']=hashlib.sha256(response.content).hexdigest()
                try:result.update(status='found',lead=extract(response.text,cin=cin,company_name=row['company_name'],source_url=url,observed_on=observed))
                except ValueError as error:result.update(status='no_public_figure',reason=str(error))
            saved.write_text(json.dumps(result,separators=(',',':')))
        except Exception as error:
            result.update(status='blocked' if STOP.is_set() else 'error',reason=str(error)[:200])
            if STOP.is_set():saved.write_text(json.dumps(result,separators=(',',':')))
        return result
    results=[];print('Pending public-company profiles:',len(pending),flush=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(run,row) for row in pending]
        for n,future in enumerate(as_completed(futures),1):
            results.append(future.result())
            if n%20==0 or n==len(pending):
                counts={key:sum(r['status']==key for r in results) for key in ['found','no_public_figure','unavailable','error','blocked','deferred']}
                (CACHE/'report.json').write_text(json.dumps({'offline':args.offline,'targets':len(pending),'completed_jobs':n,'counts':counts,'access_stop':STOP.is_set(),'results':results},separators=(',',':')))
                print(n,'/',len(pending),counts,flush=True)
    print('Finished; provider stop:',STOP.is_set(),flush=True)
if __name__=='__main__':main()
