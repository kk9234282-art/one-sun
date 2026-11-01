"""Check missing/imported financial UI using a disposable synthetic database only."""
import sys,tempfile,threading
from pathlib import Path
from werkzeug.serving import make_server,WSGIRequestHandler
from werkzeug.security import generate_password_hash
from playwright.sync_api import sync_playwright,expect
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from intelligence import create_app
from intelligence.db import get_db,now
from intelligence.ingest import ingest

class QuietHandler(WSGIRequestHandler):
 def log_request(self,*args,**kwargs):pass

def main():
 with tempfile.TemporaryDirectory() as folder:
  root=Path(folder);app=create_app({'DATABASE':str(root/'test.sqlite'),'TESTING':True,'SECRET_KEY':'financial-browser-test-only'})
  cin='L12345MH2010PLC000001';name='Synthetic financial browser fixture';source='https://www.bseindia.com/synthetic-test-only.pdf'
  companies=root/'companies.csv';companies.write_text(f'cin,name,class,status,state,listing_status,incorporated,paid_up_capital\n{cin},{name},Public,Active,Maharashtra,listed,2010-01-01,1000000\n')
  with app.app_context():
   db=get_db();db.execute('INSERT INTO users(username,password_hash,role,created_at) VALUES(?,?,?,?)',('financial-test',generate_password_hash('financial-test-only'),'analyst',now()));db.commit();result=ingest(db,companies,'companies','mca','2025-03-31');assert result['inserted']==1
  server=make_server('127.0.0.1',0,app,threaded=True,request_handler=QuietHandler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True);page=browser.new_page(viewport={'width':1440,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(f'http://127.0.0.1:{server.server_port}/');page.get_by_label('Username',exact=True).fill('financial-test');page.get_by_label('Password',exact=True).fill('financial-test-only');page.get_by_role('button',name='Sign in →',exact=True).click();expect(page.locator('#result-count')).to_have_text('1 records',timeout=30000)
    headers=page.locator('#results th').all_text_contents();revenue=headers.index('Revenue / income');profit=headers.index('Net profit');year=headers.index('FY ending');cells=page.locator('#results tbody tr').first.locator('td');expect(cells.nth(revenue)).to_have_text('Not imported');expect(cells.nth(profit)).to_have_text('Not imported')
    page.get_by_role('button',name=name,exact=True).click();expect(page.locator('#profile')).to_be_visible();expect(page.locator('#error')).to_be_hidden();expect(page.locator('#profile-content')).to_contain_text('Financial statement not imported');page.locator('#close-profile').click()
    financial=root/'financials.csv';financial.write_text(f'cin,financial_year,reporting_type,unit,revenue,net_profit,source_url\n{cin},2025,standalone,INR lakh,100,0,{source}\n')
    with app.app_context():assert ingest(get_db(),financial,'financials','bse','2025-06-01')['inserted']==1
    page.reload();expect(page.locator('#result-count')).to_have_text('1 records',timeout=30000);cells=page.locator('#results tbody tr').first.locator('td');expect(cells.nth(revenue)).to_have_text('₹1 cr');expect(cells.nth(profit)).to_have_text('₹0');expect(cells.nth(year)).to_have_text('2025')
    page.get_by_role('button',name=name,exact=True).click();expect(page.locator('#profile')).to_be_visible();expect(page.locator('#error')).to_be_hidden();expect(page.locator('#profile-content')).to_contain_text('Selected financial statement');expect(page.locator('#profile-content')).not_to_contain_text('Financial statement not imported');expect(page.get_by_role('link',name='View source statement ↗',exact=True)).to_have_attribute('href',source)
    assert not errors,errors;browser.close()
   print('Financial UI checks passed: honest missing-state labels, imported revenue, zero profit, financial year, unit conversion and source links. Only disposable synthetic data used.')
  finally:server.shutdown();thread.join(timeout=5)
if __name__=='__main__':main()
