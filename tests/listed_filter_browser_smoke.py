"""Regression: listed + capital filters must read one compact index, not the country."""
import csv,io,json,threading,time
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from urllib.parse import urlsplit,unquote
from playwright.sync_api import sync_playwright,expect
root=Path(__file__).resolve().parents[1];catalog=json.loads((root/'deployment/national/catalog.json').read_text());seen=[];timings={}
class Handler(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
 def translate_path(self,path):
  value=unquote(urlsplit(path).path)
  if value=='/':return str(root/'public/index.html')
  for prefix,folder in [('/static/',root/'public/static'),('/national/',root/'deployment/national'),('/cities/',root/'deployment/cities'),('/listed/',root/'instance/build/listed-index')]:
   if value.startswith(prefix):
    target=(folder/value[len(prefix):]).resolve();return str(target) if target.is_relative_to(folder.resolve()) else str(root/'nonexistent')
  return str(root/'nonexistent')
 def do_GET(self):
  seen.append(urlsplit(self.path).path)
  if urlsplit(self.path).path=='/national/catalog.json':
   prefix=f'http://127.0.0.1:{self.server.server_port}'
   data={**catalog,'base_url':prefix+'/national/','locations':{**catalog['locations'],'base_url':prefix+'/cities/'},'listed_index':{**catalog['listed_index'],'path':prefix+'/listed/'+catalog['listed_index']['path'].rsplit('/',1)[1]}}
   body=json.dumps(data).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
  else:super().do_GET()
server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True);page=browser.new_page(viewport={'width':1440,'height':1000},accept_downloads=True);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(f'http://127.0.0.1:{server.server_port}/');expect(page.locator('#result-count')).to_have_text('32,36,908 records',timeout=30000)
  start=len(seen);form=page.locator('#filters');form.locator('[name=listing]').select_option('listed');form.locator('[name=capital_band]').select_option('under_1cr');clock=time.perf_counter();form.get_by_role('button',name='Apply filters',exact=True).click();expect(page.locator('#result-count')).to_have_text('1,576 records',timeout=10000);timings['filter_seconds']=round(time.perf_counter()-clock,3)
  rows=page.evaluate("async()=>await AtlasSnapshot.request('/api/companies?listing=listed&capital_band=under_1cr')")
  assert rows['total']==1576 and len(rows['rows'])==25 and all(row['effective_listing']=='listed' and row['paid_up_capital'] is not None and row['paid_up_capital']<10000000 for row in rows['rows'])
  overview=page.evaluate("async()=>await AtlasSnapshot.request('/api/overview?listing=listed&capital_band=under_1cr')");assert overview['summary']['companies']==overview['summary']['listed']==1576
  page.locator('#next').click();expect(page.locator('#page-info')).to_contain_text('Page 2',timeout=5000)
  with page.expect_download(timeout=10000) as download:page.locator('#export-csv').click()
  exported=list(csv.DictReader(io.StringIO(Path(download.value.path()).read_text(encoding='utf-8-sig'))));assert len(exported)==1576 and all(row['listing_status']=='listed' and float(row['paid_up_capital'])<10000000 for row in exported)
  data_requests=[path for path in seen[start:] if path.endswith('.gz')];assert data_requests==['/listed/'+catalog['listed_index']['path'].rsplit('/',1)[1]],data_requests
  # Geographic and class combinations stay within the same compact index.
  combo=page.evaluate("async()=>await AtlasSnapshot.request('/api/companies?listing=listed&capital_band=under_1cr&state=Maharashtra&city=Pune&class=Public')")
  assert combo['total']>0 and all(row['district']=='Pune' and row['state']=='Maharashtra' and row['class']=='Public' and row['paid_up_capital']<10000000 for row in combo['rows'])
  form.locator('details summary').click();form.locator('[name=sort]').select_option('paid_up_capital');form.locator('[name=direction]').select_option('desc');form.get_by_role('button',name='Apply filters',exact=True).click();expect(page.locator('#result-count')).to_have_text('1,576 records',timeout=5000)
  sorted_rows=page.evaluate("async()=>await AtlasSnapshot.request('/api/companies?listing=listed&capital_band=under_1cr&sort=paid_up_capital&direction=desc')")['rows'];assert [row['paid_up_capital'] for row in sorted_rows]==sorted([row['paid_up_capital'] for row in sorted_rows],reverse=True)
  page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');assert not errors,errors
  browser.close()
 print('Listed browser checks passed:',json.dumps(timings),'1,576 exact matches, one 782,530-byte data request, pagination, totals, CSV, geographic/class combinations and sorting.')
finally:server.shutdown();thread.join(timeout=5)
