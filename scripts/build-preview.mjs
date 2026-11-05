import { cp, mkdir, readFile, writeFile, rm } from 'node:fs/promises';

// National data lives in a separate immutable GitHub branch, not the site bundle.
let national;
try{national=JSON.parse(await readFile(new URL('../deployment/national/catalog.json',import.meta.url),'utf8'));}
catch(error){if(error.code!=='ENOENT')throw error;}
if(national){
  if(national.schema_version!==2||national.publication_mode!=='authorised-public-dataset')throw Error('Invalid national catalog.');
  if(!national.date_quality_applied)throw Error('Review and apply the source-date quality policy before deployment.');
  if(!/^https:\/\/raw\.githubusercontent\.com\/[^/]+\/[^/]+\/[a-f0-9]{40}\/deployment\/national\/$/.test(national.base_url||''))throw Error('National data must point to an immutable GitHub commit.');
  if(national.global_chunks.reduce((sum,item)=>sum+item.rows,0)!==national.record_count)throw Error('National index count mismatch.');
  if(Object.values(national.states).reduce((sum,state)=>sum+state.stats.summary.companies,0)!==national.record_count)throw Error('State totals do not reconcile.');
  if(Object.values(national.profile_buckets).reduce((sum,item)=>sum+item.rows,0)!==national.record_count)throw Error('Profile count mismatch.');
  if(national.listed_index){
    const listed=national.listed_index;
    if(listed.source_data_commit!==national.data_commit||listed.rows!==national.stats.summary.listed||JSON.stringify(listed.full_fields)!==JSON.stringify(national.full_fields))throw Error('Listed-company index does not match the national snapshot.');
    if(!/^https:\/\/raw\.githubusercontent\.com\/[^/]+\/[^/]+\/[a-f0-9]{40}\/deployment\/listed\/listed-[a-f0-9]{12}\.json\.gz$/.test(listed.path)||!/^[a-f0-9]{64}$/.test(listed.sha256))throw Error('Listed-company data must use an immutable GitHub URL and checksum.');
  }
  if(national.financials){
    const financial=national.financials;
    if(financial.schema_version!==1||financial.source_data_commit!==national.data_commit||!national.listed_index||!financial.rows||!financial.covered_companies||financial.covered_companies>national.listed_index.rows)throw Error('Financial statements do not match the listed-company snapshot.');
    if(!/^https:\/\/raw\.githubusercontent\.com\/[^/]+\/[^/]+\/[a-f0-9]{40}\/deployment\/financials\/financials-[a-f0-9]{12}\.json\.gz$/.test(financial.path)||!/^[a-f0-9]{64}$/.test(financial.sha256))throw Error('Financial statements must use immutable data and a checksum.');
  }
  if(national.active_summary){
    const descriptor=national.active_summary;
    if(descriptor.source_data_commit!==national.data_commit||descriptor.companies!==national.stats.summary.active||!/^\/national\/active-summary-[a-f0-9]{12}\.json\.gz$/.test(descriptor.path))throw Error('Active-company summary does not match the national source.');
    const body=await readFile(new URL('../deployment'+descriptor.path,import.meta.url));const {createHash}=await import('node:crypto');if(createHash('sha256').update(body).digest('hex')!==descriptor.sha256)throw Error('Active-company summary checksum mismatch.');
  }
  if(national.web_revenue_research){const d=national.web_revenue_research;if(d.source_data_commit!==national.data_commit||!/^\/national\/web-revenue-[a-f0-9]{12}\.json\.gz$/.test(d.path))throw Error('Invalid web revenue research descriptor');const body=await readFile(new URL('../deployment'+d.path,import.meta.url));const {createHash}=await import('node:crypto');if(createHash('sha256').update(body).digest('hex')!==d.sha256)throw Error('Web revenue research checksum mismatch');}
  if(national.activity_review_flags){const d=national.activity_review_flags;if(d.schema_version!==1||d.source_data_commit!==national.data_commit||!/^\/static\/activity-review-flags-[a-f0-9]{12}\.json\.gz$/.test(d.path))throw Error('Invalid activity audit flags descriptor');const body=await readFile(new URL('../intelligence'+d.path,import.meta.url));const {createHash}=await import('node:crypto'),{gunzipSync}=await import('node:zlib');if(createHash('sha256').update(body).digest('hex')!==d.sha256)throw Error('Activity audit flag checksum mismatch');const data=JSON.parse(gunzipSync(body))[0];if(data.source_data_commit!==national.data_commit||data.flags.length!==d.companies||data.queue_overlay.base_manifest_sha256!==national.review_queue?.sha256||data.flags.some(flag=>flag.status!=='needs_primary_evidence'))throw Error('Activity audit flags do not match the queue snapshot');}
  if(national.review_queue){const d=national.review_queue;if(d.schema_version!==1||d.source_data_commit!==national.data_commit||!/^\/review-queue\/manifest-[a-f0-9]{12}\.json\.gz$/.test(d.path))throw Error('Invalid review queue descriptor');const {createHash}=await import('node:crypto'),{gunzipSync}=await import('node:zlib');const verify=async item=>{if(!/^\/review-queue\/[a-z0-9-]+\.json\.gz$/.test(item.path))throw Error('Invalid queue asset path');const body=await readFile(new URL('../deployment'+item.path,import.meta.url));if(createHash('sha256').update(body).digest('hex')!==item.sha256)throw Error('Review queue checksum mismatch');return body;};const meta=JSON.parse(gunzipSync(await verify(d)))[0];if(meta.source_data_commit!==national.data_commit||meta.total!==d.total||meta.chunks.reduce((sum,item)=>sum+item.rows,0)!==meta.total)throw Error('Review queue totals do not reconcile');const files=[...meta.chunks,...meta.membership];for(let i=0;i<files.length;i+=16)await Promise.all(files.slice(i,i+16).map(verify));}
  if(national.cin_activities){const d=national.cin_activities;if(d.schema_version!==1||d.source_data_commit!==national.data_commit||d.companies!==national.record_count||!/^\/static\/cin-activities-[a-f0-9]{12}\.json\.gz$/.test(d.path))throw Error('Invalid CIN activity descriptor');const body=await readFile(new URL('../intelligence'+d.path,import.meta.url));const {createHash}=await import('node:crypto');if(createHash('sha256').update(body).digest('hex')!==d.sha256)throw Error('CIN activity checksum mismatch');const {gunzipSync}=await import('node:zlib');const data=JSON.parse(gunzipSync(body))[0];if(data.source_data_commit!==national.data_commit||data.report.companies_processed!==national.record_count)throw Error('CIN activity snapshot mismatch');}
  if(national.business_activities){const d=national.business_activities;if(d.schema_version!==1||d.source_data_commit!==national.data_commit||!/^\/static\/business-activities-[a-f0-9]{12}\.json\.gz$/.test(d.path))throw Error('Invalid business activity descriptor');const body=await readFile(new URL('../intelligence'+d.path,import.meta.url));const {createHash}=await import('node:crypto');if(createHash('sha256').update(body).digest('hex')!==d.sha256)throw Error('Business activity checksum mismatch');const {gunzipSync}=await import('node:zlib');const data=JSON.parse(gunzipSync(body))[0];if(data.source_data_commit!==national.data_commit||data.records.length!==d.companies)throw Error('Business activity snapshot mismatch');}
  const html=await readFile(new URL('../deployment/index.html',import.meta.url),'utf8');
  if(!html.includes('data-online-catalog="/national/catalog.json"'))throw Error('National HTML entry point is missing.');
  const output=new URL('../public/',import.meta.url);await rm(output,{recursive:true,force:true});await mkdir(new URL('national/',output),{recursive:true});
  await writeFile(new URL('index.html',output),html);
  await cp(new URL('../deployment/national/catalog.json',import.meta.url),new URL('national/catalog.json',output));
  await cp(new URL('../deployment/national/source-report.json',import.meta.url),new URL('national/source-report.json',output));
  if(national.active_summary)await cp(new URL('../deployment'+national.active_summary.path,import.meta.url),new URL(national.active_summary.path.slice(1),output));
  if(national.active_listed_financials)for(const name of ['active-listed-financials.csv','remaining-active-listed-financials.csv','active-listed-financial-coverage.json'])await cp(new URL('../deployment/national/'+name,import.meta.url),new URL('national/'+name,output));
  try{await cp(new URL('../deployment/national/screener-name-source-report.json',import.meta.url),new URL('national/screener-name-source-report.json',output));}catch(error){if(error.code!=='ENOENT')throw error;}
  if(national.financials?.supplementary_sources?.includes('screener'))await cp(new URL('../deployment/national/screener-source-report.json',import.meta.url),new URL('national/screener-source-report.json',output));
  try{await cp(new URL('../deployment/national/financial-source-report.json',import.meta.url),new URL('national/financial-source-report.json',output));}catch(error){if(error.code!=='ENOENT')throw error;}
  if(national.web_revenue_research){const d=national.web_revenue_research;for(const name of [d.path.split('/').pop(),'web-revenue-research-report.json','high-capital-revenue-research.csv',...(d.rows?['unverified-web-revenue.csv']:[])])await cp(new URL('../deployment/national/'+name,import.meta.url),new URL('national/'+name,output));}
  if(national?.review_queue)await cp(new URL('../deployment/review-queue/',import.meta.url),new URL('review-queue/',output),{recursive:true});
  await cp(new URL('../intelligence/static/',import.meta.url),new URL('static/',output),{recursive:true});
  console.log(`Built small national website: ${national.record_count} shared companies; compressed data loads on demand from GitHub.`);
  process.exit(0);
}

