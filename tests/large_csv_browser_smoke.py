"""Prove >32 MiB local CSV processing and automatic bounded transfer files."""
import csv
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
import io
from pathlib import Path
import tempfile
import threading
from playwright.sync_api import sync_playwright,expect
from static_snapshot_fixture import legacy_server


def main():
    root=Path(__file__).resolve().parents[1]
    server=legacy_server(root)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'synthetic-large-company-master-2026-10-31.csv'
            with path.open('w',encoding='utf-8',newline='') as output:
                writer=csv.writer(output)
                writer.writerow(['CIN','Company Name','Company Registration Date','Company Category','Company Class','Listing Status','Authorized Capital','Paidup Capital','Company ROC','Company Address','Pin Code','Company State','Company Status','Company Sub Category','Company Industrial Classification'])
                for i in range(100000):
                    writer.writerow([f'U12345MH2010PTC{i:06d}',f'Synthetic local browser test {i}','2010-01-01','Company limited by shares','Private','Unlisted','500000','100000','ROC Test','Synthetic address '+('x'*260),'400001','Maharashtra','Active','Non-government company','Synthetic test industry'])
                writer.writerow(['U12345MH2010PTC000000','Synthetic duplicate fixture','2010-01-01','Company limited by shares','Private','Unlisted','500000','100000','ROC Test','Synthetic address','400001','Maharashtra','Active','Non-government company','Synthetic test industry'])
                writer.writerow(['U01110MH2022PTC388674','Synthetic local overwrite fixture','2022-08-17','Company limited by shares','Private','Unlisted','500000','100000','ROC Test','Synthetic address','400001','Maharashtra','Active','Non-government company','Synthetic test industry'])
                writer.writerow(['invalid','Synthetic exception']+['']*13)
            assert path.stat().st_size>32*1024*1024
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True)
                page=browser.new_page(viewport={'width':1440,'height':1000},accept_downloads=True)
                errors=[];writes=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.on('request',lambda request:writes.append(request.url) if request.method not in ('GET','HEAD') else None)
                page.goto(f'http://127.0.0.1:{server.server_port}/')
                expect(page.locator('.metric .number').first).to_have_text('32,078',timeout=30000)
                page.locator('#local-csv-tools summary').click()
                page.locator('#local-csv-file').set_input_files(str(path))
                expect(page.locator('#local-csv-date')).to_have_value('2026-10-31')
                page.get_by_role('button',name='Load CSV in this browser',exact=True).click()
                page.get_by_role('button',name='Cancel reading',exact=True).click()
                expect(page.locator('#local-csv-status')).to_contain_text('Cancelled.')
                expect(page.locator('.metric .number').first).to_have_text('32,078')
                page.get_by_role('button',name='Load CSV in this browser',exact=True).click()
                expect(page.locator('#local-csv-status')).to_contain_text('Loaded in this browser only:',timeout=120000)
                expect(page.locator('#local-csv-status')).to_contain_text('1 exceptions')
                expect(page.locator('#local-csv-status')).to_contain_text('1 duplicate rows')
                expect(page.locator('.metric .number').first).to_have_text('1,32,078',timeout=30000)
                form=page.locator('#filters');form.locator('[name=q]').fill('Synthetic local browser test 99999')
                form.get_by_role('button',name='Apply filters',exact=True).click()
                expect(page.locator('#result-count')).to_have_text('1 records')
                page.get_by_role('button',name='Create smaller files for this chat',exact=True).click()
                expect(page.locator('#local-csv-status')).to_contain_text('Prepared ',timeout=120000)
                page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.set_viewport_size({'width':1440,'height':1000})
                buttons=page.locator('#local-parts button').filter(has_text='Download part ')
                assert buttons.count()>1
                total=0;seen=set()
                for i in range(buttons.count()):
                    with page.expect_download() as download:buttons.nth(i).click()
                    result=Path(download.value.path())
                    assert result.stat().st_size<=8*1024*1024
                    rows=list(csv.DictReader(io.StringIO(result.read_text())))
                    assert 'listing_status' in rows[0]
                    for row in rows:assert row['cin'] not in seen;seen.add(row['cin'])
                    total+=len(rows)
                assert total==100001
                page.get_by_role('button',name='Restore published data',exact=True).click()
                expect(page.locator('.metric .number').first).to_have_text('32,078',timeout=30000)
                # File-level errors must retain the last complete dataset.
                bad=Path(temp)/'bad-2026-10-31.csv';bad.write_text('CIN,Company Name\nU12345MH2010PTC000001,"Unclosed')
                page.locator('#local-csv-file').set_input_files(str(bad))
                page.get_by_role('button',name='Load CSV in this browser',exact=True).click()
                expect(page.locator('#local-csv-status')).to_contain_text('Previous dataset retained',timeout=30000)
                expect(page.locator('.metric .number').first).to_have_text('32,078')
                older=Path(temp)/'older-2025-03-31.csv';older.write_text('CIN,Company Name\nU01110MH2022PTC388674,Synthetic stale fixture\n')
                page.locator('#local-csv-file').set_input_files(str(older))
                page.get_by_role('button',name='Load CSV in this browser',exact=True).click()
                expect(page.locator('#local-csv-status')).to_contain_text('1 older records retained',timeout=30000)
                company=page.evaluate("async()=>await window.AtlasSnapshot.request('/api/company/U01110MH2022PTC388674')")
                assert company['company']['name']=='GRAMGROW PRIVATE LIMITED'
                assert not writes,writes
                assert not errors,errors
                browser.close()
                print(f'Large CSV browser test passed: {path.stat().st_size:,} bytes, 100,000 new synthetic records plus one existing-CIN update, automatic <=8 MiB parts without omissions/duplicates, exceptions, cancellation, rollback, restore, older-snapshot protection, mobile layout and zero upload requests.')
    finally:
        server.shutdown();thread.join(timeout=5)


if __name__=='__main__':main()
