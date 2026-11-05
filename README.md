# Atlas — India Corporate Intelligence

A working authenticated Flask application for traceable corporate research. Company master records, LLPs, MSME registrations, exchange securities and financial statements have separate tables and statistical universes. No company records or financial figures are fabricated. The user-authorised Vercel deployment includes shared all-India company-master records; databases, accounts and credentials remain excluded.

## Shared all-India online dashboard — free static deployment

The shared dataset is now built from the user-published GitHub Release [india-data-v1](https://github.com/kk9234282-art/one-sun/releases/tag/india-data-v1). It contains **3,236,908 unique accepted company CINs across 36 canonical state/UT labels**, from 3,236,964 source rows. Fifty-five malformed CINs and one negative paid-up-capital record are preserved separately, without guessed corrections. No duplicate valid CINs were found. No financial statements were supplied. A separately sourced NSE overlay now adds **2,236 annual statements for 1,198 listed-company CINs**, with FY, reporting basis and source links. Coverage is partial; see [financial data coverage and import requirements](docs/LISTED_FINANCIALS.md).

The website runs on the current Vercel static setup. Code and a small national catalog are on `main`; compressed query/profile chunks are pinned to an immutable commit on the separate `data/india-index-v1` GitHub branch. **Do not merge the data-only branch into main or deploy it as the website.** The Vercel website output is approximately 2 MB; the approximately 419 MB of indexed data stays on GitHub and loads in bounded chunks only when needed. No paid database, serverless query service, Git LFS or new paid plan is used. Provider free-plan rules and usage limits still apply; this is not unlimited hosting.

Visitors do not choose or upload files to browse the shared records. National/state/industry summaries are precomputed, name-sorted directory pages load only the required index chunks, and profiles fetch one checksum-verified bucket. Broad substring searches or complex filters may scan more compressed indices; selecting a state reduces transfer and latency. The worker retains a bounded cache rather than loading the original 1.04 GB CSV dataset into RAM.

Import this repository into Vercel or redeploy `main`. Root Directory: repository root. Framework: **Other**. Build: `node scripts/build-preview.mjs`. Output: `public`. No environment variables or Python dependencies are needed for the static website. The build validates catalog counts and immutable GitHub URLs and excludes bulk data from the website bundle.

Source registration/listing labels are user-supplied and not independently authenticated against MCA/NSE/BSE. The date 2026-10-31 is the filename label, not proof of official publication date. Registered entities are not necessarily operating businesses. The dataset is not certified as an exhaustive national census. Original state labels are retained alongside documented current-name aliases. See [release/validation report](docs/INDIA_RELEASE.md) and [Vercel architecture](docs/VERCEL.md).

Local CSV/ZIP tools remain available as separate browser-only views. **Use published data** switches back to the shared national dataset. Accounts, session keys, local uploads, SQLite files and backups are not published. The full authenticated Flask application's private local database is separate from the national static build cache.

## Large CSV files that cannot be attached in chat

### All-India ZIP archives of CSV files

Use **Open all-India ZIP (CSV files)**, choose the archive directly from your computer, set its snapshot date label and click **Load ZIP into local database**. The loader streams stored/DEFLATE CSV entries, verifies their sizes and CRCs, validates company fields and deduplicates CINs across files. Records are stored in the browser's local database rather than retained as one large in-memory array. The ZIP becomes a separate local dataset; it is not added to the published agriculture subset or assumed to be a verified national census.

Search, state/industry filters, charts, profiles and screening work on local records. **Reopen saved ZIP dataset** restores the completed import after refresh; **Use published data** returns to the server snapshot. Source CSV names, duplicate/rejected/skipped counts and an import report are available. All rejected rows remain stored locally, with a download of the first 5,000 exceptions. No archive contents are uploaded or published.

Use a desktop browser with sufficient free disk space. Standard ZIP is supported; encrypted/multi-volume/ZIP64 archives are rejected with an explanation. Local data persists until browser storage is cleared; it is not a backup. Large filtered CSV exports are capped at 50,000 records. Missing financial information stays unknown. The ZIP decoder is the pinned MIT-licensed fflate 0.8.2 package, whose npm SHA-512 integrity was checked; licence and provenance are retained under `intelligence/static/vendor/`.

Verification: `.venv/bin/python tests/india_zip_browser_smoke.py` checks compressed multi-state fixtures. Add `--large` to test a 253 MB archive containing 225,000 synthetic records, persistent reopening, duplicate/exception handling, checksum rollback, local queries and no upload requests. The user's actual all-India archive has not been inspected or published by these tests.

### Individual CSV files

The Vercel dashboard has **Open a large company CSV from your computer**. Select the original CSV and its snapshot date label, then **Load CSV in this browser**. A streaming worker validates rows and merges by CIN without uploading the file. Use a desktop browser with sufficient available memory. This changes only the current browser tab and is discarded on reload; it does not update the shared deployment.

Choose **Create smaller files for this chat** to automatically prepare normalized CSV parts of at most 8 MiB each. Download and attach those parts in chat to enable permanent import/publication. The parts contain the selected file's unique valid records, not merely the visible page. Duplicate CINs use the last structurally valid row; exceptions are separate. No manual CSV splitting or compression is required.

Tests: `node tests/test_csv_worker.mjs` and `.venv/bin/python tests/large_csv_browser_smoke.py`. The latter uses a temporary synthetic CSV larger than 32 MiB and verifies overlap/deduplication, complete bounded exports, malformed-file rollback, restore and zero upload requests. It does not import or publish synthetic records in the application database.

## Run locally

Python 3.12 and SQLite 3.35+; no Redis, Node build, CDN or external database required. SQLite WAL is suitable for a small research deployment with concurrent readers and one importing writer. National-scale multi-user operations require the database/job architecture described in [operations](docs/OPERATIONS.md).

```sh
cd /workspace/one-sun
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/flask --app wsgi create-user admin
.venv/bin/gunicorn --bind 0.0.0.0:8000 --workers 2 --threads 2 --timeout 120 wsgi:app
```

`create-user` prompts for a password (minimum 12 characters); no default account or password exists. Use `--role analyst` for read-only accounts. The database and a random session key are created under ignored `instance/`; keep that directory persistent. For a production HTTPS deployment, supply a high-entropy `SECRET_KEY` securely and `COOKIE_SECURE=1`. Do not expose the development server publicly. A local development server is available with `.venv/bin/flask --app wsgi run --port 8000`.

## Working features

- Authentication, admin/analyst roles, CSRF validation, password hashing, login throttling and restrictive browser headers.
- Search by name, CIN or historical name; filters, sorting, pagination, company profiles and streaming CSV / Excel exports. Spreadsheet formulas are escaped on export.
- Private/public and listed/unlisted analysis, state and industry charts, incorporation/capital distributions, interactive **schematic state tile map** (not a geographic boundary map).
- Financial year and reporting-basis selection; original units on statements and normalized INR in comparisons. Revenue/profit growth uses the previous consecutive year with a positive base. Unknown values remain NULL.
- Confirmed-unlisted research screening with configurable weights, visible coverage and methodology. No score is a SEBI eligibility determination or investment recommendation.
- Streaming CSV/read-only Excel imports, checksummed duplicate-file detection, CIN/LLPIN validation, foreign-key checks, source publication dates, older-snapshot protection, per-row rejection details and historical revisions.
- Seven source definitions and individual connector functions; automated NSE CSV and configurable OGD REST pagination, with permitted manual import for sources without verified open APIs.

## Import data

Use **Data & imports** as an administrator, download a blank template, and import an authorised CSV/XLSX with a source publication date. Large datasets should use the CLI rather than an HTTP request:

```sh
.venv/bin/flask --app wsgi import-data /path/master.csv --kind companies --source mca --as-of 2025-03-31
.venv/bin/flask --app wsgi import-data /path/llp.xlsx --kind llps --source mca --as-of 2025-03-31
.venv/bin/flask --app wsgi import-data /path/statements.csv --kind financials --source mca --as-of 2025-03-31
.venv/bin/flask --app wsgi probe-sources
.venv/bin/flask --app wsgi sync nse --as-of YYYY-MM-DD
```

Replace `YYYY-MM-DD` with the **actual source publication date**; do not assume retrieval time is publication time. Automated connectors do not run at startup or silently scrape official portals. Set `DATA_GOV_RESOURCE_ID` and `DATA_GOV_API_KEY` from the API documentation for the chosen company-master resource before `sync data_gov`. `--offset` and `--max-pages` control pagination. No example resource ID or API key is invented. Current OGD sync expects company-master fields and preserves unrecognised columns only in the original source file, so review mappings first.

See [import contract](docs/IMPORTS.md) for required fields, units, identifiers and partial-failure behavior. Never import aggregate dashboard counts as individual records. Sources requiring login/CAPTCHA are manual only; obtain permitted exports yourself without bypassing controls.

## Verify

```sh
.venv/bin/python -m pytest -q
node --check intelligence/static/app.js
```

Tests use explicitly synthetic temporary fixtures, never the application's database. Browser verification requires `pip install -r requirements-dev.txt` and system Chromium, then `python tests/browser_smoke.py`. It starts an isolated temporary server, exercises authenticated navigation/import/profile/exports and checks mobile layouts. No official company-data access is implied by passing tests.

## API

Session-authenticated JSON: `GET /api/overview`, `/api/companies`, `/api/company/<cin>`, `/api/screen`, `/api/options`, `/api/records/{securities,llps,msmes}`, `/api/sources`. Company filters include `q`, `state`, `district`, `industry`, `nic`, `class`, `status`, `listing`, `incorporated_from/to`, `as_of_from/to`, `fy`, `reporting_type`, `min_revenue`, `min_revenue_growth`, `min_profit_growth`, `min_capital`, `positive_profit`, `min_age`, `sort`, `direction`, `page`, `per_page` (max 100). Exports use the same filters at `/api/export.csv` and `/api/export.xlsx` (Excel capped at 100,000 rows). Exports from company modules include company records only.

Admin-only writes: `POST /api/import` (multipart: file/kind/source/as_of), `POST /api/sources/<id>/probe`. Supply session CSRF token in `X-CSRF-Token`. Public liveness/database probe: `GET /healthz`. Source probes show reachability, not authentication success, dataset completeness or licence verification.

## Scope and production status

This is a tested initial platform, not a claim of production certification, full Indian market coverage, live exchange quotations, SEBI eligibility evaluation or verified national totals. Financial coverage remains partial and source access varies. NSE filings and verified supplemental Screener tables are supported; BSE/Moneycontrol may deny automated access. The geographic view is a tile map; licensed authoritative GeoJSON boundaries are not bundled. Compliance and industry-prospect score factors remain unassessed. Container deployment, backup restoration, public TLS ingress and load testing must be validated in the target hosting environment before production release.

The dashboard shows only companies whose source status is **Active**. Search, totals, charts, geographic options and CSV exports share this scope. The original archive retains other statuses for audit. Active totals and geographic summaries are precomputed by `scripts/build_active_summary.py` and shipped as a small verified asset.

Active listed financial research is limited to exact CINs with source status `Active` and listing `listed`. Run `scripts/export_active_listed_financials.py` after updating financial data to rebuild the revenue/profit CSV and the remaining-coverage queue. The dashboard coverage card links both files. The CSV retains the latest available annual statement for each CIN and reporting basis, includes original source links, and leaves missing amounts blank. The export does not fetch new financial statements.

Supplemental financial imports use public Screener annual tables after confirming each target CIN in an NSE annual report. The table retrieval date, report dissemination date and rounding provenance are retained separately. See [financial acquisition details](docs/LISTED_FINANCIALS.md).


Web-reported revenue is a separate research field for Active companies with paid-up capital **≥ ₹10 crore**. It contains low-confidence source claims: some use legal-name matches and others reference public CIN profiles. These are not confirmed financial statements. Profiles and CSVs retain the source company name, period, reporting basis (which can be unspecified), observed date, source link and rounding notice. These leads do not enter verified revenue filters, growth or research scores. `scripts/build_web_revenue_research.py` uses existing cached public tables and builds the full high-capital research CSV; it does not perform general web searches. Generated Google links are pending research suggestions, not evidence that a search was performed.

The high-capital CSV has separate columns for imported statement revenue and unverified web revenue. The statement columns prefer the latest standalone report, or use an explicitly labelled consolidated report if no standalone report exists. Amounts are in INR. The CSV is a research queue, not a completed internet search of every company.

Public Tofler profiles can supply dated operating-revenue ranges. These are stored with lower/upper INR bounds and the original claim; an open bound remains blank. No midpoint or exact revenue is invented. Revenue ranges remain unverified research and are excluded from financial filters and scores. The CIN printed on the public profile must match the master. Paid figures, login/challenge pages and service/access/rate barriers are not bypassed.

For direct public-profile collection, `scripts/fetch_tofler_revenue.py` checkpoints each company and stops on access, rate, service or challenge barriers. `--offline` only consolidates existing results; it does not claim the remaining profiles were checked. After a service outage has resolved, `--retry-deferred` can revisit deferred records in an explicitly started new run. `scripts/fetch_screener_research_pages.py` checks known issuer addresses at a paced rate. General search probes and provider barriers appear in the research metadata; unrestricted Internet access does not itself provide a search API or guarantee public revenue for every company.

Business activity search now separates the registered industry/CIN code from source-described operations. The initial batch has **1,143 descriptions across 38 tags**, with **255 CIN-checked company matches** and **888 unverified name-match leads**. Profiles retain source and retrieval date; filters can restrict the evidence level. The rest remain marked Needs research. See [method, coverage and expansion workflow](docs/BUSINESS_ACTIVITIES.md).

The bulk CIN reference lookup now covers all **3,236,908** records. It finds registration-activity candidates for **2,147,644 Active companies**; **41,772 Active codes remain unresolved**. Multiple meanings and broad matches are labelled, and no company NIC edition or current business is assumed. See [CIN coverage, sources and interpretation rules](docs/CIN_ACTIVITIES.md).

Results now explain **Why this matches**, and profiles support sourced manual activity reviews with revision history. Public-site reviews are saved privately in the current browser; the authenticated Flask app supports shared SQLite reviews. Both storage scopes are labelled. No paid services or background requests were added. See [review storage, resource limits and workflow](docs/ACTIVITY_REVIEWS.md).

The **Needs review** queue compares broad industry, CIN candidates and source descriptions for **439,623 ambiguous Active companies**. It prioritizes **246 available source descriptions**, then paid-up capital, and tracks Pending/Manually reviewed progress from saved review status. Queue files load only on demand in small pages; no background jobs or paid services were added. See [queue workflow, progress scope and resource limits](docs/REVIEW_QUEUE.md).
