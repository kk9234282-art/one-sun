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

### Local all-India ZIP database

**Open all-India ZIP (CSV files)** accepts the archive directly from the user's computer. `india-worker.js` streams CSV data through a pinned, integrity-verified fflate decoder, compares expanded sizes/CRCs against the ZIP central directory and stores validated records in IndexedDB in bounded batches. No local archive data is sent to Vercel or GitHub. Non-company CSVs are reported as skipped; malformed company rows are recorded as exceptions. Duplicate CINs across files are reconciled rather than summed.

The new local dataset is activated only after extraction, validation and statistics finish. A failed or cancelled import retains the previously completed dataset. Metadata and state aggregates are persisted, records are queried in disk-backed batches, and profiles fetch by CIN. Reopen the completed local dataset after refresh with **Reopen saved ZIP dataset**; **Use published data** switches back without deleting the saved import. Browser-origin storage is not a backup and may be cleared by the user or browser. Sufficient free disk space is required.

The ZIP is a separate dataset, not a sum of its companies and the published subset. State/NIC/financial classifications are not inferred. Queries never turn missing financials into zero. CSV downloads in ZIP mode require at most 50,000 filtered records. All exceptions remain in the local database; the available exceptions download is capped at 5,000 with explicit total/limit metadata. The import report records source member names and skipped/accepted/rejected/duplicate counts.

Supported: standard single-volume ZIP with stored or DEFLATE-compressed UTF-8 CSV files. Encrypted and ZIP64 archives are explicitly unsupported. No source files are extracted into the application's filesystem. The package licence and verified npm tarball integrity are documented in `static/vendor/`.

The small compressed-archive and large 253,533,231-byte ZIP browser tests passed. The latter exercised 225,000 synthetic companies across five state labels, local persistence/reopening, state queries, profiles, CSV export, duplicate handling and CRC-error rollback with zero upload requests. These fixtures do not verify the contents or completeness of the user's actual archive.

### Open a CSV larger than the chat transfer limit

Expand **Open a large company CSV from your computer**, select the file, confirm the snapshot date label and click **Load CSV in this browser**. The file is streamed in a worker without sending its contents to Vercel or the chat. Valid records merge by CIN; older snapshots do not overwrite newer records. Duplicate rows in the selected file use the last structurally valid row. Entire-file parse errors discard the pending load; **Cancel reading** and **Restore published data** are available.

The local load updates search, charts, profiles and exports in that tab only. It disappears on reload. This is not a server import or a persistent publication. Browser memory limits still apply; desktop use is recommended for large datasets. CSV must be UTF-8. Only mapped company-master fields are transferred; the original source file should be retained for any unrecognized columns or later reprocessing.

**Create smaller files for this chat** prepares download buttons for normalized CSV parts at most 8 MiB each, plus a separate exceptions file when needed. These parts contain all distinct valid records from the selected file, not the whole combined browser dataset. Download each part and attach it in chat so the backend import and shared publication can be completed. No automatic upload or GitHub write occurs from the browser.

Parser validation covers quoted commas/newlines/escaped quotes, BOM, CRLF across streamed chunks, CINs, class, date and capital formats. It preserves original registered class and textual industry labels, keeps missing financials unknown, and reports nonstandard CINs rather than correcting them.

```sh
.venv/bin/python scripts/export_public_dataset.py
node scripts/build-preview.mjs
.venv/bin/python tests/public_snapshot_smoke.py
```

Export only data authorised for publication. The exporter uses an explicit field allowlist and strips local source paths. The build works in a clean checkout without SQLite or Python. It verifies the exported JSON checksum and unique CIN count before copying the deployment and static UI assets to `public/`.

The browser test serves the actual export over local HTTP without Flask APIs and checks totals, pagination, search, profiles, filtered CSV, class/listing filters, exclusion of unknown financial values, source display and mobile layout. A successful build is not proof of a completed hosted Vercel deployment; that is managed by the user's Vercel project.
