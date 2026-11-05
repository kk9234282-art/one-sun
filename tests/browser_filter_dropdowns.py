"""Dashboard filter interaction regression using synthetic API responses. Run from repository root."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import re,json
html=re.sub(r'<script\b[^>]*>.*?</script>','',Path('deployment/index.html').read_text(),flags=re.S)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=b.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.set_content(html);page.add_style_tag(content=Path('intelligence/static/app.css').read_text())
 page.evaluate('''window.fetch=async url=>{const u=new URL(url,'https://example.test');let data={};if(u.pathname==='/api/options')data={state:['Gujarat','Maharashtra'],industry:['Testing'],city:u.searchParams.get('state')?['Mumbai','Pune']:[],postal_city:['Andheri','Bandra'],postal_code:['400001','400002']};else if(u.pathname==='/api/companies')data={rows:[],total:0,page:1,per_page:25};else if(u.pathname==='/api/overview')data={summary:{companies:0},groups:{district:[],postal_city:[],state:[],industry:[],trends:[],class:[],effective_listing:[],capital:[],status:[]}};return {ok:true,status:200,json:async()=>data};}''')
 page.add_script_tag(content=Path('intelligence/static/app.js').read_text());page.wait_for_timeout(200)
 page.get_by_role('button',name='State',exact=True).click();page.get_by_role('searchbox',name='Search State',exact=True).fill('maha');page.get_by_role('option',name='Maharashtra',exact=True).click();page.wait_for_timeout(200)
 assert page.locator('[name=state]').input_value()=='Maharashtra'
 district=page.locator('[name=city]').locator('..').locator('.filter-dropdown-trigger');district.click();page.get_by_role('option',name='Mumbai',exact=True).click();assert page.locator('[name=city]').input_value()=='Mumbai'
 city=page.locator('[name=postal_city]').locator('..').locator('.filter-dropdown-trigger');city.click();page.get_by_role('option',name='Andheri',exact=True).click();assert page.locator('[name=postal_city]').input_value()=='Andheri'
 pin=page.locator('[name=postal_code]').locator('..').locator('.filter-dropdown-trigger');pin.click();page.get_by_role('option',name='400001',exact=True).click();assert page.locator('[name=postal_code]').input_value()=='400001'
 page.get_by_role('button',name='Apply filters',exact=True).click();page.wait_for_timeout(100)
 assert page.locator('[name=state]').input_value()=='Maharashtra'
 assert page.locator('[name=city]').input_value()=='Mumbai'
 assert page.locator('[name=postal_city]').input_value()=='Andheri'
 assert page.locator('[name=postal_code]').input_value()=='400001'
 page.get_by_role('button',name='Reset',exact=True).click();page.wait_for_timeout(100)
 assert page.locator('[name=state]').input_value()==''
 assert district.is_disabled()
 page.get_by_role('button',name='State',exact=True).click();page.get_by_role('searchbox',name='Search State',exact=True).fill('guj');page.get_by_role('searchbox',name='Search State',exact=True).press('ArrowDown');page.keyboard.press('Enter');page.wait_for_timeout(100)
 assert page.locator('[name=state]').input_value()=='Gujarat'
 assert not district.is_disabled()
 assert not errors,errors
 print('Dashboard dropdown regression passed: mouse and keyboard selection, location dependencies, apply and reset.')
 b.close()