// Build an explicitly authorised public export; never open the local database.
const deployment = new URL('../deployment/', import.meta.url);
let manifest;
try {
  manifest = JSON.parse(await readFile(new URL('data/manifest.json', deployment),'utf8'));
} catch(error) {
  if (error.code !== 'ENOENT') throw error;
}
if (manifest) {
  if (manifest.publication_mode !== 'authorised-public-dataset') throw new Error('Missing publication authorisation marker.');
  const content = await readFile(new URL('data/companies.json',deployment));
  const { createHash } = await import('node:crypto');
  if (createHash('sha256').update(content).digest('hex') !== manifest.data_sha256) throw new Error('Dataset checksum mismatch.');
  const data = JSON.parse(content);
  const cinIndex = data.fields.indexOf('cin');
  if (data.rows.length !== manifest.record_count || new Set(data.rows.map(row=>row[cinIndex])).size !== manifest.record_count) throw new Error('Dataset counts do not reconcile.');
  const output = new URL('../public/',import.meta.url);
  await mkdir(output,{recursive:true});
  await cp(deployment,output,{recursive:true});
  if(national?.review_queue)await cp(new URL('../deployment/review-queue/',import.meta.url),new URL('review-queue/',output),{recursive:true});
  await cp(new URL('../intelligence/static/',import.meta.url),new URL('static/',output),{recursive:true});
  console.log(`Built read-only dashboard with ${manifest.record_count} authorised company records.`);
  process.exit(0);
}
const source = new URL('../preview.html', import.meta.url);
const output = new URL('../public/', import.meta.url);
const html = await readFile(source, 'utf8');
if (!html.includes('<style>') || html.includes('{{') || html.includes('{%')) {
  throw new Error('Export a self-contained styled preview before deploying.');
}
if (!html.includes('data-publish-mode="code-only"')) {
  throw new Error('Only the code-only preview may be bundled in this deployment.');
}
await mkdir(output, { recursive: true });
await writeFile(new URL('index.html', output), html, 'utf8');
console.log('Built public/index.html: styled, read-only snapshot. No database or credentials bundled.');
