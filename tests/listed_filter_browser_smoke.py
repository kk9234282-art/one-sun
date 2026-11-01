"""Regression: listed + capital filters must read one compact index, not the country."""
import csv,io,json,threading,time,gzip
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from urllib.parse import urlsplit,unquote
from playwright.sync_api import sync_playwright,expect
root=Path(__file__).resolve().parents[1];catalog=json.loads((root/'deployment/national/catalog.json').read_text());seen=[];timings={}
listed=json.loads(gzip.decompress((root/'instance/build/listed-index'/catalog['listed_index']['path'].rsplit('/',1)[1]).read_bytes()))
fields=catalog['full_fields'];expected=sum(row[fields.index('status')]=='Active' and row[fields.index('paid_up_capital')] is not None and row[fields.index('paid_up_capital')]<10000000 for row in listed)
class Handler(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
 def translate_path(self,path):
  value=unquote(urlsplit(path).path)
  if value=='/':return str(root/'public/index.html')
  for prefix,folder in [('/static/',root/'public/static'),('/national/',root/'deployment/national'),('/cities/',root/'deployment/cities'),('/listed/',root/'instance/build/listed-index'),('/financials/',root/'instance/build/listed-financials')]:
   if value.startswith(prefix):
    target=(folder/value[len(prefix):]).resolve();return str(target) if target.is_relative_to(folder.resolve()) else str(root/'nonexistent')
  return str(root/'nonexistent')
 def do_GET(self):
  seen.append(urlsplit(self.path).path)
  if urlsplit(self.path).path=='/national/catalog.json':
   prefix=f'http://127.0.0.1:{self.server.server_port}'
   data={**catalog,'base_url':prefix+'/national/','locations':{**catalog['locations'],'base_url':prefix+'/cities/'},'listed_index':{**catalog['listed_index'],'path':prefix+'/listed/'+catalog['listed_index']['path'].rsplit('/',1)[1]}}
   if catalog.get('financials'):data['financials']={**catalog['financials'],'path':prefix+'/financials/'+catalog['financials']['path'].rsplit('/',1)[1]}
   body=json.dumps(data).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
  else:super().do_GET()
server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True);page=browser.new_page(viewport={'width':1440,'height':1000},accept_downloads=True);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(f'http://127.0.0.1:{server.server_port}/');expect(page.locator('#result-count')).to_have_text('21,89,416 records',timeout=30000)
  expect(page.get_by_role('link',name='Download Active listed revenue / profit CSV',exact=True)).to_have_attribute('href',f'http://127.0.0.1:{server.server_port}/national/active-listed-financials.csv')
  start=len(seen);form=page.locator('#filters');form.locator('[name=listing]').select_option('listed');form.locator('[name=capital_band]').select_option('under_1cr');clock=time.perf_counter();form.get_by_role('button',name='Apply filters',exact=True).click();expect(page.locator('#result-count')).to_have_text(f'{expected:,} records',timeout=10000);timings['filter_seconds']=round(time.perf_counter()-clock,3)
  rows=page.evaluate("async()=>await AtlasSnapshot.request('/api/companies?status=Active&listing=listed&capital_band=under_1cr')")
  assert rows['total']==expected and len(rows['rows'])==25 and all(row['status']=='Active' and row['effective_listing']=='listed' and row['paid_up_capital'] is not None and row['paid_up_capital']<10000000 for row in rows['rows'])
  overview=page.evaluate("async()=>await AtlasSnapshot.request('/api/overview?status=Active&listing=listed&capital_band=under_1cr')");assert overview['summary']['companies']==overview['summary']['listed']==expected
  page.locator('#next').click();expect(page.locator('#page-info')).to_contain_text('Page 2',timeout=5000)
  with page.expect_download(timeout=10000) as download:page.locator('#export-csv').click()
  exported=list(csv.DictReader(io.StringIO(Path(download.value.path()).read_text(encoding='utf-8-sig'))));assert len(exported)==expected and all(row['status']=='Active' and row['listing_status']=='listed' and float(row['paid_up_capital'])<10000000 for row in exported)
  data_requests=[path for path in seen[start:] if path.endswith('.gz')];assert all(path.startswith(('/listed/','/financials/')) for path in data_requests),data_requests
  assert seen.count('/listed/'+catalog['listed_index']['path'].rsplit('/',1)[1])==1
  # Geographic and class combinations stay within the same compact index.
  combo=page.evaluate("async()=>await AtlasSnapshot.request('/api/companies?status=Active&listing=listed&capital_band=under_1cr&state=Maharashtra&class=Public')")
  assert combo['total']>0 and all(row['status']=='Active' and row['state']=='Maharashtra' and row['class']=='Public' and row['paid_up_capital']<10000000 for row in combo['rows'])
  form.locator('details summary').click();form.locator('[name=sort]').select_option('paid_up_capital');form.locator('[name=direction]').select_option('desc');form.get_by_role('button',name='Apply filters',exact=True).click();expect(page.locator('#result-count')).to_have_text(f'{expected:,} records',timeout=5000)
  sorted_rows=page.evaluate("async()=>await AtlasSnapshot.request('/api/companies?status=Active&listing=listed&capital_band=under_1cr&sort=paid_up_capital&direction=desc')")['rows'];assert [row['paid_up_capital'] for row in sorted_rows]==sorted([row['paid_up_capital'] for row in sorted_rows],reverse=True)
  if catalog.get('financials'):
   form.locator('[name=capital_band]').select_option('');form.locator('[name=q]').fill('L17110MH1973PLC019786');form.get_by_role('button',name='Apply filters',exact=True).click();expect(page.locator('#result-count')).to_have_text('1 records',timeout=5000)
   real=page.evaluate("async()=>await AtlasSnapshot.request('/api/company/L17110MH1973PLC019786')")
   assert real['company']['financial_year']==2026 and real['company']['revenue_inr']>0 and real['company']['profit_inr']>0 and real['financials']
   assert real['company']['financial_source'].startswith('https://nsearchives.nseindia.com/')
   page.locator('#results .company-link').click();expect(page.locator('#profile')).to_be_visible();expect(page.locator('#error')).to_be_hidden();expect(page.locator('#profile-content')).to_contain_text('Selected financial statement');expect(page.locator('#profile-content')).to_contain_text('2026-03-31');expect(page.get_by_role('link',name='View source statement ↗',exact=True)).to_have_attribute('href',real['company']['financial_source']);page.locator('#close-profile').click()
   form.locator('[name=q]').fill('L65920MH1994PLC080618');form.get_by_role('button',name='Apply filters',exact=True).click();expect(page.locator('#result-count')).to_have_text('1 records',timeout=5000)
   bank=page.evaluate("async()=>await AtlasSnapshot.request('/api/company/L65920MH1994PLC080618')")['company'];assert bank['revenue_metric']=='total_income_banking' and bank['revenue_inr']>0 and bank['profit_inr']>0
   revenue_index=page.locator('#results th').all_text_contents().index('Revenue / income');expect(page.locator('#results tbody tr').first.locator('td').nth(revenue_index)).to_have_attribute('title','Reported total income (banking)')
   assert seen.count('/financials/'+catalog['financials']['path'].rsplit('/',1)[1])==1
  if 'screener' in catalog.get('financials',{}).get('supplementary_sources',[]):
   form.locator('[name=q]').fill('L99999GJ1987PLC009768');form.get_by_role('button',name='Apply filters',exact=True).click();expect(page.locator('#result-count')).to_have_text('1 records',timeout=5000)
   supplemental=page.evaluate("async()=>await AtlasSnapshot.request('/api/company/L99999GJ1987PLC009768')")['company']
   assert supplemental['financial_source_id']=='screener' and supplemental['financial_year']==2026 and supplemental['revenue_inr']==8240000000 and supplemental['profit_inr']==600000000
   assert supplemental['financial_retrieved_on']=='2026-11-01' and supplemental['financial_as_of']=='2026-07-09'
   page.locator('#results .company-link').click();expect(page.locator('#profile-content')).to_contain_text('amounts may be rounded');expect(page.get_by_role('link',name='View CIN verification report ↗',exact=True)).to_have_attribute('href',supplemental['financial_identity_source']);page.locator('#close-profile').click()
   financial_pack=json.loads(gzip.decompress((root/'instance/build/listed-financials'/catalog['financials']['path'].rsplit('/',1)[1]).read_bytes()))
   if any(row['cin']=='L24110GJ1989PLC012441' for row in financial_pack):
    variant=page.evaluate("async()=>await AtlasSnapshot.request('/api/company/L24110GJ1989PLC012441')")['company']
    assert variant['name']=='AKSHARCHEM (INDIA ) LIMITED' and variant['financial_source_id']=='screener' and variant['revenue_inr'] is not None
    assert variant['financial_source']=='https://www.screener.in/company/AKSHARCHEM/' and variant['financial_identity_source'].startswith('https://nsearchives.nseindia.com/annual_reports/')
   supplemental_csv=page.evaluate("async()=>await AtlasSnapshot.request('/api/export.csv?status=Active&listing=listed&q=L99999GJ1987PLC009768')")
   supplemental_rows=list(csv.DictReader(io.StringIO(supplemental_csv)));assert len(supplemental_rows)==1 and supplemental_rows[0]['financial_source_id']=='screener' and supplemental_rows[0]['financial_retrieved_on']=='2026-11-01'
  page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');assert not errors,errors
  browser.close()
 print('Listed browser checks passed:',json.dumps(timings),f'{expected} active exact matches, cached compact data, imported annual figures, banking income labels, pagination, totals, CSV, geographic/class combinations and sorting.')
finally:server.shutdown();thread.join(timeout=5)
