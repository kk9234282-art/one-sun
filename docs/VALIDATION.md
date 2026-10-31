# Validation record

Validated in the current cloud machine on 31 October 2026:

- Python 3.12.14; Flask 3.1.2; Gunicorn 23.0.0; system Chromium.
- Reusable installation script executed successfully against the existing virtual environment.
- `python -m pytest -q`: **22 passed**. Tests cover imports, invalid rows, file deduplication, older-snapshot rejection, name history, per-field provenance, financial units and revisions, missing values, consecutive-year growth, security/company deduplication, independent LLP/MSME totals, query validation, pagination, CSV/XLSX exports, authentication, CSRF, roles, file uploads, XLSX parsing and connector pagination/schema/error handling.
- `python tests/browser_smoke.py`: passed. Real Chromium exercised login, every module, a temporary synthetic CSV import, company profile, insufficient-evidence scoring display, CSV download, state selection and 390px mobile layout. No JavaScript exceptions. The browser test database was temporary and removed; it did not populate the application's database.
- `node --check intelligence/static/app.js`: passed.
- Gunicorn started with two workers and two threads, reloaded after final changes. Local requests: health endpoint 200 with expected payload, login 200 with sign-in form, JavaScript 200, unauthenticated company API 401.
- No database or uploaded company records are included in the repository or Vercel preview. No default user is created. Provision an account using `flask --app wsgi create-user admin` before first use.
- All seven official-source probes were unavailable through the configured proxy. NSE CSV and OGD catalog requests returned proxy CONNECT 403. No live official master-data import or remote dataset-schema verification passed.

Saved environment configuration: installation script, service startup/readiness instructions, and additional official-source domains. Draft saves were confirmed; applying/publishing the configuration and restoration in a new task were not validated. No public deployment, Docker build, live financial-data reconciliation, national-scale load test or production backup-restore test is claimed.

Code-only Vercel deployment: the build runs without a local database or Python dependencies. Company records, dataset-derived reports/screenshots and statistics are excluded from the published artifact. A private local copy is retained separately from Git.
