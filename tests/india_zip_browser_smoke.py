"""Test local multi-state ZIP ingestion, disk queries, persistence and rollback."""
import argparse
import csv
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
import io
import json
import re
from pathlib import Path
import tempfile
import threading
import zipfile
from playwright.sync_api import sync_playwright,expect
from static_snapshot_fixture import legacy_server

HEADERS=['CIN','Company Name','Company Registration Date','Company Category','Company Class','Listing Status','Authorized Capital','Paidup Capital','Company ROC','Company Address','Pin Code','Company State','Company Status','Company Sub Category','Company Industrial Classification']
STATES=[('MH','Maharashtra'),('GJ','Gujarat'),('KA','Karnataka'),('TN','Tamil Nadu'),('DL','Delhi')]
def values(code,state,i,large):
    return [f'U12345{code}2010PTC{i:06d}',f'Synthetic ZIP {state} company {i:06d}','2010-01-01','Company limited by shares','Private','Unlisted','500000','' if i==1 else '100000','ROC Test','Synthetic address '+('x'*(900 if large else 150)),'400001',state,'Active','Non-government company','Synthetic ZIP industry']

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--large',action='store_true');args=parser.parse_args()
    n=45000 if args.large else 1000
    root=Path(__file__).resolve().parents[1]
    server=legacy_server(root)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with tempfile.TemporaryDirectory() as temp:
            archive=Path(temp)/'synthetic-all-india-2026-10-31.zip'
            compression=zipfile.ZIP_STORED if args.large else zipfile.ZIP_DEFLATED
            with zipfile.ZipFile(archive,'w',compression=compression) as z:
                for code,state in STATES:
                    with z.open('states/'+state+'.csv','w') as raw:
                        with io.TextIOWrapper(raw,encoding='utf-8',newline='') as text:
                            writer=csv.writer(text);writer.writerow(HEADERS)
                            for i in range(n):writer.writerow(values(code,state,i,args.large))
                            if code=='GJ':writer.writerow(values('MH','Maharashtra',0,args.large))
                            if code=='TN':writer.writerow(['invalid','Synthetic exception']+['']*13)
                z.writestr('notes.csv','note\nSynthetic non-company CSV\n')
                z.writestr('README.txt','Synthetic test archive only; never published.')
            if args.large:assert archive.stat().st_size>200*1024*1024
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True)
                page=browser.new_page(viewport={'width':1440,'height':1000},accept_downloads=True)
                errors=[];writes=[];page.on('pageerror',lambda error:errors.append(str(error)))
                page.on('request',lambda request:writes.append(request.url) if request.method not in ('GET','HEAD') else None)
                address=f'http://127.0.0.1:{server.server_port}/';page.goto(address)
                expect(page.locator('.metric .number').first).to_have_text('32,078',timeout=30000)
                page.locator('#india-zip-tools summary').click();page.locator('#india-zip-file').set_input_files(str(archive))
                page.get_by_role('button',name='Load ZIP into local database',exact=True).click()
                expect(page.locator('#india-zip-status')).to_contain_text(re.compile(r'Local ZIP ready:|ZIP import failed:'),timeout=240000)
                assert 'Local ZIP ready:' in page.locator('#india-zip-status').inner_text(),page.locator('#india-zip-status').inner_text()
                expected='2,25,000' if args.large else '5,000'
                expect(page.locator('.metric .number').first).to_have_text(expected,timeout=30000)
                expect(page.locator('#india-zip-status')).to_contain_text('5 state/UT labels')
                expect(page.locator('#india-zip-status')).to_contain_text('1 duplicate rows reconciled')
                expect(page.locator('#india-zip-status')).to_contain_text('1 exceptions')
                assert not page.locator('#local-csv-tools').is_visible()
                counts=page.evaluate("async()=>await AtlasSnapshot.request('/api/overview')")
                assert counts['summary']['companies']==5*n and counts['summary']['active']==5*n
                assert len(counts['groups']['state'])==5
                form=page.locator('#filters');form.locator('[name=state]').select_option('Karnataka');form.get_by_role('button',name='Apply filters',exact=True).click()
                expect(page.locator('#result-count')).to_have_text(('45,000' if args.large else '1,000')+' records',timeout=30000)
                response=page.evaluate("async()=>await AtlasSnapshot.request('/api/companies?sort=paid_up_capital&direction=desc&per_page=100')")
                assert len(response['rows'])==100 and all(row['paid_up_capital'] is not None for row in response['rows'])
                form.locator('[name=q]').fill('U12345KA2010PTC000000');form.get_by_role('button',name='Apply filters',exact=True).click()
                expect(page.locator('#result-count')).to_have_text('1 records',timeout=120000)
                page.get_by_role('button',name='Synthetic ZIP Karnataka company 000000',exact=True).click()
                profile=page.evaluate("async()=>await AtlasSnapshot.request('/api/company/U12345KA2010PTC000000')")
                assert profile['company']['source_file']=='states/Karnataka.csv'  # Retained in data, hidden in the dashboard.
                page.locator('#close-profile').click()
                with page.expect_download() as download:page.locator('#export-csv').click()
                rows=list(csv.DictReader(io.StringIO(Path(download.value.path()).read_text(encoding='utf-8-sig'))));assert len(rows)==1
                with page.expect_download() as download:page.locator('#india-zip-report').click()
                report=json.loads(Path(download.value.path()).read_text());assert report['recordCount']==5*n and report['duplicates']==1 and sum(row['skipped'] for row in report['files'])==1
                with page.expect_download() as download:page.locator('#india-zip-exceptions').click()
                assert json.loads(Path(download.value.path()).read_text())['total']==1
                # Completed imports survive a browser-page reload without re-reading the ZIP.
                page.reload();expect(page.locator('.metric .number').first).to_have_text('32,078',timeout=30000)
                page.locator('#india-zip-tools summary').click();page.locator('#india-zip-reopen').click()
                expect(page.locator('.metric .number').first).to_have_text(expected,timeout=30000)
                # Tamper with a stored entry without changing its central-directory CRC.
                corrupt=Path(temp)/'corrupt-2026-10-31.zip'
                with zipfile.ZipFile(corrupt,'w',compression=zipfile.ZIP_STORED) as z:z.writestr('bad.csv','CIN,Company Name\nU12345MH2010PTC000001,Synthetic tamper\n')
                data=corrupt.read_bytes().replace(b'Synthetic tamper',b'Synthetic tampex');corrupt.write_bytes(data)
                page.locator('#india-zip-file').set_input_files(str(corrupt));page.get_by_role('button',name='Load ZIP into local database',exact=True).click()
                expect(page.locator('#india-zip-status')).to_contain_text('CRC verification failed',timeout=30000)
                expect(page.locator('.metric .number').first).to_have_text(expected)
                page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                page.locator('#india-zip-published').click();expect(page.locator('.metric .number').first).to_have_text('32,078',timeout=30000)
                assert not writes,writes;assert not errors,errors
                browser.close()
                print(f'ZIP browser test passed: {archive.stat().st_size:,} ZIP bytes, {5*n:,} unique synthetic records across five states; deduplication, skips/exceptions, filtering, profiles, exports, persistence, CRC rollback and zero upload requests.')
    finally:server.shutdown();thread.join(timeout=5)


if __name__=='__main__':main()
