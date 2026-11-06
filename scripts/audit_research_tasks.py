"""Offline browser audit using local public build and immutable dataset mirrors.
Run from the repository root with the project venv; requires Chromium, Playwright
and the existing instance build/cache files. Writes reports only under work/.
Timings exclude real network latency and follow a bounded initial source search.
"""
import json,threading,gzip,time,sqlite3
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from urllib.parse import urlencode
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'work/research-audit';OUT.mkdir(parents=True,exist_ok=True);db=sqlite3.connect('file:instance/india-online.sqlite?mode=ro',uri=True)
db.row_factory=sqlite3.Row
active=[dict(r) for r in db.execute("SELECT cin,name,json_extract(payload,'$.industry') AS industry,json_extract(payload,'$.paid_up_capital') AS paid_up_capital FROM records WHERE state='Maharashtra' AND json_extract(payload,'$.status')='Active'")];db.close()

scenarios=[('chemicals_capital',{'state':'Maharashtra','registered_activity_code':'20110','capital_band':'10cr_plus'},lambda r:r['cin'][1:6]=='20110' and r['paid_up_capital'] is not None and r['paid_up_capital']>=1e8),('capital_discovery',{'state':'Maharashtra','capital_band':'10cr_plus'},lambda r:r['paid_up_capital'] is not None and r['paid_up_capital']>=1e8)]
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT/'public')));threading.Thread(target=server.serve_forever,daemon=True).start();report={'environment':'Local Chromium with locally mirrored immutable data; timings exclude real GitHub network latency.','scenarios':[]}
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=browser.new_page();page.set_default_timeout(120000);page_errors=[];page.on('pageerror',lambda e:page_errors.append(str(e)));requests=[]
  app=(ROOT/'intelligence/static/app.js').read_text();page.route('**/static/app.js',lambda route:route.fulfill(content_type='application/javascript',body="document.querySelector('[name=activity_q]').value='liquor';\n"+app))
  def mirror(route):
   rel=route.request.url.split('/deployment/',1)[1];file=ROOT/'deployment'/rel
   if rel.startswith('financials/'):file=ROOT/'instance/build/listed-financials'/rel.rsplit('/',1)[-1]
   if rel.startswith('listed/'):file=ROOT/'instance/build/listed-index'/rel.rsplit('/',1)[-1]
   body=file.read_bytes();requests.append({'path':rel,'bytes':len(body)});route.fulfill(body=body,headers={'Access-Control-Allow-Origin':'*'})
  page.route('https://raw.githubusercontent.com/**/deployment/**',mirror);page.goto(f'http://127.0.0.1:{server.server_port}/');page.get_by_role('button',name='ASSOCIATED ALCOHOLS & BREWERIES LTD.',exact=True).wait_for(timeout=30000)
  def query(params):
   p={'status':'Active','page':'1',**params};return page.evaluate('''async p=>{AtlasOnline.beginView();const q=new URLSearchParams(p);const t=performance.now();const [records,stats]=await Promise.all([AtlasOnline.request('/api/companies?'+q),AtlasOnline.request('/api/overview?'+q)]);return {records,stats,ms:performance.now()-t};}''',p)
  for name,params,match in scenarios:
   expected=sorted([r for r in active if match(r)],key=lambda r:(r['name'].upper(),r['cin']));start=len(requests);first=query(params);assert first['records']['total']==len(expected)==first['stats']['summary']['companies'],(name,len(expected),first['records']['total']);assert {r['cin'] for r in first['records']['rows']}=={r['cin'] for r in expected[:25]}
   for group,rows in first['stats']['groups'].items():
    if group!='trends':assert sum(r['count'] for r in rows)==len(expected),(name,group)
   cold=requests[start:];start=len(requests);second=query({**params,'page':'2'});assert {r['cin'] for r in second['records']['rows']}=={r['cin'] for r in expected[25:50]};warm=requests[start:]
   report['scenarios'].append({'name':name,'filters':params,'count':len(expected),'first_ms':round(first['ms']),'first_chunks':len(cold),'first_compressed_bytes':sum(r['bytes'] for r in cold),'next_page_ms':round(second['ms']),'next_page_chunks':len(warm),'next_page_compressed_bytes':sum(r['bytes'] for r in warm),'sample':[{'cin':r['cin'],'name':r['name'],'industry':r['industry'],'description':r['business_description'],'evidence':r['activity_evidence']} for r in first['records']['rows'][:10]]});print(name,report['scenarios'][-1],flush=True)
  # Narrow source-led research, financial screening and evidence gaps.
  for name,params in [('source_chemicals',{'state':'Maharashtra','activity_tag':'Chemicals','capital_band':'10cr_plus'}),('profitable_listed',{'state':'Maharashtra','listing':'listed','positive_profit':'1','min_revenue':'1000000000'}),('missing_descriptions',{'state':'Maharashtra','registered_activity_code':'20110','activity_evidence':'needs_research','capital_band':'10cr_plus'})]:
   start=len(requests);found=query(params);assert found['records']['total']==found['stats']['summary']['companies'];rows=found['records']['rows'];assert all(r['state']=='Maharashtra' and r['status']=='Active' for r in rows)
   if name=='source_chemicals':assert all('Chemicals' in r['business_tags'] and r['business_description'] and r['paid_up_capital']>=1e8 for r in rows)
   if name=='profitable_listed':assert all(r['profit_inr']>0 and r['revenue_inr']>=1e9 and r['financial_source'] for r in rows)
   if name=='missing_descriptions':assert all(not r['business_description'] and r['cin'][1:6]=='20110' for r in rows)
   downloaded=requests[start:];report['scenarios'].append({'name':name,'count':found['records']['total'],'first_ms':round(found['ms']),'chunks':len(downloaded),'bytes':sum(r['bytes'] for r in downloaded),'sample':[{'cin':r['cin'],'name':r['name'],'description':r['business_description'],'evidence':r['activity_evidence']} for r in rows[:10]]});print(name,found['records']['total'],round(found['ms']),flush=True)
  # Exercise the actual dependent geography controls with a bounded source-led query.
  page.locator('[name=activity_q]').fill('');page.locator('[name=activity_tag]').select_option('Chemicals',force=True);page.locator('[name=capital_band]').select_option('10cr_plus',force=True)
  page.get_by_role('button',name='State',exact=True).click();page.get_by_role('searchbox',name='Search State',exact=True).fill('Maharashtra');page.get_by_role('option',name='Maharashtra',exact=True).click()
  page.wait_for_function("[...document.querySelector('[name=city]').options].some(o=>o.value==='Pune')")
  page.locator('[name=city]').select_option('Pune',force=True);page.get_by_role('button',name='Apply filters',exact=True).click()
  expect(page.locator('#result-count')).not_to_have_text('Loading companies…')
  ui=page.evaluate("async()=>AtlasOnline.request('/api/companies?'+new URLSearchParams({status:'Active',state:'Maharashtra',city:'Pune',activity_tag:'Chemicals',capital_band:'10cr_plus'}))")
  assert all(r['district']=='Pune' for r in ui['rows']);expect(page.locator('#result-count')).to_have_text(str(ui['total'])+' records')
  page.locator('[name=city]').select_option('',force=True);page.get_by_role('button',name='Apply filters',exact=True).click();expect(page.locator('#result-count')).to_have_text('17 records');
  company_name=page.locator('#results .company-link').first.inner_text()
  page.locator('#results .company-link').first.click();expect(page.get_by_role('link',name='Research '+company_name+' with Google AI Mode (opens in a new tab)',exact=True)).to_be_visible();page.locator('#close-profile').click()
  page.get_by_role('button',name='State',exact=True).click();page.get_by_role('searchbox',name='Search State',exact=True).fill('Gujarat');page.get_by_role('option',name='Gujarat',exact=True).click()
  assert page.locator('[name=city]').input_value()=='' and page.locator('[name=postal_code]').input_value()=='' and page.locator('[name=postal_city]').input_value()==''
  page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  report['ui_checks']={'pune_source_chemicals_count':ui['total'],'state_change_clears_children':True,'google_research_link':True,'mobile_no_horizontal_overflow':True}
  assert not page_errors,page_errors;browser.close()
finally:server.shutdown();(OUT/'results.json').write_text(json.dumps(report,indent=2))
