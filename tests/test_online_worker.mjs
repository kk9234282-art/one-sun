import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {gzipSync} from 'node:zlib';
import {createHash,webcrypto} from 'node:crypto';
import vm from 'node:vm';

const fields=['cin','name','class','registered_class','category','status','incorporated','state','industry','authorised_capital','paid_up_capital','effective_listing'];
const dictionaries={class:[null,'Private','Public'],registered_class:[null,'Private','Public'],category:[null,'Shares'],status:[null,'Active','Strike Off'],state:[null,'Maharashtra','Gujarat'],industry:[null,'Testing'],effective_listing:[null,'listed','unlisted']};
const raw=[
 ['U12345MH2010PTC000001','ALPHA ONE',1,1,1,1,'2010-01-01',1,1,100,10,2],
 ['U12345GJ2010PLC000002','ALPHA TWO',2,2,1,1,'2010-01-01',2,1,100,90,1],
 ['U12345MH2011PTC000003','BETA THREE',1,1,1,2,'2011-01-01',1,1,100,null,2],
 ['U12345GJ2012PLC000004','GAMMA FOUR',2,2,1,1,'2012-01-01',2,1,100,40,2]
];
const files=new Map();
function asset(path,rows){const bytes=gzipSync(JSON.stringify(rows));files.set('https://fixture.invalid/national/'+path,bytes);return {path,rows:rows.length,sha256:createHash('sha256').update(bytes).digest('hex')};}
function stats(rows){return {summary:{companies:rows.length,active:rows.filter(row=>row[5]===1).length,inactive:rows.filter(row=>row[5]===2).length,other_status:0,private:rows.filter(row=>row[2]===1).length,public:rows.filter(row=>row[2]===2).length,listed:rows.filter(row=>row[11]===1).length,unlisted:rows.filter(row=>row[11]===2).length,unknown_listing:0,oldest:'2026-10-31',newest:'2026-10-31',financial_coverage:0,llps:0,msmes:0,securities:0,unlinked_securities:0},groups:Object.fromEntries(['state','industry','class','status','effective_listing','trends','capital'].map(field=>[field,[]]))};}
function bucket(cin){let hash=2166136261;for(const c of cin)hash=Math.imul(hash^c.charCodeAt(0),16777619)>>>0;return hash%1024;}
const globalChunks=[asset('index/a.gz',raw.slice(0,2)),asset('index/b.gz',raw.slice(2))];
const catalog={schema_version:2,publication_mode:'authorised-public-dataset',record_count:4,as_of:'2026-10-31',index_fields:fields,full_fields:[...fields,'address','registered_state','source_file','as_of','source_id'],dictionaries,source:{source_url:'https://fixture.invalid/source',notice:'Synthetic test only'},stats:stats(raw),global_chunks:globalChunks,states:{},industries:{Testing:stats(raw)},profile_buckets:{},datasets:[]};
for(const [id,state]of [[1,'Maharashtra'],[2,'Gujarat']]){const rows=raw.filter(row=>row[7]===id);catalog.states[state]={stats:stats(rows),chunks:[asset('state/'+id+'.gz',rows)]};}
for(const row of raw){const values=row.map((value,i)=>dictionaries[fields[i]]?dictionaries[fields[i]][value]:value);values.push('Synthetic address','Original state','synthetic.csv','2026-10-31','user_upload');catalog.profile_buckets[String(bucket(row[0]))]=asset('profile/'+row[0]+'.gz',[values]);}
catalog.facets={class:{Private:stats(raw.filter(row=>row[2]===1)),Public:stats(raw.filter(row=>row[2]===2))},effective_listing:{listed:stats(raw.filter(row=>row[11]===1)),unlisted:stats(raw.filter(row=>row[11]===2))}};
catalog.date_quality={[raw[2][0]]:'1111-11-11'};
files.set('https://fixture.invalid/national/catalog.json',Buffer.from(JSON.stringify(catalog)));
const waiting=new Map();let sequence=0;
const context={URL,TextDecoder,Response,crypto:webcrypto,location:{origin:'https://fixture.invalid'},fetch:async url=>{const body=files.get(String(url));return new Response(body||'',{status:body?200:404});},postMessage:message=>{if(message.type==='query-progress')return;const waiter=waiting.get(message.id);waiting.delete(message.id);if(message.type==='failure')waiter.reject(Error(message.message));else waiter.resolve(message.value);}};
context.self=context;vm.createContext(context);
context.importScripts=()=>vm.runInContext(vendor,context);
const vendor=await readFile(new URL('../intelligence/static/vendor/fflate.js',import.meta.url),'utf8');
vm.runInContext(await readFile(new URL('../intelligence/static/online-worker.js',import.meta.url),'utf8'),context);
const call=(action,args={})=>new Promise((resolve,reject)=>{const id=++sequence;waiting.set(id,{resolve,reject});context.onmessage({data:{id,action,...args}});});
await call('init',{url:'/national/catalog.json'});
const request=path=>call('request',{path});
assert.equal((await request('/api/overview')).summary.companies,4);
assert.equal((await request('/api/overview?class=Public')).summary.companies,2);
assert.equal((await request('/api/overview?listing=listed')).summary.companies,1);
let result=await request('/api/companies?per_page=1&page=3');assert.equal(result.rows[0].name,'BETA THREE');assert.equal(result.total,4);
result=await request('/api/companies?state=Gujarat');assert.equal(result.total,2);assert.equal(result.rows[0].state,'Gujarat');
result=await request('/api/companies?q=ALPHA');assert.equal(result.total,2);
assert.equal((await request('/api/overview?q=ALPHA')).summary.companies,2);
result=await request('/api/companies?sort=paid_up_capital&direction=desc&per_page=3');assert.deepEqual([...result.rows.map(row=>row.paid_up_capital)],[90,40,10]);
assert.equal((await request('/api/companies?min_revenue=0')).total,0);
assert.equal((await request('/api/screen')).total,3);
const profile=await request('/api/company/'+raw[0][0]);assert.equal(profile.company.address,'Synthetic address');assert.equal(profile.company.as_of,'2026-10-31');assert.equal(profile.company.revenue_inr,null);
const questionable=await request('/api/company/'+raw[2][0]);assert.equal(questionable.company.incorporated,null);assert.equal(questionable.company.source_incorporated,'1111-11-11');assert.equal(questionable.score.assessable_points,0);
assert.equal((await request('/api/companies?q=BETA&min_age=1')).total,0);
const csv=await request('/api/export.csv?q=ALPHA');assert.ok(csv.includes('ALPHA ONE')&&csv.includes('ALPHA TWO')&&!csv.includes('BETA THREE'));
await assert.rejects(()=>request('/api/companies?min_capital=NaN'),/finite/);
console.log('National online worker tests passed: paginated/state/search queries, numeric sort, profiles, missing financials, screening and filtered CSV.');
