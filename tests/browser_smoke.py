"""End-to-end browser verification against a disposable database, not live data."""
import csv
import os
import tempfile
import threading
from pathlib import Path
from werkzeug.serving import make_server
from werkzeug.security import generate_password_hash
from playwright.sync_api import sync_playwright, expect
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from intelligence import create_app
from intelligence.db import get_db,now


def main():
    with tempfile.TemporaryDirectory() as temp:
        app=create_app({'DATABASE':str(Path(temp)/'browser.sqlite'),'TESTING':True,'SECRET_KEY':'browser-test-only'})
        with app.app_context():
            db=get_db();db.execute('INSERT INTO users(username,password_hash,role,created_at) VALUES(?,?,?,?)',
                                  ('browser-test',generate_password_hash('browser-test-password'),'admin',now()));db.commit()
        server=make_server('127.0.0.1',0,app,threaded=True)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path=os.getenv('CHROMIUM_PATH','/usr/bin/chromium'),headless=True)
                page=browser.new_page(viewport={'width':1440,'height':1000},accept_downloads=True)
                errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(f'http://127.0.0.1:{server.server_port}/')
                page.get_by_label('Username',exact=True).fill('browser-test')
                page.get_by_label('Password',exact=True).fill('browser-test-password')
                page.get_by_role('button',name='Sign in →',exact=True).click()
                page.wait_for_selector('.metric')
                assert page.locator('.metric .number').first.inner_text()=='0'
                page.screenshot(path='/tmp/atlas-empty-dashboard.png',full_page=True)
                for name in ['Company directory','Private companies','Public companies','Exchange universe','State intelligence','Industry analysis','IPO research','LLP registrations','MSME registrations','Data & imports']:
                    page.locator('.nav').filter(has_text=name).click()
                    page.wait_for_timeout(100)
                path=Path(temp)/'synthetic-browser-fixture.csv'
                path.write_text('cin,name,class,status,state,industry,listing_status,incorporated\nU12345MH2010PTC000001,Synthetic browser-only fixture,Private,Active,Maharashtra,Testing,unlisted,2010-01-01\n')
                form=page.locator('#import-form')
                form.locator('[name=source]').select_option('mca')
                form.locator('[name=kind]').select_option('companies')
                form.locator('[name=as_of]').fill('2025-03-31')
                form.locator('[name=file]').set_input_files(str(path))
                form.get_by_role('button',name='Validate & import').click()
                expect(page.locator('#import-result')).to_contain_text('completed')
                with app.app_context():
                    db=get_db()
                    batch=db.execute('SELECT id FROM imports ORDER BY id DESC LIMIT 1').fetchone()[0]
                    db.execute('INSERT INTO import_annotations VALUES(?,?,?,?,?,?,?)',
                               (batch,'Synthetic browser subset','Partial state coverage','Test date label','Test-only provenance','test-checksum','test-archive'))
                    db.commit()
                page.locator('.nav').filter(has_text='Company directory').click()
                expect(page.locator('#dataset-coverage')).to_contain_text('Partial state coverage')
                page.get_by_role('button',name='Synthetic browser-only fixture',exact=True).wait_for()
                page.get_by_role('button',name='Synthetic browser-only fixture',exact=True).click()
                page.locator('#profile[open]').wait_for()
                assert 'Insufficient evidence' in page.locator('#profile-content').inner_text()
                assert 'not an official SEBI IPO eligibility test' in page.locator('#profile-content').inner_text()
                page.get_by_role('button',name='Close company profile').click()
                with page.expect_download() as download:
                    page.locator('#export-csv').click()
                assert download.value.suggested_filename=='companies.csv'
                assert 'Synthetic browser-only fixture' in Path(download.value.path()).read_text()
                page.locator('.nav').filter(has_text='State intelligence').click()
                page.get_by_role('button',name='Maharashtra: 1 imported companies',exact=True).wait_for()
                page.get_by_role('button',name='Maharashtra: 1 imported companies',exact=True).click()
                page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                page.screenshot(path='/tmp/atlas-mobile-test.png',full_page=True)
                assert not errors, errors
                browser.close()
                print('Browser smoke passed: login, all modules, import, profile, CSV export, state map, mobile layout; no JavaScript exceptions.')
        finally:
            server.shutdown();thread.join(timeout=5)


if __name__=='__main__':main()
