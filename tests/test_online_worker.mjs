import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {gzipSync} from 'node:zlib';
import {createHash,webcrypto} from 'node:crypto';
import vm from 'node:vm';

const fields=['cin','name','class','registered_class','category','status','incorporated','state','industry','authorised_capital','paid_up_capital','effective_listing'];
const dictionaries={class:[null,'Private','Public'],registered_class:[null,'Private','Public'],category:[null,'Shares'],status:[null,'Active','Strike Off'],state:[null,'Maharashtra','Gujarat'],industry:[null,'Testing'],effective_listing:[null,'listed','unlisted']};
const raw=[
 ['U12345MH2010PTC000001','ALPHA ONE',1,1,1,1,'2010-01-01',1,1,1000000000,0,1],
 ['U12345GJ2010PLC000002','ALPHA TWO',2,2,1,1,'2010-01-01',2,1,1000000000,10000000,2],
 ['U12345MH2011PTC000003','BETA THREE',1,1,1,2,'2011-01-01',1,1,100,null,2],
 ['U12345GJ2012PLC000004','GAMMA FOUR',2,2,1,1,'2012-01-01',2,1,1000000000,100000000,2]
];
const files=new Map();
function asset(path,rows){const bytes=gzipSync(JSON.stringify(rows));files.set('https://fixture.invalid/national/'+path,bytes);return {path,rows:rows.length,sha256:createHash('sha256').update(bytes).digest('hex')};}
function stats(rows){return {summary:{companies:rows.length,active:rows.filter(row=>row[5]===1).length,inactive:rows.filter(row=>row[5]===2).length,other_status:0,private:rows.filter(row=>row[2]===1).length,public:rows.filter(row=>row[2]===2).length,listed:rows.filter(row=>row[11]===1).length,unlisted:rows.filter(row=>row[11]===2).length,unknown_listing:0,oldest:'2026-10-31',newest:'2026-10-31',financial_coverage:0,llps:0,msmes:0,securities:0,unlinked_securities:0},groups:Object.fromEntries(['state','industry','class','status','effective_listing','trends','capital'].map(field=>[field,[]]))};}
function bucket(cin){let hash=2166136261;for(const c of cin)hash=Math.imul(hash^c.charCodeAt(0),16777619)>>>0;return hash%1024;}
const globalChunks=[asset('index/a.gz',raw.slice(0,2)),asset('index/b.gz',raw.slice(2))];
const catalog={schema_version:2,publication_mode:'authorised-public-dataset',record_count:4,as_of:'2026-10-31',index_fields:fields,full_fields:[...fields,'address','registered_state','source_file','as_of','source_id','postal_code'],dictionaries,source:{source_url:'https://fixture.invalid/source',notice:'Synthetic test only'},stats:stats(raw),global_chunks:globalChunks,states:{},industries:{Testing:stats(raw)},profile_buckets:{},datasets:[]};
for(const [id,state]of [[1,'Maharashtra'],[2,'Gujarat']]){const rows=raw.filter(row=>row[7]===id);catalog.states[state]={stats:stats(rows),chunks:[asset('state/'+id+'.gz',rows)]};}
for(const row of raw){const values=row.map((value,i)=>dictionaries[fields[i]]?dictionaries[fields[i]][value]:value);values.push('Synthetic address','Original state','synthetic.csv','2026-10-31','user_upload',row[7]===1?(row[0]===raw[0][0]?'411001':null):'380001');catalog.profile_buckets[String(bucket(row[0]))]=asset('profile/'+row[0]+'.gz',[values]);}
catalog.facets={class:{Private:stats(raw.filter(row=>row[2]===1)),Public:stats(raw.filter(row=>row[2]===2))},effective_listing:{listed:stats(raw.filter(row=>row[11]===1)),unlisted:stats(raw.filter(row=>row[11]===2))}};
catalog.date_quality={[raw[2][0]]:'1111-11-11'};
catalog.data_commit='fixture-commit';
const stateChunk=catalog.states.Maharashtra.chunks[0];
const cityChunk=asset('cities/map.gz',[[1,1,'411001'],[0,2,'999999']]);cityChunk.cin_order_sha256=createHash('sha256').update(raw.filter(row=>row[7]===1).map(row=>row[0]).join('\n')).digest('hex');
const cityBody=Buffer.from(JSON.stringify({source_data_commit:catalog.data_commit,mapping_version:2,labels:[null,'Pune'],rocs:[null,'ROC Mumbai','ROC Pune'],postal_codes:['411001','999999'],counts:[1,1],geography:{district:[{label:'Pune',count:1},{label:'Not identified',count:1}],postal_city:[{label:'Pune City',count:1},{label:'Not identified',count:1}]},areas_by_district:{Pune:[{label:'Pune City',count:1}]},chunks:{[stateChunk.path]:cityChunk}}));
files.set('https://fixture.invalid/national/cities/state.json',cityBody);
catalog.locations={base_url:'https://fixture.invalid/national/',states:{Maharashtra:{path:'cities/state.json',sha256:createHash('sha256').update(cityBody).digest('hex')}}};
catalog.locations.global_chunks={};
for(let i=0;i<globalChunks.length;i++){const descriptor=asset('cities/global'+i+'.gz',i===0?['411001','380001']:['999999','380001']);descriptor.cin_order_sha256=createHash('sha256').update(raw.slice(i*2,i*2+2).map(row=>row[0]).join('\n')).digest('hex');catalog.locations.global_chunks[globalChunks[i].path]=descriptor;}
const listedRows=raw.filter(row=>row[11]===1).map(row=>{const values=row.map((value,i)=>dictionaries[fields[i]]?dictionaries[fields[i]][value]:value);return [...values,'Synthetic address','Original state','synthetic.csv','2026-10-31','user_upload','411001'];});
catalog.listed_index={...asset('listed/companies.gz',listedRows),source_data_commit:catalog.data_commit,full_fields:catalog.full_fields};
files.set('https://fixture.invalid/national/catalog.json',Buffer.from(JSON.stringify(catalog)));
files.set('/static/pin-districts.json',await readFile(new URL('../intelligence/static/pin-districts.json',import.meta.url)));
const waiting=new Map(),requested=[];let sequence=0;
const context={URL,TextEncoder,TextDecoder,Response,crypto:webcrypto,location:{origin:'https://fixture.invalid'},fetch:async url=>{requested.push(String(url));const body=files.get(String(url));return new Response(body||'',{status:body?200:404});},postMessage:message=>{if(message.type==='query-progress')return;const waiter=waiting.get(message.id);waiting.delete(message.id);if(message.type==='failure')waiter.reject(Error(message.message));else waiter.resolve(message.value);}};
context.self=context;vm.createContext(context);
context.importScripts=(...paths)=>{for(const path of paths)vm.runInContext(path==='locality.js'?locality:path==='financials.js'?financialCode:vendor,context);};
const financialCode=await readFile(new URL('../intelligence/static/financials.js',import.meta.url),'utf8');
const locality=await readFile(new URL('../intelligence/static/locality.js',import.meta.url),'utf8');
const vendor=await readFile(new URL('../intelligence/static/vendor/fflate.js',import.meta.url),'utf8');
vm.runInContext(await readFile(new URL('../intelligence/static/online-worker.js',import.meta.url),'utf8'),context);
const call=(action,args={})=>new Promise((resolve,reject)=>{const id=++sequence;waiting.set(id,{resolve,reject});context.onmessage({data:{id,action,...args}});});
await call('init',{url:'/national/catalog.json'});
const request=path=>call('request',{path});
const fast=await request('/api/companies?listing=listed&capital_band=under_1cr');assert.equal(fast.total,1);assert.equal(fast.rows[0].cin,raw[0][0]);
assert.equal((await request('/api/overview?listing=listed&capital_band=under_1cr')).summary.companies,1);
assert.equal((await request('/api/companies?listing=listed&capital_band=under_1cr&state=Maharashtra&city=Pune&postal_city=Pune%20City')).total,1);
assert.equal((await request('/api/companies?listing=listed&capital_band=under_1cr&class=Public')).total,0);
assert.equal((await request('/api/companies?listing=listed&capital_band=1_to_10cr')).total,0);
const fastCSV=await request('/api/export.csv?listing=listed&capital_band=under_1cr');assert.ok(fastCSV.includes('ALPHA ONE')&&!fastCSV.includes('ALPHA TWO'));
assert.equal((await request('/api/companies?listing=listed&capital_band=under_1cr&page=2&per_page=1')).rows.length,0);
assert.deepEqual(requested.filter(url=>url.endsWith('.gz')),['https://fixture.invalid/national/listed/companies.gz'],'Listed queries and export must never scan national indices, PIN maps or profiles.');

