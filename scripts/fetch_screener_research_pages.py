"""Fetch known public issuer pages for high-capital research; never search/challenge bypass."""
import csv,hashlib,io,json,re,sys,time
from pathlib import Path
from urllib.robotparser import RobotFileParser
import requests
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from intelligence.company_names import candidate_key
ROOT=Path(__file__).resolve().parents[1];CACHE=ROOT/'instance/build/screener-financials'
def main():
    rows=list(csv.DictReader((ROOT/'deployment/national/high-capital-revenue-research.csv').open(encoding='utf-8-sig')));names={}
    for row in rows:
        if row['research_status']=='Not researched':names.setdefault(candidate_key(row['company_name']),[]).append(row)
    url='https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv';issuers=list(csv.DictReader(io.StringIO((CACHE/(hashlib.sha256(url.encode()).hexdigest()+'.body')).read_text(encoding='utf-8-sig'))));jobs=[]
    for issuer in issuers:
        match=names.get(candidate_key(issuer['NAME OF COMPANY']),[])
        if len(match)==1:
            source='https://www.screener.in/company/'+issuer['SYMBOL']+'/';path=CACHE/(hashlib.sha256(source.encode()).hexdigest()+'.body')
            if not path.exists():jobs.append((match[0]['cin'],source,path))
    robots=RobotFileParser();robot_path=CACHE/(hashlib.sha256(b'https://www.screener.in/robots.txt').hexdigest()+'.body');robots.parse(robot_path.read_text().splitlines());report={'candidates':len(jobs),'pages':[],'provider_stop':None};print('Uncached known public issuer pages:',len(jobs),flush=True)
    for n,(cin,url,path) in enumerate(jobs,1):
        if not robots.can_fetch('*',url):report['pages'].append({'cin':cin,'status':'robots-excluded'});continue
        try:
            r=requests.get(url,timeout=(10,30),verify='/etc/ssl/certs/ca-certificates.crt',allow_redirects=False)
            if r.status_code in (401,403,429,502,503,504):report['provider_stop']='HTTP '+str(r.status_code);break
            if re.search(r'just a moment|verify you are human|challenge-platform',r.text,re.I):report['provider_stop']='Human/challenge barrier';break
            if r.status_code==200:path.write_bytes(r.content)
            report['pages'].append({'cin':cin,'status':r.status_code,'source_url':url})
        except Exception as error:report['pages'].append({'cin':cin,'status':'error','reason':str(error)[:120]})
        (CACHE/'research-page-fetch-report.json').write_text(json.dumps(report,separators=(',',':')))
        if n%10==0:print('Attempted',n,'/',len(jobs),'public pages',flush=True)
        time.sleep(2)
    (CACHE/'research-page-fetch-report.json').write_text(json.dumps(report,separators=(',',':')));print('Finished; provider stop:',report['provider_stop'],flush=True)
if __name__=='__main__':main()
