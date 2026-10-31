# Atlas — India Corporate Intelligence

A working authenticated Flask application for traceable corporate research. Company master records, LLPs, MSME registrations, exchange securities and financial statements have separate tables and statistical universes. No company records or financial figures are fabricated. The user-authorised Vercel deployment includes the imported company records; databases, accounts and credentials remain excluded.

## Deploy the public dataset dashboard on Vercel

Import `kk9234282-art/one-sun` into Vercel and deploy `main` from the repository root. Framework is **Other**, build command `node scripts/build-preview.mjs`, output directory `public`. No environment variables or Python dependencies are needed for this deployment.

The user explicitly authorised publication of the uploaded company data. The deployment now includes **all 32,078 imported companies** from the Maharashtra Agriculture and Allied Activities subset, with browser-side search, filters, sorting, pagination, profiles, charts, research indicators and filtered CSV export. Two nonstandard CIN rows are preserved separately in `deployment/data/cin-exceptions.csv`. This is not complete Maharashtra or national coverage. Listing labels come from the supplied file; no revenue or profit figures were supplied.

`deployment/data/manifest.json` records coverage, record count and SHA-256 of the published data. The date 2026-10-31 is the filename's snapshot label, not an independently verified publication date. The build verifies the checksum and unique CIN count. It never opens the local SQLite database.

The deployed dashboard is public and read-only. Login, new imports, database revisions and financial-statement management require the full Flask application. No user accounts, passwords, session keys, databases or backups are published. See [Vercel details](docs/VERCEL.md).

To refresh the authorised public export from your local database, run `.venv/bin/python scripts/export_public_dataset.py`, review `deployment/`, then commit and push. Use this command only for data authorised for publication. `scripts/export_preview.py` still generates a separate data-free design preview by default; `--include-data` creates an ignored private local snapshot.

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

This is a tested initial platform, not a claim of production certification, full Indian market coverage, live exchange quotations, SEBI eligibility evaluation or verified national totals. Remote data ingestion remains blocked pending environment network configuration and resource-specific authorisation. The geographic view is a tile map; licensed authoritative GeoJSON boundaries are not bundled. Compliance and industry-prospect score factors remain unassessed. Container deployment, backup restoration, public TLS ingress and load testing must be validated in the target hosting environment before production release.
