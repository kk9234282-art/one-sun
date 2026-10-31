# Vercel public dataset dashboard

The user explicitly authorised publishing all uploaded company data after initially requesting code only. This deployment includes the imported master records and a browser-side read-only interface. The full Flask source is retained for backend development.

## Deploy

Import `kk9234282-art/one-sun` into Vercel, or redeploy the existing project from `main`. Root Directory: repository root. Framework: **Other**. Build: `node scripts/build-preview.mjs`. Output: `public`. No installation command or environment variables are needed. Open the deployment address provided by Vercel.

## Published data

The export contains 32,078 companies unique by CIN from the supplied Maharashtra Agriculture and Allied Activities file. It retains supplied names, CINs, classes, categories, status, registration dates, addresses, state, ROC, PIN code, capital, industry and listing labels. Two nonstandard CIN rows are preserved in a separate exceptions download and excluded from searchable totals.

Records and data-derived statistics are public in GitHub and the deployed site. No accounts, password hashes, session keys, database files, backups, environment secrets or private local paths are included. The source is user-supplied, not independently authenticated. The date 2026-10-31 comes from the filename, not independently verified publication metadata. This subset is not complete Maharashtra or national coverage.

## Functionality

The existing UI uses `static/snapshot.js` for browser-side search, filters, sorting, pagination, profiles, charts, state exploration, research evidence indicators and CSV export of the entire filtered selection. The exported JSON loads once. Company data is rendered as text; spreadsheet formula prefixes are escaped in CSV.

Missing revenue/profit values stay unknown and fail numeric financial thresholds. Only business history is assessable for research scoring. The score is not an official SEBI eligibility test or investment recommendation. LLPs, MSMEs and exchange securities remain separate empty universes because none were supplied; master listing labels do not create fictional security records.

The deployment is public and read-only. Authentication, new imports, historical revisions and Excel export remain features of the full Flask application, not this static site. The source panel links to the checksum/coverage manifest and the separate CIN exceptions file.

## Rebuild and verify

```sh
.venv/bin/python scripts/export_public_dataset.py
node scripts/build-preview.mjs
.venv/bin/python tests/public_snapshot_smoke.py
```

Export only data authorised for publication. The exporter uses an explicit field allowlist and strips local source paths. The build works in a clean checkout without SQLite or Python. It verifies the exported JSON checksum and unique CIN count before copying the deployment and static UI assets to `public/`.

The browser test serves the actual export over local HTTP without Flask APIs and checks totals, pagination, search, profiles, filtered CSV, class/listing filters, exclusion of unknown financial values, source display and mobile layout. A successful build is not proof of a completed hosted Vercel deployment; that is managed by the user's Vercel project.
