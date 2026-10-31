import { cp, mkdir, readFile, writeFile } from 'node:fs/promises';

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
