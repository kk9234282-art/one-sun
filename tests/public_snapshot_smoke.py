"""Exercise the actual public export over HTTP, without any Flask API/database."""
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import csv
import io
import json
import threading
from playwright.sync_api import sync_playwright,expect
from static_snapshot_fixture import legacy_server


def main():
    root=Path(__file__).resolve().parents[1]
    manifest=json.loads((root/'deployment/data/manifest.json').read_text())
    server=legacy_server(root)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True)
            page=browser.new_page(viewport={'width':1440,'height':1000},accept_downloads=True)
            errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(f'http://127.0.0.1:{server.server_port}/')
            expect(page.locator('.metric .number').first).to_have_text(f"{manifest['record_count']:,}",timeout=30000)
            assert page.locator('#results tbody tr').count()==25
            first=page.locator('.company-link').first.inner_text()
            page.locator('#next').click()
            expect(page.locator('#page-info')).to_contain_text('Page 2')
            assert page.locator('.company-link').first.inner_text()!=first
            assert not page.locator('#export-xlsx').is_visible()
            form=page.locator('#filters');form.locator('[name=q]').fill('GRAMGROW')
            form.get_by_role('button',name='Apply filters',exact=True).click()
            expect(page.locator('#result-count')).to_have_text('1 records')
            page.get_by_role('button',name='GRAMGROW PRIVATE LIMITED',exact=True).click()
            expect(page.locator('#profile')).to_be_visible()
            expect(page.locator('#profile-content')).to_contain_text('421401')
            expect(page.locator('#profile-content')).to_contain_text('2022-08-17')
            expect(page.locator('#profile-content')).to_contain_text('Insufficient evidence')
            page.locator('#close-profile').click()
            with page.expect_download() as download:page.locator('#export-csv').click()
            rows=list(csv.DictReader(io.StringIO(Path(download.value.path()).read_text(encoding='utf-8-sig'))))
            assert len(rows)==1 and rows[0]['cin']=='U01110MH2022PTC388674'
            form.get_by_role('button',name='Reset',exact=True).click()
            expect(page.locator('#result-count')).to_have_text('32,078 records')
            page.locator('.nav').filter(has_text='Public companies').click()
            expect(page.locator('#result-count')).to_have_text('811 records')
            page.locator('.nav').filter(has_text='Company directory').click()
            form.locator('[name=listing]').select_option('listed')
            form.get_by_role('button',name='Apply filters',exact=True).click()
            expect(page.locator('#result-count')).to_have_text('43 records')
            form.get_by_role('button',name='Reset',exact=True).click()
            page.locator('.nav').filter(has_text='IPO research').click()
            expect(page.locator('#result-count')).to_have_text('32,035 records')
            form.locator('summary').click()
            form.locator('[name=min_revenue]').select_option('100000000')
            form.get_by_role('button',name='Apply filters',exact=True).click()
            expect(page.locator('#result-count')).to_have_text('0 records')
            form.get_by_role('button',name='Reset',exact=True).click()
            page.locator('.nav').filter(has_text='State intelligence').click()
            expect(page.locator('#india-map')).to_be_visible()
            expect(page.get_by_role('button',name='Maharashtra: 32,078 imported companies',exact=True)).to_be_visible()
            page.locator('.nav').filter(has_text='Data & imports').click()
            expect(page.locator('#source-cards')).to_contain_text('User-supplied datasets')
            assert page.locator('#import-form').count()==0
            page.set_viewport_size({'width':390,'height':844})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            assert not errors,errors
            browser.close()
            print('Public dataset browser checks passed: totals, pagination, search, profile, filtered CSV, public/listed/unlisted filters, missing-financial exclusion, source status and mobile layout.')
    finally:
        server.shutdown();thread.join(timeout=5)


if __name__=='__main__':main()
