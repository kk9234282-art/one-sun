/* Disk-backed local ZIP ingestion and queries. No network requests for user data. */
'use strict';
importScripts('csv-worker.js','vendor/fflate.js','locality.js');
(() => {
  function capitalMatches(value,band){
    if(!band)return true;
    switch(band){
      case 'under_1cr':return value!=null&&value<10000000;
      case '1_to_10cr':return value!=null&&value>=10000000&&value<100000000;
      case '10cr_plus':return value!=null&&value>=100000000;
      case 'unknown':return value==null;
      default:throw Error('Invalid paid-up capital range.');
    }
  }

const {CSVStream,normalize,fields,header}=self.AtlasCSV;
const inactive=new Set(['Strike Off','Struck Off','Dormant','Dissolved','Under Liquidation','Inactive','Amalgamated','Converted To Llp','Dissolved (Liquidated)','Dormant Under Section 455','Dissolved Under Section 59(8)','Dissolved Under Section 54']);
let database=null,metadata=null;
const queryCache=new Map();
const done=transaction=>new Promise((resolve,reject)=>{transaction.oncomplete=resolve;transaction.onabort=()=>reject(transaction.error||Error('Local database transaction aborted.'));transaction.onerror=()=>{};});
const result=request=>new Promise((resolve,reject)=>{request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error);});
function open(name,create=false){return new Promise((resolve,reject)=>{const request=indexedDB.open(name,1);request.onupgradeneeded=()=>{
  if(!create){request.transaction.abort();return;}
  const db=request.result,companies=db.createObjectStore('companies',{keyPath:'cin'});
  for(const index of ['name','incorporated','capital','as_of'])companies.createIndex(index,'_keys.'+index);
  db.createObjectStore('metadata');db.createObjectStore('exceptions',{autoIncrement:true});
};request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error||Error('Saved local dataset is unavailable.'));});}
function keys(row){row._keys={name:[row.name,row.cin],incorporated:[row.incorporated?0:1,row.incorporated||'',row.cin],capital:[row.paid_up_capital==null?1:0,row.paid_up_capital||0,row.cin],as_of:[row.as_of,row.cin]};return row;}
function analysisDate(row){return row.incorporated&&row.incorporated!=='1111-11-11'&&row.incorporated<=(row.as_of||new Date().toISOString().slice(0,10))?row.incorporated:null;}
function clean(row){const value=self.AtlasLocality.enrich(row);if(row.incorporated&&!analysisDate(row)){value.source_incorporated=row.incorporated;value.incorporated=null;value.data_quality='Implausible source date retained but withheld from date analyses and age scores; no corrected date inferred.';}delete value._keys;for(const field of ['financial_year','reporting_type','revenue_inr','profit_inr','assets_inr','liabilities_inr','revenue_growth','profit_growth','financial_source','financial_as_of'])value[field]=null;return value;}

