"""Browser-storage review regression using an isolated synthetic page and database."""
import tempfile,threading
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright,expect

ROOT=Path(__file__).resolve().parents[1]
def main():
    with tempfile.TemporaryDirectory() as folder:
        temp=Path(folder)
        (temp/'research.js').write_bytes((ROOT/'intelligence/static/research.js').read_bytes())
        (temp/'index.html').write_text('''<!doctype html><meta charset="utf-8"><body data-review-storage="browser"><main id="root"></main><script src="/research.js"></script><script>AtlasResearch.reviewPanel(document.querySelector('#root'),{cin:'U15511MH2010PTC000001',name:'Synthetic company'});</script></body>''')
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=folder));threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=browser.new_page();errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{server.server_port}/');page.get_by_role('button',name='Open saved review / add a review',exact=True).click();page.get_by_text('Add a sourced review',exact=True).click()
                fields={'description':'Manufactures plywood sheets and decorative laminates.','tags':'Plywood, Laminates','source_url':'https://example.test/products','source_excerpt':'We manufacture plywood sheets and decorative laminates.'}
                for key,value in fields.items():page.locator('#review-'+key).fill(value)
                page.locator('#review-source_kind').select_option('company_website');page.locator('#review-identity_basis').select_option('name_and_address');page.locator('#review-status').select_option('reviewed');page.get_by_role('button',name='Save review',exact=True).click();expect(page.locator('.review-status')).to_have_text('Review saved in this browser.')
                page.reload();page.get_by_role('button',name='Open saved review / add a review',exact=True).click();expect(page.locator('.review-panel')).to_contain_text(fields['description']);page.get_by_text('Edit / add review revision',exact=True).click();page.locator('#review-description').fill('Manufactures plywood; other product activities need checking.');page.locator('#review-status').select_option('needs_review');page.get_by_role('button',name='Save review',exact=True).click();expect(page.locator('.review-status')).to_have_text('Review saved in this browser.');page.get_by_text('Previous review revisions',exact=True).click();expect(page.locator('.review-panel')).to_contain_text('Revision 1');expect(page.locator('.review-panel')).to_contain_text('Revision 2');expect(page.locator('.review-panel')).to_contain_text('Not shared or backed up');assert not errors,errors
                browser.close();print('Browser review persistence, revision history and storage-scope labels passed.')
        finally:server.shutdown()
if __name__=='__main__':main()
