"""Exercise the real released national data over static HTTP, without a database API."""
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
import csv
import io
import json
from pathlib import Path
import threading
from urllib.parse import unquote,urlsplit
from playwright.sync_api import sync_playwright,expect

def indian(value):
    text=str(value)
    if len(text)<=3:return text
    prefix=text[:-3];parts=[]
    while prefix:parts.insert(0,prefix[-2:]);prefix=prefix[:-2]
    return ','.join(parts+[text[-3:]])

def main():
    root=Path(__file__).resolve().parents[1];catalog=json.loads((root/'deployment/national/catalog.json').read_text());seen=[]
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self,*args):pass
        def translate_path(self,path):
            parsed=unquote(urlsplit(path).path)
            if parsed=='/':return str(root/'deployment/index.html')
            for prefix,directory in [('/cities/',root/'deployment/cities'),('/static/',root/'intelligence/static'),('/national/',root/'deployment/national')]:
                if parsed.startswith(prefix):
                    target=(directory/parsed[len(prefix):]).resolve()
                    return str(target) if target.is_relative_to(directory.resolve()) else str(root/'nonexistent')
            return str(root/'nonexistent')
        def do_GET(self):
            seen.append(urlsplit(self.path).path)
            if urlsplit(self.path).path=='/national/catalog.json':
                data=dict(catalog);data['base_url']=f'http://127.0.0.1:{self.server.server_port}/national/'
                data['locations']={**data['locations'],'base_url':f'http://127.0.0.1:{self.server.server_port}/cities/'}
                body=json.dumps(data).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
            else:super().do_GET()
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True)
            page=browser.new_page(viewport={'width':1440,'height':1000},accept_downloads=True);errors=[];writes=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.on('request',lambda request:writes.append(request.url) if request.method not in ('GET','HEAD') else None)
            page.goto(f'http://127.0.0.1:{server.server_port}/')
            expect(page.locator('.metric .number').first).to_have_text(indian(catalog['record_count']),timeout=30000)
            assert len([path for path in seen if path.endswith('.gz')])<=2,'Initial browse must not download the country dataset.'
            assert not any(path=='/data/companies.json' for path in seen),'Must not silently load the old agriculture subset.'
            assert page.locator('#results tbody tr').count()==25
            assert page.locator('#filters [name=state] option').count()==37
            page.locator('#next').click();expect(page.locator('#page-info')).to_contain_text('Page 2')
            form=page.locator('#filters');form.locator('[name=state]').select_option('Maharashtra');form.get_by_role('button',name='Apply filters',exact=True).click()
            expect(page.locator('#result-count')).to_have_text(indian(catalog['states']['Maharashtra']['stats']['summary']['companies'])+' records',timeout=30000)
            expect(form.locator('[name=city]')).to_be_enabled()
            form.locator('[name=city]').fill('Pune');form.get_by_role('button',name='Apply filters',exact=True).click()
            city_data=json.loads((root/'deployment/cities'/catalog['locations']['states']['Maharashtra']['path']).read_text())
            count=city_data['counts'][city_data['labels'].index('Pune')]
            expect(page.locator('#result-count')).to_have_text(indian(count)+' records',timeout=120000)
            result=page.evaluate("async()=>await AtlasSnapshot.request('/api/companies?state=Maharashtra&city=Pune')")
            assert result['total']==count and all(row['city']=='Pune' for row in result['rows'])
            form.locator('[name=city]').fill('')
            form.locator('[name=q]').fill('GRAMGROW');form.get_by_role('button',name='Apply filters',exact=True).click()
            expect(page.locator('#result-count')).to_have_text('1 records',timeout=120000)
            page.get_by_role('button',name='GRAMGROW PRIVATE LIMITED',exact=True).click()
            expect(page.locator('#profile-content')).to_contain_text('421401',timeout=30000)
            expect(page.locator('#profile-content')).to_contain_text('2022-08-17')
            page.locator('#close-profile').click()
            with page.expect_download(timeout=120000) as download:page.locator('#export-csv').click()
            rows=list(csv.DictReader(io.StringIO(Path(download.value.path()).read_text(encoding='utf-8-sig'))));assert len(rows)==1 and rows[0]['cin']=='U01110MH2022PTC388674'
            # Current state names retain the original source label in full profiles.
            record=page.evaluate("async()=>await AtlasSnapshot.request('/api/companies?state=Odisha&per_page=1')")['rows'][0]
            company=page.evaluate("async cin=>await AtlasSnapshot.request('/api/company/'+cin)",record['cin'])['company']
            assert company['state']=='Odisha' and company['registered_state']=='Orissa'
            assert company['revenue_inr'] is None
            suspicious=next(iter(catalog['date_quality']))
            reviewed=page.evaluate("async cin=>await AtlasSnapshot.request('/api/company/'+cin)",suspicious)
            assert reviewed['company']['incorporated'] is None
            assert reviewed['company']['source_incorporated']==catalog['date_quality'][suspicious]
            assert reviewed['score']['assessable_points']==0
            assert not any(row['label'] in ['1111','5600','9076'] for row in catalog['stats']['groups']['trends'])
            page.locator('.nav').filter(has_text='Data & imports').click()
            expect(page.locator('#source-cards')).to_contain_text('All-India company master')
            with page.expect_download(timeout=30000) as download:page.locator('#national-exceptions').click()
            assert len(list(csv.DictReader(io.StringIO(Path(download.value.path()).read_text()))))==56
            page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert not writes,writes;assert not errors,errors
            browser.close()
            print(f"National static browser checks passed: {catalog['record_count']:,} companies, 36 states/UTs, bounded first-page load, state/name search, profiles, source-state preservation, filtered CSV, 56 exceptions and mobile layout.")
    finally:server.shutdown();thread.join(timeout=5)

if __name__=='__main__':main()
