# Listed-company financial statements

## Current data status

The supplied company master contains registration, listing labels and capital fields, but no financial statements. As of this change, **no real financial overlay has been imported or published**. Public availability of exchange filings does not populate the master CSV automatically. Synthetic test statements are confined to tests and are never built into the site.

On 2026-11-01, the active cloud network policy excluded NSE/BSE. Requests to the official NSE financial-results page and BSE corporate-results page both failed with `ProxyError`. The saved environment draft already contains the NSE/BSE domains, but runtime status confirms those custom domains are not active. Review and save the pending network configuration in Cloud Environment settings, then publish the environment before retrying official downloads. Access must use the configured proxy and verified TLS; access controls and undocumented APIs are not bypassed. No paid service or API subscription has been added.

The national site now supports a separately imported annual-statement overlay. Until real statements are provided, listed-company revenue, profit and FY fields show **Not imported**. A missing figure within an imported statement shows **Not reported**. This is a data-coverage distinction, not a claim that filings do not exist publicly.

## Input and validation

Use the header-only template at `intelligence/static/listed-financials-template.csv`. Supply an authorised real financial export, including an exact CIN, annual period end, 12-month duration, FY-end year, standalone/consolidated basis, units, source URL and actual source publication date. Financial-year year must agree with the period-end year. NSE/BSE source IDs must reference their official HTTPS domains. Company-report references are accepted as explicitly supplied sources, without implying independent verification. Source files do not authenticate their own provenance merely by naming an exchange.

All CINs must exist in the exact listed subset of this master snapshot. Names, tickers, PINs and paid-up capital are never used to infer financial values or company identity. Quarterly/TTM data, future dates, unknown units, non-finite amounts, invalid dates and missing references are rejected. A missing value remains null; zero and negative profit remain real values. Conflicting same-date records block publication. Later source publications can replace an earlier statement for the same CIN/year/basis. The source CSV hash is recorded; the original export should be retained by its operator.

## Prepare and publish a real dataset

From the repository root:

```bash
.venv/bin/python scripts/build_listed_financials.py /path/to/real-financial-export.csv
```

Review `instance/build/listed-financials/validation-report.json`. Any rejected rows prevent dataset preparation. No records are sent to a network service. With a clean report and real data:

```bash
.venv/bin/python scripts/prepare_financial_branch.py --branch data/listed-financials-v1
```

This creates a reviewable, immutable data-only Git branch and pins its URL/checksum in `deployment/national/catalog.json`; it does not push or deploy automatically. Publish the prepared data branch and main catalog through the repository's normal deployment process. Use a new versioned branch for subsequent changes. The publisher checks the validation report, source snapshot and content hash. The build validates immutable data URLs and source-snapshot compatibility. Company data and account databases remain separate.

## Application behavior

The national worker verifies the financial pack's checksum and source snapshot, then joins by exact CIN. It selects the requested reporting basis and FY, or the latest imported annual year for that basis. It never silently falls back between standalone and consolidated accounts. Financial figures in the directory and CSV are converted to INR; profiles retain source units, period end, year, reporting basis, publication date and statement links.

Annual growth uses the immediately preceding year with the same basis and fiscal period end, converting each year's units independently. Growth remains missing across gaps or changed period ends. Profit growth is not calculated from zero/negative prior profit. Selected financials feed the existing evidence-score rules; compliance and industry prospects remain unassessed.

Revenue/profit filters, sorts, overview coverage and exports use the selected figures. Financial filters use the small listed-company index rather than scanning the whole master. Uncovered listed companies keep blank financials. The existing public site remains functional when no financial descriptor is present.

Validation: `pytest`, `node tests/test_financials.mjs`, `node tests/test_online_worker.mjs`, and the listed-company browser smoke test. The financial tests use temporary or in-memory fixtures only.
