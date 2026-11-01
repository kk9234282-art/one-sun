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
  const html=await readFile(new URL('../deployment/index.html',import.meta.url),'utf8');
  if(!html.includes('data-online-catalog="/national/catalog.json"'))throw Error('National HTML entry point is missing.');
  const output=new URL('../public/',import.meta.url);await rm(output,{recursive:true,force:true});await mkdir(new URL('national/',output),{recursive:true});
  await writeFile(new URL('index.html',output),html);
  await cp(new URL('../deployment/national/catalog.json',import.meta.url),new URL('national/catalog.json',output));
  await cp(new URL('../deployment/national/source-report.json',import.meta.url),new URL('national/source-report.json',output));
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