// Central directory inspection permits streaming extraction and independent CRC checks.
const crcTable=Array.from({length:256},(_,n)=>{for(let i=0;i<8;i++)n=n&1?0xedb88320^(n>>>1):n>>>1;return n>>>0;});
function crcStep(crc,bytes){for(const byte of bytes)crc=crcTable[(crc^byte)&255]^(crc>>>8);return crc;}
async function zipDirectory(file){
  const tail=new Uint8Array(await file.slice(Math.max(0,file.size-65557)).arrayBuffer()),view=new DataView(tail.buffer);let end=-1;
  for(let i=tail.length-22;i>=0;i--)if(view.getUint32(i,true)===0x06054b50&&i+22+view.getUint16(i+20,true)===tail.length){end=i;break;}
  if(end<0)throw Error('ZIP central directory not found. Choose a complete standard ZIP file.');
  if(view.getUint16(end+4,true)!==0||view.getUint16(end+6,true)!==0)throw Error('Multi-volume ZIP archives are unsupported.');
  const count=view.getUint16(end+10,true),size=view.getUint32(end+12,true),offset=view.getUint32(end+16,true);
  if(count===65535||size===0xffffffff||offset===0xffffffff)throw Error('ZIP64 archives are unsupported in this local loader. Use standard ZIP with CSV files smaller than 4 GiB each.');
  if(size>32*1024*1024||offset+size>file.size)throw Error('Invalid or oversized ZIP central directory.');
  const bytes=new Uint8Array(await file.slice(offset,offset+size).arrayBuffer()),central=new DataView(bytes.buffer),decoder=new TextDecoder('utf-8',{fatal:true}),entries=new Map();let position=0,total=0;
  for(let n=0;n<count;n++){
    if(position+46>bytes.length||central.getUint32(position,true)!==0x02014b50)throw Error('Corrupt ZIP directory.');
    const flags=central.getUint16(position+8,true),method=central.getUint16(position+10,true),crc=central.getUint32(position+16,true),uncompressed=central.getUint32(position+24,true);
    const length=central.getUint16(position+28,true),extra=central.getUint16(position+30,true),comment=central.getUint16(position+32,true);
    const name=decoder.decode(bytes.slice(position+46,position+46+length));position+=46+length+extra+comment;
    if(!/\.csv$/i.test(name)||name.startsWith('__MACOSX/')||name.split('/').pop().startsWith('.'))continue;
    if(flags&1)throw Error('Encrypted ZIP entries are unsupported.');
    if(![0,8].includes(method))throw Error('Only stored or DEFLATE-compressed CSV entries are supported.');
    if(uncompressed===0xffffffff)throw Error('A ZIP64 CSV entry is unsupported.');
    if(entries.has(name))throw Error('Duplicate ZIP member names make source verification ambiguous: '+name);
    entries.set(name,{name,crc,uncompressed});total+=uncompressed;
  }
  if(!entries.size)throw Error('No CSV files found in this ZIP.');
  return {entries,total};
}
async function ingestZip({file,asOf,name}){await self.AtlasLocality.ready;
  if(!/^atlas-india-[a-zA-Z0-9-]+$/.test(name))throw Error('Invalid local database name.');
  if(!/^\d{4}-\d{2}-\d{2}$/.test(asOf)||!Number.isFinite(Date.parse(asOf))||new Date(asOf).toISOString().slice(0,10)!==asOf||asOf>new Date().toISOString().slice(0,10))throw Error('Choose a valid snapshot date label, not in the future.');
  const {entries,total}=await zipDirectory(file);
  const storage=await navigator.storage?.estimate?.();
  if(storage?.quota&&total>storage.quota-(storage.usage||0))throw Error('The archive expands beyond available browser storage. Free browser disk space or use the persistent-server importer.');
  database=await open(name,true);
  let pending=[],exceptions=[],accepted=0,rejected=0,duplicates=0,compressed=0,completed=0,failure=null;
  const files=[];
  async function flush(){
    if(!pending.length&&!exceptions.length)return;
    const rows=pending;pending=[];const errors=exceptions;exceptions=[];
    const tx=database.transaction(['companies','exceptions'],'readwrite'),finished=done(tx),store=tx.objectStore('companies');
    // Preserve input order, including duplicates within a single transaction.
    const batches=new Map();for(const row of rows){if(batches.has(row.cin))duplicates++;batches.set(row.cin,{...(batches.get(row.cin)||{}),...Object.fromEntries(Object.entries(row).filter(([,v])=>v!==null))});}
    for(const row of batches.values()){
      const request=store.get(row.cin);request.onsuccess=()=>{const previous=request.result;if(previous)duplicates++;const merged={...(previous||{}),...row};for(const field of fields)if(!(field in merged))merged[field]=null;if(!merged.effective_listing)merged.effective_listing='unknown';store.put(keys(merged));};
    }
    for(const error of errors)tx.objectStore('exceptions').add(error);
    await finished;
  }
  const unzip=new fflate.Unzip(entry=>{
    const expected=entries.get(entry.name);if(!expected)return;
    let names=null,headers=null,record=0,fileAccepted=0,fileRejected=0,crc=0xffffffff,length=0,skipped=false;
    const decoder=new TextDecoder('utf-8',{fatal:true});
    const parser=new CSVStream(values=>{
      record++;
      if(!names){headers=values;names=values.map(header);if(new Set(names).size!==names.length)throw Error('Duplicate headers in '+entry.name);if(!names.includes('cin')||!names.includes('name')){skipped=true;}return;}
      if(skipped)return;
      try{const valuesOut=normalize(values,names,asOf),row=Object.fromEntries(fields.map((field,i)=>[field,valuesOut[i]]));row.source_file=entry.name;pending.push(row);accepted++;fileAccepted++;}
      catch(error){exceptions.push({source_file:entry.name,source_record:record,reason:error.message,headers,values});rejected++;fileRejected++;}
    });
    entry.ondata=(error,bytes,final)=>{
      if(error){failure=error;return;}
      if(failure)return;
      try{
        length+=bytes.length;if(length>expected.uncompressed)throw Error('Expanded size exceeds directory declaration for '+entry.name);
        crc=crcStep(crc,bytes);parser.feed(decoder.decode(bytes,{stream:!final}),final);
        if(final){if(!names)skipped=true;if(length!==expected.uncompressed||((crc^0xffffffff)>>>0)!==expected.crc)throw Error('ZIP size/CRC verification failed for '+entry.name);completed++;files.push({name:entry.name,accepted:fileAccepted,rejected:fileRejected,skipped,reason:skipped?'No CIN/company-name columns':null});}
      }catch(error){failure=error;}
    };entry.start();
  });
  unzip.register(fflate.UnzipInflate);
  const reader=file.stream().getReader();
  while(true){const {value,done:finished}=await reader.read();if(finished)break;compressed+=value.length;unzip.push(value,false);if(failure)throw failure;await flush();self.postMessage({type:'import-progress',compressed,total:file.size,accepted,rejected,files:completed,fileCount:entries.size});}
  unzip.push(new Uint8Array(0),true);if(failure)throw failure;await flush();
  if(completed!==entries.size)throw Error('Not all CSV members were verified; previous dataset is retained.');
  if(!accepted)throw Error('No structurally valid company records found in the ZIP.');
  self.postMessage({type:'import-progress',compressed:file.size,total:file.size,accepted,rejected,files:completed,fileCount:entries.size,phase:'Building local state and industry statistics…'});
  metadata={normalizer_version:3,name,filename:file.name,asOf,files,accepted,rejected,duplicates,duplicatePolicy:'Later nonempty values in ZIP entry order replace earlier values for the same CIN. Archive order does not certify recency.',expandedBytes:total,createdAt:new Date().toISOString()};
  const combined=new Stats(),states=new Map();
  for await(const rows of batchesOf('cin'))for(const row of rows){combined.add(row);const label=row.state||'Unknown';if(!states.has(label))states.set(label,new Stats());states.get(label).add(row);}
  metadata.stats=combined.output();metadata.stateStats=Object.fromEntries([...states].map(([label,stats])=>[label,stats.output()]));metadata.recordCount=metadata.stats.summary.companies;
  const tx=database.transaction('metadata','readwrite'),finished=done(tx);tx.objectStore('metadata').put(metadata,'active');await finished;
  queryCache.clear();return metadata;
}
function bounds(range,last,direction){if(!last)return range;if(direction==='next')return range?.upper!==undefined?IDBKeyRange.bound(last,range.upper,true,range.upperOpen):IDBKeyRange.lowerBound(last,true);return range?.lower!==undefined?IDBKeyRange.bound(range.lower,last,range.lowerOpen,true):IDBKeyRange.upperBound(last,true);}
async function readBatch(index,range,direction){
  const tx=database.transaction('companies','readonly'),finished=done(tx),store=tx.objectStore('companies'),source=index==='cin'?store:store.index(index);
  let rows;
  if(direction==='next')rows=await result(source.getAll(range,3000));
  else rows=await new Promise((resolve,reject)=>{const output=[],request=source.openCursor(range,'prev');request.onerror=()=>reject(request.error);request.onsuccess=()=>{const cursor=request.result;if(!cursor||output.length===3000){resolve(output);return;}output.push(cursor.value);cursor.continue();};});
  await finished;return rows;
}
async function* batchesOf(index='name',direction='next',initialRange){let last=null;while(true){const range=bounds(initialRange,last,direction),rows=await readBatch(index,range,direction);if(!rows.length)break;yield rows;const row=rows[rows.length-1];last=index==='cin'?row.cin:row._keys[index];if(rows.length<3000)break;}}
class Stats{
  constructor(){this.summary={companies:0,active:0,inactive:0,other_status:0,private:0,public:0,listed:0,unlisted:0,unknown_listing:0,financial_coverage:0,oldest:null,newest:null,llps:0,msmes:0,securities:0,unlinked_securities:0};this.groups=Object.fromEntries(['state','industry','class','status','effective_listing','district','postal_city','trends','capital'].map(key=>[key,new Map()]));}
  add(row){row=self.AtlasLocality.enrich(row);const s=this.summary;s.companies++;s[row.status==='Active'?'active':inactive.has(row.status)?'inactive':'other_status']++;if(row.class==='Private')s.private++;if(row.class==='Public')s.public++;s[row.effective_listing==='listed'?'listed':row.effective_listing==='unlisted'?'unlisted':'unknown_listing']++;if(!s.oldest||row.as_of<s.oldest)s.oldest=row.as_of;if(!s.newest||row.as_of>s.newest)s.newest=row.as_of;for(const field of ['state','industry','class','status','effective_listing','district','postal_city'])this.increment(field,row[field]||'Unknown');if(analysisDate(row))this.increment('trends',analysisDate(row).slice(0,4));this.increment('capital',row.paid_up_capital==null?'Unknown':row.paid_up_capital<1e7?'< ₹1 crore':row.paid_up_capital<1e8?'₹1–10 crore':'≥ ₹10 crore');}
  increment(field,label){const map=this.groups[field];map.set(label,(map.get(label)||0)+1);}
  output(){return {summary:this.summary,groups:Object.fromEntries(Object.entries(this.groups).map(([field,map])=>[field,[...map].map(([label,count])=>({label,count})).sort((a,b)=>field==='trends'?a.label.localeCompare(b.label):b.count-a.count||a.label.localeCompare(b.label))]))};}
}
const weights={revenue_growth:25,profitability:20,financial_stability:20,business_history:15,corporate_compliance:10,industry_prospects:10};
const scoreNotice='Partial research indicator, not an official SEBI IPO eligibility test or investment recommendation. Missing evidence is unscored; points are not normalized to 100.';
function score(row){const age=analysisDate(row)?(Date.now()-Date.parse(analysisDate(row)+'T00:00:00Z'))/(365.2425*86400000):null,points=age===null?null:Math.round(Math.max(0,Math.min(1,age/10))*1500)/100;return {observed_points:points||0,assessable_points:points===null?0:15,maximum:100,factors:Object.fromEntries(Object.entries(weights).map(([key,maximum])=>[key,{maximum,points:key==='business_history'?points:null}])),notice:scoreNotice};}
function matches(row,p){if(!capitalMatches(row.paid_up_capital,p.get('capital_band')))return false;row=self.AtlasLocality.enrich(row);for(const field of ['district','postal_city'])if(p.get(field)){const expected=p.get(field).toLowerCase();if(expected==='(not identified)'?!!row[field]:(row[field]||'').toLowerCase()!==expected)return false;}const city=self.AtlasLocality.derive(row);if(p.get('city')&&(p.get('city').toLowerCase()==='(not identified)'?!!city:(city||'').toLowerCase()!==p.get('city').toLowerCase()))return false;const q=(p.get('q')||'').toLowerCase();if(q&&!row.name.toLowerCase().includes(q)&&!row.cin.toLowerCase().includes(q))return false;for(const field of ['state','industry','class','status','nic','roc','postal_code'])if(p.get(field)&&p.get(field)!==row[field])return false;if(p.get('listing')&&p.get('listing')!==row.effective_listing)return false;for(const field of ['incorporated','as_of']){const value=field==='incorporated'?analysisDate(row):row[field];if(p.get(field+'_from')&&(!value||value<p.get(field+'_from')))return false;if(p.get(field+'_to')&&(!value||value>p.get(field+'_to')))return false;}for(const field of ['min_revenue','min_profit','min_revenue_growth','min_profit_growth'])if(p.get(field))return false;if(p.get('positive_profit')==='1')return false;if(p.get('min_capital')&&(row.paid_up_capital==null||row.paid_up_capital<Number(p.get('min_capital'))))return false;if(p.get('min_age')&&(!analysisDate(row)||(Date.now()-Date.parse(analysisDate(row)+'T00:00:00Z'))/(365.2425*86400000)<Number(p.get('min_age'))))return false;return true;}
function cachedStats(p){let relevant=[...p].filter(([key,value])=>value&&!['page','per_page','sort','direction','reporting_type','fy'].includes(key));if(p.get('status')==='Active'&&metadata.activeStats){relevant=relevant.filter(([key])=>key!=='status');if(!relevant.length)return metadata.activeStats;if(relevant.length===1&&relevant[0][0]==='state')return metadata.activeStateStats[relevant[0][1]]||new Stats().output();return null;}if(!relevant.length)return metadata.stats;if(relevant.length===1&&relevant[0][0]==='state')return metadata.stateStats[relevant[0][1]]||new Stats().output();return null;}
async function ensureActiveStats(){if(metadata.activeStats)return;const stats=new Stats(),states=new Map();for await(const batch of batchesOf('name'))for(const row of batch)if(row.status==='Active'){stats.add(row);if(!states.has(row.state))states.set(row.state,new Stats());states.get(row.state).add(row);}metadata.activeStats=stats.output();metadata.activeStateStats=Object.fromEntries([...states].map(([state,value])=>[state,value.output()]));}
function sortPlan(p){const field=p.get('sort')||'name',direction=p.get('direction')==='desc'?'prev':'next';if(field==='name')return {index:'name',direction};if(field==='cin')return {index:'cin',direction};if(field==='as_of')return {index:'as_of',direction};if(['incorporated','paid_up_capital'].includes(field))return {index:field==='incorporated'?'incorporated':'capital',direction,ranges:[IDBKeyRange.bound([0],[1],false,true),IDBKeyRange.bound([1],[2],false,true)]};if(['revenue_inr','profit_inr','revenue_growth'].includes(field))return {index:'cin',direction:'next'};throw Error('Unsupported sort field.');}
async function scan(p){
  if(['min_revenue','min_profit','min_revenue_growth','min_profit_growth'].some(key=>p.get(key)!==null&&p.get(key)!=='')||p.get('positive_profit')==='1')return {rows:[],total:0,page:Math.max(1,Number(p.get('page'))||1),per_page:Math.min(100,Math.max(1,Number(p.get('per_page'))||25)),stats:new Stats().output()};
  const key=JSON.stringify([...p].sort());if(queryCache.has(key))return queryCache.get(key);
  const promise=(async()=>{const known=cachedStats(p),stats=known?null:new Stats(),plan=sortPlan(p),page=Math.max(1,Number(p.get('page'))||1),perPage=Math.min(100,Math.max(1,Number(p.get('per_page'))||25)),offset=(page-1)*perPage,rows=[];let total=0;
    for(const range of plan.ranges||[undefined])for await(const batch of batchesOf(plan.index,plan.direction,range)){for(const row of batch)if(matches(row,p)){if(total>=offset&&rows.length<perPage)rows.push(clean(row));total++;if(stats)stats.add(row);}if(known&&total>=offset+perPage)return {rows,total:known.summary.companies,page,per_page:perPage,stats:known};}
    return {rows,total:known?known.summary.companies:total,page,per_page:perPage,stats:known||stats.output()};})();
  queryCache.set(key,promise);if(queryCache.size>6)queryCache.delete(queryCache.keys().next().value);try{return await promise;}catch(error){queryCache.delete(key);throw error;}
}
const dataset=()=>[{title:'Local all-India ZIP: '+metadata.filename,scope:`Local database: ${metadata.recordCount.toLocaleString('en-IN')} unique company CINs across ${metadata.stats.groups.state.filter(row=>row.label!=='Unknown').length} supplied state/UT labels. Coverage is determined by the CSV contents, not certified as a national census.`,date_basis:metadata.asOf+' is a user-selected snapshot label, not independently verified publication metadata.',provenance:`${metadata.files.filter(file=>!file.skipped).length} CSV files processed; ${metadata.duplicates} duplicate CIN rows reconciled; ${metadata.rejected} exceptions kept locally. ZIP CRCs verified. No file contents uploaded.`}];
const localityOptionsCache=new WeakMap();
async function request(path){const url=new URL(path,'https://local.invalid'),p=url.searchParams;if(url.pathname==='/api/review-queue')throw Error('The review queue uses the published dataset. Use published data first.');if(['activity_tag','activity_evidence','activity_q','registered_activity_code','registered_activity_q','registered_activity_status'].some(key=>p.get(key)))throw Error('Business activity enrichment applies to the published dataset. Use published data to search business activities.');if(!metadata)throw Error('No completed local ZIP dataset is active.');await self.AtlasLocality.ready;if(p.get('status')==='Active')await ensureActiveStats();
  for(const key of ['min_revenue','min_profit','min_revenue_growth','min_profit_growth','min_capital','min_age'])if(p.get(key)!==null&&p.get(key)!==''&&!Number.isFinite(Number(p.get(key))))throw Error('Numeric filters must be finite.');
  if(url.pathname==='/api/options'){const optionStats=p.get('status')==='Active'?metadata.activeStats:metadata.stats;const result={state:optionStats.groups.state.map(row=>row.label).filter(label=>label!=='Unknown').sort(),industry:optionStats.groups.industry.map(row=>row.label).filter(label=>label!=='Unknown').sort(),class:['Private','Public'],status:optionStats.groups.status.map(row=>row.label).sort(),district:[],nic:[]};result.city=[];result.city_unknown=0;result.roc=[];result.postal_code=[];if(p.get('state')){let cache=localityOptionsCache.get(metadata);if(!cache){cache=new Map();localityOptionsCache.set(metadata,cache);}const optionKey=p.get('state')+'|'+(p.get('city')||'')+'|'+(p.get('status')||'');const saved=cache.get(optionKey);if(saved)return {...result,...saved};const areaLabels=new Set();let areaUnknown=0;const labels=new Set(),rocs=new Set(),pins=new Set();for await(const batch of batchesOf('name'))for(const row of batch)if(row.state===p.get('state')&&(!p.get('status')||row.status===p.get('status'))){if(row.roc)rocs.add(row.roc);if(row.postal_code)pins.add(row.postal_code);const city=self.AtlasLocality.derive(row);if(!p.get('city')||(city||'(Not identified)').toLowerCase()===p.get('city').trim().toLowerCase()){const area=self.AtlasLocality.area(row);if(area)areaLabels.add(area);else areaUnknown++;}if(city)labels.add(city);else result.city_unknown++;}result.city=[...labels].sort();result.roc=[...rocs].sort();result.postal_code=[...pins].sort();result.postal_city=[...areaLabels].sort();result.postal_city_unknown=areaUnknown;cache.set(optionKey,{postal_city:result.postal_city,postal_city_unknown:areaUnknown,city:result.city,city_unknown:result.city_unknown,roc:result.roc,postal_code:result.postal_code});}return result;}
  if(url.pathname==='/api/sources')return {sources:[{id:'user_upload',name:'Local ZIP / user-supplied CSV files',url:'',mode:'local',status:'local',checked_at:null,message:metadata.filename,note:'Records and exceptions are stored in this browser only. No official source verification is implied.'}],imports:[]};
  if(url.pathname.startsWith('/api/records/'))return {rows:[],total:0,page:Number(p.get('page'))||1,per_page:50};
  if(url.pathname.startsWith('/api/company/')){const tx=database.transaction('companies','readonly'),row=await result(tx.objectStore('companies').get(decodeURIComponent(url.pathname.split('/').pop())));if(!row)throw Error('Company not found.');return {company:clean(row),score:score(row),financials:[],field_sources:[],historical_names:[],securities:[],directors:[],filings:[],company_history:[],financial_history:[]};}
  if(url.pathname==='/api/overview'){const known=cachedStats(p);if(known&&!known.groups.district){const geographic=new Stats();for await(const batch of batchesOf('name'))for(const row of batch)if(!p.get('state')||row.state===p.get('state'))geographic.add(row);const groups=geographic.output().groups;known.groups.district=groups.district;known.groups.postal_city=groups.postal_city;}return {...(known||((await scan(p)).stats)),datasets:dataset()};}
  if(url.pathname==='/api/companies'||url.pathname==='/api/screen'){const screen=url.pathname==='/api/screen';if(screen)p.set('listing','unlisted');const {stats,...output}=await scan(p);return screen?{...output,rows:output.rows.map(row=>({...row,research_score:score(row)})),methodology:{weights,notice:scoreNotice}}:output;}
  if(url.pathname==='/api/export.csv'){
    const count=(await scan(p)).total;if(count>50000)throw Error('Local ZIP CSV export is limited to 50,000 selected companies. Narrow the filters; your original ZIP remains unchanged.');
    const cell=value=>{let text=value==null?'':String(value);if(typeof value==='string'&&/^\s*[=+\-@]/.test(text))text="'"+text;return '"'+text.replaceAll('"','""')+'"';};const exportFields=[...new Set([...fields,'postal_city','source_district'])];const lines=[exportFields.map(field=>field==='effective_listing'?'listing_status':field).map(cell).join(',')];for await(const batch of batchesOf('name'))for(const row of batch)if(matches(row,p)){const value=clean(row);lines.push(exportFields.map(field=>cell(value[field])).join(','));}return '\ufeff'+lines.join('\r\n');
  }
  throw Error('This action is unavailable for a local ZIP dataset.');
}
self.onmessage=async event=>{const {id,action,...args}=event.data;try{
  let value;
  if(action==='import'){value=await ingestZip(args);}
  else if(action==='open'){database=await open(args.name);metadata=await result(database.transaction('metadata','readonly').objectStore('metadata').get('active'));if(!metadata)throw Error('This import did not complete. Load the ZIP again.');value=metadata;}
  else if(action==='request')value=await request(args.path);
  else if(action==='report')value={...metadata,stats:undefined,stateStats:undefined};
  else if(action==='exceptions'){const tx=database.transaction('exceptions','readonly');value={total:metadata.rejected,records:await result(tx.objectStore('exceptions').getAll(null,5000)),notice:'First 5,000 exception records at most; all exceptions remain stored locally.'};}
  else throw Error('Unknown local database action.');
  self.postMessage({type:'result',id,value});
}catch(error){self.postMessage({type:'failure',id,message:error.name==='QuotaExceededError'?'Browser storage is full. The previous dataset has been retained.':error.message});}};

})();
