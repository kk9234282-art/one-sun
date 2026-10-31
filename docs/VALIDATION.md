# Validation record

## Shared national release (current)

The public GitHub release archive was downloaded and its 216,238,578 bytes verified against GitHub SHA-256 `b6dfedff66c92f5eeff0caf5ea0b493c3cba00f6695413bd6a1c1b80fe0979dc`. Five CSV files expanded to 1,043,430,058 bytes. From 3,236,964 source rows, 3,236,908 unique company CINs were accepted; 55 malformed CINs and one negative paid-up-capital record were retained as exceptions; no valid duplicate CINs were found.

All 1,697 compressed chunks were decompressed and checked against their SHA-256 and record counts. Global/state indices, profile buckets, national counts and 36-state totals reconcile. The maximum chunk is 280,367 bytes. The separate data-only GitHub branch was published; an actual public raw chunk returned HTTP 200 with CORS and matched its descriptor SHA-256. The Vercel output contains only the small UI/catalog/source report, under 1 MB, without bulk data or private state.

The actual national static browser test passed: country count, bounded first-page download, state options, pagination, Maharashtra/name search, full profile details, original Orissa/Odisha state preservation, filtered CSV, 56 exceptions, mobile layout and no upload requests. Worker tests passed for search/state/pagination, bounded numeric sorting, missing financials, screening and CSV. The Python suite now has **30 passing tests**, including structural acceptance of additional three-letter CIN constitution codes. No paid service or new paid plan was enabled; hosted Vercel completion is not established by these local checks.

Earlier validation stages below describe their historical scope; the current shared dataset is the national snapshot above, not only the initial agriculture subset or a local browser-only import.

Final date-quality review identified 2,291 implausible incorporation dates among otherwise accepted records. The original values are retained, but incorporation trends/date filters/age scores withhold them without guessed corrections. Precomputed national/state/industry/class/status/listing trend counts were adjusted consistently. Worker and actual-data browser tests verify the raw date remains available while the analysis date and age score become unknown. This does not change the company count or silently rewrite the source chunks.

Validated in the current cloud machine on 31 October 2026:

- Python 3.12.14; Flask 3.1.2; Gunicorn 23.0.0; system Chromium.
- Reusable installation script executed successfully against the existing virtual environment.
- `python -m pytest -q`: **22 passed**. Tests cover imports, invalid rows, file deduplication, older-snapshot rejection, name history, per-field provenance, financial units and revisions, missing values, consecutive-year growth, security/company deduplication, independent LLP/MSME totals, query validation, pagination, CSV/XLSX exports, authentication, CSRF, roles, file uploads, XLSX parsing and connector pagination/schema/error handling.
- `python tests/browser_smoke.py`: passed. Real Chromium exercised login, every module, a temporary synthetic CSV import, company profile, insufficient-evidence scoring display, CSV download, state selection and 390px mobile layout. No JavaScript exceptions. The browser test database was temporary and removed; it did not populate the application's database.
- `node --check intelligence/static/app.js`: passed.
- Gunicorn started with two workers and two threads, reloaded after final changes. Local requests: health endpoint 200 with expected payload, login 200 with sign-in form, JavaScript 200, unauthenticated company API 401.
- No database files, user accounts, session keys or credentials are included in the repository or Vercel deployment. No default user is created. Provision an account using `flask --app wsgi create-user admin` before first use.
- All seven official-source probes were unavailable through the configured proxy. NSE CSV and OGD catalog requests returned proxy CONNECT 403. No live official master-data import or remote dataset-schema verification passed.

Saved environment configuration: installation script, service startup/readiness instructions, and additional official-source domains. Draft saves were confirmed; applying/publishing the configuration and restoration in a new task were not validated. No public deployment, Docker build, live financial-data reconciliation, national-scale load test or production backup-restore test is claimed.

Initial code-only Vercel deployment was built without records. The user subsequently explicitly authorised publication of all uploaded company data. The current static deployment includes the authorised master records and separate CIN exceptions. Database files, accounts, session keys, credentials and backups remain excluded.

Public export verification: 32,078 distinct CINs; JSON checksum recorded and verified at build time. Static browser tests passed for totals, pagination, search, profile data, filtered CSV export, private/public/listed/unlisted views, missing-financial filtering, source status and mobile layout. No Flask APIs are required by the static deployment. The Python backend suite remains at 22 passed. Actual hosted Vercel deployment is not independently verified by these local checks.

Large-file workaround: a streaming browser CSV loader and automatic transfer-file exporter were verified using a 48,689,621-byte synthetic CSV. Tests checked 100,000 new synthetic records, an update to an existing CIN, duplicate handling, one invalid exception, cancellation, file-level rollback, older-snapshot protection, restore, mobile layout and zero upload requests. Downloaded parts each stayed at or below 8 MiB and collectively retained all 100,001 distinct valid input CINs. Parser tests covered BOM, CRLF and quotes/newlines across chunk boundaries. The synthetic data was temporary and did not enter the application database or public dataset.

The user's full Maharashtra CSV has not yet been transferred or imported: it exceeded the attachment-transfer limit. The loader enables local exploration and smaller part generation; it does not pretend to update the shared server dataset by itself. The existing published agriculture dataset remains unchanged pending receipt of the generated parts.

All-India ZIP support: compressed CSV archives were tested with a 5,000-company/five-state fixture and a 253,533,231-byte standard ZIP containing 225,000 synthetic unique companies. Both verified cross-file CIN deduplication, skipped non-company CSVs, validation exceptions, local state filtering, sorted queries, profiles, filtered CSV downloads, persistent reopening after page reload, mobile layout, CRC-corruption rollback and zero upload requests. Records were stored and queried via IndexedDB; temporary fixtures did not enter the application database or public export. Browser storage/disk quota and ZIP-format limits are documented. The actual user-owned 200 MB all-India ZIP has not been read or published.
