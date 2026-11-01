"""Read issuer-declared CIN/symbol/ISIN from publicly linked NSE BRSR files.

Cache unchanged URLs, use bounded concurrency, and stop on access/rate denial.
No CAPTCHA, cookie challenges, credentials, or name-based identity inference.
"""
import csv,hashlib,json,threading,time,xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from urllib.parse import urlsplit
import requests
ROOT=Path(__file__).resolve().parents[1];FOLDER=ROOT/'instance/build/nse-financials';CACHE=FOLDER/'identity-xml';CACHE.mkdir(parents=True,exist_ok=True)
def main():
    stop=threading.Event()
    rows=[{key.strip():value for key,value in row.items()} for row in csv.DictReader((FOLDER/'brsr-2026.csv').open(encoding='utf-8-sig'))]
    urls=list(dict.fromkeys(row['**XBRL'] for row in rows if row.get('**XBRL','').startswith('https://nsearchives.nseindia.com/')))
    def fetch(url):
        if stop.is_set():return {'url':url,'error':'Stopped after access/rate denial'}
        path=CACHE/(hashlib.sha256(url.encode()).hexdigest()+'.xml')
        try:
            if path.exists():body=path.read_bytes()
            else:
                response=requests.get(url,timeout=(10,35),verify='/etc/ssl/certs/ca-certificates.crt',allow_redirects=False)
                if response.status_code in (401,403,429):stop.set();return {'url':url,'error':'Access/rate denial HTTP '+str(response.status_code)}
                response.raise_for_status();body=response.content
                if len(body)>15*1024*1024:raise ValueError('Oversized issuer report')
                if b'<!DOCTYPE' in body.upper() or b'<!ENTITY' in body.upper():raise ValueError('External/entity XML declarations rejected')
                path.write_bytes(body);time.sleep(0.15)
            root=ET.fromstring(body);facts={}
            for element in root:
                name=element.tag.split('}')[-1]
                if name in ('CorporateIdentityNumber','NSESymbol','ISIN','NameOfTheCompany'):
                    facts.setdefault(name,set()).add((element.text or '').strip())
            if any(len(facts.get(name,set()))!=1 for name in ('CorporateIdentityNumber','NSESymbol','ISIN')):raise ValueError('Missing or conflicting issuer identity facts')
            return {'cin':next(iter(facts['CorporateIdentityNumber'])).upper(),'symbol':next(iter(facts['NSESymbol'])).upper(),'isin':next(iter(facts['ISIN'])).upper(),'source_url':url,'source_sha256':hashlib.sha256(body).hexdigest()}
        except (requests.RequestException,ValueError,ET.ParseError) as error:return {'url':url,'error':str(error)[:180]}
    results=[]
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures=[executor.submit(fetch,url) for url in urls]
        for number,future in enumerate(as_completed(futures),1):
            results.append(future.result())
            if number%100==0:print('Issuer identities processed',number,'/',len(urls),'valid',sum('cin' in row for row in results),flush=True)
    (FOLDER/'issuer-identities.json').write_text(json.dumps(results,separators=(',',':')))
    print('Issuer identity download complete:',len(results),'reports,',sum('cin' in row for row in results),'with exact identities; access_stop=',stop.is_set(),flush=True)

if __name__=='__main__':main()