assert.equal((await request('/api/overview')).summary.companies,4);
assert.equal((await request('/api/overview?class=Public')).summary.companies,2);
assert.equal((await request('/api/overview?listing=listed')).summary.companies,1);
let result=await request('/api/companies?per_page=1&page=3');assert.equal(result.rows[0].name,'BETA THREE');assert.equal(result.total,4);
result=await request('/api/companies?state=Gujarat');assert.equal(result.total,2);assert.equal(result.rows[0].state,'Gujarat');
result=await request('/api/companies?q=ALPHA');assert.equal(result.total,2);
assert.equal((await request('/api/overview?q=ALPHA')).summary.companies,2);
result=await request('/api/companies?sort=paid_up_capital&direction=desc&per_page=3');assert.deepEqual([...result.rows.map(row=>row.paid_up_capital)],[100000000,10000000,0]);
assert.equal((await request('/api/companies?min_revenue=0')).total,0);
assert.equal((await request('/api/screen')).total,3);
const profile=await request('/api/company/'+raw[0][0]);assert.equal(profile.company.address,'Synthetic address');assert.equal(profile.company.as_of,'2026-10-31');assert.equal(profile.company.revenue_inr,null);
const questionable=await request('/api/company/'+raw[2][0]);assert.equal(questionable.company.incorporated,null);assert.equal(questionable.company.source_incorporated,'1111-11-11');assert.equal(questionable.score.assessable_points,0);
assert.equal((await request('/api/companies?q=BETA&min_age=1')).total,0);
const csv=await request('/api/export.csv?q=ALPHA');assert.ok(csv.includes('ALPHA ONE')&&csv.includes('ALPHA TWO')&&!csv.includes('BETA THREE'));
await assert.rejects(()=>request('/api/companies?min_capital=NaN'),/finite/);
assert.equal((await request('/api/companies?state=Maharashtra&city=Pune')).total,1);
assert.equal((await request('/api/overview?state=Maharashtra&city=Pune')).summary.companies,1);
assert.equal((await request('/api/companies?state=Maharashtra&city=(Not%20identified)')).total,1);
assert.equal((await request('/api/companies?state=Maharashtra&city=Missing')).total,0);
assert.deepEqual([...(await request('/api/options?state=Maharashtra')).city],['Pune']);
assert.ok((await request('/api/export.csv?state=Maharashtra&city=Pune')).includes('ALPHA ONE'));
assert.equal((await request('/api/companies?state=Maharashtra&city=Pune&roc=ROC%20Mumbai&postal_code=411001')).total,1);
assert.equal((await request('/api/companies?state=Maharashtra&city=Pune&roc=ROC%20Pune')).total,0);
assert.equal((await request('/api/companies?state=Maharashtra&postal_code=999999')).rows[0].name,'BETA THREE');
const initial=(await request('/api/companies?per_page=1')).rows[0];assert.equal(initial.district,'Pune');assert.equal(initial.postal_city,'Pune City');
const geo=await request('/api/overview?state=Maharashtra&city=Pune');assert.equal(geo.groups.postal_city[0].label,'Pune City');assert.equal(geo.groups.postal_city.reduce((n,row)=>n+row.count,0),geo.summary.companies);
assert.equal((await request('/api/companies?state=Maharashtra&city=Pune&postal_city=Pune%20City')).total,1);
assert.equal((await request('/api/companies?state=Maharashtra&city=Pune&postal_city=Baramati')).total,0);
for(const band of ['under_1cr','1_to_10cr','10cr_plus','unknown']){assert.equal((await request('/api/companies?capital_band='+band)).total,1);assert.equal((await request('/api/overview?capital_band='+band)).summary.companies,1);}
const middle=await request('/api/export.csv?capital_band=1_to_10cr');assert.ok(middle.includes('ALPHA TWO')&&!middle.includes('ALPHA ONE')&&!middle.includes('GAMMA FOUR'));
await assert.rejects(()=>request('/api/companies?capital_band=invalid'),/Invalid paid-up capital range/);
// Financial overlay fixtures are synthetic and exist only in this in-memory worker test.
const annual=changes=>({cin:raw[0][0],financial_year:2025,reporting_type:'standalone',unit:'INR lakh',period_end:'2025-03-31',period_months:12,revenue:150,net_profit:-2,assets:null,liabilities:null,expenses:null,ebitda:null,source_id:'bse',source_url:'https://www.bseindia.com/synthetic-test.pdf',as_of:'2025-05-20',...changes});
catalog.financials={...asset('financials/statements.gz',[annual({}),annual({financial_year:2024,period_end:'2024-03-31',as_of:'2024-05-20',unit:'INR crore',revenue:1,net_profit:0.1}),annual({reporting_type:'consolidated',unit:'INR crore',revenue:2,net_profit:0})]),schema_version:1,source_data_commit:catalog.data_commit};
files.set('https://fixture.invalid/national/catalog.json',Buffer.from(JSON.stringify(catalog)));await call('init',{url:'/national/catalog.json'});
let financial=(await request('/api/companies?listing=listed&capital_band=under_1cr')).rows[0];assert.equal(financial.revenue_inr,15000000);assert.equal(financial.profit_inr,-200000);assert.equal(financial.revenue_growth,50);assert.equal(financial.profit_growth,-120);assert.equal(financial.financial_year,2025);
financial=(await request('/api/companies?listing=listed&reporting_type=consolidated')).rows[0];assert.equal(financial.revenue_inr,20000000);assert.equal(financial.profit_inr,0);
financial=(await request('/api/companies?listing=listed&fy=2024')).rows[0];assert.equal(financial.revenue_inr,10000000);assert.equal(financial.financial_year,2024);
financial=(await request('/api/companies?listing=listed&fy=2023')).rows[0];assert.equal(financial.revenue_inr,null);
assert.equal((await request('/api/companies?min_revenue=12000000')).total,1);
assert.equal((await request('/api/companies?listing=listed&positive_profit=1')).total,0);
assert.equal((await request('/api/companies?listing=listed&positive_profit=1&fy=2024')).total,1);
assert.equal((await request('/api/overview')).summary.financial_coverage,1);
assert.equal((await request('/api/overview?listing=listed&fy=2023')).summary.financial_coverage,0);
const financialProfile=await request('/api/company/'+raw[0][0]);assert.equal(financialProfile.financials.length,3);assert.equal(financialProfile.company.revenue_inr,15000000);assert.equal(financialProfile.score.assessable_points,60);assert.equal(financialProfile.score.factors.profitability.points,0);
const financialCSV=await request('/api/export.csv?listing=listed');assert.ok(financialCSV.includes('revenue_inr')&&financialCSV.includes('15000000')&&financialCSV.includes('-200000')&&financialCSV.includes('https://www.bseindia.com/synthetic-test.pdf'));
console.log('National online worker tests passed: paginated/state/search queries, numeric sort, profiles, missing financials, screening and filtered CSV.');
