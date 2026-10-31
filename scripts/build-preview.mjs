import { mkdir, readFile, writeFile } from 'node:fs/promises';

// Build the already exported snapshot; do not open the private local database.
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
